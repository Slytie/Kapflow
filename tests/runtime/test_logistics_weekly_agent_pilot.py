from __future__ import annotations

import json
from pathlib import Path

from onetruth.application.services.logistics_weekly_agent_pilot import (
    PILOT_WEEKLY_STAGE04_AGENT,
    run_logistics_weekly_agent_pilot_suite,
)
from onetruth.infrastructure.db.session import open_sqlite_connection
from onetruth.infrastructure.events.event_store import create_sqlite_substrate


def _run_pilot(
    tmp_dir: Path,
    *,
    pilot_ids: list[str],
    pilot_key: str,
    openai_mode: str = "mock",
) -> tuple[str, dict[str, object], list[dict[str, object]]]:
    db_path = tmp_dir / "runtime.db"
    db_url = f"sqlite:///{db_path}"
    output_root = tmp_dir / "packets"
    artifact_root = tmp_dir / "artifacts"

    connection = open_sqlite_connection(db_url)
    try:
        create_sqlite_substrate(connection)
        summary = run_logistics_weekly_agent_pilot_suite(
            connection,
            db_url=db_url,
            pilot_key=pilot_key,
            output_root=output_root,
            artifact_root=artifact_root,
            pilot_ids=pilot_ids,
            openai_mode=openai_mode,
        )
    finally:
        connection.close()

    packets: list[dict[str, object]] = []
    for run in summary["pilot_runs"]:
        packet_path = Path(str(run["inspection_packet_path"]))
        packets.append(json.loads(packet_path.read_text(encoding="utf-8")))
    return db_url, summary, packets


def _count_by_workflow_run_id(db_url: str, workflow_run_id: str) -> dict[str, int]:
    queries = {
        "workflow_runs": "SELECT COUNT(*) FROM workflow_runs WHERE workflow_run_id = ?",
        "task_runs": "SELECT COUNT(*) FROM task_runs WHERE workflow_run_id = ?",
        "human_tasks": "SELECT COUNT(*) FROM human_tasks WHERE workflow_run_id = ?",
        "artifact_versions": "SELECT COUNT(*) FROM artifact_versions WHERE workflow_run_id = ?",
        "artifact_pointers": "SELECT COUNT(*) FROM artifact_pointers WHERE workflow_run_id = ?",
        "execution_sessions": "SELECT COUNT(*) FROM execution_sessions WHERE workflow_run_id = ?",
        "tool_executions": (
            "SELECT COUNT(*) FROM tool_executions "
            "WHERE execution_session_id IN (SELECT execution_session_id FROM execution_sessions WHERE workflow_run_id = ?)"
        ),
        "policy_decisions": (
            "SELECT COUNT(*) FROM policy_decisions "
            "WHERE tool_execution_id IN ("
            "SELECT tool_execution_id FROM tool_executions "
            "WHERE execution_session_id IN (SELECT execution_session_id FROM execution_sessions WHERE workflow_run_id = ?)"
            ")"
        ),
        "timeline_events": "SELECT COUNT(*) FROM timeline_events WHERE workflow_run_id = ?",
    }

    connection = open_sqlite_connection(db_url)
    try:
        counts: dict[str, int] = {}
        for key, query in queries.items():
            row = connection.execute(query, (workflow_run_id,)).fetchone()
            assert row is not None
            counts[key] = int(row[0])
        return counts
    finally:
        connection.close()


def test_weekly_stage04_pilot_mock_emits_canonical_execution_and_evidence_packet(
    tmp_path: Path,
) -> None:
    _, summary, packets = _run_pilot(
        tmp_path,
        pilot_ids=[PILOT_WEEKLY_STAGE04_AGENT],
        pilot_key="weekly-stage04-pilot",
    )
    packet = packets[0]

    assert summary["openai_mode"] == "mock"
    assert packet["workflow_run"]["workflow_id"] == "weekly_schedule_planning.v1"
    assert packet["stage_focus"] == "Stage04"
    assert packet["openai_mode"] == "mock"

    quality = packet["quality_signals"]
    assert quality["execution_session_succeeded"] is True
    assert quality["tool_execution_completed"] is True
    assert quality["policy_allow_recorded"] is True
    assert quality["execution_semantics_evidence_present"] is True
    assert quality["runtime_turn_evidence_present"] is True
    assert quality["stage04_output_artifacts_present"] is True
    assert quality["no_pointer_promotions"] is True
    assert quality["timeline_has_execution_lifecycle"] is True

    canonical_evidence = packet["canonical_evidence"]
    for ids in canonical_evidence["execution_semantics_evidence_by_kind"].values():
        assert ids
    for ids in canonical_evidence["runtime_turn_evidence_by_kind"].values():
        assert ids
    for ids in canonical_evidence["stage04_output_artifacts_by_kind"].values():
        assert ids
    assert canonical_evidence["canonical_query_commands"]

    event_types = {
        event["event_type"] for event in packet["timeline"]["events_of_interest"]
    }
    assert "execution.session.created" in event_types
    assert "tool.execution.requested" in event_types
    assert "tool.execution.approved" in event_types
    assert "tool.execution.completed" in event_types


def test_repeat_pilot_run_with_same_key_does_not_duplicate_canonical_effects(tmp_path: Path) -> None:
    db_url, first_summary, first_packets = _run_pilot(
        tmp_path,
        pilot_ids=[PILOT_WEEKLY_STAGE04_AGENT],
        pilot_key="repeat-safe-weekly-stage04",
    )
    workflow_run_id = str(first_packets[0]["workflow_run"]["workflow_run_id"])
    before = _count_by_workflow_run_id(db_url, workflow_run_id)

    _, second_summary, second_packets = _run_pilot(
        tmp_path,
        pilot_ids=[PILOT_WEEKLY_STAGE04_AGENT],
        pilot_key="repeat-safe-weekly-stage04",
    )
    after = _count_by_workflow_run_id(db_url, workflow_run_id)

    assert before == after
    assert first_summary["pilot_runs"][0]["workflow_run_id"] == workflow_run_id
    assert second_summary["pilot_runs"][0]["reused_existing"] is True
    assert str(second_packets[0]["workflow_run"]["workflow_run_id"]) == workflow_run_id
