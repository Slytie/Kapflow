from __future__ import annotations

from pathlib import Path

import yaml

from tests.helpers.repo_paths import REPO_ROOT
from tests.helpers.suite_markers import (
    CAPEX_SEMANTIC_TEST_GLOBS,
    is_capex_semantic_test_path,
)


MANIFEST_PATH = REPO_ROOT / "docs/planning/CAPEX_CB2_SEMANTIC_TEST_BACKLOG.yaml"
ALLOWED_PHASE_STATUSES = {"repo_evidence_green", "tracked_future_phase"}
RAW_CORPUS_MARKERS = (
    "projektordner",
    "reference project",
    "blind-validation holdout",
    "alma ruma",
    "11639 otc",
)


def _manifest() -> dict:
    loaded = yaml.safe_load(MANIFEST_PATH.read_text(encoding="utf-8"))
    assert isinstance(loaded, dict)
    return loaded


def test_capex_cb2_semantic_backlog_tracks_all_rows_in_order() -> None:
    rows = _manifest()["rows"]

    assert [row["cb2_id"] for row in rows] == [f"CB2-T{index:03d}" for index in range(1, 15)]
    assert {row["phase_status"] for row in rows} <= ALLOWED_PHASE_STATUSES
    assert "tracking_only_no_capex_activation" == _manifest()["activation_posture"]


def test_capex_cb2_semantic_rows_point_to_repo_evidence_or_future_phase() -> None:
    future_rows = []
    green_rows = []

    for row in _manifest()["rows"]:
        evidence_paths = row["evidence_paths"]
        assert evidence_paths, row["cb2_id"]
        assert row["gate_refs"], row["cb2_id"]
        assert row["task_refs"], row["cb2_id"]
        assert row["rationale"], row["cb2_id"]
        for relative in evidence_paths:
            assert (REPO_ROOT / relative).exists(), f"{row['cb2_id']} -> {relative}"
        if row["phase_status"] == "tracked_future_phase":
            future_rows.append(row["cb2_id"])
        else:
            green_rows.append(row["cb2_id"])

    assert set(future_rows) == {"CB2-T006", "CB2-T012"}
    assert {"CB2-T011", "CB2-T013", "CB2-T014"} <= set(green_rows)


def test_capex_semantic_marker_manifest_globs_match_real_tests() -> None:
    missing_patterns: list[str] = []
    matched_paths: set[str] = set()

    for pattern in CAPEX_SEMANTIC_TEST_GLOBS:
        matches = sorted(REPO_ROOT.glob(pattern))
        if not matches:
            missing_patterns.append(pattern)
        matched_paths.update(path.relative_to(REPO_ROOT).as_posix() for path in matches)

    assert missing_patterns == []
    assert "tests/contract/test_capex_semantic_test_suite.py" in matched_paths
    assert "tests/unit/test_capex_interface_burden_policy.py" in matched_paths
    assert "tests/unit/test_approval_response_hooks.py" not in matched_paths
    assert "tests/runtime/scenarios/test_logistics_weekly_to_live_golden_slice.py" not in matched_paths


def test_capex_semantic_marker_classifier_is_narrow() -> None:
    assert is_capex_semantic_test_path(
        REPO_ROOT / "tests/contract/test_capex_semantic_test_suite.py",
        repo_root=REPO_ROOT,
    )
    assert is_capex_semantic_test_path(
        REPO_ROOT / "tests/unit/test_capex_workpage_command_envelope.py",
        repo_root=REPO_ROOT,
    )
    assert not is_capex_semantic_test_path(
        REPO_ROOT / "tests/runtime/scenarios/test_logistics_weekly_to_live_golden_slice.py",
        repo_root=REPO_ROOT,
    )


def test_capex_semantic_backlog_contains_no_raw_corpus_markers() -> None:
    lowered = MANIFEST_PATH.read_text(encoding="utf-8").lower()

    for marker in RAW_CORPUS_MARKERS:
        assert marker not in lowered
