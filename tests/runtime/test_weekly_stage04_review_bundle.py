from __future__ import annotations

import csv
import json
import os
from pathlib import Path
import subprocess
import sys
import zipfile

from onetruth.application.services.logistics_weekly_agent_pilot import (
    PILOT_WEEKLY_STAGE04_ACTUAL_OPS_LAB,
    run_logistics_weekly_agent_pilot_suite,
)
from onetruth.infrastructure.db.session import open_sqlite_connection
from onetruth.infrastructure.events.event_store import create_sqlite_substrate
from tests.runtime.helpers.runtime_cli import REPO_ROOT, SRC_ROOT


_EXPECTED_ARCHIVE_ENTRIES = {
    "bundle_manifest.json",
    "README.md",
    "canonical_outputs/planning.candidate_schedule_delta.workbook.json",
    "canonical_outputs/planning.validation_summary.doc.json",
    "canonical_outputs/planning.draft_weekly_schedule.workbook.json",
    "canonical_outputs/planning.draft_weekly_schedule.doc.json",
    "csv/new_agreement_required_rows.csv",
    "csv/selected_route_slot_assignments.csv",
    "notes/on_call_template_usage.md",
}

_CSV_FIELDNAMES = [
    "service_date",
    "route_slot_id",
    "route_id",
    "assigned_driver_id",
    "availability_state",
    "baseline_template_state",
    "planned_driver_day_state",
    "new_agreement_required",
    "new_agreement_trigger_reason",
    "template_state_preservation_fit",
    "iteration_index",
    "phase",
    "projected_minutes",
    "rationale_code",
]

_CANONICAL_OUTPUT_KINDS = (
    "planning.candidate_schedule_delta.workbook",
    "planning.validation_summary.doc",
    "planning.draft_weekly_schedule.workbook",
    "planning.draft_weekly_schedule.doc",
)

_BASELINE_TEMPLATE_STATE_ORDER = (
    "assigned_template",
    "on_call_template",
    "white_template",
    "yellow_template",
    "black_template",
)


def _run_pilot(tmp_path: Path) -> tuple[Path, dict[str, object], dict[str, object]]:
    db_url = f"sqlite:///{tmp_path / 'runtime.db'}"
    output_root = tmp_path / "pilot_outputs"
    artifact_root = tmp_path / "artifacts"

    connection = open_sqlite_connection(db_url)
    try:
        create_sqlite_substrate(connection)
        summary = run_logistics_weekly_agent_pilot_suite(
            connection,
            db_url=db_url,
            pilot_key="review-bundle-tests",
            output_root=output_root,
            artifact_root=artifact_root,
            pilot_ids=[PILOT_WEEKLY_STAGE04_ACTUAL_OPS_LAB],
            openai_mode="mock",
        )
    finally:
        connection.close()

    run_root = Path(str(summary["output_root"]))
    packet_path = run_root / PILOT_WEEKLY_STAGE04_ACTUAL_OPS_LAB / "inspection_packet.json"
    packet = json.loads(packet_path.read_text(encoding="utf-8"))
    return run_root, summary, packet


def _run_export_script(tmp_path: Path, *, run_root: Path) -> tuple[Path, dict[str, object]]:
    output_path = tmp_path / "review_bundle.zip"
    env = os.environ.copy()
    existing_pythonpath = env.get("PYTHONPATH")
    if existing_pythonpath:
        env["PYTHONPATH"] = f"{SRC_ROOT}{os.pathsep}{existing_pythonpath}"
    else:
        env["PYTHONPATH"] = str(SRC_ROOT)

    result = subprocess.run(
        [
            sys.executable,
            "scripts/export_weekly_stage04_review_bundle.py",
            "--run-root",
            str(run_root),
            "--pilot-id",
            PILOT_WEEKLY_STAGE04_ACTUAL_OPS_LAB,
            "--output",
            str(output_path),
            "--json",
        ],
        cwd=REPO_ROOT,
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )
    if result.returncode != 0:
        raise AssertionError(
            f"export script failed ({result.returncode})\nSTDOUT: {result.stdout}\nSTDERR: {result.stderr}"
        )
    return output_path, json.loads(result.stdout)


