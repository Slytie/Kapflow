from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import base64
import binascii
import hashlib
import hmac
import json
import sqlite3
from typing import Any, Callable

from onetruth.infrastructure.repositories.capex_workpage_projections import get_projection_snapshot


CURSOR_SCHEMA_VERSION = "capex.workpage_projection_cursor.v1"


@dataclass(frozen=True)
class ProjectionCursor:
    schema_version: str
    projection_snapshot_id: str
    tenant_id: str
    domain_id: str
    project_id: str
    basis_hash: str
    issued_at: str
    expires_at: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "projection_snapshot_id": self.projection_snapshot_id,
            "tenant_id": self.tenant_id,
            "domain_id": self.domain_id,
            "project_id": self.project_id,
            "basis_hash": self.basis_hash,
            "issued_at": self.issued_at,
            "expires_at": self.expires_at,
        }


@dataclass(frozen=True)
class WorkpageCommandEnvelope:
    tenant_id: str
    domain_id: str
    project_id: str
    workpage_kind: str
    command_type: str
    actor_id: str
    actor_type: str
    idempotency_key: str
    projection_snapshot_id: str
    signed_cursor: str
    expected_basis_hash: str
    payload: dict[str, Any]


class WorkpageCommandEnvelopeError(ValueError):
    def __init__(self, code: str, details: dict[str, Any] | None = None) -> None:
        super().__init__(code)
        self.code = code
        self.details = details or {}


def sign_projection_cursor(
    *,
    projection_snapshot_id: str,
    tenant_id: str,
    domain_id: str,
    project_id: str,
    basis_hash: str,
    issued_at: str,
    expires_at: str,
    signing_key: str,
) -> str:
    _require_signing_key(signing_key)
    cursor = ProjectionCursor(
        schema_version=CURSOR_SCHEMA_VERSION,
        projection_snapshot_id=projection_snapshot_id,
        tenant_id=tenant_id,
        domain_id=domain_id,
        project_id=project_id,
        basis_hash=basis_hash,
        issued_at=issued_at,
        expires_at=expires_at,
    )
    payload = _canonical_json(cursor.to_dict()).encode("utf-8")
    signature = hmac.new(signing_key.encode("utf-8"), payload, hashlib.sha256).digest()
    return ".".join(
        (
            "capexpc_v1",
            _base64url(payload),
            _base64url(signature),
        )
    )


