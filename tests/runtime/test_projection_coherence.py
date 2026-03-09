from __future__ import annotations

import json
import os
from pathlib import Path
import sqlite3
import subprocess
import sys

from tests.runtime.helpers.runtime_api import RuntimeApiClient
from tests.runtime.helpers.runtime_cli import REPO_ROOT, SRC_ROOT, run_cli, stdout_json
from tests.runtime.helpers.scenario_harness import RuntimeScenarioHarness

SCENARIO_STAGE06_PUBLISH = (
    REPO_ROOT / "fixtures/scenarios/schedule_planning/stage06_publish_happy.yaml"
)


def _client(harness: RuntimeScenarioHarness) -> RuntimeApiClient:
    return RuntimeApiClient(
        db_url=harness.db_url,
        tenant_id="tenant-a",
        domain_id="domain-x",
        actor_id="human:dispatch-supervisor-1",
        actor_type="human",
        actor_roles=["dispatch_supervisor"],
    )


def _promote_cross_run_pointer_target(harness: RuntimeScenarioHarness) -> tuple[str, str]:
    primary_run = stdout_json(
        run_cli(
            "--db-url",
            harness.db_url,
            "runs",
            "show",
            "--workflow-run-id",
            harness.workflow_run_id,
            "--json",
        )
    )["workflow_run"]

    sibling_run = stdout_json(
        run_cli(
            "--db-url",
            harness.db_url,
            "runs",
            "create",
            "--json",
            json.dumps(
                {
                    "workflow_id": "schedule_planning.v1",
                    "workflow_version": "v1",
                    "tenant_id": "tenant-a",
                    "domain_id": "domain-x",
                    "partition_key": primary_run["partition_key"],
                    "logical_date": primary_run.get("logical_date"),
                    "activation_key": "coherence-cross-run-sibling",
                    "idempotency_key": "coherence-cross-run-sibling-run",
                }
            ),
        )
    )["workflow_run"]

    sibling_artifact = stdout_json(
        run_cli(
            "--db-url",
            harness.db_url,
            "artifacts",
            "create-version",
            "--json",
            json.dumps(
                {
                    "workflow_run_id": sibling_run["workflow_run_id"],
                    "artifact_kind": "schedule.published_schedule.workbook",
                    "artifact_role": "official_output",
                    "media_type": "application/json",
                    "storage_uri": "s3://runtime/coherence-cross-run-sibling.json",
                    "content_digest": "sha256:coherence-cross-run-sibling",
                    "byte_size": 256,
                    "metadata_json": {"source": "projection-coherence-test"},
                    "idempotency_key": "coherence-cross-run-sibling-artifact",
                }
            ),
        )
    )["artifact_version"]

    run_cli(
        "--db-url",
        harness.db_url,
        "pointers",
        "promote",
        "--json",
        json.dumps(
            {
                "workflow_run_id": harness.workflow_run_id,
                "scope_kind": "stage",
                "scope_ref": "Stage06",
                "pointer_key": "official:schedule.published_schedule.workbook",
                "artifact_kind": "schedule.published_schedule.workbook",
                "artifact_version_id": sibling_artifact["artifact_version_id"],
                "promotion_reason": "manual_promote",
                "idempotency_key": "coherence-cross-run-promote",
            }
        ),
    )
    return str(sibling_artifact["artifact_version_id"]), str(sibling_run["workflow_run_id"])


def _set_artifact_kind(db_path: Path, *, artifact_version_id: str, artifact_kind: str) -> None:
    connection = sqlite3.connect(db_path)
    try:
        connection.execute(
            "UPDATE artifact_versions SET artifact_kind = ? WHERE artifact_version_id = ?",
            (artifact_kind, artifact_version_id),
        )
        connection.commit()
    finally:
        connection.close()


def _set_pointer_dataset_key(
    db_path: Path,
    *,
    pointer_key: str,
    dataset_key: str | None,
) -> None:
    connection = sqlite3.connect(db_path)
    try:
        cursor = connection.execute(
            """
            UPDATE artifact_pointers
            SET dataset_key = ?
            WHERE pointer_key = ?
            """,
            (dataset_key, pointer_key),
        )
        if int(cursor.rowcount) <= 0:
            raise AssertionError(f"no artifact pointer rows updated for pointer_key={pointer_key}")
        connection.commit()
    finally:
        connection.close()


