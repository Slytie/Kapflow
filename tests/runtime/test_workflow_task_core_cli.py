from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
import json
import os
from pathlib import Path
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


def _create_workflow_run(db_url: str, *, activation_key: str = "act-run-001") -> dict[str, Any]:
    payload = {
        "workflow_id": "schedule_planning.v1",
        "workflow_version": "v1",
        "tenant_id": "tenant-a",
        "domain_id": "domain-x",
        "partition_key": "SD-2026-03-03",
        "logical_date": "2026-03-03",
        "activation_key": activation_key,
        "idempotency_key": f"idem-run-{activation_key}",
    }
    result = _run_cli("--db-url", db_url, "runs", "create", "--json", json.dumps(payload))
    parsed = _stdout_json(result)
    assert parsed["status"] == "ok"
    return parsed["workflow_run"]


def _create_task_with_human(
    db_url: str,
    *,
    workflow_run_id: str,
    activation_key: str = "task-act-001",
) -> dict[str, Any]:
    payload = {
        "workflow_run_id": workflow_run_id,
        "stage_id": "Stage03",
        "task_kind": "work_item",
        "activation_key": activation_key,
        "candidate_roles": ["schedule_planner"],
        "owner_role": "operations_manager",
        "create_human_task": True,
        "idempotency_key": f"idem-task-{activation_key}",
    }
    result = _run_cli("--db-url", db_url, "tasks", "create", "--json", json.dumps(payload))
    parsed = _stdout_json(result)
    assert parsed["status"] == "ok"
    return parsed["result"]


def test_workflow_run_create_persists_row_and_emits_event(tmp_path: Path) -> None:
    db_url = f"sqlite:///{tmp_path / 'runtime.db'}"
    _run_cli("--db-url", db_url, "init-db")

    workflow_run = _create_workflow_run(db_url)
    assert workflow_run["workflow_id"] == "schedule_planning.v1"
    assert workflow_run["state"] == "OPEN"

    show_result = _run_cli(
        "--db-url",
        db_url,
        "runs",
        "show",
        "--workflow-run-id",
        workflow_run["workflow_run_id"],
        "--json",
    )
    shown = _stdout_json(show_result)["workflow_run"]
    assert shown["activation_key"] == "act-run-001"

    events = _events_for_run(db_url, workflow_run["workflow_run_id"])
    created_events = [event for event in events if event["event_type"] == "workflow.run.created"]
    assert len(created_events) == 1
    assert created_events[0]["payload"]["workflow_id"] == "schedule_planning.v1"
    assert created_events[0]["payload"]["activation_key"] == "act-run-001"


def test_task_create_with_human_persists_rows_and_emits_events(tmp_path: Path) -> None:
    db_url = f"sqlite:///{tmp_path / 'runtime.db'}"
    _run_cli("--db-url", db_url, "init-db")
    workflow_run = _create_workflow_run(db_url)

    created = _create_task_with_human(db_url, workflow_run_id=workflow_run["workflow_run_id"])
    task_run = created["task_run"]
    human_task = created["human_task"]
    assert task_run["state"] == "READY"
    assert human_task["state"] == "OPEN"
    assert human_task["task_run_id"] == task_run["task_run_id"]

    listed_result = _run_cli(
        "--db-url",
        db_url,
        "tasks",
        "list",
        "--workflow-run-id",
        workflow_run["workflow_run_id"],
        "--json",
    )
    listed = _stdout_json(listed_result)["tasks"]
    assert len(listed) == 1
    assert listed[0]["human_task_id"] == human_task["human_task_id"]
    assert listed[0]["task_run_state"] == "READY"

    events = _events_for_run(db_url, workflow_run["workflow_run_id"])
    assert len([event for event in events if event["event_type"] == "task.run.created"]) == 1
    assert len([event for event in events if event["event_type"] == "task.created"]) == 1


