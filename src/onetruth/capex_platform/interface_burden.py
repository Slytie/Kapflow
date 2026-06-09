from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal


InterfaceBurdenState = Literal[
    "owned",
    "transferred",
    "waived",
    "accepted_residual",
    "open",
]

VALID_INTERFACE_BURDEN_STATES: tuple[InterfaceBurdenState, ...] = (
    "owned",
    "transferred",
    "waived",
    "accepted_residual",
    "open",
)
DEFAULT_INTERFACE_BURDEN_POLICY_VERSION = "capex.interface_burden.v1"
SOURCE_OCCURRENCE_REF_PREFIX = "source_occurrence:"
ALLOWED_EVIDENCE_REF_PREFIXES: tuple[str, ...] = (
    "artifact_version:",
    "closure_gate_evaluation:",
    "closure_snapshot:",
    "source_occurrence:",
    "task_run:",
    "timeline_event:",
    "waiver:",
)


@dataclass(frozen=True)
class InterfaceBurdenFollowUpTask:
    follow_up_key: str
    task_kind: str
    owner_actor_ref: str
    reason: str
    metadata: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return {
            "follow_up_key": self.follow_up_key,
            "task_kind": self.task_kind,
            "owner_actor_ref": self.owner_actor_ref,
            "reason": self.reason,
            "metadata": dict(self.metadata),
        }


@dataclass(frozen=True)
class InterfaceBurdenObligation:
    obligation_id: str
    interface_ref: str
    tenant_id: str
    domain_id: str
    project_id: str | None
    state: str
    owner_actor_ref: str | None = None
    transfer_target_actor_ref: str | None = None
    waiver_id: str | None = None
    residual_acceptance_ref: str | None = None
    follow_up_owner_actor_ref: str | None = None
    follow_up_task_kind: str = "capex.interface_resolution"
    source_refs: tuple[str, ...] = ()
    evidence_refs: tuple[str, ...] = ()
    reason: str | None = None
    policy_version: str = DEFAULT_INTERFACE_BURDEN_POLICY_VERSION

    @property
    def basis_refs(self) -> tuple[str, ...]:
        return tuple(sorted({*self.source_refs, *self.evidence_refs}))

    def scope(self) -> dict[str, str | None]:
        return {
            "tenant_id": self.tenant_id,
            "domain_id": self.domain_id,
            "project_id": self.project_id,
        }


@dataclass(frozen=True)
class InterfaceBurdenValidationResult:
    conserved: bool
    obligation_id: str | None
    state: str | None
    error_codes: tuple[str, ...]
    follow_up_tasks: tuple[InterfaceBurdenFollowUpTask, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "conserved": self.conserved,
            "obligation_id": self.obligation_id,
            "state": self.state,
            "error_codes": list(self.error_codes),
            "follow_up_tasks": [task.to_dict() for task in self.follow_up_tasks],
        }


class InterfaceBurdenPolicyError(ValueError):
    def __init__(self, message: str, *, result: InterfaceBurdenValidationResult) -> None:
        super().__init__(message)
        self.result = result


