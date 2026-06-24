from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import re
import sqlite3
from typing import Any


SHA256_DIGEST_RE = re.compile(r"\Asha256:[0-9a-f]{64}\Z")
POINTER_FAMILY_RE = re.compile(r"\A[a-z][a-z0-9_.-]{1,127}\Z")
ACTOR_REF_RE = re.compile(r"\A[A-Za-z0-9][A-Za-z0-9_.:/#@-]{0,254}\Z")
EVENT_KINDS = {
    "promoted",
    "drift_detected",
    "promotion_rejected",
    "policy_registered",
}
REGISTRY_KINDS = {"singleton", "stream"}
POLICY_STATES = {"active", "inactive"}
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

POINTER_EVENT_COLUMNS = """
    artifact_pointer_event_id,
    tenant_id,
    domain_id,
    project_id,
    pointer_id,
    pointer_family,
    event_kind,
    from_generation,
    to_generation,
    artifact_version_id,
    previous_artifact_version_id,
    basis_digest,
    payload_digest,
    payload_json,
    metadata_json,
    recorded_at,
    recorded_by_actor_ref
"""

POINTER_FAMILY_POLICY_COLUMNS = """
    artifact_pointer_family_policy_id,
    tenant_id,
    domain_id,
    project_id,
    pointer_family,
    registry_kind,
    policy_version,
    basis_digest,
    policy_digest,
    policy_json,
    state,
    created_at,
    updated_at
"""


@dataclass(frozen=True)
class ArtifactPointerFoundationError(ValueError):
    code: str
    details: dict[str, Any]

    def __str__(self) -> str:
        return self.code


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
        raise ArtifactPointerFoundationError(
            code="artifact_pointer_payload_not_canonical_json",
            details={},
        ) from exc


def sha256_digest(value: Any) -> str:
    return f"sha256:{hashlib.sha256(canonical_json_bytes(value)).hexdigest()}"


def artifact_pointer_event_id(
    *,
    tenant_id: str,
    domain_id: str,
    project_id: str,
    pointer_id: str,
    pointer_family: str,
    event_kind: str,
    to_generation: int,
    payload_digest: str,
) -> str:
    digest = sha256_digest(
        {
            "tenant_id": tenant_id,
            "domain_id": domain_id,
            "project_id": project_id,
            "pointer_id": pointer_id,
            "pointer_family": pointer_family,
            "event_kind": event_kind,
            "to_generation": to_generation,
            "payload_digest": payload_digest,
        }
    ).removeprefix("sha256:")
    return f"artifact-pointer-event:{digest}"


def artifact_pointer_family_policy_id(
    *,
    tenant_id: str,
    domain_id: str,
    project_id: str,
    pointer_family: str,
) -> str:
    digest = sha256_digest(
        {
            "tenant_id": tenant_id,
            "domain_id": domain_id,
            "project_id": project_id,
            "pointer_family": pointer_family,
        }
    ).removeprefix("sha256:")
    return f"artifact-pointer-family-policy:{digest}"


