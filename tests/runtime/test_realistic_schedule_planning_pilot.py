from __future__ import annotations

import json
from pathlib import Path

from onetruth.application.services.realistic_schedule_planning_pilot import (
    PILOT_STAGE03_06_HUMAN_GATED,
    PILOT_STAGE06_NEEDS_INFORMATION,
    PILOT_STAGE06_PUBLISH_READY,
    PILOT_STAGE07_ISSUE_REPLAN,
    run_realistic_schedule_planning_pilot_suite,
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
        summary = run_realistic_schedule_planning_pilot_suite(
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
        "approvals": "SELECT COUNT(*) FROM approvals WHERE workflow_run_id = ?",
        "artifact_versions": "SELECT COUNT(*) FROM artifact_versions WHERE workflow_run_id = ?",
        "artifact_pointers": "SELECT COUNT(*) FROM artifact_pointers WHERE workflow_run_id = ?",
        "flags": "SELECT COUNT(*) FROM flags WHERE workflow_run_id = ?",
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


def test_pilot_seeding_is_deterministic_for_same_key(tmp_path: Path) -> None:
    run_a = tmp_path / "run-a"
    run_b = tmp_path / "run-b"
    run_a.mkdir(parents=True, exist_ok=True)
    run_b.mkdir(parents=True, exist_ok=True)

    _, _, packets_a = _run_pilot(
        run_a,
        pilot_ids=[PILOT_STAGE06_NEEDS_INFORMATION],
        pilot_key="determinism",
    )
    _, _, packets_b = _run_pilot(
        run_b,
        pilot_ids=[PILOT_STAGE06_NEEDS_INFORMATION],
        pilot_key="determinism",
    )

    packet_a = packets_a[0]
    packet_b = packets_b[0]

    seeded_artifacts_a = sorted(
        str(item["artifact_version_id"])
        for item in packet_a["artifacts"]
        if isinstance(item.get("metadata_json"), dict)
        and item["metadata_json"].get("seed_set_id") == "stage06_needs_information_example_set"
    )
    seeded_artifacts_b = sorted(
        str(item["artifact_version_id"])
        for item in packet_b["artifacts"]
        if isinstance(item.get("metadata_json"), dict)
        and item["metadata_json"].get("seed_set_id") == "stage06_needs_information_example_set"
    )

    assert seeded_artifacts_a
    assert seeded_artifacts_a == seeded_artifacts_b


def test_stage06_publish_ready_pilot_creates_expected_canonical_records(tmp_path: Path) -> None:
    db_url, _, packets = _run_pilot(
        tmp_path,
        pilot_ids=[PILOT_STAGE06_PUBLISH_READY],
        pilot_key="stage06-publish",
    )
    packet = packets[0]

    assert packet["workflow_run"]["workflow_id"] == "schedule_planning.v1"
    assert packet["execution_runtime"]["execution_sessions"]
    assert packet["execution_runtime"]["tool_executions"]
    assert packet["execution_runtime"]["policy_decisions"]

    connection = open_sqlite_connection(db_url)
    try:
        session_state = connection.execute(
            "SELECT state FROM execution_sessions"
        ).fetchone()
        tool_state = connection.execute(
            "SELECT state FROM tool_executions"
        ).fetchone()
        policy_decision = connection.execute(
            "SELECT decision FROM policy_decisions"
        ).fetchone()
        approval_state = connection.execute(
            "SELECT state FROM approvals"
        ).fetchone()
        assert session_state is not None and session_state[0] == "SUCCEEDED"
        assert tool_state is not None and tool_state[0] == "COMPLETED"
        assert policy_decision is not None and policy_decision[0] == "allow"
        assert approval_state is not None and approval_state[0] == "RESPONDED"
    finally:
        connection.close()


def test_stage06_pilot_persists_canonical_evidence_artifact(tmp_path: Path) -> None:
    db_url, _, packets = _run_pilot(
        tmp_path,
        pilot_ids=[PILOT_STAGE06_NEEDS_INFORMATION],
        pilot_key="stage06-evidence",
    )
    packet = packets[0]

    evidence = [
        artifact
        for artifact in packet["artifacts"]
        if artifact["artifact_kind"] == "schedule.stage06.review_ai_evidence.json"
    ]
    assert len(evidence) == 1

    metadata = evidence[0]["metadata_json"]
    assert metadata["execution_session_id"]
    assert metadata["tool_execution_id"]
    assert metadata["policy_decision_id"]

    connection = open_sqlite_connection(db_url)
    try:
        row = connection.execute(
            "SELECT COUNT(*) FROM artifact_versions WHERE artifact_kind = ?",
            ("schedule.stage06.review_ai_evidence.json",),
        ).fetchone()
        assert row is not None
        assert int(row[0]) == 1
    finally:
        connection.close()


def test_stage03_to_stage06_human_gated_pilot_leaves_document_and_signoff_gates_open(
    tmp_path: Path,
) -> None:
    db_url, _, packets = _run_pilot(
        tmp_path,
        pilot_ids=[PILOT_STAGE03_06_HUMAN_GATED],
        pilot_key="stage03-06-human-gated",
    )
    packet = packets[0]
    workflow_run_id = str(packet["workflow_run"]["workflow_run_id"])

    connection = open_sqlite_connection(db_url)
    try:
        stage05 = connection.execute(
            """
            SELECT ht.human_task_id, ht.state, ht.assignee_actor_id
            FROM human_tasks ht
            JOIN task_runs tr
              ON tr.task_run_id = ht.task_run_id
            WHERE ht.workflow_run_id = ?
              AND tr.stage_id = 'Stage05'
              AND tr.task_kind = 'information_request'
            """,
            (workflow_run_id,),
        ).fetchone()
        assert stage05 is not None
        assert str(stage05["state"]) == "CLAIMED"
        assert str(stage05["assignee_actor_id"]) == "human:schedule-planner-pilot"

        stage05_upload = connection.execute(
            """
            SELECT COUNT(*)
            FROM artifact_links al
            JOIN artifact_versions av
              ON av.artifact_version_id = al.artifact_version_id
            WHERE al.workflow_run_id = ?
              AND al.subject_kind = 'human_task'
              AND al.subject_id = ?
              AND av.artifact_kind = 'schedule.draft_schedule.workbook'
            """,
            (workflow_run_id, str(stage05["human_task_id"])),
        ).fetchone()
        assert stage05_upload is not None
        assert int(stage05_upload[0]) == 0

        stage06_final_review = connection.execute(
            """
            SELECT ht.state, ht.assignee_actor_id
            FROM human_tasks ht
            JOIN task_runs tr
              ON tr.task_run_id = ht.task_run_id
            WHERE ht.workflow_run_id = ?
              AND tr.stage_id = 'Stage06'
              AND tr.task_kind = 'final_review'
            """,
            (workflow_run_id,),
        ).fetchone()
        assert stage06_final_review is not None
        assert str(stage06_final_review["state"]) == "CLAIMED"
        assert str(stage06_final_review["assignee_actor_id"]) == "human:dispatch-supervisor-pilot"

        stage06_pending_approval = connection.execute(
            """
            SELECT COUNT(*)
            FROM approvals
            WHERE workflow_run_id = ?
              AND scope_ref = 'Stage06'
              AND state = 'PENDING'
            """,
            (workflow_run_id,),
        ).fetchone()
        assert stage06_pending_approval is not None
        assert int(stage06_pending_approval[0]) == 1

        stage04_responded_approval = connection.execute(
            """
            SELECT COUNT(*)
            FROM approvals
            WHERE workflow_run_id = ?
              AND scope_ref = 'Stage04'
              AND state = 'RESPONDED'
            """,
            (workflow_run_id,),
        ).fetchone()
        assert stage04_responded_approval is not None
        assert int(stage04_responded_approval[0]) == 1
    finally:
        connection.close()


def test_inspection_packet_contains_expected_references_and_routes(tmp_path: Path) -> None:
    _, _, packets = _run_pilot(
        tmp_path,
        pilot_ids=[PILOT_STAGE06_PUBLISH_READY],
        pilot_key="packet-routes",
    )
    packet = packets[0]
    workflow_run_id = packet["workflow_run"]["workflow_run_id"]

    assert packet["linked_ids"]["artifact_version_ids"]
    assert packet["linked_ids"]["execution_session_ids"]
    assert packet["linked_ids"]["tool_execution_ids"]
    assert packet["linked_ids"]["policy_decision_ids"]

    ui_routes = packet["inspection"]["ui_routes"]
    api_routes = packet["inspection"]["api_routes"]
    assert f"/runs/{workflow_run_id}" in ui_routes
    assert f"/api/v1/workflow-runs/{workflow_run_id}" in api_routes
    assert f"/api/v1/timeline-events?workflow_run_id={workflow_run_id}" in api_routes

    event_types = {
        event["event_type"]
        for event in packet["timeline"]["events_of_interest"]
    }
    assert "execution.session.created" in event_types
    assert "tool.execution.requested" in event_types
    assert "tool.execution.completed" in event_types


def test_stage07_pilot_yields_coherent_flags_artifacts_and_pointers(tmp_path: Path) -> None:
    _, _, packets = _run_pilot(
        tmp_path,
        pilot_ids=[PILOT_STAGE07_ISSUE_REPLAN],
        pilot_key="stage07-coherence",
    )
    packet = packets[0]

    pointer_keys = {pointer["pointer_key"] for pointer in packet["pointers"]}
    assert "official:schedule.published_schedule.workbook" in pointer_keys
    assert "official:schedule.replan_delta.workbook" in pointer_keys

    assert any(flag["state"] == "resolved" for flag in packet["flags"])
    assert any(approval["state"] == "RESPONDED" for approval in packet["approvals"])
    assert any(
        artifact["artifact_kind"] == "schedule.replan_delta.workbook"
        and artifact.get("supersedes_artifact_version_id")
        for artifact in packet["artifacts"]
    )

    event_types = {
        event["event_type"] for event in packet["timeline"]["events_of_interest"]
    }
    assert "flag.created" in event_types
    assert "flag.state_changed" in event_types
    assert "artifact.pointer.promoted" in event_types


def test_repeat_pilot_run_with_same_key_does_not_duplicate_canonical_effects(tmp_path: Path) -> None:
    db_url, first_summary, first_packets = _run_pilot(
        tmp_path,
        pilot_ids=[PILOT_STAGE06_PUBLISH_READY],
        pilot_key="repeat-safe",
    )
    workflow_run_id = str(first_packets[0]["workflow_run"]["workflow_run_id"])
    before = _count_by_workflow_run_id(db_url, workflow_run_id)

    _, second_summary, second_packets = _run_pilot(
        tmp_path,
        pilot_ids=[PILOT_STAGE06_PUBLISH_READY],
        pilot_key="repeat-safe",
    )
    after = _count_by_workflow_run_id(db_url, workflow_run_id)

    assert before == after
    assert first_summary["pilot_runs"][0]["workflow_run_id"] == workflow_run_id
    assert second_summary["pilot_runs"][0]["reused_existing"] is True
    assert str(second_packets[0]["workflow_run"]["workflow_run_id"]) == workflow_run_id
