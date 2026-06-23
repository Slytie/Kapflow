from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from tests.helpers.repo_paths import REPO_ROOT


PROPOSAL_PATH = (
    REPO_ROOT
    / "docs/planning/capex_workflow_catalog/"
    "procurement_escalation_workflow_proposal.yaml"
)
PROJECT_INTAKE_PATH = (
    REPO_ROOT
    / "docs/planning/capex_workflow_catalog/"
    "project_intake_router_workflow.yaml"
)
GOVERNANCE_COMMITMENT_PATH = (
    REPO_ROOT
    / "docs/planning/capex_workflow_catalog/"
    "governance_commitment_chain_workflow.yaml"
)
ASSUMPTION_CLOSURE_PATH = (
    REPO_ROOT
    / "docs/planning/capex_workflow_catalog/"
    "assumption_closure_workflow.yaml"
)
OWNER_INTERFACE_PATH = (
    REPO_ROOT
    / "docs/planning/capex_workflow_catalog/"
    "owner_interface_resolution_workflow.yaml"
)
LIFECYCLE_STAGE_STATE_PATH = (
    REPO_ROOT
    / "docs/planning/capex_workflow_catalog/"
    "lifecycle_stage_state_workflow.yaml"
)
PROJECT_STATE_SNAPSHOT_PATH = (
    REPO_ROOT
    / "docs/planning/capex_workflow_catalog/"
    "project_state_snapshot_workflow.yaml"
)
RISK_CEO_TRANSPARENCY_PATH = (
    REPO_ROOT
    / "docs/planning/capex_workflow_catalog/"
    "risk_ceo_transparency_workflow.yaml"
)
RISK_STALE_CEO_COCKPIT_WORKPAGE_PATH = (
    REPO_ROOT
    / "docs/planning/capex_workpage_catalog/"
    "risk_stale_ceo_cockpit_workpage.yaml"
)
PROCUREMENT_FIELDS_THRESHOLDS_PATH = (
    REPO_ROOT
    / "docs/planning/capex_real_project_acceptance/"
    "PROCUREMENT_FIELDS_AND_EXECUTIVE_THRESHOLDS_CONTRACT.yaml"
)
RISK_SIGNAL_CONTRACT_PATH = (
    REPO_ROOT
    / "docs/planning/capex_transparency/"
    "RISK_SIGNAL_CONTRACT.yaml"
)
CEO_TRANSPARENCY_FRESHNESS_CONTRACT_PATH = (
    REPO_ROOT
    / "docs/planning/capex_transparency/"
    "CEO_TRANSPARENCY_SNAPSHOT_W8_FRESHNESS_CONTRACT.yaml"
)
ANNEX_B_PATH = (
    REPO_ROOT
    / "docs/planning/capex_real_project_acceptance/"
    "ANNEX_B_MANDATORY_FIELDS_AND_ESCALATION_THRESHOLDS_DRAFT.md"
)
TASK_0659_PATH = (
    REPO_ROOT
    / "codex/tasks/"
    "TASK-0659-define-procurement-fields-and-executive-escalation-thresholds.md"
)
RAW_CORPUS_MARKERS = (
    "projektordner",
    "reference project",
    "blind-validation",
    "alma ruma",
    "11639 otc",
)


def _proposal() -> dict[str, Any]:
    loaded = yaml.safe_load(PROPOSAL_PATH.read_text(encoding="utf-8"))
    assert isinstance(loaded, dict)
    return loaded


def _project_intake() -> dict[str, Any]:
    loaded = yaml.safe_load(PROJECT_INTAKE_PATH.read_text(encoding="utf-8"))
    assert isinstance(loaded, dict)
    return loaded


def _governance_commitment() -> dict[str, Any]:
    loaded = yaml.safe_load(GOVERNANCE_COMMITMENT_PATH.read_text(encoding="utf-8"))
    assert isinstance(loaded, dict)
    return loaded


def _assumption_closure() -> dict[str, Any]:
    loaded = yaml.safe_load(ASSUMPTION_CLOSURE_PATH.read_text(encoding="utf-8"))
    assert isinstance(loaded, dict)
    return loaded


def _owner_interface() -> dict[str, Any]:
    loaded = yaml.safe_load(OWNER_INTERFACE_PATH.read_text(encoding="utf-8"))
    assert isinstance(loaded, dict)
    return loaded


def _lifecycle_stage_state() -> dict[str, Any]:
    loaded = yaml.safe_load(LIFECYCLE_STAGE_STATE_PATH.read_text(encoding="utf-8"))
    assert isinstance(loaded, dict)
    return loaded


def _project_state_snapshot() -> dict[str, Any]:
    loaded = yaml.safe_load(PROJECT_STATE_SNAPSHOT_PATH.read_text(encoding="utf-8"))
    assert isinstance(loaded, dict)
    return loaded


def _risk_ceo_transparency() -> dict[str, Any]:
    loaded = yaml.safe_load(RISK_CEO_TRANSPARENCY_PATH.read_text(encoding="utf-8"))
    assert isinstance(loaded, dict)
    return loaded


