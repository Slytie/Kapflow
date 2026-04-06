from __future__ import annotations

import json
from pathlib import Path

from onetruth.infrastructure.db.session import open_sqlite_connection
from tests.runtime.helpers.runtime_api import RuntimeApiClient
from tests.runtime.helpers.workpage_runs import (
    seed_actual_ops_weekly_schedule_run,
    seed_actual_ops_weekly_schedule_run_with_stage04_outputs,
)


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


def _query_rows(db_url: str, sql: str, params: tuple[object, ...] = ()) -> list[dict[str, object]]:
    with open_sqlite_connection(db_url) as connection:
        rows = connection.execute(sql, params).fetchall()
    return [dict(row) for row in rows]


def _action_ref(
    *,
    action_id: str,
    workpage_kind: str,
    workflow_run_id: str,
    artifact_version_id: str | None,
) -> dict[str, object]:
    return {
        "action_id": action_id,
        "workpage_kind": workpage_kind,
        "workflow_run_id": workflow_run_id,
        "artifact_version_id": artifact_version_id,
        "subject": None,
    }


def _route_demand_submit_rows(route_artifact: dict[str, object]) -> list[dict[str, object]]:
    metadata_json = route_artifact["metadata_json"]
    assert isinstance(metadata_json, dict)
    rows = []
    for item in metadata_json["daily_demand_rows"]:
        rows.append(
            {
                "service_date": str(item[0]),
                "planned_route_count": int(item[1]),
            }
        )
    return rows


def test_route_demand_run_workpage_contract_returns_latest_route_demand_projection(
    tmp_path: Path,
) -> None:
    seeded = seed_actual_ops_weekly_schedule_run(
        db_url=_db_url(tmp_path),
        tenant_id="tenant-a",
        domain_id="domain-x",
        run_tag="api:workpages:route-demand:run",
    )
    workflow_run_id = str(seeded["workflow_run_id"])
    latest_route_artifact_id = str(
        seeded["artifacts_by_kind"]["planning.route_slot_requirements.workbook"]["artifact_version_id"]
    )
    client = _client(tmp_path)

    response = client.get(
        f"/api/v1/workpages/workflow-runs/{workflow_run_id}/route-demand-v0"
    )
    assert response.status_code == 200, response.payload

    payload = response.payload
    assert payload["workpage"]["workpage_id"] == "route-demand-v0"
    assert payload["workpage"]["version"] == 1
    assert payload["source"] == {
        "mode": "run_projection",
        "primary_dataset_key": "planning.route_slot_requirements.workbook",
        "source_dataset_keys": ["planning.route_slot_requirements.workbook"],
        "source_artifact_version_id": None,
        "source_refs": [f"/api/v1/artifacts/{latest_route_artifact_id}"],
    }
    assert payload["artifact_state"] == {
        "state_kind": "run_projection",
        "artifact_kind": "planning.route_slot_requirements.workbook",
        "editable": False,
        "current_artifact_version_id": None,
        "latest_artifact_version_id": latest_route_artifact_id,
        "accepted_artifact_version_id": None,
    }
    assert payload["artifact_history"] is None
    assert payload["schedule_impact"] == {
        "latest_schedule_draft_artifact_version_id": None,
        "dependency_state": "no_draft",
        "schedule_state": "no_draft",
        "refresh_task": None,
    }
    assert payload["actions"] == [
        {
            "action_id": "workpage.route-demand-v0.open_latest",
            "kind": "open_latest",
            "label": "Open route demand",
            "state": "available",
            "workpage_kind": "route-demand-v0",
            "artifact_version_id": latest_route_artifact_id,
            "route": f"/runs/{workflow_run_id}/workpages/route-demand-v0/artifacts/{latest_route_artifact_id}",
            "action_ref": _action_ref(
                action_id="workpage.route-demand-v0.open_latest",
                workpage_kind="route-demand-v0",
                workflow_run_id=workflow_run_id,
                artifact_version_id=latest_route_artifact_id,
            ),
        }
    ]
    assert payload["calculations"]["day_cards"]


