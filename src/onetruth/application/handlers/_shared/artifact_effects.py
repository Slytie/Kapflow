from __future__ import annotations

import hashlib
import json
from pathlib import Path
import sqlite3
from typing import Any
from uuid import uuid4

from onetruth.application.handlers._shared.command_boundary import (
    CommandError,
    _event_envelope,
    _validate_task_run_belongs_to_workflow,
    _workflow_scope,
)
from onetruth.domain.pointer_address import (
    PartitionRef,
    PointerAddressError,
    load_dataset_partition_index,
)
from onetruth.infrastructure.artifacts.storage import (
    ArtifactIngressDescriptor,
    ArtifactStorageError,
    write_blob,
)
from onetruth.infrastructure.events.event_store import append_event, utc_now_iso
from onetruth.infrastructure.repositories.approvals import get_approval
from onetruth.infrastructure.repositories.artifact_links import (
    create_artifact_link,
    list_artifact_links_for_artifact,
)
from onetruth.infrastructure.repositories.artifact_provenance import (
    create_artifact_provenance_edge,
)
from onetruth.infrastructure.repositories.artifact_versions import (
    create_artifact_version,
    get_artifact_version,
)
from onetruth.infrastructure.repositories.execution_sessions import get_execution_session
from onetruth.infrastructure.repositories.flags import get_flag
from onetruth.infrastructure.repositories.human_tasks import get_human_task
from onetruth.infrastructure.repositories.input_bindings import (
    create_task_input_binding,
    create_workflow_run_input,
)
from onetruth.infrastructure.repositories.policy_decisions import get_policy_decision
from onetruth.infrastructure.repositories.tool_executions import get_tool_execution


