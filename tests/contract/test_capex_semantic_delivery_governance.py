from __future__ import annotations

import csv
from pathlib import Path

from tests.helpers.repo_paths import REPO_ROOT


DELIVERY_DIR = REPO_ROOT / "docs/planning/capex_delivery"
GOAL_PATH = DELIVERY_DIR / "MASTER_Product_Goal_and_Metrics.md"
METRICS_PATH = DELIVERY_DIR / "Product_Goal_Metric_Stack.csv"
SLICES_PATH = DELIVERY_DIR / "Vertical_Slice_Ladder.csv"
EXPECTED_METRIC_CATEGORIES = {"outcome", "learning", "flow", "quality", "operability"}
EXPECTED_SLICE_IDS = ["VS-00", "VS-01", "VS-02", "VS-03", "VS-04", "VS-05"]
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


def _csv_rows(path: Path) -> list[dict[str, str]]:
    return list(csv.DictReader(path.read_text(encoding="utf-8").splitlines()))


def _all_delivery_text() -> str:
    return "\n".join(
        path.read_text(encoding="utf-8")
        for path in (GOAL_PATH, METRICS_PATH, SLICES_PATH)
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


def test_capex_slice_ladder_leaves_dependency_register_to_task_0584() -> None:
    goal_text = GOAL_PATH.read_text(encoding="utf-8")
    task_0584 = (
        REPO_ROOT
        / "codex/tasks/TASK-0584-add-dependency-register-and-risk-based-milestone-overlay.md"
    ).read_text(encoding="utf-8")

    assert "that follow-on work remains `TASK-0584`" in goal_text
    assert "status: TODO" in task_0584
