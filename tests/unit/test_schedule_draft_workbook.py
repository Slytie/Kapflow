from __future__ import annotations

import json

import pytest

from onetruth.application.services.schedule_control.draft_workbook import (
    append_stage04_draft_weekly_schedule_assignment_rows,
    draft_workbook_bytes_from_metadata_json,
    materialize_stage04_draft_weekly_schedule_workbook,
    project_stage04_draft_weekly_schedule_workbook,
)


def _base_workbook_bytes() -> bytes:
    return json.dumps(
        {
            "columns": [
                "service_date",
                "route_slot_id",
                "assigned_driver_id",
                "assignment_status",
                "projected_minutes",
                "candidate_delta_id",
            ],
            "rows": [
                ["2026-03-22", "slot-001", "DRV-01", "assigned", 540, "cand-001"],
                ["2026-03-23", "slot-002", "DRV-02", "assigned", 480, "cand-001"],
            ],
            "reserve_rows": [
                {
                    "service_date": "2026-03-22",
                    "route_slot_id": "reserve-001",
                    "assigned_driver_id": "DRV-03",
                    "assignment_status": "on_call",
                    "phase": "reserve_selection",
                    "projected_minutes": 0,
                }
            ],
            "iteration_deltas": [
                {
                    "iteration_index": 1,
                    "batch_id": "batch-001",
                    "planning_phase": "baseline_allocation",
                }
            ],
        },
        indent=2,
        sort_keys=True,
    ).encode("utf-8")


def test_project_stage04_draft_weekly_schedule_workbook_decodes_rows_to_objects() -> None:
    projection = project_stage04_draft_weekly_schedule_workbook(_base_workbook_bytes())

    assert projection["columns"] == [
        "service_date",
        "route_slot_id",
        "assigned_driver_id",
        "assignment_status",
        "projected_minutes",
        "candidate_delta_id",
    ]
    assert projection["rows"][0] == {
        "service_date": "2026-03-22",
        "route_slot_id": "slot-001",
        "assigned_driver_id": "DRV-01",
        "assignment_status": "assigned",
        "projected_minutes": 540,
        "candidate_delta_id": "cand-001",
    }
    assert projection["reserve_rows"][0]["route_slot_id"] == "reserve-001"
    assert projection["iteration_deltas"][0]["iteration_index"] == 1


def test_materialize_stage04_draft_weekly_schedule_workbook_updates_only_editable_fields() -> None:
    projection = project_stage04_draft_weekly_schedule_workbook(_base_workbook_bytes())
    rows = [dict(row) for row in projection["rows"]]
    reserve_rows = [dict(row) for row in projection["reserve_rows"]]

    rows[0]["assigned_driver_id"] = "DRV-77"
    rows[0]["assignment_status"] = "manual_override"
    reserve_rows[0]["assigned_driver_id"] = "DRV-88"
    reserve_rows[0]["assignment_status"] = "manual_override"

    updated_bytes = materialize_stage04_draft_weekly_schedule_workbook(
        _base_workbook_bytes(),
        rows=rows,
        reserve_rows=reserve_rows,
    )
    updated = project_stage04_draft_weekly_schedule_workbook(updated_bytes)

    assert updated["rows"][0]["assigned_driver_id"] == "DRV-77"
    assert updated["rows"][0]["assignment_status"] == "manual_override"
    assert updated["rows"][0]["projected_minutes"] == 540
    assert updated["reserve_rows"][0]["assigned_driver_id"] == "DRV-88"
    assert updated["reserve_rows"][0]["assignment_status"] == "manual_override"
    assert updated["iteration_deltas"] == projection["iteration_deltas"]


def test_materialize_stage04_draft_weekly_schedule_workbook_preserves_extra_top_level_fields() -> None:
    base_payload = json.loads(_base_workbook_bytes().decode("utf-8"))
    base_payload["accepted_series_key"] = "weekly_schedule_planning.v1:dvc4:pitt-meadows"
    base_bytes = json.dumps(base_payload, indent=2, sort_keys=True).encode("utf-8")
    projection = project_stage04_draft_weekly_schedule_workbook(base_bytes)

    updated_bytes = materialize_stage04_draft_weekly_schedule_workbook(
        base_bytes,
        rows=projection["rows"],
        reserve_rows=projection["reserve_rows"],
    )

    assert json.loads(updated_bytes.decode("utf-8"))["accepted_series_key"] == (
        "weekly_schedule_planning.v1:dvc4:pitt-meadows"
    )


