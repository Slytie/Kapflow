from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path

from tests.runtime.helpers.runtime_api import RuntimeApiClient
from tests.runtime.helpers.runtime_cli import run_cli, stdout_json
from tests.runtime.helpers.workpage_runs import (
    seed_actual_ops_weekly_schedule_run,
    seed_actual_ops_weekly_schedule_run_with_stage04_outputs,
)


EXPECTED_SOURCE_DATASET_KEYS = [
    "planning.route_slot_requirements.workbook",
    "planning.approved_availability.workbook",
    "planning.driver_capabilities.workbook",
    "planning.actual_hours_snapshot.workbook",
    "planning.input_bundle.doc",
]


def _db_url(tmp_path: Path) -> str:
    return f"sqlite:///{tmp_path / 'runtime.db'}"


def _client(tmp_path: Path) -> RuntimeApiClient:
    return RuntimeApiClient(
        db_url=_db_url(tmp_path),
        tenant_id="tenant-a",
        domain_id="domain-x",
        actor_id="human:ops-manager-2",
        actor_type="human",
        actor_roles=["operations_manager", "dispatch_supervisor", "schedule_planner"],
    )


def _other_scope_client(tmp_path: Path) -> RuntimeApiClient:
    return RuntimeApiClient(
        db_url=_db_url(tmp_path),
        tenant_id="tenant-b",
        domain_id="domain-y",
        actor_id="human:ops-manager-9",
        actor_type="human",
        actor_roles=["operations_manager"],
    )


def _action_by_id(
    actions: list[dict[str, object]],
    action_id: str,
) -> dict[str, object]:
    return next(action for action in actions if action["action_id"] == action_id)


def _table_section_by_id(
    sections: list[dict[str, object]],
    table_id: str,
) -> dict[str, object]:
    return next(
        section
        for section in sections
        if section.get("kind") == "table" and section.get("table_id") == table_id
    )


def _route_demand_artifact_path(workflow_run_id: str, artifact_version_id: str) -> str:
    return (
        f"/api/v1/workpages/workflow-runs/{workflow_run_id}/route-demand-v0/"
        f"artifacts/{artifact_version_id}"
    )


def _route_demand_save_and_run_path(workflow_run_id: str, artifact_version_id: str) -> str:
    return f"{_route_demand_artifact_path(workflow_run_id, artifact_version_id)}/save-and-run"


def _route_demand_submit_rows_from_contract(
    payload: dict[str, object],
) -> list[dict[str, int | str]]:
    day_cards = payload["calculations"]["day_cards"]
    assert isinstance(day_cards, list)
    return [
        {
            "service_date": str(row["service_date"]),
            "planned_route_count": int(row["planned_route_count"]),
        }
        for row in day_cards
    ]


def _prepare_existing_week_route_demand_coverage(
    *,
    workflow_run_id: str,
    route_demand_artifact_version_id: str,
    client: RuntimeApiClient,
    route_count_delta: int = 1,
) -> dict[str, object]:
    contract = client.get(
        _route_demand_artifact_path(workflow_run_id, route_demand_artifact_version_id)
    )
    assert contract.status_code == 200, contract.payload
    submit_rows = _route_demand_submit_rows_from_contract(contract.payload)
    submit_rows[0]["planned_route_count"] = (
        int(submit_rows[0]["planned_route_count"]) + route_count_delta
    )
    saved_and_ran = client.post(
        _route_demand_save_and_run_path(workflow_run_id, route_demand_artifact_version_id),
        payload={
            "daily_demand_rows": submit_rows,
            "idempotency_key": "api:workpages:run-schedule:route-demand-coverage:prepare",
        },
    )
    assert saved_and_ran.status_code == 200, saved_and_ran.payload
    coverage_context = saved_and_ran.payload["route_demand_coverage_context"]
    assert isinstance(coverage_context, dict)
    return coverage_context


