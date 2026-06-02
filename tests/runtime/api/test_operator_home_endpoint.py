from __future__ import annotations

import asyncio
import json
from pathlib import Path
from typing import Any

from onetruth.api.dependencies import RequestContext
from onetruth.api.main import create_app
from onetruth.infrastructure.db.session import open_sqlite_connection
from onetruth.infrastructure.events.event_store import create_sqlite_substrate
from onetruth.infrastructure.repositories.artifact_versions import create_artifact_version
from onetruth.infrastructure.repositories.workflow_runs import create_workflow_run


def test_operator_home_uses_server_identity_and_surfaces_reconciler_findings(
    tmp_path: Path,
) -> None:
    db_url = _seed_weekly_with_missing_blob(tmp_path)
    app = create_app(
        db_url=db_url,
        boundary_profile="shared_env",
        principal_resolver=lambda _headers: RequestContext(
            tenant_id="tenant-a",
            domain_id="domain-x",
            actor_id="service:shared-gateway",
            actor_type="service",
            actor_roles=("dispatch_supervisor",),
        ),
    )

    status, _headers, body = _invoke(
        app,
        method="GET",
        path="/api/v1/operator/home",
        headers={
            "x-onetruth-tenant-id": "tenant-conflict",
            "x-onetruth-domain-id": "domain-conflict",
            "x-onetruth-actor-id": "human:browser-actor",
            "x-onetruth-actor-type": "human",
            "x-onetruth-actor-roles": "operations_manager",
        },
    )

    payload = json.loads(body.decode("utf-8"))
    assert status == 200
    assert payload["command"] == "api.operator.home"
    home = payload["operator_home"]
    assert home["status"] == "attention"
    assert home["viewer"] == {
        "tenant_id": "tenant-a",
        "domain_id": "domain-x",
        "actor_id": "service:shared-gateway",
        "actor_type": "service",
        "actor_roles": ["dispatch_supervisor"],
        "boundary_profile": "shared_env",
        "actor_switching_allowed": False,
    }
    failure_state = home["failure_state"]
    assert failure_state["mode"] == "dry_run"
    assert failure_state["summary"]["mutations_performed"] == 0
    codes = {item["code"] for item in failure_state["findings"]}
    assert "weekly_daily_seed_missing" in codes
    assert "artifact_blob_missing" in codes
    serialized = json.dumps(payload, sort_keys=True)
    assert "tenant-conflict" not in serialized
    assert "domain-conflict" not in serialized
    assert str(tmp_path) not in serialized


def _seed_weekly_with_missing_blob(tmp_path: Path) -> str:
    db_path = tmp_path / "runtime.db"
    db_url = f"sqlite:///{db_path}"
    connection = open_sqlite_connection(db_url)
    try:
        create_sqlite_substrate(connection)
        create_workflow_run(
            connection,
            workflow_run_id="wr-weekly-missing",
            workflow_id="weekly_schedule_planning.v1",
            workflow_version="v1",
            tenant_id="tenant-a",
            domain_id="domain-x",
            partition_key="PW-2026-W10",
            logical_date="2026-03-02",
            activation_key="weekly_schedule_planning.v1:PW-2026-W10",
            state="OPEN",
            created_at="2026-03-02T00:00:00Z",
        )
        create_artifact_version(
            connection,
            artifact_version_id="av-weekly-published-missing-blob",
            workflow_run_id="wr-weekly-missing",
            tenant_id="tenant-a",
            domain_id="domain-x",
            dataset_key="planning.published_weekly_schedule.workbook",
            partition_kind="PlanningWeekID",
            partition_key="PW-2026-W10",
            task_run_id=None,
            artifact_kind="planning.published_weekly_schedule.workbook",
            artifact_role="official_output",
            media_type="application/json",
            storage_uri=f"file://{tmp_path / 'missing-published.json'}",
            content_digest="sha256:missing",
            byte_size=128,
            metadata_json={},
            parent_artifact_version_id=None,
            supersedes_artifact_version_id=None,
            lineage_note="test_missing_blob",
            created_at="2026-03-02T00:01:00Z",
        )
        connection.commit()
    finally:
        connection.close()
    return db_url


def _invoke(
    app,
    *,
    method: str,
    path: str,
    headers: dict[str, str] | None = None,
) -> tuple[int, dict[str, str], bytes]:
    raw_headers = [
        (key.encode("latin-1"), value.encode("latin-1"))
        for key, value in (headers or {}).items()
    ]
    scope = {
        "type": "http",
        "asgi": {"version": "3.0"},
        "http_version": "1.1",
        "method": method,
        "scheme": "http",
        "path": path,
        "raw_path": path.encode("latin-1"),
        "query_string": b"",
        "headers": raw_headers,
        "client": ("testclient", 1234),
        "server": ("testserver", 80),
    }

    async def _call() -> list[dict[str, Any]]:
        sent: list[dict[str, Any]] = []
        sent_request = False

        async def receive() -> dict[str, Any]:
            nonlocal sent_request
            if sent_request:
                return {"type": "http.disconnect"}
            sent_request = True
            return {"type": "http.request", "body": b"", "more_body": False}

        async def send(message: dict[str, Any]) -> None:
            sent.append(message)

        await app(scope, receive, send)
        return sent

    messages = asyncio.run(_call())
    start = next(
        message for message in messages if message["type"] == "http.response.start"
    )
    start_headers = {
        key.decode("latin-1").lower(): value.decode("latin-1")
        for key, value in start.get("headers", [])
    }
    response_body = b"".join(
        message.get("body", b"")
        for message in messages
        if message["type"] == "http.response.body"
    )
    return int(start["status"]), start_headers, response_body
