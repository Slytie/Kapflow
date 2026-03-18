from __future__ import annotations

from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
GATE_DOC_PATH = REPO_ROOT / "docs" / "workflow_lab" / "PROMOTION_GATE.md"
WORKFLOW_LAB_README_PATH = REPO_ROOT / "docs" / "workflow_lab" / "README.md"
WORKFLOW_LAB_PHASED_PLAN_PATH = REPO_ROOT / "docs" / "workflow_lab" / "PHASED_PLAN.md"
WORKFLOW_LAB_NORMALIZATION_PATH = REPO_ROOT / "docs" / "workflow_lab" / "NORMALIZATION.md"
PLAN_PATH = REPO_ROOT / "docs" / "planning" / "PRODUCTION_AND_WORKFLOW_LAB_PLAN.md"
TOPOLOGY_PATH = REPO_ROOT / "docs" / "ops" / "production_lab_topology.md"
TASK_0121_PATH = REPO_ROOT / "codex" / "tasks" / "TASK-0121-gated-variantspec-runprofile-and-first-stage04-lab-adapter.md"
TASK_0122_PATH = REPO_ROOT / "codex" / "tasks" / "TASK-0122-gated-world-materialization-compare-report-and-semantic-version-coexistence-plan.md"


def test_workflow_lab_promotion_gate_doc_freezes_release_mediated_gate_contract() -> None:
    gate_doc = GATE_DOC_PATH.read_text(encoding="utf-8")

    assert "authoritative repo-native reference for the promotion gate `G`" in gate_doc
    assert "`lab evidence + review/certification + tagged release -> production deploy`" in gate_doc
    assert "reviewed process" in gate_doc
    assert "candidate release" in gate_doc
    assert "`release_source_bundle` is the only promotion/deploy artifact" in gate_doc
    assert "tagged release" in gate_doc
    assert "production deploy from `release_source_bundle`" in gate_doc
    assert "not live runtime mutation from lab into prod" in gate_doc
    assert "`handoff_source_bundle`" in gate_doc
    assert "`runtime_workspace_bundle`" in gate_doc
    assert "`bundle_manifest.json`" in gate_doc
    assert "`release_provenance.json`" in gate_doc
    assert "Overall status: `UNCLEARED`" in gate_doc
    assert "no repo-native evidence currently records production deployment through the official release path" in gate_doc
    assert "actual restore rehearsal evidence is still missing" in gate_doc
    assert "A gate criterion is not met merely because design docs exist." in gate_doc
    assert "`TASK-0121` remains blocked until `G1` is explicitly recorded as cleared here." in gate_doc
    assert "`TASK-0122` remains blocked until `G2` is explicitly recorded as cleared here." in gate_doc


def test_gate_doc_is_cross_linked_and_future_tasks_point_to_it() -> None:
    readme = WORKFLOW_LAB_README_PATH.read_text(encoding="utf-8")
    phased_plan = WORKFLOW_LAB_PHASED_PLAN_PATH.read_text(encoding="utf-8")
    normalization = WORKFLOW_LAB_NORMALIZATION_PATH.read_text(encoding="utf-8")
    plan = PLAN_PATH.read_text(encoding="utf-8")
    topology = TOPOLOGY_PATH.read_text(encoding="utf-8")
    task_0121 = TASK_0121_PATH.read_text(encoding="utf-8")
    task_0122 = TASK_0122_PATH.read_text(encoding="utf-8")

    assert "PROMOTION_GATE.md" in readme
    assert "PROMOTION_GATE.md" in phased_plan
    assert "PROMOTION_GATE.md" in normalization
    assert "PROMOTION_GATE.md" in plan
    assert "PROMOTION_GATE.md" in topology

    assert "docs/workflow_lab/PROMOTION_GATE.md" in task_0121
    assert "docs/workflow_lab/PROMOTION_GATE.md" in task_0122
    assert "Blocked until G1 is explicitly recorded in `docs/workflow_lab/PROMOTION_GATE.md`." in task_0121
    assert "Blocked until G2 is explicitly recorded in `docs/workflow_lab/PROMOTION_GATE.md`." in task_0122