def _create_artifact_version_effects(
    connection: sqlite3.Connection,
    payload: dict[str, Any],
    *,
    event_idempotency: str | None,
) -> dict[str, Any]:
    metadata_json = payload.get("metadata_json")
    if not isinstance(metadata_json, dict):
        raise CommandError(
            code="invalid_metadata_json",
            message="metadata_json must be a JSON object",
            details={},
        )
    requested_artifact_version_id = payload.get("artifact_version_id")
    artifact_version_id = str(requested_artifact_version_id or f"av-{uuid4()}")
    workflow_run_id = str(payload["workflow_run_id"])
    task_run_id = str(payload["task_run_id"]) if payload.get("task_run_id") is not None else None
    artifact_kind = str(payload["artifact_kind"])
    parent_artifact_version_id = (
        str(payload["parent_artifact_version_id"])
        if payload.get("parent_artifact_version_id") is not None
        else None
    )
    supersedes_artifact_version_id = (
        str(payload["supersedes_artifact_version_id"])
        if payload.get("supersedes_artifact_version_id") is not None
        else None
    )
    lineage_note = (
        str(payload["lineage_note"])
        if payload.get("lineage_note") is not None
        else None
    )
    artifact_links = _normalize_artifact_links(payload.get("links"))
    workflow_scope = _workflow_scope(connection, workflow_run_id)
    if task_run_id is not None:
        _validate_task_run_belongs_to_workflow(
            connection,
            task_run_id=task_run_id,
            workflow_run_id=workflow_run_id,
        )
    now = utc_now_iso()
    canonical_scope = _canonical_artifact_scope_fields(
        tenant_id=workflow_scope["tenant_id"],
        domain_id=workflow_scope["domain_id"],
        workflow_partition_key=workflow_scope["partition_key"],
        artifact_kind=artifact_kind,
    )
    has_partition_kind_override = payload.get("canonical_partition_kind") is not None
    has_partition_key_override = payload.get("canonical_partition_key") is not None
    if has_partition_kind_override != has_partition_key_override:
        raise CommandError(
            code="invalid_payload",
            message="canonical_partition_kind and canonical_partition_key must be provided together",
            details={},
        )
    if has_partition_kind_override and has_partition_key_override:
        canonical_scope["partition_kind"] = str(payload["canonical_partition_kind"])
        canonical_scope["partition_key"] = str(payload["canonical_partition_key"])
    create_artifact_version(
        connection,
        artifact_version_id=artifact_version_id,
        workflow_run_id=workflow_run_id,
        tenant_id=canonical_scope["tenant_id"],
        domain_id=canonical_scope["domain_id"],
        dataset_key=canonical_scope["dataset_key"],
        partition_kind=canonical_scope["partition_kind"],
        partition_key=canonical_scope["partition_key"],
        task_run_id=task_run_id,
        artifact_kind=artifact_kind,
        artifact_role=(
            str(payload["artifact_role"])
            if payload.get("artifact_role") is not None
            else None
        ),
        media_type=str(payload["media_type"]),
        storage_uri=str(payload["storage_uri"]),
        content_digest=str(payload["content_digest"]),
        byte_size=(
            int(payload["byte_size"])
            if payload.get("byte_size") is not None
            else None
        ),
        metadata_json=metadata_json,
        parent_artifact_version_id=parent_artifact_version_id,
        supersedes_artifact_version_id=supersedes_artifact_version_id,
        lineage_note=lineage_note,
        created_at=now,
    )
    _write_artifact_provenance_compatibility_edges(
        connection,
        workflow_run_id=workflow_run_id,
        artifact_version_id=artifact_version_id,
        parent_artifact_version_id=parent_artifact_version_id,
        supersedes_artifact_version_id=supersedes_artifact_version_id,
        created_at=now,
    )
    _capture_artifact_lineage_input_bindings(
        connection,
        workflow_run_id=workflow_run_id,
        task_run_id=task_run_id,
        artifact_version_id=artifact_version_id,
        parent_artifact_version_id=parent_artifact_version_id,
        supersedes_artifact_version_id=supersedes_artifact_version_id,
        captured_at=now,
        event_idempotency=event_idempotency,
    )
    links = [
        {"rel": "subject", "type": "artifact_version", "id": artifact_version_id},
        {"rel": "subject", "type": "workflow_run", "id": workflow_run_id},
    ]
    if task_run_id is not None:
        links.append({"rel": "subject", "type": "task_run", "id": task_run_id})
    for artifact_link in artifact_links:
        _validate_artifact_link_subject(
            connection,
            workflow_run_id=workflow_run_id,
            subject_kind=artifact_link["subject_kind"],
            subject_id=artifact_link["subject_id"],
        )
        create_artifact_link(
            connection,
            artifact_version_id=artifact_version_id,
            workflow_run_id=workflow_run_id,
            subject_kind=artifact_link["subject_kind"],
            subject_id=artifact_link["subject_id"],
            relation_kind=artifact_link["relation_kind"],
            created_at=now,
            created_by_actor_id=str(payload.get("actor_id", "system:runtime")),
            created_by_actor_type=str(payload.get("actor_type", "system")),
        )
        link_payload = {
            "rel": artifact_link["relation_kind"],
            "type": artifact_link["subject_kind"],
            "id": artifact_link["subject_id"],
        }
        if link_payload not in links:
            links.append(link_payload)

    append_event(
        connection,
        _event_envelope(
            event_type="artifact.version.created",
            tenant_id=workflow_scope["tenant_id"],
            domain_id=workflow_scope["domain_id"],
            actor_type=str(payload.get("actor_type", "system")),
            actor_id=str(payload.get("actor_id", "system:runtime")),
            links=links,
            payload={
                "artifact_version_id": artifact_version_id,
                "dataset_key": artifact_kind,
                "supersedes_artifact_version_id": supersedes_artifact_version_id,
            },
            idempotency_key=event_idempotency,
        ),
    )

    artifact_version = get_artifact_version(connection, artifact_version_id)
    if artifact_version is None:
        raise CommandError(
            code="artifact_version_not_found",
            message="artifact version was not found after creation",
            details={"artifact_version_id": artifact_version_id},
        )
    artifact_version["links"] = list_artifact_links_for_artifact(
        connection,
        artifact_version_id=artifact_version_id,
    )
    return artifact_version


def canonical_json_bytes(value: Any) -> bytes:
    return json.dumps(
        value,
        separators=(",", ":"),
        sort_keys=True,
        ensure_ascii=True,
        allow_nan=False,
    ).encode("utf-8")


