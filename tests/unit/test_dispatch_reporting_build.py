from __future__ import annotations

from onetruth.application.services.dispatch_reporting_build import (
    build_planning_actual_hours_snapshot_payload,
    merge_planning_actual_hours_snapshot_payloads,
)


def test_build_planning_actual_hours_snapshot_payload_aggregates_duplicate_driver_days() -> None:
    payload = build_planning_actual_hours_snapshot_payload(
        normalized_payload={
            "rows": [
                {
                    "service_date": "2026-03-16",
                    "driver_id": "A1",
                    "driver_name": "Driver A",
                    "route_id": "CX93",
                    "actual_minutes": 540,
                },
                {
                    "service_date": "2026-03-16",
                    "driver_id": "A1",
                    "driver_name": "Driver A",
                    "route_id": "CX94",
                    "actual_minutes": 120,
                },
                {
                    "service_date": "2026-03-17",
                    "driver_id": "B2",
                    "driver_name": "Driver B",
                    "route_id": "CX95",
                    "actual_minutes": 600,
                },
            ]
        },
        source_artifact_version_id="av-reporting-final-1",
    )

    assert payload["columns"] == [
        "service_date",
        "driver_id",
        "driver_name",
        "historical_state",
        "actual_minutes",
        "route_id",
        "route_slot_class",
        "call_in_sick_flag",
        "cancellation_flag",
        "non_working_day_flag",
        "source_snapshot_row_ref",
    ]
    assert payload["rows"] == [
        [
            "2026-03-16",
            "A1",
            "Driver A",
            "WORKED",
            660,
            "CX93,CX94",
            "",
            0,
            0,
            0,
            payload["rows"][0][10],
        ],
        [
            "2026-03-17",
            "B2",
            "Driver B",
            "WORKED",
            600,
            "CX95",
            "",
            0,
            0,
            0,
            payload["rows"][1][10],
        ],
    ]
    assert payload["rows"][0][10].startswith("dispatch-reporting:")
    assert payload["rows"][1][10].startswith("dispatch-reporting:")


def test_merge_planning_actual_hours_snapshot_payloads_replaces_matching_driver_days() -> None:
    current_payload = {
        "columns": [
            "service_date",
            "driver_id",
            "driver_name",
            "historical_state",
            "actual_minutes",
            "route_id",
            "route_slot_class",
            "call_in_sick_flag",
            "cancellation_flag",
            "non_working_day_flag",
            "source_snapshot_row_ref",
        ],
        "rows": [
            [
                "2026-03-15",
                "A1",
                "Driver A",
                "WORKED",
                500,
                "CX90",
                "",
                0,
                0,
                0,
                "dispatch-reporting:old",
            ],
            [
                "2026-03-16",
                "B2",
                "Driver B",
                "WORKED",
                600,
                "CX91",
                "",
                0,
                0,
                0,
                "dispatch-reporting:current",
            ],
        ],
    }
    incoming_payload = {
        "columns": list(current_payload["columns"]),
        "rows": [
            [
                "2026-03-16",
                "B2",
                "Driver B",
                "WORKED",
                720,
                "CX92",
                "",
                0,
                0,
                0,
                "dispatch-reporting:new",
            ],
            [
                "2026-03-17",
                "C3",
                "Driver C",
                "WORKED",
                480,
                "CX93",
                "",
                0,
                0,
                0,
                "dispatch-reporting:added",
            ],
        ],
    }

    merged = merge_planning_actual_hours_snapshot_payloads(
        current_payload=current_payload,
        incoming_payload=incoming_payload,
    )

    assert merged["rows"] == [
        current_payload["rows"][0],
        incoming_payload["rows"][0],
        incoming_payload["rows"][1],
    ]
