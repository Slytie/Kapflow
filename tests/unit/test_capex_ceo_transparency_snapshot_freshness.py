from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

from onetruth.capex_platform.ceo_transparency_snapshot import (
    CEO_TRANSPARENCY_SNAPSHOT_FRESHNESS_ACTIVATION_POSTURE,
    CEO_TRANSPARENCY_SNAPSHOT_FRESHNESS_SCHEMA_VERSION,
    CeoTransparencySnapshotError,
    build_ceo_transparency_snapshot_freshness_outputs,
    ceo_transparency_snapshot_freshness_digest,
)
from onetruth.capex_platform.risk_ceo_transparency_workflow import (
    build_risk_ceo_transparency_workflow_outputs,
)
from onetruth.capex_platform.risk_signal import build_risk_signal_outputs


ROOT = Path(__file__).resolve().parents[2]
SCHEMA_PATH = (
    ROOT / "schemas/runtime/capex_ceo_transparency_snapshot_freshness.schema.json"
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


def _risk_signal_outputs(basis: dict[str, object]) -> dict[str, object]:
    return build_risk_signal_outputs(
        risk_ceo_transparency_outputs=basis,
        signal_register_id="risk-signals-001",
        created_at=NOW,
        created_by_actor_id="human:pm",
        created_by_actor_type="human",
        policy_version="risk_signal_policy.v1",
    )


def _freshness(
    basis: dict[str, object] | None = None,
    snapshot: dict[str, object] | None = None,
    **overrides: object,
) -> dict[str, object]:
    risk_ceo = basis or _risk_ceo_outputs()
    payload: dict[str, object] = {
        "ceo_transparency_snapshot": snapshot or risk_ceo["ceo_transparency_snapshot"],
        "risk_ceo_transparency_outputs": risk_ceo,
        "freshness_id": "ceo-freshness-001",
        "created_at": NOW,
        "created_by_actor_id": "human:pm",
        "created_by_actor_type": "human",
        "project_snapshot_watermark": "snapshot:2026-06-23",
        "risk_snapshot_watermark": "snapshot:2026-06-23",
    }
    payload.update(overrides)
    return build_ceo_transparency_snapshot_freshness_outputs(**payload)  # type: ignore[arg-type]


def test_valid_w8_freshness_payload_matches_schema_and_is_deterministic() -> None:
    basis = _risk_ceo_outputs()
    first = _freshness(basis, risk_signal_outputs=_risk_signal_outputs(basis))
    second = _freshness(basis, risk_signal_outputs=_risk_signal_outputs(basis))
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))

    Draft202012Validator(schema).validate(first)

    assert first == second
    assert first["schema_version"] == CEO_TRANSPARENCY_SNAPSHOT_FRESHNESS_SCHEMA_VERSION
    assert (
        first["activation_posture"]
        == CEO_TRANSPARENCY_SNAPSHOT_FRESHNESS_ACTIVATION_POSTURE
    )
    assert first["freshness"]["freshness_state"] == "current"  # type: ignore[index]
    assert first["risk_signal_refs"] == ["risk_signal:risk-cost"]
    assert ceo_transparency_snapshot_freshness_digest(first).startswith("sha256:")
    assert first["truth_effects"] == {
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


def test_blocker_caveats_and_watermark_staleness_propagate() -> None:
    basis = _risk_ceo_outputs(
        [
            _risk_observation(
                risk_id="risk-missing",
                observation_state="missing_evidence",
                source_refs=["source_occurrence:so-missing"],
            ),
            _risk_observation(
                risk_id="risk-conflict",
                observation_state="conflict",
                project_state_component_id="owner_interface_resolution",
                source_refs=["source_occurrence:so-conflict"],
            ),
            _risk_observation(
                risk_id="risk-ai",
                observation_state="ai_draft_only",
                source_refs=["source_occurrence:so-ai"],
            ),
            _risk_observation(
                risk_id="risk-stale",
                observation_state="stale_pointer",
                project_state_component_id="official_pointer_posture",
                source_refs=["source_occurrence:so-stale"],
            ),
            _risk_observation(
                risk_id="risk-waiver",
                observation_state="waiver_recorded",
                source_refs=["source_occurrence:so-waiver"],
                waiver_refs=["waiver:waiver-001"],
            ),
        ]
    )

    output = _freshness(
        basis,
        risk_snapshot_watermark="snapshot:2026-06-22",
        risk_signal_outputs=_risk_signal_outputs(basis),
    )

    caveat_types = {row["caveat_type"] for row in output["caveat_propagation"]}  # type: ignore[index]
    assert {
        "evidence_missing",
        "evidence_conflict",
        "ai_draft_only",
        "stale_pointer",
        "waiver_recorded",
        "not_forecastable",
    } <= caveat_types
    assert output["freshness"]["freshness_state"] == "blocked"  # type: ignore[index]
    assert {
        "project_risk_watermark_mismatch",
        "missing_evidence_caveat",
        "evidence_conflict_caveat",
        "ai_draft_only_caveat",
        "stale_pointer_caveat",
    } <= set(output["freshness"]["stale_reasons"])  # type: ignore[index]


def test_scope_unknown_refs_and_bad_digests_are_rejected() -> None:
    basis = _risk_ceo_outputs()
    bad_scope = copy.deepcopy(basis)
    bad_scope["tenant_id"] = "other-tenant"
    with pytest.raises(CeoTransparencySnapshotError) as scope_error:
        _freshness(bad_scope)
    assert scope_error.value.code == "ceo_transparency_freshness_scope_mismatch"

    unknown_source = copy.deepcopy(basis)
    unknown_source["risk_ceo_flags"]["rows"].append(  # type: ignore[index]
        {
            "flag_id": "unknown-source",
            "risk_id": "risk-cost",
            "flag_type": "stale_pointer",
            "severity": "high",
            "source_refs": ["source_occurrence:not-in-ceo-snapshot"],
            "blocks_ceo_forecast": True,
            "creates_official_truth": False,
        }
    )
    with pytest.raises(CeoTransparencySnapshotError) as source_error:
        _freshness(unknown_source)
    assert source_error.value.code == "ceo_transparency_source_ref_not_in_snapshot"

    bad_digest = copy.deepcopy(basis)
    bad_digest["risk_state_snapshot"]["snapshot_digest"] = "sha256:bad"  # type: ignore[index]
    with pytest.raises(CeoTransparencySnapshotError) as digest_error:
        _freshness(bad_digest)
    assert digest_error.value.code == "ceo_transparency_freshness_digest_invalid"


def test_risk_signal_refs_false_precision_and_raw_content_are_rejected() -> None:
    basis = _risk_ceo_outputs(
        [_risk_observation(observation_state="missing_evidence")]
    )
    risk_signals = _risk_signal_outputs(basis)
    risk_signals["risk_signal_register"]["rows"][0]["source_refs"] = [  # type: ignore[index]
        "source_occurrence:not-in-ceo-snapshot"
    ]
    with pytest.raises(CeoTransparencySnapshotError) as signal_error:
        _freshness(basis, risk_signal_outputs=risk_signals)
    assert signal_error.value.code == "ceo_transparency_source_ref_not_in_snapshot"

    mutated_snapshot = copy.deepcopy(basis["ceo_transparency_snapshot"])
    mutated_snapshot["management_actions"][0]["forecast_date"] = "2026-07-15"  # type: ignore[index]
    with pytest.raises(CeoTransparencySnapshotError) as precision_error:
        _freshness(basis, snapshot=mutated_snapshot)  # type: ignore[arg-type]
    assert precision_error.value.code == "ceo_transparency_false_precision_forbidden"

    raw_snapshot = copy.deepcopy(basis["ceo_transparency_snapshot"])
    raw_snapshot["raw_ai"] = "unreviewed generated prose"  # type: ignore[index]
    with pytest.raises(CeoTransparencySnapshotError) as raw_error:
        _freshness(basis, snapshot=raw_snapshot)  # type: ignore[arg-type]
    assert raw_error.value.code == "ceo_transparency_raw_material_rejected"