def persist_generated_artifact_effects(
    connection: sqlite3.Connection,
    *,
    storage_root: Path,
    workflow_run_id: str,
    artifact_kind: str,
    artifact_role: str | None,
    media_type: str,
    file_name: str,
    payload: Any,
    metadata_json: dict[str, Any] | None = None,
    actor_id: str = "system:runtime",
    actor_type: str = "system",
    artifact_version_id: str | None = None,
    task_run_id: str | None = None,
    parent_artifact_version_id: str | None = None,
    supersedes_artifact_version_id: str | None = None,
    lineage_note: str | None = None,
    links: list[dict[str, Any]] | None = None,
    canonical_partition_kind: str | None = None,
    canonical_partition_key: str | None = None,
    expected_content_digest: str | None = None,
    event_idempotency: str | None = None,
) -> dict[str, Any]:
    has_partition_kind_override = canonical_partition_kind is not None
    has_partition_key_override = canonical_partition_key is not None
    if has_partition_kind_override != has_partition_key_override:
        raise CommandError(
            code="invalid_payload",
            message="canonical_partition_kind and canonical_partition_key must be provided together",
            details={},
        )
    if metadata_json is None:
        metadata_json = {}
    if not isinstance(metadata_json, dict):
        raise CommandError(
            code="invalid_metadata_json",
            message="metadata_json must be a JSON object",
            details={},
        )
    try:
        json.dumps(
            metadata_json,
            separators=(",", ":"),
            sort_keys=True,
            ensure_ascii=True,
            allow_nan=False,
        )
    except (TypeError, ValueError) as exc:
        raise CommandError(
            code="invalid_metadata_json",
            message="metadata_json must be JSON-serializable",
            details={},
        ) from exc

    try:
        content = canonical_json_bytes(payload)
    except (TypeError, ValueError) as exc:
        raise CommandError(
            code="invalid_generated_artifact_payload",
            message="generated artifact payload must be JSON-serializable",
            details={},
        ) from exc

    content_digest = _generated_content_digest(content)
    byte_size = len(content)
    normalized_expected_digest = _normalize_expected_content_digest(expected_content_digest)
    if normalized_expected_digest is not None and normalized_expected_digest != content_digest:
        raise CommandError(
            code="generated_artifact_digest_mismatch",
            message="generated artifact digest did not match expected digest",
            details={
                "expected_content_digest": normalized_expected_digest,
                "actual_content_digest": content_digest,
            },
        )

    expected_scope = _expected_generated_artifact_scope(
        connection,
        workflow_run_id=workflow_run_id,
        artifact_kind=artifact_kind,
        canonical_partition_kind=canonical_partition_kind,
        canonical_partition_key=canonical_partition_key,
    )
    if artifact_version_id is not None:
        existing = get_artifact_version(connection, artifact_version_id)
        if existing is not None:
            _validate_existing_generated_artifact(
                existing,
                workflow_run_id=workflow_run_id,
                task_run_id=task_run_id,
                artifact_kind=artifact_kind,
                artifact_role=artifact_role,
                media_type=media_type,
                content_digest=content_digest,
                byte_size=byte_size,
                expected_scope=expected_scope,
            )
            existing["links"] = list_artifact_links_for_artifact(
                connection,
                artifact_version_id=artifact_version_id,
            )
            return {
                "artifact_version": existing,
                "generated": {
                    "file_name": file_name,
                    "media_type": media_type,
                    "byte_size": byte_size,
                    "content_digest": content_digest,
                    "storage_uri": str(existing["storage_uri"]),
                },
                "replay": True,
            }

    try:
        storage_uri, stored_digest, stored_byte_size = write_blob(
            storage_root=storage_root,
            workflow_run_id=workflow_run_id,
            file_name=file_name,
            content=content,
        )
    except ArtifactStorageError as exc:
        raise CommandError(
            code="generated_artifact_storage_failed",
            message=str(exc),
            details={},
        ) from exc
    if stored_digest != content_digest or stored_byte_size != byte_size:
        raise CommandError(
            code="generated_artifact_storage_failed",
            message="generated artifact storage digest or size mismatch",
            details={
                "expected_content_digest": content_digest,
                "stored_content_digest": stored_digest,
                "expected_byte_size": byte_size,
                "stored_byte_size": stored_byte_size,
            },
        )

    artifact_version = _create_artifact_version_effects(
        connection,
        {
            "artifact_version_id": artifact_version_id,
            "workflow_run_id": workflow_run_id,
            "task_run_id": task_run_id,
            "artifact_kind": artifact_kind,
            "artifact_role": artifact_role,
            "media_type": media_type,
            "storage_uri": storage_uri,
            "content_digest": content_digest,
            "byte_size": byte_size,
            "metadata_json": metadata_json,
            "parent_artifact_version_id": parent_artifact_version_id,
            "supersedes_artifact_version_id": supersedes_artifact_version_id,
            "lineage_note": lineage_note,
            "links": links,
            "actor_id": actor_id,
            "actor_type": actor_type,
            "canonical_partition_kind": canonical_partition_kind,
            "canonical_partition_key": canonical_partition_key,
        },
        event_idempotency=event_idempotency,
    )
    return {
        "artifact_version": artifact_version,
        "generated": {
            "file_name": file_name,
            "media_type": media_type,
            "byte_size": byte_size,
            "content_digest": content_digest,
            "storage_uri": storage_uri,
        },
        "replay": False,
    }


