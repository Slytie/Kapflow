from __future__ import annotations

import sqlite3

import pytest

from onetruth.infrastructure.events.event_store import create_sqlite_substrate
from onetruth.infrastructure.repositories.capex_ingest_jobs import (
    IngestJobStateError,
    append_ingest_job_log,
    create_ingest_attempt,
    create_ingest_batch,
    create_ingest_job,
    list_ingest_job_logs,
    transition_ingest_attempt_status,
    transition_ingest_batch_status,
    transition_ingest_job_status,
)
from onetruth.infrastructure.repositories.capex_projects import create_capex_project


TENANT_ID = "tenant-a"
DOMAIN_ID = "domain-x"
PROJECT_ID = "cp-alpha"
OTHER_PROJECT_ID = "cp-beta"
NOW = "2026-06-23T00:00:00Z"
SHA256_A = "sha256:" + ("a" * 64)
SHA256_B = "sha256:" + ("b" * 64)


def _connection() -> sqlite3.Connection:
    connection = sqlite3.connect(":memory:")
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON;")
    create_sqlite_substrate(connection)
    _project(connection, PROJECT_ID)
    return connection


def _project(connection: sqlite3.Connection, project_id: str) -> None:
    create_capex_project(
        connection,
        project_id=project_id,
        tenant_id=TENANT_ID,
        domain_id=DOMAIN_ID,
        project_key=project_id.upper(),
        name=project_id,
        state="active",
        metadata_json={},
        created_by_actor_id="human:admin",
        created_by_actor_type="human",
        created_at=NOW,
    )


def _batch(
    connection: sqlite3.Connection,
    *,
    ingest_batch_id: str = "ingest-batch-001",
    project_id: str = PROJECT_ID,
    request_fingerprint: str = SHA256_A,
    status: str = "planned",
    metadata_json: dict[str, object] | None = None,
) -> dict[str, object]:
    return create_ingest_batch(
        connection,
        ingest_batch_id=ingest_batch_id,
        tenant_id=TENANT_ID,
        domain_id=DOMAIN_ID,
        project_id=project_id,
        intake_ref="capex.bulk_ingest_adapter_seam.outputs.v1:adapter-request-001",
        idempotency_key=f"{ingest_batch_id}:idempotency",
        request_fingerprint=request_fingerprint,
        status=status,
        descriptor_count=2,
        metadata_json=metadata_json or {"fixture": "synthetic", "material_committed": False},
        created_by_actor_id="human:pm",
        created_by_actor_type="human",
        created_at=NOW,
    )


def _job(
    connection: sqlite3.Connection,
    *,
    ingest_job_id: str = "ingest-job-001",
    ingest_batch_id: str = "ingest-batch-001",
    project_id: str = PROJECT_ID,
    job_kind: str = "source_inventory",
    status: str = "queued",
    priority: int = 10,
    metadata_json: dict[str, object] | None = None,
) -> dict[str, object]:
    return create_ingest_job(
        connection,
        ingest_job_id=ingest_job_id,
        ingest_batch_id=ingest_batch_id,
        tenant_id=TENANT_ID,
        domain_id=DOMAIN_ID,
        project_id=project_id,
        job_kind=job_kind,
        status=status,
        priority=priority,
        idempotency_key=f"{ingest_job_id}:idempotency",
        request_fingerprint=SHA256_B,
        planned_task_refs_json=["task_run:planned-ingest-task"],
        planned_artifact_refs_json=["artifact_version:planned-ingest-artifact"],
        metadata_json=metadata_json or {"fixture": "synthetic", "material_committed": False},
        created_at=NOW,
    )


