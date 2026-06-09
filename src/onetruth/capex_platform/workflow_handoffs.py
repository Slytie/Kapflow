from __future__ import annotations

from dataclasses import dataclass
import sqlite3
from typing import Any, Mapping

from onetruth.capex_platform.source_refs import SourceRefResolutionError, require_meaningful_source_refs
from onetruth.infrastructure.repositories.artifact_pointers import get_pointer_by_id
from onetruth.infrastructure.repositories.artifact_versions import get_artifact_version
from onetruth.infrastructure.repositories.capex_closure_governance import (
    get_closure_gate_evaluation,
    get_closure_snapshot,
)
from onetruth.infrastructure.repositories.workflow_runs import get_workflow_run


@dataclass(frozen=True)
class HandoffManifest:
    manifest_id: str
    schema_version: str
    tenant_id: str
    domain_id: str
    project_id: str | None
    source_workflow_run_id: str
    target_workflow_id: str
    target_workflow_version: str
    target_partition_key: str
    artifact_versions: tuple[dict[str, Any], ...]
    pointers: tuple[dict[str, Any], ...]
    source_refs: tuple[str, ...]
    validation_summaries: tuple[dict[str, Any], ...]
    closure_gate_evaluation_ids: tuple[str, ...]
    closure_snapshot_ids: tuple[str, ...]
    task_handoff_bindings: tuple[dict[str, Any], ...]
    workpage_handoff_bindings: tuple[dict[str, Any], ...]
    basis_version_vector_json: dict[str, Any]
    metadata_json: dict[str, Any]

    @classmethod
    def from_dict(cls, raw: Mapping[str, Any]) -> HandoffManifest:
        return cls(
            manifest_id=str(raw["manifest_id"]),
            schema_version=str(raw["schema_version"]),
            tenant_id=str(raw["tenant_id"]),
            domain_id=str(raw["domain_id"]),
            project_id=raw["project_id"] if raw.get("project_id") is not None else None,
            source_workflow_run_id=str(raw["source_workflow_run_id"]),
            target_workflow_id=str(raw["target_workflow_id"]),
            target_workflow_version=str(raw["target_workflow_version"]),
            target_partition_key=str(raw["target_partition_key"]),
            artifact_versions=tuple(dict(item) for item in raw.get("artifact_versions", ())),
            pointers=tuple(dict(item) for item in raw.get("pointers", ())),
            source_refs=tuple(str(item) for item in raw.get("source_refs", ())),
            validation_summaries=tuple(dict(item) for item in raw.get("validation_summaries", ())),
            closure_gate_evaluation_ids=tuple(
                str(item) for item in raw.get("closure_gate_evaluation_ids", ())
            ),
            closure_snapshot_ids=tuple(str(item) for item in raw.get("closure_snapshot_ids", ())),
            task_handoff_bindings=tuple(dict(item) for item in raw.get("task_handoff_bindings", ())),
            workpage_handoff_bindings=tuple(
                dict(item) for item in raw.get("workpage_handoff_bindings", ())
            ),
            basis_version_vector_json=dict(raw.get("basis_version_vector_json", {})),
            metadata_json=dict(raw.get("metadata_json", {})),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "manifest_id": self.manifest_id,
            "schema_version": self.schema_version,
            "tenant_id": self.tenant_id,
            "domain_id": self.domain_id,
            "project_id": self.project_id,
            "source_workflow_run_id": self.source_workflow_run_id,
            "target_workflow_id": self.target_workflow_id,
            "target_workflow_version": self.target_workflow_version,
            "target_partition_key": self.target_partition_key,
            "artifact_versions": list(self.artifact_versions),
            "pointers": list(self.pointers),
            "source_refs": list(self.source_refs),
            "validation_summaries": list(self.validation_summaries),
            "closure_gate_evaluation_ids": list(self.closure_gate_evaluation_ids),
            "closure_snapshot_ids": list(self.closure_snapshot_ids),
            "task_handoff_bindings": list(self.task_handoff_bindings),
            "workpage_handoff_bindings": list(self.workpage_handoff_bindings),
            "basis_version_vector_json": self.basis_version_vector_json,
            "metadata_json": self.metadata_json,
        }


