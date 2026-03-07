from __future__ import annotations

from pathlib import Path

from tests.runtime.helpers.runtime_api import RuntimeApiClient
from tests.runtime.helpers.runtime_cli import REPO_ROOT
from tests.runtime.helpers.scenario_harness import RuntimeScenarioHarness

SCENARIO_STAGE06_INFO = (
    REPO_ROOT / "fixtures/scenarios/schedule_planning/stage06_review_requires_more_information.yaml"
)
SCENARIO_STAGE06_PUBLISH = (
    REPO_ROOT / "fixtures/scenarios/schedule_planning/stage06_publish_happy.yaml"
)
SCENARIO_STAGE07_INFO = (
    REPO_ROOT / "fixtures/scenarios/schedule_planning/stage07_missing_information_branch.yaml"
)
STAGE06_DOC = (
    REPO_ROOT
    / "fixtures/workflows/schedule_planning/template_pack/Stage06_Supervisor_Review_Publish/Stage06_Supervisor_Review_Publish_Document_Example_COMPLETED.docx"
)


def _client(
    harness: RuntimeScenarioHarness,
    *,
    actor_id: str,
    actor_roles: list[str],
) -> RuntimeApiClient:
    return RuntimeApiClient(
        db_url=harness.db_url,
        tenant_id="tenant-a",
        domain_id="domain-x",
        actor_id=actor_id,
        actor_type="human",
        actor_roles=actor_roles,
    )


def _workspace_item(payload: dict[str, object], *, subject_kind: str, subject_id: str) -> dict[str, object]:
    for key in ("user_work", "blocking_work"):
        items = payload.get(key)
        if not isinstance(items, list):
            continue
        for item in items:
            if not isinstance(item, dict):
                continue
            if item.get("subject_kind") == subject_kind and item.get("subject_id") == subject_id:
                return item
    raise AssertionError(f"workspace item not found: {subject_kind}:{subject_id}")


def _prepare_claimed_information_request(
    tmp_path: Path,
) -> tuple[RuntimeScenarioHarness, RuntimeApiClient, str]:
    harness = RuntimeScenarioHarness.from_yaml(SCENARIO_STAGE06_INFO, tmp_path).prepare()
    harness.run_steps()
    information_task_id = str(
        harness.output("complete_stage06_review")["result"]["spawned_children"][0]["human_task_id"]
    )
    planner_client = _client(
        harness,
        actor_id="human:schedule-planner-1",
        actor_roles=["schedule_planner"],
    )
    claimed = planner_client.post(
        f"/api/v1/human-tasks/{information_task_id}/claim",
        payload={
            "lease_seconds": 300,
            "idempotency_key": f"api:{harness.scenario_id}:workspace-actionability:claim-information",
        },
    )
    assert claimed.status_code == 200
    return harness, planner_client, information_task_id


def test_stage06_information_request_requires_upload_before_completion(tmp_path: Path) -> None:
    harness, planner_client, information_task_id = _prepare_claimed_information_request(tmp_path)

    workspace = planner_client.get(f"/api/v1/workflow-runs/{harness.workflow_run_id}/workspace")
    assert workspace.status_code == 200
    info_item = _workspace_item(
        workspace.payload,
        subject_kind="human_task",
        subject_id=information_task_id,
    )
    assert info_item["linked_artifact_count"] == 0
    assert info_item["missing_required_inputs"] == ["schedule.supervisor_review.doc"]
    assert info_item["can_complete"] is False
    assert "complete" not in info_item["available_actions"]


def test_information_request_becomes_completable_after_upload(tmp_path: Path) -> None:
    harness, planner_client, information_task_id = _prepare_claimed_information_request(tmp_path)

    uploaded = planner_client.post(
        f"/api/v1/human-tasks/{information_task_id}/artifacts/upload",
        payload={
            "artifact_kind": "schedule.supervisor_review.doc",
            "artifact_role": "evidence",
            "source_path": str(STAGE06_DOC),
            "file_name": STAGE06_DOC.name,
            "idempotency_key": f"api:{harness.scenario_id}:workspace-actionability:upload-information",
        },
    )
    assert uploaded.status_code == 200

    workspace = planner_client.get(f"/api/v1/workflow-runs/{harness.workflow_run_id}/workspace")
    assert workspace.status_code == 200
    info_item = _workspace_item(
        workspace.payload,
        subject_kind="human_task",
        subject_id=information_task_id,
    )
    assert int(info_item["linked_artifact_count"]) >= 1
    assert info_item["missing_required_inputs"] == []
    assert info_item["can_complete"] is True
    assert "complete" in info_item["available_actions"]