def verify_projection_cursor(
    token: str,
    *,
    signing_key: str,
    now_iso: str,
) -> ProjectionCursor:
    _require_signing_key(signing_key)
    parts = token.split(".")
    if len(parts) != 3 or parts[0] != "capexpc_v1":
        raise WorkpageCommandEnvelopeError("invalid_projection_cursor")
    try:
        payload_bytes = _unbase64url(parts[1])
        supplied_signature = _unbase64url(parts[2])
    except (ValueError, binascii.Error) as exc:
        raise WorkpageCommandEnvelopeError("invalid_projection_cursor") from exc

    expected_signature = hmac.new(
        signing_key.encode("utf-8"),
        payload_bytes,
        hashlib.sha256,
    ).digest()
    if not hmac.compare_digest(supplied_signature, expected_signature):
        raise WorkpageCommandEnvelopeError("invalid_projection_cursor_signature")

    try:
        payload = json.loads(payload_bytes.decode("utf-8"))
        cursor = ProjectionCursor(
            schema_version=str(payload["schema_version"]),
            projection_snapshot_id=str(payload["projection_snapshot_id"]),
            tenant_id=str(payload["tenant_id"]),
            domain_id=str(payload["domain_id"]),
            project_id=str(payload["project_id"]),
            basis_hash=str(payload["basis_hash"]),
            issued_at=str(payload["issued_at"]),
            expires_at=str(payload["expires_at"]),
        )
    except (KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
        raise WorkpageCommandEnvelopeError("invalid_projection_cursor") from exc

    if cursor.schema_version != CURSOR_SCHEMA_VERSION:
        raise WorkpageCommandEnvelopeError("invalid_projection_cursor")
    if _parse_iso(now_iso) > _parse_iso(cursor.expires_at):
        raise WorkpageCommandEnvelopeError("expired_projection_cursor")
    return cursor


def validate_workpage_command_envelope(
    connection: sqlite3.Connection,
    envelope: WorkpageCommandEnvelope,
    *,
    signing_key: str,
    now_iso: str,
) -> dict[str, Any]:
    _require_envelope(envelope)
    cursor = verify_projection_cursor(
        envelope.signed_cursor,
        signing_key=signing_key,
        now_iso=now_iso,
    )
    if (
        cursor.projection_snapshot_id != envelope.projection_snapshot_id
        or cursor.tenant_id != envelope.tenant_id
        or cursor.domain_id != envelope.domain_id
        or cursor.project_id != envelope.project_id
    ):
        raise WorkpageCommandEnvelopeError("projection_cursor_scope_mismatch")

    snapshot = get_projection_snapshot(connection, envelope.projection_snapshot_id)
    if snapshot is None:
        raise WorkpageCommandEnvelopeError("projection_snapshot_not_found")
    if (
        str(snapshot["tenant_id"]) != envelope.tenant_id
        or str(snapshot["domain_id"]) != envelope.domain_id
        or str(snapshot["project_id"]) != envelope.project_id
        or str(snapshot["workpage_kind"]) != envelope.workpage_kind
    ):
        raise WorkpageCommandEnvelopeError("projection_snapshot_scope_mismatch")
    if str(snapshot["state"]) != "current":
        raise WorkpageCommandEnvelopeError(
            "stale_projection_snapshot",
            {"state": str(snapshot["state"])},
        )
    snapshot_basis_hash = str(snapshot["basis_hash"])
    if (
        cursor.basis_hash != snapshot_basis_hash
        or envelope.expected_basis_hash != snapshot_basis_hash
    ):
        raise WorkpageCommandEnvelopeError(
            "stale_projection_basis",
            {
                "cursor_basis_hash": cursor.basis_hash,
                "expected_basis_hash": envelope.expected_basis_hash,
                "snapshot_basis_hash": snapshot_basis_hash,
            },
        )
    return snapshot


def execute_guarded_workpage_command(
    connection: sqlite3.Connection,
    envelope: WorkpageCommandEnvelope,
    *,
    signing_key: str,
    now_iso: str,
    operation: Callable[[dict[str, Any]], dict[str, Any]],
) -> dict[str, Any]:
    snapshot = validate_workpage_command_envelope(
        connection,
        envelope,
        signing_key=signing_key,
        now_iso=now_iso,
    )
    return operation(snapshot)


def _require_envelope(envelope: WorkpageCommandEnvelope) -> None:
    required_values = {
        "tenant_id": envelope.tenant_id,
        "domain_id": envelope.domain_id,
        "project_id": envelope.project_id,
        "workpage_kind": envelope.workpage_kind,
        "command_type": envelope.command_type,
        "actor_id": envelope.actor_id,
        "actor_type": envelope.actor_type,
        "idempotency_key": envelope.idempotency_key,
        "projection_snapshot_id": envelope.projection_snapshot_id,
        "signed_cursor": envelope.signed_cursor,
        "expected_basis_hash": envelope.expected_basis_hash,
    }
    missing = [key for key, value in required_values.items() if not str(value or "").strip()]
    if missing:
        raise WorkpageCommandEnvelopeError(
            "malformed_workpage_command_envelope",
            {"missing": missing},
        )


def _require_signing_key(signing_key: str) -> None:
    if not str(signing_key or "").strip():
        raise WorkpageCommandEnvelopeError("missing_projection_cursor_signing_key")


def _canonical_json(value: Any) -> str:
    return json.dumps(value, separators=(",", ":"), sort_keys=True, ensure_ascii=True)


def _base64url(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")


def _unbase64url(value: str) -> bytes:
    padding = "=" * (-len(value) % 4)
    return base64.urlsafe_b64decode((value + padding).encode("ascii"))


def _parse_iso(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(timezone.utc)


__all__ = [
    "CURSOR_SCHEMA_VERSION",
    "ProjectionCursor",
    "WorkpageCommandEnvelope",
    "WorkpageCommandEnvelopeError",
    "execute_guarded_workpage_command",
    "sign_projection_cursor",
    "validate_workpage_command_envelope",
    "verify_projection_cursor",
]
