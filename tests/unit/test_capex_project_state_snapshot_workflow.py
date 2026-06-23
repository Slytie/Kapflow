from __future__ import annotations

import pytest

from onetruth.capex_platform.project_state_snapshot_workflow import (
    PROJECT_CLOSURE_VECTOR_SCHEMA_VERSION,
    PROJECT_STATE_SNAPSHOT_ACTIVATION_POSTURE,
    PROJECT_STATE_SNAPSHOT_FLAGS_SCHEMA_VERSION,
    PROJECT_STATE_SNAPSHOT_SCHEMA_VERSION,
    PROJECT_STATE_SNAPSHOT_WORKFLOW_SCHEMA_VERSION,
    ProjectStateSnapshotWorkflowError,
    build_project_state_snapshot_workflow_outputs,
    project_state_snapshot_workflow_digest,
)


NOW = "2026-06-23T00:00:00Z"
SOURCE_REFS = [
    "source_occurrence:so-stage",
    "source_occurrence:so-commitment",
    "source_occurrence:so-assumption",
    "source_occurrence:so-interface",
    "source_occurrence:so-pointer",
    "source_occurrence:so-conflict",
    "source_occurrence:so-ai-draft",
    "source_occurrence:so-waiver",
]
STAGE_IDS = [
    "intake",
    "baseline",
    "planning_procurement",
    "execution_delivery",
    "commissioning_closeout",
    "post_closeout",
]


def _corpus_baseline_outputs() -> dict[str, object]:
    return {
        "schema_version": "capex.corpus_baseline.workflow_outputs.v1",
        "activation_posture": "planning_only_no_capex_activation",
        "workflow_id": "corpus-baseline-snapshot-001",
        "tenant_id": "tenant-a",
        "domain_id": "domain-x",
        "project_id": "cp-snapshot",
        "basis": {"packet_register_id": "packet-register-snapshot"},
        "generated_artifacts": [
            {
                "file_name": "capex.packet_register.v1.json",
                "envelope": {"source_refs": SOURCE_REFS},
            }
        ],
    }


def _lifecycle_outputs() -> dict[str, object]:
    rows = [
        {
            "stage_id": stage_id,
            "stage_order": index + 1,
            "readiness_state": "ready",
            "navigation_result": "pass",
            "source_refs": ["source_occurrence:so-stage"],
            "evidence_source_refs": ["source_occurrence:so-stage"],
        }
        for index, stage_id in enumerate(STAGE_IDS)
    ]
    return {
        "schema_version": "capex.lifecycle_stage_state.workflow_outputs.v1",
        "activation_posture": "planning_only_no_capex_activation",
        "workflow_id": "lifecycle-snapshot-001",
        "tenant_id": "tenant-a",
        "domain_id": "domain-x",
        "project_id": "cp-snapshot",
        "lifecycle_stage_state": {
            "schema_version": "capex.lifecycle_stage_state.v1",
            "rows": rows,
            "row_count": len(rows),
        },
        "stage_readiness_matrix": {
            "schema_version": "capex.stage_readiness_matrix.v1",
            "rows": rows,
            "row_count": len(rows),
        },
        "lifecycle_navigation_flags": {
            "schema_version": "capex.lifecycle_navigation_flags.v1",
            "rows": [],
            "row_count": 0,
        },
    }


def _governance_outputs() -> dict[str, object]:
    return {
        "schema_version": "capex.governance_commitment_chain.outputs.v1",
        "activation_posture": "planning_only_no_capex_activation",
        "workflow_id": "governance-snapshot-001",
        "tenant_id": "tenant-a",
        "domain_id": "domain-x",
        "project_id": "cp-snapshot",
        "commitment_chain": {
            "schema_version": "capex.commitment_chain.v1",
            "rows": [
                {
                    "commitment_id": "commitment-approved",
                    "commitment_type": "purchase_order",
                    "commercial_status": "approved",
                    "source_refs": ["source_occurrence:so-commitment"],
                }
            ],
            "row_count": 1,
        },
        "expenditure_ledger": {
            "schema_version": "capex.expenditure_ledger.v1",
            "rows": [],
            "row_count": 0,
        },
        "commitment_flags": {
            "schema_version": "capex.commitment_flags.v1",
            "rows": [],
            "row_count": 0,
        },
    }