def _projection_failure_events(db_url: str, *, workflow_run_id: str) -> list[dict[str, object]]:
    payload = stdout_json(
        run_cli(
            "--db-url",
            db_url,
            "events",
            "list",
            "--run-id",
            workflow_run_id,
            "--json",
        )
    )
    return [
        event
        for event in payload
        if event.get("event_type") == "projection.coherence_failed"
    ]


def _run_workspace_export(
    tmp_path: Path,
    *,
    db_url: str,
    workflow_run_id: str,
) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    existing_pythonpath = env.get("PYTHONPATH")
    if existing_pythonpath:
        env["PYTHONPATH"] = f"{SRC_ROOT}{os.pathsep}{existing_pythonpath}"
    else:
        env["PYTHONPATH"] = str(SRC_ROOT)
    bundle_path = tmp_path / "workspace_bundle.zip"
    return subprocess.run(
        [
            sys.executable,
            "scripts/export_run_workspace_bundle.py",
            "--db-url",
            db_url,
            "--workflow-run-id",
            workflow_run_id,
            "--output",
            str(bundle_path),
        ],
        cwd=REPO_ROOT,
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )


def _setup_weekly_handoff(tmp_path: Path) -> tuple[str, Path, str, str]:
    db_path = tmp_path / "handoff-runtime.db"
    db_url = f"sqlite:///{db_path}"
    run_cli("--db-url", db_url, "init-db")

    weekly_run = stdout_json(
        run_cli(
            "--db-url",
            db_url,
            "runs",
            "create",
            "--json",
            json.dumps(
                {
                    "workflow_id": "weekly_schedule_planning.v1",
                    "workflow_version": "v1",
                    "tenant_id": "tenant-logistics",
                    "domain_id": "domain-hub",
                    "partition_key": "PW-2026-W10",
                    "logical_date": "2026-03-02",
                    "activation_key": "weekly:PW-2026-W10",
                    "idempotency_key": "coherence:weekly:run",
                }
            ),
        )
    )["workflow_run"]

    published = stdout_json(
        run_cli(
            "--db-url",
            db_url,
            "artifacts",
            "create-version",
            "--json",
            json.dumps(
                {
                    "workflow_run_id": weekly_run["workflow_run_id"],
                    "artifact_kind": "planning.published_weekly_schedule.workbook",
                    "artifact_role": "official_output",
                    "media_type": "application/octet-stream",
                    "storage_uri": "inmem://coherence/weekly-publish",
                    "content_digest": "sha256:coherence-weekly-publish",
                    "metadata_json": {},
                    "idempotency_key": "coherence:weekly:publish",
                }
            ),
        )
    )["artifact_version"]

    materialized = stdout_json(
        run_cli(
            "--db-url",
            db_url,
            "handoffs",
            "materialize-weekly-seeds",
            "--json",
            json.dumps(
                {
                    "workflow_run_id": weekly_run["workflow_run_id"],
                    "published_artifact_version_id": published["artifact_version_id"],
                    "service_date_id": "SD-2026-03-06",
                    "idempotency_key": "coherence:handoff:materialize",
                }
            ),
        )
    )["result"]

    edge_execution_id = str(materialized["edge_executions"][0]["edge_execution_id"])
    return db_url, db_path, str(weekly_run["workflow_run_id"]), edge_execution_id


def _inject_handoff_source_drift(db_path: Path, *, edge_execution_id: str) -> None:
    connection = sqlite3.connect(db_path)
    try:
        connection.execute(
            "UPDATE edge_executions SET source_artifact_version_id = ? WHERE edge_execution_id = ?",
            ("av-missing-source", edge_execution_id),
        )
        connection.commit()
    finally:
        connection.close()


def test_workspace_official_outputs_drift_warns_visibly_and_emits_event(tmp_path: Path) -> None:
    harness = RuntimeScenarioHarness.from_yaml(SCENARIO_STAGE06_PUBLISH, tmp_path).prepare()
    sibling_artifact_id, _ = _promote_cross_run_pointer_target(harness)
    _set_artifact_kind(
        harness.db_path,
        artifact_version_id=sibling_artifact_id,
        artifact_kind="dispatch.route_delta_intake.workbook",
    )

    response = _client(harness).get(f"/api/v1/workflow-runs/{harness.workflow_run_id}/workspace")
    assert response.status_code == 200

    coherence = response.payload["official_outputs"]["coherence"]
    assert coherence["coherence_status"] == "failed"
    assert coherence["policy"]["on_drift"] == "warn_visible"
    assert coherence["failure_code"] == "official_output_kind_mismatch"

    failures = _projection_failure_events(harness.db_url, workflow_run_id=harness.workflow_run_id)
    assert any(
        event["payload"]["projection_kind"] == "workspace_official_outputs"
        and event["payload"]["failure_code"] == "official_output_kind_mismatch"
        for event in failures
    )