def _risk_stale_ceo_cockpit_workpage() -> dict[str, Any]:
    loaded = yaml.safe_load(
        RISK_STALE_CEO_COCKPIT_WORKPAGE_PATH.read_text(encoding="utf-8")
    )
    assert isinstance(loaded, dict)
    return loaded


def _procurement_fields_thresholds() -> dict[str, Any]:
    loaded = yaml.safe_load(PROCUREMENT_FIELDS_THRESHOLDS_PATH.read_text(encoding="utf-8"))
    assert isinstance(loaded, dict)
    return loaded


def _risk_signal_contract() -> dict[str, Any]:
    loaded = yaml.safe_load(RISK_SIGNAL_CONTRACT_PATH.read_text(encoding="utf-8"))
    assert isinstance(loaded, dict)
    return loaded


def _ceo_freshness_contract() -> dict[str, Any]:
    loaded = yaml.safe_load(
        CEO_TRANSPARENCY_FRESHNESS_CONTRACT_PATH.read_text(encoding="utf-8")
    )
    assert isinstance(loaded, dict)
    return loaded


def _annex_field_ids() -> list[str]:
    text = ANNEX_B_PATH.read_text(encoding="utf-8")
    field_section = text.split("## Procurement / decision package minimum fields", 1)[1]
    field_section = field_section.split("## Escalation threshold families", 1)[0]
    return [
        line.removeprefix("- `").removesuffix("`").strip()
        for line in field_section.splitlines()
        if line.startswith("- `")
    ]


def _annex_threshold_families() -> list[str]:
    text = ANNEX_B_PATH.read_text(encoding="utf-8")
    threshold_section = text.split("## Escalation threshold families", 1)[1]
    return [
        line.removeprefix("- ").strip()
        for line in threshold_section.splitlines()
        if line.startswith("- ")
    ]


def test_procurement_escalation_proposal_is_planning_only_catalog_evidence() -> None:
    proposal = _proposal()

    assert proposal["schema_version"] == "capex.workflow_catalog.proposal.v1"
    assert proposal["proposal_id"] == "capex.procurement_escalation.workflow_proposal.v1"
    assert proposal["activation_posture"] == "planning_only_no_capex_activation"
    assert proposal["catalog_surface"] == "planning_only_capex_workflow_catalog"
    assert proposal["source_task_ref"] == "TASK-0571"
    assert proposal["gate_refs"] == ["NU-GATE-011"]
    assert set(proposal["depends_on_gate_refs"]) == {
        "SME-RP-G006",
        "SME-RP-G007",
        "SME-RP-G012",
    }
    assert "TASK-0659" not in proposal["remaining_activation_task_refs"]
    assert proposal["completed_policy_task_refs"] == ["TASK-0659"]
    assert (
        "docs/planning/capex_real_project_acceptance/"
        "PROCUREMENT_FIELDS_AND_EXECUTIVE_THRESHOLDS_CONTRACT.yaml"
    ) in proposal["policy_contract_refs"]
    assert set(proposal["cannot_be_used_for"]) >= {
        "capex_runtime_activation",
        "product_activation",
        "public_route_activation",
        "authored_workflow_pack_activation",
        "migration_approval",
        "raw_corpus_import",
        "threshold_signoff",
        "procurement_field_signoff",
    }


def test_procurement_escalation_proposal_uses_task_chain_not_workpage_status() -> None:
    proposal = _proposal()
    task_ids = [task["task_id"] for task in proposal["task_chain"]]

    assert task_ids == [
        "capex.procurement_decision_package.prepare",
        "capex.procurement_evidence.reconcile",
        "capex.commercial_variance.review",
        "capex.ceo_sponsor.escalation_decide",
        "capex.post_decision.conditions_track",
    ]
    assert {
        task["canonical_output"] for task in proposal["task_chain"]
    } <= set(proposal["canonical_substrate"]["allowed_outputs"])
    assert "approval" in {
        task["canonical_output"] for task in proposal["task_chain"]
    }
    assert set(proposal["canonical_substrate"]["forbidden_outputs"]) >= {
        "workpage_state",
        "generic_status_command",
        "external_status",
        "ai_output",
    }
    assert proposal["workpage_boundary"]["blocker_routing"] == (
        "canonical_task_chain_required"
    )
    assert set(proposal["workpage_boundary"]["workpages_must_not"]) >= {
        "set_official_project_status",
        "set_closure",
        "set_evidence_sufficiency",
        "set_commercial_status",
        "edit_procurement_status_as_truth",
        "bypass_task_chain",
        "promote_pointer_directly",
    }


def test_procurement_escalation_thresholds_reference_annex_without_signoff() -> None:
    proposal = _proposal()
    task_0659_text = TASK_0659_PATH.read_text(encoding="utf-8")

    assert proposal["escalation_gates"]["threshold_families"] == (
        _annex_threshold_families()
    )
    assert proposal["escalation_gates"]["threshold_value_policy"] == (
        "no_numeric_thresholds_invented_by_platform"
    )
    assert set(proposal["escalation_gates"]["requires_business_signoff_gate_refs"]) == {
        "SME-RP-G006",
        "SME-RP-G007",
    }
    assert "status: DONE" in task_0659_text
    assert "completed_at: 2026-06-23T00:00:00Z" in task_0659_text
    assert "TASK-0659" not in proposal["remaining_activation_task_refs"]


