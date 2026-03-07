from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
import json
import os
from pathlib import Path
import sqlite3
import subprocess
import sys
from typing import Any

import pytest

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


def _stdout_json(result: subprocess.CompletedProcess[str]) -> Any:
    assert result.stdout
    return json.loads(result.stdout)


def _stderr_json(result: subprocess.CompletedProcess[str]) -> Any:
    assert result.stderr
    return json.loads(result.stderr)


def _query_rows(
    db_url: str,
    sql: str,
    params: tuple[Any, ...] = (),
) -> list[dict[str, Any]]:
    assert db_url.startswith("sqlite:///")
    db_path = db_url.removeprefix("sqlite:///")
    connection = sqlite3.connect(db_path)
    connection.row_factory = sqlite3.Row
    try:
        rows = connection.execute(sql, params).fetchall()
        return [dict(row) for row in rows]
    finally:
        connection.close()


def _events_for_run(db_url: str, workflow_run_id: str) -> list[dict[str, Any]]:
    result = _run_cli(
        "--db-url",
        db_url,
        "events",
        "list",
        "--run-id",
        workflow_run_id,
        "--json",
    )
    payload = _stdout_json(result)
    assert isinstance(payload, list)
    return payload


def _create_workflow_run(
    db_url: str,
    *,
    activation_key: str = "run-act-001",
    tenant_id: str = "tenant-a",
    domain_id: str = "domain-x",
    partition_key: str = "SD-2026-03-04",
    logical_date: str = "2026-03-04",
) -> dict[str, Any]:
    payload = {
        "workflow_id": "schedule_planning.v1",
        "workflow_version": "v1",
        "tenant_id": tenant_id,
        "domain_id": domain_id,
        "partition_key": partition_key,
        "logical_date": logical_date,
        "activation_key": activation_key,
        "idempotency_key": f"idem-run-{tenant_id}-{domain_id}-{activation_key}",
    }
    result = _run_cli("--db-url", db_url, "runs", "create", "--json", json.dumps(payload))
    parsed = _stdout_json(result)
    assert parsed["status"] == "ok"
    return parsed["workflow_run"]


def _create_task_run(
    db_url: str,
    *,
    workflow_run_id: str,
    activation_key: str = "task-act-001",
    create_human_task: bool = False,
) -> dict[str, Any]:
    payload = {
        "workflow_run_id": workflow_run_id,
        "stage_id": "Stage06",
        "task_kind": "final_review",
        "activation_key": activation_key,
        "candidate_roles": ["dispatch_supervisor"],
        "owner_role": "dispatch_supervisor",
        "create_human_task": create_human_task,
        "idempotency_key": f"idem-task-{activation_key}",
    }
    result = _run_cli("--db-url", db_url, "tasks", "create", "--json", json.dumps(payload))
    parsed = _stdout_json(result)
    assert parsed["status"] == "ok"
    return parsed["result"]


def _request_approval(
    db_url: str,
    *,
    workflow_run_id: str,
    task_run_id: str | None,
    idempotency_key: str,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "workflow_run_id": workflow_run_id,
        "approval_kind": "business_decision",
        "scope_kind": "stage",
        "scope_ref": "Stage06",
        "candidate_roles": ["dispatch_supervisor"],
        "required_role": "dispatch_supervisor",
        "action": "publish_schedule",
        "idempotency_key": idempotency_key,
    }
    if task_run_id is not None:
        payload["task_run_id"] = task_run_id
    result = _run_cli("--db-url", db_url, "approvals", "request", "--json", json.dumps(payload))
    parsed = _stdout_json(result)
    assert parsed["status"] == "ok"
    return parsed["approval"]


def _create_artifact_version(
    db_url: str,
    *,
    workflow_run_id: str,
    task_run_id: str | None,
    artifact_kind: str,
    idempotency_key: str,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "workflow_run_id": workflow_run_id,
        "artifact_kind": artifact_kind,
        "artifact_role": "official_output",
        "media_type": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        "storage_uri": f"s3://runtime/{artifact_kind}/{idempotency_key}.xlsx",
        "content_digest": f"sha256:{idempotency_key}",
        "byte_size": 1024,
        "metadata_json": {
            "source": "runtime-test",
            "idempotency_key": idempotency_key,
            "dataset": artifact_kind,
        },
        "idempotency_key": idempotency_key,
    }
    if task_run_id is not None:
        payload["task_run_id"] = task_run_id
    result = _run_cli(
        "--db-url",
        db_url,
        "artifacts",
        "create-version",
        "--json",
        json.dumps(payload),
    )
    parsed = _stdout_json(result)
    assert parsed["status"] == "ok"
    return parsed["artifact_version"]


