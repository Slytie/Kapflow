from __future__ import annotations

import hashlib
import json
from pathlib import Path
import subprocess
import sys
import zipfile

from scripts.release_bundle_provenance import RELEASE_PROVENANCE_PATH


REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT_PATH = REPO_ROOT / "scripts" / "export_clean_source_bundle.py"


def test_release_source_bundle_exports_clean_tracked_commit_snapshot(tmp_path: Path) -> None:
    repo_root = _build_committed_fixture_repo(tmp_path / "fixture_repo")
    bundle_path = tmp_path / "release-source-bundle.zip"

    payload = _run_export(repo_root, bundle_path, bundle_kind="release_source_bundle")
    archive_root = str(payload["archive_root"])
    manifest = _read_archive_json(bundle_path, f"{archive_root}/bundle_manifest.json")
    provenance = _read_archive_json(bundle_path, f"{archive_root}/{RELEASE_PROVENANCE_PATH}")
    head_commit = _git_stdout(repo_root, "rev-parse", "HEAD")

    assert payload["status"] == "ok"
    assert payload["bundle_kind"] == "release_source_bundle"
    assert payload["distribution_class"] == "operator_release"
    assert payload["provenance_path"] == RELEASE_PROVENANCE_PATH
    assert payload["tracked_only"] is True
    assert payload["git_commit"] == head_commit
    assert payload["tracked_worktree_clean"] is True

    with zipfile.ZipFile(bundle_path, "r") as archive:
        names = set(archive.namelist())

    assert f"{archive_root}/bundle_manifest.json" in names
    assert f"{archive_root}/{RELEASE_PROVENANCE_PATH}" in names
    assert f"{archive_root}/README.md" in names
    assert f"{archive_root}/src/app.py" in names
    assert f"{archive_root}/docs/notes.md" in names
    assert f"{archive_root}/pyproject.toml" in names
    assert f"{archive_root}/.env.example" in names
    assert f"{archive_root}/node_modules/.vite/results.json" not in names
    assert f"{archive_root}/build/reviews/node_modules/pkg/index.js" not in names
    assert f"{archive_root}/codex/tasks/TASK-9999.md" not in names
    assert manifest == {
        "manifest_version": 1,
        "bundle_kind": "release_source_bundle",
        "archive_root": archive_root,
        "distribution_class": "operator_release",
        "provenance_path": RELEASE_PROVENANCE_PATH,
        "tracked_only": True,
        "git_commit": head_commit,
        "tracked_worktree_clean": True,
    }
    expected_file_paths = [
        ".env.example",
        ".gitignore",
        "README.md",
        "docs/notes.md",
        "pyproject.toml",
        "src/app.py",
    ]
    assert provenance == {
        "provenance_version": 1,
        "bundle_kind": "release_source_bundle",
        "archive_root": archive_root,
        "git_commit": head_commit,
        "tracked_only": True,
        "source_manifests": [_expected_file_record(repo_root, "pyproject.toml")],
        "files": [_expected_file_record(repo_root, path) for path in expected_file_paths],
    }


def test_release_source_bundle_requires_clean_tracked_worktree(tmp_path: Path) -> None:
    repo_root = _build_committed_fixture_repo(tmp_path / "fixture_repo")
    bundle_path = tmp_path / "dirty-release-bundle.zip"
    _write_text(repo_root / "README.md", "# changed after commit\n")

    result = _run_export_raw(repo_root, bundle_path, bundle_kind="release_source_bundle")

    assert result.returncode != 0
    assert "release_source_bundle requires a clean tracked worktree" in result.stderr


def _build_committed_fixture_repo(repo_root: Path) -> Path:
    repo_root.mkdir(parents=True, exist_ok=True)
    _write_text(
        repo_root / ".gitignore",
        "\n".join(
            [
                ".tmp/",
                ".venv/",
                "node_modules/",
                "frontend/node_modules/",
                "frontend/dist/",
                "frontend/.vite/",
                "frontend/coverage/",
                "artifacts/",
                ".pytest_cache/",
                ".idea/",
                ".env*",
                "!.env.example",
                "!.env.sample",
            ]
        )
        + "\n",
    )
    _write_text(repo_root / "README.md", "# Fixture repo\n")
    _write_text(repo_root / "src" / "app.py", "print('hello')\n")
    _write_text(repo_root / "docs" / "notes.md", "tracked note\n")
    _write_text(repo_root / "pyproject.toml", "[project]\nname = 'fixture-repo'\nversion = '0.1.0'\n")
    _write_text(repo_root / ".env.example", "EXAMPLE=1\n")
    _write_text(repo_root / "codex" / "tasks" / "TASK-9999.md", "untracked source file\n")
    _write_text(repo_root / "node_modules" / ".vite" / "results.json", "{}\n")
    _write_text(
        repo_root / "build" / "reviews" / "node_modules" / "pkg" / "index.js",
        "module.exports = {};\n",
    )

    _git(repo_root, "init")
    _git(repo_root, "config", "user.email", "test@example.com")
    _git(repo_root, "config", "user.name", "Fixture User")
    _git(
        repo_root,
        "add",
        ".gitignore",
        "README.md",
        "src/app.py",
        "docs/notes.md",
        "pyproject.toml",
        ".env.example",
    )
    _git(
        repo_root,
        "add",
        "-f",
        "node_modules/.vite/results.json",
        "build/reviews/node_modules/pkg/index.js",
    )
    _git(repo_root, "commit", "-m", "fixture commit")
    return repo_root


def _run_export(repo_root: Path, bundle_path: Path, *, bundle_kind: str) -> dict[str, object]:
    result = _run_export_raw(repo_root, bundle_path, bundle_kind=bundle_kind)
    if result.returncode != 0:
        raise AssertionError(
            "source bundle export failed\n"
            f"STDOUT:\n{result.stdout}\n"
            f"STDERR:\n{result.stderr}"
        )
    return json.loads(result.stdout)


def _run_export_raw(repo_root: Path, bundle_path: Path, *, bundle_kind: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [
            sys.executable,
            str(SCRIPT_PATH),
            "--repo-root",
            str(repo_root),
            "--output",
            str(bundle_path),
            "--bundle-kind",
            bundle_kind,
        ],
        cwd=REPO_ROOT,
        text=True,
        capture_output=True,
        check=False,
    )


def _read_archive_json(bundle_path: Path, archive_name: str) -> dict[str, object]:
    with zipfile.ZipFile(bundle_path, "r") as archive:
        return json.loads(archive.read(archive_name).decode("utf-8"))


def _expected_file_record(repo_root: Path, relative_path: str) -> dict[str, object]:
    absolute_path = repo_root / relative_path
    content = absolute_path.read_bytes()
    return {
        "path": relative_path,
        "sha256": hashlib.sha256(content).hexdigest(),
        "size_bytes": len(content),
    }


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


def _git_stdout(repo_root: Path, *args: str) -> str:
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
    return result.stdout.strip()


def _write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
