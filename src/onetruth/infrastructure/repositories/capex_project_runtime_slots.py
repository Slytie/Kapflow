from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import json
import re
import sqlite3
from typing import Any


POLICY_COLUMNS = """
    project_concurrency_policy_id,
    tenant_id,
    domain_id,
    project_id,
    lock_family,
    max_active_slots,
    state,
    policy_version,
    metadata_json,
    created_at,
    updated_at
"""

SLOT_COLUMNS = """
    project_runtime_slot_id,
    tenant_id,
    domain_id,
    project_id,
    lock_family,
    slot_key,
    holder_ref,
    lease_token,
    state,
    active_family_key,
    acquired_at,
    expires_at,
    released_at,
    metadata_json,
    created_at,
    updated_at
"""

SUPPORTED_LOCK_FAMILIES = {"ingest", "pointer"}
DEFAULT_POLICY_VERSION = "capex.project_runtime_slot_policy.v1"
_CANONICAL_REF_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.:/#@-]{0,254}$")
_FORBIDDEN_RAW_KEYS = {
    "absolute_path",
    "base64",
    "base64_content",
    "blob_bytes",
    "content_base64",
    "file_name",
    "filename",
    "local_path",
    "raw_bytes",
    "raw_content",
    "raw_filename",
    "raw_log",
    "source_path",
}


@dataclass(frozen=True)
class ProjectRuntimeSlotError(ValueError):
    code: str
    details: dict[str, Any]

    def __str__(self) -> str:
        return self.code


def ensure_project_concurrency_policy(
    connection: sqlite3.Connection,
    *,
    tenant_id: str,
    domain_id: str,
    project_id: str,
    lock_family: str,
    created_at: str,
    max_active_slots: int = 1,
    policy_version: str = DEFAULT_POLICY_VERSION,
    metadata_json: dict[str, Any] | None = None,
) -> dict[str, Any]:
    _validate_scope(connection, tenant_id=tenant_id, domain_id=domain_id, project_id=project_id)
    _validate_lock_family(lock_family)
    if max_active_slots != 1:
        raise ProjectRuntimeSlotError(
            code="project_runtime_slot_policy_invalid",
            details={"max_active_slots": max_active_slots, "supported_max_active_slots": 1},
        )
    _reject_raw_material(metadata_json or {}, path="metadata_json")
    existing = get_project_concurrency_policy(
        connection,
        tenant_id=tenant_id,
        domain_id=domain_id,
        project_id=project_id,
        lock_family=lock_family,
    )
    if existing is not None:
        return existing
    policy_id = f"project-concurrency-policy:{tenant_id}:{domain_id}:{project_id}:{lock_family}"
    connection.execute(
        """
        INSERT INTO capex_project_concurrency_policies (
            project_concurrency_policy_id,
            tenant_id,
            domain_id,
            project_id,
            lock_family,
            max_active_slots,
            state,
            policy_version,
            metadata_json,
            created_at,
            updated_at
        )
        VALUES (?, ?, ?, ?, ?, ?, 'active', ?, ?, ?, ?)
        """,
        (
            policy_id,
            tenant_id,
            domain_id,
            project_id,
            lock_family,
            max_active_slots,
            policy_version,
            json.dumps(metadata_json or {}, separators=(",", ":"), sort_keys=True),
            created_at,
            created_at,
        ),
    )
    created = get_project_concurrency_policy(
        connection,
        tenant_id=tenant_id,
        domain_id=domain_id,
        project_id=project_id,
        lock_family=lock_family,
    )
    if created is None:
        raise RuntimeError("project concurrency policy insert failed")
    return created


def get_project_concurrency_policy(
    connection: sqlite3.Connection,
    *,
    tenant_id: str,
    domain_id: str,
    project_id: str,
    lock_family: str,
) -> dict[str, Any] | None:
    row = connection.execute(
        f"""
        SELECT {POLICY_COLUMNS}
        FROM capex_project_concurrency_policies
        WHERE tenant_id = ?
          AND domain_id = ?
          AND project_id = ?
          AND lock_family = ?
        """,
        (tenant_id, domain_id, project_id, lock_family),
    ).fetchone()
    if row is None:
        return None
    return _decode_json_row(dict(row), json_fields={"metadata_json"})


