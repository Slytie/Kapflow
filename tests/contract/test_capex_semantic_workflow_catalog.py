from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from tests.helpers.repo_paths import REPO_ROOT


PROPOSAL_PATH = (
    REPO_ROOT
    / "docs/planning/capex_workflow_catalog/"
    "procurement_escalation_workflow_proposal.yaml"
)
ANNEX_B_PATH = (
    REPO_ROOT
    / "docs/planning/capex_real_project_acceptance/"
    "ANNEX_B_MANDATORY_FIELDS_AND_ESCALATION_THRESHOLDS_DRAFT.md"
)
TASK_0659_PATH = (
    REPO_ROOT
    / "codex/tasks/"
    "TASK-0659-define-procurement-fields-and-executive-escalation-thresholds.md"
)
RAW_CORPUS_MARKERS = (
    "projektordner",
    "reference project",
    "blind-validation",
    "alma ruma",
    "11639 otc",
)


def _proposal() -> dict[str, Any]:
    loaded = yaml.safe_load(PROPOSAL_PATH.read_text(encoding="utf-8"))
    assert isinstance(loaded, dict)
    return loaded


def _annex_threshold_families() -> list[str]:
    text = ANNEX_B_PATH.read_text(encoding="utf-8")
    threshold_section = text.split("## Escalation threshold families", 1)[1]
    return [
        line.removeprefix("- ").strip()
        for line in threshold_section.splitlines()
        if line.startswith("- ")
    ]


def test_procurement_escalation_proposal_is_planning_only_catalog_evidence() -> None:
    proposal = _proposal()

    assert proposal["schema_version"] == "capex.workflow_catalog.proposal.v1"
    assert proposal["proposal_id"] == "capex.procurement_escalation.workflow_proposal.v1"
    assert proposal["activation_posture"] == "planning_only_no_capex_activation"
    assert proposal["catalog_surface"] == "planning_only_capex_workflow_catalog"
    assert proposal["source_task_ref"] == "TASK-0571"
    assert proposal["gate_refs"] == ["NU-GATE-011"]
    assert set(proposal["depends_on_gate_refs"]) == {
        "SME-RP-G006",
        "SME-RP-G007",
        "SME-RP-G012",
    }
    assert "TASK-0659" in proposal["remaining_activation_task_refs"]
    assert set(proposal["cannot_be_used_for"]) >= {
        "capex_runtime_activation",
        "product_activation",
        "public_route_activation",
        "authored_workflow_pack_activation",
        "migration_approval",
        "raw_corpus_import",
        "threshold_signoff",
        "procurement_field_signoff",
    }


def test_procurement_escalation_proposal_uses_task_chain_not_workpage_status() -> None:
    proposal = _proposal()
    task_ids = [task["task_id"] for task in proposal["task_chain"]]

    assert task_ids == [
        "capex.procurement_decision_package.prepare",
        "capex.procurement_evidence.reconcile",
        "capex.commercial_variance.review",
        "capex.ceo_sponsor.escalation_decide",
        "capex.post_decision.conditions_track",
    ]
    assert {
        task["canonical_output"] for task in proposal["task_chain"]
    } <= set(proposal["canonical_substrate"]["allowed_outputs"])
    assert "approval" in {
        task["canonical_output"] for task in proposal["task_chain"]
    }
    assert set(proposal["canonical_substrate"]["forbidden_outputs"]) >= {
        "workpage_state",
        "generic_status_command",
        "external_status",
        "ai_output",
    }
    assert proposal["workpage_boundary"]["blocker_routing"] == (
        "canonical_task_chain_required"
    )
    assert set(proposal["workpage_boundary"]["workpages_must_not"]) >= {
        "set_official_project_status",
        "set_closure",
        "set_evidence_sufficiency",
        "set_commercial_status",
        "edit_procurement_status_as_truth",
        "bypass_task_chain",
        "promote_pointer_directly",
    }


def test_procurement_escalation_thresholds_reference_annex_without_signoff() -> None:
    proposal = _proposal()
    task_0659_text = TASK_0659_PATH.read_text(encoding="utf-8")

    assert proposal["escalation_gates"]["threshold_families"] == (
        _annex_threshold_families()
    )
    assert proposal["escalation_gates"]["threshold_value_policy"] == (
        "no_numeric_thresholds_invented_by_platform"
    )
    assert set(proposal["escalation_gates"]["requires_business_signoff_gate_refs"]) == {
        "SME-RP-G006",
        "SME-RP-G007",
    }
    assert "status: TODO" in task_0659_text
    assert "TASK-0659" in proposal["remaining_activation_task_refs"]


def test_procurement_escalation_proposal_contains_no_raw_corpus_markers() -> None:
    lowered = PROPOSAL_PATH.read_text(encoding="utf-8").lower()

    for marker in RAW_CORPUS_MARKERS:
        assert marker not in lowered
