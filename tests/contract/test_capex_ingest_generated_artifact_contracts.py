from __future__ import annotations

import json
import re
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[2]
INGEST_CONTRACT_PATH = (
    ROOT
    / "docs/planning/capex_source_ingest/"
    "BULK_STAGED_CORPUS_INGEST_ARCHITECTURE.yaml"
)
GENERATED_ARTIFACT_CONTRACT_PATH = (
    ROOT
    / "docs/planning/capex_generated_artifacts/"
    "GENERATED_ARTIFACT_ENVELOPE_CONTRACT.yaml"
)
SOURCE_INVENTORY_CONTRACT_PATH = (
    ROOT
    / "docs/planning/capex_source_ingest/"
    "SOURCE_INVENTORY_PIPELINE_CONTRACT.yaml"
)
SOURCE_OCCURRENCE_REGISTER_CONTRACT_PATH = (
    ROOT
    / "docs/planning/capex_source_ingest/"
    "SOURCE_OCCURRENCE_REGISTER_CONTRACT.yaml"
)
ROLE_PACKET_REGISTER_CONTRACT_PATH = (
    ROOT
    / "docs/planning/capex_source_ingest/"
    "ROLE_PACKET_REGISTER_CONTRACT.yaml"
)
GENERATED_ARTIFACT_VALIDATOR_CONTRACT_PATH = (
    ROOT
    / "docs/planning/capex_generated_artifacts/"
    "GENERATED_ARTIFACT_VALIDATOR_CONTRACT.yaml"
)
CORPUS_BASELINE_WORKFLOW_PATH = (
    ROOT
    / "docs/planning/capex_workflow_catalog/"
    "corpus_baseline_workflow.yaml"
)
GENERATED_ARTIFACT_SCHEMA_PATH = (
    ROOT / "schemas/runtime/capex_generated_artifact_envelope.schema.json"
)
TASK_DIR = ROOT / "codex/tasks"
FRONTMATTER_RE = re.compile(r"\A---\n(?P<body>.*?)\n---\n", re.DOTALL)


def _load_yaml(path: Path) -> dict:
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def _frontmatter(task_id: str) -> dict[str, str]:
    [path] = sorted(TASK_DIR.glob(f"{task_id}-*.md"))
    match = FRONTMATTER_RE.match(path.read_text(encoding="utf-8"))
    assert match is not None
    values: dict[str, str] = {}
    for line in match.group("body").splitlines():
        if ":" not in line or line.startswith(" "):
            continue
        key, value = line.split(":", 1)
        values[key.strip()] = value.strip().strip('"')
    return values


def test_bulk_staged_corpus_ingest_architecture_is_planning_only_and_manifest_first() -> None:
    contract = _load_yaml(INGEST_CONTRACT_PATH)

    assert contract["owner_task"] == "TASK-0266"
    assert contract["source_row"] == "INGEST-001"
    assert contract["activation_posture"] == "planning_only_no_capex_activation"
    assert contract["overall_status"] == "architecture_recorded_not_activated"
    assert contract["body_limit_policy"]["json_base64_command_route_allowed"] is False
    assert contract["body_limit_policy"]["inline_raw_content_allowed"] is False
    assert set(contract["source_inventory_descriptor_fields"]["optional_until_TASK_0267"]) == {
        "content_digest",
        "content_byte_size",
        "content_media_type",
        "canonicalization_profile",
    }
    assert {mode["mode"] for mode in contract["staged_ingest_modes"]} == {
        "object_store_manifest",
        "folder_manifest",
        "source_root_snapshot",
    }
    assert [
        phase["phase_id"] for phase in contract["manifest_first_phases"]
    ] == [
        "project_authorization_precheck",
        "sanitized_descriptor_submission",
        "staged_object_or_folder_registration",
        "quarantine_and_leak_scan_handoff",
        "source_inventory_handoff",
    ]


def test_bulk_staged_corpus_ingest_contract_does_not_activate_raw_or_truth_surfaces() -> None:
    contract = _load_yaml(INGEST_CONTRACT_PATH)

    assert {
        "upload_endpoint",
        "blob_storage_activation",
        "source_occurrence_creation",
        "source_inventory_artifact",
        "public_api_route",
        "frontend_route",
    } <= set(contract["not_implemented_in_this_task"])
    assert {
        "raw_corpus_import",
        "json_base64_command_route",
        "source_occurrence_binding",
        "reviewed_baseline_creation",
        "official_pointer_creation",
        "capex_runtime_activation",
        "product_activation",
    } <= set(contract["cannot_be_used_for"])
    assert "full_project_corpus_files" in contract["raw_data_boundary"][
        "prohibited_repo_material"
    ]


