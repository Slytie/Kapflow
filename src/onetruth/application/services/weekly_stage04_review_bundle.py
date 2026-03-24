from __future__ import annotations

import csv
import io
import json
from pathlib import Path
from typing import Any, Iterable
import zipfile

_CANONICAL_OUTPUT_KINDS: tuple[str, ...] = (
    "planning.candidate_schedule_delta.workbook",
    "planning.validation_summary.doc",
    "planning.draft_weekly_schedule.workbook",
    "planning.draft_weekly_schedule.doc",
)

_AVAILABILITY_STATE_ORDER: tuple[str, ...] = (
    "PREFERRED",
    "AVAILABLE",
    "AVOID_IF_POSSIBLE",
    "ON_CALL_ONLY",
    "CANNOT",
)

_BASELINE_TEMPLATE_STATE_ORDER: tuple[str, ...] = (
    "assigned_template",
    "on_call_template",
    "white_template",
    "yellow_template",
    "black_template",
)

_SELECTED_ASSIGNMENT_FIELDNAMES: tuple[str, ...] = (
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
    if not summary_path.exists():
        raise ValueError(f"pilot summary not found: {summary_path}")

    summary = _load_json(summary_path)
    run_entry = _pilot_run_entry(summary, pilot_id=pilot_id)

    inspection_path = resolved_run_root / pilot_id / "inspection_packet.json"
    if not inspection_path.exists():
        raise ValueError(f"inspection packet not found: {inspection_path}")

    inspection_packet = _load_json(inspection_path)
    canonical_outputs = _canonical_output_payloads(inspection_packet)
    analysis = _build_analysis_payload(canonical_outputs)
    on_call_note = _build_on_call_template_note(analysis)

    bundle_manifest = {
        "bundle_kind": "weekly_stage04_review_bundle",
        "manifest_version": 2,
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
        "csv_files": [
            "csv/new_agreement_required_rows.csv",
            "csv/selected_route_slot_assignments.csv",
        ],
        "note_files": ["notes/on_call_template_usage.md"],
    }

    archive_entries: dict[str, bytes] = {
        "bundle_manifest.json": _json_bytes(bundle_manifest),
        "README.md": _text_bytes(
            _build_bundle_readme(
                bundle_manifest=bundle_manifest,
                analysis=analysis,
                on_call_note=on_call_note,
            )
        ),
        "csv/new_agreement_required_rows.csv": _csv_bytes(
            analysis["new_agreement_rows"],
            fieldnames=list(_SELECTED_ASSIGNMENT_FIELDNAMES),
        ),
        "csv/selected_route_slot_assignments.csv": _csv_bytes(
            analysis["selected_assignment_rows"],
            fieldnames=list(_SELECTED_ASSIGNMENT_FIELDNAMES),
        ),
        "notes/on_call_template_usage.md": _text_bytes(on_call_note),
    }
    for artifact_kind, payload in canonical_outputs.items():
        archive_entries[f"canonical_outputs/{artifact_kind}.json"] = _json_bytes(payload)

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
        metadata = _artifact_metadata(artifacts, artifact_kind)
        payloads[artifact_kind] = metadata
    return payloads


def _build_analysis_payload(
    canonical_outputs: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    validation_summary = _as_dict(
        canonical_outputs["planning.validation_summary.doc"].get("summary"),
        field_name="planning.validation_summary.doc.summary",
    )
    coverage_summary = _as_dict(
        validation_summary.get("coverage_summary"),
        field_name="planning.validation_summary.doc.summary.coverage_summary",
    )

    candidate_delta = canonical_outputs["planning.candidate_schedule_delta.workbook"]
    columns = [str(column) for column in list(candidate_delta.get("columns") or [])]
    selected_assignment_rows = [
        _selected_assignment_row(dict(zip(columns, row)))
        for row in list(candidate_delta.get("rows") or [])
        if str(dict(zip(columns, row)).get("assignment_action") or "assign") == "assign"
    ]
    selected_assignment_rows.sort(
        key=lambda row: (
            str(row["service_date"]),
            str(row["route_slot_id"]),
            str(row["assigned_driver_id"]),
        )
    )

    reserve_rows = [
        _selected_assignment_row(dict(row))
        for row in list(candidate_delta.get("reserve_rows") or [])
        if isinstance(row, dict)
    ]
    reserve_summary = dict(validation_summary.get("reserve_summary") or {})
    new_agreement_rows = [
        _selected_assignment_row(dict(row))
        for row in list(validation_summary.get("new_agreement_rows") or [])
        if isinstance(row, dict)
    ]
    availability_state_counts = {
        state: 0 for state in _availability_state_order(selected_assignment_rows)
    }
    baseline_template_state_counts = {
        state: 0 for state in _baseline_template_state_order(selected_assignment_rows)
    }
    for row in selected_assignment_rows:
        state = str(row["availability_state"] or "")
        if state and state not in availability_state_counts:
            availability_state_counts[state] = 0
        if state:
            availability_state_counts[state] += 1
        template_state = str(row["baseline_template_state"] or "")
        if template_state and template_state not in baseline_template_state_counts:
            baseline_template_state_counts[template_state] = 0
        if template_state:
            baseline_template_state_counts[template_state] += 1

    on_call_template_usage_count = sum(
        1
        for row in reserve_rows
        if str(row["baseline_template_state"] or "") == "on_call_template"
    )
    white_template_agreement_count = sum(
        1
        for row in new_agreement_rows
        if str(row["new_agreement_trigger_reason"] or "") == "white_template_to_assigned"
    )
    yellow_template_agreement_count = sum(
        1
        for row in new_agreement_rows
        if str(row["new_agreement_trigger_reason"] or "") == "yellow_template_to_assigned"
    )
    white_template_on_call_count = sum(
        1
        for row in new_agreement_rows
        if str(row["new_agreement_trigger_reason"] or "") == "white_template_to_on_call"
    )
    yellow_template_on_call_count = sum(
        1
        for row in new_agreement_rows
        if str(row["new_agreement_trigger_reason"] or "") == "yellow_template_to_on_call"
    )

    return {
        "coverage_summary": coverage_summary,
        "new_agreement_required_count": int(
            validation_summary.get("new_agreement_required_count") or 0
        ),
        "new_agreement_by_service_date": dict(
            validation_summary.get("new_agreement_by_service_date") or {}
        ),
        "warning_count": len(validation_summary.get("warnings") or []),
        "reserve_summary": reserve_summary,
        "baseline_template_state_counts": baseline_template_state_counts,
        "baseline_template_state_order": list(
            _baseline_template_state_order(selected_assignment_rows)
        ),
        "availability_state_counts": availability_state_counts,
        "availability_state_order": list(_availability_state_order(selected_assignment_rows)),
        "selected_assignment_rows": selected_assignment_rows,
        "reserve_rows": reserve_rows,
        "new_agreement_rows": new_agreement_rows,
        "on_call_template_usage_count": on_call_template_usage_count,
        "white_template_agreement_count": white_template_agreement_count,
        "yellow_template_agreement_count": yellow_template_agreement_count,
        "white_template_on_call_count": white_template_on_call_count,
        "yellow_template_on_call_count": yellow_template_on_call_count,
    }


def _selected_assignment_row(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "service_date": str(row.get("service_date") or ""),
        "route_slot_id": str(row.get("route_slot_id") or ""),
        "route_id": str(row.get("route_id") or ""),
        "assigned_driver_id": str(
            row.get("assigned_driver_id")
            or row.get("candidate_driver_id")
            or ""
        ),
        "availability_state": str(row.get("availability_state") or ""),
        "baseline_template_state": str(row.get("baseline_template_state") or ""),
        "planned_driver_day_state": str(row.get("planned_driver_day_state") or ""),
        "new_agreement_required": bool(row.get("new_agreement_required")),
        "new_agreement_trigger_reason": str(row.get("new_agreement_trigger_reason") or ""),
        "template_state_preservation_fit": row.get("template_state_preservation_fit"),
        "iteration_index": int(row.get("iteration_index") or 0),
        "phase": str(row.get("phase") or row.get("planning_phase") or ""),
        "projected_minutes": int(row.get("projected_minutes") or 0),
        "rationale_code": str(row.get("rationale_code") or ""),
    }


def _availability_state_order(selected_assignment_rows: list[dict[str, Any]]) -> tuple[str, ...]:
    discovered = {
        str(row.get("availability_state") or "").strip()
        for row in selected_assignment_rows
        if str(row.get("availability_state") or "").strip()
    }
    ordered = list(_AVAILABILITY_STATE_ORDER)
    for state in sorted(discovered):
        if state not in ordered:
            ordered.append(state)
    return tuple(ordered)


def _baseline_template_state_order(
    selected_assignment_rows: list[dict[str, Any]],
) -> tuple[str, ...]:
    discovered = {
        str(row.get("baseline_template_state") or "").strip()
        for row in selected_assignment_rows
        if str(row.get("baseline_template_state") or "").strip()
    }
    ordered = list(_BASELINE_TEMPLATE_STATE_ORDER)
    for state in sorted(discovered):
        if state not in ordered:
            ordered.append(state)
    return tuple(ordered)


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
    analysis: dict[str, Any],
    on_call_note: str,
) -> str:
    coverage_summary = analysis["coverage_summary"]
    lines = [
        "# Weekly Stage04 SME Review Bundle",
        "",
        f"- Pilot ID: `{bundle_manifest['pilot_id']}`",
        f"- Pilot key: `{bundle_manifest['pilot_key']}`",
        f"- OpenAI mode: `{bundle_manifest['openai_mode']}`",
        f"- Workflow run ID: `{bundle_manifest['workflow_run_id']}`",
        (
            f"- Coverage: `{coverage_summary.get('assigned_route_slots', 0)} assigned / "
            f"{coverage_summary.get('uncovered_route_slots', 0)} uncovered`"
        ),
        (
            f"- New agreement required count: "
            f"`{analysis['new_agreement_required_count']}`"
        ),
        f"- Warning count: `{analysis['warning_count']}`",
        "",
        "## By-Day Agreement Counts",
        "",
    ]
    for service_date, count in sorted(analysis["new_agreement_by_service_date"].items()):
        lines.append(f"- `{service_date}`: `{count}`")

    lines.extend(
        [
            "",
            "## Selected Baseline Template-State Counts",
            "",
        ]
    )
    for state in analysis["baseline_template_state_order"]:
        count = int(analysis["baseline_template_state_counts"].get(state, 0) or 0)
        if count <= 0:
            continue
        lines.append(f"- `{state}`: `{count}`")

    lines.extend(
        [
            "",
            "## Selected Availability-State Counts",
            "",
        ]
    )
    for state in analysis["availability_state_order"]:
        count = int(analysis["availability_state_counts"].get(state, 0) or 0)
        if count <= 0:
            continue
        lines.append(f"- `{state}`: `{count}`")

    lines.extend(
        [
            "",
            "## On-Call Buffer Summary",
            "",
        ]
    )
    reserve_summary = dict(analysis.get("reserve_summary") or {})
    target_by_service_date = dict(reserve_summary.get("on_call_target_by_service_date") or {})
    filled_by_service_date = dict(reserve_summary.get("selected_on_call_by_service_date") or {})
    lines.append(
        f"- On-call buffer total: `{reserve_summary.get('selected_on_call_total', 0)}` filled / "
        f"`{reserve_summary.get('target_on_call_total', 0)}` targeted"
    )
    for service_date in sorted(target_by_service_date):
        lines.append(
            f"- `{service_date}`: `{filled_by_service_date.get(service_date, 0)}` filled / "
            f"`{target_by_service_date.get(service_date, 0)}` targeted"
        )

    lines.extend(
        [
            "",
            "## On-Call Template Usage",
            "",
        ]
    )
    on_call_note_lines = list(on_call_note.splitlines())
    if on_call_note_lines and on_call_note_lines[0].startswith("# "):
        on_call_note_lines = on_call_note_lines[1:]
        if on_call_note_lines and not on_call_note_lines[0].strip():
            on_call_note_lines = on_call_note_lines[1:]
    lines.extend(on_call_note_lines)
    lines.append("")
    return "\n".join(lines)


def _build_on_call_template_note(analysis: dict[str, Any]) -> str:
    on_call_usage_count = int(analysis["on_call_template_usage_count"])
    reserve_summary = dict(analysis.get("reserve_summary") or {})
    selected_on_call_total = int(reserve_summary.get("selected_on_call_total") or 0)
    target_on_call_total = int(reserve_summary.get("target_on_call_total") or 0)
    if on_call_usage_count > 0:
        headline = (
            "- Summary: The patch filled "
            f"`{selected_on_call_total}` of `{target_on_call_total}` On-Call buffer positions "
            f"and used signed on-call template days `{on_call_usage_count}` time(s) before taking "
            "relief from white/yellow days."
        )
    else:
        headline = (
            "- Summary: The patch filled "
            f"`{selected_on_call_total}` of `{target_on_call_total}` On-Call buffer positions "
            "without using signed on-call template days."
        )
    return "\n".join(
        [
            "# On-Call Template Usage",
            "",
            headline,
            (
                "- On-call buffer positions filled: "
                f"`{selected_on_call_total}` / `{target_on_call_total}`"
            ),
            (
                "- On-call template day assignments: "
                f"`{on_call_usage_count}`"
            ),
            (
                "- White-template assigned agreement cases: "
                f"`{analysis['white_template_agreement_count']}`"
            ),
            (
                "- Yellow-template assigned agreement cases: "
                f"`{analysis['yellow_template_agreement_count']}`"
            ),
            (
                "- White-template On-Call agreement cases: "
                f"`{analysis['white_template_on_call_count']}`"
            ),
            (
                "- Yellow-template On-Call agreement cases: "
                f"`{analysis['yellow_template_on_call_count']}`"
            ),
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