def _generated_content_digest(content: bytes) -> str:
    return f"sha256:{hashlib.sha256(content).hexdigest()}"


def _normalize_expected_content_digest(raw_digest: str | None) -> str | None:
    if raw_digest is None:
        return None
    digest = str(raw_digest).strip()
    if not digest:
        raise CommandError(
            code="invalid_payload",
            message="expected_content_digest must not be empty",
            details={},
        )
    if digest.startswith("sha256:"):
        return digest
    return f"sha256:{digest}"


def _expected_generated_artifact_scope(
    connection: sqlite3.Connection,
    *,
    workflow_run_id: str,
    artifact_kind: str,
    canonical_partition_kind: str | None,
    canonical_partition_key: str | None,
) -> dict[str, str | None]:
    workflow_scope = _workflow_scope(connection, workflow_run_id)
    expected_scope = _canonical_artifact_scope_fields(
        tenant_id=workflow_scope["tenant_id"],
        domain_id=workflow_scope["domain_id"],
        workflow_partition_key=workflow_scope["partition_key"],
        artifact_kind=artifact_kind,
    )
    if canonical_partition_kind is not None and canonical_partition_key is not None:
        expected_scope["partition_kind"] = canonical_partition_kind
        expected_scope["partition_key"] = canonical_partition_key
    return expected_scope


def _validate_existing_generated_artifact(
    existing: dict[str, Any],
    *,
    workflow_run_id: str,
    task_run_id: str | None,
    artifact_kind: str,
    artifact_role: str | None,
    media_type: str,
    content_digest: str,
    byte_size: int,
    expected_scope: dict[str, str | None],
) -> None:
    expected_fields: dict[str, object] = {
        "workflow_run_id": workflow_run_id,
        "artifact_kind": artifact_kind,
        "artifact_role": artifact_role,
        "media_type": media_type,
        "content_digest": content_digest,
        "byte_size": byte_size,
        "tenant_id": expected_scope["tenant_id"],
        "domain_id": expected_scope["domain_id"],
        "dataset_key": expected_scope["dataset_key"],
        "partition_kind": expected_scope["partition_kind"],
        "partition_key": expected_scope["partition_key"],
    }
    if task_run_id is not None:
        expected_fields["task_run_id"] = task_run_id
    mismatches = {
        field: {"expected": expected, "actual": existing.get(field)}
        for field, expected in expected_fields.items()
        if existing.get(field) != expected
    }
    if mismatches:
        raise CommandError(
            code="generated_artifact_conflict",
            message="existing generated artifact row does not match requested content",
            details={
                "artifact_version_id": existing.get("artifact_version_id"),
                "mismatches": mismatches,
            },
        )