def test_claim_happy_path_updates_state_and_emits_events(tmp_path: Path) -> None:
    db_url = f"sqlite:///{tmp_path / 'runtime.db'}"
    _run_cli("--db-url", db_url, "init-db")
    workflow_run = _create_workflow_run(db_url)
    created = _create_task_with_human(db_url, workflow_run_id=workflow_run["workflow_run_id"])
    human_task = created["human_task"]

    claim_payload = {
        "human_task_id": human_task["human_task_id"],
        "actor_id": "agent:planner-a",
        "actor_type": "agent",
        "lease_seconds": 120,
        "idempotency_key": "idem-claim-001",
    }
    claim_result = _run_cli(
        "--db-url",
        db_url,
        "tasks",
        "claim",
        "--json",
        json.dumps(claim_payload),
    )
    claim = _stdout_json(claim_result)["result"]
    assert claim["human_task"]["state"] == "CLAIMED"
    assert claim["human_task"]["lease_version"] == 1
    assert claim["task_run"]["state"] == "IN_PROGRESS"

    shown = _stdout_json(
        _run_cli(
            "--db-url",
            db_url,
            "tasks",
            "show",
            "--human-task-id",
            human_task["human_task_id"],
            "--json",
        )
    )["human_task"]
    assert shown["assignee_actor_id"] == "agent:planner-a"
    assert shown["task_run_state"] == "IN_PROGRESS"

    events = _events_for_run(db_url, workflow_run["workflow_run_id"])
    assert len([event for event in events if event["event_type"] == "task.claimed"]) == 1
    state_changes = [event for event in events if event["event_type"] == "task.run.state_changed"]
    assert any(event["payload"]["to_state"] == "IN_PROGRESS" for event in state_changes)


def test_claim_concurrency_allows_exactly_one_winner(tmp_path: Path) -> None:
    db_url = f"sqlite:///{tmp_path / 'runtime.db'}"
    _run_cli("--db-url", db_url, "init-db")
    workflow_run = _create_workflow_run(db_url)
    created = _create_task_with_human(db_url, workflow_run_id=workflow_run["workflow_run_id"])
    human_task_id = created["human_task"]["human_task_id"]

    payload_a = {
        "human_task_id": human_task_id,
        "actor_id": "agent:planner-a",
        "actor_type": "agent",
        "lease_seconds": 90,
        "idempotency_key": "idem-claim-concurrency-a",
    }
    payload_b = {
        "human_task_id": human_task_id,
        "actor_id": "agent:planner-b",
        "actor_type": "agent",
        "lease_seconds": 90,
        "idempotency_key": "idem-claim-concurrency-b",
    }

    def run_claim(payload: dict[str, Any]) -> subprocess.CompletedProcess[str]:
        return _run_cli(
            "--db-url",
            db_url,
            "tasks",
            "claim",
            "--json",
            json.dumps(payload),
            expect_ok=False,
        )

    with ThreadPoolExecutor(max_workers=2) as executor:
        result_a, result_b = executor.map(run_claim, [payload_a, payload_b])

    successes = [result for result in [result_a, result_b] if result.returncode == 0]
    failures = [result for result in [result_a, result_b] if result.returncode != 0]
    assert len(successes) == 1
    assert len(failures) == 1
    loser_error = _stderr_json(failures[0])
    assert loser_error["error_code"] == "task_not_claimable"

    winner_actor = _stdout_json(successes[0])["result"]["human_task"]["assignee_actor_id"]
    shown = _stdout_json(
        _run_cli(
            "--db-url",
            db_url,
            "tasks",
            "show",
            "--human-task-id",
            human_task_id,
            "--json",
        )
    )["human_task"]
    assert shown["assignee_actor_id"] == winner_actor

    events = _events_for_run(db_url, workflow_run["workflow_run_id"])
    assert len([event for event in events if event["event_type"] == "task.claimed"]) == 1


def test_claim_idempotency_key_retry_fails_without_duplicate_effect(tmp_path: Path) -> None:
    db_url = f"sqlite:///{tmp_path / 'runtime.db'}"
    _run_cli("--db-url", db_url, "init-db")
    workflow_run = _create_workflow_run(db_url)
    created = _create_task_with_human(db_url, workflow_run_id=workflow_run["workflow_run_id"])
    human_task_id = created["human_task"]["human_task_id"]

    claim_payload = {
        "human_task_id": human_task_id,
        "actor_id": "agent:planner-a",
        "actor_type": "agent",
        "lease_seconds": 60,
        "idempotency_key": "idem-claim-retry-001",
    }

    first = _run_cli("--db-url", db_url, "tasks", "claim", "--json", json.dumps(claim_payload))
    assert _stdout_json(first)["status"] == "ok"

    second = _run_cli(
        "--db-url",
        db_url,
        "tasks",
        "claim",
        "--json",
        json.dumps(claim_payload),
        expect_ok=False,
    )
    assert second.returncode != 0
    error = _stderr_json(second)
    assert error["error_code"] == "duplicate_idempotency_key"

    events = _events_for_run(db_url, workflow_run["workflow_run_id"])
    assert len([event for event in events if event["event_type"] == "task.claimed"]) == 1


