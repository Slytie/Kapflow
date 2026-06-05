from __future__ import annotations

from dataclasses import dataclass, field
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


@dataclass(frozen=True)
class ApprovalEffectRegistration:
    hook: ApprovalResponseHook
    workflow_ids: tuple[str, ...]


@dataclass(frozen=True)
class ApprovalEffectPack:
    pack_name: str
    effects: tuple[ApprovalEffectRegistration, ...] = field(default_factory=tuple)


@dataclass(frozen=True)
class ApprovalEffectRegistry:
    packs: tuple[ApprovalEffectPack, ...] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        pack_names = [pack.pack_name for pack in self.packs]
        duplicate_packs = sorted(
            pack_name
            for pack_name in set(pack_names)
            if pack_names.count(pack_name) > 1
        )
        if duplicate_packs:
            raise ValueError(
                f"duplicate approval effect packs: {', '.join(duplicate_packs)}"
            )

        effect_ids = [effect.hook.hook_id for pack in self.packs for effect in pack.effects]
        duplicate_effects = sorted(
            effect_id
            for effect_id in set(effect_ids)
            if effect_ids.count(effect_id) > 1
        )
        if duplicate_effects:
            raise ValueError(
                f"duplicate approval effects: {', '.join(duplicate_effects)}"
            )

    @property
    def pack_names(self) -> tuple[str, ...]:
        return tuple(pack.pack_name for pack in self.packs)

    def with_pack(self, pack: ApprovalEffectPack) -> ApprovalEffectRegistry:
        return ApprovalEffectRegistry((*self.packs, pack))

    def hooks_for_workflow(self, workflow_id: str) -> tuple[ApprovalResponseHook, ...]:
        hooks: list[ApprovalResponseHook] = []
        for pack in self.packs:
            for effect in pack.effects:
                if workflow_id in effect.workflow_ids:
                    hooks.append(effect.hook)
        return tuple(hooks)


DEFAULT_APPROVAL_RESPONSE_HOOKS: tuple[ApprovalResponseHook, ...] = ()
DEFAULT_APPROVAL_EFFECT_REGISTRY = ApprovalEffectRegistry()


def run_registered_approval_response_hooks(
    context: ApprovalResponseHookContext,
    *,
    hooks: Sequence[ApprovalResponseHook] | None = None,
) -> None:
    active_hooks = tuple(DEFAULT_APPROVAL_RESPONSE_HOOKS if hooks is None else hooks)
    for hook in active_hooks:
        hook.handler(context)


__all__ = [
    "ApprovalEffectPack",
    "ApprovalEffectRegistration",
    "ApprovalEffectRegistry",
    "ApprovalResponseHook",
    "ApprovalResponseHookContext",
    "DEFAULT_APPROVAL_EFFECT_REGISTRY",
    "DEFAULT_APPROVAL_RESPONSE_HOOKS",
    "run_registered_approval_response_hooks",
]