def register_artifact_pointer_family_policy(
    connection: sqlite3.Connection,
    *,
    tenant_id: str,
    domain_id: str,
    project_id: str,
    pointer_family: str,
    registry_kind: str,
    policy_version: str,
    basis_digest: str,
    policy_json: dict[str, Any],
    created_at: str,
    state: str = "active",
) -> dict[str, Any]:
    _validate_scope(connection, tenant_id=tenant_id, domain_id=domain_id, project_id=project_id)
    normalized_family = _validate_pointer_family(pointer_family)
    normalized_registry_kind = _validate_registry_kind(registry_kind)
    normalized_state = _validate_policy_state(state)
    _validate_digest(basis_digest, field="basis_digest")
    _assert_json_object(policy_json, field="policy_json")
    _assert_no_raw_material(policy_json, path="policy_json")
    policy_digest = sha256_digest(policy_json)
    policy_id = artifact_pointer_family_policy_id(
        tenant_id=tenant_id,
        domain_id=domain_id,
        project_id=project_id,
        pointer_family=normalized_family,
    )
    existing = get_artifact_pointer_family_policy(
        connection,
        tenant_id=tenant_id,
        domain_id=domain_id,
        project_id=project_id,
        pointer_family=normalized_family,
    )
    if existing is not None:
        if _policy_matches(
            existing,
            registry_kind=normalized_registry_kind,
            policy_version=policy_version,
            basis_digest=basis_digest,
            policy_digest=policy_digest,
            policy_json=policy_json,
            state=normalized_state,
        ):
            return existing
        raise ArtifactPointerFoundationError(
            code="artifact_pointer_family_policy_conflict",
            details={"artifact_pointer_family_policy_id": existing["artifact_pointer_family_policy_id"]},
        )

    connection.execute(
        """
        INSERT INTO artifact_pointer_family_policies (
            artifact_pointer_family_policy_id,
            tenant_id,
            domain_id,
            project_id,
            pointer_family,
            registry_kind,
            policy_version,
            basis_digest,
            policy_digest,
            policy_json,
            state,
            created_at,
            updated_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            policy_id,
            tenant_id,
            domain_id,
            project_id,
            normalized_family,
            normalized_registry_kind,
            policy_version,
            basis_digest,
            policy_digest,
            json.dumps(policy_json, separators=(",", ":"), sort_keys=True),
            normalized_state,
            created_at,
            created_at,
        ),
    )
    created = get_artifact_pointer_family_policy_by_id(
        connection,
        artifact_pointer_family_policy_id=policy_id,
    )
    if created is None:
        raise RuntimeError("artifact pointer family policy not found after insert")
    return created


def get_artifact_pointer_family_policy(
    connection: sqlite3.Connection,
    *,
    tenant_id: str,
    domain_id: str,
    project_id: str,
    pointer_family: str,
) -> dict[str, Any] | None:
    row = connection.execute(
        f"""
        SELECT {POINTER_FAMILY_POLICY_COLUMNS}
        FROM artifact_pointer_family_policies
        WHERE tenant_id = ?
          AND domain_id = ?
          AND project_id = ?
          AND pointer_family = ?
        """,
        (tenant_id, domain_id, project_id, _validate_pointer_family(pointer_family)),
    ).fetchone()
    return _policy_from_row(row)


def get_artifact_pointer_family_policy_by_id(
    connection: sqlite3.Connection,
    *,
    artifact_pointer_family_policy_id: str,
) -> dict[str, Any] | None:
    row = connection.execute(
        f"""
        SELECT {POINTER_FAMILY_POLICY_COLUMNS}
        FROM artifact_pointer_family_policies
        WHERE artifact_pointer_family_policy_id = ?
        """,
        (artifact_pointer_family_policy_id,),
    ).fetchone()
    return _policy_from_row(row)


def record_artifact_pointer_event(
    connection: sqlite3.Connection,
    *,
    tenant_id: str,
    domain_id: str,
    project_id: str,
    pointer_id: str,
    pointer_family: str,
    event_kind: str,
    to_generation: int,
    basis_digest: str,
    payload_json: dict[str, Any],
    recorded_at: str,
    recorded_by_actor_ref: str,
    from_generation: int | None = None,
    artifact_version_id: str | None = None,
    previous_artifact_version_id: str | None = None,
    metadata_json: dict[str, Any] | None = None,
    artifact_pointer_event_id: str | None = None,
) -> dict[str, Any]:
    _validate_scope(connection, tenant_id=tenant_id, domain_id=domain_id, project_id=project_id)
    _validate_existing_pointer_scope(
        connection,
        tenant_id=tenant_id,
        domain_id=domain_id,
        project_id=project_id,
        pointer_id=pointer_id,
    )
    normalized_family = _validate_pointer_family(pointer_family)
    normalized_event_kind = _validate_event_kind(event_kind)
    _validate_generation(from_generation=from_generation, to_generation=to_generation)
    _validate_digest(basis_digest, field="basis_digest")
    if not ACTOR_REF_RE.match(str(recorded_by_actor_ref)):
        raise ArtifactPointerFoundationError(
            code="artifact_pointer_actor_ref_invalid",
            details={"recorded_by_actor_ref": recorded_by_actor_ref},
        )
    _assert_json_object(payload_json, field="payload_json")
    metadata = dict(metadata_json or {})
    _assert_json_object(metadata, field="metadata_json")
    _assert_no_raw_material(payload_json, path="payload_json")
    _assert_no_raw_material(metadata, path="metadata_json")
    _validate_artifact_scope(
        connection,
        tenant_id=tenant_id,
        domain_id=domain_id,
        project_id=project_id,
        artifact_version_id=artifact_version_id,
        field="artifact_version_id",
    )
    _validate_artifact_scope(
        connection,
        tenant_id=tenant_id,
        domain_id=domain_id,
        project_id=project_id,
        artifact_version_id=previous_artifact_version_id,
        field="previous_artifact_version_id",
    )
    payload_digest = sha256_digest(payload_json)
    event_id = (
        str(artifact_pointer_event_id).strip()
        if artifact_pointer_event_id
        else artifact_pointer_event_id_factory(
            tenant_id=tenant_id,
            domain_id=domain_id,
            project_id=project_id,
            pointer_id=pointer_id,
            pointer_family=normalized_family,
            event_kind=normalized_event_kind,
            to_generation=to_generation,
            payload_digest=payload_digest,
        )
    )
    existing = get_artifact_pointer_event_by_id(
        connection,
        artifact_pointer_event_id=event_id,
    )
    if existing is not None:
        if _event_matches(
            existing,
            tenant_id=tenant_id,
            domain_id=domain_id,
            project_id=project_id,
            pointer_id=pointer_id,
            pointer_family=normalized_family,
            event_kind=normalized_event_kind,
            from_generation=from_generation,
            to_generation=to_generation,
            artifact_version_id=artifact_version_id,
            previous_artifact_version_id=previous_artifact_version_id,
            basis_digest=basis_digest,
            payload_digest=payload_digest,
            payload_json=payload_json,
            metadata_json=metadata,
            recorded_at=recorded_at,
            recorded_by_actor_ref=recorded_by_actor_ref,
        ):
            return existing
        raise ArtifactPointerFoundationError(
            code="artifact_pointer_event_conflict",
            details={"artifact_pointer_event_id": event_id},
        )

    try:
        connection.execute(
            """
            INSERT INTO artifact_pointer_events (
                artifact_pointer_event_id,
                tenant_id,
                domain_id,
                project_id,
                pointer_id,
                pointer_family,
                event_kind,
                from_generation,
                to_generation,
                artifact_version_id,
                previous_artifact_version_id,
                basis_digest,
                payload_digest,
                payload_json,
                metadata_json,
                recorded_at,
                recorded_by_actor_ref
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                event_id,
                tenant_id,
                domain_id,
                project_id,
                pointer_id,
                normalized_family,
                normalized_event_kind,
                from_generation,
                to_generation,
                artifact_version_id,
                previous_artifact_version_id,
                basis_digest,
                payload_digest,
                json.dumps(payload_json, separators=(",", ":"), sort_keys=True),
                json.dumps(metadata, separators=(",", ":"), sort_keys=True),
                recorded_at,
                recorded_by_actor_ref,
            ),
        )
    except sqlite3.IntegrityError as exc:
        raise ArtifactPointerFoundationError(
            code="artifact_pointer_event_conflict",
            details={"pointer_id": pointer_id, "to_generation": to_generation},
        ) from exc
    created = get_artifact_pointer_event_by_id(
        connection,
        artifact_pointer_event_id=event_id,
    )
    if created is None:
        raise RuntimeError("artifact pointer event not found after insert")
    return created


