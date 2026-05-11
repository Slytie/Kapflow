from __future__ import annotations

import base64
import json
from pathlib import Path

from onetruth.application.handlers.artifacts import ingest_artifact_document_command
from onetruth.infrastructure.artifacts.storage import default_storage_root_for_db_url
from onetruth.infrastructure.db.session import open_sqlite_connection
from tests.runtime.helpers.runtime_api import RuntimeApiClient
from tests.runtime.helpers.workpage_runs import (
    seed_actual_ops_weekly_schedule_run,
    seed_actual_ops_weekly_schedule_run_with_stage04_outputs,
)
from tests.runtime.api.test_weekly_stage04_openai_agent_api import _mock_stage04_runner


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


def _route_demand_submit_rows_from_contract(
    contract_payload: dict[str, object],
) -> list[dict[str, object]]:
    day_cards = contract_payload["calculations"]["day_cards"]
    assert isinstance(day_cards, list)
    return [
        {
            "service_date": str(item["service_date"]),
            "planned_route_count": int(item["planned_route_count"]),
        }
        for item in day_cards
    ]


def _action_by_kind(
    payload: dict[str, object],
    *,
    kind: str,
) -> dict[str, object]:
    actions = payload["actions"]
    assert isinstance(actions, list)
    for action in actions:
        if isinstance(action, dict) and action.get("kind") == kind:
            return action
    raise AssertionError(f"missing action kind {kind!r}")


def _ingest_file_backed_route_demand_artifact(
    tmp_path: Path,
    *,
    workflow_run_id: str,
    route_payload: dict[str, object],
    idempotency_key: str,
) -> dict[str, object]:
    db_url = _db_url(tmp_path)
    content = json.dumps(route_payload, separators=(",", ":"), sort_keys=True).encode("utf-8")
    with open_sqlite_connection(db_url) as connection:
        created = ingest_artifact_document_command(
            connection,
            {
                "workflow_run_id": workflow_run_id,
                "artifact_kind": "planning.route_slot_requirements.workbook",
                "artifact_role": "official_input",
                "file_name": "weekly_route_slot_requirements.json",
                "media_type": "application/json",
                "metadata_json": {
                    "original_file_name": "weekly_route_slot_requirements.xlsx",
                    "uploaded_via": "tests",
                    "subject_kind": "human_task",
                    "subject_id": "ht-tests-route-demand-upload",
                },
                "content_base64": base64.b64encode(content).decode("ascii"),
                "idempotency_key": idempotency_key,
                "actor_id": "human:ops-manager-2",
                "actor_type": "human",
            },
            storage_root=default_storage_root_for_db_url(db_url),
            include_receipt=True,
        )
    return created["result"]["artifact_version"]


