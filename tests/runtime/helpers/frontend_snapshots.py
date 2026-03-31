from __future__ import annotations

import json
import tempfile
from pathlib import Path
import re
from typing import Any

from tests.runtime.helpers.runtime_api import RuntimeApiClient
from tests.runtime.helpers.runtime_cli import REPO_ROOT, run_cli
from tests.runtime.helpers.scenario_harness import RuntimeScenarioHarness
from tests.runtime.helpers.workpage_runs import (
    seed_actual_ops_weekly_schedule_run,
    seed_actual_ops_weekly_schedule_run_with_stage04_outputs,
    seed_dispatch_workspace_stage04_approval_with_draft,
    seed_dispatch_workspace_stage04_approval_without_draft,
    seed_dispatch_reporting_workpage_run,
    seed_weekly_workspace_stage04_task_surface_without_draft,
    seed_weekly_workspace_supported_task_surface_with_draft,
)

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
    "workpage_schedule_v0_state": "workpage_schedule_v0_state.json",
    "workpage_schedule_v0_run_state": "workpage_schedule_v0_run_state.json",
    "workpage_schedule_v0_artifact_state": "workpage_schedule_v0_artifact_state.json",
    "workpage_schedule_v0_artifact_submit_response": "workpage_schedule_v0_artifact_submit_response.json",
    "workspace_schedule_workpage_action_available_state": "workspace_schedule_workpage_action_available_state.json",
    "workspace_schedule_workpage_action_unavailable_state": "workspace_schedule_workpage_action_unavailable_state.json",
    "workspace_eod_workpage_action_create_state": "workspace_eod_workpage_action_create_state.json",
    "workspace_eod_workpage_action_open_state": "workspace_eod_workpage_action_open_state.json",
    "workpage_eod_v0_state": "workpage_eod_v0_state.json",
    "workpage_eod_v0_run_state": "workpage_eod_v0_run_state.json",
    "workpage_eod_v0_run_artifact_create_response": "workpage_eod_v0_run_artifact_create_response.json",
    "workpage_eod_v0_artifact_create_response": "workpage_eod_v0_artifact_create_response.json",
    "workpage_eod_v0_artifact_state": "workpage_eod_v0_artifact_state.json",
    "workpage_eod_v0_artifact_submit_response": "workpage_eod_v0_artifact_submit_response.json",
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
    "generated_at",
}

