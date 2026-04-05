from __future__ import annotations

from pathlib import Path

from tests.runtime.helpers.runtime_api import RuntimeApiClient


def _client(tmp_path: Path) -> RuntimeApiClient:
    return RuntimeApiClient(
        db_url=str(tmp_path / "demo_schedule_workpage.db"),
        tenant_id="tenant-a",
        domain_id="domain-x",
        actor_id="human:ops-manager-2",
        actor_type="human",
        actor_roles=["operations_manager", "dispatch_supervisor", "schedule_planner"],
    )


def test_schedule_demo_workpage_alias_route_is_retired(tmp_path: Path) -> None:
    client = _client(tmp_path)

    response = client.get("/api/v1/workpages/demo/schedule-v0")

    assert response.status_code == 404
    assert response.payload["error"]["code"] == "not_found"


def test_schedule_demo_workpage_unknown_id_stays_not_found(tmp_path: Path) -> None:
    client = _client(tmp_path)

    response = client.get("/api/v1/workpages/demo/unknown-workpage")

    assert response.status_code == 404
    assert response.payload["error"]["code"] == "not_found"