def _ingest_json_artifact(
    tmp_path: Path,
    *,
    workflow_run_id: str,
    artifact_kind: str,
    artifact_role: str,
    metadata_json: dict[str, object],
    idempotency_key: str,
) -> dict[str, object]:
    db_url = _db_url(tmp_path)
    content = json.dumps(metadata_json, separators=(",", ":"), sort_keys=True).encode("utf-8")
    with open_sqlite_connection(db_url) as connection:
        created = ingest_artifact_document_command(
            connection,
            {
                "workflow_run_id": workflow_run_id,
                "artifact_kind": artifact_kind,
                "artifact_role": artifact_role,
                "file_name": f"{artifact_kind}.json",
                "media_type": "application/json",
                "metadata_json": {
                    "original_file_name": f"{artifact_kind}.json",
                    "uploaded_via": "tests",
                },
                "content_base64": base64.b64encode(content).decode("ascii"),
                "idempotency_key": idempotency_key,
                "actor_id": "human:ops-manager-2",
                "actor_type": "human",
            },
            storage_root=default_storage_root_for_db_url(db_url),
            include_receipt=True,
        )
    return created["result"]["artifact_version"]


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
        },
        {
            "action_id": "workpage.route-demand-v0.add_next_week",
            "kind": "add_next_week",
            "label": "Add a week",
            "state": "available",
            "workpage_kind": "route-demand-v0",
            "artifact_version_id": None,
            "create_path": f"/api/v1/workpages/workflow-runs/{workflow_run_id}/route-demand-v0/next-week",
            "action_ref": _action_ref(
                action_id="workpage.route-demand-v0.add_next_week",
                workpage_kind="route-demand-v0",
                workflow_run_id=workflow_run_id,
                artifact_version_id=None,
            ),
            "disabled_reason": None,
        },
    ]
    day_cards = payload["calculations"]["day_cards"]
    assert len(day_cards) == 14
    assert day_cards[0]["service_date"] == "2026-03-22"
    assert day_cards[-1]["service_date"] == "2026-04-04"
    assert payload["workpage"]["summary"]["service_day_count"] == 7
    assert payload["workpage"]["summary"]["planned_route_total"] == 134
    assert payload["future_week_options"] == [
        {
            "option_id": "next_week",
            "label": "Week 2",
            "planning_week_id": "PW-2026-W14",
            "start_date": "2026-03-29",
            "end_date": "2026-04-04",
            "date_range_label": "2026-03-29 to 2026-04-04",
        }
    ]
    assert payload["future_week_activation"]["state"] == "idle"


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
    assert initial_payload["workpage"]["summary"]["service_day_count"] == 7
    assert initial_payload["workpage"]["summary"]["planned_route_total"] == 134
    assert len(initial_payload["calculations"]["day_cards"]) == 14
    assert initial_payload["calculations"]["day_cards"][0]["service_date"] == "2026-03-22"
    assert initial_payload["calculations"]["day_cards"][-1]["service_date"] == "2026-04-04"
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
        },
        {
            "action_id": "workpage.route-demand-v0.add_next_week",
            "kind": "add_next_week",
            "label": "Add a week",
            "state": "available",
            "workpage_kind": "route-demand-v0",
            "artifact_version_id": None,
            "create_path": f"/api/v1/workpages/workflow-runs/{workflow_run_id}/route-demand-v0/next-week",
            "action_ref": _action_ref(
                action_id="workpage.route-demand-v0.add_next_week",
                workpage_kind="route-demand-v0",
                workflow_run_id=workflow_run_id,
                artifact_version_id=None,
            ),
            "disabled_reason": None,
        },
        {
            "action_id": "workpage.route-demand-v0.save_and_run",
            "kind": "save_and_run",
            "label": "Run coverage agent",
            "state": "available",
            "workpage_kind": "route-demand-v0",
            "artifact_version_id": route_artifact_id,
            "submit_path": (
                f"/api/v1/workpages/workflow-runs/{workflow_run_id}/route-demand-v0/"
                f"artifacts/{route_artifact_id}/save-and-run"
            ),
            "action_ref": _action_ref(
                action_id="workpage.route-demand-v0.save_and_run",
                workpage_kind="route-demand-v0",
                workflow_run_id=workflow_run_id,
                artifact_version_id=route_artifact_id,
            ),
            "disabled_reason": None,
        },
    ]
    alias_read = client.get(f"/api/v1/workpages/artifacts/{route_artifact_id}")
    assert alias_read.status_code == 404
    assert alias_read.payload["error"]["code"] == "not_found"