def test_approval_request_happy_path_persists_row_and_emits_event(tmp_path: Path) -> None:
    db_url = f"sqlite:///{tmp_path / 'runtime.db'}"
    _run_cli("--db-url", db_url, "init-db")

    workflow_run = _create_workflow_run(db_url)
    listed_runs = _stdout_json(
        _run_cli(
            "--db-url",
            db_url,
            "runs",
            "list",
            "--workflow-id",
            "schedule_planning.v1",
            "--json",
        )
    )["workflow_runs"]
    assert any(item["workflow_run_id"] == workflow_run["workflow_run_id"] for item in listed_runs)

    task_run = _create_task_run(db_url, workflow_run_id=workflow_run["workflow_run_id"])["task_run"]
    approval = _request_approval(
        db_url,
        workflow_run_id=workflow_run["workflow_run_id"],
        task_run_id=task_run["task_run_id"],
        idempotency_key="idem-approval-request-001",
    )

    assert approval["state"] == "PENDING"
    assert approval["workflow_run_id"] == workflow_run["workflow_run_id"]
    assert approval["task_run_id"] == task_run["task_run_id"]

    shown = _stdout_json(
        _run_cli(
            "--db-url",
            db_url,
            "approvals",
            "show",
            "--approval-id",
            approval["approval_id"],
            "--json",
        )
    )["approval"]
    assert shown["scope_kind"] == "stage"
    assert shown["scope_ref"] == "Stage06"
    assert shown["candidate_roles"] == ["dispatch_supervisor"]

    events = _events_for_run(db_url, workflow_run["workflow_run_id"])
    requested = [event for event in events if event["event_type"] == "approval.requested"]
    assert len(requested) == 1
    assert requested[0]["payload"]["approval_id"] == approval["approval_id"]
    assert requested[0]["payload"]["action"] == "publish_schedule"


def test_approval_respond_happy_path_transitions_state_and_emits_event(tmp_path: Path) -> None:
    db_url = f"sqlite:///{tmp_path / 'runtime.db'}"
    _run_cli("--db-url", db_url, "init-db")

    workflow_run = _create_workflow_run(db_url)
    approval = _request_approval(
        db_url,
        workflow_run_id=workflow_run["workflow_run_id"],
        task_run_id=None,
        idempotency_key="idem-approval-request-respond-001",
    )

    respond_payload = {
        "approval_id": approval["approval_id"],
        "actor_id": "human:supervisor-1",
        "actor_type": "human",
        "response_kind": "approve",
        "response_reason": "review complete",
        "idempotency_key": "idem-approval-respond-001",
    }
    respond_result = _run_cli(
        "--db-url",
        db_url,
        "approvals",
        "respond",
        "--json",
        json.dumps(respond_payload),
    )
    responded = _stdout_json(respond_result)["approval"]
    assert responded["state"] == "RESPONDED"
    assert responded["response_kind"] == "approve"
    assert responded["decided_by_actor_id"] == "human:supervisor-1"

    events = _events_for_run(db_url, workflow_run["workflow_run_id"])
    responded_events = [event for event in events if event["event_type"] == "approval.responded"]
    assert len(responded_events) == 1
    assert responded_events[0]["payload"]["response"] == "approve"
    assert responded_events[0]["payload"]["outcome"] == "approved"


