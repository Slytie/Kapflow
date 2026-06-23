from __future__ import annotations

import pytest

from onetruth.capex_platform.lifecycle_stage_state_workflow import (
    LIFECYCLE_NAVIGATION_FLAGS_SCHEMA_VERSION,
    LIFECYCLE_STAGE_STATE_ACTIVATION_POSTURE,
    LIFECYCLE_STAGE_STATE_SCHEMA_VERSION,
    LIFECYCLE_STAGE_STATE_WORKFLOW_SCHEMA_VERSION,
    STAGE_READINESS_MATRIX_SCHEMA_VERSION,
    LifecycleStageStateWorkflowError,
    build_lifecycle_stage_state_workflow_outputs,
    lifecycle_stage_state_workflow_digest,
)


NOW = "2026-06-23T00:00:00Z"
SOURCE_REFS = [
    "source_occurrence:so-lifecycle-intake",
    "source_occurrence:so-lifecycle-baseline",
    "source_occurrence:so-lifecycle-procurement",
    "source_occurrence:so-lifecycle-conflict",
    "source_occurrence:so-lifecycle-ai-draft",
]


def _corpus_baseline_outputs() -> dict[str, object]:
    return {
        "schema_version": "capex.corpus_baseline.workflow_outputs.v1",
        "activation_posture": "planning_only_no_capex_activation",
        "workflow_id": "corpus-baseline-lifecycle-001",
        "tenant_id": "tenant-a",
        "domain_id": "domain-x",
        "project_id": "cp-lifecycle",
        "basis": {"packet_register_id": "packet-register-lifecycle"},
        "generated_artifacts": [
            {
                "file_name": "capex.packet_register.v1.json",
                "envelope": {"source_refs": SOURCE_REFS},
            }
        ],
    }


def _stage_observations() -> list[dict[str, object]]:
    return [
        {
            "stage_id": "planning_procurement",
            "readiness_state": "blocked_missing_evidence",
            "stage_summary": "Planning and procurement navigation is missing reviewed evidence.",
            "source_refs": ["source_occurrence:so-lifecycle-procurement"],
        },
        {
            "stage_id": "baseline",
            "readiness_state": "ready",
            "stage_summary": "Baseline navigation has reviewed source evidence.",
            "source_refs": ["source_occurrence:so-lifecycle-baseline"],
            "evidence_source_refs": ["source_occurrence:so-lifecycle-baseline"],
        },
        {
            "stage_id": "execution_delivery",
            "readiness_state": "in_progress",
            "stage_summary": "Execution navigation has conflicting stage evidence.",
            "source_refs": ["source_occurrence:so-lifecycle-conflict"],
            "conflict_source_refs": ["source_occurrence:so-lifecycle-conflict"],
        },
        {
            "stage_id": "commissioning_closeout",
            "readiness_state": "ready",
            "stage_summary": "AI draft suggests closeout navigation without evidence.",
            "source_refs": ["source_occurrence:so-lifecycle-ai-draft"],
            "ai_draft_source_refs": ["source_occurrence:so-lifecycle-ai-draft"],
        },
        {
            "stage_id": "intake",
            "readiness_state": "not_started",
            "stage_summary": "Intake navigation is recorded as a derived bucket only.",
            "source_refs": ["source_occurrence:so-lifecycle-intake"],
        },
    ]


def _outputs(**overrides: object) -> dict[str, object]:
    payload: dict[str, object] = {
        "corpus_baseline_outputs": _corpus_baseline_outputs(),
        "stage_observations": _stage_observations(),
        "workflow_id": "lifecycle-workflow-001",
        "created_at": NOW,
        "created_by_actor_id": "human:pm",
        "created_by_actor_type": "human",
    }
    payload.update(overrides)
    return build_lifecycle_stage_state_workflow_outputs(**payload)  # type: ignore[arg-type]