def test_route_demand_artifact_workpage_uses_canonical_route_and_retires_alias(
    tmp_path: Path,
) -> None:
    seeded = seed_actual_ops_weekly_schedule_run_with_stage04_outputs(
        db_url=_db_url(tmp_path),
        tenant_id="tenant-a",
        domain_id="domain-x",
        run_tag="api:workpages:route-demand:artifact",
    )
    workflow_run_id = str(seeded["workflow_run_id"])
    route_artifact = seeded["artifacts_by_kind"]["planning.route_slot_requirements.workbook"]
    route_artifact_id = str(route_artifact["artifact_version_id"])
    client = _client(tmp_path)

    initial = client.get(
        f"/api/v1/workpages/workflow-runs/{workflow_run_id}/"
        f"route-demand-v0/artifacts/{route_artifact_id}"
    )
    assert initial.status_code == 200, initial.payload
    initial_payload = initial.payload
    assert initial_payload["workpage"]["workpage_id"] == "route-demand-v0"
    assert initial_payload["artifact_state"]["editable"] is True
    assert initial_payload["artifact_state"]["current_artifact_version_id"] == route_artifact_id
    assert initial_payload["artifact_history"]["current_artifact_version_id"] == route_artifact_id
    assert initial_payload["artifact_history"]["latest_artifact_version_id"] == route_artifact_id
    assert initial_payload["artifact_history"]["previous_artifact_version_id"] is None
    assert initial_payload["artifact_history"]["next_artifact_version_id"] is None
    assert initial_payload["artifact_history"]["entries"] == [
        {
            "artifact_version_id": route_artifact_id,
            "workflow_run_id": workflow_run_id,
            "artifact_kind": "planning.route_slot_requirements.workbook",
            "created_at": route_artifact["created_at"],
            "lineage_note": route_artifact["lineage_note"],
            "supersedes_artifact_version_id": None,
            "route": (
                f"/runs/{workflow_run_id}/workpages/route-demand-v0/artifacts/{route_artifact_id}"
            ),
        }
    ]
    assert initial_payload["actions"] == [
        {
            "action_id": "workpage.route-demand-v0.save",
            "kind": "save",
            "label": "Save route demand",
            "state": "available",
            "workpage_kind": "route-demand-v0",
            "artifact_version_id": route_artifact_id,
            "submit_path": f"/api/v1/workpages/workflow-runs/{workflow_run_id}/route-demand-v0/artifacts/{route_artifact_id}/submit",
            "action_ref": _action_ref(
                action_id="workpage.route-demand-v0.save",
                workpage_kind="route-demand-v0",
                workflow_run_id=workflow_run_id,
                artifact_version_id=route_artifact_id,
            ),
            "disabled_reason": None,
        }
    ]
    alias_read = client.get(f"/api/v1/workpages/artifacts/{route_artifact_id}")
    assert alias_read.status_code == 404
    assert alias_read.payload["error"]["code"] == "not_found"

    submit_rows = _route_demand_submit_rows(route_artifact)
    submit_rows[0]["planned_route_count"] = int(submit_rows[0]["planned_route_count"]) + 2
    submitted = client.post(
        f"/api/v1/workpages/workflow-runs/{workflow_run_id}/route-demand-v0/artifacts/{route_artifact_id}/submit",
        payload={
            "daily_demand_rows": submit_rows,
            "idempotency_key": "api:workpages:route-demand:artifact:submit",
        },
    )
    assert submitted.status_code == 200, submitted.payload
    latest_route_artifact_id = str(submitted.payload["submitted"]["artifact_version_id"])

    historical = client.get(
        f"/api/v1/workpages/workflow-runs/{workflow_run_id}/route-demand-v0/artifacts/{route_artifact_id}"
    )
    assert historical.status_code == 200, historical.payload
    historical_payload = historical.payload
    assert historical_payload["artifact_state"] == {
        "state_kind": "artifact_projection",
        "artifact_kind": "planning.route_slot_requirements.workbook",
        "editable": False,
        "current_artifact_version_id": route_artifact_id,
        "latest_artifact_version_id": latest_route_artifact_id,
        "accepted_artifact_version_id": None,
    }
    assert historical_payload["artifact_history"]["current_artifact_version_id"] == route_artifact_id
    assert historical_payload["artifact_history"]["latest_artifact_version_id"] == latest_route_artifact_id
    assert historical_payload["artifact_history"]["previous_artifact_version_id"] is None
    assert historical_payload["artifact_history"]["next_artifact_version_id"] == latest_route_artifact_id
    assert [entry["artifact_version_id"] for entry in historical_payload["artifact_history"]["entries"]] == [
        latest_route_artifact_id,
        route_artifact_id,
    ]
    assert historical_payload["actions"] == [
        {
            "action_id": "workpage.route-demand-v0.save",
            "kind": "save",
            "label": "Save route demand",
            "state": "blocked",
            "workpage_kind": "route-demand-v0",
            "artifact_version_id": route_artifact_id,
            "submit_path": f"/api/v1/workpages/workflow-runs/{workflow_run_id}/route-demand-v0/artifacts/{route_artifact_id}/submit",
            "action_ref": _action_ref(
                action_id="workpage.route-demand-v0.save",
                workpage_kind="route-demand-v0",
                workflow_run_id=workflow_run_id,
                artifact_version_id=route_artifact_id,
            ),
            "disabled_reason": "historical_artifact_read_only",
        }
    ]


