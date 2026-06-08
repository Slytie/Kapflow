from __future__ import annotations

import json
import sqlite3
from typing import Any


WAIVER_COLUMNS = """
    waiver_id,
    tenant_id,
    domain_id,
    project_id,
    scope_kind,
    scope_ref,
    state,
    reason,
    policy_version,
    metadata_json,
    created_by_actor_id,
    created_by_actor_type,
    expires_at,
    revoked_at,
    created_at,
    updated_at
"""

EVALUATION_COLUMNS = """
    closure_gate_evaluation_id,
    tenant_id,
    domain_id,
    project_id,
    closure_target_kind,
    closure_target_ref,
    policy_version,
    required_dimensions_json,
    satisfied_dimensions_json,
    missing_dimensions_json,
    waiver_refs_json,
    basis_version_vector_json,
    result,
    metadata_json,
    created_by_actor_id,
    created_by_actor_type,
    created_at
"""

SNAPSHOT_COLUMNS = """
    closure_snapshot_id,
    closure_gate_evaluation_id,
    tenant_id,
    domain_id,
    project_id,
    closure_target_kind,
    closure_target_ref,
    policy_version,
    state,
    result,
    basis_version_vector_json,
    metadata_json,
    created_by_actor_id,
    created_by_actor_type,
    stale_reason,
    stale_at,
    reopened_at,
    created_at,
    updated_at
"""

WAIVER_STATES = ("active", "revoked", "expired")
CLOSURE_EVALUATION_RESULTS = ("pass", "fail", "satisfied_by_waiver")
CLOSURE_SNAPSHOT_STATES = ("current", "stale", "reopened")


def create_waiver(
    connection: sqlite3.Connection,
    *,
    waiver_id: str,
    tenant_id: str,
    domain_id: str,
    project_id: str | None,
    scope_kind: str,
    scope_ref: str,
    state: str,
    reason: str,
    policy_version: str,
    metadata_json: dict[str, Any],
    created_by_actor_id: str,
    created_by_actor_type: str,
    created_at: str,
    expires_at: str | None = None,
    revoked_at: str | None = None,
) -> None:
    if state not in WAIVER_STATES:
        raise ValueError(f"invalid waiver state: {state}")
    connection.execute(
        """
        INSERT INTO capex_waivers (
            waiver_id,
            tenant_id,
            domain_id,
            project_id,
            scope_kind,
            scope_ref,
            state,
            reason,
            policy_version,
            metadata_json,
            created_by_actor_id,
            created_by_actor_type,
            expires_at,
            revoked_at,
            created_at,
            updated_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            waiver_id,
            tenant_id,
            domain_id,
            project_id,
            scope_kind,
            scope_ref,
            state,
            reason,
            policy_version,
            json.dumps(metadata_json, separators=(",", ":"), sort_keys=True),
            created_by_actor_id,
            created_by_actor_type,
            expires_at,
            revoked_at,
            created_at,
            created_at,
        ),
    )


def update_waiver_state(
    connection: sqlite3.Connection,
    *,
    waiver_id: str,
    state: str,
    updated_at: str,
    revoked_at: str | None = None,
) -> None:
    if state not in WAIVER_STATES:
        raise ValueError(f"invalid waiver state: {state}")
    connection.execute(
        """
        UPDATE capex_waivers
        SET state = ?, revoked_at = ?, updated_at = ?
        WHERE waiver_id = ?
        """,
        (state, revoked_at, updated_at, waiver_id),
    )


def get_waiver(
    connection: sqlite3.Connection,
    waiver_id: str,
) -> dict[str, Any] | None:
    row = connection.execute(
        f"""
        SELECT {WAIVER_COLUMNS}
        FROM capex_waivers
        WHERE waiver_id = ?
        """,
        (waiver_id,),
    ).fetchone()
    return _waiver_row(row)


def create_closure_gate_evaluation(
    connection: sqlite3.Connection,
    *,
    closure_gate_evaluation_id: str,
    tenant_id: str,
    domain_id: str,
    project_id: str | None,
    closure_target_kind: str,
    closure_target_ref: str,
    policy_version: str,
    required_dimensions_json: list[dict[str, Any]],
    satisfied_dimensions_json: list[dict[str, Any]],
    missing_dimensions_json: list[dict[str, Any]],
    waiver_refs_json: list[dict[str, Any]],
    basis_version_vector_json: dict[str, Any],
    result: str,
    metadata_json: dict[str, Any],
    created_by_actor_id: str,
    created_by_actor_type: str,
    created_at: str,
) -> None:
    if result not in CLOSURE_EVALUATION_RESULTS:
        raise ValueError(f"invalid closure evaluation result: {result}")
    connection.execute(
        """
        INSERT INTO capex_closure_gate_evaluations (
            closure_gate_evaluation_id,
            tenant_id,
            domain_id,
            project_id,
            closure_target_kind,
            closure_target_ref,
            policy_version,
            required_dimensions_json,
            satisfied_dimensions_json,
            missing_dimensions_json,
            waiver_refs_json,
            basis_version_vector_json,
            result,
            metadata_json,
            created_by_actor_id,
            created_by_actor_type,
            created_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            closure_gate_evaluation_id,
            tenant_id,
            domain_id,
            project_id,
            closure_target_kind,
            closure_target_ref,
            policy_version,
            json.dumps(required_dimensions_json, separators=(",", ":"), sort_keys=True),
            json.dumps(satisfied_dimensions_json, separators=(",", ":"), sort_keys=True),
            json.dumps(missing_dimensions_json, separators=(",", ":"), sort_keys=True),
            json.dumps(waiver_refs_json, separators=(",", ":"), sort_keys=True),
            json.dumps(basis_version_vector_json, separators=(",", ":"), sort_keys=True),
            result,
            json.dumps(metadata_json, separators=(",", ":"), sort_keys=True),
            created_by_actor_id,
            created_by_actor_type,
            created_at,
        ),
    )


