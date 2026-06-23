from __future__ import annotations

import copy

import pytest

from onetruth.capex_platform.risk_ceo_transparency_workflow import (
    build_risk_ceo_transparency_workflow_outputs,
)
from onetruth.capex_platform.risk_signal import (
    RISK_SIGNAL_ACTIVATION_POSTURE,
    RISK_SIGNAL_OUTPUTS_SCHEMA_VERSION,
    RISK_SIGNAL_REGISTER_SCHEMA_VERSION,
    RiskSignalError,
    build_risk_signal_outputs,
    risk_signal_outputs_digest,
)


NOW = "2026-06-23T00:00:00Z"
PROJECT_DIGEST = "sha256:" + ("1" * 64)
CLOSURE_DIGEST = "sha256:" + ("2" * 64)
FLAGS_DIGEST = "sha256:" + ("3" * 64)
SOURCE_REFS = [
    "source_occurrence:so-risk",
    "source_occurrence:so-missing",
    "source_occurrence:so-conflict",
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
            "rows": [],
            "row_count": 0,
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


def _risk_ceo_outputs(
    observations: list[dict[str, object]] | None = None,
) -> dict[str, object]:
    return build_risk_ceo_transparency_workflow_outputs(
        project_state_snapshot_outputs=_project_state_outputs(),
        risk_observations=observations or [_risk_observation()],
        workflow_id="risk-ceo-001",
        created_at=NOW,
        created_by_actor_id="human:pm",
        created_by_actor_type="human",
    )


def _risk_signal(
    basis: dict[str, object] | None = None,
    **overrides: object,
) -> dict[str, object]:
    payload: dict[str, object] = {
        "risk_ceo_transparency_outputs": basis or _risk_ceo_outputs(),
        "signal_register_id": "risk-signals-001",
        "created_at": NOW,
        "created_by_actor_id": "human:pm",
        "created_by_actor_type": "human",
        "policy_version": "risk_signal_policy.v1",
    }
    payload.update(overrides)
    return build_risk_signal_outputs(**payload)  # type: ignore[arg-type]


def test_builds_deterministic_risk_signal_register_from_risk_ceo_outputs() -> None:
    basis = _risk_ceo_outputs(
        [
            _risk_observation(risk_id="risk-schedule", risk_kind="schedule"),
            _risk_observation(risk_id="risk-cost", risk_kind="cost"),
        ]
    )
    reversed_basis = copy.deepcopy(basis)
    reversed_basis["risk_state_snapshot"]["rows"] = list(  # type: ignore[index]
        reversed(reversed_basis["risk_state_snapshot"]["rows"])  # type: ignore[index]
    )

    first = _risk_signal(basis)
    second = _risk_signal(reversed_basis)

    assert first == second
    assert first["schema_version"] == RISK_SIGNAL_OUTPUTS_SCHEMA_VERSION
    assert first["activation_posture"] == RISK_SIGNAL_ACTIVATION_POSTURE
    register = first["risk_signal_register"]  # type: ignore[index]
    assert register["schema_version"] == RISK_SIGNAL_REGISTER_SCHEMA_VERSION
    assert [row["risk_signal_id"] for row in register["rows"]] == [
        "risk_signal:risk-cost",
        "risk_signal:risk-schedule",
    ]
    assert all(row["policy_version"] == "risk_signal_policy.v1" for row in register["rows"])
    assert all(row["row_digest"].startswith("sha256:") for row in register["rows"])
    assert register["register_digest"].startswith("sha256:")
    assert risk_signal_outputs_digest(first).startswith("sha256:")
    assert first["truth_effects"] == {
        "creates_workflow_run": False,
        "creates_tasks": False,
        "creates_approvals": False,
        "creates_risk_engine_state": False,
        "creates_risk_signal_runtime_state": False,
        "creates_ceo_cockpit_state": False,
        "creates_closure_snapshots": False,
        "creates_official_project_state": False,
        "writes_artifacts": False,
        "promotes_official_pointers": False,
        "activates_workflow_pack": False,
    }


def test_custom_signal_rows_validate_known_refs_and_duplicate_ids() -> None:
    valid = {
        "risk_signal_id": "risk_signal:custom-cost",
        "predicate_id": "predicate:cost:open",
        "risk_ref": "risk_state_item:risk-cost",
        "severity": "medium",
        "status": "open",
        "owner_role": "project_manager",
        "source_refs": ["source_occurrence:so-risk"],
    }
    output = _risk_signal(signal_observations=[valid])
    assert output["risk_signal_register"]["rows"][0]["risk_signal_id"] == (  # type: ignore[index]
        "risk_signal:custom-cost"
    )

    with pytest.raises(RiskSignalError) as unknown_risk:
        _risk_signal(signal_observations=[valid | {"risk_ref": "risk_state_item:missing"}])
    assert unknown_risk.value.code == "risk_signal_unknown_risk_ref"

    with pytest.raises(RiskSignalError) as unknown_source:
        _risk_signal(
            signal_observations=[
                valid | {"source_refs": ["source_occurrence:not-in-risk-ceo"]}
            ]
        )
    assert unknown_source.value.code == "risk_signal_unknown_source_ref"

    with pytest.raises(RiskSignalError) as duplicate:
        _risk_signal(signal_observations=[valid, valid | {"predicate_id": "predicate:x:y"}])
    assert duplicate.value.code == "risk_signal_duplicate_id"


def test_bad_digests_enums_policy_and_raw_material_are_rejected() -> None:
    basis = _risk_ceo_outputs()
    basis["risk_state_snapshot"]["snapshot_digest"] = "sha256:not-a-real-digest"  # type: ignore[index]
    with pytest.raises(RiskSignalError) as digest_error:
        _risk_signal(basis)
    assert digest_error.value.code == "risk_signal_digest_invalid"

    with pytest.raises(RiskSignalError) as policy_error:
        _risk_signal(policy_version="")
    assert policy_error.value.code == "risk_signal_required_field_missing"

    row = {
        "risk_signal_id": "risk_signal:bad",
        "predicate_id": "predicate:cost:open",
        "risk_ref": "risk_state_item:risk-cost",
        "severity": "urgent",
        "status": "open",
        "owner_role": "project_manager",
        "source_refs": ["source_occurrence:so-risk"],
    }
    with pytest.raises(RiskSignalError) as severity_error:
        _risk_signal(signal_observations=[row])
    assert severity_error.value.code == "risk_signal_severity_invalid"

    with pytest.raises(RiskSignalError) as status_error:
        _risk_signal(signal_observations=[row | {"severity": "medium", "status": "new"}])
    assert status_error.value.code == "risk_signal_status_invalid"

    with pytest.raises(RiskSignalError) as raw_error:
        _risk_signal(signal_observations=[row | {"severity": "medium", "raw_ai": "..."}])
    assert raw_error.value.code == "risk_signal_raw_material_rejected"
