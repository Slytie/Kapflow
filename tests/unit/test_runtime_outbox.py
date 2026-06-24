from __future__ import annotations

import sqlite3

import pytest

from onetruth.infrastructure.events.event_store import append_event, create_sqlite_substrate
from onetruth.infrastructure.repositories.runtime_outbox import (
    MAX_RUNTIME_OUTBOX_BATCH_SIZE,
    RuntimeOutboxError,
    dispatch_runtime_outbox_batch,
    get_runtime_outbox_cursor,
    list_runtime_outbox_events,
)


NOW = "2026-06-23T00:00:00Z"


def _connection(path: str = ":memory:") -> sqlite3.Connection:
    connection = sqlite3.connect(path)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON;")
    create_sqlite_substrate(connection)
    return connection


def _append_event(
    connection: sqlite3.Connection,
    *,
    event_id: str,
    event_type: str = "runtime.outbox.test",
    tenant_id: str = "tenant-a",
    domain_id: str = "domain-x",
) -> None:
    append_event(
        connection,
        {
            "event_id": event_id,
            "event_type": event_type,
            "schema_version": "runtime.outbox.test.v1",
            "occurred_at": NOW,
            "recorded_at": NOW,
            "tenant_id": tenant_id,
            "domain_id": domain_id,
            "actor": {"type": "system", "id": "system:runtime-outbox-test"},
            "links": [],
            "payload": {"event_id": event_id},
        },
    )


def test_runtime_outbox_reads_only_committed_timeline_events(tmp_path) -> None:
    db_path = str(tmp_path / "runtime-outbox.sqlite")
    writer = _connection(db_path)
    reader = sqlite3.connect(db_path)
    reader.row_factory = sqlite3.Row
    try:
        _append_event(writer, event_id="evt-uncommitted")

        assert (
            list_runtime_outbox_events(
                reader,
                consumer_name="consumer.alpha",
                tenant_id="tenant-a",
                domain_id="domain-x",
            )
            == []
        )

        writer.commit()
        events = list_runtime_outbox_events(
            reader,
            consumer_name="consumer.alpha",
            tenant_id="tenant-a",
            domain_id="domain-x",
        )
        assert [event["event_id"] for event in events] == ["evt-uncommitted"]
    finally:
        writer.close()
        reader.close()


def test_dispatch_advances_cursor_and_replay_returns_no_duplicate_events() -> None:
    connection = _connection()
    try:
        for index in range(1, 4):
            _append_event(connection, event_id=f"evt-{index:03d}")

        dispatched: list[str] = []
        result = dispatch_runtime_outbox_batch(
            connection,
            consumer_name="consumer.alpha",
            tenant_id="tenant-a",
            domain_id="domain-x",
            dispatch=lambda event: dispatched.append(str(event["event_id"])),
            dispatched_at=NOW,
        )

        assert dispatched == ["evt-001", "evt-002", "evt-003"]
        assert result["last_sequence_no"] == 3
        assert get_runtime_outbox_cursor(
            connection,
            consumer_name="consumer.alpha",
            tenant_id="tenant-a",
            domain_id="domain-x",
        )["last_sequence_no"] == 3

        replayed: list[str] = []
        replay = dispatch_runtime_outbox_batch(
            connection,
            consumer_name="consumer.alpha",
            tenant_id="tenant-a",
            domain_id="domain-x",
            dispatch=lambda event: replayed.append(str(event["event_id"])),
            dispatched_at=NOW,
        )
        assert replayed == []
        assert replay["dispatched_events"] == []
        assert replay["last_sequence_no"] == 3
    finally:
        connection.close()


def test_event_type_filter_skips_events_and_advances_past_skipped_rows() -> None:
    connection = _connection()
    try:
        _append_event(connection, event_id="evt-keep-1", event_type="runtime.keep")
        _append_event(connection, event_id="evt-skip", event_type="runtime.skip")
        _append_event(connection, event_id="evt-keep-2", event_type="runtime.keep")

        dispatched: list[str] = []
        result = dispatch_runtime_outbox_batch(
            connection,
            consumer_name="consumer.filtered",
            tenant_id="tenant-a",
            domain_id="domain-x",
            event_types={"runtime.keep"},
            dispatch=lambda event: dispatched.append(str(event["event_id"])),
            dispatched_at=NOW,
        )

        assert dispatched == ["evt-keep-1", "evt-keep-2"]
        assert result["skipped_sequence_nos"] == [2]
        assert result["last_sequence_no"] == 3
    finally:
        connection.close()


