from __future__ import annotations

from copy import deepcopy
from pathlib import Path

from tests.runtime.helpers.runtime_api import RuntimeApiClient


EXPECTED_SOURCE_DATASET_KEYS = [
    "reporting.eos_raw.workbook",
    "reporting.actuals_normalized.workbook",
    "reporting.upd_draft.workbook",
]

EXPECTED_SOURCE_REFS = [
    "docs/workflows/dispatch_reporting/v1/examples/eos_route_rows_2026_03_16_qdci_partial_example.yaml",
    "docs/workflows/dispatch_reporting/v1/examples/normalized_actuals_2026_03_16_qdci_partial_example.yaml",
    "docs/workflows/dispatch_reporting/v1/examples/upd_candidate_2026_03_16_qdci_partial_example.yaml",
]

EXPECTED_VALIDATION_WARNINGS = [
    "This server-owned demo query is built from an intentionally partial 2026-03-16 dispatch-reporting example family.",
    "Workbook summary formulas were broken in the source material, so row-level actuals remain the primary truth for this projection.",
    "Manual closeout inputs remain local-only in v0; no submit/materialize contract exists yet.",
]


def _client(tmp_path: Path) -> RuntimeApiClient:
    return RuntimeApiClient(
        db_url=str(tmp_path / "demo_eod_workpage.db"),
        tenant_id="tenant-a",
        domain_id="domain-x",
        actor_id="human:ops-manager-2",
        actor_type="human",
        actor_roles=["operations_manager", "dispatch_supervisor", "schedule_planner"],
    )


