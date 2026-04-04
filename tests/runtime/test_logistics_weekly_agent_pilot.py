from __future__ import annotations

from collections import Counter
import json
import os
from pathlib import Path
from urllib.parse import urlparse

from onetruth.application.services.logistics_weekly_agent_pilot import (
    PILOT_DEFINITIONS,
    PILOT_WEEKLY_STAGE04_AGENT,
    PILOT_WEEKLY_STAGE04_ACTUAL_OPS_LAB,
    PILOT_WEEKLY_STAGE04_ACTUAL_OPS_LAB_V4,
    PILOT_WEEKLY_STAGE04_REALISTIC_ARTIFACTS,
    _ensure_workflow_run,
    _run_weekly_stage04_agent_pilot,
    describe_weekly_stage04_pilot_fixture_profile,
    resolve_weekly_stage04_pilot_ids,
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


def _artifact_rows_for_kind(
    db_url: str,
    workflow_run_id: str,
    artifact_kind: str,
) -> list[dict[str, object]]:
    connection = open_sqlite_connection(db_url)
    try:
        rows = connection.execute(
            """
            SELECT artifact_kind, metadata_json, storage_uri
            FROM artifact_versions
            WHERE workflow_run_id = ?
              AND artifact_kind = ?
            ORDER BY created_at ASC, artifact_version_id ASC
            """,
            (workflow_run_id, artifact_kind),
        ).fetchall()
        return [dict(row) for row in rows]
    finally:
        connection.close()


def _load_artifact_payload(row: dict[str, object]) -> dict[str, object]:
    storage_uri = str(row["storage_uri"])
    parsed_uri = urlparse(storage_uri)
    if parsed_uri.scheme in {"", "file"}:
        payload_path = Path(parsed_uri.path if parsed_uri.scheme == "file" else storage_uri)
        if payload_path.exists():
            return json.loads(payload_path.read_text(encoding="utf-8"))
    metadata = row.get("metadata_json")
    if isinstance(metadata, dict):
        return metadata
    if isinstance(metadata, str):
        return json.loads(metadata)
    raise FileNotFoundError(f"artifact payload is unavailable for storage_uri={storage_uri}")


def _payload_size_bytes(payload: dict[str, object]) -> int:
    return len(json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8"))


def _contains_key(value: object, target_key: str) -> bool:
    if isinstance(value, dict):
        if target_key in value:
            return True
        return any(_contains_key(item, target_key) for item in value.values())
    if isinstance(value, list):
        return any(_contains_key(item, target_key) for item in value)
    return False


def _driver_shift_distribution(
    *,
    candidate_delta: dict[str, object],
    input_bundle: dict[str, object],
) -> tuple[Counter[str], dict[str, dict[str, object]], list[str]]:
    columns = [str(column) for column in candidate_delta["columns"]]
    shift_counter: Counter[str] = Counter()
    for row in candidate_delta["rows"]:
        normalized = dict(zip(columns, row))
        driver_id = str(normalized.get("assigned_driver_id") or "")
        if driver_id:
            shift_counter[driver_id] += 1
    for row in candidate_delta.get("reserve_rows") or []:
        driver_id = str(row.get("assigned_driver_id") or row.get("candidate_driver_id") or "")
        if driver_id:
            shift_counter[driver_id] += 1

    profiles = {
        str(profile["driver_id"]): dict(profile)
        for profile in input_bundle["bundle"]["driver_profiles"]
    }
    zero_shift_driver_ids = sorted(set(profiles) - set(shift_counter))
    return shift_counter, profiles, zero_shift_driver_ids


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
    assert packet["stage04_analysis"]["iterations"]
    assert packet["stage04_analysis"]["runtime_turns"]
    assert packet["stage04_analysis"]["tradeoffs"] == []


def test_weekly_stage04_pilot_selection_defaults_real_to_realistic() -> None:
    assert resolve_weekly_stage04_pilot_ids(None, openai_mode="mock") == (
        PILOT_WEEKLY_STAGE04_AGENT,
        PILOT_WEEKLY_STAGE04_REALISTIC_ARTIFACTS,
    )
    assert resolve_weekly_stage04_pilot_ids(None, openai_mode="real") == (
        PILOT_WEEKLY_STAGE04_REALISTIC_ARTIFACTS,
    )
    assert resolve_weekly_stage04_pilot_ids(["all"], openai_mode="real") == (
        PILOT_WEEKLY_STAGE04_AGENT,
        PILOT_WEEKLY_STAGE04_REALISTIC_ARTIFACTS,
        PILOT_WEEKLY_STAGE04_ACTUAL_OPS_LAB,
        PILOT_WEEKLY_STAGE04_ACTUAL_OPS_LAB_V4,
    )
    assert resolve_weekly_stage04_pilot_ids(
        [PILOT_WEEKLY_STAGE04_AGENT],
        openai_mode="real",
    ) == (PILOT_WEEKLY_STAGE04_AGENT,)
    assert resolve_weekly_stage04_pilot_ids(
        [PILOT_WEEKLY_STAGE04_ACTUAL_OPS_LAB],
        openai_mode="mock",
    ) == (PILOT_WEEKLY_STAGE04_ACTUAL_OPS_LAB,)

def test_weekly_stage04_fixture_profiles_cover_tiny_realistic_and_actual_ops() -> None:
    realistic = describe_weekly_stage04_pilot_fixture_profile(
        PILOT_WEEKLY_STAGE04_REALISTIC_ARTIFACTS
    )
    actual_ops = describe_weekly_stage04_pilot_fixture_profile(
        PILOT_WEEKLY_STAGE04_ACTUAL_OPS_LAB
    )
    actual_ops_v4 = describe_weekly_stage04_pilot_fixture_profile(
        PILOT_WEEKLY_STAGE04_ACTUAL_OPS_LAB_V4
    )
    tiny = describe_weekly_stage04_pilot_fixture_profile(PILOT_WEEKLY_STAGE04_AGENT)

    assert realistic["planning_week_id"] == "PW-2026-W12"
    assert realistic["route_slot_count"] == 139
    assert realistic["driver_count"] == 40
    assert realistic["has_daily_availability_states"] is True
    assert realistic["has_previous_week_history"] is True

    assert actual_ops["planning_week_id"] == "PW-2026-W13"
    assert actual_ops["route_slot_count"] == 134
    assert actual_ops["driver_count"] == 51
    assert actual_ops["has_daily_availability_states"] is True
    assert actual_ops["has_previous_week_history"] is True
    assert actual_ops["fixture_contract"] == "weekly_stage04_actual_ops_lab_v3"

    assert actual_ops_v4["planning_week_id"] == "PW-2026-W13"
    assert actual_ops_v4["route_slot_count"] == 134
    assert actual_ops_v4["driver_count"] == 51
    assert actual_ops_v4["has_daily_availability_states"] is True
    assert actual_ops_v4["has_previous_week_history"] is True
    assert actual_ops_v4["fixture_contract"] == "weekly_stage04_actual_ops_lab_v4"

    assert tiny["planning_week_id"] == "PW-2026-W10"
    assert tiny["route_slot_count"] == 2
    assert tiny["driver_count"] == 2
    assert tiny["has_daily_availability_states"] is False
    assert tiny["has_previous_week_history"] is False


def test_realistic_live_stage04_pilot_scopes_gpt5mini_override(
    tmp_path: Path,
    monkeypatch,
) -> None:
    observed_calls: list[dict[str, object]] = []

    def _fake_run_weekly_stage04_openai_agent(_connection, _payload, *, runner=None):
        observed_calls.append(
            {
                "model": os.environ.get("ONETRUTH_OPENAI_MODEL"),
                "uses_mock_runner": runner is not None,
            }
        )
        return {
            "execution_session": {"execution_session_id": f"xs-{len(observed_calls)}"},
            "tool_execution": {"tool_execution_id": f"tx-{len(observed_calls)}"},
            "policy_decision": {"policy_decision_id": f"pd-{len(observed_calls)}"},
        }

    monkeypatch.setattr(
        "onetruth.application.services.logistics_weekly_agent_pilot.run_weekly_stage04_openai_agent",
        _fake_run_weekly_stage04_openai_agent,
    )
    monkeypatch.setenv("ONETRUTH_OPENAI_MODEL", "gpt-4.1-mini")

    db_path = tmp_path / "runtime.db"
    db_url = f"sqlite:///{db_path}"
    storage_root = tmp_path / "artifacts"
    connection = open_sqlite_connection(db_url)
    try:
        create_sqlite_substrate(connection)

        def _invoke(pilot_id: str, *, pilot_key: str, openai_mode: str) -> None:
            definition = PILOT_DEFINITIONS[pilot_id]
            workflow_run_id = f"wr-{pilot_key}"
            _ensure_workflow_run(
                connection,
                definition=definition,
                workflow_run_id=workflow_run_id,
                pilot_key=pilot_key,
            )
            _run_weekly_stage04_agent_pilot(
                connection,
                definition=definition,
                workflow_run_id=workflow_run_id,
                pilot_key=pilot_key,
                openai_mode=openai_mode,
                storage_root=storage_root,
            )

        _invoke(
            PILOT_WEEKLY_STAGE04_REALISTIC_ARTIFACTS,
            pilot_key="stage04-realistic-live-model",
            openai_mode="real",
        )
        _invoke(
            PILOT_WEEKLY_STAGE04_AGENT,
            pilot_key="stage04-baseline-live-model",
            openai_mode="real",
        )
        _invoke(
            PILOT_WEEKLY_STAGE04_REALISTIC_ARTIFACTS,
            pilot_key="stage04-realistic-mock-model",
            openai_mode="mock",
        )
    finally:
        connection.close()

    assert observed_calls == [
        {"model": "gpt-5-mini", "uses_mock_runner": False},
        {"model": "gpt-4.1-mini", "uses_mock_runner": False},
        {"model": "gpt-4.1-mini", "uses_mock_runner": True},
    ]
    assert os.environ["ONETRUTH_OPENAI_MODEL"] == "gpt-4.1-mini"


def test_realistic_weekly_stage04_pilot_compacts_model_payloads_and_keeps_full_evidence(
    tmp_path: Path,
) -> None:
    db_url, summary, packets = _run_pilot(
        tmp_path,
        pilot_ids=[PILOT_WEEKLY_STAGE04_REALISTIC_ARTIFACTS],
        pilot_key="weekly-stage04-realistic-compact-payloads",
    )
    workflow_run_id = str(packets[0]["workflow_run"]["workflow_run_id"])
    assert summary["openai_mode"] == "mock"

    request_rows = _artifact_rows_for_kind(
        db_url,
        workflow_run_id,
        "runtime.tool_request.json",
    )
    result_rows = _artifact_rows_for_kind(
        db_url,
        workflow_run_id,
        "runtime.tool_result.json",
    )
    assert len(request_rows) == len(result_rows)
    assert len(request_rows) >= 10

    parsed_requests = [_load_artifact_payload(row) for row in request_rows]
    parsed_results = [_load_artifact_payload(row) for row in result_rows]

    post_turn_one_requests = [
        payload for payload in parsed_requests if int(payload.get("turn_index") or 0) > 1
    ]
    assert post_turn_one_requests
    assert max(_payload_size_bytes(payload["request_payload"]) for payload in post_turn_one_requests) < 10_000

    for payload in post_turn_one_requests:
        for item in payload["request_payload"]["input"]:
            if str(item.get("type") or "") != "function_call_output":
                continue
            output_payload = json.loads(str(item.get("output") or "{}"))
            assert not _contains_key(output_payload, "new_agreement_rows")
            assert not _contains_key(output_payload, "new_agreement_driver_ids")
            assert not _contains_key(output_payload, "new_agreement_by_service_date")
            assert not _contains_key(output_payload, "route_allocations")
            assert not _contains_key(output_payload, "remaining_route_slot_ids")
            assert not _contains_key(output_payload, "selected_candidates")

    apply_result = next(
        payload
        for payload in parsed_results
        if any(call["name"] == "apply_stage04_next_iteration" for call in payload["function_calls"])
    )
    apply_call = next(call for call in apply_result["function_calls"] if call["name"] == "apply_stage04_next_iteration")
    assert _contains_key(apply_call["output"], "route_allocations")
    assert not _contains_key(apply_call["model_output"], "route_allocations")
    assert _contains_key(apply_call["output"], "remaining_route_slot_ids")
    assert not _contains_key(apply_call["model_output"], "remaining_route_slot_ids")

    finalize_result = next(
        payload
        for payload in parsed_results
        if any(call["name"] == "finalize_weekly_stage04_draft_outputs" for call in payload["function_calls"])
    )
    finalize_call = next(
        call
        for call in finalize_result["function_calls"]
        if call["name"] == "finalize_weekly_stage04_draft_outputs"
    )
    assert _contains_key(finalize_call["output"], "new_agreement_rows")
    assert not _contains_key(finalize_call["model_output"], "new_agreement_rows")
    assert not _contains_key(finalize_call["model_output"], "new_agreement_driver_ids")
    assert not _contains_key(finalize_call["model_output"], "new_agreement_by_service_date")
    assert _contains_key(finalize_call["output"], "selected_candidates")
    assert not _contains_key(finalize_call["model_output"], "selected_candidates")


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


def test_realistic_weekly_stage04_pilot_seeds_shared_realistic_fixture_shape(tmp_path: Path) -> None:
    db_url, summary, packets = _run_pilot(
        tmp_path,
        pilot_ids=[PILOT_WEEKLY_STAGE04_REALISTIC_ARTIFACTS],
        pilot_key="weekly-stage04-realistic",
    )
    packet = packets[0]
    workflow_run_id = str(packet["workflow_run"]["workflow_run_id"])

    assert summary["openai_mode"] == "mock"
    assert packet["stage_focus"] == "Stage04"
    assert packet["quality_signals"]["stage04_output_artifacts_present"] is True
    assert packet["workflow_run"]["partition_key"] == "PW-2026-W12"

    connection = open_sqlite_connection(db_url)
    try:
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
        output_rows = connection.execute(
            """
            SELECT artifact_kind, metadata_json
            FROM artifact_versions
            WHERE workflow_run_id = ?
              AND artifact_kind IN (
                'planning.candidate_schedule_delta.workbook',
                'planning.validation_summary.doc'
              )
            ORDER BY artifact_kind ASC
            """,
            (workflow_run_id,),
        ).fetchall()
    finally:
        connection.close()

    metadata_by_kind = {
        str(row["artifact_kind"]): json.loads(str(row["metadata_json"]))
        for row in rows
    }
    output_metadata_by_kind = {
        str(row["artifact_kind"]): json.loads(str(row["metadata_json"]))
        for row in output_rows
    }
    route_slots = metadata_by_kind["planning.route_slot_requirements.workbook"]
    driver_capabilities = metadata_by_kind["planning.driver_capabilities.workbook"]
    availability = metadata_by_kind["planning.approved_availability.workbook"]
    actual_hours = metadata_by_kind["planning.actual_hours_snapshot.workbook"]
    candidate_delta = output_metadata_by_kind["planning.candidate_schedule_delta.workbook"]
    validation_summary = output_metadata_by_kind["planning.validation_summary.doc"]["summary"]

    assert len(driver_capabilities["rows"]) == 40
    assert len(availability["rows"]) == 280
    assert sum(int(item[1]) for item in route_slots["daily_demand_rows"]) == 139
    assert sum(int(item[1]) for item in route_slots["daily_demand_rows"]) < (40 * 4)
    assert len(actual_hours["rows"]) == 280
    assert "route_family" in route_slots["columns"]
    assert "seniority_rank" in driver_capabilities["columns"]
    assert "attendance_reliability_index" in driver_capabilities["columns"]
    assert "previous_week_state" in availability["columns"]
    assert "rolling_7_total_minutes" in actual_hours["columns"]
    assert len(candidate_delta["iteration_deltas"]) >= 10
    assert candidate_delta["coverage_summary"]["phase_counts"]["improvement"] >= 1
    assert candidate_delta["coverage_summary"]["reallocation_move_count"] >= 1
    assert validation_summary["coverage_summary"]["assigned_route_slots"] == 135
    assert validation_summary["coverage_summary"]["uncovered_route_slots"] == 4
    assert validation_summary["coverage_summary"]["reallocation_move_count"] >= 1
    assert validation_summary["hard_rule_result"] == "fail"
    assert validation_summary["soft_score_totals"]["previous_week_stability"] > 0.0
    stage04_analysis = packet["stage04_analysis"]
    assert len(stage04_analysis["iterations"]) >= 10
    assert stage04_analysis["runtime_turns"]
    assert stage04_analysis["tradeoffs"]
    assert stage04_analysis["phase_counts"]["improvement"] >= 1
    assert any(item["phase"] == "improvement" for item in stage04_analysis["iterations"])
    final_iteration = stage04_analysis["iterations"][-1]
    assert final_iteration["route_allocations"]
    assert final_iteration["phase"] == "improvement"
    assert final_iteration["moved_route_slot_ids"]
    assert final_iteration["soft_objective_delta"] > 0.0


def test_actual_ops_weekly_stage04_pilot_exports_expected_output_kinds_and_full_coverage(
    tmp_path: Path,
) -> None:
    db_url, summary, packets = _run_pilot(
        tmp_path,
        pilot_ids=[PILOT_WEEKLY_STAGE04_ACTUAL_OPS_LAB],
        pilot_key="weekly-stage04-actual-ops",
    )
    packet = packets[0]
    workflow_run_id = str(packet["workflow_run"]["workflow_run_id"])

    assert summary["openai_mode"] == "mock"
    assert packet["workflow_run"]["partition_key"] == "PW-2026-W13"
    assert packet["quality_signals"]["stage04_output_artifacts_present"] is True
    assert packet["quality_signals"]["no_pointer_promotions"] is True
    output_artifacts = packet["canonical_evidence"]["stage04_output_artifacts_by_kind"]
    assert set(output_artifacts) == {
        "planning.candidate_schedule_delta.workbook",
        "planning.draft_weekly_schedule.doc",
        "planning.draft_weekly_schedule.workbook",
        "planning.input_bundle.doc",
        "planning.validation_summary.doc",
    }
    for ids in output_artifacts.values():
        assert ids
    assert packet["stage04_analysis"]["coverage_summary"]["assigned_route_slots"] == 134
    assert packet["stage04_analysis"]["coverage_summary"]["uncovered_route_slots"] == 0
    assert 14 <= packet["stage04_analysis"]["excess_capacity_summary"][
        "selected_excess_capacity_total"
    ] <= 35
    assert len(
        packet["stage04_analysis"]["contract_change_summary"]["new_agreement_rows"]
    ) == packet["stage04_analysis"]["contract_change_summary"]["new_agreement_required_count"]
    assert packet["stage04_analysis"]["iterations"]

    candidate_delta = _load_artifact_payload(
        _artifact_rows_for_kind(
            db_url,
            workflow_run_id,
            "planning.candidate_schedule_delta.workbook",
        )[0]
    )
    input_bundle = _load_artifact_payload(
        _artifact_rows_for_kind(
            db_url,
            workflow_run_id,
            "planning.input_bundle.doc",
        )[0]
    )
    validation_summary = _load_artifact_payload(
        _artifact_rows_for_kind(
            db_url,
            workflow_run_id,
            "planning.validation_summary.doc",
        )[0]
    )["summary"]
    draft_doc = _load_artifact_payload(
        _artifact_rows_for_kind(
            db_url,
            workflow_run_id,
            "planning.draft_weekly_schedule.doc",
        )[0]
    )
    new_agreement_idx = candidate_delta["columns"].index("new_agreement_required")
    shift_counter, profiles, zero_shift_driver_ids = _driver_shift_distribution(
        candidate_delta=candidate_delta,
        input_bundle=input_bundle,
    )
    drivers_below_three = {
        driver_id: count for driver_id, count in shift_counter.items() if count < 3
    }

    assert "baseline_template_state" in candidate_delta["columns"]
    assert candidate_delta["coverage_summary"]["assigned_route_slots"] == 134
    assert 21 <= validation_summary["reserve_summary"]["target_on_call_total"] <= 35
    assert 21 <= validation_summary["reserve_summary"]["selected_on_call_total"] <= 35
    assert all(
        0 <= count <= 5
        for count in validation_summary["reserve_summary"]["selected_on_call_by_service_date"].values()
    )
    assert all(
        0 <= count <= 5
        for count in validation_summary["reserve_summary"]["on_call_target_by_service_date"].values()
    )
    assert 14 <= validation_summary["excess_capacity_summary"]["target_excess_capacity_total"] <= 35
    assert 14 <= validation_summary["excess_capacity_summary"]["selected_excess_capacity_total"] <= 35
    assert all(
        0 <= count <= 5
        for count in validation_summary["excess_capacity_summary"][
            "selected_excess_capacity_by_service_date"
        ].values()
    )
    assert all(
        0 <= count <= 5
        for count in validation_summary["excess_capacity_summary"][
            "excess_capacity_target_by_service_date"
        ].values()
    )
    assert any(
        key.endswith("_to_on_call")
        for key in validation_summary["new_agreement_transition_counts"]
    )
    route_new_agreement_count = sum(
        1 for row in candidate_delta["rows"] if bool(row[new_agreement_idx])
    )
    reserve_new_agreement_count = sum(
        1 for row in candidate_delta.get("reserve_rows") or [] if bool(row.get("new_agreement_required"))
    )
    assert (
        route_new_agreement_count + reserve_new_agreement_count
        == validation_summary["new_agreement_required_count"]
    )
    assert len(candidate_delta["iteration_deltas"]) == len(packet["stage04_analysis"]["iterations"])
    assert draft_doc["summary"]["new_agreement_required_count"] == validation_summary[
        "new_agreement_required_count"
    ]
    assert (
        draft_doc["summary"]["selected_excess_capacity_count"]
        == validation_summary["excess_capacity_summary"]["selected_excess_capacity_total"]
    )
    assert zero_shift_driver_ids == []
    assert max(shift_counter.values(), default=0) <= 5
    assert all(
        (
            int(profiles[driver_id]["policy_signal"]["source_target_shifts_per_week"] or 0) < 3
            or int(profiles[driver_id]["policy_signal"]["max_shifts_per_week"] or 0) <= 2
            or int(profiles[driver_id]["policy_signal"]["max_minutes_rolling7"] or 0) <= 1200
            or sum(
                1
                for state in profiles[driver_id]["daily_states"]
                if str(state.get("normalized_state") or "") in {"available", "emergency_only"}
            ) < 3
        )
        for driver_id in drivers_below_three
    )


def test_actual_ops_v4_weekly_stage04_pilot_corrects_low_shift_driver_inputs(
    tmp_path: Path,
) -> None:
    db_url, summary, packets = _run_pilot(
        tmp_path,
        pilot_ids=[PILOT_WEEKLY_STAGE04_ACTUAL_OPS_LAB_V4],
        pilot_key="weekly-stage04-actual-ops-v4",
    )
    packet = packets[0]
    workflow_run_id = str(packet["workflow_run"]["workflow_run_id"])

    assert summary["openai_mode"] == "mock"
    assert packet["workflow_run"]["partition_key"] == "PW-2026-W13"
    assert packet["quality_signals"]["stage04_output_artifacts_present"] is True
    assert packet["quality_signals"]["no_pointer_promotions"] is True
    assert packet["stage04_analysis"]["coverage_summary"]["assigned_route_slots"] == 134
    assert packet["stage04_analysis"]["coverage_summary"]["uncovered_route_slots"] == 0

    candidate_delta = _load_artifact_payload(
        _artifact_rows_for_kind(
            db_url,
            workflow_run_id,
            "planning.candidate_schedule_delta.workbook",
        )[0]
    )
    input_bundle = _load_artifact_payload(
        _artifact_rows_for_kind(
            db_url,
            workflow_run_id,
            "planning.input_bundle.doc",
        )[0]
    )
    output_artifacts = packet["canonical_evidence"]["stage04_output_artifacts_by_kind"]
    assert set(output_artifacts) == {
        "planning.candidate_schedule_delta.workbook",
        "planning.draft_weekly_schedule.doc",
        "planning.draft_weekly_schedule.workbook",
        "planning.input_bundle.doc",
        "planning.validation_summary.doc",
    }

    shift_counter, profiles, zero_shift_driver_ids = _driver_shift_distribution(
        candidate_delta=candidate_delta,
        input_bundle=input_bundle,
    )
    corrected_driver_ids = {
        "A2GJBFCCI1VYRB",
        "A3NLLQPB0L46N9",
        "A7IT4OGI9NGQX",
        "AGOU3M5WUIHWC",
    }
    assert zero_shift_driver_ids == []
    assert min(shift_counter.values(), default=0) >= 3
    assert max(shift_counter.values(), default=0) <= 4
    for driver_id in corrected_driver_ids:
        assert int(profiles[driver_id]["policy_signal"]["source_target_shifts_per_week"] or 0) == 4
        assert int(profiles[driver_id]["policy_signal"]["max_shifts_per_week"] or 0) == 4
        assert int(profiles[driver_id]["policy_signal"]["max_minutes_rolling7"] or 0) == 2400
