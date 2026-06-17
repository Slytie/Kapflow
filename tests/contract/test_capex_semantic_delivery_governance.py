from __future__ import annotations

import csv
import re
from pathlib import Path

from tests.helpers.repo_paths import REPO_ROOT


DELIVERY_DIR = REPO_ROOT / "docs/planning/capex_delivery"
GOAL_PATH = DELIVERY_DIR / "MASTER_Product_Goal_and_Metrics.md"
METRICS_PATH = DELIVERY_DIR / "Product_Goal_Metric_Stack.csv"
SLICES_PATH = DELIVERY_DIR / "Vertical_Slice_Ladder.csv"
DEPENDENCIES_PATH = DELIVERY_DIR / "MASTER_Dependency_Register.csv"
MILESTONES_PATH = DELIVERY_DIR / "Risk_Based_Milestone_Model.csv"
BACKLOG_GUIDE_PATH = DELIVERY_DIR / "Backlog_Taxonomy_and_Decomposition_Guide.md"
CADENCE_PATH = DELIVERY_DIR / "MASTER_Delivery_Operating_Cadence.md"
FIRST_90_DAYS_PATH = DELIVERY_DIR / "MASTER_First_90_Days_Execution_Overlay.md"
DOR_DOD_PATH = DELIVERY_DIR / "MASTER_Definition_of_Ready_Done.md"
PR_TEMPLATE_PATH = REPO_ROOT / ".github/pull_request_template.md"
TEMPLATES_DIR = DELIVERY_DIR / "templates"
EXPECTED_METRIC_CATEGORIES = {"outcome", "learning", "flow", "quality", "operability"}
EXPECTED_SLICE_IDS = ["VS-00", "VS-01", "VS-02", "VS-03", "VS-04", "VS-05"]
EXPECTED_MILESTONE_NAMES = [
    "stakeholder aligned",
    "architecture proven",
    "system viable",
    "business increment",
    "production ready",
]
EXPECTED_TEMPLATE_FILES = {
    "outcome_epic_template.md",
    "feature_template.md",
    "vertical_story_template.md",
    "gwt_acceptance_scenario_template.md",
}
EXPECTED_CADENCE_RHYTHMS = {
    "weekly refinement",
    "three-amigos",
    "monthly dependency/risk review",
    "demo/review",
    "8-12 week outcome roadmap refresh",
}
EXPECTED_90_DAY_ELEMENTS = {
    "goal/metrics",
    "dependency board",
    "ci baseline",
    "first slice demo",
    "first mmf",
    "roadmap refresh",
}
EXPECTED_DOR_DOD_CLASSES = {
    "architecture",
    "runtime",
    "workpage",
    "fixture",
    "agent-lab",
    "migration/release",
}
RAW_CORPUS_MARKERS = (
    "projektordner",
    "reference project",
    "blind-validation holdout",
    "alma ruma",
    "11639 otc",
)
ACTIVATION_PHRASES = (
    "public route activation",
    "product activation",
    "CAPEX runtime activation",
    "raw corpus import",
)
FORBIDDEN_ACTIVATION_CLAIMS = (
    "runtime activation approved",
    "product activation approved",
    "public activation approved",
    "public route activation approved",
    "capex activation approved",
)


def _csv_rows(path: Path) -> list[dict[str, str]]:
    return list(csv.DictReader(path.read_text(encoding="utf-8").splitlines()))


def _all_delivery_text() -> str:
    return "\n".join(
        path.read_text(encoding="utf-8")
        for path in sorted(DELIVERY_DIR.rglob("*"))
        if path.is_file()
    )


def test_capex_product_goal_and_metric_sources_exist_and_are_planning_only() -> None:
    goal_text = GOAL_PATH.read_text(encoding="utf-8")
    metrics = _csv_rows(METRICS_PATH)

    assert GOAL_PATH.exists()
    assert METRICS_PATH.exists()
    assert "Build a governed CAPEX evidence-to-decision workflow foundation" in goal_text
    assert "planning_only_no_capex_activation" in goal_text
    assert "Repo planning acceptance for `SD-GATE-001`" in goal_text
    assert "not implementation approval" in goal_text
    for phrase in ACTIVATION_PHRASES:
        assert phrase in goal_text
    assert metrics
    assert {row["activation_posture"] for row in metrics} == {
        "planning_only_no_capex_activation"
    }