def _assumption_outputs() -> dict[str, object]:
    return {
        "schema_version": "capex.assumption_closure.workflow_outputs.v1",
        "activation_posture": "planning_only_no_capex_activation",
        "workflow_id": "assumption-snapshot-001",
        "tenant_id": "tenant-a",
        "domain_id": "domain-x",
        "project_id": "cp-snapshot",
        "counterparty_assumption_register": {
            "schema_version": "capex.counterparty_assumption_register.v1",
            "rows": [
                {
                    "assumption_id": "assumption-closed",
                    "counterparty_id": "owner-alpha",
                    "source_refs": ["source_occurrence:so-assumption"],
                }
            ],
            "row_count": 1,
        },
        "assumption_closure_matrix": {
            "schema_version": "capex.assumption_closure_matrix.v1",
            "rows": [
                {
                    "assumption_id": "assumption-closed",
                    "closure_state": "closed_with_evidence",
                    "result": "pass",
                    "source_refs": ["source_occurrence:so-assumption"],
                    "evidence_source_refs": ["source_occurrence:so-assumption"],
                }
            ],
            "row_count": 1,
        },
        "assumption_flags": {
            "schema_version": "capex.assumption_flags.v1",
            "rows": [],
            "row_count": 0,
        },
    }


def _owner_interface_outputs() -> dict[str, object]:
    return {
        "schema_version": "capex.owner_interface_resolution.workflow_outputs.v1",
        "activation_posture": "planning_only_no_capex_activation",
        "workflow_id": "owner-interface-snapshot-001",
        "tenant_id": "tenant-a",
        "domain_id": "domain-x",
        "project_id": "cp-snapshot",
        "distributed_requirement_register": {
            "schema_version": "capex.distributed_requirement_register.v1",
            "rows": [
                {
                    "requirement_id": "req-owner",
                    "interface_id": "interface-owner",
                    "source_refs": ["source_occurrence:so-interface"],
                }
            ],
            "row_count": 1,
        },
        "interface_register": {
            "schema_version": "capex.interface_register.v1",
            "rows": [
                {
                    "interface_id": "interface-owner",
                    "requirement_id": "req-owner",
                    "resolution_state": "resolved_with_evidence",
                    "result": "pass",
                    "source_refs": ["source_occurrence:so-interface"],
                    "evidence_source_refs": ["source_occurrence:so-interface"],
                }
            ],
            "row_count": 1,
        },
        "owner_interface_flags": {
            "schema_version": "capex.owner_interface_flags.v1",
            "rows": [],
            "row_count": 0,
        },
    }


def _pointer_observations() -> list[dict[str, object]]:
    return [
        {
            "pointer_id": "pointer-baseline",
            "pointer_family": "reviewed_baseline",
            "pointer_state": "current",
            "review_state": "reviewed",
            "target_artifact_ref": "artifact_version:baseline-reviewed-001",
            "related_stage_id": "baseline",
            "related_commitment_id": "commitment-approved",
            "related_assumption_id": "assumption-closed",
            "related_interface_id": "interface-owner",
            "source_refs": ["source_occurrence:so-pointer"],
        }
    ]


def _outputs(**overrides: object) -> dict[str, object]:
    payload: dict[str, object] = {
        "corpus_baseline_outputs": _corpus_baseline_outputs(),
        "lifecycle_stage_state_outputs": _lifecycle_outputs(),
        "governance_commitment_outputs": _governance_outputs(),
        "assumption_closure_outputs": _assumption_outputs(),
        "owner_interface_resolution_outputs": _owner_interface_outputs(),
        "pointer_observations": _pointer_observations(),
        "workflow_id": "project-state-snapshot-001",
        "created_at": NOW,
        "created_by_actor_id": "human:pm",
        "created_by_actor_type": "human",
    }
    payload.update(overrides)
    return build_project_state_snapshot_workflow_outputs(**payload)  # type: ignore[arg-type]