def test_dispatch_failure_leaves_cursor_before_failed_event_for_retry() -> None:
    connection = _connection()
    try:
        for index in range(1, 4):
            _append_event(connection, event_id=f"evt-{index:03d}")
        dispatched: list[str] = []

        def _failing_dispatch(event: dict[str, object]) -> None:
            dispatched.append(str(event["event_id"]))
            if event["event_id"] == "evt-002":
                raise RuntimeError("boom")

        with pytest.raises(RuntimeOutboxError) as exc_info:
            dispatch_runtime_outbox_batch(
                connection,
                consumer_name="consumer.retry",
                tenant_id="tenant-a",
                domain_id="domain-x",
                dispatch=_failing_dispatch,
                dispatched_at=NOW,
            )

        assert exc_info.value.code == "runtime_outbox_dispatch_failed"
        assert dispatched == ["evt-001", "evt-002"]
        assert get_runtime_outbox_cursor(
            connection,
            consumer_name="consumer.retry",
            tenant_id="tenant-a",
            domain_id="domain-x",
        )["last_sequence_no"] == 1

        retried: list[str] = []
        dispatch_runtime_outbox_batch(
            connection,
            consumer_name="consumer.retry",
            tenant_id="tenant-a",
            domain_id="domain-x",
            dispatch=lambda event: retried.append(str(event["event_id"])),
            dispatched_at=NOW,
        )
        assert retried == ["evt-002", "evt-003"]
    finally:
        connection.close()


def test_runtime_outbox_scope_validation_limits_and_no_second_outbox_table() -> None:
    connection = _connection()
    try:
        _append_event(connection, event_id="evt-a", tenant_id="tenant-a")
        _append_event(connection, event_id="evt-b", tenant_id="tenant-b")

        assert [
            event["event_id"]
            for event in list_runtime_outbox_events(
                connection,
                consumer_name="consumer.alpha",
                tenant_id="tenant-a",
                domain_id="domain-x",
            )
        ] == ["evt-a"]

        with pytest.raises(RuntimeOutboxError) as bad_limit:
            list_runtime_outbox_events(
                connection,
                consumer_name="consumer.alpha",
                tenant_id="tenant-a",
                domain_id="domain-x",
                limit=MAX_RUNTIME_OUTBOX_BATCH_SIZE + 1,
            )
        assert bad_limit.value.code == "runtime_outbox_limit_invalid"

        with pytest.raises(RuntimeOutboxError) as bad_consumer:
            list_runtime_outbox_events(
                connection,
                consumer_name="bad consumer name",
                tenant_id="tenant-a",
                domain_id="domain-x",
            )
        assert bad_consumer.value.code == "runtime_outbox_consumer_invalid"

        dispatch_runtime_outbox_batch(
            connection,
            consumer_name="consumer.empty",
            tenant_id="tenant-a",
            domain_id="domain-x",
            limit=1,
            event_types={"runtime.missing"},
            dispatch=lambda event: None,
            dispatched_at=NOW,
        )
        dispatch_runtime_outbox_batch(
            connection,
            consumer_name="consumer.empty",
            tenant_id="tenant-a",
            domain_id="domain-x",
            limit=1,
            event_types={"runtime.missing"},
            dispatch=lambda event: None,
            dispatched_at=NOW,
        )
        cursor_count = connection.execute(
            """
            SELECT COUNT(*) AS row_count
            FROM consumer_cursors
            WHERE consumer_name = 'consumer.empty'
            """
        ).fetchone()["row_count"]
        assert cursor_count == 1

        table_names = {
            str(row["name"])
            for row in connection.execute(
                """
                SELECT name
                FROM sqlite_master
                WHERE type = 'table'
                """
            ).fetchall()
        }
        assert "runtime_outbox" not in table_names
        assert "runtime_outbox_events" not in table_names
    finally:
        connection.close()
