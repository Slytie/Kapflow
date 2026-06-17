from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sys

from onetruth.application.services.capex_invariant_audit import (
    AuditEvaluation,
    CAPEX_INVARIANT_REGISTRY,
    CapexInvariant,
    _check_approval_response_hook_source,
    _check_capex_project_security_probe_coverage,
    _check_capex_workpage_command_guardrails,
    _check_workpage_default_registry_source,
    capex_invariant_audit_exit_code,
    run_capex_invariant_audit,
)

REPO_ROOT = Path(__file__).resolve().parents[2]
SRC_ROOT = REPO_ROOT / "src"


def test_capex_invariant_registry_has_expected_gate_modes() -> None:
    modes = {entry.gate_mode for entry in CAPEX_INVARIANT_REGISTRY}

    assert modes == {"hard_gate", "known_gap"}
    assert sum(1 for entry in CAPEX_INVARIANT_REGISTRY if entry.gate_mode == "hard_gate") == 16
    assert sum(1 for entry in CAPEX_INVARIANT_REGISTRY if entry.gate_mode == "known_gap") == 3
    assert all(entry.task_refs for entry in CAPEX_INVARIANT_REGISTRY)


def test_capex_invariant_audit_report_records_known_gaps_without_failing(
    tmp_path: Path,
) -> None:
    manifest = run_capex_invariant_audit(
        repo_root=REPO_ROOT,
        output_root=tmp_path / "audit",
        now_iso="2026-06-02T00:00:00Z",
    )

    assert manifest["status"] == "passed"
    assert capex_invariant_audit_exit_code(manifest) == 0
    assert manifest["summary"] == {
        "total": 19,
        "hard_gate_passed": 16,
        "hard_gate_failed": 0,
        "known_gaps": 3,
        "advisory": 0,
    }
    statuses = {check["invariant_id"]: check["status"] for check in manifest["checks"]}
    assert statuses["capex.clean001.approval_response_hooks_domain_neutral"] == "passed"
    assert statuses["capex.clean002.workpage_defaults_domain_neutral"] == "passed"
    assert statuses["capex.pr002.artifact_storage_root_confined"] == "passed"
    assert statuses["capex.pr006.run_input_edge_helpers"] == "passed"
    assert statuses["capex.pr007.platform_foundation_v0"] == "passed"
    assert statuses["capex.pr008.release_image_manifest"] == "passed"
    assert statuses["capex.pr009.backup_manifest_skeleton"] == "passed"
    assert statuses["capex.pr010.lab_auth_smoke"] == "passed"
    assert statuses["capex.pr011.lab_vm_deploy_pipeline"] == "passed"
    assert statuses["capex.nu008.semantic_tests_codeowners"] == "passed"
    assert statuses["capex.nu009.interface_burden_conserved"] == "passed"
    assert statuses["capex.redteam.workpage_command_activation_idempotency"] == "passed"
    assert statuses["capex.redteam.project_security_probe_coverage"] == "passed"
    details = {
        check["invariant_id"]: check["details"] for check in manifest["checks"]
    }
    assert details["capex.pr011.lab_vm_deploy_pipeline"][
        "live_deploy_evidence_recorded"
    ] is False
    assert details["capex.pr011.lab_vm_deploy_pipeline"][
        "task_closeout_status"
    ] == "BLOCKED_PENDING_LIVE_GCP_EVIDENCE"

    report_paths = manifest["report_paths"]
    json_report = Path(str(report_paths["json"]))
    markdown_report = Path(str(report_paths["markdown"]))
    assert json_report.exists()
    assert markdown_report.exists()
    assert json.loads(json_report.read_text(encoding="utf-8"))["status"] == "passed"
    assert "| capex.pr001.no_active_tracked_node_modules |" in markdown_report.read_text(
        encoding="utf-8"
    )


