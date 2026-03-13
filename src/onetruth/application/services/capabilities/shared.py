from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Iterable, Mapping, Sequence


@dataclass(frozen=True)
class Principal:
    actor_id: str
    actor_type: str
    actor_roles: tuple[str, ...]


@dataclass(frozen=True)
class DecisionReason:
    code: str
    details: Mapping[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class CapabilityDecision:
    capability_id: str
    allowed: bool
    reasons: tuple[DecisionReason, ...] = ()
    metadata: Mapping[str, Any] = field(default_factory=dict)


def reason(code: str, **details: Any) -> DecisionReason:
    return DecisionReason(code=code, details=details)


def allow(
    capability_id: str,
    *,
    metadata: Mapping[str, Any] | None = None,
) -> CapabilityDecision:
    return CapabilityDecision(
        capability_id=capability_id,
        allowed=True,
        metadata=metadata or {},
    )


def deny(
    capability_id: str,
    *,
    reasons: Iterable[DecisionReason],
    metadata: Mapping[str, Any] | None = None,
) -> CapabilityDecision:
    return CapabilityDecision(
        capability_id=capability_id,
        allowed=False,
        reasons=tuple(reasons),
        metadata=metadata or {},
    )


def project_available_actions(
    actions: Sequence[tuple[str, CapabilityDecision]],
) -> list[str]:
    return [public_action for public_action, decision in actions if decision.allowed]


def legacy_reason_code(reason_item: DecisionReason) -> str:
    if reason_item.code == "required_upload_missing":
        dataset_key = str(reason_item.details.get("dataset_key") or "").strip()
        if dataset_key:
            return f"{reason_item.code}:{dataset_key}"
    if reason_item.code == "required_review_confirmation_missing":
        artifact_kind = str(reason_item.details.get("artifact_kind") or "").strip()
        if artifact_kind:
            return f"{reason_item.code}:{artifact_kind}"
    return reason_item.code


def legacy_reason_codes(reasons: Iterable[DecisionReason]) -> list[str]:
    codes: list[str] = []
    seen: set[str] = set()
    for reason_item in reasons:
        code = legacy_reason_code(reason_item)
        if code in seen:
            continue
        seen.add(code)
        codes.append(code)
    return codes
