from __future__ import annotations

import asyncio
import json
import re
from typing import Any

from onetruth.api.main import create_app

REQUEST_ID_PATTERN = re.compile(r"^httpreq_[0-9a-f]{32}$")


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
    path: str = "/",
    headers: dict[str, str] | None = None,
    body: bytes = b"",
    scope_type: str = "http",
) -> tuple[int, dict[str, str], bytes]:
    raw_headers = [
        (key.encode("latin-1"), value.encode("latin-1"))
        for key, value in (headers or {}).items()
    ]
    scope = {
        "type": scope_type,
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


def _parsed_json(body: bytes) -> dict[str, object]:
    assert body
    return json.loads(body.decode("utf-8"))


def _assert_generated_request_id(request_id: str) -> None:
    assert REQUEST_ID_PATTERN.fullmatch(request_id), request_id


def test_api_shell_unknown_path_and_method_mismatch_return_not_found_with_request_id() -> None:
    app = create_app(
        db_url="sqlite:///:memory:",
        boundary_profile="ci_test",
    )

    for method, path in [
        ("GET", "/api/v1/not-a-route"),
        ("POST", "/api/v1/workflow-runs"),
    ]:
        status, headers, body = _invoke(
            app,
            method=method,
            path=path,
            headers=_trusted_headers(),
        )

        parsed = _parsed_json(body)
        assert status == 404
        assert parsed["status"] == "error"
        assert parsed["error"]["code"] == "not_found"
        assert parsed["error"]["details"] == {"method": method, "path": path}
        _assert_generated_request_id(headers["x-request-id"])


def test_api_shell_invalid_json_echoes_valid_request_id() -> None:
    app = create_app(
        db_url="sqlite:///:memory:",
        boundary_profile="ci_test",
    )

    status, headers, body = _invoke(
        app,
        method="POST",
        path="/api/v1/human-tasks/ht-stage06-review/claim",
        headers={
            **_trusted_headers(),
            "content-type": "application/json",
            "x-request-id": "client-request-123",
        },
        body=b"{",
    )

    parsed = _parsed_json(body)
    assert status == 400
    assert parsed["status"] == "error"
    assert parsed["error"]["code"] == "invalid_json"
    assert headers["x-request-id"] == "client-request-123"


def test_api_shell_non_object_json_generates_request_id_for_unusable_header() -> None:
    app = create_app(
        db_url="sqlite:///:memory:",
        boundary_profile="ci_test",
    )

    status, headers, body = _invoke(
        app,
        method="POST",
        path="/api/v1/human-tasks/ht-stage06-review/claim",
        headers={
            **_trusted_headers(),
            "content-type": "application/json",
            "x-request-id": " " * 8,
        },
        body=b"[]",
    )

    parsed = _parsed_json(body)
    assert status == 400
    assert parsed["status"] == "error"
    assert parsed["error"]["code"] == "invalid_payload"
    _assert_generated_request_id(headers["x-request-id"])


def test_api_shell_non_http_scope_returns_unsupported_scope_with_request_id() -> None:
    app = create_app(db_url="sqlite:///:memory:")

    status, headers, body = _invoke(
        app,
        scope_type="websocket",
    )

    parsed = _parsed_json(body)
    assert status == 500
    assert parsed["status"] == "error"
    assert parsed["error"]["code"] == "unsupported_scope"
    _assert_generated_request_id(headers["x-request-id"])


def test_api_shell_unhandled_exceptions_return_internal_error_without_leaking_message() -> None:
    def _boom(_headers: dict[str, str]) -> Any:
        raise RuntimeError("do not leak me")

    app = create_app(
        db_url="sqlite:///:memory:",
        principal_resolver=_boom,
    )

    status, headers, body = _invoke(
        app,
        method="GET",
        path="/api/v1/workflow-runs",
    )

    parsed = _parsed_json(body)
    assert status == 500
    assert parsed["status"] == "error"
    assert parsed["error"]["code"] == "internal_error"
    assert parsed["error"]["details"] == {"exception": "RuntimeError"}
    assert "do not leak me" not in body.decode("utf-8")
    _assert_generated_request_id(headers["x-request-id"])
