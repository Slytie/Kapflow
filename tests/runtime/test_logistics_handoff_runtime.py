from __future__ import annotations

import json
from pathlib import Path
import sqlite3
from typing import Any

from onetruth.application.services.logistics_handoff_runtime import (
    MajorReplanPolicy,
    deterministic_rank_candidates,
    should_escalate_major_replan,
)
from tests.runtime.helpers.runtime_cli import run_cli, stderr_json, stdout_json


PLANNING_WEEK_ID = "PW-2026-W10"
FUTURE_PLANNING_WEEK_ID = "PW-2026-W11"
SERVICE_DATE_ID = "SD-2026-03-06"


def _init_db(tmp_path: Path) -> tuple[str, Path]:
    db_path = tmp_path / "runtime.db"
    db_url = f"sqlite:///{db_path}"
    run_cli("--db-url", db_url, "init-db")
    return db_url, db_path


def _create_workflow_run(
    db_url: str,
    *,
    workflow_id: str,
    partition_key: str,
    logical_date: str,
    tenant_id: str = "tenant-logistics",
    domain_id: str = "domain-hub",
    activation_key: str | None = None,
    idempotency_key: str | None = None,
) -> dict[str, Any]:
    payload = {
        "workflow_id": workflow_id,
        "workflow_version": "v1",
        "tenant_id": tenant_id,
        "domain_id": domain_id,
        "partition_key": partition_key,
        "logical_date": logical_date,
        "activation_key": activation_key or f"{workflow_id}:{partition_key}",
        "idempotency_key": idempotency_key or f"idem:runs.create:{workflow_id}:{partition_key}",
    }
    result = run_cli(
        "--db-url",
        db_url,
        "runs",
        "create",
        "--json",
        json.dumps(payload, separators=(",", ":")),
    )
    return stdout_json(result)["workflow_run"]


def _create_artifact_version(
    db_url: str,
    *,
    workflow_run_id: str,
    artifact_kind: str,
    idempotency_key: str,
    artifact_role: str = "official_input",
    media_type: str = "application/octet-stream",
    task_run_id: str | None = None,
    metadata_json: dict[str, Any] | None = None,
    parent_artifact_version_id: str | None = None,
    supersedes_artifact_version_id: str | None = None,
    canonical_partition_kind: str | None = None,
    canonical_partition_key: str | None = None,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "workflow_run_id": workflow_run_id,
        "artifact_kind": artifact_kind,
        "artifact_role": artifact_role,
        "media_type": media_type,
        "storage_uri": f"inmem://{workflow_run_id}/{artifact_kind}/{idempotency_key}",
        "content_digest": f"sha256:{idempotency_key[-32:]:0>32}",
        "metadata_json": metadata_json or {},
        "idempotency_key": idempotency_key,
    }
    if task_run_id is not None:
        payload["task_run_id"] = task_run_id
    if parent_artifact_version_id is not None:
        payload["parent_artifact_version_id"] = parent_artifact_version_id
    if supersedes_artifact_version_id is not None:
        payload["supersedes_artifact_version_id"] = supersedes_artifact_version_id
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


def _materialize_handoff(
    db_url: str,
    *,
    workflow_run_id: str,
    published_artifact_version_id: str,
    idempotency_key: str,
    service_date_id: str | None = None,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "workflow_run_id": workflow_run_id,
        "published_artifact_version_id": published_artifact_version_id,
        "idempotency_key": idempotency_key,
    }
    if service_date_id is not None:
        payload["service_date_id"] = service_date_id
    result = run_cli(
        "--db-url",
        db_url,
        "handoffs",
        "materialize-weekly-seeds",
        "--json",
        json.dumps(payload, separators=(",", ":")),
    )
    return stdout_json(result)["result"]


def _activate_handoff(
    db_url: str,
    *,
    edge_execution_id: str,
    route_delta_source_artifact_version_id: str,
    actual_hours_source_artifact_version_id: str,
    idempotency_key: str,
) -> dict[str, Any]:
    payload = {
        "edge_execution_id": edge_execution_id,
        "route_delta_source_artifact_version_id": route_delta_source_artifact_version_id,
        "actual_hours_source_artifact_version_id": actual_hours_source_artifact_version_id,
        "idempotency_key": idempotency_key,
    }
    result = run_cli(
        "--db-url",
        db_url,
        "handoffs",
        "activate-live-dispatch",
        "--json",
        json.dumps(payload, separators=(",", ":")),
    )
    return stdout_json(result)["result"]


def _notify_only_handoff(
    db_url: str,
    *,
    edge_id: str,
    source_workflow_run_id: str,
    source_artifact_version_id: str,
    idempotency_key: str,
) -> dict[str, Any]:
    payload = {
        "edge_id": edge_id,
        "source_workflow_run_id": source_workflow_run_id,
        "source_artifact_version_id": source_artifact_version_id,
        "idempotency_key": idempotency_key,
    }
    result = run_cli(
        "--db-url",
        db_url,
        "handoffs",
        "notify-only",
        "--json",
        json.dumps(payload, separators=(",", ":")),
    )
    return stdout_json(result)["result"]


def _query_rows(db_path: Path, sql: str, params: tuple[Any, ...] = ()) -> list[dict[str, Any]]:
    connection = sqlite3.connect(db_path)
    connection.row_factory = sqlite3.Row
    try:
        rows = connection.execute(sql, params).fetchall()
        return [dict(row) for row in rows]
    finally:
        connection.close()


def _execute_sql(db_path: Path, sql: str, params: tuple[Any, ...] = ()) -> None:
    connection = sqlite3.connect(db_path)
    try:
        connection.execute(sql, params)
        connection.commit()
    finally:
        connection.close()


def _setup_weekly_with_publish(tmp_path: Path) -> tuple[str, Path, dict[str, Any], dict[str, Any]]:
    db_url, db_path = _init_db(tmp_path)
    weekly_run = _create_workflow_run(
        db_url,
        workflow_id="weekly_schedule_planning.v1",
        partition_key=PLANNING_WEEK_ID,
        logical_date="2026-03-02",
    )
    published = _create_artifact_version(
        db_url,
        workflow_run_id=str(weekly_run["workflow_run_id"]),
        artifact_kind="planning.published_weekly_schedule.workbook",
        idempotency_key="idem:artifact:weekly-publish",
    )
    return db_url, db_path, weekly_run, published


def _setup_reporting_with_final_packet(
    tmp_path: Path,
) -> tuple[str, Path, dict[str, Any], dict[str, Any]]:
    db_url, db_path = _init_db(tmp_path)
    reporting_run = _create_workflow_run(
        db_url,
        workflow_id="dispatch_reporting.v1",
        partition_key=SERVICE_DATE_ID,
        logical_date="2026-03-06",
    )
    _, final_packet = _create_reporting_feedback_artifacts(
        db_url,
        workflow_run_id=str(reporting_run["workflow_run_id"]),
        service_date="2026-03-06",
        idempotency_suffix="reporting-final-packet",
    )
    return db_url, db_path, reporting_run, final_packet


def _normalized_reporting_payload(
    *,
    service_date: str,
    driver_id: str,
    driver_name: str,
    route_id: str,
    actual_minutes: int,
) -> dict[str, Any]:
    return {
        "schema_version": "1.0",
        "kind": "dispatch_reporting.actuals_normalized",
        "service_date": service_date,
        "station_code": "DVC4",
        "dsp_name": "QDCI",
        "rows": [
            {
                "row_id": f"{driver_id}:{service_date}",
                "service_date": service_date,
                "route_id": route_id,
                "driver_id": driver_id,
                "driver_name": driver_name,
                "actual_minutes": actual_minutes,
                "returned_packages": 0,
                "return_reasons": "",
                "upd_candidate": False,
                "formula_integrity_warning": "",
            }
        ],
        "quality_warnings": [],
        "break_tracker": {"sheet_present": False, "rows": []},
        "route_adherence": {"sheet_present": False, "cycles": []},
        "totals": {"route_count": 1, "upd_candidate_count": 0},
    }