def _attempt(
    connection: sqlite3.Connection,
    *,
    ingest_attempt_id: str = "ingest-attempt-001",
    ingest_job_id: str = "ingest-job-001",
    attempt_no: int = 1,
    status: str = "queued",
    metadata_json: dict[str, object] | None = None,
) -> dict[str, object]:
    return create_ingest_attempt(
        connection,
        ingest_attempt_id=ingest_attempt_id,
        ingest_job_id=ingest_job_id,
        tenant_id=TENANT_ID,
        domain_id=DOMAIN_ID,
        project_id=PROJECT_ID,
        attempt_no=attempt_no,
        status=status,
        metadata_json=metadata_json or {"fixture": "synthetic", "material_committed": False},
        created_at=NOW,
    )


def test_ingest_job_state_records_batch_job_attempt_and_logs_without_side_effects() -> None:
    connection = _connection()
    try:
        before_artifacts = connection.execute(
            "SELECT COUNT(*) FROM artifact_versions"
        ).fetchone()[0]
        before_occurrences = connection.execute(
            "SELECT COUNT(*) FROM capex_source_occurrences"
        ).fetchone()[0]

        batch = _batch(connection)
        job = _job(connection)
        attempt = _attempt(connection)
        log = append_ingest_job_log(
            connection,
            ingest_job_log_id="ingest-log-001",
            ingest_job_id="ingest-job-001",
            ingest_attempt_id="ingest-attempt-001",
            tenant_id=TENANT_ID,
            domain_id=DOMAIN_ID,
            project_id=PROJECT_ID,
            log_kind="state_transition",
            severity="info",
            message_code="INGEST_ATTEMPT_QUEUED",
            message_summary="Attempt queued from sanitized planning state.",
            metadata_json={"attempt_no": 1},
            created_at=NOW,
        )

        assert batch["status"] == "planned"
        assert job["planned_task_refs_json"] == ["task_run:planned-ingest-task"]
        assert job["planned_artifact_refs_json"] == ["artifact_version:planned-ingest-artifact"]
        assert attempt["attempt_no"] == 1
        assert log["message_code"] == "INGEST_ATTEMPT_QUEUED"
        assert [row["ingest_job_log_id"] for row in list_ingest_job_logs(connection, ingest_job_id="ingest-job-001")] == [
            "ingest-log-001"
        ]
        assert connection.execute("SELECT COUNT(*) FROM artifact_versions").fetchone()[0] == (
            before_artifacts
        )
        assert connection.execute(
            "SELECT COUNT(*) FROM capex_source_occurrences"
        ).fetchone()[0] == before_occurrences
    finally:
        connection.close()


def test_ingest_job_state_rejects_bad_statuses_digests_duplicates_and_scope_mismatch() -> None:
    connection = _connection()
    try:
        _batch(connection)

        with pytest.raises(IngestJobStateError) as digest_exc:
            _batch(
                connection,
                ingest_batch_id="ingest-batch-bad-digest",
                request_fingerprint="not-a-sha",
            )
        assert digest_exc.value.code == "ingest_state_digest_invalid"

        with pytest.raises(sqlite3.IntegrityError):
            _batch(connection, ingest_batch_id="ingest-batch-001")

        with pytest.raises(IngestJobStateError) as kind_exc:
            _job(connection, ingest_job_id="ingest-job-bad-kind", job_kind="worker_runtime")
        assert kind_exc.value.code == "ingest_job_kind_invalid"

        _project(connection, OTHER_PROJECT_ID)
        with pytest.raises(IngestJobStateError) as scope_exc:
            _job(
                connection,
                ingest_job_id="ingest-job-cross-project",
                project_id=OTHER_PROJECT_ID,
            )
        assert scope_exc.value.code == "ingest_state_batch_scope_mismatch"
    finally:
        connection.close()


