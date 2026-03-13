from __future__ import annotations

from pathlib import Path

from tests.runtime.helpers.scenario_harness import RuntimeScenarioHarness
from tests.runtime.helpers.runtime_cli import REPO_ROOT

PUBLISH_SCENARIO_PATH = (
    REPO_ROOT
    / "fixtures/scenarios/schedule_planning/stage06_publish_happy.yaml"
)
INFO_SCENARIO_PATH = (
    REPO_ROOT
    / "fixtures/scenarios/schedule_planning/stage06_review_requires_more_information.yaml"
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
    "pointer_id",
    "workflow_run_id",
    "pointer_key",
    "tenant_id",
    "domain_id",
    "dataset_key",
    "partition_kind",
    "partition_key",
    "stream_key",
    "registry_kind",
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


def test_hitl_query_contract_shapes_stage06_publish_scenario(tmp_path: Path) -> None:
    harness = RuntimeScenarioHarness.from_yaml(PUBLISH_SCENARIO_PATH, tmp_path).prepare()
    harness.run_steps()

    tasks = harness.list_tasks()["tasks"]
    approvals = harness.list_approvals()["approvals"]
    pointers = harness.list_pointers()["pointers"]
    workflow_runs = harness.list_workflow_runs()["workflow_runs"]

    _assert_row_shape(tasks, EXPECTED_TASK_KEYS)
    _assert_row_shape(approvals, EXPECTED_APPROVAL_KEYS)
    _assert_row_shape(pointers, EXPECTED_POINTER_KEYS)
    _assert_row_shape(workflow_runs, EXPECTED_WORKFLOW_KEYS)

    assert any(row["workflow_run_id"] == harness.workflow_run_id for row in tasks)
    assert approvals[0]["state"] == "RESPONDED"
    assert approvals[0]["response_kind"] == "approve"
    assert pointers[0]["pointer_key"] == "official:schedule.published_schedule.workbook"
    assert pointers[0]["artifact_version_id"] == harness.output("create_published_artifact")["artifact_version"]["artifact_version_id"]
    assert any(row["workflow_run_id"] == harness.workflow_run_id for row in workflow_runs)


def test_hitl_query_contract_task_queue_snapshot_stage06_info_request_scenario(
    tmp_path: Path,
) -> None:
    harness = RuntimeScenarioHarness.from_yaml(INFO_SCENARIO_PATH, tmp_path).prepare()
    harness.run_steps()

    tasks = harness.list_tasks()["tasks"]
    _assert_row_shape(tasks, EXPECTED_TASK_KEYS)

    snapshot = [
        (row["stage_id"], row["task_kind"], row["state"])
        for row in sorted(tasks, key=lambda row: str(row["task_kind"]))
    ]
    assert snapshot == [
        ("Stage06", "information_request", "OPEN"),
        ("Stage06", "review_packet", "COMPLETED"),
    ]
