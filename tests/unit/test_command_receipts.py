from __future__ import annotations

import json
import sqlite3

import pytest

from onetruth.application.handlers._shared.command_boundary import (
    COMMAND_RECEIPT_INPUT_HASH_PROFILE,
    _execute_with_command_receipt,
    _command_request_fingerprint,
    _prepare_command_receipt,
    _public_command_scope_key,
)
from onetruth.application.handlers.workflow_task_lifecycle import (
    CommandError,
    create_workflow_run_command,
)
from onetruth.infrastructure.events.event_store import create_sqlite_substrate


def _scope(parts: tuple[object, ...]) -> str:
    return json.dumps(
        [None if value is None else str(value) for value in parts],
        separators=(",", ":"),
        ensure_ascii=True,
    )


def _connection() -> sqlite3.Connection:
    connection = sqlite3.connect(":memory:")
    connection.row_factory = sqlite3.Row
    create_sqlite_substrate(connection)
    return connection


@pytest.mark.parametrize(
    ("command_name", "payload", "expected_scope"),
    [
        (
            "runs.create",
            {
                "tenant_id": "tenant-a",
                "domain_id": "domain-x",
                "workflow_id": "schedule_planning.v1",
                "partition_key": "SD-2026-03-13",
                "activation_key": "weekly-run",
            },
            _scope(("tenant-a", "domain-x", "schedule_planning.v1", "SD-2026-03-13", "weekly-run")),
        ),
        (
            "capex.workpages.command-envelope.execute",
            {
                "project_id": "cp-002",
                "workpage_kind": "capex-source-review-v0",
                "command_type": "promote_review_basis",
                "projection_snapshot_id": "wps-001",
            },
            _scope(("cp-002", "capex-source-review-v0", "promote_review_basis", "wps-001")),
        ),
        (
            "capex.project_memberships.revoke",
            {
                "project_id": "cp-002",
                "project_membership_id": "pm-002",
            },
            _scope(("cp-002", "pm-002")),
        ),
        (
            "tasks.create",
            {
                "workflow_run_id": "wr-001",
                "activation_key": "stage06-final-review",
            },
            _scope(("wr-001", "stage06-final-review")),
        ),
        (
            "tasks.claim",
            {"human_task_id": "ht-001"},
            _scope(("ht-001",)),
        ),
        (
            "tasks.complete",
            {"human_task_id": "ht-002"},
            _scope(("ht-002",)),
        ),
        (
            "tasks.confirm-review",
            {"human_task_id": "ht-003"},
            _scope(("ht-003",)),
        ),
        (
            "flags.create",
            {
                "workflow_run_id": "wr-002",
                "dedupe_key": "traffic:berlin-east",
            },
            _scope(("wr-002", "traffic:berlin-east")),
        ),
        (
            "flags.transition",
            {"flag_id": "fl-001"},
            _scope(("fl-001",)),
        ),
        (
            "approvals.request",
            {
                "workflow_run_id": "wr-003",
                "approval_kind": "business_decision",
                "scope_kind": "stage",
                "scope_ref": "Stage06",
                "task_run_id": "tr-001",
                "action": "publish_schedule",
            },
            _scope(("wr-003", "business_decision", "stage", "Stage06", "tr-001", "publish_schedule")),
        ),
        (
            "approvals.respond",
            {"approval_id": "ap-001"},
            _scope(("ap-001",)),
        ),
        (
            "artifacts.create-version",
            {
                "workflow_run_id": "wr-004",
                "task_run_id": "tr-002",
                "artifact_kind": "schedule.publish.packet",
            },
            _scope(("wr-004", "tr-002", "schedule.publish.packet")),
        ),
        (
            "artifacts.ingest",
            {
                "workflow_run_id": "wr-005",
                "task_run_id": None,
                "artifact_kind": "schedule.supervisor_review.doc",
            },
            _scope(("wr-005", None, "schedule.supervisor_review.doc")),
        ),
        (
            "artifacts.seed-corpus",
            {
                "workflow_run_id": "wr-006",
                "seed_set_id": "stage06_review_ready_example_set",
                "manifest_path": None,
            },
            _scope(("wr-006", "stage06_review_ready_example_set", "default_manifest")),
        ),
        (
            "pointers.promote",
            {
                "workflow_run_id": "wr-007",
                "pointer_key": "schedule.publish.packet:official:SD-2026-03-13",
            },
            _scope(("wr-007", "schedule.publish.packet:official:SD-2026-03-13")),
        ),
        (
            "execution-sessions.create",
            {
                "workflow_run_id": "wr-008",
                "task_run_id": "tr-003",
                "execution_spec_id": "stage06.review.execspec",
                "owner_mode": "agent",
            },
            _scope(("wr-008", "tr-003", "stage06.review.execspec", "agent")),
        ),
        (
            "execution-sessions.transition",
            {"execution_session_id": "xs-001"},
            _scope(("xs-001",)),
        ),
        (
            "tool-executions.request",
            {
                "execution_session_id": "xs-002",
                "tool_class": "validation",
                "tool_name": None,
            },
            _scope(("xs-002", "validation", None)),
        ),
        (
            "tool-executions.complete",
            {"tool_execution_id": "tx-001"},
            _scope(("tx-001",)),
        ),
    ],
)
def test_public_command_scope_key_derives_expected_scope(
    command_name: str,
    payload: dict[str, object],
    expected_scope: str,
) -> None:
    assert _public_command_scope_key(command_name, payload) == expected_scope


