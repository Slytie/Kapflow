from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
import json
import re
import sqlite3
from typing import Any


INGEST_BATCH_COLUMNS = """
    ingest_batch_id,
    tenant_id,
    domain_id,
    project_id,
    intake_ref,
    idempotency_key,
    request_fingerprint,
    status,
    descriptor_count,
    metadata_json,
    created_by_actor_id,
    created_by_actor_type,
    created_at,
    updated_at
"""

INGEST_JOB_COLUMNS = """
    ingest_job_id,
    ingest_batch_id,
    tenant_id,
    domain_id,
    project_id,
    job_kind,
    status,
    priority,
    idempotency_key,
    request_fingerprint,
    command_receipt_id,
    planned_task_refs_json,
    planned_artifact_refs_json,
    metadata_json,
    created_at,
    updated_at,
    terminal_at
"""

INGEST_ATTEMPT_COLUMNS = """
    ingest_attempt_id,
    ingest_job_id,
    tenant_id,
    domain_id,
    project_id,
    attempt_no,
    status,
    execution_session_id,
    command_receipt_id,
    lease_token,
    metadata_json,
    started_at,
    completed_at,
    error_code,
    created_at,
    updated_at
"""

INGEST_JOB_LOG_COLUMNS = """
    ingest_job_log_id,
    ingest_job_id,
    ingest_attempt_id,
    tenant_id,
    domain_id,
    project_id,
    log_kind,
    severity,
    message_code,
    message_summary,
    metadata_json,
    created_at
"""

INGEST_BATCH_STATUSES = (
    "planned",
    "accepted",
    "processing",
    "succeeded",
    "failed",
    "canceled",
)
TERMINAL_INGEST_BATCH_STATUSES = frozenset({"succeeded", "failed", "canceled"})

INGEST_JOB_KINDS = (
    "source_inventory",
    "source_occurrence_binding",
    "document_manifest_build",
    "text_extraction",
    "page_manifest",
    "chunk_index",
    "evidence_binding",
    "corpus_processing",
)
INGEST_JOB_STATUSES = (
    "queued",
    "running",
    "retry_pending",
    "resume_pending",
    "succeeded",
    "failed",
    "canceled",
)
TERMINAL_INGEST_JOB_STATUSES = frozenset({"succeeded", "failed", "canceled"})

INGEST_ATTEMPT_STATUSES = ("queued", "running", "succeeded", "failed", "canceled")
TERMINAL_INGEST_ATTEMPT_STATUSES = frozenset({"succeeded", "failed", "canceled"})

INGEST_JOB_LOG_KINDS = (
    "state_transition",
    "validation",
    "retry",
    "failure",
    "operator_note",
    "worker",
)
INGEST_JOB_LOG_SEVERITIES = ("debug", "info", "warning", "error")

_SHA256_RE = re.compile(r"^sha256:[0-9a-f]{64}$")
_ABSOLUTE_PATH_RE = re.compile(r"^(?:/|[A-Za-z]:[\\/]|\\\\)")
_RAW_FILENAME_RE = re.compile(
    r"^[^/\s]+\.(?:csv|doc|docx|eml|jpeg|jpg|msg|pdf|png|txt|xls|xlsx|zip)$",
    re.IGNORECASE,
)
_RAW_PATH_MARKERS = ("/Users/", "\\Users\\")
_FORBIDDEN_RAW_KEYS = {
    "absolute_path",
    "base64",
    "base64_content",
    "blob_bytes",
    "content",
    "content_base64",
    "document_text",
    "file_name",
    "filename",
    "local_path",
    "ocr_text",
    "raw_bytes",
    "raw_content",
    "raw_file",
    "raw_filename",
    "source_file_path",
    "source_filename",
    "source_path",
    "stack_trace",
    "stderr",
    "stdout",
}


@dataclass(frozen=True)
class IngestJobStateError(ValueError):
    code: str
    details: dict[str, Any]

    def __str__(self) -> str:
        return self.code


