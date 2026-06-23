from __future__ import annotations

import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

from onetruth.capex_platform.ceo_transparency_snapshot import (
    CEO_TRANSPARENCY_SNAPSHOT_ACTIVATION_POSTURE,
    CEO_TRANSPARENCY_SNAPSHOT_ARTIFACT_KIND,
    CEO_TRANSPARENCY_SNAPSHOT_ARTIFACT_ROLE,
    CEO_TRANSPARENCY_SNAPSHOT_FILE_NAME,
    CEO_TRANSPARENCY_SNAPSHOT_SCHEMA_VERSION,
    CeoTransparencySnapshotError,
    build_ceo_transparency_snapshot,
    build_ceo_transparency_snapshot_envelope,
    ceo_transparency_snapshot_digest,
)
from onetruth.capex_platform.generated_artifact_validators import (
    capex_generated_artifact_digest,
    validate_capex_generated_artifact_envelope,
)


ROOT = Path(__file__).resolve().parents[2]
SCHEMA_PATH = ROOT / "schemas/runtime/capex_ceo_transparency_snapshot.schema.json"
NOW = "2026-06-23T00:00:00Z"
SOURCE_REF = "source_occurrence:so-ceo"
INPUT_DIGEST = "sha256:" + ("a" * 64)


def _snapshot(**overrides: object) -> dict[str, object]:
    payload: dict[str, object] = {
        "snapshot_id": "ceo-snapshot-001",
        "tenant_id": "tenant-a",
        "domain_id": "domain-x",
        "project_id": "project-ceo",
        "created_at": NOW,
        "created_by_actor_id": "human:pm",
        "created_by_actor_type": "human",
        "source_refs": [SOURCE_REF],
        "input_digests": [INPUT_DIGEST],
        "forecastability_grade": "forecastable",
        "caveats": [
            {
                "caveat_id": "caveat-reviewed-basis",
                "caveat_type": "management_attention",
                "caveat_label": "Reviewed basis contains management attention items",
                "source_refs": [SOURCE_REF],
            }
        ],
        "management_actions": [
            {
                "action_id": "action-mitigate",
                "action_label": "Assign owner for mitigation package",
                "owner_role": "project_manager",
                "action_status": "open",
                "forecast_date": "2026-07-15",
                "source_refs": [SOURCE_REF],
                "drilldown_refs": ["risk_state_item:risk-cost"],
            }
        ],
        "drilldown_refs": [
            {
                "drilldown_id": "drill-risk",
                "drilldown_kind": "risk_state_item",
                "target_ref": "risk_state_item:risk-cost",
                "source_refs": [SOURCE_REF],
            }
        ],
    }
    payload.update(overrides)
    return build_ceo_transparency_snapshot(**payload)  # type: ignore[arg-type]


def test_valid_ceo_snapshot_matches_payload_schema() -> None:
    snapshot = _snapshot()
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))

    Draft202012Validator(schema).validate(snapshot)

    assert snapshot["schema_version"] == CEO_TRANSPARENCY_SNAPSHOT_SCHEMA_VERSION
    assert snapshot["artifact_kind"] == CEO_TRANSPARENCY_SNAPSHOT_ARTIFACT_KIND
    assert snapshot["artifact_file_name"] == CEO_TRANSPARENCY_SNAPSHOT_FILE_NAME
    assert snapshot["activation_posture"] == CEO_TRANSPARENCY_SNAPSHOT_ACTIVATION_POSTURE
    assert snapshot["forecastability"]["grade"] == "forecastable"  # type: ignore[index]
    assert snapshot["truth_effects"] == {
        "creates_workflow_run": False,
        "creates_risk_engine_state": False,
        "creates_ceo_cockpit_state": False,
        "creates_closure_snapshots": False,
        "creates_official_project_state": False,
        "writes_artifacts": False,
        "promotes_official_pointers": False,
        "activates_workflow_pack": False,
    }


