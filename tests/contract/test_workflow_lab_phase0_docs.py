from __future__ import annotations

from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
WORKFLOW_LAB_README_PATH = REPO_ROOT / "docs/workflow_lab/README.md"
WORKFLOW_LAB_AUTHORITY_PATH = REPO_ROOT / "docs/workflow_lab/AUTHORITY_BOUNDARY.md"
WORKFLOW_LAB_PHASED_PLAN_PATH = REPO_ROOT / "docs/workflow_lab/PHASED_PLAN.md"
AUTHORITY_MODEL_PATH = REPO_ROOT / "docs/architecture/AUTHORITY_MODEL.md"
DERIVATION_POLICY_PATH = REPO_ROOT / "docs/architecture/DERIVATION_AND_GENERATION_POLICY.md"
PLAN_PATH = REPO_ROOT / "docs/planning/PRODUCTION_AND_WORKFLOW_LAB_PLAN.md"
EPIC_PATH = REPO_ROOT / "docs/planning/epics/EPIC-110.md"
CONTEXT_PATH = REPO_ROOT / "codex/context/EPIC-110.md"


def test_workflow_lab_phase0_docs_freeze_boundary_and_scope() -> None:
    readme = WORKFLOW_LAB_README_PATH.read_text(encoding="utf-8")
    authority_boundary = WORKFLOW_LAB_AUTHORITY_PATH.read_text(encoding="utf-8")
    phased_plan = WORKFLOW_LAB_PHASED_PLAN_PATH.read_text(encoding="utf-8")

    assert "thin internal candidate-evaluation lane" in readme
    assert "non-authoritative" in readme
    assert "`lab -> review/certification/release -> prod`" in readme
    assert "execution variants under fixed semantics" in readme
    assert "no public Workflow Lab API or UI in Phase 0" in readme
    assert "no `src/onetruth/workflow_lab/` package is required in Phase 0" in readme
    assert "Tenant/domain separation inside one environment is not an acceptable substitute." in readme

    assert "evidence or derived material" in authority_boundary
    assert "Workflow Lab must not mutate production runtime state directly." in authority_boundary
    assert "a second semantics compiler" in authority_boundary
    assert "a public product surface in Phase 0" in authority_boundary
    assert "semantic/version changes as if they were merely execution variants" in authority_boundary
    assert "separate DBs, artifact roots, and secrets" in authority_boundary

    assert "TASK-0118" in phased_plan
    assert "TASK-0119" in phased_plan
    assert "TASK-0121" in phased_plan
    assert "TASK-0122" in phased_plan
    assert "G1 recap" in phased_plan
    assert "G2 recap" in phased_plan


def test_workflow_lab_phase0_docs_align_with_authority_and_planning() -> None:
    authority_model = AUTHORITY_MODEL_PATH.read_text(encoding="utf-8")
    derivation_policy = DERIVATION_POLICY_PATH.read_text(encoding="utf-8")
    plan = PLAN_PATH.read_text(encoding="utf-8")
    epic = EPIC_PATH.read_text(encoding="utf-8")
    context = CONTEXT_PATH.read_text(encoding="utf-8")

    assert (
        "Workflow Lab outputs may exist as derived material or as explicitly linked evidence artifacts."
        in authority_model
    )
    assert "Workflow Lab reports, freshness summaries, or compare packets as production truth" in authority_model

    assert "Workflow Lab reports, freshness summaries, compare packets, and candidate evaluations may inform review" in derivation_policy
    assert "do not themselves change official state or authorize promotion" in derivation_policy

    assert "docs/workflow_lab/README.md" in plan
    assert "docs/workflow_lab/AUTHORITY_BOUNDARY.md" in plan
    assert "docs/workflow_lab/PHASED_PLAN.md" in plan

    assert "docs/workflow_lab/README.md" in epic
    assert "docs/workflow_lab/README.md" in context
    assert "TASK-0118" in epic
    assert "TASK-0118" in context