def test_export_bundle_blocks_on_official_output_drift_and_emits_event(tmp_path: Path) -> None:
    harness = RuntimeScenarioHarness.from_yaml(SCENARIO_STAGE06_PUBLISH, tmp_path).prepare()
    sibling_artifact_id, _ = _promote_cross_run_pointer_target(harness)
    _set_artifact_kind(
        harness.db_path,
        artifact_version_id=sibling_artifact_id,
        artifact_kind="dispatch.route_delta_intake.workbook",
    )

    result = _run_workspace_export(
        tmp_path,
        db_url=harness.db_url,
        workflow_run_id=harness.workflow_run_id,
    )
    assert result.returncode != 0
    error = json.loads(result.stderr)
    assert error["error_code"] == "projection_coherence_failed"
    assert error["details"]["projection_kind"] == "workspace_export_bundle"
    assert error["details"]["failure_code"] == "official_output_kind_mismatch"

    failures = _projection_failure_events(harness.db_url, workflow_run_id=harness.workflow_run_id)
    assert any(
        event["payload"]["projection_kind"] == "workspace_export_bundle"
        and event["payload"]["failure_code"] == "official_output_kind_mismatch"
        for event in failures
    )


def test_export_bundle_blocks_on_missing_source_lineage_and_emits_event(tmp_path: Path) -> None:
    harness = RuntimeScenarioHarness.from_yaml(SCENARIO_STAGE06_PUBLISH, tmp_path).prepare()
    _promote_cross_run_pointer_target(harness)
    _set_pointer_dataset_key(
        harness.db_path,
        pointer_key="official:schedule.published_schedule.workbook",
        dataset_key=None,
    )

    result = _run_workspace_export(
        tmp_path,
        db_url=harness.db_url,
        workflow_run_id=harness.workflow_run_id,
    )
    assert result.returncode != 0
    error = json.loads(result.stderr)
    assert error["error_code"] == "projection_coherence_failed"
    assert error["details"]["projection_kind"] == "workspace_export_bundle"
    assert error["details"]["failure_code"] == "official_output_pointer_lineage_missing"
    assert error["details"]["issues"]

    failures = _projection_failure_events(harness.db_url, workflow_run_id=harness.workflow_run_id)
    assert any(
        event["payload"]["projection_kind"] == "workspace_export_bundle"
        and event["payload"]["failure_code"] == "official_output_pointer_lineage_missing"
        for event in failures
    )


def test_handoff_operator_view_drift_warns_visibly_and_emits_event(tmp_path: Path) -> None:
    db_url, db_path, workflow_run_id, edge_execution_id = _setup_weekly_handoff(tmp_path)
    _inject_handoff_source_drift(db_path, edge_execution_id=edge_execution_id)

    show_payload = stdout_json(
        run_cli(
            "--db-url",
            db_url,
            "handoffs",
            "show",
            "--edge-execution-id",
            edge_execution_id,
            "--json",
        )
    )
    coherence = show_payload["coherence"]
    assert coherence["coherence_status"] == "failed"
    assert coherence["policy"]["on_drift"] == "warn_visible"
    assert coherence["failure_code"] == "handoff_source_artifact_missing"

    failures = _projection_failure_events(db_url, workflow_run_id=workflow_run_id)
    assert any(
        event["payload"]["projection_kind"] == "handoff_operator_view"
        and event["payload"]["failure_code"] == "handoff_source_artifact_missing"
        for event in failures
    )


def test_projection_coherence_policy_is_warn_for_workspace_and_block_for_export(tmp_path: Path) -> None:
    harness = RuntimeScenarioHarness.from_yaml(SCENARIO_STAGE06_PUBLISH, tmp_path).prepare()
    sibling_artifact_id, _ = _promote_cross_run_pointer_target(harness)
    _set_artifact_kind(
        harness.db_path,
        artifact_version_id=sibling_artifact_id,
        artifact_kind="dispatch.route_delta_intake.workbook",
    )

    workspace = _client(harness).get(f"/api/v1/workflow-runs/{harness.workflow_run_id}/workspace")
    assert workspace.status_code == 200
    assert workspace.payload["official_outputs"]["coherence"]["policy"]["on_drift"] == "warn_visible"

    export = _run_workspace_export(
        tmp_path,
        db_url=harness.db_url,
        workflow_run_id=harness.workflow_run_id,
    )
    assert export.returncode != 0