def test_procurement_fields_thresholds_contract_matches_annex_and_boundaries() -> None:
    contract = _procurement_fields_thresholds()

    assert contract["schema_version"] == "capex.real_project_acceptance.contract.v1"
    assert contract["contract_id"] == (
        "capex.procurement_fields_and_executive_thresholds.v1"
    )
    assert contract["owner_task"] == "TASK-0659"
    assert contract["activation_posture"] == "planning_only_no_capex_activation"
    assert contract["gate_refs"] == ["SME-RP-G006", "SME-RP-G007"]
    assert contract["procurement_required_field_register"]["field_ids"] == (
        _annex_field_ids()
    )
    assert contract["executive_escalation_threshold_family_register"][
        "threshold_families"
    ] == _annex_threshold_families()
    assert contract["executive_escalation_threshold_family_register"][
        "threshold_value_policy"
    ] == "no_numeric_thresholds_invented_by_platform"
    assert contract["executive_escalation_threshold_family_register"][
        "threshold_values_present"
    ] is False
    assert contract["commercial_observation_boundary"][
        "commercial_evidence_can_directly_close_dimensions"
    ] is False
    assert set(
        contract["commercial_observation_boundary"][
            "commercial_evidence_cannot_close_dimensions"
        ]
    ) == {"technical", "effectiveness", "handover", "assumption", "closure"}
    assert contract["truth_effects"] == {
        "creates_workflow_run": False,
        "creates_tasks": False,
        "creates_approvals": False,
        "creates_threshold_values": False,
        "activates_thresholds": False,
        "activates_procurement_workflow": False,
        "creates_erp_or_accounting_behavior": False,
        "creates_ceo_cockpit_state": False,
        "creates_official_project_state": False,
        "writes_artifacts": False,
        "promotes_official_pointers": False,
        "activates_workflow_pack": False,
    }


def test_procurement_escalation_proposal_contains_no_raw_corpus_markers() -> None:
    lowered = PROPOSAL_PATH.read_text(encoding="utf-8").lower()

    for marker in RAW_CORPUS_MARKERS:
        assert marker not in lowered


def test_project_intake_router_contract_is_planning_only_and_human_confirmed() -> None:
    proposal = _project_intake()

    assert proposal["schema_version"] == "capex.workflow_catalog.proposal.v1"
    assert proposal["proposal_id"] == "capex.project_intake_router.workflow.v1"
    assert proposal["source_task_ref"] == "TASK-0283"
    assert proposal["source_row"] == "WFLOW-001"
    assert proposal["activation_posture"] == "planning_only_no_capex_activation"
    assert proposal["acceptance_gates"] == ["AT-007", "NU-001"]
    assert proposal["entry_modes"] == [
        "new_project",
        "mid_project",
        "issue_escalation",
        "ceo_sponsor_entry",
    ]
    assert proposal["canonical_outputs"] == [
        "project_intake_profile",
        "module_activation_profile",
        "handoff_manifest",
    ]
    assert proposal["human_confirmation_policy"]["human_confirms"] is True
    assert proposal["human_confirmation_policy"]["ai_draft_only"] is True
    assert {
        "entry_mode",
        "module_activation",
        "reviewed_baseline",
        "official_project_truth",
    } <= set(proposal["human_confirmation_policy"]["ai_must_not_confirm"])


def test_project_intake_router_contract_sets_k12_and_activation_boundaries() -> None:
    proposal = _project_intake()

    assert proposal["mid_project_k12_policy"]["fixture_tier"] == (
        "k12_sanitized_expected_output"
    )
    assert proposal["mid_project_k12_policy"]["raw_k12_corpus_allowed"] is False
    assert proposal["routing_results"]["module_activation_profile"]["authority"] == (
        "none_planning_profile_only"
    )
    assert proposal["truth_effects"] == {
        "creates_workflow_run": False,
        "creates_source_occurrences": False,
        "writes_artifacts": False,
        "promotes_official_pointers": False,
        "activates_workflow_pack": False,
    }
    assert {
        "capex_runtime_activation",
        "product_activation",
        "public_route_activation",
        "authored_workflow_pack_activation",
        "raw_corpus_import",
        "source_occurrence_binding",
        "reviewed_baseline_creation",
        "module_activation_approval",
        "official_pointer_creation",
    } <= set(proposal["cannot_be_used_for"])


def test_project_intake_router_contract_contains_no_raw_corpus_markers() -> None:
    lowered = PROJECT_INTAKE_PATH.read_text(encoding="utf-8").lower()

    for marker in RAW_CORPUS_MARKERS:
        assert marker not in lowered


