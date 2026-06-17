from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from tests.helpers.repo_paths import REPO_ROOT


PREFLIGHT_DIR = REPO_ROOT / "docs/planning/capex_production_preflight"
P0_REVIEW_PATH = PREFLIGHT_DIR / "P0_ACTIVATION_BLOCKER_REVIEW.yaml"
THREE_PROJECT_REVIEW_PATH = PREFLIGHT_DIR / "THREE_PROJECT_EVIDENCE_PACKAGE_REVIEW.yaml"
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
)


def _load_yaml(path: Path) -> dict[str, Any]:
    loaded = yaml.safe_load(path.read_text(encoding="utf-8"))
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
