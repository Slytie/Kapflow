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
