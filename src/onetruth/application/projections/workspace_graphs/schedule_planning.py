from __future__ import annotations

from typing import Any

from .base import WorkspaceGraphEdge, WorkspaceGraphNode, WorkspaceGraphProjection

ACTIVE_FLAG_STATES = {"open", "triage", "blocked"}
TERMINAL_FLAG_STATES = {"resolved", "closed", "waived"}


def project_schedule_planning_workspace_graph(
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
    del task_runs  # Human-task rows already carry stage/task state needed in this slice.

    run_updated_at = str(workflow_run.get("updated_at") or workflow_run.get("created_at") or "")
    pointer_by_key = {str(item.get("pointer_key")): item for item in pointers}
    artifacts_by_kind = {str(item.get("artifact_kind")) for item in artifact_versions}

    stage04_tasks = _tasks_for_stage(human_tasks, "Stage04")
    stage05_tasks = _tasks_for_stage(human_tasks, "Stage05")
    stage06_tasks = _tasks_for_stage(human_tasks, "Stage06")
    stage07_tasks = _tasks_for_stage(human_tasks, "Stage07")

    stage06_approvals = _approvals_for_scope(approvals, "Stage06")
    stage07_approvals = _approvals_for_scope(approvals, "Stage07")

    base_pointer = pointer_by_key.get("official:schedule.published_schedule.workbook")
    delta_pointer = pointer_by_key.get("official:schedule.replan_delta.workbook")

    stage03_status = "completed" if _has_downstream_evidence(
        human_tasks=human_tasks,
        approvals=approvals,
        flags=flags,
        pointers=pointers,
        artifact_versions=artifact_versions,
    ) else "not_started"
    stage03_reason = (
        "Canonical downstream records indicate Stage03 inputs were already satisfied."
        if stage03_status == "completed"
        else "No canonical run activity exists yet."
    )
    stage03_primary = _artifact_subject_id(artifact_versions)
    stage03_node = WorkspaceGraphNode(
        node_id="stage03_inputs_ready",
        label="Stage03 Inputs Ready",
        kind="input",
        status=stage03_status,
        reason=stage03_reason,
        blocking_subject_ids=(),
        primary_subject_id=stage03_primary,
        updated_at=_latest_updated_at(artifact_versions, run_updated_at),
    )

    stage04_state = _stage_task_status(stage04_tasks)
    if stage04_state == "open_or_claimed":
        stage04_status = "in_progress"
        stage04_reason = "Stage04 capacity work is currently active."
    elif stage04_state == "completed":
        stage04_status = "completed"
        stage04_reason = "Stage04 capacity tasks are completed."
    elif stage05_tasks or stage06_tasks or stage07_tasks or "schedule.draft_schedule.workbook" in artifacts_by_kind:
        stage04_status = "completed"
        stage04_reason = "Downstream Stage05/Stage06 evidence implies Stage04 completion."
    elif stage03_status == "completed":
        stage04_status = "ready"
        stage04_reason = "Stage04 can start from completed Stage03 inputs."
    else:
        stage04_status = "not_started"
        stage04_reason = "Waiting for Stage03 readiness."
    stage04_node = WorkspaceGraphNode(
        node_id="stage04_capacity_ready",
        label="Stage04 Capacity Ready",
        kind="stage",
        status=stage04_status,
        reason=stage04_reason,
        blocking_subject_ids=tuple(_subject_ids("human_task", _open_or_claimed(stage04_tasks))),
        primary_subject_id=_subject_id("human_task", stage04_tasks[0].get("human_task_id")) if stage04_tasks else None,
        updated_at=_latest_updated_at(stage04_tasks, stage03_node.updated_at),
    )

    stage05_state = _stage_task_status(stage05_tasks)
    stage06_review_completed = any(
        str(item.get("task_kind")) in {"final_review", "review_packet"}
        and str(item.get("state")) == "COMPLETED"
        for item in stage06_tasks
    )
    if stage05_state == "open_or_claimed" and stage06_review_completed:
        stage05_status = "warning"
        stage05_reason = "Stage05 rework loop is active after Stage06 review feedback."
    elif stage05_state == "open_or_claimed":
        stage05_status = "in_progress"
        stage05_reason = "Stage05 triage work is currently active."
    elif stage05_state == "completed":
        stage05_status = "completed"
        stage05_reason = "Stage05 triage tasks are completed."
    elif stage06_tasks or stage06_approvals or base_pointer is not None:
        stage05_status = "completed"
        stage05_reason = "Stage06 progression implies Stage05 completion."
    elif stage04_status in {"completed", "ready"}:
        stage05_status = "ready"
        stage05_reason = "Stage05 can start from Stage04 capacity readiness."
    else:
        stage05_status = "not_started"
        stage05_reason = "Stage05 has no canonical activity yet."
    stage05_node = WorkspaceGraphNode(
        node_id="stage05_draft_triage",
        label="Stage05 Draft Triage",
        kind="stage",
        status=stage05_status,
        reason=stage05_reason,
        blocking_subject_ids=tuple(_subject_ids("human_task", _open_or_claimed(stage05_tasks))),
        primary_subject_id=_subject_id("human_task", stage05_tasks[0].get("human_task_id")) if stage05_tasks else None,
        updated_at=_latest_updated_at(stage05_tasks, stage04_node.updated_at),
    )

    stage06_info_open = [
        item for item in stage06_tasks
        if str(item.get("task_kind")) == "information_request" and str(item.get("state")) in {"OPEN", "CLAIMED"}
    ]
    if stage06_info_open:
        stage06_status = "blocked"
        stage06_reason = "Stage06 review is blocked by open information requests."
    elif any(str(item.get("state")) == "CLAIMED" for item in stage06_tasks):
        stage06_status = "in_progress"
        stage06_reason = "Stage06 review work is currently claimed."
    elif any(str(item.get("state")) == "OPEN" for item in stage06_tasks):
        stage06_status = "ready"
        stage06_reason = "Stage06 review tasks are open and ready."
    elif any(str(item.get("state")) == "COMPLETED" for item in stage06_tasks):
        stage06_status = "completed"
        stage06_reason = "Current Stage06 review loop tasks are completed."
    elif stage05_status in {"completed", "warning"}:
        stage06_status = "ready"
        stage06_reason = "Stage06 can start after Stage05 triage."
    else:
        stage06_status = "not_started"
        stage06_reason = "Stage06 has no canonical task activity yet."
    stage06_node = WorkspaceGraphNode(
        node_id="stage06_review",
        label="Stage06 Review",
        kind="stage",
        status=stage06_status,
        reason=stage06_reason,
        blocking_subject_ids=tuple(_subject_ids("human_task", stage06_info_open)),
        primary_subject_id=_subject_id("human_task", stage06_tasks[0].get("human_task_id")) if stage06_tasks else None,
        updated_at=_latest_updated_at(stage06_tasks, stage05_node.updated_at),
    )

    stage06_pending = [item for item in stage06_approvals if str(item.get("state")) == "PENDING"]
    stage06_approved = [
        item for item in stage06_approvals
        if str(item.get("state")) == "RESPONDED" and str(item.get("response_kind")) == "approve"
    ]
    stage06_non_approve = [
        item for item in stage06_approvals
        if str(item.get("state")) == "RESPONDED" and str(item.get("response_kind")) != "approve"
    ]
    if stage06_pending:
        stage06_approval_status = "awaiting_approval"
        stage06_approval_reason = "Stage06 publish approval is pending."
    elif stage06_non_approve:
        stage06_approval_status = "warning"
        stage06_approval_reason = "Stage06 approval responded without approval; rework is expected."
    elif stage06_approved:
        stage06_approval_status = "completed"
        stage06_approval_reason = "Stage06 publish approval has been granted."
    elif stage06_status == "completed":
        stage06_approval_status = "ready"
        stage06_approval_reason = "Stage06 review complete; publish approval can be requested."
    else:
        stage06_approval_status = "not_started"
        stage06_approval_reason = "No Stage06 publish approval records yet."
    stage06_approval_node = WorkspaceGraphNode(
        node_id="stage06_publish_approval",
        label="Stage06 Publish Approval",
        kind="approval",
        status=stage06_approval_status,
        reason=stage06_approval_reason,
        blocking_subject_ids=tuple(_subject_ids("approval", stage06_pending)),
        primary_subject_id=_subject_id("approval", stage06_approvals[0].get("approval_id")) if stage06_approvals else None,
        updated_at=_latest_updated_at(stage06_approvals, stage06_node.updated_at),
    )

    if base_pointer is not None:
        stage06_publish_status = "completed"
        stage06_publish_reason = "Official Stage06 base schedule pointer has been promoted."
    elif stage06_approval_status == "awaiting_approval":
        stage06_publish_status = "blocked"
        stage06_publish_reason = "Waiting for Stage06 publish approval before pointer promotion."
    elif stage06_approval_status == "warning":
        stage06_publish_status = "warning"
        stage06_publish_reason = "Stage06 publish approval was not approved."
    elif stage06_approval_status == "completed":
        stage06_publish_status = "in_progress"
        stage06_publish_reason = "Approval exists; waiting for official base pointer promotion."
    elif stage06_status == "completed":
        stage06_publish_status = "ready"
        stage06_publish_reason = "Stage06 review completed; base publish is ready."
    else:
        stage06_publish_status = "not_started"
        stage06_publish_reason = "Stage06 publish has not started."
    stage06_publish_node = WorkspaceGraphNode(
        node_id="stage06_base_published",
        label="Stage06 Base Published",
        kind="output",
        status=stage06_publish_status,
        reason=stage06_publish_reason,
        blocking_subject_ids=tuple(_subject_ids("approval", stage06_pending)),
        primary_subject_id=_subject_id("pointer", base_pointer.get("pointer_key")) if base_pointer is not None else None,
        updated_at=_latest_updated_at([base_pointer] if base_pointer is not None else [], stage06_approval_node.updated_at),
    )

    active_flags = [item for item in flags if str(item.get("state")) in ACTIVE_FLAG_STATES]
    blocked_flags = [item for item in flags if str(item.get("state")) == "blocked"]
    terminal_flags = [item for item in flags if str(item.get("state")) in TERMINAL_FLAG_STATES]
    stage07_state = _stage_task_status(stage07_tasks)
    if blocked_flags:
        stage07_status = "blocked"
        stage07_reason = "Stage07 has blocked exceptions requiring intervention."
    elif active_flags or stage07_state == "open_or_claimed":
        stage07_status = "in_progress"
        stage07_reason = "Active exceptions or open Stage07 tasks are in progress."
    elif stage07_state == "completed" or terminal_flags:
        stage07_status = "completed"
        stage07_reason = "Stage07 exception loop has completed current known work."
    elif stage06_publish_status == "completed":
        stage07_status = "ready"
        stage07_reason = "Stage07 exception control is ready after base publication."
    else:
        stage07_status = "not_started"
        stage07_reason = "Stage07 has no canonical exception activity yet."
    stage07_node = WorkspaceGraphNode(
        node_id="stage07_exception_control",
        label="Stage07 Exception Control",
        kind="exception",
        status=stage07_status,
        reason=stage07_reason,
        blocking_subject_ids=tuple(_subject_ids("flag", blocked_flags)),
        primary_subject_id=_subject_id("flag", active_flags[0].get("flag_id")) if active_flags else None,
        updated_at=_latest_updated_at(flags + stage07_tasks, stage06_publish_node.updated_at),
    )

    stage07_pending = [item for item in stage07_approvals if str(item.get("state")) == "PENDING"]
    stage07_approved = [
        item for item in stage07_approvals
        if str(item.get("state")) == "RESPONDED" and str(item.get("response_kind")) == "approve"
    ]
    stage07_non_approve = [
        item for item in stage07_approvals
        if str(item.get("state")) == "RESPONDED" and str(item.get("response_kind")) != "approve"
    ]
    stage07_final_reviews = [
        item for item in stage07_tasks
        if str(item.get("task_kind")) == "final_review" and str(item.get("state")) == "COMPLETED"
    ]
    if stage07_pending:
        stage07_approval_status = "awaiting_approval"
        stage07_approval_reason = "Stage07 major-replan approval is pending."
    elif stage07_non_approve:
        stage07_approval_status = "warning"
        stage07_approval_reason = "Stage07 replan approval was not approved."
    elif stage07_approved:
        stage07_approval_status = "completed"
        stage07_approval_reason = "Stage07 major-replan approval has been granted."
    elif stage07_final_reviews and delta_pointer is None:
        stage07_approval_status = "ready"
        stage07_approval_reason = "Stage07 final review completed; approval can be requested."
    else:
        stage07_approval_status = "not_started"
        stage07_approval_reason = "No Stage07 replan approval records yet."
    stage07_approval_node = WorkspaceGraphNode(
        node_id="stage07_replan_approval",
        label="Stage07 Replan Approval",
        kind="approval",
        status=stage07_approval_status,
        reason=stage07_approval_reason,
        blocking_subject_ids=tuple(_subject_ids("approval", stage07_pending)),
        primary_subject_id=_subject_id("approval", stage07_approvals[0].get("approval_id")) if stage07_approvals else None,
        updated_at=_latest_updated_at(stage07_approvals, stage07_node.updated_at),
    )

    if delta_pointer is not None:
        stage07_delta_status = "completed"
        stage07_delta_reason = "Official Stage07 delta pointer has been promoted."
    elif stage07_approval_status == "awaiting_approval":
        stage07_delta_status = "blocked"
        stage07_delta_reason = "Waiting for Stage07 approval before delta promotion."
    elif stage07_approval_status == "warning":
        stage07_delta_status = "warning"
        stage07_delta_reason = "Stage07 delta publication is blocked by non-approval response."
    elif stage07_approval_status == "completed":
        stage07_delta_status = "in_progress"
        stage07_delta_reason = "Approval exists; waiting for Stage07 pointer promotion."
    elif stage07_status in {"in_progress", "completed", "blocked"}:
        stage07_delta_status = "ready"
        stage07_delta_reason = "Stage07 work is active; delta publication path is available."
    else:
        stage07_delta_status = "not_started"
        stage07_delta_reason = "Stage07 delta publication has not started."
    stage07_delta_node = WorkspaceGraphNode(
        node_id="stage07_delta_published",
        label="Stage07 Delta Published",
        kind="output",
        status=stage07_delta_status,
        reason=stage07_delta_reason,
        blocking_subject_ids=tuple(_subject_ids("approval", stage07_pending)),
        primary_subject_id=_subject_id("pointer", delta_pointer.get("pointer_key")) if delta_pointer is not None else None,
        updated_at=_latest_updated_at([delta_pointer] if delta_pointer is not None else [], stage07_approval_node.updated_at),
    )

    nodes = (
        stage03_node,
        stage04_node,
        stage05_node,
        stage06_node,
        stage06_approval_node,
        stage06_publish_node,
        stage07_node,
        stage07_approval_node,
        stage07_delta_node,
    )
    edges = (
        WorkspaceGraphEdge("stage03_inputs_ready", "stage04_capacity_ready", "mainline", None),
        WorkspaceGraphEdge("stage04_capacity_ready", "stage05_draft_triage", "mainline", None),
        WorkspaceGraphEdge("stage05_draft_triage", "stage06_review", "mainline", None),
        WorkspaceGraphEdge("stage06_review", "stage06_publish_approval", "mainline", None),
        WorkspaceGraphEdge("stage06_publish_approval", "stage06_base_published", "mainline", None),
        WorkspaceGraphEdge("stage06_base_published", "stage07_exception_control", "mainline", None),
        WorkspaceGraphEdge("stage07_exception_control", "stage07_replan_approval", "branch", "major replan"),
        WorkspaceGraphEdge("stage07_replan_approval", "stage07_delta_published", "mainline", None),
        WorkspaceGraphEdge("stage06_review", "stage05_draft_triage", "loopback", "request changes"),
        WorkspaceGraphEdge("stage06_review", "stage06_review", "loopback", "information request"),
        WorkspaceGraphEdge("stage07_exception_control", "stage07_exception_control", "loopback", "child issue / info"),
    )

    warnings: list[dict[str, Any]] = []
    critical_flags = [
        item for item in active_flags
        if str(item.get("severity")) in {"critical", "high"}
    ]
    if critical_flags:
        warnings.append(
            {
                "code": "active_high_severity_flags",
                "message": "High-severity active exceptions are present in Stage07.",
                "subject_ids": _subject_ids("flag", critical_flags),
            }
        )
    if stage06_non_approve:
        warnings.append(
            {
                "code": "stage06_not_approved",
                "message": "Stage06 publish approval responded without approval.",
                "subject_ids": _subject_ids("approval", stage06_non_approve),
            }
        )
    if stage07_non_approve:
        warnings.append(
            {
                "code": "stage07_not_approved",
                "message": "Stage07 replan approval responded without approval.",
                "subject_ids": _subject_ids("approval", stage07_non_approve),
            }
        )
    if stage06_info_open:
        warnings.append(
            {
                "code": "stage06_information_required",
                "message": "Stage06 has open information requests that block progress.",
                "subject_ids": _subject_ids("human_task", stage06_info_open),
            }
        )

    status_counts: dict[str, int] = {}
    for node in nodes:
        status_counts[node.status] = status_counts.get(node.status, 0) + 1

    summary = {
        "workflow_id": str(workflow_run.get("workflow_id")),
        "workflow_run_id": str(workflow_run.get("workflow_run_id")),
        "node_count": len(nodes),
        "status_counts": status_counts,
        "completed_count": status_counts.get("completed", 0),
        "blocking_count": status_counts.get("blocked", 0) + status_counts.get("awaiting_approval", 0),
        "warning_count": status_counts.get("warning", 0),
    }
    return WorkspaceGraphProjection(
        nodes=nodes,
        edges=edges,
        summary=summary,
        latest_event_sequence=latest_event_sequence,
        warnings=tuple(warnings),
    )


def _tasks_for_stage(human_tasks: list[dict[str, Any]], stage_id: str) -> list[dict[str, Any]]:
    return [item for item in human_tasks if str(item.get("stage_id")) == stage_id]


def _approvals_for_scope(approvals: list[dict[str, Any]], scope_ref: str) -> list[dict[str, Any]]:
    return [item for item in approvals if str(item.get("scope_ref")) == scope_ref]


def _stage_task_status(stage_tasks: list[dict[str, Any]]) -> str:
    if not stage_tasks:
        return "none"
    if any(str(item.get("state")) in {"OPEN", "CLAIMED"} for item in stage_tasks):
        return "open_or_claimed"
    if all(str(item.get("state")) == "COMPLETED" for item in stage_tasks):
        return "completed"
    return "mixed"


def _open_or_claimed(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [item for item in items if str(item.get("state")) in {"OPEN", "CLAIMED"}]


def _has_downstream_evidence(
    *,
    human_tasks: list[dict[str, Any]],
    approvals: list[dict[str, Any]],
    flags: list[dict[str, Any]],
    pointers: list[dict[str, Any]],
    artifact_versions: list[dict[str, Any]],
) -> bool:
    return bool(human_tasks or approvals or flags or pointers or artifact_versions)


def _latest_updated_at(items: list[dict[str, Any] | None], fallback: str) -> str:
    timestamps: list[str] = []
    for item in items:
        if not item:
            continue
        updated = item.get("updated_at")
        created = item.get("created_at")
        if isinstance(updated, str) and updated:
            timestamps.append(updated)
        elif isinstance(created, str) and created:
            timestamps.append(created)
    if not timestamps:
        return fallback
    return max(timestamps)


def _subject_id(kind: str, value: Any) -> str | None:
    if value is None:
        return None
    raw = str(value).strip()
    if not raw:
        return None
    return f"{kind}:{raw}"


def _subject_ids(kind: str, items: list[dict[str, Any]]) -> list[str]:
    values: list[str] = []
    for item in items:
        for key in ("human_task_id", "approval_id", "flag_id"):
            if item.get(key) is None:
                continue
            values.append(f"{kind}:{item[key]}")
            break
    return values


def _artifact_subject_id(artifact_versions: list[dict[str, Any]]) -> str | None:
    if not artifact_versions:
        return None
    first = artifact_versions[0]
    return _subject_id("artifact_version", first.get("artifact_version_id"))