def _create_reporting_feedback_artifacts(
    db_url: str,
    *,
    workflow_run_id: str,
    service_date: str,
    idempotency_suffix: str,
    driver_id: str = "A1NQEGRS26IBJA",
    driver_name: str = "Suraj Pratap Singh",
    route_id: str = "CX93",
    actual_minutes: int = 540,
) -> tuple[dict[str, Any], dict[str, Any]]:
    normalized = _create_artifact_version(
        db_url,
        workflow_run_id=workflow_run_id,
        artifact_kind="reporting.actuals_normalized.workbook",
        idempotency_key=f"idem:artifact:{idempotency_suffix}:normalized",
        artifact_role="official_input",
        media_type="application/json",
        metadata_json=_normalized_reporting_payload(
            service_date=service_date,
            driver_id=driver_id,
            driver_name=driver_name,
            route_id=route_id,
            actual_minutes=actual_minutes,
        ),
    )
    final_packet = _create_artifact_version(
        db_url,
        workflow_run_id=workflow_run_id,
        artifact_kind="reporting.final_packet.workbook",
        idempotency_key=f"idem:artifact:{idempotency_suffix}:final",
        artifact_role="official_output",
        media_type="application/octet-stream",
        metadata_json={
            "normalized_artifact_version_id": str(normalized["artifact_version_id"]),
        },
        canonical_partition_kind="ServiceDateID",
        canonical_partition_key=f"SD-{service_date}",
    )
    return normalized, final_packet


def test_handoff_record_creation_is_explicit_and_idempotent(tmp_path: Path) -> None:
    db_url, db_path, weekly_run, published = _setup_weekly_with_publish(tmp_path)
    first = _materialize_handoff(
        db_url,
        workflow_run_id=str(weekly_run["workflow_run_id"]),
        published_artifact_version_id=str(published["artifact_version_id"]),
        service_date_id=SERVICE_DATE_ID,
        idempotency_key="idem:handoff:materialize:one-day",
    )
    second = _materialize_handoff(
        db_url,
        workflow_run_id=str(weekly_run["workflow_run_id"]),
        published_artifact_version_id=str(published["artifact_version_id"]),
        service_date_id=SERVICE_DATE_ID,
        idempotency_key="idem:handoff:materialize:one-day",
    )

    assert len(first["edge_executions"]) == 1
    assert len(first["seed_artifacts"]) == 1
    assert first["edge_executions"][0]["status"] == "prepared"
    assert first["edge_executions"][0]["edge_execution_id"] == second["edge_executions"][0]["edge_execution_id"]

    edge_rows = _query_rows(
        db_path,
        "SELECT edge_execution_id, status FROM edge_executions",
    )
    assert len(edge_rows) == 1
    assert edge_rows[0]["status"] == "prepared"


def test_duplicate_logical_materialize_request_reuses_same_edge_with_new_idempotency(
    tmp_path: Path,
) -> None:
    db_url, db_path, weekly_run, published = _setup_weekly_with_publish(tmp_path)
    first = _materialize_handoff(
        db_url,
        workflow_run_id=str(weekly_run["workflow_run_id"]),
        published_artifact_version_id=str(published["artifact_version_id"]),
        service_date_id=SERVICE_DATE_ID,
        idempotency_key="idem:handoff:materialize:logical:first",
    )
    second = _materialize_handoff(
        db_url,
        workflow_run_id=str(weekly_run["workflow_run_id"]),
        published_artifact_version_id=str(published["artifact_version_id"]),
        service_date_id=SERVICE_DATE_ID,
        idempotency_key="idem:handoff:materialize:logical:retry",
    )

    assert first["edge_executions"][0]["edge_execution_id"] == second["edge_executions"][0]["edge_execution_id"]
    assert first["seed_artifacts"][0]["artifact_version_id"] == second["seed_artifacts"][0]["artifact_version_id"]

    rows = _query_rows(
        db_path,
        """
        SELECT edge_execution_id, materialize_idempotency_key
        FROM edge_executions
        WHERE edge_id = 'weekly_seed_to_live_dispatch'
        """,
    )
    assert len(rows) == 1
    assert rows[0]["materialize_idempotency_key"] == "idem:handoff:materialize:logical:first"


def test_retry_after_daily_seed_exists_reuses_seed_without_duplication(tmp_path: Path) -> None:
    db_url, db_path, weekly_run, published = _setup_weekly_with_publish(tmp_path)
    first = _materialize_handoff(
        db_url,
        workflow_run_id=str(weekly_run["workflow_run_id"]),
        published_artifact_version_id=str(published["artifact_version_id"]),
        service_date_id=SERVICE_DATE_ID,
        idempotency_key="idem:handoff:materialize:seed-exists:first",
    )
    original_edge_id = str(first["edge_executions"][0]["edge_execution_id"])
    seed_artifact_id = str(first["seed_artifacts"][0]["artifact_version_id"])

    _execute_sql(
        db_path,
        "DELETE FROM edge_executions WHERE edge_execution_id = ?",
        (original_edge_id,),
    )

    replay = _materialize_handoff(
        db_url,
        workflow_run_id=str(weekly_run["workflow_run_id"]),
        published_artifact_version_id=str(published["artifact_version_id"]),
        service_date_id=SERVICE_DATE_ID,
        idempotency_key="idem:handoff:materialize:seed-exists:retry",
    )

    assert str(replay["seed_artifacts"][0]["artifact_version_id"]) == seed_artifact_id
    assert str(replay["edge_executions"][0]["edge_execution_id"]) != original_edge_id

    seed_rows = _query_rows(
        db_path,
        """
        SELECT artifact_version_id
        FROM artifact_versions
        WHERE artifact_kind = 'planning.daily_dispatch_seed.workbook'
        """,
    )
    edge_rows = _query_rows(
        db_path,
        "SELECT edge_execution_id FROM edge_executions WHERE edge_id = 'weekly_seed_to_live_dispatch'",
    )
    assert len(seed_rows) == 1
    assert len(edge_rows) == 1


def test_stage07_seed_materialization_is_one_logical_seed_per_service_day(tmp_path: Path) -> None:
    db_url, db_path, weekly_run, published = _setup_weekly_with_publish(tmp_path)
    result = _materialize_handoff(
        db_url,
        workflow_run_id=str(weekly_run["workflow_run_id"]),
        published_artifact_version_id=str(published["artifact_version_id"]),
        idempotency_key="idem:handoff:materialize:full-week",
    )
    assert len(result["edge_executions"]) == 7
    assert len(result["seed_artifacts"]) == 7

    seed_days = {
        str(item["metadata_json"]["service_date_id"])
        for item in result["seed_artifacts"]
    }
    assert seed_days == {
        "SD-2026-03-02",
        "SD-2026-03-03",
        "SD-2026-03-04",
        "SD-2026-03-05",
        "SD-2026-03-06",
        "SD-2026-03-07",
        "SD-2026-03-08",
    }

    artifact_rows = _query_rows(
        db_path,
        """
        SELECT artifact_version_id, partition_kind, partition_key
        FROM artifact_versions
        WHERE workflow_run_id = ? AND artifact_kind = 'planning.daily_dispatch_seed.workbook'
        ORDER BY artifact_version_id ASC
        """,
        (str(weekly_run["workflow_run_id"]),),
    )
    assert len(artifact_rows) == 7
    assert all(row["partition_kind"] == "ServiceDateID" for row in artifact_rows)
    assert sorted(str(row["partition_key"]) for row in artifact_rows) == sorted(seed_days)


