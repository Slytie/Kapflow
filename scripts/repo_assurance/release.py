from __future__ import annotations

import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import zipfile

from scripts.release_bundle_provenance import (
    RELEASE_PROVENANCE_PATH,
    SOURCE_MANIFEST_CANDIDATES,
)
from scripts.repo_assurance.core import (
    AssuranceState,
    RELEASE_DISTRIBUTION_CLASS,
    RELEASE_SOURCE_BUNDLE,
    ROOT,
    source_bundle_path_is_excluded,
)


def run_release_domain(state: AssuranceState) -> None:
    validate_release_source_bundle_export_payload(state)


def get_release_validation_unavailable_reason(repo_root: Path) -> str | None:
    if shutil.which("git") is None:
        return "live git checkout with resolvable git toplevel is required"

    top_level = subprocess.run(
        ["git", "rev-parse", "--show-toplevel"],
        cwd=repo_root,
        capture_output=True,
        text=True,
        check=False,
    )
    if top_level.returncode != 0:
        return "live git checkout with resolvable git toplevel is required"
    raw_git_root = top_level.stdout.strip()
    if not raw_git_root:
        return "live git checkout with resolvable git toplevel is required"

    git_root = Path(raw_git_root).resolve()
    resolved_repo_root = repo_root.resolve()
    if git_root != resolved_repo_root:
        return f"live git checkout resolves to {git_root}, expected {resolved_repo_root}"

    head = subprocess.run(
        ["git", "rev-parse", "--verify", "HEAD"],
        cwd=repo_root,
        capture_output=True,
        text=True,
        check=False,
    )
    if head.returncode != 0 or not head.stdout.strip():
        return "committed HEAD is required for release validation"
    return None