def test_schedule_workflow_run_workpage_contract_returns_run_backed_projection(
    tmp_path: Path,
) -> None:
    seed = seed_actual_ops_weekly_schedule_run(
        db_url=_db_url(tmp_path),
        tenant_id="tenant-a",
        domain_id="domain-x",
        run_tag="api:workpages:run-schedule:happy",
    )
    workflow_run_id = str(seed["workflow_run_id"])
    client = _client(tmp_path)

    response = client.get(f"/api/v1/workpages/workflow-runs/{workflow_run_id}/schedule-v0")
    assert response.status_code == 200

    payload = response.payload
    assert payload["status"] == "ok"
    assert payload["command"] == "api.workpages.workflow_run"
    assert payload["draft_resolution"] is None

    workpage = payload["workpage"]
    assert workpage["workpage_id"] == "schedule-v0"
    assert workpage["version"] == 2
    assert workpage["title"] == "Weekly schedule review"
    assert workpage["mode"] == "example"
    assert workpage["workflow_id"] == "weekly_schedule_planning.v1"
    assert workpage["dataset_key"] == "planning.input_bundle.doc"
    assert workpage["source_artifact_version_id"] is None
    assert workpage["source_examples"] == {}

    source = payload["source"]
    assert source["mode"] == "run_projection"
    assert source["primary_dataset_key"] is None
    assert source["source_dataset_keys"] == EXPECTED_SOURCE_DATASET_KEYS
    assert source["source_artifact_version_id"] is None
    assert source["source_refs"] == [
        f"/api/v1/artifacts/{seed['artifacts_by_kind']['planning.route_slot_requirements.workbook']['artifact_version_id']}",
        f"/api/v1/artifacts/{seed['artifacts_by_kind']['planning.approved_availability.workbook']['artifact_version_id']}",
        f"/api/v1/artifacts/{seed['artifacts_by_kind']['planning.driver_capabilities.workbook']['artifact_version_id']}",
        f"/api/v1/artifacts/{seed['artifacts_by_kind']['planning.actual_hours_snapshot.workbook']['artifact_version_id']}",
    ]

    freshness = payload["freshness"]
    assert freshness["source_kind"] == "workflow_run_projection"
    assert freshness["source_version"].startswith("bundle-")
    assert freshness["generated_at"]

    run_context = payload["run_context"]
    assert run_context == {
        "workflow_run_id": workflow_run_id,
        "workflow_id": "weekly_schedule_planning.v1",
        "workflow_version": "v1",
        "partition_key": "PW-2026-W13",
        "logical_date": "2026-03-22",
        "activation_key": "api:workpages:run-schedule:happy:weekly-schedule-workpage",
        "state": "OPEN",
    }

    sections = workpage["sections"]
    assert [section["table_id"] for section in sections if section["kind"] == "table"] == [
        "day_demand",
        "selected_day_preview",
        "driver_roster",
        "assignment_rows",
        "reserve_rows",
    ]
    assert [section["kind"] for section in sections] == [
        "summary_cards",
        "table",
        "table",
        "table",
        "schedule_heatmap",
        "note_panel",
        "form",
        "table",
        "table",
        "history_stub",
    ]
    heatmap_section = next(section for section in sections if section["kind"] == "schedule_heatmap")
    assert heatmap_section["service_dates"]
    assert heatmap_section["people"]
    heatmap_cells = [
        cell
        for person in heatmap_section["people"]
        for cell in person["cells"]
    ]
    assert heatmap_cells
    assert all("preference_state" in cell for cell in heatmap_cells)
    assert {cell["preference_state"] for cell in heatmap_cells} == {"unset"}
    assert _table_section_by_id(sections, "assignment_rows")["rows"]
    assert _table_section_by_id(sections, "reserve_rows")["rows"]

    summary = workpage["summary"]
    assert summary["planning_week_id"] == "PW-2026-W13"
    assert summary["operational_week_start"] == "2026-03-22"
    assert summary["service_area"] == "Pitt Meadows"
    assert summary["station_code"] == "DVC4"
    assert summary["total_routes_required"] == 134
    assert summary["drivers_in_scope"] == 51
    assert summary["on_call_target_per_day"] == 4
    assert summary["excess_capacity_target_per_day"] == 3

    warnings = workpage["validation"]["warnings"]
    assert warnings == [
        "This workflow-run-backed schedule projection is built from canonical weekly-planning input artifacts for the selected run.",
        "Selected-day controls are local what-if inputs only and do not claim ownership of live dispatch truth.",
    ]

    assert payload["artifact_state"] == {
        "state_kind": "run_projection",
        "artifact_kind": "planning.draft_weekly_schedule.workbook",
        "editable": False,
        "current_artifact_version_id": None,
        "latest_artifact_version_id": None,
        "accepted_artifact_version_id": None,
    }
    assert payload["dependencies"] == [
        {
            "dependency_key": "route_slot_requirements",
            "artifact_kind": "planning.route_slot_requirements.workbook",
            "artifact_version_id": seed["artifacts_by_kind"]["planning.route_slot_requirements.workbook"]["artifact_version_id"],
            "impact_class": "hard",
            "state": "resolved",
            "source_ref": f"/api/v1/artifacts/{seed['artifacts_by_kind']['planning.route_slot_requirements.workbook']['artifact_version_id']}",
        },
        {
            "dependency_key": "approved_availability",
            "artifact_kind": "planning.approved_availability.workbook",
            "artifact_version_id": seed["artifacts_by_kind"]["planning.approved_availability.workbook"]["artifact_version_id"],
            "impact_class": "hard",
            "state": "resolved",
            "source_ref": f"/api/v1/artifacts/{seed['artifacts_by_kind']['planning.approved_availability.workbook']['artifact_version_id']}",
        },
        {
            "dependency_key": "driver_capabilities",
            "artifact_kind": "planning.driver_capabilities.workbook",
            "artifact_version_id": seed["artifacts_by_kind"]["planning.driver_capabilities.workbook"]["artifact_version_id"],
            "impact_class": "hard",
            "state": "resolved",
            "source_ref": f"/api/v1/artifacts/{seed['artifacts_by_kind']['planning.driver_capabilities.workbook']['artifact_version_id']}",
        },
        {
            "dependency_key": "actual_hours",
            "artifact_kind": "planning.actual_hours_snapshot.workbook",
            "artifact_version_id": seed["artifacts_by_kind"]["planning.actual_hours_snapshot.workbook"]["artifact_version_id"],
            "impact_class": "hard",
            "state": "resolved",
            "source_ref": f"/api/v1/artifacts/{seed['artifacts_by_kind']['planning.actual_hours_snapshot.workbook']['artifact_version_id']}",
        },
        {
            "dependency_key": "driver_preferences",
            "artifact_kind": "planning.driver_shift_preferences.workbook",
            "artifact_version_id": None,
            "impact_class": "soft",
            "state": "not_available",
            "source_ref": None,
        },
    ]
    calculations = payload["calculations"]
    assert calculations["top_bar"]["days"]
    assert calculations["selected_day"]["service_date"] == "2026-03-24"
    assert calculations["driver_metrics"]
    assert any((day.get("routes_scheduled") or 0) > 0 for day in calculations["top_bar"]["days"])
    assert any(
        (metric.get("scheduled_routes") or 0) > 0 or (metric.get("on_call_shifts") or 0) > 0
        for metric in calculations["driver_metrics"]
    )
    assert all(
        metric["preference_state"] == "unset" for metric in calculations["driver_metrics"]
    )
    assert set(calculations["selected_day"]["available_preference_buckets"]) == {
        "open_to_work",
        "prefer_not_to_work",
        "definitely_can_not_work",
        "unset",
    }
    assert any(
        check["check_id"] == "driver_preferences_alignment" and check["blocking"] is False
        for check in calculations["checks"]
    )
    assert payload["draft_lineage"] == {
        "current_artifact_version_id": None,
        "latest_artifact_version_id": None,
        "previous_artifact_version_id": None,
        "recent_versions": [],
    }
    assert payload["artifact_history"] is None
    assert payload.get("route_demand_coverage_context") is None
    assert payload["accepted_series"] == {
        "series_key": "weekly_schedule_planning.v1:dvc4:pitt-meadows",
        "current_artifact_version_id": None,
        "previous_artifact_version_id": None,
        "next_artifact_version_id": None,
        "entries": [],
    }
    actions = payload["actions"]
    open_latest_draft = _action_by_id(actions, "workpage.schedule-v0.open_latest_draft")
    assert open_latest_draft == {
        "action_id": "workpage.schedule-v0.open_latest_draft",
        "kind": "open_latest_draft",
        "label": "Open schedule draft",
        "state": "unavailable",
        "workpage_kind": "schedule-v0",
        "artifact_version_id": None,
        "route": None,
        "action_ref": {
            "action_id": "workpage.schedule-v0.open_latest_draft",
            "workpage_kind": "schedule-v0",
            "workflow_run_id": workflow_run_id,
            "artifact_version_id": None,
            "subject": None,
        },
    }
    open_route_demand = _action_by_id(actions, "workpage.route-demand-v0.open_latest")
    assert open_route_demand == {
        "action_id": "workpage.route-demand-v0.open_latest",
        "kind": "open_latest",
        "label": "Open route demand",
        "state": "available",
        "workpage_kind": "route-demand-v0",
        "artifact_version_id": seed["artifacts_by_kind"]["planning.route_slot_requirements.workbook"]["artifact_version_id"],
        "route": (
            f"/runs/{workflow_run_id}/workpages/route-demand-v0/artifacts/"
            f"{seed['artifacts_by_kind']['planning.route_slot_requirements.workbook']['artifact_version_id']}"
        ),
        "action_ref": {
            "action_id": "workpage.route-demand-v0.open_latest",
            "workpage_kind": "route-demand-v0",
            "workflow_run_id": workflow_run_id,
            "artifact_version_id": seed["artifacts_by_kind"]["planning.route_slot_requirements.workbook"]["artifact_version_id"],
            "subject": None,
        },
    }
    create_snapshot = _action_by_id(actions, "workpage.driver-preferences-v0.create_snapshot")
    assert create_snapshot == {
        "action_id": "workpage.driver-preferences-v0.create_snapshot",
        "kind": "create_snapshot",
        "label": "Create preferences snapshot",
        "state": "available",
        "workpage_kind": "driver-preferences-v0",
        "artifact_version_id": None,
        "route": None,
        "create_path": (
            f"/api/v1/workpages/workflow-runs/{workflow_run_id}/"
            "driver-preferences-v0/snapshots"
        ),
        "action_ref": {
            "action_id": "workpage.driver-preferences-v0.create_snapshot",
            "workpage_kind": "driver-preferences-v0",
            "workflow_run_id": workflow_run_id,
            "artifact_version_id": None,
            "subject": None,
        },
    }