def create_ingest_batch(
    connection: sqlite3.Connection,
    *,
    ingest_batch_id: str,
    tenant_id: str,
    domain_id: str,
    project_id: str,
    intake_ref: str,
    idempotency_key: str,
    request_fingerprint: str,
    status: str,
    descriptor_count: int,
    metadata_json: dict[str, Any],
    created_by_actor_id: str,
    created_by_actor_type: str,
    created_at: str,
) -> dict[str, Any]:
    _require_nonempty(ingest_batch_id, "ingest_batch_id")
    _require_project_scope(
        connection,
        tenant_id=tenant_id,
        domain_id=domain_id,
        project_id=project_id,
    )
    _validate_batch_status(status)
    _validate_sha256(request_fingerprint, "request_fingerprint")
    _validate_nonnegative(descriptor_count, "descriptor_count")
    _reject_raw_material(intake_ref, path="intake_ref")
    _reject_raw_material(metadata_json, path="metadata_json")
    connection.execute(
        """
        INSERT INTO capex_ingest_batches (
            ingest_batch_id,
            tenant_id,
            domain_id,
            project_id,
            intake_ref,
            idempotency_key,
            request_fingerprint,
            status,
            descriptor_count,
            metadata_json,
            created_by_actor_id,
            created_by_actor_type,
            created_at,
            updated_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            ingest_batch_id,
            tenant_id,
            domain_id,
            project_id,
            intake_ref,
            idempotency_key,
            request_fingerprint,
            status,
            descriptor_count,
            json.dumps(metadata_json, separators=(",", ":"), sort_keys=True),
            created_by_actor_id,
            created_by_actor_type,
            created_at,
            created_at,
        ),
    )
    row = get_ingest_batch(connection, ingest_batch_id)
    if row is None:
        raise RuntimeError("ingest batch insert failed")
    return row


def get_ingest_batch(
    connection: sqlite3.Connection,
    ingest_batch_id: str,
) -> dict[str, Any] | None:
    row = connection.execute(
        f"""
        SELECT {INGEST_BATCH_COLUMNS}
        FROM capex_ingest_batches
        WHERE ingest_batch_id = ?
        """,
        (ingest_batch_id,),
    ).fetchone()
    return _batch_row(row)


def transition_ingest_batch_status(
    connection: sqlite3.Connection,
    *,
    ingest_batch_id: str,
    status: str,
    updated_at: str,
) -> dict[str, Any]:
    _validate_batch_status(status)
    current = _require_batch(connection, ingest_batch_id)
    _reject_terminal_transition(
        current_status=current["status"],
        requested_status=status,
        terminal_statuses=TERMINAL_INGEST_BATCH_STATUSES,
        code="ingest_batch_terminal_status",
        details={"ingest_batch_id": ingest_batch_id},
    )
    connection.execute(
        """
        UPDATE capex_ingest_batches
        SET status = ?, updated_at = ?
        WHERE ingest_batch_id = ?
        """,
        (status, updated_at, ingest_batch_id),
    )
    return _require_batch(connection, ingest_batch_id)


def create_ingest_job(
    connection: sqlite3.Connection,
    *,
    ingest_job_id: str,
    ingest_batch_id: str,
    tenant_id: str,
    domain_id: str,
    project_id: str,
    job_kind: str,
    status: str,
    priority: int,
    idempotency_key: str,
    request_fingerprint: str,
    planned_task_refs_json: Sequence[str],
    planned_artifact_refs_json: Sequence[str],
    metadata_json: dict[str, Any],
    created_at: str,
    command_receipt_id: int | None = None,
) -> dict[str, Any]:
    _require_nonempty(ingest_job_id, "ingest_job_id")
    _require_batch_scope(
        connection,
        ingest_batch_id=ingest_batch_id,
        tenant_id=tenant_id,
        domain_id=domain_id,
        project_id=project_id,
    )
    _validate_job_kind(job_kind)
    _validate_job_status(status)
    _validate_nonnegative(priority, "priority")
    _validate_sha256(request_fingerprint, "request_fingerprint")
    _require_command_receipt(connection, command_receipt_id)
    planned_task_refs = _validate_ref_list(
        planned_task_refs_json,
        "planned_task_refs_json",
    )
    planned_artifact_refs = _validate_ref_list(
        planned_artifact_refs_json,
        "planned_artifact_refs_json",
    )
    _reject_raw_material(metadata_json, path="metadata_json")
    connection.execute(
        """
        INSERT INTO capex_ingest_jobs (
            ingest_job_id,
            ingest_batch_id,
            tenant_id,
            domain_id,
            project_id,
            job_kind,
            status,
            priority,
            idempotency_key,
            request_fingerprint,
            command_receipt_id,
            planned_task_refs_json,
            planned_artifact_refs_json,
            metadata_json,
            created_at,
            updated_at,
            terminal_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            ingest_job_id,
            ingest_batch_id,
            tenant_id,
            domain_id,
            project_id,
            job_kind,
            status,
            priority,
            idempotency_key,
            request_fingerprint,
            command_receipt_id,
            json.dumps(planned_task_refs, separators=(",", ":"), sort_keys=True),
            json.dumps(planned_artifact_refs, separators=(",", ":"), sort_keys=True),
            json.dumps(metadata_json, separators=(",", ":"), sort_keys=True),
            created_at,
            created_at,
            created_at if status in TERMINAL_INGEST_JOB_STATUSES else None,
        ),
    )
    row = get_ingest_job(connection, ingest_job_id)
    if row is None:
        raise RuntimeError("ingest job insert failed")
    return row


