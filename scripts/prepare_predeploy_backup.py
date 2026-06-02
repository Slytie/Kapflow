#!/usr/bin/env python3
from __future__ import annotations

import argparse
from datetime import UTC, datetime
import hashlib
import json
from pathlib import Path
import sys
from urllib.parse import unquote, urlparse


BACKUP_MANIFEST_VERSION = 1


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Validate the lab/prod DB, artifact-root, and release tuple before deploy "
            "and write a backup_manifest.json. This skeleton is validate-only and does "
            "not copy, archive, restore, upload, or mutate runtime state."
        )
    )
    parser.add_argument("--environment", required=True, choices=["lab", "prod"])
    parser.add_argument("--db-url", required=True)
    parser.add_argument("--artifact-root", required=True)
    parser.add_argument("--release-manifest", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument(
        "--secret-ref",
        action="append",
        default=[],
        help="Secret/config reference name. Repeat as needed; do not pass secret values.",
    )
    parser.add_argument("--json", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    manifest = prepare_predeploy_backup_manifest(
        environment=str(args.environment),
        db_url=str(args.db_url),
        artifact_root=Path(args.artifact_root),
        release_manifest=Path(args.release_manifest),
        output=Path(args.output),
        secret_refs=tuple(str(ref) for ref in args.secret_ref),
    )
    if args.json:
        sys.stdout.write(json.dumps(manifest, indent=2, sort_keys=True) + "\n")
    else:
        sys.stdout.write(f"{args.output}\n")
    return 0


def prepare_predeploy_backup_manifest(
    *,
    environment: str,
    db_url: str,
    artifact_root: Path,
    release_manifest: Path,
    output: Path,
    secret_refs: tuple[str, ...] = (),
    now_iso: str | None = None,
) -> dict[str, object]:
    if environment not in {"lab", "prod"}:
        raise SystemExit("--environment must be lab or prod")

    db_path = _sqlite_path_from_url(db_url).resolve()
    if not db_path.exists() or not db_path.is_file():
        raise SystemExit(f"SQLite DB file does not exist: {db_path}")
    if db_path.stat().st_size <= 0:
        raise SystemExit(f"SQLite DB file is empty: {db_path}")

    resolved_artifact_root = artifact_root.expanduser().resolve()
    if not resolved_artifact_root.exists() or not resolved_artifact_root.is_dir():
        raise SystemExit(f"artifact root does not exist or is not a directory: {resolved_artifact_root}")

    resolved_release_manifest = release_manifest.expanduser().resolve()
    release = _load_release_tuple(resolved_release_manifest)
    safe_secret_refs = _validate_secret_refs(secret_refs)
    artifact_summary = _summarize_artifact_root(resolved_artifact_root)

    manifest = {
        "manifest_version": BACKUP_MANIFEST_VERSION,
        "command": "predeploy.backup_manifest.prepare",
        "generated_at": now_iso or _utc_now_iso(),
        "mode": "validate_only",
        "environment": environment,
        "state_copy_performed": False,
        "restore_proof": False,
        "db": {
            "url": db_url,
            "path": str(db_path),
            "size_bytes": db_path.stat().st_size,
            "sha256": _sha256_file(db_path),
        },
        "artifact_root": {
            "path": str(resolved_artifact_root),
            "file_count": artifact_summary["file_count"],
            "total_size_bytes": artifact_summary["total_size_bytes"],
        },
        "release": release,
        "secret_refs": safe_secret_refs,
    }

    output_path = output.expanduser().resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return manifest


def _sqlite_path_from_url(db_url: str) -> Path:
    parsed = urlparse(db_url)
    if parsed.scheme != "sqlite":
        raise SystemExit("predeploy backup skeleton supports local sqlite:/// DB URLs only")
    if parsed.netloc:
        raise SystemExit("sqlite DB URL must not include a network location")
    if parsed.path in {"", "/:memory:"}:
        raise SystemExit("sqlite DB URL must resolve to a filesystem DB file")
    return Path(unquote(parsed.path))


def _load_release_tuple(release_manifest: Path) -> dict[str, object]:
    if not release_manifest.exists() or not release_manifest.is_file():
        raise SystemExit(f"release manifest does not exist: {release_manifest}")
    loaded = json.loads(release_manifest.read_text(encoding="utf-8"))
    if not isinstance(loaded, dict):
        raise SystemExit("release_manifest.json must be a JSON object")
    if loaded.get("command") != "release.image.build":
        raise SystemExit("release manifest must come from release.image.build")

    source_bundle = loaded.get("release_source_bundle")
    image = loaded.get("image")
    if not isinstance(source_bundle, dict) or not isinstance(image, dict):
        raise SystemExit("release manifest missing release_source_bundle or image block")
    bundle_path_value = source_bundle.get("path")
    bundle_sha_value = source_bundle.get("sha256")
    image_digest_ref = image.get("digest_ref")
    git_commit = loaded.get("git_commit")
    if not all(isinstance(value, str) and value.strip() for value in (
        bundle_path_value,
        bundle_sha_value,
        image_digest_ref,
        git_commit,
    )):
        raise SystemExit("release manifest missing git, bundle, or image digest fields")

    bundle_path = Path(str(bundle_path_value)).expanduser().resolve()
    if not bundle_path.exists() or not bundle_path.is_file():
        raise SystemExit(f"release_source_bundle path does not exist: {bundle_path}")
    actual_bundle_sha = _sha256_file(bundle_path)
    if actual_bundle_sha != bundle_sha_value:
        raise SystemExit("release_source_bundle sha256 does not match release manifest")

    return {
        "manifest_path": str(release_manifest),
        "manifest_sha256": _sha256_file(release_manifest),
        "git_commit": str(git_commit),
        "release_source_bundle_path": str(bundle_path),
        "release_source_bundle_sha256": actual_bundle_sha,
        "image_digest_ref": str(image_digest_ref),
    }


def _validate_secret_refs(secret_refs: tuple[str, ...]) -> list[str]:
    cleaned: list[str] = []
    seen: set[str] = set()
    for raw_ref in secret_refs:
        ref = raw_ref.strip()
        if not ref:
            continue
        lowered = ref.casefold()
        if "\n" in ref or "\r" in ref or "=" in ref or "-----begin" in lowered:
            raise SystemExit("--secret-ref must be a reference name, not a secret value")
        if ref not in seen:
            cleaned.append(ref)
            seen.add(ref)
    return cleaned


def _summarize_artifact_root(artifact_root: Path) -> dict[str, int]:
    file_count = 0
    total_size_bytes = 0
    for path in artifact_root.rglob("*"):
        if path.is_file():
            file_count += 1
            total_size_bytes += path.stat().st_size
    return {"file_count": file_count, "total_size_bytes": total_size_bytes}


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _utc_now_iso() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


if __name__ == "__main__":
    raise SystemExit(main())
