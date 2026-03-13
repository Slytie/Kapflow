from __future__ import annotations

from typing import Any

from .shared import CapabilityDecision, Principal, allow, deny, reason


def respond_decision(
    *,
    approval: dict[str, Any],
    principal: Principal,
) -> CapabilityDecision:
    state = str(approval.get("state") or "")
    required_role = str(approval.get("required_role") or "")
    candidate_roles = tuple(str(role) for role in approval.get("candidate_roles") or [])
    role_match = (
        required_role in principal.actor_roles
        if required_role
        else _roles_intersect(candidate_roles, principal.actor_roles)
    )

    reasons = []
    if state != "PENDING":
        reasons.append(reason("approval_not_pending", state=state))
    if state == "PENDING" and not role_match:
        reasons.append(
            reason(
                "approval_role_mismatch",
                required_role=required_role or None,
                candidate_roles=list(candidate_roles),
                actor_roles=list(principal.actor_roles),
            )
        )

    if state == "PENDING" and role_match:
        return allow("approval.respond")
    return deny("approval.respond", reasons=reasons)


def _roles_intersect(left: tuple[str, ...], right: tuple[str, ...]) -> bool:
    return bool(set(left).intersection(right))