def _read_zip_json(archive: zipfile.ZipFile, name: str) -> dict[str, object]:
    return json.loads(archive.read(name).decode("utf-8"))


def _read_zip_csv(archive: zipfile.ZipFile, name: str) -> list[dict[str, str]]:
    text = archive.read(name).decode("utf-8")
    return list(csv.DictReader(text.splitlines()))


def _artifact_metadata(
    inspection_packet: dict[str, object],
    artifact_kind: str,
) -> dict[str, object]:
    for artifact in inspection_packet["artifacts"]:
        if artifact["artifact_kind"] == artifact_kind:
            return dict(artifact["metadata_json"])
    raise AssertionError(f"artifact not found: {artifact_kind}")


def _selected_assignment_rows(inspection_packet: dict[str, object]) -> list[dict[str, object]]:
    candidate_delta = _artifact_metadata(
        inspection_packet,
        "planning.candidate_schedule_delta.workbook",
    )
    columns = [str(column) for column in candidate_delta["columns"]]
    rows = [
        dict(zip(columns, row))
        for row in candidate_delta["rows"]
    ]
    normalized = [
        {
            "service_date": str(row.get("service_date") or ""),
            "route_slot_id": str(row.get("route_slot_id") or ""),
            "route_id": str(row.get("route_id") or ""),
            "assigned_driver_id": str(row.get("assigned_driver_id") or ""),
            "availability_state": str(row.get("availability_state") or ""),
            "baseline_template_state": str(row.get("baseline_template_state") or ""),
            "planned_driver_day_state": str(row.get("planned_driver_day_state") or ""),
            "new_agreement_required": bool(row.get("new_agreement_required")),
            "new_agreement_trigger_reason": str(row.get("new_agreement_trigger_reason") or ""),
            "template_state_preservation_fit": row.get("template_state_preservation_fit"),
            "iteration_index": int(row.get("iteration_index") or 0),
            "phase": str(row.get("phase") or ""),
            "projected_minutes": int(row.get("projected_minutes") or 0),
            "rationale_code": str(row.get("rationale_code") or ""),
        }
        for row in rows
    ]
    return sorted(
        normalized,
        key=lambda row: (
            str(row["service_date"]),
            str(row["route_slot_id"]),
            str(row["assigned_driver_id"]),
        ),
    )


def _csv_string_rows(rows: list[dict[str, object]]) -> list[dict[str, str]]:
    return [
        {
            field: "" if row.get(field) is None else str(row.get(field))
            for field in _CSV_FIELDNAMES
        }
        for row in rows
    ]


def _normalized_new_agreement_rows(rows: list[dict[str, object]]) -> list[dict[str, object]]:
    normalized = [
        {
            "service_date": str(row.get("service_date") or ""),
            "route_slot_id": str(row.get("route_slot_id") or ""),
            "route_id": str(row.get("route_id") or ""),
            "assigned_driver_id": str(
                row.get("assigned_driver_id") or row.get("candidate_driver_id") or ""
            ),
            "availability_state": str(row.get("availability_state") or ""),
            "baseline_template_state": str(row.get("baseline_template_state") or ""),
            "planned_driver_day_state": str(row.get("planned_driver_day_state") or ""),
            "new_agreement_required": bool(
                row.get("new_agreement_required") or row.get("new_agreement_trigger_reason")
            ),
            "new_agreement_trigger_reason": str(row.get("new_agreement_trigger_reason") or ""),
            "template_state_preservation_fit": row.get("template_state_preservation_fit"),
            "iteration_index": int(row.get("iteration_index") or 0),
            "phase": str(row.get("phase") or row.get("planning_phase") or ""),
            "projected_minutes": int(row.get("projected_minutes") or 0),
            "rationale_code": str(row.get("rationale_code") or ""),
        }
        for row in rows
    ]
    return sorted(
        normalized,
        key=lambda row: (
            str(row["service_date"]),
            str(row["assigned_driver_id"]),
            str(row["route_slot_id"]),
        ),
    )