def test_lazy_live_activation_captures_exact_input_bindings_and_replay_is_safe(tmp_path: Path) -> None:
    db_url, db_path, weekly_run, published = _setup_weekly_with_publish(tmp_path)
    materialized = _materialize_handoff(
        db_url,
        workflow_run_id=str(weekly_run["workflow_run_id"]),
        published_artifact_version_id=str(published["artifact_version_id"]),
        service_date_id=SERVICE_DATE_ID,
        idempotency_key="idem:handoff:materialize:activate",
    )
    edge_execution = materialized["edge_executions"][0]
    seed_artifact = materialized["seed_artifacts"][0]

    pre_live = run_cli(
        "--db-url",
        db_url,
        "runs",
        "list",
        "--workflow-id",
        "live_dispatch.v1",
        "--tenant-id",
        "tenant-logistics",
        "--domain-id",
        "domain-hub",
        "--json",
    )
    assert stdout_json(pre_live)["workflow_runs"] == []

    route_delta = _create_artifact_version(
        db_url,
        workflow_run_id=str(weekly_run["workflow_run_id"]),
        artifact_kind="dispatch.route_delta_intake.workbook",
        idempotency_key="idem:artifact:route-delta-source",
        metadata_json={"service_date_id": SERVICE_DATE_ID},
        canonical_partition_kind="ServiceDateID",
        canonical_partition_key=SERVICE_DATE_ID,
    )
    actual_hours = _create_artifact_version(
        db_url,
        workflow_run_id=str(weekly_run["workflow_run_id"]),
        artifact_kind="planning.actual_hours_snapshot.workbook",
        idempotency_key="idem:artifact:actual-hours-source",
    )

    activated = _activate_handoff(
        db_url,
        edge_execution_id=str(edge_execution["edge_execution_id"]),
        route_delta_source_artifact_version_id=str(route_delta["artifact_version_id"]),
        actual_hours_source_artifact_version_id=str(actual_hours["artifact_version_id"]),
        idempotency_key="idem:handoff:activate:one",
    )
    replay = _activate_handoff(
        db_url,
        edge_execution_id=str(edge_execution["edge_execution_id"]),
        route_delta_source_artifact_version_id=str(route_delta["artifact_version_id"]),
        actual_hours_source_artifact_version_id=str(actual_hours["artifact_version_id"]),
        idempotency_key="idem:handoff:activate:one",
    )

    live_run = activated["target_workflow_run"]
    assert live_run["workflow_id"] == "live_dispatch.v1"
    assert live_run["partition_key"] == SERVICE_DATE_ID
    assert activated["edge_execution"]["status"] == "activated"
    assert activated["edge_execution"]["trigger_ref"] == str(route_delta["artifact_version_id"])
    assert activated["edge_execution"]["target_workflow_run_id"] == str(live_run["workflow_run_id"])
    assert replay["target_workflow_run"]["workflow_run_id"] == live_run["workflow_run_id"]

    input_rows = _query_rows(
        db_path,
        """
        SELECT source_ref
        FROM workflow_run_inputs
        WHERE workflow_run_id = ?
        ORDER BY source_ref ASC
        """,
        (str(live_run["workflow_run_id"]),),
    )
    assert {str(row["source_ref"]) for row in input_rows} == {
        str(seed_artifact["artifact_version_id"]),
        str(route_delta["artifact_version_id"]),
        str(actual_hours["artifact_version_id"]),
    }

    live_input_rows = _query_rows(
        db_path,
        """
        SELECT artifact_kind, parent_artifact_version_id
        FROM artifact_versions
        WHERE workflow_run_id = ?
        ORDER BY artifact_kind ASC
        """,
        (str(live_run["workflow_run_id"]),),
    )
    by_kind = {str(row["artifact_kind"]): str(row["parent_artifact_version_id"]) for row in live_input_rows}
    assert by_kind["dispatch.base_schedule_seed.workbook"] == str(seed_artifact["artifact_version_id"])
    assert by_kind["dispatch.route_delta_intake.workbook"] == str(route_delta["artifact_version_id"])
    assert by_kind["dispatch.actual_hours_snapshot.workbook"] == str(actual_hours["artifact_version_id"])
    assert len(live_input_rows) == 3

    edge_rows = _query_rows(
        db_path,
        "SELECT edge_execution_id, status, target_workflow_run_id FROM edge_executions",
    )
    assert len(edge_rows) == 1
    assert edge_rows[0]["status"] == "activated"
    assert str(edge_rows[0]["target_workflow_run_id"]) == str(live_run["workflow_run_id"])


def test_retry_activation_reuses_existing_target_run_when_already_present(tmp_path: Path) -> None:
    db_url, db_path, weekly_run, published = _setup_weekly_with_publish(tmp_path)
    materialized = _materialize_handoff(
        db_url,
        workflow_run_id=str(weekly_run["workflow_run_id"]),
        published_artifact_version_id=str(published["artifact_version_id"]),
        service_date_id=SERVICE_DATE_ID,
        idempotency_key="idem:handoff:materialize:target-preexists",
    )
    edge_execution = materialized["edge_executions"][0]

    preexisting_live_run = _create_workflow_run(
        db_url,
        workflow_id="live_dispatch.v1",
        partition_key=SERVICE_DATE_ID,
        logical_date="2026-03-06",
        activation_key=f"live_dispatch.v1:{SERVICE_DATE_ID}",
        idempotency_key="idem:runs.create:live-preexisting",
    )
    route_delta = _create_artifact_version(
        db_url,
        workflow_run_id=str(weekly_run["workflow_run_id"]),
        artifact_kind="dispatch.route_delta_intake.workbook",
        idempotency_key="idem:artifact:target-preexists:route-delta",
        canonical_partition_kind="ServiceDateID",
        canonical_partition_key=SERVICE_DATE_ID,
    )
    actual_hours = _create_artifact_version(
        db_url,
        workflow_run_id=str(weekly_run["workflow_run_id"]),
        artifact_kind="planning.actual_hours_snapshot.workbook",
        idempotency_key="idem:artifact:target-preexists:actual-hours",
    )
    activated = _activate_handoff(
        db_url,
        edge_execution_id=str(edge_execution["edge_execution_id"]),
        route_delta_source_artifact_version_id=str(route_delta["artifact_version_id"]),
        actual_hours_source_artifact_version_id=str(actual_hours["artifact_version_id"]),
        idempotency_key="idem:handoff:activate:target-preexists",
    )

    assert str(activated["target_workflow_run"]["workflow_run_id"]) == str(
        preexisting_live_run["workflow_run_id"]
    )

    run_rows = _query_rows(
        db_path,
        """
        SELECT workflow_run_id
        FROM workflow_runs
        WHERE workflow_id = 'live_dispatch.v1'
          AND tenant_id = 'tenant-logistics'
          AND domain_id = 'domain-hub'
          AND partition_key = ?
        """,
        (SERVICE_DATE_ID,),
    )
    assert len(run_rows) == 1


def test_activation_restart_recovery_from_prepared_edge_reuses_existing_live_artifacts(
    tmp_path: Path,
) -> None:
    db_url, db_path, weekly_run, published = _setup_weekly_with_publish(tmp_path)
    materialized = _materialize_handoff(
        db_url,
        workflow_run_id=str(weekly_run["workflow_run_id"]),
        published_artifact_version_id=str(published["artifact_version_id"]),
        service_date_id=SERVICE_DATE_ID,
        idempotency_key="idem:handoff:materialize:restart-recovery",
    )
    edge_execution = materialized["edge_executions"][0]
    route_delta = _create_artifact_version(
        db_url,
        workflow_run_id=str(weekly_run["workflow_run_id"]),
        artifact_kind="dispatch.route_delta_intake.workbook",
        idempotency_key="idem:artifact:restart-recovery:route-delta",
        canonical_partition_kind="ServiceDateID",
        canonical_partition_key=SERVICE_DATE_ID,
    )
    actual_hours = _create_artifact_version(
        db_url,
        workflow_run_id=str(weekly_run["workflow_run_id"]),
        artifact_kind="planning.actual_hours_snapshot.workbook",
        idempotency_key="idem:artifact:restart-recovery:actual-hours",
    )
    first = _activate_handoff(
        db_url,
        edge_execution_id=str(edge_execution["edge_execution_id"]),
        route_delta_source_artifact_version_id=str(route_delta["artifact_version_id"]),
        actual_hours_source_artifact_version_id=str(actual_hours["artifact_version_id"]),
        idempotency_key="idem:handoff:activate:restart-recovery:first",
    )
    live_run_id = str(first["target_workflow_run"]["workflow_run_id"])

    _execute_sql(
        db_path,
        """
        UPDATE edge_executions
        SET
            status = 'prepared',
            target_workflow_run_id = NULL,
            trigger_ref = NULL,
            activation_idempotency_key = NULL,
            activated_at = NULL
        WHERE edge_execution_id = ?
        """,
        (str(edge_execution["edge_execution_id"]),),
    )

    recovered = _activate_handoff(
        db_url,
        edge_execution_id=str(edge_execution["edge_execution_id"]),
        route_delta_source_artifact_version_id=str(route_delta["artifact_version_id"]),
        actual_hours_source_artifact_version_id=str(actual_hours["artifact_version_id"]),
        idempotency_key="idem:handoff:activate:restart-recovery:retry",
    )

    assert str(recovered["target_workflow_run"]["workflow_run_id"]) == live_run_id
    assert recovered["edge_execution"]["status"] == "activated"

    live_input_rows = _query_rows(
        db_path,
        """
        SELECT artifact_kind
        FROM artifact_versions
        WHERE workflow_run_id = ?
          AND artifact_kind IN (
              'dispatch.base_schedule_seed.workbook',
              'dispatch.route_delta_intake.workbook',
              'dispatch.actual_hours_snapshot.workbook'
          )
        """,
        (live_run_id,),
    )
    binding_rows = _query_rows(
        db_path,
        "SELECT binding_key FROM workflow_run_inputs WHERE workflow_run_id = ?",
        (live_run_id,),
    )
    assert len(live_input_rows) == 3
    assert len(binding_rows) == 3


