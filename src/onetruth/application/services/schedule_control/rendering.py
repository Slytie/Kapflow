from __future__ import annotations

import hashlib
from typing import Any

from .bundle_builder import WeeklyScheduleControlBundle
from .scoring import summarize_soft_scores
from .validation import build_stage04_validation_summary


def render_stage04_input_bundle(
    *,
    bundle: WeeklyScheduleControlBundle,
) -> dict[str, Any]:
    return {
        "bundle": {
            "bundle_id": bundle.bundle_id,
            "trigger_type": bundle.trigger_type,
            "planning_week_id": bundle.planning_week_id,
            "scope_dates": {
                "start": bundle.scope_start,
                "end_exclusive": bundle.scope_end_exclusive,
            },
            "publish_intent": "publish_weekly_base_schedule",
            "referenced_artifacts": list(bundle.referenced_artifacts),
            "external_evidence_refs": list(bundle.external_evidence_refs),
            "planner_notes": list(bundle.planner_notes),
        }
    }


def render_stage04_candidate_delta(
    *,
    bundle: WeeklyScheduleControlBundle,
    selected_candidates: list[dict[str, Any]],
) -> dict[str, Any]:
    candidate_delta_id = stage04_candidate_delta_id(
        bundle_id=bundle.bundle_id,
        selected_candidates=selected_candidates,
    )
    columns = [
        "candidate_delta_id",
        "route_slot_id",
        "service_date",
        "route_id",
        "assigned_driver_id",
        "assignment_action",
        "rationale_code",
        "projected_minutes",
        "source_bundle_id",
    ]
    rows: list[list[Any]] = []
    for selected in selected_candidates:
        route_slot_id = str(selected.get("route_slot_id") or "")
        rows.append(
            [
                candidate_delta_id,
                route_slot_id,
                str(selected.get("service_date") or ""),
                _route_id_from_slot(route_slot_id),
                str(selected.get("candidate_driver_id") or ""),
                str(selected.get("assignment_action") or "assign"),
                str(selected.get("rationale_code") or ""),
                int(selected.get("projected_minutes") or 0),
                bundle.bundle_id,
            ]
        )

    return {
        "columns": columns,
        "rows": rows,
        "candidate_delta_id": candidate_delta_id,
    }


def render_stage04_validation_summary(
    *,
    bundle: WeeklyScheduleControlBundle,
    selected_candidates: list[dict[str, Any]],
    candidate_delta_id: str,
) -> dict[str, Any]:
    soft_totals = summarize_soft_scores(selected_candidates)
    summary = build_stage04_validation_summary(
        bundle=bundle,
        selected_candidates=selected_candidates,
        soft_score_totals=soft_totals,
    )
    summary["candidate_delta_id"] = candidate_delta_id
    return {"summary": summary}


def render_stage04_draft_weekly_schedule_workbook(
    *,
    bundle: WeeklyScheduleControlBundle,
    selected_candidates: list[dict[str, Any]],
    candidate_delta_id: str,
) -> dict[str, Any]:
    columns = [
        "service_date",
        "route_slot_id",
        "assigned_driver_id",
        "assignment_status",
        "projected_minutes",
        "candidate_delta_id",
        "source_bundle_id",
    ]
    rows: list[list[Any]] = []
    for selected in selected_candidates:
        rows.append(
            [
                str(selected.get("service_date") or ""),
                str(selected.get("route_slot_id") or ""),
                str(selected.get("candidate_driver_id") or ""),
                str(selected.get("hard_filter_status") or "blocked"),
                int(selected.get("projected_minutes") or 0),
                candidate_delta_id,
                bundle.bundle_id,
            ]
        )

    return {
        "columns": columns,
        "rows": rows,
    }


def render_stage04_draft_weekly_schedule_doc(
    *,
    bundle: WeeklyScheduleControlBundle,
    validation_summary: dict[str, Any],
    selected_candidates: list[dict[str, Any]],
) -> dict[str, Any]:
    summary = validation_summary.get("summary") if isinstance(validation_summary, dict) else {}
    return {
        "summary": {
            "bundle_id": bundle.bundle_id,
            "selected_route_slot_count": len(selected_candidates),
            "hard_rule_result": str(summary.get("hard_rule_result") or "unknown"),
            "recommended_action": str(summary.get("recommended_action") or "review_required"),
            "warnings": list(summary.get("warnings") or []),
            "violations": list(summary.get("violations") or []),
        }
    }


def stage04_candidate_delta_id(
    *,
    bundle_id: str,
    selected_candidates: list[dict[str, Any]],
) -> str:
    rows = [
        "|".join(
            [
                str(item.get("service_date") or ""),
                str(item.get("route_slot_id") or ""),
                str(item.get("candidate_driver_id") or ""),
                str(item.get("hard_filter_status") or ""),
                str(item.get("score_bucket") or ""),
            ]
        )
        for item in sorted(
            selected_candidates,
            key=lambda row: (
                str(row.get("service_date") or ""),
                str(row.get("route_slot_id") or ""),
            ),
        )
    ]
    digest = hashlib.sha256((bundle_id + "\n" + "\n".join(rows)).encode("utf-8")).hexdigest()[:8]
    compact = bundle_id.removeprefix("bundle-")
    return f"cand-{compact}-{digest}"


def _route_id_from_slot(route_slot_id: str) -> str:
    compact = route_slot_id.split("#", maxsplit=1)[0]
    token = compact.rsplit("-", maxsplit=1)[-1]
    return token.upper()
