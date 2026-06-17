from __future__ import annotations

import re
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[2]
REGISTER_DIR = ROOT / "docs/planning/capex_real_project_acceptance"
REGISTER_PATH = REGISTER_DIR / "SME_RP_ACCEPTANCE_REGISTER.yaml"
SIGN_OFF_PATH = REGISTER_DIR / "SME_RP_APPROVAL_WITH_CONDITIONS_SIGN_OFF.md"
SCOPE_CONTRACT_PATH = ROOT / "docs/architecture/CAPEX_SCOPE_HIERARCHY_CONTRACT.md"
RACI_CONTRACT_PATH = ROOT / "docs/architecture/CAPEX_RACI_ROLE_PERMISSION_MATRIX.md"
EVIDENCE_CONTRACT_PATH = (
    ROOT / "docs/architecture/CAPEX_EVIDENCE_STATUS_TRANSITION_CONTRACT.md"
)
SOURCE_CONTEXT_CONTRACT_PATH = (
    ROOT / "docs/architecture/CAPEX_SOURCE_OCCURRENCE_CONTEXT_AND_TRUST_CONTRACT.md"
)
WORKPAGE_GENERATION_CONTRACT_PATH = (
    ROOT / "docs/architecture/CAPEX_WORKPAGE_TO_TASK_GENERATION_CONTRACT.md"
)
PROCUREMENT_ESCALATION_PROPOSAL_PATH = (
    ROOT
    / "docs/planning/capex_workflow_catalog/"
    "procurement_escalation_workflow_proposal.yaml"
)
TASK_DIR = ROOT / "codex/tasks"
FRONTMATTER_RE = re.compile(r"\A---\n(?P<body>.*?)\n---\n", re.DOTALL)

EXPECTED_RACI_ROLES = [
    "Project Manager",
    "Engineering SME",
    "Maintenance",
    "Production / Operator",
    "EHS",
    "Procurement",
    "Controlling",
    "Plant Management",
    "Technical Director",
    "CEO / Sponsor",
    "Supplier",
]
EXPECTED_RACI_ACTIONS = [
    "create_source_occurrence",
    "review_evidence_link",
    "approve_decision_package",
    "adopt_project_state",
    "close_closure_dimension",
    "reopen_closure_dimension",
    "waive_evidence_or_residual_risk",
    "escalate_to_ceo_sponsor",
]
EXPECTED_EVIDENCE_STATUSES = [
    "proposed",
    "under_review",
    "valid",
    "partly_valid",
    "contradictory",
    "obsolete",
    "invalid",
    "insufficient",
    "accepted_with_residual_risk",
]
EXPECTED_SOURCE_ORIGIN_MODES = [
    "primary",
    "derivative",
    "generated",
    "external",
    "imported",
]
EXPECTED_SOURCE_TRUST_MODES = [
    "observed",
    "referenced",
    "imported",
    "reviewed",
    "officially_adopted",
]
EXPECTED_WORKPAGE_BLOCKER_TYPES = [
    "missing_evidence",
    "missing_responsibility",
    "revision_required",
    "commercial_cost_gap",
    "safety_readiness_gap",
    "contradictory_evidence",
]
EXPECTED_WORKPAGE_CANONICAL_OUTPUTS = [
    "task",
    "flag",
    "approval",
    "artifact_delta",
    "event",
    "pointer_request",
]
EXPECTED_WORKPAGE_REQUIRED_GUARDS = [
    "stale_basis_check",
    "source_binding",
    "actor_authority",
    "audit_evidence",
]


def _load_register() -> dict:
    return yaml.safe_load(REGISTER_PATH.read_text(encoding="utf-8"))


def _task_frontmatter(path: Path) -> dict:
    match = FRONTMATTER_RE.match(path.read_text(encoding="utf-8"))
    assert match is not None, f"{path} is missing task frontmatter"
    return yaml.safe_load(match.group("body"))


def _task_file(task_id: str) -> Path:
    matches = sorted(TASK_DIR.glob(f"{task_id}-*.md"))
    assert len(matches) == 1, f"Expected exactly one task file for {task_id}"
    return matches[0]