@dataclass(frozen=True)
class HandoffManifestValidationResult:
    manifest_id: str | None
    valid: bool
    error_codes: tuple[str, ...]


class HandoffManifestValidationError(ValueError):
    def __init__(self, result: HandoffManifestValidationResult) -> None:
        super().__init__(
            "handoff manifest is invalid: " + ", ".join(result.error_codes)
        )
        self.result = result


def validate_handoff_manifest(
    connection: sqlite3.Connection,
    manifest: HandoffManifest | Mapping[str, Any] | None,
) -> HandoffManifestValidationResult:
    if manifest is None:
        return HandoffManifestValidationResult(
            manifest_id=None,
            valid=False,
            error_codes=("missing_handoff_manifest",),
        )

    try:
        resolved = manifest if isinstance(manifest, HandoffManifest) else HandoffManifest.from_dict(manifest)
    except (KeyError, TypeError, ValueError):
        return HandoffManifestValidationResult(
            manifest_id=None,
            valid=False,
            error_codes=("malformed_handoff_manifest",),
        )

    errors: list[str] = []
    source_run = get_workflow_run(connection, resolved.source_workflow_run_id)
    if source_run is None:
        errors.append("source_workflow_run_not_found")
    elif not _row_matches_scope(source_run, resolved.tenant_id, resolved.domain_id, resolved.project_id):
        errors.append("source_workflow_run_scope_mismatch")

    if not resolved.artifact_versions:
        errors.append("missing_artifact_basis")
    for artifact_ref in resolved.artifact_versions:
        errors.extend(_validate_artifact_ref(connection, resolved, artifact_ref))

    if not resolved.pointers:
        errors.append("missing_pointer_basis")
    for pointer_ref in resolved.pointers:
        errors.extend(_validate_pointer_ref(connection, resolved, pointer_ref))

    try:
        require_meaningful_source_refs(
            connection,
            resolved.source_refs,
            tenant_id=resolved.tenant_id,
            domain_id=resolved.domain_id,
            project_id=resolved.project_id,
        )
    except SourceRefResolutionError:
        errors.append("source_refs_not_meaningful")

    if not resolved.validation_summaries:
        errors.append("missing_validation_summary")
    for summary in resolved.validation_summaries:
        if str(summary.get("result") or "") not in {"pass", "satisfied_by_waiver"}:
            errors.append("validation_summary_not_satisfied")

    if not resolved.closure_gate_evaluation_ids:
        errors.append("missing_closure_evaluation_basis")
    for evaluation_id in resolved.closure_gate_evaluation_ids:
        evaluation = get_closure_gate_evaluation(connection, evaluation_id)
        if evaluation is None:
            errors.append("closure_evaluation_not_found")
        elif not _row_matches_scope(evaluation, resolved.tenant_id, resolved.domain_id, resolved.project_id):
            errors.append("closure_evaluation_scope_mismatch")
        elif str(evaluation["result"]) == "fail":
            errors.append("closure_evaluation_failed")

    if not resolved.closure_snapshot_ids:
        errors.append("missing_closure_snapshot_basis")
    for snapshot_id in resolved.closure_snapshot_ids:
        snapshot = get_closure_snapshot(connection, snapshot_id)
        if snapshot is None:
            errors.append("closure_snapshot_not_found")
        elif not _row_matches_scope(snapshot, resolved.tenant_id, resolved.domain_id, resolved.project_id):
            errors.append("closure_snapshot_scope_mismatch")
        elif str(snapshot["state"]) != "current":
            errors.append("closure_snapshot_not_current")
        elif str(snapshot["result"]) == "fail":
            errors.append("closure_snapshot_failed")

    if not resolved.task_handoff_bindings:
        errors.append("missing_task_handoff_bindings")
    if not resolved.workpage_handoff_bindings:
        errors.append("missing_workpage_handoff_bindings")
    if not resolved.basis_version_vector_json:
        errors.append("missing_basis_version_vector")

    unique_errors = tuple(dict.fromkeys(errors))
    return HandoffManifestValidationResult(
        manifest_id=resolved.manifest_id,
        valid=not unique_errors,
        error_codes=unique_errors,
    )


