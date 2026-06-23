from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
import hashlib
import json
import re
from typing import Any

from onetruth.capex_platform.document_manifest import (
    DOCUMENT_MANIFEST_OUTPUTS_SCHEMA_VERSION,
    DOCUMENT_MANIFEST_SCHEMA_VERSION,
)


ASYNC_DOCUMENT_PROCESSING_JOB_RUNTIME_OUTPUTS_SCHEMA_VERSION = (
    "capex.async_document_processing_job_runtime.outputs.v1"
)
DOCUMENT_PROCESSING_JOB_REGISTER_SCHEMA_VERSION = (
    "capex.document_processing_job_register.v1"
)
DOCUMENT_PROCESSING_JOB_ATTEMPT_REGISTER_SCHEMA_VERSION = (
    "capex.document_processing_job_attempt_register.v1"
)
DOCUMENT_PROCESSING_JOB_PROGRESS_SCHEMA_VERSION = (
    "capex.document_processing_job_progress.v1"
)
ASYNC_DOCUMENT_PROCESSING_JOB_RUNTIME_ACTIVATION_POSTURE = (
    "planning_only_no_capex_activation"
)

JOB_KINDS = frozenset(
    {
        "document_manifest_build",
        "text_extraction",
        "page_manifest",
        "chunk_index",
        "evidence_binding",
        "corpus_processing",
    }
)
JOB_STATES = frozenset(
    {
        "queued",
        "running",
        "retry_pending",
        "resume_pending",
        "succeeded",
        "failed",
        "canceled",
    }
)
ATTEMPT_STATES = frozenset(
    {
        "queued",
        "running",
        "succeeded",
        "failed",
        "canceled",
    }
)
TERMINAL_ATTEMPT_STATES = frozenset({"succeeded", "canceled"})

_ABSOLUTE_PATH_RE = re.compile(r"^(?:/|[A-Za-z]:[\\/]|\\\\)")
_RAW_FILENAME_RE = re.compile(
    r"(?i)^[A-Za-z0-9 _.-]+\.(pdf|docx|xlsx|pptx|png|jpg|jpeg|zip|txt|csv)$"
)
_SOURCE_REF_RE = re.compile(r"^source_occurrence:[A-Za-z0-9_.:-]+$")
_SHA256_RE = re.compile(r"^sha256:[0-9a-f]{64}$")
_STORAGE_REF_RE = re.compile(r"^(?:object|storage|artifact|sanitized)://[A-Za-z0-9_./:=@-]+$")
_PLANNED_TASK_REF_RE = re.compile(r"^planned_task:[A-Za-z0-9_.:-]+$")
_PLANNED_ARTIFACT_REF_RE = re.compile(r"^planned_artifact:[A-Za-z0-9_.:-]+$")
_EXECUTION_SESSION_REF_RE = re.compile(r"^execution_session:[A-Za-z0-9_.:-]+$")
_RAW_PATH_MARKERS = ("/Users/", "\\Users\\")
_FORBIDDEN_RAW_KEYS = {
    "absolute_path",
    "base64",
    "base64_content",
    "blob_bytes",
    "content",
    "document_text",
    "error_log",
    "extracted_text",
    "file_name",
    "filename",
    "full_text",
    "job_log",
    "local_path",
    "ocr_text",
    "path",
    "raw_bytes",
    "raw_content",
    "raw_error",
    "raw_file",
    "raw_filename",
    "raw_log",
    "source_filename",
    "source_text",
    "stack_trace",
    "stderr",
    "stdout",
    "text",
    "text_excerpt",
}


@dataclass(frozen=True)
class AsyncDocumentProcessingJobRuntimeError(ValueError):
    code: str
    details: dict[str, Any]

    def __str__(self) -> str:
        return self.code


