from __future__ import annotations

from pathlib import Path
from typing import Any

from tests.runtime.helpers.runtime_cli import REPO_ROOT
from tests.runtime.helpers.scenario_harness import RuntimeScenarioHarness

SCENARIO_PATH = (
    REPO_ROOT
    / "fixtures/scenarios/schedule_planning/stage07_drift_detected.yaml"
)


def _event_index(events: list[dict[str, Any]], event_type: str, predicate: Any) -> int:
    for index, event in enumerate(events):
        if event["event_type"] != event_type:
            continue
        if predicate(event):
            return index
    raise AssertionError(f"event index not found: {event_type}")


def test_stage07_drift_detected_is_visible_in_canonical_timeline(tmp_path: Path) -> None:
    harness = RuntimeScenarioHarness.from_yaml(SCENARIO_PATH, tmp_path).prepare()
    harness.run_steps()

    events = harness.list_events()
    drift_events = [
        event
        for event in events
        if event["event_type"] == "artifact.pointer.drift_detected"
    ]
    assert len(drift_events) == 1
    drift_event = drift_events[0]
    assert drift_event["payload"]["reviewed_artifact_version_id"] == harness.output("create_base_artifact_v1")["artifact_version"]["artifact_version_id"]
    assert drift_event["payload"]["promoted_artifact_version_id"] == harness.output("create_replan_delta")["artifact_version"]["artifact_version_id"]

    promoted_idx = _event_index(
        events,
        "artifact.pointer.promoted",
        lambda event: event["payload"]["promoted_artifact_version_id"]
        == harness.output("create_replan_delta")["artifact_version"]["artifact_version_id"],
    )
    drift_idx = _event_index(
        events,
        "artifact.pointer.drift_detected",
        lambda event: event["payload"]["promoted_artifact_version_id"]
        == harness.output("create_replan_delta")["artifact_version"]["artifact_version_id"],
    )
    assert promoted_idx < drift_idx

    pointers = harness.list_pointers()["pointers"]
    pointer_by_key = {row["pointer_key"]: row for row in pointers}
    assert pointer_by_key["official:schedule.published_schedule.workbook"]["artifact_version_id"] == harness.output("create_base_artifact_v2")["artifact_version"]["artifact_version_id"]
    assert pointer_by_key["official:schedule.replan_delta.workbook"]["artifact_version_id"] == harness.output("create_replan_delta")["artifact_version"]["artifact_version_id"]