def validate_interface_burden(
    obligation: InterfaceBurdenObligation | None,
) -> InterfaceBurdenValidationResult:
    if obligation is None:
        return InterfaceBurdenValidationResult(
            conserved=False,
            obligation_id=None,
            state=None,
            error_codes=("missing_interface_burden_obligation",),
        )

    errors: list[str] = []
    if not obligation.obligation_id:
        errors.append("missing_obligation_id")
    if not obligation.interface_ref:
        errors.append("missing_interface_ref")
    if not obligation.tenant_id:
        errors.append("missing_tenant_id")
    if not obligation.domain_id:
        errors.append("missing_domain_id")

    if obligation.state not in VALID_INTERFACE_BURDEN_STATES:
        errors.append("invalid_interface_burden_state")
    elif obligation.state == "owned":
        if not obligation.owner_actor_ref:
            errors.append("missing_owner_actor_ref")
        _append_basis_errors(obligation, errors)
    elif obligation.state == "transferred":
        if not obligation.transfer_target_actor_ref:
            errors.append("missing_transfer_target_actor_ref")
        _append_basis_errors(obligation, errors)
    elif obligation.state == "waived":
        if not obligation.waiver_id:
            errors.append("missing_waiver_id")
        _append_basis_errors(obligation, errors)
    elif obligation.state == "accepted_residual":
        if not obligation.residual_acceptance_ref:
            errors.append("missing_residual_acceptance_ref")
        _append_basis_errors(obligation, errors)
    elif obligation.state == "open":
        if not obligation.follow_up_owner_actor_ref:
            errors.append("missing_follow_up_owner_actor_ref")

    if not obligation.policy_version:
        errors.append("missing_policy_version")
    for source_ref in obligation.source_refs:
        if not source_ref.startswith(SOURCE_OCCURRENCE_REF_PREFIX):
            errors.append("malformed_source_ref")
            break
    for evidence_ref in obligation.evidence_refs:
        if not evidence_ref.startswith(ALLOWED_EVIDENCE_REF_PREFIXES):
            errors.append("malformed_evidence_ref")
            break

    unique_errors = tuple(dict.fromkeys(errors))
    follow_up_tasks = (
        ()
        if unique_errors
        else _follow_up_tasks_for_obligation(obligation)
    )
    return InterfaceBurdenValidationResult(
        conserved=not unique_errors,
        obligation_id=obligation.obligation_id or None,
        state=obligation.state or None,
        error_codes=unique_errors,
        follow_up_tasks=follow_up_tasks,
    )


def require_interface_burden_conserved(
    obligation: InterfaceBurdenObligation | None,
) -> InterfaceBurdenValidationResult:
    result = validate_interface_burden(obligation)
    if not result.conserved:
        raise InterfaceBurdenPolicyError(
            "interface burden is not conserved: " + ", ".join(result.error_codes),
            result=result,
        )
    return result


def _append_basis_errors(
    obligation: InterfaceBurdenObligation,
    errors: list[str],
) -> None:
    if not obligation.basis_refs:
        errors.append("missing_traceable_basis_refs")


def _follow_up_tasks_for_obligation(
    obligation: InterfaceBurdenObligation,
) -> tuple[InterfaceBurdenFollowUpTask, ...]:
    if obligation.state == "open":
        assert obligation.follow_up_owner_actor_ref is not None
        return (
            _follow_up_task(
                obligation,
                task_kind=obligation.follow_up_task_kind,
                owner_actor_ref=obligation.follow_up_owner_actor_ref,
                reason="interface_burden_open",
            ),
        )
    if obligation.state == "transferred":
        assert obligation.transfer_target_actor_ref is not None
        return (
            _follow_up_task(
                obligation,
                task_kind="capex.interface_transfer_acceptance",
                owner_actor_ref=obligation.transfer_target_actor_ref,
                reason="interface_burden_transferred",
            ),
        )
    return ()


def _follow_up_task(
    obligation: InterfaceBurdenObligation,
    *,
    task_kind: str,
    owner_actor_ref: str,
    reason: str,
) -> InterfaceBurdenFollowUpTask:
    follow_up_key = (
        f"{obligation.policy_version}:"
        f"{obligation.tenant_id}:"
        f"{obligation.domain_id}:"
        f"{obligation.project_id or 'no-project'}:"
        f"{obligation.obligation_id}:"
        f"{task_kind}"
    )
    return InterfaceBurdenFollowUpTask(
        follow_up_key=follow_up_key,
        task_kind=task_kind,
        owner_actor_ref=owner_actor_ref,
        reason=reason,
        metadata={
            "obligation_id": obligation.obligation_id,
            "interface_ref": obligation.interface_ref,
            "state": obligation.state,
            "scope": obligation.scope(),
            "basis_refs": list(obligation.basis_refs),
            "reason": obligation.reason,
            "policy_version": obligation.policy_version,
        },
    )


__all__ = [
    "ALLOWED_EVIDENCE_REF_PREFIXES",
    "DEFAULT_INTERFACE_BURDEN_POLICY_VERSION",
    "InterfaceBurdenFollowUpTask",
    "InterfaceBurdenObligation",
    "InterfaceBurdenPolicyError",
    "InterfaceBurdenState",
    "InterfaceBurdenValidationResult",
    "VALID_INTERFACE_BURDEN_STATES",
    "require_interface_burden_conserved",
    "validate_interface_burden",
]