def test_governance_commitment_chain_contract_is_planning_only_catalog_evidence() -> None:
    proposal = _governance_commitment()

    assert proposal["schema_version"] == "capex.workflow_catalog.proposal.v1"
    assert proposal["proposal_id"] == "capex.governance_commitment_chain.workflow.v1"
    assert proposal["source_task_ref"] == "TASK-0286"
    assert proposal["source_row"] == "WFLOW-004"
    assert proposal["activation_posture"] == "planning_only_no_capex_activation"
    assert proposal["acceptance_gates"] == ["AT-002", "AT-COMMIT-001"]
    assert proposal["depends_on"]["repo_tasks"] == ["TASK-0284"]
    assert proposal["canonical_outputs"] == [
        "commitment_chain",
        "expenditure_ledger",
        "commitment_flags",
    ]


def test_governance_commitment_chain_contract_preserves_commercial_boundaries() -> None:
    proposal = _governance_commitment()

    assert proposal["commitment_chain"]["preserves_revision_history"] is True
    assert proposal["commitment_chain"]["duplicate_commitment_ids_allowed"] is False
    assert proposal["expenditure_ledger"]["commercial_status_not_technical_status"] is True
    assert proposal["commitment_flags"]["settlement_not_rca_flag_required"] is True
    assert proposal["officialness_policy"] == {
        "external_internal_distinction_required": True,
        "reviewed_metadata_is_pointer_truth": False,
        "approval_response_mutation_allowed": False,
        "commercial_settlement_closes_technical_rca": False,
    }
    assert proposal["truth_effects"] == {
        "creates_workflow_run": False,
        "creates_approvals": False,
        "closes_technical_rca": False,
        "creates_reviewed_baseline": False,
        "writes_artifacts": False,
        "promotes_official_pointers": False,
        "activates_workflow_pack": False,
    }
    assert {
        "authored_workflow_pack_activation",
        "raw_corpus_import",
        "approval_response_mutation",
        "technical_rca_closure",
        "reviewed_baseline_creation",
        "official_pointer_creation",
        "capex_runtime_activation",
        "product_activation",
    } <= set(proposal["cannot_be_used_for"])


def test_governance_commitment_chain_contract_contains_no_raw_corpus_markers() -> None:
    lowered = GOVERNANCE_COMMITMENT_PATH.read_text(encoding="utf-8").lower()

    for marker in RAW_CORPUS_MARKERS:
        assert marker not in lowered


def test_assumption_closure_contract_is_planning_only_catalog_evidence() -> None:
    proposal = _assumption_closure()

    assert proposal["schema_version"] == "capex.workflow_catalog.proposal.v1"
    assert proposal["proposal_id"] == "capex.assumption_closure.workflow.v1"
    assert proposal["source_task_ref"] == "TASK-0287"
    assert proposal["source_row"] == "WFLOW-005"
    assert proposal["activation_posture"] == "planning_only_no_capex_activation"
    assert proposal["acceptance_gates"] == ["AT-007", "NEG-CLOSE-001"]
    assert proposal["depends_on"]["repo_tasks"] == ["TASK-0284", "TASK-0286"]
    assert proposal["canonical_outputs"] == [
        "counterparty_assumption_register",
        "assumption_closure_matrix",
        "assumption_flags",
    ]


def test_assumption_closure_contract_records_negative_closure_policy() -> None:
    proposal = _assumption_closure()

    assert proposal["assumption_closure_matrix"]["states"] == [
        "closed_with_evidence",
        "closed_by_waiver",
        "open_missing_evidence",
        "blocked_contradicted",
        "open_ai_draft_only",
    ]
    assert proposal["assumption_closure_matrix"]["waiver_result"] == (
        "satisfied_by_waiver"
    )
    assert proposal["officialness_policy"] == {
        "ai_draft_closes_assumption": False,
        "missing_evidence_closes_assumption": False,
        "contradicted_evidence_closes_assumption": False,
        "waiver_is_pass": False,
        "reviewed_metadata_is_pointer_truth": False,
    }
    assert proposal["truth_effects"] == {
        "creates_workflow_run": False,
        "creates_approvals": False,
        "creates_closure_snapshots": False,
        "creates_reviewed_baseline": False,
        "writes_artifacts": False,
        "promotes_official_pointers": False,
        "activates_workflow_pack": False,
    }
    assert {
        "authored_workflow_pack_activation",
        "raw_corpus_import",
        "closure_snapshot_creation",
        "evidence_sufficiency_claim",
        "reviewed_baseline_creation",
        "official_pointer_creation",
        "capex_runtime_activation",
        "product_activation",
    } <= set(proposal["cannot_be_used_for"])


def test_assumption_closure_contract_contains_no_raw_corpus_markers() -> None:
    lowered = ASSUMPTION_CLOSURE_PATH.read_text(encoding="utf-8").lower()

    for marker in RAW_CORPUS_MARKERS:
        assert marker not in lowered


