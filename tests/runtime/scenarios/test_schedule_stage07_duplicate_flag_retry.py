from __future__ import annotations

from pathlib import Path

from tests.runtime.helpers.runtime_cli import REPO_ROOT
from tests.runtime.helpers.scenario_harness import RuntimeScenarioHarness

SCENARIO_PATH = (
    REPO_ROOT
    / "fixtures/scenarios/schedule_planning/stage07_duplicate_flag_retry.yaml"
)


def test_stage07_activation_dedupes_duplicate_flag_retries(tmp_path: Path) -> None:
    harness = RuntimeScenarioHarness.from_yaml(SCENARIO_PATH, tmp_path).prepare()
    harness.run_steps()

    first = harness.output("activate_issue_first")["result"]
    retry = harness.output("activate_issue_retry")["result"]
    assert first["deduped"] is False
    assert retry["deduped"] is True
    assert retry["task_run"]["task_run_id"] == first["task_run"]["task_run_id"]
    assert retry["human_task"]["human_task_id"] == first["human_task"]["human_task_id"]

    tasks = harness.list_tasks()["tasks"]
    assert len(tasks) == 1
    assert tasks[0]["task_kind"] == "exception_triage"
    assert tasks[0]["state"] == "OPEN"

    events = harness.list_events()
    task_run_created = [
        event
        for event in events
        if event["event_type"] == "task.run.created"
        and event["payload"]["activation_key"] == first["task_run"]["activation_key"]
    ]
    task_created = [
        event
        for event in events
        if event["event_type"] == "task.created"
        and event["payload"]["human_task_id"] == first["human_task"]["human_task_id"]
    ]
    assert len(task_run_created) == 1
    assert len(task_created) == 1
