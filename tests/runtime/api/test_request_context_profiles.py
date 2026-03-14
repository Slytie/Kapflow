from __future__ import annotations

import asyncio
import json
from pathlib import Path

from onetruth.api.dependencies import RequestContext
from onetruth.api.main import create_app
from tests.runtime.helpers.runtime_cli import run_cli


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

    async def _call() -> list[dict[str, object]]:
        sent: list[dict[str, object]] = []
        sent_request = False

        async def receive() -> dict[str, object]:
            nonlocal sent_request
            if sent_request:
                return {"type": "http.disconnect"}
            sent_request = True
            return {"type": "http.request", "body": b"", "more_body": False}

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
    body = b"".join(
        message.get("body", b"")
        for message in messages
        if message["type"] == "http.response.body"
    )
    return int(start["status"]), start_headers, body


def _parsed_json(body: bytes) -> dict[str, object]:
    assert body
    return json.loads(body.decode("utf-8"))


def _trusted_headers() -> dict[str, str]:
    return {
        "x-onetruth-tenant-id": "tenant-a",
        "x-onetruth-domain-id": "domain-x",
        "x-onetruth-actor-id": "human:dispatch-supervisor-1",
        "x-onetruth-actor-type": "human",
        "x-onetruth-actor-roles": "dispatch_supervisor",
    }


def _initialized_db_url(tmp_path: Path, name: str) -> str:
    db_path = tmp_path / f"{name}.db"
    db_url = f"sqlite:///{db_path}"
    run_cli("--db-url", db_url, "init-db")
    return db_url


def test_shared_env_default_fails_closed_without_principal_resolver() -> None:
    app = create_app(db_url="sqlite:///:memory:")

    status, headers, body = _invoke(
        app,
        method="GET",
        path="/api/v1/workflow-runs",
        headers=_trusted_headers(),
    )

    parsed = _parsed_json(body)
    assert status == 503
    assert parsed["status"] == "error"
    assert parsed["error"]["code"] == "principal_resolver_unavailable"
    assert headers["x-request-id"].startswith("httpreq_")
    assert "access-control-allow-origin" not in headers


def test_shared_env_accepts_injected_principal_resolver(tmp_path: Path) -> None:
    db_url = _initialized_db_url(tmp_path, "shared-env-injected-resolver")
    app = create_app(
        db_url=db_url,
        principal_resolver=lambda headers: RequestContext(
            tenant_id="tenant-a",
            domain_id="domain-x",
            actor_id="service:gateway",
            actor_type="service",
            actor_roles=("dispatch_supervisor",),
        ),
    )

    status, headers, body = _invoke(
        app,
        method="GET",
        path="/api/v1/workflow-runs",
    )

    parsed = _parsed_json(body)
    assert status == 200
    assert parsed["status"] == "ok"
    assert parsed["workflow_runs"] == []
    assert headers["x-request-id"].startswith("httpreq_")
    assert "access-control-allow-origin" not in headers


def test_local_dev_profile_accepts_trusted_headers(tmp_path: Path) -> None:
    db_url = _initialized_db_url(tmp_path, "local-dev-profile")
    app = create_app(
        db_url=db_url,
        boundary_profile="local_dev",
    )

    status, headers, body = _invoke(
        app,
        method="GET",
        path="/api/v1/workflow-runs",
        headers=_trusted_headers(),
    )

    parsed = _parsed_json(body)
    assert status == 200
    assert parsed["status"] == "ok"
    assert parsed["workflow_runs"] == []
    assert headers["x-request-id"].startswith("httpreq_")


def test_ci_test_profile_accepts_trusted_headers(tmp_path: Path) -> None:
    db_url = _initialized_db_url(tmp_path, "ci-test-profile")
    app = create_app(
        db_url=db_url,
        boundary_profile="ci_test",
    )

    status, headers, body = _invoke(
        app,
        method="GET",
        path="/api/v1/workflow-runs",
        headers=_trusted_headers(),
    )

    parsed = _parsed_json(body)
    assert status == 200
    assert parsed["status"] == "ok"
    assert parsed["workflow_runs"] == []
    assert headers["x-request-id"].startswith("httpreq_")
    assert "access-control-allow-origin" not in headers


def test_local_dev_cors_reflects_only_loopback_origins() -> None:
    app = create_app(
        db_url="sqlite:///:memory:",
        boundary_profile="local_dev",
    )

    trusted_header_request = {
        "access-control-request-method": "GET",
        "access-control-request-headers": (
            "x-onetruth-tenant-id,x-onetruth-domain-id,"
            "x-onetruth-actor-id,x-onetruth-actor-type,x-onetruth-actor-roles"
        ),
    }
    allowed_status, allowed_headers, allowed_body = _invoke(
        app,
        method="OPTIONS",
        path="/api/v1/workflow-runs",
        headers={
            "origin": "http://localhost:5173",
            **trusted_header_request,
        },
    )
    denied_status, denied_headers, denied_body = _invoke(
        app,
        method="OPTIONS",
        path="/api/v1/workflow-runs",
        headers={
            "origin": "https://evil.example.com",
            **trusted_header_request,
        },
    )

    assert allowed_status == 204
    assert allowed_body == b""
    assert allowed_headers["x-request-id"].startswith("httpreq_")
    assert (
        allowed_headers["access-control-allow-origin"] == "http://localhost:5173"
    )
    assert "x-onetruth-actor-roles" in allowed_headers["access-control-allow-headers"]
    assert "x-request-id" in allowed_headers["access-control-expose-headers"]

    assert denied_status == 204
    assert denied_body == b""
    assert denied_headers["x-request-id"].startswith("httpreq_")
    assert "access-control-allow-origin" not in denied_headers
    assert "access-control-allow-headers" not in denied_headers


def test_shared_env_does_not_advertise_trusted_header_cors() -> None:
    app = create_app(db_url="sqlite:///:memory:")

    status, headers, body = _invoke(
        app,
        method="OPTIONS",
        path="/api/v1/workflow-runs",
        headers={
            "origin": "http://localhost:5173",
            "access-control-request-method": "GET",
            "access-control-request-headers": (
                "x-onetruth-tenant-id,x-onetruth-domain-id,"
                "x-onetruth-actor-id,x-onetruth-actor-type,x-onetruth-actor-roles"
            ),
        },
    )

    assert status == 204
    assert body == b""
    assert headers["x-request-id"].startswith("httpreq_")
    assert "access-control-allow-origin" not in headers
    assert "access-control-allow-headers" not in headers
    assert "access-control-expose-headers" not in headers
