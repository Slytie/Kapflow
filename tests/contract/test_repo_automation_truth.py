from __future__ import annotations

from pathlib import Path

import yaml

from tests.helpers.repo_paths import REPO_ROOT


DEPENDABOT_PATH = REPO_ROOT / ".github" / "dependabot.yml"
SECRET_HYGIENE_WORKFLOW_PATH = REPO_ROOT / ".github" / "workflows" / "secret_hygiene.yml"


def _load_yaml(path: Path) -> dict[str, object]:
    loaded = yaml.safe_load(path.read_text(encoding="utf-8"))
    assert isinstance(loaded, dict), f"{path} must parse as a YAML object"
    return loaded


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

    triggers = loaded.get("on")
    assert isinstance(triggers, dict)
    assert "pull_request" in triggers
    assert "push" in triggers
    assert "schedule" in triggers
    assert "workflow_dispatch" in triggers

    jobs = loaded.get("jobs")
    assert isinstance(jobs, dict)
    workflow_text = SECRET_HYGIENE_WORKFLOW_PATH.read_text(encoding="utf-8")
    assert 'python -m pip install -e ".[api,dev]"' in workflow_text
    assert "python scripts/validate_repo.py --secrets-only" in workflow_text

