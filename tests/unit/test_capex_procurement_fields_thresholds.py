from __future__ import annotations

import copy

import pytest

from onetruth.capex_platform.procurement_fields_thresholds import (
    ANNEX_B_PROCUREMENT_FIELD_IDS,
    ANNEX_B_THRESHOLD_FAMILIES,
    COMMERCIAL_EVIDENCE_CANNOT_CLOSE_DIMENSIONS,
    COMMERCIAL_OBSERVATION_BOUNDARY_SCHEMA_VERSION,
    EXECUTIVE_ESCALATION_THRESHOLD_FAMILY_REGISTER_SCHEMA_VERSION,
    PROCUREMENT_FIELDS_THRESHOLDS_ACTIVATION_POSTURE,
    PROCUREMENT_FIELDS_THRESHOLDS_OUTPUTS_SCHEMA_VERSION,
    PROCUREMENT_REQUIRED_FIELD_REGISTER_SCHEMA_VERSION,
    REQUIRED_SIGNOFF_GATE_REFS,
    ProcurementFieldsThresholdsError,
    build_procurement_fields_and_threshold_policy_outputs,
    procurement_fields_thresholds_digest,
)


NOW = "2026-06-23T00:00:00Z"


def _outputs(**overrides: object) -> dict[str, object]:
    payload: dict[str, object] = {
        "policy_id": "procurement-threshold-policy-001",
        "created_at": NOW,
        "created_by_actor_id": "human:controller",
        "created_by_actor_type": "human",
    }
    payload.update(overrides)
    return build_procurement_fields_and_threshold_policy_outputs(**payload)  # type: ignore[arg-type]


def test_defaults_reflect_annex_b_fields_and_threshold_families() -> None:
    outputs = _outputs()
    fields = outputs["procurement_required_field_register"]["rows"]  # type: ignore[index]
    threshold_families = outputs[
        "executive_escalation_threshold_family_register"
    ]["rows"]  # type: ignore[index]

    assert outputs["schema_version"] == PROCUREMENT_FIELDS_THRESHOLDS_OUTPUTS_SCHEMA_VERSION
    assert outputs["activation_posture"] == PROCUREMENT_FIELDS_THRESHOLDS_ACTIVATION_POSTURE
    assert outputs["signoff_gate_refs"] == sorted(REQUIRED_SIGNOFF_GATE_REFS)
    assert outputs["procurement_required_field_register"]["schema_version"] == (  # type: ignore[index]
        PROCUREMENT_REQUIRED_FIELD_REGISTER_SCHEMA_VERSION
    )
    assert outputs["executive_escalation_threshold_family_register"]["schema_version"] == (  # type: ignore[index]
        EXECUTIVE_ESCALATION_THRESHOLD_FAMILY_REGISTER_SCHEMA_VERSION
    )
    assert outputs["commercial_observation_boundary"]["schema_version"] == (  # type: ignore[index]
        COMMERCIAL_OBSERVATION_BOUNDARY_SCHEMA_VERSION
    )
    assert {row["field_id"] for row in fields} == set(ANNEX_B_PROCUREMENT_FIELD_IDS)
    assert {row["threshold_family_label"] for row in threshold_families} == set(
        ANNEX_B_THRESHOLD_FAMILIES
    )
    assert outputs["executive_escalation_threshold_family_register"][  # type: ignore[index]
        "threshold_value_policy"
    ] == "no_numeric_thresholds_invented_by_platform"
    assert outputs["executive_escalation_threshold_family_register"][  # type: ignore[index]
        "threshold_values_present"
    ] is False
    assert procurement_fields_thresholds_digest(outputs).startswith("sha256:")


def test_output_is_deterministic_with_unsorted_rows() -> None:
    first = _outputs()
    fields = list(
        reversed(first["procurement_required_field_register"]["rows"])  # type: ignore[index]
    )
    threshold_families = list(
        reversed(
            first["executive_escalation_threshold_family_register"]["rows"]  # type: ignore[index]
        )
    )
    second = _outputs(field_rows=fields, threshold_family_rows=threshold_families)

    assert first == second


def test_numeric_thresholds_and_bad_gate_refs_are_rejected() -> None:
    outputs = _outputs()
    threshold_families = copy.deepcopy(
        outputs["executive_escalation_threshold_family_register"]["rows"]  # type: ignore[index]
    )
    threshold_families[0]["threshold_value"] = 10

    with pytest.raises(ProcurementFieldsThresholdsError) as numeric_error:
        _outputs(threshold_family_rows=threshold_families)
    assert numeric_error.value.code == "procurement_numeric_threshold_value_forbidden"

    with pytest.raises(ProcurementFieldsThresholdsError) as gate_error:
        _outputs(signoff_gate_refs=["SME-RP-G006"])
    assert gate_error.value.code == "procurement_required_signoff_gate_refs_missing"


def test_commercial_boundary_duplicate_ids_and_raw_material_are_rejected() -> None:
    outputs = _outputs()
    fields = copy.deepcopy(
        outputs["procurement_required_field_register"]["rows"]  # type: ignore[index]
    )
    fields[0]["closes_dimensions"] = ["technical"]
    with pytest.raises(ProcurementFieldsThresholdsError) as closure_error:
        _outputs(field_rows=fields)
    assert closure_error.value.code == "procurement_commercial_closure_boundary_violation"

    duplicate_fields = copy.deepcopy(
        outputs["procurement_required_field_register"]["rows"]  # type: ignore[index]
    )
    duplicate_fields.append(copy.deepcopy(duplicate_fields[0]))
    with pytest.raises(ProcurementFieldsThresholdsError) as duplicate_error:
        _outputs(field_rows=duplicate_fields)
    assert duplicate_error.value.code == "procurement_duplicate_field_id"

    raw_fields = copy.deepcopy(
        outputs["procurement_required_field_register"]["rows"]  # type: ignore[index]
    )
    raw_fields[0]["raw_content"] = "copied procurement excerpt"
    with pytest.raises(ProcurementFieldsThresholdsError) as raw_error:
        _outputs(field_rows=raw_fields)
    assert raw_error.value.code == "procurement_raw_material_rejected"


def test_commercial_evidence_cannot_close_core_dimensions_and_no_activation_effects() -> None:
    outputs = _outputs()
    boundary = outputs["commercial_observation_boundary"]  # type: ignore[assignment]

    assert boundary["commercial_evidence_can_directly_close_dimensions"] is False
    assert set(boundary["commercial_evidence_cannot_close_dimensions"]) == set(
        COMMERCIAL_EVIDENCE_CANNOT_CLOSE_DIMENSIONS
    )
    assert outputs["truth_effects"] == {
        "creates_workflow_run": False,
        "creates_tasks": False,
        "creates_approvals": False,
        "creates_threshold_values": False,
        "activates_thresholds": False,
        "activates_procurement_workflow": False,
        "creates_erp_or_accounting_behavior": False,
        "creates_ceo_cockpit_state": False,
        "creates_official_project_state": False,
        "writes_artifacts": False,
        "promotes_official_pointers": False,
        "activates_workflow_pack": False,
    }
