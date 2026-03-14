from __future__ import annotations

import subprocess

from tests.helpers.repo_paths import REPO_ROOT


PYPROJECT_PATH = REPO_ROOT / "pyproject.toml"
REQUIREMENTS_PATH = REPO_ROOT / "requirements.txt"
EDITORCONFIG_PATH = REPO_ROOT / ".editorconfig"
FRONTEND_PACKAGE_PATH = REPO_ROOT / "frontend" / "package.json"
MAIN_WORKFLOW_PATH = REPO_ROOT / ".github" / "workflows" / "main.yml"
AGENT_API_WORKFLOW_PATH = REPO_ROOT / ".github" / "workflows" / "agent_api.yml"

EXPECTED_EDITORCONFIG = """root = true

[*]
charset = utf-8
end_of_line = lf
insert_final_newline = true
trim_trailing_whitespace = true
indent_style = space
indent_size = 2

[*.md]
trim_trailing_whitespace = false

[*.py]
indent_size = 4

[Makefile]
indent_style = tab
"""


def test_pyproject_requires_validated_python_311_only() -> None:
    text = PYPROJECT_PATH.read_text(encoding="utf-8")
    assert 'requires-python = ">=3.11,<3.12"' in text


def test_requirements_is_only_a_pyproject_compatibility_shim() -> None:
    text = REQUIREMENTS_PATH.read_text(encoding="utf-8")
    non_comment_lines = [line.strip() for line in text.splitlines() if line.strip() and not line.lstrip().startswith("#")]
    assert non_comment_lines == ["-e .[api,dev]"]
    assert "pyproject.toml" in text


def test_editorconfig_matches_repo_defaults() -> None:
    assert EDITORCONFIG_PATH.exists()
    assert EDITORCONFIG_PATH.read_text(encoding="utf-8") == EXPECTED_EDITORCONFIG


def test_frontend_package_declares_node_20_engine() -> None:
    text = FRONTEND_PACKAGE_PATH.read_text(encoding="utf-8")
    assert '"engines"' in text
    assert '"node": ">=20 <21"' in text


def test_ci_workflows_install_from_editable_pyproject_extras_only() -> None:
    for path in (MAIN_WORKFLOW_PATH, AGENT_API_WORKFLOW_PATH):
        text = path.read_text(encoding="utf-8")
        assert 'python -m pip install -e ".[api,dev]"' in text
        assert "pip install -r requirements.txt" not in text


def test_git_tracks_no_egg_info_build_artifacts() -> None:
    result = subprocess.run(
        ["git", "ls-files", "--", "*.egg-info/*"],
        cwd=REPO_ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == ""