def _expected_on_call_note_lines(
    *,
    reserve_rows: list[dict[str, object]],
    reserve_summary: dict[str, object],
    new_agreement_rows: list[dict[str, object]],
) -> list[str]:
    on_call_usage_count = sum(
        1
        for row in reserve_rows
        if str(row.get("baseline_template_state") or "") == "on_call_template"
    )
    white_template_count = sum(
        1
        for row in new_agreement_rows
        if str(row.get("new_agreement_trigger_reason") or "") == "white_template_to_assigned"
    )
    yellow_template_count = sum(
        1
        for row in new_agreement_rows
        if str(row.get("new_agreement_trigger_reason") or "") == "yellow_template_to_assigned"
    )
    white_template_on_call_count = sum(
        1
        for row in new_agreement_rows
        if str(row.get("new_agreement_trigger_reason") or "") == "white_template_to_on_call"
    )
    yellow_template_on_call_count = sum(
        1
        for row in new_agreement_rows
        if str(row.get("new_agreement_trigger_reason") or "") == "yellow_template_to_on_call"
    )
    selected_on_call_total = int(reserve_summary.get("selected_on_call_total") or 0)
    target_on_call_total = int(reserve_summary.get("target_on_call_total") or 0)
    if on_call_usage_count > 0:
        summary_line = (
            "- Summary: The patch filled "
            f"`{selected_on_call_total}` of `{target_on_call_total}` On-Call buffer positions "
            f"and used signed on-call template days `{on_call_usage_count}` time(s) before taking "
            "relief from white/yellow days."
        )
    else:
        summary_line = (
            "- Summary: The patch filled "
            f"`{selected_on_call_total}` of `{target_on_call_total}` On-Call buffer positions "
            "without using signed on-call template days."
        )
    return [
        summary_line,
        f"- On-call buffer positions filled: `{selected_on_call_total}` / `{target_on_call_total}`",
        f"- On-call template day assignments: `{on_call_usage_count}`",
        f"- White-template assigned agreement cases: `{white_template_count}`",
        f"- Yellow-template assigned agreement cases: `{yellow_template_count}`",
        f"- White-template On-Call agreement cases: `{white_template_on_call_count}`",
        f"- Yellow-template On-Call agreement cases: `{yellow_template_on_call_count}`",
    ]


def _baseline_template_counts(selected_rows: list[dict[str, object]]) -> dict[str, int]:
    counts = {state: 0 for state in _BASELINE_TEMPLATE_STATE_ORDER}
    for row in selected_rows:
        state = str(row.get("baseline_template_state") or "")
        if not state:
            continue
        counts[state] = counts.get(state, 0) + 1
    return counts


