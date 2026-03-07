from __future__ import annotations

from pathlib import Path

from tests.runtime.helpers.runtime_api import RuntimeApiClient
from tests.runtime.helpers.runtime_cli import REPO_ROOT
from tests.runtime.helpers.scenario_harness import RuntimeScenarioHarness

SCENARIO_STAGE05 = (
    REPO_ROOT
    / "fixtures/scenarios/schedule_planning/stage05_missing_workbook_template_upload.yaml"
)
SCENARIO_STAGE06 = (
    REPO_ROOT
    / "fixtures/scenarios/schedule_planning/stage06_publish_ready_confirm_review.yaml"
)
SCENARIO_STAGE07 = (
    REPO_ROOT
    / "fixtures/scenarios/schedule_planning/stage07_major_replan_confirm_review.yaml"
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


def _workspace_item(payload: dict[str, object], *, human_task_id: str) -> dict[str, object]:
    for key in ("user_work", "blocking_work"):
        items = payload.get(key)
        if not isinstance(items, list):
            continue
        for item in items:
            if not isinstance(item, dict):
                continue
            if item.get("subject_kind") == "human_task" and item.get("subject_id") == human_task_id:
                return item
    raise AssertionError(f"workspace item not found for human_task_id={human_task_id}")


def test_stage05_missing_workbook_requires_template_upload(tmp_path: Path) -> None:
    harness = RuntimeScenarioHarness.from_yaml(SCENARIO_STAGE05, tmp_path).prepare()
    harness.run_named_step("create_stage05_information_request")
    harness.run_named_step("claim_stage05_information_request")
    task_id = str(
        harness.output("create_stage05_information_request")["result"]["human_task"]["human_task_id"]
    )

    planner_client = _client(
        harness,
        actor_id="human:schedule-planner-1",
        actor_roles=["schedule_planner"],
    )
    workspace = planner_client.get(f"/api/v1/workflow-runs/{harness.workflow_run_id}/workspace")
    assert workspace.status_code == 200
    item = _workspace_item(workspace.payload, human_task_id=task_id)
    required_uploads = item["required_uploads"]
    assert isinstance(required_uploads, list) and required_uploads
    workbook_req = [
        req for req in required_uploads if req.get("dataset_key") == "schedule.draft_schedule.workbook"
    ]
    assert workbook_req
    assert workbook_req[0]["template_id"] == "schedule.stage05.draft_schedule.workbook.empty.v1"
    assert workbook_req[0]["status"] == "missing"
    assert "complete" not in item["available_actions"]

    failed = harness.run_named_step("complete_stage05_before_upload")
    assert failed["status"] == "error"
    assert failed["error"]["error_code"] == "task_requirements_not_satisfied"
    harness.run_named_step("upload_stage05_required_workbook")
    completed = harness.run_named_step("complete_stage05_after_upload")
    assert completed["status"] == "ok"


def test_stage06_publish_ready_requires_confirm_review_before_completion(tmp_path: Path) -> None:
    harness = RuntimeScenarioHarness.from_yaml(SCENARIO_STAGE06, tmp_path).prepare()
    harness.run_named_step("create_stage06_final_review")
    harness.run_named_step("claim_stage06_final_review")
    harness.run_named_step("create_draft_publish_packet")
    harness.run_named_step("create_draft_published_schedule")
    task_id = str(
        harness.output("create_stage06_final_review")["result"]["human_task"]["human_task_id"]
    )

    reviewer_client = _client(
        harness,
        actor_id="human:dispatch-supervisor-6",
        actor_roles=["dispatch_supervisor"],
    )
    workspace = reviewer_client.get(f"/api/v1/workflow-runs/{harness.workflow_run_id}/workspace")
    assert workspace.status_code == 200
    item = _workspace_item(workspace.payload, human_task_id=task_id)
    required_reviews = item["required_reviews"]
    assert isinstance(required_reviews, list) and len(required_reviews) == 2
    assert {review["status"] for review in required_reviews} == {"pending_confirmation"}
    assert "confirm_review" in item["available_actions"]
    assert "complete" not in item["available_actions"]

    failed = harness.run_named_step("complete_stage06_before_confirm_review")
    assert failed["status"] == "error"
    assert failed["error"]["error_code"] == "task_requirements_not_satisfied"
    confirmed = harness.run_named_step("confirm_stage06_review")
    assert confirmed["status"] == "ok"
    assert confirmed["result"]["artifact_version"]["artifact_kind"] == "human_task.review_confirmation.json"

    harness.run_named_step("complete_stage06_final_review")
    harness.run_named_step("request_publish_approval")
    harness.run_named_step("respond_publish_approval")
    promoted = harness.run_named_step("promote_official_pointer")
    assert promoted["status"] == "ok"
    assert (
        promoted["pointer"]["artifact_version_id"]
        == harness.output("create_draft_published_schedule")["artifact_version"]["artifact_version_id"]
    )


def test_stage07_major_replan_requires_upload_and_confirm_review(tmp_path: Path) -> None:
    harness = RuntimeScenarioHarness.from_yaml(SCENARIO_STAGE07, tmp_path).prepare()
    harness.run_steps()

    triage_before = harness.output("complete_triage_before_upload")
    assert triage_before["status"] == "error"
    assert triage_before["error"]["error_code"] == "task_requirements_not_satisfied"
    final_before = harness.output("complete_final_review_before_confirm")
    assert final_before["status"] == "error"
    assert final_before["error"]["error_code"] == "task_requirements_not_satisfied"

    confirmation = harness.output("confirm_final_review")
    assert confirmation["status"] == "ok"
    assert confirmation["result"]["artifact_version"]["artifact_kind"] == "human_task.review_confirmation.json"

    promoted = harness.output("promote_replan_pointer")
    assert promoted["status"] == "ok"
    assert (
        promoted["pointer"]["artifact_version_id"]
        == harness.output("create_draft_replan_delta")["artifact_version"]["artifact_version_id"]
    )