def test_append_stage04_draft_weekly_schedule_assignment_rows_appends_new_rows_after_validation() -> None:
    projection = project_stage04_draft_weekly_schedule_workbook(_base_workbook_bytes())
    rows = [dict(row) for row in projection["rows"]]
    reserve_rows = [dict(row) for row in projection["reserve_rows"]]
    rows[0]["assigned_driver_id"] = "DRV-77"
    rows[0]["assignment_status"] = "manual_override"
    reserve_rows[0]["assigned_driver_id"] = "DRV-88"
    reserve_rows[0]["assignment_status"] = "manual_override"

    updated_bytes = append_stage04_draft_weekly_schedule_assignment_rows(
        _base_workbook_bytes(),
        rows=rows,
        reserve_rows=reserve_rows,
        appended_rows=[
            {
                "service_date": "2026-03-24",
                "route_slot_id": "slot-003",
                "assigned_driver_id": "DRV-99",
                "assignment_status": "manual_override",
                "projected_minutes": 525,
                "candidate_delta_id": "cand-777",
            }
        ],
    )
    updated = project_stage04_draft_weekly_schedule_workbook(updated_bytes)

    assert updated["rows"][-1] == {
        "service_date": "2026-03-24",
        "route_slot_id": "slot-003",
        "assigned_driver_id": "DRV-99",
        "assignment_status": "manual_override",
        "projected_minutes": 525,
        "candidate_delta_id": "cand-777",
    }
    assert updated["rows"][0]["assigned_driver_id"] == "DRV-77"
    assert updated["reserve_rows"][0]["assigned_driver_id"] == "DRV-88"


def test_append_stage04_draft_weekly_schedule_assignment_rows_rejects_duplicate_identity() -> None:
    projection = project_stage04_draft_weekly_schedule_workbook(_base_workbook_bytes())

    with pytest.raises(ValueError, match="duplicates existing row identity"):
        append_stage04_draft_weekly_schedule_assignment_rows(
            _base_workbook_bytes(),
            rows=projection["rows"],
            reserve_rows=projection["reserve_rows"],
            appended_rows=[
                {
                    "service_date": "2026-03-22",
                    "route_slot_id": "slot-001",
                    "assigned_driver_id": "DRV-99",
                    "assignment_status": "manual_override",
                    "projected_minutes": 525,
                    "candidate_delta_id": "cand-777",
                }
            ],
        )


def test_materialize_stage04_draft_weekly_schedule_workbook_rejects_row_count_changes() -> None:
    projection = project_stage04_draft_weekly_schedule_workbook(_base_workbook_bytes())

    with pytest.raises(ValueError, match="same row count"):
        materialize_stage04_draft_weekly_schedule_workbook(
            _base_workbook_bytes(),
            rows=projection["rows"][:-1],
            reserve_rows=projection["reserve_rows"],
        )


def test_materialize_stage04_draft_weekly_schedule_workbook_rejects_identity_reordering() -> None:
    projection = project_stage04_draft_weekly_schedule_workbook(_base_workbook_bytes())
    rows = list(reversed([dict(row) for row in projection["rows"]]))

    with pytest.raises(ValueError, match="identity changed"):
        materialize_stage04_draft_weekly_schedule_workbook(
            _base_workbook_bytes(),
            rows=rows,
            reserve_rows=projection["reserve_rows"],
        )


def test_materialize_stage04_draft_weekly_schedule_workbook_rejects_immutable_field_changes() -> None:
    projection = project_stage04_draft_weekly_schedule_workbook(_base_workbook_bytes())
    rows = [dict(row) for row in projection["rows"]]
    rows[0]["projected_minutes"] = 999

    with pytest.raises(ValueError, match="immutable field 'projected_minutes'"):
        materialize_stage04_draft_weekly_schedule_workbook(
            _base_workbook_bytes(),
            rows=rows,
            reserve_rows=projection["reserve_rows"],
        )


def test_draft_workbook_bytes_from_metadata_json_round_trips_json_payload() -> None:
    metadata = {"columns": ["service_date"], "rows": [["2026-03-22"]], "reserve_rows": [], "iteration_deltas": []}

    encoded = draft_workbook_bytes_from_metadata_json(metadata)

    assert json.loads(encoded.decode("utf-8")) == metadata