def test_stage07_information_request_still_requires_upload(tmp_path: Path) -> None:
    harness = RuntimeScenarioHarness.from_yaml(SCENARIO_STAGE07_INFO, tmp_path).prepare()
    harness.run_steps()
    information_task_id = str(
        harness.output("complete_issue")["result"]["spawned_children"][0]["human_task_id"]
    )
    planner_client = _client(
        harness,
        actor_id="human:schedule-planner-7",
        actor_roles=["schedule_planner"],
    )
    claimed = planner_client.post(
        f"/api/v1/human-tasks/{information_task_id}/claim",
        payload={
            "lease_seconds": 300,
            "idempotency_key": f"api:{harness.scenario_id}:workspace-actionability:claim-stage07-information",
        },
    )
    assert claimed.status_code == 200

    workspace = planner_client.get(f"/api/v1/workflow-runs/{harness.workflow_run_id}/workspace")
    assert workspace.status_code == 200
    info_item = _workspace_item(
        workspace.payload,
        subject_kind="human_task",
        subject_id=information_task_id,
    )
    assert info_item["linked_artifact_count"] == 0
    assert info_item["can_complete"] is False
    assert "schedule.exception_board.doc" in info_item["missing_required_inputs"]
    assert "complete" not in info_item["available_actions"]


def test_stage06_run_agent_review_action_is_policy_gated(tmp_path: Path) -> None:
    allowed_harness = RuntimeScenarioHarness.from_yaml(SCENARIO_STAGE06_PUBLISH, tmp_path / "allowed").prepare()
    created = allowed_harness.run_named_step("create_stage06_review")
    stage06_human_task_id = str(created["result"]["human_task"]["human_task_id"])
    dispatch_client = _client(
        allowed_harness,
        actor_id="human:dispatch-supervisor-1",
        actor_roles=["dispatch_supervisor"],
    )
    claimed = dispatch_client.post(
        f"/api/v1/human-tasks/{stage06_human_task_id}/claim",
        payload={
            "lease_seconds": 300,
            "idempotency_key": f"api:{allowed_harness.scenario_id}:workspace-actionability:claim-stage06-dispatch",
        },
    )
    assert claimed.status_code == 200
    allowed_workspace = dispatch_client.get(
        f"/api/v1/workflow-runs/{allowed_harness.workflow_run_id}/workspace"
    )
    assert allowed_workspace.status_code == 200
    allowed_item = _workspace_item(
        allowed_workspace.payload,
        subject_kind="human_task",
        subject_id=stage06_human_task_id,
    )
    assert allowed_item["can_run_stage06_agent_review"] is True
    assert "run_stage06_agent_review" in allowed_item["available_actions"]

    denied_harness = RuntimeScenarioHarness.from_yaml(SCENARIO_STAGE06_PUBLISH, tmp_path / "denied").prepare()
    denied_created = denied_harness.run_named_step("create_stage06_review")
    denied_task_id = str(denied_created["result"]["human_task"]["human_task_id"])
    planner_client = _client(
        denied_harness,
        actor_id="human:schedule-planner-9",
        actor_roles=["schedule_planner"],
    )
    denied_claimed = planner_client.post(
        f"/api/v1/human-tasks/{denied_task_id}/claim",
        payload={
            "lease_seconds": 300,
            "idempotency_key": f"api:{denied_harness.scenario_id}:workspace-actionability:claim-stage06-planner",
        },
    )
    assert denied_claimed.status_code == 200
    denied_workspace = planner_client.get(
        f"/api/v1/workflow-runs/{denied_harness.workflow_run_id}/workspace"
    )
    assert denied_workspace.status_code == 200
    denied_item = _workspace_item(
        denied_workspace.payload,
        subject_kind="human_task",
        subject_id=denied_task_id,
    )
    assert denied_item["can_run_stage06_agent_review"] is False
    assert "run_stage06_agent_review" not in denied_item["available_actions"]
