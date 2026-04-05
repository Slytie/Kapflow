from __future__ import annotations

from onetruth.application.services.logistics_weekly_agent_pilot import (
    build_actual_ops_weekly_stage04_fixture_payloads,
)
from onetruth.application.services.schedule_control.bundle_builder import (
    build_weekly_schedule_control_bundle,
)
from onetruth.application.services.schedule_control.driver_preferences_workbook import (
    DRIVER_PREFERENCE_WEEKDAY_KEYS,
    build_initial_driver_preferences_workbook,
    driver_preferences_workbook_bytes_from_metadata_json,
    materialize_driver_preferences_workbook,
    project_driver_preferences_workbook,
)


def _actual_ops_bundle():
    fixture_payloads = build_actual_ops_weekly_stage04_fixture_payloads()
    workflow_run = {
        "workflow_run_id": "wr-driver-preferences-001",
        "partition_key": "PW-2026-W13",
        "logical_date": "2026-03-22",
    }
    return build_weekly_schedule_control_bundle(
        workflow_run=workflow_run,
        route_slot_requirements_artifact={
            "artifact_kind": "planning.route_slot_requirements.workbook",
            "dataset_key": "planning.route_slot_requirements.workbook",
            "metadata_json": fixture_payloads["route_slot_requirements"],
        },
        driver_capabilities_artifact={
            "artifact_kind": "planning.driver_capabilities.workbook",
            "dataset_key": "planning.driver_capabilities.workbook",
            "metadata_json": fixture_payloads["driver_capabilities"],
        },
        approved_availability_artifact={
            "artifact_kind": "planning.approved_availability.workbook",
            "dataset_key": "planning.approved_availability.workbook",
            "metadata_json": fixture_payloads["approved_availability"],
        },
        actual_hours_artifact={
            "artifact_kind": "planning.actual_hours_snapshot.workbook",
            "dataset_key": "planning.actual_hours_snapshot.workbook",
            "metadata_json": fixture_payloads["actual_hours"],
        },
    )


def test_driver_preferences_workbook_builds_initial_snapshot_from_roster_scope() -> None:
    workbook = build_initial_driver_preferences_workbook(bundle=_actual_ops_bundle())

    assert workbook["planning_week_id"] == "PW-2026-W13"
    assert workbook["weekdays"] == list(DRIVER_PREFERENCE_WEEKDAY_KEYS)
    assert workbook["drivers"]
    first_driver = workbook["drivers"][0]
    assert set(first_driver["preferences_by_weekday"]) == set(DRIVER_PREFERENCE_WEEKDAY_KEYS)
    assert all(value is None for value in first_driver["preferences_by_weekday"].values())


def test_driver_preferences_workbook_round_trips_projection_and_submit_values() -> None:
    initial = build_initial_driver_preferences_workbook(bundle=_actual_ops_bundle())
    initial_bytes = driver_preferences_workbook_bytes_from_metadata_json(initial)
    projection = project_driver_preferences_workbook(initial_bytes)

    first_driver = projection["drivers"][0]
    second_driver = projection["drivers"][1]
    submitted_rows = [
        {
            "driver_id": row["driver_id"],
            "preferences_by_weekday": {
                **row["preferences_by_weekday"],
                "mon": (
                    "open_to_work"
                    if row["driver_id"] == first_driver["driver_id"]
                    else row["preferences_by_weekday"]["mon"]
                ),
                "fri": (
                    "prefer_not_to_work"
                    if row["driver_id"] == second_driver["driver_id"]
                    else row["preferences_by_weekday"]["fri"]
                ),
            },
        }
        for row in projection["drivers"]
    ]

    updated_bytes = materialize_driver_preferences_workbook(
        initial_bytes,
        driver_rows=submitted_rows,
    )
    updated_projection = project_driver_preferences_workbook(updated_bytes)
    updated_by_id = {row["driver_id"]: row for row in updated_projection["drivers"]}

    assert updated_projection["weekdays"] == list(DRIVER_PREFERENCE_WEEKDAY_KEYS)
    assert (
        updated_by_id[first_driver["driver_id"]]["preferences_by_weekday"]["mon"]
        == "open_to_work"
    )
    assert (
        updated_by_id[second_driver["driver_id"]]["preferences_by_weekday"]["fri"]
        == "prefer_not_to_work"
    )
    assert (
        updated_by_id[first_driver["driver_id"]]["preferences_by_weekday"]["sun"] is None
    )