def _ingest_artifact_document_effects(
    connection: sqlite3.Connection,
    payload: dict[str, Any],
    *,
    storage_root: Path,
    ingress_descriptor: ArtifactIngressDescriptor,
    raw_content: bytes,
    file_name: str,
    media_type: str,
    event_idempotency: str | None,
) -> dict[str, Any]:
    try:
        storage_uri, content_digest, byte_size = write_blob(
            storage_root=storage_root,
            workflow_run_id=str(payload["workflow_run_id"]),
            file_name=file_name,
            content=raw_content,
        )
    except ArtifactStorageError as exc:
        raise CommandError(
            code="artifact_ingress_failed",
            message=str(exc),
            details={},
        ) from exc

    metadata_json = payload.get("metadata_json")
    if metadata_json is None:
        metadata_json = {}
    if not isinstance(metadata_json, dict):
        raise CommandError(
            code="invalid_metadata_json",
            message="metadata_json must be a JSON object",
            details={},
        )
    metadata_json = {
        **metadata_json,
        "ingress_file_name": file_name,
        "ingress_media_type": media_type,
        "ingress_kind": ingress_descriptor.ingress_kind,
    }
    if ingress_descriptor.ingress_kind == "local_source_path":
        assert ingress_descriptor.source_path is not None
        seed_source_path = metadata_json.get("seed_source_path")
        if isinstance(seed_source_path, str):
            metadata_json["seed_source_path"] = _stable_ingress_source_path(
                seed_source_path
            )
        ingress_source_path = metadata_json.get("ingress_source_path")
        if isinstance(ingress_source_path, str):
            metadata_json["ingress_source_path"] = _stable_ingress_source_path(
                ingress_source_path
            )
        else:
            metadata_json.setdefault(
                "ingress_source_path",
                _stable_ingress_source_path(str(ingress_descriptor.source_path)),
            )
    else:
        metadata_json.pop("seed_source_path", None)
        metadata_json.pop("ingress_source_path", None)

    artifact_version = _create_artifact_version_effects(
        connection,
        {
            "artifact_version_id": payload.get("artifact_version_id"),
            "workflow_run_id": payload["workflow_run_id"],
            "task_run_id": payload.get("task_run_id"),
            "artifact_kind": payload["artifact_kind"],
            "artifact_role": payload.get("artifact_role"),
            "media_type": media_type,
            "storage_uri": storage_uri,
            "content_digest": content_digest,
            "byte_size": byte_size,
            "metadata_json": metadata_json,
            "parent_artifact_version_id": payload.get("parent_artifact_version_id"),
            "supersedes_artifact_version_id": payload.get("supersedes_artifact_version_id"),
            "lineage_note": payload.get("lineage_note"),
            "links": payload.get("links"),
            "actor_id": payload.get("actor_id", "system:runtime"),
            "actor_type": payload.get("actor_type", "system"),
        },
        event_idempotency=event_idempotency,
    )
    return {
        "artifact_version": artifact_version,
        "ingress": {
            "file_name": file_name,
            "media_type": media_type,
            "byte_size": byte_size,
            "content_digest": content_digest,
            "storage_uri": storage_uri,
        },
    }


def _stable_ingress_source_path(raw_path: str) -> str:
    normalized = raw_path.replace("\\", "/")
    parts = [part for part in normalized.split("/") if part and part != "."]
    for index, part in enumerate(parts):
        if part.lower() == "fixtures":
            return "/".join(["fixtures", *parts[index + 1 :]])
    fallback = Path(normalized).name
    return fallback or normalized


def _normalize_artifact_links(raw_links: Any) -> list[dict[str, str]]:
    if raw_links is None:
        return []
    if not isinstance(raw_links, list):
        raise CommandError(
            code="invalid_artifact_links",
            message="links must be a list of objects",
            details={},
        )
    normalized: list[dict[str, str]] = []
    dedupe: set[tuple[str, str, str]] = set()
    for index, raw in enumerate(raw_links):
        if not isinstance(raw, dict):
            raise CommandError(
                code="invalid_artifact_links",
                message="links entries must be objects",
                details={"index": index},
            )
        subject_kind = raw.get("subject_kind")
        subject_id = raw.get("subject_id")
        relation_kind = raw.get("relation_kind") or "attachment"
        if subject_kind is None or subject_id is None:
            raise CommandError(
                code="invalid_artifact_links",
                message="each link requires subject_kind and subject_id",
                details={"index": index},
            )
        item = {
            "subject_kind": str(subject_kind),
            "subject_id": str(subject_id),
            "relation_kind": str(relation_kind),
        }
        key = (item["subject_kind"], item["subject_id"], item["relation_kind"])
        if key in dedupe:
            raise CommandError(
                code="invalid_artifact_links",
                message="duplicate link in links payload",
                details={"subject_kind": item["subject_kind"], "subject_id": item["subject_id"]},
            )
        dedupe.add(key)
        normalized.append(item)
    return normalized


