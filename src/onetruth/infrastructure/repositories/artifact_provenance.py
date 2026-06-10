from __future__ import annotations

import json
import sqlite3
from typing import Any, Iterable
from uuid import uuid4


class ProvenanceCycleError(ValueError):
    def __init__(self, output_artifact_version_id: str, input_artifact_version_id: str) -> None:
        super().__init__(
            "artifact provenance edge would create a cycle "
            f"(output_artifact_version_id={output_artifact_version_id}, "
            f"input_artifact_version_id={input_artifact_version_id})"
        )
        self.output_artifact_version_id = output_artifact_version_id
        self.input_artifact_version_id = input_artifact_version_id


class ProvenanceProjectScopeError(ValueError):
    def __init__(
        self,
        *,
        output_artifact_version_id: str,
        input_artifact_version_id: str,
        workflow_run_id: str | None,
    ) -> None:
        super().__init__(
            "artifact provenance edge crosses project scope "
            f"(output_artifact_version_id={output_artifact_version_id}, "
            f"input_artifact_version_id={input_artifact_version_id}, "
            f"workflow_run_id={workflow_run_id})"
        )
        self.output_artifact_version_id = output_artifact_version_id
        self.input_artifact_version_id = input_artifact_version_id
        self.workflow_run_id = workflow_run_id