def test_approval_negative_cannot_respond_twice(tmp_path: Path) -> None:
    db_url = f"sqlite:///{tmp_path / 'runtime.db'}"
    _run_cli("--db-url", db_url, "init-db")

    workflow_run = _create_workflow_run(db_url)
    approval = _request_approval(
        db_url,
        workflow_run_id=workflow_run["workflow_run_id"],
        task_run_id=None,
        idempotency_key="idem-approval-request-neg-001",
    )

    _run_cli(
        "--db-url",
        db_url,
        "approvals",
        "respond",
        "--json",
        json.dumps(
            {
                "approval_id": approval["approval_id"],
                "actor_id": "human:supervisor-1",
                "actor_type": "human",
                "response_kind": "approve",
                "response_reason": "ok",
                "idempotency_key": "idem-approval-respond-neg-001",
            }
        ),
    )

    second = _run_cli(
        "--db-url",
        db_url,
        "approvals",
        "respond",
        "--json",
        json.dumps(
            {
                "approval_id": approval["approval_id"],
                "actor_id": "human:supervisor-2",
                "actor_type": "human",
                "response_kind": "reject",
                "response_reason": "late conflict",
                "idempotency_key": "idem-approval-respond-neg-002",
            }
        ),
        expect_ok=False,
    )
    assert second.returncode != 0
    assert _stderr_json(second)["error_code"] == "approval_not_respondable"

    events = _events_for_run(db_url, workflow_run["workflow_run_id"])
    assert len([event for event in events if event["event_type"] == "approval.responded"]) == 1


def test_artifact_version_creation_round_trip_and_event(tmp_path: Path) -> None:
    db_url = f"sqlite:///{tmp_path / 'runtime.db'}"
    _run_cli("--db-url", db_url, "init-db")

    workflow_run = _create_workflow_run(db_url)
    task_run = _create_task_run(db_url, workflow_run_id=workflow_run["workflow_run_id"])["task_run"]
    artifact = _create_artifact_version(
        db_url,
        workflow_run_id=workflow_run["workflow_run_id"],
        task_run_id=task_run["task_run_id"],
        artifact_kind="schedule.published_schedule.workbook",
        idempotency_key="idem-artifact-create-001",
    )

    shown = _stdout_json(
        _run_cli(
            "--db-url",
            db_url,
            "artifacts",
            "show",
            "--artifact-version-id",
            artifact["artifact_version_id"],
            "--json",
        )
    )["artifact_version"]
    assert shown["storage_uri"] == artifact["storage_uri"]
    assert shown["content_digest"] == artifact["content_digest"]
    assert shown["metadata_json"] == artifact["metadata_json"]
    assert shown["task_run_id"] == task_run["task_run_id"]

    events = _events_for_run(db_url, workflow_run["workflow_run_id"])
    created_events = [event for event in events if event["event_type"] == "artifact.version.created"]
    assert len(created_events) == 1
    assert created_events[0]["payload"]["artifact_version_id"] == artifact["artifact_version_id"]
    assert created_events[0]["payload"]["dataset_key"] == "schedule.published_schedule.workbook"


def test_artifact_version_idempotency_duplicate_key_fails_without_duplicate_effect(tmp_path: Path) -> None:
    db_url = f"sqlite:///{tmp_path / 'runtime.db'}"
    _run_cli("--db-url", db_url, "init-db")

    workflow_run = _create_workflow_run(db_url)
    payload = {
        "workflow_run_id": workflow_run["workflow_run_id"],
        "artifact_kind": "schedule.supervisor_review.doc",
        "artifact_role": "evidence",
        "media_type": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "storage_uri": "s3://runtime/schedule.supervisor_review.doc/dup.docx",
        "content_digest": "sha256:duplicate-test",
        "byte_size": 2048,
        "metadata_json": {"source": "runtime-test", "scenario": "idempotency"},
        "idempotency_key": "idem-artifact-idempotent-001",
    }

    first = _run_cli(
        "--db-url",
        db_url,
        "artifacts",
        "create-version",
        "--json",
        json.dumps(payload),
    )
    assert _stdout_json(first)["status"] == "ok"

    second = _run_cli(
        "--db-url",
        db_url,
        "artifacts",
        "create-version",
        "--json",
        json.dumps(payload),
        expect_ok=False,
    )
    assert second.returncode != 0
    assert _stderr_json(second)["error_code"] == "duplicate_idempotency_key"

    listed = _stdout_json(
        _run_cli(
            "--db-url",
            db_url,
            "artifacts",
            "list",
            "--workflow-run-id",
            workflow_run["workflow_run_id"],
            "--json",
        )
    )["artifact_versions"]
    assert len(listed) == 1

    events = _events_for_run(db_url, workflow_run["workflow_run_id"])
    assert len([event for event in events if event["event_type"] == "artifact.version.created"]) == 1


