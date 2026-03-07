from __future__ import annotations

import sqlite3
from typing import Any


class PointerConflictError(ValueError):
    def __init__(self, pointer_key: str, current_artifact_version_id: str, generation: int) -> None:
        super().__init__(
            "pointer already targets a different artifact version "
            f"(pointer_key={pointer_key}, artifact_version_id={current_artifact_version_id}, generation={generation})"
        )
        self.pointer_key = pointer_key
        self.current_artifact_version_id = current_artifact_version_id
        self.generation = generation


class PointerGenerationMismatchError(ValueError):
    def __init__(self, pointer_key: str, expected_generation: int, actual_generation: int) -> None:
        super().__init__(
            "pointer generation mismatch "
            f"(pointer_key={pointer_key}, expected={expected_generation}, actual={actual_generation})"
        )
        self.pointer_key = pointer_key
        self.expected_generation = expected_generation
        self.actual_generation = actual_generation


class PointerDefinitionMismatchError(ValueError):
    def __init__(self, pointer_key: str) -> None:
        super().__init__(f"pointer scope/kind does not match existing definition: {pointer_key}")
        self.pointer_key = pointer_key


_DEFAULT_REGISTRY_KIND = "singleton"
_UNSET = object()


def _pointer_columns() -> str:
    return """
        pointer_id,
        workflow_run_id,
        pointer_key,
        tenant_id,
        domain_id,
        dataset_key,
        partition_kind,
        partition_key,
        stream_key,
        registry_kind,
        scope_kind,
        scope_ref,
        artifact_kind,
        artifact_version_id,
        promotion_reason,
        promoted_by_task_run_id,
        approved_by_approval_id,
        generation,
        updated_at
    """


def _workflow_scope(
    connection: sqlite3.Connection,
    workflow_run_id: str,
) -> dict[str, str] | None:
    row = connection.execute(
        """
        SELECT tenant_id, domain_id, partition_key
        FROM workflow_runs
        WHERE workflow_run_id = ?
        """,
        (workflow_run_id,),
    ).fetchone()
    if row is None:
        return None
    return {
        "tenant_id": str(row["tenant_id"]),
        "domain_id": str(row["domain_id"]),
        "partition_key": str(row["partition_key"]),
    }


def get_pointer_by_id(
    connection: sqlite3.Connection,
    *,
    pointer_id: str,
) -> dict[str, Any] | None:
    row = connection.execute(
        f"""
        SELECT {_pointer_columns()}
        FROM artifact_pointers
        WHERE pointer_id = ?
        """,
        (pointer_id,),
    ).fetchone()
    if row is None:
        return None
    return dict(row)


def get_pointer_by_address(
    connection: sqlite3.Connection,
    *,
    tenant_id: str,
    domain_id: str,
    dataset_key: str,
    partition_kind: str,
    partition_key: str,
    stream_key: str | None,
    registry_kind: str | None = None,
) -> dict[str, Any] | None:
    normalized_registry_kind = str(registry_kind or _DEFAULT_REGISTRY_KIND)
    row = connection.execute(
        f"""
        SELECT {_pointer_columns()}
        FROM artifact_pointers
        WHERE tenant_id = ?
          AND domain_id = ?
          AND dataset_key = ?
          AND partition_kind = ?
          AND partition_key = ?
          AND registry_kind = ?
          AND (
            (stream_key IS NULL AND ? IS NULL)
            OR stream_key = ?
          )
        ORDER BY updated_at DESC, pointer_id ASC
        LIMIT 1
        """,
        (
            tenant_id,
            domain_id,
            dataset_key,
            partition_kind,
            partition_key,
            normalized_registry_kind,
            stream_key,
            stream_key,
        ),
    ).fetchone()
    if row is None:
        return None
    return dict(row)


