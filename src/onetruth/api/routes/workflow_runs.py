from __future__ import annotations

import json
import sqlite3
from typing import Any

from onetruth.application.handlers.workflow_task_lifecycle import (
    CommandError,
    list_approvals_for_workflow_run_command,
    list_artifacts_for_workflow_run_command,
    list_flags_for_workflow_run_command,
    list_pointers_for_workflow_run_command,
    list_tasks_for_workflow_run_command,
)
from onetruth.application.projections.coherence_harness import (
    COHERENCE_POLICY_WARN_VISIBLE,
    COHERENCE_STATUS_FAILED,
    evaluate_official_outputs_coherence,
    maybe_emit_projection_coherence_failed,
)
from onetruth.application.projections.workspace_graphs.registry import (
    project_workspace_graph,
)
from onetruth.application.services.task_actionability import (
    build_artifact_link_count_index,
    compute_approval_actionability,
    compute_flag_actionability,
    compute_human_task_actionability,
)
from onetruth.application.services.task_requirements import (
    build_human_task_requirement_index,
)
from onetruth.infrastructure.events.event_store import utc_now_iso
from onetruth.infrastructure.repositories.artifact_links import (
    list_artifact_links_for_artifact,
)

from onetruth.api.dependencies import (
    Page,
    RequestContext,
    enforce_scope_filter,
    parse_int,
    scoped_workflow_run,
)
from onetruth.api.queries import query_workflow_runs
from onetruth.api.errors import api_error_from_command

ACTIVE_FLAG_STATES = {"open", "triage", "blocked"}
WORKSPACE_RELEVANT_FLAG_ROLES = {
    "dispatch_supervisor",
    "operations_manager",
    "fleet_coordinator",
    "schedule_planner",
}


def list_workflow_runs_endpoint(
    connection: sqlite3.Connection,
    *,
    context: RequestContext,
    query: dict[str, str],
    page: Page,
) -> dict[str, Any]:
    workflow_id = query.get("workflow_id")
    state = query.get("state")
    tenant_id = query.get("tenant_id")
    domain_id = query.get("domain_id")

    enforce_scope_filter(
        context=context,
        tenant_id=tenant_id,
        domain_id=domain_id,
    )

    rows = query_workflow_runs(
        connection,
        context=context,
        workflow_id=workflow_id,
        state=state,
        page=page,
    )
    return {
        "command": "api.workflow_runs.list",
        "workflow_runs": rows,
        "page": {"limit": page.limit, "offset": page.offset},
    }


def get_workflow_run_detail_endpoint(
    connection: sqlite3.Connection,
    *,
    context: RequestContext,
    workflow_run_id: str,
) -> dict[str, Any]:
    workflow_run = scoped_workflow_run(connection, context, workflow_run_id)
    try:
        human_tasks = list_tasks_for_workflow_run_command(connection, workflow_run_id)
        approvals = list_approvals_for_workflow_run_command(connection, workflow_run_id)
        artifact_versions = list_artifacts_for_workflow_run_command(connection, workflow_run_id)
        pointers = list_pointers_for_workflow_run_command(connection, workflow_run_id)
        flags = list_flags_for_workflow_run_command(connection, workflow_run_id)
    except CommandError as exc:
        raise api_error_from_command(exc) from exc

    return {
        "command": "api.workflow_runs.detail",
        "workflow_run": workflow_run,
        "human_tasks": human_tasks,
        "approvals": approvals,
        "artifact_versions": artifact_versions,
        "pointers": pointers,
        "flags": flags,
        "summary": {
            "human_task_count": len(human_tasks),
            "approval_count": len(approvals),
            "artifact_version_count": len(artifact_versions),
            "pointer_count": len(pointers),
            "flag_count": len(flags),
            "active_issue_count": int(workflow_run.get("active_issue_count", 0)),
        },
    }