def _assert_no_legacy_gate_prefix(paths: list[Path]) -> None:
    legacy_gate_prefix = "SME-K12" + "-G"
    offenders = [
        str(path.relative_to(ROOT))
        for path in paths
        if legacy_gate_prefix in path.read_text(encoding="utf-8")
    ]
    assert offenders == []


def test_sme_rp_register_uses_generalized_gate_namespace() -> None:
    register = _load_register()
    gate_ids = [gate["gate_id"] for gate in register["acceptance_gates"]]
    legacy_annex_dir = ROOT / "docs/planning" / ("capex_sme" + "_k12_annexes")

    assert REGISTER_DIR.exists()
    assert not legacy_annex_dir.exists()
    assert register["namespace"] == "SME-RP"
    assert gate_ids == [f"SME-RP-G{index:03d}" for index in range(1, 14)]
    assert register["source_provenance"]["source_namespace"] == "SME-K12"
    assert register["source_provenance"]["repo_namespace"] == "SME-RP"

    paths_to_scan = [
        *REGISTER_DIR.glob("*"),
        *TASK_DIR.glob("TASK-06*.md"),
        *(ROOT / "docs/planning/epics").glob("EPIC-1*.md"),
        *(ROOT / "codex/context").glob("EPIC-1*.md"),
        SCOPE_CONTRACT_PATH,
        RACI_CONTRACT_PATH,
        EVIDENCE_CONTRACT_PATH,
        SOURCE_CONTEXT_CONTRACT_PATH,
        WORKPAGE_GENERATION_CONTRACT_PATH,
        ROOT / "docs/status/CURRENT_FOCUS.md",
        ROOT / "docs/status/DECISIONS_SINCE_LAST.md",
    ]
    _assert_no_legacy_gate_prefix(paths_to_scan)


def test_sme_rp_task_remap_is_complete_and_collision_free() -> None:
    register = _load_register()
    remap = register["task_remap"]
    repo_task_ids = [row["repo_task_id"] for row in remap]
    source_task_ids = [row["source_task_id"] for row in remap]

    assert repo_task_ids == [f"TASK-{index:04d}" for index in range(648, 665)]
    assert source_task_ids == [f"TASK-{index:04d}" for index in range(625, 642)]
    assert len(repo_task_ids) == len(set(repo_task_ids)) == 17
    assert len(source_task_ids) == len(set(source_task_ids)) == 17

    all_task_ids: dict[str, Path] = {}
    for path in TASK_DIR.glob("TASK-*.md"):
        frontmatter = _task_frontmatter(path)
        task_id = frontmatter["id"]
        assert task_id not in all_task_ids, (
            f"{task_id} appears in both {all_task_ids[task_id]} and {path}"
        )
        all_task_ids[task_id] = path

    for row in remap:
        path = _task_file(row["repo_task_id"])
        frontmatter = _task_frontmatter(path)
        text = path.read_text(encoding="utf-8")

        assert all_task_ids[row["repo_task_id"]] == path
        assert frontmatter["epic"] == row["target_epic"]
        assert f"Source task ID: `{row['source_task_id']}`" in text
        assert "Source namespace: `SME-K12`" in text
        assert "Repo namespace: `SME-RP`" in text
        for gate_ref in row["gate_refs"]:
            assert gate_ref in text


def test_k12_cases_are_fixture_case_ids_not_acceptance_namespace() -> None:
    register = _load_register()
    fixture_case_ids = [case["fixture_case_id"] for case in register["fixture_cases"]]
    gate_ids = [gate["gate_id"] for gate in register["acceptance_gates"]]
    annex_c_text = (
        REGISTER_DIR / "ANNEX_C_REAL_PROJECT_BINDING_ACCEPTANCE_CATALOGUE.md"
    ).read_text(encoding="utf-8")

    assert fixture_case_ids == [f"K12-T{index}" for index in range(1, 11)]
    assert not any(gate_id.startswith("K12") for gate_id in gate_ids)
    assert "Real-Project Binding Acceptance Catalogue" in annex_c_text
    assert "fixture-case IDs" in annex_c_text
    assert "top-level acceptance namespace" in annex_c_text


