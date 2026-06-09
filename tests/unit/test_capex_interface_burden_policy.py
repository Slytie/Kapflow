from __future__ import annotations

import pytest

from onetruth.capex_platform.interface_burden import (
    InterfaceBurdenObligation,
    InterfaceBurdenPolicyError,
    require_interface_burden_conserved,
    validate_interface_burden,
)


BASE = {
    "obligation_id": "iface-001",
    "interface_ref": "capex-interface:site-power-handover",
    "tenant_id": "tenant-a",
    "domain_id": "domain-x",
    "project_id": "cp-alpha",
}
SOURCE_REF = "source_occurrence:so-interface-001"
EVIDENCE_REF = "closure_snapshot:cs-interface-001"


def _obligation(**overrides: object) -> InterfaceBurdenObligation:
    payload = dict(BASE)
    payload.update(overrides)
    return InterfaceBurdenObligation(**payload)  # type: ignore[arg-type]


def test_owned_interface_burden_is_conserved_with_owner_and_basis() -> None:
    result = validate_interface_burden(
        _obligation(
            state="owned",
            owner_actor_ref="human:site-owner",
            source_refs=(SOURCE_REF,),
        )
    )

    assert result.conserved is True
    assert result.error_codes == ()
    assert result.follow_up_tasks == ()


def test_transfer_creates_deterministic_acceptance_follow_up_without_mutating_runtime() -> None:
    obligation = _obligation(
        state="transferred",
        transfer_target_actor_ref="human:receiving-owner",
        source_refs=(SOURCE_REF,),
        evidence_refs=(EVIDENCE_REF,),
        reason="handover moved to receiving discipline",
    )

    first = require_interface_burden_conserved(obligation)
    second = require_interface_burden_conserved(obligation)

    assert first.conserved is True
    assert first.follow_up_tasks == second.follow_up_tasks
    follow_up = first.follow_up_tasks[0]
    assert follow_up.task_kind == "capex.interface_transfer_acceptance"
    assert follow_up.owner_actor_ref == "human:receiving-owner"
    assert follow_up.metadata["basis_refs"] == sorted([SOURCE_REF, EVIDENCE_REF])
    assert follow_up.follow_up_key.endswith(":iface-001:capex.interface_transfer_acceptance")


def test_open_interface_burden_requires_traceable_follow_up_owner() -> None:
    result = validate_interface_burden(
        _obligation(
            state="open",
            follow_up_owner_actor_ref="human:interface-manager",
            follow_up_task_kind="capex.interface_resolution",
        )
    )

    assert result.conserved is True
    follow_up = result.follow_up_tasks[0]
    assert follow_up.task_kind == "capex.interface_resolution"
    assert follow_up.reason == "interface_burden_open"
    assert follow_up.metadata["basis_refs"] == []


def test_waiver_and_residual_acceptance_need_traceable_basis() -> None:
    waiver = validate_interface_burden(
        _obligation(
            state="waived",
            waiver_id="waiver:interface-001",
            source_refs=(SOURCE_REF,),
        )
    )
    residual = validate_interface_burden(
        _obligation(
            state="accepted_residual",
            residual_acceptance_ref="approval:residual-risk-001",
            evidence_refs=(EVIDENCE_REF,),
        )
    )

    assert waiver.conserved is True
    assert residual.conserved is True


@pytest.mark.parametrize(
    ("state", "kwargs", "expected_error"),
    [
        ("owned", {}, "missing_owner_actor_ref"),
        ("transferred", {}, "missing_transfer_target_actor_ref"),
        ("waived", {}, "missing_waiver_id"),
        ("accepted_residual", {}, "missing_residual_acceptance_ref"),
        ("open", {}, "missing_follow_up_owner_actor_ref"),
    ],
)
def test_interface_burden_states_fail_closed_when_required_holder_is_missing(
    state: str,
    kwargs: dict[str, object],
    expected_error: str,
) -> None:
    result = validate_interface_burden(
        _obligation(state=state, source_refs=(SOURCE_REF,), **kwargs)
    )

    assert result.conserved is False
    assert expected_error in result.error_codes


def test_non_open_closure_like_states_require_traceable_basis_refs() -> None:
    result = validate_interface_burden(
        _obligation(state="waived", waiver_id="waiver:interface-001")
    )

    assert result.conserved is False
    assert "missing_traceable_basis_refs" in result.error_codes


def test_malformed_source_or_evidence_refs_are_rejected() -> None:
    malformed_source = validate_interface_burden(
        _obligation(
            state="owned",
            owner_actor_ref="human:owner",
            source_refs=("artifact_version:av-001",),
        )
    )
    malformed_evidence = validate_interface_burden(
        _obligation(
            state="owned",
            owner_actor_ref="human:owner",
            source_refs=(SOURCE_REF,),
            evidence_refs=("plain-id",),
        )
    )

    assert "malformed_source_ref" in malformed_source.error_codes
    assert "malformed_evidence_ref" in malformed_evidence.error_codes


def test_require_interface_burden_conserved_raises_with_result() -> None:
    with pytest.raises(InterfaceBurdenPolicyError) as exc_info:
        require_interface_burden_conserved(None)

    assert exc_info.value.result.error_codes == ("missing_interface_burden_obligation",)


def test_unknown_interface_burden_state_is_not_conserved() -> None:
    result = validate_interface_burden(
        _obligation(
            state="closed",
            owner_actor_ref="human:owner",
            source_refs=(SOURCE_REF,),
        )
    )

    assert result.conserved is False
    assert result.error_codes == ("invalid_interface_burden_state",)
