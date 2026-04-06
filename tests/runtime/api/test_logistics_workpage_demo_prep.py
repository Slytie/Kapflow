from __future__ import annotations

from pathlib import Path

from onetruth.application.services.logistics_workpage_demo_prep import (
    prepare_logistics_workpage_demo,
)
from onetruth.infrastructure.db.session import open_sqlite_connection
from onetruth.infrastructure.events.event_store import create_sqlite_substrate
from tests.runtime.helpers.runtime_api import RuntimeApiClient


def _db_url(tmp_path: Path) -> str:
    return f"sqlite:///{tmp_path / 'runtime.db'}"


def _client(tmp_path: Path) -> RuntimeApiClient:
    return RuntimeApiClient(
        db_url=_db_url(tmp_path),
        tenant_id="tenant-logistics",
        domain_id="domain-hub",
        actor_id="human:demo-operator",
        actor_type="human",
        actor_roles=["schedule_planner", "dispatch_supervisor", "operations_manager"],
    )


def _action_by_id(
    actions: list[dict[str, object]],
    action_id: str,
) -> dict[str, object]:
    return next(action for action in actions if action["action_id"] == action_id)


def test_prepare_logistics_workpage_demo_serves_canonical_run_workpages(
    tmp_path: Path,
) -> None:
    db_url = _db_url(tmp_path)
    with open_sqlite_connection(db_url) as connection:
        create_sqlite_substrate(connection)
        prepared = prepare_logistics_workpage_demo(
            connection,
            db_url=db_url,
            planning_week_id="PW-2026-W10",
            service_date_id="SD-2026-03-06",
        )

    weekly_run_id = str(prepared["weekly_run_id"])
    reporting_run_id = str(prepared["reporting_run_id"])
    client = _client(tmp_path)

    schedule = client.get(f"/api/v1/workpages/workflow-runs/{weekly_run_id}/schedule-v0")
    assert schedule.status_code == 200, schedule.payload
    schedule_actions = schedule.payload["actions"]
    assert _action_by_id(schedule_actions, "workpage.schedule-v0.open_latest_draft") == {
        "action_id": "workpage.schedule-v0.open_latest_draft",
        "kind": "open_latest_draft",
        "label": "Open schedule draft",
        "state": "available",
        "workpage_kind": "schedule-v0",
        "artifact_version_id": prepared["schedule_artifact_version_id"],
        "route": prepared["schedule_artifact_url"],
        "action_ref": {
            "action_id": "workpage.schedule-v0.open_latest_draft",
            "workpage_kind": "schedule-v0",
            "workflow_run_id": weekly_run_id,
            "artifact_version_id": prepared["schedule_artifact_version_id"],
            "subject": None,
        },
    }
    assert _action_by_id(schedule_actions, "workpage.route-demand-v0.open_latest") == {
        "action_id": "workpage.route-demand-v0.open_latest",
        "kind": "open_latest",
        "label": "Open route demand",
        "state": "available",
        "workpage_kind": "route-demand-v0",
        "artifact_version_id": prepared["route_demand_artifact_version_id"],
        "route": prepared["route_demand_artifact_url"],
        "action_ref": {
            "action_id": "workpage.route-demand-v0.open_latest",
            "workpage_kind": "route-demand-v0",
            "workflow_run_id": weekly_run_id,
            "artifact_version_id": prepared["route_demand_artifact_version_id"],
            "subject": None,
        },
    }
    assert _action_by_id(schedule_actions, "workpage.driver-preferences-v0.open_latest") == {
        "action_id": "workpage.driver-preferences-v0.open_latest",
        "kind": "open_latest",
        "label": "Open driver preferences",
        "state": "available",
        "workpage_kind": "driver-preferences-v0",
        "artifact_version_id": prepared["driver_preferences_artifact_version_id"],
        "route": prepared["driver_preferences_artifact_url"],
        "action_ref": {
            "action_id": "workpage.driver-preferences-v0.open_latest",
            "workpage_kind": "driver-preferences-v0",
            "workflow_run_id": weekly_run_id,
            "artifact_version_id": prepared["driver_preferences_artifact_version_id"],
            "subject": None,
        },
    }

    route_demand = client.get(
        f"/api/v1/workpages/workflow-runs/{weekly_run_id}/route-demand-v0"
    )
    assert route_demand.status_code == 200, route_demand.payload
    assert route_demand.payload["workpage"]["workpage_id"] == "route-demand-v0"

    driver_preferences = client.get(
        f"/api/v1/workpages/workflow-runs/{weekly_run_id}/driver-preferences-v0"
    )
    assert driver_preferences.status_code == 200, driver_preferences.payload
    assert driver_preferences.payload["workpage"]["workpage_id"] == "driver-preferences-v0"
    assert driver_preferences.payload["artifact_state"] == {
        "state_kind": "run_projection",
        "artifact_kind": "planning.driver_shift_preferences.workbook",
        "editable": False,
        "current_artifact_version_id": None,
        "latest_artifact_version_id": prepared["driver_preferences_artifact_version_id"],
        "accepted_artifact_version_id": None,
    }
    assert _action_by_id(
        driver_preferences.payload["actions"],
        "workpage.driver-preferences-v0.open_latest",
    ) == {
        "action_id": "workpage.driver-preferences-v0.open_latest",
        "kind": "open_latest",
        "label": "Open latest snapshot",
        "state": "available",
        "workpage_kind": "driver-preferences-v0",
        "artifact_version_id": prepared["driver_preferences_artifact_version_id"],
        "route": prepared["driver_preferences_artifact_url"],
        "action_ref": {
            "action_id": "workpage.driver-preferences-v0.open_latest",
            "workpage_kind": "driver-preferences-v0",
            "workflow_run_id": weekly_run_id,
            "artifact_version_id": prepared["driver_preferences_artifact_version_id"],
            "subject": None,
        },
    }

    eod = client.get(f"/api/v1/workpages/workflow-runs/{reporting_run_id}/eod-v0")
    assert eod.status_code == 200, eod.payload
    assert eod.payload["workpage"]["workpage_id"] == "eod-v0"
