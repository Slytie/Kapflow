from __future__ import annotations

from pathlib import Path

from onetruth.application.handlers.approvals import (
    request_approval_command,
    respond_approval_command,
)
from onetruth.application.handlers.artifacts import create_artifact_version_command
from onetruth.application.handlers.pointers import promote_pointer_command
from onetruth.application.services.logistics_operational_cadence import (
    tick_logistics_operational_cadence,
)
from onetruth.infrastructure.db.session import open_sqlite_connection
from onetruth.infrastructure.events.event_store import create_sqlite_substrate


def _db_url(tmp_path: Path) -> str:
    return f"sqlite:///{tmp_path / 'runtime.db'}"


def test_tick_logistics_operational_cadence_prepares_live_dispatch_after_weekly_publish(
    tmp_path: Path,
) -> None:
    connection = open_sqlite_connection(_db_url(tmp_path))
    try:
        create_sqlite_substrate(connection)

        first = tick_logistics_operational_cadence(
            connection,
            service_date_id="SD-2026-03-06",
        )
        assert first["weekly"]["status"] == "created"
        assert first["reporting"]["status"] == "created"
        assert first["live_dispatch"]["status"] == "skipped"
        assert first["live_dispatch"]["skipped_reason"] == "waiting_on_weekly_publish"

        weekly_run_id = str(first["weekly"]["workflow_run_id"])
        published = create_artifact_version_command(
            connection,
            {
                "artifact_version_id": "av-test-cadence-published-weekly",
                "workflow_run_id": weekly_run_id,
                "artifact_kind": "planning.published_weekly_schedule.workbook",
                "artifact_role": "official_output",
                "media_type": "application/json",
                "storage_uri": f"inmem://tests/cadence/{weekly_run_id}/published.json",
                "content_digest": "sha256:test-cadence-published-weekly",
                "metadata_json": {"source": "test_logistics_operational_cadence_tick"},
                "canonical_partition_kind": "PlanningWeekID",
                "canonical_partition_key": "PW-2026-W10",
                "idempotency_key": "tests:cadence:artifact:published-weekly",
                "actor_id": "human:test-ops-manager",
                "actor_type": "human",
            },
            include_receipt=True,
        )["result"]
        approval = request_approval_command(
            connection,
            {
                "approval_id": "ap-test-cadence-weekly-publish",
                "workflow_run_id": weekly_run_id,
                "approval_kind": "business_decision",
                "scope_kind": "stage",
                "scope_ref": "Stage06",
                "action": "manual_publish_gate",
                "candidate_roles": ["operations_manager"],
                "required_role": "operations_manager",
                "idempotency_key": "tests:cadence:approval:weekly-publish-request",
                "actor_id": "human:test-ops-manager",
                "actor_type": "human",
            },
            include_receipt=True,
        )["result"]
        respond_approval_command(
            connection,
            {
                "approval_id": str(approval["approval_id"]),
                "actor_id": "human:test-ops-manager",
                "actor_type": "human",
                "actor_roles": ["operations_manager"],
                "response_kind": "approve",
                "idempotency_key": "tests:cadence:approval:weekly-publish-respond",
            },
            include_receipt=True,
        )
        promote_pointer_command(
            connection,
            {
                "workflow_run_id": weekly_run_id,
                "scope_kind": "stage",
                "scope_ref": "Stage06",
                "pointer_key": "official:planning.published_weekly_schedule.workbook",
                "artifact_kind": "planning.published_weekly_schedule.workbook",
                "artifact_version_id": str(published["artifact_version_id"]),
                "promotion_reason": "official_publish",
                "approved_by_approval_id": str(approval["approval_id"]),
                "idempotency_key": "tests:cadence:pointer:published-weekly",
                "actor_id": "human:test-ops-manager",
                "actor_type": "human",
            },
            include_receipt=True,
        )

        second = tick_logistics_operational_cadence(
            connection,
            service_date_id="SD-2026-03-06",
        )
        assert second["live_dispatch"]["status"] == "created"
        assert second["live_dispatch"]["workflow_run_id"] is not None
        assert second["live_dispatch"]["human_task_id"] is not None
        assert second["live_dispatch"]["edge_execution_id"] is not None

        live_run_id = str(second["live_dispatch"]["workflow_run_id"])
        third = tick_logistics_operational_cadence(
            connection,
            service_date_id="SD-2026-03-06",
        )
        assert third["live_dispatch"]["status"] == "existing"
        assert third["live_dispatch"]["workflow_run_id"] == live_run_id
        assert third["live_dispatch"]["human_task_id"] == second["live_dispatch"]["human_task_id"]
        assert third["live_dispatch"]["edge_execution_id"] == second["live_dispatch"]["edge_execution_id"]

        seed_counts = connection.execute(
            """
            SELECT COUNT(*) AS row_count
            FROM artifact_versions
            WHERE workflow_run_id = ?
              AND artifact_kind = 'dispatch.base_schedule_seed.workbook'
            """,
            (live_run_id,),
        ).fetchone()
        assert seed_counts is not None
        assert int(seed_counts["row_count"]) == 1

        live_task_counts = connection.execute(
            """
            SELECT COUNT(*) AS row_count
            FROM human_tasks
            WHERE workflow_run_id = ?
              AND task_kind = 'dispatch_seed_intake'
            """,
            (live_run_id,),
        ).fetchone()
        assert live_task_counts is not None
        assert int(live_task_counts["row_count"]) == 1
    finally:
        connection.close()


def test_tick_logistics_operational_cadence_skips_weekly_on_non_friday(
    tmp_path: Path,
) -> None:
    connection = open_sqlite_connection(_db_url(tmp_path))
    try:
        create_sqlite_substrate(connection)

        result = tick_logistics_operational_cadence(
            connection,
            service_date_id="SD-2026-03-09",
        )

        assert result["effective_planning_week_id"] == "PW-2026-W11"
        assert result["weekly"]["status"] == "skipped"
        assert result["weekly"]["skipped_reason"] == "not_planning_day"
        assert result["weekly"]["workflow_run_id"] is None
        assert result["reporting"]["status"] == "created"
        assert result["live_dispatch"]["status"] == "skipped"
        assert result["live_dispatch"]["skipped_reason"] == "waiting_on_weekly_publish"

        workflow_runs = connection.execute(
            """
            SELECT workflow_id, COUNT(*) AS run_count
            FROM workflow_runs
            GROUP BY workflow_id
            ORDER BY workflow_id ASC
            """
        ).fetchall()
        assert [dict(row) for row in workflow_runs] == [
            {"workflow_id": "dispatch_reporting.v1", "run_count": 1}
        ]
    finally:
        connection.close()