def test_execute_with_command_receipt_replays_same_scope_and_fingerprint() -> None:
    connection = _connection()
    payload = {
        "human_task_id": "ht-claim-001",
        "idempotency_key": "idem-claim-001",
    }
    receipt = _prepare_command_receipt(
        command_name="tasks.claim",
        payload=payload,
        fingerprint_payload={
            "human_task_id": "ht-claim-001",
            "actor_id": "agent:planner-1",
            "lease_seconds": 300,
        },
        tenant_id="tenant-a",
        domain_id="domain-x",
        workflow_run_id="wr-001",
        idempotency_required=True,
    )
    assert receipt is not None

    calls = 0

    def _operation() -> dict[str, object]:
        nonlocal calls
        calls += 1
        return {"human_task_id": "ht-claim-001", "lease_version": 1}

    first_result, first_replay = _execute_with_command_receipt(
        connection,
        receipt=receipt,
        operation=_operation,
    )
    second_result, second_replay = _execute_with_command_receipt(
        connection,
        receipt=receipt,
        operation=_operation,
    )

    assert first_replay is False
    assert second_replay is True
    assert first_result == second_result
    assert calls == 1


def test_command_receipt_canonical_hash_vector_is_stable_across_key_order() -> None:
    assert (
        _command_request_fingerprint({"b": 2, "a": 1})
        == "sha256:43258cff783fe7036d8a43033f830adfc60ec037382473548ac742b888292777"
    )
    assert _command_request_fingerprint({"a": 1, "b": 2}) == _command_request_fingerprint(
        {"b": 2, "a": 1}
    )


def test_command_receipt_hash_rejects_nan_input() -> None:
    with pytest.raises(CommandError) as excinfo:
        _prepare_command_receipt(
            command_name="tasks.claim",
            payload={
                "human_task_id": "ht-nan-001",
                "idempotency_key": "idem-nan-001",
            },
            fingerprint_payload={"human_task_id": "ht-nan-001", "score": float("nan")},
            tenant_id="tenant-a",
            domain_id="domain-x",
            workflow_run_id="wr-001",
            idempotency_required=True,
        )

    assert excinfo.value.code == "command_receipt_input_not_canonical_json"


def test_command_receipt_persists_hash_profile_and_sha256_prefix() -> None:
    connection = _connection()
    receipt = _prepare_command_receipt(
        command_name="tasks.claim",
        payload={
            "human_task_id": "ht-profile-001",
            "idempotency_key": "idem-profile-001",
        },
        fingerprint_payload={"human_task_id": "ht-profile-001", "actor_id": "agent-a"},
        tenant_id="tenant-a",
        domain_id="domain-x",
        workflow_run_id="wr-001",
        idempotency_required=True,
    )
    assert receipt is not None

    _execute_with_command_receipt(
        connection,
        receipt=receipt,
        operation=lambda: {"human_task_id": "ht-profile-001"},
    )

    row = connection.execute(
        """
        SELECT request_fingerprint, request_fingerprint_profile
        FROM command_receipts
        WHERE idempotency_key = 'idem-profile-001'
        """
    ).fetchone()
    assert row is not None
    assert str(row["request_fingerprint"]).startswith("sha256:")
    assert row["request_fingerprint_profile"] == COMMAND_RECEIPT_INPUT_HASH_PROFILE
    assert receipt.request_fingerprint_profile == COMMAND_RECEIPT_INPUT_HASH_PROFILE


