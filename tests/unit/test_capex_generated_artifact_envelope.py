from __future__ import annotations

import hashlib
import json
from pathlib import Path
import sqlite3
from urllib.parse import urlparse

import pytest
from jsonschema import Draft202012Validator

from onetruth.application.handlers._shared.artifact_effects import (
    CAPEX_GENERATED_ARTIFACT_ENVELOPE_SCHEMA_VERSION,
    CAPEX_SOURCE_INVENTORY_PRE_OCCURRENCE_VALIDATION_RESULT,
    build_capex_generated_artifact_envelope,
    canonical_capex_generated_artifact_file_name,
    canonical_json_bytes,
    persist_capex_generated_artifact_effects,
    persist_generated_artifact_effects,
    validate_capex_generated_artifact_file_name,
)
from onetruth.application.handlers._shared.command_boundary import CommandError
from onetruth.application.handlers.workflow_task_lifecycle import create_workflow_run_command
from onetruth.infrastructure.events.event_store import create_sqlite_substrate, list_events


ROOT = Path(__file__).resolve().parents[2]
SCHEMA_PATH = ROOT / "schemas/runtime/capex_generated_artifact_envelope.schema.json"
SOURCE_REF = "source_occurrence:so-sanitized"
INPUT_DIGEST = "sha256:" + ("1" * 64)


def _connection() -> sqlite3.Connection:
    connection = sqlite3.connect(":memory:")
    connection.row_factory = sqlite3.Row
    create_sqlite_substrate(connection)
    return connection


def _create_run(connection: sqlite3.Connection, workflow_run_id: str = "wr-capex") -> None:
    create_workflow_run_command(
        connection,
        {
            "workflow_run_id": workflow_run_id,
            "workflow_id": "weekly_schedule_planning.v1",
            "workflow_version": "v1",
            "tenant_id": "tenant-a",
            "domain_id": "domain-x",
            "partition_key": "capex-project-alpha",
            "logical_date": "2026-06-17",
            "activation_key": f"capex-generated:{workflow_run_id}",
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


def test_capex_generated_artifact_envelope_schema_accepts_canonical_helper_payload() -> None:
    envelope = build_capex_generated_artifact_envelope(
        artifact_kind="capex.source_inventory.plan",
        artifact_role="evidence",
        source_refs=[SOURCE_REF],
        input_digests=[INPUT_DIGEST],
        validation_summary={"result": "planning_only", "policy": "shape_only"},
        payload={"descriptor_count": 2},
    )
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))

    Draft202012Validator(schema).validate(envelope)

    assert envelope["schema_version"] == CAPEX_GENERATED_ARTIFACT_ENVELOPE_SCHEMA_VERSION
    assert canonical_json_bytes(envelope) == canonical_json_bytes(
        {
            "payload": {"descriptor_count": 2},
            "validation_summary": {"policy": "shape_only", "result": "planning_only"},
            "input_digests": [INPUT_DIGEST],
            "source_refs": [SOURCE_REF],
            "artifact_role": "evidence",
            "artifact_kind": "capex.source_inventory.plan",
            "schema_version": CAPEX_GENERATED_ARTIFACT_ENVELOPE_SCHEMA_VERSION,
        }
    )


def test_capex_source_inventory_envelope_allows_pre_occurrence_empty_source_refs() -> None:
    envelope = build_capex_generated_artifact_envelope(
        artifact_kind="capex.source_inventory",
        artifact_role="evidence",
        source_refs=[],
        input_digests=[INPUT_DIGEST],
        validation_summary={
            "result": CAPEX_SOURCE_INVENTORY_PRE_OCCURRENCE_VALIDATION_RESULT,
            "policy": "content_identity_only_no_source_occurrence_binding",
        },
        payload={"schema_version": "capex.source_inventory.v1", "descriptor_count": 2},
    )
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))

    Draft202012Validator(schema).validate(envelope)

    assert envelope["source_refs"] == []
    assert canonical_capex_generated_artifact_file_name(
        "capex.source_inventory"
    ) == "capex.source_inventory.v1.json"