def build_async_document_processing_job_runtime_outputs(
    *,
    document_manifest_outputs: Mapping[str, Any],
    job_rows: Sequence[Mapping[str, Any]],
    attempt_rows: Sequence[Mapping[str, Any]],
    progress_rows: Sequence[Mapping[str, Any]],
    runtime_id: str,
    created_at: str,
    created_by_actor_id: str,
    created_by_actor_type: str,
) -> dict[str, Any]:
    """Build planning-only async document-processing job runtime outputs."""

    basis = _require_document_manifest_outputs(document_manifest_outputs)
    if not job_rows:
        raise AsyncDocumentProcessingJobRuntimeError(
            "async_job_rows_required",
            {"field": "job_rows"},
        )
    if not attempt_rows:
        raise AsyncDocumentProcessingJobRuntimeError(
            "async_job_attempt_rows_required",
            {"field": "attempt_rows"},
        )
    if not progress_rows:
        raise AsyncDocumentProcessingJobRuntimeError(
            "async_job_progress_rows_required",
            {"field": "progress_rows"},
        )

    runtime_id = _require_nonempty(runtime_id, "runtime_id")
    jobs: list[dict[str, Any]] = []
    seen_job_ids: set[str] = set()
    seen_task_refs: set[str] = set()
    seen_artifact_refs: set[str] = set()
    for index, raw_row in enumerate(job_rows):
        if not isinstance(raw_row, Mapping):
            raise AsyncDocumentProcessingJobRuntimeError(
                "async_job_row_must_be_object",
                {"index": index},
            )
        row = _job_row(
            index=index,
            raw_row=raw_row,
            basis=basis,
            runtime_id=runtime_id,
        )
        if row["job_id"] in seen_job_ids:
            raise AsyncDocumentProcessingJobRuntimeError(
                "async_job_duplicate_job_id",
                {"index": index, "job_id": row["job_id"]},
            )
        _ensure_global_unique_refs(row["planned_task_refs"], seen_task_refs, index, "planned_task_ref")
        _ensure_global_unique_refs(
            row["planned_artifact_refs"],
            seen_artifact_refs,
            index,
            "planned_artifact_ref",
        )
        seen_job_ids.add(row["job_id"])
        jobs.append(row)

    jobs_by_id = {row["job_id"]: row for row in jobs}
    attempts: list[dict[str, Any]] = []
    seen_attempt_ids: set[str] = set()
    attempts_by_job: dict[str, list[dict[str, Any]]] = {job_id: [] for job_id in jobs_by_id}
    for index, raw_row in enumerate(attempt_rows):
        if not isinstance(raw_row, Mapping):
            raise AsyncDocumentProcessingJobRuntimeError(
                "async_job_attempt_row_must_be_object",
                {"index": index},
            )
        row = _attempt_row(index=index, raw_row=raw_row, jobs_by_id=jobs_by_id)
        if row["attempt_id"] in seen_attempt_ids:
            raise AsyncDocumentProcessingJobRuntimeError(
                "async_job_duplicate_attempt_id",
                {"index": index, "attempt_id": row["attempt_id"]},
            )
        seen_attempt_ids.add(row["attempt_id"])
        attempts_by_job[row["job_id"]].append(row)
        attempts.append(row)

    for job_id, rows in attempts_by_job.items():
        if not rows:
            raise AsyncDocumentProcessingJobRuntimeError(
                "async_job_attempt_required_for_job",
                {"job_id": job_id},
            )
        _validate_attempt_sequence(job=jobs_by_id[job_id], attempts=rows)

    progress: list[dict[str, Any]] = []
    seen_progress_ids: set[str] = set()
    for index, raw_row in enumerate(progress_rows):
        if not isinstance(raw_row, Mapping):
            raise AsyncDocumentProcessingJobRuntimeError(
                "async_job_progress_row_must_be_object",
                {"index": index},
            )
        row = _progress_row(index=index, raw_row=raw_row, jobs_by_id=jobs_by_id)
        if row["progress_id"] in seen_progress_ids:
            raise AsyncDocumentProcessingJobRuntimeError(
                "async_job_duplicate_progress_id",
                {"index": index, "progress_id": row["progress_id"]},
            )
        seen_progress_ids.add(row["progress_id"])
        progress.append(row)

    jobs = sorted(jobs, key=lambda row: row["job_id"])
    attempts = sorted(attempts, key=lambda row: (row["job_id"], row["attempt_no"], row["attempt_id"]))
    progress = sorted(progress, key=lambda row: (row["job_id"], row["progress_id"]))
    return {
        "schema_version": ASYNC_DOCUMENT_PROCESSING_JOB_RUNTIME_OUTPUTS_SCHEMA_VERSION,
        "activation_posture": ASYNC_DOCUMENT_PROCESSING_JOB_RUNTIME_ACTIVATION_POSTURE,
        "runtime_id": runtime_id,
        "tenant_id": basis["tenant_id"],
        "domain_id": basis["domain_id"],
        "project_id": basis["project_id"],
        "created_at": _require_nonempty(created_at, "created_at"),
        "created_by_actor": {
            "id": _require_nonempty(created_by_actor_id, "created_by_actor_id"),
            "type": _require_nonempty(created_by_actor_type, "created_by_actor_type"),
        },
        "basis": {
            "document_manifest_id": basis["document_manifest_id"],
            "document_manifest_snapshot_digest": basis["document_manifest_snapshot_digest"],
            "extraction_state_register_id": basis["extraction_state_register_id"],
        },
        "document_processing_job_register": {
            "schema_version": DOCUMENT_PROCESSING_JOB_REGISTER_SCHEMA_VERSION,
            "rows": jobs,
            "row_count": len(jobs),
            "snapshot_digest": _digest(jobs),
        },
        "document_processing_job_attempt_register": {
            "schema_version": DOCUMENT_PROCESSING_JOB_ATTEMPT_REGISTER_SCHEMA_VERSION,
            "rows": attempts,
            "row_count": len(attempts),
            "snapshot_digest": _digest(attempts),
        },
        "document_processing_job_progress": {
            "schema_version": DOCUMENT_PROCESSING_JOB_PROGRESS_SCHEMA_VERSION,
            "rows": progress,
            "row_count": len(progress),
            "snapshot_digest": _digest(progress),
        },
        "truth_effects": {
            "creates_extraction_jobs": False,
            "creates_execution_sessions": False,
            "creates_command_receipts": False,
            "starts_workers": False,
            "runs_parser_adapter": False,
            "writes_artifacts": False,
            "promotes_official_pointers": False,
            "activates_workflow_pack": False,
        },
        "cannot_be_used_for": [
            "queue_worker_activation",
            "parser_runtime_activation",
            "ocr_runtime_activation",
            "search_runtime_activation",
            "public_route_activation",
            "frontend_route_activation",
            "migration_approval",
            "raw_corpus_import",
            "reviewed_baseline_creation",
            "official_pointer_creation",
            "capex_runtime_activation",
            "product_activation",
        ],
    }