def test_eod_demo_workpage_contract_returns_server_owned_wrapper(tmp_path: Path) -> None:
    client = _client(tmp_path)

    response = client.get("/api/v1/workpages/demo/eod-v0")
    assert response.status_code == 200

    payload = response.payload
    assert payload["status"] == "ok"
    assert payload["command"] == "api.workpages.demo"

    workpage = payload["workpage"]
    assert workpage["workpage_id"] == "eod-v0"
    assert workpage["version"] == 2
    assert workpage["title"] == "End-of-day report"
    assert workpage["mode"] == "example"
    assert workpage["workflow_id"] == "dispatch_reporting.v1"
    assert workpage["dataset_key"] == "reporting.upd_draft.workbook"
    assert workpage["source_artifact_version_id"] is None

    source = payload["source"]
    assert source["mode"] == "demo"
    assert source["primary_dataset_key"] == "reporting.upd_draft.workbook"
    assert source["source_dataset_keys"] == EXPECTED_SOURCE_DATASET_KEYS
    assert source["source_artifact_version_id"] is None
    assert source["source_refs"] == EXPECTED_SOURCE_REFS

    freshness = payload["freshness"]
    assert freshness["source_kind"] == "repo_example_bundle"
    assert freshness["source_version"] == "dispatch_reporting_2026_03_16_qdci_dvc4_partial_v1"
    assert freshness["generated_at"]

    sections = workpage["sections"]
    assert [section["kind"] for section in sections] == [
        "summary_cards",
        "note_panel",
        "table",
        "form",
        "checklist",
        "history_stub",
    ]
    assert [section["table_id"] for section in sections if section["kind"] == "table"] == [
        "route_actuals"
    ]
    assert [section["checklist_id"] for section in sections if section["kind"] == "checklist"] == [
        "upd_candidates"
    ]

    summary = workpage["summary"]
    assert summary == {
        "service_date": "2026-03-16",
        "station_code": "DVC4",
        "dsp_name": "QDCI",
        "total_routes_actual": 3,
        "packages_dispatched": 786,
        "actual_dispatched": 786,
        "packages_delivered": 783,
        "packages_returned": 3,
        "delivered_pct": 99.62,
        "return_pct": 0.38,
        "average_route_time": "9:47:00",
        "formula_integrity_warning": True,
        "warning_note": (
            "This backend demo query is built from an intentionally partial 2026-03-16 "
            "QDCI / DVC4 reporting example family. Row-level actuals remain the primary truth "
            "because the source workbook summary tabs contained broken formulas."
        ),
    }

    summary_cards_section = next(
        section for section in sections if section["kind"] == "summary_cards"
    )
    assert summary_cards_section["cards"] == [
        {"key": "total_routes", "label": "Total routes actual", "value": 3},
        {"key": "packages_dispatched", "label": "Packages dispatched", "value": 786},
        {"key": "packages_delivered", "label": "Packages delivered", "value": 783},
        {"key": "packages_returned", "label": "Packages returned", "value": 3},
        {"key": "delivered_pct", "label": "Delivered %", "value": "99.62%"},
        {"key": "average_route_time", "label": "Average route time", "value": "9:47:00"},
    ]

    note_section = next(section for section in sections if section["kind"] == "note_panel")
    assert note_section["title"] == "Formula-integrity warning"
    assert note_section["body"] == (
        "This backend demo query uses intentionally partial repo examples. Source workbook "
        "summary tabs showed formula failures, so row-level actuals remain the primary truth "
        "and v0 surfaces a warning instead of reproducing broken formulas."
    )

    route_actuals_section = next(
        section for section in sections if section.get("table_id") == "route_actuals"
    )
    assert route_actuals_section["rows"] == [
        {
            "route_id": "CX100",
            "driver_name": "Brahamvir Singh",
            "packages_dispatched": 286,
            "packages_delivered": 286,
            "planned_window": "11:50 - 18:40",
            "actual_window": "11:50 - 22:27",
            "actual_minutes": 637,
            "returns": 0,
            "return_reasons": "",
            "upd_candidate": True,
        },
        {
            "route_id": "CX95",
            "driver_name": "Tarandeep Singh",
            "packages_dispatched": 292,
            "packages_delivered": 290,
            "planned_window": "11:50 - 18:20",
            "actual_window": "11:50 - 21:37",
            "actual_minutes": 587,
            "returns": 2,
            "return_reasons": "BC,FDD",
            "upd_candidate": False,
        },
        {
            "route_id": "CX99",
            "driver_name": "Yong-Kyoon Kim",
            "packages_dispatched": 208,
            "packages_delivered": 207,
            "planned_window": "11:55 - 18:30",
            "actual_window": "11:55 - 20:52",
            "actual_minutes": 537,
            "returns": 1,
            "return_reasons": "NSL",
            "upd_candidate": False,
        },
    ]

    form_section = next(section for section in sections if section["kind"] == "form")
    field_map = {field["key"]: field for field in form_section["fields"]}
    assert field_map["sick_calls"]["options"] == [
        "Brahamvir Singh",
        "Tarandeep Singh",
        "Yong-Kyoon Kim",
    ]
    assert field_map["unavailable_drivers"]["options"] == [
        "Brahamvir Singh",
        "Tarandeep Singh",
        "Yong-Kyoon Kim",
    ]
    assert field_map["last_driver_clockout"]["value"] == "22:27"

    checklist_section = next(section for section in sections if section["kind"] == "checklist")
    assert checklist_section["items"] == [
        {
            "item_id": "upd-candidate-cx100",
            "title": "Brahamvir Singh · CX100",
            "detail": ">600 minutes actual time",
            "selected": False,
            "note": "",
            "tags": ["637 minutes"],
        },
        {
            "item_id": "upd-candidate-cx95",
            "title": "Tarandeep Singh · CX95",
            "detail": "Below 600 minutes",
            "selected": False,
            "note": "",
            "tags": ["587 minutes"],
        },
    ]

    validation = workpage["validation"]
    assert validation["status"] == "informational"
    assert validation["warnings"] == EXPECTED_VALIDATION_WARNINGS


def test_eod_demo_workpage_reads_are_stable_except_for_generated_at(tmp_path: Path) -> None:
    client = _client(tmp_path)

    first = client.get("/api/v1/workpages/demo/eod-v0")
    second = client.get("/api/v1/workpages/demo/eod-v0")

    assert first.status_code == 200
    assert second.status_code == 200
    assert _without_generated_at(first.payload) == _without_generated_at(second.payload)


def _without_generated_at(payload: dict[str, object]) -> dict[str, object]:
    copied = deepcopy(payload)
    freshness = copied.get("freshness")
    assert isinstance(freshness, dict)
    freshness.pop("generated_at", None)
    return copied