def test_activation_replay_requires_exact_canonical_input_bindings(tmp_path: Path) -> None:
    db_url, db_path, weekly_run, published = _setup_weekly_with_publish(tmp_path)
    materialized = _materialize_handoff(
        db_url,
        workflow_run_id=str(weekly_run["workflow_run_id"]),
        published_artifact_version_id=str(published["artifact_version_id"]),
        service_date_id=SERVICE_DATE_ID,
        idempotency_key="idem:handoff:materialize:exact-inputs",
    )
    edge_execution = materialized["edge_executions"][0]
    route_delta = _create_artifact_version(
        db_url,
        workflow_run_id=str(weekly_run["workflow_run_id"]),
        artifact_kind="dispatch.route_delta_intake.workbook",
        idempotency_key="idem:artifact:exact-inputs:route-delta",
        canonical_partition_kind="ServiceDateID",
        canonical_partition_key=SERVICE_DATE_ID,
    )
    actual_hours = _create_artifact_version(
        db_url,
        workflow_run_id=str(weekly_run["workflow_run_id"]),
        artifact_kind="planning.actual_hours_snapshot.workbook",
        idempotency_key="idem:artifact:exact-inputs:actual-hours",
    )
    activated = _activate_handoff(
        db_url,
        edge_execution_id=str(edge_execution["edge_execution_id"]),
        route_delta_source_artifact_version_id=str(route_delta["artifact_version_id"]),
        actual_hours_source_artifact_version_id=str(actual_hours["artifact_version_id"]),
        idempotency_key="idem:handoff:activate:exact-inputs:first",
    )
    live_run_id = str(activated["target_workflow_run"]["workflow_run_id"])

    replay_ok = _activate_handoff(
        db_url,
        edge_execution_id=str(edge_execution["edge_execution_id"]),
        route_delta_source_artifact_version_id=str(route_delta["artifact_version_id"]),
        actual_hours_source_artifact_version_id=str(actual_hours["artifact_version_id"]),
        idempotency_key="idem:handoff:activate:exact-inputs:retry",
    )
    assert str(replay_ok["target_workflow_run"]["workflow_run_id"]) == live_run_id

    route_delta_retry = _create_artifact_version(
        db_url,
        workflow_run_id=str(weekly_run["workflow_run_id"]),
        artifact_kind="dispatch.route_delta_intake.workbook",
        idempotency_key="idem:artifact:exact-inputs:route-delta:changed",
        canonical_partition_kind="ServiceDateID",
        canonical_partition_key=SERVICE_DATE_ID,
    )
    failed = run_cli(
        "--db-url",
        db_url,
        "handoffs",
        "activate-live-dispatch",
        "--json",
        json.dumps(
            {
                "edge_execution_id": str(edge_execution["edge_execution_id"]),
                "route_delta_source_artifact_version_id": str(route_delta_retry["artifact_version_id"]),
                "actual_hours_source_artifact_version_id": str(actual_hours["artifact_version_id"]),
                "idempotency_key": "idem:handoff:activate:exact-inputs:mismatch",
            },
            separators=(",", ":"),
        ),
        expect_ok=False,
    )
    error = stderr_json(failed)
    assert error["error_code"] == "handoff_activation_input_mismatch"

    binding_rows = _query_rows(
        db_path,
        "SELECT binding_key FROM workflow_run_inputs WHERE workflow_run_id = ?",
        (live_run_id,),
    )
    assert len(binding_rows) == 3


def test_activation_rejects_superseded_route_delta_source(tmp_path: Path) -> None:
    db_url, _, weekly_run, published = _setup_weekly_with_publish(tmp_path)
    materialized = _materialize_handoff(
        db_url,
        workflow_run_id=str(weekly_run["workflow_run_id"]),
        published_artifact_version_id=str(published["artifact_version_id"]),
        service_date_id=SERVICE_DATE_ID,
        idempotency_key="idem:handoff:materialize:superseded-route",
    )
    edge_execution = materialized["edge_executions"][0]
    route_delta_stale = _create_artifact_version(
        db_url,
        workflow_run_id=str(weekly_run["workflow_run_id"]),
        artifact_kind="dispatch.route_delta_intake.workbook",
        idempotency_key="idem:artifact:superseded-route:stale",
        canonical_partition_kind="ServiceDateID",
        canonical_partition_key=SERVICE_DATE_ID,
    )
    _create_artifact_version(
        db_url,
        workflow_run_id=str(weekly_run["workflow_run_id"]),
        artifact_kind="dispatch.route_delta_intake.workbook",
        idempotency_key="idem:artifact:superseded-route:new",
        canonical_partition_kind="ServiceDateID",
        canonical_partition_key=SERVICE_DATE_ID,
        supersedes_artifact_version_id=str(route_delta_stale["artifact_version_id"]),
    )
    actual_hours = _create_artifact_version(
        db_url,
        workflow_run_id=str(weekly_run["workflow_run_id"]),
        artifact_kind="planning.actual_hours_snapshot.workbook",
        idempotency_key="idem:artifact:superseded-route:actual-hours",
    )

    failed = run_cli(
        "--db-url",
        db_url,
        "handoffs",
        "activate-live-dispatch",
        "--json",
        json.dumps(
            {
                "edge_execution_id": str(edge_execution["edge_execution_id"]),
                "route_delta_source_artifact_version_id": str(route_delta_stale["artifact_version_id"]),
                "actual_hours_source_artifact_version_id": str(actual_hours["artifact_version_id"]),
                "idempotency_key": "idem:handoff:activate:superseded-route",
            },
            separators=(",", ":"),
        ),
        expect_ok=False,
    )
    error = stderr_json(failed)
    assert error["error_code"] == "handoff_source_artifact_superseded"


def test_activation_rejects_superseded_actual_hours_source(tmp_path: Path) -> None:
    db_url, _, weekly_run, published = _setup_weekly_with_publish(tmp_path)
    materialized = _materialize_handoff(
        db_url,
        workflow_run_id=str(weekly_run["workflow_run_id"]),
        published_artifact_version_id=str(published["artifact_version_id"]),
        service_date_id=SERVICE_DATE_ID,
        idempotency_key="idem:handoff:materialize:superseded-hours",
    )
    edge_execution = materialized["edge_executions"][0]
    route_delta = _create_artifact_version(
        db_url,
        workflow_run_id=str(weekly_run["workflow_run_id"]),
        artifact_kind="dispatch.route_delta_intake.workbook",
        idempotency_key="idem:artifact:superseded-hours:route-delta",
        canonical_partition_kind="ServiceDateID",
        canonical_partition_key=SERVICE_DATE_ID,
    )
    actual_hours_stale = _create_artifact_version(
        db_url,
        workflow_run_id=str(weekly_run["workflow_run_id"]),
        artifact_kind="planning.actual_hours_snapshot.workbook",
        idempotency_key="idem:artifact:superseded-hours:stale",
    )
    _create_artifact_version(
        db_url,
        workflow_run_id=str(weekly_run["workflow_run_id"]),
        artifact_kind="planning.actual_hours_snapshot.workbook",
        idempotency_key="idem:artifact:superseded-hours:new",
        supersedes_artifact_version_id=str(actual_hours_stale["artifact_version_id"]),
    )

    failed = run_cli(
        "--db-url",
        db_url,
        "handoffs",
        "activate-live-dispatch",
        "--json",
        json.dumps(
            {
                "edge_execution_id": str(edge_execution["edge_execution_id"]),
                "route_delta_source_artifact_version_id": str(route_delta["artifact_version_id"]),
                "actual_hours_source_artifact_version_id": str(actual_hours_stale["artifact_version_id"]),
                "idempotency_key": "idem:handoff:activate:superseded-hours",
            },
            separators=(",", ":"),
        ),
        expect_ok=False,
    )
    error = stderr_json(failed)
    assert error["error_code"] == "handoff_source_artifact_superseded"


