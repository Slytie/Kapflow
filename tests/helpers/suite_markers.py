from __future__ import annotations

from fnmatch import fnmatchcase
from pathlib import Path


LOGISTICS_REGRESSION_TEST_GLOBS: tuple[str, ...] = (
    "tests/contract/test_logistics_*.py",
    "tests/integration_openai/test_weekly_stage04_openai_real_e2e.py",
    "tests/runtime/test_logistics_*.py",
    "tests/runtime/test_realistic_schedule_planning_pilot.py",
    "tests/runtime/test_schedule_control_*.py",
    "tests/runtime/test_weekly_stage04_*.py",
    "tests/runtime/api/test_binary_download_transport.py",
    "tests/runtime/api/test_dispatch_reporting_*.py",
    "tests/runtime/api/test_human_task_subgraph_contract.py",
    "tests/runtime/api/test_logistics_*.py",
    "tests/runtime/api/test_operator_home_endpoint.py",
    "tests/runtime/api/test_weekly_publish_loop_api.py",
    "tests/runtime/api/test_weekly_stage04_*.py",
    "tests/runtime/api/test_workpage_mutation_smoke.py",
    "tests/runtime/api/test_workpages_*.py",
    "tests/runtime/api/test_workspace_workpage_actions.py",
    "tests/runtime/contracts/test_logistics_*.py",
    "tests/runtime/scenarios/test_logistics_*.py",
    "tests/runtime/scenarios/test_weekly_*.py",
    "tests/security/isolation/test_logistics_*.py",
    "tests/unit/test_dispatch_reporting_*.py",
    "tests/unit/test_driver_preferences_*.py",
    "tests/unit/test_logistics_*.py",
    "tests/unit/test_route_demand_*.py",
    "tests/unit/test_schedule_control_*.py",
    "tests/unit/test_schedule_draft_workbook.py",
    "tests/unit/test_template_registry.py",
    "tests/unit/test_weekly_stage04_*.py",
    "tests/unit/test_workpages_*.py",
)

LOGISTICS_FIXTURE_REFERENCE_MARKERS: tuple[str, ...] = (
    "fixtures/logistics/",
    "fixtures/scenarios/logistics/",
    "fixtures/workflows/dispatch_reporting/",
)


def normalize_repo_test_path(path: Path | str, *, repo_root: Path) -> str:
    candidate = Path(path)
    if candidate.is_absolute():
        candidate = candidate.resolve().relative_to(repo_root.resolve())
    return candidate.as_posix()


def is_logistics_regression_test_path(path: Path | str, *, repo_root: Path) -> bool:
    normalized = normalize_repo_test_path(path, repo_root=repo_root)
    return any(
        fnmatchcase(normalized, pattern)
        for pattern in LOGISTICS_REGRESSION_TEST_GLOBS
    )
