from __future__ import annotations

import hashlib
import json
import sqlite3
from typing import Any

from onetruth.infrastructure.events.event_store import (
    DuplicateIdempotencyKeyError,
    append_event,
    event_id_for_type,
    utc_now_iso,
)

COHERENCE_POLICY_WARN_VISIBLE = "warn_visible"
COHERENCE_POLICY_DEGRADE_VISIBLE = "degrade_visible"
COHERENCE_POLICY_ALLOW = "allow"
COHERENCE_POLICY_BLOCK = "block"
COHERENCE_STATUS_PASSED = "passed"
COHERENCE_STATUS_FAILED = "failed"


def evaluate_official_outputs_coherence(
    *,
    projection_id: str,
    projection_kind: str,
    outputs: list[dict[str, Any]],
    policy_on_drift: str,
) -> dict[str, Any]:
    issues: list[dict[str, Any]] = []
    source_refs: list[dict[str, str]] = []

    for row_index, row in enumerate(outputs):
        if not isinstance(row, dict):
            issues.append(
                {
                    "code": "official_output_row_invalid",
                    "message": "official outputs projection row must be an object",
                    "refs": {"row_index": str(row_index)},
                }
            )
            continue
        pointer = row.get("pointer")
        linked_artifact = row.get("artifact_version")
        if not isinstance(pointer, dict):
            issues.append(
                {
                    "code": "official_output_pointer_missing",
                    "message": "official output row is missing canonical pointer lineage",
                    "refs": {"row_index": str(row_index)},
                }
            )
            continue

        pointer_id = _optional_string(pointer.get("pointer_id"))
        pointer_artifact_version_id = _optional_string(pointer.get("artifact_version_id"))
        pointer_artifact_kind = _optional_string(pointer.get("artifact_kind"))
        pointer_dataset_key = _optional_string(pointer.get("dataset_key"))
        pointer_partition_kind = _optional_string(pointer.get("partition_kind"))
        pointer_partition_key = _optional_string(pointer.get("partition_key"))

        if pointer_id is not None:
            source_refs.append({"type": "pointer", "id": pointer_id})
        if pointer_artifact_version_id is not None:
            source_refs.append({"type": "artifact_version", "id": pointer_artifact_version_id})

        missing_pointer_fields = _missing_required_fields(
            {
                "pointer_id": pointer_id,
                "artifact_version_id": pointer_artifact_version_id,
                "artifact_kind": pointer_artifact_kind,
                "dataset_key": pointer_dataset_key,
                "partition_kind": pointer_partition_kind,
                "partition_key": pointer_partition_key,
            }
        )
        if missing_pointer_fields:
            issues.append(
                {
                    "code": "official_output_pointer_lineage_missing",
                    "message": "official output pointer is missing required canonical lineage fields",
                    "refs": {
                        "row_index": str(row_index),
                        "pointer_id": pointer_id,
                        "missing_fields": ",".join(missing_pointer_fields),
                    },
                }
            )

        if not isinstance(linked_artifact, dict):
            issues.append(
                {
                    "code": "official_output_artifact_missing",
                    "message": "official output pointer target artifact was not found in canonical scope",
                    "refs": {
                        "pointer_id": pointer_id,
                        "artifact_version_id": pointer_artifact_version_id,
                    },
                }
            )
            continue

        linked_artifact_version_id = _optional_string(linked_artifact.get("artifact_version_id"))
        linked_artifact_kind = _optional_string(linked_artifact.get("artifact_kind"))
        linked_dataset_key = _optional_string(linked_artifact.get("dataset_key"))
        linked_partition_kind = _optional_string(linked_artifact.get("partition_kind"))
        linked_partition_key = _optional_string(linked_artifact.get("partition_key"))

        missing_artifact_fields = _missing_required_fields(
            {
                "artifact_version_id": linked_artifact_version_id,
                "artifact_kind": linked_artifact_kind,
                "dataset_key": linked_dataset_key,
                "partition_kind": linked_partition_kind,
                "partition_key": linked_partition_key,
            }
        )
        if missing_artifact_fields:
            issues.append(
                {
                    "code": "official_output_artifact_lineage_missing",
                    "message": "official output artifact is missing required canonical lineage fields",
                    "refs": {
                        "row_index": str(row_index),
                        "pointer_id": pointer_id,
                        "artifact_version_id": linked_artifact_version_id,
                        "missing_fields": ",".join(missing_artifact_fields),
                    },
                }
            )

        if linked_artifact_version_id is not None:
            source_refs.append({"type": "artifact_version", "id": linked_artifact_version_id})

        if (
            pointer_artifact_version_id is not None
            and linked_artifact_version_id is not None
            and pointer_artifact_version_id != linked_artifact_version_id
        ):
            issues.append(
                {
                    "code": "official_output_artifact_version_mismatch",
                    "message": "official output view resolved a different artifact_version_id than pointer target",
                    "refs": {
                        "pointer_id": pointer_id,
                        "pointer_artifact_version_id": pointer_artifact_version_id,
                        "linked_artifact_version_id": linked_artifact_version_id,
                    },
                }
            )

        if (
            pointer_artifact_kind is not None
            and linked_artifact_kind is not None
            and pointer_artifact_kind != linked_artifact_kind
        ):
            issues.append(
                {
                    "code": "official_output_kind_mismatch",
                    "message": "official output pointer artifact_kind does not match linked artifact kind",
                    "refs": {
                        "pointer_id": pointer_id,
                        "pointer_artifact_kind": pointer_artifact_kind,
                        "linked_artifact_kind": linked_artifact_kind,
                    },
                }
            )

        if (
            pointer_dataset_key is not None
            and linked_dataset_key is not None
            and pointer_dataset_key != linked_dataset_key
        ):
            issues.append(
                {
                    "code": "official_output_dataset_mismatch",
                    "message": "official output pointer dataset_key does not match linked artifact dataset_key",
                    "refs": {
                        "pointer_id": pointer_id,
                        "pointer_dataset_key": pointer_dataset_key,
                        "linked_dataset_key": linked_dataset_key,
                    },
                }
            )

        if (
            pointer_partition_kind is not None
            and linked_partition_kind is not None
            and pointer_partition_kind != linked_partition_kind
        ):
            issues.append(
                {
                    "code": "official_output_partition_mismatch",
                    "message": "official output pointer partition_kind does not match linked artifact partition_kind",
                    "refs": {
                        "pointer_id": pointer_id,
                        "pointer_partition_kind": pointer_partition_kind,
                        "linked_partition_kind": linked_partition_kind,
                    },
                }
            )

        if (
            pointer_partition_key is not None
            and linked_partition_key is not None
            and pointer_partition_key != linked_partition_key
        ):
            issues.append(
                {
                    "code": "official_output_partition_mismatch",
                    "message": "official output pointer partition_key does not match linked artifact partition_key",
                    "refs": {
                        "pointer_id": pointer_id,
                        "pointer_partition_key": pointer_partition_key,
                        "linked_partition_key": linked_partition_key,
                    },
                }
            )

    return _coherence_result(
        projection_id=projection_id,
        projection_kind=projection_kind,
        policy_on_drift=policy_on_drift,
        issues=issues,
        source_refs=_dedupe_source_refs(source_refs),
    )