def test_target_epic_notes_reference_sme_rp_addendum_tasks() -> None:
    required_by_epic = {
        "EPIC-136": ["TASK-0648", "TASK-0664", "SME-RP real-project acceptance addendum"],
        "EPIC-140": ["TASK-0649", "TASK-0650", "SME-RP real-project acceptance addendum"],
        "EPIC-141": ["TASK-0652", "SME-RP real-project acceptance addendum"],
        "EPIC-142": ["TASK-0651", "TASK-0658", "TASK-0660"],
        "EPIC-143": ["TASK-0654", "TASK-0655", "TASK-0656", "TASK-0657"],
        "EPIC-144": ["TASK-0653", "Workpages may surface"],
        "EPIC-145": ["CAPEX real-project fixture governance", "New acceptance gates"],
        "EPIC-146": ["TASK-0661", "K12-T1..T10"],
        "EPIC-147": ["fixture tiers", "generalized SME-RP gates"],
        "EPIC-149": ["TASK-0662", "SME-RP-G013"],
        "EPIC-151": ["TASK-0659", "TASK-0663", "SME-RP-G011"],
    }

    for epic_id, required_snippets in required_by_epic.items():
        text = (ROOT / f"docs/planning/epics/{epic_id}.md").read_text(
            encoding="utf-8"
        )
        assert "SME-RP" in text
        for snippet in required_snippets:
            assert snippet in text


def test_approval_with_conditions_posture_is_closeout_grade() -> None:
    register = _load_register()
    posture = register["approval_posture"]
    sign_off_text = SIGN_OFF_PATH.read_text(encoding="utf-8")
    readme_text = (REGISTER_DIR / "README.md").read_text(encoding="utf-8")

    assert posture["gate_id"] == "SME-RP-G001"
    assert posture["approval_kind"] == "approval_with_conditions"
    assert posture["conditional"] is True
    assert posture["module_specific"] is True
    assert posture["non_activation"] is True
    assert posture["blocking_scope"] == "affected_module_only"
    assert posture["affected_module_only"] is True
    assert posture["wording_ref"] == (
        "docs/planning/capex_real_project_acceptance/"
        "SME_RP_APPROVAL_WITH_CONDITIONS_SIGN_OFF.md"
    )
    assert set(posture["cannot_be_used_for"]) >= {
        "implementation_approval",
        "capex_runtime_activation",
        "product_activation",
        "public_route_activation",
        "migration_approval",
        "raw_corpus_import",
    }

    normalized = re.sub(r"\s+", " ", sign_off_text)
    normalized_lower = normalized.lower()
    for required in (
        "SME-RP acceptance is conditional and module-specific",
        "not implementation approval",
        "not CAPEX runtime activation",
        "affected module only",
    ):
        assert required in normalized
    assert "non-activation" in normalized_lower
    assert "SME_RP_APPROVAL_WITH_CONDITIONS_SIGN_OFF.md" in readme_text


def test_capex_scope_hierarchy_contract_preserves_boundaries() -> None:
    text = SCOPE_CONTRACT_PATH.read_text(encoding="utf-8")
    normalized = re.sub(r"\s+", " ", text)
    hierarchy = re.findall(r"^\d+\. `([^`]+)`$", text, flags=re.MULTILINE)

    assert hierarchy == [
        "project",
        "module_workstream",
        "package",
        "discipline",
        "source_occurrence",
        "artifact",
        "task",
        "approval",
        "flag",
        "external_binding",
    ]
    for required in (
        "Scope rows never cross tenant, domain, or project boundaries.",
        "Parent and child scope refs must stay inside the same `project_id`.",
        "`capex_projects.project_id` remains the durable project root.",
        "`workflow_run_id` is execution identity only; it is not project identity and is not scope identity.",
        "One closed scope cannot imply overall closure.",
    ):
        assert required in normalized
    assert "`K12-T1` is the motivating fixture case" in normalized
    assert "`K12-T1` is a fixture-case ID only" in normalized
    assert "not a product namespace, gate namespace, or runtime scope kind" in normalized