def test_capex_metric_stack_covers_required_categories_without_velocity_only_bias() -> None:
    metrics = _csv_rows(METRICS_PATH)

    assert {row["category"] for row in metrics} == EXPECTED_METRIC_CATEGORIES
    assert {row["metric_id"] for row in metrics} >= {
        "MG-OUT-001",
        "MG-LRN-001",
        "MG-FLW-001",
        "MG-QLT-001",
        "MG-OPS-001",
    }
    for row in metrics:
        assert row["definition"], row
        assert row["source"], row
        assert row["desired_direction"] in {"higher", "lower"}, row
        assert row["guardrail"], row
        assert row["owner"], row
        if "velocity" in row["name"].lower() or "velocity" in row["definition"].lower():
            assert any(
                term in row["guardrail"].lower()
                for term in ("truth", "quality", "safety", "operability")
            ), row
    assert "No metric may reward velocity alone." in GOAL_PATH.read_text(encoding="utf-8")


def test_capex_vertical_slice_ladder_has_exact_rows_and_valid_metric_refs() -> None:
    metrics = {row["metric_id"] for row in _csv_rows(METRICS_PATH)}
    slices = _csv_rows(SLICES_PATH)

    assert [row["slice_id"] for row in slices] == EXPECTED_SLICE_IDS
    for row in slices:
        assert row["entry_gates"], row
        assert row["exit_gates"], row
        assert row["repo_evidence_refs"], row
        assert row["activation_posture"] == "planning_only_no_capex_activation", row
        assert row["non_demo_theater_guardrail"], row
        assert "demo" in row["non_demo_theater_guardrail"].lower(), row
        metric_refs = [value.strip() for value in row["metric_refs"].split(";")]
        assert metric_refs, row
        assert set(metric_refs) <= metrics, row


def test_capex_delivery_sources_preserve_non_activation_and_raw_boundary() -> None:
    lowered = _all_delivery_text().lower()

    assert "planning_only_no_capex_activation" in lowered
    assert "runtime activation" in lowered
    assert "raw corpus" in lowered
    for marker in RAW_CORPUS_MARKERS:
        assert marker not in lowered


def test_capex_dependency_register_and_milestone_model_are_planning_only() -> None:
    dependencies = _csv_rows(DEPENDENCIES_PATH)
    milestones = _csv_rows(MILESTONES_PATH)
    dependency_ids = {row["dependency_id"] for row in dependencies}

    assert dependencies
    assert milestones
    assert {row["activation_posture"] for row in dependencies} == {
        "planning_only_no_capex_activation"
    }
    assert {row["activation_posture"] for row in milestones} == {
        "planning_only_no_capex_activation"
    }
    for row in dependencies:
        assert row["owner"], row
        assert row["needed_by_milestone"], row
        assert row["mitigation"], row
        assert row["risk_if_late"], row
        assert row["status"] in {"satisfied", "open", "blocked"}, row
    assert {row["name"] for row in dependencies} >= {
        "Product goal and metric baseline",
        "Vertical-slice ladder baseline",
        "Source and evidence governance",
        "Closure and pointer safety",
        "Procurement and workflow routing",
        "Fixture governance",
        "Workpage guardrails",
        "Storage restore and preflight evidence",
        "Production preflight",
        "Backlog and cadence quality",
    }
    assert [row["milestone_name"] for row in milestones] == EXPECTED_MILESTONE_NAMES
    for row in milestones:
        refs = [value.strip() for value in row["dependency_refs"].split(";")]
        assert refs, row
        assert set(refs) <= dependency_ids, row
    production_ready = next(
        row for row in milestones if row["milestone_name"] == "production ready"
    )
    assert production_ready["status"] == "blocked"
    for required in ("restore", "capacity", "release", "storage", "raw-corpus", "production-preflight"):
        assert required in production_ready["blocked_reason"], production_ready


def test_capex_backlog_hierarchy_and_templates_are_singular_and_vertical() -> None:
    guide_text = BACKLOG_GUIDE_PATH.read_text(encoding="utf-8")
    lowered_guide = guide_text.lower()
    template_paths = {path.name: path for path in TEMPLATES_DIR.glob("*.md")}

    assert EXPECTED_TEMPLATE_FILES <= set(template_paths)
    assert (
        "product goal -> outcome epic -> feature -> vertical slice -> story -> given-when-then acceptance scenario"
        in lowered_guide
    )
    assert "one authoritative backlog" in lowered_guide
    assert "duplicate backlog systems" in lowered_guide
    assert "demo-only success" in lowered_guide
    assert "vertical, testable, metric-linked" in lowered_guide
    assert "planning_only_no_capex_activation" in lowered_guide
    for template_name, template_path in template_paths.items():
        text = template_path.read_text(encoding="utf-8")
        lowered = text.lower()
        assert "metric refs" in lowered, template_name
        assert "slice refs" in lowered, template_name
        assert "source/evidence refs" in lowered, template_name
        assert "given" in lowered and "when" in lowered and "then" in lowered, template_name
        assert "planning_only_no_capex_activation" in lowered, template_name
        assert "rollback" in lowered or "recovery" in lowered, template_name
        for phrase in FORBIDDEN_ACTIVATION_CLAIMS:
            assert phrase not in lowered, template_name