def test_owner_interface_contract_is_planning_only_catalog_evidence() -> None:
    proposal = _owner_interface()

    assert proposal["schema_version"] == "capex.workflow_catalog.proposal.v1"
    assert proposal["proposal_id"] == "capex.owner_interface_resolution.workflow.v1"
    assert proposal["source_task_ref"] == "TASK-0288"
    assert proposal["source_row"] == "WFLOW-006"
    assert proposal["activation_posture"] == "planning_only_no_capex_activation"
    assert proposal["acceptance_gates"] == ["AT-INTERFACE-001"]
    assert proposal["depends_on"]["repo_tasks"] == ["TASK-0284", "TASK-0287"]
    assert proposal["canonical_outputs"] == [
        "distributed_requirement_register",
        "interface_register",
        "owner_interface_flags",
    ]


def test_owner_interface_contract_preserves_responsibility_boundaries() -> None:
    proposal = _owner_interface()

    assert proposal["distributed_requirement_register"] == {
        "schema_version": "capex.distributed_requirement_register.v1",
        "duplicate_requirement_ids_allowed": False,
        "assumption_refs_must_be_known": True,
        "source_refs_required": True,
    }
    assert proposal["interface_register"]["states"] == [
        "resolved_with_evidence",
        "open_missing_responsibility",
        "open_missing_evidence",
        "blocked_conflict",
        "open_ai_draft_only",
        "open_waiver_only",
    ]
    assert proposal["officialness_policy"] == {
        "responsibility_can_disappear": False,
        "ai_draft_resolves_interface": False,
        "waiver_assigns_responsibility": False,
        "missing_evidence_resolves_interface": False,
        "conflicting_evidence_resolves_interface": False,
        "reviewed_metadata_is_pointer_truth": False,
    }
    assert proposal["truth_effects"] == {
        "creates_workflow_run": False,
        "creates_tasks": False,
        "creates_approvals": False,
        "creates_closure_snapshots": False,
        "creates_reviewed_baseline": False,
        "writes_artifacts": False,
        "promotes_official_pointers": False,
        "activates_workflow_pack": False,
    }
    assert {
        "authored_workflow_pack_activation",
        "raw_corpus_import",
        "responsibility_assignment_authority",
        "closure_snapshot_creation",
        "evidence_sufficiency_claim",
        "reviewed_baseline_creation",
        "official_pointer_creation",
        "capex_runtime_activation",
        "product_activation",
    } <= set(proposal["cannot_be_used_for"])


def test_owner_interface_contract_contains_no_raw_corpus_markers() -> None:
    lowered = OWNER_INTERFACE_PATH.read_text(encoding="utf-8").lower()

    for marker in RAW_CORPUS_MARKERS:
        assert marker not in lowered


def test_lifecycle_stage_state_contract_is_planning_only_catalog_evidence() -> None:
    proposal = _lifecycle_stage_state()

    assert proposal["schema_version"] == "capex.workflow_catalog.proposal.v1"
    assert proposal["proposal_id"] == "capex.lifecycle_stage_state.workflow.v1"
    assert proposal["source_task_ref"] == "TASK-0285"
    assert proposal["source_row"] == "WFLOW-003"
    assert proposal["activation_posture"] == "planning_only_no_capex_activation"
    assert proposal["acceptance_gates"] == ["NU-003"]
    assert proposal["depends_on"]["repo_tasks"] == ["TASK-0284"]
    assert proposal["canonical_outputs"] == [
        "lifecycle_stage_state",
        "stage_readiness_matrix",
        "lifecycle_navigation_flags",
    ]


def test_lifecycle_stage_state_contract_preserves_navigation_boundary() -> None:
    proposal = _lifecycle_stage_state()

    assert proposal["lifecycle_stage_state"] == {
        "schema_version": "capex.lifecycle_stage_state.v1",
        "derived_navigation_only": True,
        "official_truth": False,
        "duplicate_stage_ids_allowed": False,
        "stages": [
            "intake",
            "baseline",
            "planning_procurement",
            "execution_delivery",
            "commissioning_closeout",
            "post_closeout",
        ],
    }
    assert proposal["stage_readiness_matrix"]["ready_requires_evidence"] is True
    assert proposal["stage_readiness_matrix"]["ai_draft_can_make_ready"] is False
    assert proposal["officialness_policy"] == {
        "stage_is_truth": False,
        "stage_is_derived_navigation": True,
        "stage_advances_waterfall_gate": False,
        "ai_draft_sets_lifecycle_stage": False,
        "reviewed_metadata_is_pointer_truth": False,
    }
    assert proposal["truth_effects"] == {
        "creates_workflow_run": False,
        "creates_tasks": False,
        "creates_approvals": False,
        "creates_closure_snapshots": False,
        "creates_reviewed_baseline": False,
        "writes_artifacts": False,
        "promotes_official_pointers": False,
        "activates_workflow_pack": False,
    }
    assert {
        "authored_workflow_pack_activation",
        "raw_corpus_import",
        "official_stage_truth",
        "waterfall_gate_authority",
        "reviewed_baseline_creation",
        "closure_snapshot_creation",
        "evidence_sufficiency_claim",
        "official_pointer_creation",
        "capex_runtime_activation",
        "product_activation",
    } <= set(proposal["cannot_be_used_for"])