def artifact_pointer_event_id_factory(
    *,
    tenant_id: str,
    domain_id: str,
    project_id: str,
    pointer_id: str,
    pointer_family: str,
    event_kind: str,
    to_generation: int,
    payload_digest: str,
) -> str:
    return artifact_pointer_event_id(
        tenant_id=tenant_id,
        domain_id=domain_id,
        project_id=project_id,
        pointer_id=pointer_id,
        pointer_family=pointer_family,
        event_kind=event_kind,
        to_generation=to_generation,
        payload_digest=payload_digest,
    )


def get_artifact_pointer_event_by_id(
    connection: sqlite3.Connection,
    *,
    artifact_pointer_event_id: str,
) -> dict[str, Any] | None:
    row = connection.execute(
        f"""
        SELECT {POINTER_EVENT_COLUMNS}
        FROM artifact_pointer_events
        WHERE artifact_pointer_event_id = ?
        """,
        (artifact_pointer_event_id,),
    ).fetchone()
    return _event_from_row(row)


def list_artifact_pointer_events(
    connection: sqlite3.Connection,
    *,
    tenant_id: str,
    domain_id: str,
    project_id: str,
    pointer_family: str | None = None,
) -> list[dict[str, Any]]:
    query = f"""
        SELECT {POINTER_EVENT_COLUMNS}
        FROM artifact_pointer_events
        WHERE tenant_id = ? AND domain_id = ? AND project_id = ?
    """
    params: list[Any] = [tenant_id, domain_id, project_id]
    if pointer_family is not None:
        query += " AND pointer_family = ?"
        params.append(_validate_pointer_family(pointer_family))
    query += " ORDER BY recorded_at ASC, pointer_id ASC, to_generation ASC"
    rows = connection.execute(query, params).fetchall()
    return [_event_from_row(row) for row in rows if row is not None]


