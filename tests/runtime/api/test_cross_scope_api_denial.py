from __future__ import annotations

import base64
import json
from pathlib import Path

from tests.runtime.helpers.runtime_api import RuntimeApiClient
from tests.runtime.helpers.runtime_cli import REPO_ROOT
from tests.runtime.helpers.scenario_harness import RuntimeScenarioHarness

SCENARIO_PATH = REPO_ROOT / "fixtures/scenarios/schedule_planning/stage06_publish_happy.yaml"
STAGE06_DOC = (
    REPO_ROOT
    / "fixtures/workflows/schedule_planning/template_pack/Stage06_Supervisor_Review_Publish/Stage06_Supervisor_Review_Publish_Document_Example_COMPLETED.docx"
)


def _encoded_file(path: Path) -> str:
    return base64.b64encode(path.read_bytes()).decode("ascii")


def test_cross_scope_requests_are_denied_and_do_not_leak_rows(tmp_path: Path) -> None:
    harness = RuntimeScenarioHarness.from_yaml(SCENARIO_PATH, tmp_path).prepare()
    created = harness.run_named_step("create_stage06_review")
    human_task_id = created["result"]["human_task"]["human_task_id"]
    uploaded = RuntimeApiClient(
        db_url=harness.db_url,
        tenant_id="tenant-a",
        domain_id="domain-x",
        actor_id="human:dispatch-supervisor-1",
        actor_type="human",
        actor_roles=["dispatch_supervisor"],
    ).post(
        f"/api/v1/human-tasks/{human_task_id}/artifacts/upload",
        payload={
            "artifact_kind": "schedule.supervisor_review.doc",
            "artifact_role": "evidence",
            "content_base64": _encoded_file(STAGE06_DOC),
            "file_name": STAGE06_DOC.name,
            "idempotency_key": f"api:{harness.scenario_id}:cross-scope-artifact-seed",
        },
    )
    assert uploaded.status_code == 200
    artifact_version_id = uploaded.payload["artifact_version"]["artifact_version_id"]
    created_flag = harness.run_action(
        action="flags.create",
        payload={
            "workflow_run_id": harness.workflow_run_id,
            "kind": "cross_scope_probe",
            "severity": "low",
            "summary": "cross scope denial probe",
            "details_json": {"probe": True},
            "created_by": {"id": "human:dispatch-supervisor-1", "type": "human"},
            "idempotency_key": f"scenario:{harness.scenario_id}:flags.create:cross-scope-probe",
        },
    )
    flag_id = created_flag["flag"]["flag_id"]

    wrong_scope_client = RuntimeApiClient(
        db_url=harness.db_url,
        tenant_id="tenant-b",
        domain_id="domain-y",
        actor_id="human:other-actor",
        actor_type="human",
        actor_roles=["dispatch_supervisor"],
    )

    detail_denied = wrong_scope_client.get(f"/api/v1/workflow-runs/{harness.workflow_run_id}")
    assert detail_denied.status_code == 404
    assert detail_denied.payload["error"]["code"] == "workflow_run_not_found"

    timeline_denied = wrong_scope_client.get(
        f"/api/v1/workflow-runs/{harness.workflow_run_id}/timeline"
    )
    assert timeline_denied.status_code == 404
    assert timeline_denied.payload["error"]["code"] == "workflow_run_not_found"

    scoped_list_denied = wrong_scope_client.get(
        "/api/v1/human-tasks",
        query={"workflow_run_id": harness.workflow_run_id},
    )
    assert scoped_list_denied.status_code == 404
    assert scoped_list_denied.payload["error"]["code"] == "workflow_run_not_found"

    task_detail_denied = wrong_scope_client.get(f"/api/v1/human-tasks/{human_task_id}")
    assert task_detail_denied.status_code == 404
    assert task_detail_denied.payload["error"]["code"] == "workflow_run_not_found"

    mutation_denied = wrong_scope_client.post(
        f"/api/v1/human-tasks/{human_task_id}/claim",
        payload={
            "lease_seconds": 300,
            "idempotency_key": f"api:{harness.scenario_id}:cross-scope-claim",
        },
    )
    assert mutation_denied.status_code == 404
    assert mutation_denied.payload["error"]["code"] == "workflow_run_not_found"

    flag_list_denied = wrong_scope_client.get(
        "/api/v1/flags",
        query={"workflow_run_id": harness.workflow_run_id},
    )
    assert flag_list_denied.status_code == 404
    assert flag_list_denied.payload["error"]["code"] == "workflow_run_not_found"

    flag_detail_denied = wrong_scope_client.get(f"/api/v1/flags/{flag_id}")
    assert flag_detail_denied.status_code == 404
    assert flag_detail_denied.payload["error"]["code"] == "workflow_run_not_found"

    flag_transition_denied = wrong_scope_client.post(
        f"/api/v1/flags/{flag_id}/transition",
        payload={
            "to_state": "triage",
            "reason": "cross scope denial probe",
            "idempotency_key": f"api:{harness.scenario_id}:cross-scope-flag-transition",
        },
    )
    assert flag_transition_denied.status_code == 404
    assert flag_transition_denied.payload["error"]["code"] == "workflow_run_not_found"

    artifact_list_denied = wrong_scope_client.get(
        "/api/v1/artifacts",
        query={"workflow_run_id": harness.workflow_run_id},
    )
    assert artifact_list_denied.status_code == 404
    assert artifact_list_denied.payload["error"]["code"] == "workflow_run_not_found"

    artifact_detail_denied = wrong_scope_client.get(f"/api/v1/artifacts/{artifact_version_id}")
    assert artifact_detail_denied.status_code == 404
    assert artifact_detail_denied.payload["error"]["code"] == "workflow_run_not_found"

    artifact_download_denied = wrong_scope_client.get(
        f"/api/v1/artifacts/{artifact_version_id}/download"
    )
    assert artifact_download_denied.status_code == 404
    assert artifact_download_denied.payload["error"]["code"] == "workflow_run_not_found"

    artifact_binary_download_denied = wrong_scope_client.get_raw(
        f"/api/v1/artifacts/{artifact_version_id}/download.bin"
    )
    assert artifact_binary_download_denied.status_code == 404
    assert artifact_binary_download_denied.headers["content-type"] == "application/json"
    assert (
        json.loads(artifact_binary_download_denied.body.decode("utf-8"))["error"]["code"]
        == "workflow_run_not_found"
    )

    artifact_subject_list_denied = wrong_scope_client.get(
        f"/api/v1/human-tasks/{human_task_id}/artifacts",
    )
    assert artifact_subject_list_denied.status_code == 404
    assert artifact_subject_list_denied.payload["error"]["code"] == "workflow_run_not_found"

    artifact_subject_upload_denied = wrong_scope_client.post(
        f"/api/v1/human-tasks/{human_task_id}/artifacts/upload",
        payload={
            "artifact_kind": "schedule.supervisor_review.doc",
            "artifact_role": "evidence",
            "source_path": str(STAGE06_DOC),
            "file_name": STAGE06_DOC.name,
            "idempotency_key": f"api:{harness.scenario_id}:cross-scope-artifact-upload",
        },
    )
    assert artifact_subject_upload_denied.status_code == 404
    assert artifact_subject_upload_denied.payload["error"]["code"] == "workflow_run_not_found"

    list_no_leak = wrong_scope_client.get("/api/v1/workflow-runs")
    assert list_no_leak.status_code == 200
    assert list_no_leak.payload["workflow_runs"] == []

    global_artifacts_no_leak = wrong_scope_client.get("/api/v1/artifacts")
    assert global_artifacts_no_leak.status_code == 200
    assert global_artifacts_no_leak.payload["artifact_versions"] == []
