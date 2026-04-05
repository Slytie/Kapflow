from __future__ import annotations

from onetruth.application.services.schedule_control.route_demand_workbook import (
    materialize_route_demand_workbook,
    project_route_demand_workbook,
    route_demand_workbook_bytes_from_metadata_json,
)


def test_route_demand_workbook_updates_single_standard_row_days() -> None:
    workbook = {
        "columns": [
            "service_date",
            "route_slot_id",
            "route_slot_class",
            "required_count",
            "station_code",
            "service_area",
        ],
        "rows": [
            ["2026-03-22", "slot-20260322-standard", "cycle1_standard", 10, "DVC4", "Pitt Meadows"],
        ],
        "daily_demand_columns": [
            "service_date",
            "planned_route_count",
            "standard_slot_count",
            "rescue_slot_count",
            "overflow_slot_count",
        ],
        "daily_demand_rows": [
            ["2026-03-22", 10, 10, 0, 0],
        ],
    }

    updated = materialize_route_demand_workbook(
        route_demand_workbook_bytes_from_metadata_json(workbook),
        daily_demand_rows=[{"service_date": "2026-03-22", "planned_route_count": 13}],
    )
    projection = project_route_demand_workbook(updated)

    assert projection["rows"] == [
        {
            "service_date": "2026-03-22",
            "route_slot_id": "slot-20260322-standard",
            "route_slot_class": "cycle1_standard",
            "required_count": 13,
            "station_code": "DVC4",
            "service_area": "Pitt Meadows",
        }
    ]
    assert projection["daily_demand_rows"] == [
        {
            "service_date": "2026-03-22",
            "planned_route_count": 13,
            "standard_slot_count": 13,
            "rescue_slot_count": 0,
            "overflow_slot_count": 0,
        }
    ]


def test_route_demand_workbook_preserves_non_standard_buckets_and_split_ratio() -> None:
    workbook = {
        "columns": [
            "service_date",
            "route_slot_id",
            "route_slot_class",
            "required_count",
            "slot_band",
            "station_code",
            "service_area",
        ],
        "rows": [
            ["2026-03-16", "slot-20260316-std-early", "cycle1_standard_early", 11, "early", "DVC4", "Pitt Meadows"],
            ["2026-03-16", "slot-20260316-std-late", "cycle1_standard_late", 6, "late", "DVC4", "Pitt Meadows"],
            ["2026-03-16", "slot-20260316-rsc", "cycle1_rescue", 3, "rescue", "DVC4", "Pitt Meadows"],
            ["2026-03-16", "slot-20260316-ovf", "cycle1_overflow", 3, "overflow", "DVC4", "Pitt Meadows"],
        ],
        "daily_demand_columns": [
            "service_date",
            "planned_route_count",
            "standard_slot_count",
            "standard_early_slot_count",
            "standard_late_slot_count",
            "rescue_slot_count",
            "overflow_slot_count",
        ],
        "daily_demand_rows": [
            ["2026-03-16", 23, 17, 11, 6, 3, 3],
        ],
    }

    updated = materialize_route_demand_workbook(
        route_demand_workbook_bytes_from_metadata_json(workbook),
        daily_demand_rows=[{"service_date": "2026-03-16", "planned_route_count": 28}],
    )
    projection = project_route_demand_workbook(updated)

    assert projection["rows"] == [
        {
            "service_date": "2026-03-16",
            "route_slot_id": "slot-20260316-std-early",
            "route_slot_class": "cycle1_standard_early",
            "required_count": 14,
            "slot_band": "early",
            "station_code": "DVC4",
            "service_area": "Pitt Meadows",
        },
        {
            "service_date": "2026-03-16",
            "route_slot_id": "slot-20260316-std-late",
            "route_slot_class": "cycle1_standard_late",
            "required_count": 8,
            "slot_band": "late",
            "station_code": "DVC4",
            "service_area": "Pitt Meadows",
        },
        {
            "service_date": "2026-03-16",
            "route_slot_id": "slot-20260316-rsc",
            "route_slot_class": "cycle1_rescue",
            "required_count": 3,
            "slot_band": "rescue",
            "station_code": "DVC4",
            "service_area": "Pitt Meadows",
        },
        {
            "service_date": "2026-03-16",
            "route_slot_id": "slot-20260316-ovf",
            "route_slot_class": "cycle1_overflow",
            "required_count": 3,
            "slot_band": "overflow",
            "station_code": "DVC4",
            "service_area": "Pitt Meadows",
        },
    ]
    assert projection["daily_demand_rows"] == [
        {
            "service_date": "2026-03-16",
            "planned_route_count": 28,
            "standard_slot_count": 22,
            "standard_early_slot_count": 14,
            "standard_late_slot_count": 8,
            "rescue_slot_count": 3,
            "overflow_slot_count": 3,
        }
    ]
