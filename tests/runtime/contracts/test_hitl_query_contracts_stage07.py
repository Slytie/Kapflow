from __future__ import annotations

from pathlib import Path

from tests.runtime.helpers.runtime_api import RuntimeApiClient
from tests.runtime.helpers.runtime_cli import REPO_ROOT
from tests.runtime.helpers.scenario_harness import RuntimeScenarioHarness

MAJOR_SCENARIO_PATH = (
    REPO_ROOT
    / "fixtures/scenarios/schedule_planning/stage07_major_replan_happy.yaml"
)
INFO_SCENARIO_PATH = (
    REPO_ROOT
    / "fixtures/scenarios/schedule_planning/stage07_missing_information_branch.yaml"
)

EXPECTED_TASK_KEYS = {
    "human_task_id",
    "workflow_run_id",
    "task_run_id",
    "task_kind",
    "state",
    "candidate_roles",
    "owner_role",
    "assignee_actor_id",
    "assignee_actor_type",
    "due_at",
    "escalation_at",
    "lease_version",
    "claimed_at",
    "claimed_until",
    "linked_approval_id",
    "reopen_count",
    "generation",
    "created_at",
    "updated_at",
    "task_run_state",
    "stage_id",
    "blocked_on_kind",
    "blocked_on_ref",
    "spawned_from_flag_id",
}

EXPECTED_APPROVAL_KEYS = {
    "approval_id",
    "workflow_run_id",
    "task_run_id",
    "approval_kind",
    "scope_kind",
    "scope_ref",
    "state",
    "requested_by_task_run_id",
    "candidate_roles",
    "required_role",
    "requested_at",
    "responded_at",
    "response_kind",
    "response_reason",
    "decided_by_actor_id",
    "decided_by_actor_type",
    "generation",
    "created_at",
    "updated_at",
}

EXPECTED_POINTER_KEYS = {
    "workflow_run_id",
    "pointer_key",
    "scope_kind",
    "scope_ref",
    "artifact_kind",
    "artifact_version_id",
    "promotion_reason",
    "promoted_by_task_run_id",
    "approved_by_approval_id",
    "generation",
    "updated_at",
}

EXPECTED_FLAG_KEYS = {
    "flag_id",
    "workflow_run_id",
    "tenant_id",
    "domain_id",
    "workflow_id",
    "partition_key",
    "kind",
    "severity",
    "state",
    "summary",
    "details_json",
    "assigned_group",
    "created_at",
    "closed_at",
    "created_by_actor_id",
    "created_by_actor_type",
    "source_event_id",
    "dedupe_key",
    "updated_at",
}

EXPECTED_WORKFLOW_KEYS = {
    "workflow_run_id",
    "workflow_id",
    "workflow_version",
    "tenant_id",
    "domain_id",
    "partition_key",
    "logical_date",
    "activation_key",
    "state",
    "created_at",
    "updated_at",
    "active_issue_count",
}


def _assert_row_shape(rows: list[dict[str, object]], expected_keys: set[str]) -> None:
    assert rows
    for row in rows:
        assert set(row.keys()) == expected_keys


def _api_client(harness: RuntimeScenarioHarness, actor_id: str) -> RuntimeApiClient:
    return RuntimeApiClient(
        db_url=harness.db_url,
        tenant_id="tenant-a",
        domain_id="domain-x",
        actor_id=actor_id,
        actor_type="human",
        actor_roles=["operations_manager"],
    )


def test_stage07_query_contract_shapes_major_replan_scenario(tmp_path: Path) -> None:
    harness = RuntimeScenarioHarness.from_yaml(MAJOR_SCENARIO_PATH, tmp_path).prepare()
    harness.run_steps()

    tasks = harness.list_tasks()["tasks"]
    approvals = harness.list_approvals()["approvals"]
    pointers = harness.list_pointers()["pointers"]
    workflow_runs = harness.list_workflow_runs()["workflow_runs"]
    flags = harness.list_flags()["flags"]

    _assert_row_shape(tasks, EXPECTED_TASK_KEYS)
    _assert_row_shape(approvals, EXPECTED_APPROVAL_KEYS)
    _assert_row_shape(pointers, EXPECTED_POINTER_KEYS)
    _assert_row_shape(workflow_runs, EXPECTED_WORKFLOW_KEYS)
    _assert_row_shape(flags, EXPECTED_FLAG_KEYS)

    assert any(row["task_kind"] == "exception_triage" for row in tasks)
    assert any(row["task_kind"] == "final_review" for row in tasks)
    assert approvals[0]["state"] == "RESPONDED"
    assert approvals[0]["response_kind"] == "approve"
    assert any(row["pointer_key"] == "official:schedule.replan_delta.workbook" for row in pointers)
    run_row = next(row for row in workflow_runs if row["workflow_run_id"] == harness.workflow_run_id)
    assert int(run_row["active_issue_count"]) == 0
    assert flags[0]["state"] == "resolved"


def test_stage07_board_contract_renders_issue_cards_and_lanes(tmp_path: Path) -> None:
    harness = RuntimeScenarioHarness.from_yaml(INFO_SCENARIO_PATH, tmp_path).prepare()
    harness.run_steps()

    client = _api_client(harness, "human:ops-manager-2")
    response = client.get(
        "/api/v1/board/schedule-planning",
        query={"workflow_run_id": harness.workflow_run_id},
    )
    assert response.status_code == 200
    payload = response.payload
    assert payload["status"] == "ok"
    assert payload["command"] == "api.board.schedule_planning"

    board = payload["board"]
    cards = board["cards"]
    human_cards = [card for card in cards if card["card_type"] == "human_task"]
    assert len(human_cards) == 2
    assert all(card["stage_id"] == "Stage07" for card in human_cards)
    assert any(card["task_kind"] == "information_request" and card["lane"] == "human_tasks.open" for card in human_cards)
    assert any(card["task_kind"] == "exception_triage" and card["lane"] == "human_tasks.completed" for card in human_cards)
    assert all("spawned_from_flag_id" in card for card in human_cards)

    workflow_runs = board["workflow_runs"]
    assert workflow_runs
    run_row = next(row for row in workflow_runs if row["workflow_run_id"] == harness.workflow_run_id)
    assert int(run_row["active_issue_count"]) == 1