def test_lifecycle_stage_state_contract_contains_no_raw_corpus_markers() -> None:
    lowered = LIFECYCLE_STAGE_STATE_PATH.read_text(encoding="utf-8").lower()

    for marker in RAW_CORPUS_MARKERS:
        assert marker not in lowered


def test_project_state_snapshot_contract_is_planning_only_catalog_evidence() -> None:
    proposal = _project_state_snapshot()

    assert proposal["schema_version"] == "capex.workflow_catalog.proposal.v1"
    assert proposal["proposal_id"] == "capex.project_state_snapshot.workflow.v1"
    assert proposal["source_task_ref"] == "TASK-0289"
    assert proposal["source_row"] == "WFLOW-007"
    assert proposal["activation_posture"] == "planning_only_no_capex_activation"
    assert proposal["acceptance_gates"] == ["AT-001", "AT-010"]
    assert proposal["depends_on"]["repo_tasks"] == [
        "TASK-0285",
        "TASK-0286",
        "TASK-0287",
        "TASK-0288",
    ]
    assert proposal["canonical_outputs"] == [
        "project_state_snapshot",
        "project_closure_vector",
        "project_state_snapshot_flags",
    ]


def test_project_state_snapshot_contract_preserves_closure_and_pointer_boundaries() -> None:
    proposal = _project_state_snapshot()

    assert proposal["project_state_snapshot"] == {
        "schema_version": "capex.project_state_snapshot.v1",
        "reviewed_state_only": True,
        "official_truth": False,
        "duplicate_snapshot_ids_allowed": False,
        "includes_pointer_observations": True,
    }
    assert proposal["project_closure_vector"] == {
        "schema_version": "capex.project_closure_vector.v1",
        "components": [
            "lifecycle_stage_state",
            "governance_commitments",
            "assumption_closure",
            "owner_interface_resolution",
            "official_pointer_posture",
        ],
        "waiver_result": "waiver_recorded_not_pass",
        "conflict_result": "fail",
        "missing_evidence_result": "fail",
        "ai_draft_result": "fail",
    }
    assert proposal["officialness_policy"] == {
        "snapshot_is_official_project_truth": False,
        "snapshot_creates_closure": False,
        "ai_draft_closes_project_state": False,
        "waiver_is_pass": False,
        "missing_evidence_closes_project_state": False,
        "conflict_closes_project_state": False,
        "reviewed_metadata_is_pointer_truth": False,
    }
    assert proposal["truth_effects"] == {
        "creates_workflow_run": False,
        "creates_tasks": False,
        "creates_approvals": False,
        "creates_closure_snapshots": False,
        "creates_project_state": False,
        "creates_reviewed_baseline": False,
        "writes_artifacts": False,
        "promotes_official_pointers": False,
        "activates_workflow_pack": False,
    }
    assert {
        "authored_workflow_pack_activation",
        "raw_corpus_import",
        "official_project_state",
        "closure_snapshot_creation",
        "evidence_sufficiency_claim",
        "reviewed_baseline_creation",
        "official_pointer_creation",
        "capex_runtime_activation",
        "product_activation",
    } <= set(proposal["cannot_be_used_for"])


def test_project_state_snapshot_contract_contains_no_raw_corpus_markers() -> None:
    lowered = PROJECT_STATE_SNAPSHOT_PATH.read_text(encoding="utf-8").lower()

    for marker in RAW_CORPUS_MARKERS:
        assert marker not in lowered


def test_risk_ceo_transparency_contract_is_planning_only_catalog_evidence() -> None:
    proposal = _risk_ceo_transparency()

    assert proposal["schema_version"] == "capex.workflow_catalog.proposal.v1"
    assert proposal["proposal_id"] == "capex.risk_ceo_transparency.workflow.v1"
    assert proposal["source_task_ref"] == "TASK-0290"
    assert proposal["source_row"] == "WFLOW-008"
    assert proposal["activation_posture"] == "planning_only_no_capex_activation"
    assert proposal["acceptance_gates"] == ["AT-BRIDGE-008", "NU-010"]
    assert proposal["depends_on"]["repo_tasks"] == ["TASK-0277", "TASK-0289"]
    assert proposal["canonical_outputs"] == [
        "risk_state_snapshot",
        "ceo_transparency_snapshot",
        "risk_ceo_flags",
    ]