def test_schedule_workflow_run_workpage_prefers_latest_draft_rows_when_present(
    tmp_path: Path,
) -> None:
    seeded = seed_actual_ops_weekly_schedule_run_with_stage04_outputs(
        db_url=_db_url(tmp_path),
        tenant_id="tenant-a",
        domain_id="domain-x",
        run_tag="api:workpages:run-schedule:latest-draft",
    )
    workflow_run_id = str(seeded["workflow_run_id"])
    latest_draft_artifact_id = str(
        seeded["stage04_outputs"]["draft_workbook"]["artifact_version_id"]
    )
    client = _client(tmp_path)

    response = client.get(f"/api/v1/workpages/workflow-runs/{workflow_run_id}/schedule-v0")
    assert response.status_code == 200, response.payload

    payload = response.payload
    assert payload["freshness"]["source_version"] == latest_draft_artifact_id
    assert payload["artifact_state"]["latest_artifact_version_id"] == latest_draft_artifact_id
    assert _action_by_id(payload["actions"], "workpage.schedule-v0.open_latest_draft") == {
        "action_id": "workpage.schedule-v0.open_latest_draft",
        "kind": "open_latest_draft",
        "label": "Open schedule draft",
        "state": "available",
        "workpage_kind": "schedule-v0",
        "artifact_version_id": latest_draft_artifact_id,
        "route": f"/runs/{workflow_run_id}/workpages/schedule-v0/artifacts/{latest_draft_artifact_id}",
        "action_ref": {
            "action_id": "workpage.schedule-v0.open_latest_draft",
            "workpage_kind": "schedule-v0",
            "workflow_run_id": workflow_run_id,
            "artifact_version_id": latest_draft_artifact_id,
            "subject": None,
        },
    }

    sections = payload["workpage"]["sections"]
    assert _table_section_by_id(sections, "assignment_rows")["rows"]
    assert _table_section_by_id(sections, "reserve_rows")["rows"]
    assert next(section for section in sections if section["kind"] == "schedule_heatmap")["people"]


