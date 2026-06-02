#!/usr/bin/env python3
from __future__ import annotations

import argparse
from collections.abc import Callable, Sequence
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path, PurePosixPath
import re
import shlex
import subprocess
import sys
from typing import Any


LAB_VM_DEPLOY_REPORT_VERSION = 1
Runner = Callable[..., subprocess.CompletedProcess[str]]

_SHELL_ENV_NAME_RE = re.compile(r"^[A-Z_][A-Z0-9_]*$")
_PRODUCTION_WORD_RE = re.compile(r"(^|[^a-z0-9])(prod|production)([^a-z0-9]|$)")


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Plan or execute a lab-only VM deploy using gcloud compute scp/ssh. "
            "This command never targets production, Cloud Run, Kubernetes, or Terraform."
        )
    )
    parser.add_argument("--environment", required=True, choices=["lab"])
    parser.add_argument("--gcp-project", required=True)
    parser.add_argument("--zone", required=True)
    parser.add_argument("--instance", required=True)
    parser.add_argument("--release-source-bundle", required=True)
    parser.add_argument("--release-manifest", required=True)
    parser.add_argument("--remote-release-root", required=True)
    parser.add_argument("--remote-db-url", required=True)
    parser.add_argument("--remote-artifact-root", required=True)
    parser.add_argument("--remote-service-name", required=True)
    parser.add_argument("--remote-viewer-token-env", required=True)
    parser.add_argument("--remote-port", default="8080")
    parser.add_argument("--secret-ref", action="append", default=[])
    parser.add_argument("--output", default=None)
    parser.add_argument("--gcloud-bin", default="gcloud")
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--confirm-lab-target", action="store_true")
    parser.add_argument("--confirm-no-real-users", action="store_true")
    parser.add_argument("--json", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    report = deploy_lab_vm(
        environment=str(args.environment),
        gcp_project=str(args.gcp_project),
        zone=str(args.zone),
        instance=str(args.instance),
        release_source_bundle=Path(args.release_source_bundle),
        release_manifest=Path(args.release_manifest),
        remote_release_root=str(args.remote_release_root),
        remote_db_url=str(args.remote_db_url),
        remote_artifact_root=str(args.remote_artifact_root),
        remote_service_name=str(args.remote_service_name),
        remote_viewer_token_env=str(args.remote_viewer_token_env),
        remote_port=int(args.remote_port),
        secret_refs=tuple(str(ref) for ref in args.secret_ref),
        output=Path(args.output) if args.output else None,
        gcloud_bin=str(args.gcloud_bin),
        execute=bool(args.execute),
        confirm_lab_target=bool(args.confirm_lab_target),
        confirm_no_real_users=bool(args.confirm_no_real_users),
    )
    if args.json:
        sys.stdout.write(json.dumps(report, indent=2, sort_keys=True) + "\n")
    else:
        report_path = report.get("report_path")
        sys.stdout.write(f"{report_path or report['status']}\n")
    return 0


def deploy_lab_vm(
    *,
    environment: str,
    gcp_project: str,
    zone: str,
    instance: str,
    release_source_bundle: Path,
    release_manifest: Path,
    remote_release_root: str,
    remote_db_url: str,
    remote_artifact_root: str,
    remote_service_name: str,
    remote_viewer_token_env: str,
    remote_port: int = 8080,
    secret_refs: tuple[str, ...] = (),
    output: Path | None = None,
    gcloud_bin: str = "gcloud",
    execute: bool = False,
    confirm_lab_target: bool = False,
    confirm_no_real_users: bool = False,
    runner: Runner = subprocess.run,
    now_iso: str | None = None,
) -> dict[str, object]:
    plan = plan_lab_vm_deploy(
        environment=environment,
        gcp_project=gcp_project,
        zone=zone,
        instance=instance,
        release_source_bundle=release_source_bundle,
        release_manifest=release_manifest,
        remote_release_root=remote_release_root,
        remote_db_url=remote_db_url,
        remote_artifact_root=remote_artifact_root,
        remote_service_name=remote_service_name,
        remote_viewer_token_env=remote_viewer_token_env,
        remote_port=remote_port,
        secret_refs=secret_refs,
        gcloud_bin=gcloud_bin,
        execute=execute,
        confirm_lab_target=confirm_lab_target,
        confirm_no_real_users=confirm_no_real_users,
        now_iso=now_iso,
    )
    if execute:
        for command in plan["commands"]:
            assert isinstance(command, dict)
            argv = command["argv"]
            assert isinstance(argv, list)
            _run_checked([str(part) for part in argv], runner=runner)
        plan["status"] = "executed"
        plan["live_deploy_evidence_recorded"] = True
    if output is not None:
        report_path = output.expanduser().resolve()
        report_path.parent.mkdir(parents=True, exist_ok=True)
        plan["report_path"] = str(report_path)
        report_path.write_text(
            json.dumps(plan, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
    return plan


def plan_lab_vm_deploy(
    *,
    environment: str,
    gcp_project: str,
    zone: str,
    instance: str,
    release_source_bundle: Path,
    release_manifest: Path,
    remote_release_root: str,
    remote_db_url: str,
    remote_artifact_root: str,
    remote_service_name: str,
    remote_viewer_token_env: str,
    remote_port: int = 8080,
    secret_refs: tuple[str, ...] = (),
    gcloud_bin: str = "gcloud",
    execute: bool = False,
    confirm_lab_target: bool = False,
    confirm_no_real_users: bool = False,
    now_iso: str | None = None,
) -> dict[str, object]:
    if environment != "lab":
        raise SystemExit("lab VM deploy supports --environment lab only")
    if execute and not (confirm_lab_target and confirm_no_real_users):
        raise SystemExit(
            "--execute requires --confirm-lab-target and --confirm-no-real-users"
        )
    if not (1 <= remote_port <= 65535):
        raise SystemExit("--remote-port must be between 1 and 65535")
    _validate_no_production_target(
        {
            "gcp_project": gcp_project,
            "instance": instance,
            "remote_release_root": remote_release_root,
            "remote_db_url": remote_db_url,
            "remote_artifact_root": remote_artifact_root,
            "remote_service_name": remote_service_name,
        }
    )
    _validate_gcloud_bin(gcloud_bin)
    _validate_remote_path(remote_release_root, "--remote-release-root")
    _validate_remote_path(remote_artifact_root, "--remote-artifact-root")
    _validate_remote_sqlite_url(remote_db_url)
    _validate_shell_env_name(remote_viewer_token_env, "--remote-viewer-token-env")
    _validate_service_name(remote_service_name)
    safe_secret_refs = _validate_secret_refs(secret_refs)

    resolved_bundle = release_source_bundle.expanduser().resolve()
    resolved_manifest = release_manifest.expanduser().resolve()
    release = _load_release_tuple(
        release_manifest=resolved_manifest,
        release_source_bundle=resolved_bundle,
    )
    release_id = _release_id(release)
    remote_release_root_path = PurePosixPath(remote_release_root)
    remote_staging_dir = remote_release_root_path / "incoming" / release_id
    remote_release_dir = remote_release_root_path / "releases" / release_id
    remote_manifest_path = remote_staging_dir / resolved_manifest.name
    remote_bundle_path = remote_staging_dir / resolved_bundle.name
    remote_backup_output = remote_staging_dir / "backup_manifest.json"

    commands = [
        _gcloud_ssh_command(
            gcloud_bin=gcloud_bin,
            project=gcp_project,
            zone=zone,
            instance=instance,
            remote_command=(
                "mkdir -p "
                f"{shlex.quote(str(remote_staging_dir))} "
                f"{shlex.quote(str(remote_release_dir))}"
            ),
            kind="prepare_remote_dirs",
        ),
        _gcloud_scp_command(
            gcloud_bin=gcloud_bin,
            project=gcp_project,
            zone=zone,
            instance=instance,
            sources=(resolved_bundle, resolved_manifest),
            destination=f"{instance}:{remote_staging_dir}/",
        ),
        _gcloud_ssh_command(
            gcloud_bin=gcloud_bin,
            project=gcp_project,
            zone=zone,
            instance=instance,
            remote_command=_remote_deploy_script(
                remote_bundle_path=remote_bundle_path,
                remote_manifest_path=remote_manifest_path,
                remote_release_dir=remote_release_dir,
                remote_db_url=remote_db_url,
                remote_artifact_root=remote_artifact_root,
                remote_backup_output=remote_backup_output,
                remote_service_name=remote_service_name,
                remote_viewer_token_env=remote_viewer_token_env,
                remote_port=remote_port,
                secret_refs=safe_secret_refs,
            ),
            kind="deploy_and_smoke",
        ),
    ]
    _assert_allowed_command_plan(commands)
    return {
        "manifest_version": LAB_VM_DEPLOY_REPORT_VERSION,
        "command": "lab.vm.deploy",
        "generated_at": now_iso or _utc_now_iso(),
        "status": "planned",
        "environment": "lab",
        "execution": {
            "execute_requested": execute,
            "confirm_lab_target": confirm_lab_target,
            "confirm_no_real_users": confirm_no_real_users,
        },
        "live_deploy_evidence_recorded": False,
        "live_deploy_evidence_required_for_task_done": True,
        "gcp": {
            "project": gcp_project,
            "zone": zone,
            "instance": instance,
        },
        "release": release,
        "remote": {
            "release_root": str(remote_release_root_path),
            "staging_dir": str(remote_staging_dir),
            "release_dir": str(remote_release_dir),
            "db_url": remote_db_url,
            "artifact_root": remote_artifact_root,
            "service_name": remote_service_name,
            "viewer_token_env": remote_viewer_token_env,
            "port": remote_port,
        },
        "secret_refs": safe_secret_refs,
        "commands": commands,
        "forbidden_tooling_policy": {
            "allowed_gcloud_compute_subcommands": ["scp", "ssh"],
            "cloud_run": False,
            "kubernetes": False,
            "terraform": False,
            "production_targets": False,
        },
        "smoke_checks": [
            "/api/v1/ops/health",
            "/api/v1/ops/readiness",
            "/api/v1/viewer",
            "remote_artifact_root_exists_and_writable",
        ],
    }


def _load_release_tuple(
    *,
    release_manifest: Path,
    release_source_bundle: Path,
) -> dict[str, object]:
    if not release_manifest.exists() or not release_manifest.is_file():
        raise SystemExit(f"release manifest does not exist: {release_manifest}")
    if not release_source_bundle.exists() or not release_source_bundle.is_file():
        raise SystemExit(f"release_source_bundle does not exist: {release_source_bundle}")
    loaded = json.loads(release_manifest.read_text(encoding="utf-8"))
    if not isinstance(loaded, dict) or loaded.get("command") != "release.image.build":
        raise SystemExit("release manifest must come from release.image.build")
    source_bundle = loaded.get("release_source_bundle")
    image = loaded.get("image")
    if not isinstance(source_bundle, dict) or not isinstance(image, dict):
        raise SystemExit("release manifest missing release_source_bundle or image block")
    if source_bundle.get("bundle_kind") != "release_source_bundle":
        raise SystemExit("release manifest bundle_kind must be release_source_bundle")
    expected_bundle_sha = source_bundle.get("sha256")
    image_digest_ref = image.get("digest_ref")
    git_commit = loaded.get("git_commit")
    if not all(
        isinstance(value, str) and value.strip()
        for value in (expected_bundle_sha, image_digest_ref, git_commit)
    ):
        raise SystemExit("release manifest missing git, bundle, or image digest fields")
    actual_bundle_sha = _sha256_file(release_source_bundle)
    if actual_bundle_sha != expected_bundle_sha:
        raise SystemExit("release_source_bundle sha256 does not match release manifest")
    return {
        "manifest_path": str(release_manifest),
        "manifest_sha256": _sha256_file(release_manifest),
        "git_commit": str(git_commit),
        "release_source_bundle_path": str(release_source_bundle),
        "release_source_bundle_sha256": actual_bundle_sha,
        "image_digest_ref": str(image_digest_ref),
    }


def _remote_deploy_script(
    *,
    remote_bundle_path: PurePosixPath,
    remote_manifest_path: PurePosixPath,
    remote_release_dir: PurePosixPath,
    remote_db_url: str,
    remote_artifact_root: str,
    remote_backup_output: PurePosixPath,
    remote_service_name: str,
    remote_viewer_token_env: str,
    remote_port: int,
    secret_refs: Sequence[str],
) -> str:
    secret_args = " ".join(
        f"--secret-ref {shlex.quote(secret_ref)}" for secret_ref in secret_refs
    )
    backup_command = (
        "python3.11 scripts/prepare_predeploy_backup.py "
        "--environment lab "
        f"--db-url {shlex.quote(remote_db_url)} "
        f"--artifact-root {shlex.quote(remote_artifact_root)} "
        f"--release-manifest {shlex.quote(str(remote_manifest_path))} "
        f"--output {shlex.quote(str(remote_backup_output))} "
        f"{secret_args} --json"
    )
    return "\n".join(
        [
            "set -euo pipefail",
            f"rm -rf {shlex.quote(str(remote_release_dir))}",
            f"mkdir -p {shlex.quote(str(remote_release_dir))}",
            "python3.11 - <<'PY'",
            "from pathlib import Path",
            "import zipfile",
            f"bundle = Path({str(remote_bundle_path)!r})",
            f"target = Path({str(remote_release_dir)!r})",
            "with zipfile.ZipFile(bundle, 'r') as archive:",
            "    archive.extractall(target)",
            "PY",
            f"cd {shlex.quote(str(remote_release_dir))}/*",
            backup_command,
            'python3.11 -m pip install --upgrade pip',
            'python3.11 -m pip install -e ".[api]"',
            'if [ -d frontend ]; then (cd frontend && npm ci && npm run build); fi',
            f"sudo systemctl restart {shlex.quote(remote_service_name)}",
            f"curl -fsS http://127.0.0.1:{remote_port}/api/v1/ops/health >/tmp/onetruth-lab-health.json",
            f"curl -fsS http://127.0.0.1:{remote_port}/api/v1/ops/readiness >/tmp/onetruth-lab-readiness.json",
            f"test -d {shlex.quote(remote_artifact_root)}",
            f"test -w {shlex.quote(remote_artifact_root)}",
            f"test -n \"${{{remote_viewer_token_env}:-}}\"",
            (
                'curl -fsS -H "Authorization: Bearer '
                f"${{{remote_viewer_token_env}}}\" "
                f"http://127.0.0.1:{remote_port}/api/v1/viewer "
                ">/tmp/onetruth-lab-viewer.json"
            ),
            "python3.11 - <<'PY'",
            "import json",
            "viewer = json.loads(open('/tmp/onetruth-lab-viewer.json', encoding='utf-8').read())",
            "session = viewer['viewer_session']",
            "assert session['request_context_mode'] == 'server_derived'",
            "assert session['actor_switching_allowed'] is False",
            "PY",
        ]
    )


def _gcloud_ssh_command(
    *,
    gcloud_bin: str,
    project: str,
    zone: str,
    instance: str,
    remote_command: str,
    kind: str,
) -> dict[str, object]:
    return {
        "kind": kind,
        "tool": "gcloud_compute_ssh",
        "argv": [
            gcloud_bin,
            "compute",
            "ssh",
            instance,
            "--project",
            project,
            "--zone",
            zone,
            "--command",
            remote_command,
        ],
    }


def _gcloud_scp_command(
    *,
    gcloud_bin: str,
    project: str,
    zone: str,
    instance: str,
    sources: Sequence[Path],
    destination: str,
) -> dict[str, object]:
    return {
        "kind": "copy_release_inputs",
        "tool": "gcloud_compute_scp",
        "argv": [
            gcloud_bin,
            "compute",
            "scp",
            "--project",
            project,
            "--zone",
            zone,
            *(str(source) for source in sources),
            destination,
        ],
    }


def _assert_allowed_command_plan(commands: Sequence[dict[str, object]]) -> None:
    for command in commands:
        argv = command.get("argv")
        if not isinstance(argv, list) or len(argv) < 3:
            raise SystemExit("invalid gcloud command plan")
        joined = " ".join(str(part) for part in argv)
        if argv[0] != "gcloud" and not str(argv[0]).endswith("/gcloud"):
            raise SystemExit("lab deploy may only invoke gcloud")
        if argv[1:3] != ["compute", "ssh"] and argv[1:3] != ["compute", "scp"]:
            raise SystemExit("lab deploy may only invoke gcloud compute scp/ssh")
        lowered = joined.casefold()
        forbidden = ("gcloud run", "kubectl", "terraform", "cloud run deploy")
        hit = [item for item in forbidden if item in lowered]
        if hit:
            raise SystemExit(f"forbidden deploy tooling in command plan: {hit[0]}")


def _run_checked(command: list[str], *, runner: Runner) -> subprocess.CompletedProcess[str]:
    result = runner(
        command,
        text=True,
        capture_output=True,
        check=False,
    )
    if result.returncode != 0:
        raise SystemExit(result.stderr.strip() or f"command failed: {' '.join(command)}")
    return result


def _validate_no_production_target(values: dict[str, str]) -> None:
    for name, value in values.items():
        if _PRODUCTION_WORD_RE.search(value.casefold()):
            raise SystemExit(f"{name} must not reference a production target")


def _validate_remote_path(value: str, arg_name: str) -> None:
    path = PurePosixPath(value)
    if not value.startswith("/") or ".." in path.parts:
        raise SystemExit(f"{arg_name} must be an absolute remote path without '..'")


def _validate_remote_sqlite_url(value: str) -> None:
    if not value.startswith("sqlite:////") or ".." in value:
        raise SystemExit("--remote-db-url must be an absolute sqlite://// remote path")


def _validate_shell_env_name(value: str, arg_name: str) -> None:
    if not _SHELL_ENV_NAME_RE.match(value):
        raise SystemExit(f"{arg_name} must be a shell env var name")


def _validate_service_name(value: str) -> None:
    if not re.match(r"^[A-Za-z0-9_.@:-]+$", value):
        raise SystemExit("--remote-service-name must be a systemd service name")


def _validate_gcloud_bin(value: str) -> None:
    path = PurePosixPath(value)
    if path.name != "gcloud":
        raise SystemExit("--gcloud-bin must point to gcloud")


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


def _release_id(release: dict[str, object]) -> str:
    git_commit = str(release["git_commit"])
    manifest_sha = str(release["manifest_sha256"])
    return f"release-{git_commit[:12]}-{manifest_sha[:12]}"


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _utc_now_iso() -> str:
    return (
        datetime.now(timezone.utc)
        .replace(microsecond=0)
        .isoformat()
        .replace("+00:00", "Z")
    )


if __name__ == "__main__":
    raise SystemExit(main())
