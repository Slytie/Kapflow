from __future__ import annotations

import sqlite3
from typing import Any

from onetruth.application.handlers._shared.command_boundary import CommandError
from onetruth.application.handlers.human_tasks import (
    claim_human_task_command,
    complete_human_task_command,
    confirm_human_task_review_command,
)
from onetruth.application.read_commands import (
    list_artifacts_for_subject_command,
    show_human_task_command,
)
from onetruth.application.services.task_actionability import (
    build_artifact_link_count_index,
    compute_human_task_actionability,
)
from onetruth.application.services.stage06_openai_sandbox import (
    run_stage06_openai_review_sandbox,
)
from onetruth.application.services.weekly_stage04_openai_agent import (
    run_weekly_stage04_openai_agent,
)
from onetruth.application.services.task_requirements import (
    build_human_task_requirement_index,
)
from onetruth.integrations.openai import OpenAIConfigError, OpenAIResponsesError
from onetruth.infrastructure.events.event_store import DuplicateIdempotencyKeyError
from onetruth.infrastructure.repositories.human_tasks import get_human_task
from onetruth.infrastructure.artifacts.storage import default_storage_root_for_db_url

from onetruth.api.dependencies import Page, RequestContext, scoped_workflow_run
from onetruth.api.queries import query_human_tasks
from onetruth.api.errors import (
    ApiError,
    api_error_from_command,
    api_error_from_duplicate_idempotency,
)
from onetruth.api.routes.workflow_runs import (
    project_human_task_workpage_actions_for_detail,
)


TASK_SUBGRAPH_TEMPLATES: dict[str, dict[str, Any]] = {
    "actual_hours_review": {
        "template_id": "schedule_planning.feedback_review.v1",
        "title": "Planning feedback review",
        "nodes": [
            {"node_id": "ingest_actual_hours", "label": "Ingest actual-hours snapshot"},
            {"node_id": "reconcile_plan_variance", "label": "Reconcile plan variance"},
            {"node_id": "draft_feedback_packet", "label": "Draft planning feedback packet"},
            {"node_id": "publish_feedback_handoff", "label": "Publish feedback handoff"},
        ],
    },
    "planning_feedback_review": {
        "template_id": "schedule_planning.feedback_review.v1",
        "title": "Planning feedback review",
        "nodes": [
            {"node_id": "ingest_actual_hours", "label": "Ingest actual-hours snapshot"},
            {"node_id": "reconcile_plan_variance", "label": "Reconcile plan variance"},
            {"node_id": "draft_feedback_packet", "label": "Draft planning feedback packet"},
            {"node_id": "publish_feedback_handoff", "label": "Publish feedback handoff"},
        ],
    },
    "dispatcher_review": {
        "template_id": "live_dispatch.seed_intake.v1",
        "title": "Live dispatch seed intake",
        "nodes": [
            {"node_id": "ingest_weekly_seed", "label": "Ingest weekly seed package"},
            {"node_id": "verify_route_delta", "label": "Verify route delta inputs"},
            {"node_id": "resolve_capacity_conflicts", "label": "Resolve capacity conflicts"},
            {"node_id": "dispatch_ready_confirmation", "label": "Confirm dispatch readiness"},
        ],
    },
    "dispatch_seed_intake": {
        "template_id": "live_dispatch.seed_intake.v1",
        "title": "Live dispatch seed intake",
        "nodes": [
            {"node_id": "ingest_weekly_seed", "label": "Ingest weekly seed package"},
            {"node_id": "verify_route_delta", "label": "Verify route delta inputs"},
            {"node_id": "resolve_capacity_conflicts", "label": "Resolve capacity conflicts"},
            {"node_id": "dispatch_ready_confirmation", "label": "Confirm dispatch readiness"},
        ],
    },
    "final_packet_review": {
        "template_id": "dispatch_reporting.final_packet.v1",
        "title": "Reporting packet closeout",
        "nodes": [
            {"node_id": "collect_route_metrics", "label": "Collect route metrics"},
            {"node_id": "reconcile_variance_notes", "label": "Reconcile variance notes"},
            {"node_id": "finalize_reporting_packet", "label": "Finalize reporting packet"},
            {"node_id": "notify_planning_feedback", "label": "Notify planning feedback"},
        ],
    },
    "finalize_reporting_packet": {
        "template_id": "dispatch_reporting.final_packet.v1",
        "title": "Reporting packet closeout",
        "nodes": [
            {"node_id": "collect_route_metrics", "label": "Collect route metrics"},
            {"node_id": "reconcile_variance_notes", "label": "Reconcile variance notes"},
            {"node_id": "finalize_reporting_packet", "label": "Finalize reporting packet"},
            {"node_id": "notify_planning_feedback", "label": "Notify planning feedback"},
        ],
    },
}


