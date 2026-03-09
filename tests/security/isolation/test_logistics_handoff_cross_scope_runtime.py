from __future__ import annotations

import json
from pathlib import Path
import sqlite3
from typing import Any

from tests.runtime.helpers.runtime_cli import run_cli, stderr_json, stdout_json


def _query_rows(db_path: Path, sql: str, params: tuple[Any, ...] = ()) -> list[dict[str, Any]]:
    connection = sqlite3.connect(db_path)
    connection.row_factory = sqlite3.Row
    try:
        rows = connection.execute(sql, params).fetchall()
        return [dict(row) for row in rows]
    finally:
        connection.close()


def _create_workflow_run(
    db_url: str,
    *,
    workflow_id: str,
    partition_key: str,
    logical_date: str,
    tenant_id: str,
    domain_id: str,
    idempotency_key: str,
) -> dict[str, Any]:
    result = run_cli(
        "--db-url",
        db_url,
        "runs",
        "create",
        "--json",
        json.dumps(
            {
                "workflow_id": workflow_id,
                "workflow_version": "v1",
                "tenant_id": tenant_id,
                "domain_id": domain_id,
                "partition_key": partition_key,
                "logical_date": logical_date,
                "activation_key": f"{workflow_id}:{partition_key}",
                "idempotency_key": idempotency_key,
            },
            separators=(",", ":"),
        ),
    )
    return stdout_json(result)["workflow_run"]


def _create_artifact(
    db_url: str,
    *,
    workflow_run_id: str,
    artifact_kind: str,
    idempotency_key: str,
    canonical_partition_kind: str | None = None,
    canonical_partition_key: str | None = None,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "workflow_run_id": workflow_run_id,
        "artifact_kind": artifact_kind,
        "artifact_role": "official_input",
        "media_type": "application/octet-stream",
        "storage_uri": f"inmem://{workflow_run_id}/{artifact_kind}/{idempotency_key}",
        "content_digest": f"sha256:{idempotency_key[-32:]:0>32}",
        "metadata_json": {},
        "idempotency_key": idempotency_key,
    }
    if canonical_partition_kind is not None:
        payload["canonical_partition_kind"] = canonical_partition_kind
    if canonical_partition_key is not None:
        payload["canonical_partition_key"] = canonical_partition_key
    result = run_cli(
        "--db-url",
        db_url,
        "artifacts",
        "create-version",
        "--json",
        json.dumps(payload, separators=(",", ":")),
    )
    return stdout_json(result)["artifact_version"]


def test_logistics_handoff_cross_scope_input_is_denied_without_target_side_effects(
    tmp_path: Path,
) -> None:
    db_path = tmp_path / "runtime.db"
    db_url = f"sqlite:///{db_path}"
    run_cli("--db-url", db_url, "init-db")

    weekly_run = _create_workflow_run(
        db_url,
        workflow_id="weekly_schedule_planning.v1",
        partition_key="PW-2026-W10",
        logical_date="2026-03-02",
        tenant_id="tenant-logistics",
        domain_id="domain-hub",
        idempotency_key="idem:security:weekly-run",
    )
    published = _create_artifact(
        db_url,
        workflow_run_id=str(weekly_run["workflow_run_id"]),
        artifact_kind="planning.published_weekly_schedule.workbook",
        idempotency_key="idem:security:published",
    )

    materialized = run_cli(
        "--db-url",
        db_url,
        "handoffs",
        "materialize-weekly-seeds",
        "--json",
        json.dumps(
            {
                "workflow_run_id": str(weekly_run["workflow_run_id"]),
                "published_artifact_version_id": str(published["artifact_version_id"]),
                "service_date_id": "SD-2026-03-06",
                "idempotency_key": "idem:security:materialize",
            },
            separators=(",", ":"),
        ),
    )
    edge_execution_id = str(
        stdout_json(materialized)["result"]["edge_executions"][0]["edge_execution_id"]
    )

    other_scope_run = _create_workflow_run(
        db_url,
        workflow_id="weekly_schedule_planning.v1",
        partition_key="PW-2026-W10",
        logical_date="2026-03-02",
        tenant_id="tenant-other",
        domain_id="domain-other",
        idempotency_key="idem:security:other-scope-run",
    )
    route_delta_cross_scope = _create_artifact(
        db_url,
        workflow_run_id=str(other_scope_run["workflow_run_id"]),
        artifact_kind="dispatch.route_delta_intake.workbook",
        idempotency_key="idem:security:cross-scope-route-delta",
        canonical_partition_kind="ServiceDateID",
        canonical_partition_key="SD-2026-03-06",
    )
    actual_hours = _create_artifact(
        db_url,
        workflow_run_id=str(weekly_run["workflow_run_id"]),
        artifact_kind="planning.actual_hours_snapshot.workbook",
        idempotency_key="idem:security:actual-hours",
    )

    failed = run_cli(
        "--db-url",
        db_url,
        "handoffs",
        "activate-live-dispatch",
        "--json",
        json.dumps(
            {
                "edge_execution_id": edge_execution_id,
                "route_delta_source_artifact_version_id": str(
                    route_delta_cross_scope["artifact_version_id"]
                ),
                "actual_hours_source_artifact_version_id": str(actual_hours["artifact_version_id"]),
                "idempotency_key": "idem:security:activate-cross-scope",
            },
            separators=(",", ":"),
        ),
        expect_ok=False,
    )
    error = stderr_json(failed)
    assert error["error_code"] == "cross_scope_handoff_input"

    edge_rows = _query_rows(
        db_path,
        "SELECT status, target_workflow_run_id FROM edge_executions WHERE edge_execution_id = ?",
        (edge_execution_id,),
    )
    live_runs = _query_rows(
        db_path,
        "SELECT workflow_run_id FROM workflow_runs WHERE workflow_id = 'live_dispatch.v1'",
    )
    assert len(edge_rows) == 1
    assert edge_rows[0]["status"] == "prepared"
    assert edge_rows[0]["target_workflow_run_id"] is None
    assert live_runs == []
