from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable, Mapping


_BASELINE_TEMPLATE_STATE_BY_AVAILABILITY = {
    "PREFERRED": "assigned_template",
    "ON_CALL_ONLY": "on_call_template",
    "AVAILABLE": "white_template",
    "AVOID_IF_POSSIBLE": "yellow_template",
    "CANNOT": "black_template",
}

_TEMPLATE_STATE_PRESERVATION_FIT = {
    "assigned_template": 1.0,
    "on_call_template": 0.9,
    "white_template": 0.38,
    "yellow_template": 0.12,
    "black_template": 0.0,
    "unknown_template": 0.35,
}


@dataclass(frozen=True)
class ContractMinimizationAssessment:
    baseline_template_state: str
    planned_driver_day_state: str
    new_agreement_required: bool
    new_agreement_trigger_reason: str
    template_state_preservation_fit: float


def baseline_template_state_from_availability_state(availability_state: Any) -> str:
    token = str(availability_state or "").strip().upper()
    if not token:
        return "unknown_template"
    return _BASELINE_TEMPLATE_STATE_BY_AVAILABILITY.get(token, "unknown_template")


def assess_contract_minimization(
    *,
    availability_state: Any,
    planned_driver_day_state: str = "assigned",
) -> ContractMinimizationAssessment:
    normalized_planned_state = str(planned_driver_day_state or "").strip().lower() or "unknown"
    baseline_template_state = baseline_template_state_from_availability_state(availability_state)
    new_agreement_required = (
        normalized_planned_state == "assigned"
        and baseline_template_state in {"white_template", "yellow_template"}
    )
    trigger_reason = ""
    if new_agreement_required:
        trigger_reason = f"{baseline_template_state}_to_{normalized_planned_state}"
    fit = (
        _TEMPLATE_STATE_PRESERVATION_FIT.get(baseline_template_state, 0.35)
        if normalized_planned_state == "assigned"
        else 0.0
    )
    return ContractMinimizationAssessment(
        baseline_template_state=baseline_template_state,
        planned_driver_day_state=normalized_planned_state,
        new_agreement_required=new_agreement_required,
        new_agreement_trigger_reason=trigger_reason,
        template_state_preservation_fit=round(float(fit), 6),
    )


def summarize_contract_change_metrics(
    selected_candidates: Iterable[Mapping[str, Any]],
) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    for item in selected_candidates:
        if str(item.get("assignment_action") or "assign") != "assign":
            continue
        if not bool(item.get("new_agreement_required")):
            continue
        rows.append(
            {
                "route_slot_id": str(item.get("route_slot_id") or ""),
                "route_id": str(item.get("route_id") or ""),
                "service_date": str(item.get("service_date") or ""),
                "candidate_driver_id": str(item.get("candidate_driver_id") or ""),
                "baseline_template_state": str(item.get("baseline_template_state") or ""),
                "planned_driver_day_state": str(item.get("planned_driver_day_state") or ""),
                "new_agreement_trigger_reason": str(
                    item.get("new_agreement_trigger_reason") or ""
                ),
            }
        )

    rows = sorted(
        rows,
        key=lambda row: (
            row["service_date"],
            row["candidate_driver_id"],
            row["route_slot_id"],
        ),
    )
    driver_days = {
        (row["candidate_driver_id"], row["service_date"])
        for row in rows
        if row["candidate_driver_id"] and row["service_date"]
    }
    by_service_date: dict[str, int] = {}
    for row in rows:
        service_date = row["service_date"]
        by_service_date[service_date] = by_service_date.get(service_date, 0) + 1

    return {
        "new_agreement_required_count": len(rows),
        "new_agreement_driver_day_count": len(driver_days),
        "new_agreement_driver_ids": sorted(
            {
                row["candidate_driver_id"]
                for row in rows
                if row["candidate_driver_id"]
            }
        ),
        "new_agreement_by_service_date": dict(sorted(by_service_date.items())),
        "new_agreement_rows": rows,
    }