def test_route_demand_existing_week_save_and_run_requires_positive_delta_and_returns_coverage_context(
    tmp_path: Path,
) -> None:
    seeded = seed_actual_ops_weekly_schedule_run_with_stage04_outputs(
        db_url=_db_url(tmp_path),
        tenant_id="tenant-a",
        domain_id="domain-x",
        run_tag="api:workpages:route-demand:existing-week-coverage",
    )
    workflow_run_id = str(seeded["workflow_run_id"])
    route_artifact_id = str(
        seeded["artifacts_by_kind"]["planning.route_slot_requirements.workbook"][
            "artifact_version_id"
        ]
    )
    schedule_artifact_id = str(seeded["stage04_outputs"]["draft_workbook"]["artifact_version_id"])
    client = _client(tmp_path)
    contract = client.get(
        f"/api/v1/workpages/workflow-runs/{workflow_run_id}/"
        f"route-demand-v0/artifacts/{route_artifact_id}"
    )
    assert contract.status_code == 200, contract.payload
    submit_rows = _route_demand_submit_rows_from_contract(contract.payload)

    unchanged = client.post(
        f"/api/v1/workpages/workflow-runs/{workflow_run_id}/"
        f"route-demand-v0/artifacts/{route_artifact_id}/save-and-run",
        payload={
            "daily_demand_rows": submit_rows,
            "idempotency_key": "api:workpages:route-demand:existing-week-coverage:unchanged",
        },
    )
    assert unchanged.status_code == 400, unchanged.payload
    assert unchanged.payload["error"]["code"] == "route_demand_increase_required"

    submit_rows[0]["planned_route_count"] = int(submit_rows[0]["planned_route_count"]) + 1
    saved_and_ran = client.post(
        f"/api/v1/workpages/workflow-runs/{workflow_run_id}/"
        f"route-demand-v0/artifacts/{route_artifact_id}/save-and-run",
        payload={
            "daily_demand_rows": submit_rows,
            "idempotency_key": "api:workpages:route-demand:existing-week-coverage:increase",
        },
    )
    assert saved_and_ran.status_code == 200, saved_and_ran.payload
    assert saved_and_ran.payload["submitted"]["target_workflow_run_id"] == workflow_run_id
    assert saved_and_ran.payload["submitted"]["target_schedule_route"] == (
        f"/runs/{workflow_run_id}/workpages/schedule-v0"
    )
    assert saved_and_ran.payload["submitted"]["target_schedule_artifact_version_id"] == (
        schedule_artifact_id
    )
    coverage_context = saved_and_ran.payload["route_demand_coverage_context"]
    assert saved_and_ran.payload["submitted"]["route_demand_coverage_context"] == coverage_context
    assert coverage_context == {
        "workflow_run_id": workflow_run_id,
        "schedule_artifact_version_id": schedule_artifact_id,
        "route_demand_artifact_version_id": saved_and_ran.payload["submitted"][
            "artifact_version_id"
        ],
        "coverage_candidates_path": (
            f"/api/v1/workpages/workflow-runs/{workflow_run_id}/schedule-v0/"
            f"artifacts/{schedule_artifact_id}/route-demand-coverage-candidates"
        ),
        "coverage_apply_path": (
            f"/api/v1/workpages/workflow-runs/{workflow_run_id}/schedule-v0/"
            f"artifacts/{schedule_artifact_id}/route-demand-coverage"
        ),
        "service_dates": [submit_rows[0]["service_date"]],
        "added_route_count": 1,
        "deltas": [
            {
                "service_date": submit_rows[0]["service_date"],
                "previous_planned_route_count": int(submit_rows[0]["planned_route_count"]) - 1,
                "planned_route_count": int(submit_rows[0]["planned_route_count"]),
                "delta": 1,
            }
        ],
    }

def test_route_demand_historical_artifact_becomes_read_only_after_successor_save(
    tmp_path: Path,
) -> None:
    seeded = seed_actual_ops_weekly_schedule_run_with_stage04_outputs(
        db_url=_db_url(tmp_path),
        tenant_id="tenant-a",
        domain_id="domain-x",
        run_tag="api:workpages:route-demand:artifact-history",
    )
    workflow_run_id = str(seeded["workflow_run_id"])
    route_artifact = seeded["artifacts_by_kind"]["planning.route_slot_requirements.workbook"]
    route_artifact_id = str(route_artifact["artifact_version_id"])
    client = _client(tmp_path)

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


def test_route_demand_artifact_workpage_reloads_successor_for_file_backed_base_artifact(
    tmp_path: Path,
) -> None:
    seeded = seed_actual_ops_weekly_schedule_run_with_stage04_outputs(
        db_url=_db_url(tmp_path),
        tenant_id="tenant-a",
        domain_id="domain-x",
        run_tag="api:workpages:route-demand:file-backed-base",
    )
    workflow_run_id = str(seeded["workflow_run_id"])
    route_artifact = seeded["artifacts_by_kind"]["planning.route_slot_requirements.workbook"]
    route_payload = route_artifact["metadata_json"]
    assert isinstance(route_payload, dict)
    file_backed_artifact = _ingest_file_backed_route_demand_artifact(
        tmp_path,
        workflow_run_id=workflow_run_id,
        route_payload=route_payload,
        idempotency_key="api:workpages:route-demand:file-backed-base:ingest",
    )
    base_artifact_version_id = str(file_backed_artifact["artifact_version_id"])
    client = _client(tmp_path)

    initial = client.get(
        f"/api/v1/workpages/workflow-runs/{workflow_run_id}/"
        f"route-demand-v0/artifacts/{base_artifact_version_id}"
    )
    assert initial.status_code == 200, initial.payload

    submit_rows = _route_demand_submit_rows(route_artifact)
    submit_rows[0]["planned_route_count"] = int(submit_rows[0]["planned_route_count"]) + 2
    submitted = client.post(
        f"/api/v1/workpages/workflow-runs/{workflow_run_id}/route-demand-v0/artifacts/{base_artifact_version_id}/submit",
        payload={
            "daily_demand_rows": submit_rows,
            "idempotency_key": "api:workpages:route-demand:file-backed-base:submit",
        },
    )
    assert submitted.status_code == 200, submitted.payload
    latest_route_artifact_id = str(submitted.payload["submitted"]["artifact_version_id"])

    latest = client.get(
        f"/api/v1/workpages/workflow-runs/{workflow_run_id}/"
        f"route-demand-v0/artifacts/{latest_route_artifact_id}"
    )
    assert latest.status_code == 200, latest.payload
    day_cards = latest.payload["calculations"]["day_cards"]
    assert day_cards
    assert day_cards[0]["delta_from_previous_version"] == {
        "planned_route_count_delta": 2,
    }