def test_generated_artifact_envelope_contract_points_to_schema_and_unblocks_intake() -> None:
    contract = _load_yaml(GENERATED_ARTIFACT_CONTRACT_PATH)
    schema = json.loads(GENERATED_ARTIFACT_SCHEMA_PATH.read_text(encoding="utf-8"))

    assert contract["owner_task"] == "TASK-0276"
    assert contract["source_row"] == "ART-001"
    assert contract["activation_posture"] == "planning_only_no_capex_activation"
    assert contract["canonical_envelope"]["schema_ref"] == (
        "schemas/runtime/capex_generated_artifact_envelope.schema.json"
    )
    assert contract["canonical_envelope"]["required_fields"] == schema["required"]
    assert contract["canonical_naming"]["file_name_pattern"] == (
        "capex.<family>.<artifact>.vN.json"
    )
    assert contract["source_ref_policy"]["later_enforcement_task"] == "TASK-0279"
    assert contract["source_ref_policy"]["pre_occurrence_exception"] == {
        "artifact_kind": "capex.source_inventory",
        "validation_result": "inventory_pre_source_occurrence",
        "reason": "TASK-0267 records content identity before TASK-0268 source occurrence binding.",
    }
    assert "TASK-0283" in contract["unblocks"]


def test_source_inventory_pipeline_contract_is_pre_occurrence_and_raw_safe() -> None:
    contract = _load_yaml(SOURCE_INVENTORY_CONTRACT_PATH)

    assert contract["owner_task"] == "TASK-0267"
    assert contract["source_row"] == "INGEST-002"
    assert contract["activation_posture"] == "planning_only_no_capex_activation"
    assert contract["source_inventory_artifact"]["artifact_kind"] == "capex.source_inventory"
    assert contract["source_inventory_artifact"]["file_name"] == (
        "capex.source_inventory.v1.json"
    )
    assert contract["source_inventory_artifact"]["validation_result"] == (
        "inventory_pre_source_occurrence"
    )
    assert contract["digest_store"]["repository"] == "capex_content_identities"
    assert contract["digest_store"]["source_occurrence_creation"] is False
    assert contract["dedupe_policy"]["same_bytes_multiple_descriptors"] == (
        "one_content_identity_many_inventory_items"
    )
    assert {
        "source_occurrence_binding",
        "raw_corpus_import",
        "reviewed_baseline_creation",
        "official_pointer_creation",
        "capex_runtime_activation",
        "product_activation",
    } <= set(contract["cannot_be_used_for"])


def test_source_occurrence_register_contract_separates_occurrence_from_roles() -> None:
    contract = _load_yaml(SOURCE_OCCURRENCE_REGISTER_CONTRACT_PATH)

    assert contract["owner_task"] == "TASK-0268"
    assert contract["source_row"] == "INGEST-003"
    assert contract["activation_posture"] == "planning_only_no_capex_activation"
    assert contract["register_output"]["artifact_kind"] == (
        "capex.source_occurrence_register"
    )
    assert contract["register_output"]["row_count_must_match_physical_rows"] is True
    assert contract["register_output"]["snapshot_digest_must_match_physical_rows"] is True
    assert contract["occurrence_identity_policy"]["content_identity_not_occurrence"] is True
    assert contract["occurrence_identity_policy"]["occurrence_not_role"] is True
    assert contract["occurrence_identity_policy"]["role_assignment_task"] == "TASK-0269"
    assert contract["truth_effects"] == {
        "creates_source_occurrences": True,
        "creates_role_assignments": False,
        "creates_packet_register": False,
        "writes_artifacts_by_default": False,
        "promotes_official_pointers": False,
        "activates_workflow_pack": False,
    }
    assert {
        "raw_corpus_import",
        "role_assignment_approval",
        "packet_register_approval",
        "reviewed_baseline_creation",
        "official_pointer_creation",
        "capex_runtime_activation",
        "product_activation",
    } <= set(contract["cannot_be_used_for"])


def test_generated_artifact_validator_contract_is_non_promotional() -> None:
    contract = _load_yaml(GENERATED_ARTIFACT_VALIDATOR_CONTRACT_PATH)

    assert contract["owner_task"] == "TASK-0278"
    assert contract["source_row"] == "ART-003"
    assert contract["activation_posture"] == "planning_only_no_capex_activation"
    assert contract["validator_scope"] == {
        "schema_validator": True,
        "canonical_name_validator": True,
        "canonical_digest_validator": True,
        "bundle_cross_reference_validator": True,
        "evidence_sufficiency_validator": False,
        "pointer_promotion_policy_validator": False,
    }
    assert {
        "duplicate_canonical_name_rejected",
        "missing_source_ref_rejected",
        "stale_input_digest_rejected",
        "artifact_kind_name_mismatch_rejected",
        "deprecated_name_rejected",
    } <= set(contract["bundle_checks"])
    assert contract["promotion_boundary"] == {
        "schema_valid_is_promotable": False,
        "bundle_valid_is_evidence_sufficient": False,
        "pointer_promotion_policy_task": "TASK-0280",
    }
    assert contract["source_ref_policy"]["meaningful_source_ref_policy_task"] == (
        "TASK-0279"
    )


