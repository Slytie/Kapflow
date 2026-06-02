from __future__ import annotations

import sqlite3

from onetruth.application.services.approval_response_hooks import (
    ApprovalResponseHook,
    ApprovalResponseHookContext,
    DEFAULT_APPROVAL_RESPONSE_HOOKS,
    run_registered_approval_response_hooks,
)
from onetruth.application.services.logistics_approval_response_hooks import (
    LOGISTICS_APPROVAL_RESPONSE_HOOKS,
    dispatch_reporting_finalize_approval_hook,
    weekly_publish_approval_hook,
)


def _hook_context(
    *,
    connection: sqlite3.Connection,
    response_kind: str = "approve",
) -> ApprovalResponseHookContext:
    return ApprovalResponseHookContext(
        connection=connection,
        approval={
            "approval_id": "ap-test-001",
            "workflow_run_id": "wr-test-001",
            "scope_ref": "Stage06",
        },
        requested_action="publish_weekly_base_schedule",
        response_kind=response_kind,
        actor_id="human:reviewer",
        actor_type="human",
        event_idempotency_base="idem:test:approval-respond",
    )


def test_registered_approval_response_hook_runner_invokes_explicit_hooks() -> None:
    connection = sqlite3.connect(":memory:")
    calls: list[tuple[str, str]] = []

    def _record(context: ApprovalResponseHookContext) -> None:
        calls.append((str(context.approval["approval_id"]), context.response_kind))

    run_registered_approval_response_hooks(
        _hook_context(connection=connection),
        hooks=(ApprovalResponseHook(hook_id="test.record", handler=_record),),
    )

    assert calls == [("ap-test-001", "approve")]


def test_default_approval_response_hooks_are_logistics_registry_entries() -> None:
    assert DEFAULT_APPROVAL_RESPONSE_HOOKS == LOGISTICS_APPROVAL_RESPONSE_HOOKS
    assert [hook.hook_id for hook in DEFAULT_APPROVAL_RESPONSE_HOOKS] == [
        "logistics.weekly_publish_approval",
        "logistics.dispatch_reporting_finalize_approval",
    ]


def test_logistics_approval_hooks_ignore_non_approved_responses_before_db_reads() -> None:
    connection = sqlite3.connect(":memory:")
    context = _hook_context(connection=connection, response_kind="reject")

    weekly_publish_approval_hook(context)
    dispatch_reporting_finalize_approval_hook(context)
