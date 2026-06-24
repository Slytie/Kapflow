from __future__ import annotations

from collections.abc import Callable, Iterable
from dataclasses import dataclass
import json
import re
import sqlite3
from typing import Any


MAX_RUNTIME_OUTBOX_BATCH_SIZE = 500
_CONSUMER_NAME_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.:-]{0,127}$")


@dataclass(frozen=True)
class RuntimeOutboxError(ValueError):
    code: str
    details: dict[str, Any]

    def __str__(self) -> str:
        return self.code


def get_runtime_outbox_cursor(
    connection: sqlite3.Connection,
    *,
    consumer_name: str,
    tenant_id: str,
    domain_id: str,
) -> dict[str, Any]:
    _validate_scope(
        consumer_name=consumer_name,
        tenant_id=tenant_id,
        domain_id=domain_id,
    )
    row = connection.execute(
        """
        SELECT consumer_name, tenant_id, domain_id, last_sequence_no, updated_at
        FROM consumer_cursors
        WHERE consumer_name = ?
          AND tenant_id = ?
          AND domain_id = ?
        """,
        (consumer_name, tenant_id, domain_id),
    ).fetchone()
    if row is None:
        return {
            "consumer_name": consumer_name,
            "tenant_id": tenant_id,
            "domain_id": domain_id,
            "last_sequence_no": 0,
            "updated_at": None,
        }
    return dict(row)


def list_runtime_outbox_events(
    connection: sqlite3.Connection,
    *,
    consumer_name: str,
    tenant_id: str,
    domain_id: str,
    limit: int = 100,
) -> list[dict[str, Any]]:
    cursor = get_runtime_outbox_cursor(
        connection,
        consumer_name=consumer_name,
        tenant_id=tenant_id,
        domain_id=domain_id,
    )
    return _list_events_after_sequence(
        connection,
        tenant_id=tenant_id,
        domain_id=domain_id,
        after_sequence_no=int(cursor["last_sequence_no"]),
        limit=_validate_limit(limit),
    )


def dispatch_runtime_outbox_batch(
    connection: sqlite3.Connection,
    *,
    consumer_name: str,
    tenant_id: str,
    domain_id: str,
    dispatch: Callable[[dict[str, Any]], None],
    limit: int = 100,
    event_types: Iterable[str] | None = None,
    dispatched_at: str,
) -> dict[str, Any]:
    if not callable(dispatch):
        raise RuntimeOutboxError(
            code="runtime_outbox_dispatcher_invalid",
            details={"consumer_name": consumer_name},
        )
    allowed_event_types = _normalize_event_types(event_types)
    cursor = get_runtime_outbox_cursor(
        connection,
        consumer_name=consumer_name,
        tenant_id=tenant_id,
        domain_id=domain_id,
    )
    starting_sequence_no = int(cursor["last_sequence_no"])
    events = _list_events_after_sequence(
        connection,
        tenant_id=tenant_id,
        domain_id=domain_id,
        after_sequence_no=starting_sequence_no,
        limit=_validate_limit(limit),
    )
    dispatched: list[dict[str, Any]] = []
    skipped_sequence_nos: list[int] = []
    last_successful_sequence_no = starting_sequence_no

    for event in events:
        sequence_no = int(event["sequence_no"])
        if allowed_event_types is not None and event["event_type"] not in allowed_event_types:
            skipped_sequence_nos.append(sequence_no)
            last_successful_sequence_no = sequence_no
            continue
        try:
            dispatch(event)
        except Exception as exc:
            _advance_runtime_outbox_cursor(
                connection,
                consumer_name=consumer_name,
                tenant_id=tenant_id,
                domain_id=domain_id,
                last_sequence_no=last_successful_sequence_no,
                updated_at=dispatched_at,
            )
            raise RuntimeOutboxError(
                code="runtime_outbox_dispatch_failed",
                details={
                    "consumer_name": consumer_name,
                    "tenant_id": tenant_id,
                    "domain_id": domain_id,
                    "failed_sequence_no": sequence_no,
                    "failed_event_id": event["event_id"],
                    "error_type": type(exc).__name__,
                },
            ) from exc
        dispatched.append(event)
        last_successful_sequence_no = sequence_no

    _advance_runtime_outbox_cursor(
        connection,
        consumer_name=consumer_name,
        tenant_id=tenant_id,
        domain_id=domain_id,
        last_sequence_no=last_successful_sequence_no,
        updated_at=dispatched_at,
    )
    return {
        "consumer_name": consumer_name,
        "tenant_id": tenant_id,
        "domain_id": domain_id,
        "starting_sequence_no": starting_sequence_no,
        "last_sequence_no": last_successful_sequence_no,
        "dispatched_events": dispatched,
        "skipped_sequence_nos": skipped_sequence_nos,
    }