def test_raci_role_permission_matrix_is_business_overlay_only() -> None:
    register = _load_register()
    matrix = register["raci_role_permission_matrix"]
    text = RACI_CONTRACT_PATH.read_text(encoding="utf-8")
    normalized = re.sub(r"\s+", " ", text)

    assert matrix["gate_id"] == "SME-RP-G002"
    assert matrix["contract_ref"] == "docs/architecture/CAPEX_RACI_ROLE_PERMISSION_MATRIX.md"
    assert matrix["authority_boundary"] == (
        "business_responsibility_overlay_not_authorization_source"
    )
    assert matrix["roles"] == EXPECTED_RACI_ROLES
    assert matrix["governed_actions"] == EXPECTED_RACI_ACTIONS
    assert set(matrix["permission_sources"]) == {
        "project_memberships",
        "capex_project_authorization",
        "canonical_approvals",
        "audited_events",
        "immutable_artifacts",
        "promotion_pointers",
    }
    assert set(matrix["never_permission_sources"]) >= {
        "generated_material",
        "workpage_state",
        "ai_output",
        "external_status",
    }
    assert set(matrix["minimum_project_role_posture"]) == set(EXPECTED_RACI_ACTIONS)

    for role in EXPECTED_RACI_ROLES:
        assert role in text
    for action in EXPECTED_RACI_ACTIONS:
        assert f"`{action}`" in text
    for required in (
        "RACI is a business-responsibility overlay, not a runtime authorization source.",
        "Generated material, workpage state, AI output, external status",
        "These postures are acceptance constraints for later implementation. They do not grant permission by themselves.",
    ):
        assert required in normalized


def test_module_specific_readiness_rule_is_affected_module_only() -> None:
    register = _load_register()
    rule = register["module_specific_readiness_rule"]
    task = _task_file("TASK-0664")
    frontmatter = _task_frontmatter(task)
    task_text = task.read_text(encoding="utf-8")
    epic_text = (ROOT / "docs/planning/epics/EPIC-136.md").read_text(
        encoding="utf-8"
    )

    assert rule["rule_id"] == "SME-RP-MODULE-READINESS-RULE.v1"
    assert rule["gate_refs"] == ["SME-RP-G002", "SME-RP-G012"]
    assert rule["blocking_scope"] == "affected_module_only"
    assert (
        rule["unresolved_business_definitions_block"]
        == "dependent_modules_and_surfaces_only"
    )
    assert set(rule["affected_surface_types"]) == {
        "workflow",
        "workpage_family",
        "projection_family",
        "snapshot_export_surface",
        "external_observation_surface",
    }
    assert set(rule["independent_work_may_continue"]) >= {
        "platform_hardening",
        "schema_parity",
        "security_fixes",
        "neutral_foundation_work",
        "disabled_capex_scaffolding",
    }
    assert set(rule["readiness_requires"]) == {
        "required_business_definitions_accepted_or_explicitly_waived",
        "raci_role_permission_posture_resolved_for_governed_actions",
        "workflow_extension_classification_resolved",
        "activation_gate_evidence_recorded_for_affected_module",
    }
    assert set(rule["cannot_be_used_for"]) >= {
        "implementation_approval",
        "capex_runtime_activation",
        "product_activation",
        "public_route_activation",
        "migration_approval",
        "raw_corpus_import",
    }
    assert frontmatter["status"] == "DONE"
    assert "planning_only_no_capex_activation" in task_text
    assert "affected module only" in task_text
    assert "SME-RP-MODULE-READINESS-RULE.v1" in task_text
    assert "module-specific readiness rule is recorded" in epic_text


