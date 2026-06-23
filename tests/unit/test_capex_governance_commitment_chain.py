from __future__ import annotations

import pytest

from onetruth.capex_platform.governance_commitment_chain import (
    GOVERNANCE_COMMITMENT_CHAIN_ACTIVATION_POSTURE,
    GOVERNANCE_COMMITMENT_CHAIN_SCHEMA_VERSION,
    GovernanceCommitmentChainError,
    build_governance_commitment_chain_outputs,
    governance_commitment_chain_digest,
)


NOW = "2026-06-17T00:00:00Z"


def _corpus_baseline_outputs() -> dict[str, object]:
    source_refs = [
        "source_occurrence:so-commitment-primary",
        "source_occurrence:so-commitment-supporting",
    ]
    return {
        "schema_version": "capex.corpus_baseline.workflow_outputs.v1",
        "activation_posture": "planning_only_no_capex_activation",
        "workflow_id": "corpus-baseline-workflow-commitments",
        "tenant_id": "tenant-a",
        "domain_id": "domain-x",
        "project_id": "cp-commitments",
        "basis": {"packet_register_id": "packet-register-commitments"},
        "generated_artifacts": [
            {
                "file_name": "capex.packet_register.v1.json",
                "envelope": {
                    "source_refs": source_refs,
                },
            }
        ],
    }


def _observations() -> list[dict[str, object]]:
    return [
        {
            "commitment_id": "commitment-po-001",
            "commitment_type": "purchase_order",
            "commercial_status": "revised",
            "officialness_scope": "external",
            "source_refs": ["source_occurrence:so-commitment-primary"],
            "events": [
                {
                    "event_id": "po-001-order",
                    "event_type": "order",
                    "effective_at": "2026-01-10T00:00:00Z",
                    "revision_id": "rev-0",
                    "amount_cents": 125000,
                    "currency": "USD",
                },
                {
                    "event_id": "po-001-revision",
                    "event_type": "revision",
                    "effective_at": "2026-01-15T00:00:00Z",
                    "revision_id": "rev-1",
                    "amount_cents": 135000,
                    "currency": "USD",
                },
            ],
        },
        {
            "commitment_id": "commitment-settlement-001",
            "commitment_type": "settlement",
            "commercial_status": "settled",
            "officialness_scope": "mixed",
            "source_refs": ["source_occurrence:so-commitment-supporting"],
            "events": [
                {
                    "event_id": "settlement-001",
                    "event_type": "settlement",
                    "effective_at": "2026-02-01T00:00:00Z",
                    "amount_cents": 50000,
                    "currency": "USD",
                }
            ],
            "flags": [
                {
                    "flag_id": "flag-commercial-technical-boundary",
                    "flag_type": "commercial_not_technical_closure",
                    "severity": "high",
                }
            ],
        },
        {
            "commitment_id": "commitment-responsibility-001",
            "commitment_type": "responsibility",
            "commercial_status": "approved",
            "officialness_scope": "internal",
            "source_refs": ["source_occurrence:so-commitment-primary"],
            "responsibility_shift": "owner_interface_to_commercial_review",
            "events": [
                {
                    "event_id": "responsibility-shift-001",
                    "event_type": "responsibility_shift",
                    "effective_at": "2026-02-10T00:00:00Z",
                    "responsibility_from": "owner_interface",
                    "responsibility_to": "commercial_review",
                }
            ],
        },
    ]


def _outputs(**overrides: object) -> dict[str, object]:
    payload: dict[str, object] = {
        "corpus_baseline_outputs": _corpus_baseline_outputs(),
        "commitment_observations": _observations(),
        "workflow_id": "commitment-chain-workflow-001",
        "created_at": NOW,
        "created_by_actor_id": "human:pm",
        "created_by_actor_type": "human",
    }
    payload.update(overrides)
    return build_governance_commitment_chain_outputs(**payload)  # type: ignore[arg-type]


