from __future__ import annotations

import base64
from pathlib import Path

from tests.runtime.helpers.runtime_api import RuntimeApiClient
from tests.runtime.helpers.runtime_cli import REPO_ROOT
from tests.runtime.helpers.scenario_harness import RuntimeScenarioHarness

SCENARIO_PATH = REPO_ROOT / "fixtures/scenarios/schedule_planning/stage06_publish_happy.yaml"
TEMPLATE_PACK_ROOT = REPO_ROOT / "fixtures/workflows/schedule_planning/template_pack"
STAGE06_DOC = (
    TEMPLATE_PACK_ROOT
    / "Stage06_Supervisor_Review_Publish/Stage06_Supervisor_Review_Publish_Document_Example_COMPLETED.docx"
)
STAGE07_DOC = (
    TEMPLATE_PACK_ROOT
    / "Stage07_Intraday_Exception_Control/Stage07_Intraday_Exception_Control_Document_Example_COMPLETED.docx"
)
STAGE07_WORKBOOK = (
    TEMPLATE_PACK_ROOT
    / "Stage07_Intraday_Exception_Control/Stage07_Intraday_Exception_Control_Spreadsheet_Example_COMPLETED.xlsx"
)


def _api_client(harness: RuntimeScenarioHarness) -> RuntimeApiClient:
    return RuntimeApiClient(
        db_url=harness.db_url,
        tenant_id="tenant-a",
        domain_id="domain-x",
        actor_id="human:dispatch-supervisor-1",
        actor_type="human",
        actor_roles=["dispatch_supervisor", "operations_manager"],
    )


def _encoded_file(path: Path) -> str:
    return base64.b64encode(path.read_bytes()).decode("ascii")


def test_human_task_artifact_upload_list_show_download(tmp_path: Path) -> None:
    harness = RuntimeScenarioHarness.from_yaml(SCENARIO_PATH, tmp_path).prepare()
    created = harness.run_named_step("create_stage06_review")
    human_task_id = str(created["result"]["human_task"]["human_task_id"])

    client = _api_client(harness)
    uploaded = client.post(
        f"/api/v1/human-tasks/{human_task_id}/artifacts/upload",
        payload={
            "artifact_kind": "schedule.supervisor_review.doc",
            "artifact_role": "evidence",
            "content_base64": _encoded_file(STAGE06_DOC),
            "file_name": STAGE06_DOC.name,
            "idempotency_key": f"api:{harness.scenario_id}:human-task-artifact-upload",
        },
    )
    assert uploaded.status_code == 200
    artifact = uploaded.payload["artifact_version"]
    artifact_version_id = str(artifact["artifact_version_id"])
    assert any(
        link["subject_kind"] == "human_task" and link["subject_id"] == human_task_id
        for link in artifact["links"]
    )

    uploaded_second = client.post(
        f"/api/v1/human-tasks/{human_task_id}/artifacts/upload",
        payload={
            "artifact_kind": "schedule.replan_delta.workbook",
            "artifact_role": "evidence",
            "content_base64": _encoded_file(STAGE07_WORKBOOK),
            "file_name": STAGE07_WORKBOOK.name,
            "idempotency_key": f"api:{harness.scenario_id}:human-task-artifact-upload-second",
        },
    )
    assert uploaded_second.status_code == 200
    second_artifact_version_id = str(
        uploaded_second.payload["artifact_version"]["artifact_version_id"]
    )

    listed = client.get(f"/api/v1/human-tasks/{human_task_id}/artifacts")
    assert listed.status_code == 200
    listed_ids = {row["artifact_version_id"] for row in listed.payload["artifact_versions"]}
    assert artifact_version_id in listed_ids
    assert second_artifact_version_id in listed_ids

    nested_page = client.get(
        f"/api/v1/human-tasks/{human_task_id}/artifacts",
        query={"limit": "1", "offset": "1"},
    )
    assert nested_page.status_code == 200
    assert nested_page.payload["command"] == "api.human_tasks.artifacts.list"
    assert nested_page.payload["page"] == {"limit": 1, "offset": 1}
    assert len(nested_page.payload["artifact_versions"]) == 1

    list_by_subject = client.get(
        "/api/v1/artifacts",
        query={
            "workflow_run_id": harness.workflow_run_id,
            "subject_kind": "human_task",
            "subject_id": human_task_id,
        },
    )
    assert list_by_subject.status_code == 200
    subject_ids = {row["artifact_version_id"] for row in list_by_subject.payload["artifact_versions"]}
    assert artifact_version_id in subject_ids
    assert second_artifact_version_id in subject_ids

    filtered_subject_page = client.get(
        "/api/v1/artifacts",
        query={
            "workflow_run_id": harness.workflow_run_id,
            "subject_kind": "human_task",
            "subject_id": human_task_id,
            "artifact_kind": "schedule.replan_delta.workbook",
            "limit": "1",
            "offset": "0",
        },
    )
    assert filtered_subject_page.status_code == 200
    assert filtered_subject_page.payload["command"] == "api.artifacts.list"
    assert filtered_subject_page.payload["page"] == {"limit": 1, "offset": 0}
    assert [
        row["artifact_version_id"]
        for row in filtered_subject_page.payload["artifact_versions"]
    ] == [second_artifact_version_id]

    detail = client.get(f"/api/v1/artifacts/{artifact_version_id}")
    assert detail.status_code == 200
    assert detail.payload["artifact_version"]["artifact_version_id"] == artifact_version_id

    downloaded = client.get(f"/api/v1/artifacts/{artifact_version_id}/download")
    assert downloaded.status_code == 200
    downloaded_bytes = base64.b64decode(downloaded.payload["content_base64"])
    assert downloaded_bytes == STAGE06_DOC.read_bytes()

    events = harness.list_events()
    created_events = [
        event
        for event in events
        if event["event_type"] == "artifact.version.created"
        and event["payload"]["artifact_version_id"] == artifact_version_id
    ]
    assert len(created_events) == 1
    link_types = {link["type"] for link in created_events[0]["links"]}
    assert {"workflow_run", "artifact_version", "human_task"} <= link_types


