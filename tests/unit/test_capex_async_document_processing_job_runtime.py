from __future__ import annotations

import hashlib
import json

import pytest

from onetruth.capex_platform.async_document_processing_job_runtime import (
    ASYNC_DOCUMENT_PROCESSING_JOB_RUNTIME_ACTIVATION_POSTURE,
    ASYNC_DOCUMENT_PROCESSING_JOB_RUNTIME_OUTPUTS_SCHEMA_VERSION,
    DOCUMENT_PROCESSING_JOB_ATTEMPT_REGISTER_SCHEMA_VERSION,
    DOCUMENT_PROCESSING_JOB_PROGRESS_SCHEMA_VERSION,
    DOCUMENT_PROCESSING_JOB_REGISTER_SCHEMA_VERSION,
    AsyncDocumentProcessingJobRuntimeError,
    async_document_processing_job_runtime_digest,
    build_async_document_processing_job_runtime_outputs,
)


NOW = "2026-06-23T00:00:00Z"


def _digest(value: object) -> str:
    return "sha256:" + hashlib.sha256(
        json.dumps(
            value,
            separators=(",", ":"),
            sort_keys=True,
            ensure_ascii=True,
            allow_nan=False,
        ).encode("utf-8")
    ).hexdigest()


def _idempotency_key(
    *,
    job_id: str,
    job_kind: str,
    document_ids: list[str],
) -> str:
    seed = _digest(
        {
            "tenant_id": "tenant-a",
            "domain_id": "domain-x",
            "project_id": "cp-async",
            "job_id": job_id,
            "job_kind": job_kind,
            "document_ids": sorted(document_ids),
        }
    ).removeprefix("sha256:")
    return f"capex-doc-processing:{seed}"


def _receipt(job_id: str, job_kind: str, document_ids: list[str]) -> dict[str, str]:
    return {
        "command_name": "capex.document_processing.plan",
        "scope_key": f"tenant-a:domain-x:cp-async:{job_id}",
        "idempotency_key": _idempotency_key(
            job_id=job_id,
            job_kind=job_kind,
            document_ids=document_ids,
        ),
        "request_fingerprint": _digest({"job_id": job_id, "job_kind": job_kind}),
    }


def _document_manifest_outputs() -> dict[str, object]:
    rows = [
        {
            "document_id": "doc-001",
            "descriptor_id": "descriptor-001",
            "storage_ref": "object://capex/doc-001",
            "content_digest": _digest({"document": "doc-001"}),
            "source_refs": ["source_occurrence:so-doc-001"],
        },
        {
            "document_id": "doc-002",
            "descriptor_id": "descriptor-002",
            "storage_ref": "object://capex/doc-002",
            "content_digest": _digest({"document": "doc-002"}),
            "source_refs": ["source_occurrence:so-doc-002"],
        },
    ]
    return {
        "schema_version": "capex.document_manifest.outputs.v1",
        "activation_posture": "planning_only_no_capex_activation",
        "document_manifest": {
            "schema_version": "capex.document_manifest.v1",
            "manifest_id": "document-manifest-async-001",
            "tenant_id": "tenant-a",
            "domain_id": "domain-x",
            "project_id": "cp-async",
            "rows": rows,
            "snapshot_digest": _digest(rows),
        },
        "extraction_state_register": {
            "schema_version": "capex.extraction_state_register.v1",
            "register_id": "document-manifest-async-001:extraction-state",
        },
    }


def _job_rows() -> list[dict[str, object]]:
    return [
        {
            "job_id": "job-text-extraction",
            "job_kind": "text_extraction",
            "job_state": "retry_pending",
            "document_ids": ["doc-001", "doc-002"],
            "source_refs": [
                "source_occurrence:so-doc-001",
                "source_occurrence:so-doc-002",
            ],
            "command_receipt": _receipt(
                "job-text-extraction",
                "text_extraction",
                ["doc-001", "doc-002"],
            ),
            "execution_session_ref": "execution_session:session-text-extraction",
            "planned_task_refs": ["planned_task:runtime-001:job-text-extraction"],
            "planned_artifact_refs": [
                "planned_artifact:runtime-001:job-text-extraction:outputs"
            ],
            "job_manifest_storage_ref": "object://capex/jobs/job-text-extraction",
        }
    ]