def get_workflow_run_workspace_endpoint(
    connection: sqlite3.Connection,
    *,
    context: RequestContext,
    workflow_run_id: str,
    query: dict[str, str],
) -> dict[str, Any]:
    workflow_run = scoped_workflow_run(connection, context, workflow_run_id)
    timeline_limit = parse_int(
        query,
        key="timeline_limit",
        default=25,
        min_value=1,
        max_value=200,
    )
    timeline_excerpt, latest_event_sequence, latest_event_recorded_at = _query_timeline_excerpt(
        connection,
        tenant_id=context.tenant_id,
        domain_id=context.domain_id,
        workflow_run_id=workflow_run_id,
        limit=timeline_limit,
    )

    try:
        human_tasks = list_tasks_for_workflow_run_command(connection, workflow_run_id)
        approvals = list_approvals_for_workflow_run_command(connection, workflow_run_id)
        flags = list_flags_for_workflow_run_command(connection, workflow_run_id)
        pointers = list_pointers_for_workflow_run_command(connection, workflow_run_id)
        artifact_versions = list_artifacts_for_workflow_run_command(connection, workflow_run_id)
    except CommandError as exc:
        raise api_error_from_command(exc) from exc
    task_runs = _query_task_runs_for_workflow_run(connection, workflow_run_id=workflow_run_id)

    link_counts = build_artifact_link_count_index(
        connection,
        workflow_run_id=workflow_run_id,
    )
    requirement_index = build_human_task_requirement_index(
        connection,
        workflow_run_id=workflow_run_id,
        human_tasks=human_tasks,
        artifact_versions=artifact_versions,
    )
    graph = project_workspace_graph(
        workflow_id=str(workflow_run.get("workflow_id")),
        workflow_run=workflow_run,
        task_runs=task_runs,
        human_tasks=human_tasks,
        approvals=approvals,
        flags=flags,
        pointers=pointers,
        artifact_versions=artifact_versions,
        latest_event_sequence=latest_event_sequence,
    )

    user_work: list[dict[str, Any]] = []
    blocking_work: list[dict[str, Any]] = []

    for task in human_tasks:
        item = _workspace_human_task_item(
            task=task,
            context=context,
            linked_artifact_count=_linked_count(
                link_counts,
                subject_kind="human_task",
                subject_id=str(task["human_task_id"]),
            ),
            requirement_state=requirement_index.get(str(task["human_task_id"])),
        )
        if _is_user_relevant_task(task=task, context=context):
            user_work.append(item)
        if str(task.get("state")) in {"OPEN", "CLAIMED"}:
            blocking_work.append(item)

    for approval in approvals:
        item = _workspace_approval_item(
            approval=approval,
            context=context,
            linked_artifact_count=_linked_count(
                link_counts,
                subject_kind="approval",
                subject_id=str(approval["approval_id"]),
            ),
        )
        if _is_user_relevant_approval(approval=approval, context=context):
            user_work.append(item)
        if str(approval.get("state")) == "PENDING":
            blocking_work.append(item)

    for flag in flags:
        item = _workspace_flag_item(
            flag=flag,
            context=context,
            linked_artifact_count=_linked_count(
                link_counts,
                subject_kind="flag",
                subject_id=str(flag["flag_id"]),
            ),
        )
        if _is_user_relevant_flag(flag=flag, context=context):
            user_work.append(item)
        if str(flag.get("state")) in ACTIVE_FLAG_STATES:
            blocking_work.append(item)

    official_outputs = _build_official_outputs(
        connection=connection,
        context=context,
        pointers=pointers,
        artifact_versions=artifact_versions,
    )
    outputs_coherence = evaluate_official_outputs_coherence(
        projection_id=f"workspace_official_outputs:{workflow_run_id}",
        projection_kind="workspace_official_outputs",
        outputs=list(official_outputs.get("outputs") or []),
        policy_on_drift=COHERENCE_POLICY_WARN_VISIBLE,
    )
    official_outputs["coherence"] = outputs_coherence
    if outputs_coherence.get("coherence_status") == COHERENCE_STATUS_FAILED:
        maybe_emit_projection_coherence_failed(
            connection,
            tenant_id=context.tenant_id,
            domain_id=context.domain_id,
            workflow_run_id=workflow_run_id,
            coherence=outputs_coherence,
        )
        warnings = graph.get("warnings")
        if not isinstance(warnings, list):
            warnings = []
        warnings.append(
            {
                "code": "projection_coherence_failed",
                "projection_kind": outputs_coherence["projection_kind"],
                "failure_code": outputs_coherence["failure_code"],
                "policy": outputs_coherence["policy"],
            }
        )
        graph["warnings"] = warnings
    freshness = {
        "latest_event_sequence": latest_event_sequence,
        "latest_event_recorded_at": latest_event_recorded_at,
        "workflow_run_updated_at": workflow_run.get("updated_at"),
        "generated_at": utc_now_iso(),
    }

    return {
        "command": "api.workflow_runs.workspace",
        "workflow_run": workflow_run,
        "graph": graph,
        "user_work": user_work,
        "blocking_work": blocking_work,
        "official_outputs": official_outputs,
        "projection_coherence": [outputs_coherence],
        "timeline_excerpt": {
            "events": timeline_excerpt,
            "event_count": len(timeline_excerpt),
        },
        "freshness": freshness,
    }


