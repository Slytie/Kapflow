from __future__ import annotations

import pytest

from onetruth.capex_platform.ceo_transparency_snapshot import (
    CEO_TRANSPARENCY_SNAPSHOT_SCHEMA_VERSION,
)
from onetruth.capex_platform.risk_ceo_transparency_workflow import (
    RISK_CEO_FLAGS_SCHEMA_VERSION,
    RISK_CEO_TRANSPARENCY_ACTIVATION_POSTURE,
    RISK_CEO_TRANSPARENCY_WORKFLOW_SCHEMA_VERSION,
    RISK_STATE_SNAPSHOT_SCHEMA_VERSION,
    RiskCeoTransparencyWorkflowError,
    build_risk_ceo_transparency_workflow_outputs,
    risk_ceo_transparency_workflow_digest,
)


NOW = "2026-06-23T00:00:00Z"
PROJECT_DIGEST = "sha256:" + ("1" * 64)
CLOSURE_DIGEST = "sha256:" + ("2" * 64)
FLAGS_DIGEST = "sha256:" + ("3" * 64)
SOURCE_REFS = [
    "source_occurrence:so-risk",
    "source_occurrence:so-missing",
    "source_occurrence:so-conflict",
    "source_occurrence:so-ai",
    "source_occurrence:so-waiver",
    "source_occurrence:so-stale",
]


def _project_state_outputs() -> dict[str, object]:
    closure_rows = [
        {
            "component_id": "governance_commitments",
            "status": "reviewed",
            "result": "pass",
            "reason": "commitments_reviewed",
            "source_refs": ["source_occurrence:so-risk"],
            "creates_official_truth": False,
        },
        {
            "component_id": "official_pointer_posture",
            "status": "current",
            "result": "pass",
            "reason": "official_pointers_current_and_reviewed",
            "source_refs": ["source_occurrence:so-stale"],
            "creates_official_truth": False,
        },
        {
            "component_id": "owner_interface_resolution",
            "status": "resolved",
            "result": "pass",
            "reason": "owner_interfaces_resolved_with_evidence",
            "source_refs": ["source_occurrence:so-conflict"],
            "creates_official_truth": False,
        },
    ]
    return {
        "schema_version": "capex.project_state_snapshot.workflow_outputs.v1",
        "activation_posture": "planning_only_no_capex_activation",
        "workflow_id": "project-state-snapshot-001",
        "tenant_id": "tenant-a",
        "domain_id": "domain-x",
        "project_id": "project-risk",
        "created_at": NOW,
        "created_by_actor": {"id": "human:pm", "type": "human"},
        "basis": {"project_state_snapshot_workflow_id": "basis"},
        "project_state_snapshot": {
            "schema_version": "capex.project_state_snapshot.v1",
            "snapshot_id": "project-state-snapshot-001:snapshot",
            "tenant_id": "tenant-a",
            "domain_id": "domain-x",
            "project_id": "project-risk",
            "closure_ready": True,
            "reviewed_state_only": True,
            "official_truth": False,
            "pointer_observations": [
                {
                    "pointer_id": "pointer-reviewed",
                    "pointer_family": "reviewed_baseline",
                    "pointer_state": "current",
                    "review_state": "reviewed",
                    "target_artifact_ref": "artifact_version:baseline-reviewed",
                    "source_refs": SOURCE_REFS,
                    "official_truth": False,
                }
            ],
            "snapshot_digest": PROJECT_DIGEST,
        },
        "project_closure_vector": {
            "schema_version": "capex.project_closure_vector.v1",
            "rows": closure_rows,
            "row_count": len(closure_rows),
            "closure_ready": True,
            "snapshot_digest": CLOSURE_DIGEST,
        },
        "project_state_snapshot_flags": {
            "schema_version": "capex.project_state_snapshot_flags.v1",
            "rows": [
                {
                    "flag_id": "stale-pointer",
                    "component_id": "official_pointer_posture",
                    "flag_type": "stale_pointer",
                    "severity": "high",
                    "source_refs": ["source_occurrence:so-stale"],
                    "blocks_closure_ready": True,
                }
            ],
            "row_count": 1,
            "snapshot_digest": FLAGS_DIGEST,
        },
        "truth_effects": {
            "creates_workflow_run": False,
            "creates_tasks": False,
            "creates_approvals": False,
            "creates_closure_snapshots": False,
            "creates_project_state": False,
            "creates_reviewed_baseline": False,
            "writes_artifacts": False,
            "promotes_official_pointers": False,
            "activates_workflow_pack": False,
        },
    }


def _risk_observation(**overrides: object) -> dict[str, object]:
    payload: dict[str, object] = {
        "risk_id": "risk-cost",
        "risk_kind": "cost",
        "risk_label": "Cost exposure requires management attention",
        "observation_state": "open",
        "risk_status": "open",
        "severity": "medium",
        "forecastability_grade": "forecastable",
        "project_state_component_id": "governance_commitments",
        "source_refs": ["source_occurrence:so-risk"],
        "management_action_label": "Assign commercial mitigation owner",
        "owner_role": "project_manager",
    }
    payload.update(overrides)
    return payload


def _outputs(**overrides: object) -> dict[str, object]:
    payload: dict[str, object] = {
        "project_state_snapshot_outputs": _project_state_outputs(),
        "risk_observations": [_risk_observation()],
        "workflow_id": "risk-ceo-001",
        "created_at": NOW,
        "created_by_actor_id": "human:pm",
        "created_by_actor_type": "human",
    }
    payload.update(overrides)
    return build_risk_ceo_transparency_workflow_outputs(**payload)  # type: ignore[arg-type]


