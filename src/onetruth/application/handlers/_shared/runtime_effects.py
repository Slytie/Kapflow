from __future__ import annotations

import hashlib
import json
import sqlite3
from typing import Any
from uuid import uuid4

from onetruth.application.handlers._shared.command_boundary import CommandError
from onetruth.infrastructure.events.event_store import utc_now_iso
from onetruth.infrastructure.repositories.edge_executions import (
    EdgeExecutionConflictError,
    create_edge_execution,
    get_edge_execution,
    get_edge_execution_by_correlation,
)
from onetruth.infrastructure.repositories.input_bindings import (
    InputBindingConflictError,
    create_workflow_run_input,
)
from onetruth.infrastructure.repositories.workflow_runs import (
    create_workflow_run,
    get_workflow_run,
    list_workflow_runs,
)


DEFAULT_HANDOFF_POLICY_VERSION = "logistics_handoff_policy.v0"
HANDOFF_EFFECT_SCOPE_SCHEMA_VERSION = "handoff_effect_scope.v1"


def handoff_artifact_source_truth(
    *,
    workflow_run_id: str,
    artifact: dict[str, Any],
) -> dict[str, str]:
    return {
        "workflow_run_id": _required_text(workflow_run_id, field_name="workflow_run_id"),
        "artifact_version_id": _required_text(
            artifact.get("artifact_version_id"),
            field_name="artifact_version_id",
        ),
        "artifact_kind": _required_text(
            artifact.get("artifact_kind"),
            field_name="artifact_kind",
        ),
        "content_digest": _required_text(
            artifact.get("content_digest"),
            field_name="content_digest",
        ),
    }


def build_handoff_effect_scope(
    *,
    edge_id: str,
    source_truth: list[dict[str, Any]] | tuple[dict[str, Any], ...],
    target_partition_kind: str,
    target_partition_key: str,
    policy_version: str = DEFAULT_HANDOFF_POLICY_VERSION,
    policy_context: dict[str, Any] | None = None,
) -> dict[str, Any]:
    normalized_source_truth = [
        _normalize_handoff_source_truth(item, index=index)
        for index, item in enumerate(source_truth)
    ]
    if not normalized_source_truth:
        raise CommandError(
            code="invalid_handoff_effect_scope",
            message="handoff effect scope requires at least one source truth record",
            details={},
        )
    scope_body = {
        "schema_version": HANDOFF_EFFECT_SCOPE_SCHEMA_VERSION,
        "edge_id": _required_text(edge_id, field_name="edge_id"),
        "source_truth": normalized_source_truth,
        "target_partition": {
            "partition_kind": _required_text(
                target_partition_kind,
                field_name="target_partition_kind",
            ),
            "partition_key": _required_text(
                target_partition_key,
                field_name="target_partition_key",
            ),
        },
        "policy_version": _required_text(policy_version, field_name="policy_version"),
    }
    if policy_context is not None:
        scope_body["policy_context"] = _normalize_json_object(
            policy_context,
            field_name="policy_context",
        )
    return {
        "scope_key": _stable_handoff_scope_key(scope_body),
        **scope_body,
    }


