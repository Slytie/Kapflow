from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

from onetruth.application.services.logistics_weekly_agent_pilot import (
    PILOT_WEEKLY_STAGE04_REALISTIC_ARTIFACTS,
    describe_weekly_stage04_pilot_fixture_profile,
    run_logistics_weekly_agent_pilot_suite,
)
from onetruth.application.services.schedule_control.route_slot_requirements import (
    expand_route_slot_requirements,
    parse_route_slot_requirements,
)
from onetruth.infrastructure.db.session import open_sqlite_connection
from onetruth.infrastructure.events.event_store import create_sqlite_substrate

RUN_REAL = os.environ.get("ONETRUTH_RUN_OPENAI_E2E", "0") == "1" and os.environ.get(
    "ONETRUTH_RUN_OPENAI_WEEKLY_AGENT_E2E",
    "0",
) == "1"

REQUIRED_EVIDENCE_KINDS = {
    "execution.compiled_spec.json",
    "execution.compile_source_manifest.json",
    "runtime.context_pack.json",
    "runtime.tool_request.json",
    "runtime.tool_result.json",
    "execution.trace.json",
}
REQUIRED_STAGE04_OUTPUT_KINDS = {
    "planning.input_bundle.doc",
    "planning.candidate_schedule_delta.workbook",
    "planning.validation_summary.doc",
    "planning.draft_weekly_schedule.workbook",
    "planning.draft_weekly_schedule.doc",
}


def _stage04_input_metadata_by_kind(connection, workflow_run_id: str) -> dict[str, dict[str, object]]:
    rows = connection.execute(
        """
        SELECT artifact_kind, metadata_json
        FROM artifact_versions
        WHERE workflow_run_id = ?
          AND artifact_kind IN (
            'planning.route_slot_requirements.workbook',
            'planning.driver_capabilities.workbook',
            'planning.approved_availability.workbook',
            'planning.actual_hours_snapshot.workbook'
          )
        ORDER BY artifact_kind ASC
        """,
        (workflow_run_id,),
    ).fetchall()
    return {
        str(row["artifact_kind"]): json.loads(str(row["metadata_json"]))
        for row in rows
    }


def _expanded_route_slot_count(metadata: dict[str, object]) -> int:
    route_slots = parse_route_slot_requirements(
        columns=[str(column) for column in metadata.get("columns") or []],
        rows=list(metadata.get("rows") or []),
    )
    return len(expand_route_slot_requirements(route_slots))