def validate_release_source_bundle_export_payload(state: AssuranceState) -> None:
    collector = state.collector
    unavailable_reason = get_release_validation_unavailable_reason(ROOT)
    if unavailable_reason is not None:
        collector.fail(f"release validation unavailable: {unavailable_reason}")
        return

    script_path = ROOT / "scripts" / "export_clean_source_bundle.py"
    with tempfile.TemporaryDirectory(prefix="validate-release-source-bundle-") as temp_dir:
        temp_root = Path(temp_dir)
        clone_root = temp_root / "repo"
        bundle_path = temp_root / "release-source-bundle.zip"

        clone_result = subprocess.run(
            ["git", "clone", "--quiet", str(ROOT), str(clone_root)],
            capture_output=True,
            text=True,
            check=False,
        )
        if clone_result.returncode != 0:
            collector.fail(
                "failed to create temporary clean clone for release bundle validation: "
                f"{clone_result.stderr.strip()}"
            )
            return

        export_result = subprocess.run(
            [
                sys.executable,
                str(script_path),
                "--repo-root",
                str(clone_root),
                "--output",
                str(bundle_path),
                "--bundle-kind",
                RELEASE_SOURCE_BUNDLE,
            ],
            capture_output=True,
            text=True,
            check=False,
        )
        if export_result.returncode != 0:
            collector.fail(
                "release source bundle export failed during validation: "
                f"{export_result.stderr.strip() or export_result.stdout.strip()}"
            )
            return

        try:
            payload = json.loads(export_result.stdout)
        except json.JSONDecodeError as exc:
            collector.fail(f"release source bundle export emitted invalid JSON: {exc}")
            return

        collector.require(bundle_path.exists(), "release source bundle archive is created")
        collector.require(
            payload.get("bundle_kind") == RELEASE_SOURCE_BUNDLE,
            "release source bundle payload records explicit bundle kind",
        )
        collector.require(
            payload.get("distribution_class") == RELEASE_DISTRIBUTION_CLASS,
            "release source bundle payload records operator release distribution class",
        )
        collector.require(
            payload.get("provenance_path") == RELEASE_PROVENANCE_PATH,
            "release source bundle payload records provenance sidecar path",
        )
        collector.require(
            payload.get("tracked_only") is True,
            "release source bundle payload is tracked-only",
        )
        collector.require(
            isinstance(payload.get("git_commit"), str)
            and bool(str(payload["git_commit"]).strip()),
            "release source bundle payload records git commit",
        )
        collector.require(
            payload.get("tracked_worktree_clean") is True,
            "release source bundle payload records clean tracked worktree",
        )

        archive_root = payload.get("archive_root")
        if not isinstance(archive_root, str) or not archive_root.strip():
            collector.fail("release source bundle payload missing archive_root")
            return

        try:
            with zipfile.ZipFile(bundle_path, "r") as archive:
                archive_names = set(archive.namelist())
                manifest_name = f"{archive_root}/bundle_manifest.json"
                provenance_name = f"{archive_root}/{RELEASE_PROVENANCE_PATH}"
                collector.require(
                    manifest_name in archive_names,
                    "release source bundle archive includes bundle manifest",
                )
                collector.require(
                    provenance_name in archive_names,
                    "release source bundle archive includes provenance sidecar",
                )
                if manifest_name not in archive_names or provenance_name not in archive_names:
                    return
                manifest = json.loads(archive.read(manifest_name).decode("utf-8"))
                provenance = json.loads(archive.read(provenance_name).decode("utf-8"))
        except (OSError, zipfile.BadZipFile, KeyError, json.JSONDecodeError) as exc:
            collector.fail(f"release source bundle archive could not be inspected: {exc}")
            return

        collector.require(
            manifest.get("bundle_kind") == RELEASE_SOURCE_BUNDLE,
            "release source bundle manifest records explicit bundle kind",
        )
        collector.require(
            manifest.get("distribution_class") == RELEASE_DISTRIBUTION_CLASS,
            "release source bundle manifest records operator release distribution class",
        )
        collector.require(
            manifest.get("archive_root") == archive_root,
            "release source bundle manifest matches payload archive_root",
        )
        collector.require(
            manifest.get("provenance_path") == RELEASE_PROVENANCE_PATH,
            "release source bundle manifest points at provenance sidecar",
        )
        collector.require(
            manifest.get("tracked_only") is True
            and manifest.get("tracked_only") == payload.get("tracked_only"),
            "release source bundle manifest matches tracked-only payload",
        )
        collector.require(
            manifest.get("git_commit") == payload.get("git_commit"),
            "release source bundle manifest matches payload git commit",
        )
        collector.require(
            manifest.get("tracked_worktree_clean") is True
            and manifest.get("tracked_worktree_clean") == payload.get("tracked_worktree_clean"),
            "release source bundle manifest matches clean-worktree payload",
        )
        collector.require(
            provenance.get("bundle_kind") == RELEASE_SOURCE_BUNDLE,
            "release provenance records explicit bundle kind",
        )
        collector.require(
            provenance.get("archive_root") == archive_root,
            "release provenance matches payload archive_root",
        )
        collector.require(
            provenance.get("git_commit") == payload.get("git_commit"),
            "release provenance matches payload git commit",
        )
        collector.require(
            provenance.get("tracked_only") is True
            and provenance.get("tracked_only") == payload.get("tracked_only"),
            "release provenance matches tracked-only payload",
        )

        inner_paths: list[str] = []
        prefix = f"{archive_root}/"
        for name in sorted(archive_names):
            if not name.startswith(prefix):
                collector.fail(
                    f"release source bundle archive member escapes archive root: {name}"
                )
                continue
            inner_paths.append(name.removeprefix(prefix))

        collector.require(
            len(archive_names) == int(payload.get("file_count") or 0),
            "release source bundle payload file_count matches actual archive entries",
        )

        clutter_paths = [
            path
            for path in inner_paths
            if path not in {"bundle_manifest.json", RELEASE_PROVENANCE_PATH}
            and source_bundle_path_is_excluded(path)
        ]
        collector.require(
            not clutter_paths,
            "release source bundle archive excludes workstation and runtime clutter",
        )
        for path in clutter_paths:
            collector.fail(f"release source bundle unexpectedly includes excluded path: {path}")

        file_inventory = provenance.get("files")
        collector.require(
            isinstance(file_inventory, list),
            "release provenance includes bundled file inventory",
        )
        if not isinstance(file_inventory, list):
            return

        inventory_by_path: dict[str, dict[str, object]] = {}
        for entry in file_inventory:
            if not isinstance(entry, dict):
                collector.fail("release provenance file inventory entries must be objects")
                continue
            path = entry.get("path")
            if not isinstance(path, str) or not path:
                collector.fail("release provenance file inventory entry missing path")
                continue
            inventory_by_path[path] = entry

        release_data_paths = sorted(
            path
            for path in inner_paths
            if path not in {"bundle_manifest.json", RELEASE_PROVENANCE_PATH}
        )
        missing_inventory_paths = [
            path for path in release_data_paths if path not in inventory_by_path
        ]
        collector.require(
            not missing_inventory_paths,
            "release provenance inventories every bundled non-manifest file",
        )
        for path in missing_inventory_paths:
            collector.fail(f"release provenance missing bundled file entry: {path}")

        source_manifest_entries = provenance.get("source_manifests")
        collector.require(
            isinstance(source_manifest_entries, list),
            "release provenance includes curated source manifest list",
        )
        source_manifest_paths: set[str] = set()
        if isinstance(source_manifest_entries, list):
            for entry in source_manifest_entries:
                if not isinstance(entry, dict):
                    collector.fail(
                        "release provenance source_manifests entries must be objects"
                    )
                    continue
                path = entry.get("path")
                if not isinstance(path, str) or not path:
                    collector.fail("release provenance source_manifests entry missing path")
                    continue
                source_manifest_paths.add(path)
                collector.require(
                    inventory_by_path.get(path) == entry,
                    f"release provenance source manifest matches bundled file inventory: {path}",
                )

        for candidate in SOURCE_MANIFEST_CANDIDATES:
            if candidate in release_data_paths:
                collector.require(
                    candidate in source_manifest_paths,
                    f"release provenance records curated source manifest when present: {candidate}",
                )

        try:
            with zipfile.ZipFile(bundle_path, "r") as archive:
                for path in release_data_paths:
                    content = archive.read(f"{archive_root}/{path}")
                    entry = inventory_by_path.get(path)
                    if entry is None:
                        continue
                    collector.require(
                        entry.get("size_bytes") == len(content),
                        f"release provenance size matches archive entry: {path}",
                    )
                    collector.require(
                        entry.get("sha256") == hashlib.sha256(content).hexdigest(),
                        f"release provenance digest matches archive entry: {path}",
                    )
        except (OSError, zipfile.BadZipFile, KeyError) as exc:
            collector.fail(
                f"release source bundle archive could not verify provenance digests: {exc}"
            )