def test_approval_and_flag_artifact_endpoints_are_coherent(tmp_path: Path) -> None:
    harness = RuntimeScenarioHarness.from_yaml(SCENARIO_PATH, tmp_path).prepare()
    created = harness.run_named_step("create_stage06_review")
    task_run_id = str(created["result"]["task_run"]["task_run_id"])
    approval = harness.run_action(
        action="approvals.request",
        payload={
            "workflow_run_id": harness.workflow_run_id,
            "task_run_id": task_run_id,
            "approval_kind": "business_decision",
            "scope_kind": "stage",
            "scope_ref": "Stage06",
            "action": "publish_schedule",
            "candidate_roles": ["dispatch_supervisor"],
            "required_role": "dispatch_supervisor",
            "idempotency_key": f"scenario:{harness.scenario_id}:approvals.request:artifact-linkage",
        },
    )["approval"]
    approval_id = str(approval["approval_id"])
    flag = harness.run_action(
        action="flags.create",
        payload={
            "workflow_run_id": harness.workflow_run_id,
            "kind": "artifact_linkage_probe",
            "severity": "medium",
            "summary": "flag attachment linkage probe",
            "details_json": {"probe": True},
            "created_by": {"id": "human:dispatch-supervisor-1", "type": "human"},
            "idempotency_key": f"scenario:{harness.scenario_id}:flags.create:artifact-linkage",
        },
    )["flag"]
    flag_id = str(flag["flag_id"])

    client = _api_client(harness)
    uploaded_approval = client.post(
        f"/api/v1/approvals/{approval_id}/artifacts/upload",
        payload={
            "artifact_kind": "schedule.supervisor_review.doc",
            "artifact_role": "evidence",
            "content_base64": _encoded_file(STAGE07_DOC),
            "file_name": STAGE07_DOC.name,
            "idempotency_key": f"api:{harness.scenario_id}:approval-artifact-upload",
        },
    )
    assert uploaded_approval.status_code == 200
    approval_artifact_id = uploaded_approval.payload["artifact_version"]["artifact_version_id"]

    uploaded_flag = client.post(
        f"/api/v1/flags/{flag_id}/artifacts/upload",
        payload={
            "artifact_kind": "schedule.replan_delta.workbook",
            "artifact_role": "evidence",
            "content_base64": _encoded_file(STAGE07_WORKBOOK),
            "file_name": STAGE07_WORKBOOK.name,
            "idempotency_key": f"api:{harness.scenario_id}:flag-artifact-upload",
        },
    )
    assert uploaded_flag.status_code == 200
    flag_artifact_id = uploaded_flag.payload["artifact_version"]["artifact_version_id"]

    approvals_list = client.get(f"/api/v1/approvals/{approval_id}/artifacts")
    assert approvals_list.status_code == 200
    assert {row["artifact_version_id"] for row in approvals_list.payload["artifact_versions"]} == {
        approval_artifact_id
    }

    flags_list = client.get(f"/api/v1/flags/{flag_id}/artifacts")
    assert flags_list.status_code == 200
    assert {row["artifact_version_id"] for row in flags_list.payload["artifact_versions"]} == {
        flag_artifact_id
    }

    all_artifacts = client.get(
        "/api/v1/artifacts",
        query={"workflow_run_id": harness.workflow_run_id},
    )
    assert all_artifacts.status_code == 200
    artifact_ids = {row["artifact_version_id"] for row in all_artifacts.payload["artifact_versions"]}
    assert approval_artifact_id in artifact_ids
    assert flag_artifact_id in artifact_ids
