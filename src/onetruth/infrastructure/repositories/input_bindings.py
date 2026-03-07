from __future__ import annotations

import json
import sqlite3
from typing import Any
from uuid import uuid4

from onetruth.infrastructure.repositories.artifact_pointers import get_pointer


class InputBindingConflictError(ValueError):
    def __init__(self, scope_kind: str, scope_ref: str, binding_key: str) -> None:
        super().__init__(
            "input binding already exists for scope/binding key "
            f"(scope_kind={scope_kind}, scope_ref={scope_ref}, binding_key={binding_key})"
        )
        self.scope_kind = scope_kind
        self.scope_ref = scope_ref
        self.binding_key = binding_key


def create_workflow_run_artifact_input(
    connection: sqlite3.Connection,
    *,
    workflow_run_id: str,
    binding_key: str,
    artifact_version_id: str,
    captured_by_task_run_id: str | None,
    captured_at: str,
    metadata_json: dict[str, Any] | None = None,
    workflow_run_input_id: str | None = None,
) -> str:
    return create_workflow_run_input(
        connection,
        workflow_run_id=workflow_run_id,
        binding_key=binding_key,
        source_kind="artifact_version",
        source_ref=artifact_version_id,
        artifact_version_id=artifact_version_id,
        pointer_key=None,
        pointer_generation=None,
        pointer_artifact_version_id=None,
        captured_by_task_run_id=captured_by_task_run_id,
        captured_at=captured_at,
        metadata_json=metadata_json,
        workflow_run_input_id=workflow_run_input_id,
    )


def create_workflow_run_input(
    connection: sqlite3.Connection,
    *,
    workflow_run_id: str,
    binding_key: str,
    source_kind: str,
    source_ref: str,
    artifact_version_id: str | None,
    pointer_key: str | None,
    pointer_generation: int | None,
    pointer_artifact_version_id: str | None,
    captured_by_task_run_id: str | None,
    captured_at: str,
    metadata_json: dict[str, Any] | None = None,
    workflow_run_input_id: str | None = None,
) -> str:
    resolved_id = workflow_run_input_id or f"wri-{uuid4()}"
    try:
        connection.execute(
            """
            INSERT INTO workflow_run_inputs (
                workflow_run_input_id,
                workflow_run_id,
                binding_key,
                source_kind,
                source_ref,
                artifact_version_id,
                pointer_key,
                pointer_generation,
                pointer_artifact_version_id,
                captured_by_task_run_id,
                captured_at,
                metadata_json
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                resolved_id,
                workflow_run_id,
                binding_key,
                source_kind,
                source_ref,
                artifact_version_id,
                pointer_key,
                pointer_generation,
                pointer_artifact_version_id,
                captured_by_task_run_id,
                captured_at,
                (
                    json.dumps(metadata_json, separators=(",", ":"))
                    if metadata_json is not None
                    else None
                ),
            ),
        )
    except sqlite3.IntegrityError as exc:
        message = str(exc)
        if (
            "uq_workflow_run_inputs_binding" in message
            or "workflow_run_inputs.workflow_run_id, workflow_run_inputs.binding_key" in message
        ):
            raise InputBindingConflictError("workflow_run", workflow_run_id, binding_key) from exc
        raise
    return resolved_id


def create_task_input_binding(
    connection: sqlite3.Connection,
    *,
    task_run_id: str,
    workflow_run_id: str,
    binding_key: str,
    source_kind: str,
    source_ref: str,
    artifact_version_id: str | None,
    pointer_key: str | None,
    pointer_generation: int | None,
    pointer_artifact_version_id: str | None,
    captured_at: str,
    metadata_json: dict[str, Any] | None = None,
    task_input_binding_id: str | None = None,
) -> str:
    resolved_id = task_input_binding_id or f"tib-{uuid4()}"
    try:
        connection.execute(
            """
            INSERT INTO task_input_bindings (
                task_input_binding_id,
                task_run_id,
                workflow_run_id,
                binding_key,
                source_kind,
                source_ref,
                artifact_version_id,
                pointer_key,
                pointer_generation,
                pointer_artifact_version_id,
                captured_at,
                metadata_json
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                resolved_id,
                task_run_id,
                workflow_run_id,
                binding_key,
                source_kind,
                source_ref,
                artifact_version_id,
                pointer_key,
                pointer_generation,
                pointer_artifact_version_id,
                captured_at,
                (
                    json.dumps(metadata_json, separators=(",", ":"))
                    if metadata_json is not None
                    else None
                ),
            ),
        )
    except sqlite3.IntegrityError as exc:
        message = str(exc)
        if (
            "uq_task_input_bindings_binding" in message
            or "task_input_bindings.task_run_id, task_input_bindings.binding_key" in message
        ):
            raise InputBindingConflictError("task_run", task_run_id, binding_key) from exc
        raise
    return resolved_id


