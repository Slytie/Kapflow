from __future__ import annotations

import base64
from pathlib import Path
import sqlite3

import pytest

import onetruth.application.handlers._shared.artifact_effects as artifact_effects
import onetruth.application.handlers._shared.command_boundary as command_boundary
import onetruth.application.handlers.artifacts as new_artifacts
import onetruth.application.handlers.pointers as new_pointers
import onetruth.application.handlers.workflow_task_lifecycle as legacy_handlers
from onetruth.infrastructure.events.event_store import create_sqlite_substrate, list_events


def _connection() -> sqlite3.Connection:
    connection = sqlite3.connect(":memory:")
    connection.row_factory = sqlite3.Row
    create_sqlite_substrate(connection)
    return connection


def _freeze_handler_time(monkeypatch: pytest.MonkeyPatch) -> None:
    fixed_now = "2026-03-17T13:00:00Z"
    monkeypatch.setattr(command_boundary, "utc_now_iso", lambda: fixed_now)
    monkeypatch.setattr(artifact_effects, "utc_now_iso", lambda: fixed_now)
    monkeypatch.setattr(legacy_handlers, "utc_now_iso", lambda: fixed_now)
    monkeypatch.setattr(new_pointers, "utc_now_iso", lambda: fixed_now)


def _workflow_payload(workflow_run_id: str, activation_key: str) -> dict[str, str]:
    return {
        "workflow_run_id": workflow_run_id,
        "workflow_id": "schedule_planning.v1",
        "workflow_version": "v1",
        "tenant_id": "tenant-a",
        "domain_id": "domain-x",
        "partition_key": "SD-2026-03-17",
        "logical_date": "2026-03-17",
        "activation_key": activation_key,
    }


def _artifact_payload(
    workflow_run_id: str,
    *,
    artifact_version_id: str,
    artifact_kind: str,
    idempotency_key: str,
) -> dict[str, object]:
    return {
        "artifact_version_id": artifact_version_id,
        "workflow_run_id": workflow_run_id,
        "artifact_kind": artifact_kind,
        "artifact_role": "official_output",
        "media_type": "application/json",
        "storage_uri": f"s3://runtime/{artifact_version_id}.json",
        "content_digest": f"sha256:{artifact_version_id}",
        "byte_size": 64,
        "metadata_json": {"artifact_version_id": artifact_version_id},
        "idempotency_key": idempotency_key,
    }


def _ingest_payload(workflow_run_id: str, *, idempotency_key: str) -> dict[str, object]:
    return {
        "artifact_version_id": "av-compat-ingest",
        "workflow_run_id": workflow_run_id,
        "artifact_kind": "schedule.supervisor_review.doc",
        "artifact_role": "evidence",
        "content_base64": base64.b64encode(b"artifact-compat-bytes").decode("ascii"),
        "file_name": "review.docx",
        "metadata_json": {"seed_source_path": "/tmp/seed/review.docx"},
        "idempotency_key": idempotency_key,
    }


def _pointer_payload(
    workflow_run_id: str,
    artifact_version_id: str,
    *,
    idempotency_key: str,
) -> dict[str, object]:
    return {
        "workflow_run_id": workflow_run_id,
        "scope_kind": "stage",
        "scope_ref": "Stage06",
        "pointer_key": "official:schedule.published_schedule.workbook",
        "artifact_kind": "schedule.published_schedule.workbook",
        "artifact_version_id": artifact_version_id,
        "promotion_reason": "manual_promote",
        "idempotency_key": idempotency_key,
        "actor_id": "system:runtime",
        "actor_type": "system",
    }


def _artifact_summary(row: dict[str, object]) -> dict[str, object]:
    return {
        "artifact_version_id": row["artifact_version_id"],
        "workflow_run_id": row["workflow_run_id"],
        "task_run_id": row["task_run_id"],
        "artifact_kind": row["artifact_kind"],
        "artifact_role": row["artifact_role"],
        "media_type": row["media_type"],
        "content_digest": row["content_digest"],
        "byte_size": row["byte_size"],
        "tenant_id": row["tenant_id"],
        "domain_id": row["domain_id"],
        "dataset_key": row["dataset_key"],
        "partition_kind": row["partition_kind"],
        "partition_key": row["partition_key"],
        "parent_artifact_version_id": row["parent_artifact_version_id"],
        "supersedes_artifact_version_id": row["supersedes_artifact_version_id"],
        "metadata_json": row["metadata_json"],
        "links": row["links"],
    }


