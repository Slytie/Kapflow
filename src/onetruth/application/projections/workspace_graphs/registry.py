from __future__ import annotations

from typing import Any, Callable

from .base import WorkspaceGraphProjection
from .live_dispatch import project_live_dispatch_workspace_graph
from .schedule_planning import project_schedule_planning_workspace_graph

GraphProjector = Callable[..., WorkspaceGraphProjection]

PROJECTOR_REGISTRY: dict[str, GraphProjector] = {
    "live_dispatch.v1": project_live_dispatch_workspace_graph,
    "schedule_planning.v1": project_schedule_planning_workspace_graph,
}


def project_workspace_graph(
    *,
    workflow_id: str,
    workflow_run: dict[str, Any],
    task_runs: list[dict[str, Any]],
    human_tasks: list[dict[str, Any]],
    approvals: list[dict[str, Any]],
    flags: list[dict[str, Any]],
    pointers: list[dict[str, Any]],
    artifact_versions: list[dict[str, Any]],
    latest_event_sequence: int | None,
) -> dict[str, Any]:
    projector = PROJECTOR_REGISTRY.get(workflow_id)
    if projector is None:
        projection = WorkspaceGraphProjection(
            nodes=(),
            edges=(),
            summary={
                "workflow_id": workflow_id,
                "workflow_run_id": str(workflow_run.get("workflow_run_id")),
                "node_count": 0,
                "status_counts": {},
                "completed_count": 0,
                "blocking_count": 0,
                "warning_count": 0,
            },
            latest_event_sequence=latest_event_sequence,
            warnings=(
                {
                    "code": "workspace_graph_projector_not_found",
                    "message": f"No workspace graph projector is registered for workflow_id={workflow_id}.",
                    "subject_ids": [],
                },
            ),
        )
        return projection.as_dict()

    projection = projector(
        workflow_run=workflow_run,
        task_runs=task_runs,
        human_tasks=human_tasks,
        approvals=approvals,
        flags=flags,
        pointers=pointers,
        artifact_versions=artifact_versions,
        latest_event_sequence=latest_event_sequence,
    )
    return projection.as_dict()
