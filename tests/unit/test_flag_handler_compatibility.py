from __future__ import annotations

import sqlite3

import pytest

import onetruth.application.handlers._shared.command_boundary as command_boundary
import onetruth.application.handlers.flags as new_flags
import onetruth.application.handlers.workflow_task_lifecycle as legacy_handlers
from onetruth.infrastructure.events.event_store import create_sqlite_substrate, list_events


def _connection() -> sqlite3.Connection:
    connection = sqlite3.connect(":memory:")
    connection.row_factory = sqlite3.Row
    create_sqlite_substrate(connection)
    return connection


def _freeze_handler_time(monkeypatch: pytest.MonkeyPatch) -> None:
    fixed_now = "2026-03-17T12:00:00Z"
    monkeypatch.setattr(command_boundary, "utc_now_iso", lambda: fixed_now)
    monkeypatch.setattr(legacy_handlers, "utc_now_iso", lambda: fixed_now)
    monkeypatch.setattr(new_flags, "utc_now_iso", lambda: fixed_now)


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


def _flag_payload(workflow_run_id: str, *, flag_id: str, idempotency_key: str) -> dict[str, object]:
    return {
        "flag_id": flag_id,
        "workflow_run_id": workflow_run_id,
        "kind": "missing_input",
        "severity": "high",
        "summary": "Workbook missing from Stage05 packet",
        "details_json": {"artifact_kind": "planning.draft_weekly_schedule.workbook"},
        "assigned_group": "operations_manager",
        "source_event_id": "evt-flag-source",
        "idempotency_key": idempotency_key,
        "actor_id": "system:runtime",
        "actor_type": "system",
    }


def _transition_payload(flag_id: str, *, idempotency_key: str, actor_roles: list[str]) -> dict[str, object]:
    return {
        "flag_id": flag_id,
        "to_state": "triage",
        "reason": "Ops accepted the issue",
        "actor_id": "human:ops-manager-1",
        "actor_type": "human",
        "actor_roles": actor_roles,
        "idempotency_key": idempotency_key,
    }


def _activation_payload(
    workflow_run_id: str,
    flag_id: str,
    *,
    task_run_id: str,
    human_task_id: str,
    idempotency_key: str,
) -> dict[str, object]:
    return {
        "workflow_run_id": workflow_run_id,
        "flag_id": flag_id,
        "generation": 0,
        "task_run_id": task_run_id,
        "human_task_id": human_task_id,
        "idempotency_key": idempotency_key,
        "actor_id": "system:stage07-reconcile",
        "actor_type": "system",
    }


def _flag_summary(row: dict[str, object]) -> dict[str, object]:
    return {
        "flag_id": row["flag_id"],
        "workflow_run_id": row["workflow_run_id"],
        "kind": row["kind"],
        "severity": row["severity"],
        "state": row["state"],
        "summary": row["summary"],
        "assigned_group": row["assigned_group"],
        "source_event_id": row["source_event_id"],
    }


def _task_run_summary(row: dict[str, object]) -> dict[str, object]:
    return {
        "task_run_id": row["task_run_id"],
        "workflow_run_id": row["workflow_run_id"],
        "stage_id": row["stage_id"],
        "task_kind": row["task_kind"],
        "state": row["state"],
        "generation": row["generation"],
        "activation_key": row["activation_key"],
        "spawned_from_flag_id": row["spawned_from_flag_id"],
        "spawn_rule_id": row["spawn_rule_id"],
        "spawn_cause_kind": row["spawn_cause_kind"],
        "spawn_cause_event_id": row["spawn_cause_event_id"],
        "spawn_depth": row["spawn_depth"],
        "spawn_budget_key": row["spawn_budget_key"],
    }


def _human_task_summary(row: dict[str, object] | None) -> dict[str, object] | None:
    if row is None:
        return None
    return {
        "human_task_id": row["human_task_id"],
        "workflow_run_id": row["workflow_run_id"],
        "task_run_id": row["task_run_id"],
        "task_kind": row["task_kind"],
        "state": row["state"],
        "candidate_roles": row["candidate_roles"],
        "owner_role": row["owner_role"],
        "generation": row["generation"],
    }


def _event_payloads(connection: sqlite3.Connection, workflow_run_id: str) -> list[tuple[str, dict[str, object]]]:
    relevant_types = {
        "flag.created",
        "flag.state_changed",
        "task.run.created",
        "task.created",
    }
    return [
        (str(event["event_type"]), dict(event["payload"]))
        for event in list_events(connection, run_id=workflow_run_id)
        if str(event["event_type"]) in relevant_types
    ]