def canonical_async_document_processing_job_runtime_bytes(
    outputs: Mapping[str, Any],
) -> bytes:
    return json.dumps(
        outputs,
        separators=(",", ":"),
        sort_keys=True,
        ensure_ascii=True,
        allow_nan=False,
    ).encode("utf-8")


def async_document_processing_job_runtime_digest(outputs: Mapping[str, Any]) -> str:
    return "sha256:" + hashlib.sha256(
        canonical_async_document_processing_job_runtime_bytes(outputs)
    ).hexdigest()


def _job_row(
    *,
    index: int,
    raw_row: Mapping[str, Any],
    basis: Mapping[str, Any],
    runtime_id: str,
) -> dict[str, Any]:
    _reject_raw_material(raw_row, path=f"job_rows[{index}]")
    job_id = _require_nonempty(raw_row.get("job_id"), f"job_rows[{index}].job_id")
    job_kind = _allowed(
        raw_row.get("job_kind"),
        JOB_KINDS,
        f"job_rows[{index}].job_kind",
        "async_job_kind_invalid",
    )
    job_state = _allowed(
        raw_row.get("job_state"),
        JOB_STATES,
        f"job_rows[{index}].job_state",
        "async_job_state_invalid",
    )
    document_ids = _document_ids(raw_row.get("document_ids"), basis, index)
    source_refs = _source_refs(raw_row.get("source_refs"), basis, index=index, required=True)
    receipt = _command_receipt(raw_row.get("command_receipt"), index=index, field="command_receipt")
    derived_idempotency_key = _derived_idempotency_key(
        tenant_id=basis["tenant_id"],
        domain_id=basis["domain_id"],
        project_id=basis["project_id"],
        job_id=job_id,
        job_kind=job_kind,
        document_ids=document_ids,
    )
    if receipt["idempotency_key"] != derived_idempotency_key:
        raise AsyncDocumentProcessingJobRuntimeError(
            "async_job_idempotency_key_mismatch",
            {
                "index": index,
                "job_id": job_id,
                "expected": derived_idempotency_key,
                "actual": receipt["idempotency_key"],
            },
        )
    execution_session_ref = _optional_ref(
        raw_row.get("execution_session_ref"),
        _EXECUTION_SESSION_REF_RE,
        f"job_rows[{index}].execution_session_ref",
        "async_job_execution_session_ref_invalid",
    )
    planned_task_refs = _planned_refs(
        raw_row.get("planned_task_refs"),
        default=[f"planned_task:{runtime_id}:{job_id}"],
        regex=_PLANNED_TASK_REF_RE,
        field=f"job_rows[{index}].planned_task_refs",
        error_code="async_job_planned_task_ref_invalid",
    )
    planned_artifact_refs = _planned_refs(
        raw_row.get("planned_artifact_refs"),
        default=[f"planned_artifact:{runtime_id}:{job_id}:outputs"],
        regex=_PLANNED_ARTIFACT_REF_RE,
        field=f"job_rows[{index}].planned_artifact_refs",
        error_code="async_job_planned_artifact_ref_invalid",
    )
    storage_ref = _optional_ref(
        raw_row.get("job_manifest_storage_ref"),
        _STORAGE_REF_RE,
        f"job_rows[{index}].job_manifest_storage_ref",
        "async_job_storage_ref_invalid",
    )
    return {
        "job_id": job_id,
        "job_kind": job_kind,
        "job_state": job_state,
        "document_ids": document_ids,
        "source_refs": source_refs,
        "command_receipt": receipt,
        "derived_idempotency_key": derived_idempotency_key,
        "execution_session_ref": execution_session_ref,
        "planned_task_refs": planned_task_refs,
        "planned_artifact_refs": planned_artifact_refs,
        "job_manifest_storage_ref": storage_ref,
        "side_effects_planned_only": True,
    }