def test_activation_rejects_invalid_status_transition(tmp_path: Path) -> None:
    db_url, db_path, weekly_run, published = _setup_weekly_with_publish(tmp_path)
    materialized = _materialize_handoff(
        db_url,
        workflow_run_id=str(weekly_run["workflow_run_id"]),
        published_artifact_version_id=str(published["artifact_version_id"]),
        service_date_id=SERVICE_DATE_ID,
        idempotency_key="idem:handoff:materialize:invalid-status",
    )
    edge_execution = materialized["edge_executions"][0]
    _execute_sql(
        db_path,
        "UPDATE edge_executions SET status = 'stale' WHERE edge_execution_id = ?",
        (str(edge_execution["edge_execution_id"]),),
    )

    route_delta = _create_artifact_version(
        db_url,
        workflow_run_id=str(weekly_run["workflow_run_id"]),
        artifact_kind="dispatch.route_delta_intake.workbook",
        idempotency_key="idem:artifact:invalid-status:route-delta",
        canonical_partition_kind="ServiceDateID",
        canonical_partition_key=SERVICE_DATE_ID,
    )
    actual_hours = _create_artifact_version(
        db_url,
        workflow_run_id=str(weekly_run["workflow_run_id"]),
        artifact_kind="planning.actual_hours_snapshot.workbook",
        idempotency_key="idem:artifact:invalid-status:actual-hours",
    )
    failed = run_cli(
        "--db-url",
        db_url,
        "handoffs",
        "activate-live-dispatch",
        "--json",
        json.dumps(
            {
                "edge_execution_id": str(edge_execution["edge_execution_id"]),
                "route_delta_source_artifact_version_id": str(route_delta["artifact_version_id"]),
                "actual_hours_source_artifact_version_id": str(actual_hours["artifact_version_id"]),
                "idempotency_key": "idem:handoff:activate:invalid-status",
            },
            separators=(",", ":"),
        ),
        expect_ok=False,
    )
    error = stderr_json(failed)
    assert error["error_code"] == "edge_execution_status_transition_invalid"


def test_handoff_rejects_cross_scope_input_bindings(tmp_path: Path) -> None:
    db_url, _, weekly_run, published = _setup_weekly_with_publish(tmp_path)
    materialized = _materialize_handoff(
        db_url,
        workflow_run_id=str(weekly_run["workflow_run_id"]),
        published_artifact_version_id=str(published["artifact_version_id"]),
        service_date_id=SERVICE_DATE_ID,
        idempotency_key="idem:handoff:materialize:cross-scope",
    )
    edge_execution = materialized["edge_executions"][0]

    other_scope_run = _create_workflow_run(
        db_url,
        workflow_id="weekly_schedule_planning.v1",
        partition_key=PLANNING_WEEK_ID,
        logical_date="2026-03-02",
        tenant_id="tenant-other",
        domain_id="domain-other",
        activation_key="weekly:other",
        idempotency_key="idem:runs.create:other",
    )
    route_delta_other_scope = _create_artifact_version(
        db_url,
        workflow_run_id=str(other_scope_run["workflow_run_id"]),
        artifact_kind="dispatch.route_delta_intake.workbook",
        idempotency_key="idem:artifact:cross-scope-route-delta",
        canonical_partition_kind="ServiceDateID",
        canonical_partition_key=SERVICE_DATE_ID,
    )
    actual_hours = _create_artifact_version(
        db_url,
        workflow_run_id=str(weekly_run["workflow_run_id"]),
        artifact_kind="planning.actual_hours_snapshot.workbook",
        idempotency_key="idem:artifact:actual-hours-cross-scope",
    )

    failed = run_cli(
        "--db-url",
        db_url,
        "handoffs",
        "activate-live-dispatch",
        "--json",
        json.dumps(
            {
                "edge_execution_id": str(edge_execution["edge_execution_id"]),
                "route_delta_source_artifact_version_id": str(route_delta_other_scope["artifact_version_id"]),
                "actual_hours_source_artifact_version_id": str(actual_hours["artifact_version_id"]),
                "idempotency_key": "idem:handoff:activate:cross-scope",
            },
            separators=(",", ":"),
        ),
        expect_ok=False,
    )
    error = stderr_json(failed)
    assert error["error_code"] == "cross_scope_handoff_input"


def test_live_replan_delta_promotion_is_ordered_and_immutable(tmp_path: Path) -> None:
    db_url, db_path, weekly_run, published = _setup_weekly_with_publish(tmp_path)
    materialized = _materialize_handoff(
        db_url,
        workflow_run_id=str(weekly_run["workflow_run_id"]),
        published_artifact_version_id=str(published["artifact_version_id"]),
        service_date_id=SERVICE_DATE_ID,
        idempotency_key="idem:handoff:materialize:ordered-delta",
    )
    edge_execution = materialized["edge_executions"][0]

    route_delta = _create_artifact_version(
        db_url,
        workflow_run_id=str(weekly_run["workflow_run_id"]),
        artifact_kind="dispatch.route_delta_intake.workbook",
        idempotency_key="idem:artifact:ordered-route-delta",
        canonical_partition_kind="ServiceDateID",
        canonical_partition_key=SERVICE_DATE_ID,
    )
    actual_hours = _create_artifact_version(
        db_url,
        workflow_run_id=str(weekly_run["workflow_run_id"]),
        artifact_kind="planning.actual_hours_snapshot.workbook",
        idempotency_key="idem:artifact:ordered-actual-hours",
    )
    activated = _activate_handoff(
        db_url,
        edge_execution_id=str(edge_execution["edge_execution_id"]),
        route_delta_source_artifact_version_id=str(route_delta["artifact_version_id"]),
        actual_hours_source_artifact_version_id=str(actual_hours["artifact_version_id"]),
        idempotency_key="idem:handoff:activate:ordered-delta",
    )
    live_run_id = str(activated["target_workflow_run"]["workflow_run_id"])

    delta_1 = _create_artifact_version(
        db_url,
        workflow_run_id=live_run_id,
        artifact_kind="dispatch.official_replan_delta.workbook",
        idempotency_key="idem:artifact:delta-1",
        metadata_json={"delta_sequence": 1},
    )
    promote_1 = run_cli(
        "--db-url",
        db_url,
        "pointers",
        "promote",
        "--json",
        json.dumps(
            {
                "workflow_run_id": live_run_id,
                "scope_kind": "stage",
                "scope_ref": "Stage05",
                "pointer_key": "official:dispatch.official_replan_delta.workbook",
                "artifact_kind": "dispatch.official_replan_delta.workbook",
                "artifact_version_id": str(delta_1["artifact_version_id"]),
                "promotion_reason": "live_replan_delta",
                "stream_key": "delta",
                "registry_kind": "ordered_stream",
                "idempotency_key": "idem:pointer:delta:1",
            },
            separators=(",", ":"),
        ),
    )
    pointer_1 = stdout_json(promote_1)["pointer"]
    assert int(pointer_1["generation"]) == 0
    assert pointer_1["registry_kind"] == "ordered_stream"
    assert pointer_1["stream_key"] == "delta"

    delta_2 = _create_artifact_version(
        db_url,
        workflow_run_id=live_run_id,
        artifact_kind="dispatch.official_replan_delta.workbook",
        idempotency_key="idem:artifact:delta-2",
        supersedes_artifact_version_id=str(delta_1["artifact_version_id"]),
        metadata_json={"delta_sequence": 2},
    )
    promote_2 = run_cli(
        "--db-url",
        db_url,
        "pointers",
        "promote",
        "--json",
        json.dumps(
            {
                "workflow_run_id": live_run_id,
                "scope_kind": "stage",
                "scope_ref": "Stage05",
                "pointer_key": "official:dispatch.official_replan_delta.workbook",
                "artifact_kind": "dispatch.official_replan_delta.workbook",
                "artifact_version_id": str(delta_2["artifact_version_id"]),
                "promotion_reason": "live_replan_delta",
                "stream_key": "delta",
                "registry_kind": "ordered_stream",
                "expected_generation": 0,
                "idempotency_key": "idem:pointer:delta:2",
            },
            separators=(",", ":"),
        ),
    )
    pointer_2 = stdout_json(promote_2)["pointer"]
    assert int(pointer_2["generation"]) == 1
    assert pointer_2["artifact_version_id"] == str(delta_2["artifact_version_id"])

    lineage = _query_rows(
        db_path,
        """
        SELECT output_artifact_version_id, input_artifact_version_id, edge_type
        FROM artifact_provenance_edges
        WHERE output_artifact_version_id = ?
        """,
        (str(delta_2["artifact_version_id"]),),
    )
    assert {
        (str(row["output_artifact_version_id"]), str(row["input_artifact_version_id"]), str(row["edge_type"]))
        for row in lineage
    } == {
        (str(delta_2["artifact_version_id"]), str(delta_1["artifact_version_id"]), "supersedes"),
    }


