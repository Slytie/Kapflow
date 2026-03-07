from __future__ import annotations

import base64
from pathlib import Path

from tests.runtime.helpers.runtime_api import RuntimeApiClient
from tests.runtime.helpers.runtime_cli import REPO_ROOT

TEMPLATE_IDS = {
    "schedule.stage05.draft_schedule.doc.empty.v1",
    "schedule.stage05.draft_schedule.workbook.empty.v1",
    "schedule.stage06.supervisor_review.doc.empty.v1",
    "schedule.stage07.exception_board.doc.empty.v1",
    "schedule.stage07.replan_delta.workbook.empty.v1",
}


def _client(tmp_path: Path) -> RuntimeApiClient:
    return RuntimeApiClient(
        db_url=f"sqlite:///{tmp_path / 'runtime.db'}",
        tenant_id="tenant-a",
        domain_id="domain-x",
        actor_id="human:test-user",
        actor_type="human",
        actor_roles=["dispatch_supervisor"],
    )


def test_template_registry_list_endpoint_returns_versioned_templates(tmp_path: Path) -> None:
    client = _client(tmp_path)
    response = client.get("/api/v1/templates")
    assert response.status_code == 200
    assert response.payload["command"] == "api.templates.list"

    registry = response.payload["registry"]
    assert registry["id"] == "schedule_planning.template_registry"
    assert registry["workflow_id"] == "schedule_planning.v1"
    assert int(registry["version"]) == 1

    template_ids = {
        item["template_id"] for item in response.payload["templates"]
    }
    assert TEMPLATE_IDS.issubset(template_ids)


def test_template_download_endpoint_returns_expected_bytes(tmp_path: Path) -> None:
    client = _client(tmp_path)
    template_id = "schedule.stage05.draft_schedule.workbook.empty.v1"
    response = client.get(f"/api/v1/templates/{template_id}/download")
    assert response.status_code == 200
    assert response.payload["command"] == "api.templates.download"
    template = response.payload["template"]
    assert template["template_id"] == template_id

    raw = base64.b64decode(response.payload["content_base64"])
    assert len(raw) == int(response.payload["byte_size"])
    expected_path = REPO_ROOT / template["file_path"]
    assert expected_path.exists()
    assert raw == expected_path.read_bytes()


def test_template_download_endpoint_returns_not_found_for_unknown_template(tmp_path: Path) -> None:
    client = _client(tmp_path)
    response = client.get("/api/v1/templates/does-not-exist/download")
    assert response.status_code == 404
    assert response.payload["error"]["code"] == "template_not_found"