def acquire_project_runtime_slot(
    connection: sqlite3.Connection,
    *,
    project_runtime_slot_id: str,
    tenant_id: str,
    domain_id: str,
    project_id: str,
    lock_family: str,
    slot_key: str,
    holder_ref: str,
    lease_token: str,
    acquired_at: str,
    expires_at: str | None,
    metadata_json: dict[str, Any] | None = None,
) -> dict[str, Any]:
    _validate_scope(connection, tenant_id=tenant_id, domain_id=domain_id, project_id=project_id)
    _validate_lock_family(lock_family)
    _validate_slot_key(lock_family=lock_family, slot_key=slot_key)
    _validate_ref(holder_ref, "holder_ref")
    _validate_ref(lease_token, "lease_token")
    _reject_raw_material(metadata_json or {}, path="metadata_json")
    policy = ensure_project_concurrency_policy(
        connection,
        tenant_id=tenant_id,
        domain_id=domain_id,
        project_id=project_id,
        lock_family=lock_family,
        created_at=acquired_at,
    )
    if policy["state"] != "active" or int(policy["max_active_slots"]) != 1:
        raise ProjectRuntimeSlotError(
            code="project_runtime_slot_policy_inactive",
            details={"project_id": project_id, "lock_family": lock_family},
        )
    active = get_active_project_runtime_slot(
        connection,
        tenant_id=tenant_id,
        domain_id=domain_id,
        project_id=project_id,
        lock_family=lock_family,
    )
    if active is not None:
        if _slot_expired(active, now_iso=acquired_at):
            _expire_project_runtime_slot(
                connection,
                project_runtime_slot_id=str(active["project_runtime_slot_id"]),
                expired_at=acquired_at,
            )
        elif (
            active["slot_key"] == slot_key
            and active["holder_ref"] == holder_ref
            and active["lease_token"] == lease_token
        ):
            return active
        else:
            raise ProjectRuntimeSlotError(
                code="project_runtime_slot_conflict",
                details={
                    "project_id": project_id,
                    "lock_family": lock_family,
                    "active_slot_key": active["slot_key"],
                    "requested_slot_key": slot_key,
                },
            )
    active_family_key = _active_family_key(
        tenant_id=tenant_id,
        domain_id=domain_id,
        project_id=project_id,
        lock_family=lock_family,
    )
    connection.execute(
        """
        INSERT INTO capex_project_runtime_slots (
            project_runtime_slot_id,
            tenant_id,
            domain_id,
            project_id,
            lock_family,
            slot_key,
            holder_ref,
            lease_token,
            state,
            active_family_key,
            acquired_at,
            expires_at,
            released_at,
            metadata_json,
            created_at,
            updated_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'active', ?, ?, ?, NULL, ?, ?, ?)
        """,
        (
            project_runtime_slot_id,
            tenant_id,
            domain_id,
            project_id,
            lock_family,
            slot_key,
            holder_ref,
            lease_token,
            active_family_key,
            acquired_at,
            expires_at,
            json.dumps(metadata_json or {}, separators=(",", ":"), sort_keys=True),
            acquired_at,
            acquired_at,
        ),
    )
    slot = get_project_runtime_slot(connection, project_runtime_slot_id)
    if slot is None:
        raise RuntimeError("project runtime slot insert failed")
    return slot


def release_project_runtime_slot(
    connection: sqlite3.Connection,
    *,
    project_runtime_slot_id: str,
    lease_token: str,
    released_at: str,
) -> dict[str, Any]:
    slot = get_project_runtime_slot(connection, project_runtime_slot_id)
    if slot is None:
        raise ProjectRuntimeSlotError(
            code="project_runtime_slot_not_found",
            details={"project_runtime_slot_id": project_runtime_slot_id},
        )
    if slot["state"] != "active" or slot["lease_token"] != lease_token:
        raise ProjectRuntimeSlotError(
            code="project_runtime_slot_stale_release",
            details={"project_runtime_slot_id": project_runtime_slot_id},
        )
    connection.execute(
        """
        UPDATE capex_project_runtime_slots
        SET state = 'released',
            active_family_key = NULL,
            released_at = ?,
            updated_at = ?
        WHERE project_runtime_slot_id = ?
          AND lease_token = ?
          AND state = 'active'
        """,
        (released_at, released_at, project_runtime_slot_id, lease_token),
    )
    released = get_project_runtime_slot(connection, project_runtime_slot_id)
    if released is None:
        raise RuntimeError("project runtime slot release failed")
    return released


def get_project_runtime_slot(
    connection: sqlite3.Connection,
    project_runtime_slot_id: str,
) -> dict[str, Any] | None:
    row = connection.execute(
        f"""
        SELECT {SLOT_COLUMNS}
        FROM capex_project_runtime_slots
        WHERE project_runtime_slot_id = ?
        """,
        (project_runtime_slot_id,),
    ).fetchone()
    if row is None:
        return None
    return _decode_json_row(dict(row), json_fields={"metadata_json"})