def test_capex_dependency_and_backlog_tasks_are_closed_with_evidence() -> None:
    goal_text = GOAL_PATH.read_text(encoding="utf-8")
    task_0584_text = (
        REPO_ROOT
        / "codex/tasks/TASK-0584-add-dependency-register-and-risk-based-milestone-overlay.md"
    ).read_text(encoding="utf-8")
    task_0585_text = (
        REPO_ROOT
        / "codex/tasks/TASK-0585-add-backlog-hierarchy-and-story-decomposition-templates.md"
    ).read_text(encoding="utf-8")

    assert "dependency register and risk milestone overlay" in goal_text
    for task_text in (task_0584_text, task_0585_text):
        assert "status: DONE" in task_text
        assert 'completed_at: "2026-06-17T00:00:00Z"' in task_text
        assert "## Closeout evidence" in task_text


def test_capex_delivery_cadence_is_lightweight_and_planning_only() -> None:
    cadence_text = CADENCE_PATH.read_text(encoding="utf-8")
    lowered = cadence_text.lower()

    assert "planning_only_no_capex_activation" in lowered
    assert "sd-gate-005" in lowered
    for rhythm in EXPECTED_CADENCE_RHYTHMS:
        assert rhythm in lowered
    for field in ("inputs", "outputs", "owner", "decision record"):
        assert field in lowered
    assert "lean governance" in lowered
    assert "no meeting bloat" in lowered
    assert "duplicate meeting" in lowered
    for phrase in FORBIDDEN_ACTIVATION_CLAIMS:
        assert phrase not in lowered


def test_capex_first_90_days_overlay_uses_ranges_and_existing_refs() -> None:
    overlay_text = FIRST_90_DAYS_PATH.read_text(encoding="utf-8")
    lowered = overlay_text.lower()
    metric_ids = {row["metric_id"].lower() for row in _csv_rows(METRICS_PATH)}
    slice_ids = {row["slice_id"].lower() for row in _csv_rows(SLICES_PATH)}
    dependency_ids = {row["dependency_id"].lower() for row in _csv_rows(DEPENDENCIES_PATH)}
    milestone_names = {
        row["milestone_name"].lower() for row in _csv_rows(MILESTONES_PATH)
    }

    assert "planning_only_no_capex_activation" in lowered
    assert "sd-gate-006" in lowered
    assert not re.search(r"\b20\d{2}-\d{2}-\d{2}\b", overlay_text)
    assert "no false date precision" in lowered
    for element in EXPECTED_90_DAY_ELEMENTS:
        assert element in lowered
    for phrase in ("blocker", "learning slice", "first mmf", "roadmap refresh"):
        assert phrase in lowered
    assert {"mg-out-001", "mg-lrn-001", "mg-flw-001"} <= metric_ids
    assert {"vs-00", "vs-01", "vs-03", "vs-05"} <= slice_ids
    assert {"dep-001", "dep-002", "dep-010"} <= dependency_ids
    for ref in (
        "mg-out-001",
        "mg-lrn-001",
        "mg-flw-001",
        "vs-00",
        "vs-01",
        "vs-03",
        "vs-05",
        "dep-001",
        "dep-002",
        "dep-010",
    ):
        assert ref in lowered
    for milestone_name in milestone_names:
        assert milestone_name in lowered
    for phrase in FORBIDDEN_ACTIVATION_CLAIMS:
        assert phrase not in lowered


def test_capex_definition_of_ready_done_covers_task_classes() -> None:
    text = DOR_DOD_PATH.read_text(encoding="utf-8")
    lowered = text.lower()

    assert "planning_only_no_capex_activation" in lowered
    assert "sd-gate-007" in lowered
    for task_class in EXPECTED_DOR_DOD_CLASSES:
        assert task_class in lowered
    for required in (
        "definition of ready",
        "definition of done",
        "tdd",
        "code review",
        "refactor separation",
        "source truth",
        "rollback",
        "recovery",
        "raw corpus",
    ):
        assert required in lowered
    for phrase in FORBIDDEN_ACTIVATION_CLAIMS:
        assert phrase not in lowered


def test_capex_pr_template_contains_dor_dod_consistency_checklist() -> None:
    text = PR_TEMPLATE_PATH.read_text(encoding="utf-8")
    lowered = text.lower()

    assert "capex dor/dod consistency" in lowered
    for required in (
        "source truth updated",
        "tests or accepted test-gap",
        "raw-data boundary",
        "activation boundary",
        "rollback/recovery",
        "generated/progress freshness",
    ):
        assert required in lowered