def test_risk_ceo_transparency_contract_preserves_forecast_and_truth_boundaries() -> None:
    proposal = _risk_ceo_transparency()

    assert proposal["risk_state_snapshot"] == {
        "schema_version": "capex.risk_state_snapshot.v1",
        "official_truth": False,
        "duplicate_risk_ids_allowed": False,
        "source_refs_must_be_in_project_state_snapshot": True,
        "project_state_component_refs_must_be_known": True,
    }
    assert proposal["ceo_transparency_snapshot"] == {
        "schema_version": "capex.ceo_transparency_snapshot.v1",
        "artifact_kind": "capex.ceo_transparency_snapshot",
        "file_name": "capex.ceo_transparency_snapshot.v1.json",
        "forecastability_grades": [
            "forecastable",
            "bounded_uncertainty",
            "not_forecastable",
        ],
        "drilldown_refs_required": True,
        "raw_ai_text_allowed": False,
        "false_precision_allowed_when_not_forecastable": False,
    }
    assert proposal["forecastability_policy"] == {
        "missing_evidence_maps_to": "not_forecastable",
        "conflict_maps_to": "not_forecastable",
        "stale_pointer_maps_to": "not_forecastable",
        "ai_draft_only_maps_to": "not_forecastable",
        "waiver_maps_to": "bounded_uncertainty",
        "deterministic_severity_mapping": True,
        "exact_date_cost_percent_without_forecastability_allowed": False,
    }
    assert proposal["officialness_policy"] == {
        "risk_state_snapshot_is_official_truth": False,
        "ceo_snapshot_is_official_project_truth": False,
        "ai_draft_resolves_risk": False,
        "external_status_sets_official_state": False,
        "waiver_silently_closes_risk": False,
        "missing_evidence_allows_forecast": False,
        "conflict_allows_forecast": False,
        "reviewed_metadata_is_pointer_truth": False,
    }
    assert proposal["truth_effects"] == {
        "creates_workflow_run": False,
        "creates_tasks": False,
        "creates_approvals": False,
        "creates_risk_engine_state": False,
        "creates_ceo_cockpit_state": False,
        "creates_closure_snapshots": False,
        "creates_official_project_state": False,
        "writes_artifacts": False,
        "promotes_official_pointers": False,
        "activates_workflow_pack": False,
    }
    assert {
        "runtime_risk_engine",
        "ceo_cockpit",
        "public_api_route",
        "frontend_route",
        "migration",
        "event_registry_change",
        "RiskSignal_runtime_contract",
        "W8_ceo_transparency_freshness_contract",
    } <= set(proposal["not_implemented_in_this_task"])
    assert {
        "authored_workflow_pack_activation",
        "raw_corpus_import",
        "ceo_cockpit_activation",
        "runtime_risk_engine_activation",
        "closure_snapshot_creation",
        "official_project_state",
        "official_pointer_creation",
        "capex_runtime_activation",
        "product_activation",
    } <= set(proposal["cannot_be_used_for"])


def test_risk_ceo_transparency_contract_contains_no_raw_corpus_markers() -> None:
    lowered = RISK_CEO_TRANSPARENCY_PATH.read_text(encoding="utf-8").lower()

    for marker in RAW_CORPUS_MARKERS:
        assert marker not in lowered


def test_risk_signal_contract_is_planning_only_transparency_evidence() -> None:
    contract = _risk_signal_contract()

    assert contract["schema_version"] == "capex.transparency.contract.v1"
    assert contract["contract_id"] == "capex.risk_signal.v1"
    assert contract["owner_task"] == "TASK-0539"
    assert contract["source_row"] == "ARCH-W8-S03"
    assert contract["activation_posture"] == "planning_only_no_capex_activation"
    assert contract["depends_on"]["repo_tasks"] == ["TASK-0290"]
    assert contract["required_basis"]["schema_version"] == (
        "capex.risk_ceo_transparency.workflow_outputs.v1"
    )
    assert contract["canonical_outputs"] == ["risk_signal_register"]
    assert contract["risk_signal_register"]["schema_version"] == (
        "capex.risk_signal_register.v1"
    )
    assert contract["risk_signal_register"][
        "duplicate_risk_signal_ids_allowed"
    ] is False
    assert contract["risk_signal_register"][
        "risk_refs_must_be_in_risk_ceo_outputs"
    ] is True
    assert contract["policy_version"] == {
        "required": True,
        "row_policy_must_match_register_policy": True,
    }
    assert contract["truth_effects"] == {
        "creates_workflow_run": False,
        "creates_tasks": False,
        "creates_approvals": False,
        "creates_risk_engine_state": False,
        "creates_risk_signal_runtime_state": False,
        "creates_ceo_cockpit_state": False,
        "creates_closure_snapshots": False,
        "creates_official_project_state": False,
        "writes_artifacts": False,
        "promotes_official_pointers": False,
        "activates_workflow_pack": False,
    }
    assert {
        "runtime_risk_engine",
        "risk_signal_runtime_table",
        "ceo_cockpit",
        "public_api_route",
        "frontend_route",
        "migration",
        "event_registry_change",
    } <= set(contract["not_implemented_in_this_task"])
    assert {
        "raw_corpus_import",
        "runtime_risk_engine_activation",
        "ceo_cockpit_activation",
        "official_project_state",
        "official_pointer_creation",
        "capex_runtime_activation",
        "product_activation",
    } <= set(contract["cannot_be_used_for"])