def evaluate_handoff_operator_view_coherence(
    connection: sqlite3.Connection,
    *,
    projection_id: str,
    edge_execution: dict[str, Any],
    policy_on_drift: str,
) -> dict[str, Any]:
    issues: list[dict[str, Any]] = []
    source_refs: list[dict[str, str]] = []
    edge_execution_id = _optional_string(edge_execution.get("edge_execution_id"))
    if edge_execution_id is not None:
        source_refs.append({"type": "edge_execution", "id": edge_execution_id})

    source_workflow_run_id = _optional_string(edge_execution.get("source_workflow_run_id"))
    if source_workflow_run_id is not None:
        source_refs.append({"type": "workflow_run", "id": source_workflow_run_id})
    source_workflow_run = _workflow_run(connection, source_workflow_run_id)
    if source_workflow_run is None:
        issues.append(
            {
                "code": "handoff_source_workflow_run_missing",
                "message": "handoff source workflow run is missing",
                "refs": {"edge_execution_id": edge_execution_id, "workflow_run_id": source_workflow_run_id},
            }
        )

    source_artifact_version_id = _optional_string(edge_execution.get("source_artifact_version_id"))
    if source_artifact_version_id is not None:
        source_refs.append({"type": "artifact_version", "id": source_artifact_version_id})
    source_artifact = _artifact(connection, source_artifact_version_id)
    if source_artifact is None:
        issues.append(
            {
                "code": "handoff_source_artifact_missing",
                "message": "handoff source artifact is missing",
                "refs": {
                    "edge_execution_id": edge_execution_id,
                    "artifact_version_id": source_artifact_version_id,
                },
            }
        )
    elif source_workflow_run_id is not None and str(source_artifact.get("workflow_run_id")) != source_workflow_run_id:
        issues.append(
            {
                "code": "handoff_source_artifact_run_mismatch",
                "message": "handoff source artifact belongs to a different workflow run",
                "refs": {
                    "edge_execution_id": edge_execution_id,
                    "source_workflow_run_id": source_workflow_run_id,
                    "artifact_workflow_run_id": _optional_string(source_artifact.get("workflow_run_id")),
                },
            }
        )

    seed_artifact_version_id = _optional_string(edge_execution.get("seed_artifact_version_id"))
    if seed_artifact_version_id is not None:
        source_refs.append({"type": "artifact_version", "id": seed_artifact_version_id})
        if _artifact(connection, seed_artifact_version_id) is None:
            issues.append(
                {
                    "code": "handoff_seed_artifact_missing",
                    "message": "handoff seed artifact is missing",
                    "refs": {
                        "edge_execution_id": edge_execution_id,
                        "seed_artifact_version_id": seed_artifact_version_id,
                    },
                }
            )

    status = _optional_string(edge_execution.get("status")) or ""
    target_workflow_run_id = _optional_string(edge_execution.get("target_workflow_run_id"))
    target_partition_key = _optional_string(edge_execution.get("target_partition_key"))
    target_workflow_id = _optional_string(edge_execution.get("target_workflow_id"))

    if status == "activated":
        if target_workflow_run_id is None:
            issues.append(
                {
                    "code": "handoff_target_run_missing",
                    "message": "activated handoff is missing target_workflow_run_id",
                    "refs": {"edge_execution_id": edge_execution_id},
                }
            )
            target_workflow_run = None
        else:
            source_refs.append({"type": "workflow_run", "id": target_workflow_run_id})
            target_workflow_run = _workflow_run(connection, target_workflow_run_id)
            if target_workflow_run is None:
                issues.append(
                    {
                        "code": "handoff_target_run_missing",
                        "message": "activated handoff target workflow run is missing",
                        "refs": {
                            "edge_execution_id": edge_execution_id,
                            "target_workflow_run_id": target_workflow_run_id,
                        },
                    }
                )

        if target_workflow_run is not None:
            actual_workflow_id = _optional_string(target_workflow_run.get("workflow_id"))
            actual_partition_key = _optional_string(target_workflow_run.get("partition_key"))
            if (
                target_workflow_id is not None
                and actual_workflow_id is not None
                and target_workflow_id != actual_workflow_id
            ):
                issues.append(
                    {
                        "code": "handoff_target_workflow_mismatch",
                        "message": "target workflow run workflow_id does not match edge target_workflow_id",
                        "refs": {
                            "edge_execution_id": edge_execution_id,
                            "edge_target_workflow_id": target_workflow_id,
                            "run_workflow_id": actual_workflow_id,
                        },
                    }
                )
            if (
                target_partition_key is not None
                and actual_partition_key is not None
                and target_partition_key != actual_partition_key
            ):
                issues.append(
                    {
                        "code": "handoff_target_partition_mismatch",
                        "message": "target workflow run partition_key does not match edge target partition",
                        "refs": {
                            "edge_execution_id": edge_execution_id,
                            "edge_target_partition_key": target_partition_key,
                            "run_partition_key": actual_partition_key,
                        },
                    }
                )

        trigger_ref = _optional_string(edge_execution.get("trigger_ref"))
        if trigger_ref is None:
            issues.append(
                {
                    "code": "handoff_trigger_ref_missing",
                    "message": "activated handoff is missing trigger_ref",
                    "refs": {"edge_execution_id": edge_execution_id},
                }
            )
        else:
            source_refs.append({"type": "artifact_version", "id": trigger_ref})
            if _artifact(connection, trigger_ref) is None:
                issues.append(
                    {
                        "code": "handoff_trigger_ref_artifact_missing",
                        "message": "trigger_ref points to a missing artifact version",
                        "refs": {
                            "edge_execution_id": edge_execution_id,
                            "trigger_ref": trigger_ref,
                        },
                    }
                )

    return _coherence_result(
        projection_id=projection_id,
        projection_kind="handoff_operator_view",
        policy_on_drift=policy_on_drift,
        issues=issues,
        source_refs=source_refs,
    )