def test_weekly_stage04_review_bundle_exports_expected_structure_and_metrics(
    tmp_path: Path,
) -> None:
    run_root, _summary, inspection_packet = _run_pilot(tmp_path)
    bundle_path, export_result = _run_export_script(tmp_path, run_root=run_root)

    validation_summary = _artifact_metadata(
        inspection_packet,
        "planning.validation_summary.doc",
    )["summary"]
    candidate_delta = _artifact_metadata(
        inspection_packet,
        "planning.candidate_schedule_delta.workbook",
    )
    coverage_summary = validation_summary["coverage_summary"]
    selected_rows = _selected_assignment_rows(inspection_packet)
    expected_selected_rows = _csv_string_rows(selected_rows)
    reserve_rows = list(candidate_delta.get("reserve_rows") or [])
    reserve_summary = dict(validation_summary.get("reserve_summary") or {})
    excess_capacity_summary = dict(validation_summary.get("excess_capacity_summary") or {})
    new_agreement_rows = list(validation_summary.get("new_agreement_rows") or [])
    expected_new_agreement_rows = _csv_string_rows(
        _normalized_new_agreement_rows(new_agreement_rows)
    )

    availability_counts: dict[str, int] = {}
    for row in selected_rows:
        state = str(row["availability_state"] or "")
        if not state:
            continue
        availability_counts[state] = availability_counts.get(state, 0) + 1
    baseline_template_counts = _baseline_template_counts(selected_rows)

    assert bundle_path.exists()
    assert export_result["status"] == "ok"
    assert export_result["bundle_kind"] == "weekly_stage04_review_bundle"
    assert export_result["pilot_id"] == PILOT_WEEKLY_STAGE04_ACTUAL_OPS_LAB

    with zipfile.ZipFile(bundle_path, "r") as archive:
        names = set(archive.namelist())
        assert names == _EXPECTED_ARCHIVE_ENTRIES

        for artifact_kind in _CANONICAL_OUTPUT_KINDS:
            expected = _artifact_metadata(inspection_packet, artifact_kind)
            actual = _read_zip_json(archive, f"canonical_outputs/{artifact_kind}.json")
            assert actual == expected

        readme = archive.read("README.md").decode("utf-8")
        assert (
            f"- Coverage: `{coverage_summary['assigned_route_slots']} assigned / "
            f"{coverage_summary['uncovered_route_slots']} uncovered`"
        ) in readme
        assert (
            f"- New agreement required count: "
            f"`{validation_summary['new_agreement_required_count']}`"
        ) in readme
        assert f"- Warning count: `{len(validation_summary['warnings'])}`" in readme
        for service_date, count in sorted(validation_summary["new_agreement_by_service_date"].items()):
            assert f"- `{service_date}`: `{count}`" in readme
        for state in _BASELINE_TEMPLATE_STATE_ORDER:
            count = baseline_template_counts.get(state, 0)
            if count <= 0:
                continue
            assert f"- `{state}`: `{count}`" in readme
        for state, count in sorted(availability_counts.items()):
            if count <= 0:
                continue
            assert f"- `{state}`: `{count}`" in readme
        assert (
            "- Excess-capacity baseline shifts: "
            f"`{excess_capacity_summary['selected_excess_capacity_total']}` filled / "
            f"`{excess_capacity_summary['target_excess_capacity_total']}` targeted"
        ) in readme
        for service_date, count in sorted(
            excess_capacity_summary["selected_excess_capacity_by_service_date"].items()
        ):
            assert (
                f"- `{service_date}`: `{count}` filled / "
                f"`{excess_capacity_summary['excess_capacity_target_by_service_date'][service_date]}` targeted"
            ) in readme

        note_text = archive.read("notes/on_call_template_usage.md").decode("utf-8")
        assert "# On-Call Template Usage" in note_text
        for line in _expected_on_call_note_lines(
            reserve_rows=reserve_rows,
            reserve_summary=reserve_summary,
            new_agreement_rows=new_agreement_rows,
        ):
            assert line in note_text
            assert line in readme

        selected_assignment_rows = _read_zip_csv(
            archive,
            "csv/selected_route_slot_assignments.csv",
        )
        assert selected_assignment_rows == expected_selected_rows
        assert len(selected_assignment_rows) == (
            coverage_summary["assigned_route_slots"]
            + excess_capacity_summary["selected_excess_capacity_total"]
        )
        assert list(selected_assignment_rows[0].keys()) == _CSV_FIELDNAMES

        new_agreement_rows = _read_zip_csv(
            archive,
            "csv/new_agreement_required_rows.csv",
        )
        assert new_agreement_rows == expected_new_agreement_rows
        assert len(new_agreement_rows) == validation_summary["new_agreement_required_count"]
        assert all(row["new_agreement_required"] == "True" for row in new_agreement_rows)

        manifest = _read_zip_json(archive, "bundle_manifest.json")
        assert manifest["bundle_kind"] == "weekly_stage04_review_bundle"
        assert manifest["pilot_id"] == PILOT_WEEKLY_STAGE04_ACTUAL_OPS_LAB
        assert manifest["workflow_run_id"] == inspection_packet["workflow_run"]["workflow_run_id"]
        assert manifest["canonical_output_kinds"] == list(_CANONICAL_OUTPUT_KINDS)
        assert manifest["csv_files"] == [
            "csv/new_agreement_required_rows.csv",
            "csv/selected_route_slot_assignments.csv",
        ]
        assert manifest["note_files"] == ["notes/on_call_template_usage.md"]