def test_capex_audit_rejects_default_logistics_approval_hooks(tmp_path: Path) -> None:
    repo_root = _minimal_audit_repo(tmp_path)
    _write_repo_file(
        repo_root,
        "src/onetruth/application/services/approval_response_hooks.py",
        """
from onetruth.application.services.logistics_approval_response_hooks import LOGISTICS_APPROVAL_RESPONSE_HOOKS
class ApprovalResponseHookContext: ...
DEFAULT_APPROVAL_RESPONSE_HOOKS = LOGISTICS_APPROVAL_RESPONSE_HOOKS
""",
    )

    evaluation = _check_approval_response_hook_source(repo_root)

    assert not evaluation.passed
    assert "generic_registry_neutral" in evaluation.details["missing_markers"]
    assert "LOGISTICS_APPROVAL_RESPONSE_HOOKS" in evaluation.details[
        "generic_registry_forbidden_hits"
    ]


def test_capex_audit_rejects_default_logistics_workpage_packs(tmp_path: Path) -> None:
    repo_root = _minimal_audit_repo(tmp_path)
    _write_repo_file(
        repo_root,
        "src/onetruth/application/services/workpage_descriptor_registry_defaults.py",
        """
from onetruth.application.services.logistics_workpage_descriptors import LOGISTICS_WORKPAGE_DESCRIPTOR_PACK
DEFAULT_WORKPAGE_DESCRIPTOR_REGISTRY = WorkpageDescriptorRegistry(packs=(LOGISTICS_WORKPAGE_DESCRIPTOR_PACK,))
""",
    )
    _write_repo_file(
        repo_root,
        "src/onetruth/application/services/workpage_action_registry_defaults.py",
        """
from onetruth.application.services.logistics_workpage_action_registry import LOGISTICS_WORKPAGE_ACTION_PACK
DEFAULT_WORKPAGE_ACTION_REGISTRY = WorkpageActionRegistry((LOGISTICS_WORKPAGE_ACTION_PACK,))
""",
    )

    evaluation = _check_workpage_default_registry_source(repo_root)

    assert not evaluation.passed
    assert "descriptor_default_neutral" in evaluation.details["missing_markers"]
    assert "action_default_neutral" in evaluation.details["missing_markers"]
    assert "LOGISTICS_WORKPAGE_DESCRIPTOR_PACK" in evaluation.details[
        "descriptor_default_forbidden_hits"
    ]
    assert "LOGISTICS_WORKPAGE_ACTION_PACK" in evaluation.details[
        "action_default_forbidden_hits"
    ]


def test_capex_audit_rejects_missing_workpage_command_activation_and_idempotency(
    tmp_path: Path,
) -> None:
    repo_root = _minimal_audit_repo(tmp_path)
    _write_repo_file(
        repo_root,
        "src/onetruth/capex_platform/workpage_projection_commands.py",
        """
def execute_guarded_workpage_command(connection, envelope, *, signing_key, now_iso, operation):
    snapshot = validate_workpage_command_envelope(connection, envelope, signing_key=signing_key, now_iso=now_iso)
    return operation(snapshot)
""",
    )
    _write_repo_file(
        repo_root,
        "tests/unit/test_capex_workpage_command_envelope.py",
        """
def test_valid_command_envelope_allows_mutation_callback(): pass
""",
    )

    evaluation = _check_capex_workpage_command_guardrails(repo_root)

    assert not evaluation.passed
    assert "activation_contract" in evaluation.details["missing_markers"]
    assert "receipt_lookup_before_operation" in evaluation.details["missing_markers"]
    assert "idempotency_tests" in evaluation.details["missing_markers"]


