from __future__ import annotations

import json
import tempfile
from pathlib import Path
import re
from typing import Any

from tests.runtime.helpers.runtime_api import RuntimeApiClient
from tests.runtime.helpers.runtime_cli import REPO_ROOT
from tests.runtime.helpers.scenario_harness import RuntimeScenarioHarness

FRONTEND_SNAPSHOT_DIR = REPO_ROOT / "fixtures/frontend_contracts"

STAGE06_PUBLISH_SCENARIO = (
    REPO_ROOT / "fixtures/scenarios/schedule_planning/stage06_publish_happy.yaml"
)
STAGE06_INFO_SCENARIO = (
    REPO_ROOT
    / "fixtures/scenarios/schedule_planning/stage06_review_requires_more_information.yaml"
)
STAGE07_MAJOR_SCENARIO = (
    REPO_ROOT
    / "fixtures/scenarios/schedule_planning/stage07_major_replan_happy.yaml"
)
STAGE07_CHILD_ISSUE_SCENARIO = (
    REPO_ROOT
    / "fixtures/scenarios/schedule_planning/stage07_child_issue_branch.yaml"
)

SNAPSHOT_FILES = {
    "stage06_publish_ready_board_state": "stage06_publish_ready_board_state.json",
    "stage06_needs_information_state": "stage06_needs_information_state.json",
    "stage07_major_replan_board_state": "stage07_major_replan_board_state.json",
    "stage07_exception_branch_state": "stage07_exception_branch_state.json",
    "approval_queue_state": "approval_queue_state.json",
    "run_detail_state": "run_detail_state.json",
    "timeline_state": "timeline_state.json",
    "official_outputs_pointers_state": "official_outputs_pointers_state.json",
}

ID_FIELDS = {
    "workflow_run_id",
    "task_run_id",
    "human_task_id",
    "approval_id",
    "artifact_version_id",
    "flag_id",
    "source_event_id",
    "spawned_from_task_run_id",
    "spawned_from_flag_id",
    "spawn_cause_event_id",
    "linked_approval_id",
    "approved_by_approval_id",
    "promoted_by_task_run_id",
    "requested_by_task_run_id",
    "parent_artifact_version_id",
    "supersedes_artifact_version_id",
    "event_id",
    "storage_uri",
}

TIMESTAMP_FIELDS = {
    "created_at",
    "updated_at",
    "requested_at",
    "responded_at",
    "claimed_at",
    "claimed_until",
    "closed_at",
    "due_at",
    "escalation_at",
    "event_time",
    "occurred_at",
    "recorded_at",
}

EMBEDDED_ID_PATTERNS = {
    "workflow_run_id": re.compile(r"wr-[0-9a-fA-F-]{8,}"),
    "task_run_id": re.compile(r"tr-[0-9a-fA-F-]{8,}"),
    "human_task_id": re.compile(r"ht-[0-9a-fA-F-]{8,}"),
    "approval_id": re.compile(r"ap-[0-9a-fA-F-]{8,}"),
    "artifact_version_id": re.compile(r"av-[0-9a-fA-F-]{8,}"),
    "flag_id": re.compile(r"fl-[0-9a-fA-F-]{8,}"),
}


