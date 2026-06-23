from __future__ import annotations

import sqlite3
from typing import Any

from onetruth.application.handlers._shared.artifact_effects import (
    _validate_artifact_link_subject,
)
from onetruth.application.handlers._shared.command_boundary import (
    CommandError,
    _workflow_scope,
)
from onetruth.infrastructure.repositories.artifact_links import list_artifacts_for_subject
from onetruth.infrastructure.repositories.artifact_pointers import (
    get_pointer,
    list_pointers_for_workflow_run,
)
from onetruth.infrastructure.repositories.artifact_relation_hydration import (
    attach_hydrated_artifact_relations,
    list_artifact_versions_page_for_subject_with_relations,
    list_artifact_versions_page_for_workflow_run_with_relations,
)
from onetruth.infrastructure.repositories.artifact_versions import (
    get_artifact_version,
    list_artifact_versions_for_workflow_run,
)
from onetruth.infrastructure.repositories.execution_sessions import (
    get_execution_session,
    list_execution_sessions_for_workflow_run,
)
from onetruth.infrastructure.repositories.flags import (
    get_flag,
    list_flags_for_workflow_run,
)
from onetruth.infrastructure.repositories.human_tasks import (
    get_human_task,
    list_human_tasks_for_workflow_run,
)
from onetruth.infrastructure.repositories.policy_decisions import get_policy_decision
from onetruth.infrastructure.repositories.task_runs import get_task_run
from onetruth.infrastructure.repositories.tool_executions import get_tool_execution
from onetruth.infrastructure.repositories.workflow_runs import (
    get_workflow_run,
    list_workflow_runs,
)

WORKFLOW_RUN_STATES = frozenset({"OPEN", "COMPLETED"})


def show_workflow_run_command(
    connection: sqlite3.Connection,
    workflow_run_id: str,
) -> dict[str, Any]:
    workflow_run = get_workflow_run(connection, workflow_run_id)
    if workflow_run is None:
        raise CommandError(
            code="workflow_run_not_found",
            message="workflow run not found",
            details={"workflow_run_id": workflow_run_id},
        )
    return workflow_run


def list_workflow_runs_command(
    connection: sqlite3.Connection,
    *,
    workflow_id: str | None = None,
    tenant_id: str | None = None,
    domain_id: str | None = None,
    state: str | None = None,
) -> list[dict[str, Any]]:
    if state is not None and state not in WORKFLOW_RUN_STATES:
        raise CommandError(
            code="invalid_workflow_state",
            message=f"unsupported workflow run state: {state}",
            details={"allowed_states": sorted(WORKFLOW_RUN_STATES)},
        )
    return list_workflow_runs(
        connection,
        workflow_id=workflow_id,
        tenant_id=tenant_id,
        domain_id=domain_id,
        state=state,
    )


def show_human_task_command(
    connection: sqlite3.Connection,
    human_task_id: str,
) -> dict[str, Any]:
    human_task = get_human_task(connection, human_task_id)
    if human_task is None:
        raise CommandError(
            code="human_task_not_found",
            message="human task not found",
            details={"human_task_id": human_task_id},
        )
    task_run = get_task_run(connection, str(human_task["task_run_id"]))
    if task_run is not None:
        human_task["task_run_state"] = task_run["state"]
        human_task["stage_id"] = task_run["stage_id"]
        human_task["blocked_on_kind"] = task_run["blocked_on_kind"]
        human_task["blocked_on_ref"] = task_run["blocked_on_ref"]
        human_task["spawned_from_flag_id"] = task_run["spawned_from_flag_id"]
    return human_task


def list_tasks_for_workflow_run_command(
    connection: sqlite3.Connection,
    workflow_run_id: str,
) -> list[dict[str, Any]]:
    _workflow_scope(connection, workflow_run_id)
    tasks = list_human_tasks_for_workflow_run(connection, workflow_run_id)
    results: list[dict[str, Any]] = []
    for task in tasks:
        task_run = get_task_run(connection, str(task["task_run_id"]))
        item = dict(task)
        if task_run is not None:
            item["task_run_state"] = task_run["state"]
            item["stage_id"] = task_run["stage_id"]
            item["blocked_on_kind"] = task_run["blocked_on_kind"]
            item["blocked_on_ref"] = task_run["blocked_on_ref"]
            item["spawned_from_flag_id"] = task_run["spawned_from_flag_id"]
        results.append(item)
    return results


def show_flag_command(
    connection: sqlite3.Connection,
    flag_id: str,
) -> dict[str, Any]:
    flag = get_flag(connection, flag_id)
    if flag is None:
        raise CommandError(
            code="flag_not_found",
            message="flag not found",
            details={"flag_id": flag_id},
        )
    return flag


def list_flags_for_workflow_run_command(
    connection: sqlite3.Connection,
    workflow_run_id: str,
) -> list[dict[str, Any]]:
    _workflow_scope(connection, workflow_run_id)
    return list_flags_for_workflow_run(connection, workflow_run_id)


def show_artifact_version_command(
    connection: sqlite3.Connection,
    artifact_version_id: str,
) -> dict[str, Any]:
    artifact_version = get_artifact_version(connection, artifact_version_id)
    if artifact_version is None:
        raise CommandError(
            code="artifact_version_not_found",
            message="artifact version not found",
            details={"artifact_version_id": artifact_version_id},
        )
    attach_hydrated_artifact_relations(connection, [artifact_version])
    return artifact_version