def test_pointer_promotion_happy_path_updates_row_and_emits_event(tmp_path: Path) -> None:
    db_url = f"sqlite:///{tmp_path / 'runtime.db'}"
    _run_cli("--db-url", db_url, "init-db")

    workflow_run = _create_workflow_run(db_url)
    artifact = _create_artifact_version(
        db_url,
        workflow_run_id=workflow_run["workflow_run_id"],
        task_run_id=None,
        artifact_kind="schedule.published_schedule.workbook",
        idempotency_key="idem-pointer-artifact-001",
    )

    promote_payload = {
        "workflow_run_id": workflow_run["workflow_run_id"],
        "scope_kind": "workflow_partition",
        "scope_ref": "SD-2026-03-04",
        "pointer_key": "schedule.published_schedule.workbook:official:SD-2026-03-04",
        "artifact_kind": "schedule.published_schedule.workbook",
        "artifact_version_id": artifact["artifact_version_id"],
        "promotion_reason": "manual_promote",
        "idempotency_key": "idem-pointer-promote-001",
    }
    promote = _run_cli(
        "--db-url",
        db_url,
        "pointers",
        "promote",
        "--json",
        json.dumps(promote_payload),
    )
    pointer = _stdout_json(promote)["pointer"]
    assert pointer["artifact_version_id"] == artifact["artifact_version_id"]
    assert pointer["generation"] == 0

    shown = _stdout_json(
        _run_cli(
            "--db-url",
            db_url,
            "pointers",
            "show",
            "--pointer-key",
            promote_payload["pointer_key"],
            "--workflow-run-id",
            workflow_run["workflow_run_id"],
            "--json",
        )
    )["pointer"]
    assert shown["artifact_version_id"] == artifact["artifact_version_id"]

    events = _events_for_run(db_url, workflow_run["workflow_run_id"])
    promoted_events = [event for event in events if event["event_type"] == "artifact.pointer.promoted"]
    assert len(promoted_events) == 1
    assert promoted_events[0]["payload"]["pointer_id"] == promote_payload["pointer_key"]


def test_pointer_promotion_allows_same_scope_cross_workflow_artifact_reference(
    tmp_path: Path,
) -> None:
    db_url = f"sqlite:///{tmp_path / 'runtime.db'}"
    _run_cli("--db-url", db_url, "init-db")

    source_run = _create_workflow_run(db_url, activation_key="run-source-same-scope")
    target_run = _create_workflow_run(db_url, activation_key="run-target-same-scope")
    source_artifact = _create_artifact_version(
        db_url,
        workflow_run_id=source_run["workflow_run_id"],
        task_run_id=None,
        artifact_kind="schedule.published_schedule.workbook",
        idempotency_key="idem-cross-run-same-scope-av-001",
    )

    promote = _run_cli(
        "--db-url",
        db_url,
        "pointers",
        "promote",
        "--json",
        json.dumps(
            {
                "workflow_run_id": target_run["workflow_run_id"],
                "scope_kind": "stage",
                "scope_ref": "Stage06",
                "pointer_key": "official:schedule.published_schedule.workbook",
                "artifact_kind": "schedule.published_schedule.workbook",
                "artifact_version_id": source_artifact["artifact_version_id"],
                "promotion_reason": "manual_promote",
                "idempotency_key": "idem-cross-run-same-scope-promote-001",
            }
        ),
    )
    promoted_pointer = _stdout_json(promote)["pointer"]
    assert promoted_pointer["workflow_run_id"] == target_run["workflow_run_id"]
    assert promoted_pointer["artifact_version_id"] == source_artifact["artifact_version_id"]

    shown = _stdout_json(
        _run_cli(
            "--db-url",
            db_url,
            "pointers",
            "show",
            "--pointer-key",
            "official:schedule.published_schedule.workbook",
            "--workflow-run-id",
            target_run["workflow_run_id"],
            "--json",
        )
    )["pointer"]
    assert shown["artifact_version_id"] == source_artifact["artifact_version_id"]

    events = _events_for_run(db_url, target_run["workflow_run_id"])
    promoted_events = [event for event in events if event["event_type"] == "artifact.pointer.promoted"]
    assert len(promoted_events) == 1
    assert promoted_events[0]["payload"]["promoted_artifact_version_id"] == source_artifact["artifact_version_id"]


