from __future__ import annotations

import pytest

from onetruth.capex_platform.project_intake_router import (
    PROJECT_INTAKE_ACTIVATION_POSTURE,
    PROJECT_INTAKE_ENTRY_MODES,
    PROJECT_INTAKE_HANDOFF_MANIFEST_SCHEMA_VERSION,
    PROJECT_INTAKE_PROFILE_SCHEMA_VERSION,
    PROJECT_INTAKE_ROUTER_SCHEMA_VERSION,
    ProjectIntakeRouterError,
    build_project_intake_router_outputs,
    canonical_project_intake_router_bytes,
    project_intake_router_digest,
)


def _outputs(**overrides: object) -> dict[str, object]:
    payload: dict[str, object] = {
        "tenant_id": "tenant-a",
        "domain_id": "domain-x",
        "project_id": "cp-intake",
        "intake_request_id": "intake-001",
        "entry_mode": "new_project",
        "requested_by_actor_id": "human:pm",
        "requested_by_actor_type": "human",
        "created_at": "2026-06-17T00:00:00Z",
        "human_confirmation": {
            "decision": "confirmed",
            "confirmed_by_actor_id": "human:pm",
            "confirmed_at": "2026-06-17T00:00:00Z",
        },
        "sanitized_context_refs": [
            "source_inventory:source-inventory-001",
            "fixture_tier:k12_expected_output_manifest",
        ],
        "module_candidates": [
            {
                "module_id": "module:scope_management",
                "readiness": "candidate",
                "routing_reason": "sanitized_context_ref_present",
            }
        ],
    }
    payload.update(overrides)
    return build_project_intake_router_outputs(**payload)  # type: ignore[arg-type]


@pytest.mark.parametrize("entry_mode", PROJECT_INTAKE_ENTRY_MODES)
def test_project_intake_router_builds_outputs_for_all_entry_modes(entry_mode: str) -> None:
    extra = {"fixture_tier": "k12_sanitized_expected_output"} if entry_mode == "mid_project" else {}

    outputs = _outputs(entry_mode=entry_mode, **extra)

    profile = outputs["project_intake_profile"]  # type: ignore[index]
    handoff = outputs["handoff_manifest"]  # type: ignore[index]
    assert outputs["schema_version"] == PROJECT_INTAKE_ROUTER_SCHEMA_VERSION
    assert outputs["activation_posture"] == PROJECT_INTAKE_ACTIVATION_POSTURE
    assert profile["schema_version"] == PROJECT_INTAKE_PROFILE_SCHEMA_VERSION
    assert profile["entry_mode"] == entry_mode
    assert profile["ai_draft_only"] is True
    assert handoff["schema_version"] == PROJECT_INTAKE_HANDOFF_MANIFEST_SCHEMA_VERSION
    assert handoff["activation_allowed"] is False
    assert project_intake_router_digest(outputs).startswith("sha256:")


def test_project_intake_mid_project_k12_uses_sanitized_fixture_refs_only() -> None:
    outputs = _outputs(
        entry_mode="mid_project",
        fixture_tier="k12_sanitized_expected_output",
        sanitized_context_refs=[
            "source_inventory:source-inventory-k12",
            "oracle_manifest:K12_EXPECTED_OUTPUT_MANIFEST",
        ],
    )

    profile = outputs["project_intake_profile"]  # type: ignore[index]
    assert profile["fixture_tier"] == "k12_sanitized_expected_output"
    assert "oracle_manifest:K12_EXPECTED_OUTPUT_MANIFEST" in profile[
        "sanitized_context_refs"
    ]
    assert b"/Users/" not in canonical_project_intake_router_bytes(outputs)


def test_project_intake_router_requires_human_confirmation() -> None:
    with pytest.raises(ProjectIntakeRouterError) as exc_info:
        _outputs(human_confirmation={"decision": "ai_draft"})

    assert exc_info.value.code == "project_intake_human_confirmation_required"


def test_project_intake_router_rejects_raw_context_paths_and_filenames() -> None:
    for raw_ref in ("/Users/pm/Client/raw.pdf", "Real Client Budget.xlsx"):
        with pytest.raises(ProjectIntakeRouterError) as exc_info:
            _outputs(sanitized_context_refs=[raw_ref])
        assert exc_info.value.code == "project_intake_raw_context_ref_forbidden"


def test_project_intake_router_outputs_have_no_runtime_truth_effects() -> None:
    outputs = _outputs()

    assert set(outputs["cannot_be_used_for"]) >= {  # type: ignore[arg-type]
        "capex_runtime_activation",
        "product_activation",
        "public_route_activation",
        "authored_workflow_pack_activation",
        "raw_corpus_import",
        "reviewed_baseline_creation",
        "official_pointer_creation",
        "module_activation_approval",
    }
    assert outputs["truth_effects"] == {
        "creates_workflow_run": False,
        "creates_source_occurrences": False,
        "writes_artifacts": False,
        "promotes_official_pointers": False,
        "activates_workflow_pack": False,
    }