def test_capex_audit_rejects_missing_project_security_probe_tests(tmp_path: Path) -> None:
    repo_root = _minimal_audit_repo(tmp_path)
    for relative_path in (
        "tests/unit/test_capex_authorized_projects_query.py",
        "tests/runtime/api/test_capex_project_access_api.py",
        "tests/unit/test_capex_official_pointer_families.py",
        "tests/runtime/api/test_capex_project_official_pointer_api.py",
        "tests/unit/test_artifact_provenance_dag.py",
        "tests/unit/test_capex_source_occurrence_resolver.py",
    ):
        _write_repo_file(repo_root, relative_path, "def test_placeholder(): pass")

    evaluation = _check_capex_project_security_probe_coverage(repo_root)

    assert not evaluation.passed
    assert "revocation_projection_stale_unit" in evaluation.details["missing_markers"]
    assert "artifact_identity" in evaluation.details["missing_markers"]
    assert "source_ref_isolation" in evaluation.details["missing_markers"]


def test_capex_invariant_audit_fails_only_for_hard_gate_failure(tmp_path: Path) -> None:
    registry = (
        CapexInvariant(
            invariant_id="test.hard_failure",
            title="hard failure",
            gate_mode="hard_gate",
            task_refs=("TASK-0000",),
            description="test hard failure",
            evaluator=lambda _repo_root: AuditEvaluation(False, {"reason": "expected"}),
        ),
        CapexInvariant(
            invariant_id="test.known_gap",
            title="known gap",
            gate_mode="known_gap",
            task_refs=("TASK-0001",),
            description="test known gap",
        ),
    )

    manifest = run_capex_invariant_audit(
        repo_root=REPO_ROOT,
        output_root=tmp_path / "audit",
        now_iso="2026-06-02T00:00:00Z",
        registry=registry,
    )

    assert manifest["status"] == "failed"
    assert capex_invariant_audit_exit_code(manifest) == 1
    assert manifest["summary"]["hard_gate_failed"] == 1
    assert manifest["summary"]["known_gaps"] == 1