def _attempt_rows() -> list[dict[str, object]]:
    receipt = _receipt("job-text-extraction", "text_extraction", ["doc-001", "doc-002"])
    return [
        {
            "attempt_id": "attempt-001",
            "job_id": "job-text-extraction",
            "attempt_no": 1,
            "attempt_state": "failed",
            "command_receipt": receipt,
            "planned_task_refs": ["planned_task:runtime-001:job-text-extraction"],
            "planned_artifact_refs": [
                "planned_artifact:runtime-001:job-text-extraction:outputs"
            ],
        },
        {
            "attempt_id": "attempt-002",
            "job_id": "job-text-extraction",
            "attempt_no": 2,
            "attempt_state": "failed",
            "command_receipt": receipt,
            "planned_task_refs": ["planned_task:runtime-001:job-text-extraction"],
            "planned_artifact_refs": [
                "planned_artifact:runtime-001:job-text-extraction:outputs"
            ],
        },
    ]


def _progress_rows() -> list[dict[str, object]]:
    return [
        {
            "progress_id": "progress-001",
            "job_id": "job-text-extraction",
            "documents_total": 2,
            "documents_processed": 1,
            "documents_failed": 1,
            "source_refs": ["source_occurrence:so-doc-001"],
        }
    ]


def _outputs(**overrides: object) -> dict[str, object]:
    payload: dict[str, object] = {
        "document_manifest_outputs": _document_manifest_outputs(),
        "job_rows": _job_rows(),
        "attempt_rows": _attempt_rows(),
        "progress_rows": _progress_rows(),
        "runtime_id": "runtime-001",
        "created_at": NOW,
        "created_by_actor_id": "human:pm",
        "created_by_actor_type": "human",
    }
    payload.update(overrides)
    return build_async_document_processing_job_runtime_outputs(**payload)  # type: ignore[arg-type]


def test_builds_deterministic_async_job_runtime_outputs() -> None:
    first = _outputs()
    second = _outputs(attempt_rows=list(reversed(_attempt_rows())))

    assert first == second
    assert first["schema_version"] == ASYNC_DOCUMENT_PROCESSING_JOB_RUNTIME_OUTPUTS_SCHEMA_VERSION
    assert first["activation_posture"] == ASYNC_DOCUMENT_PROCESSING_JOB_RUNTIME_ACTIVATION_POSTURE
    assert first["tenant_id"] == "tenant-a"
    assert first["domain_id"] == "domain-x"
    assert first["project_id"] == "cp-async"
    assert first["document_processing_job_register"]["schema_version"] == (
        DOCUMENT_PROCESSING_JOB_REGISTER_SCHEMA_VERSION
    )
    assert first["document_processing_job_attempt_register"]["schema_version"] == (
        DOCUMENT_PROCESSING_JOB_ATTEMPT_REGISTER_SCHEMA_VERSION
    )
    assert first["document_processing_job_progress"]["schema_version"] == (
        DOCUMENT_PROCESSING_JOB_PROGRESS_SCHEMA_VERSION
    )
    assert async_document_processing_job_runtime_digest(first).startswith("sha256:")


def test_retry_reuses_planned_task_and_artifact_refs_without_runtime_effects() -> None:
    outputs = _outputs()
    job = outputs["document_processing_job_register"]["rows"][0]  # type: ignore[index]
    attempts = outputs["document_processing_job_attempt_register"]["rows"]  # type: ignore[index]

    assert [row["planned_task_refs"] for row in attempts] == [
        job["planned_task_refs"],
        job["planned_task_refs"],
    ]
    assert [row["planned_artifact_refs"] for row in attempts] == [
        job["planned_artifact_refs"],
        job["planned_artifact_refs"],
    ]
    assert outputs["truth_effects"] == {
        "creates_extraction_jobs": False,
        "creates_execution_sessions": False,
        "creates_command_receipts": False,
        "starts_workers": False,
        "runs_parser_adapter": False,
        "writes_artifacts": False,
        "promotes_official_pointers": False,
        "activates_workflow_pack": False,
    }


