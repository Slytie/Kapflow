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
        invariant_id="capex.pr006.run_input_edge_helpers",
        title="Shared run/input/edge helpers and logistics resolver are present",
        gate_mode="hard_gate",
        task_refs=("TASK-0239",),
        description="Shared runtime effects and LogisticsRunResolver must reject activation-key drift.",
        evaluator=lambda repo_root: _check_run_input_edge_helper_source(repo_root),
    ),
    CapexInvariant(
        invariant_id="capex.pr007.platform_foundation_v0",
        title="Platform Foundation v0 declaration is recorded",
        gate_mode="hard_gate",
        task_refs=("TASK-0240",),
        description="PF0 branch-gate matrix must record allowed scope and blocked activation paths.",
        evaluator=lambda repo_root: _check_platform_foundation_v0_source(repo_root),
    ),
    CapexInvariant(
        invariant_id="capex.pr008.release_image_manifest",
        title="Release image build lane records digest manifest without deploy",
        gate_mode="hard_gate",
        task_refs=("TASK-0241",),
        description="Release build must produce API image evidence and release_manifest.json without deployment posture.",
        evaluator=lambda repo_root: _check_release_image_manifest_source(repo_root),
    ),
    CapexInvariant(
        invariant_id="capex.pr009.backup_manifest_skeleton",
        title="Predeploy backup manifest skeleton is validate-only",
        gate_mode="hard_gate",
        task_refs=("TASK-0242",),
        description="Backup skeleton must validate DB/artifact/release tuple without copying or restoring state.",
        evaluator=lambda repo_root: _check_backup_manifest_skeleton_source(repo_root),
    ),
    CapexInvariant(
        invariant_id="capex.pr010.lab_auth_smoke",
        title="Lab-only shared-env JWT viewer smoke is present",
        gate_mode="hard_gate",
        task_refs=("TASK-0243",),
        description="Lab auth smoke must use the existing RS256 shared_env resolver and reject browser-header identity spoofing.",
        evaluator=lambda repo_root: _check_lab_auth_smoke_source(repo_root),
    ),
    CapexInvariant(
        invariant_id="capex.pr011.lab_vm_deploy_pipeline",
        title="Lab VM deploy pipeline is implemented and live evidence remains explicit",
        gate_mode="hard_gate",
        task_refs=("TASK-0244",),
        description="Lab deploy lane must be operator-gated, GCP VM only, and distinguish implementation from live execute-and-smoke evidence.",
        evaluator=lambda repo_root: _check_lab_vm_deploy_pipeline_source(repo_root),
    ),
    CapexInvariant(
        invariant_id="capex.clean001.approval_response_hooks_domain_neutral",
        title="Approval response side effects are explicit domain hooks",
        gate_mode="hard_gate",
        task_refs=("TASK-0257", "TASK-0561", "TASK-0576", "TASK-0643"),
        description="Generic approval.response records only the approval transition/event and invokes registered domain hooks for logistics effects.",
        evaluator=lambda repo_root: _check_approval_response_hook_source(repo_root),
    ),
    CapexInvariant(
        invariant_id="capex.clean002.workpage_defaults_domain_neutral",
        title="Workpage defaults are neutral with explicit logistics activation",
        gate_mode="hard_gate",
        task_refs=("TASK-0258", "TASK-0561", "TASK-0643"),
        description="Generic workpage descriptor/action defaults must not import logistics packs; logistics workpages activate their packs explicitly.",
        evaluator=lambda repo_root: _check_workpage_default_registry_source(repo_root),
    ),
    CapexInvariant(
        invariant_id="capex.nu008.semantic_tests_codeowners",
        title="CAPEX semantic test suite and CODEOWNERS gate are active",
        gate_mode="hard_gate",
        task_refs=("TASK-0568",),
        description="CAPEX semantic tests must have a marker, focused Make/CI lane, CB2 backlog manifest, and real-owner CODEOWNERS entries.",
        evaluator=lambda repo_root: _check_capex_semantic_gate_source(repo_root),
    ),
    CapexInvariant(
        invariant_id="capex.nu009.interface_burden_conserved",
        title="Interface burden conservation policy is present",
        gate_mode="hard_gate",
        task_refs=("TASK-0569",),
        description="Interface obligations must be owned, transferred, waived, accepted residual, or open with a traceable follow-up.",
        evaluator=lambda repo_root: _check_capex_interface_burden_source(repo_root),
    ),
    CapexInvariant(
        invariant_id="capex.redteam.workpage_command_activation_idempotency",
        title="Workpage command activation and idempotency fail closed",
        gate_mode="hard_gate",
        task_refs=("TASK-0237", "TASK-0567", "TASK-0568"),
        description="Internal CAPEX workpage command dispatch must require active policy and replay command receipts before handler effects.",
        evaluator=lambda repo_root: _check_capex_workpage_command_guardrails(repo_root),
    ),
    CapexInvariant(
        invariant_id="capex.redteam.project_security_probe_coverage",
        title="Project security red-team probes are first-class regressions",
        gate_mode="hard_gate",
        task_refs=("TASK-0237", "TASK-0265", "TASK-0564", "TASK-0568"),
        description="Revocation, artifact identity, provenance, SourceRef, and pointer isolation probes must live in focused tests.",
        evaluator=lambda repo_root: _check_capex_project_security_probe_coverage(repo_root),
    ),
    CapexInvariant(
        invariant_id="capex.known_gap.capex_activation_downstream_governance",
        title="CAPEX activation and downstream governance gates",
        gate_mode="known_gap",
        task_refs=("TASK-0263", "TASK-0385", "TASK-0386", "TASK-0387", "TASK-0388", "TASK-0389", "TASK-0390", "TASK-0563", "TASK-0566", "TASK-0567"),
        description="The durable project anchor, direct memberships, first project child APIs, selector/dashboard slice, project-scope helper, official pointer-family substrate, domain manifests, approval-effect registry shadow parity, project authorization CED, projection-backed AuthorizedProjectsQuery, physical authorization projection runtime state, storage/blob custody CED, pilot storage gate checklist, W1 code pattern register, W1 closeout review, handoff manifest foundation, projection stale-command foundation, and internal workpage command activation/idempotency guards exist, but pointer-promotion policy checks, real pilot storage evidence or waiver, source governance dependencies, authored CAPEX workflow packs, public CAPEX workpages, and activation remain blocked.",
    ),
    CapexInvariant(
        invariant_id="capex.known_gap.source_occurrence_sourceref",
        title="Broader source governance and evidence binding",
        gate_mode="known_gap",
        task_refs=("TASK-0268", "TASK-0391", "TASK-0407", "TASK-0428", "TASK-0564", "TASK-0578"),
        description="TASK-0564 adds physical source occurrence truth and the first SourceRef resolver; broader corpus ingest, source occurrence relation/locator work, extraction, and evidence binding remain future scope.",
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


def _check_run_input_edge_helper_source(repo_root: Path) -> AuditEvaluation:
    helper_text = (
        repo_root / "src/onetruth/application/handlers/_shared/runtime_effects.py"
    ).read_text(encoding="utf-8")
    resolver_text = (
        repo_root / "src/onetruth/application/services/logistics_run_resolver.py"
    ).read_text(encoding="utf-8")
    handoff_text = (
        repo_root / "src/onetruth/application/handlers/logistics_handoff.py"
    ).read_text(encoding="utf-8")
    test_text = (repo_root / "tests/unit/test_runtime_effect_helpers.py").read_text(
        encoding="utf-8"
    )
    required_markers = {
        "run_helper": "def resolve_or_create_workflow_run_effects(" in helper_text,
        "input_helper": "def create_or_validate_workflow_artifact_input_effects(" in helper_text,
        "edge_helper": "def create_or_reuse_edge_execution_effects(" in helper_text,
        "activation_drift_error": "activation_key_drift_detected" in helper_text,
        "edge_replay_conflict": "edge_execution_replay_conflict" in helper_text,
        "resolver_class": "class LogisticsRunResolver" in resolver_text,
        "handoff_uses_resolver": "_LOGISTICS_RUN_RESOLVER.resolve_or_create" in handoff_text,
        "handoff_uses_input_helper": "create_or_validate_workflow_artifact_input_effects(" in handoff_text,
        "handoff_uses_edge_helper": "create_or_reuse_edge_execution_effects(" in handoff_text,
        "helper_tests": "test_edge_execution_helper_reuses_correlation" in test_text,
    }
    missing = [key for key, present in required_markers.items() if not present]
    return AuditEvaluation(
        passed=not missing,
        details={"missing_markers": missing},
    )


def _check_platform_foundation_v0_source(repo_root: Path) -> AuditEvaluation:
    path = repo_root / "docs/planning/CAPEX_PLATFORM_FOUNDATION_V0.md"
    if not path.exists():
        return AuditEvaluation(
            passed=False,
            details={"missing_path": "docs/planning/CAPEX_PLATFORM_FOUNDATION_V0.md"},
        )
    text = path.read_text(encoding="utf-8")
    required = (
        "DECLARED_FOR_REPO_PLATFORM_READINESS",
        "PR000",
        "PR001",
        "PR002",
        "PR003",
        "PR004",
        "PR005",
        "PR006",
        "PR007",
        "foundation/ip5",
        "CAPEX production activation and pilot readiness claims remain blocked",
        "Raw K12, K3, and blind-validation corpus files",
        "Release/deploy work",
        "CAPEX project child APIs, authorization projections",
        "Source occurrence and SourceRef runtime foundation is present",
        "external/operator-managed",
    )
    missing = [item for item in required if item not in text]
    return AuditEvaluation(
        passed=not missing,
        details={"missing_markers": missing},
    )


def _check_release_image_manifest_source(repo_root: Path) -> AuditEvaluation:
    dockerfile_text = (repo_root / "Dockerfile").read_text(encoding="utf-8")
    build_script_text = (repo_root / "scripts/build_release_image.py").read_text(
        encoding="utf-8"
    )
    schema_text = (
        repo_root / "schemas/release/release_manifest.schema.json"
    ).read_text(encoding="utf-8")
    makefile_text = (repo_root / "Makefile").read_text(encoding="utf-8")
    deploy_runbook = (
        repo_root / "docs/ops/runbooks/rollback_and_deploy.md"
    ).read_text(encoding="utf-8")
    test_text = (repo_root / "tests/unit/test_release_image_build.py").read_text(
        encoding="utf-8"
    )
    required_markers = {
        "dockerfile_api_runtime": "onetruth-api" in dockerfile_text
        and "ONETRUTH_API_BOUNDARY_PROFILE=shared_env" in dockerfile_text,
        "dockerfile_no_secret": "OPENAI_API_KEY" not in dockerfile_text
        and "PRODUCTION_DB_URL" not in dockerfile_text,
        "script_exists": "def build_release_image(" in build_script_text,
        "script_push_capable": '"push"' in build_script_text
        and "registry_push" in build_script_text,
        "script_no_deploy_manifest": '"performed": False' in build_script_text,
        "schema_exists": '"release.image.build"' in schema_text
        and '"digest_ref"' in schema_text,
        "make_target": "release-image:" in makefile_text
        and "scripts/build_release_image.py" in makefile_text,
        "runbook_boundary": "release_source_bundle remains the only deploy input"
        in deploy_runbook
        and "not deployment approval" in deploy_runbook,
        "tests_exist": "test_release_image_push_records_registry_digest" in test_text,
    }
    missing = [key for key, present in required_markers.items() if not present]
    return AuditEvaluation(
        passed=not missing,
        details={"missing_markers": missing},
    )


def _check_backup_manifest_skeleton_source(repo_root: Path) -> AuditEvaluation:
    backup_script_text = (
        repo_root / "scripts/prepare_predeploy_backup.py"
    ).read_text(encoding="utf-8")
    schema_text = (repo_root / "schemas/ops/backup_manifest.schema.json").read_text(
        encoding="utf-8"
    )
    makefile_text = (repo_root / "Makefile").read_text(encoding="utf-8")
    backup_runbook = (
        repo_root / "docs/ops/runbooks/backup_and_restore.md"
    ).read_text(encoding="utf-8")
    test_text = (
        repo_root / "tests/unit/test_predeploy_backup_manifest.py"
    ).read_text(encoding="utf-8")
    required_markers = {
        "script_exists": "def prepare_predeploy_backup_manifest(" in backup_script_text,
        "script_validate_only": '"validate_only"' in backup_script_text
        and '"state_copy_performed": False' in backup_script_text
        and '"restore_proof": False' in backup_script_text,
        "script_secret_refs_only": "_validate_secret_refs" in backup_script_text
        and "not a secret value" in backup_script_text,
        "schema_exists": '"predeploy.backup_manifest.prepare"' in schema_text
        and '"state_copy_performed"' in schema_text,
        "make_target": "predeploy-backup-manifest:" in makefile_text
        and "scripts/prepare_predeploy_backup.py" in makefile_text,
        "runbook_boundary": "validation-only predeploy backup skeleton" in backup_runbook
        and "does not copy live state" in backup_runbook
        and "not restore proof" in backup_runbook,
        "tests_exist": "test_predeploy_backup_manifest_validates_tuple_without_copying_state"
        in test_text,
    }
    missing = [key for key, present in required_markers.items() if not present]
    return AuditEvaluation(
        passed=not missing,
        details={"missing_markers": missing},
    )


def _check_lab_auth_smoke_source(repo_root: Path) -> AuditEvaluation:
    script_text = (repo_root / "scripts/run_lab_auth_smoke.py").read_text(
        encoding="utf-8"
    )
    schema_text = (
        repo_root / "schemas/ops/lab_auth_smoke_report.schema.json"
    ).read_text(encoding="utf-8")
    makefile_text = (repo_root / "Makefile").read_text(encoding="utf-8")
    runbook_text = (
        repo_root / "docs/ops/runbooks/lab_auth_and_vm_deploy.md"
    ).read_text(encoding="utf-8")
    test_text = (repo_root / "tests/unit/test_lab_auth_smoke.py").read_text(
        encoding="utf-8"
    )
    required_markers = {
        "script_exists": "def run_lab_auth_smoke(" in script_text,
        "uses_existing_resolver": "build_shared_env_jwt_principal_resolver" in script_text,
        "viewer_smoke": 'path="/api/v1/viewer"' in script_text,
        "spoof_assertion": "spoofed_headers_ignored" in script_text,
        "no_token_record": '"token_value_recorded": False' in script_text,
        "schema_exists": '"lab.auth.smoke"' in schema_text
        and '"token_value_recorded"' in schema_text,
        "make_target": "lab-auth-smoke:" in makefile_text
        and "scripts/run_lab_auth_smoke.py" in makefile_text,
        "runbook_boundary": "existing `shared_env` RS256 JWT resolver" in runbook_text
        and "does not add JWKS" in runbook_text
        and "must not print or persist bearer token values" in runbook_text,
        "tests_exist": "test_lab_auth_smoke_accepts_jwt" in test_text
        and "test_lab_auth_smoke_reports_invalid_bearer_token" in test_text,
    }
    missing = [key for key, present in required_markers.items() if not present]
    return AuditEvaluation(
        passed=not missing,
        details={"missing_markers": missing},
    )


def _check_approval_response_hook_source(repo_root: Path) -> AuditEvaluation:
    approvals_text = (
        repo_root / "src/onetruth/application/handlers/approvals.py"
    ).read_text(encoding="utf-8")
    approvals_route_text = (
        repo_root / "src/onetruth/api/routes/approvals.py"
    ).read_text(encoding="utf-8")
    hook_registry_text = (
        repo_root / "src/onetruth/application/services/approval_response_hooks.py"
    ).read_text(encoding="utf-8")
    logistics_hook_text = (
        repo_root / "src/onetruth/application/services/logistics_approval_response_hooks.py"
    ).read_text(encoding="utf-8")
    boundary_test_text = (
        repo_root / "tests/contract/test_handler_import_boundaries.py"
    ).read_text(encoding="utf-8")
    unit_test_text = (
        repo_root / "tests/unit/test_approval_response_hooks.py"
    ).read_text(encoding="utf-8")
    respond_body = approvals_text.split("def respond_approval_command", 1)[-1]
    forbidden_generic_markers = (
        "notify_only_handoff_command",
        "dispatch_reporting_build",
        "DISPATCH_REPORTING_WORKFLOW_ID",
        "WEEKLY_WORKFLOW_ID",
        "_maybe_auto_publish_weekly_approval",
        "_maybe_finalize_dispatch_reporting_approval",
        "_create_artifact_version_effects",
        "_promote_pointer_effects",
        "weekly-publish.",
        "dispatch-reporting.final-packet.",
    )
    generic_hits = [
        marker for marker in forbidden_generic_markers if marker in approvals_text
    ]
    hook_registry_forbidden_hits = [
        marker
        for marker in (
            "LOGISTICS_APPROVAL_RESPONSE_HOOKS",
            "logistics_approval_response_hooks",
            "weekly_publish_approval_hook",
            "dispatch_reporting_finalize_approval_hook",
        )
        if marker in hook_registry_text
    ]
    required_markers = {
        "handler_runs_registry": "run_registered_approval_response_hooks(" in respond_body
        and "ApprovalResponseHookContext(" in respond_body,
        "handler_no_direct_logistics": not generic_hits,
        "handler_accepts_explicit_hooks": "approval_response_hooks:" in respond_body
        and "hooks=approval_response_hooks" in respond_body,
        "generic_registry_neutral": "DEFAULT_APPROVAL_RESPONSE_HOOKS" in hook_registry_text
        and "ApprovalResponseHookContext" in hook_registry_text
        and "DEFAULT_APPROVAL_RESPONSE_HOOKS: tuple[ApprovalResponseHook, ...] = ()"
        in hook_registry_text
        and not hook_registry_forbidden_hits,
        "logistics_hooks_registered": "LOGISTICS_APPROVAL_RESPONSE_HOOKS" in logistics_hook_text
        and "weekly_publish_approval_hook" in logistics_hook_text
        and "dispatch_reporting_finalize_approval_hook" in logistics_hook_text
        and "logistics_approval_response_hooks_for_workflow" in logistics_hook_text,
        "api_activates_logistics_hooks_explicitly": "approval_response_hooks=logistics_approval_response_hooks_for_workflow("
        in approvals_route_text,
        "boundary_test_exists": "test_approval_respond_side_effects_are_registered_domain_hooks"
        in boundary_test_text,
        "unit_tests_exist": "test_default_approval_response_hooks_are_platform_neutral"
        in unit_test_text
        and "test_logistics_approval_response_hooks_are_explicitly_selected_by_workflow"
        in unit_test_text
        and "test_logistics_approval_hooks_ignore_non_approved_responses_before_db_reads"
        in unit_test_text,
    }
    missing = [key for key, present in required_markers.items() if not present]
    return AuditEvaluation(
        passed=not missing,
        details={
            "missing_markers": missing,
            "generic_handler_forbidden_hits": generic_hits,
            "generic_registry_forbidden_hits": hook_registry_forbidden_hits,
        },
    )


def _check_workpage_default_registry_source(repo_root: Path) -> AuditEvaluation:
    descriptor_defaults_text = (
        repo_root
        / "src/onetruth/application/services/workpage_descriptor_registry_defaults.py"
    ).read_text(encoding="utf-8")
    action_defaults_text = (
        repo_root
        / "src/onetruth/application/services/workpage_action_registry_defaults.py"
    ).read_text(encoding="utf-8")
    projection_text = (
        repo_root / "src/onetruth/application/services/workpage_action_projection.py"
    ).read_text(encoding="utf-8")
    action_resolution_text = (
        repo_root / "src/onetruth/application/handlers/workpage_action_resolution.py"
    ).read_text(encoding="utf-8")
    logistics_descriptor_text = (
        repo_root / "src/onetruth/application/services/logistics_workpage_descriptors.py"
    ).read_text(encoding="utf-8")
    logistics_action_text = (
        repo_root
        / "src/onetruth/application/services/logistics_workpage_action_registry.py"
    ).read_text(encoding="utf-8")
    workflow_runs_route_text = (
        repo_root / "src/onetruth/api/routes/workflow_runs.py"
    ).read_text(encoding="utf-8")
    human_tasks_route_text = (
        repo_root / "src/onetruth/api/routes/human_tasks.py"
    ).read_text(encoding="utf-8")
    workpages_route_text = (
        repo_root / "src/onetruth/api/routes/workpages.py"
    ).read_text(encoding="utf-8")
    boundary_test_text = (
        repo_root / "tests/contract/test_handler_import_boundaries.py"
    ).read_text(encoding="utf-8")
    descriptor_unit_test_text = (
        repo_root / "tests/unit/test_workpage_descriptor_registry.py"
    ).read_text(encoding="utf-8")
    action_unit_test_text = (
        repo_root / "tests/unit/test_workpage_domain_registry.py"
    ).read_text(encoding="utf-8")
    descriptor_default_forbidden_hits = [
        marker
        for marker in (
            "LOGISTICS_WORKPAGE_DESCRIPTOR_PACK",
            "logistics_workpage",
            "schedule-v0",
            "eod-v0",
        )
        if marker in descriptor_defaults_text
    ]
    action_default_forbidden_hits = [
        marker
        for marker in (
            "LOGISTICS_WORKPAGE_ACTION_PACK",
            "logistics_workpage",
            "schedule-v0",
            "eod-v0",
        )
        if marker in action_defaults_text
    ]
    required_markers = {
        "descriptor_default_neutral": "DEFAULT_WORKPAGE_DESCRIPTOR_REGISTRY"
        in descriptor_defaults_text
        and "WorkpageDescriptorRegistry()" in descriptor_defaults_text
        and not descriptor_default_forbidden_hits,
        "action_default_neutral": "DEFAULT_WORKPAGE_ACTION_REGISTRY"
        in action_defaults_text
        and "WorkpageActionRegistry()" in action_defaults_text
        and not action_default_forbidden_hits,
        "projection_accepts_explicit_registry": "registry: WorkpageActionRegistry | None = None"
        in projection_text
        and "active_registry = DEFAULT_WORKPAGE_ACTION_REGISTRY if registry is None else registry"
        in projection_text,
        "resolution_accepts_explicit_registries": "action_registry: WorkpageActionRegistry | None = None"
        in action_resolution_text
        and "descriptor_registry: WorkpageDescriptorRegistry | None = None"
        in action_resolution_text
        and "_active_action_registry(action_registry).supports_human_task_subject("
        in action_resolution_text
        and "_active_descriptor_registry(descriptor_registry).require_descriptor("
        in action_resolution_text,
        "logistics_descriptor_factory_exists": "LOGISTICS_WORKPAGE_DESCRIPTOR_PACK"
        in logistics_descriptor_text
        and "def logistics_workpage_descriptor_registry()" in logistics_descriptor_text,
        "logistics_action_factory_exists": "LOGISTICS_WORKPAGE_ACTION_PACK"
        in logistics_action_text
        and "def logistics_workpage_action_registry()" in logistics_action_text
        and "def logistics_workpage_action_registry_for_workflow(" in logistics_action_text,
        "api_routes_activate_logistics_explicitly": "logistics_workpage_action_registry_for_workflow("
        in workflow_runs_route_text
        and "logistics_workpage_action_registry_for_workflow(" in human_tasks_route_text
        and "logistics_workpage_descriptor_registry().descriptor_for_public_run("
        in workpages_route_text,
        "tests_invert_defaults": "test_default_descriptor_registry_is_platform_neutral"
        in descriptor_unit_test_text
        and "test_default_action_registry_is_platform_neutral" in action_unit_test_text
        and "test_logistics_action_registry_is_explicitly_selected_by_workflow"
        in action_unit_test_text
        and "LOGISTICS_WORKPAGE_DESCRIPTOR_PACK\" not in descriptor_defaults_text"
        in boundary_test_text
        and "LOGISTICS_WORKPAGE_ACTION_PACK\" not in action_defaults_text"
        in boundary_test_text,
    }
    missing = [key for key, present in required_markers.items() if not present]
    return AuditEvaluation(
        passed=not missing,
        details={
            "missing_markers": missing,
            "descriptor_default_forbidden_hits": descriptor_default_forbidden_hits,
            "action_default_forbidden_hits": action_default_forbidden_hits,
        },
    )


def _check_lab_vm_deploy_pipeline_source(repo_root: Path) -> AuditEvaluation:
    script_text = (repo_root / "scripts/deploy_lab_vm.py").read_text(
        encoding="utf-8"
    )
    schema_text = (
        repo_root / "schemas/ops/lab_vm_deploy_report.schema.json"
    ).read_text(encoding="utf-8")
    makefile_text = (repo_root / "Makefile").read_text(encoding="utf-8")
    runbook_text = (
        repo_root / "docs/ops/runbooks/lab_auth_and_vm_deploy.md"
    ).read_text(encoding="utf-8")
    test_text = (repo_root / "tests/unit/test_lab_vm_deploy.py").read_text(
        encoding="utf-8"
    )
    required_markers = {
        "script_exists": "def deploy_lab_vm(" in script_text
        and "def plan_lab_vm_deploy(" in script_text,
        "lab_only": 'choices=["lab"]' in script_text
        and "supports --environment lab only" in script_text,
        "operator_confirmations": "--confirm-lab-target" in script_text
        and "--confirm-no-real-users" in script_text,
        "gcp_vm_only": '"compute"' in script_text
        and '"scp"' in script_text
        and '"ssh"' in script_text
        and "allowed_gcloud_compute_subcommands" in script_text,
        "backup_and_smoke": "prepare_predeploy_backup.py" in script_text
        and "/api/v1/ops/health" in script_text
        and "/api/v1/ops/readiness" in script_text
        and "/api/v1/viewer" in script_text,
        "live_evidence_distinction": "live_deploy_evidence_recorded" in script_text
        and "live_deploy_evidence_required_for_task_done" in script_text,
        "schema_exists": '"lab.vm.deploy"' in schema_text
        and '"live_deploy_evidence_recorded"' in schema_text,
        "make_targets": "lab-vm-deploy-plan:" in makefile_text
        and "lab-vm-deploy:" in makefile_text
        and "scripts/deploy_lab_vm.py" in makefile_text,
        "runbook_boundary": "lab-only VM lane" in runbook_text
        and "actual operator-supplied lab VM execute-and-smoke evidence" in runbook_text
        and "not CAPEX activation" in runbook_text,
        "tests_exist": "test_lab_vm_deploy_execute_runs_gcloud_commands_in_order"
        in test_text
        and "test_lab_vm_deploy_rejects_non_lab_or_production_targets" in test_text,
    }
    missing = [key for key, present in required_markers.items() if not present]
    return AuditEvaluation(
        passed=not missing,
        details={
            "missing_markers": missing,
            "pipeline_implemented": not missing,
            "live_deploy_evidence_recorded": False,
            "task_closeout_status": "BLOCKED_PENDING_LIVE_GCP_EVIDENCE",
        },
    )


def _check_capex_semantic_gate_source(repo_root: Path) -> AuditEvaluation:
    pytest_text = (repo_root / "pytest.ini").read_text(encoding="utf-8")
    makefile_text = (repo_root / "Makefile").read_text(encoding="utf-8")
    workflow_text = (repo_root / ".github/workflows/main.yml").read_text(
        encoding="utf-8"
    )
    codeowners_text = (repo_root / ".github/CODEOWNERS").read_text(encoding="utf-8")
    marker_text = (repo_root / "tests/helpers/suite_markers.py").read_text(
        encoding="utf-8"
    )
    conftest_text = (repo_root / "tests/conftest.py").read_text(encoding="utf-8")
    manifest_text = (
        repo_root / "docs/planning/CAPEX_CB2_SEMANTIC_TEST_BACKLOG.yaml"
    ).read_text(encoding="utf-8")
    semantic_test_text = (
        repo_root / "tests/contract/test_capex_semantic_test_suite.py"
    ).read_text(encoding="utf-8")
    codeowners_test_text = (
        repo_root / "tests/contract/test_capex_semantic_codeowners_gates.py"
    ).read_text(encoding="utf-8")
    required_markers = {
        "pytest_marker": "capex_semantic:" in pytest_text,
        "make_lane": "capex-semantic-tests:" in makefile_text
        and "-m capex_semantic tests/contract tests/unit" in makefile_text,
        "workflow_lane": "capex-semantic-tests" in workflow_text
        and "make PYTHON=python capex-semantic-tests" in workflow_text,
        "marker_manifest": "CAPEX_SEMANTIC_TEST_GLOBS" in marker_text
        and "def is_capex_semantic_test_path(" in marker_text
        and "pytest.mark.capex_semantic" in conftest_text,
        "cb2_manifest": "CB2-T001" in manifest_text
        and "CB2-T014" in manifest_text
        and "tracking_only_no_capex_activation" in manifest_text
        and "repo_evidence_green" in manifest_text
        and "tracked_future_phase" in manifest_text,
        "codeowners_paths": "/docs/planning/CAPEX_CB2_SEMANTIC_TEST_BACKLOG.yaml"
        in codeowners_text
        and "/tests/contract/test_capex_semantic_test_suite.py" in codeowners_text
        and "@tylerclark" in codeowners_text,
        "contract_tests": "test_capex_cb2_semantic_backlog_tracks_all_rows_in_order"
        in semantic_test_text
        and "test_main_workflow_exposes_capex_semantic_grouping"
        in codeowners_test_text,
    }
    missing = [key for key, present in required_markers.items() if not present]
    return AuditEvaluation(
        passed=not missing,
        details={"missing_markers": missing},
    )


def _check_capex_interface_burden_source(repo_root: Path) -> AuditEvaluation:
    source_text = (
        repo_root / "src/onetruth/capex_platform/interface_burden.py"
    ).read_text(encoding="utf-8")
    doc_text = (
        repo_root / "docs/architecture/CAPEX_INTERFACE_BURDEN_POLICY.md"
    ).read_text(encoding="utf-8")
    unit_test_text = (
        repo_root / "tests/unit/test_capex_interface_burden_policy.py"
    ).read_text(encoding="utf-8")
    contract_test_text = (
        repo_root / "tests/contract/test_capex_interface_burden_policy_doc.py"
    ).read_text(encoding="utf-8")
    required_markers = {
        "states": all(
            marker in source_text
            for marker in (
                "owned",
                "transferred",
                "waived",
                "accepted_residual",
                "open",
            )
        ),
        "validator": "def validate_interface_burden(" in source_text
        and "missing_traceable_basis_refs" in source_text
        and "def require_interface_burden_conserved(" in source_text,
        "follow_up_specs": "InterfaceBurdenFollowUpTask" in source_text
        and "capex.interface_transfer_acceptance" in source_text,
        "doc_boundary": "Interface responsibility must not disappear" in doc_text
        and "does not create a second task system" in doc_text
        and "CAPEX runtime activation disabled" in doc_text,
        "tests_exist": "test_transfer_creates_deterministic_acceptance_follow_up_without_mutating_runtime"
        in unit_test_text
        and "test_capex_interface_burden_policy_records_conservation_states"
        in contract_test_text,
    }
    missing = [key for key, present in required_markers.items() if not present]
    return AuditEvaluation(
        passed=not missing,
        details={"missing_markers": missing},
    )


def _check_capex_workpage_command_guardrails(repo_root: Path) -> AuditEvaluation:
    source_text = (
        repo_root / "src/onetruth/capex_platform/workpage_projection_commands.py"
    ).read_text(encoding="utf-8")
    test_text = (
        repo_root / "tests/unit/test_capex_workpage_command_envelope.py"
    ).read_text(encoding="utf-8")
    execute_body = source_text.split("def execute_guarded_workpage_command", 1)[-1]
    receipt_body = source_text.split("def _execute_with_workpage_command_receipt", 1)[-1]
    receipt_lookup_before_operation = (
        "get_command_receipt(" in receipt_body
        and "result = operation()" in receipt_body
        and receipt_body.index("get_command_receipt(")
        < receipt_body.index("result = operation()")
    )
    required_markers = {
        "activation_contract": "class WorkpageCommandActivation" in source_text
        and "WORKPAGE_COMMAND_DISPATCH_POLICY" in source_text
        and "activation: WorkpageCommandActivation" in execute_body,
        "activation_disabled_error": "workpage_command_activation_disabled" in source_text,
        "activation_policy_error": "workpage_command_activation_policy_mismatch" in source_text,
        "receipt_store": "WORKPAGE_COMMAND_RECEIPT_NAME" in source_text
        and "capex.workpages.command-envelope.execute" in source_text
        and "create_command_receipt(" in source_text,
        "receipt_lookup_before_operation": receipt_lookup_before_operation,
        "receipt_mismatch_error": "workpage_command_receipt_mismatch" in source_text,
        "activation_tests": "test_workpage_command_activation_fails_closed_before_operation"
        in test_text,
        "idempotency_tests": "test_workpage_command_idempotency_replays_receipt_without_handler_reentry"
        in test_text
        and "test_workpage_command_same_idempotency_key_with_changed_payload_fails_closed"
        in test_text,
    }
    missing = [key for key, present in required_markers.items() if not present]
    return AuditEvaluation(
        passed=not missing,
        details={"missing_markers": missing},
    )


def _check_capex_project_security_probe_coverage(repo_root: Path) -> AuditEvaluation:
    authorized_text = (
        repo_root / "tests/unit/test_capex_authorized_projects_query.py"
    ).read_text(encoding="utf-8")
    access_api_text = (
        repo_root / "tests/runtime/api/test_capex_project_access_api.py"
    ).read_text(encoding="utf-8")
    pointer_unit_text = (
        repo_root / "tests/unit/test_capex_official_pointer_families.py"
    ).read_text(encoding="utf-8")
    pointer_api_text = (
        repo_root / "tests/runtime/api/test_capex_project_official_pointer_api.py"
    ).read_text(encoding="utf-8")
    provenance_text = (
        repo_root / "tests/unit/test_artifact_provenance_dag.py"
    ).read_text(encoding="utf-8")
    source_ref_text = (
        repo_root / "tests/unit/test_capex_source_occurrence_resolver.py"
    ).read_text(encoding="utf-8")
    required_markers = {
        "revocation_projection_stale_unit": "test_authorized_projects_query_fails_closed_when_projection_is_stale_after_revocation"
        in authorized_text
        and "test_revoke_then_regrant_uses_live_direct_membership_role" in authorized_text
        and "test_authorized_projects_visibility_sql_preserves_no_project_rows"
        in authorized_text,
        "revocation_api": "test_capex_project_membership_revoke_api_fails_closed_without_refresh_gap"
        in access_api_text,
        "artifact_identity": "test_artifact_versions_capture_project_identity_and_reject_mismatch"
        in pointer_unit_text
        and "test_project_official_pointer_fails_closed_on_artifact_project_identity_mismatch"
        in pointer_unit_text,
        "provenance_isolation": "test_provenance_edges_persist_same_project_identity"
        in provenance_text
        and "test_provenance_edges_reject_cross_project_and_project_to_null_edges"
        in provenance_text,
        "source_ref_isolation": "test_same_digest_in_two_projects_creates_distinct_project_scoped_occurrences"
        in source_ref_text
        and "test_source_occurrence_relations_remain_inactive_until_same_project_policy_exists"
        in source_ref_text,
        "pointer_api_isolation": "test_capex_project_official_pointer_routes_promote_and_scope_snapshots"
        in pointer_api_text
        and "test_capex_project_official_pointer_route_fails_closed_on_artifact_project_mismatch"
        in pointer_api_text,
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