def test_route_demand_save_propagates_schedule_drift_and_creates_one_refresh_task(
    tmp_path: Path,
) -> None:
    db_url = _db_url(tmp_path)
    seeded = seed_actual_ops_weekly_schedule_run_with_stage04_outputs(
        db_url=db_url,
        tenant_id="tenant-a",
        domain_id="domain-x",
        run_tag="api:workpages:route-demand:save",
    )
    workflow_run_id = str(seeded["workflow_run_id"])
    route_artifact = seeded["artifacts_by_kind"]["planning.route_slot_requirements.workbook"]
    route_artifact_id = str(route_artifact["artifact_version_id"])
    schedule_draft_artifact_id = str(
        seeded["stage04_outputs"]["draft_workbook"]["artifact_version_id"]
    )
    client = _client(tmp_path)

    submit_rows = _route_demand_submit_rows(route_artifact)
    submit_rows[0]["planned_route_count"] = int(submit_rows[0]["planned_route_count"]) + 2
    submitted = client.post(
        f"/api/v1/workpages/workflow-runs/{workflow_run_id}/route-demand-v0/artifacts/{route_artifact_id}/submit",
        payload={
            "daily_demand_rows": submit_rows,
            "idempotency_key": "api:workpages:route-demand:save:first",
        },
    )
    assert submitted.status_code == 200, submitted.payload
    latest_route_artifact_id = str(submitted.payload["submitted"]["artifact_version_id"])

    run_schedule = client.get(f"/api/v1/workpages/workflow-runs/{workflow_run_id}/schedule-v0")
    assert run_schedule.status_code == 200, run_schedule.payload
    route_dependency = next(
        row
        for row in run_schedule.payload["dependencies"]
        if row["dependency_key"] == "route_slot_requirements"
    )
    assert route_dependency["artifact_version_id"] == latest_route_artifact_id
    assert any(
        action["action_id"] == "workpage.route-demand-v0.open_latest"
        and action["artifact_version_id"] == latest_route_artifact_id
        for action in run_schedule.payload["actions"]
    )

    artifact_schedule = client.get(
        f"/api/v1/workpages/workflow-runs/{workflow_run_id}/"
        f"schedule-v0/artifacts/{schedule_draft_artifact_id}"
    )
    assert artifact_schedule.status_code == 200, artifact_schedule.payload
    artifact_route_dependency = next(
        row
        for row in artifact_schedule.payload["dependencies"]
        if row["dependency_key"] == "route_slot_requirements"
    )
    assert artifact_route_dependency["artifact_version_id"] == route_artifact_id
    assert artifact_route_dependency["state"] == "drifted"

    latest_route_contract = client.get(
        f"/api/v1/workpages/workflow-runs/{workflow_run_id}/route-demand-v0/artifacts/{latest_route_artifact_id}"
    )
    assert latest_route_contract.status_code == 200, latest_route_contract.payload
    assert latest_route_contract.payload["schedule_impact"]["latest_schedule_draft_artifact_version_id"] == schedule_draft_artifact_id
    assert latest_route_contract.payload["schedule_impact"]["dependency_state"] == "drifted"
    assert latest_route_contract.payload["schedule_impact"]["schedule_state"] == "awaiting_refresh"
    refresh_task = latest_route_contract.payload["schedule_impact"]["refresh_task"]
    assert refresh_task is not None
    assert refresh_task["state"] == "OPEN"

    open_refresh_rows = _query_rows(
        db_url,
        """
        SELECT ht.human_task_id, ht.state, tr.activation_key, tr.stage_id, ht.task_kind
        FROM human_tasks ht
        JOIN task_runs tr ON tr.task_run_id = ht.task_run_id
        WHERE ht.workflow_run_id = ?
        """,
        (workflow_run_id,),
    )
    open_refresh_rows = [
        row
        for row in open_refresh_rows
        if str(row["activation_key"]).startswith("workpage.route-demand-v0.schedule-refresh:")
    ]
    assert len(open_refresh_rows) == 1
    assert open_refresh_rows[0]["state"] == "OPEN"
    assert open_refresh_rows[0]["stage_id"] == "Stage04"
    assert open_refresh_rows[0]["task_kind"] == "work_item"

    latest_artifact = _query_rows(
        db_url,
        """
        SELECT artifact_version_id, metadata_json
        FROM artifact_versions
        WHERE artifact_version_id = ?
        """,
        (latest_route_artifact_id,),
    )[0]
    metadata_json = json.loads(str(latest_artifact["metadata_json"]))
    second_submit_rows = [
        {
            "service_date": str(item[0]),
            "planned_route_count": int(item[1]) + (1 if index == 1 else 0),
        }
        for index, item in enumerate(metadata_json["daily_demand_rows"])
    ]
    second_submit = client.post(
        f"/api/v1/workpages/workflow-runs/{workflow_run_id}/route-demand-v0/artifacts/{latest_route_artifact_id}/submit",
        payload={
            "daily_demand_rows": second_submit_rows,
            "idempotency_key": "api:workpages:route-demand:save:second",
        },
    )
    assert second_submit.status_code == 200, second_submit.payload

    refresh_rows_after_second_submit = _query_rows(
        db_url,
        """
        SELECT ht.human_task_id, tr.activation_key
        FROM human_tasks ht
        JOIN task_runs tr ON tr.task_run_id = ht.task_run_id
        WHERE ht.workflow_run_id = ?
        """,
        (workflow_run_id,),
    )
    refresh_rows_after_second_submit = [
        row
        for row in refresh_rows_after_second_submit
        if str(row["activation_key"]).startswith("workpage.route-demand-v0.schedule-refresh:")
    ]
    assert len(refresh_rows_after_second_submit) == 1


