from __future__ import annotations

import json
import sqlite3
from typing import Any


CONTENT_IDENTITY_COLUMNS = """
    content_identity_id,
    tenant_id,
    domain_id,
    digest_algorithm,
    content_digest,
    byte_size,
    media_type,
    canonicalization_profile,
    metadata_json,
    created_at
"""

SOURCE_OCCURRENCE_COLUMNS = """
    source_occurrence_id,
    tenant_id,
    domain_id,
    project_id,
    content_identity_id,
    occurrence_kind,
    status,
    source_ref,
    locator_json,
    metadata_json,
    registered_by_actor_id,
    registered_by_actor_type,
    created_at,
    updated_at
"""

SOURCE_REF_PREFIX = "source_occurrence:"
SOURCE_OCCURRENCE_STATUSES = (
    "available",
    "quarantined",
    "redacted",
    "superseded",
    "deleted",
)
RESOLVABLE_SOURCE_OCCURRENCE_STATUSES = frozenset({"available"})


def content_identity_id(
    *,
    tenant_id: str,
    domain_id: str,
    digest_algorithm: str,
    content_digest: str,
) -> str:
    return (
        f"cci:{tenant_id}:{domain_id}:"
        f"{digest_algorithm.lower()}:{content_digest.lower()}"
    )


def source_ref_for_occurrence(source_occurrence_id: str) -> str:
    return f"{SOURCE_REF_PREFIX}{source_occurrence_id}"


def parse_source_occurrence_ref(source_ref: str) -> str | None:
    if not source_ref.startswith(SOURCE_REF_PREFIX):
        return None
    source_occurrence_id = source_ref.removeprefix(SOURCE_REF_PREFIX)
    if not source_occurrence_id or any(character.isspace() for character in source_occurrence_id):
        return None
    return source_occurrence_id