def test_pointer_promotion_rejects_out_of_scope_cross_workflow_artifact_reference(
    tmp_path: Path,
) -> None:
    db_url = f"sqlite:///{tmp_path / 'runtime.db'}"
    _run_cli("--db-url", db_url, "init-db")

    source_run = _create_workflow_run(
        db_url,
        activation_key="run-source-other-partition",
        partition_key="SD-2026-03-04",
        logical_date="2026-03-04",
    )
    target_run = _create_workflow_run(
        db_url,
        activation_key="run-target-other-partition",
        partition_key="SD-2026-03-05",
        logical_date="2026-03-05",
    )
    source_artifact = _create_artifact_version(
        db_url,
        workflow_run_id=source_run["workflow_run_id"],
        task_run_id=None,
        artifact_kind="schedule.published_schedule.workbook",
        idempotency_key="idem-cross-run-out-of-scope-av-001",
    )

    promote = _run_cli(
        "--db-url",
        db_url,
        "pointers",
        "promote",
        "--json",
        json.dumps(
            {
                "workflow_run_id": target_run["workflow_run_id"],
                "scope_kind": "stage",
                "scope_ref": "Stage06",
                "pointer_key": "official:schedule.published_schedule.workbook",
                "artifact_kind": "schedule.published_schedule.workbook",
                "artifact_version_id": source_artifact["artifact_version_id"],
                "promotion_reason": "manual_promote",
                "idempotency_key": "idem-cross-run-out-of-scope-promote-001",
            }
        ),
        expect_ok=False,
    )
    assert promote.returncode != 0
    assert _stderr_json(promote)["error_code"] == "artifact_scope_mismatch"

    pointers = _stdout_json(
        _run_cli(
            "--db-url",
            db_url,
            "pointers",
            "list",
            "--workflow-run-id",
            target_run["workflow_run_id"],
            "--json",
        )
    )["pointers"]
    assert pointers == []

    events = _events_for_run(db_url, target_run["workflow_run_id"])
    assert not any(event["event_type"] == "artifact.pointer.promoted" for event in events)


def test_pointer_promotion_keeps_governance_local_approval_checks(
    tmp_path: Path,
) -> None:
    db_url = f"sqlite:///{tmp_path / 'runtime.db'}"
    _run_cli("--db-url", db_url, "init-db")

    approval_run = _create_workflow_run(db_url, activation_key="run-approval-scope")
    target_run = _create_workflow_run(db_url, activation_key="run-target-scope")
    task_run = _create_task_run(
        db_url,
        workflow_run_id=approval_run["workflow_run_id"],
        activation_key="task-approval-scope",
    )["task_run"]
    approval = _request_approval(
        db_url,
        workflow_run_id=approval_run["workflow_run_id"],
        task_run_id=task_run["task_run_id"],
        idempotency_key="idem-governance-local-approval-request-001",
    )
    _run_cli(
        "--db-url",
        db_url,
        "approvals",
        "respond",
        "--json",
        json.dumps(
            {
                "approval_id": approval["approval_id"],
                "actor_id": "human:dispatch-supervisor-1",
                "actor_type": "human",
                "response_kind": "approve",
                "response_reason": "approved",
                "idempotency_key": "idem-governance-local-approval-respond-001",
            }
        ),
    )
    target_artifact = _create_artifact_version(
        db_url,
        workflow_run_id=target_run["workflow_run_id"],
        task_run_id=None,
        artifact_kind="schedule.published_schedule.workbook",
        idempotency_key="idem-governance-local-av-001",
    )

    promote = _run_cli(
        "--db-url",
        db_url,
        "pointers",
        "promote",
        "--json",
        json.dumps(
            {
                "workflow_run_id": target_run["workflow_run_id"],
                "scope_kind": "stage",
                "scope_ref": "Stage06",
                "pointer_key": "official:schedule.published_schedule.workbook",
                "artifact_kind": "schedule.published_schedule.workbook",
                "artifact_version_id": target_artifact["artifact_version_id"],
                "promotion_reason": "official_publish",
                "approved_by_approval_id": approval["approval_id"],
                "actor_id": "human:dispatch-supervisor-1",
                "actor_type": "human",
                "idempotency_key": "idem-governance-local-promote-001",
            }
        ),
        expect_ok=False,
    )
    assert promote.returncode != 0
    assert _stderr_json(promote)["error_code"] == "cross_workflow_approval_reference"


