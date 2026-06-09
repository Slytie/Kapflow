from __future__ import annotations

from pathlib import Path

import yaml

from tests.helpers.repo_paths import REPO_ROOT


CODEOWNERS_PATH = REPO_ROOT / ".github/CODEOWNERS"
MAKEFILE_PATH = REPO_ROOT / "Makefile"
MAIN_WORKFLOW_PATH = REPO_ROOT / ".github/workflows/main.yml"
PYTEST_INI_PATH = REPO_ROOT / "pytest.ini"


SEMANTIC_CODEOWNER_PATHS = {
    "/docs/planning/CAPEX_CB2_SEMANTIC_TEST_BACKLOG.yaml",
    "/docs/architecture/CAPEX_INTERFACE_BURDEN_POLICY.md",
    "/src/onetruth/capex_platform/",
    "/tests/contract/test_capex_semantic_test_suite.py",
    "/tests/contract/test_capex_semantic_codeowners_gates.py",
    "/tests/contract/test_capex_interface_burden_policy_doc.py",
    "/tests/unit/test_capex_interface_burden_policy.py",
}


def _codeowners_entries() -> dict[str, tuple[str, ...]]:
    entries: dict[str, tuple[str, ...]] = {}
    for raw_line in CODEOWNERS_PATH.read_text(encoding="utf-8").splitlines():
        stripped = raw_line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        pattern, *owners = stripped.split()
        entries[pattern] = tuple(owners)
    return entries


def test_capex_semantic_codeowners_entries_use_real_repo_owner() -> None:
    entries = _codeowners_entries()

    for pattern in SEMANTIC_CODEOWNER_PATHS:
        assert entries[pattern] == ("@tylerclark",)
        relative_path = pattern.lstrip("/").rstrip("/")
        assert (REPO_ROOT / relative_path).exists(), pattern


def test_capex_semantic_pytest_marker_and_make_lane_are_exposed() -> None:
    pytest_ini = PYTEST_INI_PATH.read_text(encoding="utf-8")
    makefile = MAKEFILE_PATH.read_text(encoding="utf-8")

    assert "capex_semantic: CAPEX semantic safety" in pytest_ini
    assert "capex-semantic-tests:" in makefile
    assert "PYTHONPATH=src $(PYTEST) -m capex_semantic tests/contract tests/unit" in makefile


def test_main_workflow_exposes_capex_semantic_grouping() -> None:
    workflow = yaml.safe_load(MAIN_WORKFLOW_PATH.read_text(encoding="utf-8"))

    assert "capex-semantic-tests" in workflow["jobs"]
    job = workflow["jobs"]["capex-semantic-tests"]
    assert job["name"] == "capex-semantic-tests"
    workflow_text = MAIN_WORKFLOW_PATH.read_text(encoding="utf-8")
    assert "make PYTHON=python capex-semantic-tests" in workflow_text
