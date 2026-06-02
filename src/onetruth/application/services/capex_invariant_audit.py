from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path, PurePosixPath
import subprocess
from typing import Callable, Literal, Sequence

from onetruth.infrastructure.events.event_store import utc_now_iso

GateMode = Literal["hard_gate", "known_gap", "advisory"]


@dataclass(frozen=True)
class AuditEvaluation:
    passed: bool
    details: dict[str, object]


@dataclass(frozen=True)
class CapexInvariant:
    invariant_id: str
    title: str
    gate_mode: GateMode
    task_refs: tuple[str, ...]
    description: str
    evaluator: Callable[[Path], AuditEvaluation] | None = None


CAPEX_INVARIANT_REGISTRY: tuple[CapexInvariant, ...] = (
    CapexInvariant(
        invariant_id="capex.pr001.no_active_tracked_node_modules",
        title="No active tracked node_modules residue",
        gate_mode="hard_gate",
        task_refs=("TASK-0234",),
        description="Repo truth must not contain active tracked node_modules paths.",
        evaluator=lambda repo_root: _check_no_active_tracked_node_modules(repo_root),
    ),
    CapexInvariant(
        invariant_id="capex.pr001.cloudbuild_pr_secretless",
        title="Cloud Build PR skeleton is secretless and non-deploying",
        gate_mode="hard_gate",
        task_refs=("TASK-0234",),
        description="PR validation must not carry production secrets, deploy commands, or artifact-root mutation.",
        evaluator=lambda repo_root: _check_cloudbuild_pr_skeleton(repo_root),
    ),
    CapexInvariant(
        invariant_id="capex.pr002.artifact_storage_root_confined",
        title="Artifact download/storage root confinement is present",
        gate_mode="hard_gate",
        task_refs=("TASK-0235",),
        description="Artifact writes/read downloads must be root-confined and authorize before blob reads.",
        evaluator=lambda repo_root: _check_artifact_storage_safety_source(repo_root),
    ),
    CapexInvariant(
        invariant_id="capex.pr003.command_transaction_savepoint",
        title="Command transaction helper composes under outer transactions",
        gate_mode="hard_gate",
        task_refs=("TASK-0236",),
        description="Schedule-control and logistics-handoff handlers must use the savepoint-aware helper.",
        evaluator=lambda repo_root: _check_command_transaction_source(repo_root),
    ),
    CapexInvariant(
        invariant_id="capex.known_gap.approval_side_effect_coupling",
        title="Approval response domain side-effect coupling",
        gate_mode="known_gap",
        task_refs=("TASK-0257", "TASK-0561", "TASK-0576"),
        description="Tracked in CAPEX intake; not closed by TASK-0237/TASK-0238.",
    ),
    CapexInvariant(
        invariant_id="capex.known_gap.project_membership_runtime",
        title="CAPEX project membership runtime",
        gate_mode="known_gap",
        task_refs=("TASK-0261", "TASK-0262", "TASK-0263", "TASK-0385", "TASK-0386", "TASK-0563"),
        description="Tracked in CAPEX intake; future project-scope runtime remains blocked.",
    ),
    CapexInvariant(
        invariant_id="capex.known_gap.source_occurrence_sourceref",
        title="Source occurrence and SourceRef runtime",
        gate_mode="known_gap",
        task_refs=("TASK-0268", "TASK-0391", "TASK-0407", "TASK-0428", "TASK-0564", "TASK-0578"),
        description="Tracked in CAPEX intake; source evidence resolver work remains future scope.",
    ),
    CapexInvariant(
        invariant_id="capex.known_gap.generated_artifact_migration",
        title="Generated-artifact migration beyond helper",
        gate_mode="known_gap",
        task_refs=("TASK-0276", "TASK-0375", "TASK-0401", "TASK-0405"),
        description="TASK-0238 adds the foundation helper only; broad generated-artifact migration is later work.",
    ),
)