def test_live_dispatch_activation_rejects_existing_target_run_activation_key_drift(
    tmp_path: Path,
) -> None:
    db_url, db_path, weekly_run, published = _setup_weekly_with_publish(tmp_path)
    weekly_run_id = str(weekly_run["workflow_run_id"])
    materialized = _materialize_handoff(
        db_url,
        workflow_run_id=weekly_run_id,
        published_artifact_version_id=str(published["artifact_version_id"]),
        service_date_id=SERVICE_DATE_ID,
        idempotency_key="idem:handoff:activation-key-drift:materialize",
    )
    edge_execution = materialized["edge_executions"][0]
    route_delta = _create_artifact_version(
        db_url,
        workflow_run_id=weekly_run_id,
        artifact_kind="dispatch.route_delta_intake.workbook",
        idempotency_key="idem:artifact:activation-key-drift:route-delta",
        canonical_partition_kind="ServiceDateID",
        canonical_partition_key=SERVICE_DATE_ID,
    )
    actual_hours = _create_artifact_version(
        db_url,
        workflow_run_id=weekly_run_id,
        artifact_kind="planning.actual_hours_snapshot.workbook",
        idempotency_key="idem:artifact:activation-key-drift:actual-hours",
    )
    drifted_live_run = _create_workflow_run(
        db_url,
        workflow_id="live_dispatch.v1",
        partition_key=SERVICE_DATE_ID,
        logical_date="2026-03-06",
        activation_key=f"live_dispatch.v1:{SERVICE_DATE_ID}:drifted",
        idempotency_key="idem:runs.create:activation-key-drift",
    )

    failed = run_cli(
        "--db-url",
        db_url,
        "handoffs",
        "activate-live-dispatch",
        "--json",
        json.dumps(
            {
                "edge_execution_id": str(edge_execution["edge_execution_id"]),
                "route_delta_source_artifact_version_id": str(route_delta["artifact_version_id"]),
                "actual_hours_source_artifact_version_id": str(actual_hours["artifact_version_id"]),
                "idempotency_key": "idem:handoff:activation-key-drift:activate",
            },
            separators=(",", ":"),
        ),
        expect_ok=False,
    )

    assert stderr_json(failed)["error_code"] == "activation_key_drift_detected"
    edge_rows = _query_rows(
        db_path,
        """
        SELECT status, target_workflow_run_id
        FROM edge_executions
        WHERE edge_execution_id = ?
        """,
        (str(edge_execution["edge_execution_id"]),),
    )
    assert edge_rows == [{"status": "prepared", "target_workflow_run_id": None}]
    input_rows = _query_rows(
        db_path,
        "SELECT binding_key FROM workflow_run_inputs WHERE workflow_run_id = ?",
        (str(drifted_live_run["workflow_run_id"]),),
    )
    assert input_rows == []


