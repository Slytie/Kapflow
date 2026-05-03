from __future__ import annotations

from copy import deepcopy
from pathlib import Path
import sqlite3

from onetruth.application.services.schedule_control import build_weekly_schedule_control_bundle
from onetruth.application.services.schedule_control.validation import evaluate_hard_constraints
from onetruth.infrastructure.repositories.artifact_versions import (
    list_artifact_versions_for_workflow_run,
)
from onetruth.infrastructure.repositories.workflow_runs import get_workflow_run
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


def _runtime_connection(tmp_path: Path) -> sqlite3.Connection:
    connection = sqlite3.connect(tmp_path / "runtime.db")
    connection.row_factory = sqlite3.Row
    return connection


def _latest_artifact_for_kind(
    artifacts: list[dict[str, object]],
    artifact_kind: str,
) -> dict[str, object]:
    matches = [
        artifact
        for artifact in artifacts
        if artifact.get("artifact_kind") == artifact_kind
    ]
    assert matches
    return sorted(
        matches,
        key=lambda item: (
            str(item.get("created_at") or ""),
            str(item.get("artifact_version_id") or ""),
        ),
    )[-1]


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
    assert payload["preference_grid"]["service_dates"] == [
        {"service_date": "2026-03-22", "label": "2026-03-22", "weekday_label": "Sun"},
        {"service_date": "2026-03-23", "label": "2026-03-23", "weekday_label": "Mon"},
        {"service_date": "2026-03-24", "label": "2026-03-24", "weekday_label": "Tue"},
        {"service_date": "2026-03-25", "label": "2026-03-25", "weekday_label": "Wed"},
        {"service_date": "2026-03-26", "label": "2026-03-26", "weekday_label": "Thu"},
        {"service_date": "2026-03-27", "label": "2026-03-27", "weekday_label": "Fri"},
        {"service_date": "2026-03-28", "label": "2026-03-28", "weekday_label": "Sat"},
    ]
    assert payload["preference_grid"]["drivers"]
    assert all(
        row["driver_quality"] == "medium"
        for row in payload["preference_grid"]["drivers"]
    )
    assert payload["driver_availability_exceptions"] == {"items": []}
    assert "driver_availability_exceptions" not in payload["preference_grid"]
    assert all(
        value is not None
        for value in payload["preference_grid"]["drivers"][0]["preferences_by_weekday"].values()
    )
    assert 4 <= sum(
        1
        for value in payload["preference_grid"]["drivers"][0]["preferences_by_weekday"].values()
        if value == "open_to_work"
    ) <= 6
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
        "action_ref": _action_ref(
            action_id="workpage.driver-preferences-v0.create_snapshot",
            workpage_kind="driver-preferences-v0",
            workflow_run_id=workflow_run_id,
            artifact_version_id=None,
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
    assert payload["preference_grid"]["service_dates"] == [
        {"service_date": "2026-03-22", "label": "2026-03-22", "weekday_label": "Sun"},
        {"service_date": "2026-03-23", "label": "2026-03-23", "weekday_label": "Mon"},
        {"service_date": "2026-03-24", "label": "2026-03-24", "weekday_label": "Tue"},
        {"service_date": "2026-03-25", "label": "2026-03-25", "weekday_label": "Wed"},
        {"service_date": "2026-03-26", "label": "2026-03-26", "weekday_label": "Thu"},
        {"service_date": "2026-03-27", "label": "2026-03-27", "weekday_label": "Fri"},
        {"service_date": "2026-03-28", "label": "2026-03-28", "weekday_label": "Sat"},
    ]
    assert all(
        value is not None
        for value in payload["preference_grid"]["drivers"][0]["preferences_by_weekday"].values()
    )
    assert payload["preference_grid"]["drivers"][0]["driver_quality"] == "medium"
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
        "action_ref": _action_ref(
            action_id="workpage.driver-preferences-v0.save",
            workpage_kind="driver-preferences-v0",
            workflow_run_id=workflow_run_id,
            artifact_version_id=artifact_version_id,
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
    driver_rows[0]["driver_quality"] = "high"

    submitted = client.post(
        f"/api/v1/workpages/workflow-runs/{workflow_run_id}/"
        f"driver-preferences-v0/artifacts/{artifact_version_id}/submit",
        payload={
            "driver_rows": [
                {
                    "driver_id": row["driver_id"],
                    "driver_quality": row["driver_quality"],
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
    latest_payload = client.get(
        f"/api/v1/workpages/workflow-runs/{workflow_run_id}/"
        f"driver-preferences-v0/artifacts/{latest_artifact_version_id}"
    ).payload
    updated_by_id = {
        row["driver_id"]: row
        for row in latest_payload["preference_grid"]["drivers"]
    }
    assert updated_by_id[driver_rows[0]["driver_id"]]["driver_quality"] == "high"
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
        "action_ref": _action_ref(
            action_id="workpage.driver-preferences-v0.save",
            workpage_kind="driver-preferences-v0",
            workflow_run_id=workflow_run_id,
            artifact_version_id=artifact_version_id,
        ),
        "disabled_reason": "historical_artifact_read_only",
    }


def test_driver_preferences_availability_exception_creates_approved_hard_block(
    tmp_path: Path,
) -> None:
    seeded = seed_actual_ops_weekly_schedule_run_with_stage04_outputs(
        db_url=_db_url(tmp_path),
        tenant_id="tenant-a",
        domain_id="domain-x",
        run_tag="api:workpages:driver-preferences:availability-exception",
    )
    workflow_run_id = str(seeded["workflow_run_id"])
    client = _client(tmp_path)

    before = client.get(
        f"/api/v1/workpages/workflow-runs/{workflow_run_id}/driver-preferences-v0"
    )
    assert before.status_code == 200, before.payload
    preference_grid_before = deepcopy(before.payload["preference_grid"])
    driver = preference_grid_before["drivers"][0]
    driver_id = str(driver["driver_id"])
    driver_name = str(driver["driver_name"])
    action_ref = _action_ref(
        action_id="workpage.driver-preferences-v0.add_availability_exception",
        workpage_kind="driver-preferences-v0",
        workflow_run_id=workflow_run_id,
        artifact_version_id=None,
    )

    created = client.post(
        f"/api/v1/workpages/workflow-runs/{workflow_run_id}/"
        "driver-preferences-v0/availability-exceptions",
        payload={
            "driver_id": driver_id,
            "start_date": "2026-03-24",
            "end_date": "2026-03-25",
            "reason_code": "wedding",
            "reason_note": "Family wedding",
            "action_ref": action_ref,
            "idempotency_key": "api:workpages:driver-preferences:availability-exception:add",
        },
    )
    assert created.status_code == 200, created.payload
    created_again = client.post(
        f"/api/v1/workpages/workflow-runs/{workflow_run_id}/"
        "driver-preferences-v0/availability-exceptions",
        payload={
            "driver_id": driver_id,
            "start_date": "2026-03-24",
            "end_date": "2026-03-25",
            "reason_code": "wedding",
            "reason_note": "Family wedding",
            "action_ref": action_ref,
            "idempotency_key": "api:workpages:driver-preferences:availability-exception:add",
        },
    )
    assert created_again.status_code == 200, created_again.payload
    assert created_again.payload["created"] == created.payload["created"]

    exception = created.payload["created"]["exception"]
    assert exception == {
        "exception_id": exception["exception_id"],
        "driver_id": driver_id,
        "driver_name": driver_name,
        "start_date": "2026-03-24",
        "end_date": "2026-03-25",
        "reason_code": "wedding",
        "reason_note": "Family wedding",
        "status": "approved",
        "source_workflow_run_id": exception["source_workflow_run_id"],
        "source_artifact_version_id": exception["source_artifact_version_id"],
        "affected_planning_week_ids": ["PW-2026-W13"],
    }
    assert created.payload["created"]["affected_service_dates"] == [
        "2026-03-24",
        "2026-03-25",
    ]

    after = client.get(
        f"/api/v1/workpages/workflow-runs/{workflow_run_id}/driver-preferences-v0"
    )
    assert after.status_code == 200, after.payload
    assert after.payload["preference_grid"] == preference_grid_before
    assert after.payload["driver_availability_exceptions"]["items"] == [exception]

    with _runtime_connection(tmp_path) as connection:
        workflow_run = get_workflow_run(connection, workflow_run_id)
        assert workflow_run is not None
        artifacts = list_artifact_versions_for_workflow_run(connection, workflow_run_id)
        latest_availability = _latest_artifact_for_kind(
            artifacts,
            "planning.approved_availability.workbook",
        )
        metadata = latest_availability["metadata_json"]
        columns = list(metadata["columns"])
        rows = [
            dict(zip(columns, row, strict=False))
            for row in metadata["rows"]
        ]
        affected_rows = [
            row
            for row in rows
            if row.get("driver_id") == driver_id
            and row.get("service_date") in {"2026-03-24", "2026-03-25"}
        ]
        assert [row["service_date"] for row in affected_rows] == [
            "2026-03-24",
            "2026-03-25",
        ]
        assert all(row["availability_state"] == "CANNOT" for row in affected_rows)
        assert all(row["locked_by_manager"] == "yes" for row in affected_rows)
        assert all(row["source_exception_id"] == exception["exception_id"] for row in affected_rows)

        artifacts_by_kind = {
            str(artifact["artifact_kind"]): artifact
            for artifact in artifacts
        }
        artifacts_by_kind["planning.approved_availability.workbook"] = latest_availability
        bundle = build_weekly_schedule_control_bundle(
            workflow_run=workflow_run,
            route_slot_requirements_artifact=artifacts_by_kind[
                "planning.route_slot_requirements.workbook"
            ],
            driver_capabilities_artifact=artifacts_by_kind[
                "planning.driver_capabilities.workbook"
            ],
            approved_availability_artifact=latest_availability,
            actual_hours_artifact=artifacts_by_kind[
                "planning.actual_hours_snapshot.workbook"
            ],
        )
        route_slot = next(
            slot for slot in bundle.route_slots if slot.service_date == "2026-03-24"
        )
        bundle_driver = next(item for item in bundle.drivers if item.driver_id == driver_id)
        validation = evaluate_hard_constraints(
            bundle=bundle,
            route_slot=route_slot,
            driver=bundle_driver,
        )
        assert validation.driver_day_availability_state == "CANNOT"
        assert "driver_unavailable" in validation.reasons

    other_client = RuntimeApiClient(
        db_url=_db_url(tmp_path),
        tenant_id="tenant-b",
        domain_id="domain-x",
        actor_id="human:ops-manager-2",
        actor_type="human",
        actor_roles=["operations_manager"],
    )
    denied = other_client.post(
        f"/api/v1/workpages/workflow-runs/{workflow_run_id}/"
        "driver-preferences-v0/availability-exceptions",
        payload={
            "driver_id": driver_id,
            "start_date": "2026-03-24",
            "end_date": "2026-03-24",
            "reason_code": "wedding",
            "reason_note": "Cross tenant",
            "idempotency_key": "api:workpages:driver-preferences:availability-exception:denied",
        },
    )
    assert denied.status_code == 404


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
                    "driver_quality": row["driver_quality"],
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
    aligned_heatmap = next(
        section
        for section in aligned_schedule_payload["workpage"]["sections"]
        if section["kind"] == "schedule_heatmap"
    )
    conflict_heatmap_cell = next(
        cell
        for person in aligned_heatmap["people"]
        if person["driver_id"] == conflict_driver_id
        for cell in person["cells"]
        if cell["service_date"] == selected_date
    )
    assert conflict_heatmap_cell["preference_state"] == "definitely_can_not_work"
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
                    "driver_quality": row["driver_quality"],
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
        "action_ref": _action_ref(
            action_id="workpage.driver-preferences-v0.open_latest",
            workpage_kind="driver-preferences-v0",
            workflow_run_id=workflow_run_id,
            artifact_version_id=latest_preferences_artifact_id,
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
