from __future__ import annotations

from pathlib import Path

from onetruth.application.services.logistics_local_demo import (
    seed_combined_logistics_local_demo,
)
from onetruth.infrastructure.db.session import open_sqlite_connection
from onetruth.infrastructure.events.event_store import create_sqlite_substrate
from tests.runtime.api.test_weekly_stage04_openai_agent_api import _mock_stage04_runner
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


def test_combined_local_demo_story_endpoint_includes_scratch_and_review_ready_runs(
    tmp_path: Path,
) -> None:
    db_url = _db_url(tmp_path)
    with open_sqlite_connection(db_url) as connection:
        create_sqlite_substrate(connection)
        seeded = seed_combined_logistics_local_demo(
            connection,
            db_url=db_url,
            planning_week_id="PW-2026-W10",
            service_date_id="SD-2026-03-06",
        )

    client = _client(tmp_path)
    response = client.get(
        "/api/v1/stories/logistics-three-workflow",
        query={
            "planning_week_id": "PW-2026-W10",
            "service_date_id": "SD-2026-03-06",
        },
    )
    assert response.status_code == 200, response.payload

    story = response.payload["story"]
    linked = story["linked_workflow_runs"]
    assert linked["summary"] == {
        "weekly_schedule_planning_count": 2,
        "live_dispatch_count": 0,
        "dispatch_reporting_count": 3,
    }

    weekly_runs = linked["weekly_schedule_planning"]
    assert [run["workflow_run_id"] for run in weekly_runs] == [
        seeded["weekly_run_id"],
        seeded["review_ready_weekly_run_id"],
    ]

    reporting_runs = linked["dispatch_reporting"]
    assert [run["workflow_run_id"] for run in reporting_runs] == [
        seeded["prior_reporting_run_id"],
        seeded["reporting_run_id"],
        seeded["review_ready_reporting_run_id"],
    ]

    modules = {module["module_id"]: module for module in story["family_graph"]["modules"]}
    assert modules["weekly_schedule_planning"]["drilldown_kind"] == "run_group"
    assert [ref["workflow_run_id"] for ref in modules["weekly_schedule_planning"]["drilldown_refs"]] == [
        seeded["weekly_run_id"],
        seeded["review_ready_weekly_run_id"],
    ]
    assert modules["dispatch_reporting"]["drilldown_kind"] == "run_group"
    assert [ref["workflow_run_id"] for ref in modules["dispatch_reporting"]["drilldown_refs"]] == [
        seeded["prior_reporting_run_id"],
        seeded["reporting_run_id"],
        seeded["review_ready_reporting_run_id"],
    ]

    work_items = {
        (item["workflow_run_id"], item["stage_id"], item["task_kind"])
        for item in story["board"]["work_items"]
    }
    assert {
        (seeded["review_ready_weekly_run_id"], "Stage04", "weekly_input_intake"),
        (seeded["review_ready_weekly_run_id"], "Stage04", "work_item"),
        (seeded["review_ready_reporting_run_id"], "Stage01", "eos_input_intake"),
    }.issubset(work_items)

    active_work_items = {
        (item["workflow_run_id"], item["stage_id"], item["task_kind"])
        for item in story["board"]["work_items"]
        if str(item["state"]) not in {"COMPLETED", "RESPONDED", "CLOSED", "RESOLVED"}
    }
    assert active_work_items == {
        (seeded["weekly_run_id"], "Stage04", "weekly_input_intake"),
        (seeded["reporting_run_id"], "Stage01", "eos_input_intake"),
        (seeded["review_ready_weekly_run_id"], "Stage05", "final_review"),
        (seeded["review_ready_reporting_run_id"], "Stage04", "final_packet_review"),
    }

    summary = story["official_outputs"]["summary"]
    assert summary["artifact_kind_counts"] == {
        "reporting.final_packet.workbook": 1
    }


def test_combined_local_demo_scratch_weekly_future_week_save_and_run_succeeds(
    tmp_path: Path,
    monkeypatch,
) -> None:
    monkeypatch.setattr(
        "onetruth.application.services.weekly_stage04_openai_agent.build_weekly_stage04_openai_agent_runner_from_env",
        lambda: _mock_stage04_runner(),
    )
    monkeypatch.setenv("ONETRUTH_ARTIFACT_ROOT", str(tmp_path / "artifacts"))
    db_url = _db_url(tmp_path)
    with open_sqlite_connection(db_url) as connection:
        create_sqlite_substrate(connection)
        seeded = seed_combined_logistics_local_demo(
            connection,
            db_url=db_url,
            planning_week_id="PW-2026-W10",
            service_date_id="SD-2026-03-06",
        )

    client = _client(tmp_path)
    created = client.post(
        f"/api/v1/workpages/workflow-runs/{seeded['weekly_run_id']}/route-demand-v0/next-week",
        payload={"idempotency_key": "api:combined-demo:route-demand:add-next-week"},
    )
    assert created.status_code == 200, created.payload
    future_workflow_run_id = str(created.payload["created"]["workflow_run_id"])
    future_artifact_version_id = str(created.payload["created"]["artifact_version_id"])

    future_contract = client.get(
        f"/api/v1/workpages/workflow-runs/{future_workflow_run_id}/"
        f"route-demand-v0/artifacts/{future_artifact_version_id}"
    )
    assert future_contract.status_code == 200, future_contract.payload
    day_cards = future_contract.payload["calculations"]["day_cards"]
    assert isinstance(day_cards, list) and day_cards
    submit_rows = [
        {
            "service_date": str(item["service_date"]),
            "planned_route_count": int(item["planned_route_count"]),
            "on_call_target": int(item["on_call_target"]),
        }
        for item in day_cards
    ]
    submit_rows[0]["on_call_target"] = 1

    saved_and_ran = client.post(
        f"/api/v1/workpages/workflow-runs/{future_workflow_run_id}/"
        f"route-demand-v0/artifacts/{future_artifact_version_id}/save-and-run",
        payload={
            "daily_demand_rows": submit_rows,
            "idempotency_key": "api:combined-demo:route-demand:save-and-run",
        },
    )
    assert saved_and_ran.status_code == 200, saved_and_ran.payload
    assert saved_and_ran.payload["submitted"]["target_workflow_run_id"] == future_workflow_run_id
    assert saved_and_ran.payload["submitted"]["target_schedule_route"] == (
        f"/runs/{future_workflow_run_id}/workpages/schedule-v0"
    )


def test_combined_local_demo_review_ready_weekly_workpages_open_successfully(
    tmp_path: Path,
) -> None:
    db_url = _db_url(tmp_path)
    with open_sqlite_connection(db_url) as connection:
        create_sqlite_substrate(connection)
        seeded = seed_combined_logistics_local_demo(
            connection,
            db_url=db_url,
            planning_week_id="PW-2026-W10",
            service_date_id="SD-2026-03-06",
        )

    client = _client(tmp_path)
    schedule_contract = client.get(
        f"/api/v1/workpages/workflow-runs/{seeded['review_ready_weekly_run_id']}/schedule-v0"
    )
    assert schedule_contract.status_code == 200, schedule_contract.payload
    assert schedule_contract.payload["workpage"]["title"] == "Weekly schedule review"

    driver_preferences_contract = client.get(
        f"/api/v1/workpages/workflow-runs/{seeded['review_ready_weekly_run_id']}/"
        "driver-preferences-v0"
    )
    assert driver_preferences_contract.status_code == 200, driver_preferences_contract.payload
    assert driver_preferences_contract.payload["workpage"]["title"] == "Weekly driver preferences"
