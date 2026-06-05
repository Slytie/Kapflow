from __future__ import annotations

import pytest

from onetruth.application.services.approval_response_hooks import (
    ApprovalEffectPack,
    ApprovalEffectRegistration,
    ApprovalEffectRegistry,
    ApprovalResponseHook,
    ApprovalResponseHookContext,
    DEFAULT_APPROVAL_EFFECT_REGISTRY,
)
from onetruth.application.services.logistics_approval_response_hooks import (
    DISPATCH_REPORTING_WORKFLOW_ID,
    LOGISTICS_APPROVAL_RESPONSE_EFFECT_PACK,
    LOGISTICS_APPROVAL_RESPONSE_EFFECT_REGISTRY,
    LOGISTICS_APPROVAL_RESPONSE_HOOKS,
    WEEKLY_WORKFLOW_ID,
    logistics_approval_response_hooks_for_workflow,
)


def _noop(_: ApprovalResponseHookContext) -> None:
    return None


def _hook(hook_id: str) -> ApprovalResponseHook:
    return ApprovalResponseHook(hook_id=hook_id, handler=_noop)


def test_default_approval_effect_registry_is_platform_neutral() -> None:
    assert DEFAULT_APPROVAL_EFFECT_REGISTRY.pack_names == ()
    assert DEFAULT_APPROVAL_EFFECT_REGISTRY.hooks_for_workflow("capex.intake.v1") == ()
    assert DEFAULT_APPROVAL_EFFECT_REGISTRY.hooks_for_workflow("unknown.workflow.v1") == ()


def test_approval_effect_registry_returns_hooks_for_matching_workflow_in_pack_order() -> None:
    first = _hook("test.first")
    second = _hook("test.second")
    registry = ApprovalEffectRegistry(
        packs=(
            ApprovalEffectPack(
                pack_name="alpha",
                effects=(
                    ApprovalEffectRegistration(
                        hook=first,
                        workflow_ids=("alpha.v1", "beta.v1"),
                    ),
                    ApprovalEffectRegistration(
                        hook=second,
                        workflow_ids=("alpha.v1",),
                    ),
                ),
            ),
        )
    )

    assert registry.hooks_for_workflow("alpha.v1") == (first, second)
    assert registry.hooks_for_workflow("beta.v1") == (first,)
    assert registry.hooks_for_workflow("gamma.v1") == ()


def test_approval_effect_registry_rejects_duplicate_pack_names() -> None:
    with pytest.raises(ValueError, match="duplicate approval effect packs: alpha"):
        ApprovalEffectRegistry(
            packs=(
                ApprovalEffectPack(pack_name="alpha"),
                ApprovalEffectPack(pack_name="alpha"),
            )
        )


def test_approval_effect_registry_rejects_duplicate_effect_ids() -> None:
    with pytest.raises(ValueError, match="duplicate approval effects: test.effect"):
        ApprovalEffectRegistry(
            packs=(
                ApprovalEffectPack(
                    pack_name="alpha",
                    effects=(
                        ApprovalEffectRegistration(
                            hook=_hook("test.effect"),
                            workflow_ids=("alpha.v1",),
                        ),
                    ),
                ),
                ApprovalEffectPack(
                    pack_name="beta",
                    effects=(
                        ApprovalEffectRegistration(
                            hook=_hook("test.effect"),
                            workflow_ids=("beta.v1",),
                        ),
                    ),
                ),
            )
        )


def test_logistics_approval_effect_registry_preserves_existing_workflow_selector_parity() -> None:
    assert LOGISTICS_APPROVAL_RESPONSE_EFFECT_REGISTRY.pack_names == ("logistics",)
    assert LOGISTICS_APPROVAL_RESPONSE_EFFECT_PACK.effects
    assert (
        logistics_approval_response_hooks_for_workflow(WEEKLY_WORKFLOW_ID)
        == LOGISTICS_APPROVAL_RESPONSE_HOOKS
    )
    assert (
        logistics_approval_response_hooks_for_workflow(DISPATCH_REPORTING_WORKFLOW_ID)
        == LOGISTICS_APPROVAL_RESPONSE_HOOKS
    )
    assert logistics_approval_response_hooks_for_workflow("capex.intake.v1") == ()
    assert logistics_approval_response_hooks_for_workflow("unknown.workflow.v1") == ()
