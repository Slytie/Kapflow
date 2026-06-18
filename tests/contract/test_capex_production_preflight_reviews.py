from __future__ import annotations

from pathlib import Path
import re
from typing import Any

import yaml

from tests.helpers.repo_paths import REPO_ROOT


PREFLIGHT_DIR = REPO_ROOT / "docs/planning/capex_production_preflight"
P0_REVIEW_PATH = PREFLIGHT_DIR / "P0_ACTIVATION_BLOCKER_REVIEW.yaml"
THREE_PROJECT_REVIEW_PATH = PREFLIGHT_DIR / "THREE_PROJECT_EVIDENCE_PACKAGE_REVIEW.yaml"
RAW_DATA_REVIEW_PATH = PREFLIGHT_DIR / "RAW_DATA_QUARANTINE_LEAK_SCAN_REVIEW.yaml"
CAPACITY_REVIEW_PATH = PREFLIGHT_DIR / "CAPACITY_RESTORE_FULL_CORPUS_REVIEW.yaml"
RELEASE_REVIEW_PATH = (
    PREFLIGHT_DIR / "RELEASE_MIGRATION_ACTIVATION_ROLLBACK_REVIEW.yaml"
)
SEMANTIC_CI_REVIEW_PATH = PREFLIGHT_DIR / "SEMANTIC_REVIEW_CI_GATE_REVIEW.yaml"
GO_NO_GO_MEMO_PATH = PREFLIGHT_DIR / "PRODUCTION_PREFLIGHT_GO_NO_GO_MEMO.md"
FRONTMATTER_RE = re.compile(r"\A---\n(?P<body>.*?)\n---\n", re.DOTALL)
EXPECTED_P0_FAMILIES = {
    "approval_response_neutrality",
    "artifact_auth_before_read",
    "project_membership_authorization",
    "source_occurrence_sourceref_resolution",
    "closure_waiver_lifecycle",
    "stale_command_guards",
    "capex_semantic_tests",
    "codeowners_review_gates",
    "storage_pilot_readiness",
    "release_preflight_chain",
}
EXPECTED_THREE_PROJECT_REFS = {
    "THREE_PROJECT_FIXTURE_GOVERNANCE_RUNBOOK.md",
    "K12_EXPECTED_OUTPUT_MANIFEST.yaml",
    "K3_MINI_FIXTURE_EXPECTATION_CATALOG.yaml",
    "BLIND_VALIDATION_FREEZE_PROTOCOL.yaml",
    "CROSS_PROJECT_INVARIANT_SCORECARD.yaml",
    "AGENT_LAB_EVAL_MATRIX.yaml",
    "OFF_REPO_FULL_CORPUS_RUNBOOK.yaml",
    "NO_OVERFITTING_REVIEW_CHECKPOINT.yaml",
    "PROJECT_ORACLE_MANIFEST_FORMAT.yaml",
    "FIXTURE_TIER_CI_POLICY.yaml",
}
EXPECTED_RAW_DATA_SURFACES = {
    "repo_tracked_files",
    "planning_packs",
    "generated_packs",
    "release_bundles",
    "ci_logs",
    "screenshots_and_logs",
    "off_repo_reviewed_copy_boundary",
}
EXPECTED_CAPACITY_CONTRACTS = {
    "off_repo_full_corpus_runbook",
    "pilot_storage_gate_checklist",
    "backup_restore_runbook",
    "predeploy_backup_skeleton",
    "release_backup_readiness_tests",
}
EXPECTED_RELEASE_FAMILIES = {
    "release_bundle_manifest",
    "migration_lane_evidence",
    "activation_gate_manifest",
    "rollback_compensation_plan",
    "release_approval_waiver_trail",
}
EXPECTED_SEMANTIC_CI_FAMILIES = {
    "codeowners",
    "capex_semantic_test_lane",
    "capex_invariant_audit",
    "semantic_merge_review",
    "review_tier_rules",
    "hosted_ci_required_checks",
}
EXPECTED_MEMO_REFS = {
    "MASTER_Production_Preflight_Review.md",
    "P0_ACTIVATION_BLOCKER_REVIEW.yaml",
    "THREE_PROJECT_EVIDENCE_PACKAGE_REVIEW.yaml",
    "RAW_DATA_QUARANTINE_LEAK_SCAN_REVIEW.yaml",
    "CAPACITY_RESTORE_FULL_CORPUS_REVIEW.yaml",
    "RELEASE_MIGRATION_ACTIVATION_ROLLBACK_REVIEW.yaml",
    "SEMANTIC_REVIEW_CI_GATE_REVIEW.yaml",
}
EXPECTED_RESIDUAL_BLOCKERS = {
    "p0_activation_blockers_without_waiver",
    "three_project_fixture_release_and_baseline_evidence",
    "raw_data_quarantine_full_surface_leak_scan",
    "full_corpus_capacity_backup_restore_rehearsal",
    "release_migration_activation_rollback_rehearsal",
    "semantic_review_codeowners_hosted_ci_enforcement",
}
FORBIDDEN_CLAIMS = (
    "runtime activation approved",
    "product activation approved",
    "capex activation approved",
    "production preflight approved",
    "pilot readiness approved",
    "final go/no-go approved",
    "waiver approved",
    "fixture release approved",
    "raw corpus import approved",
    "leak scan passes for all surfaces",
    "restore proof approved",
    "capacity pass approved",
    "release approved",
    "migration approved",
    "activation approved",
    "rollback rehearsal complete",
    "compensation rehearsal complete",
    "ci enforcement enabled",
    "hosted branch protection enabled",
    "required checks enforced",
)


