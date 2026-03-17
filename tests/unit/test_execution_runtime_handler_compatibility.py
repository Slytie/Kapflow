from __future__ import annotations

import sqlite3

import pytest

import onetruth.application.handlers._shared.command_boundary as command_boundary
import onetruth.application.handlers.execution_runtime as new_execution_runtime
import onetruth.application.handlers.workflow_task_lifecycle as legacy_handlers
from onetruth.infrastructure.events.event_store import create_sqlite_substrate, list_events


def _connection() -> sqlite3.Connection:
    connection = sqlite3.connect(":memory:")
    connection.row_factory = sqlite3.Row
    create_sqlite_substrate(connection)
    return connection


def _freeze_handler_time(monkeypatch: pytest.MonkeyPatch) -> None:
    fixed_now = "2026-03-17T14:00:00Z"
    monkeypatch.setattr(command_boundary, "utc_now_iso", lambda: fixed_now)
    monkeypatch.setattr(legacy_handlers, "utc_now_iso", lambda: fixed_now)
    monkeypatch.setattr(new_execution_runtime, "utc_now_iso", lambda: fixed_now)


def _workflow_payload(workflow_run_id: str, activation_key: str) -> dict[str, str]:
    return {
        "workflow_run_id": workflow_run_id,
        "workflow_id": "schedule_planning.v1",
        "workflow_version": "v1",
        "tenant_id": "tenant-a",
        "domain_id": "domain-x",
        "partition_key": "SD-2026-03-17",
        "logical_date": "2026-03-17",
        "activation_key": activation_key,
    }


def _task_payload(workflow_run_id: str) -> dict[str, object]:
    return {
        "workflow_run_id": workflow_run_id,
        "task_run_id": "tr-exec-compat-001",
        "stage_id": "Stage06",
        "task_kind": "review_packet",
        "activation_key": "exec-compat-review",
    }


def _execution_session_payload(workflow_run_id: str, *, idempotency_key: str) -> dict[str, object]:
    return {
        "execution_session_id": "xs-compat-001",
        "workflow_run_id": workflow_run_id,
        "task_run_id": "tr-exec-compat-001",
        "execution_spec_id": "execspec.schedule_planning_v1.stage06.reference.compat",
        "owner_mode": "agent",
        "state": "WAITING_POLICY",
        "principal_actor": {"type": "agent", "id": "agent:compat"},
        "budget": {"max_tool_calls": 1},
        "idempotency_key": idempotency_key,
        "actor_id": "agent:compat",
        "actor_type": "agent",
    }


def _tool_request_payload(*, idempotency_key: str) -> dict[str, object]:
    return {
        "tool_execution_id": "tx-compat-001",
        "execution_session_id": "xs-compat-001",
        "tool_class": "model.openai.responses.stage06.review",
        "tool_name": "stage06_review",
        "idempotency_key": idempotency_key,
        "actor_id": "agent:compat",
        "actor_type": "agent",
    }


def _policy_payload(*, idempotency_key: str) -> dict[str, object]:
    return {
        "policy_decision_id": "pd-compat-001",
        "tool_execution_id": "tx-compat-001",
        "decision": "allow",
        "principal_actor": {"type": "agent", "id": "agent:compat"},
        "idempotency_key": idempotency_key,
    }


def _tool_complete_payload(*, idempotency_key: str) -> dict[str, object]:
    return {
        "tool_execution_id": "tx-compat-001",
        "result": "succeeded",
        "idempotency_key": idempotency_key,
        "actor_id": "agent:compat",
        "actor_type": "agent",
    }


def _session_transition_payload(*, idempotency_key: str) -> dict[str, object]:
    return {
        "execution_session_id": "xs-compat-001",
        "to_state": "SUCCEEDED",
        "reason": "tool_execution_succeeded",
        "idempotency_key": idempotency_key,
        "actor_id": "agent:compat",
        "actor_type": "agent",
    }


def _session_summary(row: dict[str, object]) -> dict[str, object]:
    return {
        "execution_session_id": row["execution_session_id"],
        "workflow_run_id": row["workflow_run_id"],
        "task_run_id": row["task_run_id"],
        "execution_spec_id": row["execution_spec_id"],
        "state": row["state"],
        "owner_mode": row["owner_mode"],
        "principal_actor": row["principal_actor"],
        "budget": row["budget"],
        "tool_call_count": row["tool_call_count"],
    }