def test_dual_write_authoritative_paths_capture_canonical_scope_provenance_and_inputs(
    tmp_path: Path,
) -> None:
    db_url = f"sqlite:///{tmp_path / 'runtime.db'}"
    _run_cli("--db-url", db_url, "init-db")

    workflow_run = _create_workflow_run(db_url, activation_key="run-act-dual-write-001")
    task_run = _create_task_run(
        db_url,
        workflow_run_id=workflow_run["workflow_run_id"],
        activation_key="task-act-dual-write-001",
    )["task_run"]

    base_artifact = _create_artifact_version(
        db_url,
        workflow_run_id=workflow_run["workflow_run_id"],
        task_run_id=task_run["task_run_id"],
        artifact_kind="schedule.published_schedule.workbook",
        idempotency_key="idem-dual-write-base-001",
    )

    _run_cli(
        "--db-url",
        db_url,
        "pointers",
        "promote",
        "--json",
        json.dumps(
            {
                "workflow_run_id": workflow_run["workflow_run_id"],
                "scope_kind": "stage",
                "scope_ref": "Stage06",
                "pointer_key": "official:schedule.published_schedule.workbook",
                "artifact_kind": "schedule.published_schedule.workbook",
                "artifact_version_id": base_artifact["artifact_version_id"],
                "promotion_reason": "seed_base",
                "idempotency_key": "idem-dual-write-promote-base-001",
            }
        ),
    )

    delta_payload = {
        "workflow_run_id": workflow_run["workflow_run_id"],
        "task_run_id": task_run["task_run_id"],
        "artifact_kind": "schedule.replan_delta.workbook",
        "artifact_role": "official_output",
        "media_type": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        "storage_uri": "s3://runtime/schedule.replan_delta.workbook/idem-dual-write-delta-001.xlsx",
        "content_digest": "sha256:idem-dual-write-delta-001",
        "byte_size": 2048,
        "metadata_json": {"source": "runtime-test", "scenario": "dual-write"},
        "parent_artifact_version_id": base_artifact["artifact_version_id"],
        "supersedes_artifact_version_id": base_artifact["artifact_version_id"],
        "idempotency_key": "idem-dual-write-delta-001",
    }
    delta_artifact = _stdout_json(
        _run_cli(
            "--db-url",
            db_url,
            "artifacts",
            "create-version",
            "--json",
            json.dumps(delta_payload),
        )
    )["artifact_version"]

    promoted_replan = _stdout_json(
        _run_cli(
            "--db-url",
            db_url,
            "pointers",
            "promote",
            "--json",
            json.dumps(
                {
                    "workflow_run_id": workflow_run["workflow_run_id"],
                    "scope_kind": "stage",
                    "scope_ref": "Stage07",
                    "pointer_key": "official:schedule.replan_delta.workbook",
                    "artifact_kind": "schedule.replan_delta.workbook",
                    "artifact_version_id": delta_artifact["artifact_version_id"],
                    "promotion_reason": "manual_promote",
                    "promoted_by_task_run_id": task_run["task_run_id"],
                    "reviewed_base_artifact_version_id": base_artifact["artifact_version_id"],
                    "base_pointer_key": "official:schedule.published_schedule.workbook",
                    "idempotency_key": "idem-dual-write-promote-delta-001",
                }
            ),
        )
    )["pointer"]

    artifact_rows = _query_rows(
        db_url,
        """
        SELECT
            tenant_id,
            domain_id,
            dataset_key,
            partition_kind,
            partition_key
        FROM artifact_versions
        WHERE artifact_version_id = ?
        """,
        (delta_artifact["artifact_version_id"],),
    )
    assert len(artifact_rows) == 1
    artifact_row = artifact_rows[0]
    assert artifact_row["tenant_id"] == "tenant-a"
    assert artifact_row["domain_id"] == "domain-x"
    assert artifact_row["dataset_key"] == "schedule.replan_delta.workbook"
    assert artifact_row["partition_kind"] == "ScheduleDateID"
    assert artifact_row["partition_key"] == "SD-2026-03-04"

    pointer_rows = _query_rows(
        db_url,
        """
        SELECT
            pointer_id,
            tenant_id,
            domain_id,
            dataset_key,
            partition_kind,
            partition_key,
            stream_key,
            registry_kind,
            artifact_version_id
        FROM artifact_pointers
        WHERE workflow_run_id = ? AND pointer_key = ?
        """,
        (
            workflow_run["workflow_run_id"],
            "official:schedule.replan_delta.workbook",
        ),
    )
    assert len(pointer_rows) == 1
    pointer_row = pointer_rows[0]
    assert pointer_row["pointer_id"]
    assert pointer_row["tenant_id"] == "tenant-a"
    assert pointer_row["domain_id"] == "domain-x"
    assert pointer_row["dataset_key"] == "schedule.replan_delta.workbook"
    assert pointer_row["partition_kind"] == "ScheduleDateID"
    assert pointer_row["partition_key"] == "SD-2026-03-04"
    assert pointer_row["stream_key"] is None
    assert pointer_row["registry_kind"] == "singleton"
    assert pointer_row["artifact_version_id"] == delta_artifact["artifact_version_id"]
    assert promoted_replan["artifact_version_id"] == delta_artifact["artifact_version_id"]

    provenance_rows = _query_rows(
        db_url,
        """
        SELECT edge_type, input_artifact_version_id
        FROM artifact_provenance_edges
        WHERE output_artifact_version_id = ?
        ORDER BY edge_type ASC
        """,
        (delta_artifact["artifact_version_id"],),
    )
    assert ({"edge_type": "derives_from", "input_artifact_version_id": base_artifact["artifact_version_id"]}) in provenance_rows
    assert ({"edge_type": "supersedes", "input_artifact_version_id": base_artifact["artifact_version_id"]}) in provenance_rows

    input_binding_rows = _query_rows(
        db_url,
        """
        SELECT
            source_kind,
            source_ref,
            artifact_version_id,
            pointer_key,
            pointer_generation,
            pointer_artifact_version_id
        FROM task_input_bindings
        WHERE task_run_id = ?
        """,
        (task_run["task_run_id"],),
    )
    assert any(
        row["source_kind"] == "pointer"
        and row["source_ref"] == "official:schedule.published_schedule.workbook"
        and row["pointer_generation"] == 0
        and row["pointer_artifact_version_id"] == base_artifact["artifact_version_id"]
        for row in input_binding_rows
    )
    assert any(
        row["source_kind"] == "artifact_version"
        and row["source_ref"] == base_artifact["artifact_version_id"]
        and row["artifact_version_id"] == base_artifact["artifact_version_id"]
        for row in input_binding_rows
    )