def test_evidence_status_vocabulary_and_transitions_are_pinned() -> None:
    register = _load_register()
    vocabulary = register["evidence_status_vocabulary"]
    text = EVIDENCE_CONTRACT_PATH.read_text(encoding="utf-8")
    normalized = re.sub(r"\s+", " ", text)

    assert vocabulary["gate_id"] == "SME-RP-G004"
    assert vocabulary["contract_ref"] == (
        "docs/architecture/CAPEX_EVIDENCE_STATUS_TRANSITION_CONTRACT.md"
    )
    assert vocabulary["principle"] == "presence_is_not_sufficiency"
    assert vocabulary["statuses"] == EXPECTED_EVIDENCE_STATUSES
    assert vocabulary["closure_eligibility"]["valid"] == "may_satisfy_closure"
    assert (
        vocabulary["closure_eligibility"]["accepted_with_residual_risk"]
        == "requires_explicit_residual_risk_acceptance_or_waiver"
    )
    for status in (
        "proposed",
        "under_review",
        "partly_valid",
        "contradictory",
        "obsolete",
        "invalid",
        "insufficient",
    ):
        assert vocabulary["closure_eligibility"][status] == "cannot_satisfy_closure"

    assert vocabulary["transitions"] == {
        "proposed": ["under_review", "invalid", "obsolete"],
        "under_review": [
            "valid",
            "partly_valid",
            "contradictory",
            "obsolete",
            "invalid",
            "insufficient",
        ],
        "valid": ["under_review", "contradictory", "obsolete"],
        "partly_valid": [
            "under_review",
            "accepted_with_residual_risk",
            "contradictory",
            "obsolete",
            "invalid",
            "insufficient",
        ],
        "accepted_with_residual_risk": [
            "under_review",
            "contradictory",
            "obsolete",
        ],
        "contradictory": ["under_review", "obsolete"],
        "invalid": ["under_review", "obsolete"],
        "insufficient": ["under_review", "invalid", "obsolete"],
        "obsolete": ["under_review"],
    }
    assert vocabulary["transition_notes"]["obsolete_to_under_review"] == (
        "requires_new_source_occurrence_or_revision_reopen"
    )
    assert set(vocabulary["never_sufficient_alone"]) >= {
        "raw_file_presence",
        "extracted_text",
        "ai_output",
        "workpage_state",
        "external_status",
        "generated_artifact",
    }

    for status in EXPECTED_EVIDENCE_STATUSES:
        assert f"`{status}`" in text
    for required in (
        "Evidence presence is not evidence sufficiency.",
        "`valid` may satisfy closure.",
        "`accepted_with_residual_risk` may satisfy closure only with explicit residual-risk acceptance or waiver.",
        "`proposed`, `under_review`, `partly_valid`, `contradictory`, `obsolete`, `invalid`, and `insufficient` cannot satisfy closure by themselves.",
    ):
        assert required in normalized


def test_source_occurrence_context_profile_and_trust_taxonomy_are_pinned() -> None:
    register = _load_register()
    profile = register["source_occurrence_context_profile"]
    text = SOURCE_CONTEXT_CONTRACT_PATH.read_text(encoding="utf-8")
    normalized = re.sub(r"\s+", " ", text)

    assert profile["gate_id"] == "SME-RP-G004"
    assert profile["contract_ref"] == (
        "docs/architecture/CAPEX_SOURCE_OCCURRENCE_CONTEXT_AND_TRUST_CONTRACT.md"
    )
    assert (
        profile["source_truth_boundary"]
        == "observed_source_truth_not_reviewed_project_truth"
    )
    assert profile["source_origin_modes"] == EXPECTED_SOURCE_ORIGIN_MODES
    assert profile["evidence_source_trust_modes"] == EXPECTED_SOURCE_TRUST_MODES
    assert set(profile["required_context_fields"]) >= {
        "source_occurrence_id",
        "tenant_id",
        "domain",
        "project_id",
        "capex_scope_ref",
        "source_ref",
        "original_source_role",
        "package_workstream_ref",
        "source_state_hint",
        "extraction_state",
        "redaction_state",
        "source_origin_mode",
        "evidence_source_trust_mode",
    }
    assert profile["separation_rules"] == [
        "source_occurrence_is_observed_source_truth",
        "source_ref_points_to_meaningful_source_occurrence",
        "evidence_binding_links_claim_to_reviewed_source_context",
        "review_records_evidence_status",
        "approval_records_governed_decision",
        "official_adoption_requires_canonical_artifact_event_pointer_evidence",
    ]
    assert set(profile["cannot_overwrite_capex_state"]) >= {
        "raw_file",
        "external_status",
        "imported_status",
        "generated_artifact",
        "ai_output",
        "workpage_state",
    }
    assert profile["later_scope_gate_refs"] == ["SME-RP-G011"]

    for mode in EXPECTED_SOURCE_ORIGIN_MODES + EXPECTED_SOURCE_TRUST_MODES:
        assert f"`{mode}`" in text
    for required in (
        "Source occurrence context is observed source truth, not reviewed project truth.",
        "Source occurrence, SourceRef, evidence binding, review, approval, and official adoption remain separate.",
        "No source occurrence field, imported metadata value, external status, generated artifact, AI output, workpage state, raw file, or local folder state can overwrite CAPEX state directly.",
        "`officially_adopted` is permitted only after the source-backed claim has been reviewed and adopted through the canonical one-truth substrate.",
    ):
        assert required in normalized