def maybe_emit_projection_coherence_failed(
    connection: sqlite3.Connection,
    *,
    tenant_id: str,
    domain_id: str,
    workflow_run_id: str | None,
    coherence: dict[str, Any],
) -> None:
    if coherence.get("coherence_status") != COHERENCE_STATUS_FAILED:
        return

    projection_id = _optional_string(coherence.get("projection_id"))
    projection_kind = _optional_string(coherence.get("projection_kind"))
    failure_code = _optional_string(coherence.get("failure_code"))
    if projection_id is None or projection_kind is None or failure_code is None:
        return

    digest_source = {
        "projection_id": projection_id,
        "projection_kind": projection_kind,
        "failure_code": failure_code,
        "fingerprint": _optional_string(coherence.get("fingerprint")) or "",
    }
    digest = hashlib.sha256(
        json.dumps(digest_source, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()[:32]
    idempotency_key = f"projection.coherence_failed:{digest}"
    links: list[dict[str, str]] = [
        {"rel": "subject", "type": "projection", "id": projection_id},
    ]
    if workflow_run_id is not None and str(workflow_run_id).strip():
        links.append({"rel": "subject", "type": "workflow_run", "id": str(workflow_run_id)})

    occurred_at = utc_now_iso()
    try:
        append_event(
            connection,
            {
                "event_id": event_id_for_type("projection.coherence_failed"),
                "event_type": "projection.coherence_failed",
                "schema_version": "1.0",
                "occurred_at": occurred_at,
                "recorded_at": occurred_at,
                "tenant_id": tenant_id,
                "domain_id": domain_id,
                "actor": {"type": "service", "id": "service:projection-coherence-harness"},
                "links": links,
                "payload": {
                    "projection_id": projection_id,
                    "projection_kind": projection_kind,
                    "failure_code": failure_code,
                },
                "idempotency_key": idempotency_key,
            },
        )
    except DuplicateIdempotencyKeyError:
        return
    connection.commit()


def _coherence_result(
    *,
    projection_id: str,
    projection_kind: str,
    policy_on_drift: str,
    issues: list[dict[str, Any]],
    source_refs: list[dict[str, str]],
) -> dict[str, Any]:
    normalized_issues = [_normalize_issue(issue) for issue in issues]
    fingerprint = hashlib.sha256(
        json.dumps(normalized_issues, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()[:24]
    if normalized_issues:
        return {
            "projection_id": projection_id,
            "projection_kind": projection_kind,
            "coherence_status": COHERENCE_STATUS_FAILED,
            "policy": {"on_drift": policy_on_drift, "emit_event": "projection.coherence_failed"},
            "failure_code": str(normalized_issues[0]["code"]),
            "issues": normalized_issues,
            "source_refs": source_refs,
            "fingerprint": fingerprint,
        }
    return {
        "projection_id": projection_id,
        "projection_kind": projection_kind,
        "coherence_status": COHERENCE_STATUS_PASSED,
        "policy": {"on_drift": policy_on_drift, "emit_event": "projection.coherence_failed"},
        "failure_code": None,
        "issues": [],
        "source_refs": source_refs,
        "fingerprint": fingerprint,
    }


def _normalize_issue(issue: dict[str, Any]) -> dict[str, Any]:
    refs = issue.get("refs")
    normalized_refs: dict[str, str] = {}
    if isinstance(refs, dict):
        for key, value in refs.items():
            if value is None:
                continue
            normalized_refs[str(key)] = str(value)
    return {
        "code": str(issue.get("code") or "projection_coherence_failed"),
        "message": str(issue.get("message") or "projection coherence failure"),
        "refs": normalized_refs,
    }


def _missing_required_fields(values: dict[str, str | None]) -> list[str]:
    return sorted(key for key, value in values.items() if value is None)


def _dedupe_source_refs(source_refs: list[dict[str, str]]) -> list[dict[str, str]]:
    deduped: list[dict[str, str]] = []
    seen: set[tuple[str, str]] = set()
    for source_ref in source_refs:
        ref_type = _optional_string(source_ref.get("type"))
        ref_id = _optional_string(source_ref.get("id"))
        if ref_type is None or ref_id is None:
            continue
        key = (ref_type, ref_id)
        if key in seen:
            continue
        seen.add(key)
        deduped.append({"type": ref_type, "id": ref_id})
    return deduped


def _optional_string(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    return text


def _workflow_run(connection: sqlite3.Connection, workflow_run_id: str | None) -> dict[str, Any] | None:
    if workflow_run_id is None:
        return None
    row = connection.execute(
        """
        SELECT workflow_run_id, workflow_id, tenant_id, domain_id, partition_key
        FROM workflow_runs
        WHERE workflow_run_id = ?
        """,
        (workflow_run_id,),
    ).fetchone()
    if row is None:
        return None
    return dict(row)


def _artifact(connection: sqlite3.Connection, artifact_version_id: str | None) -> dict[str, Any] | None:
    if artifact_version_id is None:
        return None
    row = connection.execute(
        """
        SELECT artifact_version_id, workflow_run_id, artifact_kind, dataset_key, partition_kind, partition_key
        FROM artifact_versions
        WHERE artifact_version_id = ?
        """,
        (artifact_version_id,),
    ).fetchone()
    if row is None:
        return None
    return dict(row)
