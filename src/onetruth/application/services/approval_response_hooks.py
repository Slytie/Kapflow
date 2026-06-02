from __future__ import annotations

from dataclasses import dataclass
import sqlite3
from typing import Any, Callable, Sequence


@dataclass(frozen=True)
class ApprovalResponseHookContext:
    connection: sqlite3.Connection
    approval: dict[str, Any]
    requested_action: str
    response_kind: str
    actor_id: str
    actor_type: str
    event_idempotency_base: str | None


@dataclass(frozen=True)
class ApprovalResponseHook:
    hook_id: str
    handler: Callable[[ApprovalResponseHookContext], None]


def _load_default_hooks() -> tuple[ApprovalResponseHook, ...]:
    from onetruth.application.services.logistics_approval_response_hooks import (
        LOGISTICS_APPROVAL_RESPONSE_HOOKS,
    )

    return LOGISTICS_APPROVAL_RESPONSE_HOOKS


DEFAULT_APPROVAL_RESPONSE_HOOKS: tuple[ApprovalResponseHook, ...] = _load_default_hooks()


def run_registered_approval_response_hooks(
    context: ApprovalResponseHookContext,
    *,
    hooks: Sequence[ApprovalResponseHook] | None = None,
) -> None:
    active_hooks = tuple(DEFAULT_APPROVAL_RESPONSE_HOOKS if hooks is None else hooks)
    for hook in active_hooks:
        hook.handler(context)


__all__ = [
    "ApprovalResponseHook",
    "ApprovalResponseHookContext",
    "DEFAULT_APPROVAL_RESPONSE_HOOKS",
    "run_registered_approval_response_hooks",
]