def _load_yaml(path: Path) -> dict[str, Any]:
    loaded = yaml.safe_load(path.read_text(encoding="utf-8"))
    assert isinstance(loaded, dict)
    return loaded


def _load_frontmatter(path: Path) -> dict[str, Any]:
    match = FRONTMATTER_RE.match(path.read_text(encoding="utf-8"))
    assert match is not None
    loaded = yaml.safe_load(match.group("body"))
    assert isinstance(loaded, dict)
    return loaded


def _assert_review_boundary(review: dict[str, Any], path: Path) -> None:
    lowered = path.read_text(encoding="utf-8").lower()

    assert review["activation_posture"] == "planning_only_no_capex_activation"
    assert review["overall_status"] == "no_go_blocked_pending_evidence"
    assert review["approved_waivers"] == []
    assert set(review["future_waiver_required_fields"]) >= {
        "owner",
        "reason",
        "residual_risk",
        "expiry_or_review_date",
        "affected_gate",
    }
    assert set(review["cannot_be_used_for"]) >= {
        "capex_runtime_activation",
        "product_activation",
        "public_route_activation",
        "workflow_pack_activation",
        "raw_corpus_import",
        "fixture_release_approval",
        "waiver_approval",
        "pilot_readiness_approval",
        "production_preflight_approval",
        "final_go_no_go_approval",
    }
    assert set(review["raw_data_boundary"]["prohibited_repo_material"]) >= {
        "full project corpus files",
        "unrestricted source excerpts",
        "raw project filenames",
        "screenshots or logs containing source content",
        "project-specific hardcoded logic",
    }
    for forbidden in FORBIDDEN_CLAIMS:
        assert forbidden not in lowered


def test_p0_activation_blocker_review_fails_closed_with_open_blockers() -> None:
    review = _load_yaml(P0_REVIEW_PATH)

    assert review["schema_version"] == "capex.production_preflight_gate_review.v1"
    assert review["owner_task"] == "TASK-0600"
    assert review["source_task_id"] == "PP-TASK-002"
    assert review["gate_refs"] == ["PROD-PRE-G01"]
    _assert_review_boundary(review, P0_REVIEW_PATH)

    families = review["reviewed_blocker_families"]
    assert {row["family_id"] for row in families} == EXPECTED_P0_FAMILIES
    assert review["rollup"]["reviewed_family_count"] == len(EXPECTED_P0_FAMILIES)
    assert review["rollup"]["blocking_family_count"] == sum(
        1 for row in families if row["blocking"] is True
    )
    assert any(row["blocking"] is True for row in families)
    assert all(row["evidence_refs"] for row in families)
    assert all(
        row["status"] != "open_blocking_without_waiver" or row["blocking"] is True
        for row in families
    )
    assert review["approved_waivers"] == []