def _attempt_row(
    *,
    index: int,
    raw_row: Mapping[str, Any],
    jobs_by_id: Mapping[str, Mapping[str, Any]],
) -> dict[str, Any]:
    _reject_raw_material(raw_row, path=f"attempt_rows[{index}]")
    attempt_id = _require_nonempty(raw_row.get("attempt_id"), f"attempt_rows[{index}].attempt_id")
    job_id = _require_nonempty(raw_row.get("job_id"), f"attempt_rows[{index}].job_id")
    job = jobs_by_id.get(job_id)
    if job is None:
        raise AsyncDocumentProcessingJobRuntimeError(
            "async_job_attempt_unknown_job_id",
            {"index": index, "job_id": job_id},
        )
    attempt_no = _positive_int(raw_row.get("attempt_no"), f"attempt_rows[{index}].attempt_no")
    attempt_state = _allowed(
        raw_row.get("attempt_state"),
        ATTEMPT_STATES,
        f"attempt_rows[{index}].attempt_state",
        "async_job_attempt_state_invalid",
    )
    receipt = _command_receipt(raw_row.get("command_receipt"), index=index, field="command_receipt")
    if receipt["idempotency_key"] != job["derived_idempotency_key"]:
        raise AsyncDocumentProcessingJobRuntimeError(
            "async_job_attempt_idempotency_key_mismatch",
            {
                "index": index,
                "job_id": job_id,
                "expected": job["derived_idempotency_key"],
                "actual": receipt["idempotency_key"],
            },
        )
    planned_task_refs = _planned_refs(
        raw_row.get("planned_task_refs"),
        default=list(job["planned_task_refs"]),
        regex=_PLANNED_TASK_REF_RE,
        field=f"attempt_rows[{index}].planned_task_refs",
        error_code="async_job_planned_task_ref_invalid",
    )
    planned_artifact_refs = _planned_refs(
        raw_row.get("planned_artifact_refs"),
        default=list(job["planned_artifact_refs"]),
        regex=_PLANNED_ARTIFACT_REF_RE,
        field=f"attempt_rows[{index}].planned_artifact_refs",
        error_code="async_job_planned_artifact_ref_invalid",
    )
    if planned_task_refs != job["planned_task_refs"]:
        raise AsyncDocumentProcessingJobRuntimeError(
            "async_job_attempt_task_refs_not_stable",
            {"index": index, "job_id": job_id},
        )
    if planned_artifact_refs != job["planned_artifact_refs"]:
        raise AsyncDocumentProcessingJobRuntimeError(
            "async_job_attempt_artifact_refs_not_stable",
            {"index": index, "job_id": job_id},
        )
    return {
        "attempt_id": attempt_id,
        "job_id": job_id,
        "attempt_no": attempt_no,
        "attempt_state": attempt_state,
        "command_receipt": receipt,
        "planned_task_refs": planned_task_refs,
        "planned_artifact_refs": planned_artifact_refs,
        "retry_reuses_planned_refs": True,
    }