def _ingress_summary(result: dict[str, object]) -> dict[str, object]:
    ingress = result["ingress"]
    artifact = result["artifact_version"]
    return {
        "artifact": _artifact_summary(artifact),
        "ingress": {
            "file_name": ingress["file_name"],
            "media_type": ingress["media_type"],
            "byte_size": ingress["byte_size"],
            "content_digest": ingress["content_digest"],
        },
    }


def _pointer_summary(row: dict[str, object]) -> dict[str, object]:
    return {
        "workflow_run_id": row["workflow_run_id"],
        "pointer_key": row["pointer_key"],
        "pointer_id": row["pointer_id"],
        "scope_kind": row["scope_kind"],
        "scope_ref": row["scope_ref"],
        "artifact_kind": row["artifact_kind"],
        "artifact_version_id": row["artifact_version_id"],
        "generation": row["generation"],
        "tenant_id": row["tenant_id"],
        "domain_id": row["domain_id"],
        "dataset_key": row["dataset_key"],
        "partition_kind": row["partition_kind"],
        "partition_key": row["partition_key"],
        "stream_key": row["stream_key"],
        "registry_kind": row["registry_kind"],
        "promotion_reason": row["promotion_reason"],
    }


def _event_payloads(connection: sqlite3.Connection, workflow_run_id: str) -> list[tuple[str, dict[str, object]]]:
    relevant_types = {
        "artifact.version.created",
        "artifact.pointer.promoted",
        "artifact.pointer.drift_detected",
    }
    payloads: list[tuple[str, dict[str, object]]] = []
    for event in list_events(connection, run_id=workflow_run_id):
        event_type = str(event["event_type"])
        if event_type not in relevant_types:
            continue
        payloads.append((event_type, dict(event["payload"])))
    return payloads


def test_artifact_and_pointer_handlers_keep_legacy_and_new_surfaces_in_sync(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _freeze_handler_time(monkeypatch)
    legacy_connection = _connection()
    new_connection = _connection()
    workflow_run_id = "wr-artifact-pointer-compat"

    legacy_handlers.create_workflow_run_command(
        legacy_connection,
        _workflow_payload(workflow_run_id, "artifact-pointer-legacy"),
    )
    legacy_handlers.create_workflow_run_command(
        new_connection,
        _workflow_payload(workflow_run_id, "artifact-pointer-new"),
    )

    legacy_created = legacy_handlers.create_artifact_version_command(
        legacy_connection,
        _artifact_payload(
            workflow_run_id,
            artifact_version_id="av-compat-official",
            artifact_kind="schedule.published_schedule.workbook",
            idempotency_key="idem:legacy:artifacts.create",
        ),
    )
    new_created = new_artifacts.create_artifact_version_command(
        new_connection,
        _artifact_payload(
            workflow_run_id,
            artifact_version_id="av-compat-official",
            artifact_kind="schedule.published_schedule.workbook",
            idempotency_key="idem:new:artifacts.create",
        ),
    )
    assert _artifact_summary(legacy_created) == _artifact_summary(new_created)

    legacy_ingested = legacy_handlers.ingest_artifact_document_command(
        legacy_connection,
        _ingest_payload(workflow_run_id, idempotency_key="idem:legacy:artifacts.ingest"),
        storage_root=tmp_path / "legacy",
    )
    new_ingested = new_artifacts.ingest_artifact_document_command(
        new_connection,
        _ingest_payload(workflow_run_id, idempotency_key="idem:new:artifacts.ingest"),
        storage_root=tmp_path / "new",
    )
    assert _ingress_summary(legacy_ingested) == _ingress_summary(new_ingested)

    legacy_downloaded = legacy_handlers.download_artifact_blob_command(
        legacy_connection,
        "av-compat-ingest",
    )
    new_downloaded = new_artifacts.download_artifact_blob_command(
        new_connection,
        "av-compat-ingest",
    )
    assert legacy_downloaded["content_bytes"] == new_downloaded["content_bytes"]
    assert _artifact_summary(legacy_downloaded["artifact_version"]) == _artifact_summary(
        new_downloaded["artifact_version"]
    )

    legacy_pointer = legacy_handlers.promote_pointer_command(
        legacy_connection,
        _pointer_payload(
            workflow_run_id,
            "av-compat-official",
            idempotency_key="idem:legacy:pointers.promote",
        ),
    )
    new_pointer = new_pointers.promote_pointer_command(
        new_connection,
        _pointer_payload(
            workflow_run_id,
            "av-compat-official",
            idempotency_key="idem:new:pointers.promote",
        ),
    )
    assert _pointer_summary(legacy_pointer) == _pointer_summary(new_pointer)
    assert _event_payloads(legacy_connection, workflow_run_id) == _event_payloads(
        new_connection,
        workflow_run_id,
    )
