from __future__ import annotations

import csv
import json
import os
from pathlib import Path
import subprocess
import sys
import zipfile

from onetruth.infrastructure.db.session import open_sqlite_connection
from onetruth.infrastructure.events.event_store import create_sqlite_substrate
from onetruth.application.services.logistics_weekly_agent_pilot import (
    PILOT_WEEKLY_STAGE04_ACTUAL_OPS_LAB,
    run_logistics_weekly_agent_pilot_suite,
)
from tests.runtime.helpers.runtime_cli import REPO_ROOT, SRC_ROOT


_EXPECTED_ARCHIVE_ENTRIES = {
    "bundle_manifest.json",
    "README.md",
    "canonical_outputs/planning.input_bundle.doc.json",
    "canonical_outputs/planning.candidate_schedule_delta.workbook.json",
    "canonical_outputs/planning.validation_summary.doc.json",
    "canonical_outputs/planning.draft_weekly_schedule.workbook.json",
    "canonical_outputs/planning.draft_weekly_schedule.doc.json",
    "pilot_outputs/inspection_packet.json",
    "pilot_outputs/inspection_packet.md",
    "pilot_outputs/pilot_summary.json",
    "pilot_outputs/pilot_summary.md",
    "pilot_outputs/workflow_lab_run_report.json",
    "pilot_outputs/workflow_lab_review_packet.md",
    "analysis/analyst_report.md",
    "analysis/service_date_summary.csv",
    "analysis/assignment_details.csv",
    "analysis/availability_state_summary.csv",
    "analysis/request_day_assignments.csv",
    "comparison/manager_schedule_comparison_template.csv",
    "comparison/README.md",
}


def _run_pilot(tmp_path: Path) -> tuple[Path, Path, dict[str, object], dict[str, object]]:
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
    return run_root, packet_path, summary, packet


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


def test_weekly_stage04_review_bundle_exports_expected_structure_and_metrics(
    tmp_path: Path,
) -> None:
    run_root, packet_path, _summary, inspection_packet = _run_pilot(tmp_path)
    bundle_path, export_result = _run_export_script(tmp_path, run_root=run_root)

    assert bundle_path.exists()
    assert export_result["status"] == "ok"
    assert export_result["bundle_kind"] == "weekly_stage04_review_bundle"
    assert export_result["pilot_id"] == PILOT_WEEKLY_STAGE04_ACTUAL_OPS_LAB

    with zipfile.ZipFile(bundle_path, "r") as archive:
        names = set(archive.namelist())
        assert _EXPECTED_ARCHIVE_ENTRIES.issubset(names)

        for artifact_kind in (
            "planning.input_bundle.doc",
            "planning.candidate_schedule_delta.workbook",
            "planning.validation_summary.doc",
            "planning.draft_weekly_schedule.workbook",
            "planning.draft_weekly_schedule.doc",
        ):
            expected = next(
                artifact["metadata_json"]
                for artifact in inspection_packet["artifacts"]
                if artifact["artifact_kind"] == artifact_kind
            )
            actual = _read_zip_json(archive, f"canonical_outputs/{artifact_kind}.json")
            assert actual == expected

        analyst_report = archive.read("analysis/analyst_report.md").decode("utf-8")
        assert "139 assigned / 0 uncovered" in analyst_report
        assert "Assigned route slots: `139`" in analyst_report
        assert "Uncovered route slots: `0`" in analyst_report
        assert "Manager ground-truth comparison is pending" in analyst_report

        service_date_rows = _read_zip_csv(archive, "analysis/service_date_summary.csv")
        assert service_date_rows == [
            {
                "service_date": "2026-03-22",
                "planned_route_count": "18",
                "assigned_route_count": "18",
                "assigned_driver_count": "18",
            },
            {
                "service_date": "2026-03-23",
                "planned_route_count": "23",
                "assigned_route_count": "23",
                "assigned_driver_count": "23",
            },
            {
                "service_date": "2026-03-24",
                "planned_route_count": "20",
                "assigned_route_count": "20",
                "assigned_driver_count": "20",
            },
            {
                "service_date": "2026-03-25",
                "planned_route_count": "20",
                "assigned_route_count": "20",
                "assigned_driver_count": "20",
            },
            {
                "service_date": "2026-03-26",
                "planned_route_count": "20",
                "assigned_route_count": "20",
                "assigned_driver_count": "20",
            },
            {
                "service_date": "2026-03-27",
                "planned_route_count": "20",
                "assigned_route_count": "20",
                "assigned_driver_count": "20",
            },
            {
                "service_date": "2026-03-28",
                "planned_route_count": "18",
                "assigned_route_count": "18",
                "assigned_driver_count": "18",
            },
        ]

        availability_rows = _read_zip_csv(archive, "analysis/availability_state_summary.csv")
        assert availability_rows == [
            {"availability_state": "PREFERRED", "assignment_count": "121"},
            {"availability_state": "AVAILABLE", "assignment_count": "17"},
            {"availability_state": "AVOID_IF_POSSIBLE", "assignment_count": "1"},
            {"availability_state": "ON_CALL_ONLY", "assignment_count": "0"},
            {"availability_state": "CANNOT", "assignment_count": "0"},
        ]

        request_rows = _read_zip_csv(archive, "analysis/request_day_assignments.csv")
        assert request_rows == []

        assignment_rows = _read_zip_csv(archive, "analysis/assignment_details.csv")
        assert len(assignment_rows) == 139
        assert assignment_rows[0]["request_day_flag"] == "no"

        comparison_readme = archive.read("comparison/README.md").decode("utf-8")
        assert "not bundled yet" in comparison_readme
        comparison_rows = _read_zip_csv(archive, "comparison/manager_schedule_comparison_template.csv")
        assert len(comparison_rows) == 139
        assert comparison_rows[0]["manager_assigned_driver_id"] == ""

        manifest = _read_zip_json(archive, "bundle_manifest.json")
        assert manifest["bundle_kind"] == "weekly_stage04_review_bundle"
        assert manifest["pilot_id"] == PILOT_WEEKLY_STAGE04_ACTUAL_OPS_LAB
        assert manifest["workflow_run_id"] == inspection_packet["workflow_run"]["workflow_run_id"]

    assert packet_path.exists()