def get_closure_gate_evaluation(
    connection: sqlite3.Connection,
    closure_gate_evaluation_id: str,
) -> dict[str, Any] | None:
    row = connection.execute(
        f"""
        SELECT {EVALUATION_COLUMNS}
        FROM capex_closure_gate_evaluations
        WHERE closure_gate_evaluation_id = ?
        """,
        (closure_gate_evaluation_id,),
    ).fetchone()
    return _evaluation_row(row)


def create_closure_snapshot(
    connection: sqlite3.Connection,
    *,
    closure_snapshot_id: str,
    closure_gate_evaluation_id: str,
    tenant_id: str,
    domain_id: str,
    project_id: str | None,
    closure_target_kind: str,
    closure_target_ref: str,
    policy_version: str,
    state: str,
    result: str,
    basis_version_vector_json: dict[str, Any],
    metadata_json: dict[str, Any],
    created_by_actor_id: str,
    created_by_actor_type: str,
    created_at: str,
) -> None:
    if state not in CLOSURE_SNAPSHOT_STATES:
        raise ValueError(f"invalid closure snapshot state: {state}")
    if result not in CLOSURE_EVALUATION_RESULTS:
        raise ValueError(f"invalid closure snapshot result: {result}")
    connection.execute(
        """
        INSERT INTO capex_closure_snapshots (
            closure_snapshot_id,
            closure_gate_evaluation_id,
            tenant_id,
            domain_id,
            project_id,
            closure_target_kind,
            closure_target_ref,
            policy_version,
            state,
            result,
            basis_version_vector_json,
            metadata_json,
            created_by_actor_id,
            created_by_actor_type,
            created_at,
            updated_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            closure_snapshot_id,
            closure_gate_evaluation_id,
            tenant_id,
            domain_id,
            project_id,
            closure_target_kind,
            closure_target_ref,
            policy_version,
            state,
            result,
            json.dumps(basis_version_vector_json, separators=(",", ":"), sort_keys=True),
            json.dumps(metadata_json, separators=(",", ":"), sort_keys=True),
            created_by_actor_id,
            created_by_actor_type,
            created_at,
            created_at,
        ),
    )


def get_closure_snapshot(
    connection: sqlite3.Connection,
    closure_snapshot_id: str,
) -> dict[str, Any] | None:
    row = connection.execute(
        f"""
        SELECT {SNAPSHOT_COLUMNS}
        FROM capex_closure_snapshots
        WHERE closure_snapshot_id = ?
        """,
        (closure_snapshot_id,),
    ).fetchone()
    return _snapshot_row(row)


def list_current_closure_snapshots(
    connection: sqlite3.Connection,
    *,
    tenant_id: str | None = None,
    domain_id: str | None = None,
    project_id: str | None = None,
) -> list[dict[str, Any]]:
    clauses = ["state = 'current'"]
    params: list[str] = []
    if tenant_id is not None:
        clauses.append("tenant_id = ?")
        params.append(tenant_id)
    if domain_id is not None:
        clauses.append("domain_id = ?")
        params.append(domain_id)
    if project_id is not None:
        clauses.append("project_id = ?")
        params.append(project_id)
    where_clause = " AND ".join(clauses)
    rows = connection.execute(
        f"""
        SELECT {SNAPSHOT_COLUMNS}
        FROM capex_closure_snapshots
        WHERE {where_clause}
        ORDER BY created_at ASC, closure_snapshot_id ASC
        """,
        tuple(params),
    ).fetchall()
    return [_snapshot_row(row) for row in rows if row is not None]


def mark_closure_snapshot_stale(
    connection: sqlite3.Connection,
    *,
    closure_snapshot_id: str,
    stale_reason: str,
    stale_at: str,
) -> None:
    connection.execute(
        """
        UPDATE capex_closure_snapshots
        SET state = 'stale',
            stale_reason = ?,
            stale_at = ?,
            updated_at = ?
        WHERE closure_snapshot_id = ?
          AND state = 'current'
        """,
        (stale_reason, stale_at, stale_at, closure_snapshot_id),
    )


def _waiver_row(row: sqlite3.Row | None) -> dict[str, Any] | None:
    if row is None:
        return None
    item = dict(row)
    item["metadata_json"] = json.loads(str(item["metadata_json"]))
    return item


def _evaluation_row(row: sqlite3.Row | None) -> dict[str, Any] | None:
    if row is None:
        return None
    item = dict(row)
    for key in (
        "required_dimensions_json",
        "satisfied_dimensions_json",
        "missing_dimensions_json",
        "waiver_refs_json",
        "basis_version_vector_json",
        "metadata_json",
    ):
        item[key] = json.loads(str(item[key]))
    return item


def _snapshot_row(row: sqlite3.Row | None) -> dict[str, Any] | None:
    if row is None:
        return None
    item = dict(row)
    item["basis_version_vector_json"] = json.loads(str(item["basis_version_vector_json"]))
    item["metadata_json"] = json.loads(str(item["metadata_json"]))
    return item
