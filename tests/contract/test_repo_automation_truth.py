from __future__ import annotations

import re
from pathlib import Path
import subprocess

import yaml

from tests.helpers.repo_paths import REPO_ROOT


DEPENDABOT_PATH = REPO_ROOT / ".github" / "dependabot.yml"
WORKFLOWS_DIR = REPO_ROOT / ".github" / "workflows"
SECRET_HYGIENE_WORKFLOW_PATH = REPO_ROOT / ".github" / "workflows" / "secret_hygiene.yml"
MAIN_WORKFLOW_PATH = REPO_ROOT / ".github" / "workflows" / "main.yml"
AGENT_API_WORKFLOW_PATH = REPO_ROOT / ".github" / "workflows" / "agent_api.yml"
AGENT_API_LIVE_WORKFLOW_PATH = REPO_ROOT / ".github" / "workflows" / "agent_api_live.yml"
DEPENDENCY_REVIEW_WORKFLOW_PATH = REPO_ROOT / ".github" / "workflows" / "dependency_review.yml"
CODEQL_WORKFLOW_PATH = REPO_ROOT / ".github" / "workflows" / "codeql.yml"
CLOUD_BUILD_PR_PATH = REPO_ROOT / "cloudbuild.pr.yaml"
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


def _assert_all_actions_are_sha_pinned(path: Path) -> None:
    workflow_text = path.read_text(encoding="utf-8")
    for line in workflow_text.splitlines():
        if "uses:" not in line:
            continue
        uses_value = line.split("uses:", 1)[1].strip()
        if uses_value.startswith("./") or uses_value.startswith("docker://"):
            continue
        assert re.fullmatch(r"[^@\s]+@[0-9a-f]{40}(?:\s+#.*)?", uses_value), (
            f"{path} must pin external actions to a full 40-character commit SHA: {uses_value}"
        )


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
    _assert_all_actions_are_sha_pinned(SECRET_HYGIENE_WORKFLOW_PATH)


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
        ("workpage-mutation-smoke", "workpage-mutation-smoke"),
        ("security", "security"),
    }

    runtime_required = jobs.get("runtime-required")
    assert isinstance(runtime_required, dict)
    assert runtime_required.get("name") == "runtime-required"

    frontend = jobs.get("frontend")
    assert isinstance(frontend, dict)
    assert frontend.get("name") == "frontend"

    frontend_workpages_smoke = jobs.get("frontend-workpages-smoke")
    assert isinstance(frontend_workpages_smoke, dict)
    assert frontend_workpages_smoke.get("name") == "frontend / workpages-smoke"

    release_confidence = jobs.get("release-confidence")
    assert isinstance(release_confidence, dict)
    assert (
        release_confidence.get("if")
        == "${{ github.event_name == 'push' || github.event_name == 'workflow_dispatch' }}"
    )

    workflow_text = MAIN_WORKFLOW_PATH.read_text(encoding="utf-8")
    assert "make PYTHON=python ci-runtime-required" in workflow_text
    assert "make PYTHON=python ${{ matrix.make_target }}" in workflow_text
    assert "make frontend-workpages-smoke" in workflow_text
    _assert_all_actions_are_sha_pinned(MAIN_WORKFLOW_PATH)


def test_agent_api_workflow_is_mock_only_and_uses_fast_backend_baseline() -> None:
    assert AGENT_API_WORKFLOW_PATH.exists()
    loaded, _jobs = _load_workflow_jobs(AGENT_API_WORKFLOW_PATH)
    assert loaded["name"] == "agent_api"

    triggers = _load_workflow_triggers(loaded)
    assert "workflow_dispatch" in triggers
    assert "schedule" in triggers

    workflow_text = AGENT_API_WORKFLOW_PATH.read_text(encoding="utf-8")
    assert "make PYTHON=python ci-fast-backend" in workflow_text
    assert "make PYTHON=python ci-backend" not in workflow_text
    assert "OPENAI_API_KEY" not in workflow_text
    assert "tests/integration_openai" not in workflow_text
    _assert_all_actions_are_sha_pinned(AGENT_API_WORKFLOW_PATH)


def test_agent_api_live_workflow_is_manual_and_runs_gated_openai_tests() -> None:
    assert AGENT_API_LIVE_WORKFLOW_PATH.exists()
    loaded, jobs = _load_workflow_jobs(AGENT_API_LIVE_WORKFLOW_PATH)
    assert loaded["name"] == "agent_api_live"

    triggers = _load_workflow_triggers(loaded)
    assert set(triggers) == {"workflow_dispatch"}

    job = jobs.get("openai-live-integration")
    assert isinstance(job, dict)

    workflow_text = AGENT_API_LIVE_WORKFLOW_PATH.read_text(encoding="utf-8")
    assert "make PYTHON=python ci-fast-backend" in workflow_text
    assert "OPENAI_API_KEY" in workflow_text
    assert "ONETRUTH_RUN_OPENAI_E2E=1" in workflow_text
    assert "ONETRUTH_RUN_OPENAI_WEEKLY_AGENT_E2E" in workflow_text
    assert "tests/integration_openai" in workflow_text
    _assert_all_actions_are_sha_pinned(AGENT_API_LIVE_WORKFLOW_PATH)