def test_unknown_document_source_and_duplicate_ids_are_rejected() -> None:
    jobs = _job_rows()
    jobs[0]["document_ids"] = ["doc-001", "doc-missing"]
    with pytest.raises(AsyncDocumentProcessingJobRuntimeError) as unknown_doc:
        _outputs(job_rows=jobs)
    assert unknown_doc.value.code == "async_job_unknown_document_id"

    jobs = _job_rows()
    jobs[0]["source_refs"] = ["source_occurrence:so-missing"]
    with pytest.raises(AsyncDocumentProcessingJobRuntimeError) as unknown_source:
        _outputs(job_rows=jobs)
    assert unknown_source.value.code == "async_job_source_ref_not_in_document_manifest"

    duplicate = _job_rows() + _job_rows()
    with pytest.raises(AsyncDocumentProcessingJobRuntimeError) as duplicate_error:
        _outputs(job_rows=duplicate)
    assert duplicate_error.value.code == "async_job_duplicate_job_id"


def test_bad_spans_digests_receipts_and_progress_fail_closed() -> None:
    bad_manifest = _document_manifest_outputs()
    bad_manifest["document_manifest"]["snapshot_digest"] = "sha256:not-a-digest"  # type: ignore[index]
    with pytest.raises(AsyncDocumentProcessingJobRuntimeError) as bad_digest:
        _outputs(document_manifest_outputs=bad_manifest)
    assert bad_digest.value.code == "async_job_sha256_digest_invalid"

    jobs = _job_rows()
    jobs[0]["command_receipt"] = {
        **jobs[0]["command_receipt"],  # type: ignore[arg-type]
        "request_fingerprint": "sha256:not-a-digest",
    }
    with pytest.raises(AsyncDocumentProcessingJobRuntimeError) as bad_receipt:
        _outputs(job_rows=jobs)
    assert bad_receipt.value.code == "async_job_sha256_digest_invalid"

    progress = _progress_rows()
    progress[0]["documents_processed"] = 2
    progress[0]["documents_failed"] = 1
    with pytest.raises(AsyncDocumentProcessingJobRuntimeError) as bad_progress:
        _outputs(progress_rows=progress)
    assert bad_progress.value.code == "async_job_progress_counts_invalid"


def test_attempt_transition_guards_reject_cancel_retry_and_bad_order() -> None:
    attempts = _attempt_rows()
    attempts[0]["attempt_state"] = "canceled"
    with pytest.raises(AsyncDocumentProcessingJobRuntimeError) as canceled_retry:
        _outputs(attempt_rows=attempts)
    assert canceled_retry.value.code == "async_job_retry_after_terminal_attempt"

    attempts = _attempt_rows()
    attempts[1]["attempt_no"] = 3
    with pytest.raises(AsyncDocumentProcessingJobRuntimeError) as bad_sequence:
        _outputs(attempt_rows=attempts)
    assert bad_sequence.value.code == "async_job_attempt_sequence_not_monotonic"

    jobs = _job_rows()
    jobs[0]["job_state"] = "canceled"
    with pytest.raises(AsyncDocumentProcessingJobRuntimeError) as bad_terminal:
        _outputs(job_rows=jobs)
    assert bad_terminal.value.code == "async_job_canceled_requires_canceled_attempt"


def test_attempt_refs_and_idempotency_keys_must_stay_stable() -> None:
    attempts = _attempt_rows()
    attempts[1]["planned_task_refs"] = ["planned_task:runtime-001:other"]
    with pytest.raises(AsyncDocumentProcessingJobRuntimeError) as task_ref:
        _outputs(attempt_rows=attempts)
    assert task_ref.value.code == "async_job_attempt_task_refs_not_stable"

    attempts = _attempt_rows()
    receipt = dict(attempts[1]["command_receipt"])  # type: ignore[arg-type]
    receipt["idempotency_key"] = "manual-retry-key"
    attempts[1]["command_receipt"] = receipt
    with pytest.raises(AsyncDocumentProcessingJobRuntimeError) as idempotency:
        _outputs(attempt_rows=attempts)
    assert idempotency.value.code == "async_job_attempt_idempotency_key_mismatch"


def test_raw_content_and_paths_are_rejected() -> None:
    jobs = _job_rows()
    jobs[0]["raw_log"] = "secret.pdf"

    with pytest.raises(AsyncDocumentProcessingJobRuntimeError) as exc:
        _outputs(job_rows=jobs)

    assert exc.value.code == "async_job_raw_material_rejected"
