from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys
import zipfile

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT_PATH = REPO_ROOT / "scripts" / "export_clean_source_bundle.py"


def test_clean_source_bundle_exports_source_and_excludes_clutter(tmp_path: Path) -> None:
    repo_root = _build_fixture_repo(tmp_path / "fixture_repo")
    bundle_path = repo_root / ".tmp" / "clean-source-bundle.zip"

    payload = _run_export(repo_root, bundle_path)
    archive_root = str(payload["archive_root"])

    assert payload["status"] == "ok"
    assert payload["tracked_only"] is False
    assert bundle_path.exists()

    with zipfile.ZipFile(bundle_path, "r") as archive:
        names = set(archive.namelist())

    assert f"{archive_root}/README.md" in names
    assert f"{archive_root}/src/app.py" in names
    assert f"{archive_root}/docs/notes.md" in names
    assert f"{archive_root}/.env.example" in names
    assert f"{archive_root}/codex/tasks/TASK-9999.md" in names

    assert f"{archive_root}/.env" not in names
    assert f"{archive_root}/.env.local" not in names
    assert f"{archive_root}/.venv/bin/python" not in names
    assert f"{archive_root}/.tmp/runtime.json" not in names
    assert f"{archive_root}/.onetruth_artifacts/run-123/artifact.json" not in names
    assert f"{archive_root}/artifacts/run/output.json" not in names
    assert f"{archive_root}/frontend/dist/app.js" not in names
    assert f"{archive_root}/frontend/node_modules/pkg/index.js" not in names
    assert f"{archive_root}/frontend/.vite/deps.js" not in names
    assert f"{archive_root}/frontend/coverage/index.html" not in names
    assert f"{archive_root}/.pytest_cache/v/cache/nodeids" not in names
    assert f"{archive_root}/.idea/workspace.xml" not in names
    assert f"{archive_root}/local.db" not in names
    assert f"{archive_root}/runtime.sqlite3" not in names
    assert f"{archive_root}/.git/config" not in names
    assert f"{archive_root}/.tmp/clean-source-bundle.zip" not in names


def test_clean_source_bundle_tracked_only_skips_untracked_source(tmp_path: Path) -> None:
    repo_root = _build_fixture_repo(tmp_path / "fixture_repo")
    bundle_path = tmp_path / "tracked-only.zip"

    payload = _run_export(repo_root, bundle_path, tracked_only=True)
    archive_root = str(payload["archive_root"])

    with zipfile.ZipFile(bundle_path, "r") as archive:
        names = set(archive.namelist())

    assert payload["tracked_only"] is True
    assert f"{archive_root}/README.md" in names
    assert f"{archive_root}/codex/tasks/TASK-9999.md" not in names


def _build_fixture_repo(repo_root: Path) -> Path:
    repo_root.mkdir(parents=True, exist_ok=True)
    _write_text(
        repo_root / ".gitignore",
        "\n".join(
            [
                ".tmp/",
                ".venv/",
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
    _write_text(repo_root / ".env.example", "EXAMPLE=1\n")
    _write_text(repo_root / "codex" / "tasks" / "TASK-9999.md", "untracked source file\n")

    _write_text(repo_root / ".env", "SECRET=1\n")
    _write_text(repo_root / ".env.local", "LOCAL=1\n")
    _write_text(repo_root / ".venv" / "bin" / "python", "python\n")
    _write_text(repo_root / ".tmp" / "runtime.json", "{}\n")
    _write_text(repo_root / ".onetruth_artifacts" / "run-123" / "artifact.json", "{}\n")
    _write_text(repo_root / "artifacts" / "run" / "output.json", "{}\n")
    _write_text(repo_root / "frontend" / "dist" / "app.js", "console.log('dist')\n")
    _write_text(
        repo_root / "frontend" / "node_modules" / "pkg" / "index.js",
        "module.exports = {};\n",
    )
    _write_text(repo_root / "frontend" / ".vite" / "deps.js", "export {};\n")
    _write_text(repo_root / "frontend" / "coverage" / "index.html", "<html></html>\n")
    _write_text(repo_root / ".pytest_cache" / "v" / "cache" / "nodeids", "[]\n")
    _write_text(repo_root / ".idea" / "workspace.xml", "<workspace />\n")
    _write_text(repo_root / "local.db", "sqlite bytes\n")
    _write_text(repo_root / "runtime.sqlite3", "sqlite bytes\n")

    _git(repo_root, "init")
    _git(repo_root, "add", ".gitignore", "README.md", "src/app.py", "docs/notes.md", ".env.example")
    return repo_root


def _run_export(repo_root: Path, bundle_path: Path, *, tracked_only: bool = False) -> dict[str, object]:
    args = [
        sys.executable,
        str(SCRIPT_PATH),
        "--repo-root",
        str(repo_root),
        "--output",
        str(bundle_path),
    ]
    if tracked_only:
        args.append("--tracked-only")
    result = subprocess.run(
        args,
        cwd=REPO_ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    if result.returncode != 0:
        raise AssertionError(
            "clean source bundle export failed\n"
            f"STDOUT:\n{result.stdout}\n"
            f"STDERR:\n{result.stderr}"
        )
    return json.loads(result.stdout)


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
