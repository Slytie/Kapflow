from __future__ import annotations

import pytest

from tests.helpers.reference_model import canonicalize_state, reduce_events
from tests.helpers.scenario_catalog import SCENARIO_CATALOG
from tests.helpers.trace_loader import load_trace


@pytest.mark.parametrize("scenario_id", sorted(SCENARIO_CATALOG))
def test_schedule_scenarios_reduce_to_expected_state(scenario_id: str) -> None:
    scenario = SCENARIO_CATALOG[scenario_id]
    state = reduce_events(load_trace(scenario.trace_name))

    for run_id, expected_state in scenario.expected_workflow_states.items():
        assert state["workflow_runs"][run_id]["state"] == expected_state

    for task_run_id, expected_state in scenario.expected_task_states.items():
        assert state["task_runs"][task_run_id]["state"] == expected_state

    for dataset_key, artifact_version_id in scenario.expected_pointer_targets.items():
        assert state["pointer_targets_by_dataset"][dataset_key] == artifact_version_id

    for approval_id, outcome in scenario.expected_approval_outcomes.items():
        assert state["approvals"][approval_id]["outcome"] == outcome

    for execution_session_id, expected_state in scenario.expected_execution_states.items():
        assert state["execution_sessions"][execution_session_id]["state"] == expected_state

    for tool_execution_id, expected_state in scenario.expected_tool_states.items():
        assert state["tool_executions"][tool_execution_id]["state"] == expected_state

    for component, expected_state in scenario.expected_degraded_components.items():
        assert state["degraded_components"][component] == expected_state

    if scenario.required_stage_ids:
        actual_stages = {task["stage_id"] for task in state["task_runs"].values()}
        assert set(scenario.required_stage_ids) <= actual_stages


@pytest.mark.parametrize("trace_name", sorted({s.trace_name for s in SCENARIO_CATALOG.values()}))
def test_replay_is_deterministic(trace_name: str) -> None:
    events = load_trace(trace_name)
    assert canonicalize_state(reduce_events(events)) == canonicalize_state(reduce_events(events))
