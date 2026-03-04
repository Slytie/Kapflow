from __future__ import annotations

import json
import sqlite3
from typing import Any


def create_artifact_link(
    connection: sqlite3.Connection,
    *,
    artifact_version_id: str,
    workflow_run_id: str,
    subject_kind: str,
    subject_id: str,
    relation_kind: str,
    created_at: str,
    created_by_actor_id: str,
    created_by_actor_type: str,
) -> None:
    connection.execute(
        """
        INSERT INTO artifact_links (
            artifact_version_id,
            workflow_run_id,
            subject_kind,
            subject_id,
            relation_kind,
            created_at,
            created_by_actor_id,
            created_by_actor_type
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            artifact_version_id,
            workflow_run_id,
            subject_kind,
            subject_id,
            relation_kind,
            created_at,
            created_by_actor_id,
            created_by_actor_type,
        ),
    )


def list_artifact_links_for_subject(
    connection: sqlite3.Connection,
    *,
    workflow_run_id: str,
    subject_kind: str,
    subject_id: str,
) -> list[dict[str, Any]]:
    rows = connection.execute(
        """
        SELECT
            artifact_version_id,
            workflow_run_id,
            subject_kind,
            subject_id,
            relation_kind,
            created_at,
            created_by_actor_id,
            created_by_actor_type
        FROM artifact_links
        WHERE workflow_run_id = ?
            AND subject_kind = ?
            AND subject_id = ?
        ORDER BY created_at ASC, artifact_version_id ASC
        """,
        (workflow_run_id, subject_kind, subject_id),
    ).fetchall()
    return [dict(row) for row in rows]


def list_artifact_links_for_artifact(
    connection: sqlite3.Connection,
    *,
    artifact_version_id: str,
) -> list[dict[str, Any]]:
    rows = connection.execute(
        """
        SELECT
            artifact_version_id,
            workflow_run_id,
            subject_kind,
            subject_id,
            relation_kind,
            created_at,
            created_by_actor_id,
            created_by_actor_type
        FROM artifact_links
        WHERE artifact_version_id = ?
        ORDER BY created_at ASC, subject_kind ASC, subject_id ASC
        """,
        (artifact_version_id,),
    ).fetchall()
    return [dict(row) for row in rows]


def list_artifacts_for_subject(
    connection: sqlite3.Connection,
    *,
    workflow_run_id: str,
    subject_kind: str,
    subject_id: str,
) -> list[dict[str, Any]]:
    rows = connection.execute(
        """
        SELECT
            av.artifact_version_id,
            av.workflow_run_id,
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
            av.created_at
        FROM artifact_versions av
        JOIN artifact_links al
            ON al.artifact_version_id = av.artifact_version_id
        WHERE al.workflow_run_id = ?
            AND al.subject_kind = ?
            AND al.subject_id = ?
        ORDER BY av.created_at ASC, av.artifact_version_id ASC
        """,
        (workflow_run_id, subject_kind, subject_id),
    ).fetchall()
    items: list[dict[str, Any]] = []
    for row in rows:
        item = dict(row)
        item["metadata_json"] = json.loads(item["metadata_json"])
        items.append(item)
    return items