def test_governance_commitment_chain_preserves_revision_history_and_ledger() -> None:
    outputs = _outputs()

    assert outputs["schema_version"] == GOVERNANCE_COMMITMENT_CHAIN_SCHEMA_VERSION
    assert outputs["activation_posture"] == GOVERNANCE_COMMITMENT_CHAIN_ACTIVATION_POSTURE
    chain = outputs["commitment_chain"]  # type: ignore[index]
    ledger = outputs["expenditure_ledger"]  # type: ignore[index]
    po = next(row for row in chain["rows"] if row["commitment_id"] == "commitment-po-001")
    assert po["current_revision_id"] == "rev-1"
    assert [revision["revision_id"] for revision in po["revision_history"]] == [
        "rev-0",
        "rev-1",
    ]
    assert ledger["row_count"] == 3
    assert governance_commitment_chain_digest(outputs).startswith("sha256:")


def test_settlement_rows_do_not_close_technical_rca_and_raise_boundary_flag() -> None:
    outputs = _outputs()

    chain = outputs["commitment_chain"]  # type: ignore[index]
    flags = outputs["commitment_flags"]  # type: ignore[index]
    settlement = next(
        row for row in chain["rows"] if row["commitment_id"] == "commitment-settlement-001"
    )
    assert settlement["technical_rca_status"] == "not_closed_by_commercial_settlement"
    assert {
        flag["flag_type"] for flag in flags["rows"]
    } >= {
        "settlement_not_technical_rca",
        "commercial_not_technical_closure",
    }


def test_commitment_chain_distinguishes_commercial_and_responsibility_state() -> None:
    outputs = _outputs()

    chain = outputs["commitment_chain"]  # type: ignore[index]
    responsibility = next(
        row for row in chain["rows"] if row["commitment_id"] == "commitment-responsibility-001"
    )
    assert responsibility["commitment_type"] == "responsibility"
    assert responsibility["commercial_status"] == "approved"
    assert responsibility["officialness_scope"] == "internal"
    assert responsibility["responsibility_shift"] == "owner_interface_to_commercial_review"
    assert responsibility["official_truth"] is False


def test_commitment_chain_fails_closed_for_missing_basis_invalid_event_duplicate_and_scope() -> None:
    with pytest.raises(GovernanceCommitmentChainError) as missing_basis:
        _outputs(corpus_baseline_outputs={"schema_version": "wrong"})
    assert missing_basis.value.code == "commitment_requires_corpus_baseline_outputs"

    invalid_event = _observations()
    invalid_event[0] = {
        **invalid_event[0],
        "events": [
            {
                "event_id": "bad-event",
                "event_type": "technical_rca",
                "effective_at": "2026-01-10T00:00:00Z",
            }
        ],
    }
    with pytest.raises(GovernanceCommitmentChainError) as invalid_event_exc:
        _outputs(commitment_observations=invalid_event)
    assert invalid_event_exc.value.code == "commitment_event_type_invalid"

    duplicate = _observations()
    duplicate[1] = {**duplicate[1], "commitment_id": "commitment-po-001"}
    with pytest.raises(GovernanceCommitmentChainError) as duplicate_exc:
        _outputs(commitment_observations=duplicate)
    assert duplicate_exc.value.code == "commitment_duplicate_id"

    missing_source = _observations()
    missing_source[0] = {
        **missing_source[0],
        "source_refs": ["source_occurrence:missing"],
    }
    with pytest.raises(GovernanceCommitmentChainError) as source_exc:
        _outputs(commitment_observations=missing_source)
    assert source_exc.value.code == "commitment_source_ref_not_in_corpus_baseline"


def test_settlement_cannot_claim_technical_rca_closure() -> None:
    observations = _observations()
    observations[1] = {**observations[1], "closes_technical_rca": True}

    with pytest.raises(GovernanceCommitmentChainError) as exc_info:
        _outputs(commitment_observations=observations)

    assert exc_info.value.code == "settlement_must_not_close_technical_rca"


def test_commitment_chain_has_no_activation_or_official_truth_effects() -> None:
    outputs = _outputs()

    assert outputs["truth_effects"] == {
        "creates_workflow_run": False,
        "creates_approvals": False,
        "closes_technical_rca": False,
        "creates_reviewed_baseline": False,
        "writes_artifacts": False,
        "promotes_official_pointers": False,
        "activates_workflow_pack": False,
    }
    assert set(outputs["cannot_be_used_for"]) >= {  # type: ignore[arg-type]
        "authored_workflow_pack_activation",
        "workflow_run_creation",
        "public_route_activation",
        "frontend_route_activation",
        "approval_response_mutation",
        "technical_rca_closure",
        "official_pointer_creation",
        "capex_runtime_activation",
        "product_activation",
    }
