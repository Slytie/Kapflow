from __future__ import annotations

import base64
from pathlib import Path

from tests.runtime.helpers.runtime_api import RuntimeApiClient
from tests.runtime.helpers.runtime_cli import REPO_ROOT

SCHEDULE_TEMPLATE_IDS = {
    "schedule.stage05.draft_schedule.doc.empty.v1",
    "schedule.stage05.draft_schedule.workbook.empty.v1",
    "schedule.stage06.supervisor_review.doc.empty.v1",
    "schedule.stage07.exception_board.doc.empty.v1",
    "schedule.stage07.replan_delta.workbook.empty.v1",
}
REPORTING_TEMPLATE_IDS = {
    "dispatch_reporting.stage03.upd_draft.workbook.empty.v1",
    "dispatch_reporting.stage03.upd_draft.workbook.example.v1",
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


def test_template_registry_list_endpoint_returns_multi_workflow_templates(tmp_path: Path) -> None:
    client = _client(tmp_path)
    response = client.get("/api/v1/templates")
    assert response.status_code == 200
    assert response.payload["command"] == "api.templates.list"
    assert response.payload["registry"] is None

    registries = response.payload["registries"]
    assert [item["workflow_id"] for item in registries] == [
        "dispatch_reporting.v1",
        "schedule_planning.v1",
    ]

    template_ids = {
        item["template_id"] for item in response.payload["templates"]
    }
    assert SCHEDULE_TEMPLATE_IDS.issubset(template_ids)
    assert REPORTING_TEMPLATE_IDS.issubset(template_ids)


def test_template_registry_list_endpoint_supports_dispatch_reporting_filter(tmp_path: Path) -> None:
    client = _client(tmp_path)
    response = client.get(
        "/api/v1/templates",
        query={"workflow_id": "dispatch_reporting.v1"},
    )
    assert response.status_code == 200
    assert response.payload["command"] == "api.templates.list"

    registry = response.payload["registry"]
    assert registry["id"] == "dispatch_reporting.template_registry"
    assert registry["workflow_id"] == "dispatch_reporting.v1"
    assert int(registry["version"]) == 1
    assert response.payload["registries"] == [registry]

    template_ids = {
        item["template_id"] for item in response.payload["templates"]
    }
    assert template_ids == REPORTING_TEMPLATE_IDS


def test_template_download_endpoint_returns_expected_bytes_for_dispatch_reporting(
    tmp_path: Path,
) -> None:
    client = _client(tmp_path)
    template_id = "dispatch_reporting.stage03.upd_draft.workbook.empty.v1"
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


def test_template_registry_list_endpoint_surfaces_invalid_catalog_errors(
    tmp_path: Path,
    monkeypatch,
) -> None:
    from onetruth.api.routes import templates as template_routes

    def _boom():
        raise ValueError("duplicate template_id across registries")

    monkeypatch.setattr(template_routes, "load_template_registry_catalog", _boom)

    client = _client(tmp_path)
    response = client.get("/api/v1/templates")
    assert response.status_code == 500
    assert response.payload["error"]["code"] == "template_registry_invalid"