def test_ingest_attempt_numbers_are_monotonic_and_terminal_states_do_not_reopen() -> None:
    connection = _connection()
    try:
        _batch(connection)
        _job(connection)

        with pytest.raises(IngestJobStateError) as first_attempt_exc:
            _attempt(connection, ingest_attempt_id="ingest-attempt-002", attempt_no=2)
        assert first_attempt_exc.value.code == "ingest_attempt_number_not_monotonic"

        _attempt(connection)
        with pytest.raises(IngestJobStateError) as duplicate_attempt_exc:
            _attempt(connection, ingest_attempt_id="ingest-attempt-dup", attempt_no=1)
        assert duplicate_attempt_exc.value.code == "ingest_attempt_number_not_monotonic"

        transition_ingest_attempt_status(
            connection,
            ingest_attempt_id="ingest-attempt-001",
            status="failed",
            updated_at="2026-06-23T00:05:00Z",
            completed_at="2026-06-23T00:05:00Z",
            error_code="SANITIZED_VALIDATION_FAILURE",
        )
        with pytest.raises(IngestJobStateError) as terminal_attempt_exc:
            transition_ingest_attempt_status(
                connection,
                ingest_attempt_id="ingest-attempt-001",
                status="running",
                updated_at="2026-06-23T00:06:00Z",
            )
        assert terminal_attempt_exc.value.code == "ingest_attempt_terminal_status"

        transition_ingest_job_status(
            connection,
            ingest_job_id="ingest-job-001",
            status="succeeded",
            updated_at="2026-06-23T00:07:00Z",
        )
        with pytest.raises(IngestJobStateError) as terminal_job_exc:
            transition_ingest_job_status(
                connection,
                ingest_job_id="ingest-job-001",
                status="running",
                updated_at="2026-06-23T00:08:00Z",
            )
        assert terminal_job_exc.value.code == "ingest_job_terminal_status"

        transition_ingest_batch_status(
            connection,
            ingest_batch_id="ingest-batch-001",
            status="canceled",
            updated_at="2026-06-23T00:09:00Z",
        )
        with pytest.raises(IngestJobStateError) as terminal_batch_exc:
            transition_ingest_batch_status(
                connection,
                ingest_batch_id="ingest-batch-001",
                status="processing",
                updated_at="2026-06-23T00:10:00Z",
            )
        assert terminal_batch_exc.value.code == "ingest_batch_terminal_status"
    finally:
        connection.close()


def test_ingest_job_state_rejects_raw_material_in_metadata_refs_and_logs() -> None:
    connection = _connection()
    try:
        raw_batch_cases = [
            {"metadata_json": {"source_path": "/Users/pm/client.pdf"}},
            {"metadata_json": {"preview": "data:application/pdf;base64,AAAA"}},
        ]
        for index, kwargs in enumerate(raw_batch_cases, start=1):
            with pytest.raises(IngestJobStateError):
                _batch(connection, ingest_batch_id=f"ingest-batch-raw-{index}", **kwargs)

        _batch(connection)
        with pytest.raises(IngestJobStateError) as raw_ref_exc:
            create_ingest_job(
                connection,
                ingest_job_id="ingest-job-raw-ref",
                ingest_batch_id="ingest-batch-001",
                tenant_id=TENANT_ID,
                domain_id=DOMAIN_ID,
                project_id=PROJECT_ID,
                job_kind="source_inventory",
                status="queued",
                priority=0,
                idempotency_key="ingest-job-raw-ref:idempotency",
                request_fingerprint=SHA256_B,
                planned_task_refs_json=["client-source.pdf"],
                planned_artifact_refs_json=[],
                metadata_json={},
                created_at=NOW,
            )
        assert raw_ref_exc.value.code == "ingest_state_raw_filename_forbidden"

        _job(connection)
        with pytest.raises(IngestJobStateError) as raw_log_exc:
            append_ingest_job_log(
                connection,
                ingest_job_log_id="ingest-log-raw",
                ingest_job_id="ingest-job-001",
                tenant_id=TENANT_ID,
                domain_id=DOMAIN_ID,
                project_id=PROJECT_ID,
                log_kind="failure",
                severity="error",
                message_code="FAILURE",
                message_summary="/Users/pm/client/source.pdf",
                metadata_json={},
                created_at=NOW,
            )
        assert raw_log_exc.value.code == "ingest_state_raw_absolute_path_forbidden"
    finally:
        connection.close()