def _tool_summary(row: dict[str, object]) -> dict[str, object]:
    return {
        "tool_execution_id": row["tool_execution_id"],
        "execution_session_id": row["execution_session_id"],
        "tool_class": row["tool_class"],
        "tool_name": row["tool_name"],
        "state": row["state"],
        "attempt_no": row["attempt_no"],
        "policy_decision_id": row["policy_decision_id"],
        "output_artifact_version_ids": row["output_artifact_version_ids"],
        "error_code": row["error_code"],
    }


def _policy_summary(row: dict[str, object]) -> dict[str, object]:
    return {
        "policy_decision_id": row["policy_decision_id"],
        "principal_actor": row["principal_actor"],
        "decision": row["decision"],
        "reason_code": row["reason_code"],
        "required_approval_action": row["required_approval_action"],
        "tool_execution_id": row["tool_execution_id"],
    }


def _event_payloads(connection: sqlite3.Connection, workflow_run_id: str) -> list[tuple[str, dict[str, object]]]:
    relevant_types = {
        "execution.session.created",
        "execution.session.state_changed",
        "tool.execution.requested",
        "tool.execution.approved",
        "tool.execution.completed",
    }
    return [
        (str(event["event_type"]), dict(event["payload"]))
        for event in list_events(connection, run_id=workflow_run_id)
        if str(event["event_type"]) in relevant_types
    ]


def test_execution_runtime_handler_compatibility_keeps_legacy_and_new_surfaces_in_sync(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _freeze_handler_time(monkeypatch)
    legacy_connection = _connection()
    new_connection = _connection()
    workflow_run_id = "wr-exec-compat"

    legacy_handlers.create_workflow_run_command(
        legacy_connection,
        _workflow_payload(workflow_run_id, "exec-compat-legacy"),
    )
    legacy_handlers.create_workflow_run_command(
        new_connection,
        _workflow_payload(workflow_run_id, "exec-compat-new"),
    )
    legacy_handlers.create_task_run_command(
        legacy_connection,
        _task_payload(workflow_run_id),
    )
    legacy_handlers.create_task_run_command(
        new_connection,
        _task_payload(workflow_run_id),
    )

    legacy_session = legacy_handlers.create_execution_session_command(
        legacy_connection,
        _execution_session_payload(
            workflow_run_id,
            idempotency_key="idem:compat:execution.create",
        ),
    )
    new_session = new_execution_runtime.create_execution_session_command(
        new_connection,
        _execution_session_payload(
            workflow_run_id,
            idempotency_key="idem:compat:execution.create",
        ),
    )
    assert _session_summary(legacy_session) == _session_summary(new_session)

    legacy_tool_request = legacy_handlers.request_tool_execution_command(
        legacy_connection,
        _tool_request_payload(idempotency_key="idem:compat:tool.request"),
    )
    new_tool_request = new_execution_runtime.request_tool_execution_command(
        new_connection,
        _tool_request_payload(idempotency_key="idem:compat:tool.request"),
    )
    assert _tool_summary(legacy_tool_request) == _tool_summary(new_tool_request)

    legacy_policy = legacy_handlers.evaluate_policy_decision_command(
        legacy_connection,
        _policy_payload(idempotency_key="idem:compat:policy.allow"),
    )
    new_policy = new_execution_runtime.evaluate_policy_decision_command(
        new_connection,
        _policy_payload(idempotency_key="idem:compat:policy.allow"),
    )
    assert _tool_summary(legacy_policy["tool_execution"]) == _tool_summary(
        new_policy["tool_execution"]
    )
    assert _policy_summary(legacy_policy["policy_decision"]) == _policy_summary(
        new_policy["policy_decision"]
    )
    assert _session_summary(legacy_policy["execution_session"]) == _session_summary(
        new_policy["execution_session"]
    )

    legacy_completed_tool = legacy_handlers.complete_tool_execution_command(
        legacy_connection,
        _tool_complete_payload(idempotency_key="idem:compat:tool.complete"),
    )
    new_completed_tool = new_execution_runtime.complete_tool_execution_command(
        new_connection,
        _tool_complete_payload(idempotency_key="idem:compat:tool.complete"),
    )
    assert _tool_summary(legacy_completed_tool) == _tool_summary(new_completed_tool)

    legacy_completed_session = legacy_handlers.transition_execution_session_state_command(
        legacy_connection,
        _session_transition_payload(idempotency_key="idem:compat:session.transition"),
    )
    new_completed_session = new_execution_runtime.transition_execution_session_state_command(
        new_connection,
        _session_transition_payload(idempotency_key="idem:compat:session.transition"),
    )
    assert _session_summary(legacy_completed_session) == _session_summary(
        new_completed_session
    )

    assert _event_payloads(legacy_connection, workflow_run_id) == _event_payloads(
        new_connection,
        workflow_run_id,
    )
