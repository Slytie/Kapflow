from __future__ import annotations

import json
import sqlite3
from typing import Any

from onetruth.api.dependencies import Page, RequestContext, scoped_workflow_run


def list_timeline_events_endpoint(
    connection: sqlite3.Connection,
    *,
    context: RequestContext,
    query: dict[str, str],
    page: Page,
) -> dict[str, Any]:
    workflow_run_id = query.get("workflow_run_id")
    if workflow_run_id is not None:
        scoped_workflow_run(connection, context, workflow_run_id)
    event_type = query.get("event_type")
    rows = query_timeline_events(
        connection,
        tenant_id=context.tenant_id,
        domain_id=context.domain_id,
        workflow_run_id=workflow_run_id,
        event_type=event_type,
        page=page,
    )
    return {
        "command": "api.timeline_events.list",
        "events": rows,
        "page": {"limit": page.limit, "offset": page.offset},
    }


def query_timeline_events(
    connection: sqlite3.Connection,
    *,
    tenant_id: str,
    domain_id: str,
    workflow_run_id: str | None,
    event_type: str | None,
    page: Page,
) -> list[dict[str, Any]]:
    query = """
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
    """
    params: list[Any] = [tenant_id, domain_id]

    if workflow_run_id is not None:
        query += " AND workflow_run_id = ?"
        params.append(workflow_run_id)
    if event_type is not None:
        query += " AND event_type = ?"
        params.append(event_type)

    query += " ORDER BY sequence_no DESC LIMIT ? OFFSET ?"
    params.extend([page.limit, page.offset])

    rows = connection.execute(query, params).fetchall()
    return [_timeline_row_to_payload(row) for row in rows]


def list_workflow_run_timeline_endpoint(
    connection: sqlite3.Connection,
    *,
    context: RequestContext,
    workflow_run_id: str,
    query: dict[str, str],
    page: Page,
) -> dict[str, Any]:
    scoped_workflow_run(connection, context, workflow_run_id)

    since_event_id = query.get("since_event_id")
    event_type = query.get("event_type")
    rows = query_workflow_run_timeline(
        connection,
        workflow_run_id=workflow_run_id,
        tenant_id=context.tenant_id,
        domain_id=context.domain_id,
        since_event_id=since_event_id,
        event_type=event_type,
        page=page,
    )
    return {
        "command": "api.workflow_runs.timeline",
        "workflow_run_id": workflow_run_id,
        "events": rows,
        "page": {"limit": page.limit, "offset": page.offset},
        "since_event_id": since_event_id,
        "event_type": event_type,
    }


def query_workflow_run_timeline(
    connection: sqlite3.Connection,
    *,
    workflow_run_id: str,
    tenant_id: str,
    domain_id: str,
    since_event_id: str | None,
    event_type: str | None,
    page: Page,
) -> list[dict[str, Any]]:
    since_sequence_no: int | None = None
    if since_event_id is not None:
        row = connection.execute(
            """
            SELECT sequence_no
            FROM timeline_events
            WHERE event_id = ?
                AND workflow_run_id = ?
                AND tenant_id = ?
                AND domain_id = ?
            """,
            (since_event_id, workflow_run_id, tenant_id, domain_id),
        ).fetchone()
        if row is None:
            return []
        since_sequence_no = int(row["sequence_no"])

    query = """
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
        WHERE workflow_run_id = ?
            AND tenant_id = ?
            AND domain_id = ?
    """
    params: list[Any] = [workflow_run_id, tenant_id, domain_id]

    if since_sequence_no is not None:
        query += " AND sequence_no > ?"
        params.append(since_sequence_no)
    if event_type is not None:
        query += " AND event_type = ?"
        params.append(event_type)

    query += " ORDER BY sequence_no ASC LIMIT ? OFFSET ?"
    params.extend([page.limit, page.offset])

    rows = connection.execute(query, params).fetchall()
    return [_timeline_row_to_payload(row) for row in rows]


def _timeline_row_to_payload(row: sqlite3.Row) -> dict[str, Any]:
    item: dict[str, Any] = {
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
        item["correlation_id"] = str(row["correlation_id"])
    if row["causation_id"] is not None:
        item["causation_id"] = str(row["causation_id"])
    if row["idempotency_key"] is not None:
        item["idempotency_key"] = str(row["idempotency_key"])
    if row["integrity"] is not None:
        item["integrity"] = json.loads(row["integrity"])
    return item
