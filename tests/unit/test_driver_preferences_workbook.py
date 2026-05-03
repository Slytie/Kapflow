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


def _actual_ops_bundle(*, workflow_run_id: str = "wr-driver-preferences-001"):
    fixture_payloads = build_actual_ops_weekly_stage04_fixture_payloads()
    workflow_run = {
        "workflow_run_id": workflow_run_id,
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
    bundle = _actual_ops_bundle()
    workbook = build_initial_driver_preferences_workbook(bundle=bundle)
    repeated = build_initial_driver_preferences_workbook(bundle=bundle)

    assert workbook["planning_week_id"] == "PW-2026-W13"
    assert workbook["weekdays"] == list(DRIVER_PREFERENCE_WEEKDAY_KEYS)
    assert workbook["service_dates"] == [
        {"service_date": "2026-03-22", "label": "2026-03-22", "weekday_label": "Sun"},
        {"service_date": "2026-03-23", "label": "2026-03-23", "weekday_label": "Mon"},
        {"service_date": "2026-03-24", "label": "2026-03-24", "weekday_label": "Tue"},
        {"service_date": "2026-03-25", "label": "2026-03-25", "weekday_label": "Wed"},
        {"service_date": "2026-03-26", "label": "2026-03-26", "weekday_label": "Thu"},
        {"service_date": "2026-03-27", "label": "2026-03-27", "weekday_label": "Fri"},
        {"service_date": "2026-03-28", "label": "2026-03-28", "weekday_label": "Sat"},
    ]
    assert workbook == repeated
    assert workbook["drivers"]
    first_driver = workbook["drivers"][0]
    assert first_driver["driver_quality"] == "medium"
    assert set(first_driver["preferences_by_weekday"]) == set(DRIVER_PREFERENCE_WEEKDAY_KEYS)
    assert all(value is not None for value in first_driver["preferences_by_weekday"].values())
    assert 4 <= sum(
        1
        for value in first_driver["preferences_by_weekday"].values()
        if value == "open_to_work"
    ) <= 6


def test_driver_preferences_workbook_seed_is_stable_across_workflow_runs() -> None:
    first = build_initial_driver_preferences_workbook(
        bundle=_actual_ops_bundle(workflow_run_id="wr-driver-preferences-001")
    )
    second = build_initial_driver_preferences_workbook(
        bundle=_actual_ops_bundle(workflow_run_id="wr-driver-preferences-002")
    )

    assert first["drivers"] == second["drivers"]


def test_driver_preferences_workbook_round_trips_projection_and_submit_values() -> None:
    initial = build_initial_driver_preferences_workbook(bundle=_actual_ops_bundle())
    initial_bytes = driver_preferences_workbook_bytes_from_metadata_json(initial)
    projection = project_driver_preferences_workbook(initial_bytes)

    first_driver = projection["drivers"][0]
    second_driver = projection["drivers"][1]
    submitted_rows = [
        {
            "driver_id": row["driver_id"],
            "driver_quality": (
                "high"
                if row["driver_id"] == first_driver["driver_id"]
                else "low"
                if row["driver_id"] == second_driver["driver_id"]
                else row["driver_quality"]
            ),
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
    assert updated_projection["service_dates"] == initial["service_dates"]
    assert updated_by_id[first_driver["driver_id"]]["driver_quality"] == "high"
    assert updated_by_id[second_driver["driver_id"]]["driver_quality"] == "low"
    assert (
        updated_by_id[first_driver["driver_id"]]["preferences_by_weekday"]["mon"]
        == "open_to_work"
    )
    assert (
        updated_by_id[second_driver["driver_id"]]["preferences_by_weekday"]["fri"]
        == "prefer_not_to_work"
    )
    assert (
        updated_by_id[first_driver["driver_id"]]["preferences_by_weekday"]["sun"]
        == first_driver["preferences_by_weekday"]["sun"]
    )


def test_driver_preferences_workbook_defaults_missing_quality_to_medium() -> None:
    initial = build_initial_driver_preferences_workbook(bundle=_actual_ops_bundle())
    for row in initial["drivers"]:
        row.pop("driver_quality", None)

    projection = project_driver_preferences_workbook(
        driver_preferences_workbook_bytes_from_metadata_json(initial)
    )

    assert projection["drivers"]
    assert all(row["driver_quality"] == "medium" for row in projection["drivers"])


def test_driver_preferences_workbook_preserves_base_quality_when_submit_omits_it() -> None:
    initial = build_initial_driver_preferences_workbook(bundle=_actual_ops_bundle())
    first_driver_id = str(initial["drivers"][0]["driver_id"])
    initial["drivers"][0]["driver_quality"] = "high"
    initial_bytes = driver_preferences_workbook_bytes_from_metadata_json(initial)
    projection = project_driver_preferences_workbook(initial_bytes)

    updated_bytes = materialize_driver_preferences_workbook(
        initial_bytes,
        driver_rows=[
            {
                "driver_id": row["driver_id"],
                "preferences_by_weekday": row["preferences_by_weekday"],
            }
            for row in projection["drivers"]
        ],
    )
    updated_projection = project_driver_preferences_workbook(updated_bytes)
    updated_by_id = {row["driver_id"]: row for row in updated_projection["drivers"]}

    assert updated_by_id[first_driver_id]["driver_quality"] == "high"
    assert all(
        row["driver_quality"] in {"high", "medium", "low"}
        for row in updated_projection["drivers"]
    )