def create_artifact_provenance_edge(
    connection: sqlite3.Connection,
    *,
    output_artifact_version_id: str,
    input_artifact_version_id: str,
    edge_type: str,
    workflow_run_id: str | None,
    edge_order: int | None,
    created_at: str,
    edge_id: str | None = None,
    metadata_json: dict[str, Any] | None = None,
) -> str:
    if output_artifact_version_id == input_artifact_version_id:
        raise ProvenanceCycleError(output_artifact_version_id, input_artifact_version_id)

    if _creates_cycle(
        connection,
        output_artifact_version_id=output_artifact_version_id,
        input_artifact_version_id=input_artifact_version_id,
    ):
        raise ProvenanceCycleError(output_artifact_version_id, input_artifact_version_id)

    project_id = _resolve_edge_project_id(
        connection,
        output_artifact_version_id=output_artifact_version_id,
        input_artifact_version_id=input_artifact_version_id,
        workflow_run_id=workflow_run_id,
    )
    resolved_edge_id = edge_id or f"ape-{uuid4()}"
    connection.execute(
        """
        INSERT INTO artifact_provenance_edges (
            edge_id,
            workflow_run_id,
            project_id,
            output_artifact_version_id,
            input_artifact_version_id,
            edge_type,
            edge_order,
            metadata_json,
            created_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            resolved_edge_id,
            workflow_run_id,
            project_id,
            output_artifact_version_id,
            input_artifact_version_id,
            _normalize_edge_type(edge_type),
            edge_order,
            (
                json.dumps(metadata_json, separators=(",", ":"))
                if metadata_json is not None
                else None
            ),
            created_at,
        ),
    )
    return resolved_edge_id


def list_artifact_provenance_edges_for_output(
    connection: sqlite3.Connection,
    output_artifact_version_id: str,
) -> list[dict[str, Any]]:
    rows = connection.execute(
        """
        SELECT
            edge_id,
            workflow_run_id,
            project_id,
            output_artifact_version_id,
            input_artifact_version_id,
            edge_type,
            edge_order,
            metadata_json,
            created_at
        FROM artifact_provenance_edges
        WHERE output_artifact_version_id = ?
        ORDER BY
            CASE WHEN edge_order IS NULL THEN 1 ELSE 0 END ASC,
            edge_order ASC,
            edge_type ASC,
            input_artifact_version_id ASC,
            edge_id ASC
        """,
        (output_artifact_version_id,),
    ).fetchall()
    items: list[dict[str, Any]] = []
    for row in rows:
        item = dict(row)
        if item["metadata_json"] is not None:
            item["metadata_json"] = json.loads(item["metadata_json"])
        items.append(item)
    return items


def project_legacy_lineage_fields(
    connection: sqlite3.Connection,
    output_artifact_version_id: str,
) -> dict[str, str | None]:
    edge_rows = list_artifact_provenance_edges_for_output(connection, output_artifact_version_id)
    return project_legacy_lineage_from_edge_rows(edge_rows)


def project_legacy_lineage_from_edge_rows(
    edge_rows: Iterable[dict[str, Any]],
) -> dict[str, str | None]:
    rows = [dict(row) for row in edge_rows]
    parent_artifact_version_id = _pick_first_input(rows, edge_type="derives_from")
    supersedes_artifact_version_id = _pick_first_input(rows, edge_type="supersedes")
    return {
        "parent_artifact_version_id": parent_artifact_version_id,
        "supersedes_artifact_version_id": supersedes_artifact_version_id,
    }


def _pick_first_input(rows: list[dict[str, Any]], *, edge_type: str) -> str | None:
    normalized = _normalize_edge_type(edge_type)
    candidates = [row for row in rows if _normalize_edge_type(str(row.get("edge_type", ""))) == normalized]
    if not candidates:
        return None
    ordered = sorted(
        candidates,
        key=lambda row: (
            row.get("edge_order") is None,
            _edge_order_value(row.get("edge_order")),
            str(row.get("input_artifact_version_id", "")),
            str(row.get("edge_id", "")),
        ),
    )
    return str(ordered[0].get("input_artifact_version_id")) or None


def _edge_order_value(raw: Any) -> int:
    if raw is None:
        return 0
    try:
        return int(raw)
    except (TypeError, ValueError):
        return 0


def _normalize_edge_type(edge_type: str) -> str:
    normalized = str(edge_type).strip().lower().replace("-", "_")
    if not normalized:
        raise ValueError("edge_type must be non-empty")
    return normalized


def _resolve_edge_project_id(
    connection: sqlite3.Connection,
    *,
    output_artifact_version_id: str,
    input_artifact_version_id: str,
    workflow_run_id: str | None,
) -> str | None:
    output_scope = _artifact_scope(connection, output_artifact_version_id)
    input_scope = _artifact_scope(connection, input_artifact_version_id)
    output_project_id = output_scope.get("project_id")
    input_project_id = input_scope.get("project_id")
    if output_project_id != input_project_id:
        raise ProvenanceProjectScopeError(
            output_artifact_version_id=output_artifact_version_id,
            input_artifact_version_id=input_artifact_version_id,
            workflow_run_id=workflow_run_id,
        )
    if workflow_run_id is not None:
        workflow_scope = _workflow_scope(connection, workflow_run_id)
        workflow_project_id = workflow_scope.get("project_id")
        if workflow_project_id != output_project_id:
            raise ProvenanceProjectScopeError(
                output_artifact_version_id=output_artifact_version_id,
                input_artifact_version_id=input_artifact_version_id,
                workflow_run_id=workflow_run_id,
            )
    return output_project_id


def _artifact_scope(
    connection: sqlite3.Connection,
    artifact_version_id: str,
) -> dict[str, str | None]:
    row = connection.execute(
        """
        SELECT project_id
        FROM artifact_versions
        WHERE artifact_version_id = ?
        """,
        (artifact_version_id,),
    ).fetchone()
    if row is None:
        return {"project_id": None}
    return {
        "project_id": (
            str(row["project_id"]) if row["project_id"] is not None else None
        )
    }


def _workflow_scope(
    connection: sqlite3.Connection,
    workflow_run_id: str,
) -> dict[str, str | None]:
    row = connection.execute(
        """
        SELECT project_id
        FROM workflow_runs
        WHERE workflow_run_id = ?
        """,
        (workflow_run_id,),
    ).fetchone()
    if row is None:
        return {"project_id": None}
    return {
        "project_id": (
            str(row["project_id"]) if row["project_id"] is not None else None
        )
    }


def _creates_cycle(
    connection: sqlite3.Connection,
    *,
    output_artifact_version_id: str,
    input_artifact_version_id: str,
) -> bool:
    row = connection.execute(
        """
        WITH RECURSIVE lineage(node) AS (
            SELECT ?
            UNION
            SELECT edge.input_artifact_version_id
            FROM artifact_provenance_edges AS edge
            JOIN lineage ON edge.output_artifact_version_id = lineage.node
        )
        SELECT 1
        FROM lineage
        WHERE node = ?
        LIMIT 1
        """,
        (input_artifact_version_id, output_artifact_version_id),
    ).fetchone()
    return row is not None