def test_builds_deterministic_risk_and_ceo_outputs_from_project_state() -> None:
    observations = [
        _risk_observation(risk_id="risk-schedule", risk_kind="schedule"),
        _risk_observation(risk_id="risk-cost", risk_kind="cost"),
    ]
    first = _outputs(risk_observations=observations)
    second = _outputs(risk_observations=list(reversed(observations)))

    assert first == second
    assert first["schema_version"] == RISK_CEO_TRANSPARENCY_WORKFLOW_SCHEMA_VERSION
    assert first["activation_posture"] == RISK_CEO_TRANSPARENCY_ACTIVATION_POSTURE
    assert first["risk_state_snapshot"]["schema_version"] == RISK_STATE_SNAPSHOT_SCHEMA_VERSION  # type: ignore[index]
    assert first["ceo_transparency_snapshot"]["schema_version"] == (  # type: ignore[index]
        CEO_TRANSPARENCY_SNAPSHOT_SCHEMA_VERSION
    )
    assert first["risk_ceo_flags"]["schema_version"] == RISK_CEO_FLAGS_SCHEMA_VERSION  # type: ignore[index]
    assert first["ceo_transparency_snapshot"]["forecastability"]["grade"] == "forecastable"  # type: ignore[index]
    assert risk_ceo_transparency_workflow_digest(first).startswith("sha256:")


def test_blocker_states_propagate_to_not_forecastable_ceo_snapshot() -> None:
    outputs = _outputs(
        risk_observations=[
            _risk_observation(
                risk_id="risk-missing",
                observation_state="missing_evidence",
                source_refs=["source_occurrence:so-missing"],
                project_state_component_id="governance_commitments",
            ),
            _risk_observation(
                risk_id="risk-conflict",
                observation_state="conflict",
                source_refs=["source_occurrence:so-conflict"],
                project_state_component_id="owner_interface_resolution",
            ),
            _risk_observation(
                risk_id="risk-ai",
                observation_state="ai_draft_only",
                source_refs=["source_occurrence:so-ai"],
            ),
            _risk_observation(
                risk_id="risk-stale",
                observation_state="stale_pointer",
                source_refs=["source_occurrence:so-stale"],
                project_state_component_id="official_pointer_posture",
            ),
            _risk_observation(
                risk_id="risk-waiver",
                observation_state="waiver_recorded",
                source_refs=["source_occurrence:so-waiver"],
                waiver_refs=["waiver:waiver-001"],
            ),
        ]
    )

    flags = outputs["risk_ceo_flags"]["rows"]  # type: ignore[index]
    flag_types = {row["flag_type"] for row in flags}
    assert {
        "missing_evidence",
        "evidence_conflict",
        "ai_draft_only",
        "stale_pointer",
        "waiver_recorded",
        "not_forecastable",
    } <= flag_types
    ceo = outputs["ceo_transparency_snapshot"]  # type: ignore[assignment]
    assert ceo["forecastability"]["grade"] == "not_forecastable"  # type: ignore[index]
    assert all(
        "forecast_date" not in action
        for action in ceo["management_actions"]  # type: ignore[index]
    )
    assert {
        caveat["caveat_type"]
        for caveat in ceo["caveats"]  # type: ignore[index]
    } >= {"not_forecastable", "waiver_recorded", "ai_draft_only"}


def test_scope_source_component_duplicate_and_raw_material_are_rejected() -> None:
    with pytest.raises(RiskCeoTransparencyWorkflowError) as scope_error:
        _outputs(risk_observations=[_risk_observation(tenant_id="other-tenant")])
    assert scope_error.value.code == "risk_ceo_scope_mismatch"

    with pytest.raises(RiskCeoTransparencyWorkflowError) as source_error:
        _outputs(
            risk_observations=[
                _risk_observation(source_refs=["source_occurrence:not-in-project-state"])
            ]
        )
    assert source_error.value.code == "risk_ceo_source_ref_not_in_project_state"

    with pytest.raises(RiskCeoTransparencyWorkflowError) as component_error:
        _outputs(
            risk_observations=[
                _risk_observation(project_state_component_id="unknown-component")
            ]
        )
    assert component_error.value.code == "risk_ceo_unknown_project_state_component"

    duplicate = [_risk_observation(), _risk_observation()]
    with pytest.raises(RiskCeoTransparencyWorkflowError) as duplicate_error:
        _outputs(risk_observations=duplicate)
    assert duplicate_error.value.code == "risk_ceo_duplicate_risk_id"

    with pytest.raises(RiskCeoTransparencyWorkflowError) as raw_error:
        _outputs(risk_observations=[_risk_observation(ai_output="unreviewed prose")])
    assert raw_error.value.code == "risk_ceo_raw_material_rejected"


def test_false_precision_and_no_runtime_official_effects() -> None:
    with pytest.raises(RiskCeoTransparencyWorkflowError) as precision_error:
        _outputs(
            risk_observations=[
                _risk_observation(
                    observation_state="missing_evidence",
                    forecast_date="2026-07-15",
                    source_refs=["source_occurrence:so-missing"],
                )
            ]
        )
    assert precision_error.value.code == "risk_ceo_false_precision_forbidden"

    outputs = _outputs()
    assert outputs["truth_effects"] == {
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