def _advance_runtime_outbox_cursor(
    connection: sqlite3.Connection,
    *,
    consumer_name: str,
    tenant_id: str,
    domain_id: str,
    last_sequence_no: int,
    updated_at: str,
) -> None:
    current = get_runtime_outbox_cursor(
        connection,
        consumer_name=consumer_name,
        tenant_id=tenant_id,
        domain_id=domain_id,
    )
    current_sequence = int(current["last_sequence_no"])
    if last_sequence_no < current_sequence:
        raise RuntimeOutboxError(
            code="runtime_outbox_cursor_rewind",
            details={
                "consumer_name": consumer_name,
                "current_sequence_no": current_sequence,
                "requested_sequence_no": last_sequence_no,
            },
        )
    connection.execute(
        """
        INSERT INTO consumer_cursors (
            consumer_name,
            tenant_id,
            domain_id,
            last_sequence_no,
            updated_at
        )
        VALUES (?, ?, ?, ?, ?)
        ON CONFLICT(consumer_name, tenant_id, domain_id)
        DO UPDATE SET
            last_sequence_no = excluded.last_sequence_no,
            updated_at = excluded.updated_at
        """,
        (consumer_name, tenant_id, domain_id, last_sequence_no, updated_at),
    )


def _list_events_after_sequence(
    connection: sqlite3.Connection,
    *,
    tenant_id: str,
    domain_id: str,
    after_sequence_no: int,
    limit: int,
) -> list[dict[str, Any]]:
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
            workflow_run_id,
            project_id,
            actor,
            links,
            payload,
            correlation_id,
            causation_id,
            idempotency_key,
            integrity,
            created_at
        FROM timeline_events
        WHERE tenant_id = ?
          AND domain_id = ?
          AND sequence_no > ?
        ORDER BY sequence_no ASC
        LIMIT ?
        """,
        (tenant_id, domain_id, after_sequence_no, limit),
    ).fetchall()
    return [_event_from_row(dict(row)) for row in rows]


def _event_from_row(row: dict[str, Any]) -> dict[str, Any]:
    for field in ("actor", "links", "payload", "integrity"):
        if row.get(field) is not None:
            row[field] = json.loads(row[field])
    return row


def _normalize_event_types(event_types: Iterable[str] | None) -> set[str] | None:
    if event_types is None:
        return None
    normalized = {str(event_type).strip() for event_type in event_types if str(event_type).strip()}
    if not normalized:
        raise RuntimeOutboxError(
            code="runtime_outbox_event_types_invalid",
            details={"event_types": []},
        )
    return normalized


def _validate_limit(limit: int) -> int:
    if not isinstance(limit, int) or limit < 1 or limit > MAX_RUNTIME_OUTBOX_BATCH_SIZE:
        raise RuntimeOutboxError(
            code="runtime_outbox_limit_invalid",
            details={
                "limit": limit,
                "max_limit": MAX_RUNTIME_OUTBOX_BATCH_SIZE,
            },
        )
    return limit


def _validate_scope(
    *,
    consumer_name: str,
    tenant_id: str,
    domain_id: str,
) -> None:
    if _CONSUMER_NAME_RE.fullmatch(str(consumer_name)) is None:
        raise RuntimeOutboxError(
            code="runtime_outbox_consumer_invalid",
            details={"consumer_name": consumer_name},
        )
    if not str(tenant_id).strip() or not str(domain_id).strip():
        raise RuntimeOutboxError(
            code="runtime_outbox_scope_invalid",
            details={"tenant_id": tenant_id, "domain_id": domain_id},
        )