def test_flag_handler_compatibility_keeps_legacy_and_new_surfaces_in_sync(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _freeze_handler_time(monkeypatch)
    legacy_connection = _connection()
    new_connection = _connection()
    workflow_run_id = "wr-flag-compat"

    legacy_handlers.create_workflow_run_command(
        legacy_connection,
        _workflow_payload(workflow_run_id, "flag-compat"),
    )
    legacy_handlers.create_workflow_run_command(
        new_connection,
        _workflow_payload(workflow_run_id, "flag-compat"),
    )

    legacy_created = legacy_handlers.create_flag_command(
        legacy_connection,
        _flag_payload(
            workflow_run_id,
            flag_id="fl-compat-001",
            idempotency_key="idem:legacy:flags.create",
        ),
    )
    new_created = new_flags.create_flag_command(
        new_connection,
        _flag_payload(
            workflow_run_id,
            flag_id="fl-compat-001",
            idempotency_key="idem:new:flags.create",
        ),
    )

    assert _flag_summary(legacy_created) == _flag_summary(new_created)
    assert _event_payloads(legacy_connection, workflow_run_id) == _event_payloads(
        new_connection,
        workflow_run_id,
    )

    legacy_transitioned = legacy_handlers.transition_flag_state_command(
        legacy_connection,
        _transition_payload(
            "fl-compat-001",
            idempotency_key="idem:legacy:flags.transition",
            actor_roles=["operations_manager"],
        ),
    )
    new_transitioned = new_flags.transition_flag_state_command(
        new_connection,
        _transition_payload(
            "fl-compat-001",
            idempotency_key="idem:new:flags.transition",
            actor_roles=["operations_manager"],
        ),
    )

    assert _flag_summary(legacy_transitioned) == _flag_summary(new_transitioned)
    assert _event_payloads(legacy_connection, workflow_run_id) == _event_payloads(
        new_connection,
        workflow_run_id,
    )

    legacy_activation = legacy_handlers.activate_stage07_issue_from_flag_command(
        legacy_connection,
        _activation_payload(
            workflow_run_id,
            "fl-compat-001",
            task_run_id="tr-stage07-compat",
            human_task_id="ht-stage07-compat",
            idempotency_key="idem:legacy:stage07.activate",
        ),
    )
    new_activation = new_flags.activate_stage07_issue_from_flag_command(
        new_connection,
        _activation_payload(
            workflow_run_id,
            "fl-compat-001",
            task_run_id="tr-stage07-compat",
            human_task_id="ht-stage07-compat",
            idempotency_key="idem:new:stage07.activate",
        ),
    )

    assert _task_run_summary(legacy_activation["task_run"]) == _task_run_summary(
        new_activation["task_run"]
    )
    assert _human_task_summary(legacy_activation["human_task"]) == _human_task_summary(
        new_activation["human_task"]
    )
    assert _event_payloads(legacy_connection, workflow_run_id) == _event_payloads(
        new_connection,
        workflow_run_id,
    )


def test_flag_handler_compatibility_preserves_forbidden_error_details(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _freeze_handler_time(monkeypatch)
    legacy_connection = _connection()
    new_connection = _connection()
    workflow_run_id = "wr-flag-compat-forbidden"

    legacy_handlers.create_workflow_run_command(
        legacy_connection,
        _workflow_payload(workflow_run_id, "flag-compat-forbidden"),
    )
    legacy_handlers.create_workflow_run_command(
        new_connection,
        _workflow_payload(workflow_run_id, "flag-compat-forbidden"),
    )
    legacy_handlers.create_flag_command(
        legacy_connection,
        _flag_payload(
            workflow_run_id,
            flag_id="fl-compat-forbidden-001",
            idempotency_key="idem:legacy:flags.create:forbidden",
        ),
    )
    new_flags.create_flag_command(
        new_connection,
        _flag_payload(
            workflow_run_id,
            flag_id="fl-compat-forbidden-001",
            idempotency_key="idem:new:flags.create:forbidden",
        ),
    )

    with pytest.raises(legacy_handlers.CommandError) as legacy_exc:
        legacy_handlers.transition_flag_state_command(
            legacy_connection,
            _transition_payload(
                "fl-compat-forbidden-001",
                idempotency_key="idem:legacy:flags.transition:forbidden",
                actor_roles=["auditor"],
            ),
        )

    with pytest.raises(new_flags.CommandError) as new_exc:
        new_flags.transition_flag_state_command(
            new_connection,
            _transition_payload(
                "fl-compat-forbidden-001",
                idempotency_key="idem:new:flags.transition:forbidden",
                actor_roles=["auditor"],
            ),
        )

    assert legacy_exc.value.code == "flag_transition_forbidden"
    assert new_exc.value.code == legacy_exc.value.code
    assert new_exc.value.details == legacy_exc.value.details
