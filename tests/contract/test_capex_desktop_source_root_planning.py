from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import yaml

from tests.helpers.repo_paths import REPO_ROOT


STAGE_MODEL_PATH = (
    REPO_ROOT
    / "docs/planning/capex_desktop_source_roots/"
    "EPIC150_STAGE_MODEL_AND_BOUNDARY.yaml"
)
IMPORT_PROTOCOL_PATH = (
    REPO_ROOT
    / "docs/planning/capex_desktop_source_roots/"
    "BROWSER_FOLDER_ZIP_IMPORT_MVP_PROTOCOL.yaml"
)
EXPECTED_RUNTIME_SCHEMA_PATHS = {
    "schemas/runtime/capex_source_root_binding.schema.json",
    "schemas/runtime/capex_source_root_sync_run.schema.json",
    "schemas/runtime/capex_folder_tree_snapshot.schema.json",
}
EXPECTED_RUNTIME_TABLES = {
    "capex_source_root_bindings",
    "capex_source_root_sync_runs",
    "capex_folder_tree_snapshots",
}
EXPECTED_STAGE_IDS = [
    "stage_1_mvp_manual_import",
    "stage_2_mvp_plus_manual_resync",
    "stage_3_deferred_controlled_pilot",
]
FORBIDDEN_TEXT = (
    "raw corpus import approved",
    "desktop sync activation approved",
    "watcher events are authoritative",
    "ai proposal creates reviewed baseline",
    "local deletion deletes evidence",
    "official pointer creation approved",
    "capex activation approved",
    "source occurrence binding approved",
    "upload endpoint activated",
)


def _load_yaml(path: Path) -> dict[str, Any]:
    loaded = yaml.safe_load(path.read_text(encoding="utf-8"))
    assert isinstance(loaded, dict)
    return loaded


def test_epic150_stage_model_contract_freezes_planning_boundary() -> None:
    contract = _load_yaml(STAGE_MODEL_PATH)
    lowered = STAGE_MODEL_PATH.read_text(encoding="utf-8").lower()

    assert contract["schema_version"] == "capex.desktop_source_root_stage_model.v1"
    assert contract["owner_task"] == "TASK-0607"
    assert contract["source_rows"] == ["DST-001", "DFS-D01"]
    assert contract["activation_posture"] == "planning_only_no_capex_activation"
    assert contract["overall_status"] == "planning_boundary_recorded"

    stages = contract["stage_model"]
    assert [stage["stage_id"] for stage in stages] == EXPECTED_STAGE_IDS
    assert {
        "browser_folder_selection",
        "zip_import",
        "user_selected_folder_upload",
    } <= set(stages[0]["allowed_inputs"])
    assert {
        "manual_resync_of_registered_source_root",
        "immutable_folder_tree_snapshot",
        "source_occurrence_delta",
    } <= set(stages[1]["allowed_inputs"])
    assert {
        "desktop_companion_app",
        "local_service",
        "cloud_connector",
        "server_mounted_folder",
    } <= set(stages[2]["allowed_inputs"])
    assert "watcher_event_as_truth" in stages[2]["forbidden_shortcuts"]

    assert set(contract["mvp_boundary"]["included"]) >= {
        "manual_source_root_registration_planning",
        "immutable_snapshot_and_delta_concepts",
        "pm_review_before_baseline_update_rule",
        "redacted_path_locator_rule",
        "observation_proposal_review_chain",
        "internal_source_root_runtime_state",
    }
    assert set(contract["mvp_boundary"]["excluded"]) >= {
        "public_api_routes",
        "frontend_routes",
        "persistent_desktop_agent",
        "bidirectional_sync_or_writeback",
        "raw_corpus_import",
        "capex_runtime_activation",
        "reviewed_baseline_mutation",
        "official_pointer_promotion",
    }
    assert contract["non_authority_rules"] == {
        "folder_paths_and_names": "cannot_create_project_truth",
        "content_digests": "cannot_collapse_source_occurrence_context",
        "watcher_events": "hints_only_must_reconcile_against_snapshots",
        "local_deletions": "create_missing_or_stale_review_state_not_evidence_deletion",
        "ai_proposals": "draft_only_until_pm_review",
        "reviewed_baseline": "cannot_create_official_pointer_without_governed_promotion",
    }
    assert set(contract["cannot_be_used_for"]) >= {
        "capex_runtime_activation",
        "product_activation",
        "public_route_activation",
        "workflow_pack_activation",
        "raw_corpus_import",
        "desktop_sync_activation",
        "desktop_agent_activation",
        "bidirectional_sync",
        "writeback_to_source_root",
        "watcher_authority",
        "local_deletion_authority",
        "ai_proposal_authority",
        "reviewed_baseline_creation",
        "official_pointer_creation",
        "production_preflight_approval",
        "pilot_readiness_approval",
    }
    assert set(contract["raw_data_boundary"]["prohibited_repo_material"]) >= {
        "full project corpus files",
        "unrestricted source excerpts",
        "raw project filenames",
        "absolute local paths",
        "usernames or machine names from local paths",
        "screenshots or logs containing source content",
    }
    for forbidden in FORBIDDEN_TEXT:
        assert forbidden not in lowered