def test_schedule_workflow_run_workpage_returns_route_demand_coverage_context_when_latest_draft_is_behind(
    tmp_path: Path,
) -> None:
    seeded = seed_actual_ops_weekly_schedule_run_with_stage04_outputs(
        db_url=_db_url(tmp_path),
        tenant_id="tenant-a",
        domain_id="domain-x",
        run_tag="api:workpages:run-schedule:route-demand-recovery",
    )
    workflow_run_id = str(seeded["workflow_run_id"])
    route_demand_artifact_version_id = str(
        seeded["artifacts_by_kind"]["planning.route_slot_requirements.workbook"][
            "artifact_version_id"
        ]
    )
    client = _client(tmp_path)
    expected_context = _prepare_existing_week_route_demand_coverage(
        workflow_run_id=workflow_run_id,
        route_demand_artifact_version_id=route_demand_artifact_version_id,
        client=client,
        route_count_delta=2,
    )

    response = client.get(f"/api/v1/workpages/workflow-runs/{workflow_run_id}/schedule-v0")
    assert response.status_code == 200, response.payload
    assert response.payload["route_demand_coverage_context"] == expected_context


def test_schedule_workflow_run_workpage_reads_are_stable_except_for_generated_at(
    tmp_path: Path,
) -> None:
    seed = seed_actual_ops_weekly_schedule_run(
        db_url=_db_url(tmp_path),
        tenant_id="tenant-a",
        domain_id="domain-x",
        run_tag="api:workpages:run-schedule:stable",
    )
    client = _client(tmp_path)
    path = f"/api/v1/workpages/workflow-runs/{seed['workflow_run_id']}/schedule-v0"

    first = client.get(path)
    second = client.get(path)

    assert first.status_code == 200
    assert second.status_code == 200
    assert _without_generated_at(first.payload) == _without_generated_at(second.payload)