def _validate_artifact_link_subject(
    connection: sqlite3.Connection,
    *,
    workflow_run_id: str,
    subject_kind: str,
    subject_id: str,
) -> None:
    if subject_kind == "workflow_run":
        if subject_id != workflow_run_id:
            raise CommandError(
                code="cross_workflow_link_reference",
                message="workflow_run attachment link must target the same workflow_run_id",
                details={"workflow_run_id": workflow_run_id, "subject_id": subject_id},
            )
        _workflow_scope(connection, workflow_run_id)
        return

    if subject_kind == "task_run":
        _validate_task_run_belongs_to_workflow(
            connection,
            task_run_id=subject_id,
            workflow_run_id=workflow_run_id,
        )
        return

    if subject_kind == "human_task":
        human_task = get_human_task(connection, subject_id)
        if human_task is None:
            raise CommandError(
                code="human_task_not_found",
                message="human task not found for artifact link",
                details={"human_task_id": subject_id},
            )
        if str(human_task["workflow_run_id"]) != workflow_run_id:
            raise CommandError(
                code="cross_workflow_link_reference",
                message="human task belongs to a different workflow_run",
                details={
                    "workflow_run_id": workflow_run_id,
                    "human_task_id": subject_id,
                    "subject_workflow_run_id": str(human_task["workflow_run_id"]),
                },
            )
        return

    if subject_kind == "execution_session":
        session = get_execution_session(connection, subject_id)
        if session is None:
            raise CommandError(
                code="execution_session_not_found",
                message="execution session not found for artifact link",
                details={"execution_session_id": subject_id},
            )
        if str(session["workflow_run_id"]) != workflow_run_id:
            raise CommandError(
                code="cross_workflow_link_reference",
                message="execution session belongs to a different workflow_run",
                details={
                    "workflow_run_id": workflow_run_id,
                    "execution_session_id": subject_id,
                    "subject_workflow_run_id": str(session["workflow_run_id"]),
                },
            )
        return

    if subject_kind == "tool_execution":
        tool_execution = get_tool_execution(connection, subject_id)
        if tool_execution is None:
            raise CommandError(
                code="tool_execution_not_found",
                message="tool execution not found for artifact link",
                details={"tool_execution_id": subject_id},
            )
        session = get_execution_session(
            connection,
            str(tool_execution["execution_session_id"]),
        )
        if session is None:
            raise CommandError(
                code="execution_session_not_found",
                message="execution session was not found while validating tool execution link",
                details={
                    "tool_execution_id": subject_id,
                    "execution_session_id": str(tool_execution["execution_session_id"]),
                },
            )
        if str(session["workflow_run_id"]) != workflow_run_id:
            raise CommandError(
                code="cross_workflow_link_reference",
                message="tool execution belongs to a different workflow_run",
                details={
                    "workflow_run_id": workflow_run_id,
                    "tool_execution_id": subject_id,
                    "subject_workflow_run_id": str(session["workflow_run_id"]),
                },
            )
        return

    if subject_kind == "policy_decision":
        policy_decision = get_policy_decision(connection, subject_id)
        if policy_decision is None:
            raise CommandError(
                code="policy_decision_not_found",
                message="policy decision not found for artifact link",
                details={"policy_decision_id": subject_id},
            )
        linked_tool_execution_id = policy_decision.get("tool_execution_id")
        if linked_tool_execution_id is None:
            raise CommandError(
                code="policy_decision_scope_unresolved",
                message="policy decision is not linked to a tool execution",
                details={"policy_decision_id": subject_id},
            )
        tool_execution = get_tool_execution(connection, str(linked_tool_execution_id))
        if tool_execution is None:
            raise CommandError(
                code="tool_execution_not_found",
                message="policy decision tool execution was not found for artifact link",
                details={
                    "policy_decision_id": subject_id,
                    "tool_execution_id": str(linked_tool_execution_id),
                },
            )
        session = get_execution_session(
            connection,
            str(tool_execution["execution_session_id"]),
        )
        if session is None:
            raise CommandError(
                code="execution_session_not_found",
                message="execution session was not found while validating policy decision link",
                details={
                    "policy_decision_id": subject_id,
                    "execution_session_id": str(tool_execution["execution_session_id"]),
                },
            )
        if str(session["workflow_run_id"]) != workflow_run_id:
            raise CommandError(
                code="cross_workflow_link_reference",
                message="policy decision belongs to a different workflow_run",
                details={
                    "workflow_run_id": workflow_run_id,
                    "policy_decision_id": subject_id,
                    "subject_workflow_run_id": str(session["workflow_run_id"]),
                },
            )
        return

    if subject_kind == "approval":
        approval = get_approval(connection, subject_id)
        if approval is None:
            raise CommandError(
                code="approval_not_found",
                message="approval not found for artifact link",
                details={"approval_id": subject_id},
            )
        if str(approval["workflow_run_id"]) != workflow_run_id:
            raise CommandError(
                code="cross_workflow_link_reference",
                message="approval belongs to a different workflow_run",
                details={
                    "workflow_run_id": workflow_run_id,
                    "approval_id": subject_id,
                    "subject_workflow_run_id": str(approval["workflow_run_id"]),
                },
            )
        return

    if subject_kind == "flag":
        flag = get_flag(connection, subject_id)
        if flag is None:
            raise CommandError(
                code="flag_not_found",
                message="flag not found for artifact link",
                details={"flag_id": subject_id},
            )
        if str(flag["workflow_run_id"]) != workflow_run_id:
            raise CommandError(
                code="cross_workflow_link_reference",
                message="flag belongs to a different workflow_run",
                details={
                    "workflow_run_id": workflow_run_id,
                    "flag_id": subject_id,
                    "subject_workflow_run_id": str(flag["workflow_run_id"]),
                },
            )
        return

    if subject_kind == "artifact_version":
        artifact = get_artifact_version(connection, subject_id)
        if artifact is None:
            raise CommandError(
                code="artifact_version_not_found",
                message="artifact version not found for artifact link",
                details={"artifact_version_id": subject_id},
            )
        if str(artifact["workflow_run_id"]) != workflow_run_id:
            raise CommandError(
                code="cross_workflow_link_reference",
                message="artifact version belongs to a different workflow_run",
                details={
                    "workflow_run_id": workflow_run_id,
                    "artifact_version_id": subject_id,
                    "subject_workflow_run_id": str(artifact["workflow_run_id"]),
                },
            )
        return

    raise CommandError(
        code="invalid_artifact_link_subject_kind",
        message=f"unsupported artifact link subject_kind: {subject_kind}",
        details={
            "allowed_subject_kinds": [
                "workflow_run",
                "task_run",
                "human_task",
                "execution_session",
                "tool_execution",
                "policy_decision",
                "approval",
                "flag",
                "artifact_version",
            ]
        },
    )


