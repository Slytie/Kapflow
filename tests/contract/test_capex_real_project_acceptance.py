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
THREE_PROJECT_RUNBOOK_PATH = (
    ROOT
    / "docs/planning/capex_three_project_validation/"
    "THREE_PROJECT_FIXTURE_GOVERNANCE_RUNBOOK.md"
)
K12_EXPECTED_OUTPUT_MANIFEST_PATH = (
    ROOT
    / "docs/planning/capex_three_project_validation/"
    "K12_EXPECTED_OUTPUT_MANIFEST.yaml"
)
K3_MINI_FIXTURE_EXPECTATION_CATALOG_PATH = (
    ROOT
    / "docs/planning/capex_three_project_validation/"
    "K3_MINI_FIXTURE_EXPECTATION_CATALOG.yaml"
)
BLIND_VALIDATION_FREEZE_PROTOCOL_PATH = (
    ROOT
    / "docs/planning/capex_three_project_validation/"
    "BLIND_VALIDATION_FREEZE_PROTOCOL.yaml"
)
CROSS_PROJECT_INVARIANT_SCORECARD_PATH = (
    ROOT
    / "docs/planning/capex_three_project_validation/"
    "CROSS_PROJECT_INVARIANT_SCORECARD.yaml"
)
AGENT_LAB_EVAL_MATRIX_PATH = (
    ROOT
    / "docs/planning/capex_three_project_validation/"
    "AGENT_LAB_EVAL_MATRIX.yaml"
)
OFF_REPO_FULL_CORPUS_RUNBOOK_PATH = (
    ROOT
    / "docs/planning/capex_three_project_validation/"
    "OFF_REPO_FULL_CORPUS_RUNBOOK.yaml"
)
NO_OVERFITTING_REVIEW_CHECKPOINT_PATH = (
    ROOT
    / "docs/planning/capex_three_project_validation/"
    "NO_OVERFITTING_REVIEW_CHECKPOINT.yaml"
)
PROJECT_ORACLE_MANIFEST_FORMAT_PATH = (
    ROOT
    / "docs/planning/capex_three_project_validation/"
    "PROJECT_ORACLE_MANIFEST_FORMAT.yaml"
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
EXPECTED_TP_GATES = [f"TP-G{index:02d}" for index in range(1, 13)]
EXPECTED_THREE_PROJECT_TIERS = [
    "K12",
    "K3",
    "blind validation",
]
EXPECTED_BLIND_FREEZE_DIMENSIONS = {
    "runtime_rules",
    "prompt_versions",
    "retrieval_recipe_versions",
    "schema_versions",
    "tool_registry",
    "evaluator_criteria",
    "access_controls",
    "baseline_output_custody",
}
EXPECTED_SCORECARD_INVARIANTS = {
    "source_identity_context",
    "source_ref_sufficiency",
    "no_false_closure",
    "pointer_officialness",
    "stale_reopen_behavior",
    "authorization_project_boundary",
    "raw_leakage_scan",
    "generated_artifact_authority",
    "workpage_non_authority",
    "no_project_specific_hardcoding",
}
EXPECTED_AGENT_LAB_TIERS = [
    "K12",
    "K3_mini",
    "K3_shadow",
    "blind_baseline",
]
EXPECTED_OFF_REPO_STEPS = [
    "repo_clean_preflight",
    "operator_owned_quarantine_path",
    "read_only_raw_corpus_mount",
    "sanitized_output_directory",
    "aggregate_reports_only",
    "leak_scan_before_repo_copy",
    "reviewed_repo_copy",
    "teardown",
]
EXPECTED_NO_OVERFITTING_CLASSIFICATIONS = {
    "generalizable",
    "fixture_specific",
    "evidence_absent",
    "deferred_module",
    "invalid_expectation",
}
EXPECTED_PROJECT_ORACLE_TIERS = [
    "K12",
    "K3_mini",
    "K3_shadow",
    "blind_baseline",
]
EXPECTED_PROJECT_ORACLE_ROW_FAMILIES = {
    "expected_output",
    "negative_test",
    "human_oracle_approval",
    "re_review_trigger",
    "pointer_officialness",
    "authority_lifecycle",
    "raw_leakage_guard",
    "no_overfitting_classification",
}


def _load_register() -> dict:
    return yaml.safe_load(REGISTER_PATH.read_text(encoding="utf-8"))


def _load_yaml(path: Path) -> dict:
    loaded = yaml.safe_load(path.read_text(encoding="utf-8"))
    assert isinstance(loaded, dict)
    return loaded


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


def test_three_project_fixture_governance_runbook_is_planning_only() -> None:
    text = THREE_PROJECT_RUNBOOK_PATH.read_text(encoding="utf-8")
    normalized = re.sub(r"\s+", " ", text)
    lowered = normalized.lower()

    assert "planning_only_no_capex_activation" in lowered
    assert "TP-TASK-001" in text
    assert "TP-G01..TP-G12" in text
    for tier in EXPECTED_THREE_PROJECT_TIERS:
        assert tier in text
    for required in (
        "raw/full corpora stay off-repo",
        "sanitized fixtures",
        "manifests",
        "hashes",
        "aggregate evidence",
        "quarantine",
        "leak-scan",
        "release approval",
        "no-overfitting",
        "no project-specific hardcoding",
    ):
        assert required in lowered
    for gate in EXPECTED_TP_GATES:
        assert gate in text
    assert "does not pass all TP gates" in normalized
    for forbidden in (
        "raw K12 content",
        "raw K3 content",
        "raw blind-validation content",
        "product activation approved",
        "runtime activation approved",
    ):
        assert forbidden.lower() not in lowered


def test_k12_expected_output_manifest_is_sanitized_planning_evidence() -> None:
    manifest = _load_yaml(K12_EXPECTED_OUTPUT_MANIFEST_PATH)
    text = K12_EXPECTED_OUTPUT_MANIFEST_PATH.read_text(encoding="utf-8")
    lowered = text.lower()

    assert manifest["schema_version"] == "capex.fixture_expected_output_manifest.v1"
    assert manifest["owner_task"] == "TASK-0590"
    assert manifest["source_task_id"] == "TP-TASK-002"
    assert manifest["fixture_tier"] == "K12"
    assert manifest["activation_posture"] == "planning_only_no_capex_activation"
    assert manifest["oracle_format_ref"] == "PROJECT_ORACLE_MANIFEST_FORMAT.yaml"
    assert manifest["source_evidence"]["package_name"] == (
        "k12_passes_9_11_and_full_synthesis_pack.zip"
    )
    assert manifest["source_evidence"]["package_sha256"] == (
        "7d011a821849fc3e3315d2dee079bfe910848ad276b402b790e5c667a0d965dd"
    )
    assert set(manifest["gate_refs"]) >= {
        "TP-G01",
        "TP-G02",
        "TP-G03",
        "TP-G08",
        "TP-G11",
        "TP-G12",
    }
    assert set(manifest["cannot_be_used_for"]) >= {
        "capex_runtime_activation",
        "product_activation",
        "public_route_activation",
        "workflow_pack_activation",
        "raw_corpus_import",
        "fixture_release_approval",
        "production_preflight_approval",
    }

    oracle_rows = manifest["oracle_rows"]
    assert len(oracle_rows) >= 5
    assert {row["category"] for row in oracle_rows} >= {
        "source_occurrence_context",
        "source_ref_required",
        "verified_read_failure",
        "re_review_trigger",
        "pointer_blocked_by_open_flags",
    }
    for row in oracle_rows:
        assert row["oracle_id"].startswith("K12-EO-")
        assert row["source_table_refs"]
        assert row["expected_result"]
        assert row["evidence_basis"]
        assert row["release_gate"]
        assert row["rollback_recovery"]
        assert set(row["tp_gate_refs"]).issubset(set(manifest["gate_refs"]))

    hardening_rows = manifest["hardening_rows"]
    assert {row["finding_area"] for row in hardening_rows} >= {
        "schema_packaging",
        "source_refs_cardinality",
        "rows_cardinality",
    }
    assert manifest["raw_data_boundary"]["allowed_repo_material"] == [
        "sanitized oracle identifiers",
        "source package hashes",
        "aggregate expectations",
        "gate mappings",
        "rollback and remediation policy",
    ]
    assert set(manifest["raw_data_boundary"]["prohibited_repo_material"]) >= {
        "full project corpus files",
        "unrestricted source excerpts",
        "raw project filenames",
        "screenshots or logs containing source content",
        "project-specific hardcoded logic",
    }
    for forbidden in (
        "product activation approved",
        "runtime activation approved",
        "public route approved",
        "fixture release approved",
        "raw k12 content",
        "raw k3 content",
    ):
        assert forbidden not in lowered


def test_k3_mini_fixture_expectation_catalog_is_sanitized_planning_evidence() -> None:
    catalog = _load_yaml(K3_MINI_FIXTURE_EXPECTATION_CATALOG_PATH)
    text = K3_MINI_FIXTURE_EXPECTATION_CATALOG_PATH.read_text(encoding="utf-8")
    lowered = text.lower()

    assert catalog["schema_version"] == "capex.k3_mini_fixture_expectation_catalog.v1"
    assert catalog["owner_task"] == "TASK-0591"
    assert catalog["source_task_id"] == "TP-TASK-003"
    assert catalog["fixture_tier"] == "K3"
    assert catalog["activation_posture"] == "planning_only_no_capex_activation"
    assert catalog["oracle_format_ref"] == "PROJECT_ORACLE_MANIFEST_FORMAT.yaml"
    assert catalog["source_evidence"]["package_name"] == (
        "k3_passes_9_11_full_synthesis_clean_pack.zip"
    )
    assert catalog["source_evidence"]["package_sha256"] == (
        "03d052edc7d4b27f59f9fbcdceece57c077c388ec3fefb604a44f690966ca1e8"
    )
    assert set(catalog["gate_refs"]) >= {
        "TP-G01",
        "TP-G04",
        "TP-G05",
        "TP-G08",
        "TP-G11",
        "TP-G12",
    }
    assert set(catalog["cannot_be_used_for"]) >= {
        "capex_runtime_activation",
        "product_activation",
        "public_route_activation",
        "workflow_pack_activation",
        "raw_corpus_import",
        "fixture_release_approval",
        "full_k3_module_activation",
        "production_preflight_approval",
    }

    expectation_rows = catalog["expectation_rows"]
    assert len(expectation_rows) >= 6
    assert {row["category"] for row in expectation_rows} >= {
        "source_identity",
        "artifact_role_identity",
        "relation_collision",
        "stale_reopen",
        "pointer_policy",
        "workpage_schema_freeze",
    }
    for row in expectation_rows:
        assert row["expectation_id"].startswith("K3-EXP-")
        assert row["source_table_refs"]
        assert row["expected_behavior"]
        assert row["failure_if"]
        assert row["authority_lifecycle_surface"]
        assert row["rollback_recovery"]
        assert set(row["tp_gate_refs"]).issubset(set(catalog["gate_refs"]))

    assert set(catalog["freeze_families"]) == {
        "schema_freeze",
        "workpage_contract_freeze",
        "pointer_policy_freeze",
        "stale_reopen_enforcement",
    }
    assert catalog["raw_data_boundary"]["allowed_repo_material"] == [
        "sanitized expectation identifiers",
        "source package hashes",
        "aggregate authority and lifecycle expectations",
        "gate mappings",
        "rollback and remediation policy",
    ]
    assert set(catalog["raw_data_boundary"]["prohibited_repo_material"]) >= {
        "full project corpus files",
        "unrestricted source excerpts",
        "raw project filenames",
        "screenshots or logs containing source content",
        "project-specific hardcoded logic",
    }
    for forbidden in (
        "product activation approved",
        "runtime activation approved",
        "public route approved",
        "fixture release approved",
        "raw k12 content",
        "raw k3 content",
    ):
        assert forbidden not in lowered


def test_blind_validation_freeze_protocol_is_planning_only() -> None:
    protocol = _load_yaml(BLIND_VALIDATION_FREEZE_PROTOCOL_PATH)
    text = BLIND_VALIDATION_FREEZE_PROTOCOL_PATH.read_text(encoding="utf-8")
    lowered = text.lower()

    assert protocol["schema_version"] == "capex.blind_validation_freeze_protocol.v1"
    assert protocol["owner_task"] == "TASK-0592"
    assert protocol["source_task_id"] == "TP-TASK-004"
    assert protocol["fixture_tier"] == "blind_validation"
    assert protocol["activation_posture"] == "planning_only_no_capex_activation"
    assert (
        protocol["no_overfitting_checkpoint_ref"]
        == "NO_OVERFITTING_REVIEW_CHECKPOINT.yaml"
    )
    assert set(protocol["gate_refs"]) >= {
        "TP-G01",
        "TP-G06",
        "TP-G07",
        "TP-G08",
        "TP-G09",
        "TP-G12",
    }
    assert protocol["source_policy"]["blind_holdout_location"] == "off_repo_quarantine"
    assert (
        protocol["source_policy"]["contamination_policy"]
        == "no_tuning_from_blind_holdout_before_baseline"
    )
    assert {row["name"] for row in protocol["freeze_dimensions"]} == (
        EXPECTED_BLIND_FREEZE_DIMENSIONS
    )
    for row in protocol["freeze_dimensions"]:
        assert row["dimension_id"].startswith("BV-FREEZE-")
        assert row["required_record"]
        assert row["freeze_requirement"]
        assert row["change_after_freeze_requires"]

    assert set(protocol["required_pre_run_records"]) >= {
        "runtime_rule_set_id",
        "prompt_version_manifest",
        "retrieval_recipe_manifest",
        "schema_version_manifest",
        "tool_registry_manifest",
        "evaluator_criteria_manifest",
        "blind_holdout_access_log",
    }
    assert set(protocol["required_first_run_records"]) >= {
        "unmodified_output_manifest",
        "error_manifest",
        "unsupported_claims_manifest",
        "missing_evidence_recall_manifest",
        "false_closure_manifest",
        "raw_leak_scan_report",
    }
    assert set(protocol["post_blind_change_classification"]["allowed_values"]) == {
        "generalizable",
        "fixture_specific",
        "evidence_absent",
        "deferred_module",
        "invalid_expectation",
    }
    assert protocol["agent_lab_boundary"]["lab_output_authority"] == "advisory_only"
    assert protocol["agent_lab_boundary"]["official_truth_mutation_allowed"] is False
    assert set(protocol["agent_lab_boundary"]["prohibited_direct_outputs"]) >= {
        "official_pointer",
        "approval_response",
        "closure_snapshot",
        "runtime_truth_mutation",
    }
    assert set(protocol["cannot_be_used_for"]) >= {
        "capex_runtime_activation",
        "product_activation",
        "public_route_activation",
        "workflow_pack_activation",
        "raw_corpus_import",
        "blind_baseline_completion_claim",
        "production_preflight_approval",
        "pilot_readiness_approval",
    }
    assert set(protocol["raw_data_boundary"]["allowed_repo_material"]) >= {
        "frozen protocol metadata",
        "gate mappings",
        "access-control requirements",
        "aggregate baseline record requirements",
        "leak-scan requirement",
        "rollback and remediation policy",
    }
    assert set(protocol["raw_data_boundary"]["prohibited_repo_material"]) >= {
        "full project corpus files",
        "unrestricted source excerpts",
        "raw project filenames",
        "screenshots or logs containing source content",
        "project-specific hardcoded logic",
    }
    for forbidden in (
        "product activation approved",
        "runtime activation approved",
        "public route approved",
        "blind baseline passed",
        "production preflight approved",
    ):
        assert forbidden not in lowered


def test_cross_project_invariant_scorecard_records_structure_not_pass_claim() -> None:
    scorecard = _load_yaml(CROSS_PROJECT_INVARIANT_SCORECARD_PATH)
    text = CROSS_PROJECT_INVARIANT_SCORECARD_PATH.read_text(encoding="utf-8")
    lowered = text.lower()

    assert scorecard["schema_version"] == "capex.cross_project_invariant_scorecard.v1"
    assert scorecard["owner_task"] == "TASK-0593"
    assert scorecard["source_task_id"] == "TP-TASK-005"
    assert scorecard["activation_posture"] == "planning_only_no_capex_activation"
    assert (
        scorecard["no_overfitting_checkpoint_ref"]
        == "NO_OVERFITTING_REVIEW_CHECKPOINT.yaml"
    )
    assert set(scorecard["gate_refs"]) >= {
        "TP-G01",
        "TP-G02",
        "TP-G03",
        "TP-G04",
        "TP-G05",
        "TP-G06",
        "TP-G07",
        "TP-G08",
        "TP-G09",
        "TP-G11",
        "TP-G12",
    }
    assert [row["tier_id"] for row in scorecard["fixture_tiers"]] == [
        "K12",
        "K3_mini",
        "K3_shadow",
        "blind_baseline",
    ]
    assert set(scorecard["status_vocabulary"]) == {
        "not_run",
        "green",
        "red",
        "waived",
        "blocked_pending_evidence",
    }
    assert set(scorecard["waiver_requirements"]["required_fields"]) >= {
        "owner",
        "reason",
        "residual_risk",
        "expiry_or_review_date",
        "affected_invariant_id",
        "affected_fixture_tier",
    }
    assert {row["name"] for row in scorecard["invariant_rows"]} == (
        EXPECTED_SCORECARD_INVARIANTS
    )
    valid_statuses = set(scorecard["status_vocabulary"])
    fixture_tiers = {row["tier_id"] for row in scorecard["fixture_tiers"]}
    for row in scorecard["invariant_rows"]:
        assert row["invariant_id"].startswith("CP-INV-")
        assert row["requirement"]
        assert set(row["tier_statuses"]) == fixture_tiers
        assert set(row["tier_statuses"].values()).issubset(valid_statuses)
        assert set(row["gate_refs"]).issubset(set(scorecard["gate_refs"]))
        assert "green" not in set(row["tier_statuses"].values())
        assert "waived" not in set(row["tier_statuses"].values())

    assert scorecard["rollup_policy"]["current_rollup_status"] == (
        "blocked_pending_evidence"
    )
    assert "not been run or approved" in scorecard["rollup_policy"][
        "current_rollup_reason"
    ]
    assert set(scorecard["cannot_be_used_for"]) >= {
        "capex_runtime_activation",
        "product_activation",
        "public_route_activation",
        "workflow_pack_activation",
        "raw_corpus_import",
        "tp_g11_pass_claim",
        "production_preflight_approval",
        "pilot_readiness_approval",
    }
    assert set(scorecard["raw_data_boundary"]["prohibited_repo_material"]) >= {
        "full project corpus files",
        "unrestricted source excerpts",
        "raw project filenames",
        "screenshots or logs containing source content",
        "project-specific hardcoded logic",
    }
    for forbidden in (
        "tp-g11 passed",
        "product activation approved",
        "runtime activation approved",
        "public route approved",
        "production preflight approved",
    ):
        assert forbidden not in lowered


def test_agent_lab_eval_matrix_is_advisory_only() -> None:
    matrix = _load_yaml(AGENT_LAB_EVAL_MATRIX_PATH)
    text = AGENT_LAB_EVAL_MATRIX_PATH.read_text(encoding="utf-8")
    lowered = text.lower()

    assert matrix["schema_version"] == "capex.agent_lab_eval_matrix.v1"
    assert matrix["owner_task"] == "TASK-0594"
    assert matrix["source_task_id"] == "TP-TASK-006"
    assert matrix["activation_posture"] == "planning_only_no_capex_activation"
    assert (
        matrix["no_overfitting_checkpoint_ref"]
        == "NO_OVERFITTING_REVIEW_CHECKPOINT.yaml"
    )
    assert set(matrix["gate_refs"]) >= {
        "TP-G01",
        "TP-G06",
        "TP-G07",
        "TP-G08",
        "TP-G09",
        "TP-G11",
        "TP-G12",
    }
    assert [row["tier_id"] for row in matrix["fixture_tiers"]] == (
        EXPECTED_AGENT_LAB_TIERS
    )
    expected_refs = {
        "K12_EXPECTED_OUTPUT_MANIFEST.yaml",
        "K3_MINI_FIXTURE_EXPECTATION_CATALOG.yaml",
        "BLIND_VALIDATION_FREEZE_PROTOCOL.yaml",
        "CROSS_PROJECT_INVARIANT_SCORECARD.yaml",
    }
    observed_refs = {
        ref
        for tier in matrix["fixture_tiers"]
        for ref in tier.get("evidence_refs", [])
    }
    assert expected_refs.issubset(observed_refs)
    assert set(matrix["status_vocabulary"]) >= {
        "planning_ready",
        "not_run",
        "advisory_report_recorded",
        "blocked_pending_evidence",
        "blocked_pending_freeze_and_baseline",
        "invalidated_pending_remediation",
    }

    non_authority = matrix["lab_non_authority"]
    assert non_authority["lab_output_authority"] == "advisory_only"
    assert non_authority["official_truth_mutation_allowed"] is False
    assert non_authority["required_tool_action_mode"] == "ToolProposal_until_approved"
    assert set(non_authority["prohibited_direct_outputs"]) >= {
        "official_pointer",
        "approval_response",
        "closure_snapshot",
        "runtime_truth_mutation",
        "fixture_release_approval",
        "public_route_activation",
        "product_activation",
    }

    assert {row["eval_family"] for row in matrix["matrix_rows"]} >= {
        "source_ref_and_evidence_binding",
        "no_false_closure",
        "pointer_and_officialness",
        "raw_leak_scan",
        "no_overfitting_guard",
    }
    valid_tiers = set(EXPECTED_AGENT_LAB_TIERS)
    for row in matrix["matrix_rows"]:
        assert row["matrix_row_id"].startswith("LAB-EVAL-")
        assert set(row["fixture_tiers"]).issubset(valid_tiers)
        assert row["expected_advisory_output"]
        assert row["required_evidence_refs"]
        assert set(row["gate_refs"]).issubset(set(matrix["gate_refs"]))

    assert matrix["rollup_policy"]["current_rollup_status"] == (
        "planning_ready_not_active"
    )
    assert set(matrix["cannot_be_used_for"]) >= {
        "capex_runtime_activation",
        "product_activation",
        "public_route_activation",
        "workflow_pack_activation",
        "raw_corpus_import",
        "fixture_release_approval",
        "official_pointer_creation",
        "approval_response_creation",
        "closure_snapshot_creation",
        "production_preflight_approval",
        "pilot_readiness_approval",
    }
    for forbidden in (
        "product activation approved",
        "runtime activation approved",
        "public route approved",
        "official pointer created",
        "approval response created",
        "production preflight approved",
    ):
        assert forbidden not in lowered


def test_off_repo_full_corpus_runbook_keeps_raw_data_off_repo() -> None:
    runbook = _load_yaml(OFF_REPO_FULL_CORPUS_RUNBOOK_PATH)
    text = OFF_REPO_FULL_CORPUS_RUNBOOK_PATH.read_text(encoding="utf-8")
    lowered = text.lower()

    assert runbook["schema_version"] == "capex.off_repo_full_corpus_runbook.v1"
    assert runbook["owner_task"] == "TASK-0595"
    assert runbook["source_task_id"] == "TP-TASK-007"
    assert runbook["activation_posture"] == "planning_only_no_capex_activation"
    assert set(runbook["gate_refs"]) >= {
        "TP-G01",
        "TP-G10",
        "TP-G11",
        "TP-G12",
    }
    assert set(runbook["downstream_gate_refs"]) == {
        "PROD-PRE-G06",
        "PROD-PRE-G07",
    }
    assert (
        runbook["run_scope"]["raw_corpus_location_policy"]
        == "off_repo_operator_owned_quarantine"
    )
    assert runbook["run_scope"]["default_run_mode"] == "validate_and_report_only"
    assert [row["name"] for row in runbook["workflow_steps"]] == (
        EXPECTED_OFF_REPO_STEPS
    )
    for row in runbook["workflow_steps"]:
        assert row["step_id"].startswith("OFFREPO-")
        assert row["required_controls"]
        assert row["evidence_output"]

    assert runbook["capacity_restore_placeholders"][
        "capacity_realism_status"
    ] == "blocked_pending_evidence"
    assert runbook["capacity_restore_placeholders"][
        "backup_restore_status"
    ] == "blocked_pending_evidence"
    assert set(runbook["capacity_restore_placeholders"][
        "required_before_tp_g10_claim"
    ]) >= {
        "full_off_repo_corpus_run_report",
        "extraction_projection_search_summary",
        "backup_manifest",
        "restore_rehearsal_report",
        "no_raw_leakage_report",
    }
    assert set(runbook["cannot_be_used_for"]) >= {
        "capex_runtime_activation",
        "product_activation",
        "public_route_activation",
        "workflow_pack_activation",
        "raw_corpus_import",
        "fixture_release_approval",
        "tp_g10_pass_claim",
        "production_preflight_approval",
        "pilot_readiness_approval",
    }
    assert set(runbook["raw_data_boundary"]["allowed_repo_material"]) >= {
        "package basenames and digests",
        "aggregate counts",
        "sanitized status summaries",
        "leak-scan pass/fail summaries",
        "operator attestations",
        "rollback and remediation notes",
    }
    assert set(runbook["raw_data_boundary"]["prohibited_repo_material"]) >= {
        "full project corpus files",
        "unrestricted source excerpts",
        "raw project filenames",
        "screenshots or logs containing source content",
        "mounted raw corpus paths",
        "project-specific hardcoded logic",
    }
    for forbidden in (
        "raw corpus import approved",
        "tp-g10 passed",
        "production preflight approved",
        "pilot readiness approved",
        "product activation approved",
    ):
        assert forbidden not in lowered


def test_no_overfitting_review_checkpoint_is_blocked_until_blind_baseline() -> None:
    checkpoint = _load_yaml(NO_OVERFITTING_REVIEW_CHECKPOINT_PATH)
    text = NO_OVERFITTING_REVIEW_CHECKPOINT_PATH.read_text(encoding="utf-8")
    lowered = text.lower()

    assert (
        checkpoint["schema_version"]
        == "capex.no_overfitting_review_checkpoint.v1"
    )
    assert checkpoint["owner_task"] == "TASK-0596"
    assert checkpoint["source_task_id"] == "TP-TASK-008"
    assert checkpoint["activation_posture"] == "planning_only_no_capex_activation"
    assert checkpoint["status"] == "blocked_pending_blind_baseline_evidence"
    assert set(checkpoint["gate_refs"]) >= {
        "TP-G01",
        "TP-G07",
        "TP-G08",
        "TP-G09",
        "TP-G11",
        "TP-G12",
    }
    assert set(checkpoint["depends_on_evidence"]) >= {
        "BLIND_VALIDATION_FREEZE_PROTOCOL.yaml",
        "CROSS_PROJECT_INVARIANT_SCORECARD.yaml",
        "AGENT_LAB_EVAL_MATRIX.yaml",
        "OFF_REPO_FULL_CORPUS_RUNBOOK.yaml",
    }
    assert set(checkpoint["checkpoint_record_required_fields"]) >= {
        "blind_baseline_ref",
        "changed_surface",
        "affected_fixture_tiers",
        "evidence_refs",
        "reviewer",
        "decision",
        "rollback_remediation",
        "classification",
    }
    assert set(checkpoint["classification_vocabulary"]) == (
        EXPECTED_NO_OVERFITTING_CLASSIFICATIONS
    )
    assert set(checkpoint["affected_fixture_tiers"]) == set(
        EXPECTED_PROJECT_ORACLE_TIERS
    )
    observed_classifications = {
        row["required_classification"] for row in checkpoint["checkpoint_rows"]
    }
    assert observed_classifications == EXPECTED_NO_OVERFITTING_CLASSIFICATIONS
    for row in checkpoint["checkpoint_rows"]:
        assert row["checkpoint_row_id"].startswith("NO-OVERFIT-")
        assert row["changed_surface"]
        assert row["required_evidence_refs"]
        assert row["expected_decision"] in checkpoint["decision_vocabulary"]
        assert row["rollback_remediation"]
        assert set(row["tp_gate_refs"]).issubset(set(checkpoint["gate_refs"]))

    assert checkpoint["rollup_policy"]["current_rollup_status"] == (
        "blocked_pending_blind_baseline_evidence"
    )
    assert set(checkpoint["cannot_be_used_for"]) >= {
        "capex_runtime_activation",
        "product_activation",
        "public_route_activation",
        "workflow_pack_activation",
        "raw_corpus_import",
        "fixture_release_approval",
        "blind_tuning_approval",
        "tp_g08_pass_claim",
        "production_preflight_approval",
        "pilot_readiness_approval",
    }
    assert set(checkpoint["raw_data_boundary"]["prohibited_repo_material"]) >= {
        "full project corpus files",
        "unrestricted source excerpts",
        "raw project filenames",
        "screenshots or logs containing source content",
        "project-specific hardcoded logic",
    }
    for forbidden in (
        "fixture release approved",
        "blind tuning approved",
        "tp-g08 passed",
        "product activation approved",
        "runtime activation approved",
        "public route approved",
        "production preflight approved",
        "pilot readiness approved",
    ):
        assert forbidden not in lowered


def test_project_oracle_manifest_format_is_cross_tier_planning_contract() -> None:
    oracle_format = _load_yaml(PROJECT_ORACLE_MANIFEST_FORMAT_PATH)
    text = PROJECT_ORACLE_MANIFEST_FORMAT_PATH.read_text(encoding="utf-8")
    lowered = text.lower()

    assert (
        oracle_format["schema_version"]
        == "capex.project_oracle_manifest_format.v1"
    )
    assert oracle_format["owner_task"] == "TASK-0597"
    assert oracle_format["source_task_id"] == "TP-TASK-009"
    assert oracle_format["activation_posture"] == (
        "planning_only_no_capex_activation"
    )
    assert oracle_format["fixture_tiers"] == EXPECTED_PROJECT_ORACLE_TIERS
    assert set(oracle_format["gate_refs"]) >= {
        "TP-G01",
        "TP-G02",
        "TP-G03",
        "TP-G04",
        "TP-G05",
        "TP-G06",
        "TP-G07",
        "TP-G08",
        "TP-G09",
        "TP-G10",
        "TP-G11",
        "TP-G12",
    }
    assert set(oracle_format["evidence_contract_refs"]) >= {
        "K12_EXPECTED_OUTPUT_MANIFEST.yaml",
        "K3_MINI_FIXTURE_EXPECTATION_CATALOG.yaml",
        "BLIND_VALIDATION_FREEZE_PROTOCOL.yaml",
        "CROSS_PROJECT_INVARIANT_SCORECARD.yaml",
        "AGENT_LAB_EVAL_MATRIX.yaml",
        "OFF_REPO_FULL_CORPUS_RUNBOOK.yaml",
        "NO_OVERFITTING_REVIEW_CHECKPOINT.yaml",
    }
    assert set(oracle_format["required_top_level_fields"]) >= {
        "schema_version",
        "manifest_id",
        "owner_task",
        "source_task_id",
        "fixture_tier",
        "activation_posture",
        "source_evidence",
        "versioning_basis",
        "oracle_rows",
        "human_oracle_approval",
        "raw_data_boundary",
    }
    assert set(oracle_format["required_oracle_row_fields"]) >= {
        "oracle_id",
        "row_family",
        "fixture_tier",
        "source_evidence_refs",
        "expected_behavior",
        "expected_result",
        "failure_condition",
        "tp_gate_refs",
        "automation_posture",
        "human_review_posture",
        "rollback_remediation",
        "versioning_basis",
    }
    assert set(oracle_format["row_family_vocabulary"]) == (
        EXPECTED_PROJECT_ORACLE_ROW_FAMILIES
    )
    observed_families = {
        row["row_family"] for row in oracle_format["example_oracle_rows"]
    }
    assert observed_families == EXPECTED_PROJECT_ORACLE_ROW_FAMILIES
    for row in oracle_format["example_oracle_rows"]:
        assert row["oracle_id"].startswith("ORACLE-FORMAT-")
        assert row["fixture_tier"] in EXPECTED_PROJECT_ORACLE_TIERS
        assert row["source_evidence_refs"]
        assert row["expected_behavior"]
        assert row["expected_result"]
        assert row["failure_condition"]
        assert row["automation_posture"] in oracle_format[
            "automation_posture_vocabulary"
        ]
        assert row["human_review_posture"] in oracle_format[
            "human_review_posture_vocabulary"
        ]
        assert row["rollback_remediation"]
        assert set(row["tp_gate_refs"]).issubset(set(oracle_format["gate_refs"]))
        assert set(row["versioning_basis"]) == set(
            oracle_format["versioning_basis_fields"]
        )

    approval = oracle_format["human_oracle_approval_contract"]
    assert approval["approval_authority"] == "planning_evidence_only"
    assert set(approval["required_fields"]) >= {
        "reviewer",
        "review_date",
        "decision",
        "source_evidence_refs",
        "residual_risk",
        "rollback_remediation",
    }
    assert set(oracle_format["cannot_be_used_for"]) >= {
        "capex_runtime_activation",
        "product_activation",
        "public_route_activation",
        "workflow_pack_activation",
        "raw_corpus_import",
        "fixture_release_approval",
        "official_pointer_creation",
        "approval_response_creation",
        "closure_snapshot_creation",
        "production_preflight_approval",
        "pilot_readiness_approval",
    }
    assert set(oracle_format["raw_data_boundary"]["prohibited_repo_material"]) >= {
        "full project corpus files",
        "unrestricted source excerpts",
        "raw project filenames",
        "screenshots or logs containing source content",
        "project-specific hardcoded logic",
    }

    k12_manifest = _load_yaml(K12_EXPECTED_OUTPUT_MANIFEST_PATH)
    k3_catalog = _load_yaml(K3_MINI_FIXTURE_EXPECTATION_CATALOG_PATH)
    assert k12_manifest["oracle_format_ref"] == "PROJECT_ORACLE_MANIFEST_FORMAT.yaml"
    assert k3_catalog["oracle_format_ref"] == "PROJECT_ORACLE_MANIFEST_FORMAT.yaml"
    for forbidden in (
        "raw corpus import approved",
        "fixture release approved",
        "official pointer created",
        "approval response created",
        "product activation approved",
        "runtime activation approved",
        "public route approved",
        "production preflight approved",
    ):
        assert forbidden not in lowered


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
