from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import re
import sqlite3
from typing import Any


SHA256_DIGEST_RE = re.compile(r"\Asha256:[0-9a-f]{64}\Z")
EFFECT_REF_RE = re.compile(r"\A[A-Za-z0-9][A-Za-z0-9_.:/#@-]{0,254}\Z")
EFFECT_NAME_RE = re.compile(r"\A[a-z][a-z0-9_.-]{1,63}\Z")
EFFECT_STATUSES = {"planned", "applied"}
RAW_MATERIAL_KEY_MARKERS = {
    "absolute_path",
    "base64",
    "blob",
    "blob_bytes",
    "bytes",
    "content_base64",
    "excerpt",
    "file_name",
    "filename",
    "local_path",
    "log",
    "ocr_text",
    "raw_content",
    "raw_filename",
    "raw_log",
    "raw_material",
    "raw_text",
    "source_path",
}


@dataclass
class EffectLedgerError(ValueError):
    code: str
    message: str
    details: dict[str, Any]


def canonical_json_bytes(value: Any) -> bytes:
    try:
        return json.dumps(
            value,
            separators=(",", ":"),
            sort_keys=True,
            ensure_ascii=True,
            allow_nan=False,
        ).encode("utf-8")
    except (TypeError, ValueError) as exc:
        raise EffectLedgerError(
            code="effect_payload_not_canonical_json",
            message="effect payload must be canonical JSON",
            details={},
        ) from exc


def sha256_digest(value: Any) -> str:
    return f"sha256:{hashlib.sha256(canonical_json_bytes(value)).hexdigest()}"


def effect_ledger_entry_id(
    *,
    command_name: str,
    scope_key: str,
    idempotency_key: str,
    effect_key: str,
) -> str:
    digest = sha256_digest(
        {
            "command_name": command_name,
            "scope_key": scope_key,
            "idempotency_key": idempotency_key,
            "effect_key": effect_key,
        }
    ).removeprefix("sha256:")
    return f"effect-ledger:{digest}"


def _assert_no_raw_material(value: Any, *, path: str = "$") -> None:
    if isinstance(value, dict):
        for key, child in value.items():
            normalized_key = str(key).lower().replace("-", "_")
            if normalized_key in RAW_MATERIAL_KEY_MARKERS:
                raise EffectLedgerError(
                    code="effect_ledger_raw_material",
                    message="effect ledger payloads must not contain raw material fields",
                    details={"path": f"{path}.{key}", "field": str(key)},
                )
            _assert_no_raw_material(child, path=f"{path}.{key}")
        return
    if isinstance(value, (list, tuple)):
        for index, child in enumerate(value):
            _assert_no_raw_material(child, path=f"{path}[{index}]")
        return
    if isinstance(value, (bytes, bytearray, memoryview)):
        raise EffectLedgerError(
            code="effect_ledger_raw_material",
            message="effect ledger payloads must not contain blob bytes",
            details={"path": path},
        )
    if isinstance(value, str):
        if value.startswith(("/", "file://")) or "\\Users\\" in value or ":\\Users\\" in value:
            raise EffectLedgerError(
                code="effect_ledger_raw_material",
                message="effect ledger payloads must not contain local paths",
                details={"path": path},
            )


def validate_effect_entry_fields(
    *,
    tenant_id: str | None,
    domain_id: str | None,
    command_name: str,
    scope_key: str,
    idempotency_key: str,
    request_fingerprint: str,
    request_fingerprint_profile: str,
    effect_key: str,
    effect_kind: str,
    target_kind: str,
    target_ref: str,
    payload_hash: str,
    payload_json: dict[str, Any],
    metadata_json: dict[str, Any],
    status: str,
) -> None:
    if not tenant_id or not domain_id:
        raise EffectLedgerError(
            code="effect_ledger_scope_required",
            message="effect ledger entries require tenant and domain scope",
            details={"tenant_id": tenant_id, "domain_id": domain_id},
        )
    for field_name, value in {
        "command_name": command_name,
        "scope_key": scope_key,
        "idempotency_key": idempotency_key,
        "request_fingerprint_profile": request_fingerprint_profile,
        "effect_key": effect_key,
        "effect_kind": effect_kind,
        "target_kind": target_kind,
        "target_ref": target_ref,
    }.items():
        if not isinstance(value, str) or not value.strip():
            raise EffectLedgerError(
                code="effect_ledger_invalid_field",
                message=f"{field_name} must be a non-empty string",
                details={"field": field_name},
            )
    if EFFECT_NAME_RE.fullmatch(effect_kind) is None:
        raise EffectLedgerError(
            code="effect_ledger_invalid_effect_kind",
            message="effect_kind is not canonical",
            details={"effect_kind": effect_kind},
        )
    if EFFECT_NAME_RE.fullmatch(target_kind) is None or EFFECT_REF_RE.fullmatch(target_ref) is None:
        raise EffectLedgerError(
            code="effect_ledger_invalid_target_ref",
            message="effect target must use a canonical reference",
            details={"target_kind": target_kind, "target_ref": target_ref},
        )
    if SHA256_DIGEST_RE.fullmatch(request_fingerprint) is None:
        raise EffectLedgerError(
            code="effect_ledger_bad_digest",
            message="request_fingerprint must be a sha256 digest",
            details={"field": "request_fingerprint"},
        )
    if SHA256_DIGEST_RE.fullmatch(payload_hash) is None:
        raise EffectLedgerError(
            code="effect_ledger_bad_digest",
            message="payload_hash must be a sha256 digest",
            details={"field": "payload_hash"},
        )
    if status not in EFFECT_STATUSES:
        raise EffectLedgerError(
            code="effect_ledger_invalid_status",
            message="effect ledger status is invalid",
            details={"status": status, "allowed_statuses": sorted(EFFECT_STATUSES)},
        )
    _assert_no_raw_material(payload_json)
    _assert_no_raw_material(metadata_json)