def run_capex_invariant_audit(
    *,
    repo_root: Path,
    output_root: Path,
    now_iso: str | None = None,
    registry: Sequence[CapexInvariant] | None = None,
) -> dict[str, object]:
    resolved_repo_root = repo_root.expanduser().resolve()
    resolved_output_root = output_root.expanduser().resolve()
    invariants = tuple(registry or CAPEX_INVARIANT_REGISTRY)
    checks = [_evaluate_invariant(entry, resolved_repo_root) for entry in invariants]
    summary = _summarize_checks(checks)
    status = "failed" if summary["hard_gate_failed"] else "passed"
    generated_at = now_iso or utc_now_iso()
    manifest = {
        "manifest_version": 1,
        "command": "capex.invariant_audit.run",
        "status": status,
        "generated_at": generated_at,
        "repo_root": str(resolved_repo_root),
        "output_root": str(resolved_output_root),
        "summary": summary,
        "checks": checks,
    }

    resolved_output_root.mkdir(parents=True, exist_ok=True)
    json_path = resolved_output_root / "capex_invariant_audit.json"
    markdown_path = resolved_output_root / "capex_invariant_audit.md"
    json_path.write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    markdown_path.write_text(_render_markdown_report(manifest), encoding="utf-8")
    manifest["report_paths"] = {
        "json": str(json_path),
        "markdown": str(markdown_path),
    }
    json_path.write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return manifest


def capex_invariant_audit_exit_code(manifest: dict[str, object]) -> int:
    return 0 if str(manifest.get("status")) == "passed" else 1


def _evaluate_invariant(entry: CapexInvariant, repo_root: Path) -> dict[str, object]:
    if entry.gate_mode == "known_gap":
        status = "known_gap"
        details: dict[str, object] = {"blocking": False}
    elif entry.evaluator is None:
        status = "advisory"
        details = {"blocking": False}
    else:
        evaluation = entry.evaluator(repo_root)
        status = "passed" if evaluation.passed else "failed"
        details = dict(evaluation.details)
        details["blocking"] = entry.gate_mode == "hard_gate" and not evaluation.passed

    return {
        "invariant_id": entry.invariant_id,
        "title": entry.title,
        "gate_mode": entry.gate_mode,
        "status": status,
        "task_refs": list(entry.task_refs),
        "description": entry.description,
        "details": details,
    }


def _summarize_checks(checks: Sequence[dict[str, object]]) -> dict[str, int]:
    hard_gate_failed = sum(
        1
        for check in checks
        if check.get("gate_mode") == "hard_gate" and check.get("status") == "failed"
    )
    return {
        "total": len(checks),
        "hard_gate_passed": sum(
            1
            for check in checks
            if check.get("gate_mode") == "hard_gate" and check.get("status") == "passed"
        ),
        "hard_gate_failed": hard_gate_failed,
        "known_gaps": sum(1 for check in checks if check.get("status") == "known_gap"),
        "advisory": sum(1 for check in checks if check.get("gate_mode") == "advisory"),
    }


def _render_markdown_report(manifest: dict[str, object]) -> str:
    summary = manifest["summary"]
    assert isinstance(summary, dict)
    lines = [
        "# CAPEX Invariant Audit",
        "",
        f"- Status: `{manifest['status']}`",
        f"- Generated at: `{manifest['generated_at']}`",
        f"- Hard gates passed: `{summary['hard_gate_passed']}`",
        f"- Hard gates failed: `{summary['hard_gate_failed']}`",
        f"- Known gaps: `{summary['known_gaps']}`",
        "",
        "| Invariant | Gate mode | Status | Task refs | Title |",
        "|---|---|---|---|---|",
    ]
    checks = manifest["checks"]
    assert isinstance(checks, list)
    for check in checks:
        assert isinstance(check, dict)
        task_refs = ", ".join(str(ref) for ref in check.get("task_refs", []))
        lines.append(
            "| {invariant_id} | `{gate_mode}` | `{status}` | {task_refs} | {title} |".format(
                invariant_id=check["invariant_id"],
                gate_mode=check["gate_mode"],
                status=check["status"],
                task_refs=task_refs,
                title=check["title"],
            )
        )
    lines.append("")
    return "\n".join(lines)


def _check_no_active_tracked_node_modules(repo_root: Path) -> AuditEvaluation:
    tracked = set(_git_lines(repo_root, "ls-files"))
    deleted = set(_git_lines(repo_root, "ls-files", "--deleted"))
    active_tracked = [path for path in tracked if path not in deleted]
    offenders = [
        path
        for path in sorted(active_tracked)
        if "node_modules" in PurePosixPath(path).parts
    ]
    return AuditEvaluation(
        passed=not offenders,
        details={"offenders": offenders},
    )


