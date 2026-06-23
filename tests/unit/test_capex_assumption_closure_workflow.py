from __future__ import annotations

import pytest

from onetruth.capex_platform.assumption_closure_workflow import (
    ASSUMPTION_CLOSURE_ACTIVATION_POSTURE,
    ASSUMPTION_CLOSURE_MATRIX_SCHEMA_VERSION,
    ASSUMPTION_CLOSURE_WORKFLOW_SCHEMA_VERSION,
    ASSUMPTION_FLAGS_SCHEMA_VERSION,
    COUNTERPARTY_ASSUMPTION_REGISTER_SCHEMA_VERSION,
    AssumptionClosureWorkflowError,
    assumption_closure_workflow_digest,
    build_assumption_closure_workflow_outputs,
)


NOW = "2026-06-23T00:00:00Z"
SOURCE_REFS = [
    "source_occurrence:so-assumption-primary",
    "source_occurrence:so-assumption-supporting",
    "source_occurrence:so-assumption-waiver",
    "source_occurrence:so-assumption-contradiction",
    "source_occurrence:so-assumption-ai-draft",
]


def _corpus_baseline_outputs() -> dict[str, object]:
    return {
        "schema_version": "capex.corpus_baseline.workflow_outputs.v1",
        "activation_posture": "planning_only_no_capex_activation",
        "workflow_id": "corpus-baseline-assumption-001",
        "tenant_id": "tenant-a",
        "domain_id": "domain-x",
        "project_id": "cp-assumptions",
        "basis": {"packet_register_id": "packet-register-assumptions"},
        "generated_artifacts": [
            {
                "file_name": "capex.packet_register.v1.json",
                "envelope": {"source_refs": SOURCE_REFS},
            }
        ],
    }


def _governance_commitment_outputs() -> dict[str, object]:
    return {
        "schema_version": "capex.governance_commitment_chain.outputs.v1",
        "activation_posture": "planning_only_no_capex_activation",
        "workflow_id": "governance-commitment-assumption-001",
        "tenant_id": "tenant-a",
        "domain_id": "domain-x",
        "project_id": "cp-assumptions",
        "commitment_chain": {
            "schema_version": "capex.commitment_chain.v1",
            "rows": [
                {
                    "commitment_id": "commitment-001",
                    "source_refs": ["source_occurrence:so-assumption-primary"],
                }
            ],
            "row_count": 1,
            "snapshot_digest": "sha256:" + "1".zfill(64),
        },
        "expenditure_ledger": {
            "schema_version": "capex.expenditure_ledger.v1",
            "rows": [],
            "row_count": 0,
            "snapshot_digest": "sha256:" + "2".zfill(64),
        },
        "commitment_flags": {
            "schema_version": "capex.commitment_flags.v1",
            "rows": [],
            "row_count": 0,
            "snapshot_digest": "sha256:" + "3".zfill(64),
        },
    }


def _assumptions() -> list[dict[str, object]]:
    return [
        {
            "assumption_id": "assumption-supported",
            "counterparty_id": "supplier-alpha",
            "assumption_kind": "supplier",
            "assumption_summary": "Supplier lead-time basis recorded in sanitized metadata.",
            "owner_role": "commercial_owner",
            "source_refs": ["source_occurrence:so-assumption-primary"],
            "evidence_source_refs": ["source_occurrence:so-assumption-supporting"],
        },
        {
            "assumption_id": "assumption-waived",
            "counterparty_id": "supplier-beta",
            "assumption_kind": "commercial",
            "assumption_summary": "Commercial residual risk accepted by waiver.",
            "source_refs": ["source_occurrence:so-assumption-waiver"],
            "waiver_ids": ["waiver-commercial-risk"],
        },
        {
            "assumption_id": "assumption-missing",
            "counterparty_id": "supplier-gamma",
            "assumption_kind": "schedule",
            "assumption_summary": "Schedule dependency has no closure evidence yet.",
            "source_refs": ["source_occurrence:so-assumption-primary"],
        },
        {
            "assumption_id": "assumption-contradicted",
            "counterparty_id": "supplier-delta",
            "assumption_kind": "technical",
            "assumption_summary": "Technical assumption is contradicted by later metadata.",
            "source_refs": ["source_occurrence:so-assumption-primary"],
            "evidence_source_refs": ["source_occurrence:so-assumption-supporting"],
            "contradicted_by_source_refs": ["source_occurrence:so-assumption-contradiction"],
        },
        {
            "assumption_id": "assumption-ai-draft",
            "counterparty_id": "supplier-epsilon",
            "assumption_kind": "interface",
            "assumption_summary": "AI draft proposes closure but no reviewed evidence exists.",
            "source_refs": ["source_occurrence:so-assumption-primary"],
            "ai_draft_source_refs": ["source_occurrence:so-assumption-ai-draft"],
        },
    ]