def test_ceo_freshness_transparency_contract_preserves_w8_boundaries() -> None:
    contract = _ceo_freshness_contract()

    assert contract["schema_version"] == "capex.transparency.contract.v1"
    assert contract["contract_id"] == (
        "capex.ceo_transparency_snapshot_freshness.v1"
    )
    assert contract["owner_task"] == "TASK-0540"
    assert contract["source_row"] == "ARCH-W8-S04"
    assert contract["activation_posture"] == "planning_only_no_capex_activation"
    assert contract["required_basis"] == {
        "ceo_snapshot_schema_version": "capex.ceo_transparency_snapshot.v1",
        "risk_ceo_workflow_schema_version": (
            "capex.risk_ceo_transparency.workflow_outputs.v1"
        ),
        "optional_risk_signal_outputs_schema_version": "capex.risk_signal.outputs.v1",
    }
    assert contract["ceo_transparency_snapshot_freshness"][
        "schema_version"
    ] == "capex.ceo_transparency_snapshot_freshness.v1"
    assert contract["validation_policy"] == {
        "same_tenant_domain_project_required": True,
        "source_refs_must_be_in_ceo_snapshot": True,
        "input_digests_must_use_sha256_prefix": True,
        "risk_signal_refs_must_be_known_when_present": True,
        "duplicate_caveat_propagation_ids_allowed": False,
        "deterministic_ordering_required": True,
    }
    assert contract["truth_effects"] == {
        "creates_workflow_run": False,
        "creates_tasks": False,
        "creates_approvals": False,
        "creates_risk_engine_state": False,
        "creates_ceo_cockpit_state": False,
        "creates_closure_snapshots": False,
        "creates_official_project_state": False,
        "writes_artifacts": False,
        "promotes_official_pointers": False,
        "activates_workflow_pack": False,
    }
    assert "replacement_of_capex_ceo_transparency_snapshot_v1" in contract[
        "not_implemented_in_this_task"
    ]


def test_risk_stale_ceo_cockpit_workpage_is_planning_only_catalog_evidence() -> None:
    proposal = _risk_stale_ceo_cockpit_workpage()

    assert proposal["schema_version"] == "capex.workpage_catalog.proposal.v1"
    assert proposal["proposal_id"] == "capex.risk_stale_ceo_cockpit.workpage.v1"
    assert proposal["source_task_ref"] == "TASK-0299"
    assert proposal["source_row"] == "WP-009"
    assert proposal["activation_posture"] == "planning_only_no_capex_activation"
    assert proposal["depends_on"]["repo_tasks"] == ["TASK-0290"]
    assert proposal["required_basis"]["schema_version"] == (
        "capex.risk_ceo_transparency.workflow_outputs.v1"
    )
    assert proposal["canonical_outputs"] == [
        "risk_cards",
        "stale_blocker_cards",
        "ceo_management_action_cards",
        "source_drilldown_refs",
        "forecastability_display",
    ]


def test_risk_stale_ceo_cockpit_workpage_preserves_display_truth_boundaries() -> None:
    proposal = _risk_stale_ceo_cockpit_workpage()

    assert proposal["risk_cards"] == {
        "schema_version": "capex.risk_cockpit.risk_cards.v1",
        "source_refs_visible": True,
        "drilldown_refs_visible": True,
        "duplicate_card_ids_allowed": False,
        "official_truth": False,
    }
    assert proposal["stale_blocker_cards"]["stale_pointer_flag_required"] is True
    assert proposal["stale_blocker_cards"]["missing_evidence_flag_required"] is True
    assert proposal["stale_blocker_cards"]["evidence_conflict_flag_required"] is True
    assert proposal["stale_blocker_cards"]["ai_draft_only_flag_required"] is True
    assert proposal["forecastability_display"][
        "false_precision_allowed_when_not_forecastable"
    ] is False
    assert proposal["truth_effects"] == {
        "creates_public_route": False,
        "creates_frontend_route": False,
        "creates_ceo_cockpit_state": False,
        "creates_risk_engine_state": False,
        "creates_workflow_run": False,
        "creates_tasks": False,
        "creates_approvals": False,
        "creates_closure_snapshots": False,
        "creates_official_project_state": False,
        "writes_artifacts": False,
        "promotes_official_pointers": False,
        "activates_workflow_pack": False,
    }
    assert {
        "public_capex_route",
        "frontend_route",
        "ceo_cockpit_runtime",
        "runtime_risk_engine",
        "authored_workflow_pack",
        "migration",
        "event_registry_change",
    } <= set(proposal["not_implemented_in_this_task"])
    assert {
        "capex_runtime_activation",
        "product_activation",
        "public_route_activation",
        "frontend_route_activation",
        "ceo_cockpit_activation",
        "runtime_risk_engine_activation",
        "official_project_state",
        "official_pointer_creation",
    } <= set(proposal["cannot_be_used_for"])


def test_risk_stale_ceo_cockpit_and_procurement_contracts_have_no_raw_markers() -> None:
    for path in (
        RISK_STALE_CEO_COCKPIT_WORKPAGE_PATH,
        PROCUREMENT_FIELDS_THRESHOLDS_PATH,
        RISK_SIGNAL_CONTRACT_PATH,
        CEO_TRANSPARENCY_FRESHNESS_CONTRACT_PATH,
    ):
        lowered = path.read_text(encoding="utf-8").lower()
        for marker in RAW_CORPUS_MARKERS:
            assert marker not in lowered