def test_three_project_evidence_review_covers_g02_to_g05_without_pass_claims() -> None:
    review = _load_yaml(THREE_PROJECT_REVIEW_PATH)

    assert review["schema_version"] == "capex.production_preflight_gate_review.v1"
    assert review["owner_task"] == "TASK-0601"
    assert review["source_task_id"] == "PP-TASK-003"
    assert review["gate_refs"] == [
        "PROD-PRE-G02",
        "PROD-PRE-G03",
        "PROD-PRE-G04",
        "PROD-PRE-G05",
    ]
    _assert_review_boundary(review, THREE_PROJECT_REVIEW_PATH)

    assert set(review["evidence_contract_refs"]) >= EXPECTED_THREE_PROJECT_REFS
    gate_reviews = review["gate_reviews"]
    assert [row["gate_id"] for row in gate_reviews] == review["gate_refs"]
    assert all(
        row["status"] == "reviewed_no_go_blocked_pending_evidence"
        for row in gate_reviews
    )
    observed_refs = {
        evidence_ref
        for row in gate_reviews
        for evidence_ref in row["evidence_refs"]
    }
    assert {
        "K12_EXPECTED_OUTPUT_MANIFEST.yaml",
        "K3_MINI_FIXTURE_EXPECTATION_CATALOG.yaml",
        "BLIND_VALIDATION_FREEZE_PROTOCOL.yaml",
        "CROSS_PROJECT_INVARIANT_SCORECARD.yaml",
        "PROJECT_ORACLE_MANIFEST_FORMAT.yaml",
        "AGENT_LAB_EVAL_MATRIX.yaml",
        "NO_OVERFITTING_REVIEW_CHECKPOINT.yaml",
    } <= observed_refs
    assert set(review["missing_evidence"]) >= {
        "fixture_release_approval",
        "k3_shadow_execution_report",
        "blind_baseline_execution_report",
        "signed_freeze_evidence",
        "cross_project_scorecard_pass_or_waiver",
        "explicit_gate_waiver_evidence",
    }
    assert review["rollup"]["passed_gate_count"] == 0


def test_raw_data_quarantine_review_covers_surfaces_and_blocks_missing_evidence() -> None:
    review = _load_yaml(RAW_DATA_REVIEW_PATH)

    assert review["schema_version"] == "capex.production_preflight_gate_review.v1"
    assert review["owner_task"] == "TASK-0602"
    assert review["source_task_id"] == "PP-TASK-004"
    assert review["gate_refs"] == ["PROD-PRE-G06"]
    _assert_review_boundary(review, RAW_DATA_REVIEW_PATH)

    surfaces = review["reviewed_surfaces"]
    assert {row["surface_id"] for row in surfaces} == EXPECTED_RAW_DATA_SURFACES
    assert review["rollup"]["reviewed_surface_count"] == len(EXPECTED_RAW_DATA_SURFACES)
    assert review["rollup"]["blocking_surface_count"] == sum(
        1 for row in surfaces if row["blocking"] is True
    )
    assert any(row["blocking"] is True for row in surfaces)
    assert all(row["evidence_refs"] for row in surfaces)
    assert {
        "generated_pack_leak_scan_report",
        "release_bundle_leak_scan_report",
        "ci_log_leak_scan_report",
        "screenshot_log_leak_scan_report",
        "full_corpus_reviewed_copy_attestation",
    } <= set(review["missing_evidence"])
    assert "leak_scan_pass_claim_for_all_surfaces" in review["cannot_be_used_for"]


def test_capacity_restore_review_blocks_until_real_execution_evidence_exists() -> None:
    review = _load_yaml(CAPACITY_REVIEW_PATH)

    assert review["schema_version"] == "capex.production_preflight_gate_review.v1"
    assert review["owner_task"] == "TASK-0603"
    assert review["source_task_id"] == "PP-TASK-005"
    assert review["gate_refs"] == ["PROD-PRE-G07"]
    _assert_review_boundary(review, CAPACITY_REVIEW_PATH)

    contracts = review["reviewed_evidence_contracts"]
    assert {row["evidence_id"] for row in contracts} == EXPECTED_CAPACITY_CONTRACTS
    assert review["rollup"]["reviewed_contract_count"] == len(EXPECTED_CAPACITY_CONTRACTS)
    assert review["rollup"]["blocking_contract_count"] == sum(
        1 for row in contracts if row["blocking"] is True
    )
    assert all(row["blocking"] is True for row in contracts)
    assert all(row["evidence_refs"] for row in contracts)
    assert {
        "realistic_full_corpus_run_report",
        "ingest_extraction_projection_search_metrics",
        "backup_set_capture_record",
        "restore_rehearsal_report",
        "post_restore_auth_before_read_artifact_check",
        "capacity_metrics",
    } <= set(review["missing_evidence"])
    assert {
        "full_corpus_run_completion_claim",
        "restore_rehearsal_completion_claim",
        "capacity_pass_claim",
    } <= set(review["cannot_be_used_for"])


