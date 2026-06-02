from __future__ import annotations

import hashlib
from pathlib import Path
import sqlite3
from types import SimpleNamespace
from urllib.parse import urlparse

from onetruth.application.handlers.schedule_control import (
    STAGE04_OUTPUT_SPECS,
    build_weekly_schedule_control_command,
    persist_weekly_stage04_output_payloads,
)
from onetruth.application.handlers.workflow_task_lifecycle import (
    create_workflow_run_command,
)
from onetruth.infrastructure.events.event_store import (
    create_sqlite_substrate,
    list_events,
    utc_now_iso,
)
from onetruth.infrastructure.repositories.artifact_provenance import (
    list_artifact_provenance_edges_for_output,
)
from onetruth.infrastructure.repositories.artifact_versions import create_artifact_version


def _connection() -> sqlite3.Connection:
    connection = sqlite3.connect(":memory:")
    connection.row_factory = sqlite3.Row
    create_sqlite_substrate(connection)
    return connection


def _create_weekly_run(
    connection: sqlite3.Connection,
    *,
    workflow_run_id: str,
    partition_key: str = "PW-2026-W13",
) -> dict[str, object]:
    return create_workflow_run_command(
        connection,
        {
            "workflow_run_id": workflow_run_id,
            "workflow_id": "weekly_schedule_planning.v1",
            "workflow_version": "v1",
            "tenant_id": "tenant-logistics",
            "domain_id": "domain-hub",
            "partition_key": partition_key,
            "logical_date": "2026-03-22",
            "activation_key": f"weekly_schedule_planning.v1:{partition_key}:{workflow_run_id}",
        },
    )


def _create_input_artifact(
    connection: sqlite3.Connection,
    *,
    workflow_run_id: str,
    artifact_version_id: str,
    artifact_kind: str,
    payload: dict[str, object],
) -> str:
    digest = hashlib.sha256(repr(payload).encode("utf-8")).hexdigest()
    create_artifact_version(
        connection,
        artifact_version_id=artifact_version_id,
        workflow_run_id=workflow_run_id,
        tenant_id="tenant-logistics",
        domain_id="domain-hub",
        dataset_key=artifact_kind,
        partition_kind="PlanningWeekID",
        partition_key="PW-2026-W13",
        task_run_id=None,
        artifact_kind=artifact_kind,
        artifact_role="official_input",
        media_type="application/json",
        storage_uri=f"inmem://stage04-input/{artifact_version_id}",
        content_digest=f"sha256:{digest}",
        byte_size=None,
        metadata_json=payload,
        parent_artifact_version_id=None,
        supersedes_artifact_version_id=None,
        lineage_note="test fixture input",
        created_at=utc_now_iso(),
    )
    return artifact_version_id


def _artifact_created_events(
    connection: sqlite3.Connection,
    *,
    workflow_run_id: str,
) -> list[dict[str, object]]:
    return [
        event
        for event in list_events(connection, run_id=workflow_run_id, limit=1000)
        if event["event_type"] == "artifact.version.created"
    ]


def test_weekly_stage04_outputs_are_file_backed_evented_and_provenance_linked(
    tmp_path: Path,
    monkeypatch,
) -> None:
    storage_root = tmp_path / "artifact-root"
    monkeypatch.setenv("ONETRUTH_ARTIFACT_ROOT", str(storage_root))
    connection = _connection()
    workflow_run = _create_weekly_run(connection, workflow_run_id="wr-stage04-hardening")
    source_input_ids = [
        _create_input_artifact(
            connection,
            workflow_run_id="wr-stage04-hardening",
            artifact_version_id="av-stage04-route-slots",
            artifact_kind="planning.route_slot_requirements.workbook",
            payload={"kind": "route-slots"},
        ),
        _create_input_artifact(
            connection,
            workflow_run_id="wr-stage04-hardening",
            artifact_version_id="av-stage04-driver-caps",
            artifact_kind="planning.driver_capabilities.workbook",
            payload={"kind": "driver-capabilities"},
        ),
    ]
    output_payloads = {
        artifact_kind: {
            "artifact_kind": artifact_kind,
            "candidate_delta_id": "candidate-delta-hardening",
            "payload": [artifact_kind],
        }
        for artifact_kind, _artifact_role in STAGE04_OUTPUT_SPECS
    }

    created = persist_weekly_stage04_output_payloads(
        connection,
        workflow_run=workflow_run,
        bundle_id="bundle-stage04-hardening",
        output_payloads=output_payloads,
        source_input_ids=source_input_ids,
        event_idempotency_base="test-stage04-hardening",
    )

    assert set(created) == {artifact_kind for artifact_kind, _ in STAGE04_OUTPUT_SPECS}
    assert len(_artifact_created_events(connection, workflow_run_id="wr-stage04-hardening")) == 6
    input_bundle_id = str(created["planning.input_bundle.doc"]["artifact_version_id"])
    storage_root_resolved = storage_root.resolve()
    for artifact_kind, artifact in created.items():
        parsed_uri = urlparse(str(artifact["storage_uri"]))
        assert parsed_uri.scheme == "file"
        blob_path = Path(parsed_uri.path).resolve()
        blob_path.relative_to(storage_root_resolved)
        blob_bytes = blob_path.read_bytes()
        assert artifact["byte_size"] == len(blob_bytes)
        assert artifact["content_digest"] == "sha256:" + hashlib.sha256(blob_bytes).hexdigest()
        assert artifact["metadata_json"] == output_payloads[artifact_kind]
        assert artifact["partition_kind"] == "PlanningWeekID"
        assert artifact["partition_key"] == "PW-2026-W13"

        provenance_edges = list_artifact_provenance_edges_for_output(
            connection,
            str(artifact["artifact_version_id"]),
        )
        source_edges = [
            edge
            for edge in provenance_edges
            if (edge.get("metadata_json") or {}).get("lineage_class")
            == "deterministic_weekly_build"
        ]
        assert {edge["input_artifact_version_id"] for edge in source_edges} == set(
            source_input_ids
        )
        if artifact_kind != "planning.input_bundle.doc":
            bundle_edges = [
                edge
                for edge in provenance_edges
                if (edge.get("metadata_json") or {}).get("lineage_class")
                == "bundle_lowering"
            ]
            assert [edge["input_artifact_version_id"] for edge in bundle_edges] == [
                input_bundle_id
            ]


