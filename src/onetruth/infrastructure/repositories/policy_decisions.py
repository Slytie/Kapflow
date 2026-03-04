from __future__ import annotations

import json
import sqlite3
from typing import Any


def create_policy_decision(
    connection: sqlite3.Connection,
    *,
    policy_decision_id: str,
    principal_actor: dict[str, Any],
    decision: str,
    reason_code: str | None,
    required_approval_action: str | None,
    tool_execution_id: str | None,
    decided_at: str,
) -> None:
    connection.execute(
        """
        INSERT INTO policy_decisions (
            policy_decision_id,
            principal_actor,
            decision,
            reason_code,
            required_approval_action,
            tool_execution_id,
            decided_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (
            policy_decision_id,
            json.dumps(principal_actor, separators=(",", ":")),
            decision,
            reason_code,
            required_approval_action,
            tool_execution_id,
            decided_at,
        ),
    )


def get_policy_decision(
    connection: sqlite3.Connection,
    policy_decision_id: str,
) -> dict[str, Any] | None:
    row = connection.execute(
        """
        SELECT
            policy_decision_id,
            principal_actor,
            decision,
            reason_code,
            required_approval_action,
            tool_execution_id,
            decided_at
        FROM policy_decisions
        WHERE policy_decision_id = ?
        """,
        (policy_decision_id,),
    ).fetchone()
    if row is None:
        return None
    item = dict(row)
    item["principal_actor"] = json.loads(item["principal_actor"])
    return item


def get_policy_decision_for_tool_execution(
    connection: sqlite3.Connection,
    *,
    tool_execution_id: str,
) -> dict[str, Any] | None:
    row = connection.execute(
        """
        SELECT
            policy_decision_id,
            principal_actor,
            decision,
            reason_code,
            required_approval_action,
            tool_execution_id,
            decided_at
        FROM policy_decisions
        WHERE tool_execution_id = ?
        """,
        (tool_execution_id,),
    ).fetchone()
    if row is None:
        return None
    item = dict(row)
    item["principal_actor"] = json.loads(item["principal_actor"])
    return item