def test_workpage_to_task_generation_rules_preserve_canonical_truth() -> None:
    register = _load_register()
    rules = register["workpage_task_generation_rules"]
    text = WORKPAGE_GENERATION_CONTRACT_PATH.read_text(encoding="utf-8")
    normalized = re.sub(r"\s+", " ", text)

    assert rules["gate_id"] == "SME-RP-G005"
    assert rules["contract_ref"] == (
        "docs/architecture/CAPEX_WORKPAGE_TO_TASK_GENERATION_CONTRACT.md"
    )
    assert rules["authority_boundary"] == "workpages_never_set_official_project_status"
    assert rules["blocker_types"] == EXPECTED_WORKPAGE_BLOCKER_TYPES
    assert rules["allowed_canonical_outputs"] == EXPECTED_WORKPAGE_CANONICAL_OUTPUTS
    assert rules["required_guards"] == EXPECTED_WORKPAGE_REQUIRED_GUARDS
    assert set(rules["cannot_set_by_workpage_projection"]) == {
        "official_project_status",
        "closure",
        "evidence_sufficiency",
        "commercial_status",
        "safety_readiness",
    }
    assert rules["disallowed_command_families"] == ["generic_status_command"]
    assert set(rules["required_rejection_conditions"]) >= {
        "invalid_signature",
        "expired_cursor",
        "stale_projection_snapshot",
        "superseded_projection_snapshot",
        "basis_hash_mismatch",
        "unresolved_source_ref",
        "missing_actor_authority",
        "missing_audit_evidence",
    }

    for value in (
        EXPECTED_WORKPAGE_BLOCKER_TYPES
        + EXPECTED_WORKPAGE_CANONICAL_OUTPUTS
        + EXPECTED_WORKPAGE_REQUIRED_GUARDS
    ):
        assert f"`{value}`" in text
    for required in (
        "They never set official project status by projection update, row state, local UI state, or generic status command.",
        "A workpage-originated blocker must become one or more canonical outputs before it can affect official readiness or closure:",
        "Workpage projections cannot set closure, evidence sufficiency, commercial status, safety readiness, or official project status.",
        "Generic status commands are not allowed.",
    ):
        assert required in normalized


def test_procurement_escalation_workflow_proposal_is_planning_only() -> None:
    register = _load_register()
    proposal = register["procurement_escalation_workflow_proposal"]

    assert proposal["proposal_id"] == "capex.procurement_escalation.workflow_proposal.v1"
    assert proposal["proposal_ref"] == (
        "docs/planning/capex_workflow_catalog/"
        "procurement_escalation_workflow_proposal.yaml"
    )
    assert PROCUREMENT_ESCALATION_PROPOSAL_PATH.exists()
    assert proposal["activation_posture"] == "planning_only_no_capex_activation"
    assert proposal["gate_refs"] == ["NU-GATE-011"]
    assert set(proposal["depends_on_gate_refs"]) == {
        "SME-RP-G006",
        "SME-RP-G007",
        "SME-RP-G012",
    }
    assert proposal["task_refs"] == ["TASK-0571"]
    assert "TASK-0659" in proposal["remaining_activation_task_refs"]
    assert proposal["routing_boundary"] == (
        "procurement_and_ceo_decisions_are_task_chains_not_editable_workpage_status"
    )
    assert set(proposal["cannot_be_used_for"]) >= {
        "implementation_approval",
        "capex_runtime_activation",
        "product_activation",
        "public_route_activation",
        "public_workpage_activation",
        "authored_workflow_pack_activation",
        "migration_approval",
        "raw_corpus_import",
        "threshold_signoff",
        "procurement_field_signoff",
    }