def list_artifacts_for_workflow_run_command(
    connection: sqlite3.Connection,
    workflow_run_id: str,
) -> list[dict[str, Any]]:
    _workflow_scope(connection, workflow_run_id)
    artifacts = list_artifact_versions_for_workflow_run(connection, workflow_run_id)
    attach_hydrated_artifact_relations(connection, artifacts)
    return artifacts


def list_artifacts_for_workflow_run_page_command(
    connection: sqlite3.Connection,
    workflow_run_id: str,
    *,
    limit: int,
    offset: int = 0,
    artifact_kind: str | None = None,
    tenant_id: str | None = None,
    domain_id: str | None = None,
    project_id: str | None = None,
) -> list[dict[str, Any]]:
    _workflow_scope(connection, workflow_run_id)
    return list_artifact_versions_page_for_workflow_run_with_relations(
        connection,
        workflow_run_id=workflow_run_id,
        limit=limit,
        offset=offset,
        artifact_kind=artifact_kind,
        tenant_id=tenant_id,
        domain_id=domain_id,
        project_id=project_id,
        include_provenance=False,
    )


def list_artifacts_for_subject_command(
    connection: sqlite3.Connection,
    *,
    workflow_run_id: str,
    subject_kind: str,
    subject_id: str,
) -> list[dict[str, Any]]:
    _workflow_scope(connection, workflow_run_id)
    _validate_artifact_link_subject(
        connection,
        workflow_run_id=workflow_run_id,
        subject_kind=subject_kind,
        subject_id=subject_id,
    )
    artifacts = list_artifacts_for_subject(
        connection,
        workflow_run_id=workflow_run_id,
        subject_kind=subject_kind,
        subject_id=subject_id,
    )
    attach_hydrated_artifact_relations(connection, artifacts)
    return artifacts


def list_artifacts_for_subject_page_command(
    connection: sqlite3.Connection,
    *,
    workflow_run_id: str,
    subject_kind: str,
    subject_id: str,
    limit: int,
    offset: int = 0,
    artifact_kind: str | None = None,
    tenant_id: str | None = None,
    domain_id: str | None = None,
    project_id: str | None = None,
) -> list[dict[str, Any]]:
    _workflow_scope(connection, workflow_run_id)
    _validate_artifact_link_subject(
        connection,
        workflow_run_id=workflow_run_id,
        subject_kind=subject_kind,
        subject_id=subject_id,
    )
    return list_artifact_versions_page_for_subject_with_relations(
        connection,
        workflow_run_id=workflow_run_id,
        subject_kind=subject_kind,
        subject_id=subject_id,
        limit=limit,
        offset=offset,
        artifact_kind=artifact_kind,
        tenant_id=tenant_id,
        domain_id=domain_id,
        project_id=project_id,
        include_provenance=False,
    )


def show_pointer_command(
    connection: sqlite3.Connection,
    *,
    workflow_run_id: str,
    pointer_key: str,
) -> dict[str, Any]:
    pointer = get_pointer(
        connection,
        workflow_run_id=workflow_run_id,
        pointer_key=pointer_key,
    )
    if pointer is None:
        raise CommandError(
            code="pointer_not_found",
            message="pointer not found",
            details={"workflow_run_id": workflow_run_id, "pointer_key": pointer_key},
        )
    return pointer


def list_pointers_for_workflow_run_command(
    connection: sqlite3.Connection,
    workflow_run_id: str,
) -> list[dict[str, Any]]:
    _workflow_scope(connection, workflow_run_id)
    return list_pointers_for_workflow_run(connection, workflow_run_id)


def show_execution_session_command(
    connection: sqlite3.Connection,
    execution_session_id: str,
) -> dict[str, Any]:
    session = get_execution_session(connection, execution_session_id)
    if session is None:
        raise CommandError(
            code="execution_session_not_found",
            message="execution session not found",
            details={"execution_session_id": execution_session_id},
        )
    return session


def list_execution_sessions_for_workflow_run_command(
    connection: sqlite3.Connection,
    workflow_run_id: str,
) -> list[dict[str, Any]]:
    _workflow_scope(connection, workflow_run_id)
    return list_execution_sessions_for_workflow_run(connection, workflow_run_id)


def show_tool_execution_command(
    connection: sqlite3.Connection,
    tool_execution_id: str,
) -> dict[str, Any]:
    tool_execution = get_tool_execution(connection, tool_execution_id)
    if tool_execution is None:
        raise CommandError(
            code="tool_execution_not_found",
            message="tool execution not found",
            details={"tool_execution_id": tool_execution_id},
        )
    return tool_execution


def show_policy_decision_command(
    connection: sqlite3.Connection,
    policy_decision_id: str,
) -> dict[str, Any]:
    policy_decision = get_policy_decision(connection, policy_decision_id)
    if policy_decision is None:
        raise CommandError(
            code="policy_decision_not_found",
            message="policy decision not found",
            details={"policy_decision_id": policy_decision_id},
        )
    return policy_decision