def get_effect_ledger_entry(
    connection: sqlite3.Connection,
    *,
    command_name: str,
    scope_key: str,
    idempotency_key: str,
    effect_key: str,
) -> dict[str, Any] | None:
    row = connection.execute(
        """
        SELECT
            effect_ledger_entry_id,
            tenant_id,
            domain_id,
            workflow_run_id,
            command_name,
            scope_key,
            idempotency_key,
            request_fingerprint,
            request_fingerprint_profile,
            effect_key,
            effect_kind,
            target_kind,
            target_ref,
            payload_hash,
            payload_json,
            status,
            result_json,
            metadata_json,
            created_at,
            applied_at
        FROM effect_ledger_entries
        WHERE command_name = ?
          AND scope_key = ?
          AND idempotency_key = ?
          AND effect_key = ?
        """,
        (command_name, scope_key, idempotency_key, effect_key),
    ).fetchone()
    if row is None:
        return None
    return {
        "effect_ledger_entry_id": row["effect_ledger_entry_id"],
        "tenant_id": row["tenant_id"],
        "domain_id": row["domain_id"],
        "workflow_run_id": row["workflow_run_id"],
        "command_name": row["command_name"],
        "scope_key": row["scope_key"],
        "idempotency_key": row["idempotency_key"],
        "request_fingerprint": row["request_fingerprint"],
        "request_fingerprint_profile": row["request_fingerprint_profile"],
        "effect_key": row["effect_key"],
        "effect_kind": row["effect_kind"],
        "target_kind": row["target_kind"],
        "target_ref": row["target_ref"],
        "payload_hash": row["payload_hash"],
        "payload_json": json.loads(row["payload_json"]),
        "status": row["status"],
        "result_json": None if row["result_json"] is None else json.loads(row["result_json"]),
        "metadata_json": json.loads(row["metadata_json"]),
        "created_at": row["created_at"],
        "applied_at": row["applied_at"],
    }


def create_effect_ledger_entry(
    connection: sqlite3.Connection,
    *,
    tenant_id: str | None,
    domain_id: str | None,
    workflow_run_id: str | None,
    command_name: str,
    scope_key: str,
    idempotency_key: str,
    request_fingerprint: str,
    request_fingerprint_profile: str,
    effect_key: str,
    effect_kind: str,
    target_kind: str,
    target_ref: str,
    payload_json: dict[str, Any],
    metadata_json: dict[str, Any] | None = None,
    created_at: str | None = None,
) -> dict[str, Any]:
    metadata = dict(metadata_json or {})
    payload_hash = sha256_digest(payload_json)
    validate_effect_entry_fields(
        tenant_id=tenant_id,
        domain_id=domain_id,
        command_name=command_name,
        scope_key=scope_key,
        idempotency_key=idempotency_key,
        request_fingerprint=request_fingerprint,
        request_fingerprint_profile=request_fingerprint_profile,
        effect_key=effect_key,
        effect_kind=effect_kind,
        target_kind=target_kind,
        target_ref=target_ref,
        payload_hash=payload_hash,
        payload_json=payload_json,
        metadata_json=metadata,
        status="planned",
    )
    entry_id = effect_ledger_entry_id(
        command_name=command_name,
        scope_key=scope_key,
        idempotency_key=idempotency_key,
        effect_key=effect_key,
    )
    connection.execute(
        """
        INSERT INTO effect_ledger_entries (
            effect_ledger_entry_id,
            tenant_id,
            domain_id,
            workflow_run_id,
            command_name,
            scope_key,
            idempotency_key,
            request_fingerprint,
            request_fingerprint_profile,
            effect_key,
            effect_kind,
            target_kind,
            target_ref,
            payload_hash,
            payload_json,
            status,
            result_json,
            metadata_json,
            created_at,
            applied_at
        )
        VALUES (
            ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'planned', NULL, ?,
            COALESCE(?, datetime('now')), NULL
        )
        """,
        (
            entry_id,
            tenant_id,
            domain_id,
            workflow_run_id,
            command_name,
            scope_key,
            idempotency_key,
            request_fingerprint,
            request_fingerprint_profile,
            effect_key,
            effect_kind,
            target_kind,
            target_ref,
            payload_hash,
            json.dumps(payload_json, separators=(",", ":"), sort_keys=True),
            json.dumps(metadata, separators=(",", ":"), sort_keys=True),
            created_at,
        ),
    )
    return get_effect_ledger_entry(
        connection,
        command_name=command_name,
        scope_key=scope_key,
        idempotency_key=idempotency_key,
        effect_key=effect_key,
    ) or {}


def mark_effect_ledger_entry_applied(
    connection: sqlite3.Connection,
    *,
    command_name: str,
    scope_key: str,
    idempotency_key: str,
    effect_key: str,
    result_json: dict[str, Any],
    applied_at: str | None = None,
) -> None:
    _assert_no_raw_material(result_json)
    connection.execute(
        """
        UPDATE effect_ledger_entries
        SET status = 'applied',
            result_json = ?,
            applied_at = COALESCE(?, datetime('now'))
        WHERE command_name = ?
          AND scope_key = ?
          AND idempotency_key = ?
          AND effect_key = ?
        """,
        (
            json.dumps(result_json, separators=(",", ":"), sort_keys=True),
            applied_at,
            command_name,
            scope_key,
            idempotency_key,
            effect_key,
        ),
    )