def create_content_identity(
    connection: sqlite3.Connection,
    *,
    content_identity_id: str,
    tenant_id: str,
    domain_id: str,
    digest_algorithm: str,
    content_digest: str,
    byte_size: int | None,
    media_type: str | None,
    canonicalization_profile: str | None,
    metadata_json: dict[str, Any],
    created_at: str,
) -> None:
    connection.execute(
        """
        INSERT INTO capex_content_identities (
            content_identity_id,
            tenant_id,
            domain_id,
            digest_algorithm,
            content_digest,
            byte_size,
            media_type,
            canonicalization_profile,
            metadata_json,
            created_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            content_identity_id,
            tenant_id,
            domain_id,
            digest_algorithm,
            content_digest,
            byte_size,
            media_type,
            canonicalization_profile,
            json.dumps(metadata_json, separators=(",", ":"), sort_keys=True),
            created_at,
        ),
    )


def upsert_content_identity(
    connection: sqlite3.Connection,
    *,
    tenant_id: str,
    domain_id: str,
    digest_algorithm: str,
    content_digest: str,
    byte_size: int | None,
    media_type: str | None,
    canonicalization_profile: str | None,
    metadata_json: dict[str, Any],
    created_at: str,
    requested_content_identity_id: str | None = None,
) -> str:
    resolved_id = requested_content_identity_id or content_identity_id(
        tenant_id=tenant_id,
        domain_id=domain_id,
        digest_algorithm=digest_algorithm,
        content_digest=content_digest,
    )
    connection.execute(
        """
        INSERT INTO capex_content_identities (
            content_identity_id,
            tenant_id,
            domain_id,
            digest_algorithm,
            content_digest,
            byte_size,
            media_type,
            canonicalization_profile,
            metadata_json,
            created_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(tenant_id, domain_id, digest_algorithm, content_digest)
        DO NOTHING
        """,
        (
            resolved_id,
            tenant_id,
            domain_id,
            digest_algorithm,
            content_digest,
            byte_size,
            media_type,
            canonicalization_profile,
            json.dumps(metadata_json, separators=(",", ":"), sort_keys=True),
            created_at,
        ),
    )
    existing = get_content_identity_by_digest(
        connection,
        tenant_id=tenant_id,
        domain_id=domain_id,
        digest_algorithm=digest_algorithm,
        content_digest=content_digest,
    )
    if existing is None:
        raise RuntimeError("content identity upsert failed")
    return str(existing["content_identity_id"])


def get_content_identity(
    connection: sqlite3.Connection,
    content_identity_id: str,
) -> dict[str, Any] | None:
    row = connection.execute(
        f"""
        SELECT {CONTENT_IDENTITY_COLUMNS}
        FROM capex_content_identities
        WHERE content_identity_id = ?
        """,
        (content_identity_id,),
    ).fetchone()
    return _content_identity_row(row)


def get_content_identity_by_digest(
    connection: sqlite3.Connection,
    *,
    tenant_id: str,
    domain_id: str,
    digest_algorithm: str,
    content_digest: str,
) -> dict[str, Any] | None:
    row = connection.execute(
        f"""
        SELECT {CONTENT_IDENTITY_COLUMNS}
        FROM capex_content_identities
        WHERE tenant_id = ?
          AND domain_id = ?
          AND digest_algorithm = ?
          AND content_digest = ?
        """,
        (tenant_id, domain_id, digest_algorithm, content_digest),
    ).fetchone()
    return _content_identity_row(row)


def create_source_occurrence(
    connection: sqlite3.Connection,
    *,
    source_occurrence_id: str,
    tenant_id: str,
    domain_id: str,
    project_id: str | None,
    content_identity_id: str,
    occurrence_kind: str,
    status: str,
    locator_json: dict[str, Any],
    metadata_json: dict[str, Any],
    registered_by_actor_id: str,
    registered_by_actor_type: str,
    created_at: str,
    source_ref: str | None = None,
) -> None:
    if status not in SOURCE_OCCURRENCE_STATUSES:
        raise ValueError(f"invalid source occurrence status: {status}")
    resolved_source_ref = source_ref or source_ref_for_occurrence(source_occurrence_id)
    connection.execute(
        """
        INSERT INTO capex_source_occurrences (
            source_occurrence_id,
            tenant_id,
            domain_id,
            project_id,
            content_identity_id,
            occurrence_kind,
            status,
            source_ref,
            locator_json,
            metadata_json,
            registered_by_actor_id,
            registered_by_actor_type,
            created_at,
            updated_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            source_occurrence_id,
            tenant_id,
            domain_id,
            project_id,
            content_identity_id,
            occurrence_kind,
            status,
            resolved_source_ref,
            json.dumps(locator_json, separators=(",", ":"), sort_keys=True),
            json.dumps(metadata_json, separators=(",", ":"), sort_keys=True),
            registered_by_actor_id,
            registered_by_actor_type,
            created_at,
            created_at,
        ),
    )


def update_source_occurrence_status(
    connection: sqlite3.Connection,
    *,
    source_occurrence_id: str,
    status: str,
    updated_at: str,
) -> None:
    if status not in SOURCE_OCCURRENCE_STATUSES:
        raise ValueError(f"invalid source occurrence status: {status}")
    connection.execute(
        """
        UPDATE capex_source_occurrences
        SET status = ?, updated_at = ?
        WHERE source_occurrence_id = ?
        """,
        (status, updated_at, source_occurrence_id),
    )


def get_source_occurrence(
    connection: sqlite3.Connection,
    source_occurrence_id: str,
) -> dict[str, Any] | None:
    row = connection.execute(
        f"""
        SELECT {SOURCE_OCCURRENCE_COLUMNS}
        FROM capex_source_occurrences
        WHERE source_occurrence_id = ?
        """,
        (source_occurrence_id,),
    ).fetchone()
    return _source_occurrence_row(row)


def get_source_occurrence_by_ref(
    connection: sqlite3.Connection,
    source_ref: str,
) -> dict[str, Any] | None:
    row = connection.execute(
        f"""
        SELECT {SOURCE_OCCURRENCE_COLUMNS}
        FROM capex_source_occurrences
        WHERE source_ref = ?
        """,
        (source_ref,),
    ).fetchone()
    return _source_occurrence_row(row)


def get_source_occurrence_with_content_identity(
    connection: sqlite3.Connection,
    source_ref: str,
) -> dict[str, Any] | None:
    row = connection.execute(
        """
        SELECT
            so.source_occurrence_id,
            so.tenant_id,
            so.domain_id,
            so.project_id,
            so.content_identity_id,
            so.occurrence_kind,
            so.status,
            so.source_ref,
            so.locator_json,
            so.metadata_json,
            so.registered_by_actor_id,
            so.registered_by_actor_type,
            so.created_at,
            so.updated_at,
            ci.digest_algorithm AS content_digest_algorithm,
            ci.content_digest AS content_digest,
            ci.byte_size AS content_byte_size,
            ci.media_type AS content_media_type,
            ci.canonicalization_profile AS content_canonicalization_profile
        FROM capex_source_occurrences so
        JOIN capex_content_identities ci
          ON ci.content_identity_id = so.content_identity_id
        WHERE so.source_ref = ?
        """,
        (source_ref,),
    ).fetchone()
    if row is None:
        return None
    item = _source_occurrence_row(row)
    assert item is not None
    item.update(
        {
            "content_digest_algorithm": row["content_digest_algorithm"],
            "content_digest": row["content_digest"],
            "content_byte_size": row["content_byte_size"],
            "content_media_type": row["content_media_type"],
            "content_canonicalization_profile": row[
                "content_canonicalization_profile"
            ],
        }
    )
    return item


def _content_identity_row(row: sqlite3.Row | None) -> dict[str, Any] | None:
    if row is None:
        return None
    item = dict(row)
    item["metadata_json"] = json.loads(str(item["metadata_json"]))
    return item


def _source_occurrence_row(row: sqlite3.Row | None) -> dict[str, Any] | None:
    if row is None:
        return None
    item = dict(row)
    item["locator_json"] = json.loads(str(item["locator_json"]))
    item["metadata_json"] = json.loads(str(item["metadata_json"]))
    return item