def resolve_or_create_workflow_run_effects(
    connection: sqlite3.Connection,
    *,
    workflow_id: str,
    tenant_id: str,
    domain_id: str,
    partition_kind: str,
    partition_key: str,
    activation_key: str,
    logical_date: str | None,
    created_at: str | None = None,
    workflow_version: str = "v1",
    state: str = "OPEN",
    workflow_run_id: str | None = None,
) -> dict[str, Any]:
    existing_runs = [
        run
        for run in list_workflow_runs(
            connection,
            workflow_id=workflow_id,
            tenant_id=tenant_id,
            domain_id=domain_id,
            state=None,
        )
        if str(run["partition_key"]) == partition_key
    ]
    for run in existing_runs:
        if str(run["activation_key"]) == activation_key:
            return run
    if existing_runs:
        raise CommandError(
            code="activation_key_drift_detected",
            message="existing workflow run partition uses a different activation key",
            details={
                "tenant_id": tenant_id,
                "domain_id": domain_id,
                "workflow_id": workflow_id,
                "partition_kind": partition_kind,
                "partition_key": partition_key,
                "expected_activation_key": activation_key,
                "existing_activation_keys": sorted(
                    str(run["activation_key"]) for run in existing_runs
                ),
                "existing_workflow_run_ids": sorted(
                    str(run["workflow_run_id"]) for run in existing_runs
                ),
            },
        )

    resolved_workflow_run_id = workflow_run_id or f"wr-{uuid4()}"
    now = created_at or utc_now_iso()
    try:
        create_workflow_run(
            connection,
            workflow_run_id=resolved_workflow_run_id,
            workflow_id=workflow_id,
            workflow_version=workflow_version,
            tenant_id=tenant_id,
            domain_id=domain_id,
            partition_key=partition_key,
            logical_date=logical_date,
            activation_key=activation_key,
            state=state,
            created_at=now,
        )
    except sqlite3.IntegrityError:
        refreshed = [
            run
            for run in list_workflow_runs(
                connection,
                workflow_id=workflow_id,
                tenant_id=tenant_id,
                domain_id=domain_id,
                state=None,
            )
            if str(run["partition_key"]) == partition_key
        ]
        for run in refreshed:
            if str(run["activation_key"]) == activation_key:
                return run
        if refreshed:
            raise CommandError(
                code="activation_key_drift_detected",
                message="existing workflow run partition uses a different activation key",
                details={
                    "tenant_id": tenant_id,
                    "domain_id": domain_id,
                    "workflow_id": workflow_id,
                    "partition_kind": partition_kind,
                    "partition_key": partition_key,
                    "expected_activation_key": activation_key,
                    "existing_activation_keys": sorted(
                        str(run["activation_key"]) for run in refreshed
                    ),
                    "existing_workflow_run_ids": sorted(
                        str(run["workflow_run_id"]) for run in refreshed
                    ),
                },
            )
        raise

    created = get_workflow_run(connection, resolved_workflow_run_id)
    if created is None:
        raise CommandError(
            code="workflow_run_not_found",
            message="workflow run not found after creation",
            details={"workflow_run_id": resolved_workflow_run_id},
        )
    return created


def create_or_validate_workflow_artifact_input_effects(
    connection: sqlite3.Connection,
    *,
    workflow_run_id: str,
    binding_key: str,
    source_ref: str,
    artifact_version_id: str,
    metadata_json: dict[str, Any],
    captured_at: str,
    replace_on_conflict: bool = False,
) -> dict[str, Any]:
    try:
        create_workflow_run_input(
            connection,
            workflow_run_id=workflow_run_id,
            binding_key=binding_key,
            source_kind="artifact_version",
            source_ref=source_ref,
            artifact_version_id=artifact_version_id,
            pointer_key=None,
            pointer_generation=None,
            pointer_artifact_version_id=None,
            captured_by_task_run_id=None,
            captured_at=captured_at,
            metadata_json=metadata_json,
        )
        created = get_workflow_artifact_input_effects(
            connection,
            workflow_run_id=workflow_run_id,
            binding_key=binding_key,
        )
        if created is None:
            raise CommandError(
                code="workflow_input_binding_not_found",
                message="workflow input binding was not found after creation",
                details={"workflow_run_id": workflow_run_id, "binding_key": binding_key},
            )
        return {"binding": created, "effect": "created"}
    except InputBindingConflictError:
        existing = get_workflow_artifact_input_effects(
            connection,
            workflow_run_id=workflow_run_id,
            binding_key=binding_key,
        )
        if _workflow_artifact_binding_matches(
            existing,
            source_ref=source_ref,
            artifact_version_id=artifact_version_id,
        ):
            return {"binding": existing, "effect": "replay"}
        if replace_on_conflict and existing is not None:
            _replace_workflow_artifact_input_effects(
                connection,
                workflow_run_id=workflow_run_id,
                binding_key=binding_key,
                source_ref=source_ref,
                artifact_version_id=artifact_version_id,
                metadata_json=metadata_json,
                captured_at=captured_at,
            )
            replaced = get_workflow_artifact_input_effects(
                connection,
                workflow_run_id=workflow_run_id,
                binding_key=binding_key,
            )
            return {"binding": replaced, "effect": "replaced"}
        raise CommandError(
            code="workflow_input_binding_conflict",
            message="existing workflow input binding conflicts with replay inputs",
            details={
                "workflow_run_id": workflow_run_id,
                "binding_key": binding_key,
                "expected_source_ref": source_ref,
                "expected_artifact_version_id": artifact_version_id,
                "existing_source_ref": (
                    str(existing.get("source_ref"))
                    if existing is not None and existing.get("source_ref") is not None
                    else None
                ),
                "existing_artifact_version_id": (
                    str(existing.get("artifact_version_id"))
                    if existing is not None and existing.get("artifact_version_id") is not None
                    else None
                ),
            },
        )


