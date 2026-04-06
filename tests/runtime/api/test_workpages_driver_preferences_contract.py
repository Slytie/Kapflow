from __future__ import annotations

from copy import deepcopy
from pathlib import Path

from tests.runtime.helpers.runtime_api import RuntimeApiClient
from tests.runtime.helpers.workpage_runs import (
    create_driver_preferences_snapshot,
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


def _action_by_id(
    actions: list[dict[str, object]],
    action_id: str,
) -> dict[str, object]:
    return next(action for action in actions if action["action_id"] == action_id)


def _schedule_submit_rows(
    client: RuntimeApiClient,
    workflow_run_id: str,
    artifact_version_id: str,
) -> tuple[list[dict[str, object]], list[dict[str, object]]]:
    payload = client.get(
        f"/api/v1/workpages/workflow-runs/{workflow_run_id}/"
        f"schedule-v0/artifacts/{artifact_version_id}"
    ).payload
    sections = payload["workpage"]["sections"]
    assignment_section = next(
        section for section in sections if section.get("table_id") == "assignment_rows"
    )
    reserve_section = next(
        section for section in sections if section.get("table_id") == "reserve_rows"
    )
    return (deepcopy(assignment_section["rows"]), deepcopy(reserve_section["rows"]))


def test_driver_preferences_run_workpage_lands_on_create_snapshot_when_none_exists(
    tmp_path: Path,
) -> None:
    seeded = seed_actual_ops_weekly_schedule_run_with_stage04_outputs(
        db_url=_db_url(tmp_path),
        tenant_id="tenant-a",
        domain_id="domain-x",
        run_tag="api:workpages:driver-preferences:run",
    )
    workflow_run_id = str(seeded["workflow_run_id"])
    schedule_draft_artifact_id = str(
        seeded["stage04_outputs"]["draft_workbook"]["artifact_version_id"]
    )
    client = _client(tmp_path)

    response = client.get(
        f"/api/v1/workpages/workflow-runs/{workflow_run_id}/driver-preferences-v0"
    )
    assert response.status_code == 200, response.payload

    payload = response.payload
    assert payload["workpage"]["workpage_id"] == "driver-preferences-v0"
    assert payload["workpage"]["version"] == 1
    assert payload["artifact_state"] == {
        "state_kind": "run_projection",
        "artifact_kind": "planning.driver_shift_preferences.workbook",
        "editable": False,
        "current_artifact_version_id": None,
        "latest_artifact_version_id": None,
        "accepted_artifact_version_id": None,
    }
    assert payload["artifact_history"] is None
    assert payload["preference_grid"]["weekdays"] == [
        "sun",
        "mon",
        "tue",
        "wed",
        "thu",
        "fri",
        "sat",
    ]
    assert payload["preference_grid"]["drivers"]
    assert all(
        value is None
        for value in payload["preference_grid"]["drivers"][0]["preferences_by_weekday"].values()
    )
    assert payload["schedule_impact"] == {
        "latest_schedule_draft_artifact_version_id": schedule_draft_artifact_id,
        "latest_driver_preferences_artifact_version_id": None,
        "dependency_state": "no_snapshot",
        "schedule_state": "no_snapshot",
    }
    assert _action_by_id(payload["actions"], "workpage.driver-preferences-v0.create_snapshot") == {
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
    }


def test_driver_preferences_create_route_returns_canonical_artifact_and_retires_alias_read(
    tmp_path: Path,
) -> None:
    seeded = seed_actual_ops_weekly_schedule_run_with_stage04_outputs(
        db_url=_db_url(tmp_path),
        tenant_id="tenant-a",
        domain_id="domain-x",
        run_tag="api:workpages:driver-preferences:create",
    )
    workflow_run_id = str(seeded["workflow_run_id"])
    client = _client(tmp_path)

    created = client.post(
        f"/api/v1/workpages/workflow-runs/{workflow_run_id}/driver-preferences-v0/snapshots",
        payload={"idempotency_key": "api:workpages:driver-preferences:create"},
    )
    assert created.status_code == 200, created.payload
    artifact_version_id = str(created.payload["created"]["artifact_version_id"])
    assert created.payload["created"] == {
        "workflow_run_id": workflow_run_id,
        "artifact_version_id": artifact_version_id,
        "route": (
            f"/runs/{workflow_run_id}/workpages/driver-preferences-v0/artifacts/"
            f"{artifact_version_id}"
        ),
    }

    payload = client.get(
        f"/api/v1/workpages/workflow-runs/{workflow_run_id}/"
        f"driver-preferences-v0/artifacts/{artifact_version_id}"
    ).payload
    assert payload["workpage"]["workpage_id"] == "driver-preferences-v0"
    assert payload["artifact_state"] == {
        "state_kind": "artifact_projection",
        "artifact_kind": "planning.driver_shift_preferences.workbook",
        "editable": True,
        "current_artifact_version_id": artifact_version_id,
        "latest_artifact_version_id": artifact_version_id,
        "accepted_artifact_version_id": None,
    }
    assert payload["artifact_history"]["current_artifact_version_id"] == artifact_version_id
    assert payload["artifact_history"]["latest_artifact_version_id"] == artifact_version_id
    assert payload["artifact_history"]["previous_artifact_version_id"] is None
    assert payload["artifact_history"]["next_artifact_version_id"] is None
    assert payload["artifact_history"]["entries"] == [
        {
            "artifact_version_id": artifact_version_id,
            "workflow_run_id": workflow_run_id,
            "artifact_kind": "planning.driver_shift_preferences.workbook",
            "created_at": payload["artifact_history"]["entries"][0]["created_at"],
            "lineage_note": "Created initial driver preferences snapshot.",
            "supersedes_artifact_version_id": None,
            "route": (
                f"/runs/{workflow_run_id}/workpages/driver-preferences-v0/artifacts/"
                f"{artifact_version_id}"
            ),
        }
    ]
    assert payload["artifact_history"]["entries"][0]["created_at"]
    assert _action_by_id(payload["actions"], "workpage.driver-preferences-v0.save") == {
        "action_id": "workpage.driver-preferences-v0.save",
        "kind": "save",
        "label": "Save preferences snapshot",
        "state": "available",
        "workpage_kind": "driver-preferences-v0",
        "artifact_version_id": artifact_version_id,
        "submit_path": (
            f"/api/v1/workpages/workflow-runs/{workflow_run_id}/"
            f"driver-preferences-v0/artifacts/{artifact_version_id}/submit"
        ),
        "disabled_reason": None,
    }
    alias_read = client.get(f"/api/v1/workpages/artifacts/{artifact_version_id}")
    assert alias_read.status_code == 404
    assert alias_read.payload["error"]["code"] == "not_found"


def test_driver_preferences_submit_creates_successor_and_historical_read_only(
    tmp_path: Path,
) -> None:
    seeded = seed_actual_ops_weekly_schedule_run_with_stage04_outputs(
        db_url=_db_url(tmp_path),
        tenant_id="tenant-a",
        domain_id="domain-x",
        run_tag="api:workpages:driver-preferences:submit",
    )
    workflow_run_id = str(seeded["workflow_run_id"])
    created = create_driver_preferences_snapshot(
        db_url=_db_url(tmp_path),
        tenant_id="tenant-a",
        domain_id="domain-x",
        workflow_run_id=workflow_run_id,
        run_tag="api:workpages:driver-preferences:submit",
    )
    artifact_version_id = str(created["created"]["artifact_version_id"])
    client = _client(tmp_path)

    current = client.get(
        f"/api/v1/workpages/workflow-runs/{workflow_run_id}/"
        f"driver-preferences-v0/artifacts/{artifact_version_id}"
    )
    assert current.status_code == 200, current.payload
    driver_rows = deepcopy(current.payload["preference_grid"]["drivers"])
    driver_rows[0]["preferences_by_weekday"]["mon"] = "open_to_work"

    submitted = client.post(
        f"/api/v1/workpages/workflow-runs/{workflow_run_id}/"
        f"driver-preferences-v0/artifacts/{artifact_version_id}/submit",
        payload={
            "driver_rows": [
                {
                    "driver_id": row["driver_id"],
                    "preferences_by_weekday": row["preferences_by_weekday"],
                }
                for row in driver_rows
            ],
            "idempotency_key": "api:workpages:driver-preferences:submit:successor",
        },
    )
    assert submitted.status_code == 200, submitted.payload
    latest_artifact_version_id = str(submitted.payload["submitted"]["artifact_version_id"])
    assert submitted.payload["submitted"] == {
        "workflow_run_id": workflow_run_id,
        "artifact_version_id": latest_artifact_version_id,
        "supersedes_artifact_version_id": artifact_version_id,
        "route": (
            f"/runs/{workflow_run_id}/workpages/driver-preferences-v0/artifacts/"
            f"{latest_artifact_version_id}"
        ),
    }

    historical = client.get(
        f"/api/v1/workpages/workflow-runs/{workflow_run_id}/"
        f"driver-preferences-v0/artifacts/{artifact_version_id}"
    )
    assert historical.status_code == 200, historical.payload
    historical_payload = historical.payload
    assert historical_payload["artifact_state"] == {
        "state_kind": "artifact_projection",
        "artifact_kind": "planning.driver_shift_preferences.workbook",
        "editable": False,
        "current_artifact_version_id": artifact_version_id,
        "latest_artifact_version_id": latest_artifact_version_id,
        "accepted_artifact_version_id": None,
    }
    assert historical_payload["artifact_history"]["current_artifact_version_id"] == artifact_version_id
    assert historical_payload["artifact_history"]["latest_artifact_version_id"] == latest_artifact_version_id
    assert historical_payload["artifact_history"]["previous_artifact_version_id"] is None
    assert historical_payload["artifact_history"]["next_artifact_version_id"] == latest_artifact_version_id
    assert [
        entry["artifact_version_id"]
        for entry in historical_payload["artifact_history"]["entries"]
    ] == [
        latest_artifact_version_id,
        artifact_version_id,
    ]
    assert _action_by_id(
        historical_payload["actions"], "workpage.driver-preferences-v0.save"
    ) == {
        "action_id": "workpage.driver-preferences-v0.save",
        "kind": "save",
        "label": "Save preferences snapshot",
        "state": "blocked",
        "workpage_kind": "driver-preferences-v0",
        "artifact_version_id": artifact_version_id,
        "submit_path": (
            f"/api/v1/workpages/workflow-runs/{workflow_run_id}/"
            f"driver-preferences-v0/artifacts/{artifact_version_id}/submit"
        ),
        "disabled_reason": "historical_artifact_read_only",
    }


def test_schedule_contracts_use_latest_preferences_softly_and_keep_pinned_drafts_saveable(
    tmp_path: Path,
) -> None:
    seeded = seed_actual_ops_weekly_schedule_run_with_stage04_outputs(
        db_url=_db_url(tmp_path),
        tenant_id="tenant-a",
        domain_id="domain-x",
        run_tag="api:workpages:driver-preferences:schedule-soft",
    )
    workflow_run_id = str(seeded["workflow_run_id"])
    initial_schedule_artifact_id = str(
        seeded["stage04_outputs"]["draft_workbook"]["artifact_version_id"]
    )
    client = _client(tmp_path)

    created = create_driver_preferences_snapshot(
        db_url=_db_url(tmp_path),
        tenant_id="tenant-a",
        domain_id="domain-x",
        workflow_run_id=workflow_run_id,
        run_tag="api:workpages:driver-preferences:schedule-soft",
    )
    assignment_rows, reserve_rows = _schedule_submit_rows(
        client,
        workflow_run_id,
        initial_schedule_artifact_id,
    )
    first_preferences_artifact_id = str(created["created"]["artifact_version_id"])
    run_schedule_before_update = client.get(
        f"/api/v1/workpages/workflow-runs/{workflow_run_id}/schedule-v0"
    )
    assert run_schedule_before_update.status_code == 200, run_schedule_before_update.payload
    selected_date = str(
        run_schedule_before_update.payload["calculations"]["selected_day"]["service_date"]
    )
    conflict_driver_id = next(
        str(row["assigned_driver_id"])
        for row in [*assignment_rows, *reserve_rows]
        if row.get("service_date") == selected_date and str(row.get("assigned_driver_id") or "").strip()
    )

    current_preferences = client.get(
        f"/api/v1/workpages/workflow-runs/{workflow_run_id}/"
        f"driver-preferences-v0/artifacts/{first_preferences_artifact_id}"
    )
    assert current_preferences.status_code == 200, current_preferences.payload
    driver_rows = deepcopy(current_preferences.payload["preference_grid"]["drivers"])
    weekday_key = {
        "2026-03-22": "sun",
        "2026-03-23": "mon",
        "2026-03-24": "tue",
        "2026-03-25": "wed",
        "2026-03-26": "thu",
        "2026-03-27": "fri",
        "2026-03-28": "sat",
    }[selected_date]
    for row in driver_rows:
        if row["driver_id"] == conflict_driver_id:
            row["preferences_by_weekday"][weekday_key] = "definitely_can_not_work"

    updated_preferences = client.post(
        f"/api/v1/workpages/workflow-runs/{workflow_run_id}/"
        f"driver-preferences-v0/artifacts/{first_preferences_artifact_id}/submit",
        payload={
            "driver_rows": [
                {
                    "driver_id": row["driver_id"],
                    "preferences_by_weekday": row["preferences_by_weekday"],
                }
                for row in driver_rows
            ],
            "idempotency_key": "api:workpages:driver-preferences:schedule-soft:update",
        },
    )
    assert updated_preferences.status_code == 200, updated_preferences.payload
    pinned_preferences_artifact_id = str(updated_preferences.payload["submitted"]["artifact_version_id"])

    saved_schedule = client.post(
        f"/api/v1/workpages/workflow-runs/{workflow_run_id}/"
        f"schedule-v0/artifacts/{initial_schedule_artifact_id}/submit",
        payload={
            "rows": assignment_rows,
            "reserve_rows": reserve_rows,
            "idempotency_key": "api:workpages:driver-preferences:schedule-soft:save",
        },
    )
    assert saved_schedule.status_code == 200, saved_schedule.payload
    pinned_schedule_artifact_id = str(saved_schedule.payload["submitted"]["artifact_version_id"])

    aligned_schedule_payload = client.get(
        f"/api/v1/workpages/workflow-runs/{workflow_run_id}/"
        f"schedule-v0/artifacts/{pinned_schedule_artifact_id}"
    ).payload
    aligned_driver_preferences_dependency = next(
        row
        for row in aligned_schedule_payload["dependencies"]
        if row["dependency_key"] == "driver_preferences"
    )
    assert aligned_driver_preferences_dependency["artifact_version_id"] == pinned_preferences_artifact_id
    assert aligned_driver_preferences_dependency["state"] == "aligned"
    assert any(
        metric["driver_id"] == conflict_driver_id
        and metric["preference_state"] == "definitely_can_not_work"
        for metric in aligned_schedule_payload["calculations"]["driver_metrics"]
    )
    assert any(
        check["check_id"] == "driver_preferences_alignment"
        and check["blocking"] is False
        and conflict_driver_id in (check.get("affected_driver_ids") or [])
        for check in aligned_schedule_payload["calculations"]["checks"]
    )

    for row in driver_rows:
        if row["driver_id"] == conflict_driver_id:
            row["preferences_by_weekday"][weekday_key] = "prefer_not_to_work"
    drifted_preferences = client.post(
        f"/api/v1/workpages/workflow-runs/{workflow_run_id}/"
        f"driver-preferences-v0/artifacts/{pinned_preferences_artifact_id}/submit",
        payload={
            "driver_rows": [
                {
                    "driver_id": row["driver_id"],
                    "preferences_by_weekday": row["preferences_by_weekday"],
                }
                for row in driver_rows
            ],
            "idempotency_key": "api:workpages:driver-preferences:schedule-soft:drift",
        },
    )
    assert drifted_preferences.status_code == 200, drifted_preferences.payload
    latest_preferences_artifact_id = str(drifted_preferences.payload["submitted"]["artifact_version_id"])

    run_schedule = client.get(f"/api/v1/workpages/workflow-runs/{workflow_run_id}/schedule-v0")
    assert run_schedule.status_code == 200, run_schedule.payload
    run_payload = run_schedule.payload
    run_driver_preferences_dependency = next(
        row
        for row in run_payload["dependencies"]
        if row["dependency_key"] == "driver_preferences"
    )
    assert run_driver_preferences_dependency["artifact_version_id"] == latest_preferences_artifact_id
    assert run_driver_preferences_dependency["state"] == "resolved"
    assert _action_by_id(run_payload["actions"], "workpage.driver-preferences-v0.open_latest") == {
        "action_id": "workpage.driver-preferences-v0.open_latest",
        "kind": "open_latest",
        "label": "Open driver preferences",
        "state": "available",
        "workpage_kind": "driver-preferences-v0",
        "artifact_version_id": latest_preferences_artifact_id,
        "route": (
            f"/runs/{workflow_run_id}/workpages/driver-preferences-v0/artifacts/"
            f"{latest_preferences_artifact_id}"
        ),
    }
    assert set(run_payload["calculations"]["selected_day"]["available_preference_buckets"]) == {
        "open_to_work",
        "prefer_not_to_work",
        "definitely_can_not_work",
        "unset",
    }

    drifted_schedule_payload = client.get(
        f"/api/v1/workpages/workflow-runs/{workflow_run_id}/"
        f"schedule-v0/artifacts/{pinned_schedule_artifact_id}"
    ).payload
    drifted_driver_preferences_dependency = next(
        row
        for row in drifted_schedule_payload["dependencies"]
        if row["dependency_key"] == "driver_preferences"
    )
    assert drifted_driver_preferences_dependency["artifact_version_id"] == pinned_preferences_artifact_id
    assert drifted_driver_preferences_dependency["state"] == "drifted"
    assert _action_by_id(drifted_schedule_payload["actions"], "workpage.schedule-v0.preview_recalc")["state"] == "available"
    assert _action_by_id(drifted_schedule_payload["actions"], "workpage.schedule-v0.save_draft")["state"] == "available"