def _query_task_runs_for_workflow_run(
    connection: sqlite3.Connection,
    *,
    workflow_run_id: str,
) -> list[dict[str, Any]]:
    rows = connection.execute(
        """
        SELECT
            task_run_id,
            workflow_run_id,
            stage_id,
            task_kind,
            state,
            generation,
            activation_key,
            blocked_on_kind,
            blocked_on_ref,
            spawned_from_flag_id,
            spawned_from_task_run_id,
            spawn_rule_id,
            spawn_cause_kind,
            spawn_cause_event_id,
            spawn_depth,
            spawn_budget_key,
            created_at,
            updated_at
        FROM task_runs
        WHERE workflow_run_id = ?
        ORDER BY created_at ASC, task_run_id ASC
        """,
        (workflow_run_id,),
    ).fetchall()
    return [dict(row) for row in rows]


def _query_timeline_excerpt(
    connection: sqlite3.Connection,
    *,
    tenant_id: str,
    domain_id: str,
    workflow_run_id: str,
    limit: int,
) -> tuple[list[dict[str, Any]], int | None, str | None]:
    rows = connection.execute(
        """
        SELECT
            sequence_no,
            event_id,
            event_type,
            schema_version,
            occurred_at,
            recorded_at,
            tenant_id,
            domain_id,
            actor,
            links,
            payload,
            correlation_id,
            causation_id,
            idempotency_key,
            integrity
        FROM timeline_events
        WHERE tenant_id = ?
          AND domain_id = ?
          AND workflow_run_id = ?
        ORDER BY sequence_no DESC
        LIMIT ?
        """,
        (tenant_id, domain_id, workflow_run_id, limit),
    ).fetchall()
    if not rows:
        return [], None, None
    latest_event_sequence = int(rows[0]["sequence_no"])
    latest_event_recorded_at = str(rows[0]["recorded_at"])
    events = [_timeline_row_to_payload(row) for row in rows]
    events.reverse()
    return events, latest_event_sequence, latest_event_recorded_at


def _timeline_row_to_payload(row: sqlite3.Row) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "sequence_no": int(row["sequence_no"]),
        "event_id": str(row["event_id"]),
        "event_type": str(row["event_type"]),
        "schema_version": str(row["schema_version"]),
        "occurred_at": str(row["occurred_at"]),
        "recorded_at": str(row["recorded_at"]),
        "tenant_id": str(row["tenant_id"]),
        "domain_id": str(row["domain_id"]),
        "actor": json.loads(row["actor"]),
        "links": json.loads(row["links"]),
        "payload": json.loads(row["payload"]),
    }
    if row["correlation_id"] is not None:
        payload["correlation_id"] = str(row["correlation_id"])
    if row["causation_id"] is not None:
        payload["causation_id"] = str(row["causation_id"])
    if row["idempotency_key"] is not None:
        payload["idempotency_key"] = str(row["idempotency_key"])
    if row["integrity"] is not None:
        payload["integrity"] = json.loads(row["integrity"])
    return payload


