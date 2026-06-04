from __future__ import annotations

from typing import Any

from onetruth.application.services.workpage_action_registry import WorkpageActionRegistry
from onetruth.application.services.workpage_action_registry_defaults import (
    DEFAULT_WORKPAGE_ACTION_REGISTRY,
)


def build_workspace_workpage_projection(
    *,
    workflow_run: dict[str, Any],
    artifact_versions: list[dict[str, Any]],
    registry: WorkpageActionRegistry | None = None,
) -> dict[str, Any]:
    active_registry = DEFAULT_WORKPAGE_ACTION_REGISTRY if registry is None else registry
    return active_registry.build_projection(
        workflow_run=workflow_run,
        artifact_versions=artifact_versions,
    )


def project_human_task_workpage_actions(
    *,
    task: dict[str, Any],
    workflow_run: dict[str, Any],
    workpage_projection: dict[str, Any],
    registry: WorkpageActionRegistry | None = None,
) -> list[dict[str, Any]]:
    active_registry = DEFAULT_WORKPAGE_ACTION_REGISTRY if registry is None else registry
    return active_registry.project_human_task_actions(
        task=task,
        workflow_run=workflow_run,
        workpage_projection=workpage_projection,
    )


def project_approval_workpage_actions(
    *,
    approval: dict[str, Any],
    workflow_run: dict[str, Any],
    workpage_projection: dict[str, Any],
    registry: WorkpageActionRegistry | None = None,
) -> list[dict[str, Any]]:
    active_registry = DEFAULT_WORKPAGE_ACTION_REGISTRY if registry is None else registry
    return active_registry.project_approval_actions(
        approval=approval,
        workflow_run=workflow_run,
        workpage_projection=workpage_projection,
    )


def project_flag_workpage_actions(
    *,
    flag: dict[str, Any],
    workpage_projection: dict[str, Any],
) -> list[dict[str, Any]]:
    del flag, workpage_projection
    return []