def _validate_scope(
    connection: sqlite3.Connection,
    *,
    tenant_id: str,
    domain_id: str,
    project_id: str,
) -> None:
    row = connection.execute(
        """
        SELECT 1
        FROM capex_projects
        WHERE tenant_id = ? AND domain_id = ? AND project_id = ?
        """,
        (tenant_id, domain_id, project_id),
    ).fetchone()
    if row is None:
        raise ArtifactPointerFoundationError(
            code="artifact_pointer_scope_mismatch",
            details={"tenant_id": tenant_id, "domain_id": domain_id, "project_id": project_id},
        )


def _validate_existing_pointer_scope(
    connection: sqlite3.Connection,
    *,
    tenant_id: str,
    domain_id: str,
    project_id: str,
    pointer_id: str,
) -> None:
    row = connection.execute(
        """
        SELECT tenant_id, domain_id, scope_kind, scope_ref
        FROM artifact_pointers
        WHERE pointer_id = ?
        """,
        (pointer_id,),
    ).fetchone()
    if row is None:
        return
    if str(row["tenant_id"]) != tenant_id or str(row["domain_id"]) != domain_id:
        raise ArtifactPointerFoundationError(
            code="artifact_pointer_scope_mismatch",
            details={"pointer_id": pointer_id},
        )
    if str(row["scope_kind"]) == "capex_project" and str(row["scope_ref"]) != project_id:
        raise ArtifactPointerFoundationError(
            code="artifact_pointer_scope_mismatch",
            details={"pointer_id": pointer_id, "project_id": project_id},
        )


def _validate_artifact_scope(
    connection: sqlite3.Connection,
    *,
    tenant_id: str,
    domain_id: str,
    project_id: str,
    artifact_version_id: str | None,
    field: str,
) -> None:
    if artifact_version_id is None:
        return
    row = connection.execute(
        """
        SELECT tenant_id, domain_id, project_id
        FROM artifact_versions
        WHERE artifact_version_id = ?
        """,
        (artifact_version_id,),
    ).fetchone()
    if row is None:
        raise ArtifactPointerFoundationError(
            code="artifact_pointer_artifact_unknown",
            details={field: artifact_version_id},
        )
    if (
        str(row["tenant_id"]) != tenant_id
        or str(row["domain_id"]) != domain_id
        or str(row["project_id"]) != project_id
    ):
        raise ArtifactPointerFoundationError(
            code="artifact_pointer_scope_mismatch",
            details={field: artifact_version_id},
        )


def _validate_pointer_family(pointer_family: str) -> str:
    normalized = str(pointer_family).strip()
    if not POINTER_FAMILY_RE.match(normalized):
        raise ArtifactPointerFoundationError(
            code="artifact_pointer_family_invalid",
            details={"pointer_family": pointer_family},
        )
    return normalized


def _validate_event_kind(event_kind: str) -> str:
    normalized = str(event_kind).strip()
    if normalized not in EVENT_KINDS:
        raise ArtifactPointerFoundationError(
            code="artifact_pointer_event_kind_invalid",
            details={"event_kind": event_kind},
        )
    return normalized


def _validate_registry_kind(registry_kind: str) -> str:
    normalized = str(registry_kind).strip()
    if normalized not in REGISTRY_KINDS:
        raise ArtifactPointerFoundationError(
            code="artifact_pointer_registry_kind_invalid",
            details={"registry_kind": registry_kind},
        )
    return normalized


def _validate_policy_state(state: str) -> str:
    normalized = str(state).strip()
    if normalized not in POLICY_STATES:
        raise ArtifactPointerFoundationError(
            code="artifact_pointer_family_policy_state_invalid",
            details={"state": state},
        )
    return normalized


def _validate_digest(value: str, *, field: str) -> None:
    if not SHA256_DIGEST_RE.match(str(value)):
        raise ArtifactPointerFoundationError(
            code="artifact_pointer_digest_invalid",
            details={"field": field, "value": value},
        )