def test_builds_closure_ready_project_state_snapshot() -> None:
    outputs = _outputs()

    assert outputs["schema_version"] == PROJECT_STATE_SNAPSHOT_WORKFLOW_SCHEMA_VERSION
    assert outputs["activation_posture"] == PROJECT_STATE_SNAPSHOT_ACTIVATION_POSTURE
    assert outputs["project_state_snapshot"]["schema_version"] == (
        PROJECT_STATE_SNAPSHOT_SCHEMA_VERSION
    )
    assert outputs["project_closure_vector"]["schema_version"] == (
        PROJECT_CLOSURE_VECTOR_SCHEMA_VERSION
    )
    assert outputs["project_state_snapshot_flags"]["schema_version"] == (
        PROJECT_STATE_SNAPSHOT_FLAGS_SCHEMA_VERSION
    )
    assert outputs["project_state_snapshot"]["closure_ready"] is True
    assert outputs["project_state_snapshot"]["official_truth"] is False
    assert outputs["project_closure_vector"]["closure_ready"] is True
    assert outputs["project_state_snapshot_flags"]["row_count"] == 0
    assert project_state_snapshot_workflow_digest(outputs).startswith("sha256:")


def test_snapshot_is_deterministic_and_has_no_official_truth_effects() -> None:
    outputs = _outputs(pointer_observations=list(reversed(_pointer_observations())))
    again = _outputs()

    assert outputs == again
    assert outputs["truth_effects"] == {
        "creates_workflow_run": False,
        "creates_tasks": False,
        "creates_approvals": False,
        "creates_closure_snapshots": False,
        "creates_project_state": False,
        "creates_reviewed_baseline": False,
        "writes_artifacts": False,
        "promotes_official_pointers": False,
        "activates_workflow_pack": False,
    }


def test_missing_evidence_conflict_ai_draft_and_waiver_block_closure_ready() -> None:
    assumption = _assumption_outputs()
    assumption["assumption_closure_matrix"]["rows"][0]["result"] = "fail"  # type: ignore[index]
    assumption["assumption_closure_matrix"]["rows"][0]["closure_state"] = "open_missing_evidence"  # type: ignore[index]
    assumption["assumption_flags"]["rows"] = [  # type: ignore[index]
        {
            "flag_id": "assumption-closed:missing-evidence",
            "flag_type": "missing_evidence",
            "source_refs": ["source_occurrence:so-assumption"],
        }
    ]
    outputs = _outputs(assumption_closure_outputs=assumption)
    reasons = {row["reason"] for row in outputs["project_closure_vector"]["rows"]}  # type: ignore[index]
    assert "assumption_closure_blocked" in reasons
    assert outputs["project_state_snapshot"]["closure_ready"] is False

    interface = _owner_interface_outputs()
    interface["interface_register"]["rows"][0]["result"] = "fail"  # type: ignore[index]
    interface["interface_register"]["rows"][0]["resolution_state"] = "blocked_conflict"  # type: ignore[index]
    interface["owner_interface_flags"]["rows"] = [  # type: ignore[index]
        {
            "flag_id": "interface-owner:conflicting-responsibility",
            "flag_type": "conflicting_responsibility",
            "source_refs": ["source_occurrence:so-conflict"],
        }
    ]
    outputs = _outputs(owner_interface_resolution_outputs=interface)
    reasons = {row["reason"] for row in outputs["project_closure_vector"]["rows"]}  # type: ignore[index]
    assert "owner_interface_resolution_blocked" in reasons

    lifecycle = _lifecycle_outputs()
    lifecycle["lifecycle_stage_state"]["rows"][0]["readiness_state"] = "ai_draft_only"  # type: ignore[index]
    lifecycle["lifecycle_navigation_flags"]["rows"] = [  # type: ignore[index]
        {
            "flag_id": "intake:ai-draft",
            "flag_type": "ai_draft_cannot_set_lifecycle_stage",
            "source_refs": ["source_occurrence:so-ai-draft"],
        }
    ]
    outputs = _outputs(lifecycle_stage_state_outputs=lifecycle)
    reasons = {row["reason"] for row in outputs["project_closure_vector"]["rows"]}  # type: ignore[index]
    assert "lifecycle_flags_open" in reasons

    waiver = _assumption_outputs()
    waiver["assumption_closure_matrix"]["rows"][0]["result"] = "satisfied_by_waiver"  # type: ignore[index]
    waiver["assumption_closure_matrix"]["rows"][0]["closure_state"] = "closed_by_waiver"  # type: ignore[index]
    waiver["assumption_closure_matrix"]["rows"][0]["waiver_refs"] = ["waiver:waiver-001"]  # type: ignore[index]
    outputs = _outputs(assumption_closure_outputs=waiver)
    vector = {
        row["component_id"]: row
        for row in outputs["project_closure_vector"]["rows"]  # type: ignore[index]
    }
    assert vector["assumption_closure"]["result"] == "waiver"
    assert outputs["project_state_snapshot"]["closure_ready"] is False


