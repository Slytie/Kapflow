from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sys

import pytest

from onetruth.infrastructure.db.session import open_sqlite_connection
from onetruth.infrastructure.repositories.input_bindings import (
    InputBindingConflictError,
    capture_task_pointer_input,
    is_task_input_binding_stale,
)


REPO_ROOT = Path(__file__).resolve().parents[2]
SRC_ROOT = REPO_ROOT / "src"


def _run_cli(*args: str, expect_ok: bool = True) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    existing_pythonpath = env.get("PYTHONPATH")
    if existing_pythonpath:
        env["PYTHONPATH"] = f"{SRC_ROOT}{os.pathsep}{existing_pythonpath}"
    else:
        env["PYTHONPATH"] = str(SRC_ROOT)

    result = subprocess.run(
        [sys.executable, "-m", "onetruth.cli", *args],
        cwd=REPO_ROOT,
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )
    if expect_ok and result.returncode != 0:
        pytest.fail(
            f"CLI failed ({result.returncode})\nSTDOUT: {result.stdout}\nSTDERR: {result.stderr}"
        )
    return result


def _stdout_json(result: subprocess.CompletedProcess[str]) -> dict[str, object]:
    assert result.stdout
    payload = json.loads(result.stdout)
    assert isinstance(payload, dict)
    return payload


def _create_workflow_run(db_url: str) -> str:
    payload = {
        "workflow_id": "schedule_planning.v1",
        "workflow_version": "v1",
        "tenant_id": "tenant-a",
        "domain_id": "domain-ops",
        "partition_key": "SD-2026-03-04",
        "logical_date": "2026-03-04",
        "activation_key": "run-activation-001",
        "idempotency_key": "idem-run-001",
    }
    result = _run_cli("--db-url", db_url, "runs", "create", "--json", json.dumps(payload))
    return str(_stdout_json(result)["workflow_run"]["workflow_run_id"])


def _create_task_run(db_url: str, workflow_run_id: str) -> str:
    payload = {
        "workflow_run_id": workflow_run_id,
        "stage_id": "Stage06",
        "task_kind": "review_packet",
        "activation_key": "task-activation-001",
        "candidate_roles": ["dispatch_supervisor"],
        "owner_role": "dispatch_supervisor",
        "create_human_task": False,
        "idempotency_key": "idem-task-001",
    }
    result = _run_cli("--db-url", db_url, "tasks", "create", "--json", json.dumps(payload))
    return str(_stdout_json(result)["result"]["task_run"]["task_run_id"])


def _create_artifact(
    db_url: str,
    *,
    workflow_run_id: str,
    task_run_id: str,
    artifact_version_id: str,
    idempotency_key: str,
) -> None:
    payload = {
        "artifact_version_id": artifact_version_id,
        "workflow_run_id": workflow_run_id,
        "task_run_id": task_run_id,
        "artifact_kind": "schedule.published_schedule.workbook",
        "artifact_role": "official_output",
        "media_type": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        "storage_uri": f"s3://runtime/{artifact_version_id}.xlsx",
        "content_digest": f"sha256:{artifact_version_id}",
        "byte_size": 512,
        "metadata_json": {"seed": artifact_version_id},
        "idempotency_key": idempotency_key,
    }
    _run_cli("--db-url", db_url, "artifacts", "create-version", "--json", json.dumps(payload))


def _promote_pointer(
    db_url: str,
    *,
    workflow_run_id: str,
    task_run_id: str,
    artifact_version_id: str,
    idempotency_key: str,
    expected_generation: int | None,
) -> None:
    payload = {
        "workflow_run_id": workflow_run_id,
        "scope_kind": "stage",
        "scope_ref": "Stage06",
        "pointer_key": "official:schedule.published_schedule.workbook",
        "artifact_kind": "schedule.published_schedule.workbook",
        "artifact_version_id": artifact_version_id,
        "promoted_by_task_run_id": task_run_id,
        "promotion_reason": "strategy_a_snapshot_test",
        "actor_type": "service",
        "actor_id": "service:strategy-a-tests",
        "idempotency_key": idempotency_key,
    }
    if expected_generation is not None:
        payload["expected_generation"] = expected_generation
    _run_cli("--db-url", db_url, "pointers", "promote", "--json", json.dumps(payload))


def test_runtime_can_capture_exact_pointer_binding_and_detect_stale_baseline(
    tmp_path: Path,
) -> None:
    db_url = f"sqlite:///{tmp_path / 'runtime.db'}"
    _run_cli("--db-url", db_url, "init-db")

    workflow_run_id = _create_workflow_run(db_url)
    task_run_id = _create_task_run(db_url, workflow_run_id)
    _create_artifact(
        db_url,
        workflow_run_id=workflow_run_id,
        task_run_id=task_run_id,
        artifact_version_id="av-001",
        idempotency_key="idem-av-001",
    )
    _create_artifact(
        db_url,
        workflow_run_id=workflow_run_id,
        task_run_id=task_run_id,
        artifact_version_id="av-002",
        idempotency_key="idem-av-002",
    )

    _promote_pointer(
        db_url,
        workflow_run_id=workflow_run_id,
        task_run_id=task_run_id,
        artifact_version_id="av-001",
        idempotency_key="idem-promote-001",
        expected_generation=None,
    )

    connection = open_sqlite_connection(db_url)
    try:
        capture_task_pointer_input(
            connection,
            task_run_id=task_run_id,
            workflow_run_id=workflow_run_id,
            binding_key="reviewed_base_pointer",
            pointer_key="official:schedule.published_schedule.workbook",
            captured_at="2026-03-07T10:15:00Z",
        )
        connection.commit()

        with pytest.raises(InputBindingConflictError):
            capture_task_pointer_input(
                connection,
                task_run_id=task_run_id,
                workflow_run_id=workflow_run_id,
                binding_key="reviewed_base_pointer",
                pointer_key="official:schedule.published_schedule.workbook",
                captured_at="2026-03-07T10:15:01Z",
            )

        assert not is_task_input_binding_stale(
            connection,
            task_run_id=task_run_id,
            binding_key="reviewed_base_pointer",
        )
    finally:
        connection.close()

    _promote_pointer(
        db_url,
        workflow_run_id=workflow_run_id,
        task_run_id=task_run_id,
        artifact_version_id="av-002",
        idempotency_key="idem-promote-002",
        expected_generation=0,
    )

    connection = open_sqlite_connection(db_url)
    try:
        assert is_task_input_binding_stale(
            connection,
            task_run_id=task_run_id,
            binding_key="reviewed_base_pointer",
        )
    finally:
        connection.close()