def _canonical_artifact_scope_fields(
    *,
    tenant_id: str,
    domain_id: str,
    workflow_partition_key: str,
    artifact_kind: str,
) -> dict[str, str | None]:
    dataset_key = str(artifact_kind).strip().lower()
    partition_kind: str | None = None
    partition_value: str | None = None

    try:
        partition_index = load_dataset_partition_index()
    except Exception:
        partition_index = {}
    partition_hint = partition_index.get(dataset_key)
    if partition_hint is not None:
        try:
            partition_ref = PartitionRef(
                key=str(partition_hint),
                value=workflow_partition_key,
            )
            partition_kind = partition_ref.key
            partition_value = partition_ref.value
        except PointerAddressError:
            partition_kind = str(partition_hint)
            partition_value = str(workflow_partition_key)

    return {
        "tenant_id": str(tenant_id),
        "domain_id": str(domain_id),
        "dataset_key": dataset_key,
        "partition_kind": partition_kind,
        "partition_key": partition_value,
    }


def _write_artifact_provenance_compatibility_edges(
    connection: sqlite3.Connection,
    *,
    workflow_run_id: str,
    artifact_version_id: str,
    parent_artifact_version_id: str | None,
    supersedes_artifact_version_id: str | None,
    created_at: str,
) -> None:
    if (
        parent_artifact_version_id is not None
        and parent_artifact_version_id != artifact_version_id
    ):
        create_artifact_provenance_edge(
            connection,
            output_artifact_version_id=artifact_version_id,
            input_artifact_version_id=parent_artifact_version_id,
            edge_type="derives_from",
            workflow_run_id=workflow_run_id,
            edge_order=1,
            created_at=created_at,
            metadata_json={"compatibility_source": "parent_artifact_version_id"},
        )
    if (
        supersedes_artifact_version_id is not None
        and supersedes_artifact_version_id != artifact_version_id
    ):
        create_artifact_provenance_edge(
            connection,
            output_artifact_version_id=artifact_version_id,
            input_artifact_version_id=supersedes_artifact_version_id,
            edge_type="supersedes",
            workflow_run_id=workflow_run_id,
            edge_order=1,
            created_at=created_at,
            metadata_json={"compatibility_source": "supersedes_artifact_version_id"},
        )


