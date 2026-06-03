from __future__ import annotations

from pathlib import Path
import subprocess
import sys

import yaml

from tests.helpers.repo_paths import REPO_ROOT
from tests.helpers.suite_markers import (
    LOGISTICS_FIXTURE_REFERENCE_MARKERS,
    LOGISTICS_REGRESSION_TEST_GLOBS,
    is_logistics_regression_test_path,
)


MAKEFILE_PATH = REPO_ROOT / "Makefile"
MAIN_WORKFLOW_PATH = REPO_ROOT / ".github" / "workflows" / "main.yml"


def test_logistics_regression_manifest_globs_match_real_tests() -> None:
    matched_paths: set[str] = set()
    missing_patterns: list[str] = []

    for pattern in LOGISTICS_REGRESSION_TEST_GLOBS:
        matches = sorted(REPO_ROOT.glob(pattern))
        if not matches:
            missing_patterns.append(pattern)
        matched_paths.update(path.relative_to(REPO_ROOT).as_posix() for path in matches)

    assert missing_patterns == []
    assert "tests/runtime/scenarios/test_logistics_weekly_to_live_golden_slice.py" in matched_paths
    assert "tests/runtime/api/test_workpages_route_demand_contract.py" in matched_paths
    assert "tests/unit/test_schedule_control_validation.py" in matched_paths
    assert "tests/contract/test_handler_import_boundaries.py" not in matched_paths
    assert "tests/unit/test_approval_response_hooks.py" not in matched_paths


def test_tests_referencing_logistics_fixture_roots_are_classified_as_logistics_regressions() -> None:
    violations: list[str] = []

    for path in _test_files():
        text = path.read_text(encoding="utf-8")
        if not any(marker in text for marker in LOGISTICS_FIXTURE_REFERENCE_MARKERS):
            continue
        if is_logistics_regression_test_path(path, repo_root=REPO_ROOT):
            continue
        violations.append(path.relative_to(REPO_ROOT).as_posix())

    assert violations == []


def test_marker_selection_excludes_logistics_regressions_from_platform_expression() -> None:
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "pytest",
            "-q",
            "--collect-only",
            "-m",
            "not logistics_regression",
            "tests/runtime/api/test_weekly_publish_loop_api.py",
        ],
        cwd=REPO_ROOT,
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 5, result.stdout + result.stderr


def test_makefile_exposes_platform_and_logistics_test_lanes() -> None:
    text = MAKEFILE_PATH.read_text(encoding="utf-8")

    assert "platform-substrate-tests:" in text
    assert (
        'PYTHONPATH=src $(PYTEST) -m "not logistics_regression" '
        "tests/contract tests/unit tests/runtime/test_cli_timeline_smoke.py "
        "tests/runtime/test_workflow_task_core_cli.py "
        "tests/runtime/test_approvals_artifacts_pointers_cli.py "
        "tests/runtime/test_execution_session_runtime.py "
        "tests/runtime/test_projection_coherence.py "
        "tests/runtime/test_example_document_corpus_ingress.py "
        "tests/runtime/api/test_approval_respond_via_api.py "
        "tests/runtime/api/test_human_task_claim_via_api.py "
        "tests/runtime/api/test_human_task_complete_via_api.py "
        "tests/runtime/api/test_cross_scope_api_denial.py "
        "tests/security tests/property tests/integration"
        in text
    )
    assert "logistics-regression-tests:" in text
    assert (
        "PYTHONPATH=src $(PYTEST) -m logistics_regression "
        "tests/contract/test_logistics_control_layer_contracts.py "
        "tests/contract/test_logistics_definition_contracts.py "
        "tests/contract/test_logistics_docs_inventory.py "
        "tests/contract/test_logistics_operational_cadence_runbook_docs.py "
        "tests/contract/test_logistics_workpage_demo_runbook_docs.py "
        "tests/runtime/scenarios/test_logistics_weekly_to_live_golden_slice.py "
        "tests/runtime/scenarios/test_logistics_three_workflow_demo_story_seed.py "
        "tests/runtime/test_logistics_handoff_runtime.py "
        "tests/security/isolation/test_logistics_handoff_cross_scope_runtime.py"
        in text
    )


def test_main_workflow_exposes_platform_and_logistics_groupings() -> None:
    workflow = yaml.safe_load(MAIN_WORKFLOW_PATH.read_text(encoding="utf-8"))
    jobs = workflow["jobs"]
    domain_boundary = jobs["domain-boundary-tests"]

    assert domain_boundary["name"] == "domain-boundary / ${{ matrix.check }}"
    include = domain_boundary["strategy"]["matrix"]["include"]
    assert {
        (entry["check"], entry["make_target"])
        for entry in include
    } == {
        ("platform-substrate", "platform-substrate-tests"),
        ("logistics-regression", "logistics-regression-tests"),
    }

    workflow_text = MAIN_WORKFLOW_PATH.read_text(encoding="utf-8")
    assert "make PYTHON=python ${{ matrix.make_target }}" in workflow_text


def _test_files() -> list[Path]:
    return sorted((REPO_ROOT / "tests").rglob("test_*.py"))