def get_ingest_job(
    connection: sqlite3.Connection,
    ingest_job_id: str,
) -> dict[str, Any] | None:
    row = connection.execute(
        f"""
        SELECT {INGEST_JOB_COLUMNS}
        FROM capex_ingest_jobs
        WHERE ingest_job_id = ?
        """,
        (ingest_job_id,),
    ).fetchone()
    return _job_row(row)


def transition_ingest_job_status(
    connection: sqlite3.Connection,
    *,
    ingest_job_id: str,
    status: str,
    updated_at: str,
) -> dict[str, Any]:
    _validate_job_status(status)
    current = _require_job(connection, ingest_job_id)
    _reject_terminal_transition(
        current_status=current["status"],
        requested_status=status,
        terminal_statuses=TERMINAL_INGEST_JOB_STATUSES,
        code="ingest_job_terminal_status",
        details={"ingest_job_id": ingest_job_id},
    )
    terminal_at = updated_at if status in TERMINAL_INGEST_JOB_STATUSES else None
    connection.execute(
        """
        UPDATE capex_ingest_jobs
        SET status = ?, updated_at = ?, terminal_at = ?
        WHERE ingest_job_id = ?
        """,
        (status, updated_at, terminal_at, ingest_job_id),
    )
    return _require_job(connection, ingest_job_id)