def export_frontend_snapshots(output_dir: Path = FRONTEND_SNAPSHOT_DIR) -> list[Path]:
    payloads = build_frontend_snapshots_payloads()
    output_dir.mkdir(parents=True, exist_ok=True)
    written: list[Path] = []
    for snapshot_key, file_name in SNAPSHOT_FILES.items():
        path = output_dir / file_name
        path.write_text(
            json.dumps(payloads[snapshot_key], indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        written.append(path)
    return written


def load_frontend_snapshots(output_dir: Path = FRONTEND_SNAPSHOT_DIR) -> dict[str, dict[str, Any]]:
    loaded: dict[str, dict[str, Any]] = {}
    for snapshot_key, file_name in SNAPSHOT_FILES.items():
        payload = json.loads((output_dir / file_name).read_text(encoding="utf-8"))
        loaded[snapshot_key] = payload
    return loaded


def build_frontend_snapshots_payloads() -> dict[str, dict[str, Any]]:
    with tempfile.TemporaryDirectory(prefix="frontend-snapshots-") as tmp_root:
        base = Path(tmp_root)

        stage06_publish = _run_full(STAGE06_PUBLISH_SCENARIO, base / "stage06_publish")
        stage06_info = _run_full(STAGE06_INFO_SCENARIO, base / "stage06_info")
        stage07_major = _run_full(STAGE07_MAJOR_SCENARIO, base / "stage07_major")
        stage07_child = _run_full(STAGE07_CHILD_ISSUE_SCENARIO, base / "stage07_child")
        stage07_major_pending = _run_stage07_major_until_approval_requested(
            STAGE07_MAJOR_SCENARIO, base / "stage07_major_pending"
        )

        snapshots = {
            "stage06_publish_ready_board_state": _build_board_snapshot(
                snapshot_id="stage06_publish_ready_board_state",
                harness=stage06_publish,
                capture_note="after_full_scenario",
            ),
            "stage06_needs_information_state": _build_board_snapshot(
                snapshot_id="stage06_needs_information_state",
                harness=stage06_info,
                capture_note="after_full_scenario",
            ),
            "stage07_major_replan_board_state": _build_board_snapshot(
                snapshot_id="stage07_major_replan_board_state",
                harness=stage07_major,
                capture_note="after_full_scenario",
            ),
            "stage07_exception_branch_state": _build_board_snapshot(
                snapshot_id="stage07_exception_branch_state",
                harness=stage07_child,
                capture_note="after_full_scenario",
            ),
            "approval_queue_state": _build_approval_queue_snapshot(
                harness=stage07_major_pending
            ),
            "run_detail_state": _build_run_detail_snapshot(harness=stage07_major),
            "timeline_state": _build_timeline_snapshot(harness=stage07_major),
            "official_outputs_pointers_state": _build_official_outputs_snapshot(
                harness=stage07_major
            ),
        }
        return snapshots


def _run_full(scenario_path: Path, tmp_path: Path) -> RuntimeScenarioHarness:
    harness = RuntimeScenarioHarness.from_yaml(scenario_path, tmp_path).prepare()
    harness.run_steps()
    return harness


def _run_stage07_major_until_approval_requested(
    scenario_path: Path,
    tmp_path: Path,
) -> RuntimeScenarioHarness:
    harness = RuntimeScenarioHarness.from_yaml(scenario_path, tmp_path).prepare()
    step_ids = [
        "create_base_artifact",
        "promote_base_pointer",
        "create_flag",
        "activate_issue",
        "claim_triage",
        "complete_triage",
        "claim_final_review",
        "complete_final_review",
        "request_major_replan_approval",
    ]
    for step_id in step_ids:
        harness.run_named_step(step_id)
    return harness


def _api_client(harness: RuntimeScenarioHarness) -> RuntimeApiClient:
    return RuntimeApiClient(
        db_url=harness.db_url,
        tenant_id="tenant-a",
        domain_id="domain-x",
        actor_id="human:frontend-snapshot-exporter",
        actor_type="human",
        actor_roles=["dispatch_supervisor", "operations_manager", "schedule_planner"],
    )


def _build_board_snapshot(
    *,
    snapshot_id: str,
    harness: RuntimeScenarioHarness,
    capture_note: str,
) -> dict[str, Any]:
    client = _api_client(harness)
    board = client.get(
        "/api/v1/board/schedule-planning",
        query={"workflow_run_id": harness.workflow_run_id},
    ).payload
    return _stabilize(
        {
            "snapshot_id": snapshot_id,
            "source": {
                "scenario_id": harness.scenario_id,
                "capture": capture_note,
            },
            "board": board,
        }
    )


def _build_approval_queue_snapshot(harness: RuntimeScenarioHarness) -> dict[str, Any]:
    client = _api_client(harness)
    approvals = client.get(
        "/api/v1/approvals",
        query={"workflow_run_id": harness.workflow_run_id},
    ).payload
    return _stabilize(
        {
            "snapshot_id": "approval_queue_state",
            "source": {
                "scenario_id": harness.scenario_id,
                "capture": "after_request_major_replan_approval",
            },
            "approval_queue": approvals,
        }
    )


def _build_run_detail_snapshot(harness: RuntimeScenarioHarness) -> dict[str, Any]:
    client = _api_client(harness)
    detail = client.get(f"/api/v1/workflow-runs/{harness.workflow_run_id}").payload
    return _stabilize(
        {
            "snapshot_id": "run_detail_state",
            "source": {
                "scenario_id": harness.scenario_id,
                "capture": "after_full_scenario",
            },
            "run_detail": detail,
        }
    )


def _build_timeline_snapshot(harness: RuntimeScenarioHarness) -> dict[str, Any]:
    events = harness.list_events()
    return _stabilize(
        {
            "snapshot_id": "timeline_state",
            "source": {
                "scenario_id": harness.scenario_id,
                "capture": "after_full_scenario",
            },
            "timeline": {
                "event_count": len(events),
                "event_type_sequence": [event["event_type"] for event in events],
                "events": events,
            },
        }
    )


def _build_official_outputs_snapshot(harness: RuntimeScenarioHarness) -> dict[str, Any]:
    pointers = harness.list_pointers()
    artifacts = harness.list_artifacts()
    return _stabilize(
        {
            "snapshot_id": "official_outputs_pointers_state",
            "source": {
                "scenario_id": harness.scenario_id,
                "capture": "after_full_scenario",
            },
            "official_outputs": {
                "pointers": pointers,
                "artifact_versions": artifacts,
            },
        }
    )


def _stabilize(payload: dict[str, Any]) -> dict[str, Any]:
    state = {
        "id_tokens": {},  # type: ignore[var-annotated]
        "ts_tokens": {},  # type: ignore[var-annotated]
    }
    return _stabilize_value(payload, key=None, state=state)


def _stabilize_value(
    value: Any,
    *,
    key: str | None,
    state: dict[str, dict[str, str]],
) -> Any:
    if isinstance(value, dict):
        return {
            item_key: _stabilize_value(item_value, key=item_key, state=state)
            for item_key, item_value in sorted(value.items())
        }
    if isinstance(value, list):
        return [_stabilize_value(item, key=key, state=state) for item in value]
    if key in ID_FIELDS and value is not None:
        return _tokenize(state["id_tokens"], key, value)
    if key in TIMESTAMP_FIELDS and value is not None:
        return _tokenize(state["ts_tokens"], key, value)
    if isinstance(value, str):
        return _replace_embedded_ids(value, state)
    return value


def _tokenize(bucket_map: dict[str, str], key: str, value: object) -> str:
    raw = f"{key}:{value}"
    token = bucket_map.get(raw)
    if token is not None:
        return token
    prefix = "ts" if key in TIMESTAMP_FIELDS else key
    token = f"<{prefix}:{len(bucket_map) + 1}>"
    bucket_map[raw] = token
    return token


def _replace_embedded_ids(value: str, state: dict[str, dict[str, str]]) -> str:
    updated = value
    for id_key, pattern in EMBEDDED_ID_PATTERNS.items():
        updated = pattern.sub(
            lambda match: _tokenize(state["id_tokens"], id_key, match.group(0)),
            updated,
        )
    return updated
