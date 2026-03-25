from __future__ import annotations

from copy import deepcopy
from pathlib import Path

from tests.runtime.helpers.runtime_api import RuntimeApiClient


EXPECTED_SOURCE_DATASET_KEYS = [
    "planning.route_slot_requirements.workbook",
    "planning.approved_availability.workbook",
    "planning.driver_capabilities.workbook",
    "planning.actual_hours_snapshot.workbook",
    "planning.input_bundle.doc",
]

EXPECTED_SOURCE_REFS = [
    "docs/workflows/weekly_schedule_planning/v1/examples/route_slot_requirements_actual_ops_lab_v2.yaml",
    "docs/workflows/weekly_schedule_planning/v1/examples/approved_availability_actual_ops_lab_v1.yaml",
    "docs/workflows/weekly_schedule_planning/v1/examples/driver_capabilities_actual_ops_lab_v1.yaml",
    "docs/workflows/weekly_schedule_planning/v1/examples/actual_hours_snapshot_actual_ops_lab_v1.yaml",
    "docs/workflows/weekly_schedule_planning/v1/examples/stage04_input_bundle_actual_ops_lab_v2.yaml",
]


def _client(tmp_path: Path) -> RuntimeApiClient:
    return RuntimeApiClient(
        db_url=str(tmp_path / "demo_schedule_workpage.db"),
        tenant_id="tenant-a",
        domain_id="domain-x",
        actor_id="human:ops-manager-2",
        actor_type="human",
        actor_roles=["operations_manager", "dispatch_supervisor", "schedule_planner"],
    )


def test_schedule_demo_workpage_contract_returns_server_owned_wrapper(tmp_path: Path) -> None:
    client = _client(tmp_path)

    response = client.get("/api/v1/workpages/demo/schedule-v0")
    assert response.status_code == 200

    payload = response.payload
    assert payload["status"] == "ok"
    assert payload["command"] == "api.workpages.demo"

    workpage = payload["workpage"]
    assert workpage["workpage_id"] == "schedule-v0"
    assert workpage["version"] == 2
    assert workpage["title"] == "Weekly schedule review"
    assert workpage["mode"] == "example"
    assert workpage["workflow_id"] == "weekly_schedule_planning.v1"
    assert workpage["dataset_key"] == "planning.input_bundle.doc"
    assert workpage["source_artifact_version_id"] is None

    source = payload["source"]
    assert source["mode"] == "demo"
    assert source["primary_dataset_key"] is None
    assert source["source_dataset_keys"] == EXPECTED_SOURCE_DATASET_KEYS
    assert source["source_artifact_version_id"] is None
    assert source["source_refs"] == EXPECTED_SOURCE_REFS

    freshness = payload["freshness"]
    assert freshness["source_kind"] == "repo_example_bundle"
    assert freshness["source_version"] == "weekly_stage04_actual_ops_lab_v2"
    assert freshness["generated_at"]

    sections = workpage["sections"]
    assert [section["table_id"] for section in sections if section["kind"] == "table"] == [
        "day_demand",
        "selected_day_preview",
        "driver_roster",
    ]
    assert [section["kind"] for section in sections] == [
        "summary_cards",
        "table",
        "table",
        "table",
        "note_panel",
        "form",
        "history_stub",
    ]

    summary = workpage["summary"]
    assert summary["planning_week_id"] == "PW-2026-W13"
    assert summary["operational_week_start"] == "2026-03-22"
    assert summary["service_area"] == "Pitt Meadows"
    assert summary["station_code"] == "DVC4"
    assert summary["total_routes_required"] == 134
    assert summary["drivers_in_scope"] == 51
    assert summary["on_call_target_per_day"] == 4
    assert summary["excess_capacity_target_per_day"] == 3

    day_demand_section = next(
        section for section in sections if section.get("table_id") == "day_demand"
    )
    day_demand_by_date = {
        row["service_date"]: row for row in day_demand_section["rows"]
    }
    assert day_demand_by_date["2026-03-23"]["planned_route_count"] == 23
    assert (
        day_demand_by_date["2026-03-23"]["note"]
        == "Holdout route total override; Highest-demand day in the example week"
    )
    assert (
        day_demand_by_date["2026-03-24"]["note"]
        == "Holdout route total override; Selected-day preview default"
    )

    preview_section = next(
        section for section in sections if section.get("table_id") == "selected_day_preview"
    )
    assert preview_section["rows"] == [
        {
            "service_date": "2026-03-24",
            "routes_required": 20,
            "drivers_available": 24,
            "projected_on_call_needed": 4,
            "open_questions": "Confirm late requests and final on-call posture before day-of handoff.",
        }
    ]

    roster_section = next(
        section for section in sections if section.get("table_id") == "driver_roster"
    )
    assert [row["driver_name"] for row in roster_section["rows"]] == [
        "Parampreet Singh",
        "Balwinder Singh",
        "Navjot Singh",
    ]
    parampreet_row = roster_section["rows"][0]
    assert parampreet_row["previous_week_minutes"] == 1710
    assert (
        parampreet_row["availability_summary"]
        == "preferred 4 days; on-call-only 1 day; avoid-if-possible 2 days"
    )


def test_schedule_demo_workpage_reads_are_stable_except_for_generated_at(tmp_path: Path) -> None:
    client = _client(tmp_path)

    first = client.get("/api/v1/workpages/demo/schedule-v0")
    second = client.get("/api/v1/workpages/demo/schedule-v0")

    assert first.status_code == 200
    assert second.status_code == 200
    assert _without_generated_at(first.payload) == _without_generated_at(second.payload)


def test_schedule_demo_workpage_unknown_id_returns_404(tmp_path: Path) -> None:
    client = _client(tmp_path)

    response = client.get("/api/v1/workpages/demo/unknown-workpage")
    assert response.status_code == 404
    assert response.payload["error"]["code"] == "workpage_not_found"
    assert response.payload["error"]["details"] == {"workpage_id": "unknown-workpage"}


def _without_generated_at(payload: dict[str, object]) -> dict[str, object]:
    copied = deepcopy(payload)
    freshness = copied.get("freshness")
    assert isinstance(freshness, dict)
    freshness.pop("generated_at", None)
    return copied