def test_capex_invariant_audit_cli_writes_json_and_markdown(tmp_path: Path) -> None:
    env = os.environ.copy()
    existing_pythonpath = env.get("PYTHONPATH")
    env["PYTHONPATH"] = (
        f"{SRC_ROOT}{os.pathsep}{existing_pythonpath}"
        if existing_pythonpath
        else str(SRC_ROOT)
    )
    result = subprocess.run(
        [
            sys.executable,
            "scripts/run_capex_invariant_audit.py",
            "--output-root",
            str(tmp_path / "audit"),
            "--json",
        ],
        cwd=REPO_ROOT,
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload["status"] == "passed"
    assert Path(payload["report_paths"]["json"]).exists()
    assert Path(payload["report_paths"]["markdown"]).exists()


def test_capex_platform_foundation_v0_doc_records_branch_gate_and_blocked_scopes() -> None:
    path = REPO_ROOT / "docs/planning/CAPEX_PLATFORM_FOUNDATION_V0.md"
    text = path.read_text(encoding="utf-8")

    for gate_id in ("PR000", "PR001", "PR002", "PR003", "PR004", "PR005", "PR006", "PR007"):
        assert gate_id in text
    assert "foundation/ip5" in text
    assert "CAPEX production activation and pilot readiness claims remain blocked" in text
    assert "Raw K12, K3, and blind-validation corpus files" in text
    assert "Release/deploy work" in text
    assert "CAPEX project child APIs, authorization projections" in text
    assert "Source occurrence and SourceRef runtime foundation is present" in text
    assert "external/operator-managed" in text


def _minimal_audit_repo(tmp_path: Path) -> Path:
    repo_root = tmp_path / "repo"
    files = {
        "src/onetruth/application/handlers/approvals.py": """
def respond_approval_command(
    connection,
    payload,
    *,
    approval_response_hooks=None,
):
    run_registered_approval_response_hooks(
        ApprovalResponseHookContext(),
        hooks=approval_response_hooks,
    )
""",
        "src/onetruth/api/routes/approvals.py": """
updated = respond_approval_command(
    connection,
    payload,
    approval_response_hooks=logistics_approval_response_hooks_for_workflow(workflow_id),
)
""",
        "src/onetruth/application/services/approval_response_hooks.py": """
class ApprovalResponseHook: ...
class ApprovalResponseHookContext: ...
DEFAULT_APPROVAL_RESPONSE_HOOKS: tuple[ApprovalResponseHook, ...] = ()
""",
        "src/onetruth/application/services/logistics_approval_response_hooks.py": """
LOGISTICS_APPROVAL_RESPONSE_HOOKS = ()
def weekly_publish_approval_hook(context): pass
def dispatch_reporting_finalize_approval_hook(context): pass
def logistics_approval_response_hooks_for_workflow(workflow_id): return ()
""",
        "tests/contract/test_handler_import_boundaries.py": """
def test_approval_respond_side_effects_are_registered_domain_hooks(): pass
assert "LOGISTICS_WORKPAGE_DESCRIPTOR_PACK" not in descriptor_defaults_text
assert "LOGISTICS_WORKPAGE_ACTION_PACK" not in action_defaults_text
""",
        "tests/unit/test_approval_response_hooks.py": """
def test_default_approval_response_hooks_are_platform_neutral(): pass
def test_logistics_approval_response_hooks_are_explicitly_selected_by_workflow(): pass
def test_logistics_approval_hooks_ignore_non_approved_responses_before_db_reads(): pass
""",
        "src/onetruth/application/services/workpage_descriptor_registry_defaults.py": """
DEFAULT_WORKPAGE_DESCRIPTOR_REGISTRY = WorkpageDescriptorRegistry()
""",
        "src/onetruth/application/services/workpage_action_registry_defaults.py": """
DEFAULT_WORKPAGE_ACTION_REGISTRY = WorkpageActionRegistry()
""",
        "src/onetruth/application/services/workpage_action_projection.py": """
def project(registry: WorkpageActionRegistry | None = None):
    active_registry = DEFAULT_WORKPAGE_ACTION_REGISTRY if registry is None else registry
""",
        "src/onetruth/application/handlers/workpage_action_resolution.py": """
def f(
    action_registry: WorkpageActionRegistry | None = None,
    descriptor_registry: WorkpageDescriptorRegistry | None = None,
):
    _active_action_registry(action_registry).supports_human_task_subject()
    _active_action_registry(action_registry).supports_approval_subject()
    _active_descriptor_registry(descriptor_registry).require_descriptor()
""",
        "src/onetruth/application/services/logistics_workpage_descriptors.py": """
LOGISTICS_WORKPAGE_DESCRIPTOR_PACK = ()
def logistics_workpage_descriptor_registry(): pass
""",
        "src/onetruth/application/services/logistics_workpage_action_registry.py": """
LOGISTICS_WORKPAGE_ACTION_PACK = ()
def logistics_workpage_action_registry(): pass
def logistics_workpage_action_registry_for_workflow(workflow_id): pass
""",
        "src/onetruth/api/routes/workflow_runs.py": """
logistics_workpage_action_registry_for_workflow(workflow_id)
""",
        "src/onetruth/api/routes/human_tasks.py": """
logistics_workpage_action_registry_for_workflow(workflow_id)
""",
        "src/onetruth/api/routes/workpages.py": """
logistics_workpage_descriptor_registry().descriptor_for_public_run()
""",
        "tests/unit/test_workpage_descriptor_registry.py": """
def test_default_descriptor_registry_is_platform_neutral(): pass
""",
        "tests/unit/test_workpage_domain_registry.py": """
def test_default_action_registry_is_platform_neutral(): pass
def test_logistics_action_registry_is_explicitly_selected_by_workflow(): pass
""",
    }
    for relative_path, content in files.items():
        _write_repo_file(repo_root, relative_path, content)
    return repo_root


def _write_repo_file(repo_root: Path, relative_path: str, content: str) -> None:
    path = repo_root / relative_path
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content.strip() + "\n", encoding="utf-8")
