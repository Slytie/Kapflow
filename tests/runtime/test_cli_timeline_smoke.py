from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
import subprocess
import sys
from uuid import uuid4

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
SRC_ROOT = REPO_ROOT / "src"


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _event(
    *,
    event_type: str,
    run_id: str,
    payload: dict[str, object],
    idempotency_key: str | None = None,
) -> dict[str, object]:
    task_run_id = f"tr-{run_id}-{event_type.replace('.', '-')}"
    human_task_id = f"ht-{run_id}-{event_type.replace('.', '-')}"
    envelope: dict[str, object] = {
        "event_id": f"evt-{uuid4()}",
        "event_type": event_type,
        "schema_version": "1.0",
        "occurred_at": _now_iso(),
        "recorded_at": _now_iso(),
        "tenant_id": "tenant-a",
        "domain_id": "domain-x",
        "actor": {"type": "agent", "id": "agent:runtime-smoke"},
        "links": _links_for_event(
            event_type=event_type,
            run_id=run_id,
            task_run_id=task_run_id,
            human_task_id=human_task_id,
        ),
        "payload": payload,
    }
    if idempotency_key:
        envelope["idempotency_key"] = idempotency_key
    return envelope


def _links_for_event(
    *,
    event_type: str,
    run_id: str,
    task_run_id: str,
    human_task_id: str,
) -> list[dict[str, str]]:
    if event_type == "workflow.run.created":
        return [
            {"rel": "run", "type": "workflow_run", "id": run_id},
            {
                "rel": "workflow_contract_version",
                "type": "workflow_contract_version",
                "id": "test.workflow_contract@1",
            },
            {
                "rel": "decision_catalog_version",
                "type": "decision_catalog_version",
                "id": "test.decision_catalog@1",
            },
            {
                "rel": "execution_profile_version",
                "type": "execution_profile_version",
                "id": "test.execution_profile@1",
            },
        ]
    if event_type == "task.run.created":
        return [
            {"rel": "run", "type": "workflow_run", "id": run_id},
            {"rel": "task_run", "type": "task_run", "id": task_run_id},
        ]
    if event_type == "task.completed":
        return [
            {"rel": "task_run", "type": "task_run", "id": task_run_id},
            {"rel": "human_task", "type": "human_task", "id": human_task_id},
        ]
    return [{"rel": "run", "type": "workflow_run", "id": run_id}]


def _run_cli(*args: str, expect_ok: bool = True) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    existing_pythonpath = env.get("PYTHONPATH")
    if existing_pythonpath:
        env["PYTHONPATH"] = f"{SRC_ROOT}{os.pathsep}{existing_pythonpath}"
    else:
        env["PYTHONPATH"] = str(SRC_ROOT)

    cmd = [sys.executable, "-m", "onetruth.cli", *args]
    result = subprocess.run(
        cmd,
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


def _stdout_json(result: subprocess.CompletedProcess[str]) -> object:
    assert result.stdout, "expected JSON stdout output"
    return json.loads(result.stdout)


def test_cli_init_append_and_list_round_trip(tmp_path: Path) -> None:
    db_url = f"sqlite:///{tmp_path / 'runtime.db'}"

    init_result = _run_cli("--db-url", db_url, "init-db")
    init_payload = _stdout_json(init_result)
    assert isinstance(init_payload, dict)
    assert init_payload["status"] == "ok"

    run_id = "run-001"
    other_run_id = "run-002"
    events = [
        _event(
            event_type="workflow.run.created",
            run_id=run_id,
            payload={"step": 1, "meta": {"source": "smoke-test"}},
        ),
        _event(
            event_type="task.run.created",
            run_id=run_id,
            payload={"step": 2, "task_kind": "analysis"},
        ),
        _event(
            event_type="task.completed",
            run_id=other_run_id,
            payload={"step": 3, "result": {"ok": True, "count": 3}},
        ),
    ]

    for event in events:
        append_result = _run_cli(
            "--db-url",
            db_url,
            "events",
            "append",
            "--json",
            json.dumps(event),
        )
        append_payload = _stdout_json(append_result)
        assert isinstance(append_payload, dict)
        assert append_payload["status"] == "ok"
        assert append_payload["event_id"] == event["event_id"]

    listed_result = _run_cli("--db-url", db_url, "events", "list", "--json")
    listed = _stdout_json(listed_result)
    assert isinstance(listed, list)
    assert [item["event_id"] for item in listed] == [event["event_id"] for event in events]
    assert len({item["event_id"] for item in listed}) == len(events)
    assert [item["sequence_no"] for item in listed] == [1, 2, 3]

    for i, item in enumerate(listed):
        assert item["payload"] == events[i]["payload"]

    filtered_result = _run_cli(
        "--db-url",
        db_url,
        "events",
        "list",
        "--run-id",
        run_id,
        "--json",
    )
    filtered = _stdout_json(filtered_result)
    assert isinstance(filtered, list)
    assert [item["event_id"] for item in filtered] == [events[0]["event_id"], events[1]["event_id"]]

    since_result = _run_cli(
        "--db-url",
        db_url,
        "events",
        "list",
        "--since-event-id",
        str(events[0]["event_id"]),
        "--json",
    )
    since_list = _stdout_json(since_result)
    assert isinstance(since_list, list)
    assert [item["event_id"] for item in since_list] == [events[1]["event_id"], events[2]["event_id"]]


def test_cli_duplicate_idempotency_key_fails_explicitly(tmp_path: Path) -> None:
    db_url = f"sqlite:///{tmp_path / 'runtime.db'}"
    _run_cli("--db-url", db_url, "init-db")

    idempotency_key = "idem-key-001"
    first_event = _event(
        event_type="task.run.created",
        run_id="run-004",
        payload={"attempt": 1},
        idempotency_key=idempotency_key,
    )
    duplicate_event = _event(
        event_type="task.run.created",
        run_id="run-004",
        payload={"attempt": 2},
        idempotency_key=idempotency_key,
    )

    _run_cli(
        "--db-url",
        db_url,
        "events",
        "append",
        "--json",
        json.dumps(first_event),
    )
    duplicate_result = _run_cli(
        "--db-url",
        db_url,
        "events",
        "append",
        "--json",
        json.dumps(duplicate_event),
        expect_ok=False,
    )
    assert duplicate_result.returncode != 0
    assert duplicate_result.stderr
    error_payload = json.loads(duplicate_result.stderr)
    assert error_payload["status"] == "error"
    assert error_payload["error_code"] == "duplicate_idempotency_key"
    assert error_payload["details"]["idempotency_key"] == idempotency_key

    listed_result = _run_cli("--db-url", db_url, "events", "list", "--json")
    listed = _stdout_json(listed_result)
    assert isinstance(listed, list)
    assert [item["event_id"] for item in listed] == [first_event["event_id"]]
