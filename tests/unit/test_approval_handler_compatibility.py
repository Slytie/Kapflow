from __future__ import annotations

import sqlite3

import pytest

from onetruth.application.handlers.approvals import (
    list_approvals_for_workflow_run_command as new_list_approvals_for_workflow_run_command,
    request_approval_command as new_request_approval_command,
    respond_approval_command as new_respond_approval_command,
    show_approval_command as new_show_approval_command,
)
from onetruth.application.handlers.workflow_task_lifecycle import (
    CommandError,
    create_workflow_run_command,
    list_approvals_for_workflow_run_command as legacy_list_approvals_for_workflow_run_command,
    request_approval_command as legacy_request_approval_command,
    respond_approval_command as legacy_respond_approval_command,
    show_approval_command as legacy_show_approval_command,
)
from onetruth.infrastructure.events.event_store import create_sqlite_substrate, list_events


def _connection() -> sqlite3.Connection:
    connection = sqlite3.connect(":memory:")
    connection.row_factory = sqlite3.Row
    create_sqlite_substrate(connection)
    return connection


def _workflow_payload(workflow_run_id: str, activation_key: str) -> dict[str, str]:
    return {
        "workflow_run_id": workflow_run_id,
        "workflow_id": "schedule_planning.v1",
        "workflow_version": "v1",
        "tenant_id": "tenant-a",
        "domain_id": "domain-x",
        "partition_key": "SD-2026-03-13",
        "logical_date": "2026-03-13",
        "activation_key": activation_key,
    }


def _approval_request_payload(workflow_run_id: str, approval_id: str, idempotency_key: str) -> dict[str, object]:
    return {
        "approval_id": approval_id,
        "workflow_run_id": workflow_run_id,
        "approval_kind": "business_decision",
        "scope_kind": "stage",
        "scope_ref": "Stage06",
        "candidate_roles": ["dispatch_supervisor"],
        "required_role": "dispatch_supervisor",
        "action": "publish_schedule",
        "idempotency_key": idempotency_key,
        "actor_id": "system:runtime",
        "actor_type": "system",
    }


def _approval_respond_payload(approval_id: str, idempotency_key: str, actor_roles: list[str]) -> dict[str, object]:
    return {
        "approval_id": approval_id,
        "actor_id": "human:dispatch-supervisor-1",
        "actor_type": "human",
        "actor_roles": actor_roles,
        "response_kind": "approve",
        "response_reason": "approved in compatibility test",
        "idempotency_key": idempotency_key,
    }


def _approval_summary(row: dict[str, object]) -> dict[str, object]:
    return {
        "approval_id": row["approval_id"],
        "workflow_run_id": row["workflow_run_id"],
        "task_run_id": row["task_run_id"],
        "approval_kind": row["approval_kind"],
        "scope_kind": row["scope_kind"],
        "scope_ref": row["scope_ref"],
        "state": row["state"],
        "requested_by_task_run_id": row["requested_by_task_run_id"],
        "candidate_roles": row["candidate_roles"],
        "required_role": row["required_role"],
        "response_kind": row["response_kind"],
        "response_reason": row["response_reason"],
        "decided_by_actor_id": row["decided_by_actor_id"],
        "decided_by_actor_type": row["decided_by_actor_type"],
        "generation": row["generation"],
    }


def _event_payloads(connection: sqlite3.Connection, workflow_run_id: str) -> list[tuple[str, dict[str, object]]]:
    return [
        (str(event["event_type"]), dict(event["payload"]))
        for event in list_events(connection, run_id=workflow_run_id)
        if str(event["event_type"]).startswith("approval.")
    ]


def test_approval_handler_compatibility_keeps_legacy_and_new_surfaces_in_sync() -> None:
    legacy_connection = _connection()
    new_connection = _connection()
    workflow_run_id = "wr-approval-compat"
    activation_key = "approval-compat"

    create_workflow_run_command(
        legacy_connection,
        _workflow_payload(workflow_run_id, activation_key),
    )
    create_workflow_run_command(
        new_connection,
        _workflow_payload(workflow_run_id, activation_key),
    )

    legacy_requested = legacy_request_approval_command(
        legacy_connection,
        _approval_request_payload(workflow_run_id, "ap-compat-001", "idem:legacy:request"),
    )
    new_requested = new_request_approval_command(
        new_connection,
        _approval_request_payload(workflow_run_id, "ap-compat-001", "idem:new:request"),
    )

    assert _approval_summary(legacy_requested) == _approval_summary(new_requested)
    assert _event_payloads(legacy_connection, workflow_run_id) == _event_payloads(
        new_connection,
        workflow_run_id,
    )

    legacy_approval = legacy_show_approval_command(legacy_connection, "ap-compat-001")
    new_approval = new_show_approval_command(new_connection, "ap-compat-001")
    assert _approval_summary(legacy_approval) == _approval_summary(new_approval)
    assert _approval_summary(
        legacy_list_approvals_for_workflow_run_command(legacy_connection, workflow_run_id)[0]
    ) == _approval_summary(
        new_list_approvals_for_workflow_run_command(new_connection, workflow_run_id)[0]
    )

    legacy_responded = legacy_respond_approval_command(
        legacy_connection,
        _approval_respond_payload("ap-compat-001", "idem:legacy:respond", ["dispatch_supervisor"]),
    )
    new_responded = new_respond_approval_command(
        new_connection,
        _approval_respond_payload("ap-compat-001", "idem:new:respond", ["dispatch_supervisor"]),
    )

    assert _approval_summary(legacy_responded) == _approval_summary(new_responded)
    assert _event_payloads(legacy_connection, workflow_run_id) == _event_payloads(
        new_connection,
        workflow_run_id,
    )


def test_approval_handler_compatibility_preserves_forbidden_error_details() -> None:
    legacy_connection = _connection()
    new_connection = _connection()
    workflow_run_id = "wr-approval-compat-forbidden"
    activation_key = "approval-compat-forbidden"

    create_workflow_run_command(
        legacy_connection,
        _workflow_payload(workflow_run_id, activation_key),
    )
    create_workflow_run_command(
        new_connection,
        _workflow_payload(workflow_run_id, activation_key),
    )
    legacy_request_approval_command(
        legacy_connection,
        _approval_request_payload(
            workflow_run_id,
            "ap-compat-forbidden-001",
            "idem:legacy:request:forbidden",
        ),
    )
    new_request_approval_command(
        new_connection,
        _approval_request_payload(
            workflow_run_id,
            "ap-compat-forbidden-001",
            "idem:new:request:forbidden",
        ),
    )

    with pytest.raises(CommandError) as legacy_exc:
        legacy_respond_approval_command(
            legacy_connection,
            _approval_respond_payload(
                "ap-compat-forbidden-001",
                "idem:legacy:respond:forbidden",
                ["schedule_planner"],
            ),
        )

    with pytest.raises(CommandError) as new_exc:
        new_respond_approval_command(
            new_connection,
            _approval_respond_payload(
                "ap-compat-forbidden-001",
                "idem:new:respond:forbidden",
                ["schedule_planner"],
            ),
        )

    assert legacy_exc.value.code == "approval_respond_forbidden"
    assert new_exc.value.code == legacy_exc.value.code
    assert new_exc.value.details == legacy_exc.value.details