def require_valid_handoff_manifest(
    connection: sqlite3.Connection,
    manifest: HandoffManifest | Mapping[str, Any] | None,
) -> HandoffManifest:
    result = validate_handoff_manifest(connection, manifest)
    if not result.valid:
        raise HandoffManifestValidationError(result)
    return manifest if isinstance(manifest, HandoffManifest) else HandoffManifest.from_dict(manifest or {})


def _validate_artifact_ref(
    connection: sqlite3.Connection,
    manifest: HandoffManifest,
    artifact_ref: Mapping[str, Any],
) -> list[str]:
    artifact_version_id = str(artifact_ref.get("artifact_version_id") or "")
    if not artifact_version_id:
        return ["malformed_artifact_basis"]
    artifact = get_artifact_version(connection, artifact_version_id)
    if artifact is None:
        return ["artifact_version_not_found"]

    errors: list[str] = []
    if str(artifact["workflow_run_id"]) != manifest.source_workflow_run_id:
        errors.append("artifact_workflow_run_mismatch")
    if artifact.get("tenant_id") is not None and str(artifact["tenant_id"]) != manifest.tenant_id:
        errors.append("artifact_scope_mismatch")
    if artifact.get("domain_id") is not None and str(artifact["domain_id"]) != manifest.domain_id:
        errors.append("artifact_scope_mismatch")
    if artifact_ref.get("artifact_kind") is not None and str(artifact["artifact_kind"]) != str(
        artifact_ref["artifact_kind"]
    ):
        errors.append("artifact_kind_mismatch")
    if artifact_ref.get("content_digest") is not None and str(artifact["content_digest"]) != str(
        artifact_ref["content_digest"]
    ):
        errors.append("artifact_digest_mismatch")
    return errors


def _validate_pointer_ref(
    connection: sqlite3.Connection,
    manifest: HandoffManifest,
    pointer_ref: Mapping[str, Any],
) -> list[str]:
    pointer_id = str(pointer_ref.get("pointer_id") or "")
    if not pointer_id:
        return ["malformed_pointer_basis"]
    pointer = get_pointer_by_id(connection, pointer_id=pointer_id)
    if pointer is None:
        return ["pointer_not_found"]

    errors: list[str] = []
    if str(pointer.get("tenant_id") or "") != manifest.tenant_id:
        errors.append("pointer_scope_mismatch")
    if str(pointer.get("domain_id") or "") != manifest.domain_id:
        errors.append("pointer_scope_mismatch")
    if pointer_ref.get("pointer_key") is not None and str(pointer["pointer_key"]) != str(
        pointer_ref["pointer_key"]
    ):
        errors.append("pointer_key_mismatch")
    if pointer_ref.get("artifact_version_id") is not None and str(pointer["artifact_version_id"]) != str(
        pointer_ref["artifact_version_id"]
    ):
        errors.append("pointer_artifact_mismatch")
    if pointer_ref.get("generation") is not None and int(pointer["generation"]) != int(
        pointer_ref["generation"]
    ):
        errors.append("pointer_generation_drift")
    return errors


def _row_matches_scope(
    row: Mapping[str, Any],
    tenant_id: str,
    domain_id: str,
    project_id: str | None,
) -> bool:
    row_project_id = row.get("project_id") if row.get("project_id") is not None else None
    return str(row["tenant_id"]) == tenant_id and str(row["domain_id"]) == domain_id and row_project_id == project_id


__all__ = [
    "HandoffManifest",
    "HandoffManifestValidationError",
    "HandoffManifestValidationResult",
    "require_valid_handoff_manifest",
    "validate_handoff_manifest",
]
