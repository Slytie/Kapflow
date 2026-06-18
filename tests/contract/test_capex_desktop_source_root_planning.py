from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from tests.helpers.repo_paths import REPO_ROOT


STAGE_MODEL_PATH = (
    REPO_ROOT
    / "docs/planning/capex_desktop_source_roots/"
    "EPIC150_STAGE_MODEL_AND_BOUNDARY.yaml"
)
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
    }
    assert set(contract["mvp_boundary"]["excluded"]) >= {
        "runtime_tables_or_migrations",
        "public_api_routes",
        "frontend_routes",
        "persistent_desktop_agent",
        "bidirectional_sync_or_writeback",
        "raw_corpus_import",
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