def create_ingest_attempt(
    connection: sqlite3.Connection,
    *,
    ingest_attempt_id: str,
    ingest_job_id: str,
    tenant_id: str,
    domain_id: str,
    project_id: str,
    attempt_no: int,
    status: str,
    metadata_json: dict[str, Any],
    created_at: str,
    execution_session_id: str | None = None,
    command_receipt_id: int | None = None,
    lease_token: str | None = None,
    started_at: str | None = None,
    completed_at: str | None = None,
    error_code: str | None = None,
) -> dict[str, Any]:
    _require_nonempty(ingest_attempt_id, "ingest_attempt_id")
    job = _require_job_scope(
        connection,
        ingest_job_id=ingest_job_id,
        tenant_id=tenant_id,
        domain_id=domain_id,
        project_id=project_id,
    )
    if job["status"] in TERMINAL_INGEST_JOB_STATUSES:
        raise IngestJobStateError(
            "ingest_attempt_job_terminal",
            {"ingest_job_id": ingest_job_id, "status": job["status"]},
        )
    _validate_attempt_status(status)
    _validate_attempt_number(connection, ingest_job_id=ingest_job_id, attempt_no=attempt_no)
    _require_execution_session(connection, execution_session_id)
    _require_command_receipt(connection, command_receipt_id)
    _reject_raw_material(metadata_json, path="metadata_json")
    if lease_token is not None:
        _reject_raw_material(lease_token, path="lease_token")
    if error_code is not None:
        _reject_raw_material(error_code, path="error_code")
    connection.execute(
        """
        INSERT INTO capex_ingest_attempts (
            ingest_attempt_id,
            ingest_job_id,
            tenant_id,
            domain_id,
            project_id,
            attempt_no,
            status,
            execution_session_id,
            command_receipt_id,
            lease_token,
            metadata_json,
            started_at,
            completed_at,
            error_code,
            created_at,
            updated_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            ingest_attempt_id,
            ingest_job_id,
            tenant_id,
            domain_id,
            project_id,
            attempt_no,
            status,
            execution_session_id,
            command_receipt_id,
            lease_token,
            json.dumps(metadata_json, separators=(",", ":"), sort_keys=True),
            started_at,
            completed_at,
            error_code,
            created_at,
            created_at,
        ),
    )
    row = get_ingest_attempt(connection, ingest_attempt_id)
    if row is None:
        raise RuntimeError("ingest attempt insert failed")
    return row


def get_ingest_attempt(
    connection: sqlite3.Connection,
    ingest_attempt_id: str,
) -> dict[str, Any] | None:
    row = connection.execute(
        f"""
        SELECT {INGEST_ATTEMPT_COLUMNS}
        FROM capex_ingest_attempts
        WHERE ingest_attempt_id = ?
        """,
        (ingest_attempt_id,),
    ).fetchone()
    return _attempt_row(row)


def transition_ingest_attempt_status(
    connection: sqlite3.Connection,
    *,
    ingest_attempt_id: str,
    status: str,
    updated_at: str,
    completed_at: str | None = None,
    error_code: str | None = None,
) -> dict[str, Any]:
    _validate_attempt_status(status)
    current = _require_attempt(connection, ingest_attempt_id)
    _reject_terminal_transition(
        current_status=current["status"],
        requested_status=status,
        terminal_statuses=TERMINAL_INGEST_ATTEMPT_STATUSES,
        code="ingest_attempt_terminal_status",
        details={"ingest_attempt_id": ingest_attempt_id},
    )
    if error_code is not None:
        _reject_raw_material(error_code, path="error_code")
    connection.execute(
        """
        UPDATE capex_ingest_attempts
        SET status = ?,
            updated_at = ?,
            completed_at = ?,
            error_code = ?
        WHERE ingest_attempt_id = ?
        """,
        (
            status,
            updated_at,
            completed_at if status in TERMINAL_INGEST_ATTEMPT_STATUSES else None,
            error_code,
            ingest_attempt_id,
        ),
    )
    return _require_attempt(connection, ingest_attempt_id)


def append_ingest_job_log(
    connection: sqlite3.Connection,
    *,
    ingest_job_log_id: str,
    ingest_job_id: str,
    tenant_id: str,
    domain_id: str,
    project_id: str,
    log_kind: str,
    severity: str,
    message_code: str,
    metadata_json: dict[str, Any],
    created_at: str,
    ingest_attempt_id: str | None = None,
    message_summary: str | None = None,
) -> dict[str, Any]:
    _require_nonempty(ingest_job_log_id, "ingest_job_log_id")
    _require_job_scope(
        connection,
        ingest_job_id=ingest_job_id,
        tenant_id=tenant_id,
        domain_id=domain_id,
        project_id=project_id,
    )
    if ingest_attempt_id is not None:
        _require_attempt_scope(
            connection,
            ingest_attempt_id=ingest_attempt_id,
            ingest_job_id=ingest_job_id,
            tenant_id=tenant_id,
            domain_id=domain_id,
            project_id=project_id,
        )
    _validate_log_kind(log_kind)
    _validate_log_severity(severity)
    _require_nonempty(message_code, "message_code")
    _reject_raw_material(message_code, path="message_code")
    _reject_raw_material(metadata_json, path="metadata_json")
    if message_summary is not None:
        _reject_raw_material(message_summary, path="message_summary")
    connection.execute(
        """
        INSERT INTO capex_ingest_job_logs (
            ingest_job_log_id,
            ingest_job_id,
            ingest_attempt_id,
            tenant_id,
            domain_id,
            project_id,
            log_kind,
            severity,
            message_code,
            message_summary,
            metadata_json,
            created_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            ingest_job_log_id,
            ingest_job_id,
            ingest_attempt_id,
            tenant_id,
            domain_id,
            project_id,
            log_kind,
            severity,
            message_code,
            message_summary,
            json.dumps(metadata_json, separators=(",", ":"), sort_keys=True),
            created_at,
        ),
    )
    row = get_ingest_job_log(connection, ingest_job_log_id)
    if row is None:
        raise RuntimeError("ingest job log insert failed")
    return row


