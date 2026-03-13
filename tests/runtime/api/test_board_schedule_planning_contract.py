"""Legacy schedule-only board contract coverage.

This suite preserves the secondary regression surface without re-centering product posture
away from `/demo/logistics`.
"""

from __future__ import annotations

from pathlib import Path

from tests.runtime.helpers.runtime_api import RuntimeApiClient
from tests.runtime.helpers.runtime_cli import REPO_ROOT
from tests.runtime.helpers.scenario_harness import RuntimeScenarioHarness

INFO_SCENARIO_PATH = (
    REPO_ROOT / "fixtures/scenarios/schedule_planning/stage06_review_requires_more_information.yaml"
)
STAGE07_SCENARIO_PATH = (
    REPO_ROOT / "fixtures/scenarios/schedule_planning/stage07_missing_information_branch.yaml"
)

EXPECTED_LANES = [
    "flags.open",
    "human_tasks.open",
    "human_tasks.claimed",
    "approvals.pending",
    "approvals.responded",
    "human_tasks.completed",
    "flags.resolved",
    "flags.closed",
]

REQUIRED_HUMAN_CARD_KEYS = {
    "card_id",
    "card_type",
    "lane",
    "title",
    "workflow_run_id",
    "workflow_id",
    "task_run_id",
    "human_task_id",
    "stage_id",
    "task_kind",
    "state",
    "owner_role",
    "assignee_actor_id",
    "assignee_actor_type",
    "due_at",
    "claimed_at",
    "claimed_until",
    "blocked_on_kind",
    "blocked_on_ref",
    "spawned_from_flag_id",
    "linked_approval_count",
    "linked_approval_states",
}

REQUIRED_FLAG_CARD_KEYS = {
    "card_id",
    "card_type",
    "lane",
    "title",
    "workflow_run_id",
    "workflow_id",
    "flag_id",
    "kind",
    "severity",
    "state",
    "summary",
    "assigned_group",
    "created_at",
    "closed_at",
    "linked_task_count",
    "linked_open_task_count",
}


def _api_client(harness: RuntimeScenarioHarness) -> RuntimeApiClient:
    return RuntimeApiClient(
        db_url=harness.db_url,
        tenant_id="tenant-a",
        domain_id="domain-x",
        actor_id="human:dispatch-supervisor-2",
        actor_type="human",
        actor_roles=["dispatch_supervisor"],
    )


def test_schedule_planning_board_contract_and_child_task_lane_mapping(tmp_path: Path) -> None:
    harness = RuntimeScenarioHarness.from_yaml(INFO_SCENARIO_PATH, tmp_path).prepare()
    harness.run_steps()

    client = _api_client(harness)
    result = client.get(
        "/api/v1/board/schedule-planning",
        query={"workflow_run_id": harness.workflow_run_id},
    )
    assert result.status_code == 200

    payload = result.payload
    assert payload["status"] == "ok"
    assert payload["command"] == "api.board.schedule_planning"

    board = payload["board"]
    lane_names = [lane["lane"] for lane in board["lanes"]]
    assert lane_names == EXPECTED_LANES
    lane_counts = {lane["lane"]: lane["card_count"] for lane in board["lanes"]}
    assert lane_counts["flags.open"] == 0
    assert lane_counts["flags.resolved"] == 0
    assert lane_counts["flags.closed"] == 0

    cards = board["cards"]
    human_cards = [card for card in cards if card["card_type"] == "human_task"]
    assert len(human_cards) == 2
    for card in human_cards:
        assert REQUIRED_HUMAN_CARD_KEYS.issubset(set(card.keys()))

    info_request_cards = [
        card
        for card in human_cards
        if card["task_kind"] == "information_request" and card["state"] == "OPEN"
    ]
    assert len(info_request_cards) == 1
    assert info_request_cards[0]["lane"] == "human_tasks.open"
    assert info_request_cards[0]["stage_id"] == "Stage06"

    completed_review_cards = [
        card
        for card in human_cards
        if card["task_kind"] == "review_packet" and card["state"] == "COMPLETED"
    ]
    assert len(completed_review_cards) == 1
    assert completed_review_cards[0]["lane"] == "human_tasks.completed"


def test_schedule_planning_board_includes_exception_cards_for_stage07(tmp_path: Path) -> None:
    harness = RuntimeScenarioHarness.from_yaml(STAGE07_SCENARIO_PATH, tmp_path).prepare()
    harness.run_steps()

    client = _api_client(harness)
    result = client.get(
        "/api/v1/board/schedule-planning",
        query={"workflow_run_id": harness.workflow_run_id},
    )
    assert result.status_code == 200
    board = result.payload["board"]

    cards = board["cards"]
    flag_cards = [card for card in cards if card["card_type"] == "flag"]
    human_cards = [card for card in cards if card["card_type"] == "human_task"]

    assert len(flag_cards) == 1
    assert REQUIRED_FLAG_CARD_KEYS.issubset(set(flag_cards[0].keys()))
    assert flag_cards[0]["lane"] == "flags.open"
    assert flag_cards[0]["kind"] == "vehicle_issue"
    assert flag_cards[0]["state"] == "open"
    assert flag_cards[0]["linked_open_task_count"] >= 1

    info_request_cards = [
        card
        for card in human_cards
        if card["task_kind"] == "information_request" and card["state"] == "OPEN"
    ]
    assert len(info_request_cards) == 1
    assert info_request_cards[0]["lane"] == "human_tasks.open"