def test_source_root_runtime_state_has_schema_contracts_without_activation() -> None:
    for relative_path in EXPECTED_RUNTIME_SCHEMA_PATHS:
        path = REPO_ROOT / relative_path
        schema = json.loads(path.read_text(encoding="utf-8"))

        assert schema["type"] == "object"
        assert "capex_runtime_activation" not in path.read_text(encoding="utf-8")


def test_browser_folder_zip_import_protocol_is_manifest_first_and_planning_only() -> None:
    protocol = _load_yaml(IMPORT_PROTOCOL_PATH)
    lowered = IMPORT_PROTOCOL_PATH.read_text(encoding="utf-8").lower()

    assert (
        protocol["schema_version"]
        == "capex.browser_folder_zip_import_mvp_protocol.v1"
    )
    assert protocol["owner_task"] == "TASK-0609"
    assert protocol["source_rows"] == ["DST-003", "DFS-DELTA-002"]
    assert protocol["activation_posture"] == "planning_only_no_capex_activation"
    assert protocol["overall_status"] == "protocol_recorded_not_activated"
    assert set(protocol["state_model_refs"]["runtime_tables"]) == EXPECTED_RUNTIME_TABLES
    assert set(protocol["state_model_refs"]["runtime_schemas"]) == (
        EXPECTED_RUNTIME_SCHEMA_PATHS
    )
    assert set(protocol["allowed_stage_1_inputs"]) == {
        "browser_folder_selection",
        "zip_import",
        "user_selected_folder_upload",
    }

    phases = protocol["manifest_first_phases"]
    assert [phase["phase_id"] for phase in phases] == [
        "project_authorization_precheck",
        "sanitized_manifest_submission",
        "source_root_and_sync_run_creation",
        "upload_authorization_after_manifest_acceptance",
        "folder_tree_snapshot_finalization",
        "pm_review_handoff",
    ]
    observed_boundaries = {phase["authority_boundary"] for phase in phases}
    assert "cannot_read_or_upload_blob_bytes" in observed_boundaries
    assert (
        "this_contract_does_not_implement_upload_endpoint_or_blob_storage"
        in observed_boundaries
    )
    assert {
        "upload_endpoint",
        "blob_storage_or_blob_custody",
        "background_watcher",
        "manual_resync_execution",
        "source_occurrence_binding",
        "reviewed_corpus_baseline_creation",
        "official_pointer_creation",
        "public_api_route",
        "frontend_route",
    } <= set(protocol["not_implemented_in_this_task"])
    assert set(protocol["cannot_be_used_for"]) >= {
        "capex_runtime_activation",
        "product_activation",
        "public_route_activation",
        "raw_corpus_import",
        "upload_endpoint_activation",
        "blob_storage_activation",
        "source_occurrence_binding",
        "reviewed_baseline_creation",
        "official_pointer_creation",
        "desktop_sync_activation",
        "background_watcher_activation",
        "manual_resync_activation",
        "evidence_sufficiency_claim",
    }
    assert set(protocol["raw_data_boundary"]["prohibited_repo_material"]) >= {
        "full project corpus files",
        "unrestricted source excerpts",
        "raw project filenames",
        "absolute local paths",
        "usernames or machine names from local paths",
        "uploaded blob bytes",
    }
    for forbidden in FORBIDDEN_TEXT:
        assert forbidden not in lowered