def test_weekly_to_live_dispatch_first_golden_slice_end_to_end(tmp_path: Path) -> None:
    db_url, db_path, weekly_run, published = _setup_weekly_with_publish(tmp_path)
    weekly_run_id = str(weekly_run["workflow_run_id"])

    _create_artifact_version(
        db_url,
        workflow_run_id=weekly_run_id,
        artifact_kind="planning.route_horizon.workbook",
        idempotency_key="idem:artifact:route-horizon",
    )
    _create_artifact_version(
        db_url,
        workflow_run_id=weekly_run_id,
        artifact_kind="planning.approved_availability.workbook",
        idempotency_key="idem:artifact:approved-availability",
    )
    actual_hours = _create_artifact_version(
        db_url,
        workflow_run_id=weekly_run_id,
        artifact_kind="planning.actual_hours_snapshot.workbook",
        idempotency_key="idem:artifact:golden-actual-hours",
    )

    weekly_approval_requested = run_cli(
        "--db-url",
        db_url,
        "approvals",
        "request",
        "--json",
        json.dumps(
            {
                "workflow_run_id": weekly_run_id,
                "approval_kind": "business_decision",
                "scope_kind": "stage",
                "scope_ref": "Stage06",
                "candidate_roles": ["operations_manager"],
                "required_role": "operations_manager",
                "idempotency_key": "idem:approval:weekly:request",
            },
            separators=(",", ":"),
        ),
    )
    weekly_approval_id = stdout_json(weekly_approval_requested)["approval"]["approval_id"]
    run_cli(
        "--db-url",
        db_url,
        "approvals",
        "respond",
        "--json",
        json.dumps(
            {
                "approval_id": str(weekly_approval_id),
                "actor_id": "human:ops-manager-1",
                "actor_type": "human",
                "actor_roles": ["operations_manager"],
                "response_kind": "approve",
                "idempotency_key": "idem:approval:weekly:respond",
            },
            separators=(",", ":"),
        ),
    )
    weekly_pointer = run_cli(
        "--db-url",
        db_url,
        "pointers",
        "promote",
        "--json",
        json.dumps(
            {
                "workflow_run_id": weekly_run_id,
                "scope_kind": "stage",
                "scope_ref": "Stage06",
                "pointer_key": "official:planning.published_weekly_schedule.workbook",
                "artifact_kind": "planning.published_weekly_schedule.workbook",
                "artifact_version_id": str(published["artifact_version_id"]),
                "promotion_reason": "official_publish",
                "approved_by_approval_id": str(weekly_approval_id),
                "actor_id": "human:ops-manager-1",
                "actor_type": "human",
                "idempotency_key": "idem:pointer:weekly:publish",
            },
            separators=(",", ":"),
        ),
    )
    assert stdout_json(weekly_pointer)["pointer"]["artifact_version_id"] == str(
        published["artifact_version_id"]
    )

    materialized = _materialize_handoff(
        db_url,
        workflow_run_id=weekly_run_id,
        published_artifact_version_id=str(published["artifact_version_id"]),
        service_date_id=SERVICE_DATE_ID,
        idempotency_key="idem:handoff:golden:materialize",
    )
    edge_execution = materialized["edge_executions"][0]
    seed_artifact = materialized["seed_artifacts"][0]
    assert seed_artifact["metadata_json"]["service_date_id"] == SERVICE_DATE_ID

    route_delta = _create_artifact_version(
        db_url,
        workflow_run_id=weekly_run_id,
        artifact_kind="dispatch.route_delta_intake.workbook",
        idempotency_key="idem:artifact:golden-route-delta",
        metadata_json={"service_date_id": SERVICE_DATE_ID},
        canonical_partition_kind="ServiceDateID",
        canonical_partition_key=SERVICE_DATE_ID,
    )
    activated = _activate_handoff(
        db_url,
        edge_execution_id=str(edge_execution["edge_execution_id"]),
        route_delta_source_artifact_version_id=str(route_delta["artifact_version_id"]),
        actual_hours_source_artifact_version_id=str(actual_hours["artifact_version_id"]),
        idempotency_key="idem:handoff:golden:activate",
    )
    live_run_id = str(activated["target_workflow_run"]["workflow_run_id"])
    assert activated["edge_execution"]["status"] == "activated"
    assert activated["target_workflow_run"]["workflow_id"] == "live_dispatch.v1"
    assert activated["target_workflow_run"]["partition_key"] == SERVICE_DATE_ID

    run_cli(
        "--db-url",
        db_url,
        "tasks",
        "create",
        "--json",
        json.dumps(
            {
                "workflow_run_id": live_run_id,
                "stage_id": "Stage02",
                "task_kind": "exception_triage",
                "activation_key": f"live-dispatch:{SERVICE_DATE_ID}:stage02:triage",
                "idempotency_key": "idem:task:live:stage02:triage",
            },
            separators=(",", ":"),
        ),
    )
    ranked_candidates = deterministic_rank_candidates(
        [
            {"candidate_driver_id": "DRV-03", "hard_filter_status": "pass", "score_bucket": "good"},
            {"candidate_driver_id": "DRV-02", "hard_filter_status": "pass", "score_bucket": "best"},
            {"candidate_driver_id": "DRV-01", "hard_filter_status": "pass", "score_bucket": "best"},
            {"candidate_driver_id": "DRV-99", "hard_filter_status": "blocked", "score_bucket": "best"},
        ]
    )
    assert [item["candidate_driver_id"] for item in ranked_candidates] == [
        "DRV-01",
        "DRV-02",
        "DRV-03",
        "DRV-99",
    ]
    _create_artifact_version(
        db_url,
        workflow_run_id=live_run_id,
        artifact_kind="dispatch.replan_candidate.workbook",
        idempotency_key="idem:artifact:golden-replan-candidates",
        metadata_json={"ranked_candidates": ranked_candidates},
    )

    policy = MajorReplanPolicy(route_delta_abs_threshold=2)
    assert (
        should_escalate_major_replan(
            route_delta_abs=1,
            no_compliant_candidate=False,
            after_shift_confirmation=False,
            policy=policy,
        )
        is False
    )
    before_escalation = _query_rows(
        db_path,
        "SELECT COUNT(*) AS count FROM approvals WHERE workflow_run_id = ?",
        (live_run_id,),
    )
    assert int(before_escalation[0]["count"]) == 0
    assert (
        should_escalate_major_replan(
            route_delta_abs=3,
            no_compliant_candidate=False,
            after_shift_confirmation=False,
            policy=policy,
        )
        is True
    )
    live_approval_requested = run_cli(
        "--db-url",
        db_url,
        "approvals",
        "request",
        "--json",
        json.dumps(
            {
                "workflow_run_id": live_run_id,
                "approval_kind": "business_decision",
                "scope_kind": "stage",
                "scope_ref": "Stage04",
                "candidate_roles": ["operations_manager"],
                "required_role": "operations_manager",
                "idempotency_key": "idem:approval:live:request",
            },
            separators=(",", ":"),
        ),
    )
    live_approval_id = stdout_json(live_approval_requested)["approval"]["approval_id"]
    run_cli(
        "--db-url",
        db_url,
        "approvals",
        "respond",
        "--json",
        json.dumps(
            {
                "approval_id": str(live_approval_id),
                "actor_id": "human:ops-manager-1",
                "actor_type": "human",
                "actor_roles": ["operations_manager"],
                "response_kind": "approve",
                "idempotency_key": "idem:approval:live:respond",
            },
            separators=(",", ":"),
        ),
    )

    live_delta = _create_artifact_version(
        db_url,
        workflow_run_id=live_run_id,
        artifact_kind="dispatch.official_replan_delta.workbook",
        idempotency_key="idem:artifact:golden-live-delta-1",
        parent_artifact_version_id=str(seed_artifact["artifact_version_id"]),
        metadata_json={"delta_sequence": 1},
    )
    promoted_live_delta = run_cli(
        "--db-url",
        db_url,
        "pointers",
        "promote",
        "--json",
        json.dumps(
            {
                "workflow_run_id": live_run_id,
                "scope_kind": "stage",
                "scope_ref": "Stage05",
                "pointer_key": "official:dispatch.official_replan_delta.workbook",
                "artifact_kind": "dispatch.official_replan_delta.workbook",
                "artifact_version_id": str(live_delta["artifact_version_id"]),
                "promotion_reason": "live_replan_delta",
                "stream_key": "delta",
                "registry_kind": "ordered_stream",
                "idempotency_key": "idem:pointer:live:delta:1",
            },
            separators=(",", ":"),
        ),
    )
    promoted_pointer = stdout_json(promoted_live_delta)["pointer"]
    assert promoted_pointer["registry_kind"] == "ordered_stream"
    assert promoted_pointer["stream_key"] == "delta"
    assert promoted_pointer["artifact_version_id"] == str(live_delta["artifact_version_id"])

    replay_materialize = _materialize_handoff(
        db_url,
        workflow_run_id=weekly_run_id,
        published_artifact_version_id=str(published["artifact_version_id"]),
        service_date_id=SERVICE_DATE_ID,
        idempotency_key="idem:handoff:golden:materialize",
    )
    replay_activate = _activate_handoff(
        db_url,
        edge_execution_id=str(edge_execution["edge_execution_id"]),
        route_delta_source_artifact_version_id=str(route_delta["artifact_version_id"]),
        actual_hours_source_artifact_version_id=str(actual_hours["artifact_version_id"]),
        idempotency_key="idem:handoff:golden:activate",
    )
    assert replay_materialize["edge_executions"][0]["edge_execution_id"] == str(
        edge_execution["edge_execution_id"]
    )
    assert replay_activate["target_workflow_run"]["workflow_run_id"] == live_run_id

    handoff_rows = _query_rows(
        db_path,
        """
        SELECT edge_execution_id, status, target_workflow_run_id, trigger_ref
        FROM edge_executions
        WHERE edge_execution_id = ?
        """,
        (str(edge_execution["edge_execution_id"]),),
    )
    assert len(handoff_rows) == 1
    assert handoff_rows[0]["status"] == "activated"
    assert str(handoff_rows[0]["target_workflow_run_id"]) == live_run_id
    assert str(handoff_rows[0]["trigger_ref"]) == str(route_delta["artifact_version_id"])

    lineage_rows = _query_rows(
        db_path,
        """
        SELECT output_artifact_version_id, input_artifact_version_id, edge_type
        FROM artifact_provenance_edges
        WHERE output_artifact_version_id = ?
        """,
        (str(seed_artifact["artifact_version_id"]),),
    )
    assert (
        str(seed_artifact["artifact_version_id"]),
        str(published["artifact_version_id"]),
        "derives_from",
    ) in {
        (str(row["output_artifact_version_id"]), str(row["input_artifact_version_id"]), str(row["edge_type"]))
        for row in lineage_rows
    }

    live_inputs = _query_rows(
        db_path,
        """
        SELECT source_ref
        FROM workflow_run_inputs
        WHERE workflow_run_id = ?
        ORDER BY source_ref ASC
        """,
        (live_run_id,),
    )
    assert {str(row["source_ref"]) for row in live_inputs} == {
        str(seed_artifact["artifact_version_id"]),
        str(route_delta["artifact_version_id"]),
        str(actual_hours["artifact_version_id"]),
    }


def test_notify_only_handoff_dispatches_over_compiled_reporting_edge_and_materializes_target_input(
    tmp_path: Path,
) -> None:
    db_url, db_path, reporting_run, final_packet = _setup_reporting_with_final_packet(tmp_path)
    notified = _notify_only_handoff(
        db_url,
        edge_id="reporting_actuals_to_future_planning",
        source_workflow_run_id=str(reporting_run["workflow_run_id"]),
        source_artifact_version_id=str(final_packet["artifact_version_id"]),
        idempotency_key="idem:handoff:notify:reporting:one",
    )

    assert len(notified["edge_executions"]) == 1
    assert len(notified["target_workflow_runs"]) == 1
    assert len(notified["target_input_artifacts"]) == 1

    edge = notified["edge_executions"][0]
    target_run = notified["target_workflow_runs"][0]
    target_input = notified["target_input_artifacts"][0]
    assert edge["edge_id"] == "reporting_actuals_to_future_planning"
    assert edge["target_workflow_id"] == "weekly_schedule_planning.v1"
    assert edge["target_partition_kind"] == "PlanningWeekID"
    assert edge["target_partition_key"] == FUTURE_PLANNING_WEEK_ID
    assert str(edge["target_workflow_run_id"]) == str(target_run["workflow_run_id"])
    assert target_run["partition_key"] == FUTURE_PLANNING_WEEK_ID
    assert target_input["artifact_kind"] == "planning.actual_hours_snapshot.workbook"
    assert str(target_input["parent_artifact_version_id"]) == str(final_packet["artifact_version_id"])
    assert target_input["metadata_json"]["columns"][0] == "service_date"
    assert target_input["metadata_json"]["rows"] == [
        [
            "2026-03-06",
            "A1NQEGRS26IBJA",
            "Suraj Pratap Singh",
            "WORKED",
            540,
            "CX93",
            "",
            0,
            0,
            0,
            target_input["metadata_json"]["rows"][0][10],
        ]
    ]

    input_rows = _query_rows(
        db_path,
        """
        SELECT binding_key, source_ref, artifact_version_id
        FROM workflow_run_inputs
        WHERE workflow_run_id = ?
        ORDER BY binding_key ASC
        """,
        (str(target_run["workflow_run_id"]),),
    )
    assert input_rows == [
        {
            "binding_key": "stage03.actual_hours_snapshot",
            "source_ref": str(final_packet["artifact_version_id"]),
            "artifact_version_id": str(target_input["artifact_version_id"]),
        }
    ]

    pointer_rows = _query_rows(
        db_path,
        "SELECT pointer_key FROM artifact_pointers WHERE workflow_run_id = ?",
        (str(target_run["workflow_run_id"]),),
    )
    assert pointer_rows == []

    official_output_rows = _query_rows(
        db_path,
        """
        SELECT artifact_version_id
        FROM artifact_versions
        WHERE workflow_run_id = ? AND artifact_role = 'official_output'
        """,
        (str(target_run["workflow_run_id"]),),
    )
    assert official_output_rows == []


