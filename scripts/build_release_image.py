#!/usr/bin/env python3
from __future__ import annotations

import argparse
from collections.abc import Callable, Sequence
from datetime import UTC, datetime
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import zipfile


RELEASE_MANIFEST_VERSION = 1
RELEASE_SOURCE_BUNDLE = "release_source_bundle"
RELEASE_PROVENANCE_PATH = "release_provenance.json"
DEFAULT_BUNDLE_NAME = "release-source-bundle.zip"
DEFAULT_MANIFEST_NAME = "release_manifest.json"
LOCAL_DIGEST_SOURCE = "local_image_id"
PUSH_DIGEST_SOURCE = "registry_push"
SHA256_DIGEST_RE = re.compile(r"sha256:[0-9a-f]{64}")


Runner = Callable[..., subprocess.CompletedProcess[str]]


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Build the onetruth-api release image from a canonical release_source_bundle "
            "and write a release_manifest.json. This command never deploys."
        )
    )
    parser.add_argument(
        "--repo-root",
        default=str(Path(__file__).resolve().parents[1]),
        help="Repository root used when exporting a release_source_bundle.",
    )
    parser.add_argument(
        "--output-root",
        required=True,
        help="Directory for release_source_bundle, image iid file, and release_manifest.json.",
    )
    parser.add_argument(
        "--image-ref",
        required=True,
        help="Image reference to build, for example us-docker.pkg.dev/project/repo/onetruth-api:tag.",
    )
    parser.add_argument(
        "--release-source-bundle",
        default=None,
        help="Existing release_source_bundle ZIP. If omitted, one is exported from --repo-root.",
    )
    parser.add_argument(
        "--push",
        action="store_true",
        help="Push the image ref and record the registry digest returned by docker push.",
    )
    parser.add_argument(
        "--docker-bin",
        default="docker",
        help="Docker executable. Defaults to docker.",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Emit the release manifest JSON to stdout.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    manifest = build_release_image(
        repo_root=Path(args.repo_root),
        output_root=Path(args.output_root),
        image_ref=str(args.image_ref),
        release_source_bundle=(
            Path(args.release_source_bundle) if args.release_source_bundle else None
        ),
        push=bool(args.push),
        docker_bin=str(args.docker_bin),
    )
    if args.json:
        sys.stdout.write(json.dumps(manifest, indent=2, sort_keys=True) + "\n")
    else:
        sys.stdout.write(f"{manifest['manifest_path']}\n")
    return 0


def build_release_image(
    *,
    repo_root: Path,
    output_root: Path,
    image_ref: str,
    release_source_bundle: Path | None = None,
    push: bool = False,
    docker_bin: str = "docker",
    runner: Runner = subprocess.run,
    now_iso: str | None = None,
) -> dict[str, object]:
    resolved_repo_root = repo_root.expanduser().resolve()
    resolved_output_root = output_root.expanduser().resolve()
    resolved_output_root.mkdir(parents=True, exist_ok=True)
    _validate_image_ref(image_ref)

    bundle_path = (
        release_source_bundle.expanduser().resolve()
        if release_source_bundle is not None
        else _export_release_source_bundle(
            repo_root=resolved_repo_root,
            output_root=resolved_output_root,
            runner=runner,
        )
    )
    if not bundle_path.exists() or not bundle_path.is_file():
        raise SystemExit(f"release_source_bundle does not exist: {bundle_path}")

    bundle_manifest, release_provenance_present = _read_bundle_manifest(bundle_path)
    archive_root = _require_str(bundle_manifest, "archive_root")
    git_commit = _require_str(bundle_manifest, "git_commit")
    bundle_kind = _require_str(bundle_manifest, "bundle_kind")
    if bundle_kind != RELEASE_SOURCE_BUNDLE:
        raise SystemExit(
            f"expected bundle_kind {RELEASE_SOURCE_BUNDLE!r}, got {bundle_kind!r}"
        )
    if not release_provenance_present:
        raise SystemExit(
            f"release_source_bundle must include {RELEASE_PROVENANCE_PATH}"
        )

    bundle_digest = _sha256_file(bundle_path)
    bundle_size = bundle_path.stat().st_size
    iid_path = resolved_output_root / "release_image.iid"
    if iid_path.exists():
        iid_path.unlink()

    with tempfile.TemporaryDirectory(prefix="onetruth-release-image-") as temp_dir:
        extract_root = Path(temp_dir)
        with zipfile.ZipFile(bundle_path, "r") as archive:
            archive.extractall(extract_root)
        source_root = (extract_root / archive_root).resolve()
        dockerfile_path = source_root / "Dockerfile"
        if not dockerfile_path.exists():
            raise SystemExit(
                "release_source_bundle does not contain root Dockerfile required "
                "for API image build"
            )
        dockerfile_digest = _sha256_file(dockerfile_path)

        build_command = _docker_build_command(
            docker_bin=docker_bin,
            image_ref=image_ref,
            dockerfile_path=dockerfile_path,
            source_root=source_root,
            iid_path=iid_path,
            git_commit=git_commit,
        )
        _run_checked(build_command, runner=runner)
        local_image_id = _read_digest_file(iid_path, "docker build iidfile")

        if push:
            push_result = _run_checked(
                [docker_bin, "push", image_ref],
                runner=runner,
            )
            image_digest = _parse_push_digest(push_result.stdout + "\n" + push_result.stderr)
            digest_source = PUSH_DIGEST_SOURCE
        else:
            image_digest = local_image_id
            digest_source = LOCAL_DIGEST_SOURCE

    image_repository, image_tag = _split_image_ref(image_ref)
    image_digest_ref = f"{image_repository}@{image_digest}"
    manifest = {
        "manifest_version": RELEASE_MANIFEST_VERSION,
        "command": "release.image.build",
        "created_at": now_iso or _utc_now_iso(),
        "git_commit": git_commit,
        "build_mode": "push" if push else "local",
        "deployment": {
            "performed": False,
            "commands": [],
        },
        "release_source_bundle": {
            "path": str(bundle_path),
            "sha256": bundle_digest,
            "size_bytes": bundle_size,
            "archive_root": archive_root,
            "bundle_kind": bundle_kind,
            "provenance_path": RELEASE_PROVENANCE_PATH,
        },
        "dockerfile": {
            "path": "Dockerfile",
            "sha256": dockerfile_digest,
        },
        "image": {
            "ref": image_ref,
            "repository": image_repository,
            "tag": image_tag,
            "digest": image_digest,
            "digest_ref": image_digest_ref,
            "digest_source": digest_source,
            "pushed": push,
        },
    }

    manifest_path = resolved_output_root / DEFAULT_MANIFEST_NAME
    manifest["manifest_path"] = str(manifest_path)
    manifest_path.write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return manifest


def _export_release_source_bundle(
    *,
    repo_root: Path,
    output_root: Path,
    runner: Runner,
) -> Path:
    bundle_path = output_root / DEFAULT_BUNDLE_NAME
    script_path = repo_root / "scripts" / "export_clean_source_bundle.py"
    command = [
        sys.executable,
        str(script_path),
        "--repo-root",
        str(repo_root),
        "--output",
        str(bundle_path),
        "--bundle-kind",
        RELEASE_SOURCE_BUNDLE,
    ]
    _run_checked(command, runner=runner)
    return bundle_path


def _docker_build_command(
    *,
    docker_bin: str,
    image_ref: str,
    dockerfile_path: Path,
    source_root: Path,
    iid_path: Path,
    git_commit: str,
) -> list[str]:
    return [
        docker_bin,
        "build",
        "--iidfile",
        str(iid_path),
        "--label",
        "org.opencontainers.image.title=onetruth-api",
        "--label",
        f"org.opencontainers.image.revision={git_commit}",
        "--tag",
        image_ref,
        "--file",
        str(dockerfile_path),
        str(source_root),
    ]


def _run_checked(
    command: Sequence[str],
    *,
    runner: Runner,
) -> subprocess.CompletedProcess[str]:
    _reject_deploy_command(command)
    result = runner(
        list(command),
        text=True,
        capture_output=True,
        check=False,
    )
    if result.returncode != 0:
        raise SystemExit(
            "command failed: "
            f"{' '.join(command)}\n{result.stderr.strip() or result.stdout.strip()}"
        )
    return result


def _reject_deploy_command(command: Sequence[str]) -> None:
    joined = " ".join(command).casefold()
    forbidden = (
        "gcloud run",
        "cloud run deploy",
        "kubectl",
        "terraform",
        "available_secrets",
        "availablesecrets",
        "secretenv",
        "production_db_url",
    )
    hits = [token for token in forbidden if token in joined]
    if hits:
        raise SystemExit(f"release image build command contains forbidden token: {hits[0]}")


def _read_bundle_manifest(bundle_path: Path) -> tuple[dict[str, object], bool]:
    with zipfile.ZipFile(bundle_path, "r") as archive:
        names = archive.namelist()
        manifest_names = [
            name for name in names if name.endswith("/bundle_manifest.json")
        ]
        if len(manifest_names) != 1:
            raise SystemExit(
                "release_source_bundle must contain exactly one bundle_manifest.json"
            )
        manifest = json.loads(archive.read(manifest_names[0]).decode("utf-8"))
        archive_root = manifest_names[0].removesuffix("/bundle_manifest.json")
        release_provenance_present = f"{archive_root}/{RELEASE_PROVENANCE_PATH}" in names
    if not isinstance(manifest, dict):
        raise SystemExit("bundle_manifest.json must be a JSON object")
    return manifest, release_provenance_present


def _read_digest_file(path: Path, label: str) -> str:
    if not path.exists():
        raise SystemExit(f"{label} was not written: {path}")
    raw = path.read_text(encoding="utf-8").strip()
    if not SHA256_DIGEST_RE.fullmatch(raw):
        raise SystemExit(f"{label} must contain sha256 digest, got {raw!r}")
    return raw


def _parse_push_digest(output: str) -> str:
    digest_match = re.search(r"digest:\s*(sha256:[0-9a-f]{64})", output)
    if digest_match is not None:
        return digest_match.group(1)
    fallback = SHA256_DIGEST_RE.search(output)
    if fallback is not None:
        return fallback.group(0)
    raise SystemExit("docker push did not report a registry sha256 digest")


def _split_image_ref(image_ref: str) -> tuple[str, str | None]:
    last_slash = image_ref.rfind("/")
    tag_separator = image_ref.rfind(":")
    if tag_separator > last_slash:
        return image_ref[:tag_separator], image_ref[tag_separator + 1 :]
    return image_ref, None


def _validate_image_ref(image_ref: str) -> None:
    if not image_ref.strip():
        raise SystemExit("--image-ref must not be empty")
    if "@" in image_ref:
        raise SystemExit("--image-ref must be a tag/ref, not an @sha256 digest ref")


def _require_str(mapping: dict[str, object], key: str) -> str:
    value = mapping.get(key)
    if not isinstance(value, str) or not value.strip():
        raise SystemExit(f"bundle_manifest.json missing non-empty {key}")
    return value


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
