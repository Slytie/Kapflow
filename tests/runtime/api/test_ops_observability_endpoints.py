from __future__ import annotations

import asyncio
import json
import os
from pathlib import Path

import pytest

from onetruth.api.boundary_logging import reset_request_metrics
from onetruth.api.dependencies import unavailable_principal_resolver
from onetruth.api.main import create_app
from onetruth.infrastructure.db.session import open_sqlite_connection
from onetruth.infrastructure.events.event_store import (
    append_event,
    create_sqlite_substrate,
    event_id_for_type,
    utc_now_iso,
)


@pytest.fixture(autouse=True)
def _reset_request_metrics() -> None:
    reset_request_metrics()
    yield
    reset_request_metrics()


def test_ops_health_and_metrics_work_without_headers_and_business_routes_stay_fail_closed(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    db_url = _initialized_db_url(tmp_path)
    artifact_root = tmp_path / "artifacts"
    artifact_root.mkdir(parents=True, exist_ok=True)
    monkeypatch.setenv("ONETRUTH_ARTIFACT_ROOT", str(artifact_root))
    app = _shared_env_ops_app(db_url)

    health_status, _health_headers, health_body = _invoke(
        app,
        method="GET",
        path="/api/v1/ops/health",
    )
    health_payload = json.loads(health_body.decode("utf-8"))

    assert health_status == 200
    assert health_payload == {
        "status": "ok",
        "command": "api.ops.health",
        "health": {"live": True},
    }

    workflow_status, _workflow_headers, workflow_body = _invoke(
        app,
        method="GET",
        path="/api/v1/workflow-runs",
    )
    workflow_payload = json.loads(workflow_body.decode("utf-8"))

    assert workflow_status == 503
    assert workflow_payload["error"]["code"] == "principal_resolver_unavailable"

    metrics_status, _metrics_headers, metrics_body = _invoke(
        app,
        method="GET",
        path="/api/v1/ops/metrics",
    )
    metrics_payload = json.loads(metrics_body.decode("utf-8"))

    assert metrics_status == 200
    assert metrics_payload["status"] == "ok"
    assert metrics_payload["command"] == "api.ops.metrics"
    counters = metrics_payload["metrics"]["request_counters"]
    assert any(
        counter["route_name"] == "ops.health"
        and counter["method"] == "GET"
        and counter["status_family"] == "2xx"
        and counter["count"] == 1
        and isinstance(counter["latency_ms_total"], int)
        for counter in counters
    )
    assert any(
        counter["route_name"] == "workflow_runs.list"
        and counter["status_family"] == "5xx"
        and counter["count"] == 1
        for counter in counters
    )
    serialized = json.dumps(metrics_payload, sort_keys=True)
    assert "tenant-a" not in serialized
    assert "domain-x" not in serialized
    assert "human:" not in serialized
    assert "x-request-id" not in serialized
    assert "/api/v1/ops/health" not in serialized


def test_ops_readiness_returns_200_when_db_and_artifact_storage_are_ready(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    db_url = _initialized_db_url(tmp_path)
    artifact_root = tmp_path / "artifacts"
    artifact_root.mkdir(parents=True, exist_ok=True)
    monkeypatch.setenv("ONETRUTH_ARTIFACT_ROOT", str(artifact_root))
    app = _shared_env_ops_app(db_url)

    status, _headers, body = _invoke(app, method="GET", path="/api/v1/ops/readiness")
    payload = json.loads(body.decode("utf-8"))

    assert status == 200
    assert payload["status"] == "ok"
    assert payload["command"] == "api.ops.readiness"
    assert payload["readiness"]["ready"] is True
    assert payload["readiness"]["db"] == {
        "kind": "sqlite",
        "ready": True,
        "exists": True,
        "is_file": True,
        "error_code": None,
    }
    assert payload["readiness"]["artifact_storage"] == {
        "ready": True,
        "exists": True,
        "is_directory": True,
        "writable": True,
        "error_code": None,
    }
    assert payload["readiness"]["warnings"] == {
        "degradation_visibility_available": True,
        "active_degraded_components": [],
        "projection_coherence_failed_total": 0,
    }


def test_ops_readiness_returns_503_when_db_file_is_missing(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    db_url = f"sqlite:///{tmp_path / 'missing.db'}"
    artifact_root = tmp_path / "artifacts"
    artifact_root.mkdir(parents=True, exist_ok=True)
    monkeypatch.setenv("ONETRUTH_ARTIFACT_ROOT", str(artifact_root))
    app = _shared_env_ops_app(db_url)

    status, _headers, body = _invoke(app, method="GET", path="/api/v1/ops/readiness")
    payload = json.loads(body.decode("utf-8"))

    assert status == 503
    assert payload["status"] == "not_ready"
    assert payload["readiness"]["ready"] is False
    assert payload["readiness"]["db"]["error_code"] == "missing_db_file"
    assert payload["readiness"]["artifact_storage"]["ready"] is True


@pytest.mark.parametrize(
    ("mode", "expected_error_code"),
    [
        ("missing", "missing_storage_root"),
        ("file", "storage_root_not_directory"),
        ("not_writable", "storage_root_not_writable"),
    ],
)
def test_ops_readiness_returns_503_for_unusable_artifact_root(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    mode: str,
    expected_error_code: str,
) -> None:
    db_url = _initialized_db_url(tmp_path)
    artifact_root = tmp_path / "artifacts"
    if mode == "file":
        artifact_root.write_text("not-a-directory", encoding="utf-8")
    elif mode == "not_writable":
        artifact_root.mkdir(parents=True, exist_ok=True)
        monkeypatch.setattr(
            "onetruth.infrastructure.artifacts.storage.os.access",
            lambda _path, _mode: False,
        )

    monkeypatch.setenv("ONETRUTH_ARTIFACT_ROOT", str(artifact_root))
    app = _shared_env_ops_app(db_url)

    status, _headers, body = _invoke(app, method="GET", path="/api/v1/ops/readiness")
    payload = json.loads(body.decode("utf-8"))

    assert status == 503
    assert payload["status"] == "not_ready"
    assert payload["readiness"]["ready"] is False
    assert payload["readiness"]["db"]["ready"] is True
    assert payload["readiness"]["artifact_storage"]["error_code"] == expected_error_code


def test_ops_readiness_surfaces_degraded_warnings_without_failing_core_readiness(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    db_url = _initialized_db_url(tmp_path)
    artifact_root = tmp_path / "artifacts"
    artifact_root.mkdir(parents=True, exist_ok=True)
    monkeypatch.setenv("ONETRUTH_ARTIFACT_ROOT", str(artifact_root))
    _append_visibility_events(db_url)
    app = _shared_env_ops_app(db_url)

    status, _headers, body = _invoke(app, method="GET", path="/api/v1/ops/readiness")
    payload = json.loads(body.decode("utf-8"))

    assert status == 200
    assert payload["status"] == "ok"
    assert payload["readiness"]["ready"] is True
    assert payload["readiness"]["warnings"] == {
        "degradation_visibility_available": True,
        "active_degraded_components": [
            {"component": "projection_cache", "state": "degraded"}
        ],
        "projection_coherence_failed_total": 1,
    }


def _shared_env_ops_app(db_url: str):
    return create_app(
        db_url=db_url,
        boundary_profile="shared_env",
        principal_resolver=unavailable_principal_resolver,
    )


def _initialized_db_url(tmp_path: Path) -> str:
    db_path = tmp_path / "onetruth.db"
    db_url = f"sqlite:///{db_path}"
    connection = open_sqlite_connection(db_url)
    try:
        create_sqlite_substrate(connection)
    finally:
        connection.close()
    return db_url


def _append_visibility_events(db_url: str) -> None:
    connection = open_sqlite_connection(db_url)
    try:
        now = utc_now_iso()
        append_event(
            connection,
            {
                "event_id": event_id_for_type("audit.degraded_mode.changed"),
                "event_type": "audit.degraded_mode.changed",
                "schema_version": "1.0",
                "occurred_at": now,
                "recorded_at": now,
                "tenant_id": "tenant-a",
                "domain_id": "domain-x",
                "actor": {"actor_id": "system:ops", "actor_type": "system"},
                "links": [{"type": "workflow_run", "id": "wr-ops-001"}],
                "payload": {
                    "component": "projection_cache",
                    "from_state": "normal",
                    "to_state": "degraded",
                    "reason": "backlog",
                },
            },
        )
        append_event(
            connection,
            {
                "event_id": event_id_for_type("projection.coherence_failed"),
                "event_type": "projection.coherence_failed",
                "schema_version": "1.0",
                "occurred_at": now,
                "recorded_at": now,
                "tenant_id": "tenant-a",
                "domain_id": "domain-x",
                "actor": {"actor_id": "system:ops", "actor_type": "system"},
                "links": [
                    {"type": "workflow_run", "id": "wr-ops-001"},
                    {"type": "projection", "id": "workflow_workspace"},
                ],
                "payload": {"code": "projection_coherence_failed"},
            },
        )
        connection.commit()
    finally:
        connection.close()


def _invoke(
    app,
    *,
    method: str = "GET",
    path: str = "/",
    headers: dict[str, str] | None = None,
    body: bytes = b"",
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

    async def _call() -> list[dict[str, object]]:
        sent: list[dict[str, object]] = []
        sent_request = False

        async def receive() -> dict[str, object]:
            nonlocal sent_request
            if sent_request:
                return {"type": "http.disconnect"}
            sent_request = True
            return {"type": "http.request", "body": body, "more_body": False}

        async def send(message: dict[str, object]) -> None:
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