def test_route_demand_save_reports_no_schedule_draft_without_creating_refresh_task(
    tmp_path: Path,
) -> None:
    db_url = _db_url(tmp_path)
    seeded = seed_actual_ops_weekly_schedule_run(
        db_url=db_url,
        tenant_id="tenant-a",
        domain_id="domain-x",
        run_tag="api:workpages:route-demand:no-draft",
    )
    workflow_run_id = str(seeded["workflow_run_id"])
    route_artifact = seeded["artifacts_by_kind"]["planning.route_slot_requirements.workbook"]
    route_artifact_id = str(route_artifact["artifact_version_id"])
    client = _client(tmp_path)

    submit_rows = _route_demand_submit_rows(route_artifact)
    submit_rows[0]["planned_route_count"] = int(submit_rows[0]["planned_route_count"]) + 1
    submitted = client.post(
        f"/api/v1/workpages/workflow-runs/{workflow_run_id}/route-demand-v0/artifacts/{route_artifact_id}/submit",
        payload={
            "daily_demand_rows": submit_rows,
            "idempotency_key": "api:workpages:route-demand:no-draft:submit",
        },
    )
    assert submitted.status_code == 200, submitted.payload
    latest_route_artifact_id = str(submitted.payload["submitted"]["artifact_version_id"])

    latest_route_contract = client.get(
        f"/api/v1/workpages/workflow-runs/{workflow_run_id}/route-demand-v0/artifacts/{latest_route_artifact_id}"
    )
    assert latest_route_contract.status_code == 200, latest_route_contract.payload
    assert latest_route_contract.payload["schedule_impact"] == {
        "latest_schedule_draft_artifact_version_id": None,
        "dependency_state": "no_draft",
        "schedule_state": "no_draft",
        "refresh_task": None,
    }

    refresh_rows = _query_rows(
        db_url,
        """
        SELECT ht.human_task_id
        FROM human_tasks ht
        WHERE ht.workflow_run_id = ?
        """,
        (workflow_run_id,),
    )
    assert refresh_rows == []
