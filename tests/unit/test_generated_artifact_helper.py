from __future__ import annotations

import hashlib
from pathlib import Path
import sqlite3
from urllib.parse import urlparse

import pytest

from onetruth.application.handlers._shared.artifact_effects import (
    canonical_json_bytes,
    persist_generated_artifact_effects,
)
from onetruth.application.handlers._shared.command_boundary import CommandError
from onetruth.application.handlers.workflow_task_lifecycle import create_workflow_run_command
from onetruth.infrastructure.events.event_store import create_sqlite_substrate, list_events
from onetruth.infrastructure.repositories.artifact_provenance import (
    list_artifact_provenance_edges_for_output,
)
from onetruth.infrastructure.repositories.artifact_versions import get_artifact_version


def _connection() -> sqlite3.Connection:
    connection = sqlite3.connect(":memory:")
    connection.row_factory = sqlite3.Row
    create_sqlite_substrate(connection)
    return connection


def _create_run(connection: sqlite3.Connection, workflow_run_id: str = "wr-generated") -> None:
    create_workflow_run_command(
        connection,
        {
            "workflow_run_id": workflow_run_id,
            "workflow_id": "weekly_schedule_planning.v1",
            "workflow_version": "v1",
            "tenant_id": "tenant-a",
            "domain_id": "domain-x",
            "partition_key": "PW-2026-W10",
            "logical_date": "2026-03-02",
            "activation_key": f"generated-artifact:{workflow_run_id}",
        },
    )


def _artifact_event_count(connection: sqlite3.Connection, workflow_run_id: str) -> int:
    return len(
        [
            event
            for event in list_events(connection, run_id=workflow_run_id, limit=1000)
            if event["event_type"] == "artifact.version.created"
        ]
    )


def test_canonical_json_bytes_are_deterministic_ascii_and_compact() -> None:
    assert canonical_json_bytes({"b": 2, "a": ["Café"]}) == b'{"a":["Caf\\u00e9"],"b":2}'
    assert not canonical_json_bytes({"a": 1}).endswith(b"\n")


def test_canonical_json_bytes_rejects_non_standard_json_numbers() -> None:
    with pytest.raises(ValueError):
        canonical_json_bytes({"not_json": float("nan")})


def test_persist_generated_artifact_creates_blob_event_and_provenance(
    tmp_path: Path,
) -> None:
    connection = _connection()
    _create_run(connection)
    parent = persist_generated_artifact_effects(
        connection,
        storage_root=tmp_path / "artifact-root",
        workflow_run_id="wr-generated",
        artifact_version_id="av-generated-parent",
        artifact_kind="capex.invariant_audit.parent.json",
        artifact_role="evidence",
        media_type="application/json",
        file_name="parent.json",
        payload={"parent": True},
        metadata_json={"fixture": "generated-helper"},
        event_idempotency="generated-helper.parent.created",
    )["artifact_version"]
    payload = {"z": 2, "a": {"nested": True}}
    expected_bytes = canonical_json_bytes(payload)
    expected_digest = "sha256:" + hashlib.sha256(expected_bytes).hexdigest()

    result = persist_generated_artifact_effects(
        connection,
        storage_root=tmp_path / "artifact-root",
        workflow_run_id="wr-generated",
        artifact_version_id="av-generated-child",
        artifact_kind="capex.invariant_audit.report.json",
        artifact_role="evidence",
        media_type="application/json",
        file_name="audit.json",
        payload=payload,
        metadata_json={"source": "test"},
        parent_artifact_version_id=str(parent["artifact_version_id"]),
        lineage_note="generated from parent audit input",
        expected_content_digest=expected_digest,
        event_idempotency="generated-helper.child.created",
    )

    artifact = result["artifact_version"]
    blob_path = Path(urlparse(str(artifact["storage_uri"])).path).resolve()
    blob_path.relative_to((tmp_path / "artifact-root").resolve())
    assert blob_path.read_bytes() == expected_bytes
    assert artifact["content_digest"] == expected_digest
    assert artifact["byte_size"] == len(expected_bytes)
    assert result["generated"]["content_digest"] == expected_digest
    assert _artifact_event_count(connection, "wr-generated") == 2
    provenance = list_artifact_provenance_edges_for_output(connection, "av-generated-child")
    assert provenance[0]["input_artifact_version_id"] == "av-generated-parent"
    assert provenance[0]["edge_type"] == "derives_from"


def test_persist_generated_artifact_confines_storage_segments_under_root(
    tmp_path: Path,
) -> None:
    connection = _connection()
    unsafe_workflow_run_id = "../tenant-a/workflow:../../escape"
    _create_run(connection, workflow_run_id=unsafe_workflow_run_id)

    result = persist_generated_artifact_effects(
        connection,
        storage_root=tmp_path / "artifact-root",
        workflow_run_id=unsafe_workflow_run_id,
        artifact_version_id="av-generated-confined",
        artifact_kind="capex.invariant_audit.report.json",
        artifact_role="evidence",
        media_type="application/json",
        file_name="../../audit report?.json",
        payload={"ok": True},
    )

    blob_path = Path(urlparse(str(result["artifact_version"]["storage_uri"])).path).resolve()
    relative_blob_path = blob_path.relative_to((tmp_path / "artifact-root").resolve())
    assert ".." not in relative_blob_path.parts
    assert blob_path.name == "audit_report_.json"
    assert not (tmp_path / "escape").exists()


