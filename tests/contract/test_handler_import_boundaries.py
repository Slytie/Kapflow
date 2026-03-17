from __future__ import annotations

import ast
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
HANDLERS_DIR = REPO_ROOT / "src" / "onetruth" / "application" / "handlers"
TARGET_MODULE = "onetruth.application.handlers.workflow_task_lifecycle"
API_DIR = REPO_ROOT / "src" / "onetruth" / "api"
SERVICES_DIR = REPO_ROOT / "src" / "onetruth" / "application" / "services"
CLI_MAIN = REPO_ROOT / "src" / "onetruth" / "cli" / "__main__.py"

_BANNED_LEGACY_SURFACES = {
    "CommandError",
    "complete_tool_execution_command",
    "create_artifact_version_command",
    "create_execution_session_command",
    "download_artifact_blob_command",
    "evaluate_policy_decision_command",
    "ingest_artifact_document_command",
    "list_approvals_for_workflow_run_command",
    "list_artifacts_for_subject_command",
    "list_artifacts_for_workflow_run_command",
    "list_execution_sessions_for_workflow_run_command",
    "list_flags_for_workflow_run_command",
    "list_pointers_for_workflow_run_command",
    "list_tasks_for_workflow_run_command",
    "list_workflow_runs_command",
    "reconcile_executions_command",
    "request_tool_execution_command",
    "show_approval_command",
    "show_artifact_version_command",
    "show_execution_session_command",
    "show_flag_command",
    "show_human_task_command",
    "show_pointer_command",
    "show_policy_decision_command",
    "show_tool_execution_command",
    "show_workflow_run_command",
    "transition_execution_session_state_command",
    "promote_pointer_command",
}


def test_approvals_and_shared_handler_modules_do_not_import_legacy_hotspot() -> None:
    target_files = [
        HANDLERS_DIR / "approvals.py",
        HANDLERS_DIR / "artifacts.py",
        HANDLERS_DIR / "execution_runtime.py",
        HANDLERS_DIR / "flags.py",
        HANDLERS_DIR / "human_tasks.py",
        HANDLERS_DIR / "pointers.py",
        *sorted((HANDLERS_DIR / "_shared").glob("*.py")),
    ]
    violations: list[str] = []

    for target_file in target_files:
        assert target_file.exists(), f"expected handler seam file to exist: {target_file.relative_to(REPO_ROOT)}"
        tree = ast.parse(target_file.read_text(encoding="utf-8"), filename=str(target_file))
        current_package = _package_parts_for_file(target_file)
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    if alias.name == TARGET_MODULE or alias.name.startswith(f"{TARGET_MODULE}."):
                        violations.append(
                            f"{target_file.relative_to(REPO_ROOT)} imports legacy hotspot via '{alias.name}'"
                        )
            elif isinstance(node, ast.ImportFrom):
                resolved = _resolve_import_from(node=node, current_package=current_package)
                if resolved == TARGET_MODULE or resolved.startswith(f"{TARGET_MODULE}."):
                    rendered = "." * node.level + (node.module or "")
                    violations.append(
                        f"{target_file.relative_to(REPO_ROOT)} imports legacy hotspot via '{rendered}'"
                    )

    assert not violations, "handler import boundary violations:\n" + "\n".join(violations)


def test_api_and_service_layers_do_not_import_legacy_read_or_error_surfaces() -> None:
    target_files = [
        *sorted(API_DIR.rglob("*.py")),
        *sorted(SERVICES_DIR.rglob("*.py")),
        CLI_MAIN,
        HANDLERS_DIR / "logistics_handoff.py",
        HANDLERS_DIR / "schedule_control.py",
    ]
    violations: list[str] = []

    for target_file in target_files:
        assert target_file.exists(), f"expected file to exist: {target_file.relative_to(REPO_ROOT)}"
        tree = ast.parse(target_file.read_text(encoding="utf-8"), filename=str(target_file))
        current_package = _package_parts_for_file(target_file)
        for node in ast.walk(tree):
            if not isinstance(node, ast.ImportFrom):
                continue
            resolved = _resolve_import_from(node=node, current_package=current_package)
            if resolved != TARGET_MODULE:
                continue
            legacy_names = sorted(
                alias.name for alias in node.names if alias.name in _BANNED_LEGACY_SURFACES
            )
            if not legacy_names:
                continue
            violations.append(
                f"{target_file.relative_to(REPO_ROOT)} imports banned legacy surfaces: {', '.join(legacy_names)}"
            )

    assert not violations, "api/service import boundary violations:\n" + "\n".join(violations)


def _package_parts_for_file(path: Path) -> tuple[str, ...]:
    relative_parts = path.relative_to(REPO_ROOT / "src").with_suffix("").parts
    if path.name == "__init__.py":
        return relative_parts[:-1]
    return relative_parts[:-1]


def _resolve_import_from(*, node: ast.ImportFrom, current_package: tuple[str, ...]) -> str:
    if node.level == 0:
        return node.module or ""

    base_parts = current_package[: len(current_package) - (node.level - 1)]
    if node.module:
        return ".".join((*base_parts, *node.module.split(".")))
    return ".".join(base_parts)