def _workspace_human_task_item(
    *,
    task: dict[str, Any],
    context: RequestContext,
    linked_artifact_count: int,
    requirement_state: dict[str, Any] | None,
) -> dict[str, Any]:
    actionability = compute_human_task_actionability(
        task=task,
        actor_id=context.actor_id,
        actor_type=context.actor_type,
        actor_roles=context.actor_roles,
        linked_artifact_count=linked_artifact_count,
        requirement_state=requirement_state,
    )
    return {
        "id": f"human_task:{task['human_task_id']}",
        "subject_kind": "human_task",
        "subject_id": str(task["human_task_id"]),
        "canonical_state": str(task.get("state")),
        **actionability,
        "metadata": {
            "workflow_run_id": str(task["workflow_run_id"]),
            "task_run_id": str(task["task_run_id"]),
            "stage_id": str(task.get("stage_id")),
            "task_kind": str(task.get("task_kind")),
            "owner_role": task.get("owner_role"),
            "candidate_roles": list(task.get("candidate_roles") or []),
            "assignee_actor_id": task.get("assignee_actor_id"),
            "assignee_actor_type": task.get("assignee_actor_type"),
            "due_at": task.get("due_at"),
            "blocked_on_kind": task.get("blocked_on_kind"),
            "blocked_on_ref": task.get("blocked_on_ref"),
            "spawned_from_flag_id": task.get("spawned_from_flag_id"),
            "updated_at": task.get("updated_at"),
        },
    }


def _workspace_approval_item(
    *,
    approval: dict[str, Any],
    context: RequestContext,
    linked_artifact_count: int,
) -> dict[str, Any]:
    actionability = compute_approval_actionability(
        approval=approval,
        actor_roles=context.actor_roles,
        linked_artifact_count=linked_artifact_count,
    )
    return {
        "id": f"approval:{approval['approval_id']}",
        "subject_kind": "approval",
        "subject_id": str(approval["approval_id"]),
        "canonical_state": str(approval.get("state")),
        **actionability,
        "metadata": {
            "workflow_run_id": str(approval["workflow_run_id"]),
            "task_run_id": (
                str(approval["task_run_id"])
                if approval.get("task_run_id") is not None
                else None
            ),
            "approval_kind": str(approval.get("approval_kind")),
            "scope_kind": str(approval.get("scope_kind")),
            "scope_ref": str(approval.get("scope_ref")),
            "required_role": approval.get("required_role"),
            "candidate_roles": list(approval.get("candidate_roles") or []),
            "requested_at": approval.get("requested_at"),
            "responded_at": approval.get("responded_at"),
            "response_kind": approval.get("response_kind"),
            "updated_at": approval.get("updated_at"),
        },
    }


def _workspace_flag_item(
    *,
    flag: dict[str, Any],
    context: RequestContext,
    linked_artifact_count: int,
) -> dict[str, Any]:
    actionability = compute_flag_actionability(
        flag=flag,
        actor_roles=context.actor_roles,
        linked_artifact_count=linked_artifact_count,
    )
    return {
        "id": f"flag:{flag['flag_id']}",
        "subject_kind": "flag",
        "subject_id": str(flag["flag_id"]),
        "canonical_state": str(flag.get("state")),
        **actionability,
        "metadata": {
            "workflow_run_id": str(flag["workflow_run_id"]),
            "kind": str(flag.get("kind")),
            "severity": str(flag.get("severity")),
            "summary": str(flag.get("summary")),
            "assigned_group": flag.get("assigned_group"),
            "details_json": flag.get("details_json"),
            "created_at": flag.get("created_at"),
            "closed_at": flag.get("closed_at"),
            "updated_at": flag.get("updated_at"),
        },
    }


