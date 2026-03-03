from __future__ import annotations

from pathlib import Path

from tests.runtime.helpers.runtime_cli import REPO_ROOT
from tests.runtime.helpers.scenario_harness import RuntimeScenarioHarness

SCENARIO_PATH = (
    REPO_ROOT
    / "fixtures/scenarios/schedule_planning/stage07_missing_information_branch.yaml"
)


def test_stage07_missing_information_branch_spawns_info_request(tmp_path: Path) -> None:
    harness = RuntimeScenarioHarness.from_yaml(SCENARIO_PATH, tmp_path).prepare()
    harness.run_steps()

    complete = harness.output("complete_issue")["result"]
    spawned_children = complete["spawned_children"]
    assert len(spawned_children) == 1
    child = spawned_children[0]
    assert child["stage_id"] == "Stage07"
    assert child["task_kind"] == "information_request"
    assert child["spawn_rule_id"] == "stage07_request_issue_information"

    tasks = harness.list_tasks()["tasks"]
    snapshot = sorted((row["task_kind"], row["state"]) for row in tasks)
    assert snapshot == [
        ("exception_triage", "COMPLETED"),
        ("information_request", "OPEN"),
    ]

    child_rows = harness.query_rows(
        """
        SELECT task_run_id, spawned_from_flag_id, spawn_rule_id, spawn_cause_kind, spawn_depth
        FROM task_runs
        WHERE task_run_id = ?
        """,
        (child["task_run_id"],),
    )
    assert len(child_rows) == 1
    assert child_rows[0]["spawned_from_flag_id"] == harness.output("create_flag")["flag"]["flag_id"]
    assert child_rows[0]["spawn_rule_id"] == "stage07_request_issue_information"
    assert child_rows[0]["spawn_cause_kind"] == "task_completion"
    assert int(child_rows[0]["spawn_depth"]) == 1

    events = harness.list_events()
    assert any(event["event_type"] == "task.run.created" for event in events)
    assert not any(event["event_type"] == "artifact.pointer.promoted" for event in events)
