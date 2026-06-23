from __future__ import annotations

import pytest

from onetruth.capex_platform.owner_interface_resolution_workflow import (
    DISTRIBUTED_REQUIREMENT_REGISTER_SCHEMA_VERSION,
    INTERFACE_REGISTER_SCHEMA_VERSION,
    OWNER_INTERFACE_FLAGS_SCHEMA_VERSION,
    OWNER_INTERFACE_RESOLUTION_ACTIVATION_POSTURE,
    OWNER_INTERFACE_RESOLUTION_WORKFLOW_SCHEMA_VERSION,
    OwnerInterfaceResolutionWorkflowError,
    build_owner_interface_resolution_workflow_outputs,
    owner_interface_resolution_workflow_digest,
)


NOW = "2026-06-23T00:00:00Z"
SOURCE_REFS = [
    "source_occurrence:so-interface-primary",
    "source_occurrence:so-interface-evidence",
    "source_occurrence:so-interface-missing",
    "source_occurrence:so-interface-conflict",
    "source_occurrence:so-interface-ai-draft",
    "source_occurrence:so-interface-waiver",
]


def _corpus_baseline_outputs() -> dict[str, object]:
    return {
        "schema_version": "capex.corpus_baseline.workflow_outputs.v1",
        "activation_posture": "planning_only_no_capex_activation",
        "workflow_id": "corpus-baseline-interface-001",
        "tenant_id": "tenant-a",
        "domain_id": "domain-x",
        "project_id": "cp-interface",
        "basis": {"packet_register_id": "packet-register-interface"},
        "generated_artifacts": [
            {
                "file_name": "capex.packet_register.v1.json",
                "envelope": {"source_refs": SOURCE_REFS},
            }
        ],
    }


def _assumption_closure_outputs() -> dict[str, object]:
    return {
        "schema_version": "capex.assumption_closure.workflow_outputs.v1",
        "activation_posture": "planning_only_no_capex_activation",
        "workflow_id": "assumption-closure-interface-001",
        "tenant_id": "tenant-a",
        "domain_id": "domain-x",
        "project_id": "cp-interface",
        "basis": {"packet_register_id": "packet-register-interface"},
        "counterparty_assumption_register": {
            "schema_version": "capex.counterparty_assumption_register.v1",
            "rows": [
                {
                    "assumption_id": "assumption-owner-access",
                    "counterparty_id": "owner-alpha",
                    "source_refs": ["source_occurrence:so-interface-primary"],
                },
                {
                    "assumption_id": "assumption-supplier-delivery",
                    "counterparty_id": "supplier-beta",
                    "source_refs": ["source_occurrence:so-interface-evidence"],
                },
            ],
            "row_count": 2,
        },
        "assumption_closure_matrix": {
            "schema_version": "capex.assumption_closure_matrix.v1",
            "rows": [
                {
                    "assumption_id": "assumption-owner-access",
                    "source_refs": ["source_occurrence:so-interface-primary"],
                    "evidence_source_refs": ["source_occurrence:so-interface-evidence"],
                }
            ],
            "row_count": 1,
        },
        "assumption_flags": {
            "schema_version": "capex.assumption_flags.v1",
            "rows": [],
            "row_count": 0,
        },
    }


def _observations() -> list[dict[str, object]]:
    return [
        {
            "requirement_id": "req-owner-access",
            "interface_id": "interface-owner-access",
            "requirement_kind": "owner_decision",
            "interface_kind": "owner",
            "requirement_summary": "Owner access responsibility is recorded in sanitized metadata.",
            "owner_party_id": "owner-alpha",
            "site_party_id": "site-main",
            "supplier_party_id": "supplier-beta",
            "responsible_party_id": "owner-alpha",
            "assumption_refs": ["assumption:assumption-owner-access"],
            "source_refs": ["source_occurrence:so-interface-primary"],
            "evidence_source_refs": ["source_occurrence:so-interface-evidence"],
        },
        {
            "requirement_id": "req-missing-responsibility",
            "interface_id": "interface-missing-responsibility",
            "requirement_kind": "site_access",
            "interface_kind": "site",
            "requirement_summary": "Site access has no responsible owner yet.",
            "source_refs": ["source_occurrence:so-interface-missing"],
        },
        {
            "requirement_id": "req-conflicting",
            "interface_id": "interface-conflicting",
            "requirement_kind": "supplier_deliverable",
            "interface_kind": "supplier",
            "requirement_summary": "Supplier deliverable has conflicting responsibility metadata.",
            "responsible_party_id": "supplier-beta",
            "conflicting_responsible_party_ids": ["owner-alpha"],
            "source_refs": ["source_occurrence:so-interface-primary"],
            "conflict_source_refs": ["source_occurrence:so-interface-conflict"],
        },
        {
            "requirement_id": "req-ai-draft",
            "interface_id": "interface-ai-draft",
            "requirement_kind": "technical_interface",
            "interface_kind": "contractor",
            "requirement_summary": "AI draft proposes a responsible party without reviewed evidence.",
            "responsible_party_id": "contractor-gamma",
            "source_refs": ["source_occurrence:so-interface-ai-draft"],
            "ai_draft_source_refs": ["source_occurrence:so-interface-ai-draft"],
        },
        {
            "requirement_id": "req-waiver",
            "interface_id": "interface-waiver",
            "requirement_kind": "scope",
            "interface_kind": "internal",
            "requirement_summary": "Waiver is recorded but does not assign responsibility.",
            "responsible_party_id": "internal-delta",
            "waiver_ids": ["waiver-interface-risk"],
            "source_refs": ["source_occurrence:so-interface-waiver"],
        },
    ]


