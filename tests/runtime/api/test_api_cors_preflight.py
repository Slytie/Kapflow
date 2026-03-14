from __future__ import annotations

import asyncio
import json
from typing import Any

from onetruth.api.main import create_app


def _invoke(
    app,
    *,
    method: str,
    path: str,
    headers: dict[str, str],
) -> tuple[int, dict[str, str], bytes]:
    raw_headers = [
        (key.encode("latin-1"), value.encode("latin-1"))
        for key, value in headers.items()
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
    start = next(message for message in messages if message["type"] == "http.response.start")
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


def test_options_preflight_returns_cors_headers() -> None:
    app = create_app(
        db_url="sqlite:///:memory:",
        boundary_profile="local_dev",
    )
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
    assert headers["access-control-allow-origin"] == "http://localhost:5173"
    assert "OPTIONS" in headers["access-control-allow-methods"]
    assert "x-onetruth-actor-roles" in headers["access-control-allow-headers"]
    assert "x-request-id" in headers["access-control-expose-headers"]


def test_error_responses_include_cors_headers() -> None:
    app = create_app(
        db_url="sqlite:///:memory:",
        boundary_profile="local_dev",
    )
    status, headers, body = _invoke(
        app,
        method="GET",
        path="/api/v1/workflow-runs",
        headers={"origin": "http://localhost:5173"},
    )

    parsed = json.loads(body.decode("utf-8"))
    assert status == 400
    assert parsed["status"] == "error"
    assert parsed["error"]["code"] == "invalid_request_context"
    assert headers["x-request-id"].startswith("httpreq_")
    assert headers["access-control-allow-origin"] == "http://localhost:5173"
    assert "x-request-id" in headers["access-control-expose-headers"]