def _progress_row(
    *,
    index: int,
    raw_row: Mapping[str, Any],
    jobs_by_id: Mapping[str, Mapping[str, Any]],
) -> dict[str, Any]:
    _reject_raw_material(raw_row, path=f"progress_rows[{index}]")
    progress_id = _require_nonempty(raw_row.get("progress_id"), f"progress_rows[{index}].progress_id")
    job_id = _require_nonempty(raw_row.get("job_id"), f"progress_rows[{index}].job_id")
    job = jobs_by_id.get(job_id)
    if job is None:
        raise AsyncDocumentProcessingJobRuntimeError(
            "async_job_progress_unknown_job_id",
            {"index": index, "job_id": job_id},
        )
    total = _nonnegative_int(raw_row.get("documents_total"), f"progress_rows[{index}].documents_total")
    processed = _nonnegative_int(raw_row.get("documents_processed"), f"progress_rows[{index}].documents_processed")
    failed = _nonnegative_int(raw_row.get("documents_failed", 0), f"progress_rows[{index}].documents_failed")
    if processed + failed > total:
        raise AsyncDocumentProcessingJobRuntimeError(
            "async_job_progress_counts_invalid",
            {
                "index": index,
                "job_id": job_id,
                "documents_total": total,
                "documents_processed": processed,
                "documents_failed": failed,
            },
        )
    percent = int(round(((processed + failed) / total) * 100)) if total else 0
    if percent > 100:
        raise AsyncDocumentProcessingJobRuntimeError(
            "async_job_progress_percent_invalid",
            {"index": index, "job_id": job_id, "progress_percent": percent},
        )
    source_refs = _source_refs(raw_row.get("source_refs"), {"source_refs": job["source_refs"]}, index=index, required=False)
    return {
        "progress_id": progress_id,
        "job_id": job_id,
        "documents_total": total,
        "documents_processed": processed,
        "documents_failed": failed,
        "documents_pending": total - processed - failed,
        "progress_percent": percent,
        "source_refs": source_refs or list(job["source_refs"]),
    }


def _validate_attempt_sequence(
    *,
    job: Mapping[str, Any],
    attempts: Sequence[Mapping[str, Any]],
) -> None:
    ordered = sorted(attempts, key=lambda row: int(row["attempt_no"]))
    expected = list(range(1, len(ordered) + 1))
    actual = [int(row["attempt_no"]) for row in ordered]
    if actual != expected:
        raise AsyncDocumentProcessingJobRuntimeError(
            "async_job_attempt_sequence_not_monotonic",
            {"job_id": job["job_id"], "expected": expected, "actual": actual},
        )
    terminal_index: int | None = None
    for index, row in enumerate(ordered):
        if row["attempt_state"] in TERMINAL_ATTEMPT_STATES:
            terminal_index = index
            break
    if terminal_index is not None and terminal_index != len(ordered) - 1:
        raise AsyncDocumentProcessingJobRuntimeError(
            "async_job_retry_after_terminal_attempt",
            {
                "job_id": job["job_id"],
                "attempt_state": ordered[terminal_index]["attempt_state"],
            },
        )
    last_state = ordered[-1]["attempt_state"]
    job_state = str(job["job_state"])
    if job_state == "succeeded" and last_state != "succeeded":
        raise AsyncDocumentProcessingJobRuntimeError(
            "async_job_succeeded_requires_succeeded_attempt",
            {"job_id": job["job_id"], "last_attempt_state": last_state},
        )
    if job_state == "canceled" and last_state != "canceled":
        raise AsyncDocumentProcessingJobRuntimeError(
            "async_job_canceled_requires_canceled_attempt",
            {"job_id": job["job_id"], "last_attempt_state": last_state},
        )
    if job_state == "retry_pending" and last_state != "failed":
        raise AsyncDocumentProcessingJobRuntimeError(
            "async_job_retry_pending_requires_failed_attempt",
            {"job_id": job["job_id"], "last_attempt_state": last_state},
        )
    if job_state == "resume_pending" and last_state not in {"running", "failed"}:
        raise AsyncDocumentProcessingJobRuntimeError(
            "async_job_resume_pending_requires_open_attempt",
            {"job_id": job["job_id"], "last_attempt_state": last_state},
        )