def capture_task_pointer_input(
    connection: sqlite3.Connection,
    *,
    task_run_id: str,
    workflow_run_id: str,
    binding_key: str,
    pointer_key: str,
    captured_at: str,
    metadata_json: dict[str, Any] | None = None,
    task_input_binding_id: str | None = None,
) -> str:
    pointer = get_pointer(
        connection,
        workflow_run_id=workflow_run_id,
        pointer_key=pointer_key,
    )
    if pointer is None:
        raise ValueError(
            "pointer not found for binding capture "
            f"(workflow_run_id={workflow_run_id}, pointer_key={pointer_key})"
        )

    return create_task_input_binding(
        connection,
        task_run_id=task_run_id,
        workflow_run_id=workflow_run_id,
        binding_key=binding_key,
        source_kind="pointer",
        source_ref=pointer_key,
        artifact_version_id=str(pointer["artifact_version_id"]),
        pointer_key=pointer_key,
        pointer_generation=int(pointer["generation"]),
        pointer_artifact_version_id=str(pointer["artifact_version_id"]),
        captured_at=captured_at,
        metadata_json=metadata_json,
        task_input_binding_id=task_input_binding_id,
    )


def list_task_input_bindings(
    connection: sqlite3.Connection,
    task_run_id: str,
) -> list[dict[str, Any]]:
    rows = connection.execute(
        """
        SELECT
            task_input_binding_id,
            task_run_id,
            workflow_run_id,
            binding_key,
            source_kind,
            source_ref,
            artifact_version_id,
            pointer_key,
            pointer_generation,
            pointer_artifact_version_id,
            captured_at,
            metadata_json,
            created_at
        FROM task_input_bindings
        WHERE task_run_id = ?
        ORDER BY binding_key ASC
        """,
        (task_run_id,),
    ).fetchall()
    items: list[dict[str, Any]] = []
    for row in rows:
        item = dict(row)
        if item["metadata_json"] is not None:
            item["metadata_json"] = json.loads(item["metadata_json"])
        items.append(item)
    return items


def is_task_input_binding_stale(
    connection: sqlite3.Connection,
    *,
    task_run_id: str,
    binding_key: str,
) -> bool:
    binding = connection.execute(
        """
        SELECT
            workflow_run_id,
            source_kind,
            source_ref,
            pointer_key,
            pointer_generation,
            pointer_artifact_version_id
        FROM task_input_bindings
        WHERE task_run_id = ? AND binding_key = ?
        """,
        (task_run_id, binding_key),
    ).fetchone()
    if binding is None:
        raise ValueError(
            "task input binding not found "
            f"(task_run_id={task_run_id}, binding_key={binding_key})"
        )

    if str(binding["source_kind"]) != "pointer":
        return False

    resolved_pointer_key = (
        str(binding["pointer_key"])
        if binding["pointer_key"] is not None
        else str(binding["source_ref"])
    )
    current = get_pointer(
        connection,
        workflow_run_id=str(binding["workflow_run_id"]),
        pointer_key=resolved_pointer_key,
    )
    if current is None:
        return True

    if int(current["generation"]) != int(binding["pointer_generation"]):
        return True
    if str(current["artifact_version_id"]) != str(binding["pointer_artifact_version_id"]):
        return True
    return False