def get_active_project_runtime_slot(
    connection: sqlite3.Connection,
    *,
    tenant_id: str,
    domain_id: str,
    project_id: str,
    lock_family: str,
) -> dict[str, Any] | None:
    row = connection.execute(
        f"""
        SELECT {SLOT_COLUMNS}
        FROM capex_project_runtime_slots
        WHERE tenant_id = ?
          AND domain_id = ?
          AND project_id = ?
          AND lock_family = ?
          AND state = 'active'
          AND active_family_key IS NOT NULL
        ORDER BY acquired_at ASC, project_runtime_slot_id ASC
        LIMIT 1
        """,
        (tenant_id, domain_id, project_id, lock_family),
    ).fetchone()
    if row is None:
        return None
    return _decode_json_row(dict(row), json_fields={"metadata_json"})


def _expire_project_runtime_slot(
    connection: sqlite3.Connection,
    *,
    project_runtime_slot_id: str,
    expired_at: str,
) -> None:
    connection.execute(
        """
        UPDATE capex_project_runtime_slots
        SET state = 'expired',
            active_family_key = NULL,
            updated_at = ?
        WHERE project_runtime_slot_id = ?
          AND state = 'active'
        """,
        (expired_at, project_runtime_slot_id),
    )


def _slot_expired(slot: dict[str, Any], *, now_iso: str) -> bool:
    expires_at = slot.get("expires_at")
    if expires_at is None:
        return False
    return _parse_iso(str(expires_at)) <= _parse_iso(now_iso)


def _parse_iso(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(timezone.utc)


def _active_family_key(
    *,
    tenant_id: str,
    domain_id: str,
    project_id: str,
    lock_family: str,
) -> str:
    return f"{tenant_id}:{domain_id}:{project_id}:{lock_family}"


def _validate_scope(
    connection: sqlite3.Connection,
    *,
    tenant_id: str,
    domain_id: str,
    project_id: str,
) -> None:
    row = connection.execute(
        """
        SELECT project_id
        FROM capex_projects
        WHERE project_id = ?
          AND tenant_id = ?
          AND domain_id = ?
        """,
        (project_id, tenant_id, domain_id),
    ).fetchone()
    if row is None:
        raise ProjectRuntimeSlotError(
            code="project_runtime_slot_scope_invalid",
            details={"tenant_id": tenant_id, "domain_id": domain_id, "project_id": project_id},
        )


def _validate_lock_family(lock_family: str) -> None:
    if lock_family not in SUPPORTED_LOCK_FAMILIES:
        raise ProjectRuntimeSlotError(
            code="project_runtime_slot_family_unsupported",
            details={"lock_family": lock_family, "supported_lock_families": sorted(SUPPORTED_LOCK_FAMILIES)},
        )


def _validate_slot_key(*, lock_family: str, slot_key: str) -> None:
    if not slot_key.startswith(f"{lock_family}:") or _CANONICAL_REF_RE.fullmatch(slot_key) is None:
        raise ProjectRuntimeSlotError(
            code="project_runtime_slot_key_invalid",
            details={"lock_family": lock_family, "slot_key": slot_key},
        )


def _validate_ref(value: str, field: str) -> None:
    if not isinstance(value, str) or _CANONICAL_REF_RE.fullmatch(value) is None:
        raise ProjectRuntimeSlotError(
            code="project_runtime_slot_ref_invalid",
            details={"field": field, "value": value},
        )


def _reject_raw_material(value: Any, *, path: str) -> None:
    if isinstance(value, dict):
        for key, child in value.items():
            normalized_key = str(key).lower().replace("-", "_")
            if normalized_key in _FORBIDDEN_RAW_KEYS:
                raise ProjectRuntimeSlotError(
                    code="project_runtime_slot_raw_material",
                    details={"path": f"{path}.{key}", "field": str(key)},
                )
            _reject_raw_material(child, path=f"{path}.{key}")
        return
    if isinstance(value, (list, tuple)):
        for index, child in enumerate(value):
            _reject_raw_material(child, path=f"{path}[{index}]")
        return
    if isinstance(value, (bytes, bytearray, memoryview)):
        raise ProjectRuntimeSlotError(
            code="project_runtime_slot_raw_material",
            details={"path": path},
        )
    if isinstance(value, str) and (
        value.startswith(("/", "file://")) or "\\Users\\" in value or "/Users/" in value
    ):
        raise ProjectRuntimeSlotError(
            code="project_runtime_slot_raw_material",
            details={"path": path},
        )


def _decode_json_row(row: dict[str, Any], *, json_fields: set[str]) -> dict[str, Any]:
    for field in json_fields:
        if row.get(field) is not None:
            row[field] = json.loads(row[field])
    return row