def list_human_tasks_endpoint(
    connection: sqlite3.Connection,
    *,
    context: RequestContext,
    query: dict[str, str],
    page: Page,
) -> dict[str, Any]:
    rows = query_human_tasks(
        connection,
        context=context,
        workflow_run_id=query.get("workflow_run_id"),
        state=query.get("state"),
        stage_id=query.get("stage_id"),
        task_kind=query.get("task_kind"),
        assignee_actor_id=query.get("assignee_actor_id"),
        owner_role=query.get("owner_role"),
        page=page,
    )
    rows = _enrich_human_tasks_with_actionability(
        connection,
        context=context,
        human_tasks=rows,
    )
    return {
        "command": "api.human_tasks.list",
        "human_tasks": rows,
        "page": {"limit": page.limit, "offset": page.offset},
    }


def get_human_task_endpoint(
    connection: sqlite3.Connection,
    *,
    context: RequestContext,
    human_task_id: str,
) -> dict[str, Any]:
    _ensure_human_task_in_scope(connection, context=context, human_task_id=human_task_id)
    try:
        human_task = show_human_task_command(connection, human_task_id)
        workpage_actions = project_human_task_workpage_actions_for_detail(
            connection,
            context=context,
            task=human_task,
        )
    except CommandError as exc:
        raise api_error_from_command(exc) from exc
    enriched = _enrich_human_tasks_with_actionability(
        connection,
        context=context,
        human_tasks=[human_task],
    )
    return {
        "command": "api.human_tasks.detail",
        "human_task": {**enriched[0], "workpage_actions": workpage_actions},
    }


def get_human_task_subgraph_endpoint(
    connection: sqlite3.Connection,
    *,
    context: RequestContext,
    human_task_id: str,
) -> dict[str, Any]:
    _ensure_human_task_in_scope(connection, context=context, human_task_id=human_task_id)
    try:
        human_task = show_human_task_command(connection, human_task_id)
    except CommandError as exc:
        raise api_error_from_command(exc) from exc

    metadata = _composite_task_metadata(human_task)
    if not bool(metadata["is_composite"]):
        raise ApiError(
            status_code=409,
            code="task_subgraph_not_available",
            message="task does not expose a composite subgraph",
            details={
                "human_task_id": human_task_id,
                "task_kind": str(human_task.get("task_kind") or ""),
            },
        )

    return {
        "command": "api.human_tasks.subgraph",
        "human_task_id": human_task_id,
        "is_composite": True,
        "expansion_kind": "task_subgraph",
        "subgraph": _build_task_subgraph(connection, human_task=human_task),
    }


def claim_human_task_endpoint(
    connection: sqlite3.Connection,
    *,
    context: RequestContext,
    human_task_id: str,
    payload: dict[str, Any],
) -> dict[str, Any]:
    _ensure_human_task_in_scope(connection, context=context, human_task_id=human_task_id)
    _assert_payload_human_task_id(payload, human_task_id)

    command_payload = {
        "human_task_id": human_task_id,
        "actor_id": context.actor_id,
        "actor_type": context.actor_type,
        "actor_roles": context.actor_roles,
        "lease_seconds": payload.get("lease_seconds"),
        "idempotency_key": payload.get("idempotency_key"),
    }
    try:
        result = claim_human_task_command(connection, command_payload, include_receipt=True)
    except CommandError as exc:
        raise api_error_from_command(exc) from exc
    except DuplicateIdempotencyKeyError as exc:
        raise api_error_from_duplicate_idempotency(exc) from exc

    return {
        "command": "api.human_tasks.claim",
        "human_task_id": human_task_id,
        "result": result["result"],
        "idempotent_replay": result["idempotent_replay"],
        "receipt": result["receipt"],
    }