def _capture_artifact_lineage_input_bindings(
    connection: sqlite3.Connection,
    *,
    workflow_run_id: str,
    task_run_id: str | None,
    artifact_version_id: str,
    parent_artifact_version_id: str | None,
    supersedes_artifact_version_id: str | None,
    captured_at: str,
    event_idempotency: str | None,
) -> None:
    if parent_artifact_version_id is not None:
        _capture_artifact_input_binding(
            connection,
            workflow_run_id=workflow_run_id,
            task_run_id=task_run_id,
            binding_key=_input_binding_key(
                prefix="artifact.version.parent",
                event_idempotency=event_idempotency,
                discriminator=f"{artifact_version_id}:{parent_artifact_version_id}",
            ),
            source_ref=parent_artifact_version_id,
            artifact_version_id=parent_artifact_version_id,
            captured_at=captured_at,
            metadata_json={
                "capture_reason": "artifact_version_create_parent",
                "output_artifact_version_id": artifact_version_id,
            },
        )
    if supersedes_artifact_version_id is not None:
        _capture_artifact_input_binding(
            connection,
            workflow_run_id=workflow_run_id,
            task_run_id=task_run_id,
            binding_key=_input_binding_key(
                prefix="artifact.version.supersedes",
                event_idempotency=event_idempotency,
                discriminator=f"{artifact_version_id}:{supersedes_artifact_version_id}",
            ),
            source_ref=supersedes_artifact_version_id,
            artifact_version_id=supersedes_artifact_version_id,
            captured_at=captured_at,
            metadata_json={
                "capture_reason": "artifact_version_create_supersedes",
                "output_artifact_version_id": artifact_version_id,
            },
        )


def _capture_artifact_input_binding(
    connection: sqlite3.Connection,
    *,
    workflow_run_id: str,
    task_run_id: str | None,
    binding_key: str,
    source_ref: str,
    artifact_version_id: str,
    captured_at: str,
    metadata_json: dict[str, Any],
) -> None:
    _capture_input_binding(
        connection,
        workflow_run_id=workflow_run_id,
        task_run_id=task_run_id,
        binding_key=binding_key,
        source_kind="artifact_version",
        source_ref=source_ref,
        artifact_version_id=artifact_version_id,
        pointer_key=None,
        pointer_generation=None,
        pointer_artifact_version_id=None,
        captured_at=captured_at,
        metadata_json=metadata_json,
    )


def _capture_input_binding(
    connection: sqlite3.Connection,
    *,
    workflow_run_id: str,
    task_run_id: str | None,
    binding_key: str,
    source_kind: str,
    source_ref: str,
    artifact_version_id: str | None,
    pointer_key: str | None,
    pointer_generation: int | None,
    pointer_artifact_version_id: str | None,
    captured_at: str,
    metadata_json: dict[str, Any],
) -> None:
    if task_run_id is not None:
        create_task_input_binding(
            connection,
            task_run_id=task_run_id,
            workflow_run_id=workflow_run_id,
            binding_key=binding_key,
            source_kind=source_kind,
            source_ref=source_ref,
            artifact_version_id=artifact_version_id,
            pointer_key=pointer_key,
            pointer_generation=pointer_generation,
            pointer_artifact_version_id=pointer_artifact_version_id,
            captured_at=captured_at,
            metadata_json=metadata_json,
        )
        return

    create_workflow_run_input(
        connection,
        workflow_run_id=workflow_run_id,
        binding_key=binding_key,
        source_kind=source_kind,
        source_ref=source_ref,
        artifact_version_id=artifact_version_id,
        pointer_key=pointer_key,
        pointer_generation=pointer_generation,
        pointer_artifact_version_id=pointer_artifact_version_id,
        captured_by_task_run_id=None,
        captured_at=captured_at,
        metadata_json=metadata_json,
    )


def _input_binding_key(
    *,
    prefix: str,
    event_idempotency: str | None,
    discriminator: str,
) -> str:
    digest = hashlib.sha256(
        f"{event_idempotency}|{discriminator}".encode("utf-8")
    ).hexdigest()[:20]
    return f"{prefix}:{digest}"
