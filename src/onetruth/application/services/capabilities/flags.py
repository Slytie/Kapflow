from __future__ import annotations

from typing import Any

from .shared import CapabilityDecision, Principal, allow, deny, reason

ACTIVE_FLAG_STATES = {"open", "triage", "blocked"}
FLAG_TRANSITION_ROLES = {
    "dispatch_supervisor",
    "operations_manager",
    "fleet_coordinator",
    "schedule_planner",
}


def transition_decision(
    *,
    flag: dict[str, Any],
    principal: Principal,
) -> CapabilityDecision:
    state = str(flag.get("state") or "")
    role_match = _roles_intersect(tuple(FLAG_TRANSITION_ROLES), principal.actor_roles)

    reasons = []
    if state not in ACTIVE_FLAG_STATES:
        reasons.append(reason("flag_not_active", state=state))
    if state in ACTIVE_FLAG_STATES and not role_match:
        reasons.append(
            reason(
                "flag_transition_role_mismatch",
                actor_roles=list(principal.actor_roles),
                allowed_roles=sorted(FLAG_TRANSITION_ROLES),
            )
        )

    if state in ACTIVE_FLAG_STATES and role_match:
        return allow("flag.transition")
    return deny("flag.transition", reasons=reasons)


def _roles_intersect(left: tuple[str, ...], right: tuple[str, ...]) -> bool:
    return bool(set(left).intersection(right))