def complete_human_task_endpoint(
    connection: sqlite3.Connection,
    *,
    context: RequestContext,
    db_url: str,
    human_task_id: str,
    payload: dict[str, Any],
) -> dict[str, Any]:
    _ensure_human_task_in_scope(connection, context=context, human_task_id=human_task_id)
    _assert_payload_human_task_id(payload, human_task_id)

    command_payload = {
        "human_task_id": human_task_id,
        "actor_id": context.actor_id,
        "actor_type": context.actor_type,
        "outcome": payload.get("outcome"),
        "idempotency_key": payload.get("idempotency_key"),
    }
    try:
        result = complete_human_task_command(
            connection,
            command_payload,
            include_receipt=True,
            storage_root=default_storage_root_for_db_url(db_url),
        )
    except CommandError as exc:
        raise api_error_from_command(exc) from exc
    except DuplicateIdempotencyKeyError as exc:
        raise api_error_from_duplicate_idempotency(exc) from exc

    return {
        "command": "api.human_tasks.complete",
        "human_task_id": human_task_id,
        "result": result["result"],
        "idempotent_replay": result["idempotent_replay"],
        "receipt": result["receipt"],
    }


def run_stage06_agent_review_endpoint(
    connection: sqlite3.Connection,
    *,
    context: RequestContext,
    human_task_id: str,
    payload: dict[str, Any],
) -> dict[str, Any]:
    _ensure_human_task_in_scope(connection, context=context, human_task_id=human_task_id)
    _assert_payload_human_task_id(payload, human_task_id)

    command_payload = {
        "human_task_id": human_task_id,
        "actor_id": context.actor_id,
        "actor_type": context.actor_type,
        "actor_roles": context.actor_roles,
        "idempotency_key": payload.get("idempotency_key"),
        "policy_decision": payload.get("policy_decision"),
    }
    try:
        result = run_stage06_openai_review_sandbox(connection, command_payload)
    except CommandError as exc:
        raise api_error_from_command(exc) from exc
    except DuplicateIdempotencyKeyError as exc:
        raise api_error_from_duplicate_idempotency(exc) from exc
    except OpenAIConfigError as exc:
        raise ApiError(
            status_code=503,
            code=exc.code,
            message=str(exc),
            details={},
        ) from exc
    except OpenAIResponsesError as exc:
        status_code = 503 if exc.retryable else 502
        raise ApiError(
            status_code=status_code,
            code=exc.code,
            message=str(exc),
            details=exc.details,
        ) from exc

    return {
        "command": "api.human_tasks.stage06_agent_review",
        "human_task_id": human_task_id,
        "result": result,
    }


def run_weekly_stage04_openai_agent_endpoint(
    connection: sqlite3.Connection,
    *,
    context: RequestContext,
    human_task_id: str,
    payload: dict[str, Any],
) -> dict[str, Any]:
    _ensure_human_task_in_scope(connection, context=context, human_task_id=human_task_id)
    _assert_payload_human_task_id(payload, human_task_id)

    command_payload = {
        "human_task_id": human_task_id,
        "actor_id": context.actor_id,
        "actor_type": context.actor_type,
        "actor_roles": context.actor_roles,
        "idempotency_key": payload.get("idempotency_key"),
        "policy_decision": payload.get("policy_decision"),
    }
    try:
        result = run_weekly_stage04_openai_agent(connection, command_payload)
    except CommandError as exc:
        if exc.code == "stage04_finalize_required":
            raise ApiError(
                status_code=502,
                code=exc.code,
                message=exc.message,
                details=exc.details,
            ) from exc
        raise api_error_from_command(exc) from exc
    except DuplicateIdempotencyKeyError as exc:
        raise api_error_from_duplicate_idempotency(exc) from exc
    except OpenAIConfigError as exc:
        raise ApiError(
            status_code=503,
            code=exc.code,
            message=str(exc),
            details={},
        ) from exc
    except OpenAIResponsesError as exc:
        status_code = 503 if exc.retryable else 502
        raise ApiError(
            status_code=status_code,
            code=exc.code,
            message=str(exc),
            details=exc.details,
        ) from exc

    return {
        "command": "api.human_tasks.weekly_stage04_openai_agent",
        "human_task_id": human_task_id,
        "result": result,
    }