def test_persist_generated_artifact_rejects_expected_digest_mismatch(
    tmp_path: Path,
) -> None:
    connection = _connection()
    _create_run(connection)

    with pytest.raises(CommandError) as exc_info:
        persist_generated_artifact_effects(
            connection,
            storage_root=tmp_path / "artifact-root",
            workflow_run_id="wr-generated",
            artifact_version_id="av-digest-mismatch",
            artifact_kind="capex.invariant_audit.report.json",
            artifact_role="evidence",
            media_type="application/json",
            file_name="audit.json",
            payload={"ok": True},
            expected_content_digest="sha256:" + ("0" * 64),
        )

    assert exc_info.value.code == "generated_artifact_digest_mismatch"
    assert get_artifact_version(connection, "av-digest-mismatch") is None
    assert not (tmp_path / "artifact-root").exists()


def test_persist_generated_artifact_rejects_invalid_metadata_before_storage(
    tmp_path: Path,
) -> None:
    connection = _connection()
    _create_run(connection)

    with pytest.raises(CommandError) as exc_info:
        persist_generated_artifact_effects(
            connection,
            storage_root=tmp_path / "artifact-root",
            workflow_run_id="wr-generated",
            artifact_version_id="av-invalid-metadata",
            artifact_kind="capex.invariant_audit.report.json",
            artifact_role="evidence",
            media_type="application/json",
            file_name="audit.json",
            payload={"ok": True},
            metadata_json={"bad": float("nan")},
        )

    assert exc_info.value.code == "invalid_metadata_json"
    assert get_artifact_version(connection, "av-invalid-metadata") is None
    assert not (tmp_path / "artifact-root").exists()


def test_persist_generated_artifact_replays_matching_existing_row_without_event(
    tmp_path: Path,
) -> None:
    connection = _connection()
    _create_run(connection)
    kwargs = {
        "storage_root": tmp_path / "artifact-root",
        "workflow_run_id": "wr-generated",
        "artifact_version_id": "av-generated-replay",
        "artifact_kind": "capex.invariant_audit.report.json",
        "artifact_role": "evidence",
        "media_type": "application/json",
        "file_name": "audit.json",
        "payload": {"ok": True},
        "metadata_json": {"source": "replay"},
    }
    first = persist_generated_artifact_effects(connection, **kwargs)
    event_count = _artifact_event_count(connection, "wr-generated")

    second = persist_generated_artifact_effects(
        connection,
        **{**kwargs, "event_idempotency": "should-not-emit"},
    )

    assert second["replay"] is True
    assert second["artifact_version"]["artifact_version_id"] == "av-generated-replay"
    assert second["artifact_version"]["content_digest"] == first["artifact_version"]["content_digest"]
    assert _artifact_event_count(connection, "wr-generated") == event_count


def test_persist_generated_artifact_rejects_conflicting_existing_row(
    tmp_path: Path,
) -> None:
    connection = _connection()
    _create_run(connection)
    persist_generated_artifact_effects(
        connection,
        storage_root=tmp_path / "artifact-root",
        workflow_run_id="wr-generated",
        artifact_version_id="av-generated-conflict",
        artifact_kind="capex.invariant_audit.report.json",
        artifact_role="evidence",
        media_type="application/json",
        file_name="audit.json",
        payload={"ok": True},
    )

    with pytest.raises(CommandError) as exc_info:
        persist_generated_artifact_effects(
            connection,
            storage_root=tmp_path / "artifact-root",
            workflow_run_id="wr-generated",
            artifact_version_id="av-generated-conflict",
            artifact_kind="capex.invariant_audit.report.json",
            artifact_role="evidence",
            media_type="application/json",
            file_name="audit.json",
            payload={"ok": False},
        )

    assert exc_info.value.code == "generated_artifact_conflict"
    assert "content_digest" in exc_info.value.details["mismatches"]


def test_persist_generated_artifact_validates_canonical_partition_pair(
    tmp_path: Path,
) -> None:
    connection = _connection()
    _create_run(connection)

    with pytest.raises(CommandError) as exc_info:
        persist_generated_artifact_effects(
            connection,
            storage_root=tmp_path / "artifact-root",
            workflow_run_id="wr-generated",
            artifact_version_id="av-generated-half-partition",
            artifact_kind="capex.invariant_audit.report.json",
            artifact_role="evidence",
            media_type="application/json",
            file_name="audit.json",
            payload={"ok": True},
            canonical_partition_kind="capex_audit",
        )

    assert exc_info.value.code == "invalid_payload"
    assert get_artifact_version(connection, "av-generated-half-partition") is None

    created = persist_generated_artifact_effects(
        connection,
        storage_root=tmp_path / "artifact-root",
        workflow_run_id="wr-generated",
        artifact_version_id="av-generated-full-partition",
        artifact_kind="capex.invariant_audit.report.json",
        artifact_role="evidence",
        media_type="application/json",
        file_name="audit.json",
        payload={"ok": True},
        canonical_partition_kind="capex_audit",
        canonical_partition_key="platform-readiness",
    )["artifact_version"]

    assert created["partition_kind"] == "capex_audit"
    assert created["partition_key"] == "platform-readiness"
