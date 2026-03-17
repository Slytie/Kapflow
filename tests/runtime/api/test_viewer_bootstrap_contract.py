from __future__ import annotations

import asyncio
import json

from onetruth.api.dependencies import RequestContext
from onetruth.api.main import create_app


def _trusted_headers() -> dict[str, str]:
    return {
        "x-onetruth-tenant-id": "tenant-a",
        "x-onetruth-domain-id": "domain-x",
        "x-onetruth-actor-id": "human:dispatch-supervisor-1",
        "x-onetruth-actor-type": "human",
        "x-onetruth-actor-roles": "dispatch_supervisor",
    }


def _invoke(
    app,
    *,
    method: str = "GET",
    path: str = "/api/v1/viewer",
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
    response_body = b"".join(
        message.get("body", b"")
        for message in messages
        if message["type"] == "http.response.body"
    )
    return int(start["status"]), start_headers, response_body


def _parsed_json(body: bytes) -> dict[str, object]:
    assert body
    return json.loads(body.decode("utf-8"))


def test_viewer_bootstrap_local_dev_uses_trusted_headers() -> None:
    app = create_app(
        db_url="sqlite:///:memory:",
        boundary_profile="local_dev",
    )

    status, headers, body = _invoke(
        app,
        headers=_trusted_headers(),
    )

    parsed = _parsed_json(body)
    assert status == 200
    assert headers["x-request-id"].startswith("httpreq_")
    assert parsed["status"] == "ok"
    assert parsed["command"] == "api.viewer.bootstrap"
    assert parsed["viewer_session"] == {
        "tenant_id": "tenant-a",
        "domain_id": "domain-x",
        "actor_id": "human:dispatch-supervisor-1",
        "actor_type": "human",
        "actor_roles": ["dispatch_supervisor"],
        "boundary_profile": "local_dev",
        "request_context_mode": "trusted_headers",
        "actor_switching_allowed": True,
    }


def test_viewer_bootstrap_shared_env_reflects_server_derived_principal() -> None:
    app = create_app(
        db_url="sqlite:///:memory:",
        boundary_profile="shared_env",
        principal_resolver=lambda _headers: RequestContext(
            tenant_id="tenant-b",
            domain_id="domain-y",
            actor_id="service:shared-gateway",
            actor_type="service",
            actor_roles=("dispatch_supervisor",),
        ),
    )

    status, _headers, body = _invoke(
        app,
        headers={
            **_trusted_headers(),
            "x-onetruth-tenant-id": "tenant-conflict",
            "x-onetruth-domain-id": "domain-conflict",
            "x-onetruth-actor-id": "human:browser-actor",
            "x-onetruth-actor-type": "human",
            "x-onetruth-actor-roles": "operations_manager",
        },
    )

    parsed = _parsed_json(body)
    assert status == 200
    assert parsed["viewer_session"] == {
        "tenant_id": "tenant-b",
        "domain_id": "domain-y",
        "actor_id": "service:shared-gateway",
        "actor_type": "service",
        "actor_roles": ["dispatch_supervisor"],
        "boundary_profile": "shared_env",
        "request_context_mode": "server_derived",
        "actor_switching_allowed": False,
    }
