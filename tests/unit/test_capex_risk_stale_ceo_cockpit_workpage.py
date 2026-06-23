from __future__ import annotations

import copy

import pytest

from onetruth.capex_platform.risk_ceo_transparency_workflow import (
    build_risk_ceo_transparency_workflow_outputs,
)
from onetruth.capex_platform.risk_stale_ceo_cockpit_workpage import (
    RISK_COCKPIT_FORECASTABILITY_DISPLAY_SCHEMA_VERSION,
    RISK_COCKPIT_MANAGEMENT_ACTION_CARDS_SCHEMA_VERSION,
    RISK_COCKPIT_RISK_CARDS_SCHEMA_VERSION,
    RISK_COCKPIT_SOURCE_DRILLDOWNS_SCHEMA_VERSION,
    RISK_COCKPIT_STALE_BLOCKER_CARDS_SCHEMA_VERSION,
    RISK_STALE_CEO_COCKPIT_ACTIVATION_POSTURE,
    RISK_STALE_CEO_COCKPIT_PROJECTION_SCHEMA_VERSION,
    RiskStaleCeoCockpitWorkpageError,
    build_risk_stale_ceo_cockpit_projection,
    risk_stale_ceo_cockpit_projection_digest,
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


def _projection(
    basis: dict[str, object] | None = None,
) -> dict[str, object]:
    return build_risk_stale_ceo_cockpit_projection(
        risk_ceo_transparency_outputs=basis or _risk_ceo_outputs(),
        projection_id="risk-cockpit-001",
        created_at=NOW,
        created_by_actor_id="human:pm",
        created_by_actor_type="human",
    )


def test_builds_deterministic_cockpit_projection_from_risk_ceo_outputs() -> None:
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
    reversed_basis["risk_ceo_flags"]["rows"] = list(  # type: ignore[index]
        reversed(reversed_basis["risk_ceo_flags"]["rows"])  # type: ignore[index]
    )
    reversed_basis["ceo_transparency_snapshot"]["management_actions"] = list(  # type: ignore[index]
        reversed(
            reversed_basis["ceo_transparency_snapshot"]["management_actions"]  # type: ignore[index]
        )
    )

    first = _projection(basis)
    second = _projection(reversed_basis)

    assert first == second
    assert first["schema_version"] == RISK_STALE_CEO_COCKPIT_PROJECTION_SCHEMA_VERSION
    assert first["activation_posture"] == RISK_STALE_CEO_COCKPIT_ACTIVATION_POSTURE
    assert first["risk_cards"]["schema_version"] == RISK_COCKPIT_RISK_CARDS_SCHEMA_VERSION  # type: ignore[index]
    assert first["stale_blocker_cards"]["schema_version"] == (  # type: ignore[index]
        RISK_COCKPIT_STALE_BLOCKER_CARDS_SCHEMA_VERSION
    )
    assert first["ceo_management_action_cards"]["schema_version"] == (  # type: ignore[index]
        RISK_COCKPIT_MANAGEMENT_ACTION_CARDS_SCHEMA_VERSION
    )
    assert first["source_drilldown_refs"]["schema_version"] == (  # type: ignore[index]
        RISK_COCKPIT_SOURCE_DRILLDOWNS_SCHEMA_VERSION
    )
    assert first["forecastability_display"]["schema_version"] == (  # type: ignore[index]
        RISK_COCKPIT_FORECASTABILITY_DISPLAY_SCHEMA_VERSION
    )
    assert risk_stale_ceo_cockpit_projection_digest(first).startswith("sha256:")


def test_blockers_waivers_and_not_forecastable_display_propagate() -> None:
    projection = _projection(
        _risk_ceo_outputs(
            [
                _risk_observation(
                    risk_id="risk-missing",
                    observation_state="missing_evidence",
                    source_refs=["source_occurrence:so-missing"],
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
    )

    blocker_cards = projection["stale_blocker_cards"]["rows"]  # type: ignore[index]
    blocker_types = {card["blocker_type"] for card in blocker_cards}
    assert {
        "missing_evidence",
        "evidence_conflict",
        "ai_draft_only",
        "stale_pointer",
        "not_forecastable",
        "waiver_recorded",
    } <= blocker_types
    assert projection["forecastability_display"]["grade"] == "not_forecastable"  # type: ignore[index]
    assert projection["forecastability_display"]["exact_forecast_fields_allowed"] is False  # type: ignore[index]
    assert any(
        card["blocker_classification"] == "waiver_caveat"
        for card in blocker_cards
    )


def test_source_refs_drilldowns_duplicate_ids_and_raw_material_are_rejected() -> None:
    unknown_source = copy.deepcopy(_risk_ceo_outputs())
    unknown_source["risk_state_snapshot"]["rows"][0]["source_refs"] = [  # type: ignore[index]
        "source_occurrence:not-in-ceo-snapshot"
    ]
    with pytest.raises(RiskStaleCeoCockpitWorkpageError) as source_error:
        _projection(unknown_source)
    assert source_error.value.code == "risk_cockpit_unknown_source_ref"

    unknown_drilldown = copy.deepcopy(_risk_ceo_outputs())
    unknown_drilldown["ceo_transparency_snapshot"]["management_actions"][0][  # type: ignore[index]
        "drilldown_refs"
    ] = ["risk_state_item:unknown"]
    with pytest.raises(RiskStaleCeoCockpitWorkpageError) as drilldown_error:
        _projection(unknown_drilldown)
    assert drilldown_error.value.code == "risk_cockpit_unknown_drilldown_ref"

    duplicate = copy.deepcopy(_risk_ceo_outputs())
    duplicate["risk_state_snapshot"]["rows"].append(  # type: ignore[index]
        copy.deepcopy(duplicate["risk_state_snapshot"]["rows"][0])  # type: ignore[index]
    )
    with pytest.raises(RiskStaleCeoCockpitWorkpageError) as duplicate_error:
        _projection(duplicate)
    assert duplicate_error.value.code == "risk_cockpit_duplicate_card_id"

    raw = copy.deepcopy(_risk_ceo_outputs())
    raw["risk_state_snapshot"]["rows"][0]["raw_content"] = "copied prose"  # type: ignore[index]
    with pytest.raises(RiskStaleCeoCockpitWorkpageError) as raw_error:
        _projection(raw)
    assert raw_error.value.code == "risk_cockpit_raw_material_rejected"


def test_false_precision_and_no_public_runtime_official_effects() -> None:
    basis = _risk_ceo_outputs(
        [
            _risk_observation(
                observation_state="missing_evidence",
                source_refs=["source_occurrence:so-missing"],
            )
        ]
    )
    basis["ceo_transparency_snapshot"]["management_actions"][0]["forecast_date"] = (  # type: ignore[index]
        "2026-07-15"
    )
    with pytest.raises(RiskStaleCeoCockpitWorkpageError) as precision_error:
        _projection(basis)
    assert precision_error.value.code == "risk_cockpit_false_precision_forbidden"

    projection = _projection()
    assert projection["truth_effects"] == {
        "creates_public_route": False,
        "creates_frontend_route": False,
        "creates_ceo_cockpit_state": False,
        "creates_risk_engine_state": False,
        "creates_workflow_run": False,
        "creates_tasks": False,
        "creates_approvals": False,
        "creates_closure_snapshots": False,
        "creates_official_project_state": False,
        "writes_artifacts": False,
        "promotes_official_pointers": False,
        "activates_workflow_pack": False,
    }