@pytest.mark.skipif(
    not RUN_REAL,
    reason=(
        "weekly Stage04 real OpenAI integration tests are gated; set "
        "ONETRUTH_RUN_OPENAI_E2E=1 and ONETRUTH_RUN_OPENAI_WEEKLY_AGENT_E2E=1 to run"
    ),
)
def test_weekly_stage04_openai_real_e2e(tmp_path: Path) -> None:
    api_key = os.environ.get("OPENAI_API_KEY", "").strip()
    if not api_key:
        pytest.fail(
            "ONETRUTH_RUN_OPENAI_E2E=1 and ONETRUTH_RUN_OPENAI_WEEKLY_AGENT_E2E=1 are set but OPENAI_API_KEY is missing. "
            "Set OPENAI_API_KEY before running weekly Stage04 real OpenAI e2e tests."
        )

    pilot_key = "weekly-stage04-openai-real-e2e"
    db_path = tmp_path / "runtime.db"
    db_url = f"sqlite:///{db_path}"
    output_root = tmp_path / "packets"
    artifact_root = tmp_path / "artifacts"
    expected_profile = describe_weekly_stage04_pilot_fixture_profile(
        PILOT_WEEKLY_STAGE04_REALISTIC_ARTIFACTS
    )

    connection = open_sqlite_connection(db_url)
    try:
        create_sqlite_substrate(connection)
        summary = run_logistics_weekly_agent_pilot_suite(
            connection,
            db_url=db_url,
            pilot_key=pilot_key,
            output_root=output_root,
            artifact_root=artifact_root,
            pilot_ids=[PILOT_WEEKLY_STAGE04_REALISTIC_ARTIFACTS],
            openai_mode="real",
        )

        assert summary["openai_mode"] == "real"
        assert Path(str(summary["summary_json_path"])).exists()
        assert Path(str(summary["summary_markdown_path"])).exists()
        assert len(summary["pilot_runs"]) == 1

        pilot_run = summary["pilot_runs"][0]
        assert pilot_run["pilot_id"] == PILOT_WEEKLY_STAGE04_REALISTIC_ARTIFACTS
        packet_path = Path(str(pilot_run["inspection_packet_path"]))
        packet_markdown_path = Path(str(pilot_run["inspection_markdown_path"]))
        assert packet_path.exists()
        assert packet_markdown_path.exists()

        packet = json.loads(packet_path.read_text(encoding="utf-8"))
        workflow_run_id = str(pilot_run["workflow_run_id"])
        assert packet["workflow_run"]["partition_key"] == expected_profile["planning_week_id"]
        assert packet["quality_signals"]["execution_session_succeeded"] is True
        assert packet["quality_signals"]["tool_execution_completed"] is True
        assert packet["quality_signals"]["policy_allow_recorded"] is True
        assert packet["quality_signals"]["stage04_output_artifacts_present"] is True
        assert len(packet["stage04_analysis"]["iterations"]) >= 1

        sessions = connection.execute(
            "SELECT state, tool_call_count FROM execution_sessions WHERE workflow_run_id = ?",
            (workflow_run_id,),
        ).fetchall()
        assert len(sessions) == 1
        assert sessions[0]["state"] == "SUCCEEDED"
        assert int(sessions[0]["tool_call_count"]) == 1

        tools = connection.execute(
            """
            SELECT state
            FROM tool_executions
            WHERE execution_session_id IN (
              SELECT execution_session_id
              FROM execution_sessions
              WHERE workflow_run_id = ?
            )
            """,
            (workflow_run_id,),
        ).fetchall()
        assert len(tools) == 1
        assert tools[0]["state"] == "COMPLETED"

        artifacts = connection.execute(
            "SELECT artifact_kind FROM artifact_versions WHERE workflow_run_id = ?",
            (workflow_run_id,),
        ).fetchall()
        kinds = {str(row["artifact_kind"]) for row in artifacts}
        assert REQUIRED_EVIDENCE_KINDS.issubset(kinds)
        assert REQUIRED_STAGE04_OUTPUT_KINDS.issubset(kinds)

        metadata_by_kind = _stage04_input_metadata_by_kind(connection, workflow_run_id)
        route_slots = metadata_by_kind["planning.route_slot_requirements.workbook"]
        driver_capabilities = metadata_by_kind["planning.driver_capabilities.workbook"]
        approved_availability = metadata_by_kind["planning.approved_availability.workbook"]
        actual_hours = metadata_by_kind["planning.actual_hours_snapshot.workbook"]

        assert route_slots.get("planning_week_id") == expected_profile["planning_week_id"]
        assert _expanded_route_slot_count(route_slots) == expected_profile["route_slot_count"]
        assert len(list(driver_capabilities.get("rows") or [])) == expected_profile["driver_count"]
        assert _expanded_route_slot_count(route_slots) != 2
        assert len(list(driver_capabilities.get("rows") or [])) != 2

        availability_columns = {
            str(column).strip()
            for column in approved_availability.get("columns") or []
            if str(column).strip()
        }
        actual_hours_columns = {
            str(column).strip()
            for column in actual_hours.get("columns") or []
            if str(column).strip()
        }
        assert expected_profile["has_daily_availability_states"] is True
        assert expected_profile["has_previous_week_history"] is True
        assert {"availability_state", "normalized_availability_state"} & availability_columns
        assert (
            {"previous_week_same_day_state", "previous_week_state"} & availability_columns
            or {"historical_state", "normalized_historical_state"} & actual_hours_columns
        )
    finally:
        connection.close()