def _require_document_manifest_outputs(raw: Mapping[str, Any]) -> dict[str, Any]:
    if raw.get("schema_version") != DOCUMENT_MANIFEST_OUTPUTS_SCHEMA_VERSION:
        raise AsyncDocumentProcessingJobRuntimeError(
            "async_job_requires_document_manifest_outputs",
            {
                "expected_schema_version": DOCUMENT_MANIFEST_OUTPUTS_SCHEMA_VERSION,
                "actual_schema_version": raw.get("schema_version"),
            },
        )
    manifest = raw.get("document_manifest")
    if not isinstance(manifest, Mapping) or manifest.get("schema_version") != DOCUMENT_MANIFEST_SCHEMA_VERSION:
        raise AsyncDocumentProcessingJobRuntimeError(
            "async_job_requires_document_manifest",
            {"expected_schema_version": DOCUMENT_MANIFEST_SCHEMA_VERSION},
        )
    rows = manifest.get("rows")
    if not isinstance(rows, Sequence) or isinstance(rows, (str, bytes)) or not rows:
        raise AsyncDocumentProcessingJobRuntimeError(
            "async_job_document_manifest_rows_required",
            {"field": "document_manifest.rows"},
        )
    documents: dict[str, Mapping[str, Any]] = {}
    source_refs: set[str] = set()
    for index, row in enumerate(rows):
        if not isinstance(row, Mapping):
            raise AsyncDocumentProcessingJobRuntimeError(
                "async_job_document_manifest_row_must_be_object",
                {"index": index},
            )
        document_id = _require_nonempty(row.get("document_id"), f"document_manifest.rows[{index}].document_id")
        documents[document_id] = row
        for source_ref in row.get("source_refs") or []:
            source_ref_text = str(source_ref)
            if _SOURCE_REF_RE.match(source_ref_text):
                source_refs.add(source_ref_text)
    extraction_state_register = raw.get("extraction_state_register")
    return {
        "tenant_id": _require_nonempty(manifest.get("tenant_id"), "document_manifest.tenant_id"),
        "domain_id": _require_nonempty(manifest.get("domain_id"), "document_manifest.domain_id"),
        "project_id": _require_nonempty(manifest.get("project_id"), "document_manifest.project_id"),
        "document_manifest_id": _require_nonempty(manifest.get("manifest_id"), "document_manifest.manifest_id"),
        "document_manifest_snapshot_digest": _sha256(
            manifest.get("snapshot_digest"),
            "document_manifest.snapshot_digest",
        ),
        "extraction_state_register_id": _require_nonempty(
            extraction_state_register.get("register_id")
            if isinstance(extraction_state_register, Mapping)
            else None,
            "extraction_state_register.register_id",
        ),
        "documents": documents,
        "source_refs": source_refs,
    }


def _document_ids(value: Any, basis: Mapping[str, Any], index: int) -> list[str]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes)) or not value:
        raise AsyncDocumentProcessingJobRuntimeError(
            "async_job_document_ids_required",
            {"index": index},
        )
    known_documents = basis["documents"]
    rows: list[str] = []
    for value_index, raw_id in enumerate(value):
        document_id = _require_nonempty(raw_id, f"job_rows[{index}].document_ids[{value_index}]")
        if document_id not in known_documents:
            raise AsyncDocumentProcessingJobRuntimeError(
                "async_job_unknown_document_id",
                {"index": index, "document_id": document_id},
            )
        if document_id in rows:
            raise AsyncDocumentProcessingJobRuntimeError(
                "async_job_duplicate_document_id",
                {"index": index, "document_id": document_id},
            )
        rows.append(document_id)
    return sorted(rows)


