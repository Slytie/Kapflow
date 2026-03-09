from __future__ import annotations

from collections import Counter
from functools import lru_cache
import json
from pathlib import Path
import sqlite3
from typing import Any

import yaml

from onetruth.application.handlers.workflow_task_lifecycle import (
    CommandError,
    list_artifacts_for_workflow_run_command,
)
from onetruth.application.projections.coherence_harness import (
    COHERENCE_POLICY_WARN_VISIBLE,
    COHERENCE_STATUS_FAILED,
    evaluate_handoff_operator_view_coherence,
    evaluate_official_outputs_coherence,
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
from onetruth.domain.partition_codec import PartitionCodecError, validate_partition_key
from onetruth.infrastructure.definitions.family_compiler import (
    DefinitionCompileError,
    compile_workflow_family,
)
from onetruth.infrastructure.events.event_store import utc_now_iso

from onetruth.api.dependencies import Page, RequestContext
from onetruth.api.errors import ApiError, api_error_from_command
from onetruth.api.routes.approvals import query_approvals
from onetruth.api.routes.flags import query_flags
from onetruth.api.routes.human_tasks import query_human_tasks
from onetruth.api.routes.pointers import query_pointers
from onetruth.api.routes.workflow_runs import query_workflow_runs

_REPO_ROOT = Path(__file__).resolve().parents[4]
_STORY_CONTRACT_PATH = (
    _REPO_ROOT / "docs" / "planning" / "THREE_WORKFLOW_DEMO_STORY.yaml"
)
_LOGISTICS_FAMILY_PATH = (
    _REPO_ROOT / "docs" / "workflows" / "logistics_ops_family" / "v1" / "WORKFLOW_FAMILY.yaml"
)
_LOGISTICS_TRANSFORMS_PATH = (
    _REPO_ROOT / "docs" / "workflows" / "logistics_ops_family" / "v1" / "PARTITION_TRANSFORMS.yaml"
)

_SOURCE_PAGE = Page(limit=500, offset=0)

_LANE_ORDER = {
    "flags.open": 5,
    "human_tasks.open": 10,
    "human_tasks.claimed": 20,
    "approvals.pending": 30,
    "approvals.responded": 40,
    "human_tasks.completed": 50,
    "flags.resolved": 60,
    "flags.closed": 70,
}

_LANE_LABELS = {
    "flags.open": "Open Exceptions",
    "human_tasks.open": "Open Tasks",
    "human_tasks.claimed": "Claimed Tasks",
    "approvals.pending": "Pending Approvals",
    "approvals.responded": "Responded Approvals",
    "human_tasks.completed": "Completed Tasks",
    "flags.resolved": "Resolved Exceptions",
    "flags.closed": "Closed Exceptions",
}

_PRIMARY_ACTIONS = {
    "claim",
    "complete",
    "confirm_review",
    "run_stage06_agent_review",
    "respond",
    "transition",
}


def logistics_three_workflow_story_endpoint(
    connection: sqlite3.Connection,
    *,
    context: RequestContext,
    query: dict[str, str],
    page: Page,
) -> dict[str, Any]:
    planning_week_id = str(query.get("planning_week_id") or "").strip()
    if not planning_week_id:
        raise ApiError(
            status_code=400,
            code="invalid_query_parameter",
            message="planning_week_id is required",
            details={"parameter": "planning_week_id"},
        )
    try:
        validate_partition_key("PlanningWeekID", planning_week_id)
    except PartitionCodecError as exc:
        raise ApiError(
            status_code=400,
            code="invalid_query_parameter",
            message="planning_week_id must be a valid PlanningWeekID",
            details={"parameter": "planning_week_id", "value": planning_week_id},
        ) from exc

    service_date_id: str | None = query.get("service_date_id")
    if service_date_id is not None:
        service_date_id = service_date_id.strip() or None
    if service_date_id is not None:
        try:
            validate_partition_key("ServiceDateID", service_date_id)
        except PartitionCodecError as exc:
            raise ApiError(
                status_code=400,
                code="invalid_query_parameter",
                message="service_date_id must be a valid ServiceDateID",
                details={"parameter": "service_date_id", "value": service_date_id},
            ) from exc

    contract = _load_story_contract()
    family_graph = _compiled_family_graph()
    workflow_ids = _workflow_ids(contract)
    edge_ids = tuple(str(item) for item in contract["edge_ids"])

    edge_rows = _query_story_edge_rows(
        connection,
        context=context,
        edge_ids=edge_ids,
        planning_week_id=planning_week_id,
        service_date_id=service_date_id,
        weekly_workflow_id=workflow_ids["weekly"],
        reporting_workflow_id=workflow_ids["reporting"],
    )
    runs_by_workflow = _resolve_linked_runs(
        connection,
        context=context,
        workflow_ids=workflow_ids,
        edge_rows=edge_rows,
        planning_week_id=planning_week_id,
        service_date_id=service_date_id,
    )
    runs_by_id = {
        str(run["workflow_run_id"]): run
        for workflow_runs in runs_by_workflow.values()
        for run in workflow_runs
    }

    edge_summaries = _summarize_edges(
        connection,
        edge_ids=edge_ids,
        edge_rows=edge_rows,
        runs_by_id=runs_by_id,
    )

    board, artifacts_by_run_id = _build_story_board(
        connection,
        context=context,
        runs_by_id=runs_by_id,
        page=page,
    )
    official_outputs = _build_official_outputs_summary(
        connection,
        context=context,
        run_ids=sorted(runs_by_id.keys()),
        artifacts_by_run_id=artifacts_by_run_id,
    )
    freshness = _story_freshness(
        connection,
        context=context,
        run_ids=sorted(runs_by_id.keys()),
    )

    service_date_ids = sorted(
        {
            *(item for item in _derive_service_dates(edge_rows=edge_rows) if item),
            *(str(run["partition_key"]) for run in runs_by_workflow["live_dispatch"]),
            *(str(run["partition_key"]) for run in runs_by_workflow["dispatch_reporting"]),
            *((service_date_id,) if service_date_id is not None else ()),
        }
    )

    return {
        "command": "api.stories.logistics_three_workflow",
        "story": {
            "story_id": contract["story_id"],
            "family": {
                "family_id": contract["family_id"],
                "family_version": family_graph["family_version"],
                "contract_version": contract["contract_version"],
            },
            "partitions": {
                "planning_week_id": planning_week_id,
                "service_date_ids": service_date_ids,
            },
            "family_graph": family_graph,
            "linked_workflow_runs": {
                **runs_by_workflow,
                "summary": {
                    "weekly_schedule_planning_count": len(runs_by_workflow["weekly_schedule_planning"]),
                    "live_dispatch_count": len(runs_by_workflow["live_dispatch"]),
                    "dispatch_reporting_count": len(runs_by_workflow["dispatch_reporting"]),
                },
            },
            "handoff_activity": {
                "edges": edge_summaries,
                "summary": {
                    "edge_execution_count": sum(
                        int(item["execution_count"]) for item in edge_summaries
                    ),
                    "coherence_failed_count": sum(
                        int(item["coherence_failed_count"]) for item in edge_summaries
                    ),
                },
            },
            "board": board,
            "official_outputs": official_outputs,
            "freshness": freshness,
            "coherence": {
                "official_outputs": official_outputs["coherence"],
                "handoff_edges": [
                    {
                        "edge_id": item["edge_id"],
                        "coherence_failed_count": item["coherence_failed_count"],
                    }
                    for item in edge_summaries
                ],
            },
        },
    }


def _workflow_ids(contract: dict[str, Any]) -> dict[str, str]:
    return {
        "weekly": str(contract["workflow_ids"]["weekly_schedule_planning"]),
        "live": str(contract["workflow_ids"]["live_dispatch"]),
        "reporting": str(contract["workflow_ids"]["dispatch_reporting"]),
    }


def _query_story_edge_rows(
    connection: sqlite3.Connection,
    *,
    context: RequestContext,
    edge_ids: tuple[str, ...],
    planning_week_id: str,
    service_date_id: str | None,
    weekly_workflow_id: str,
    reporting_workflow_id: str,
) -> list[dict[str, Any]]:
    placeholders = ",".join("?" for _ in edge_ids)
    rows = connection.execute(
        f"""
        SELECT
            ee.edge_execution_id,
            ee.edge_id,
            ee.source_workflow_run_id,
            ee.source_stage_id,
            ee.source_artifact_version_id,
            ee.source_activation_key,
            ee.target_workflow_id,
            ee.target_workflow_run_id,
            ee.target_stage_id,
            ee.target_partition_kind,
            ee.target_partition_key,
            ee.target_activation_key,
            ee.correlation_key,
            ee.materialize_idempotency_key,
            ee.activation_idempotency_key,
            ee.status,
            ee.cursor_state_json,
            ee.compensation_state_json,
            ee.input_bindings_json,
            ee.trigger_ref,
            ee.seed_artifact_version_id,
            ee.created_at,
            ee.updated_at,
            ee.activated_at,
            swr.workflow_id AS source_workflow_id,
            swr.partition_key AS source_partition_key
        FROM edge_executions ee
        JOIN workflow_runs swr
          ON swr.workflow_run_id = ee.source_workflow_run_id
        WHERE swr.tenant_id = ?
          AND swr.domain_id = ?
          AND ee.edge_id IN ({placeholders})
        ORDER BY ee.created_at ASC, ee.edge_execution_id ASC
        """,
        (context.tenant_id, context.domain_id, *edge_ids),
    ).fetchall()
    filtered: list[dict[str, Any]] = []
    for row in rows:
        item = _decode_edge_row(dict(row))
        edge_id = str(item["edge_id"])
        source_workflow_id = str(item.get("source_workflow_id") or "")
        source_partition_key = str(item.get("source_partition_key") or "")
        if edge_id == "weekly_seed_to_live_dispatch":
            if source_workflow_id != weekly_workflow_id:
                continue
            if source_partition_key != planning_week_id:
                continue
            if service_date_id is not None and str(item["target_partition_key"]) != service_date_id:
                continue
        elif edge_id == "reporting_actuals_to_future_planning":
            if source_workflow_id != reporting_workflow_id:
                continue
            if str(item["target_partition_key"]) != planning_week_id:
                continue
            if service_date_id is not None and source_partition_key != service_date_id:
                continue
        else:
            continue
        filtered.append(item)
    return filtered


def _resolve_linked_runs(
    connection: sqlite3.Connection,
    *,
    context: RequestContext,
    workflow_ids: dict[str, str],
    edge_rows: list[dict[str, Any]],
    planning_week_id: str,
    service_date_id: str | None,
) -> dict[str, list[dict[str, Any]]]:
    weekly_runs = query_workflow_runs(
        connection,
        context=context,
        workflow_id=workflow_ids["weekly"],
        state=None,
        page=_SOURCE_PAGE,
    )
    live_runs = query_workflow_runs(
        connection,
        context=context,
        workflow_id=workflow_ids["live"],
        state=None,
        page=_SOURCE_PAGE,
    )
    reporting_runs = query_workflow_runs(
        connection,
        context=context,
        workflow_id=workflow_ids["reporting"],
        state=None,
        page=_SOURCE_PAGE,
    )

    weekly_run_ids_from_edges: set[str] = set()
    live_run_ids_from_edges: set[str] = set()
    reporting_run_ids_from_edges: set[str] = set()
    service_date_ids: set[str] = set()
    if service_date_id is not None:
        service_date_ids.add(service_date_id)

    for edge in edge_rows:
        edge_id = str(edge["edge_id"])
        source_run_id = str(edge["source_workflow_run_id"])
        target_run_id = (
            str(edge["target_workflow_run_id"])
            if edge.get("target_workflow_run_id") is not None
            else None
        )
        if edge_id == "weekly_seed_to_live_dispatch":
            weekly_run_ids_from_edges.add(source_run_id)
            service_date_ids.add(str(edge["target_partition_key"]))
            if target_run_id is not None:
                live_run_ids_from_edges.add(target_run_id)
        elif edge_id == "reporting_actuals_to_future_planning":
            reporting_run_ids_from_edges.add(source_run_id)
            service_date_ids.add(str(edge.get("source_partition_key") or ""))
            if target_run_id is not None:
                weekly_run_ids_from_edges.add(target_run_id)

    weekly_filtered = _stable_run_sort(
        [
            run
            for run in weekly_runs
            if str(run["partition_key"]) == planning_week_id
            or str(run["workflow_run_id"]) in weekly_run_ids_from_edges
        ]
    )
    live_filtered = _stable_run_sort(
        [
            run
            for run in live_runs
            if str(run["workflow_run_id"]) in live_run_ids_from_edges
            or str(run["partition_key"]) in service_date_ids
        ]
    )
    reporting_filtered = _stable_run_sort(
        [
            run
            for run in reporting_runs
            if str(run["workflow_run_id"]) in reporting_run_ids_from_edges
            or str(run["partition_key"]) in service_date_ids
        ]
    )
    return {
        "weekly_schedule_planning": weekly_filtered,
        "live_dispatch": live_filtered,
        "dispatch_reporting": reporting_filtered,
    }


def _summarize_edges(
    connection: sqlite3.Connection,
    *,
    edge_ids: tuple[str, ...],
    edge_rows: list[dict[str, Any]],
    runs_by_id: dict[str, dict[str, Any]],
) -> list[dict[str, Any]]:
    summaries: list[dict[str, Any]] = []
    for edge_id in edge_ids:
        executions: list[dict[str, Any]] = []
        status_counts: Counter[str] = Counter()
        coherence_failed_count = 0
        for edge in edge_rows:
            if str(edge["edge_id"]) != edge_id:
                continue
            coherence = evaluate_handoff_operator_view_coherence(
                connection,
                projection_id=f"story_handoff:{edge['edge_execution_id']}",
                edge_execution=edge,
                policy_on_drift=COHERENCE_POLICY_WARN_VISIBLE,
            )
            if coherence.get("coherence_status") == COHERENCE_STATUS_FAILED:
                coherence_failed_count += 1
            item = {
                **edge,
                "source_workflow_run": runs_by_id.get(str(edge["source_workflow_run_id"])),
                "target_workflow_run": (
                    runs_by_id.get(str(edge["target_workflow_run_id"]))
                    if edge.get("target_workflow_run_id") is not None
                    else None
                ),
                "coherence": coherence,
            }
            executions.append(item)
            status_counts[str(edge["status"])] += 1
        summaries.append(
            {
                "edge_id": edge_id,
                "execution_count": len(executions),
                "status_counts": dict(status_counts),
                "coherence_failed_count": coherence_failed_count,
                "executions": executions,
            }
        )
    return summaries


def _build_story_board(
    connection: sqlite3.Connection,
    *,
    context: RequestContext,
    runs_by_id: dict[str, dict[str, Any]],
    page: Page,
) -> tuple[dict[str, Any], dict[str, list[dict[str, Any]]]]:
    work_items: list[dict[str, Any]] = []
    artifacts_by_run_id: dict[str, list[dict[str, Any]]] = {}

    for workflow_run_id, workflow_run in runs_by_id.items():
        human_tasks = query_human_tasks(
            connection,
            context=context,
            workflow_run_id=workflow_run_id,
            state=None,
            stage_id=None,
            task_kind=None,
            assignee_actor_id=None,
            owner_role=None,
            page=_SOURCE_PAGE,
        )
        approvals = query_approvals(
            connection,
            context=context,
            workflow_run_id=workflow_run_id,
            state=None,
            approval_kind=None,
            required_role=None,
            page=_SOURCE_PAGE,
        )
        flags = query_flags(
            connection,
            context=context,
            workflow_run_id=workflow_run_id,
            state=None,
            kind=None,
            severity=None,
            assigned_group=None,
            page=_SOURCE_PAGE,
        )
        try:
            artifacts = list_artifacts_for_workflow_run_command(connection, workflow_run_id)
        except CommandError as exc:
            raise api_error_from_command(exc) from exc
        artifacts_by_run_id[workflow_run_id] = artifacts

        link_counts = build_artifact_link_count_index(
            connection,
            workflow_run_id=workflow_run_id,
        )
        requirement_index = build_human_task_requirement_index(
            connection,
            workflow_run_id=workflow_run_id,
            human_tasks=human_tasks,
            artifact_versions=artifacts,
        )

        for task in human_tasks:
            subject_id = str(task["human_task_id"])
            actionability = compute_human_task_actionability(
                task=task,
                actor_id=context.actor_id,
                actor_type=context.actor_type,
                actor_roles=context.actor_roles,
                linked_artifact_count=_linked_count(
                    counts=link_counts,
                    subject_kind="human_task",
                    subject_id=subject_id,
                ),
                requirement_state=requirement_index.get(subject_id),
            )
            work_items.append(
                {
                    "item_id": f"human_task:{subject_id}",
                    "item_type": "human_task",
                    "lane": _human_task_lane(str(task["state"])),
                    "title": f"{task['stage_id']} {task['task_kind']}",
                    "workflow_run_id": workflow_run_id,
                    "workflow_id": str(workflow_run["workflow_id"]),
                    "subject_id": subject_id,
                    "stage_id": str(task["stage_id"]),
                    "task_kind": str(task["task_kind"]),
                    "state": str(task["state"]),
                    "owner_role": task.get("owner_role"),
                    "available_actions": actionability["available_actions"],
                    "blocking_reason_codes": actionability["blocking_reason_codes"],
                    "missing_required_inputs": actionability["missing_required_inputs"],
                    "linked_artifact_count": actionability["linked_artifact_count"],
                }
            )

        for approval in approvals:
            subject_id = str(approval["approval_id"])
            actionability = compute_approval_actionability(
                approval=approval,
                actor_roles=context.actor_roles,
                linked_artifact_count=_linked_count(
                    counts=link_counts,
                    subject_kind="approval",
                    subject_id=subject_id,
                ),
            )
            work_items.append(
                {
                    "item_id": f"approval:{subject_id}",
                    "item_type": "approval",
                    "lane": _approval_lane(str(approval["state"])),
                    "title": f"{approval['approval_kind']} {approval['scope_ref']}",
                    "workflow_run_id": workflow_run_id,
                    "workflow_id": str(workflow_run["workflow_id"]),
                    "subject_id": subject_id,
                    "approval_kind": str(approval["approval_kind"]),
                    "scope_kind": str(approval["scope_kind"]),
                    "scope_ref": str(approval["scope_ref"]),
                    "state": str(approval["state"]),
                    "required_role": approval.get("required_role"),
                    "available_actions": actionability["available_actions"],
                    "blocking_reason_codes": actionability["blocking_reason_codes"],
                    "missing_required_inputs": actionability["missing_required_inputs"],
                    "linked_artifact_count": actionability["linked_artifact_count"],
                }
            )

        for flag in flags:
            subject_id = str(flag["flag_id"])
            actionability = compute_flag_actionability(
                flag=flag,
                actor_roles=context.actor_roles,
                linked_artifact_count=_linked_count(
                    counts=link_counts,
                    subject_kind="flag",
                    subject_id=subject_id,
                ),
            )
            work_items.append(
                {
                    "item_id": f"flag:{subject_id}",
                    "item_type": "flag",
                    "lane": _flag_lane(str(flag["state"])),
                    "title": str(flag["summary"]),
                    "workflow_run_id": workflow_run_id,
                    "workflow_id": str(workflow_run["workflow_id"]),
                    "subject_id": subject_id,
                    "kind": str(flag["kind"]),
                    "severity": str(flag["severity"]),
                    "state": str(flag["state"]),
                    "available_actions": actionability["available_actions"],
                    "blocking_reason_codes": actionability["blocking_reason_codes"],
                    "missing_required_inputs": actionability["missing_required_inputs"],
                    "linked_artifact_count": actionability["linked_artifact_count"],
                }
            )

    work_items.sort(key=_board_item_sort_key)
    lane_counts = {lane: 0 for lane in _LANE_ORDER}
    for item in work_items:
        lane_counts[str(item["lane"])] += 1

    paged_items = work_items[page.offset : page.offset + page.limit]
    lanes = [
        {
            "lane": lane,
            "label": _LANE_LABELS[lane],
            "position": _LANE_ORDER[lane],
            "item_count": lane_counts[lane],
        }
        for lane in sorted(_LANE_ORDER, key=_LANE_ORDER.get)
    ]
    workflow_counts = Counter(str(item["workflow_id"]) for item in work_items)
    board = {
        "lanes": lanes,
        "work_items": paged_items,
        "page": {"limit": page.limit, "offset": page.offset},
        "summary": {
            "work_item_count": len(work_items),
            "human_task_count": sum(1 for item in work_items if item["item_type"] == "human_task"),
            "approval_count": sum(1 for item in work_items if item["item_type"] == "approval"),
            "flag_count": sum(1 for item in work_items if item["item_type"] == "flag"),
            "primary_actionable_count": sum(
                1
                for item in work_items
                if _PRIMARY_ACTIONS.intersection(set(item["available_actions"]))
            ),
            "workflow_item_counts": dict(workflow_counts),
        },
    }
    return board, artifacts_by_run_id


def _build_official_outputs_summary(
    connection: sqlite3.Connection,
    *,
    context: RequestContext,
    run_ids: list[str],
    artifacts_by_run_id: dict[str, list[dict[str, Any]]],
) -> dict[str, Any]:
    artifacts_by_id: dict[str, dict[str, Any]] = {}
    for run_id in run_ids:
        for artifact in artifacts_by_run_id.get(run_id, []):
            artifacts_by_id[str(artifact["artifact_version_id"])] = artifact

    pointers = _list_story_pointers(
        connection,
        context=context,
        run_ids=run_ids,
    )
    missing_artifact_ids = sorted(
        {
            str(pointer.get("artifact_version_id"))
            for pointer in pointers
            if str(pointer.get("artifact_version_id")) not in artifacts_by_id
        }
    )
    if missing_artifact_ids:
        artifacts_by_id.update(
            _load_scoped_artifacts_by_id(
                connection,
                tenant_id=context.tenant_id,
                domain_id=context.domain_id,
                artifact_version_ids=missing_artifact_ids,
            )
        )

    pointer_outputs = [
        {
            "pointer": pointer,
            "artifact_version": artifacts_by_id.get(str(pointer.get("artifact_version_id"))),
        }
        for pointer in pointers
    ]
    coherence = evaluate_official_outputs_coherence(
        projection_id="story_official_outputs",
        projection_kind="story_official_outputs",
        outputs=pointer_outputs,
        policy_on_drift=COHERENCE_POLICY_WARN_VISIBLE,
    )
    official_output_artifacts = [
        artifact
        for artifact in artifacts_by_id.values()
        if str(artifact.get("artifact_role") or "") == "official_output"
    ]
    artifact_kind_counts = Counter(
        str(artifact["artifact_kind"]) for artifact in official_output_artifacts
    )
    return {
        "pointers": pointers,
        "pointer_outputs": pointer_outputs,
        "official_output_artifacts": _stable_artifact_sort(official_output_artifacts),
        "coherence": coherence,
        "summary": {
            "pointer_count": len(pointers),
            "pointer_output_count": len(pointer_outputs),
            "official_output_artifact_count": len(official_output_artifacts),
            "artifact_kind_counts": dict(artifact_kind_counts),
        },
    }


def _list_story_pointers(
    connection: sqlite3.Connection,
    *,
    context: RequestContext,
    run_ids: list[str],
) -> list[dict[str, Any]]:
    deduped: dict[str, dict[str, Any]] = {}
    for run_id in run_ids:
        rows = query_pointers(
            connection,
            context=context,
            pointer_id=None,
            pointer_key=None,
            workflow_run_id=run_id,
            dataset_key=None,
            partition_kind=None,
            partition_key=None,
            stream_key=None,
            registry_kind=None,
            scope_kind=None,
            scope_ref=None,
            artifact_kind=None,
            page=_SOURCE_PAGE,
        )
        for row in rows:
            deduped[str(row["pointer_id"])] = row
    return sorted(
        deduped.values(),
        key=lambda item: (
            str(item.get("updated_at") or ""),
            str(item.get("pointer_id") or ""),
        ),
        reverse=True,
    )


def _story_freshness(
    connection: sqlite3.Connection,
    *,
    context: RequestContext,
    run_ids: list[str],
) -> dict[str, Any]:
    latest_event_sequence: int | None = None
    latest_event_recorded_at: str | None = None
    max_run_updated_at: str | None = None
    if run_ids:
        placeholders = ",".join("?" for _ in run_ids)
        event_row = connection.execute(
            f"""
            SELECT
                MAX(sequence_no) AS latest_event_sequence,
                MAX(recorded_at) AS latest_event_recorded_at
            FROM timeline_events
            WHERE tenant_id = ?
              AND domain_id = ?
              AND workflow_run_id IN ({placeholders})
            """,
            (context.tenant_id, context.domain_id, *run_ids),
        ).fetchone()
        if event_row is not None and event_row["latest_event_sequence"] is not None:
            latest_event_sequence = int(event_row["latest_event_sequence"])
        if event_row is not None and event_row["latest_event_recorded_at"] is not None:
            latest_event_recorded_at = str(event_row["latest_event_recorded_at"])

        run_row = connection.execute(
            f"""
            SELECT MAX(updated_at) AS max_run_updated_at
            FROM workflow_runs
            WHERE tenant_id = ?
              AND domain_id = ?
              AND workflow_run_id IN ({placeholders})
            """,
            (context.tenant_id, context.domain_id, *run_ids),
        ).fetchone()
        if run_row is not None and run_row["max_run_updated_at"] is not None:
            max_run_updated_at = str(run_row["max_run_updated_at"])
    return {
        "latest_event_sequence": latest_event_sequence,
        "latest_event_recorded_at": latest_event_recorded_at,
        "max_workflow_run_updated_at": max_run_updated_at,
        "generated_at": utc_now_iso(),
    }


def _derive_service_dates(*, edge_rows: list[dict[str, Any]]) -> set[str]:
    values: set[str] = set()
    for edge in edge_rows:
        if str(edge["edge_id"]) == "weekly_seed_to_live_dispatch":
            values.add(str(edge["target_partition_key"]))
        elif str(edge["edge_id"]) == "reporting_actuals_to_future_planning":
            source_partition_key = str(edge.get("source_partition_key") or "")
            if source_partition_key:
                values.add(source_partition_key)
    return values


def _stable_run_sort(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    deduped = {str(row["workflow_run_id"]): row for row in rows}
    return sorted(
        deduped.values(),
        key=lambda item: (
            str(item.get("created_at") or ""),
            str(item.get("workflow_run_id") or ""),
        ),
    )


def _stable_artifact_sort(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return sorted(
        rows,
        key=lambda item: (
            str(item.get("created_at") or ""),
            str(item.get("artifact_version_id") or ""),
        ),
    )


def _load_scoped_artifacts_by_id(
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
        WHERE tenant_id = ?
          AND domain_id = ?
          AND artifact_version_id IN ({placeholders})
        """,
        (tenant_id, domain_id, *artifact_version_ids),
    ).fetchall()
    loaded: dict[str, dict[str, Any]] = {}
    for row in rows:
        item = dict(row)
        item["metadata_json"] = json.loads(str(item["metadata_json"]))
        loaded[str(item["artifact_version_id"])] = item
    return loaded


def _decode_edge_row(item: dict[str, Any]) -> dict[str, Any]:
    if item.get("cursor_state_json") is not None:
        item["cursor_state"] = json.loads(str(item["cursor_state_json"]))
    else:
        item["cursor_state"] = None
    if item.get("compensation_state_json") is not None:
        item["compensation_state"] = json.loads(str(item["compensation_state_json"]))
    else:
        item["compensation_state"] = None
    if item.get("input_bindings_json") is not None:
        item["input_bindings"] = json.loads(str(item["input_bindings_json"]))
    else:
        item["input_bindings"] = None
    item.pop("cursor_state_json", None)
    item.pop("compensation_state_json", None)
    item.pop("input_bindings_json", None)
    return item


def _linked_count(
    *,
    counts: dict[tuple[str, str], int],
    subject_kind: str,
    subject_id: str,
) -> int:
    return int(counts.get((subject_kind, subject_id), 0))


def _human_task_lane(state: str) -> str:
    if state == "OPEN":
        return "human_tasks.open"
    if state == "CLAIMED":
        return "human_tasks.claimed"
    return "human_tasks.completed"


def _approval_lane(state: str) -> str:
    if state == "PENDING":
        return "approvals.pending"
    return "approvals.responded"


def _flag_lane(state: str) -> str:
    if state in {"open", "triage", "blocked"}:
        return "flags.open"
    if state == "resolved":
        return "flags.resolved"
    return "flags.closed"


def _board_item_sort_key(item: dict[str, Any]) -> tuple[Any, ...]:
    lane = str(item["lane"])
    lane_position = _LANE_ORDER.get(lane, 999)
    if item["item_type"] == "human_task":
        due_at = item.get("due_at") or "9999-12-31T23:59:59Z"
        return (
            lane_position,
            due_at,
            str(item.get("title") or ""),
            str(item["item_id"]),
        )
    if item["item_type"] == "flag":
        severity_rank = {
            "critical": 0,
            "high": 1,
            "medium": 2,
            "low": 3,
            "info": 4,
        }.get(str(item.get("severity")), 9)
        return (
            lane_position,
            severity_rank,
            str(item.get("title") or ""),
            str(item["item_id"]),
        )
    return (
        lane_position,
        str(item.get("title") or ""),
        str(item["item_id"]),
    )


@lru_cache(maxsize=1)
def _load_story_contract() -> dict[str, Any]:
    if not _STORY_CONTRACT_PATH.exists():
        raise ApiError(
            status_code=500,
            code="story_contract_missing",
            message="three-workflow demo story contract file is missing",
            details={"path": str(_STORY_CONTRACT_PATH)},
        )
    with _STORY_CONTRACT_PATH.open("r", encoding="utf-8") as handle:
        loaded = yaml.safe_load(handle)
    if not isinstance(loaded, dict):
        raise ApiError(
            status_code=500,
            code="story_contract_invalid",
            message="story contract must parse as an object",
            details={"path": str(_STORY_CONTRACT_PATH)},
        )
    story = loaded.get("story")
    if not isinstance(story, dict):
        raise ApiError(
            status_code=500,
            code="story_contract_invalid",
            message="story contract must include story object",
            details={"path": str(_STORY_CONTRACT_PATH)},
        )
    try:
        story_id = str(story["id"])
        family_id = str(story["family_id"])
        workflow_ids = story["workflow_ids"]
        edge_ids = list(story["edge_ids"])
        module_ids = list(story["module_ids"])
        contract_version = int(story.get("version", 1))
    except (KeyError, TypeError, ValueError) as exc:
        raise ApiError(
            status_code=500,
            code="story_contract_invalid",
            message="story contract is missing required fields",
            details={"path": str(_STORY_CONTRACT_PATH)},
        ) from exc
    if not isinstance(workflow_ids, dict):
        raise ApiError(
            status_code=500,
            code="story_contract_invalid",
            message="story.workflow_ids must be an object",
            details={"path": str(_STORY_CONTRACT_PATH)},
        )
    if not edge_ids or not module_ids:
        raise ApiError(
            status_code=500,
            code="story_contract_invalid",
            message="story.edge_ids and story.module_ids must be non-empty",
            details={"path": str(_STORY_CONTRACT_PATH)},
        )
    return {
        "story_id": story_id,
        "family_id": family_id,
        "contract_version": contract_version,
        "workflow_ids": workflow_ids,
        "edge_ids": tuple(str(item) for item in edge_ids),
        "module_ids": tuple(str(item) for item in module_ids),
    }


@lru_cache(maxsize=1)
def _compiled_family_graph() -> dict[str, Any]:
    contract = _load_story_contract()
    try:
        compiled = compile_workflow_family(
            repo_root=_REPO_ROOT,
            family_path=_LOGISTICS_FAMILY_PATH,
            partition_transforms_path=_LOGISTICS_TRANSFORMS_PATH,
        )
    except DefinitionCompileError as exc:
        raise ApiError(
            status_code=500,
            code="family_compilation_failed",
            message="failed to compile logistics workflow family for story projection",
            details={"error": str(exc)},
        ) from exc

    modules = []
    for module in compiled.get("compiled_modules") or []:
        if not isinstance(module, dict):
            continue
        module_id = str(module.get("module_id") or "")
        if module_id not in contract["module_ids"]:
            continue
        source_workflow = module.get("source_workflow") or {}
        partition = module.get("partition") or {}
        modules.append(
            {
                "module_id": module_id,
                "workflow_id": str(source_workflow.get("workflow_id") or ""),
                "partition_kind": str(partition.get("kind") or ""),
                "activation_policy": str(partition.get("activation_policy") or ""),
                "status": str(module.get("status") or ""),
            }
        )
    edges = []
    for edge in compiled.get("compiled_edges") or []:
        if not isinstance(edge, dict):
            continue
        edge_id = str(edge.get("edge_id") or "")
        if edge_id not in contract["edge_ids"]:
            continue
        source_ref = edge.get("source_output_ref") or {}
        target_ref = edge.get("target_input_ref") or {}
        transform = edge.get("partition_transform") or {}
        edges.append(
            {
                "edge_id": edge_id,
                "source_module_id": str(edge.get("source_module_id") or ""),
                "target_module_id": str(edge.get("target_module_id") or ""),
                "source_stage_id": str(source_ref.get("stage_id") or ""),
                "source_dataset_key": str(source_ref.get("dataset_key") or ""),
                "target_stage_id": str(target_ref.get("stage_id") or ""),
                "target_dataset_key": str(target_ref.get("dataset_key") or ""),
                "partition_transform_id": str(transform.get("id") or ""),
                "handoff_mode": str(edge.get("handoff_mode") or ""),
                "writer_mode": str(edge.get("writer_mode") or ""),
                "status": str(edge.get("status") or ""),
            }
        )
    return {
        "family_id": str(compiled.get("family_id") or contract["family_id"]),
        "family_version": int(compiled.get("family_version") or 1),
        "modules": sorted(modules, key=lambda item: item["module_id"]),
        "edges": sorted(edges, key=lambda item: item["edge_id"]),
    }
