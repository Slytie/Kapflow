from __future__ import annotations

import base64
import json
from pathlib import Path

from tests.runtime.helpers.runtime_api import RuntimeApiClient
from tests.runtime.helpers.runtime_cli import REPO_ROOT
from tests.runtime.helpers.scenario_harness import RuntimeScenarioHarness

SCENARIO_PATH = (
    REPO_ROOT / "fixtures/scenarios/schedule_planning/stage06_publish_happy.yaml"
)
ARTIFACT_PATH = (
    REPO_ROOT
    / "fixtures/workflows/schedule_planning/template_pack/Stage06_Supervisor_Review_Publish/Stage06_Supervisor_Review_Publish_Document_Example_COMPLETED.docx"
)
TEMPLATE_PATH = (
    REPO_ROOT
    / "fixtures/workflows/schedule_planning/template_pack/Stage05_Draft_Schedule_Triage/Stage05_Draft_Schedule_Triage_Spreadsheet_Template_EMPTY.xlsx"
)


def _client(tmp_path: Path) -> RuntimeApiClient:
    return RuntimeApiClient(
        db_url=f"sqlite:///{tmp_path / 'runtime.db'}",
        tenant_id="tenant-a",
        domain_id="domain-x",
        actor_id="human:test-user",
        actor_type="human",
        actor_roles=["dispatch_supervisor"],
    )


def _scenario_client(harness: RuntimeScenarioHarness) -> RuntimeApiClient:
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


def test_artifact_download_binary_endpoint_returns_exact_bytes_and_headers(
    tmp_path: Path,
) -> None:
    harness = RuntimeScenarioHarness.from_yaml(SCENARIO_PATH, tmp_path).prepare()
    created = harness.run_named_step("create_stage06_review")
    human_task_id = str(created["result"]["human_task"]["human_task_id"])
    client = _scenario_client(harness)
    uploaded = client.post(
        f"/api/v1/human-tasks/{human_task_id}/artifacts/upload",
        payload={
            "artifact_kind": "schedule.supervisor_review.doc",
            "artifact_role": "evidence",
            "content_base64": _encoded_file(ARTIFACT_PATH),
            "file_name": ARTIFACT_PATH.name,
            "metadata_json": {"file_name": ARTIFACT_PATH.name},
            "idempotency_key": f"api:{harness.scenario_id}:binary-download-artifact-upload",
        },
    )
    assert uploaded.status_code == 200
    artifact_version_id = str(uploaded.payload["artifact_version"]["artifact_version_id"])

    response = client.get_raw(f"/api/v1/artifacts/{artifact_version_id}/download.bin")

    assert response.status_code == 200
    assert response.body == ARTIFACT_PATH.read_bytes()
    assert response.headers["content-type"] == (
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    )
    assert response.headers["content-length"] == str(len(response.body))
    assert (
        response.headers["content-disposition"]
        == 'attachment; filename="Stage06_Supervisor_Review_Publish_Document_Example_COMPLETED.docx"'
    )
    assert response.headers["x-request-id"].startswith("httpreq_")


def test_template_download_binary_endpoint_returns_exact_bytes_and_headers(
    tmp_path: Path,
) -> None:
    client = _client(tmp_path)
    template_id = "schedule.stage05.draft_schedule.workbook.empty.v1"

    response = client.get_raw(f"/api/v1/templates/{template_id}/download.bin")

    assert response.status_code == 200
    assert response.body == TEMPLATE_PATH.read_bytes()
    assert response.headers["content-type"] == (
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
    assert response.headers["content-length"] == str(len(response.body))
    assert (
        response.headers["content-disposition"]
        == 'attachment; filename="Stage05_Draft_Schedule_Triage_Spreadsheet_Template_EMPTY.xlsx"'
    )
    assert response.headers["x-request-id"].startswith("httpreq_")


def test_binary_download_transport_keeps_json_download_compatibility(
    tmp_path: Path,
) -> None:
    client = _client(tmp_path)
    template_id = "schedule.stage05.draft_schedule.workbook.empty.v1"

    response = client.get(f"/api/v1/templates/{template_id}/download")

    assert response.status_code == 200
    assert response.payload["command"] == "api.templates.download"
    assert response.payload["content_base64"]
    assert response.payload["byte_size"] == TEMPLATE_PATH.stat().st_size


def test_unknown_template_binary_download_returns_json_not_found(tmp_path: Path) -> None:
    client = _client(tmp_path)

    response = client.get_raw("/api/v1/templates/does-not-exist/download.bin")

    assert response.status_code == 404
    assert response.headers["content-type"] == "application/json"
    payload = json.loads(response.body.decode("utf-8"))
    assert payload["error"]["code"] == "template_not_found"