def _source_refs(
    value: Any,
    basis: Mapping[str, Any],
    *,
    index: int,
    required: bool,
) -> list[str]:
    if value is None:
        if required:
            raise AsyncDocumentProcessingJobRuntimeError(
                "async_job_source_refs_required",
                {"index": index},
            )
        return []
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes)) or (required and not value):
        raise AsyncDocumentProcessingJobRuntimeError(
            "async_job_source_refs_must_be_list",
            {"index": index},
        )
    known_source_refs = set(basis.get("source_refs") or [])
    refs: list[str] = []
    for ref_index, raw_ref in enumerate(value):
        source_ref = _require_nonempty(raw_ref, f"source_refs[{ref_index}]")
        if not _SOURCE_REF_RE.match(source_ref):
            raise AsyncDocumentProcessingJobRuntimeError(
                "async_job_source_ref_invalid",
                {"index": index, "source_ref": source_ref},
            )
        if known_source_refs and source_ref not in known_source_refs:
            raise AsyncDocumentProcessingJobRuntimeError(
                "async_job_source_ref_not_in_document_manifest",
                {"index": index, "source_ref": source_ref},
            )
        if source_ref in refs:
            raise AsyncDocumentProcessingJobRuntimeError(
                "async_job_duplicate_source_ref",
                {"index": index, "source_ref": source_ref},
            )
        refs.append(source_ref)
    return sorted(refs)


def _command_receipt(value: Any, *, index: int, field: str) -> dict[str, str]:
    if not isinstance(value, Mapping):
        raise AsyncDocumentProcessingJobRuntimeError(
            "async_job_command_receipt_required",
            {"index": index, "field": field},
        )
    return {
        "command_name": _require_nonempty(value.get("command_name"), f"{field}.command_name"),
        "scope_key": _require_nonempty(value.get("scope_key"), f"{field}.scope_key"),
        "idempotency_key": _require_nonempty(value.get("idempotency_key"), f"{field}.idempotency_key"),
        "request_fingerprint": _sha256(
            value.get("request_fingerprint"),
            f"{field}.request_fingerprint",
        ),
    }


def _derived_idempotency_key(
    *,
    tenant_id: str,
    domain_id: str,
    project_id: str,
    job_id: str,
    job_kind: str,
    document_ids: Sequence[str],
) -> str:
    seed = _digest(
        {
            "tenant_id": tenant_id,
            "domain_id": domain_id,
            "project_id": project_id,
            "job_id": job_id,
            "job_kind": job_kind,
            "document_ids": list(document_ids),
        }
    ).removeprefix("sha256:")
    return f"capex-doc-processing:{seed}"


def _planned_refs(
    value: Any,
    *,
    default: list[str],
    regex: re.Pattern[str],
    field: str,
    error_code: str,
) -> list[str]:
    raw_values = default if value is None else value
    if not isinstance(raw_values, Sequence) or isinstance(raw_values, (str, bytes)) or not raw_values:
        raise AsyncDocumentProcessingJobRuntimeError(
            "async_job_planned_refs_required",
            {"field": field},
        )
    rows: list[str] = []
    for index, raw_value in enumerate(raw_values):
        ref = _require_nonempty(raw_value, f"{field}[{index}]")
        if not regex.match(ref):
            raise AsyncDocumentProcessingJobRuntimeError(
                error_code,
                {"field": field, "ref": ref},
            )
        if ref in rows:
            raise AsyncDocumentProcessingJobRuntimeError(
                "async_job_duplicate_planned_ref",
                {"field": field, "ref": ref},
            )
        rows.append(ref)
    return sorted(rows)


def _ensure_global_unique_refs(
    refs: Sequence[str],
    seen_refs: set[str],
    index: int,
    ref_kind: str,
) -> None:
    for ref in refs:
        if ref in seen_refs:
            raise AsyncDocumentProcessingJobRuntimeError(
                "async_job_duplicate_global_planned_ref",
                {"index": index, "ref_kind": ref_kind, "ref": ref},
            )
        seen_refs.add(ref)