def test_route_demand_save_propagates_schedule_drift_without_creating_refresh_task(
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
    assert latest_route_contract.payload["schedule_impact"]["schedule_state"] == "drifted"
    assert latest_route_contract.payload["schedule_impact"]["refresh_task"] is None

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
    assert open_refresh_rows == []

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
    assert refresh_rows_after_second_submit == []


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


def test_route_demand_add_next_week_reuses_future_run_and_seeds_zero_count_artifact(
    tmp_path: Path,
) -> None:
    seeded = seed_actual_ops_weekly_schedule_run(
        db_url=_db_url(tmp_path),
        tenant_id="tenant-a",
        domain_id="domain-x",
        run_tag="api:workpages:route-demand:add-next-week",
    )
    workflow_run_id = str(seeded["workflow_run_id"])
    client = _client(tmp_path)

    created = client.post(
        f"/api/v1/workpages/workflow-runs/{workflow_run_id}/route-demand-v0/next-week",
        payload={"idempotency_key": "api:workpages:route-demand:add-next-week:first"},
    )
    assert created.status_code == 200, created.payload
    future_workflow_run_id = str(created.payload["created"]["workflow_run_id"])
    future_artifact_version_id = str(created.payload["created"]["artifact_version_id"])
    assert future_workflow_run_id != workflow_run_id
    future_run_rows = _query_rows(
        _db_url(tmp_path),
        """
        SELECT partition_key, logical_date
        FROM workflow_runs
        WHERE workflow_run_id = ?
        """,
        (future_workflow_run_id,),
    )
    assert future_run_rows == [
        {
            "partition_key": "PW-2026-W14",
            "logical_date": "2026-03-30",
        }
    ]

    future_contract = client.get(
        f"/api/v1/workpages/workflow-runs/{future_workflow_run_id}/"
        f"route-demand-v0/artifacts/{future_artifact_version_id}"
    )
    assert future_contract.status_code == 200, future_contract.payload
    payload = future_contract.payload
    assert payload["workpage"]["summary"]["planning_week_id"] == "PW-2026-W14"
    assert payload["workpage"]["summary"]["service_day_count"] == 7
    assert payload["future_week_options"] == []
    assert payload["future_week_activation"]["state"] == "idle"
    day_cards = payload["calculations"]["day_cards"]
    assert len(day_cards) == 7
    assert day_cards[0]["service_date"] == "2026-03-29"
    assert day_cards[-1]["service_date"] == "2026-04-04"
    assert all(int(card["planned_route_count"]) == 0 for card in day_cards)
    assert payload["actions"] == [
        {
            "action_id": "workpage.route-demand-v0.save",
            "kind": "save",
            "label": "Save route demand",
            "state": "available",
            "workpage_kind": "route-demand-v0",
            "artifact_version_id": future_artifact_version_id,
            "submit_path": f"/api/v1/workpages/workflow-runs/{future_workflow_run_id}/route-demand-v0/artifacts/{future_artifact_version_id}/submit",
            "action_ref": _action_ref(
                action_id="workpage.route-demand-v0.save",
                workpage_kind="route-demand-v0",
                workflow_run_id=future_workflow_run_id,
                artifact_version_id=future_artifact_version_id,
            ),
            "disabled_reason": None,
        },
        {
            "action_id": "workpage.route-demand-v0.save_and_run",
            "kind": "save_and_run",
            "label": "Save and run scheduling agent",
            "state": "available",
            "workpage_kind": "route-demand-v0",
            "artifact_version_id": future_artifact_version_id,
            "submit_path": f"/api/v1/workpages/workflow-runs/{future_workflow_run_id}/route-demand-v0/artifacts/{future_artifact_version_id}/save-and-run",
            "action_ref": _action_ref(
                action_id="workpage.route-demand-v0.save_and_run",
                workpage_kind="route-demand-v0",
                workflow_run_id=future_workflow_run_id,
                artifact_version_id=future_artifact_version_id,
            ),
            "disabled_reason": None,
        },
    ]

    created_again = client.post(
        f"/api/v1/workpages/workflow-runs/{workflow_run_id}/route-demand-v0/next-week",
        payload={"idempotency_key": "api:workpages:route-demand:add-next-week:second"},
    )
    assert created_again.status_code == 200, created_again.payload
    assert created_again.payload["created"]["workflow_run_id"] == future_workflow_run_id
    assert created_again.payload["created"]["artifact_version_id"] == future_artifact_version_id


def test_route_demand_save_and_run_creates_future_schedule_and_locks_future_seed(
    tmp_path: Path,
    monkeypatch,
) -> None:
    monkeypatch.setattr(
        "onetruth.application.services.weekly_stage04_openai_agent.build_weekly_stage04_openai_agent_runner_from_env",
        lambda: _mock_stage04_runner(),
    )
    monkeypatch.setenv("ONETRUTH_ARTIFACT_ROOT", str(tmp_path / "artifacts"))
    seeded = seed_actual_ops_weekly_schedule_run_with_stage04_outputs(
        db_url=_db_url(tmp_path),
        tenant_id="tenant-a",
        domain_id="domain-x",
        run_tag="api:workpages:route-demand:save-and-run",
    )
    workflow_run_id = str(seeded["workflow_run_id"])
    client = _client(tmp_path)
    driver_preferences_run = client.get(
        f"/api/v1/workpages/workflow-runs/{workflow_run_id}/driver-preferences-v0"
    )
    assert driver_preferences_run.status_code == 200, driver_preferences_run.payload
    driver_id = str(driver_preferences_run.payload["preference_grid"]["drivers"][0]["driver_id"])
    exception_action_ref = {
        "action_id": "workpage.driver-preferences-v0.add_availability_exception",
        "workpage_kind": "driver-preferences-v0",
        "workflow_run_id": workflow_run_id,
        "artifact_version_id": None,
        "subject": None,
    }
    created_exception = client.post(
        f"/api/v1/workpages/workflow-runs/{workflow_run_id}/driver-preferences-v0/availability-exceptions",
        payload={
            "driver_id": driver_id,
            "start_date": "2026-03-29",
            "end_date": "2026-03-29",
            "reason_code": "wedding",
            "reason_note": "Sunday wedding",
            "action_ref": exception_action_ref,
            "idempotency_key": "api:workpages:route-demand:save-and-run:sunday-exception",
        },
    )
    assert created_exception.status_code == 200, created_exception.payload
    exception_id = str(created_exception.payload["created"]["exception"]["exception_id"])

    created = client.post(
        f"/api/v1/workpages/workflow-runs/{workflow_run_id}/route-demand-v0/next-week",
        payload={"idempotency_key": "api:workpages:route-demand:save-and-run:create"},
    )
    assert created.status_code == 200, created.payload
    future_workflow_run_id = str(created.payload["created"]["workflow_run_id"])
    future_artifact_version_id = str(created.payload["created"]["artifact_version_id"])

    future_contract = client.get(
        f"/api/v1/workpages/workflow-runs/{future_workflow_run_id}/"
        f"route-demand-v0/artifacts/{future_artifact_version_id}"
    )
    assert future_contract.status_code == 200, future_contract.payload
    submit_rows = _route_demand_submit_rows_from_contract(future_contract.payload)
    submit_rows[0]["planned_route_count"] = 4

    saved_and_ran = client.post(
        f"/api/v1/workpages/workflow-runs/{future_workflow_run_id}/"
        f"route-demand-v0/artifacts/{future_artifact_version_id}/save-and-run",
        payload={
            "daily_demand_rows": submit_rows,
            "idempotency_key": "api:workpages:route-demand:save-and-run:run",
        },
    )
    assert saved_and_ran.status_code == 200, saved_and_ran.payload
    submitted_artifact_version_id = str(saved_and_ran.payload["submitted"]["artifact_version_id"])
    assert saved_and_ran.payload["submitted"]["target_workflow_run_id"] == future_workflow_run_id
    assert saved_and_ran.payload["submitted"]["target_schedule_route"] == (
        f"/runs/{future_workflow_run_id}/workpages/schedule-v0"
    )
    assert saved_and_ran.payload["submitted"]["target_schedule_artifact_version_id"]

    latest_route_contract = client.get(
        f"/api/v1/workpages/workflow-runs/{future_workflow_run_id}/"
        f"route-demand-v0/artifacts/{submitted_artifact_version_id}"
    )
    assert latest_route_contract.status_code == 200, latest_route_contract.payload
    payload = latest_route_contract.payload
    assert payload["artifact_state"]["editable"] is False
    assert payload["future_week_activation"]["state"] == "succeeded"
    assert payload["future_week_activation"]["target_schedule_route"] == (
        f"/runs/{future_workflow_run_id}/workpages/schedule-v0"
    )
    assert payload["actions"] == [
        {
            "action_id": "workpage.route-demand-v0.save",
            "kind": "save",
            "label": "Save route demand",
            "state": "blocked",
            "workpage_kind": "route-demand-v0",
            "artifact_version_id": submitted_artifact_version_id,
            "submit_path": f"/api/v1/workpages/workflow-runs/{future_workflow_run_id}/route-demand-v0/artifacts/{submitted_artifact_version_id}/submit",
            "action_ref": _action_ref(
                action_id="workpage.route-demand-v0.save",
                workpage_kind="route-demand-v0",
                workflow_run_id=future_workflow_run_id,
                artifact_version_id=submitted_artifact_version_id,
            ),
            "disabled_reason": "continue_from_schedule",
        },
        {
            "action_id": "workpage.route-demand-v0.save_and_run",
            "kind": "save_and_run",
            "label": "Save and run scheduling agent",
            "state": "blocked",
            "workpage_kind": "route-demand-v0",
            "artifact_version_id": submitted_artifact_version_id,
            "submit_path": f"/api/v1/workpages/workflow-runs/{future_workflow_run_id}/route-demand-v0/artifacts/{submitted_artifact_version_id}/save-and-run",
            "action_ref": _action_ref(
                action_id="workpage.route-demand-v0.save_and_run",
                workpage_kind="route-demand-v0",
                workflow_run_id=future_workflow_run_id,
                artifact_version_id=submitted_artifact_version_id,
            ),
            "disabled_reason": "continue_from_schedule",
        },
    ]

    schedule_contract = client.get(
        f"/api/v1/workpages/workflow-runs/{future_workflow_run_id}/schedule-v0"
    )
    assert schedule_contract.status_code == 200, schedule_contract.payload
    assert schedule_contract.payload["artifact_state"] == {
        "state_kind": "run_projection",
        "artifact_kind": "planning.draft_weekly_schedule.workbook",
        "editable": False,
        "current_artifact_version_id": None,
        "latest_artifact_version_id": saved_and_ran.payload["submitted"][
            "target_schedule_artifact_version_id"
        ],
        "accepted_artifact_version_id": None,
    }
    open_latest_draft = _action_by_kind(schedule_contract.payload, kind="open_latest_draft")
    assert open_latest_draft["artifact_version_id"] == saved_and_ran.payload["submitted"][
        "target_schedule_artifact_version_id"
    ]
    availability_rows = _query_rows(
        _db_url(tmp_path),
        """
        SELECT metadata_json
        FROM artifact_versions
        WHERE workflow_run_id = ?
          AND artifact_kind = 'planning.approved_availability.workbook'
        ORDER BY created_at DESC, artifact_version_id DESC
        LIMIT 1
        """,
        (future_workflow_run_id,),
    )
    assert len(availability_rows) == 1
    availability_metadata = json.loads(str(availability_rows[0]["metadata_json"]))
    assert availability_metadata["scope_start"] == "2026-03-29"
    assert availability_metadata["scope_end_exclusive"] == "2026-04-05"
    availability_columns = list(availability_metadata["columns"])
    availability_row_dicts = [
        dict(zip(availability_columns, row, strict=False))
        for row in availability_metadata["rows"]
    ]
    sunday_exception_rows = [
        row
        for row in availability_row_dicts
        if row.get("driver_id") == driver_id and row.get("service_date") == "2026-03-29"
    ]
    assert len(sunday_exception_rows) == 1
    assert sunday_exception_rows[0]["availability_state"] == "CANNOT"
    assert sunday_exception_rows[0]["locked_by_manager"] == "yes"
    assert sunday_exception_rows[0]["source_exception_id"] == exception_id

    future_human_tasks = _query_rows(
        _db_url(tmp_path),
        """
        SELECT tr.stage_id, ht.task_kind, ht.state
        FROM human_tasks ht
        JOIN task_runs tr ON tr.task_run_id = ht.task_run_id
        WHERE ht.workflow_run_id = ?
        ORDER BY ht.created_at
        """,
        (future_workflow_run_id,),
    )
    assert any(
        row["stage_id"] == "Stage05" and row["state"] in {"OPEN", "CLAIMED"}
        for row in future_human_tasks
    )


def test_route_demand_save_and_run_marks_failed_future_week_activation_when_stage04_scopes_conflict(
    tmp_path: Path,
) -> None:
    seeded = seed_actual_ops_weekly_schedule_run_with_stage04_outputs(
        db_url=_db_url(tmp_path),
        tenant_id="tenant-a",
        domain_id="domain-x",
        run_tag="api:workpages:route-demand:save-and-run:scope-conflict",
    )
    workflow_run_id = str(seeded["workflow_run_id"])
    client = _client(tmp_path)

    created = client.post(
        f"/api/v1/workpages/workflow-runs/{workflow_run_id}/route-demand-v0/next-week",
        payload={"idempotency_key": "api:workpages:route-demand:scope-conflict:create"},
    )
    assert created.status_code == 200, created.payload
    future_workflow_run_id = str(created.payload["created"]["workflow_run_id"])
    future_artifact_version_id = str(created.payload["created"]["artifact_version_id"])

    conflicting_availability_payload = dict(
        seeded["artifacts_by_kind"]["planning.approved_availability.workbook"]["metadata_json"]
    )
    conflicting_availability_payload["scope_start"] = "2026-03-09"
    conflicting_availability_payload["scope_end_exclusive"] = "2026-03-16"
    _ingest_json_artifact(
        tmp_path,
        workflow_run_id=future_workflow_run_id,
        artifact_kind="planning.approved_availability.workbook",
        artifact_role="official_input",
        metadata_json=conflicting_availability_payload,
        idempotency_key="api:workpages:route-demand:scope-conflict:approved-availability",
    )

    future_contract = client.get(
        f"/api/v1/workpages/workflow-runs/{future_workflow_run_id}/"
        f"route-demand-v0/artifacts/{future_artifact_version_id}"
    )
    assert future_contract.status_code == 200, future_contract.payload
    submit_rows = _route_demand_submit_rows_from_contract(future_contract.payload)
    submit_rows[0]["planned_route_count"] = 4

    saved_and_ran = client.post(
        f"/api/v1/workpages/workflow-runs/{future_workflow_run_id}/"
        f"route-demand-v0/artifacts/{future_artifact_version_id}/save-and-run",
        payload={
            "daily_demand_rows": submit_rows,
            "idempotency_key": "api:workpages:route-demand:scope-conflict:run",
        },
    )
    assert saved_and_ran.status_code == 409, saved_and_ran.payload
    assert saved_and_ran.payload["error"]["code"] == "stage04_input_scope_mismatch"
    assert "conflicting explicit scope bounds" in saved_and_ran.payload["error"]["message"]

    execution_rows = _query_rows(
        _db_url(tmp_path),
        """
        SELECT state
        FROM execution_sessions
        WHERE workflow_run_id = ?
        ORDER BY created_at DESC, execution_session_id DESC
        LIMIT 1
        """,
        (future_workflow_run_id,),
    )
    assert execution_rows == [{"state": "FAILED"}]
    tool_rows = _query_rows(
        _db_url(tmp_path),
        """
        SELECT state, error_code
        FROM tool_executions
        WHERE execution_session_id IN (
            SELECT execution_session_id
            FROM execution_sessions
            WHERE workflow_run_id = ?
        )
        ORDER BY requested_at DESC, tool_execution_id DESC
        LIMIT 1
        """,
        (future_workflow_run_id,),
    )
    assert tool_rows == [
        {
            "state": "FAILED",
            "error_code": "stage04_input_scope_mismatch",
        }
    ]
    latest_route_artifact_rows = _query_rows(
        _db_url(tmp_path),
        """
        SELECT artifact_version_id
        FROM artifact_versions
        WHERE workflow_run_id = ?
          AND artifact_kind = 'planning.route_slot_requirements.workbook'
        ORDER BY created_at DESC, artifact_version_id DESC
        LIMIT 1
        """,
        (future_workflow_run_id,),
    )
    latest_route_artifact_id = str(latest_route_artifact_rows[0]["artifact_version_id"])
    latest_route_contract = client.get(
        f"/api/v1/workpages/workflow-runs/{future_workflow_run_id}/"
        f"route-demand-v0/artifacts/{latest_route_artifact_id}"
    )
    assert latest_route_contract.status_code == 200, latest_route_contract.payload
    assert latest_route_contract.payload["future_week_activation"]["state"] == "failed"
    assert latest_route_contract.payload["future_week_activation"]["error_code"] == (
        "stage04_input_scope_mismatch"
    )
    assert "different week scopes" in str(
        latest_route_contract.payload["future_week_activation"]["error_message"]
    )


def test_route_demand_future_week_activation_stays_failed_when_failed_stage04_already_left_a_draft(
    tmp_path: Path,
) -> None:
    seeded = seed_actual_ops_weekly_schedule_run_with_stage04_outputs(
        db_url=_db_url(tmp_path),
        tenant_id="tenant-a",
        domain_id="domain-x",
        run_tag="api:workpages:route-demand:save-and-run:failed-draft-precedence",
    )
    workflow_run_id = str(seeded["workflow_run_id"])
    client = _client(tmp_path)

    created = client.post(
        f"/api/v1/workpages/workflow-runs/{workflow_run_id}/route-demand-v0/next-week",
        payload={"idempotency_key": "api:workpages:route-demand:failed-draft-precedence:create"},
    )
    assert created.status_code == 200, created.payload
    future_workflow_run_id = str(created.payload["created"]["workflow_run_id"])
    future_artifact_version_id = str(created.payload["created"]["artifact_version_id"])

    conflicting_availability_payload = dict(
        seeded["artifacts_by_kind"]["planning.approved_availability.workbook"]["metadata_json"]
    )
    conflicting_availability_payload["scope_start"] = "2026-03-09"
    conflicting_availability_payload["scope_end_exclusive"] = "2026-03-16"
    _ingest_json_artifact(
        tmp_path,
        workflow_run_id=future_workflow_run_id,
        artifact_kind="planning.approved_availability.workbook",
        artifact_role="official_input",
        metadata_json=conflicting_availability_payload,
        idempotency_key="api:workpages:route-demand:failed-draft-precedence:approved-availability",
    )

    future_contract = client.get(
        f"/api/v1/workpages/workflow-runs/{future_workflow_run_id}/"
        f"route-demand-v0/artifacts/{future_artifact_version_id}"
    )
    assert future_contract.status_code == 200, future_contract.payload
    submit_rows = _route_demand_submit_rows_from_contract(future_contract.payload)
    submit_rows[0]["planned_route_count"] = 4

    saved_and_ran = client.post(
        f"/api/v1/workpages/workflow-runs/{future_workflow_run_id}/"
        f"route-demand-v0/artifacts/{future_artifact_version_id}/save-and-run",
        payload={
            "daily_demand_rows": submit_rows,
            "idempotency_key": "api:workpages:route-demand:failed-draft-precedence:run",
        },
    )
    assert saved_and_ran.status_code == 409, saved_and_ran.payload

    _ingest_json_artifact(
        tmp_path,
        workflow_run_id=future_workflow_run_id,
        artifact_kind="planning.draft_weekly_schedule.workbook",
        artifact_role="draft_output",
        metadata_json={
            "week_start": "2026-03-29",
            "week_end_exclusive": "2026-04-05",
            "source": "tests",
        },
        idempotency_key="api:workpages:route-demand:failed-draft-precedence:schedule-draft",
    )

    latest_route_artifact_rows = _query_rows(
        _db_url(tmp_path),
        """
        SELECT artifact_version_id
        FROM artifact_versions
        WHERE workflow_run_id = ?
          AND artifact_kind = 'planning.route_slot_requirements.workbook'
        ORDER BY created_at DESC, artifact_version_id DESC
        LIMIT 1
        """,
        (future_workflow_run_id,),
    )
    latest_route_artifact_id = str(latest_route_artifact_rows[0]["artifact_version_id"])
    latest_route_contract = client.get(
        f"/api/v1/workpages/workflow-runs/{future_workflow_run_id}/"
        f"route-demand-v0/artifacts/{latest_route_artifact_id}"
    )
    assert latest_route_contract.status_code == 200, latest_route_contract.payload
    assert latest_route_contract.payload["future_week_activation"]["state"] == "failed"
    assert latest_route_contract.payload["future_week_activation"]["error_code"] == (
        "stage04_input_scope_mismatch"
    )
    assert latest_route_contract.payload["future_week_activation"]["target_schedule_route"] == (
        f"/runs/{future_workflow_run_id}/workpages/schedule-v0"
    )
    assert latest_route_contract.payload["future_week_activation"][
        "target_schedule_artifact_version_id"
    ]