def _check_cloudbuild_pr_skeleton(repo_root: Path) -> AuditEvaluation:
    path = repo_root / "cloudbuild.pr.yaml"
    if not path.exists():
        return AuditEvaluation(
            passed=False,
            details={"missing_path": "cloudbuild.pr.yaml"},
        )
    text = path.read_text(encoding="utf-8")
    forbidden = (
        "availableSecrets",
        "secretEnv",
        "OPENAI_API_KEY",
        "PRODUCTION_DB_URL",
        "ONETRUTH_ARTIFACT_ROOT",
        "gcloud run",
        "gcloud deploy",
        "kubectl",
        "terraform",
        "firebase deploy",
    )
    required = (
        "python3 scripts/validate_repo.py",
        "make schema-validate",
    )
    violations = [item for item in forbidden if item in text]
    missing_required = [item for item in required if item not in text]
    return AuditEvaluation(
        passed=not violations and not missing_required,
        details={
            "forbidden_hits": violations,
            "missing_required_commands": missing_required,
        },
    )


def _check_artifact_storage_safety_source(repo_root: Path) -> AuditEvaluation:
    storage_text = (repo_root / "src/onetruth/infrastructure/artifacts/storage.py").read_text(
        encoding="utf-8"
    )
    route_text = (repo_root / "src/onetruth/api/routes/artifacts.py").read_text(
        encoding="utf-8"
    )
    handler_text = (repo_root / "src/onetruth/application/handlers/artifacts.py").read_text(
        encoding="utf-8"
    )
    download_body = route_text.split("def _download_artifact_for_context", 1)[-1]
    route_order_ok = (
        "artifact = show_artifact_version_command" in download_body
        and "scoped_workflow_run(connection, context" in download_body
        and "download_artifact_blob_command(" in download_body
        and download_body.index("artifact = show_artifact_version_command")
        < download_body.index("scoped_workflow_run(connection, context")
        < download_body.index("download_artifact_blob_command(")
    )
    required_markers = {
        "storage_root_error": "ArtifactStorageRootError" in storage_text,
        "write_root_check": "_require_under_root(target, root)" in storage_text,
        "read_root_check": "storage_root: Path | None = None" in storage_text
        and "_require_under_root(path, storage_root.expanduser().resolve())" in storage_text,
        "handler_root_pass": "read_blob(storage_uri, storage_root=storage_root)" in handler_text,
        "api_db_root_pass": "storage_root=storage_root_for_db_url(db_url)" in route_text,
        "api_auth_before_read": route_order_ok,
        "shared_env_inmem_reject": "artifact_storage_forbidden" in route_text
        and "inmem://" in route_text,
    }
    missing = [key for key, present in required_markers.items() if not present]
    return AuditEvaluation(
        passed=not missing,
        details={"missing_markers": missing},
    )


def _check_command_transaction_source(repo_root: Path) -> AuditEvaluation:
    boundary_text = (
        repo_root / "src/onetruth/application/handlers/_shared/command_boundary.py"
    ).read_text(encoding="utf-8")
    schedule_text = (
        repo_root / "src/onetruth/application/handlers/schedule_control.py"
    ).read_text(encoding="utf-8")
    handoff_text = (
        repo_root / "src/onetruth/application/handlers/logistics_handoff.py"
    ).read_text(encoding="utf-8")
    required_markers = {
        "helper_exists": "def command_transaction(" in boundary_text,
        "savepoint_support": "SAVEPOINT" in boundary_text,
        "schedule_uses_helper": "with command_transaction(connection):" in schedule_text,
        "handoff_uses_helper": "with command_transaction(connection):" in handoff_text,
        "schedule_no_local_begin": 'connection.execute("BEGIN' not in schedule_text,
        "handoff_no_local_begin": 'connection.execute("BEGIN' not in handoff_text,
    }
    missing = [key for key, present in required_markers.items() if not present]
    return AuditEvaluation(
        passed=not missing,
        details={"missing_markers": missing},
    )


def _git_lines(repo_root: Path, *args: str) -> list[str]:
    result = subprocess.run(
        ["git", *args],
        cwd=repo_root,
        text=True,
        capture_output=True,
        check=False,
    )
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or f"git {' '.join(args)} failed")
    return [line for line in result.stdout.splitlines() if line]
