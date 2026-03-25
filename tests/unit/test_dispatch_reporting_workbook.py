from __future__ import annotations

import pytest

from onetruth.application.services.dispatch_reporting_workbook import (
    materialize_upd_draft_workbook,
    project_upd_draft_workbook,
)
from tests.helpers.repo_paths import REPO_ROOT

TEMPLATE_PATH = (
    REPO_ROOT
    / "fixtures/workflows/dispatch_reporting/template_pack/Stage03_Threshold_Detection_and_Draft_Packet/Stage03_Threshold_Detection_and_Draft_Packet_upd_draft_Spreadsheet_Template_EMPTY.xlsx"
)


def test_project_empty_upd_draft_template_returns_expected_semantic_state() -> None:
    projection = project_upd_draft_workbook(TEMPLATE_PATH.read_bytes())

    assert projection["workflow_id"] == "dispatch_reporting.v1"
    assert projection["dataset_key"] == "reporting.upd_draft.workbook"
    assert projection["route_actuals"] == []
    assert projection["upd_candidates"] == []
    assert projection["manual_closeout"] == [
        {
            "row_id": "manual-closeout",
            "sick_calls": "",
            "unavailable_drivers": "",
            "working_devices": "",
            "rescues": "",
            "incidents": "",
            "last_driver_clockout": "",
            "dispatcher_comment": "",
            "manager_note": "",
        }
    ]
    assert projection["quality_warnings"] == []
    assert projection["change_log_stage03_upd_draft"] == []
    assert len(projection["lookups03"]) >= 1


def test_materialize_upd_draft_workbook_round_trips_and_preserves_fixture_bytes() -> None:
    base_bytes = TEMPLATE_PATH.read_bytes()
    updated_bytes = materialize_upd_draft_workbook(
        base_bytes,
        {
            "route_actuals": [
                {
                    "row_id": "route-cx100",
                    "service_date": "2026-03-16",
                    "route_id": "CX100",
                    "driver_name": "Brahamvir Singh",
                    "packages_dispatched": 286,
                    "packages_delivered": 286,
                    "planned_start": "11:50",
                    "planned_finish": "18:40",
                    "actual_start": "11:50",
                    "actual_finish": "22:27",
                    "actual_minutes": 637,
                    "returns": 0,
                    "return_reasons": "",
                    "upd_candidate": True,
                }
            ],
            "upd_candidates": [
                {
                    "row_id": "upd-cx100",
                    "service_date": "2026-03-16",
                    "route_id": "CX100",
                    "driver_name": "Brahamvir Singh",
                    "actual_minutes": 637,
                    "selected": True,
                    "reason": ">600 minutes actual time",
                    "manager_note": "Reviewed for follow-up.",
                }
            ],
            "manual_closeout": [
                {
                    "row_id": "manual-closeout",
                    "sick_calls": "None",
                    "unavailable_drivers": "",
                    "working_devices": "38",
                    "rescues": "route-cx100:0",
                    "incidents": "none",
                    "last_driver_clockout": "22:27",
                    "dispatcher_comment": "Route CX100 closed with review note.",
                    "manager_note": "Escalate in morning review.",
                }
            ],
        },
        change_log_entry={
            "row_id": "log-001",
            "change_type": "submit",
            "actor_id": "human:test-user",
            "changed_at": "2026-03-17T00:15:00Z",
            "summary": "Bounded EOD edits submitted.",
        },
    )

    assert updated_bytes != base_bytes
    assert TEMPLATE_PATH.read_bytes() == base_bytes

    round_tripped = project_upd_draft_workbook(updated_bytes)
    assert round_tripped["route_actuals"] == [
        {
            "row_id": "route-cx100",
            "service_date": "2026-03-16",
            "route_id": "CX100",
            "driver_name": "Brahamvir Singh",
            "packages_dispatched": 286,
            "packages_delivered": 286,
            "planned_start": "11:50",
            "planned_finish": "18:40",
            "actual_start": "11:50",
            "actual_finish": "22:27",
            "actual_minutes": 637,
            "returns": 0,
            "return_reasons": "",
            "upd_candidate": True,
        }
    ]
    assert round_tripped["upd_candidates"][0]["selected"] is True
    assert round_tripped["upd_candidates"][0]["manager_note"] == "Reviewed for follow-up."
    assert round_tripped["manual_closeout"][0]["working_devices"] == "38"
    assert round_tripped["manual_closeout"][0]["dispatcher_comment"] == (
        "Route CX100 closed with review note."
    )
    assert round_tripped["change_log_stage03_upd_draft"] == [
        {
            "row_id": "log-001",
            "change_type": "submit",
            "actor_id": "human:test-user",
            "changed_at": "2026-03-17T00:15:00Z",
            "summary": "Bounded EOD edits submitted.",
        }
    ]
    assert round_tripped["quality_warnings"] == []


def test_materialize_upd_draft_workbook_rejects_read_only_table_edits() -> None:
    with pytest.raises(ValueError, match="read-only workbook tables cannot be edited"):
        materialize_upd_draft_workbook(
            TEMPLATE_PATH.read_bytes(),
            {
                "quality_warnings": [
                    {
                        "row_id": "warning-1",
                        "warning_code": "formula_integrity_warning",
                        "severity": "warning",
                        "message": "Should fail.",
                        "source_sheet": "Summary",
                    }
                ]
            },
        )