def test_pointer_states_create_snapshot_flags() -> None:
    pointers = _pointer_observations()
    pointers[0]["pointer_state"] = "stale"
    pointers[0]["review_state"] = "stale"

    outputs = _outputs(pointer_observations=pointers)
    vector = {
        row["component_id"]: row
        for row in outputs["project_closure_vector"]["rows"]  # type: ignore[index]
    }
    assert vector["official_pointer_posture"]["result"] == "fail"
    assert vector["official_pointer_posture"]["reason"] == "official_pointer_stale"
    assert outputs["project_state_snapshot_flags"]["row_count"] == 1


def test_scope_source_and_unknown_refs_are_rejected() -> None:
    lifecycle = _lifecycle_outputs()
    lifecycle["tenant_id"] = "other-tenant"
    with pytest.raises(ProjectStateSnapshotWorkflowError) as scope:
        _outputs(lifecycle_stage_state_outputs=lifecycle)
    assert scope.value.code == "project_state_scope_mismatch"

    lifecycle = _lifecycle_outputs()
    lifecycle["lifecycle_stage_state"]["rows"][0]["source_refs"] = [  # type: ignore[index]
        "source_occurrence:not-in-corpus"
    ]
    with pytest.raises(ProjectStateSnapshotWorkflowError) as source_ref:
        _outputs(lifecycle_stage_state_outputs=lifecycle)
    assert source_ref.value.code == "project_state_source_ref_not_in_corpus_baseline"

    pointers = _pointer_observations()
    pointers[0]["related_assumption_id"] = "assumption-missing"
    with pytest.raises(ProjectStateSnapshotWorkflowError) as unknown_ref:
        _outputs(pointer_observations=pointers)
    assert unknown_ref.value.code == "project_state_unknown_related_ref"


def test_duplicate_pointer_current_pointer_and_raw_material_are_rejected() -> None:
    duplicate = _pointer_observations() + _pointer_observations()
    with pytest.raises(ProjectStateSnapshotWorkflowError) as duplicate_error:
        _outputs(pointer_observations=duplicate)
    assert duplicate_error.value.code == "project_state_duplicate_pointer_id"

    current_without_review = _pointer_observations()
    current_without_review[0]["review_state"] = "draft"
    with pytest.raises(ProjectStateSnapshotWorkflowError) as pointer_error:
        _outputs(pointer_observations=current_without_review)
    assert pointer_error.value.code == "project_state_current_pointer_requires_reviewed_target"

    raw_pointer = _pointer_observations()
    raw_pointer[0]["raw_snapshot"] = "project-state.pdf"
    with pytest.raises(ProjectStateSnapshotWorkflowError) as raw_error:
        _outputs(pointer_observations=raw_pointer)
    assert raw_error.value.code == "project_state_raw_material_rejected"