def _optional_ref(
    value: Any,
    regex: re.Pattern[str],
    field: str,
    error_code: str,
) -> str | None:
    if value is None:
        return None
    ref = _require_nonempty(value, field)
    if not regex.match(ref):
        raise AsyncDocumentProcessingJobRuntimeError(
            error_code,
            {"field": field, "ref": ref},
        )
    return ref


def _allowed(
    value: Any,
    allowed: frozenset[str],
    field: str,
    error_code: str,
) -> str:
    normalized = _require_nonempty(value, field)
    if normalized not in allowed:
        raise AsyncDocumentProcessingJobRuntimeError(
            error_code,
            {"field": field, "value": normalized, "allowed": sorted(allowed)},
        )
    return normalized


def _require_nonempty(value: Any, field: str) -> str:
    normalized = str(value).strip() if value is not None else ""
    if not normalized:
        raise AsyncDocumentProcessingJobRuntimeError(
            "async_job_required_field_missing",
            {"field": field},
        )
    return normalized


def _positive_int(value: Any, field: str) -> int:
    if not isinstance(value, int) or value <= 0:
        raise AsyncDocumentProcessingJobRuntimeError(
            "async_job_positive_integer_required",
            {"field": field, "value": value},
        )
    return value


def _nonnegative_int(value: Any, field: str) -> int:
    if not isinstance(value, int) or value < 0:
        raise AsyncDocumentProcessingJobRuntimeError(
            "async_job_nonnegative_integer_required",
            {"field": field, "value": value},
        )
    return value


def _sha256(value: Any, field: str) -> str:
    text = _require_nonempty(value, field)
    if not _SHA256_RE.match(text):
        raise AsyncDocumentProcessingJobRuntimeError(
            "async_job_sha256_digest_invalid",
            {"field": field, "value": text},
        )
    return text


def _reject_raw_material(value: Any, *, path: str) -> None:
    if isinstance(value, Mapping):
        for key, nested in value.items():
            key_text = str(key)
            normalized_key = key_text.strip().lower()
            if normalized_key in _FORBIDDEN_RAW_KEYS or normalized_key.startswith("raw_"):
                raise AsyncDocumentProcessingJobRuntimeError(
                    "async_job_raw_material_rejected",
                    {"path": f"{path}.{key_text}", "reason": "forbidden_key"},
                )
            _reject_raw_material(nested, path=f"{path}.{key_text}")
        return
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes)):
        for index, item in enumerate(value):
            _reject_raw_material(item, path=f"{path}[{index}]")
        return
    if isinstance(value, str):
        stripped = value.strip()
        lowered = stripped.lower()
        if (
            lowered.startswith("data:")
            or "base64," in lowered
            or _ABSOLUTE_PATH_RE.match(stripped)
            or any(marker in stripped for marker in _RAW_PATH_MARKERS)
            or _RAW_FILENAME_RE.match(stripped)
        ):
            raise AsyncDocumentProcessingJobRuntimeError(
                "async_job_raw_material_rejected",
                {"path": path, "reason": "forbidden_value"},
            )


def _digest(value: Any) -> str:
    return "sha256:" + hashlib.sha256(
        json.dumps(
            value,
            separators=(",", ":"),
            sort_keys=True,
            ensure_ascii=True,
            allow_nan=False,
        ).encode("utf-8")
    ).hexdigest()


__all__ = [
    "ASYNC_DOCUMENT_PROCESSING_JOB_RUNTIME_ACTIVATION_POSTURE",
    "ASYNC_DOCUMENT_PROCESSING_JOB_RUNTIME_OUTPUTS_SCHEMA_VERSION",
    "DOCUMENT_PROCESSING_JOB_ATTEMPT_REGISTER_SCHEMA_VERSION",
    "DOCUMENT_PROCESSING_JOB_PROGRESS_SCHEMA_VERSION",
    "DOCUMENT_PROCESSING_JOB_REGISTER_SCHEMA_VERSION",
    "AsyncDocumentProcessingJobRuntimeError",
    "async_document_processing_job_runtime_digest",
    "build_async_document_processing_job_runtime_outputs",
    "canonical_async_document_processing_job_runtime_bytes",
]