def _outputs(**overrides: object) -> dict[str, object]:
    payload: dict[str, object] = {
        "corpus_baseline_outputs": _corpus_baseline_outputs(),
        "assumption_closure_outputs": _assumption_closure_outputs(),
        "interface_observations": _observations(),
        "workflow_id": "owner-interface-workflow-001",
        "created_at": NOW,
        "created_by_actor_id": "human:pm",
        "created_by_actor_type": "human",
    }
    payload.update(overrides)
    return build_owner_interface_resolution_workflow_outputs(**payload)  # type: ignore[arg-type]


def test_owner_interface_outputs_resolution_states_and_flags() -> None:
    outputs = _outputs()

    assert outputs["schema_version"] == OWNER_INTERFACE_RESOLUTION_WORKFLOW_SCHEMA_VERSION
    assert outputs["activation_posture"] == OWNER_INTERFACE_RESOLUTION_ACTIVATION_POSTURE
    assert outputs["basis"] == {
        "corpus_baseline_workflow_id": "corpus-baseline-interface-001",
        "assumption_closure_workflow_id": "assumption-closure-interface-001",
        "packet_register_id": "packet-register-interface",
    }
    requirements = outputs["distributed_requirement_register"]  # type: ignore[index]
    interfaces = outputs["interface_register"]  # type: ignore[index]
    flags = outputs["owner_interface_flags"]  # type: ignore[index]
    assert requirements["schema_version"] == DISTRIBUTED_REQUIREMENT_REGISTER_SCHEMA_VERSION
    assert interfaces["schema_version"] == INTERFACE_REGISTER_SCHEMA_VERSION
    assert flags["schema_version"] == OWNER_INTERFACE_FLAGS_SCHEMA_VERSION
    states = {row["interface_id"]: row["resolution_state"] for row in interfaces["rows"]}  # type: ignore[index]
    assert states == {
        "interface-ai-draft": "open_ai_draft_only",
        "interface-conflicting": "blocked_conflict",
        "interface-missing-responsibility": "open_missing_responsibility",
        "interface-owner-access": "resolved_with_evidence",
        "interface-waiver": "open_waiver_only",
    }
    assert {
        flag["flag_type"] for flag in flags["rows"]  # type: ignore[index]
    } == {
        "ai_draft_cannot_resolve",
        "conflicting_responsibility",
        "missing_responsibility",
        "waiver_not_responsibility",
    }
    assert owner_interface_resolution_workflow_digest(outputs).startswith("sha256:")


def test_owner_interface_fails_closed_for_scope_source_assumption_and_duplicates() -> None:
    wrong_scope = _assumption_closure_outputs() | {"project_id": "other-project"}
    with pytest.raises(OwnerInterfaceResolutionWorkflowError) as scope_exc:
        _outputs(assumption_closure_outputs=wrong_scope)
    assert scope_exc.value.code == "owner_interface_scope_mismatch"

    missing_source = _observations()
    missing_source[0] = {
        **missing_source[0],
        "evidence_source_refs": ["source_occurrence:missing"],
    }
    with pytest.raises(OwnerInterfaceResolutionWorkflowError) as source_exc:
        _outputs(interface_observations=missing_source)
    assert source_exc.value.code == "owner_interface_source_ref_not_in_corpus_baseline"

    unknown_assumption = _observations()
    unknown_assumption[0] = {
        **unknown_assumption[0],
        "assumption_refs": ["assumption:missing"],
    }
    with pytest.raises(OwnerInterfaceResolutionWorkflowError) as assumption_exc:
        _outputs(interface_observations=unknown_assumption)
    assert assumption_exc.value.code == "owner_interface_unknown_assumption_ref"

    duplicate = _observations()
    duplicate[1] = {**duplicate[1], "requirement_id": "req-owner-access"}
    with pytest.raises(OwnerInterfaceResolutionWorkflowError) as duplicate_exc:
        _outputs(interface_observations=duplicate)
    assert duplicate_exc.value.code == "owner_interface_duplicate_requirement_id"


def test_owner_interface_rejects_responsibility_disappearance() -> None:
    disappearing = _observations()
    disappearing[1] = {
        **disappearing[1],
        "previous_responsible_party_id": "owner-alpha",
    }
    with pytest.raises(OwnerInterfaceResolutionWorkflowError) as exc_info:
        _outputs(interface_observations=disappearing)
    assert exc_info.value.code == "owner_interface_responsibility_disappeared"


def test_owner_interface_rejects_raw_paths_filenames_and_inline_text() -> None:
    raw_cases = [
        (_observations()[0] | {"requirement_summary": "/Users/pm/raw/source.pdf"}, "owner_interface_raw_value_forbidden"),
        (_observations()[0] | {"requirement_summary": "Real Client Budget.xlsx"}, "owner_interface_raw_value_forbidden"),
        (_observations()[0] | {"requirement_summary": "data:application/pdf;base64,AAAA"}, "owner_interface_inline_content_forbidden"),
        (_observations()[0] | {"requirement_text": "copied raw requirement wording"}, "owner_interface_raw_field_forbidden"),
    ]
    for observation, expected_code in raw_cases:
        with pytest.raises(OwnerInterfaceResolutionWorkflowError) as exc_info:
            _outputs(interface_observations=[observation])
        assert exc_info.value.code == expected_code


def test_owner_interface_outputs_have_no_runtime_or_official_effects() -> None:
    outputs = _outputs()

    assert outputs["truth_effects"] == {
        "creates_workflow_run": False,
        "creates_tasks": False,
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
        "responsibility_assignment_authority",
        "closure_snapshot_creation",
        "evidence_sufficiency_claim",
        "reviewed_baseline_creation",
        "official_pointer_creation",
        "capex_runtime_activation",
        "product_activation",
    }
