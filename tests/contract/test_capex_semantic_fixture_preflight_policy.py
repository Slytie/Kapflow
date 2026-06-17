from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import yaml

from tests.helpers.repo_paths import REPO_ROOT


FIXTURE_POLICY_PATH = (
    REPO_ROOT
    / "docs/planning/capex_three_project_validation/FIXTURE_TIER_CI_POLICY.yaml"
)
PREFLIGHT_REVIEW_PATH = (
    REPO_ROOT
    / "docs/planning/capex_production_preflight/"
    "MASTER_Production_Preflight_Review.md"
)
FRONTMATTER_RE = re.compile(r"\A---\n(?P<body>.*?)\n---\n", re.DOTALL)
EXPECTED_LANES = ["pr", "merge", "nightly", "release", "controlled_pilot"]
EXPECTED_FIXTURE_REFS = {
    "K12_EXPECTED_OUTPUT_MANIFEST.yaml",
    "K3_MINI_FIXTURE_EXPECTATION_CATALOG.yaml",
    "BLIND_VALIDATION_FREEZE_PROTOCOL.yaml",
    "CROSS_PROJECT_INVARIANT_SCORECARD.yaml",
    "AGENT_LAB_EVAL_MATRIX.yaml",
    "OFF_REPO_FULL_CORPUS_RUNBOOK.yaml",
    "NO_OVERFITTING_REVIEW_CHECKPOINT.yaml",
    "PROJECT_ORACLE_MANIFEST_FORMAT.yaml",
}
EXPECTED_PROD_PRE_GATES = [f"PROD-PRE-G{index:02d}" for index in range(1, 11)]
FORBIDDEN_PASS_CLAIMS = (
    "fixture release approved",
    "ci enforcement enabled",
    "hosted branch protection enabled",
    "production preflight approved",
    "pilot readiness approved",
    "product activation approved",
    "runtime activation approved",
    "capex activation approved",
    "final go/no-go approved",
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


def test_fixture_tier_ci_policy_records_planned_lanes_only() -> None:
    policy = _load_yaml(FIXTURE_POLICY_PATH)
    lowered = FIXTURE_POLICY_PATH.read_text(encoding="utf-8").lower()

    assert policy["schema_version"] == "capex.fixture_tier_ci_policy.v1"
    assert policy["owner_task"] == "TASK-0598"
    assert policy["source_task_id"] == "TP-TASK-010"
    assert policy["activation_posture"] == "planning_only_no_capex_activation"
    assert policy["lane_order"] == EXPECTED_LANES
    assert [lane["lane_id"] for lane in policy["ci_lanes"]] == EXPECTED_LANES
    assert policy["policy_scope"]["ci_enforcement_modified"] is False
    assert policy["policy_scope"]["github_required_checks_modified"] is False
    assert policy["policy_scope"]["hosted_branch_protection_claim"] is False

    allowed_checks = set(policy["allowed_check_vocabulary"])
    observed_refs = set()
    for lane in policy["ci_lanes"]:
        assert lane["activation_posture"] == "planning_only_no_capex_activation"
        assert lane["fixture_tiers"], lane
        assert lane["evidence_refs"], lane
        assert lane["raw_data_boundary"], lane
        assert set(lane["allowed_checks"]).issubset(allowed_checks), lane
        observed_refs.update(lane["evidence_refs"])

    assert EXPECTED_FIXTURE_REFS <= observed_refs
    blocked_lanes = {
        lane["lane_id"]
        for lane in policy["ci_lanes"]
        if lane["status"].startswith("blocked")
        or lane["status"].startswith("advisory_blocked")
    }
    assert blocked_lanes == {"nightly", "release", "controlled_pilot"}
    release_lane = next(lane for lane in policy["ci_lanes"] if lane["lane_id"] == "release")
    pilot_lane = next(
        lane for lane in policy["ci_lanes"] if lane["lane_id"] == "controlled_pilot"
    )
    assert "full_corpus_off_repo" in release_lane["fixture_tiers"]
    assert "full_corpus_off_repo" in pilot_lane["fixture_tiers"]
    assert "production_preflight_blocker_review" in release_lane["allowed_checks"]
    assert "production_preflight_blocker_review" in pilot_lane["allowed_checks"]

    assert policy["rollup_policy"]["current_rollup_status"] == (
        "planning_policy_recorded_not_enforced"
    )
    assert set(policy["cannot_be_used_for"]) >= {
        "capex_runtime_activation",
        "product_activation",
        "raw_corpus_import",
        "fixture_release_approval",
        "hosted_branch_protection_claim",
        "github_required_check_enforcement",
        "production_preflight_approval",
        "pilot_readiness_approval",
    }
    assert set(policy["raw_data_boundary"]["prohibited_repo_material"]) >= {
        "full project corpus files",
        "unrestricted source excerpts",
        "raw project filenames",
        "screenshots or logs containing source content",
        "project-specific hardcoded logic",
    }
    for forbidden in FORBIDDEN_PASS_CLAIMS:
        assert forbidden not in lowered


def test_production_preflight_master_review_is_no_go_and_blocked() -> None:
    frontmatter = _load_frontmatter(PREFLIGHT_REVIEW_PATH)
    lowered = PREFLIGHT_REVIEW_PATH.read_text(encoding="utf-8").lower()

    assert frontmatter["schema_version"] == "capex.production_preflight_review.v1"
    assert frontmatter["owner_task"] == "TASK-0599"
    assert frontmatter["source_task_id"] == "PP-TASK-001"
    assert frontmatter["activation_posture"] == "planning_only_no_capex_activation"
    assert frontmatter["overall_status"] == "no_go_blocked_pending_evidence"
    assert frontmatter["approved_waivers"] == []
    assert set(frontmatter["supporting_review_refs"]) >= {
        "docs/planning/capex_production_preflight/"
        "P0_ACTIVATION_BLOCKER_REVIEW.yaml",
        "docs/planning/capex_production_preflight/"
        "THREE_PROJECT_EVIDENCE_PACKAGE_REVIEW.yaml",
    }
    assert [row["gate_id"] for row in frontmatter["gate_reviews"]] == (
        EXPECTED_PROD_PRE_GATES
    )

    expected_review_refs = {
        "PROD-PRE-G01": (
            "docs/planning/capex_production_preflight/"
            "P0_ACTIVATION_BLOCKER_REVIEW.yaml"
        ),
        "PROD-PRE-G02": (
            "docs/planning/capex_production_preflight/"
            "THREE_PROJECT_EVIDENCE_PACKAGE_REVIEW.yaml"
        ),
        "PROD-PRE-G03": (
            "docs/planning/capex_production_preflight/"
            "THREE_PROJECT_EVIDENCE_PACKAGE_REVIEW.yaml"
        ),
        "PROD-PRE-G04": (
            "docs/planning/capex_production_preflight/"
            "THREE_PROJECT_EVIDENCE_PACKAGE_REVIEW.yaml"
        ),
        "PROD-PRE-G05": (
            "docs/planning/capex_production_preflight/"
            "THREE_PROJECT_EVIDENCE_PACKAGE_REVIEW.yaml"
        ),
    }
    expected_pending_tasks = {
        "PROD-PRE-G06": "TASK-0602",
        "PROD-PRE-G07": "TASK-0603",
        "PROD-PRE-G08": "TASK-0604",
        "PROD-PRE-G09": "TASK-0605",
        "PROD-PRE-G10": "TASK-0606",
    }
    for row in frontmatter["gate_reviews"]:
        assert row["reason_code"], row
        if row["gate_id"] in expected_review_refs:
            assert row["status"] == "reviewed_no_go_blocked_pending_evidence", row
            assert row["evidence_ref"] == expected_review_refs[row["gate_id"]]
        else:
            assert row["status"] == "blocked_pending_task", row
            assert row["pending_task"] == expected_pending_tasks[row["gate_id"]]

    assert set(frontmatter["future_waiver_required_fields"]) >= {
        "owner",
        "reason",
        "residual_risk",
        "expiry_or_review_date",
        "affected_gate",
    }
    assert frontmatter["rollback_posture"]["recommendation"] == "defer_no_go"
    assert frontmatter["rollback_posture"]["capex_disabled"] is True
    assert set(frontmatter["rollback_posture"]["route_later_gate_checks_to"]) == {
        "TASK-0602",
        "TASK-0603",
        "TASK-0604",
        "TASK-0605",
        "TASK-0606",
    }
    assert set(frontmatter["cannot_be_used_for"]) >= {
        "capex_runtime_activation",
        "product_activation",
        "raw_corpus_import",
        "fixture_release_approval",
        "pilot_readiness_approval",
        "production_preflight_approval",
        "final_go_no_go_approval",
    }
    for forbidden in FORBIDDEN_PASS_CLAIMS:
        assert forbidden not in lowered
