from __future__ import annotations

import sqlite3

import pytest

import onetruth.application.handlers._shared.command_boundary as command_boundary
import onetruth.application.handlers.execution_runtime as execution_runtime
import onetruth.application.handlers.workflow_task_lifecycle as lifecycle
from onetruth.application.handlers._shared.command_boundary import CommandError
from onetruth.infrastructure.events.event_store import create_sqlite_substrate, list_events
from onetruth.infrastructure.repositories.tool_execution_attempts import (
    complete_tool_execution_attempt,
    create_tool_execution_attempt,
    get_active_tool_execution_attempt,
    get_tool_execution_attempt,
)
from onetruth.infrastructure.repositories.tool_executions import get_tool_execution


NOW = "2026-06-23T00:00:00Z"


def _connection() -> sqlite3.Connection:
    connection = sqlite3.connect(":memory:")
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON;")
    create_sqlite_substrate(connection)
    return connection


def _freeze_time(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(command_boundary, "utc_now_iso", lambda: NOW)
    monkeypatch.setattr(execution_runtime, "utc_now_iso", lambda: NOW)
    monkeypatch.setattr(lifecycle, "utc_now_iso", lambda: NOW)


def _seed_approved_tool(connection: sqlite3.Connection) -> None:
    lifecycle.create_workflow_run_command(
        connection,
        {
            "workflow_run_id": "wr-attempt-001",
            "workflow_id": "schedule_planning.v1",
            "workflow_version": "v1",
            "tenant_id": "tenant-a",
            "domain_id": "domain-x",
            "partition_key": "SD-2026-06-23",
            "logical_date": "2026-06-23",
            "activation_key": "attempt-test",
        },
    )
    lifecycle.create_task_run_command(
        connection,
        {
            "workflow_run_id": "wr-attempt-001",
            "task_run_id": "tr-attempt-001",
            "stage_id": "Stage06",
            "task_kind": "review_packet",
            "activation_key": "attempt-task",
        },
    )
    execution_runtime.create_execution_session_command(
        connection,
        {
            "execution_session_id": "xs-attempt-001",
            "workflow_run_id": "wr-attempt-001",
            "task_run_id": "tr-attempt-001",
            "execution_spec_id": "execspec.attempt.test",
            "owner_mode": "agent",
            "state": "WAITING_POLICY",
            "principal_actor": {"type": "agent", "id": "agent:attempt"},
            "budget": {"max_tool_calls": 1},
            "idempotency_key": "idem:attempt:session",
            "actor_id": "agent:attempt",
            "actor_type": "agent",
        },
    )
    execution_runtime.request_tool_execution_command(
        connection,
        {
            "tool_execution_id": "tx-attempt-001",
            "execution_session_id": "xs-attempt-001",
            "tool_class": "model.openai.responses.stage06.review",
            "tool_name": "stage06_review",
            "idempotency_key": "idem:attempt:tool",
            "actor_id": "agent:attempt",
            "actor_type": "agent",
        },
    )
    execution_runtime.evaluate_policy_decision_command(
        connection,
        {
            "policy_decision_id": "pd-attempt-001",
            "tool_execution_id": "tx-attempt-001",
            "decision": "allow",
            "principal_actor": {"type": "agent", "id": "agent:attempt"},
            "idempotency_key": "idem:attempt:policy",
        },
    )


def _completion_event_count(connection: sqlite3.Connection) -> int:
    return sum(
        1
        for event in list_events(connection, run_id="wr-attempt-001")
        if event["event_type"] == "tool.execution.completed"
    )


def test_attempt_start_and_leased_completion_update_attempt_and_logical_tool(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _freeze_time(monkeypatch)
    connection = _connection()
    _seed_approved_tool(connection)

    attempt = execution_runtime.start_tool_execution_attempt_command(
        connection,
        {
            "tool_execution_attempt_id": "txa-attempt-001",
            "tool_execution_id": "tx-attempt-001",
            "lease_token": "lease-token-001",
        },
    )
    assert attempt["attempt_no"] == 1
    assert attempt["state"] == "RUNNING"
    assert get_tool_execution(connection, "tx-attempt-001")["state"] == "RUNNING"

    completed = execution_runtime.complete_tool_execution_command(
        connection,
        {
            "tool_execution_id": "tx-attempt-001",
            "tool_execution_attempt_id": "txa-attempt-001",
            "lease_token": "lease-token-001",
            "result": "succeeded",
            "idempotency_key": "idem:attempt:complete",
            "actor_id": "agent:attempt",
            "actor_type": "agent",
        },
    )

    attempt_row = get_tool_execution_attempt(connection, "txa-attempt-001")
    assert completed["state"] == "COMPLETED"
    assert attempt_row["state"] == "COMPLETED"
    assert attempt_row["active_tool_execution_id"] is None
    assert get_active_tool_execution_attempt(
        connection,
        tool_execution_id="tx-attempt-001",
    ) is None
    assert _completion_event_count(connection) == 1


def test_active_attempt_requires_matching_lease_and_does_not_emit_event_on_stale_completion(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _freeze_time(monkeypatch)
    connection = _connection()
    _seed_approved_tool(connection)
    execution_runtime.start_tool_execution_attempt_command(
        connection,
        {
            "tool_execution_attempt_id": "txa-attempt-001",
            "tool_execution_id": "tx-attempt-001",
            "lease_token": "lease-token-001",
        },
    )
    before_events = _completion_event_count(connection)

    with pytest.raises(CommandError) as excinfo:
        execution_runtime.complete_tool_execution_command(
            connection,
            {
                "tool_execution_id": "tx-attempt-001",
                "tool_execution_attempt_id": "txa-attempt-001",
                "lease_token": "stale-lease-token",
                "result": "succeeded",
                "idempotency_key": "idem:attempt:stale",
                "actor_id": "agent:attempt",
                "actor_type": "agent",
            },
        )

    assert excinfo.value.code == "tool_execution_attempt_stale_completion"
    assert get_tool_execution(connection, "tx-attempt-001")["state"] == "RUNNING"
    assert get_tool_execution_attempt(connection, "txa-attempt-001")["state"] == "RUNNING"
    assert _completion_event_count(connection) == before_events


def test_active_attempt_missing_lease_fails_closed_without_legacy_completion(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _freeze_time(monkeypatch)
    connection = _connection()
    _seed_approved_tool(connection)
    execution_runtime.start_tool_execution_attempt_command(
        connection,
        {
            "tool_execution_attempt_id": "txa-attempt-001",
            "tool_execution_id": "tx-attempt-001",
            "lease_token": "lease-token-001",
        },
    )

    with pytest.raises(CommandError) as excinfo:
        execution_runtime.complete_tool_execution_command(
            connection,
            {
                "tool_execution_id": "tx-attempt-001",
                "result": "succeeded",
                "idempotency_key": "idem:attempt:missing-lease",
                "actor_id": "agent:attempt",
                "actor_type": "agent",
            },
        )

    assert excinfo.value.code == "tool_execution_attempt_lease_required"
    assert _completion_event_count(connection) == 0


def test_legacy_completion_still_works_when_no_attempt_exists(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _freeze_time(monkeypatch)
    connection = _connection()
    _seed_approved_tool(connection)

    completed = execution_runtime.complete_tool_execution_command(
        connection,
        {
            "tool_execution_id": "tx-attempt-001",
            "result": "succeeded",
            "idempotency_key": "idem:attempt:legacy-complete",
            "actor_id": "agent:attempt",
            "actor_type": "agent",
        },
    )

    assert completed["state"] == "COMPLETED"
    assert _completion_event_count(connection) == 1


def test_one_active_attempt_guard_and_attempt_number_progression(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _freeze_time(monkeypatch)
    connection = _connection()
    _seed_approved_tool(connection)
    first = execution_runtime.start_tool_execution_attempt_command(
        connection,
        {
            "tool_execution_attempt_id": "txa-attempt-001",
            "tool_execution_id": "tx-attempt-001",
            "lease_token": "lease-token-001",
        },
    )
    replay = execution_runtime.start_tool_execution_attempt_command(
        connection,
        {
            "tool_execution_id": "tx-attempt-001",
            "lease_token": "lease-token-001",
        },
    )
    assert replay["tool_execution_attempt_id"] == first["tool_execution_attempt_id"]

    with pytest.raises(CommandError) as excinfo:
        execution_runtime.start_tool_execution_attempt_command(
            connection,
            {
                "tool_execution_attempt_id": "txa-attempt-conflict",
                "tool_execution_id": "tx-attempt-001",
                "lease_token": "lease-token-conflict",
            },
        )
    assert excinfo.value.code == "tool_execution_attempt_active_conflict"

    completed = complete_tool_execution_attempt(
        connection,
        tool_execution_attempt_id="txa-attempt-001",
        tool_execution_id="tx-attempt-001",
        lease_token="lease-token-001",
        state="FAILED",
        output_artifact_version_ids=None,
        completed_at=NOW,
        error_code="retryable_failure",
    )
    assert completed["attempt_no"] == 1
    second = create_tool_execution_attempt(
        connection,
        tool_execution_attempt_id="txa-attempt-002",
        tool_execution_id="tx-attempt-001",
        execution_session_id="xs-attempt-001",
        lease_token="lease-token-002",
        started_at=NOW,
    )
    assert second["attempt_no"] == 2