def test_weekly_build_command_receipt_replays_without_duplicate_artifact_events(
    tmp_path: Path,
    monkeypatch,
) -> None:
    monkeypatch.setenv("ONETRUTH_ARTIFACT_ROOT", str(tmp_path / "artifact-root"))
    connection = _connection()
    _create_weekly_run(connection, workflow_run_id="wr-stage04-build-receipt")
    route_slot_id = _create_input_artifact(
        connection,
        workflow_run_id="wr-stage04-build-receipt",
        artifact_version_id="av-stage04-build-route-slots",
        artifact_kind="planning.route_slot_requirements.workbook",
        payload={"route_slots": [{"route_slot_id": "RS-1"}]},
    )
    driver_capability_id = _create_input_artifact(
        connection,
        workflow_run_id="wr-stage04-build-receipt",
        artifact_version_id="av-stage04-build-driver-caps",
        artifact_kind="planning.driver_capabilities.workbook",
        payload={"drivers": [{"driver_id": "D-1"}]},
    )

    def _fake_bundle(**_kwargs: object) -> SimpleNamespace:
        return SimpleNamespace(bundle_id="bundle-stage04-build-receipt")

    def _fake_deterministic_build(*, bundle: object) -> SimpleNamespace:
        assert getattr(bundle, "bundle_id") == "bundle-stage04-build-receipt"
        return SimpleNamespace(
            input_bundle_payload={"bundle_id": "bundle-stage04-build-receipt"},
            candidate_delta_payload={
                "candidate_delta_id": "candidate-delta-build-receipt",
                "rows": [],
            },
            draft_workbook_payload={"assignments": []},
            validation_summary_payload={"summary": {"hard_rule_result": "pass"}},
            draft_doc_payload={"sections": []},
            calculation_snapshot_payload={"calculation_state": "stable"},
            candidate_matrix=[{"candidate_id": "C-1"}],
            selected_candidates=[{"candidate_id": "C-1"}],
            iteration_summaries=[],
            repair_moves=[],
            coverage_summary={"assigned_route_slots": 1, "uncovered_route_slots": 0},
        )

    monkeypatch.setattr(
        "onetruth.application.handlers.schedule_control.build_weekly_schedule_control_bundle",
        _fake_bundle,
    )
    monkeypatch.setattr(
        "onetruth.application.handlers.schedule_control.run_weekly_stage04_deterministic_build",
        _fake_deterministic_build,
    )
    command_payload = {
        "workflow_run_id": "wr-stage04-build-receipt",
        "route_slot_requirements_artifact_version_id": route_slot_id,
        "driver_capabilities_artifact_version_id": driver_capability_id,
        "idempotency_key": "idem:stage04-build:receipt",
    }

    first = build_weekly_schedule_control_command(
        connection,
        command_payload,
        include_receipt=True,
    )
    assert first["idempotent_replay"] is False
    assert len(_artifact_created_events(connection, workflow_run_id="wr-stage04-build-receipt")) == 6
    second = build_weekly_schedule_control_command(
        connection,
        command_payload,
        include_receipt=True,
    )

    assert second["idempotent_replay"] is True
    assert second["receipt"] == first["receipt"]
    assert second["result"]["artifacts"] == first["result"]["artifacts"]
    events = _artifact_created_events(connection, workflow_run_id="wr-stage04-build-receipt")
    assert len(events) == 6
    assert all(
        str(event["idempotency_key"]).endswith(":artifact.version.created")
        for event in events
    )