def get_workflow_artifact_input_effects(
    connection: sqlite3.Connection,
    *,
    workflow_run_id: str,
    binding_key: str,
) -> dict[str, Any] | None:
    row = connection.execute(
        """
        SELECT
            workflow_run_id,
            binding_key,
            source_kind,
            source_ref,
            artifact_version_id,
            metadata_json
        FROM workflow_run_inputs
        WHERE workflow_run_id = ? AND binding_key = ?
        LIMIT 1
        """,
        (workflow_run_id, binding_key),
    ).fetchone()
    if row is None:
        return None
    item = dict(row)
    if item.get("metadata_json") is not None:
        item["metadata_json"] = json.loads(str(item["metadata_json"]))
    return item


def create_or_reuse_edge_execution_effects(
    connection: sqlite3.Connection,
    *,
    edge_execution_id: str,
    edge_id: str,
    source_workflow_run_id: str,
    source_stage_id: str,
    source_artifact_version_id: str,
    source_activation_key: str,
    target_workflow_id: str,
    target_stage_id: str,
    target_partition_kind: str,
    target_partition_key: str,
    target_activation_key: str,
    correlation_key: str,
    materialize_idempotency_key: str,
    status: str,
    cursor_state: dict[str, Any] | None,
    compensation_state: dict[str, Any] | None,
    input_bindings: dict[str, Any] | None,
    trigger_ref: str | None,
    seed_artifact_version_id: str | None,
    target_workflow_run_id: str | None,
    activated_at: str | None,
    created_at: str,
) -> dict[str, Any]:
    existing = get_edge_execution_by_correlation(
        connection,
        edge_id=edge_id,
        correlation_key=correlation_key,
    )
    if existing is not None:
        _validate_existing_edge_execution(
            existing,
            edge_id=edge_id,
            source_workflow_run_id=source_workflow_run_id,
            source_stage_id=source_stage_id,
            source_artifact_version_id=source_artifact_version_id,
            source_activation_key=source_activation_key,
            target_workflow_id=target_workflow_id,
            target_stage_id=target_stage_id,
            target_partition_kind=target_partition_kind,
            target_partition_key=target_partition_key,
            target_activation_key=target_activation_key,
            correlation_key=correlation_key,
            seed_artifact_version_id=seed_artifact_version_id,
            target_workflow_run_id=target_workflow_run_id,
        )
        return existing
    try:
        create_edge_execution(
            connection,
            edge_execution_id=edge_execution_id,
            edge_id=edge_id,
            source_workflow_run_id=source_workflow_run_id,
            source_stage_id=source_stage_id,
            source_artifact_version_id=source_artifact_version_id,
            source_activation_key=source_activation_key,
            target_workflow_id=target_workflow_id,
            target_stage_id=target_stage_id,
            target_partition_kind=target_partition_kind,
            target_partition_key=target_partition_key,
            target_activation_key=target_activation_key,
            correlation_key=correlation_key,
            materialize_idempotency_key=materialize_idempotency_key,
            status=status,
            cursor_state=cursor_state,
            compensation_state=compensation_state,
            input_bindings=input_bindings,
            trigger_ref=trigger_ref,
            seed_artifact_version_id=seed_artifact_version_id,
            target_workflow_run_id=target_workflow_run_id,
            activated_at=activated_at,
            created_at=created_at,
        )
    except EdgeExecutionConflictError:
        replay = get_edge_execution_by_correlation(
            connection,
            edge_id=edge_id,
            correlation_key=correlation_key,
        )
        if replay is None:
            raise
        _validate_existing_edge_execution(
            replay,
            edge_id=edge_id,
            source_workflow_run_id=source_workflow_run_id,
            source_stage_id=source_stage_id,
            source_artifact_version_id=source_artifact_version_id,
            source_activation_key=source_activation_key,
            target_workflow_id=target_workflow_id,
            target_stage_id=target_stage_id,
            target_partition_kind=target_partition_kind,
            target_partition_key=target_partition_key,
            target_activation_key=target_activation_key,
            correlation_key=correlation_key,
            seed_artifact_version_id=seed_artifact_version_id,
            target_workflow_run_id=target_workflow_run_id,
        )
        return replay

    created = get_edge_execution(connection, edge_execution_id)
    if created is None:
        raise CommandError(
            code="edge_execution_not_found",
            message="edge execution not found after creation",
            details={"edge_execution_id": edge_execution_id},
        )
    return created


def _workflow_artifact_binding_matches(
    existing: dict[str, Any] | None,
    *,
    source_ref: str,
    artifact_version_id: str,
) -> bool:
    return (
        existing is not None
        and str(existing.get("source_kind") or "") == "artifact_version"
        and str(existing.get("source_ref") or "") == source_ref
        and str(existing.get("artifact_version_id") or "") == artifact_version_id
    )