def test_complete_happy_path_updates_state_and_emits_events(tmp_path: Path) -> None:
    db_url = f"sqlite:///{tmp_path / 'runtime.db'}"
    _run_cli("--db-url", db_url, "init-db")
    workflow_run = _create_workflow_run(db_url)
    created = _create_task_with_human(db_url, workflow_run_id=workflow_run["workflow_run_id"])
    human_task_id = created["human_task"]["human_task_id"]

    _run_cli(
        "--db-url",
        db_url,
        "tasks",
        "claim",
        "--json",
        json.dumps(
            {
                "human_task_id": human_task_id,
                "actor_id": "agent:planner-a",
                "actor_type": "agent",
                "lease_seconds": 120,
                "idempotency_key": "idem-claim-before-complete-001",
            }
        ),
    )
    complete_result = _run_cli(
        "--db-url",
        db_url,
        "tasks",
        "complete",
        "--json",
        json.dumps(
            {
                "human_task_id": human_task_id,
                "actor_id": "agent:planner-a",
                "actor_type": "agent",
                "outcome": "done",
                "idempotency_key": "idem-complete-001",
            }
        ),
    )
    completed = _stdout_json(complete_result)["result"]
    assert completed["human_task"]["state"] == "COMPLETED"
    assert completed["task_run"]["state"] == "COMPLETED"

    shown = _stdout_json(
        _run_cli(
            "--db-url",
            db_url,
            "tasks",
            "show",
            "--human-task-id",
            human_task_id,
            "--json",
        )
    )["human_task"]
    assert shown["state"] == "COMPLETED"
    assert shown["task_run_state"] == "COMPLETED"

    events = _events_for_run(db_url, workflow_run["workflow_run_id"])
    assert len([event for event in events if event["event_type"] == "task.completed"]) == 1
    state_changes = [event for event in events if event["event_type"] == "task.run.state_changed"]
    assert any(event["payload"]["to_state"] == "COMPLETED" for event in state_changes)


def test_negative_cases_for_unclaimed_complete_and_duplicate_workflow_activation(tmp_path: Path) -> None:
    db_url = f"sqlite:///{tmp_path / 'runtime.db'}"
    _run_cli("--db-url", db_url, "init-db")
    workflow_run = _create_workflow_run(db_url, activation_key="act-run-neg-001")
    created = _create_task_with_human(
        db_url,
        workflow_run_id=workflow_run["workflow_run_id"],
        activation_key="task-neg-001",
    )
    human_task_id = created["human_task"]["human_task_id"]

    complete_unclaimed = _run_cli(
        "--db-url",
        db_url,
        "tasks",
        "complete",
        "--json",
        json.dumps(
            {
                "human_task_id": human_task_id,
                "actor_id": "agent:planner-a",
                "actor_type": "agent",
                "outcome": "done",
                "idempotency_key": "idem-complete-unclaimed-001",
            }
        ),
        expect_ok=False,
    )
    assert complete_unclaimed.returncode != 0
    assert _stderr_json(complete_unclaimed)["error_code"] == "task_not_completable"

    duplicate_activation = _run_cli(
        "--db-url",
        db_url,
        "runs",
        "create",
        "--json",
        json.dumps(
            {
                "workflow_id": "schedule_planning.v1",
                "workflow_version": "v1",
                "tenant_id": "tenant-a",
                "domain_id": "domain-x",
                "partition_key": "SD-2026-03-03",
                "logical_date": "2026-03-03",
                "activation_key": "act-run-neg-001",
                "idempotency_key": "idem-run-duplicate-neg-001",
            }
        ),
        expect_ok=False,
    )
    assert duplicate_activation.returncode != 0
    assert _stderr_json(duplicate_activation)["error_code"] == "duplicate_workflow_activation"