def confirm_human_task_review_endpoint(
    connection: sqlite3.Connection,
    *,
    context: RequestContext,
    db_url: str,
    human_task_id: str,
    payload: dict[str, Any],
) -> dict[str, Any]:
    _ensure_human_task_in_scope(connection, context=context, human_task_id=human_task_id)
    _assert_payload_human_task_id(payload, human_task_id)
    _assert_no_shared_http_storage_override(
        payload,
        endpoint="api.human_tasks.confirm_review",
    )
    command_payload = {
        "human_task_id": human_task_id,
        "actor_id": context.actor_id,
        "actor_type": context.actor_type,
        "reviewed_artifact_version_ids": payload.get("reviewed_artifact_version_ids"),
        "idempotency_key": payload.get("idempotency_key"),
    }
    try:
        result = confirm_human_task_review_command(
            connection,
            command_payload,
            storage_root=default_storage_root_for_db_url(db_url),
            include_receipt=True,
        )
    except CommandError as exc:
        raise api_error_from_command(exc) from exc
    except DuplicateIdempotencyKeyError as exc:
        raise api_error_from_duplicate_idempotency(exc) from exc
    return {
        "command": "api.human_tasks.confirm_review",
        "human_task_id": human_task_id,
        "result": result["result"],
        "idempotent_replay": result["idempotent_replay"],
        "receipt": result["receipt"],
    }