def _normalize_handoff_source_truth(
    raw: dict[str, Any],
    *,
    index: int,
) -> dict[str, str]:
    if not isinstance(raw, dict):
        raise CommandError(
            code="invalid_handoff_effect_scope",
            message="source truth entries must be objects",
            details={"index": index},
        )
    return {
        "workflow_run_id": _required_text(
            raw.get("workflow_run_id"),
            field_name=f"source_truth[{index}].workflow_run_id",
        ),
        "artifact_version_id": _required_text(
            raw.get("artifact_version_id"),
            field_name=f"source_truth[{index}].artifact_version_id",
        ),
        "artifact_kind": _required_text(
            raw.get("artifact_kind"),
            field_name=f"source_truth[{index}].artifact_kind",
        ),
        "content_digest": _required_text(
            raw.get("content_digest"),
            field_name=f"source_truth[{index}].content_digest",
        ),
    }


def _stable_handoff_scope_key(scope_body: dict[str, Any]) -> str:
    body = json.dumps(
        scope_body,
        separators=(",", ":"),
        sort_keys=True,
        ensure_ascii=True,
    )
    return f"handoff-scope:{hashlib.sha256(body.encode('utf-8')).hexdigest()[:32]}"


def _normalize_json_object(value: dict[str, Any], *, field_name: str) -> dict[str, Any]:
    try:
        encoded = json.dumps(
            value,
            separators=(",", ":"),
            sort_keys=True,
            ensure_ascii=True,
        )
    except (TypeError, ValueError) as exc:
        raise CommandError(
            code="invalid_handoff_effect_scope",
            message=f"{field_name} must be JSON-serializable",
            details={"field_name": field_name},
        ) from exc
    decoded = json.loads(encoded)
    if not isinstance(decoded, dict):
        raise CommandError(
            code="invalid_handoff_effect_scope",
            message=f"{field_name} must be a JSON object",
            details={"field_name": field_name},
        )
    return decoded


def _required_text(value: Any, *, field_name: str) -> str:
    text = str(value or "").strip()
    if text:
        return text
    raise CommandError(
        code="invalid_handoff_effect_scope",
        message="handoff effect scope field must be a non-empty string",
        details={"field_name": field_name},
    )


def _replace_workflow_artifact_input_effects(
    connection: sqlite3.Connection,
    *,
    workflow_run_id: str,
    binding_key: str,
    source_ref: str,
    artifact_version_id: str,
    metadata_json: dict[str, Any],
    captured_at: str,
) -> None:
    connection.execute(
        """
        UPDATE workflow_run_inputs
        SET
            source_kind = 'artifact_version',
            source_ref = ?,
            artifact_version_id = ?,
            pointer_key = NULL,
            pointer_generation = NULL,
            pointer_artifact_version_id = NULL,
            captured_by_task_run_id = NULL,
            captured_at = ?,
            metadata_json = ?
        WHERE workflow_run_id = ? AND binding_key = ?
        """,
        (
            source_ref,
            artifact_version_id,
            captured_at,
            json.dumps(metadata_json, separators=(",", ":")),
            workflow_run_id,
            binding_key,
        ),
    )


def _validate_existing_edge_execution(
    existing: dict[str, Any],
    *,
    edge_id: str,
    source_workflow_run_id: str,
    source_stage_id: str,
    source_artifact_version_id: str,
    source_activation_key: str,
    target_workflow_id: str,
    target_stage_id: str,
    target_partition_kind: str,
    target_partition_key: str,
    target_activation_key: str,
    correlation_key: str,
    seed_artifact_version_id: str | None,
    target_workflow_run_id: str | None,
) -> None:
    expected_fields: dict[str, object | None] = {
        "edge_id": edge_id,
        "source_workflow_run_id": source_workflow_run_id,
        "source_stage_id": source_stage_id,
        "source_artifact_version_id": source_artifact_version_id,
        "source_activation_key": source_activation_key,
        "target_workflow_id": target_workflow_id,
        "target_stage_id": target_stage_id,
        "target_partition_kind": target_partition_kind,
        "target_partition_key": target_partition_key,
        "target_activation_key": target_activation_key,
        "correlation_key": correlation_key,
    }
    if seed_artifact_version_id is not None:
        expected_fields["seed_artifact_version_id"] = seed_artifact_version_id
    if target_workflow_run_id is not None:
        expected_fields["target_workflow_run_id"] = target_workflow_run_id

    mismatches = {
        field: {"expected": expected, "actual": existing.get(field)}
        for field, expected in expected_fields.items()
        if existing.get(field) != expected
    }
    if mismatches:
        raise CommandError(
            code="edge_execution_replay_conflict",
            message="existing edge execution conflicts with replay inputs",
            details={
                "edge_execution_id": existing.get("edge_execution_id"),
                "edge_id": edge_id,
                "correlation_key": correlation_key,
                "mismatches": mismatches,
            },
        )
