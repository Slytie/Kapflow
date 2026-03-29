from __future__ import annotations

from typing import Any

from .base import WorkspaceGraphEdge, WorkspaceGraphNode, WorkspaceGraphProjection


def project_live_dispatch_workspace_graph(
    *,
    workflow_run: dict[str, Any],
    task_runs: list[dict[str, Any]],
    human_tasks: list[dict[str, Any]],
    approvals: list[dict[str, Any]],
    flags: list[dict[str, Any]],
    pointers: list[dict[str, Any]],
    artifact_versions: list[dict[str, Any]],
    latest_event_sequence: int | None,
) -> WorkspaceGraphProjection:
    del task_runs
    del approvals
    del flags

    run_updated_at = str(workflow_run.get("updated_at") or workflow_run.get("created_at") or "")
    pointer_by_key = {str(item.get("pointer_key") or ""): item for item in pointers}

    stage01_tasks = [item for item in human_tasks if str(item.get("stage_id") or "") == "Stage01"]
    stage03_tasks = [item for item in human_tasks if str(item.get("stage_id") or "") == "Stage03"]
    route_delta_artifact = _latest_artifact(artifact_versions, "dispatch.route_delta_intake.workbook")
    official_delta_pointer = pointer_by_key.get("official:dispatch.official_replan_delta.workbook")

    stage01_status, stage01_reason = _stage_status(
        stage_tasks=stage01_tasks,
        ready_when=False,
        completed_when=route_delta_artifact is not None or bool(stage03_tasks) or official_delta_pointer is not None,
        ready_reason="Seed intake can start once the live service day is prepared.",
        completed_reason="Seed intake has already captured the current route-delta inputs.",
        idle_reason="Waiting for live service-day preparation.",
    )
    stage01_node = WorkspaceGraphNode(
        node_id="stage01_seed_intake",
        label="Stage01 Seed Intake",
        kind="stage",
        status=stage01_status,
        reason=stage01_reason,
        blocking_subject_ids=tuple(_subject_ids("human_task", _open_or_claimed(stage01_tasks))),
        primary_subject_id=_subject_id("human_task", stage01_tasks[0].get("human_task_id")) if stage01_tasks else None,
        updated_at=_latest_updated_at(stage01_tasks, run_updated_at),
    )

    stage03_status, stage03_reason = _stage_status(
        stage_tasks=stage03_tasks,
        ready_when=route_delta_artifact is not None,
        completed_when=official_delta_pointer is not None,
        ready_reason="Dispatcher review can start after the route-delta workbook is uploaded.",
        completed_reason="Dispatcher review is complete for the latest live replan delta.",
        idle_reason="No dispatcher review task is active yet.",
    )
    stage03_node = WorkspaceGraphNode(
        node_id="stage03_dispatcher_review",
        label="Stage03 Dispatcher Review",
        kind="stage",
        status=stage03_status,
        reason=stage03_reason,
        blocking_subject_ids=tuple(_subject_ids("human_task", _open_or_claimed(stage03_tasks))),
        primary_subject_id=_subject_id("human_task", stage03_tasks[0].get("human_task_id")) if stage03_tasks else None,
        updated_at=_latest_updated_at(stage03_tasks, stage01_node.updated_at),
    )

    if official_delta_pointer is not None:
        stage05_status = "completed"
        stage05_reason = "The official live dispatch delta has been promoted."
    elif stage03_status == "completed":
        stage05_status = "in_progress"
        stage05_reason = "Dispatcher review is complete; official delta promotion is being finalized."
    elif stage03_status in {"ready", "in_progress"}:
        stage05_status = "ready"
        stage05_reason = "Official delta publication follows the dispatcher review."
    else:
        stage05_status = "not_started"
        stage05_reason = "No official live dispatch delta has been published yet."
    stage05_node = WorkspaceGraphNode(
        node_id="stage05_delta_published",
        label="Stage05 Delta Published",
        kind="output",
        status=stage05_status,
        reason=stage05_reason,
        blocking_subject_ids=(),
        primary_subject_id=(
            _subject_id("pointer", official_delta_pointer.get("pointer_key"))
            if official_delta_pointer is not None
            else None
        ),
        updated_at=_latest_updated_at([official_delta_pointer] if official_delta_pointer is not None else [], stage03_node.updated_at),
    )

    nodes = (stage01_node, stage03_node, stage05_node)
    edges = (
        WorkspaceGraphEdge(
            from_node="stage01_seed_intake",
            to_node="stage03_dispatcher_review",
            kind="linear",
            label="complete intake",
        ),
        WorkspaceGraphEdge(
            from_node="stage03_dispatcher_review",
            to_node="stage05_delta_published",
            kind="linear",
            label="finalize official delta",
        ),
    )
    return WorkspaceGraphProjection(
        nodes=nodes,
        edges=edges,
        summary={
            "workflow_id": str(workflow_run.get("workflow_id") or ""),
            "workflow_run_id": str(workflow_run.get("workflow_run_id") or ""),
            "node_count": len(nodes),
            "status_counts": _status_counts(nodes),
            "completed_count": sum(1 for node in nodes if node.status == "completed"),
            "blocking_count": sum(1 for node in nodes if node.status == "blocked"),
            "warning_count": sum(1 for node in nodes if node.status == "warning"),
        },
        latest_event_sequence=latest_event_sequence,
        warnings=(),
    )


def _stage_status(
    *,
    stage_tasks: list[dict[str, Any]],
    ready_when: bool,
    completed_when: bool,
    ready_reason: str,
    completed_reason: str,
    idle_reason: str,
) -> tuple[str, str]:
    if any(str(item.get("state") or "") == "CLAIMED" for item in stage_tasks):
        return "in_progress", "Current stage work is actively claimed."
    if any(str(item.get("state") or "") == "OPEN" for item in stage_tasks):
        return "ready", ready_reason
    if completed_when or any(str(item.get("state") or "") == "COMPLETED" for item in stage_tasks):
        return "completed", completed_reason
    if ready_when:
        return "ready", ready_reason
    return "not_started", idle_reason


def _latest_artifact(
    artifact_versions: list[dict[str, Any]],
    artifact_kind: str,
) -> dict[str, Any] | None:
    latest: dict[str, Any] | None = None
    for artifact in artifact_versions:
        if str(artifact.get("artifact_kind") or "") != artifact_kind:
            continue
        latest = artifact
    return latest


def _open_or_claimed(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        item
        for item in items
        if str(item.get("state") or "") in {"OPEN", "CLAIMED", "PENDING"}
    ]


def _subject_ids(subject_kind: str, items: list[dict[str, Any]]) -> list[str]:
    key = {
        "human_task": "human_task_id",
        "approval": "approval_id",
        "flag": "flag_id",
    }.get(subject_kind, "")
    if not key:
        return []
    return [str(item[key]) for item in items if item.get(key) is not None]


def _subject_id(subject_kind: str, subject_value: Any) -> str | None:
    if subject_value is None:
        return None
    return f"{subject_kind}:{subject_value}"


def _latest_updated_at(items: list[dict[str, Any]], fallback: str) -> str:
    latest = fallback
    for item in items:
        updated_at = str(item.get("updated_at") or item.get("created_at") or "").strip()
        if updated_at and updated_at > latest:
            latest = updated_at
    return latest


def _status_counts(nodes: tuple[WorkspaceGraphNode, ...]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for node in nodes:
        counts[node.status] = int(counts.get(node.status, 0)) + 1
    return counts
