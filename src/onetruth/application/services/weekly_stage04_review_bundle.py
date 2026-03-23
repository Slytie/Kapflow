from __future__ import annotations

import csv
import io
import json
from pathlib import Path
from typing import Any, Iterable
import zipfile

import yaml

from onetruth.application.services.logistics_weekly_agent_pilot import PILOT_DEFINITIONS

_CANONICAL_OUTPUT_KINDS: tuple[str, ...] = (
    "planning.input_bundle.doc",
    "planning.candidate_schedule_delta.workbook",
    "planning.validation_summary.doc",
    "planning.draft_weekly_schedule.workbook",
    "planning.draft_weekly_schedule.doc",
)

_REQUIRED_PILOT_OUTPUT_FILES: tuple[str, ...] = (
    "inspection_packet.json",
    "inspection_packet.md",
    "workflow_lab_run_report.json",
    "workflow_lab_review_packet.md",
)

_AVAILABILITY_STATE_ORDER: tuple[str, ...] = (
    "PREFERRED",
    "AVAILABLE",
    "AVOID_IF_POSSIBLE",
    "ON_CALL_ONLY",
    "CANNOT",
)


def export_weekly_stage04_review_bundle(
    *,
    run_root: Path,
    pilot_id: str,
    output_path: Path,
) -> dict[str, Any]:
    resolved_run_root = run_root.expanduser().resolve()
    resolved_output_path = output_path.expanduser().resolve()
    resolved_output_path.parent.mkdir(parents=True, exist_ok=True)

    summary_path = resolved_run_root / "pilot_summary.json"
    summary_markdown_path = resolved_run_root / "pilot_summary.md"
    if not summary_path.exists():
        raise ValueError(f"pilot summary not found: {summary_path}")
    if not summary_markdown_path.exists():
        raise ValueError(f"pilot summary markdown not found: {summary_markdown_path}")

    summary = _load_json(summary_path)
    run_entry = _pilot_run_entry(summary, pilot_id=pilot_id)

    pilot_dir = resolved_run_root / pilot_id
    if not pilot_dir.exists():
        raise ValueError(f"pilot output directory not found: {pilot_dir}")

    inspection_path = pilot_dir / "inspection_packet.json"
    inspection_markdown_path = pilot_dir / "inspection_packet.md"
    workflow_lab_report_path = pilot_dir / "workflow_lab_run_report.json"
    workflow_lab_review_path = pilot_dir / "workflow_lab_review_packet.md"
    for path in (
        inspection_path,
        inspection_markdown_path,
        workflow_lab_report_path,
        workflow_lab_review_path,
    ):
        if not path.exists():
            raise ValueError(f"required pilot output not found: {path}")

    inspection_packet = _load_json(inspection_path)
    canonical_outputs = _canonical_output_payloads(inspection_packet)
    analysis = _build_analysis_payload(inspection_packet)
    assumptions = _build_assumptions(pilot_id=pilot_id, inspection_packet=inspection_packet)

    bundle_manifest = {
        "bundle_kind": "weekly_stage04_review_bundle",
        "manifest_version": 1,
        "pilot_id": pilot_id,
        "pilot_key": str(inspection_packet.get("pilot_key") or summary.get("pilot_key") or ""),
        "openai_mode": str(
            inspection_packet.get("openai_mode") or summary.get("openai_mode") or ""
        ),
        "workflow_run_id": str(
            ((inspection_packet.get("workflow_run") or {}).get("workflow_run_id"))
            or run_entry.get("workflow_run_id")
            or ""
        ),
        "generated_at": str(inspection_packet.get("generated_at") or ""),
        "canonical_output_kinds": list(_CANONICAL_OUTPUT_KINDS),
        "analysis_files": [
            "analysis/analyst_report.md",
            "analysis/service_date_summary.csv",
            "analysis/assignment_details.csv",
            "analysis/availability_state_summary.csv",
            "analysis/request_day_assignments.csv",
        ],
        "comparison_mode": "ground_truth_pending",
        "comparison_files": [
            "comparison/manager_schedule_comparison_template.csv",
            "comparison/README.md",
        ],
    }

    archive_entries: dict[str, bytes] = {
        "bundle_manifest.json": _json_bytes(bundle_manifest),
        "README.md": _text_bytes(
            _build_bundle_readme(
                bundle_manifest=bundle_manifest,
                coverage_summary=analysis["coverage_summary"],
            )
        ),
        "pilot_outputs/pilot_summary.json": summary_path.read_bytes(),
        "pilot_outputs/pilot_summary.md": summary_markdown_path.read_bytes(),
        "pilot_outputs/inspection_packet.json": inspection_path.read_bytes(),
        "pilot_outputs/inspection_packet.md": inspection_markdown_path.read_bytes(),
        "pilot_outputs/workflow_lab_run_report.json": workflow_lab_report_path.read_bytes(),
        "pilot_outputs/workflow_lab_review_packet.md": workflow_lab_review_path.read_bytes(),
        "analysis/analyst_report.md": _text_bytes(
            _build_analyst_report(
                bundle_manifest=bundle_manifest,
                analysis=analysis,
                assumptions=assumptions,
            )
        ),
        "analysis/service_date_summary.csv": _csv_bytes(
            [
                {
                    "service_date": service_date,
                    "planned_route_count": analysis["route_count_by_service_date"].get(
                        service_date, 0
                    ),
                    "assigned_route_count": analysis["assigned_route_count_by_service_date"].get(
                        service_date, 0
                    ),
                    "assigned_driver_count": analysis["assigned_driver_count_by_service_date"].get(
                        service_date, 0
                    ),
                }
                for service_date in analysis["service_dates"]
            ],
            fieldnames=[
                "service_date",
                "planned_route_count",
                "assigned_route_count",
                "assigned_driver_count",
            ],
        ),
        "analysis/assignment_details.csv": _csv_bytes(
            analysis["assignment_details"],
            fieldnames=[
                "service_date",
                "route_slot_id",
                "assigned_driver_id",
                "driver_name",
                "availability_state",
                "request_day_flag",
                "request_day_reason",
                "projected_minutes",
                "iteration_index",
                "delta_kind",
                "previous_week_stability",
            ],
        ),
        "analysis/availability_state_summary.csv": _csv_bytes(
            [
                {
                    "availability_state": state,
                    "assignment_count": analysis["assignment_count_by_availability_state"][state],
                }
                for state in analysis["availability_state_order"]
            ],
            fieldnames=["availability_state", "assignment_count"],
        ),
        "analysis/request_day_assignments.csv": _csv_bytes(
            analysis["request_day_assignments"],
            fieldnames=[
                "service_date",
                "route_slot_id",
                "assigned_driver_id",
                "driver_name",
                "availability_state",
                "request_day_reason",
                "notes",
            ],
        ),
        "comparison/manager_schedule_comparison_template.csv": _csv_bytes(
            [
                {
                    "service_date": row["service_date"],
                    "route_slot_id": row["route_slot_id"],
                    "model_assigned_driver_id": row["assigned_driver_id"],
                    "model_driver_name": row["driver_name"],
                    "manager_assigned_driver_id": "",
                    "manager_driver_name": "",
                    "comparison_status": "",
                    "notes": "",
                }
                for row in analysis["assignment_details"]
            ],
            fieldnames=[
                "service_date",
                "route_slot_id",
                "model_assigned_driver_id",
                "model_driver_name",
                "manager_assigned_driver_id",
                "manager_driver_name",
                "comparison_status",
                "notes",
            ],
        ),
        "comparison/README.md": _text_bytes(_comparison_readme_text()),
    }

    for artifact_kind, payload in canonical_outputs.items():
        archive_entries[
            f"canonical_outputs/{artifact_kind}.json"
        ] = _json_bytes(payload)

    with zipfile.ZipFile(resolved_output_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for archive_name, content in sorted(archive_entries.items()):
            archive.writestr(archive_name, content)

    return {
        "status": "ok",
        "bundle_kind": "weekly_stage04_review_bundle",
        "pilot_id": pilot_id,
        "pilot_key": bundle_manifest["pilot_key"],
        "openai_mode": bundle_manifest["openai_mode"],
        "workflow_run_id": bundle_manifest["workflow_run_id"],
        "run_root": str(resolved_run_root),
        "output_path": str(resolved_output_path),
        "bundle_manifest_path": "bundle_manifest.json",
    }


def _pilot_run_entry(summary: dict[str, Any], *, pilot_id: str) -> dict[str, Any]:
    for item in summary.get("pilot_runs") or []:
        if str(item.get("pilot_id") or "") == pilot_id:
            return dict(item)
    raise ValueError(f"pilot_id not found in pilot summary: {pilot_id}")


def _canonical_output_payloads(inspection_packet: dict[str, Any]) -> dict[str, dict[str, Any]]:
    artifacts = list(inspection_packet.get("artifacts") or [])
    payloads: dict[str, dict[str, Any]] = {}
    for artifact_kind in _CANONICAL_OUTPUT_KINDS:
        match = None
        for artifact in artifacts:
            if str(artifact.get("artifact_kind") or "") == artifact_kind:
                match = artifact
        if match is None:
            raise ValueError(f"required Stage04 output artifact not found: {artifact_kind}")
        metadata = match.get("metadata_json")
        if not isinstance(metadata, dict):
            raise ValueError(f"Stage04 output metadata is not an object: {artifact_kind}")
        payloads[artifact_kind] = dict(metadata)
    return payloads


def _build_analysis_payload(inspection_packet: dict[str, Any]) -> dict[str, Any]:
    artifacts = list(inspection_packet.get("artifacts") or [])
    input_bundle = _artifact_metadata(artifacts, "planning.input_bundle.doc")
    draft_workbook = _artifact_metadata(artifacts, "planning.draft_weekly_schedule.workbook")
    approved_availability = _artifact_metadata(artifacts, "planning.approved_availability.workbook")
    validation_summary = _artifact_metadata(artifacts, "planning.validation_summary.doc")

    bundle = _as_dict(input_bundle.get("bundle"), field_name="planning.input_bundle.doc.bundle")
    validation = _as_dict(
        validation_summary.get("summary"),
        field_name="planning.validation_summary.doc.summary",
    )

    service_dates = [
        str(item.get("service_date") or "")
        for item in list(bundle.get("demand_by_service_date") or [])
        if str(item.get("service_date") or "").strip()
    ]
    route_count_by_service_date = {
        str(item.get("service_date") or ""): int(item.get("planned_route_count") or 0)
        for item in list(bundle.get("demand_by_service_date") or [])
        if str(item.get("service_date") or "").strip()
    }

    draft_columns = [str(column) for column in list(draft_workbook.get("columns") or [])]
    draft_rows = [
        dict(zip(draft_columns, row))
        for row in list(draft_workbook.get("rows") or [])
    ]
    final_assignments = [
        row
        for row in draft_rows
        if str(row.get("assignment_status") or "").strip() == "pass"
    ]

    availability_columns = [
        str(column) for column in list(approved_availability.get("columns") or [])
    ]
    availability_rows = [
        dict(zip(availability_columns, row))
        for row in list(approved_availability.get("rows") or [])
    ]
    availability_lookup = {
        (str(row.get("driver_id") or ""), str(row.get("service_date") or "")): row
        for row in availability_rows
    }

    assignment_count_by_service_date: dict[str, int] = {service_date: 0 for service_date in service_dates}
    assigned_driver_sets: dict[str, set[str]] = {service_date: set() for service_date in service_dates}
    assignment_count_by_availability_state = {
        state: 0 for state in _AVAILABILITY_STATE_ORDER
    }
    assignment_details: list[dict[str, Any]] = []
    request_day_assignments: list[dict[str, Any]] = []

    for row in final_assignments:
        service_date = str(row.get("service_date") or "")
        driver_id = str(row.get("assigned_driver_id") or "")
        availability = availability_lookup.get((driver_id, service_date), {})
        availability_state = str(availability.get("availability_state") or "")
        if availability_state and availability_state not in assignment_count_by_availability_state:
            assignment_count_by_availability_state[availability_state] = 0
        if availability_state:
            assignment_count_by_availability_state[availability_state] += 1

        if service_date not in assignment_count_by_service_date:
            assignment_count_by_service_date[service_date] = 0
        assignment_count_by_service_date[service_date] += 1
        assigned_driver_sets.setdefault(service_date, set()).add(driver_id)

        request_day_reason = _request_day_reason(
            availability_state=availability_state,
            notes=str(availability.get("notes") or ""),
        )
        assignment_detail = {
            "service_date": service_date,
            "route_slot_id": str(row.get("route_slot_id") or ""),
            "assigned_driver_id": driver_id,
            "driver_name": str(availability.get("driver_name") or ""),
            "availability_state": availability_state,
            "request_day_flag": "yes" if request_day_reason else "no",
            "request_day_reason": request_day_reason,
            "projected_minutes": int(row.get("projected_minutes") or 0),
            "iteration_index": int(row.get("iteration_index") or 0),
            "delta_kind": str(row.get("delta_kind") or ""),
            "previous_week_stability": row.get("previous_week_stability"),
        }
        assignment_details.append(assignment_detail)

        if request_day_reason:
            request_day_assignments.append(
                {
                    "service_date": service_date,
                    "route_slot_id": str(row.get("route_slot_id") or ""),
                    "assigned_driver_id": driver_id,
                    "driver_name": str(availability.get("driver_name") or ""),
                    "availability_state": availability_state,
                    "request_day_reason": request_day_reason,
                    "notes": str(availability.get("notes") or ""),
                }
            )

    assigned_driver_count_by_service_date = {
        service_date: len(assigned_driver_sets.get(service_date, set()))
        for service_date in service_dates
    }

    return {
        "coverage_summary": _as_dict(
            validation.get("coverage_summary"),
            field_name="planning.validation_summary.doc.summary.coverage_summary",
        ),
        "service_dates": service_dates,
        "route_count_by_service_date": route_count_by_service_date,
        "assigned_route_count_by_service_date": assignment_count_by_service_date,
        "assigned_driver_count_by_service_date": assigned_driver_count_by_service_date,
        "assignment_count_by_availability_state": assignment_count_by_availability_state,
        "availability_state_order": list(_availability_state_order(approved_availability)),
        "assignment_details": assignment_details,
        "request_day_assignments": request_day_assignments,
        "warnings": [str(item) for item in list(validation.get("warnings") or [])],
        "tradeoffs": [str(item) for item in list(validation.get("tradeoffs") or [])],
    }


def _availability_state_order(approved_availability: dict[str, Any]) -> tuple[str, ...]:
    discovered = {
        str(row[4]).strip()
        for row in list(approved_availability.get("rows") or [])
        if isinstance(row, list) and len(row) > 4 and str(row[4]).strip()
    }
    ordered = list(_AVAILABILITY_STATE_ORDER)
    for state in sorted(discovered):
        if state not in ordered:
            ordered.append(state)
    return tuple(ordered)


def _request_day_reason(*, availability_state: str, notes: str) -> str:
    normalized_notes = notes.lower()
    if availability_state == "CANNOT":
        return "availability_state=CANNOT"
    if "request" in normalized_notes:
        return "notes_contains_request"
    if "time-off" in normalized_notes:
        return "notes_contains_time-off"
    return ""


def _build_assumptions(
    *,
    pilot_id: str,
    inspection_packet: dict[str, Any],
) -> list[str]:
    notes: list[str] = []
    source_material_path = getattr(PILOT_DEFINITIONS.get(pilot_id), "source_material_path", None)
    if source_material_path is not None and source_material_path.exists():
        loaded = yaml.safe_load(source_material_path.read_text(encoding="utf-8"))
        if isinstance(loaded, dict):
            notes.extend(str(item) for item in list(loaded.get("notes") or []) if str(item).strip())

    for artifact_kind in (
        "planning.route_slot_requirements.workbook",
        "planning.driver_capabilities.workbook",
        "planning.approved_availability.workbook",
        "planning.actual_hours_snapshot.workbook",
    ):
        metadata = _artifact_metadata(list(inspection_packet.get("artifacts") or []), artifact_kind)
        notes.extend(str(item) for item in list(metadata.get("planner_notes") or []) if str(item).strip())
    return list(_dedupe_preserving_order(notes))


def _artifact_metadata(artifacts: list[dict[str, Any]], artifact_kind: str) -> dict[str, Any]:
    match = None
    for artifact in artifacts:
        if str(artifact.get("artifact_kind") or "") == artifact_kind:
            match = artifact
    if match is None:
        raise ValueError(f"artifact not found in inspection packet: {artifact_kind}")
    metadata = match.get("metadata_json")
    if not isinstance(metadata, dict):
        raise ValueError(f"artifact metadata must be an object: {artifact_kind}")
    return dict(metadata)


def _build_bundle_readme(
    *,
    bundle_manifest: dict[str, Any],
    coverage_summary: dict[str, Any],
) -> str:
    return "\n".join(
        [
            "# Weekly Stage04 Review Bundle",
            "",
            f"- Pilot ID: `{bundle_manifest['pilot_id']}`",
            f"- Pilot key: `{bundle_manifest['pilot_key']}`",
            f"- OpenAI mode: `{bundle_manifest['openai_mode']}`",
            f"- Workflow run ID: `{bundle_manifest['workflow_run_id']}`",
            f"- Coverage: `{coverage_summary.get('assigned_route_slots', 0)} assigned / {coverage_summary.get('uncovered_route_slots', 0)} uncovered`",
            "",
            "## Included",
            "",
            "- Canonical Stage04 outputs serialized from the inspection packet metadata",
            "- Pilot inspection, summary, and Workflow Lab review artifacts",
            "- CSV extracts and a human-readable analyst report for SME review",
            "- A comparison template for future ops-manager ground-truth review",
            "",
            "## Comparison posture",
            "",
            "The manager ground-truth weekly schedule is not bundled yet. Use the comparison template after that file is supplied.",
            "",
        ]
    )


def _build_analyst_report(
    *,
    bundle_manifest: dict[str, Any],
    analysis: dict[str, Any],
    assumptions: list[str],
) -> str:
    lines = [
        "# Weekly Stage04 Analyst Report",
        "",
        "## Run",
        "",
        f"- Pilot ID: `{bundle_manifest['pilot_id']}`",
        f"- Pilot key: `{bundle_manifest['pilot_key']}`",
        f"- OpenAI mode: `{bundle_manifest['openai_mode']}`",
        f"- Workflow run ID: `{bundle_manifest['workflow_run_id']}`",
        "",
        "## Coverage",
        "",
        (
            f"- Coverage headline: {analysis['coverage_summary'].get('assigned_route_slots', 0)} assigned / "
            f"{analysis['coverage_summary'].get('uncovered_route_slots', 0)} uncovered"
        ),
        f"- Assigned route slots: `{analysis['coverage_summary'].get('assigned_route_slots', 0)}`",
        f"- Uncovered route slots: `{analysis['coverage_summary'].get('uncovered_route_slots', 0)}`",
        f"- Iterations: `{analysis['coverage_summary'].get('iteration_count', 0)}`",
        "",
        "## Service Date Summary",
        "",
    ]
    for service_date in analysis["service_dates"]:
        lines.append(
            (
                f"- `{service_date}`: routes=`{analysis['route_count_by_service_date'].get(service_date, 0)}`, "
                f"assigned routes=`{analysis['assigned_route_count_by_service_date'].get(service_date, 0)}`, "
                f"assigned drivers=`{analysis['assigned_driver_count_by_service_date'].get(service_date, 0)}`"
            )
        )

    lines.extend(
        [
            "",
            "## Availability State Usage",
            "",
        ]
    )
    for state in analysis["availability_state_order"]:
        lines.append(
            f"- `{state}`: `{analysis['assignment_count_by_availability_state'].get(state, 0)}` assignments"
        )

    lines.extend(
        [
            "",
            "## Request-Day Assignments",
            "",
            (
                f"- Count: `{len(analysis['request_day_assignments'])}`"
                if analysis["request_day_assignments"]
                else "- Count: `0`"
            ),
        ]
    )
    for row in analysis["request_day_assignments"][:10]:
        lines.append(
            (
                f"- `{row['service_date']}` `{row['route_slot_id']}` -> `{row['assigned_driver_id']}` "
                f"({row['availability_state']}; {row['request_day_reason']})"
            )
        )

    lines.extend(
        [
            "",
            "## Warnings",
            "",
        ]
    )
    warning_rows = analysis["warnings"][:10]
    if warning_rows:
        lines.extend(f"- {warning}" for warning in warning_rows)
    else:
        lines.append("- None")

    lines.extend(
        [
            "",
            "## Tradeoffs",
            "",
        ]
    )
    tradeoff_rows = analysis["tradeoffs"][:10]
    if tradeoff_rows:
        lines.extend(f"- {tradeoff}" for tradeoff in tradeoff_rows)
    else:
        lines.append("- None")

    lines.extend(
        [
            "",
            "## Assumptions",
            "",
        ]
    )
    if assumptions:
        lines.extend(f"- {item}" for item in assumptions)
    else:
        lines.append("- No additional pilot assumptions were found.")

    lines.extend(
        [
            "",
            "## Comparison Readiness",
            "",
            "- Manager ground-truth comparison is pending until the ops-manager weekly schedule file is supplied.",
            "- `comparison/manager_schedule_comparison_template.csv` is prefilled with model assignments so manager values can be added later.",
            "",
        ]
    )
    return "\n".join(lines)


def _comparison_readme_text() -> str:
    return "\n".join(
        [
            "# Manager Schedule Comparison",
            "",
            "The ops-manager ground-truth weekly schedule is not bundled yet.",
            "",
            "Use `manager_schedule_comparison_template.csv` after the manager file is available:",
            "- fill `manager_assigned_driver_id` and `manager_driver_name`",
            "- set `comparison_status` to values such as `match`, `mismatch`, or `missing_ground_truth`",
            "- capture reviewer notes in `notes`",
            "",
        ]
    )


def _json_bytes(payload: dict[str, Any]) -> bytes:
    return json.dumps(payload, indent=2, sort_keys=True).encode("utf-8")


def _text_bytes(text: str) -> bytes:
    return text.encode("utf-8")


def _csv_bytes(rows: list[dict[str, Any]], *, fieldnames: list[str]) -> bytes:
    buffer = io.StringIO()
    writer = csv.DictWriter(buffer, fieldnames=fieldnames)
    writer.writeheader()
    for row in rows:
        writer.writerow({field: row.get(field, "") for field in fieldnames})
    return buffer.getvalue().encode("utf-8")


def _load_json(path: Path) -> dict[str, Any]:
    loaded = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(loaded, dict):
        raise ValueError(f"expected JSON object: {path}")
    return loaded


def _as_dict(value: Any, *, field_name: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ValueError(f"{field_name} must be an object")
    return dict(value)


def _dedupe_preserving_order(values: Iterable[str]) -> list[str]:
    seen: set[str] = set()
    ordered: list[str] = []
    for value in values:
        if value in seen:
            continue
        seen.add(value)
        ordered.append(value)
    return ordered