def test_capex_generated_artifact_persistence_uses_canonical_envelope_and_name(
    tmp_path: Path,
) -> None:
    connection = _connection()
    _create_run(connection)
    envelope = build_capex_generated_artifact_envelope(
        artifact_kind="capex.source_inventory.plan",
        artifact_role="evidence",
        source_refs=[SOURCE_REF],
        input_digests=[INPUT_DIGEST],
        validation_summary={"result": "planning_only"},
        payload={"descriptor_count": 2},
    )
    expected_digest = "sha256:" + hashlib.sha256(canonical_json_bytes(envelope)).hexdigest()

    result = persist_capex_generated_artifact_effects(
        connection,
        storage_root=tmp_path / "artifact-root",
        workflow_run_id="wr-capex",
        artifact_version_id="av-capex-envelope",
        artifact_kind="capex.source_inventory.plan",
        artifact_role="evidence",
        source_refs=[SOURCE_REF],
        input_digests=[INPUT_DIGEST],
        validation_summary={"result": "planning_only"},
        payload={"descriptor_count": 2},
        expected_content_digest=expected_digest,
        event_idempotency="capex-envelope-created",
    )

    artifact = result["artifact_version"]
    blob_path = Path(urlparse(str(artifact["storage_uri"])).path)
    stored = json.loads(blob_path.read_text(encoding="utf-8"))

    assert blob_path.name == "capex.source_inventory.plan.v1.json"
    assert stored["schema_version"] == CAPEX_GENERATED_ARTIFACT_ENVELOPE_SCHEMA_VERSION
    assert stored["payload"] == {"descriptor_count": 2}
    assert artifact["artifact_kind"] == "capex.source_inventory.plan"
    assert artifact["content_digest"] == expected_digest
    assert artifact["metadata_json"]["capex_generated_artifact_file_name"] == (
        "capex.source_inventory.plan.v1.json"
    )
    assert result["generated"]["content_digest"] == expected_digest
    assert _artifact_event_count(connection, "wr-capex") == 1


def test_capex_generated_artifact_rejects_deprecated_names() -> None:
    deprecated_names = [
        "Capex.source.plan.v1.json",
        "capex.source plan.v1.json",
        "capex/source.plan.v1.json",
        "source.plan.v1.json",
        "capex.source.plan.json",
    ]

    for file_name in deprecated_names:
        with pytest.raises(CommandError) as exc_info:
            validate_capex_generated_artifact_file_name(file_name)
        assert exc_info.value.code == "invalid_capex_generated_artifact_name"

    with pytest.raises(CommandError) as exc_info:
        canonical_capex_generated_artifact_file_name("capex.Source.plan")
    assert exc_info.value.code == "invalid_capex_generated_artifact_kind"


def test_capex_generated_artifact_envelope_rejects_invalid_shape() -> None:
    with pytest.raises(CommandError) as exc_info:
        build_capex_generated_artifact_envelope(
            artifact_kind="capex.source_inventory.plan",
            artifact_role="evidence",
            source_refs=["artifact_version:av-1"],
            input_digests=[INPUT_DIGEST],
            validation_summary={"result": "planning_only"},
            payload={"ok": True},
        )

    assert exc_info.value.code == "invalid_capex_generated_artifact_envelope"
    assert exc_info.value.details["invalid_source_refs"] == ["artifact_version:av-1"]

    with pytest.raises(CommandError) as missing_refs:
        build_capex_generated_artifact_envelope(
            artifact_kind="capex.project_intake.profile",
            artifact_role="draft",
            source_refs=[],
            input_digests=[INPUT_DIGEST],
            validation_summary={
                "result": CAPEX_SOURCE_INVENTORY_PRE_OCCURRENCE_VALIDATION_RESULT
            },
            payload={"ok": True},
        )
    assert missing_refs.value.code == "invalid_capex_generated_artifact_envelope"


def test_non_capex_generated_artifacts_keep_existing_helper_behavior(tmp_path: Path) -> None:
    connection = _connection()
    _create_run(connection, workflow_run_id="wr-non-capex")

    result = persist_generated_artifact_effects(
        connection,
        storage_root=tmp_path / "artifact-root",
        workflow_run_id="wr-non-capex",
        artifact_version_id="av-non-capex",
        artifact_kind="planning.validation_summary.doc",
        artifact_role="evidence",
        media_type="application/json",
        file_name="legacy-summary.json",
        payload={"ok": True},
    )

    assert result["artifact_version"]["artifact_kind"] == "planning.validation_summary.doc"
    assert result["replay"] is False