def _enrich_human_tasks_with_actionability(
    connection: sqlite3.Connection,
    *,
    context: RequestContext,
    human_tasks: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    if not human_tasks:
        return []
    grouped: dict[str, list[dict[str, Any]]] = {}
    for task in human_tasks:
        grouped.setdefault(str(task["workflow_run_id"]), []).append(task)

    link_counts_by_run: dict[str, dict[tuple[str, str], int]] = {}
    requirements_by_run: dict[str, dict[str, dict[str, Any]]] = {}
    for workflow_run_id, tasks in grouped.items():
        link_counts_by_run[workflow_run_id] = build_artifact_link_count_index(
            connection,
            workflow_run_id=workflow_run_id,
        )
        requirements_by_run[workflow_run_id] = build_human_task_requirement_index(
            connection,
            workflow_run_id=workflow_run_id,
            human_tasks=tasks,
        )

    enriched: list[dict[str, Any]] = []
    for task in human_tasks:
        workflow_run_id = str(task["workflow_run_id"])
        human_task_id = str(task["human_task_id"])
        linked_artifact_count = int(
            link_counts_by_run.get(workflow_run_id, {}).get(("human_task", human_task_id), 0)
        )
        actionability = compute_human_task_actionability(
            task=task,
            actor_id=context.actor_id,
            actor_type=context.actor_type,
            actor_roles=context.actor_roles,
            linked_artifact_count=linked_artifact_count,
            requirement_state=requirements_by_run.get(workflow_run_id, {}).get(human_task_id),
        )
        enriched.append({**task, **actionability, **_composite_task_metadata(task)})
    return enriched


def _composite_task_metadata(task: dict[str, Any]) -> dict[str, Any]:
    task_kind = str(task.get("task_kind") or "").strip()
    human_task_id = str(task.get("human_task_id") or "").strip()
    if task_kind not in TASK_SUBGRAPH_TEMPLATES:
        return {
            "is_composite": False,
            "expansion_kind": "none",
            "subgraph_ref": None,
        }
    return {
        "is_composite": True,
        "expansion_kind": "task_subgraph",
        "subgraph_ref": {
            "human_task_id": human_task_id,
            "endpoint": f"/api/v1/human-tasks/{human_task_id}/subgraph",
        },
    }


def _build_task_subgraph(
    connection: sqlite3.Connection,
    *,
    human_task: dict[str, Any],
) -> dict[str, Any]:
    task_kind = str(human_task.get("task_kind") or "").strip()
    template = TASK_SUBGRAPH_TEMPLATES.get(task_kind)
    if template is None:
        raise ApiError(
            status_code=409,
            code="task_subgraph_not_available",
            message="task does not expose a composite subgraph",
            details={"task_kind": task_kind},
        )

    template_nodes = list(template.get("nodes") or [])
    status_for_index = _task_subgraph_status_by_index(
        task_state=str(human_task.get("state") or "OPEN"),
        node_count=len(template_nodes),
    )
    nodes: list[dict[str, Any]] = []
    for index, template_node in enumerate(template_nodes):
        nodes.append(
            {
                "node_id": str(template_node["node_id"]),
                "label": str(template_node["label"]),
                "node_kind": "step",
                "status": status_for_index[index],
                "row": 0,
                "column": index,
                "is_blocking": False,
            }
        )

    edges: list[dict[str, Any]] = []
    for index in range(max(len(nodes) - 1, 0)):
        left = nodes[index]
        right = nodes[index + 1]
        edges.append(
            {
                "edge_id": f"{left['node_id']}->{right['node_id']}",
                "from_node_id": str(left["node_id"]),
                "to_node_id": str(right["node_id"]),
                "edge_kind": "linear",
                "label": None,
            }
        )

    task_run_artifact_refs = _artifact_refs_for_subject(
        connection,
        workflow_run_id=str(human_task["workflow_run_id"]),
        subject_kind="task_run",
        subject_id=str(human_task["task_run_id"]),
        source_label="Task step output",
    )
    human_task_artifact_refs = _artifact_refs_for_subject(
        connection,
        workflow_run_id=str(human_task["workflow_run_id"]),
        subject_kind="human_task",
        subject_id=str(human_task["human_task_id"]),
        source_label="Task attachment",
    )
    artifact_refs_by_id = {
        str(item["artifact_version_id"]): item
        for item in [*task_run_artifact_refs, *human_task_artifact_refs]
    }
    artifact_refs = sorted(
        artifact_refs_by_id.values(),
        key=lambda item: str(item["label"]).lower(),
    )

    updated_at = str(human_task.get("updated_at") or "")
    return {
        "graph_id": f"task_subgraph:{human_task['human_task_id']}",
        "template_id": str(template.get("template_id") or ""),
        "title": str(template.get("title") or "Task subgraph"),
        "nodes": nodes,
        "edges": edges,
        "freshness": {
            "status": "fresh" if updated_at else "unknown",
            "as_of": updated_at or None,
            "note": "Derived from canonical human-task/task-run state",
        },
        "artifact_refs": artifact_refs,
    }


def _artifact_refs_for_subject(
    connection: sqlite3.Connection,
    *,
    workflow_run_id: str,
    subject_kind: str,
    subject_id: str,
    source_label: str,
) -> list[dict[str, str]]:
    artifacts = list_artifacts_for_subject_command(
        connection,
        workflow_run_id=workflow_run_id,
        subject_kind=subject_kind,
        subject_id=subject_id,
    )
    refs: list[dict[str, str]] = []
    for artifact in artifacts:
        metadata = artifact.get("metadata_json")
        label = ""
        if isinstance(metadata, dict):
            for key in ("file_name", "ingress_file_name"):
                value = metadata.get(key)
                if isinstance(value, str) and value.strip():
                    label = value.strip()
                    break
        if not label:
            label = str(artifact.get("artifact_kind") or artifact.get("artifact_version_id") or "artifact")
        refs.append(
            {
                "artifact_version_id": str(artifact["artifact_version_id"]),
                "label": label,
                "source_label": source_label,
            }
        )
    return refs


def _task_subgraph_status_by_index(*, task_state: str, node_count: int) -> list[str]:
    if node_count <= 0:
        return []

    normalized = task_state.strip().upper()
    if normalized == "COMPLETED":
        return ["completed" for _ in range(node_count)]
    if normalized == "CLAIMED":
        statuses = ["not_started" for _ in range(node_count)]
        statuses[0] = "completed"
        if node_count > 1:
            statuses[1] = "in_progress"
        if node_count > 2:
            statuses[2] = "ready"
        return statuses

    statuses = ["not_started" for _ in range(node_count)]
    statuses[0] = "in_progress"
    return statuses


def _ensure_human_task_in_scope(
    connection: sqlite3.Connection,
    *,
    context: RequestContext,
    human_task_id: str,
) -> dict[str, Any]:
    human_task = get_human_task(connection, human_task_id)
    if human_task is None:
        raise ApiError(
            status_code=404,
            code="human_task_not_found",
            message="human task not found",
            details={"human_task_id": human_task_id},
        )
    scoped_workflow_run(connection, context, str(human_task["workflow_run_id"]))
    return human_task


def _assert_payload_human_task_id(payload: dict[str, Any], path_human_task_id: str) -> None:
    payload_human_task_id = payload.get("human_task_id")
    if payload_human_task_id is None:
        return
    if str(payload_human_task_id) != path_human_task_id:
        raise ApiError(
            status_code=400,
            code="path_payload_mismatch",
            message="human_task_id in payload does not match URL path",
            details={
                "path_human_task_id": path_human_task_id,
                "payload_human_task_id": str(payload_human_task_id),
            },
        )


def _assert_no_shared_http_storage_override(
    payload: dict[str, Any],
    *,
    endpoint: str,
) -> None:
    if payload.get("storage_root") is None:
        return
    raise api_error_from_command(
        CommandError(
            code="invalid_artifact_ingress",
            message="shared HTTP artifact-producing endpoints do not accept storage_root",
            details={"endpoint": endpoint, "forbidden_fields": ["storage_root"]},
        )
    )