def _is_user_relevant_task(*, task: dict[str, Any], context: RequestContext) -> bool:
    assignee_actor_id = str(task.get("assignee_actor_id") or "")
    assignee_actor_type = str(task.get("assignee_actor_type") or "")
    if assignee_actor_id and assignee_actor_type:
        return assignee_actor_id == context.actor_id and assignee_actor_type == context.actor_type
    if str(task.get("state")) != "OPEN":
        return False
    candidate_roles = tuple(str(role) for role in task.get("candidate_roles") or [])
    return bool(set(candidate_roles).intersection(set(context.actor_roles)))


def _is_user_relevant_approval(*, approval: dict[str, Any], context: RequestContext) -> bool:
    if str(approval.get("state")) != "PENDING":
        return False
    required_role = str(approval.get("required_role") or "")
    if required_role:
        return required_role in context.actor_roles
    candidate_roles = tuple(str(role) for role in approval.get("candidate_roles") or [])
    return bool(set(candidate_roles).intersection(set(context.actor_roles)))


def _is_user_relevant_flag(*, flag: dict[str, Any], context: RequestContext) -> bool:
    state = str(flag.get("state") or "")
    if state not in ACTIVE_FLAG_STATES:
        return False
    assigned_group = str(flag.get("assigned_group") or "")
    if assigned_group and assigned_group not in context.actor_roles:
        return False
    return bool(set(context.actor_roles).intersection(WORKSPACE_RELEVANT_FLAG_ROLES)) or not assigned_group


def _linked_count(
    counts: dict[tuple[str, str], int],
    *,
    subject_kind: str,
    subject_id: str,
) -> int:
    return int(counts.get((subject_kind, subject_id), 0))


def _build_official_outputs(
    *,
    connection: sqlite3.Connection,
    context: RequestContext,
    pointers: list[dict[str, Any]],
    artifact_versions: list[dict[str, Any]],
) -> dict[str, Any]:
    artifacts_by_id: dict[str, dict[str, Any]] = {
        str(item.get("artifact_version_id")): item for item in artifact_versions
    }
    missing_ids = sorted(
        {
            str(pointer.get("artifact_version_id"))
            for pointer in pointers
            if str(pointer.get("artifact_version_id")) not in artifacts_by_id
        }
    )
    if missing_ids:
        artifacts_by_id.update(
            _load_scoped_artifact_versions_by_id(
                connection,
                tenant_id=context.tenant_id,
                domain_id=context.domain_id,
                artifact_version_ids=missing_ids,
            )
        )
    outputs: list[dict[str, Any]] = []
    for pointer in pointers:
        artifact_version_id = str(pointer.get("artifact_version_id"))
        linked_artifact = artifacts_by_id.get(artifact_version_id)
        outputs.append(
            {
                "pointer": pointer,
                "artifact_version": linked_artifact,
            }
        )
    return {
        "pointers": pointers,
        "outputs": outputs,
    }


def _load_scoped_artifact_versions_by_id(
    connection: sqlite3.Connection,
    *,
    tenant_id: str,
    domain_id: str,
    artifact_version_ids: list[str],
) -> dict[str, dict[str, Any]]:
    if not artifact_version_ids:
        return {}
    placeholders = ",".join("?" for _ in artifact_version_ids)
    rows = connection.execute(
        f"""
        SELECT
            artifact_version_id,
            workflow_run_id,
            task_run_id,
            dataset_key,
            partition_kind,
            partition_key,
            artifact_kind,
            artifact_role,
            media_type,
            storage_uri,
            content_digest,
            byte_size,
            metadata_json,
            parent_artifact_version_id,
            supersedes_artifact_version_id,
            lineage_note,
            created_at
        FROM artifact_versions
        WHERE artifact_version_id IN ({placeholders})
          AND tenant_id = ?
          AND domain_id = ?
        """,
        (*artifact_version_ids, tenant_id, domain_id),
    ).fetchall()

    loaded: dict[str, dict[str, Any]] = {}
    for row in rows:
        item = dict(row)
        item["metadata_json"] = json.loads(item["metadata_json"])
        item["links"] = list_artifact_links_for_artifact(
            connection,
            artifact_version_id=str(item["artifact_version_id"]),
        )
        loaded[str(item["artifact_version_id"])] = item
    return loaded
