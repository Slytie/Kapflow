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


def get_pointer(
    connection: sqlite3.Connection,
    *,
    workflow_run_id: str,
    pointer_key: str,
) -> dict[str, Any] | None:
    row = connection.execute(
        """
        SELECT
            workflow_run_id,
            pointer_key,
            scope_kind,
            scope_ref,
            artifact_kind,
            artifact_version_id,
            promotion_reason,
            promoted_by_task_run_id,
            approved_by_approval_id,
            generation,
            updated_at
        FROM artifact_pointers
        WHERE workflow_run_id = ? AND pointer_key = ?
        """,
        (workflow_run_id, pointer_key),
    ).fetchone()
    if row is None:
        return None
    return dict(row)


def list_pointers_for_workflow_run(
    connection: sqlite3.Connection,
    workflow_run_id: str,
) -> list[dict[str, Any]]:
    rows = connection.execute(
        """
        SELECT
            workflow_run_id,
            pointer_key,
            scope_kind,
            scope_ref,
            artifact_kind,
            artifact_version_id,
            promotion_reason,
            promoted_by_task_run_id,
            approved_by_approval_id,
            generation,
            updated_at
        FROM artifact_pointers
        WHERE workflow_run_id = ?
        ORDER BY pointer_key ASC
        """,
        (workflow_run_id,),
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
    existing = get_pointer(
        connection,
        workflow_run_id=workflow_run_id,
        pointer_key=pointer_key,
    )
    if existing is None:
        connection.execute(
            """
            INSERT INTO artifact_pointers (
                workflow_run_id,
                pointer_key,
                pointer_id,
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
                workflow_run_id,
                pointer_key,
                pointer_id,
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
        created = get_pointer(
            connection,
            workflow_run_id=workflow_run_id,
            pointer_key=pointer_key,
        )
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
            pointer_id = COALESCE(?, pointer_id),
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
        WHERE workflow_run_id = ? AND pointer_key = ? AND generation = ?
        """,
        (
            pointer_id,
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
            workflow_run_id,
            pointer_key,
            expected_generation,
        ),
    )

    updated = get_pointer(
        connection,
        workflow_run_id=workflow_run_id,
        pointer_key=pointer_key,
    )
    if updated is None:
        raise RuntimeError("pointer not found after update")
    return updated, True