def test_role_packet_register_contract_closes_task_0269_without_baseline_truth() -> None:
    contract = _load_yaml(ROLE_PACKET_REGISTER_CONTRACT_PATH)

    assert contract["owner_task"] == "TASK-0269"
    assert contract["source_row"] == "INGEST-004"
    assert contract["activation_posture"] == "planning_only_no_capex_activation"
    assert contract["role_assignment_register"]["artifact_kind"] == (
        "capex.role_assignment_register"
    )
    assert contract["packet_register"]["artifact_kind"] == "capex.packet_register"
    assert contract["role_assignment_register"]["ai_draft_is_official"] is False
    assert contract["identity_policy"] == {
        "content_identity_not_occurrence": True,
        "occurrence_not_role": True,
        "role_not_file_identity": True,
        "packet_not_reviewed_baseline": True,
    }
    assert contract["truth_effects"] == {
        "creates_role_assignments": True,
        "creates_packet_register": True,
        "creates_reviewed_baseline": False,
        "writes_artifacts_by_default": False,
        "promotes_official_pointers": False,
        "activates_workflow_pack": False,
    }
    assert {
        "raw_corpus_import",
        "reviewed_baseline_creation",
        "evidence_sufficiency_claim",
        "official_pointer_creation",
        "capex_runtime_activation",
        "product_activation",
    } <= set(contract["cannot_be_used_for"])


def test_corpus_baseline_workflow_contract_is_planning_only_and_unblocked() -> None:
    contract = _load_yaml(CORPUS_BASELINE_WORKFLOW_PATH)

    assert contract["source_task_ref"] == "TASK-0284"
    assert contract["source_row"] == "WFLOW-002"
    assert contract["activation_posture"] == "planning_only_no_capex_activation"
    assert contract["depends_on"]["repo_tasks"] == ["TASK-0269", "TASK-0278"]
    assert contract["workflow_basis"] == {
        "source_inventory_schema_version": "capex.source_inventory.v1",
        "source_occurrence_register_schema_version": "capex.source_occurrence_register.v1",
        "role_assignment_register_schema_version": "capex.role_assignment_register.v1",
        "packet_register_schema_version": "capex.packet_register.v1",
        "generated_artifact_bundle_schema_version": "capex.generated_artifact_bundle.v1",
    }
    assert contract["generated_artifact_contract"]["canonical_names"] == [
        "capex.role_assignment_register.v1.json",
        "capex.packet_register.v1.json",
    ]
    assert contract["truth_effects"] == {
        "creates_workflow_run": False,
        "creates_reviewed_baseline": False,
        "writes_artifacts": False,
        "promotes_official_pointers": False,
        "activates_workflow_pack": False,
    }
    assert {
        "authored_workflow_pack",
        "public_api_route",
        "frontend_route",
        "workpage_route",
        "reviewed_baseline_creation",
        "official_pointer_creation",
    } <= set(contract["not_implemented_in_this_task"])


def test_task_0267_0268_0269_0278_0283_and_0284_close_after_unblocker_pairs() -> None:
    task_0267 = _frontmatter("TASK-0267")
    task_0268 = _frontmatter("TASK-0268")
    task_0269 = _frontmatter("TASK-0269")
    task_0276 = _frontmatter("TASK-0276")
    task_0278 = _frontmatter("TASK-0278")
    task_0283 = _frontmatter("TASK-0283")
    task_0284 = _frontmatter("TASK-0284")
    task_0285 = _frontmatter("TASK-0285")

    assert task_0267["status"] == "DONE"
    assert task_0267["completed_at"] == "2026-06-17T00:00:00Z"
    assert task_0268["status"] == "DONE"
    assert task_0268["completed_at"] == "2026-06-17T00:00:00Z"
    assert task_0269["status"] == "DONE"
    assert task_0269["completed_at"] == "2026-06-17T00:00:00Z"
    assert task_0276["status"] == "DONE"
    assert task_0276["completed_at"] == "2026-06-17T00:00:00Z"
    assert task_0278["status"] == "DONE"
    assert task_0278["completed_at"] == "2026-06-17T00:00:00Z"
    assert task_0283["status"] == "DONE"
    assert task_0283["completed_at"] == "2026-06-17T00:00:00Z"
    assert "TASK-0276" in task_0283["depends_on"]
    assert task_0284["status"] == "DONE"
    assert task_0284["completed_at"] == "2026-06-17T00:00:00Z"
    assert "TASK-0269" in task_0284["depends_on"]
    assert "TASK-0278" in task_0284["depends_on"]
    assert task_0285["status"] == "TODO"
    assert "TASK-0284" in task_0285["depends_on"]


def test_generated_artifact_contract_does_not_claim_policy_or_activation_approval() -> None:
    contract = _load_yaml(GENERATED_ARTIFACT_CONTRACT_PATH)

    assert {
        "bundle_validator",
        "pointer_promotion_policy",
        "evidence_sufficiency_policy",
        "meaningful_sourceref_resolution_policy",
        "public_api_route",
        "frontend_route",
    } <= set(contract["not_implemented_in_this_task"])
    assert {
        "workflow_pack_activation",
        "raw_corpus_import",
        "evidence_sufficiency_claim",
        "reviewed_baseline_creation",
        "official_pointer_creation",
        "capex_runtime_activation",
        "product_activation",
    } <= set(contract["cannot_be_used_for"])
