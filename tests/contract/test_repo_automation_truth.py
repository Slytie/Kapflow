from __future__ import annotations

from pathlib import Path

import yaml

from tests.helpers.repo_paths import REPO_ROOT


DEPENDABOT_PATH = REPO_ROOT / ".github" / "dependabot.yml"
SECRET_HYGIENE_WORKFLOW_PATH = REPO_ROOT / ".github" / "workflows" / "secret_hygiene.yml"
MAIN_WORKFLOW_PATH = REPO_ROOT / ".github" / "workflows" / "main.yml"
AGENT_API_WORKFLOW_PATH = REPO_ROOT / ".github" / "workflows" / "agent_api.yml"
MAKEFILE_PATH = REPO_ROOT / "Makefile"


def _load_yaml(path: Path) -> dict[str, object]:
    loaded = yaml.safe_load(path.read_text(encoding="utf-8"))
    assert isinstance(loaded, dict), f"{path} must parse as a YAML object"
    return loaded


def _load_workflow_jobs(path: Path) -> tuple[dict[str, object], dict[str, object]]:
    loaded = _load_yaml(path)
    jobs = loaded.get("jobs")
    assert isinstance(jobs, dict), f"{path} must define workflow jobs"
    return loaded, jobs


def _load_workflow_triggers(loaded: dict[str, object]) -> dict[str, object]:
    triggers = loaded.get("on")
    if triggers is None:
        triggers = loaded.get(True)
    assert isinstance(triggers, dict), "workflow must define triggers under 'on'"
    return triggers


def test_dependabot_covers_repo_package_managers() -> None:
    assert DEPENDABOT_PATH.exists()
    loaded = _load_yaml(DEPENDABOT_PATH)
    assert loaded["version"] == 2
    updates = loaded.get("updates")
    assert isinstance(updates, list)
    update_pairs = {
        (str(entry.get("package-ecosystem")), str(entry.get("directory")))
        for entry in updates
        if isinstance(entry, dict)
    }
    assert ("pip", "/") in update_pairs
    assert ("npm", "/frontend") in update_pairs
    assert ("github-actions", "/") in update_pairs


def test_secret_hygiene_workflow_runs_validator_secret_mode() -> None:
    assert SECRET_HYGIENE_WORKFLOW_PATH.exists()
    loaded = _load_yaml(SECRET_HYGIENE_WORKFLOW_PATH)
    assert loaded["name"] == "secret_hygiene"

    triggers = _load_workflow_triggers(loaded)
    assert "pull_request" in triggers
    assert "push" in triggers
    assert "schedule" in triggers
    assert "workflow_dispatch" in triggers

    jobs = loaded.get("jobs")
    assert isinstance(jobs, dict)
    workflow_text = SECRET_HYGIENE_WORKFLOW_PATH.read_text(encoding="utf-8")
    assert 'python -m pip install -e ".[api,dev]"' in workflow_text
    assert "python scripts/validate_repo.py --domain secrets" in workflow_text


def test_main_workflow_splits_fast_required_lanes_and_runtime_required() -> None:
    assert MAIN_WORKFLOW_PATH.exists()
    loaded, jobs = _load_workflow_jobs(MAIN_WORKFLOW_PATH)
    assert loaded["name"] == "main"

    triggers = _load_workflow_triggers(loaded)
    assert "push" in triggers
    assert "pull_request" in triggers
    assert "workflow_dispatch" in triggers

    assert "backend" not in jobs
    required_fast = jobs.get("required-fast")
    assert isinstance(required_fast, dict)
    assert required_fast.get("name") == "required-fast / ${{ matrix.check }}"

    strategy = required_fast.get("strategy")
    assert isinstance(strategy, dict)
    matrix = strategy.get("matrix")
    assert isinstance(matrix, dict)
    include = matrix.get("include")
    assert isinstance(include, list)
    include_pairs = {
        (str(entry.get("check")), str(entry.get("make_target")))
        for entry in include
        if isinstance(entry, dict)
    }
    assert include_pairs == {
        ("lint", "backend-lint"),
        ("contract", "contract"),
        ("unit", "unit"),
        ("security", "security"),
    }

    runtime_required = jobs.get("runtime-required")
    assert isinstance(runtime_required, dict)
    assert runtime_required.get("name") == "runtime-required"

    frontend = jobs.get("frontend")
    assert isinstance(frontend, dict)
    assert frontend.get("name") == "frontend"

    release_confidence = jobs.get("release-confidence")
    assert isinstance(release_confidence, dict)
    assert (
        release_confidence.get("if")
        == "${{ github.event_name == 'push' || github.event_name == 'workflow_dispatch' }}"
    )

    workflow_text = MAIN_WORKFLOW_PATH.read_text(encoding="utf-8")
    assert "make PYTHON=python ci-runtime-required" in workflow_text
    assert "make PYTHON=python ${{ matrix.make_target }}" in workflow_text


def test_agent_api_workflow_uses_fast_backend_baseline() -> None:
    assert AGENT_API_WORKFLOW_PATH.exists()
    loaded, _jobs = _load_workflow_jobs(AGENT_API_WORKFLOW_PATH)
    assert loaded["name"] == "agent_api"

    triggers = _load_workflow_triggers(loaded)
    assert "workflow_dispatch" in triggers
    assert "schedule" in triggers

    workflow_text = AGENT_API_WORKFLOW_PATH.read_text(encoding="utf-8")
    assert "make PYTHON=python ci-fast-backend" in workflow_text
    assert "make PYTHON=python ci-backend" not in workflow_text


def test_makefile_exposes_fast_and_runtime_ci_slices() -> None:
    makefile_text = MAKEFILE_PATH.read_text(encoding="utf-8")
    assert "assurance-fast:" in makefile_text
    assert (
        "$(VALIDATOR) --domain schema --domain governance --domain metadata --domain release --domain secrets"
        in makefile_text
    )
    assert "schema-validate: assurance-fast" in makefile_text
    assert "$(VALIDATOR) --domain traces" in makefile_text
    assert "backend-lint: assurance-fast python-lint" in makefile_text
    assert "ci-fast-backend: backend-lint contract unit security" in makefile_text
    assert (
        "ci-runtime-required: replay acceptance runtime frontend-snapshots-check"
        in makefile_text
    )
    assert "ci-backend: ci-fast-backend ci-runtime-required" in makefile_text