def get_ingest_job_log(
    connection: sqlite3.Connection,
    ingest_job_log_id: str,
) -> dict[str, Any] | None:
    row = connection.execute(
        f"""
        SELECT {INGEST_JOB_LOG_COLUMNS}
        FROM capex_ingest_job_logs
        WHERE ingest_job_log_id = ?
        """,
        (ingest_job_log_id,),
    ).fetchone()
    return _log_row(row)


def list_ingest_job_logs(
    connection: sqlite3.Connection,
    *,
    ingest_job_id: str,
) -> list[dict[str, Any]]:
    rows = connection.execute(
        f"""
        SELECT {INGEST_JOB_LOG_COLUMNS}
        FROM capex_ingest_job_logs
        WHERE ingest_job_id = ?
        ORDER BY created_at ASC, ingest_job_log_id ASC
        """,
        (ingest_job_id,),
    ).fetchall()
    return [_log_row(row) for row in rows if row is not None]


def _require_project_scope(
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
        raise IngestJobStateError(
            "ingest_state_project_scope_mismatch",
            {
                "tenant_id": tenant_id,
                "domain_id": domain_id,
                "project_id": project_id,
            },
        )


def _require_batch_scope(
    connection: sqlite3.Connection,
    *,
    ingest_batch_id: str,
    tenant_id: str,
    domain_id: str,
    project_id: str,
) -> dict[str, Any]:
    batch = _require_batch(connection, ingest_batch_id)
    if (
        batch["tenant_id"] != tenant_id
        or batch["domain_id"] != domain_id
        or batch["project_id"] != project_id
    ):
        raise IngestJobStateError(
            "ingest_state_batch_scope_mismatch",
            {
                "ingest_batch_id": ingest_batch_id,
                "expected_scope": {
                    "tenant_id": tenant_id,
                    "domain_id": domain_id,
                    "project_id": project_id,
                },
                "actual_scope": {
                    "tenant_id": batch["tenant_id"],
                    "domain_id": batch["domain_id"],
                    "project_id": batch["project_id"],
                },
            },
        )
    return batch


def _require_job_scope(
    connection: sqlite3.Connection,
    *,
    ingest_job_id: str,
    tenant_id: str,
    domain_id: str,
    project_id: str,
) -> dict[str, Any]:
    job = _require_job(connection, ingest_job_id)
    if (
        job["tenant_id"] != tenant_id
        or job["domain_id"] != domain_id
        or job["project_id"] != project_id
    ):
        raise IngestJobStateError(
            "ingest_state_job_scope_mismatch",
            {
                "ingest_job_id": ingest_job_id,
                "expected_scope": {
                    "tenant_id": tenant_id,
                    "domain_id": domain_id,
                    "project_id": project_id,
                },
                "actual_scope": {
                    "tenant_id": job["tenant_id"],
                    "domain_id": job["domain_id"],
                    "project_id": job["project_id"],
                },
            },
        )
    return job


def _require_attempt_scope(
    connection: sqlite3.Connection,
    *,
    ingest_attempt_id: str,
    ingest_job_id: str,
    tenant_id: str,
    domain_id: str,
    project_id: str,
) -> dict[str, Any]:
    attempt = _require_attempt(connection, ingest_attempt_id)
    if (
        attempt["ingest_job_id"] != ingest_job_id
        or attempt["tenant_id"] != tenant_id
        or attempt["domain_id"] != domain_id
        or attempt["project_id"] != project_id
    ):
        raise IngestJobStateError(
            "ingest_state_attempt_scope_mismatch",
            {
                "ingest_attempt_id": ingest_attempt_id,
                "ingest_job_id": ingest_job_id,
            },
        )
    return attempt


def _require_batch(
    connection: sqlite3.Connection,
    ingest_batch_id: str,
) -> dict[str, Any]:
    batch = get_ingest_batch(connection, ingest_batch_id)
    if batch is None:
        raise IngestJobStateError(
            "ingest_batch_not_found",
            {"ingest_batch_id": ingest_batch_id},
        )
    return batch


def _require_job(
    connection: sqlite3.Connection,
    ingest_job_id: str,
) -> dict[str, Any]:
    job = get_ingest_job(connection, ingest_job_id)
    if job is None:
        raise IngestJobStateError(
            "ingest_job_not_found",
            {"ingest_job_id": ingest_job_id},
        )
    return job


def _require_attempt(
    connection: sqlite3.Connection,
    ingest_attempt_id: str,
) -> dict[str, Any]:
    attempt = get_ingest_attempt(connection, ingest_attempt_id)
    if attempt is None:
        raise IngestJobStateError(
            "ingest_attempt_not_found",
            {"ingest_attempt_id": ingest_attempt_id},
        )
    return attempt


def _require_command_receipt(
    connection: sqlite3.Connection,
    command_receipt_id: int | None,
) -> None:
    if command_receipt_id is None:
        return
    row = connection.execute(
        """
        SELECT command_receipt_id
        FROM command_receipts
        WHERE command_receipt_id = ?
        """,
        (command_receipt_id,),
    ).fetchone()
    if row is None:
        raise IngestJobStateError(
            "ingest_state_command_receipt_not_found",
            {"command_receipt_id": command_receipt_id},
        )


def _require_execution_session(
    connection: sqlite3.Connection,
    execution_session_id: str | None,
) -> None:
    if execution_session_id is None:
        return
    row = connection.execute(
        """
        SELECT execution_session_id
        FROM execution_sessions
        WHERE execution_session_id = ?
        """,
        (execution_session_id,),
    ).fetchone()
    if row is None:
        raise IngestJobStateError(
            "ingest_state_execution_session_not_found",
            {"execution_session_id": execution_session_id},
        )


def _validate_batch_status(status: str) -> None:
    if status not in INGEST_BATCH_STATUSES:
        raise IngestJobStateError("ingest_batch_status_invalid", {"status": status})


def _validate_job_kind(job_kind: str) -> None:
    if job_kind not in INGEST_JOB_KINDS:
        raise IngestJobStateError("ingest_job_kind_invalid", {"job_kind": job_kind})


def _validate_job_status(status: str) -> None:
    if status not in INGEST_JOB_STATUSES:
        raise IngestJobStateError("ingest_job_status_invalid", {"status": status})


def _validate_attempt_status(status: str) -> None:
    if status not in INGEST_ATTEMPT_STATUSES:
        raise IngestJobStateError("ingest_attempt_status_invalid", {"status": status})


def _validate_log_kind(log_kind: str) -> None:
    if log_kind not in INGEST_JOB_LOG_KINDS:
        raise IngestJobStateError("ingest_job_log_kind_invalid", {"log_kind": log_kind})


def _validate_log_severity(severity: str) -> None:
    if severity not in INGEST_JOB_LOG_SEVERITIES:
        raise IngestJobStateError(
            "ingest_job_log_severity_invalid",
            {"severity": severity},
        )


def _validate_sha256(value: str, field_name: str) -> None:
    if not _SHA256_RE.match(value):
        raise IngestJobStateError(
            "ingest_state_digest_invalid",
            {"field": field_name, "value": value},
        )


def _validate_nonnegative(value: int, field_name: str) -> None:
    if not isinstance(value, int) or value < 0:
        raise IngestJobStateError(
            "ingest_state_nonnegative_integer_required",
            {"field": field_name, "value": value},
        )


def _validate_attempt_number(
    connection: sqlite3.Connection,
    *,
    ingest_job_id: str,
    attempt_no: int,
) -> None:
    if not isinstance(attempt_no, int) or attempt_no < 1:
        raise IngestJobStateError(
            "ingest_attempt_number_invalid",
            {"attempt_no": attempt_no},
        )
    row = connection.execute(
        """
        SELECT MAX(attempt_no) AS max_attempt_no
        FROM capex_ingest_attempts
        WHERE ingest_job_id = ?
        """,
        (ingest_job_id,),
    ).fetchone()
    expected = 1 if row is None or row["max_attempt_no"] is None else int(row["max_attempt_no"]) + 1
    if attempt_no != expected:
        raise IngestJobStateError(
            "ingest_attempt_number_not_monotonic",
            {"attempt_no": attempt_no, "expected_attempt_no": expected},
        )


def _validate_ref_list(value: Sequence[str], field_name: str) -> list[str]:
    if isinstance(value, str) or not isinstance(value, Sequence):
        raise IngestJobStateError(
            "ingest_state_ref_list_required",
            {"field": field_name},
        )
    refs: list[str] = []
    seen: set[str] = set()
    for index, item in enumerate(value):
        if not isinstance(item, str) or not item.strip():
            raise IngestJobStateError(
                "ingest_state_ref_invalid",
                {"field": field_name, "index": index},
            )
        ref = item.strip()
        _reject_raw_material(ref, path=f"{field_name}[{index}]")
        if ref in seen:
            raise IngestJobStateError(
                "ingest_state_duplicate_ref",
                {"field": field_name, "ref": ref},
            )
        seen.add(ref)
        refs.append(ref)
    return refs


def _reject_terminal_transition(
    *,
    current_status: str,
    requested_status: str,
    terminal_statuses: frozenset[str],
    code: str,
    details: dict[str, Any],
) -> None:
    if current_status in terminal_statuses and current_status != requested_status:
        raise IngestJobStateError(
            code,
            {
                **details,
                "current_status": current_status,
                "requested_status": requested_status,
            },
        )


def _reject_raw_material(value: Any, *, path: str) -> None:
    if isinstance(value, Mapping):
        for raw_key, raw_value in value.items():
            key = str(raw_key)
            normalized_key = key.lower().replace("-", "_")
            if normalized_key in _FORBIDDEN_RAW_KEYS or normalized_key.startswith("raw_"):
                raise IngestJobStateError(
                    "ingest_state_raw_material_field_forbidden",
                    {"path": f"{path}.{key}", "field": key},
                )
            _reject_raw_material(raw_value, path=f"{path}.{key}")
        return
    if isinstance(value, list | tuple):
        for index, item in enumerate(value):
            _reject_raw_material(item, path=f"{path}[{index}]")
        return
    if isinstance(value, bytes | bytearray):
        raise IngestJobStateError("ingest_state_blob_bytes_forbidden", {"path": path})
    if isinstance(value, str):
        lowered = value.lower()
        if "base64," in lowered or lowered.startswith("data:"):
            raise IngestJobStateError(
                "ingest_state_inline_base64_forbidden",
                {"path": path},
            )
        if _ABSOLUTE_PATH_RE.match(value) or any(marker in value for marker in _RAW_PATH_MARKERS):
            raise IngestJobStateError(
                "ingest_state_raw_absolute_path_forbidden",
                {"path": path},
            )
        if _RAW_FILENAME_RE.match(value):
            raise IngestJobStateError(
                "ingest_state_raw_filename_forbidden",
                {"path": path},
            )


def _require_nonempty(value: Any, field_name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise IngestJobStateError(
            "ingest_state_required_field_missing",
            {"field": field_name},
        )
    return value.strip()


def _batch_row(row: sqlite3.Row | None) -> dict[str, Any] | None:
    if row is None:
        return None
    item = dict(row)
    item["metadata_json"] = json.loads(str(item["metadata_json"]))
    return item


def _job_row(row: sqlite3.Row | None) -> dict[str, Any] | None:
    if row is None:
        return None
    item = dict(row)
    item["planned_task_refs_json"] = json.loads(str(item["planned_task_refs_json"]))
    item["planned_artifact_refs_json"] = json.loads(
        str(item["planned_artifact_refs_json"])
    )
    item["metadata_json"] = json.loads(str(item["metadata_json"]))
    return item


def _attempt_row(row: sqlite3.Row | None) -> dict[str, Any] | None:
    if row is None:
        return None
    item = dict(row)
    item["metadata_json"] = json.loads(str(item["metadata_json"]))
    return item


def _log_row(row: sqlite3.Row | None) -> dict[str, Any] | None:
    if row is None:
        return None
    item = dict(row)
    item["metadata_json"] = json.loads(str(item["metadata_json"]))
    return item


__all__ = [
    "INGEST_ATTEMPT_STATUSES",
    "INGEST_BATCH_STATUSES",
    "INGEST_JOB_KINDS",
    "INGEST_JOB_LOG_KINDS",
    "INGEST_JOB_LOG_SEVERITIES",
    "INGEST_JOB_STATUSES",
    "IngestJobStateError",
    "append_ingest_job_log",
    "create_ingest_attempt",
    "create_ingest_batch",
    "create_ingest_job",
    "get_ingest_attempt",
    "get_ingest_batch",
    "get_ingest_job",
    "get_ingest_job_log",
    "list_ingest_job_logs",
    "transition_ingest_attempt_status",
    "transition_ingest_batch_status",
    "transition_ingest_job_status",
]