def test_notify_only_handoff_is_idempotent_for_target_run_resolution_and_edge_reuse(tmp_path: Path) -> None:
    db_url, db_path, reporting_run, final_packet = _setup_reporting_with_final_packet(tmp_path)
    first = _notify_only_handoff(
        db_url,
        edge_id="reporting_actuals_to_future_planning",
        source_workflow_run_id=str(reporting_run["workflow_run_id"]),
        source_artifact_version_id=str(final_packet["artifact_version_id"]),
        idempotency_key="idem:handoff:notify:reporting:first",
    )
    second = _notify_only_handoff(
        db_url,
        edge_id="reporting_actuals_to_future_planning",
        source_workflow_run_id=str(reporting_run["workflow_run_id"]),
        source_artifact_version_id=str(final_packet["artifact_version_id"]),
        idempotency_key="idem:handoff:notify:reporting:second",
    )

    assert first["edge_executions"][0]["edge_execution_id"] == second["edge_executions"][0]["edge_execution_id"]
    assert (
        first["target_workflow_runs"][0]["workflow_run_id"]
        == second["target_workflow_runs"][0]["workflow_run_id"]
    )

    run_rows = _query_rows(
        db_path,
        """
        SELECT workflow_run_id
        FROM workflow_runs
        WHERE workflow_id = 'weekly_schedule_planning.v1'
          AND partition_key = ?
        """,
        (FUTURE_PLANNING_WEEK_ID,),
    )
    assert len(run_rows) == 1

    edge_rows = _query_rows(
        db_path,
        """
        SELECT edge_execution_id, materialize_idempotency_key
        FROM edge_executions
        WHERE edge_id = 'reporting_actuals_to_future_planning'
        """,
    )
    assert len(edge_rows) == 1
    assert edge_rows[0]["materialize_idempotency_key"] == "idem:handoff:notify:reporting:first"

    binding_rows = _query_rows(
        db_path,
        """
        SELECT binding_key, source_ref
        FROM workflow_run_inputs
        WHERE workflow_run_id = ?
        """,
        (str(first["target_workflow_runs"][0]["workflow_run_id"]),),
    )
    assert len(binding_rows) == 1
    assert binding_rows[0]["binding_key"] == "stage03.actual_hours_snapshot"
    assert binding_rows[0]["source_ref"] == str(final_packet["artifact_version_id"])


def test_notify_only_handoff_refreshes_weekly_actual_hours_binding_for_newer_feedback(
    tmp_path: Path,
) -> None:
    db_url, db_path = _init_db(tmp_path)
    first_reporting_run = _create_workflow_run(
        db_url,
        workflow_id="dispatch_reporting.v1",
        partition_key="SD-2026-03-05",
        logical_date="2026-03-05",
        activation_key="dispatch_reporting.v1:SD-2026-03-05:first",
        idempotency_key="idem:runs.create:dispatch_reporting.v1:SD-2026-03-05:first",
    )
    _, first_final_packet = _create_reporting_feedback_artifacts(
        db_url,
        workflow_run_id=str(first_reporting_run["workflow_run_id"]),
        service_date="2026-03-05",
        idempotency_suffix="reporting-first-feedback",
        route_id="CX90",
        actual_minutes=480,
    )
    first = _notify_only_handoff(
        db_url,
        edge_id="reporting_actuals_to_future_planning",
        source_workflow_run_id=str(first_reporting_run["workflow_run_id"]),
        source_artifact_version_id=str(first_final_packet["artifact_version_id"]),
        idempotency_key="idem:handoff:notify:reporting:first-feedback",
    )

    second_reporting_run = _create_workflow_run(
        db_url,
        workflow_id="dispatch_reporting.v1",
        partition_key="SD-2026-03-06",
        logical_date="2026-03-06",
        activation_key="dispatch_reporting.v1:SD-2026-03-06:second",
        idempotency_key="idem:runs.create:dispatch_reporting.v1:SD-2026-03-06:second",
    )
    _, second_final_packet = _create_reporting_feedback_artifacts(
        db_url,
        workflow_run_id=str(second_reporting_run["workflow_run_id"]),
        service_date="2026-03-06",
        idempotency_suffix="reporting-second-feedback",
        route_id="CX93",
        actual_minutes=540,
    )
    second = _notify_only_handoff(
        db_url,
        edge_id="reporting_actuals_to_future_planning",
        source_workflow_run_id=str(second_reporting_run["workflow_run_id"]),
        source_artifact_version_id=str(second_final_packet["artifact_version_id"]),
        idempotency_key="idem:handoff:notify:reporting:second-feedback",
    )

    assert (
        str(first["target_workflow_runs"][0]["workflow_run_id"])
        == str(second["target_workflow_runs"][0]["workflow_run_id"])
    )

    binding_rows = _query_rows(
        db_path,
        """
        SELECT binding_key, source_ref, artifact_version_id
        FROM workflow_run_inputs
        WHERE workflow_run_id = ?
        """,
        (str(second["target_workflow_runs"][0]["workflow_run_id"]),),
    )
    assert binding_rows == [
        {
            "binding_key": "stage03.actual_hours_snapshot",
            "source_ref": str(second_final_packet["artifact_version_id"]),
            "artifact_version_id": str(second["target_input_artifacts"][0]["artifact_version_id"]),
        }
    ]

    artifact_rows = _query_rows(
        db_path,
        """
        SELECT artifact_version_id, supersedes_artifact_version_id, metadata_json
        FROM artifact_versions
        WHERE workflow_run_id = ?
          AND artifact_kind = 'planning.actual_hours_snapshot.workbook'
        ORDER BY created_at ASC
        """,
        (str(second["target_workflow_runs"][0]["workflow_run_id"]),),
    )
    assert len(artifact_rows) == 2
    assert artifact_rows[0]["supersedes_artifact_version_id"] is None
    assert artifact_rows[1]["supersedes_artifact_version_id"] == artifact_rows[0]["artifact_version_id"]

    latest_payload = json.loads(str(artifact_rows[1]["metadata_json"]))
    assert latest_payload["rows"] == [
        [
            "2026-03-05",
            "A1NQEGRS26IBJA",
            "Suraj Pratap Singh",
            "WORKED",
            480,
            "CX90",
            "",
            0,
            0,
            0,
            latest_payload["rows"][0][10],
        ],
        [
            "2026-03-06",
            "A1NQEGRS26IBJA",
            "Suraj Pratap Singh",
            "WORKED",
            540,
            "CX93",
            "",
            0,
            0,
            0,
            latest_payload["rows"][1][10],
        ],
    ]

    edge_rows = _query_rows(
        db_path,
        """
        SELECT edge_execution_id
        FROM edge_executions
        WHERE edge_id = 'reporting_actuals_to_future_planning'
        ORDER BY created_at ASC
        """,
    )
    assert len(edge_rows) == 2


def test_notify_only_handoff_rejects_non_notify_only_edge_ids(tmp_path: Path) -> None:
    db_url, _, weekly_run, published = _setup_weekly_with_publish(tmp_path)
    failed = run_cli(
        "--db-url",
        db_url,
        "handoffs",
        "notify-only",
        "--json",
        json.dumps(
            {
                "edge_id": "weekly_seed_to_live_dispatch",
                "source_workflow_run_id": str(weekly_run["workflow_run_id"]),
                "source_artifact_version_id": str(published["artifact_version_id"]),
                "idempotency_key": "idem:handoff:notify:mismatch",
            },
            separators=(",", ":"),
        ),
        expect_ok=False,
    )
    error = stderr_json(failed)
    assert error["error_code"] == "handoff_mode_mismatch"