def test_execute_with_command_receipt_rejects_same_scope_key_with_different_fingerprint() -> None:
    connection = _connection()
    base_payload = {
        "human_task_id": "ht-complete-001",
        "idempotency_key": "idem-complete-001",
    }
    first_receipt = _prepare_command_receipt(
        command_name="tasks.complete",
        payload=base_payload,
        fingerprint_payload={
            "human_task_id": "ht-complete-001",
            "outcome": "done",
        },
        tenant_id="tenant-a",
        domain_id="domain-x",
        workflow_run_id="wr-002",
        idempotency_required=True,
    )
    second_receipt = _prepare_command_receipt(
        command_name="tasks.complete",
        payload=base_payload,
        fingerprint_payload={
            "human_task_id": "ht-complete-001",
            "outcome": "needs_followup",
        },
        tenant_id="tenant-a",
        domain_id="domain-x",
        workflow_run_id="wr-002",
        idempotency_required=True,
    )
    assert first_receipt is not None
    assert second_receipt is not None

    _execute_with_command_receipt(
        connection,
        receipt=first_receipt,
        operation=lambda: {"human_task_id": "ht-complete-001", "outcome": "done"},
    )

    with pytest.raises(CommandError) as excinfo:
        _execute_with_command_receipt(
            connection,
            receipt=second_receipt,
            operation=lambda: {"human_task_id": "ht-complete-001", "outcome": "needs_followup"},
        )

    assert excinfo.value.code == "command_receipt_mismatch"
    assert excinfo.value.message == (
        "idempotency key was already used for a different request in this command scope"
    )


@pytest.mark.parametrize(
    ("column", "value"),
    [
        ("request_fingerprint", "bad-digest"),
        ("request_fingerprint_profile", "legacy-or-invalid-profile"),
    ],
)
def test_execute_with_command_receipt_rejects_corrupted_stored_hash_or_profile(
    column: str,
    value: str,
) -> None:
    connection = _connection()
    payload = {
        "human_task_id": "ht-corrupt-001",
        "idempotency_key": "idem-corrupt-001",
    }
    receipt = _prepare_command_receipt(
        command_name="tasks.claim",
        payload=payload,
        fingerprint_payload={"human_task_id": "ht-corrupt-001", "actor_id": "agent-a"},
        tenant_id="tenant-a",
        domain_id="domain-x",
        workflow_run_id="wr-001",
        idempotency_required=True,
    )
    assert receipt is not None
    _execute_with_command_receipt(
        connection,
        receipt=receipt,
        operation=lambda: {"human_task_id": "ht-corrupt-001"},
    )
    connection.execute(
        f"UPDATE command_receipts SET {column} = ? WHERE idempotency_key = ?",
        (value, "idem-corrupt-001"),
    )

    with pytest.raises(CommandError) as excinfo:
        _execute_with_command_receipt(
            connection,
            receipt=receipt,
            operation=lambda: {"human_task_id": "ht-corrupt-001"},
        )

    assert excinfo.value.code == "command_receipt_corrupt"


def test_same_idempotency_key_can_be_reused_across_scopes() -> None:
    connection = _connection()
    for human_task_id in ("ht-scope-a", "ht-scope-b"):
        receipt = _prepare_command_receipt(
            command_name="tasks.claim",
            payload={
                "human_task_id": human_task_id,
                "idempotency_key": "shared-client-key",
            },
            fingerprint_payload={
                "human_task_id": human_task_id,
                "actor_id": "agent:planner-1",
                "lease_seconds": 120,
            },
            tenant_id="tenant-a",
            domain_id="domain-x",
            workflow_run_id="wr-scope",
            idempotency_required=True,
        )
        assert receipt is not None
        result, replay = _execute_with_command_receipt(
            connection,
            receipt=receipt,
            operation=lambda human_task_id=human_task_id: {"human_task_id": human_task_id},
        )
        assert replay is False
        assert result["human_task_id"] == human_task_id

    row = connection.execute("SELECT COUNT(*) AS count FROM command_receipts").fetchone()
    assert row is not None
    assert int(row["count"]) == 2


def test_generated_create_ids_do_not_cause_receipt_mismatch_on_retry() -> None:
    connection = _connection()
    payload = {
        "workflow_id": "schedule_planning.v1",
        "workflow_version": "v1",
        "tenant_id": "tenant-a",
        "domain_id": "domain-x",
        "partition_key": "SD-2026-03-13",
        "logical_date": "2026-03-13",
        "activation_key": "weekly-planning",
        "idempotency_key": "idem-runs-create-001",
    }

    first = create_workflow_run_command(connection, payload, include_receipt=True)
    second = create_workflow_run_command(connection, payload, include_receipt=True)

    assert first["idempotent_replay"] is False
    assert second["idempotent_replay"] is True
    assert (
        first["result"]["workflow_run_id"]
        == second["result"]["workflow_run_id"]
    )

    workflow_rows = connection.execute("SELECT COUNT(*) AS count FROM workflow_runs").fetchone()
    event_rows = connection.execute(
        "SELECT COUNT(*) AS count FROM timeline_events WHERE event_type = 'workflow.run.created'"
    ).fetchone()
    assert workflow_rows is not None
    assert event_rows is not None
    assert int(workflow_rows["count"]) == 1
    assert int(event_rows["count"]) == 1
