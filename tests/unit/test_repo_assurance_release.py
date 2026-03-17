from __future__ import annotations

from pathlib import Path
import subprocess

from scripts.repo_assurance.release import get_release_validation_unavailable_reason


def test_release_preflight_reports_non_git_directory(tmp_path: Path) -> None:
    repo_root = tmp_path / "non_git_repo"
    repo_root.mkdir()

    reason = get_release_validation_unavailable_reason(repo_root)

    assert reason == "live git checkout with resolvable git toplevel is required"


def test_release_preflight_reports_missing_committed_head(tmp_path: Path) -> None:
    repo_root = tmp_path / "fixture_repo"
    repo_root.mkdir()
    _git(repo_root, "init")
    _git(repo_root, "config", "user.email", "test@example.com")
    _git(repo_root, "config", "user.name", "Fixture User")
    _write_text(repo_root / "README.md", "# Fixture repo\n")
    _git(repo_root, "add", "README.md")

    reason = get_release_validation_unavailable_reason(repo_root)

    assert reason == "committed HEAD is required for release validation"


def _git(repo_root: Path, *args: str) -> None:
    result = subprocess.run(
        ["git", *args],
        cwd=repo_root,
        text=True,
        capture_output=True,
        check=False,
    )
    if result.returncode != 0:
        raise AssertionError(
            "git command failed\n"
            f"CMD: git {' '.join(args)}\n"
            f"STDOUT:\n{result.stdout}\n"
            f"STDERR:\n{result.stderr}"
        )


def _write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
