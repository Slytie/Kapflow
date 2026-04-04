from __future__ import annotations

import json
import sqlite3
from typing import Any


def create_artifact_version(
    connection: sqlite3.Connection,
    *,
    artifact_version_id: str,
    workflow_run_id: str,
    task_run_id: str | None,
    artifact_kind: str,
    artifact_role: str | None,
    media_type: str,
    storage_uri: str,
    content_digest: str,
    byte_size: int | None,
    metadata_json: dict[str, Any],
    parent_artifact_version_id: str | None,
    supersedes_artifact_version_id: str | None,
    lineage_note: str | None,
    created_at: str,
    tenant_id: str | None = None,
    domain_id: str | None = None,
    dataset_key: str | None = None,
    partition_kind: str | None = None,
    partition_key: str | None = None,
) -> None:
    connection.execute(
        """
        INSERT INTO artifact_versions (
            artifact_version_id,
            workflow_run_id,
            tenant_id,
            domain_id,
            dataset_key,
            partition_kind,
            partition_key,
            task_run_id,
            artifact_kind,
            artifact_role,
            media_type,
            storage_uri,
            content_digest,
            byte_size,
            metadata_json,
            parent_artifact_version_id,
            supersedes_artifact_version_id,
            lineage_note,
            created_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            artifact_version_id,
            workflow_run_id,
            tenant_id,
            domain_id,
            dataset_key,
            partition_kind,
            partition_key,
            task_run_id,
            artifact_kind,
            artifact_role,
            media_type,
            storage_uri,
            content_digest,
            byte_size,
            json.dumps(metadata_json, separators=(",", ":")),
            parent_artifact_version_id,
            supersedes_artifact_version_id,
            lineage_note,
            created_at,
        ),
    )


def get_artifact_version(
    connection: sqlite3.Connection,
    artifact_version_id: str,
) -> dict[str, Any] | None:
    row = connection.execute(
        """
        SELECT
            artifact_version_id,
            workflow_run_id,
            tenant_id,
            domain_id,
            dataset_key,
            partition_kind,
            partition_key,
            task_run_id,
            artifact_kind,
            artifact_role,
            media_type,
            storage_uri,
            content_digest,
            byte_size,
            metadata_json,
            parent_artifact_version_id,
            supersedes_artifact_version_id,
            lineage_note,
            created_at
        FROM artifact_versions
        WHERE artifact_version_id = ?
        """,
        (artifact_version_id,),
    ).fetchone()
    if row is None:
        return None
    item = dict(row)
    item["metadata_json"] = json.loads(item["metadata_json"])
    return item


def get_superseding_artifact_version(
    connection: sqlite3.Connection,
    artifact_version_id: str,
) -> dict[str, Any] | None:
    row = connection.execute(
        """
        SELECT
            artifact_version_id,
            workflow_run_id,
            tenant_id,
            domain_id,
            dataset_key,
            partition_kind,
            partition_key,
            task_run_id,
            artifact_kind,
            artifact_role,
            media_type,
            storage_uri,
            content_digest,
            byte_size,
            metadata_json,
            parent_artifact_version_id,
            supersedes_artifact_version_id,
            lineage_note,
            created_at
        FROM artifact_versions
        WHERE supersedes_artifact_version_id = ?
        ORDER BY created_at DESC, artifact_version_id DESC
        LIMIT 1
        """,
        (artifact_version_id,),
    ).fetchone()
    if row is None:
        return None
    item = dict(row)
    item["metadata_json"] = json.loads(item["metadata_json"])
    return item


def get_latest_artifact_version_in_chain(
    connection: sqlite3.Connection,
    artifact_version_id: str,
) -> dict[str, Any] | None:
    current = get_artifact_version(connection, artifact_version_id)
    if current is None:
        return None

    seen_artifact_version_ids = {artifact_version_id}
    while True:
        superseding = get_superseding_artifact_version(
            connection,
            str(current["artifact_version_id"]),
        )
        if superseding is None:
            return current
        current_id = str(superseding["artifact_version_id"])
        if current_id in seen_artifact_version_ids:
            raise ValueError(
                f"artifact_version supersession cycle detected: {current_id}"
            )
        seen_artifact_version_ids.add(current_id)
        current = superseding


def list_artifact_versions_for_workflow_run(
    connection: sqlite3.Connection,
    workflow_run_id: str,
) -> list[dict[str, Any]]:
    rows = connection.execute(
        """
        SELECT
            artifact_version_id,
            workflow_run_id,
            tenant_id,
            domain_id,
            dataset_key,
            partition_kind,
            partition_key,
            task_run_id,
            artifact_kind,
            artifact_role,
            media_type,
            storage_uri,
            content_digest,
            byte_size,
            metadata_json,
            parent_artifact_version_id,
            supersedes_artifact_version_id,
            lineage_note,
            created_at
        FROM artifact_versions
        WHERE workflow_run_id = ?
        ORDER BY created_at ASC, artifact_version_id ASC
        """,
        (workflow_run_id,),
    ).fetchall()
    items: list[dict[str, Any]] = []
    for row in rows:
        item = dict(row)
        item["metadata_json"] = json.loads(item["metadata_json"])
        items.append(item)
    return items


def list_artifact_versions_for_scope_and_kind(
    connection: sqlite3.Connection,
    *,
    tenant_id: str,
    domain_id: str,
    artifact_kind: str,
    workflow_id: str | None = None,
) -> list[dict[str, Any]]:
    query = """
        SELECT
            av.artifact_version_id,
            av.workflow_run_id,
            av.tenant_id,
            av.domain_id,
            av.dataset_key,
            av.partition_kind,
            av.partition_key,
            av.task_run_id,
            av.artifact_kind,
            av.artifact_role,
            av.media_type,
            av.storage_uri,
            av.content_digest,
            av.byte_size,
            av.metadata_json,
            av.parent_artifact_version_id,
            av.supersedes_artifact_version_id,
            av.lineage_note,
            av.created_at,
            wr.workflow_id AS workflow_id,
            wr.partition_key AS workflow_partition_key,
            wr.logical_date AS workflow_logical_date,
            wr.state AS workflow_state
        FROM artifact_versions av
        JOIN workflow_runs wr
          ON wr.workflow_run_id = av.workflow_run_id
        WHERE av.tenant_id = ?
          AND av.domain_id = ?
          AND av.artifact_kind = ?
    """
    params: list[Any] = [tenant_id, domain_id, artifact_kind]
    if workflow_id is not None:
        query += " AND wr.workflow_id = ?"
        params.append(workflow_id)
    query += """
        ORDER BY
            wr.logical_date ASC,
            av.created_at ASC,
            av.artifact_version_id ASC
    """
    rows = connection.execute(query, params).fetchall()
    items: list[dict[str, Any]] = []
    for row in rows:
        item = dict(row)
        item["metadata_json"] = json.loads(item["metadata_json"])
        items.append(item)
    return items
