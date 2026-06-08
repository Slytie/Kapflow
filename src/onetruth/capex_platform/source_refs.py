from __future__ import annotations

from dataclasses import dataclass
import sqlite3
from typing import Any

from onetruth.infrastructure.repositories.capex_source_occurrences import (
    RESOLVABLE_SOURCE_OCCURRENCE_STATUSES,
    get_source_occurrence_with_content_identity,
    parse_source_occurrence_ref,
)


@dataclass(frozen=True)
class SourceRefResolution:
    source_ref: str
    resolved: bool
    denial_reason: str | None
    source_occurrence_id: str | None = None
    tenant_id: str | None = None
    domain_id: str | None = None
    project_id: str | None = None
    occurrence_status: str | None = None
    content_identity_id: str | None = None
    content_digest_algorithm: str | None = None
    content_digest: str | None = None
    content_byte_size: int | None = None
    content_media_type: str | None = None
    content_canonicalization_profile: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "source_ref": self.source_ref,
            "resolved": self.resolved,
            "denial_reason": self.denial_reason,
            "source_occurrence_id": self.source_occurrence_id,
            "tenant_id": self.tenant_id,
            "domain_id": self.domain_id,
            "project_id": self.project_id,
            "occurrence_status": self.occurrence_status,
            "content_identity": (
                {
                    "content_identity_id": self.content_identity_id,
                    "digest_algorithm": self.content_digest_algorithm,
                    "content_digest": self.content_digest,
                    "byte_size": self.content_byte_size,
                    "media_type": self.content_media_type,
                    "canonicalization_profile": self.content_canonicalization_profile,
                }
                if self.content_identity_id is not None
                else None
            ),
        }


class SourceRefResolutionError(ValueError):
    def __init__(
        self,
        message: str,
        *,
        resolutions: tuple[SourceRefResolution, ...] = (),
    ) -> None:
        super().__init__(message)
        self.resolutions = resolutions


def resolve_source_ref(
    connection: sqlite3.Connection,
    source_ref: str,
    *,
    tenant_id: str,
    domain_id: str,
    project_id: str | None,
) -> SourceRefResolution:
    source_occurrence_id = parse_source_occurrence_ref(source_ref)
    if source_occurrence_id is None:
        return SourceRefResolution(
            source_ref=source_ref,
            resolved=False,
            denial_reason="malformed_source_ref",
        )

    row = get_source_occurrence_with_content_identity(connection, source_ref)
    if row is None:
        return SourceRefResolution(
            source_ref=source_ref,
            resolved=False,
            denial_reason="source_occurrence_not_found",
            source_occurrence_id=source_occurrence_id,
        )

    row_tenant_id = str(row["tenant_id"])
    row_domain_id = str(row["domain_id"])
    row_project_id = row["project_id"] if row["project_id"] is not None else None
    if row_tenant_id != tenant_id or row_domain_id != domain_id or row_project_id != project_id:
        return _resolution_from_row(
            row,
            resolved=False,
            denial_reason="source_occurrence_scope_mismatch",
        )

    occurrence_status = str(row["status"])
    if occurrence_status not in RESOLVABLE_SOURCE_OCCURRENCE_STATUSES:
        return _resolution_from_row(
            row,
            resolved=False,
            denial_reason=f"source_occurrence_status_not_resolvable:{occurrence_status}",
        )

    return _resolution_from_row(row, resolved=True, denial_reason=None)


def require_meaningful_source_refs(
    connection: sqlite3.Connection,
    source_refs: list[str] | tuple[str, ...],
    *,
    tenant_id: str,
    domain_id: str,
    project_id: str | None,
) -> tuple[SourceRefResolution, ...]:
    if not source_refs:
        raise SourceRefResolutionError("source_refs must not be empty")
    resolutions = tuple(
        resolve_source_ref(
            connection,
            source_ref,
            tenant_id=tenant_id,
            domain_id=domain_id,
            project_id=project_id,
        )
        for source_ref in source_refs
    )
    unresolved = [resolution for resolution in resolutions if not resolution.resolved]
    if unresolved:
        reasons = ", ".join(
            f"{resolution.source_ref}:{resolution.denial_reason}"
            for resolution in unresolved
        )
        raise SourceRefResolutionError(
            f"source_refs are not meaningful: {reasons}",
            resolutions=resolutions,
        )
    return resolutions


def _resolution_from_row(
    row: dict[str, Any],
    *,
    resolved: bool,
    denial_reason: str | None,
) -> SourceRefResolution:
    return SourceRefResolution(
        source_ref=str(row["source_ref"]),
        resolved=resolved,
        denial_reason=denial_reason,
        source_occurrence_id=str(row["source_occurrence_id"]),
        tenant_id=str(row["tenant_id"]),
        domain_id=str(row["domain_id"]),
        project_id=row["project_id"] if row["project_id"] is not None else None,
        occurrence_status=str(row["status"]),
        content_identity_id=str(row["content_identity_id"]),
        content_digest_algorithm=str(row["content_digest_algorithm"]),
        content_digest=str(row["content_digest"]),
        content_byte_size=(
            int(row["content_byte_size"])
            if row["content_byte_size"] is not None
            else None
        ),
        content_media_type=(
            str(row["content_media_type"])
            if row["content_media_type"] is not None
            else None
        ),
        content_canonicalization_profile=(
            str(row["content_canonicalization_profile"])
            if row["content_canonicalization_profile"] is not None
            else None
        ),
    )


__all__ = [
    "SourceRefResolution",
    "SourceRefResolutionError",
    "require_meaningful_source_refs",
    "resolve_source_ref",
]