def test_snapshot_digest_is_deterministic_and_generated_artifact_compatible() -> None:
    first = _snapshot()
    second = _snapshot(
        source_refs=[SOURCE_REF],
        input_digests=[INPUT_DIGEST],
        caveats=list(reversed(first["caveats"])),  # type: ignore[arg-type]
        management_actions=list(reversed(first["management_actions"])),  # type: ignore[arg-type]
        drilldown_refs=list(reversed(first["drilldown_refs"])),  # type: ignore[arg-type]
    )
    envelope = build_ceo_transparency_snapshot_envelope(first)

    assert first == second
    assert ceo_transparency_snapshot_digest(first).startswith("sha256:")
    assert envelope["artifact_kind"] == CEO_TRANSPARENCY_SNAPSHOT_ARTIFACT_KIND
    assert envelope["artifact_role"] == CEO_TRANSPARENCY_SNAPSHOT_ARTIFACT_ROLE

    result = validate_capex_generated_artifact_envelope(
        file_name=CEO_TRANSPARENCY_SNAPSHOT_FILE_NAME,
        envelope=envelope,
        expected_content_digest=capex_generated_artifact_digest(envelope),
    )
    assert result.valid is True
    assert result.error_codes == ()


def test_not_forecastable_blocks_false_precision() -> None:
    caveats = [
        {
            "caveat_id": "caveat-not-forecastable",
            "caveat_type": "not_forecastable",
            "caveat_label": "Reviewed evidence does not support a CEO forecast",
            "source_refs": [SOURCE_REF],
        }
    ]
    valid = _snapshot(
        forecastability_grade="not_forecastable",
        caveats=caveats,
        management_actions=[
            {
                "action_id": "action-blocked",
                "action_label": "Resolve evidence blocker",
                "owner_role": "project_manager",
                "action_status": "blocked",
                "source_refs": [SOURCE_REF],
                "drilldown_refs": ["project_state_component:official_pointer_posture"],
            }
        ],
        drilldown_refs=[
            {
                "drilldown_id": "drill-blocker",
                "drilldown_kind": "project_state_component",
                "target_ref": "project_state_component:official_pointer_posture",
                "source_refs": [SOURCE_REF],
            }
        ],
    )
    assert valid["forecastability"]["exact_forecast_fields_allowed"] is False  # type: ignore[index]

    with pytest.raises(CeoTransparencySnapshotError) as exc_info:
        _snapshot(
            forecastability_grade="not_forecastable",
            caveats=caveats,
            management_actions=[
                {
                    "action_id": "action-false-precision",
                    "action_label": "Bad precise forecast",
                    "owner_role": "project_manager",
                    "action_status": "blocked",
                    "forecast_date": "2026-07-15",
                    "source_refs": [SOURCE_REF],
                    "drilldown_refs": ["risk_state_item:risk-cost"],
                }
            ],
        )
    assert exc_info.value.code == "ceo_transparency_false_precision_forbidden"


def test_source_refs_and_raw_ai_output_are_rejected() -> None:
    with pytest.raises(CeoTransparencySnapshotError) as source_error:
        _snapshot(source_refs=[])
    assert source_error.value.code == "ceo_transparency_source_refs_required"

    with pytest.raises(CeoTransparencySnapshotError) as bad_ref:
        _snapshot(source_refs=["artifact_version:not-source"])
    assert bad_ref.value.code == "ceo_transparency_source_ref_invalid"

    actions = [
        {
            "action_id": "action-raw",
            "action_label": "Contains raw output",
            "owner_role": "project_manager",
            "action_status": "open",
            "ai_output": "unreviewed model prose",
            "source_refs": [SOURCE_REF],
            "drilldown_refs": ["risk_state_item:risk-cost"],
        }
    ]
    with pytest.raises(CeoTransparencySnapshotError) as raw_error:
        _snapshot(management_actions=actions)
    assert raw_error.value.code == "ceo_transparency_raw_material_rejected"