def list_pointers_by_canonical_scope(
    connection: sqlite3.Connection,
    *,
    tenant_id: str,
    domain_id: str,
    dataset_key: str | None = None,
    partition_kind: str | None = None,
    partition_key: str | None = None,
    stream_key: object = _UNSET,
    registry_kind: str | object = _UNSET,
    pointer_key: str | None = None,
    scope_kind: str | None = None,
    scope_ref: str | None = None,
    artifact_kind: str | None = None,
) -> list[dict[str, Any]]:
    query = f"""
        SELECT {_pointer_columns()}
        FROM artifact_pointers
        WHERE tenant_id = ? AND domain_id = ?
    """
    params: list[Any] = [tenant_id, domain_id]

    if dataset_key is not None:
        query += " AND dataset_key = ?"
        params.append(dataset_key)
    if partition_kind is not None:
        query += " AND partition_kind = ?"
        params.append(partition_kind)
    if partition_key is not None:
        query += " AND partition_key = ?"
        params.append(partition_key)
    if pointer_key is not None:
        query += " AND pointer_key = ?"
        params.append(pointer_key)
    if scope_kind is not None:
        query += " AND scope_kind = ?"
        params.append(scope_kind)
    if scope_ref is not None:
        query += " AND scope_ref = ?"
        params.append(scope_ref)
    if artifact_kind is not None:
        query += " AND artifact_kind = ?"
        params.append(artifact_kind)
    if stream_key is not _UNSET:
        if stream_key is None:
            query += " AND stream_key IS NULL"
        else:
            query += " AND stream_key = ?"
            params.append(str(stream_key))
    if registry_kind is not _UNSET:
        if registry_kind is None:
            query += " AND registry_kind IS NULL"
        else:
            query += " AND registry_kind = ?"
            params.append(str(registry_kind))

    query += " ORDER BY updated_at DESC, pointer_id ASC"
    rows = connection.execute(query, params).fetchall()
    return [dict(row) for row in rows]


def get_pointer(
    connection: sqlite3.Connection,
    *,
    workflow_run_id: str,
    pointer_key: str,
) -> dict[str, Any] | None:
    direct = connection.execute(
        f"""
        SELECT {_pointer_columns()}
        FROM artifact_pointers
        WHERE workflow_run_id = ? AND pointer_key = ?
        ORDER BY updated_at DESC, pointer_id ASC
        LIMIT 1
        """,
        (workflow_run_id, pointer_key),
    ).fetchone()
    if direct is not None:
        return dict(direct)

    scope = _workflow_scope(connection, workflow_run_id)
    if scope is None:
        return None

    fallback = connection.execute(
        f"""
        SELECT {_pointer_columns()}
        FROM artifact_pointers
        WHERE tenant_id = ?
          AND domain_id = ?
          AND partition_key = ?
          AND pointer_key = ?
        ORDER BY updated_at DESC, pointer_id ASC
        LIMIT 1
        """,
        (
            scope["tenant_id"],
            scope["domain_id"],
            scope["partition_key"],
            pointer_key,
        ),
    ).fetchone()
    if fallback is None:
        return None
    return dict(fallback)


def list_pointers_for_workflow_run(
    connection: sqlite3.Connection,
    workflow_run_id: str,
) -> list[dict[str, Any]]:
    scope = _workflow_scope(connection, workflow_run_id)
    if scope is None:
        return []

    rows = connection.execute(
        f"""
        SELECT {_pointer_columns()}
        FROM artifact_pointers
        WHERE tenant_id = ?
          AND domain_id = ?
          AND partition_key = ?
        ORDER BY pointer_key ASC, updated_at DESC, pointer_id ASC
        """,
        (
            scope["tenant_id"],
            scope["domain_id"],
            scope["partition_key"],
        ),
    ).fetchall()
    return [dict(row) for row in rows]


