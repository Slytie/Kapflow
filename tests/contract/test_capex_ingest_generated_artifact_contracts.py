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
DOCUMENT_MANIFEST_CONTRACT_PATH = (
    ROOT
    / "docs/planning/capex_source_ingest/"
    "DOCUMENT_MANIFEST_CONTRACT.yaml"
)
TEXT_EXTRACTION_PAGE_MANIFEST_CONTRACT_PATH = (
    ROOT
    / "docs/planning/capex_source_ingest/"
    "TEXT_EXTRACTION_PAGE_MANIFEST_CONTRACT.yaml"
)
CHUNK_SEARCH_EVIDENCE_BINDING_CONTRACT_PATH = (
    ROOT
    / "docs/planning/capex_source_ingest/"
    "CHUNK_SEARCH_EVIDENCE_BINDING_INDEX_CONTRACT.yaml"
)
BATCH_ARTIFACT_LINK_PROVENANCE_CONTRACT_PATH = (
    ROOT
    / "docs/planning/capex_source_ingest/"
    "BATCH_ARTIFACT_LINK_PROVENANCE_HYDRATION_CONTRACT.yaml"
)
ASYNC_DOCUMENT_PROCESSING_JOB_RUNTIME_CONTRACT_PATH = (
    ROOT
    / "docs/planning/capex_source_ingest/"
    "ASYNC_DOCUMENT_PROCESSING_JOB_RUNTIME_CONTRACT.yaml"
)
CONTENT_IDENTITY_SOURCE_OCCURRENCE_RECONCILIATION_PATH = (
    ROOT
    / "docs/planning/capex_source_ingest/"
    "CONTENT_IDENTITY_SOURCE_OCCURRENCE_RUNTIME_SCHEMA_RECONCILIATION.yaml"
)
SOURCE_OCCURRENCE_RELATION_CONTRACT_PATH = (
    ROOT
    / "docs/planning/capex_source_ingest/"
    "SOURCE_OCCURRENCE_RELATION_CONTRACT.yaml"
)
INGEST_JOB_STATE_MODEL_CONTRACT_PATH = (
    ROOT
    / "docs/planning/capex_source_ingest/"
    "INGEST_JOB_STATE_MODEL_CONTRACT.yaml"
)
ARCHIVE_LINEAGE_METADATA_CONTRACT_PATH = (
    ROOT
    / "docs/planning/capex_source_ingest/"
    "ARCHIVE_LINEAGE_METADATA_CONTRACT.yaml"
)
MANIFEST_GENERATION_ATTESTATION_CONTRACT_PATH = (
    ROOT
    / "docs/planning/capex_source_ingest/"
    "MANIFEST_GENERATION_ATTESTATION_CONTRACT.yaml"
)
COMMAND_RECEIPT_CANONICAL_INPUT_CONTRACT_PATH = (
    ROOT
    / "docs/planning/capex_source_ingest/"
    "COMMAND_RECEIPT_CANONICAL_INPUT_CONTRACT.yaml"
)
EFFECT_LEDGER_GUARDED_MUTATION_CONTRACT_PATH = (
    ROOT
    / "docs/planning/capex_source_ingest/"
    "EFFECT_LEDGER_GUARDED_MUTATION_CONTRACT.yaml"
)
TOOL_EXECUTION_ATTEMPT_RUNTIME_CONTRACT_PATH = (
    ROOT
    / "docs/planning/capex_source_ingest/"
    "TOOL_EXECUTION_ATTEMPT_RUNTIME_CONTRACT.yaml"
)
PROJECT_CONCURRENCY_RUNTIME_SLOT_CONTRACT_PATH = (
    ROOT
    / "docs/planning/capex_source_ingest/"
    "PROJECT_CONCURRENCY_RUNTIME_SLOT_CONTRACT.yaml"
)
RUNTIME_OUTBOX_AFTER_COMMIT_CONTRACT_PATH = (
    ROOT
    / "docs/planning/capex_source_ingest/"
    "RUNTIME_OUTBOX_AFTER_COMMIT_CONTRACT.yaml"
)
ARTIFACT_VERSION_IDENTITY_CONTRACT_PATH = (
    ROOT
    / "docs/planning/capex_source_ingest/"
    "ARTIFACT_VERSION_IDENTITY_CONTRACT.yaml"
)
GENERATED_ARTIFACT_VALIDATOR_CONTRACT_PATH = (
    ROOT
    / "docs/planning/capex_generated_artifacts/"
    "GENERATED_ARTIFACT_VALIDATOR_CONTRACT.yaml"
)
CEO_TRANSPARENCY_SNAPSHOT_CONTRACT_PATH = (
    ROOT
    / "docs/planning/capex_generated_artifacts/"
    "CEO_TRANSPARENCY_SNAPSHOT_CONTRACT.yaml"
)
CEO_TRANSPARENCY_FRESHNESS_CONTRACT_PATH = (
    ROOT
    / "docs/planning/capex_transparency/"
    "CEO_TRANSPARENCY_SNAPSHOT_W8_FRESHNESS_CONTRACT.yaml"
)
CORPUS_BASELINE_WORKFLOW_PATH = (
    ROOT
    / "docs/planning/capex_workflow_catalog/"
    "corpus_baseline_workflow.yaml"
)
GENERATED_ARTIFACT_SCHEMA_PATH = (
    ROOT / "schemas/runtime/capex_generated_artifact_envelope.schema.json"
)
CEO_TRANSPARENCY_SCHEMA_PATH = (
    ROOT / "schemas/runtime/capex_ceo_transparency_snapshot.schema.json"
)
CEO_TRANSPARENCY_FRESHNESS_SCHEMA_PATH = (
    ROOT / "schemas/runtime/capex_ceo_transparency_snapshot_freshness.schema.json"
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
    assert contract["rf_closeout_surface"] == {
        "owner_task": "TASK-0374",
        "source_row": "RF-006",
        "adapter_helper": "onetruth.capex_platform.bulk_ingest_adapter_seam",
        "interface_kind": "staged_descriptor_manifest",
        "wraps_planner": (
            "onetruth.capex_platform.staged_corpus_ingest.plan_staged_corpus_ingest"
        ),
        "descriptor_modes": [
            "object_store_manifest",
            "folder_manifest",
            "source_root_snapshot",
        ],
        "boundary_policy": {
            "raw_corpus_import": False,
            "json_base64_artifact_route_used": False,
            "local_source_path_artifact_route_used": False,
            "artifact_ingest_command_used": False,
            "artifact_ingress_descriptor_request_bytes_used": False,
            "source_occurrence_creation": False,
            "artifact_version_creation": False,
            "official_pointer_creation": False,
            "public_route_added": False,
            "frontend_route_added": False,
        },
        "deterministic_evidence": {
            "descriptor_fingerprint_required": True,
            "idempotency_key_required": True,
            "adapter_request_id_required": True,
            "duplicate_descriptor_ids_rejected": True,
            "canonical_output_digest_helper": "bulk_ingest_adapter_seam_digest",
        },
    }


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


def test_ceo_transparency_snapshot_contract_closes_task_0277_without_activation() -> None:
    contract = _load_yaml(CEO_TRANSPARENCY_SNAPSHOT_CONTRACT_PATH)
    schema = json.loads(CEO_TRANSPARENCY_SCHEMA_PATH.read_text(encoding="utf-8"))

    assert contract["owner_task"] == "TASK-0277"
    assert contract["source_row"] == "ART-002"
    assert contract["activation_posture"] == "planning_only_no_capex_activation"
    assert contract["depends_on"]["repo_tasks"] == ["TASK-0276"]
    assert contract["generated_artifact"] == {
        "artifact_kind": "capex.ceo_transparency_snapshot",
        "artifact_role": "snapshot",
        "file_name": "capex.ceo_transparency_snapshot.v1.json",
        "schema_version": "capex.ceo_transparency_snapshot.v1",
        "schema_ref": "schemas/runtime/capex_ceo_transparency_snapshot.schema.json",
        "canonical_envelope_schema_version": "capex.generated_artifact_envelope.v1",
    }
    assert schema["properties"]["schema_version"]["const"] == (
        "capex.ceo_transparency_snapshot.v1"
    )
    assert contract["forecastability_policy"] == {
        "grades": ["forecastable", "bounded_uncertainty", "not_forecastable"],
        "false_precision_allowed": False,
        "not_forecastable_blocks_exact_date_cost_percent": True,
        "exact_forecast_fields_require_forecastable": True,
        "ceo_snapshot_reports_blockers_without_inventing_dates_or_costs": True,
    }
    assert contract["ceo_safe_output_policy"] == {
        "source_refs_required": True,
        "input_digests_required": True,
        "drilldown_refs_required": True,
        "raw_ai_text_allowed": False,
        "raw_corpus_fields_allowed": False,
        "unrestricted_excerpts_allowed": False,
        "external_status_sets_official_state": False,
        "generated_material_is_source_authority": False,
    }
    assert contract["truth_effects"] == {
        "creates_workflow_run": False,
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
        "official_pointer_creation",
        "W8_snapshot_freshness_contract",
        "RiskSignal_contract",
    } <= set(contract["not_implemented_in_this_task"])
    assert {
        "raw_corpus_import",
        "ceo_cockpit_activation",
        "runtime_risk_engine_activation",
        "closure_snapshot_creation",
        "official_project_state",
        "official_pointer_creation",
        "capex_runtime_activation",
        "product_activation",
    } <= set(contract["cannot_be_used_for"])


def test_ceo_transparency_w8_freshness_contract_is_companion_schema_only() -> None:
    contract = _load_yaml(CEO_TRANSPARENCY_FRESHNESS_CONTRACT_PATH)
    schema = json.loads(CEO_TRANSPARENCY_FRESHNESS_SCHEMA_PATH.read_text(encoding="utf-8"))

    assert contract["owner_task"] == "TASK-0540"
    assert contract["source_row"] == "ARCH-W8-S04"
    assert contract["activation_posture"] == "planning_only_no_capex_activation"
    assert contract["depends_on"]["repo_tasks"] == ["TASK-0277", "TASK-0290"]
    assert contract["depends_on"]["optional_repo_tasks"] == ["TASK-0539"]
    assert contract["existing_snapshot_policy"] == {
        "replaces_capex_ceo_transparency_snapshot_v1": False,
        "companion_payload_schema_version": (
            "capex.ceo_transparency_snapshot_freshness.v1"
        ),
        "schema_ref": (
            "schemas/runtime/capex_ceo_transparency_snapshot_freshness.schema.json"
        ),
    }
    assert schema["properties"]["schema_version"]["const"] == (
        "capex.ceo_transparency_snapshot_freshness.v1"
    )
    assert contract["freshness_policy"] == {
        "stale_pointer_caveats_propagate": True,
        "missing_evidence_caveats_propagate": True,
        "evidence_conflict_caveats_propagate": True,
        "ai_draft_only_caveats_propagate": True,
        "waiver_caveats_remain_visible": True,
        "false_precision_allowed_when_not_forecastable": False,
        "exact_date_cost_percent_without_forecastability_allowed": False,
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
    assert {
        "runtime_risk_engine",
        "ceo_cockpit",
        "public_api_route",
        "frontend_route",
        "official_pointer_creation",
        "replacement_of_capex_ceo_transparency_snapshot_v1",
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


def test_document_manifest_contract_closes_task_0270_without_extraction_runtime() -> None:
    contract = _load_yaml(DOCUMENT_MANIFEST_CONTRACT_PATH)

    assert contract["owner_task"] == "TASK-0270"
    assert contract["source_row"] == "INGEST-005"
    assert contract["activation_posture"] == "planning_only_no_capex_activation"
    assert contract["document_manifest"]["artifact_kind"] == "capex.document_manifest"
    assert contract["extraction_state_register"]["artifact_kind"] == (
        "capex.extraction_state_register"
    )
    assert set(contract["extraction_state_register"]["allowed_statuses"]) == {
        "pending",
        "queued",
        "in_progress",
        "retry_pending",
        "partial",
        "completed",
        "failed",
        "skipped",
    }
    assert contract["privacy_policy"] == {
        "raw_absolute_path_allowed": False,
        "raw_filename_allowed": False,
        "inline_raw_content_allowed": False,
        "base64_content_allowed": False,
        "raw_failure_log_allowed": False,
        "unrestricted_source_excerpt_allowed": False,
    }
    assert contract["truth_effects"] == {
        "creates_extraction_jobs": False,
        "creates_reviewed_evidence": False,
        "writes_artifacts_by_default": False,
        "promotes_official_pointers": False,
        "activates_workflow_pack": False,
    }
    assert {
        "parser_adapter",
        "extraction_runtime",
        "async_job_runtime",
        "page_manifest",
        "chunk_index",
        "evidence_binding_index",
    } <= set(contract["not_implemented_in_this_task"])


def test_text_extraction_page_manifest_contract_closes_task_0271_without_runtime() -> None:
    contract = _load_yaml(TEXT_EXTRACTION_PAGE_MANIFEST_CONTRACT_PATH)

    assert contract["owner_task"] == "TASK-0271"
    assert contract["source_row"] == "INGEST-006"
    assert contract["activation_posture"] == "planning_only_no_capex_activation"
    assert contract["depends_on"]["repo_tasks"] == ["TASK-0270"]
    assert contract["document_text_extract"] == {
        "artifact_kind": "capex.document_text_extract",
        "artifact_role": "evidence",
        "file_name": "capex.document_text_extract.v1.json",
        "schema_version": "capex.document_text_extract.v1",
    }
    assert contract["document_page_manifest"] == {
        "artifact_kind": "capex.document_page_manifest",
        "artifact_role": "evidence",
        "file_name": "capex.document_page_manifest.v1.json",
        "schema_version": "capex.document_page_manifest.v1",
    }
    assert contract["text_policy"] == {
        "inline_raw_text_allowed": False,
        "unrestricted_source_excerpt_allowed": False,
        "text_storage_ref_required": True,
        "text_digest_required": True,
        "page_source_ref_required": True,
        "ocr_optional_and_gated": True,
        "parser_adapter_required_for_runtime": True,
    }
    assert contract["truth_effects"] == {
        "creates_extraction_jobs": False,
        "runs_parser_adapter": False,
        "creates_reviewed_evidence": False,
        "writes_artifacts_by_default": False,
        "promotes_official_pointers": False,
        "activates_workflow_pack": False,
    }
    assert {
        "parser_adapter",
        "extraction_runtime",
        "async_job_runtime",
        "ocr_runtime",
        "chunk_index",
        "search_index",
        "evidence_binding_index",
    } <= set(contract["not_implemented_in_this_task"])
    assert {
        "raw_corpus_import",
        "parser_runtime_activation",
        "evidence_sufficiency_claim",
        "reviewed_baseline_creation",
        "official_pointer_creation",
        "capex_runtime_activation",
        "product_activation",
    } <= set(contract["cannot_be_used_for"])


def test_chunk_search_evidence_binding_contract_closes_task_0272_without_runtime() -> None:
    contract = _load_yaml(CHUNK_SEARCH_EVIDENCE_BINDING_CONTRACT_PATH)

    assert contract["owner_task"] == "TASK-0272"
    assert contract["source_row"] == "INGEST-007"
    assert contract["activation_posture"] == "planning_only_no_capex_activation"
    assert contract["depends_on"]["repo_tasks"] == ["TASK-0271"]
    assert contract["document_chunk_index"] == {
        "artifact_kind": "capex.document_chunk_index",
        "artifact_role": "evidence",
        "file_name": "capex.document_chunk_index.v1.json",
        "schema_version": "capex.document_chunk_index.v1",
    }
    assert contract["document_search_index"] == {
        "artifact_kind": "capex.document_search_index",
        "artifact_role": "evidence",
        "file_name": "capex.document_search_index.v1.json",
        "schema_version": "capex.document_search_index.v1",
    }
    assert contract["evidence_binding_index"] == {
        "artifact_kind": "capex.evidence_binding_index",
        "artifact_role": "evidence",
        "file_name": "capex.evidence_binding_index.v1.json",
        "schema_version": "capex.evidence_binding_index.v1",
    }
    assert contract["index_policy"] == {
        "inline_chunk_text_allowed": False,
        "unrestricted_source_excerpt_allowed": False,
        "chunk_storage_ref_required": True,
        "chunk_digest_required": True,
        "search_projection_digest_required": True,
        "generated_row_ref_shape": "generated_row:<artifact_kind>:<row_id>",
        "evidence_binding_is_reviewed_truth": False,
        "search_latency_runtime_proof_in_scope": False,
    }
    assert contract["truth_effects"] == {
        "creates_search_service": False,
        "creates_vector_store": False,
        "creates_reviewed_evidence": False,
        "writes_artifacts_by_default": False,
        "promotes_official_pointers": False,
        "activates_workflow_pack": False,
    }
    assert {
        "search_runtime",
        "vector_store",
        "retrieval_runtime",
        "evidence_review_runtime",
        "public_api_route",
        "frontend_route",
    } <= set(contract["not_implemented_in_this_task"])
    assert {
        "raw_corpus_import",
        "search_runtime_activation",
        "vector_store_activation",
        "evidence_sufficiency_claim",
        "reviewed_baseline_creation",
        "official_pointer_creation",
        "capex_runtime_activation",
        "product_activation",
    } <= set(contract["cannot_be_used_for"])


def test_batch_artifact_link_provenance_hydration_contract_closes_task_0273() -> None:
    contract = _load_yaml(BATCH_ARTIFACT_LINK_PROVENANCE_CONTRACT_PATH)

    assert contract["owner_task"] == "TASK-0273"
    assert contract["source_row"] == "INGEST-008"
    assert contract["activation_posture"] == "planning_only_no_capex_activation"
    assert contract["acceptance_gates"] == ["AT-SCALE-006"]
    assert contract["performance_surface"]["shared_loader"] == (
        "hydrate_artifact_relations_for_versions"
    )
    assert contract["performance_surface"]["max_page_size"] == 500
    assert contract["rf_closeout_surface"] == {
        "owner_tasks": ["TASK-0372", "TASK-0373"],
        "source_rows": ["RF-004", "RF-005"],
        "workflow_run_page_loader": "list_artifact_versions_page_for_workflow_run_with_relations",
        "subject_page_loader": "list_artifact_versions_page_for_subject_with_relations",
        "route_adapters": {
            "existing_routes_only": True,
            "sql_level_limit_offset": True,
            "artifact_kind_filter_before_page": True,
            "response_envelope_changed": False,
        },
        "optional_subject_summary_hydration": {
            "enabled_by_internal_flag": True,
            "subject_kinds": ["human_task", "flag"],
            "public_payload_required": False,
        },
    }
    assert contract["source_output"] == {
        "batch_loaders": True,
        "paginated_list_detail_split": True,
        "shared_relation_loader": True,
        "query_count_tests_required": True,
        "five_thousand_artifact_evidence_required": True,
    }
    assert contract["query_plan_policy"] == {
        "unbounded_page_reads_allowed": False,
        "n_plus_one_relation_loading_allowed": False,
        "new_migration_required": False,
        "existing_indexes_relied_on": [
            "ix_artifact_versions_project_scope",
            "artifact_links primary key on artifact_version_id",
            "ix_artifact_provenance_edges_output",
        ],
    }
    assert {
        "public_api_route",
        "frontend_route",
        "migration",
        "event_registry_change",
        "raw_corpus_import",
    } <= set(contract["not_implemented_in_this_task"])
    assert {
        "raw_corpus_import",
        "reviewed_baseline_creation",
        "evidence_sufficiency_claim",
        "official_pointer_creation",
        "capex_runtime_activation",
        "product_activation",
    } <= set(contract["cannot_be_used_for"])


def test_async_document_processing_job_runtime_contract_closes_task_0274_without_activation() -> None:
    contract = _load_yaml(ASYNC_DOCUMENT_PROCESSING_JOB_RUNTIME_CONTRACT_PATH)

    assert contract["owner_task"] == "TASK-0274"
    assert contract["source_row"] == "INGEST-009"
    assert contract["activation_posture"] == "planning_only_no_capex_activation"
    assert contract["acceptance_gates"] == ["NU-011", "AT-AI-RETRY-001"]
    assert contract["input_contract"]["command_receipt_substrate"] == (
        "canonical_command_receipts"
    )
    assert contract["input_contract"]["execution_session_substrate"] == (
        "canonical_execution_sessions"
    )
    assert contract["input_contract"]["physical_ingest_job_schema_task"] == "TASK-0393"
    assert contract["document_processing_job_register"] == {
        "artifact_kind": "capex.document_processing_job_register",
        "artifact_role": "evidence",
        "file_name": "capex.document_processing_job_register.v1.json",
        "schema_version": "capex.document_processing_job_register.v1",
    }
    assert contract["document_processing_job_attempt_register"] == {
        "artifact_kind": "capex.document_processing_job_attempt_register",
        "artifact_role": "evidence",
        "file_name": "capex.document_processing_job_attempt_register.v1.json",
        "schema_version": "capex.document_processing_job_attempt_register.v1",
    }
    assert contract["document_processing_job_progress"] == {
        "artifact_kind": "capex.document_processing_job_progress",
        "artifact_role": "evidence",
        "file_name": "capex.document_processing_job_progress.v1.json",
        "schema_version": "capex.document_processing_job_progress.v1",
    }
    assert contract["runtime_policy"] == {
        "retry_reuses_planned_task_refs": True,
        "retry_reuses_planned_artifact_refs": True,
        "command_receipt_required": True,
        "deterministic_idempotency_key_required": True,
        "attempt_numbers_monotonic": True,
        "retry_after_terminal_attempt_allowed": False,
        "cancel_creates_runtime_effect": False,
        "resume_creates_runtime_effect": False,
        "progress_counts_must_be_bounded": True,
        "durable_ingest_job_tables_in_scope": False,
    }
    assert contract["truth_effects"] == {
        "creates_extraction_jobs": False,
        "creates_execution_sessions": False,
        "creates_command_receipts": False,
        "starts_workers": False,
        "runs_parser_adapter": False,
        "writes_artifacts_by_default": False,
        "promotes_official_pointers": False,
        "activates_workflow_pack": False,
    }
    assert {
        "queue_worker",
        "parser_adapter",
        "extraction_runtime",
        "ocr_runtime",
        "durable_ingest_job_tables",
        "migration",
        "event_registry_change",
        "public_api_route",
        "frontend_route",
    } <= set(contract["not_implemented_in_this_task"])
    assert {
        "raw_corpus_import",
        "parser_runtime_activation",
        "ocr_runtime_activation",
        "search_runtime_activation",
        "reviewed_baseline_creation",
        "official_pointer_creation",
        "capex_runtime_activation",
        "product_activation",
    } <= set(contract["cannot_be_used_for"])


def test_content_identity_source_occurrence_schema_is_reconciled_without_duplicate_migration() -> None:
    contract = _load_yaml(CONTENT_IDENTITY_SOURCE_OCCURRENCE_RECONCILIATION_PATH)

    assert contract["owner_task"] == "TASK-0391"
    assert contract["source_row"] == "ARCH-W2-S01"
    assert contract["activation_posture"] == "planning_only_no_capex_activation"
    assert contract["reconciled_by_task"] == "TASK-0564"
    assert contract["duplicate_migration_required"] is False
    assert contract["behavior_change_required"] is False
    assert contract["runtime_state"] == {
        "alembic_revision": (
            "alembic/versions/20260608_0013_capex_source_occurrence_resolver.py"
        ),
        "sqlite_bootstrap_ddl": "src/onetruth/infrastructure/events/event_store.py",
        "sqlalchemy_models": "src/onetruth/infrastructure/db/models.py",
        "repository": (
            "src/onetruth/infrastructure/repositories/capex_source_occurrences.py"
        ),
        "resolver": "src/onetruth/capex_platform/source_refs.py",
        "runtime_schemas": [
            "schemas/runtime/capex_content_identity.schema.json",
            "schemas/runtime/capex_source_occurrence.schema.json",
        ],
    }
    assert contract["required_tables"]["capex_content_identities"][
        "unique_constraints"
    ] == [
        {
            "name": "uq_capex_content_identities_digest",
            "columns": [
                "tenant_id",
                "domain_id",
                "digest_algorithm",
                "content_digest",
            ],
        }
    ]
    assert contract["required_tables"]["capex_source_occurrences"][
        "unique_constraints"
    ] == [
        {
            "name": "uq_capex_source_occurrences_source_ref",
            "columns": ["tenant_id", "domain_id", "source_ref"],
        }
    ]
    assert {
        "ix_capex_content_identities_digest_lookup",
    } == set(contract["required_tables"]["capex_content_identities"]["indexes"])
    assert {
        "ix_capex_source_occurrences_scope_status",
        "ix_capex_source_occurrences_content_identity",
    } == set(contract["required_tables"]["capex_source_occurrences"]["indexes"])
    assert {
        "absolute_path",
        "base64_content",
        "blob_bytes",
        "content_base64",
        "document_text",
        "raw_content",
        "source_path",
    } <= set(contract["raw_data_boundary"]["prohibited_columns"])
    assert {
        "duplicate_migration",
        "source_occurrence_relation",
        "ingest_job_tables",
        "locator_union",
        "extraction_runtime",
        "raw_corpus_import",
    } <= set(contract["not_implemented_in_this_task"])
    assert {
        "capex_runtime_activation",
        "product_activation",
        "raw_corpus_import",
        "reviewed_baseline_creation",
        "official_pointer_creation",
    } <= set(contract["cannot_be_used_for"])


def test_source_occurrence_relation_contract_closes_task_0392_without_activation() -> None:
    contract = _load_yaml(SOURCE_OCCURRENCE_RELATION_CONTRACT_PATH)

    assert contract["owner_task"] == "TASK-0392"
    assert contract["source_row"] == "ARCH-W2-S02"
    assert contract["activation_posture"] == "planning_only_no_capex_activation"
    assert contract["depends_on"]["repo_tasks"] == ["TASK-0391"]
    assert contract["required_runtime_state"] == {
        "alembic_revision": (
            "alembic/versions/20260624_0018_capex_w2_source_relations_ingest_jobs.py"
        ),
        "sqlite_bootstrap_ddl": "src/onetruth/infrastructure/events/event_store.py",
        "sqlalchemy_models": "src/onetruth/infrastructure/db/models.py",
        "repository": (
            "src/onetruth/infrastructure/repositories/"
            "capex_source_occurrence_relations.py"
        ),
        "runtime_schema": "schemas/runtime/capex_source_occurrence_relation.schema.json",
    }
    assert {
        "duplicate_of",
        "archive_contains",
        "archive_member_of",
        "derivative_of",
        "redaction_of",
    } == set(contract["relation_policy"]["allowed_relation_types"])
    assert contract["relation_policy"]["same_tenant_domain_project_required"] is True
    assert contract["relation_policy"]["project_scope_required"] is True
    assert contract["relation_policy"]["self_relation_allowed"] is False
    assert contract["relation_policy"]["duplicate_inverse_active_relation_allowed"] is False
    assert {
        "ix_capex_source_occurrence_relations_source",
        "ix_capex_source_occurrence_relations_target",
        "ix_capex_source_occurrence_relations_scope_type",
    } == set(
        contract["required_table"]["capex_source_occurrence_relations"]["indexes"]
    )
    assert contract["truth_effects"] == {
        "creates_relation_rows": True,
        "creates_source_occurrences": False,
        "creates_content_identities": False,
        "creates_artifact_versions": False,
        "creates_ingest_jobs": False,
        "starts_workers": False,
        "runs_extractor": False,
        "emits_timeline_events": False,
        "promotes_official_pointers": False,
        "activates_workflow_pack": False,
    }
    assert {
        "public_relation_command",
        "public_api_route",
        "frontend_route",
        "locator_union",
        "archive_extraction_runtime",
        "evidence_binding_runtime",
        "raw_corpus_import",
    } <= set(contract["not_implemented_in_this_task"])
    assert {
        "capex_runtime_activation",
        "product_activation",
        "raw_corpus_import",
        "source_locator_union_activation",
        "reviewed_baseline_creation",
        "official_pointer_creation",
    } <= set(contract["cannot_be_used_for"])


def test_ingest_job_state_model_contract_closes_task_0393_without_activation() -> None:
    contract = _load_yaml(INGEST_JOB_STATE_MODEL_CONTRACT_PATH)

    assert contract["owner_task"] == "TASK-0393"
    assert contract["source_row"] == "ARCH-W2-S03"
    assert contract["activation_posture"] == "planning_only_no_capex_activation"
    assert contract["depends_on"]["repo_tasks"] == ["TASK-0391"]
    assert contract["required_runtime_state"] == {
        "alembic_revision": (
            "alembic/versions/20260624_0018_capex_w2_source_relations_ingest_jobs.py"
        ),
        "sqlite_bootstrap_ddl": "src/onetruth/infrastructure/events/event_store.py",
        "sqlalchemy_models": "src/onetruth/infrastructure/db/models.py",
        "repository": "src/onetruth/infrastructure/repositories/capex_ingest_jobs.py",
        "runtime_schemas": [
            "schemas/runtime/capex_ingest_batch.schema.json",
            "schemas/runtime/capex_ingest_job.schema.json",
            "schemas/runtime/capex_ingest_attempt.schema.json",
            "schemas/runtime/capex_ingest_job_log.schema.json",
        ],
    }
    assert contract["state_model_policy"]["same_tenant_domain_project_required"] is True
    assert contract["state_model_policy"]["attempt_numbers_monotonic"] is True
    assert contract["state_model_policy"]["command_receipts_created_by_this_task"] is False
    assert contract["state_model_policy"]["execution_sessions_created_by_this_task"] is False
    assert {
        "capex_ingest_batches",
        "capex_ingest_jobs",
        "capex_ingest_attempts",
        "capex_ingest_job_logs",
    } == set(contract["required_tables"])
    assert contract["truth_effects"] == {
        "creates_ingest_state_rows": True,
        "creates_command_receipts": False,
        "creates_execution_sessions": False,
        "creates_source_occurrences": False,
        "creates_artifact_versions": False,
        "starts_workers": False,
        "enqueues_runtime_jobs": False,
        "runs_parser_adapter": False,
        "emits_timeline_events": False,
        "promotes_official_pointers": False,
        "activates_workflow_pack": False,
    }
    assert {
        "queue_worker",
        "parser_adapter",
        "extraction_runtime",
        "ocr_runtime",
        "search_runtime",
        "public_api_route",
        "frontend_route",
        "upload_route",
        "event_registry_change",
        "raw_corpus_import",
    } <= set(contract["not_implemented_in_this_task"])
    assert {
        "capex_runtime_activation",
        "product_activation",
        "raw_corpus_import",
        "worker_activation",
        "parser_runtime_activation",
        "official_pointer_creation",
    } <= set(contract["cannot_be_used_for"])


def test_archive_lineage_metadata_contract_closes_task_0394_without_activation() -> None:
    contract = _load_yaml(ARCHIVE_LINEAGE_METADATA_CONTRACT_PATH)

    assert contract["owner_task"] == "TASK-0394"
    assert contract["source_row"] == "ARCH-W2-S04"
    assert contract["activation_posture"] == "planning_only_no_capex_activation"
    assert contract["depends_on"]["repo_tasks"] == ["TASK-0392", "TASK-0393"]
    assert contract["helper"] == {
        "module": "onetruth.capex_platform.archive_lineage_metadata",
        "public_function": "build_archive_lineage_metadata_outputs",
        "canonical_bytes_helper": "canonical_archive_lineage_metadata_bytes",
        "digest_helper": "archive_lineage_metadata_digest",
    }
    assert contract["outputs"]["archive_lineage_register"] == {
        "artifact_kind": "capex.archive_lineage_register",
        "artifact_role": "evidence",
        "file_name": "capex.archive_lineage_register.v1.json",
        "schema_version": "capex.archive_lineage_register.v1",
    }
    assert contract["outputs"]["nested_archive_member_metadata"] == {
        "artifact_kind": "capex.nested_archive_member_metadata",
        "artifact_role": "evidence",
        "file_name": "capex.nested_archive_member_metadata.v1.json",
        "schema_version": "capex.nested_archive_member_metadata.v1",
    }
    assert contract["basis_policy"] == {
        "source_occurrence_table": "capex_source_occurrences",
        "source_occurrence_relation_table": "capex_source_occurrence_relations",
        "allowed_relation_types": ["archive_contains", "archive_member_of"],
        "same_tenant_domain_project_required": True,
        "known_source_occurrences_required": True,
        "relation_rows_must_already_exist": True,
        "parent_child_self_relation_allowed": False,
        "archive_containment_cycles_allowed": False,
        "nested_member_depth_checked": True,
    }
    assert contract["metadata_policy"]["metadata_only_first"] is True
    assert contract["metadata_policy"]["full_archive_extractor_required"] is False
    assert contract["metadata_policy"]["raw_filenames_allowed"] is False
    assert contract["metadata_policy"]["absolute_paths_allowed"] is False
    assert contract["metadata_policy"]["inline_text_allowed"] is False
    assert contract["metadata_policy"]["base64_content_allowed"] is False
    assert contract["metadata_policy"]["blob_bytes_allowed"] is False
    assert contract["truth_effects"] == {
        "creates_relation_rows": False,
        "creates_source_occurrences": False,
        "creates_content_identities": False,
        "creates_extraction_jobs": False,
        "starts_workers": False,
        "runs_archive_extractor": False,
        "writes_artifacts_by_default": False,
        "emits_timeline_events": False,
        "promotes_official_pointers": False,
        "activates_workflow_pack": False,
    }
    assert {
        "archive_extraction_runtime",
        "locator_union",
        "parser_adapter",
        "ocr_runtime",
        "search_runtime",
        "public_api_route",
        "frontend_route",
        "event_registry_change",
        "raw_corpus_import",
    } <= set(contract["not_implemented_in_this_task"])
    assert {
        "archive_extraction_runtime_activation",
        "source_locator_union_activation",
        "parser_runtime_activation",
        "reviewed_baseline_creation",
        "official_pointer_creation",
        "capex_runtime_activation",
        "product_activation",
    } <= set(contract["cannot_be_used_for"])


def test_manifest_generation_attestation_contract_closes_task_0395_without_activation() -> None:
    contract = _load_yaml(MANIFEST_GENERATION_ATTESTATION_CONTRACT_PATH)

    assert contract["owner_task"] == "TASK-0395"
    assert contract["source_row"] == "ARCH-W2-S05"
    assert contract["activation_posture"] == "planning_only_no_capex_activation"
    assert contract["depends_on"]["repo_tasks"] == ["TASK-0391", "TASK-0392"]
    assert contract["helper"] == {
        "module": "onetruth.capex_platform.manifest_generation_attestation",
        "public_function": "build_manifest_generation_attestation_outputs",
        "canonical_bytes_helper": "canonical_manifest_generation_attestation_bytes",
        "digest_helper": "manifest_generation_attestation_digest",
    }
    assert contract["outputs"]["generated_corpus_register_manifest"] == {
        "artifact_kind": "capex.generated_corpus_register_manifest",
        "artifact_role": "evidence",
        "file_name": "capex.generated_corpus_register_manifest.v1.json",
        "schema_version": "capex.generated_corpus_register_manifest.v1",
    }
    assert contract["outputs"]["manifest_generation_attestation"] == {
        "artifact_kind": "capex.manifest_generation_attestation",
        "artifact_role": "evidence",
        "file_name": "capex.manifest_generation_attestation.v1.json",
        "schema_version": "capex.manifest_generation_attestation.v1",
    }
    assert contract["basis_policy"] == {
        "generated_from_physical_rows_only": True,
        "allowed_basis_tables": [
            "capex_content_identities",
            "capex_source_occurrences",
            "capex_source_occurrence_relations",
        ],
        "same_tenant_domain_project_required": True,
        "content_identity_scope": "tenant_domain",
        "source_occurrence_scope": "tenant_domain_project",
        "source_refs_must_be_canonical": True,
        "relation_refs_must_be_known": True,
        "input_digests_required": True,
        "generator_config_digest_required": True,
        "deterministic_ordering_required": True,
        "row_digest_required": True,
        "register_digest_required": True,
    }
    assert contract["authority_policy"] == {
        "generated_register_is_source_authority": False,
        "generated_register_can_close_evidence_sufficiency": False,
        "generated_register_can_promote_official_pointer": False,
        "generated_register_can_create_reviewed_baseline": False,
    }
    assert {
        "absolute_path",
        "base64_content",
        "blob_bytes",
        "content_base64",
        "document_text",
        "filename",
        "raw_content",
        "source_path",
    } <= set(contract["raw_data_boundary"]["prohibited_columns"])
    assert contract["truth_effects"] == {
        "creates_content_identities": False,
        "creates_source_occurrences": False,
        "creates_relation_rows": False,
        "creates_ingest_jobs": False,
        "writes_artifacts_by_default": False,
        "emits_timeline_events": False,
        "promotes_official_pointers": False,
        "activates_workflow_pack": False,
    }
    assert {
        "duplicate_migration",
        "raw_corpus_import",
        "parser_adapter",
        "archive_extraction_runtime",
        "locator_union",
        "reviewed_baseline_creation",
        "official_pointer_creation",
        "public_api_route",
        "frontend_route",
        "event_registry_change",
    } <= set(contract["not_implemented_in_this_task"])
    assert {
        "capex_runtime_activation",
        "product_activation",
        "raw_corpus_import",
        "generated_register_as_source_authority",
        "evidence_sufficiency_claim",
        "reviewed_baseline_creation",
        "official_pointer_creation",
    } <= set(contract["cannot_be_used_for"])


def test_command_receipt_canonical_input_contract_closes_task_0396_without_activation() -> None:
    contract = _load_yaml(COMMAND_RECEIPT_CANONICAL_INPUT_CONTRACT_PATH)

    assert contract["owner_task"] == "TASK-0396"
    assert contract["source_row"] == "ARCH-W2-S06"
    assert contract["activation_posture"] == "planning_only_no_capex_activation"
    assert contract["hash_profile"] == {
        "profile_id": "onetruth.command_receipt_input.canonical_json.sha256.v1",
        "digest_format": "sha256:<64 lowercase hex>",
        "canonical_json": {
            "sort_keys": True,
            "separators": [",", ":"],
            "ensure_ascii": True,
            "allow_nan": False,
        },
        "stored_columns": {
            "request_fingerprint": "required_sha256_digest",
            "request_fingerprint_profile": "required_profile_id",
        },
    }
    assert contract["scope_policy"] == {
        "uniqueness_columns": [
            "command_name",
            "scope_key",
            "idempotency_key",
        ],
        "tenant_domain_workflow_scope_preserved": True,
        "same_scope_same_hash_behavior": "replay_stored_result",
        "same_scope_different_hash_error_code": "command_receipt_mismatch",
        "corrupt_stored_hash_or_profile_error_code": "command_receipt_corrupt",
    }
    assert contract["compatibility_policy"] == {
        "legacy_bare_hex_backfill": True,
        "second_receipt_system_allowed": False,
        "public_command_shape_changed": False,
    }
    assert {
        "absolute_path",
        "base64_content",
        "blob_bytes",
        "content_base64",
        "document_text",
        "filename",
        "raw_content",
        "raw_log",
        "source_path",
    } <= set(contract["raw_data_boundary"]["prohibited_material"])
    assert contract["truth_effects"] == {
        "creates_second_receipt_system": False,
        "emits_timeline_events": False,
        "creates_artifact_versions": False,
        "creates_source_occurrences": False,
        "creates_ingest_jobs": False,
        "promotes_official_pointers": False,
        "activates_workflow_pack": False,
    }
    assert {
        "public_api_route",
        "frontend_route",
        "event_registry_change",
        "capex_workflow_activation",
        "raw_corpus_import",
        "official_pointer_creation",
        "reviewed_baseline_creation",
    } <= set(contract["not_implemented_in_this_task"])


def test_effect_ledger_guarded_mutation_contract_closes_task_0397_without_activation() -> None:
    contract = _load_yaml(EFFECT_LEDGER_GUARDED_MUTATION_CONTRACT_PATH)

    assert contract["owner_task"] == "TASK-0397"
    assert contract["source_row"] == "ARCH-W2-S07"
    assert contract["activation_posture"] == "planning_only_no_capex_activation"
    assert contract["depends_on"]["repo_tasks"] == ["TASK-0396"]
    assert contract["required_table"]["effect_ledger_entries"] == {
        "primary_key": ["effect_ledger_entry_id"],
        "unique_constraints": [
            {
                "name": "uq_effect_ledger_command_effect",
                "columns": [
                    "command_name",
                    "scope_key",
                    "idempotency_key",
                    "effect_key",
                ],
            }
        ],
        "indexes": [
            "ix_effect_ledger_entries_scope_status",
            "ix_effect_ledger_entries_target",
            "ix_effect_ledger_entries_workflow_run_id",
        ],
    }
    assert contract["effect_plan_policy"] == {
        "command_receipt_basis_required": True,
        "tenant_domain_scope_required": True,
        "workflow_scope_preserved_when_present": True,
        "deterministic_effect_entry_id_required": True,
        "effect_key_unique_per_command_scope": True,
        "payload_hash_format": "sha256:<64 lowercase hex>",
        "same_effect_key_same_payload_behavior": "replay_applied_effect",
        "same_effect_key_different_payload_error_code": "effect_ledger_conflict",
        "transaction_rollback_leaves_no_partial_effects": True,
        "broad_command_rewire_required_in_this_task": False,
    }
    assert contract["truth_effects"] == {
        "creates_effect_ledger_entries": True,
        "emits_timeline_events": False,
        "creates_artifact_versions": False,
        "creates_source_occurrences": False,
        "creates_ingest_jobs": False,
        "promotes_official_pointers": False,
        "activates_workflow_pack": False,
    }
    assert {
        "public_api_route",
        "frontend_route",
        "event_registry_change",
        "capex_workflow_activation",
        "raw_corpus_import",
        "official_pointer_creation",
        "reviewed_baseline_creation",
        "broad_command_handler_rewire",
    } <= set(contract["not_implemented_in_this_task"])


def test_tool_execution_attempt_runtime_contract_closes_task_0398_without_worker_rewire() -> None:
    contract = _load_yaml(TOOL_EXECUTION_ATTEMPT_RUNTIME_CONTRACT_PATH)

    assert contract["owner_task"] == "TASK-0398"
    assert contract["source_row"] == "ARCH-W2-S08"
    assert contract["activation_posture"] == "planning_only_no_capex_activation"
    assert contract["depends_on"]["repo_tasks"] == ["TASK-0396"]
    assert contract["required_table"]["tool_execution_attempts"] == {
        "primary_key": ["tool_execution_attempt_id"],
        "unique_constraints": [
            {
                "name": "uq_tool_execution_attempts_tool_attempt_no",
                "columns": ["tool_execution_id", "attempt_no"],
            },
            {
                "name": "uq_tool_execution_attempts_tool_lease",
                "columns": ["tool_execution_id", "lease_token"],
            },
            {
                "name": "uq_tool_execution_attempts_active_tool",
                "columns": ["active_tool_execution_id"],
            },
        ],
        "indexes": [
            "ix_tool_execution_attempts_tool_state",
            "ix_tool_execution_attempts_session_state",
        ],
    }
    assert contract["attempt_policy"] == {
        "logical_tool_execution_row_preserved": True,
        "attempts_table_added": True,
        "attempt_numbers_monotonic_per_tool_execution": True,
        "one_active_attempt_per_tool_execution": True,
        "active_attempt_states": ["RUNNING"],
        "terminal_attempt_states": ["COMPLETED", "FAILED", "CANCELED"],
        "lease_token_required_when_active_attempt_exists": True,
        "stale_completion_error_code": "tool_execution_attempt_stale_completion",
        "missing_lease_error_code": "tool_execution_attempt_lease_required",
        "active_attempt_conflict_error_code": "tool_execution_attempt_active_conflict",
        "legacy_completion_without_active_attempt_supported": True,
        "event_registry_change_required": False,
        "worker_rewire_required_in_this_task": False,
    }
    assert contract["truth_effects"] == {
        "creates_tool_execution_attempt_rows": True,
        "changes_tool_execution_current_state": True,
        "emits_new_event_types": False,
        "creates_artifact_versions": False,
        "creates_source_occurrences": False,
        "creates_ingest_jobs": False,
        "promotes_official_pointers": False,
        "activates_workflow_pack": False,
    }
    assert {
        "public_api_route",
        "frontend_route",
        "event_registry_change",
        "worker_migration",
        "capex_workflow_activation",
        "raw_corpus_import",
        "official_pointer_creation",
        "reviewed_baseline_creation",
    } <= set(contract["not_implemented_in_this_task"])


def test_project_concurrency_runtime_slot_contract_closes_task_0399_without_activation() -> None:
    contract = _load_yaml(PROJECT_CONCURRENCY_RUNTIME_SLOT_CONTRACT_PATH)

    assert contract["owner_task"] == "TASK-0399"
    assert contract["source_row"] == "ARCH-W2-S09"
    assert contract["activation_posture"] == "planning_only_no_capex_activation"
    assert contract["depends_on"]["repo_tasks"] == ["TASK-0385", "TASK-0563"]
    assert contract["required_tables"]["capex_project_concurrency_policies"] == {
        "primary_key": ["project_concurrency_policy_id"],
        "unique_constraints": [
            {
                "name": "uq_capex_project_concurrency_policy_family",
                "columns": ["tenant_id", "domain_id", "project_id", "lock_family"],
            }
        ],
        "indexes": ["ix_capex_project_concurrency_policies_scope"],
    }
    assert contract["required_tables"]["capex_project_runtime_slots"] == {
        "primary_key": ["project_runtime_slot_id"],
        "unique_constraints": [
            {
                "name": "uq_capex_project_runtime_slots_active_family",
                "columns": ["active_family_key"],
            }
        ],
        "indexes": [
            "ix_capex_project_runtime_slots_scope_state",
            "ix_capex_project_runtime_slots_slot_key",
        ],
    }
    assert contract["lock_policy"] == {
        "supported_lock_families": ["ingest", "pointer"],
        "default_max_active_slots": 1,
        "slot_key_shapes": {
            "ingest": "ingest:<ref>",
            "pointer": "pointer:<ref>",
        },
        "active_family_key_unique": True,
        "matching_holder_lease_replays": True,
        "expired_slots_reclaimable": True,
        "unsupported_family_error_code": "project_runtime_slot_family_unsupported",
        "active_conflict_error_code": "project_runtime_slot_conflict",
        "stale_release_error_code": "project_runtime_slot_stale_release",
        "broad_command_enforcement_required_in_this_task": False,
    }
    assert contract["truth_effects"] == {
        "creates_project_concurrency_policy_rows": True,
        "creates_project_runtime_slot_rows": True,
        "enforces_ingest_or_pointer_commands_globally": False,
        "emits_timeline_events": False,
        "creates_artifact_versions": False,
        "creates_source_occurrences": False,
        "creates_ingest_jobs": False,
        "promotes_official_pointers": False,
        "activates_workflow_pack": False,
    }
    assert {
        "public_api_route",
        "frontend_route",
        "event_registry_change",
        "worker_rewire",
        "broad_command_enforcement",
        "capex_workflow_activation",
        "raw_corpus_import",
        "official_pointer_creation",
        "reviewed_baseline_creation",
    } <= set(contract["not_implemented_in_this_task"])


def test_runtime_outbox_after_commit_contract_closes_task_0400_without_second_event_log() -> None:
    contract = _load_yaml(RUNTIME_OUTBOX_AFTER_COMMIT_CONTRACT_PATH)

    assert contract["owner_task"] == "TASK-0400"
    assert contract["source_row"] == "ARCH-W2-S10"
    assert contract["activation_posture"] == "planning_only_no_capex_activation"
    assert contract["depends_on"]["repo_tasks"] == ["TASK-0396", "TASK-0397"]
    assert contract["required_runtime_state"] == {
        "canonical_event_table": "timeline_events",
        "cursor_table": "consumer_cursors",
        "repository": "src/onetruth/infrastructure/repositories/runtime_outbox.py",
        "runtime_bootstrap_contract": "docs/planning/RUNTIME_BOOTSTRAP.md",
    }
    assert contract["outbox_policy"] == {
        "second_authoritative_outbox_table_allowed": False,
        "canonical_event_source": "timeline_events",
        "committed_events_only": True,
        "cursor_table": "consumer_cursors",
        "deterministic_ordering": "sequence_no_ascending",
        "max_batch_size": 500,
        "tenant_domain_scope_required": True,
        "event_type_filter_allowed": True,
        "filtered_events_advance_cursor": True,
        "dispatch_failure_error_code": "runtime_outbox_dispatch_failed",
        "dispatch_failure_cursor_position": "before_failed_event",
        "broad_worker_rewire_required_in_this_task": False,
    }
    assert contract["truth_effects"] == {
        "creates_runtime_outbox_table": False,
        "creates_second_event_log": False,
        "advances_consumer_cursors": True,
        "emits_timeline_events": False,
        "creates_artifact_versions": False,
        "creates_source_occurrences": False,
        "creates_ingest_jobs": False,
        "promotes_official_pointers": False,
        "activates_workflow_pack": False,
    }
    assert {
        "public_api_route",
        "frontend_route",
        "event_registry_change",
        "broad_worker_rewire",
        "external_bus_activation",
        "capex_workflow_activation",
        "raw_corpus_import",
    } <= set(contract["not_implemented_in_this_task"])


def test_artifact_version_identity_contract_closes_task_0401_without_officialness_field() -> None:
    contract = _load_yaml(ARTIFACT_VERSION_IDENTITY_CONTRACT_PATH)

    assert contract["owner_task"] == "TASK-0401"
    assert contract["source_row"] == "ARCH-W2-S11"
    assert contract["activation_posture"] == "planning_only_no_capex_activation"
    assert contract["depends_on"]["repo_tasks"] == ["TASK-0396"]
    assert contract["required_table"]["artifact_versions"]["added_columns"] == [
        "artifact_identity_profile",
        "artifact_identity_digest",
    ]
    assert contract["identity_policy"] == {
        "profile_id": "onetruth.artifact_version_identity.canonical_json.sha256.v1",
        "digest_format": "sha256:<64 lowercase hex>",
        "canonical_json": {
            "sort_keys": True,
            "separators": [",", ":"],
            "ensure_ascii": True,
            "allow_nan": False,
        },
        "input_fields": [
            "tenant_id",
            "domain_id",
            "project_id",
            "workflow_run_id",
            "dataset_key",
            "partition_kind",
            "partition_key",
            "artifact_kind",
            "media_type",
            "content_digest",
            "byte_size",
        ],
        "excluded_fields": [
            "artifact_version_id",
            "artifact_role",
            "storage_uri",
            "metadata_json",
            "parent_artifact_version_id",
            "supersedes_artifact_version_id",
            "lineage_note",
            "pointer_id",
            "officialness",
            "official_status",
        ],
    }
    assert contract["officialness_policy"] == {
        "artifact_version_officialness_field_allowed": False,
        "pointer_state_defines_officialness": True,
        "pointer_event_required_for_officialness_change": True,
    }
    assert contract["truth_effects"] == {
        "creates_artifact_versions": False,
        "adds_artifact_identity_metadata": True,
        "changes_pointer_officialness": False,
        "emits_timeline_events": False,
        "creates_source_occurrences": False,
        "creates_ingest_jobs": False,
        "promotes_official_pointers": False,
        "activates_workflow_pack": False,
    }
    assert {
        "public_api_route",
        "frontend_route",
        "event_registry_change",
        "pointer_promotion_service",
        "officialness_field",
        "blobref_schema",
        "capex_workflow_activation",
        "raw_corpus_import",
    } <= set(contract["not_implemented_in_this_task"])


def test_task_0267_through_0290_close_after_unblocker_pairs() -> None:
    task_0267 = _frontmatter("TASK-0267")
    task_0268 = _frontmatter("TASK-0268")
    task_0269 = _frontmatter("TASK-0269")
    task_0270 = _frontmatter("TASK-0270")
    task_0271 = _frontmatter("TASK-0271")
    task_0272 = _frontmatter("TASK-0272")
    task_0273 = _frontmatter("TASK-0273")
    task_0274 = _frontmatter("TASK-0274")
    task_0276 = _frontmatter("TASK-0276")
    task_0277 = _frontmatter("TASK-0277")
    task_0278 = _frontmatter("TASK-0278")
    task_0283 = _frontmatter("TASK-0283")
    task_0284 = _frontmatter("TASK-0284")
    task_0285 = _frontmatter("TASK-0285")
    task_0286 = _frontmatter("TASK-0286")
    task_0287 = _frontmatter("TASK-0287")
    task_0288 = _frontmatter("TASK-0288")
    task_0289 = _frontmatter("TASK-0289")
    task_0290 = _frontmatter("TASK-0290")
    task_0372 = _frontmatter("TASK-0372")
    task_0373 = _frontmatter("TASK-0373")
    task_0374 = _frontmatter("TASK-0374")
    task_0391 = _frontmatter("TASK-0391")
    task_0392 = _frontmatter("TASK-0392")
    task_0393 = _frontmatter("TASK-0393")
    task_0394 = _frontmatter("TASK-0394")
    task_0395 = _frontmatter("TASK-0395")
    task_0396 = _frontmatter("TASK-0396")
    task_0397 = _frontmatter("TASK-0397")
    task_0398 = _frontmatter("TASK-0398")
    task_0399 = _frontmatter("TASK-0399")
    task_0400 = _frontmatter("TASK-0400")
    task_0401 = _frontmatter("TASK-0401")
    task_0539 = _frontmatter("TASK-0539")
    task_0540 = _frontmatter("TASK-0540")

    assert task_0267["status"] == "DONE"
    assert task_0267["completed_at"] == "2026-06-17T00:00:00Z"
    assert task_0268["status"] == "DONE"
    assert task_0268["completed_at"] == "2026-06-17T00:00:00Z"
    assert task_0269["status"] == "DONE"
    assert task_0269["completed_at"] == "2026-06-17T00:00:00Z"
    assert task_0270["status"] == "DONE"
    assert task_0270["completed_at"] == "2026-06-17T00:00:00Z"
    assert task_0271["status"] == "DONE"
    assert task_0271["completed_at"] == "2026-06-23T00:00:00Z"
    assert "TASK-0270" in task_0271["depends_on"]
    assert task_0272["status"] == "DONE"
    assert task_0272["completed_at"] == "2026-06-23T00:00:00Z"
    assert "TASK-0271" in task_0272["depends_on"]
    assert task_0273["status"] == "DONE"
    assert task_0273["completed_at"] == "2026-06-23T00:00:00Z"
    assert "TASK-0263" in task_0273["depends_on"]
    assert task_0274["status"] == "DONE"
    assert task_0274["completed_at"] == "2026-06-23T00:00:00Z"
    assert "TASK-0266" in task_0274["depends_on"]
    assert task_0276["status"] == "DONE"
    assert task_0276["completed_at"] == "2026-06-17T00:00:00Z"
    assert task_0277["status"] == "DONE"
    assert task_0277["completed_at"] == "2026-06-23T00:00:00Z"
    assert "TASK-0276" in task_0277["depends_on"]
    assert task_0278["status"] == "DONE"
    assert task_0278["completed_at"] == "2026-06-17T00:00:00Z"
    assert task_0283["status"] == "DONE"
    assert task_0283["completed_at"] == "2026-06-17T00:00:00Z"
    assert "TASK-0276" in task_0283["depends_on"]
    assert task_0284["status"] == "DONE"
    assert task_0284["completed_at"] == "2026-06-17T00:00:00Z"
    assert "TASK-0269" in task_0284["depends_on"]
    assert "TASK-0278" in task_0284["depends_on"]
    assert task_0285["status"] == "DONE"
    assert task_0285["completed_at"] == "2026-06-23T00:00:00Z"
    assert "TASK-0284" in task_0285["depends_on"]
    assert task_0286["status"] == "DONE"
    assert task_0286["completed_at"] == "2026-06-17T00:00:00Z"
    assert "TASK-0284" in task_0286["depends_on"]
    assert task_0287["status"] == "DONE"
    assert task_0287["completed_at"] == "2026-06-23T00:00:00Z"
    assert "TASK-0286" in task_0287["depends_on"]
    assert task_0288["status"] == "DONE"
    assert task_0288["completed_at"] == "2026-06-23T00:00:00Z"
    assert "TASK-0284" in task_0288["depends_on"]
    assert "TASK-0287" in task_0288["depends_on"]
    assert task_0289["status"] == "DONE"
    assert task_0289["completed_at"] == "2026-06-23T00:00:00Z"
    assert "TASK-0285" in task_0289["depends_on"]
    assert "TASK-0286" in task_0289["depends_on"]
    assert "TASK-0287" in task_0289["depends_on"]
    assert "TASK-0288" in task_0289["depends_on"]
    assert task_0290["status"] == "DONE"
    assert task_0290["completed_at"] == "2026-06-23T00:00:00Z"
    assert "TASK-0277" in task_0290["depends_on"]
    assert "TASK-0289" in task_0290["depends_on"]
    assert task_0372["status"] == "DONE"
    assert task_0372["completed_at"] == "2026-06-23T00:00:00Z"
    assert "TASK-0273" in task_0372["depends_on"]
    assert task_0373["status"] == "DONE"
    assert task_0373["completed_at"] == "2026-06-23T00:00:00Z"
    assert "TASK-0273" in task_0373["depends_on"]
    assert "TASK-0372" in task_0373["depends_on"]
    assert task_0374["status"] == "DONE"
    assert task_0374["completed_at"] == "2026-06-23T00:00:00Z"
    assert "TASK-0266" in task_0374["depends_on"]
    assert "TASK-0267" in task_0374["depends_on"]
    assert task_0391["status"] == "DONE"
    assert task_0391["completed_at"] == "2026-06-23T00:00:00Z"
    assert "TASK-0564" in task_0391["depends_on"]
    assert task_0392["status"] == "DONE"
    assert task_0392["completed_at"] == "2026-06-23T00:00:00Z"
    assert "TASK-0391" in task_0392["depends_on"]
    assert task_0393["status"] == "DONE"
    assert task_0393["completed_at"] == "2026-06-23T00:00:00Z"
    assert "TASK-0391" in task_0393["depends_on"]
    assert task_0394["status"] == "DONE"
    assert task_0394["completed_at"] == "2026-06-23T00:00:00Z"
    assert "TASK-0392" in task_0394["depends_on"]
    assert "TASK-0393" in task_0394["depends_on"]
    assert task_0395["status"] == "DONE"
    assert task_0395["completed_at"] == "2026-06-23T00:00:00Z"
    assert "TASK-0391" in task_0395["depends_on"]
    assert "TASK-0392" in task_0395["depends_on"]
    assert task_0396["status"] == "DONE"
    assert task_0396["completed_at"] == "2026-06-23T00:00:00Z"
    assert "TASK-0233" in task_0396["depends_on"]
    assert "TASK-0240" in task_0396["depends_on"]
    assert task_0397["status"] == "DONE"
    assert task_0397["completed_at"] == "2026-06-23T00:00:00Z"
    assert "TASK-0396" in task_0397["depends_on"]
    assert task_0398["status"] == "DONE"
    assert task_0398["completed_at"] == "2026-06-23T00:00:00Z"
    assert "TASK-0396" in task_0398["depends_on"]
    assert task_0399["status"] == "DONE"
    assert task_0399["completed_at"] == "2026-06-23T00:00:00Z"
    assert "TASK-0385" in task_0399["depends_on"]
    assert "TASK-0563" in task_0399["depends_on"]
    assert task_0400["status"] == "DONE"
    assert task_0400["completed_at"] == "2026-06-23T00:00:00Z"
    assert "TASK-0396" in task_0400["depends_on"]
    assert "TASK-0397" in task_0400["depends_on"]
    assert task_0401["status"] == "DONE"
    assert task_0401["completed_at"] == "2026-06-23T00:00:00Z"
    assert "TASK-0396" in task_0401["depends_on"]
    assert task_0539["status"] == "DONE"
    assert task_0539["completed_at"] == "2026-06-23T00:00:00Z"
    assert task_0540["status"] == "DONE"
    assert task_0540["completed_at"] == "2026-06-23T00:00:00Z"


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