EMBEDDED_ID_PATTERNS = {
    "workflow_run_id": re.compile(r"wr-[0-9a-fA-F-]{8,}"),
    "task_run_id": re.compile(r"tr-[0-9a-fA-F-]{8,}"),
    "human_task_id": re.compile(r"ht-[0-9a-fA-F-]{8,}"),
    "approval_id": re.compile(r"ap-[0-9a-fA-F-]{8,}"),
    "artifact_version_id": re.compile(r"av-[0-9a-fA-F-]{8,}"),
    "flag_id": re.compile(r"fl-[0-9a-fA-F-]{8,}"),
    "bundle_id": re.compile(r"bundle-[a-z0-9-]+-stage04-[0-9a-f]{10}"),
    "candidate_delta_id": re.compile(
        r"cand-[a-z0-9-]+-stage04-[0-9a-f]{8,}-[0-9a-f]{8,}"
    ),
    "command_receipt_key": re.compile(r"command-receipt:[0-9a-f]{64}"),
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
            "workpage_schedule_v0_state": _build_schedule_workpage_snapshot(
                tmp_path=base / "workpage_schedule_v0"
            ),
            "workpage_schedule_v0_run_state": _build_schedule_run_workpage_snapshot(
                tmp_path=base / "workpage_schedule_v0_run"
            ),
            "workpage_schedule_v0_artifact_state": _build_schedule_artifact_state_snapshot(
                tmp_path=base / "workpage_schedule_v0_artifact_state"
            ),
            "workpage_schedule_v0_artifact_submit_response": _build_schedule_artifact_submit_snapshot(
                tmp_path=base / "workpage_schedule_v0_artifact_submit"
            ),
            "workspace_schedule_workpage_action_available_state": _build_workspace_schedule_action_available_snapshot(
                tmp_path=base / "workspace_schedule_workpage_action_available"
            ),
            "workspace_schedule_workpage_action_unavailable_state": _build_workspace_schedule_action_unavailable_snapshot(
                tmp_path=base / "workspace_schedule_workpage_action_unavailable"
            ),
            "workspace_eod_workpage_action_create_state": _build_workspace_eod_action_create_snapshot(
                tmp_path=base / "workspace_eod_workpage_action_create"
            ),
            "workspace_eod_workpage_action_open_state": _build_workspace_eod_action_open_snapshot(
                tmp_path=base / "workspace_eod_workpage_action_open"
            ),
            "workpage_eod_v0_state": _build_eod_workpage_snapshot(
                tmp_path=base / "workpage_eod_v0"
            ),
            "workpage_eod_v0_run_state": _build_eod_run_workpage_snapshot(
                tmp_path=base / "workpage_eod_v0_run"
            ),
            "workpage_eod_v0_run_artifact_create_response": _build_eod_run_artifact_create_snapshot(
                tmp_path=base / "workpage_eod_v0_run_artifact_create"
            ),
            "workpage_eod_v0_artifact_create_response": _build_eod_artifact_create_snapshot(
                tmp_path=base / "workpage_eod_v0_artifact_create"
            ),
            "workpage_eod_v0_artifact_state": _build_eod_artifact_state_snapshot(
                tmp_path=base / "workpage_eod_v0_artifact_state"
            ),
            "workpage_eod_v0_artifact_submit_response": _build_eod_artifact_submit_snapshot(
                tmp_path=base / "workpage_eod_v0_artifact_submit"
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
        "upload_exception_board",
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


def _build_schedule_workpage_snapshot(*, tmp_path: Path) -> dict[str, Any]:
    tmp_path.mkdir(parents=True, exist_ok=True)
    client = RuntimeApiClient(
        db_url=str(tmp_path / "workpage_schedule_v0.db"),
        tenant_id="tenant-a",
        domain_id="domain-x",
        actor_id="human:frontend-snapshot-exporter",
        actor_type="human",
        actor_roles=["dispatch_supervisor", "operations_manager", "schedule_planner"],
    )
    payload = client.get("/api/v1/workpages/demo/schedule-v0").payload
    return _stabilize(
        {
            "snapshot_id": "workpage_schedule_v0_state",
            "source": {
                "capture": "repo_example_demo_query",
                "workpage_id": "schedule-v0",
            },
            "workpage_state": payload,
        }
    )


def _build_schedule_run_workpage_snapshot(*, tmp_path: Path) -> dict[str, Any]:
    tmp_path.mkdir(parents=True, exist_ok=True)
    db_url = f"sqlite:///{tmp_path / 'workpage_schedule_v0_run.db'}"
    seeded = seed_actual_ops_weekly_schedule_run(
        db_url=db_url,
        tenant_id="tenant-a",
        domain_id="domain-x",
        run_tag="snapshot:workpage-schedule-v0-run",
    )
    client = RuntimeApiClient(
        db_url=db_url,
        tenant_id="tenant-a",
        domain_id="domain-x",
        actor_id="human:frontend-snapshot-exporter",
        actor_type="human",
        actor_roles=["dispatch_supervisor", "operations_manager", "schedule_planner"],
    )
    workflow_run_id = str(seeded["workflow_run_id"])
    payload = client.get(
        f"/api/v1/workpages/workflow-runs/{workflow_run_id}/schedule-v0"
    ).payload
    return _stabilize(
        {
            "snapshot_id": "workpage_schedule_v0_run_state",
            "source": {
                "capture": "workflow_run_query",
                "workflow_run_id": workflow_run_id,
                "workpage_id": "schedule-v0",
            },
            "workpage_state": payload,
        }
    )


def _build_schedule_artifact_state_snapshot(*, tmp_path: Path) -> dict[str, Any]:
    tmp_path.mkdir(parents=True, exist_ok=True)
    db_url = f"sqlite:///{tmp_path / 'workpage_schedule_v0_artifact.db'}"
    seeded = seed_actual_ops_weekly_schedule_run_with_stage04_outputs(
        db_url=db_url,
        tenant_id="tenant-a",
        domain_id="domain-x",
        run_tag="snapshot:workpage-schedule-v0-artifact",
    )
    client = RuntimeApiClient(
        db_url=db_url,
        tenant_id="tenant-a",
        domain_id="domain-x",
        actor_id="human:frontend-snapshot-exporter",
        actor_type="human",
        actor_roles=["dispatch_supervisor", "operations_manager", "schedule_planner"],
    )
    artifact_version_id = str(seeded["stage04_outputs"]["draft_workbook"]["artifact_version_id"])
    payload = client.get(f"/api/v1/workpages/artifacts/{artifact_version_id}").payload
    return _stabilize(
        {
            "snapshot_id": "workpage_schedule_v0_artifact_state",
            "source": {
                "capture": "artifact_backed_read_projection",
                "workflow_run_id": seeded["workflow_run_id"],
                "workpage_id": "schedule-v0",
            },
            "workpage_state": payload,
        }
    )


def _build_schedule_artifact_submit_snapshot(*, tmp_path: Path) -> dict[str, Any]:
    tmp_path.mkdir(parents=True, exist_ok=True)
    db_url = f"sqlite:///{tmp_path / 'workpage_schedule_v0_artifact_submit.db'}"
    seeded = seed_actual_ops_weekly_schedule_run_with_stage04_outputs(
        db_url=db_url,
        tenant_id="tenant-a",
        domain_id="domain-x",
        run_tag="snapshot:workpage-schedule-v0-artifact-submit",
    )
    client = RuntimeApiClient(
        db_url=db_url,
        tenant_id="tenant-a",
        domain_id="domain-x",
        actor_id="human:frontend-snapshot-exporter",
        actor_type="human",
        actor_roles=["dispatch_supervisor", "operations_manager", "schedule_planner"],
    )
    artifact_version_id = str(seeded["stage04_outputs"]["draft_workbook"]["artifact_version_id"])
    current = client.get(f"/api/v1/workpages/artifacts/{artifact_version_id}").payload
    assignment_rows = list(
        next(
            section["rows"]
            for section in current["workpage"]["sections"]
            if section.get("table_id") == "assignment_rows"
        )
    )
    reserve_rows = list(
        next(
            section["rows"]
            for section in current["workpage"]["sections"]
            if section.get("table_id") == "reserve_rows"
        )
    )
    assignment_rows[0] = {
        **assignment_rows[0],
        "assigned_driver_id": "DRV-SNAPSHOT-77",
        "assignment_status": "manual_override",
    }
    reserve_rows[0] = {
        **reserve_rows[0],
        "assigned_driver_id": "DRV-SNAPSHOT-88",
        "assignment_status": "manual_override",
    }
    payload = client.post(
        f"/api/v1/workpages/artifacts/{artifact_version_id}/submit",
        payload={
            "rows": assignment_rows,
            "reserve_rows": reserve_rows,
            "idempotency_key": "snapshot:schedule-artifact-submit",
        },
    ).payload
    return _stabilize(
        {
            "snapshot_id": "workpage_schedule_v0_artifact_submit_response",
            "source": {
                "capture": "artifact_backed_submit_response",
                "workflow_run_id": seeded["workflow_run_id"],
                "workpage_id": "schedule-v0",
            },
            "submit_response": payload,
        }
    )


def _build_workspace_schedule_action_available_snapshot(*, tmp_path: Path) -> dict[str, Any]:
    tmp_path.mkdir(parents=True, exist_ok=True)
    db_url = f"sqlite:///{tmp_path / 'workspace_schedule_action_available.db'}"
    seeded = seed_weekly_workspace_supported_task_surface_with_draft(
        db_url=db_url,
        tenant_id="tenant-a",
        domain_id="domain-x",
        run_tag="snapshot:workspace-schedule-action-available",
    )
    client = RuntimeApiClient(
        db_url=db_url,
        tenant_id="tenant-a",
        domain_id="domain-x",
        actor_id="human:frontend-snapshot-exporter",
        actor_type="human",
        actor_roles=["schedule_planner"],
    )
    payload = client.get(f"/api/v1/workflow-runs/{seeded['workflow_run_id']}/workspace").payload
    return _stabilize(
        {
            "snapshot_id": "workspace_schedule_workpage_action_available_state",
            "source": {
                "capture": "workspace_schedule_workpage_action_available",
                "workflow_run_id": seeded["workflow_run_id"],
            },
            "workspace": payload,
        }
    )


def _build_workspace_schedule_action_unavailable_snapshot(*, tmp_path: Path) -> dict[str, Any]:
    tmp_path.mkdir(parents=True, exist_ok=True)
    db_url = f"sqlite:///{tmp_path / 'workspace_schedule_action_unavailable.db'}"
    seeded = seed_weekly_workspace_stage04_task_surface_without_draft(
        db_url=db_url,
        tenant_id="tenant-a",
        domain_id="domain-x",
        run_tag="snapshot:workspace-schedule-action-unavailable",
    )
    client = RuntimeApiClient(
        db_url=db_url,
        tenant_id="tenant-a",
        domain_id="domain-x",
        actor_id="human:frontend-snapshot-exporter",
        actor_type="human",
        actor_roles=["schedule_planner"],
    )
    payload = client.get(f"/api/v1/workflow-runs/{seeded['workflow_run_id']}/workspace").payload
    return _stabilize(
        {
            "snapshot_id": "workspace_schedule_workpage_action_unavailable_state",
            "source": {
                "capture": "workspace_schedule_workpage_action_unavailable",
                "workflow_run_id": seeded["workflow_run_id"],
            },
            "workspace": payload,
        }
    )


def _build_workspace_eod_action_create_snapshot(*, tmp_path: Path) -> dict[str, Any]:
    tmp_path.mkdir(parents=True, exist_ok=True)
    db_url = f"sqlite:///{tmp_path / 'workspace_eod_action_create.db'}"
    seeded = seed_dispatch_workspace_stage04_approval_without_draft(
        db_url=db_url,
        tenant_id="tenant-a",
        domain_id="domain-x",
        run_tag="snapshot:workspace-eod-action-create",
    )
    client = RuntimeApiClient(
        db_url=db_url,
        tenant_id="tenant-a",
        domain_id="domain-x",
        actor_id="human:frontend-snapshot-exporter",
        actor_type="human",
        actor_roles=["dispatch_supervisor"],
    )
    payload = client.get(f"/api/v1/workflow-runs/{seeded['workflow_run_id']}/workspace").payload
    return _stabilize(
        {
            "snapshot_id": "workspace_eod_workpage_action_create_state",
            "source": {
                "capture": "workspace_eod_workpage_action_create",
                "workflow_run_id": seeded["workflow_run_id"],
            },
            "workspace": payload,
        }
    )


def _build_workspace_eod_action_open_snapshot(*, tmp_path: Path) -> dict[str, Any]:
    tmp_path.mkdir(parents=True, exist_ok=True)
    db_url = f"sqlite:///{tmp_path / 'workspace_eod_action_open.db'}"
    seeded = seed_dispatch_workspace_stage04_approval_with_draft(
        db_url=db_url,
        tenant_id="tenant-a",
        domain_id="domain-x",
        run_tag="snapshot:workspace-eod-action-open",
    )
    client = RuntimeApiClient(
        db_url=db_url,
        tenant_id="tenant-a",
        domain_id="domain-x",
        actor_id="human:frontend-snapshot-exporter",
        actor_type="human",
        actor_roles=["dispatch_supervisor"],
    )
    payload = client.get(f"/api/v1/workflow-runs/{seeded['workflow_run_id']}/workspace").payload
    return _stabilize(
        {
            "snapshot_id": "workspace_eod_workpage_action_open_state",
            "source": {
                "capture": "workspace_eod_workpage_action_open",
                "workflow_run_id": seeded["workflow_run_id"],
            },
            "workspace": payload,
        }
    )


def _build_eod_workpage_snapshot(*, tmp_path: Path) -> dict[str, Any]:
    tmp_path.mkdir(parents=True, exist_ok=True)
    client = RuntimeApiClient(
        db_url=str(tmp_path / "workpage_eod_v0.db"),
        tenant_id="tenant-a",
        domain_id="domain-x",
        actor_id="human:frontend-snapshot-exporter",
        actor_type="human",
        actor_roles=["dispatch_supervisor", "operations_manager", "schedule_planner"],
    )
    payload = client.get("/api/v1/workpages/demo/eod-v0").payload
    return _stabilize(
        {
            "snapshot_id": "workpage_eod_v0_state",
            "source": {
                "capture": "repo_example_demo_query",
                "workpage_id": "eod-v0",
            },
            "workpage_state": payload,
        }
    )


def _build_eod_run_workpage_snapshot(*, tmp_path: Path) -> dict[str, Any]:
    tmp_path.mkdir(parents=True, exist_ok=True)
    db_url = f"sqlite:///{tmp_path / 'workpage_eod_v0_run.db'}"
    seeded = seed_dispatch_reporting_workpage_run(
        db_url=db_url,
        tenant_id="tenant-a",
        domain_id="domain-x",
        run_tag="snapshot:workpage-eod-v0-run",
    )
    client = RuntimeApiClient(
        db_url=db_url,
        tenant_id="tenant-a",
        domain_id="domain-x",
        actor_id="human:frontend-snapshot-exporter",
        actor_type="human",
        actor_roles=["dispatch_supervisor", "operations_manager", "schedule_planner"],
    )
    workflow_run_id = str(seeded["workflow_run_id"])
    client.post(
        f"/api/v1/workpages/workflow-runs/{workflow_run_id}/eod-v0/drafts",
        payload={"idempotency_key": "snapshot:workpage-eod-v0-run:create"},
    )
    payload = client.get(
        f"/api/v1/workpages/workflow-runs/{workflow_run_id}/eod-v0"
    ).payload
    return _stabilize(
        {
            "snapshot_id": "workpage_eod_v0_run_state",
            "source": {
                "capture": "workflow_run_query",
                "workflow_run_id": workflow_run_id,
                "workpage_id": "eod-v0",
            },
            "workpage_state": payload,
        }
    )


def _artifact_workpage_client(tmp_path: Path) -> RuntimeApiClient:
    db_url = f"sqlite:///{tmp_path / 'workpage_eod_v0_artifact.db'}"
    run_cli("--db-url", db_url, "init-db")
    return RuntimeApiClient(
        db_url=db_url,
        tenant_id="tenant-a",
        domain_id="domain-x",
        actor_id="human:frontend-snapshot-exporter",
        actor_type="human",
        actor_roles=["dispatch_supervisor", "operations_manager", "schedule_planner"],
    )


def _build_eod_artifact_create_snapshot(*, tmp_path: Path) -> dict[str, Any]:
    tmp_path.mkdir(parents=True, exist_ok=True)
    client = _artifact_workpage_client(tmp_path)
    payload = client.post(
        "/api/v1/workpages/demo/eod-v0/drafts",
        payload={"idempotency_key": "snapshot:eod-artifact-create"},
    ).payload
    return _stabilize(
        {
            "snapshot_id": "workpage_eod_v0_artifact_create_response",
            "source": {
                "capture": "artifact_backed_create_response",
                "workpage_id": "eod-v0",
            },
            "create_response": payload,
        }
    )


def _build_eod_run_artifact_create_snapshot(*, tmp_path: Path) -> dict[str, Any]:
    tmp_path.mkdir(parents=True, exist_ok=True)
    db_url = f"sqlite:///{tmp_path / 'workpage_eod_v0_run_artifact_create.db'}"
    seeded = seed_dispatch_reporting_workpage_run(
        db_url=db_url,
        tenant_id="tenant-a",
        domain_id="domain-x",
        run_tag="snapshot:workpage-eod-v0-run-artifact-create",
    )
    client = RuntimeApiClient(
        db_url=db_url,
        tenant_id="tenant-a",
        domain_id="domain-x",
        actor_id="human:frontend-snapshot-exporter",
        actor_type="human",
        actor_roles=["dispatch_supervisor", "operations_manager", "schedule_planner"],
    )
    workflow_run_id = str(seeded["workflow_run_id"])
    payload = client.post(
        f"/api/v1/workpages/workflow-runs/{workflow_run_id}/eod-v0/drafts",
        payload={"idempotency_key": "snapshot:eod-run-artifact-create"},
    ).payload
    return _stabilize(
        {
            "snapshot_id": "workpage_eod_v0_run_artifact_create_response",
            "source": {
                "capture": "workflow_run_artifact_backed_create_response",
                "workflow_run_id": workflow_run_id,
                "workpage_id": "eod-v0",
            },
            "create_response": payload,
        }
    )


def _build_eod_artifact_state_snapshot(*, tmp_path: Path) -> dict[str, Any]:
    tmp_path.mkdir(parents=True, exist_ok=True)
    client = _artifact_workpage_client(tmp_path)
    created = client.post(
        "/api/v1/workpages/demo/eod-v0/drafts",
        payload={"idempotency_key": "snapshot:eod-artifact-state:create"},
    ).payload
    artifact_version_id = str(created["draft"]["artifact_version_id"])
    payload = client.get(f"/api/v1/workpages/artifacts/{artifact_version_id}").payload
    return _stabilize(
        {
            "snapshot_id": "workpage_eod_v0_artifact_state",
            "source": {
                "capture": "artifact_backed_read_projection",
                "workpage_id": "eod-v0",
            },
            "workpage_state": payload,
        }
    )


def _build_eod_artifact_submit_snapshot(*, tmp_path: Path) -> dict[str, Any]:
    tmp_path.mkdir(parents=True, exist_ok=True)
    client = _artifact_workpage_client(tmp_path)
    created = client.post(
        "/api/v1/workpages/demo/eod-v0/drafts",
        payload={"idempotency_key": "snapshot:eod-artifact-submit:create"},
    ).payload
    artifact_version_id = str(created["draft"]["artifact_version_id"])
    payload = client.post(
        f"/api/v1/workpages/artifacts/{artifact_version_id}/submit",
        payload={
            "form_values": {
                "dispatcher_comment": "Snapshot submit path",
                "manager_note": "Backend-owned artifact response fixture.",
            },
            "checklist_values": [],
            "idempotency_key": "snapshot:eod-artifact-submit",
        },
    ).payload
    return _stabilize(
        {
            "snapshot_id": "workpage_eod_v0_artifact_submit_response",
            "source": {
                "capture": "artifact_backed_submit_response",
                "workpage_id": "eod-v0",
            },
            "submit_response": payload,
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