def test_builds_deterministic_lifecycle_navigation_outputs() -> None:
    first = _outputs()
    second = _outputs(stage_observations=list(reversed(_stage_observations())))

    assert first == second
    assert first["schema_version"] == LIFECYCLE_STAGE_STATE_WORKFLOW_SCHEMA_VERSION
    assert first["activation_posture"] == LIFECYCLE_STAGE_STATE_ACTIVATION_POSTURE
    assert first["tenant_id"] == "tenant-a"
    assert first["domain_id"] == "domain-x"
    assert first["project_id"] == "cp-lifecycle"
    assert first["lifecycle_stage_state"]["schema_version"] == (
        LIFECYCLE_STAGE_STATE_SCHEMA_VERSION
    )
    assert first["stage_readiness_matrix"]["schema_version"] == (
        STAGE_READINESS_MATRIX_SCHEMA_VERSION
    )
    assert first["lifecycle_navigation_flags"]["schema_version"] == (
        LIFECYCLE_NAVIGATION_FLAGS_SCHEMA_VERSION
    )
    assert [
        row["stage_id"]
        for row in first["lifecycle_stage_state"]["rows"]  # type: ignore[index]
    ] == [
        "intake",
        "baseline",
        "planning_procurement",
        "execution_delivery",
        "commissioning_closeout",
    ]
    assert lifecycle_stage_state_workflow_digest(first).startswith("sha256:")


def test_stage_navigation_is_derived_only_and_non_authoritative() -> None:
    outputs = _outputs()
    rows = outputs["lifecycle_stage_state"]["rows"]  # type: ignore[index]

    assert all(row["derived_navigation_only"] is True for row in rows)
    assert all(row["official_truth"] is False for row in rows)
    assert outputs["truth_effects"] == {
        "creates_workflow_run": False,
        "creates_tasks": False,
        "creates_approvals": False,
        "creates_closure_snapshots": False,
        "creates_reviewed_baseline": False,
        "writes_artifacts": False,
        "promotes_official_pointers": False,
        "activates_workflow_pack": False,
    }


def test_missing_conflict_and_ai_draft_states_create_flags() -> None:
    outputs = _outputs()
    flags = {
        row["flag_type"]: row
        for row in outputs["lifecycle_navigation_flags"]["rows"]  # type: ignore[index]
    }

    assert set(flags) == {
        "missing_stage_evidence",
        "conflicting_lifecycle_evidence",
        "ai_draft_cannot_set_lifecycle_stage",
    }
    assert flags["missing_stage_evidence"]["severity"] == "medium"
    assert flags["conflicting_lifecycle_evidence"]["severity"] == "high"
    assert flags["ai_draft_cannot_set_lifecycle_stage"]["source_refs"] == [
        "source_occurrence:so-lifecycle-ai-draft"
    ]


def test_scope_and_source_ref_validation() -> None:
    bad_scope = _corpus_baseline_outputs()
    bad_scope["tenant_id"] = ""
    with pytest.raises(LifecycleStageStateWorkflowError) as scope:
        _outputs(corpus_baseline_outputs=bad_scope)
    assert scope.value.code == "lifecycle_required_field_missing"

    observations = _stage_observations()
    observations[0]["source_refs"] = ["source_occurrence:so-not-in-baseline"]
    with pytest.raises(LifecycleStageStateWorkflowError) as source_ref:
        _outputs(stage_observations=observations)
    assert source_ref.value.code == "lifecycle_source_ref_not_in_corpus_baseline"


def test_duplicate_and_invalid_stage_ids_are_rejected() -> None:
    duplicate = _stage_observations()
    duplicate[1]["stage_id"] = "planning_procurement"
    with pytest.raises(LifecycleStageStateWorkflowError) as duplicate_error:
        _outputs(stage_observations=duplicate)
    assert duplicate_error.value.code == "lifecycle_stage_duplicate_stage_id"

    invalid = _stage_observations()
    invalid[0]["stage_id"] = "waterfall_gate_7"
    with pytest.raises(LifecycleStageStateWorkflowError) as invalid_error:
        _outputs(stage_observations=invalid)
    assert invalid_error.value.code == "lifecycle_stage_id_invalid"


def test_ready_stage_without_evidence_fails_open() -> None:
    observations = [
        {
            "stage_id": "baseline",
            "readiness_state": "ready",
            "stage_summary": "Ready cannot be asserted without reviewed evidence refs.",
            "source_refs": ["source_occurrence:so-lifecycle-baseline"],
        }
    ]

    outputs = _outputs(stage_observations=observations)

    [row] = outputs["lifecycle_stage_state"]["rows"]  # type: ignore[index]
    assert row["readiness_state"] == "blocked_missing_evidence"
    assert row["navigation_result"] == "fail"


def test_raw_material_is_rejected() -> None:
    observations = _stage_observations()
    observations[0]["raw_stage"] = "secret.pdf"

    with pytest.raises(LifecycleStageStateWorkflowError) as exc:
        _outputs(stage_observations=observations)

    assert exc.value.code == "lifecycle_raw_material_rejected"