def test_schedule_workflow_run_workpage_unknown_kind_returns_404(tmp_path: Path) -> None:
    seed = seed_actual_ops_weekly_schedule_run(
        db_url=_db_url(tmp_path),
        tenant_id="tenant-a",
        domain_id="domain-x",
        run_tag="api:workpages:run-schedule:wrong-kind",
    )
    client = _client(tmp_path)

    response = client.get(
        f"/api/v1/workpages/workflow-runs/{seed['workflow_run_id']}/unknown-workpage"
    )
    assert response.status_code == 404
    assert response.payload["error"]["code"] == "workpage_not_found"
    assert response.payload["error"]["details"] == {
        "workflow_run_id": seed["workflow_run_id"],
        "workpage_id": "unknown-workpage",
    }


def test_schedule_workflow_run_workpage_rejects_non_weekly_run(tmp_path: Path) -> None:
    run_cli("--db-url", _db_url(tmp_path), "init-db")
    created = run_cli(
        "--db-url",
        _db_url(tmp_path),
        "runs",
        "create",
        "--json",
        json.dumps(
            {
                "workflow_id": "dispatch_reporting.v1",
                "workflow_version": "v1",
                "tenant_id": "tenant-a",
                "domain_id": "domain-x",
                "partition_key": "SD-2026-03-16",
                "logical_date": "2026-03-16",
                "activation_key": "api:workpages:run-schedule:wrong-workflow",
                "idempotency_key": "api:workpages:run-schedule:wrong-workflow:runs.create",
            },
            separators=(",", ":"),
        ),
    )
    workflow_run_id = str(stdout_json(created)["workflow_run"]["workflow_run_id"])
    client = _client(tmp_path)

    response = client.get(f"/api/v1/workpages/workflow-runs/{workflow_run_id}/schedule-v0")
    assert response.status_code == 404
    assert response.payload["error"]["code"] == "workpage_not_found"
    assert response.payload["error"]["details"] == {
        "workflow_run_id": workflow_run_id,
        "workpage_id": "schedule-v0",
    }


def test_schedule_workflow_run_workpage_missing_stage04_inputs_returns_409(
    tmp_path: Path,
) -> None:
    run_cli("--db-url", _db_url(tmp_path), "init-db")
    created = run_cli(
        "--db-url",
        _db_url(tmp_path),
        "runs",
        "create",
        "--json",
        json.dumps(
            {
                "workflow_id": "weekly_schedule_planning.v1",
                "workflow_version": "v1",
                "tenant_id": "tenant-a",
                "domain_id": "domain-x",
                "partition_key": "PW-2026-W13",
                "logical_date": "2026-03-22",
                "activation_key": "api:workpages:run-schedule:missing-inputs",
                "idempotency_key": "api:workpages:run-schedule:missing-inputs:runs.create",
            },
            separators=(",", ":"),
        ),
    )
    workflow_run_id = str(stdout_json(created)["workflow_run"]["workflow_run_id"])
    client = _client(tmp_path)

    response = client.get(f"/api/v1/workpages/workflow-runs/{workflow_run_id}/schedule-v0")
    assert response.status_code == 409
    assert response.payload["error"]["code"] == "workpage_projection_unavailable"
    assert response.payload["error"]["details"] == {
        "workflow_run_id": workflow_run_id,
        "workpage_id": "schedule-v0",
        "missing_dataset_keys": [
            "planning.route_slot_requirements.workbook",
            "planning.driver_capabilities.workbook",
        ],
    }


def test_schedule_workflow_run_workpage_cross_scope_access_fails_closed(
    tmp_path: Path,
) -> None:
    seed = seed_actual_ops_weekly_schedule_run(
        db_url=_db_url(tmp_path),
        tenant_id="tenant-a",
        domain_id="domain-x",
        run_tag="api:workpages:run-schedule:cross-scope",
    )
    denied = _other_scope_client(tmp_path).get(
        f"/api/v1/workpages/workflow-runs/{seed['workflow_run_id']}/schedule-v0"
    )
    assert denied.status_code == 404
    assert denied.payload["error"]["code"] == "workflow_run_not_found"


def _without_generated_at(payload: dict[str, object]) -> dict[str, object]:
    copied = deepcopy(payload)
    freshness = copied.get("freshness")
    assert isinstance(freshness, dict)
    freshness.pop("generated_at", None)
    return copied