def _validate_generation(*, from_generation: int | None, to_generation: int) -> None:
    if to_generation < 0 or (from_generation is not None and from_generation < 0):
        raise ArtifactPointerFoundationError(
            code="artifact_pointer_generation_invalid",
            details={"from_generation": from_generation, "to_generation": to_generation},
        )
    if from_generation is not None and to_generation <= from_generation:
        raise ArtifactPointerFoundationError(
            code="artifact_pointer_generation_mismatch",
            details={"from_generation": from_generation, "to_generation": to_generation},
        )
    if from_generation is None and to_generation != 0:
        raise ArtifactPointerFoundationError(
            code="artifact_pointer_generation_mismatch",
            details={"from_generation": from_generation, "to_generation": to_generation},
        )


def _assert_json_object(value: Any, *, field: str) -> None:
    if not isinstance(value, dict):
        raise ArtifactPointerFoundationError(
            code="artifact_pointer_payload_invalid",
            details={"field": field},
        )
    canonical_json_bytes(value)


def _assert_no_raw_material(value: Any, *, path: str) -> None:
    if isinstance(value, dict):
        for key, child in value.items():
            normalized_key = str(key).lower().replace("-", "_")
            if normalized_key in RAW_MATERIAL_KEY_MARKERS:
                raise ArtifactPointerFoundationError(
                    code="artifact_pointer_raw_material",
                    details={"path": f"{path}.{key}", "field": str(key)},
                )
            _assert_no_raw_material(child, path=f"{path}.{key}")
        return
    if isinstance(value, (list, tuple)):
        for index, child in enumerate(value):
            _assert_no_raw_material(child, path=f"{path}[{index}]")
        return
    if isinstance(value, (bytes, bytearray, memoryview)):
        raise ArtifactPointerFoundationError(
            code="artifact_pointer_raw_material",
            details={"path": path},
        )
    if isinstance(value, str):
        if value.startswith(("/", "file://")) or "\\Users\\" in value or ":\\Users\\" in value:
            raise ArtifactPointerFoundationError(
                code="artifact_pointer_raw_material",
                details={"path": path},
            )


def _policy_from_row(row: sqlite3.Row | None) -> dict[str, Any] | None:
    if row is None:
        return None
    item = dict(row)
    item["policy_json"] = json.loads(item["policy_json"])
    return item


def _event_from_row(row: sqlite3.Row | None) -> dict[str, Any] | None:
    if row is None:
        return None
    item = dict(row)
    item["payload_json"] = json.loads(item["payload_json"])
    item["metadata_json"] = json.loads(item["metadata_json"])
    return item


def _policy_matches(
    existing: dict[str, Any],
    *,
    registry_kind: str,
    policy_version: str,
    basis_digest: str,
    policy_digest: str,
    policy_json: dict[str, Any],
    state: str,
) -> bool:
    return (
        str(existing["registry_kind"]) == registry_kind
        and str(existing["policy_version"]) == policy_version
        and str(existing["basis_digest"]) == basis_digest
        and str(existing["policy_digest"]) == policy_digest
        and existing["policy_json"] == policy_json
        and str(existing["state"]) == state
    )


def _event_matches(
    existing: dict[str, Any],
    *,
    tenant_id: str,
    domain_id: str,
    project_id: str,
    pointer_id: str,
    pointer_family: str,
    event_kind: str,
    from_generation: int | None,
    to_generation: int,
    artifact_version_id: str | None,
    previous_artifact_version_id: str | None,
    basis_digest: str,
    payload_digest: str,
    payload_json: dict[str, Any],
    metadata_json: dict[str, Any],
    recorded_at: str,
    recorded_by_actor_ref: str,
) -> bool:
    return (
        str(existing["tenant_id"]) == tenant_id
        and str(existing["domain_id"]) == domain_id
        and str(existing["project_id"]) == project_id
        and str(existing["pointer_id"]) == pointer_id
        and str(existing["pointer_family"]) == pointer_family
        and str(existing["event_kind"]) == event_kind
        and existing["from_generation"] == from_generation
        and int(existing["to_generation"]) == to_generation
        and existing["artifact_version_id"] == artifact_version_id
        and existing["previous_artifact_version_id"] == previous_artifact_version_id
        and str(existing["basis_digest"]) == basis_digest
        and str(existing["payload_digest"]) == payload_digest
        and existing["payload_json"] == payload_json
        and existing["metadata_json"] == metadata_json
        and str(existing["recorded_at"]) == recorded_at
        and str(existing["recorded_by_actor_ref"]) == recorded_by_actor_ref
    )