def _outputs(**overrides: object) -> dict[str, object]:
    payload: dict[str, object] = {
        "corpus_baseline_outputs": _corpus_baseline_outputs(),
        "governance_commitment_outputs": _governance_commitment_outputs(),
        "assumption_observations": _assumptions(),
        "workflow_id": "assumption-closure-workflow-001",
        "created_at": NOW,
        "created_by_actor_id": "human:pm",
        "created_by_actor_type": "human",
    }
    payload.update(overrides)
    return build_assumption_closure_workflow_outputs(**payload)  # type: ignore[arg-type]


def test_assumption_closure_outputs_all_evidence_waiver_and_negative_states() -> None:
    outputs = _outputs()

    assert outputs["schema_version"] == ASSUMPTION_CLOSURE_WORKFLOW_SCHEMA_VERSION
    assert outputs["activation_posture"] == ASSUMPTION_CLOSURE_ACTIVATION_POSTURE
    assert outputs["basis"] == {
        "corpus_baseline_workflow_id": "corpus-baseline-assumption-001",
        "governance_commitment_chain_workflow_id": "governance-commitment-assumption-001",
        "packet_register_id": "packet-register-assumptions",
    }

    register = outputs["counterparty_assumption_register"]  # type: ignore[index]
    matrix = outputs["assumption_closure_matrix"]  # type: ignore[index]
    flags = outputs["assumption_flags"]  # type: ignore[index]
    assert register["schema_version"] == COUNTERPARTY_ASSUMPTION_REGISTER_SCHEMA_VERSION
    assert matrix["schema_version"] == ASSUMPTION_CLOSURE_MATRIX_SCHEMA_VERSION
    assert flags["schema_version"] == ASSUMPTION_FLAGS_SCHEMA_VERSION
    states = {row["assumption_id"]: row["closure_state"] for row in matrix["rows"]}  # type: ignore[index]
    results = {row["assumption_id"]: row["result"] for row in matrix["rows"]}  # type: ignore[index]
    assert states == {
        "assumption-ai-draft": "open_ai_draft_only",
        "assumption-contradicted": "blocked_contradicted",
        "assumption-missing": "open_missing_evidence",
        "assumption-supported": "closed_with_evidence",
        "assumption-waived": "closed_by_waiver",
    }
    assert results["assumption-supported"] == "pass"
    assert results["assumption-waived"] == "satisfied_by_waiver"
    assert results["assumption-contradicted"] == "fail"
    assert {
        flag["flag_type"] for flag in flags["rows"]  # type: ignore[index]
    } == {"ai_draft_cannot_close", "contradicted_evidence", "missing_evidence"}
    assert assumption_closure_workflow_digest(outputs).startswith("sha256:")


def test_assumption_closure_fails_closed_for_scope_source_and_duplicate_errors() -> None:
    wrong_scope = _governance_commitment_outputs() | {"project_id": "other-project"}
    with pytest.raises(AssumptionClosureWorkflowError) as scope_exc:
        _outputs(governance_commitment_outputs=wrong_scope)
    assert scope_exc.value.code == "assumption_workflow_scope_mismatch"

    missing_source = _assumptions()
    missing_source[0] = {
        **missing_source[0],
        "evidence_source_refs": ["source_occurrence:missing"],
    }
    with pytest.raises(AssumptionClosureWorkflowError) as source_exc:
        _outputs(assumption_observations=missing_source)
    assert source_exc.value.code == "assumption_source_ref_not_in_corpus_baseline"

    duplicate = _assumptions()
    duplicate[1] = {**duplicate[1], "assumption_id": "assumption-supported"}
    with pytest.raises(AssumptionClosureWorkflowError) as duplicate_exc:
        _outputs(assumption_observations=duplicate)
    assert duplicate_exc.value.code == "assumption_duplicate_id"


def test_assumption_closure_rejects_raw_paths_filenames_and_inline_text() -> None:
    raw_cases = [
        (_assumptions()[0] | {"assumption_summary": "/Users/pm/raw/source.pdf"}, "assumption_raw_value_forbidden"),
        (_assumptions()[0] | {"assumption_summary": "Real Client Budget.xlsx"}, "assumption_raw_value_forbidden"),
        (_assumptions()[0] | {"assumption_summary": "data:application/pdf;base64,AAAA"}, "assumption_inline_content_forbidden"),
        (_assumptions()[0] | {"assumption_text": "copied raw assumption wording"}, "assumption_raw_field_forbidden"),
    ]
    for assumption, expected_code in raw_cases:
        with pytest.raises(AssumptionClosureWorkflowError) as exc_info:
            _outputs(assumption_observations=[assumption])
        assert exc_info.value.code == expected_code


def test_assumption_closure_outputs_have_no_runtime_or_official_effects() -> None:
    outputs = _outputs()

    assert outputs["truth_effects"] == {
        "creates_workflow_run": False,
        "creates_approvals": False,
        "creates_closure_snapshots": False,
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
        "closure_snapshot_creation",
        "evidence_sufficiency_claim",
        "reviewed_baseline_creation",
        "official_pointer_creation",
        "capex_runtime_activation",
        "product_activation",
    }
