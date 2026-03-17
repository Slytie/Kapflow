from __future__ import annotations

import subprocess
import sys

from tests.helpers.repo_paths import REPO_ROOT
from tests.helpers.scenario_catalog import scenario_ids, SCENARIO_CATALOG
from tests.helpers.trace_loader import trace_path


def _run_validator(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "scripts/validate_repo.py", *args],
        cwd=REPO_ROOT,
        check=False,
        capture_output=True,
        text=True,
    )


def test_domain_validation_harness_passes() -> None:
    result = _run_validator(
        "--domain",
        "schema",
        "--domain",
        "governance",
        "--domain",
        "metadata",
        "--domain",
        "release",
        "--domain",
        "secrets",
    )
    assert result.returncode == 0, result.stdout + result.stderr


def test_trace_domain_validation_harness_passes() -> None:
    result = _run_validator("--domain", "traces")
    assert result.returncode == 0, result.stdout + result.stderr


def test_secret_domain_validation_harness_passes() -> None:
    result = _run_validator("--domain", "secrets")
    assert result.returncode == 0, result.stdout + result.stderr


def test_legacy_schema_validation_alias_passes() -> None:
    result = _run_validator("--schemas-only")
    assert result.returncode == 0, result.stdout + result.stderr


def test_legacy_secret_validation_alias_passes() -> None:
    result = _run_validator("--secrets-only")
    assert result.returncode == 0, result.stdout + result.stderr


def test_legacy_trace_validation_alias_passes() -> None:
    result = _run_validator("--traces-only")
    assert result.returncode == 0, result.stdout + result.stderr


def test_legacy_alias_cannot_be_combined_with_domain_selector() -> None:
    result = _run_validator("--schemas-only", "--domain", "schema")
    assert result.returncode != 0
    assert "cannot combine legacy validation mode flags with --domain" in result.stderr


def test_acceptance_scenario_catalog_is_complete() -> None:
    assert scenario_ids() == [
        "AT-SCH-001",
        "AT-SCH-002",
        "AT-SCH-003",
        "AT-SCH-004",
        "AT-SCH-005",
        "AT-SCH-006",
        "AT-SCH-007",
    ]
    for scenario in SCENARIO_CATALOG.values():
        assert trace_path(scenario.trace_name).exists()
