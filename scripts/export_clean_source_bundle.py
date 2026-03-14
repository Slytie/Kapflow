#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path, PurePosixPath
import subprocess
import sys
import zipfile

from release_bundle_provenance import (
    RELEASE_PROVENANCE_PATH,
    build_release_provenance,
)

HANDOFF_SOURCE_BUNDLE = "handoff_source_bundle"
RELEASE_SOURCE_BUNDLE = "release_source_bundle"
BUNDLE_MANIFEST_VERSION = 1
DEFAULT_ARCHIVE_ROOT_SUFFIX_BY_KIND = {
    HANDOFF_SOURCE_BUNDLE: "-clean-source-bundle",
    RELEASE_SOURCE_BUNDLE: "-release-source-bundle",
}
DEFAULT_EXCLUDED_DIR_NAMES = frozenset(
    {
        ".git",
        ".venv",
        "venv",
        ".tmp",
        ".pytest_cache",
        ".idea",
        ".mypy_cache",
        ".ruff_cache",
    }
)
DEFAULT_EXCLUDED_ROOT_PREFIXES = (
    "artifacts/",
    ".onetruth_artifacts/",
    "frontend/node_modules/",
    "frontend/dist/",
    "frontend/.vite/",
    "frontend/coverage/",
)
DEFAULT_EXCLUDED_FILE_PATTERNS = (
    ".DS_Store",
    ".codex.env",
    ".env",
    ".env.*",
    "*.pyc",
    "*.pyo",
    "*.log",
    "*.db",
    "*.db-*",
    "*.sqlite",
    "*.sqlite-*",
    "*.sqlite3",
    "*.sqlite3-*",
)
DEFAULT_ALLOWED_FILE_NAMES = frozenset({".env.example", ".env.sample"})
DISTRIBUTION_CLASS_BY_KIND = {
    HANDOFF_SOURCE_BUNDLE: "internal_handoff",
    RELEASE_SOURCE_BUNDLE: "operator_release",
}


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Export a clean source bundle ZIP from the current working tree while "
            "excluding workstation/runtime clutter."
        )
    )
    parser.add_argument(
        "--repo-root",
        default=str(Path(__file__).resolve().parents[1]),
        help="Repository root to export. Defaults to this script's parent repo.",
    )
    parser.add_argument(
        "--output",
        required=True,
        help="Output ZIP path.",
    )
    parser.add_argument(
        "--bundle-kind",
        default=HANDOFF_SOURCE_BUNDLE,
        choices=[HANDOFF_SOURCE_BUNDLE, RELEASE_SOURCE_BUNDLE],
        help=(
            "Bundle contract to export. Defaults to handoff_source_bundle; "
            "release_source_bundle requires a clean tracked worktree."
        ),
    )
    parser.add_argument(
        "--archive-root",
        default=None,
        help=(
            "Top-level directory name inside the ZIP. Defaults to a bundle-kind-specific "
            "name such as <repo>-clean-source-bundle or <repo>-release-source-bundle."
        ),
    )
    parser.add_argument(
        "--tracked-only",
        action="store_true",
        help="Export only git-tracked files and skip untracked non-ignored working-tree source files.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    repo_root = _resolve_repo_root(Path(args.repo_root).expanduser())
    output_path = Path(args.output).expanduser().resolve()
    bundle_kind = str(args.bundle_kind)
    tracked_only = bool(args.tracked_only or bundle_kind == RELEASE_SOURCE_BUNDLE)
    git_commit = _resolve_git_commit(repo_root)
    tracked_worktree_clean = _tracked_worktree_is_clean(repo_root)
    if bundle_kind == RELEASE_SOURCE_BUNDLE:
        if git_commit is None:
            raise SystemExit("release_source_bundle requires a committed HEAD")
        if not tracked_worktree_clean:
            raise SystemExit("release_source_bundle requires a clean tracked worktree")
    archive_root = _normalize_archive_root(
        args.archive_root
        or f"{repo_root.name}{DEFAULT_ARCHIVE_ROOT_SUFFIX_BY_KIND[bundle_kind]}"
    )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    if output_path.exists():
        if output_path.is_dir():
            raise SystemExit(f"output path is a directory: {output_path}")
        output_path.unlink()

    output_rel_path = _relative_to_repo(output_path, repo_root)
    candidates = _list_git_candidates(repo_root, tracked_only=tracked_only)
    files_to_write: list[Path] = []
    skipped_missing_paths: list[str] = []

    for relative_path in candidates:
        if output_rel_path is not None and relative_path == output_rel_path:
            continue
        if _should_exclude(relative_path):
            continue
        absolute_path = repo_root / relative_path
        if not absolute_path.exists():
            skipped_missing_paths.append(relative_path)
            continue
        if absolute_path.is_dir():
            continue
        files_to_write.append(absolute_path)

    bundle_manifest = {
        "manifest_version": BUNDLE_MANIFEST_VERSION,
        "bundle_kind": bundle_kind,
        "archive_root": archive_root,
        "distribution_class": DISTRIBUTION_CLASS_BY_KIND[bundle_kind],
        "tracked_only": tracked_only,
        "git_commit": git_commit,
        "tracked_worktree_clean": tracked_worktree_clean,
    }
    release_provenance: dict[str, object] | None = None
    if bundle_kind == RELEASE_SOURCE_BUNDLE:
        release_provenance = build_release_provenance(
            repo_root=repo_root,
            archive_root=archive_root,
            bundle_kind=bundle_kind,
            git_commit=str(git_commit),
            tracked_only=tracked_only,
            files_to_write=files_to_write,
        )
        bundle_manifest["provenance_path"] = RELEASE_PROVENANCE_PATH

    with zipfile.ZipFile(output_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for absolute_path in files_to_write:
            relative_path = absolute_path.relative_to(repo_root).as_posix()
            archive.write(absolute_path, arcname=f"{archive_root}/{relative_path}")
        archive.writestr(
            f"{archive_root}/bundle_manifest.json",
            json.dumps(bundle_manifest, indent=2, sort_keys=True) + "\n",
        )
        if release_provenance is not None:
            archive.writestr(
                f"{archive_root}/{RELEASE_PROVENANCE_PATH}",
                json.dumps(release_provenance, indent=2, sort_keys=True) + "\n",
            )

    payload = {
        "status": "ok",
        "command": "clean-source-bundle.export",
        "bundle_kind": bundle_kind,
        "repo_root": str(repo_root),
        "output": str(output_path),
        "archive_root": archive_root,
        "distribution_class": DISTRIBUTION_CLASS_BY_KIND[bundle_kind],
        "tracked_only": tracked_only,
        "git_commit": git_commit,
        "tracked_worktree_clean": tracked_worktree_clean,
        "file_count": len(files_to_write) + 1 + (1 if release_provenance is not None else 0),
        "skipped_missing_paths": skipped_missing_paths,
    }
    if release_provenance is not None:
        payload["provenance_path"] = RELEASE_PROVENANCE_PATH
    sys.stdout.write(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    return 0


def _resolve_repo_root(repo_root: Path) -> Path:
    resolved_root = repo_root.resolve()
    result = subprocess.run(
        ["git", "rev-parse", "--show-toplevel"],
        cwd=resolved_root,
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        raise SystemExit(
            f"failed to resolve git repository root from {resolved_root}: {result.stderr.strip()}"
        )
    git_root = Path(result.stdout.strip()).resolve()
    if git_root != resolved_root:
        raise SystemExit(
            f"--repo-root must point at the git toplevel ({git_root}), got {resolved_root}"
        )
    return git_root


def _normalize_archive_root(raw_value: str) -> str:
    archive_root = raw_value.strip().strip("/")
    if not archive_root:
        raise SystemExit("archive root must not be empty")
    return archive_root


def _resolve_git_commit(repo_root: Path) -> str | None:
    result = subprocess.run(
        ["git", "rev-parse", "--verify", "HEAD"],
        cwd=repo_root,
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        return None
    commit = result.stdout.strip()
    if not commit:
        return None
    return commit


def _tracked_worktree_is_clean(repo_root: Path) -> bool:
    result = subprocess.run(
        ["git", "status", "--porcelain", "--untracked-files=no"],
        cwd=repo_root,
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        stderr = result.stderr.strip()
        raise SystemExit(f"failed to inspect git worktree status: {stderr}")
    return result.stdout.strip() == ""


def _list_git_candidates(repo_root: Path, *, tracked_only: bool) -> list[str]:
    command = ["git", "ls-files", "-z", "--cached"]
    if not tracked_only:
        command.extend(["--others", "--exclude-standard"])
    result = subprocess.run(
        command,
        cwd=repo_root,
        capture_output=True,
        check=False,
    )
    if result.returncode != 0:
        stderr = result.stderr.decode("utf-8", errors="replace").strip()
        raise SystemExit(f"failed to enumerate repo files: {stderr}")

    candidates: list[str] = []
    seen: set[str] = set()
    for raw_path in result.stdout.split(b"\0"):
        if not raw_path:
            continue
        relative_path = Path(raw_path.decode("utf-8")).as_posix()
        if relative_path in seen:
            continue
        seen.add(relative_path)
        candidates.append(relative_path)
    return candidates


def _relative_to_repo(path: Path, repo_root: Path) -> str | None:
    try:
        return path.relative_to(repo_root).as_posix()
    except ValueError:
        return None


def _should_exclude(relative_path: str) -> bool:
    posix_path = PurePosixPath(relative_path)
    file_name = posix_path.name

    if file_name in DEFAULT_ALLOWED_FILE_NAMES:
        return False
    if any(part in DEFAULT_EXCLUDED_DIR_NAMES for part in posix_path.parts):
        return True
    if any(
        relative_path == prefix[:-1] or relative_path.startswith(prefix)
        for prefix in DEFAULT_EXCLUDED_ROOT_PREFIXES
    ):
        return True
    if file_name == ".env" or file_name.startswith(".env."):
        return True
    return any(posix_path.match(pattern) for pattern in DEFAULT_EXCLUDED_FILE_PATTERNS)


if __name__ == "__main__":
    raise SystemExit(main())