def test_dependency_review_and_codeql_workflows_exist_with_expected_posture() -> None:
    assert DEPENDENCY_REVIEW_WORKFLOW_PATH.exists()
    dependency_review_loaded, dependency_review_jobs = _load_workflow_jobs(
        DEPENDENCY_REVIEW_WORKFLOW_PATH
    )
    assert dependency_review_loaded["name"] == "dependency_review"
    assert set(_load_workflow_triggers(dependency_review_loaded)) == {"pull_request"}
    assert dependency_review_loaded["permissions"] == {"contents": "read"}
    assert "dependency-review" in dependency_review_jobs
    dependency_review_text = DEPENDENCY_REVIEW_WORKFLOW_PATH.read_text(encoding="utf-8")
    assert "actions/dependency-review-action@" in dependency_review_text
    _assert_all_actions_are_sha_pinned(DEPENDENCY_REVIEW_WORKFLOW_PATH)

    assert CODEQL_WORKFLOW_PATH.exists()
    codeql_loaded, codeql_jobs = _load_workflow_jobs(CODEQL_WORKFLOW_PATH)
    assert codeql_loaded["name"] == "codeql"
    codeql_triggers = _load_workflow_triggers(codeql_loaded)
    assert "push" in codeql_triggers
    assert "pull_request" in codeql_triggers
    assert "schedule" in codeql_triggers
    assert codeql_loaded["permissions"] == {"contents": "read"}
    analyze_job = codeql_jobs.get("analyze")
    assert isinstance(analyze_job, dict)
    assert analyze_job.get("permissions") == {
        "actions": "read",
        "contents": "read",
        "security-events": "write",
    }
    codeql_text = CODEQL_WORKFLOW_PATH.read_text(encoding="utf-8")
    assert "github/codeql-action/init@" in codeql_text
    assert "github/codeql-action/analyze@" in codeql_text
    _assert_all_actions_are_sha_pinned(CODEQL_WORKFLOW_PATH)


def test_all_checked_workflows_exist() -> None:
    workflow_names = {path.name for path in WORKFLOWS_DIR.glob("*.yml")}
    assert {
        "main.yml",
        "secret_hygiene.yml",
        "agent_api.yml",
        "agent_api_live.yml",
        "dependency_review.yml",
        "codeql.yml",
    }.issubset(workflow_names)


def test_cloud_build_pr_validation_skeleton_is_secretless_and_non_deploying() -> None:
    assert CLOUD_BUILD_PR_PATH.exists()
    loaded = _load_yaml(CLOUD_BUILD_PR_PATH)
    assert "availableSecrets" not in loaded

    steps = loaded.get("steps")
    assert isinstance(steps, list)
    step_ids = {str(step.get("id")) for step in steps if isinstance(step, dict)}
    assert {"install-validation-deps", "repo-validation", "schema-validation"}.issubset(step_ids)

    text = CLOUD_BUILD_PR_PATH.read_text(encoding="utf-8")
    assert "secretEnv" not in text
    assert "availableSecrets" not in text
    assert "OPENAI_API_KEY" not in text
    assert "PRODUCTION_DB_URL" not in text
    assert "ONETRUTH_ARTIFACT_ROOT" not in text
    assert "gcloud run" not in text
    assert "kubectl" not in text
    assert "terraform" not in text
    assert "python3 scripts/validate_repo.py" in text
    assert "make schema-validate" in text


def test_no_active_tracked_git_path_contains_node_modules() -> None:
    tracked = _git_lines("ls-files")
    pending_deleted = set(_git_lines("ls-files", "--deleted"))
    active_tracked = [path for path in tracked if path not in pending_deleted]
    offenders = [path for path in active_tracked if "node_modules" in Path(path).parts]
    assert offenders == []


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
    assert "capex-progress-check:" in makefile_text
    assert (
        "$(PYTHON) scripts/validate_capex_epic_progress_data.py frontend/src/data/capexEpicProgressData.json"
        in makefile_text
    )
    assert "capex-semantic-tests: capex-progress-check" in makefile_text
    assert "frontend-workpages-smoke:" in makefile_text
    assert "cd frontend && npm run test:workpages" in makefile_text
    assert "ci-fast-backend: backend-lint contract unit workpage-mutation-smoke security" in makefile_text
    assert (
        "ci-runtime-required: replay acceptance runtime frontend-snapshots-check"
        in makefile_text
    )
    assert "ci-backend: ci-fast-backend ci-runtime-required" in makefile_text


def _git_lines(*args: str) -> list[str]:
    result = subprocess.run(
        ["git", *args],
        cwd=REPO_ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    return [line for line in result.stdout.splitlines() if line]