def test_pointer_promotion_conflict_race_allows_single_winner(tmp_path: Path) -> None:
    db_url = f"sqlite:///{tmp_path / 'runtime.db'}"
    _run_cli("--db-url", db_url, "init-db")

    workflow_run = _create_workflow_run(db_url)
    artifact_a = _create_artifact_version(
        db_url,
        workflow_run_id=workflow_run["workflow_run_id"],
        task_run_id=None,
        artifact_kind="schedule.replan_delta.workbook",
        idempotency_key="idem-pointer-race-av-a",
    )
    artifact_b = _create_artifact_version(
        db_url,
        workflow_run_id=workflow_run["workflow_run_id"],
        task_run_id=None,
        artifact_kind="schedule.replan_delta.workbook",
        idempotency_key="idem-pointer-race-av-b",
    )
    pointer_key = "schedule.replan_delta.workbook:official:SD-2026-03-04"

    payload_a = {
        "workflow_run_id": workflow_run["workflow_run_id"],
        "scope_kind": "workflow_partition",
        "scope_ref": "SD-2026-03-04",
        "pointer_key": pointer_key,
        "artifact_kind": "schedule.replan_delta.workbook",
        "artifact_version_id": artifact_a["artifact_version_id"],
        "promotion_reason": "manual_promote",
        "idempotency_key": "idem-pointer-race-promote-a",
    }
    payload_b = {
        "workflow_run_id": workflow_run["workflow_run_id"],
        "scope_kind": "workflow_partition",
        "scope_ref": "SD-2026-03-04",
        "pointer_key": pointer_key,
        "artifact_kind": "schedule.replan_delta.workbook",
        "artifact_version_id": artifact_b["artifact_version_id"],
        "promotion_reason": "manual_promote",
        "idempotency_key": "idem-pointer-race-promote-b",
    }

    def run_promote(payload: dict[str, Any]) -> subprocess.CompletedProcess[str]:
        return _run_cli(
            "--db-url",
            db_url,
            "pointers",
            "promote",
            "--json",
            json.dumps(payload),
            expect_ok=False,
        )

    with ThreadPoolExecutor(max_workers=2) as executor:
        result_a, result_b = executor.map(run_promote, [payload_a, payload_b])

    successes = [result for result in [result_a, result_b] if result.returncode == 0]
    failures = [result for result in [result_a, result_b] if result.returncode != 0]
    assert len(successes) == 1
    assert len(failures) == 1
    assert _stderr_json(failures[0])["error_code"] == "pointer_conflict"

    winner_artifact = _stdout_json(successes[0])["pointer"]["artifact_version_id"]
    shown = _stdout_json(
        _run_cli(
            "--db-url",
            db_url,
            "pointers",
            "show",
            "--pointer-key",
            pointer_key,
            "--workflow-run-id",
            workflow_run["workflow_run_id"],
            "--json",
        )
    )["pointer"]
    assert shown["artifact_version_id"] == winner_artifact

    events = _events_for_run(db_url, workflow_run["workflow_run_id"])
    pointer_events = [event for event in events if event["event_type"] == "artifact.pointer.promoted"]
    assert len(pointer_events) == 1