def test_release_migration_activation_review_blocks_until_proof_exists() -> None:
    review = _load_yaml(RELEASE_REVIEW_PATH)

    assert review["schema_version"] == "capex.production_preflight_gate_review.v1"
    assert review["owner_task"] == "TASK-0604"
    assert review["source_task_id"] == "PP-TASK-006"
    assert review["gate_refs"] == ["PROD-PRE-G08"]
    _assert_review_boundary(review, RELEASE_REVIEW_PATH)

    families = review["reviewed_evidence_families"]
    assert {row["family_id"] for row in families} == EXPECTED_RELEASE_FAMILIES
    assert review["rollup"]["reviewed_family_count"] == len(EXPECTED_RELEASE_FAMILIES)
    assert review["rollup"]["blocking_family_count"] == sum(
        1 for row in families if row["blocking"] is True
    )
    assert all(row["blocking"] is True for row in families)
    assert all(row["evidence_refs"] for row in families)
    assert {
        "capex_release_candidate_review_record",
        "production_migration_lane_rehearsal",
        "activation_approval_record",
        "feature_gate_pass_record",
        "capex_rollback_compensation_rehearsal",
        "explicit_gate_waiver_evidence",
    } <= set(review["missing_evidence"])
    assert {
        "release_approval",
        "migration_approval",
        "activation_approval",
        "rollback_rehearsal_completion_claim",
        "compensation_rehearsal_completion_claim",
    } <= set(review["cannot_be_used_for"])


def test_semantic_review_ci_gate_review_records_repo_evidence_without_enforcement_claims() -> None:
    review = _load_yaml(SEMANTIC_CI_REVIEW_PATH)

    assert review["schema_version"] == "capex.production_preflight_gate_review.v1"
    assert review["owner_task"] == "TASK-0605"
    assert review["source_task_id"] == "PP-TASK-007"
    assert review["gate_refs"] == ["PROD-PRE-G09"]
    _assert_review_boundary(review, SEMANTIC_CI_REVIEW_PATH)

    families = review["reviewed_gate_families"]
    assert {row["family_id"] for row in families} == EXPECTED_SEMANTIC_CI_FAMILIES
    assert review["rollup"]["reviewed_family_count"] == len(
        EXPECTED_SEMANTIC_CI_FAMILIES
    )
    assert review["rollup"]["blocking_family_count"] == sum(
        1 for row in families if row["blocking"] is True
    )
    assert all(row["blocking"] is True for row in families)
    observed_refs = {
        evidence_ref
        for row in families
        for evidence_ref in row["evidence_refs"]
    }
    assert {
        ".github/CODEOWNERS",
        "Makefile",
        ".github/workflows/main.yml",
        "scripts/run_capex_invariant_audit.py",
    } <= observed_refs
    assert {
        "hosted_branch_protection_evidence",
        "github_required_check_enforcement_evidence",
        "semantic_mr_gate_log",
        "review_tier_enforcement_proof",
        "capex_runtime_change_ci_pass_record",
        "explicit_gate_waiver_evidence",
    } <= set(review["missing_evidence"])
    assert {
        "ci_enforcement_claim",
        "hosted_branch_protection_claim",
        "semantic_merge_gate_pass_claim",
        "required_check_enforcement_claim",
    } <= set(review["cannot_be_used_for"])


def test_production_preflight_go_no_go_memo_records_final_no_go_without_approval() -> None:
    memo = _load_frontmatter(GO_NO_GO_MEMO_PATH)
    lowered = GO_NO_GO_MEMO_PATH.read_text(encoding="utf-8").lower()

    assert memo["schema_version"] == "capex.production_preflight_go_no_go_memo.v1"
    assert memo["owner_task"] == "TASK-0606"
    assert memo["source_task_id"] == "PP-TASK-008"
    assert memo["gate_refs"] == ["PROD-PRE-G10"]
    assert memo["activation_posture"] == "planning_only_no_capex_activation"
    assert memo["recommendation"] == "no_go"
    assert memo["overall_status"] == "no_go_blocked_pending_evidence"
    assert memo["approved_waivers"] == []
    assert set(memo["future_waiver_required_fields"]) >= {
        "owner",
        "reason",
        "residual_risk",
        "expiry_or_review_date",
        "affected_gate",
    }
    observed_refs = {
        Path(ref).name for ref in memo["supporting_review_refs"]
    }
    assert EXPECTED_MEMO_REFS <= observed_refs
    assert set(memo["residual_blocker_families"]) >= EXPECTED_RESIDUAL_BLOCKERS
    assert memo["production_signoff_status"] == "absent"
    assert set(memo["required_signoff_roles"]) >= {
        "engineering",
        "product",
        "data_governance",
        "security",
    }
    assert set(memo["cannot_be_used_for"]) >= {
        "capex_runtime_activation",
        "product_activation",
        "public_route_activation",
        "workflow_pack_activation",
        "raw_corpus_import",
        "fixture_release_approval",
        "waiver_approval",
        "pilot_readiness_approval",
        "production_preflight_approval",
        "production_go_approval",
        "conditional_go_approval",
        "final_go_no_go_approval",
    }
    for forbidden in FORBIDDEN_CLAIMS:
        assert forbidden not in lowered