def promote_pointer(
    connection: sqlite3.Connection,
    *,
    workflow_run_id: str,
    pointer_key: str,
    scope_kind: str,
    scope_ref: str,
    artifact_kind: str,
    artifact_version_id: str,
    promotion_reason: str | None,
    promoted_by_task_run_id: str | None,
    approved_by_approval_id: str | None,
    updated_at: str,
    expected_generation: int | None,
    pointer_id: str | None = None,
    tenant_id: str | None = None,
    domain_id: str | None = None,
    dataset_key: str | None = None,
    partition_kind: str | None = None,
    partition_key: str | None = None,
    stream_key: str | None = None,
    registry_kind: str | None = None,
) -> tuple[dict[str, Any], bool]:
    resolved_pointer_id = str(pointer_id or "").strip()
    if not resolved_pointer_id:
        raise ValueError("pointer_id is required for canonical pointer promotion")

    existing = get_pointer_by_id(connection, pointer_id=resolved_pointer_id)
    if existing is None:
        connection.execute(
            """
            INSERT INTO artifact_pointers (
                pointer_id,
                workflow_run_id,
                pointer_key,
                tenant_id,
                domain_id,
                dataset_key,
                partition_kind,
                partition_key,
                stream_key,
                registry_kind,
                scope_kind,
                scope_ref,
                artifact_kind,
                artifact_version_id,
                promotion_reason,
                promoted_by_task_run_id,
                approved_by_approval_id,
                generation,
                updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                resolved_pointer_id,
                workflow_run_id,
                pointer_key,
                tenant_id,
                domain_id,
                dataset_key,
                partition_kind,
                partition_key,
                stream_key,
                registry_kind,
                scope_kind,
                scope_ref,
                artifact_kind,
                artifact_version_id,
                promotion_reason,
                promoted_by_task_run_id,
                approved_by_approval_id,
                0,
                updated_at,
            ),
        )
        created = get_pointer_by_id(connection, pointer_id=resolved_pointer_id)
        if created is None:
            raise RuntimeError("pointer not found after insert")
        return created, True

    if (
        str(existing["scope_kind"]) != scope_kind
        or str(existing["scope_ref"]) != scope_ref
        or str(existing["artifact_kind"]) != artifact_kind
    ):
        raise PointerDefinitionMismatchError(pointer_key)

    if str(existing["artifact_version_id"]) == artifact_version_id:
        return existing, False

    actual_generation = int(existing["generation"])
    if expected_generation is None:
        raise PointerConflictError(
            pointer_key,
            str(existing["artifact_version_id"]),
            actual_generation,
        )
    if expected_generation != actual_generation:
        raise PointerGenerationMismatchError(
            pointer_key,
            expected_generation,
            actual_generation,
        )

    connection.execute(
        """
        UPDATE artifact_pointers
        SET
            workflow_run_id = ?,
            pointer_key = ?,
            tenant_id = COALESCE(?, tenant_id),
            domain_id = COALESCE(?, domain_id),
            dataset_key = COALESCE(?, dataset_key),
            partition_kind = COALESCE(?, partition_kind),
            partition_key = COALESCE(?, partition_key),
            stream_key = COALESCE(?, stream_key),
            registry_kind = COALESCE(?, registry_kind),
            artifact_version_id = ?,
            promotion_reason = ?,
            promoted_by_task_run_id = ?,
            approved_by_approval_id = ?,
            generation = generation + 1,
            updated_at = ?
        WHERE pointer_id = ? AND generation = ?
        """,
        (
            workflow_run_id,
            pointer_key,
            tenant_id,
            domain_id,
            dataset_key,
            partition_kind,
            partition_key,
            stream_key,
            registry_kind,
            artifact_version_id,
            promotion_reason,
            promoted_by_task_run_id,
            approved_by_approval_id,
            updated_at,
            resolved_pointer_id,
            expected_generation,
        ),
    )

    updated = get_pointer_by_id(connection, pointer_id=resolved_pointer_id)
    if updated is None:
        raise RuntimeError("pointer not found after update")
    return updated, True