def test_cross_linkage_workflow_task_artifact_approval_pointer_chain(tmp_path: Path) -> None:
    db_url = f"sqlite:///{tmp_path / 'runtime.db'}"
    _run_cli("--db-url", db_url, "init-db")

    workflow_run = _create_workflow_run(db_url)
    task_result = _create_task_run(
        db_url,
        workflow_run_id=workflow_run["workflow_run_id"],
        activation_key="task-chain-001",
        create_human_task=True,
    )
    task_run = task_result["task_run"]

    artifact = _create_artifact_version(
        db_url,
        workflow_run_id=workflow_run["workflow_run_id"],
        task_run_id=task_run["task_run_id"],
        artifact_kind="schedule.published_schedule.workbook",
        idempotency_key="idem-chain-artifact-001",
    )

    approval = _request_approval(
        db_url,
        workflow_run_id=workflow_run["workflow_run_id"],
        task_run_id=task_run["task_run_id"],
        idempotency_key="idem-chain-approval-request-001",
    )
    _run_cli(
        "--db-url",
        db_url,
        "approvals",
        "respond",
        "--json",
        json.dumps(
            {
                "approval_id": approval["approval_id"],
                "actor_id": "human:dispatch-supervisor",
                "actor_type": "human",
                "response_kind": "approve",
                "response_reason": "publish approved",
                "idempotency_key": "idem-chain-approval-respond-001",
            }
        ),
    )

    promote_payload = {
        "workflow_run_id": workflow_run["workflow_run_id"],
        "scope_kind": "workflow_partition",
        "scope_ref": "SD-2026-03-04",
        "pointer_key": "schedule.published_schedule.workbook:official:SD-2026-03-04",
        "artifact_kind": "schedule.published_schedule.workbook",
        "artifact_version_id": artifact["artifact_version_id"],
        "promotion_reason": "official_publish",
        "promoted_by_task_run_id": task_run["task_run_id"],
        "approved_by_approval_id": approval["approval_id"],
        "actor_id": "human:dispatch-supervisor",
        "actor_type": "human",
        "idempotency_key": "idem-chain-pointer-promote-001",
    }
    _run_cli(
        "--db-url",
        db_url,
        "pointers",
        "promote",
        "--json",
        json.dumps(promote_payload),
    )

    pointer = _stdout_json(
        _run_cli(
            "--db-url",
            db_url,
            "pointers",
            "show",
            "--pointer-key",
            promote_payload["pointer_key"],
            "--workflow-run-id",
            workflow_run["workflow_run_id"],
            "--json",
        )
    )["pointer"]
    assert pointer["artifact_version_id"] == artifact["artifact_version_id"]
    assert pointer["approved_by_approval_id"] == approval["approval_id"]
    assert pointer["promoted_by_task_run_id"] == task_run["task_run_id"]

    events = _events_for_run(db_url, workflow_run["workflow_run_id"])
    event_types = [event["event_type"] for event in events]
    assert "artifact.version.created" in event_types
    assert "approval.requested" in event_types
    assert "approval.responded" in event_types
    assert "artifact.pointer.promoted" in event_types
