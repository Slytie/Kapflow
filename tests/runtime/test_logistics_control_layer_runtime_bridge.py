from __future__ import annotations

import json
import sqlite3
from pathlib import Path

from onetruth.infrastructure.definitions.control_layer import (
    compile_control_layer,
    derive_execution_session_payload,
)
from tests.runtime.helpers.runtime_cli import REPO_ROOT, run_cli, stdout_json


FAMILY_PATH = REPO_ROOT / "docs" / "workflows" / "logistics_ops_family" / "v1" / "WORKFLOW_FAMILY.yaml"
TRANSFORMS_PATH = REPO_ROOT / "docs" / "workflows" / "logistics_ops_family" / "v1" / "PARTITION_TRANSFORMS.yaml"
METHOD_PACKAGES_PATH = REPO_ROOT / "docs" / "workflows" / "logistics_ops_family" / "v1" / "METHOD_PACKAGES.yaml"


def _compile_control_layer() -> dict[str, object]:
    return compile_control_layer(
        repo_root=REPO_ROOT,
        family_path=FAMILY_PATH,
        partition_transforms_path=TRANSFORMS_PATH,
        method_packages_path=METHOD_PACKAGES_PATH,
    )


def _create_live_dispatch_run(db_url: str) -> dict[str, object]:
    result = run_cli(
        "--db-url",
        db_url,
        "runs",
        "create",
        "--json",
        json.dumps(
            {
                "workflow_id": "live_dispatch.v1",
                "workflow_version": "v1",
                "tenant_id": "tenant-logistics",
                "domain_id": "domain-hub",
                "partition_key": "SD-2026-03-06",
                "logical_date": "2026-03-06",
                "activation_key": "live-dispatch:SD-2026-03-06",
                "idempotency_key": "idem:live-dispatch:run",
            },
            separators=(",", ":"),
        ),
    )
    return stdout_json(result)["workflow_run"]


def _create_stage02_task(db_url: str, workflow_run_id: str) -> dict[str, object]:
    result = run_cli(
        "--db-url",
        db_url,
        "tasks",
        "create",
        "--json",
        json.dumps(
            {
                "workflow_run_id": workflow_run_id,
                "stage_id": "Stage02",
                "task_kind": "exception_triage",
                "activation_key": "live-dispatch:SD-2026-03-06:stage02",
                "idempotency_key": "idem:live-dispatch:stage02-task",
            },
            separators=(",", ":"),
        ),
    )
    return stdout_json(result)["result"]["task_run"]


def test_compiled_control_metadata_drives_existing_execution_session_runtime(tmp_path: Path) -> None:
    db_path = tmp_path / "runtime.db"
    db_url = f"sqlite:///{db_path}"
    run_cli("--db-url", db_url, "init-db")

    workflow_run = _create_live_dispatch_run(db_url)
    task_run = _create_stage02_task(db_url, str(workflow_run["workflow_run_id"]))

    compiled = _compile_control_layer()
    payload = derive_execution_session_payload(
        compiled_control=compiled,
        module_id="live_dispatch",
        stage_id="Stage02",
        workflow_run_id=str(workflow_run["workflow_run_id"]),
        task_run_id=str(task_run["task_run_id"]),
        principal_actor={"type": "agent", "id": "agent:dispatch-controller"},
        idempotency_key="idem:control-layer:execution-session",
        state="WAITING_POLICY",
    )

    created = run_cli(
        "--db-url",
        db_url,
        "execution-sessions",
        "create",
        "--json",
        json.dumps(payload, separators=(",", ":")),
    )
    session = stdout_json(created)["execution_session"]

    assert session["workflow_run_id"] == workflow_run["workflow_run_id"]
    assert session["task_run_id"] == task_run["task_run_id"]
    assert session["execution_spec_id"] == payload["execution_spec_id"]
    assert session["owner_mode"] == payload["owner_mode"]
    assert session["state"] == "WAITING_POLICY"
    assert session["budget"]["max_tool_calls"] == payload["budget"]["max_tool_calls"]

    connection = sqlite3.connect(db_path)
    connection.row_factory = sqlite3.Row
    try:
        sessions = connection.execute(
            "SELECT execution_session_id, execution_spec_id, owner_mode FROM execution_sessions"
        ).fetchall()
        assert len(sessions) == 1

        activation_tables = connection.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name LIKE ?",
            ("%activation%",),
        ).fetchall()
        assert [row["name"] for row in activation_tables] == []
    finally:
        connection.close()
