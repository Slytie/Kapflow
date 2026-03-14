from __future__ import annotations

import asyncio
from dataclasses import dataclass
import json
from pathlib import Path
import sys
from typing import Any
from urllib.parse import urlencode

REPO_ROOT = Path(__file__).resolve().parents[3]
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from onetruth.api.main import create_app


@dataclass(frozen=True)
class ApiResult:
    status_code: int
    payload: dict[str, Any]


@dataclass(frozen=True)
class RawApiResult:
    status_code: int
    headers: dict[str, str]
    body: bytes


class RuntimeApiClient:
    def __init__(
        self,
        *,
        db_url: str,
        tenant_id: str,
        domain_id: str,
        actor_id: str,
        actor_type: str,
        actor_roles: list[str],
        boundary_profile: str = "ci_test",
    ) -> None:
        self.app = create_app(
            db_url=db_url,
            boundary_profile=boundary_profile,
        )
        self.default_headers = {
            "x-onetruth-tenant-id": tenant_id,
            "x-onetruth-domain-id": domain_id,
            "x-onetruth-actor-id": actor_id,
            "x-onetruth-actor-type": actor_type,
            "x-onetruth-actor-roles": ",".join(actor_roles),
        }

    def get(
        self,
        path: str,
        *,
        query: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
    ) -> ApiResult:
        return self.request("GET", path, query=query, headers=headers)

    def post(
        self,
        path: str,
        *,
        payload: dict[str, Any],
        query: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
    ) -> ApiResult:
        return self.request("POST", path, payload=payload, query=query, headers=headers)

    def request(
        self,
        method: str,
        path: str,
        *,
        payload: dict[str, Any] | None = None,
        query: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
    ) -> ApiResult:
        raw = self.request_raw(
            method,
            path,
            payload=payload,
            query=query,
            headers=headers,
        )
        parsed = json.loads(raw.body.decode("utf-8")) if raw.body else {}
        return ApiResult(status_code=raw.status_code, payload=parsed)

    def get_raw(
        self,
        path: str,
        *,
        query: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
    ) -> RawApiResult:
        return self.request_raw("GET", path, query=query, headers=headers)

    def request_raw(
        self,
        method: str,
        path: str,
        *,
        payload: dict[str, Any] | None = None,
        query: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
    ) -> RawApiResult:
        all_headers = dict(self.default_headers)
        if headers:
            all_headers.update({key.lower(): value for key, value in headers.items()})

        body = b""
        if payload is not None:
            all_headers["content-type"] = "application/json"
            body = json.dumps(payload, separators=(",", ":")).encode("utf-8")

        raw_headers = [(key.encode("latin-1"), value.encode("latin-1")) for key, value in all_headers.items()]
        query_string = b""
        if query:
            query_string = urlencode(query, doseq=True).encode("latin-1")

        scope = {
            "type": "http",
            "asgi": {"version": "3.0"},
            "http_version": "1.1",
            "method": method.upper(),
            "scheme": "http",
            "path": path,
            "raw_path": path.encode("latin-1"),
            "query_string": query_string,
            "headers": raw_headers,
            "client": ("testclient", 1234),
            "server": ("testserver", 80),
        }

        async def _invoke() -> list[dict[str, Any]]:
            sent: list[dict[str, Any]] = []
            sent_request = False

            async def receive() -> dict[str, Any]:
                nonlocal sent_request
                if sent_request:
                    return {"type": "http.disconnect"}
                sent_request = True
                return {"type": "http.request", "body": body, "more_body": False}

            async def send(message: dict[str, Any]) -> None:
                sent.append(message)

            await self.app(scope, receive, send)
            return sent

        messages = asyncio.run(_invoke())
        start = next(message for message in messages if message["type"] == "http.response.start")
        start_headers = {
            key.decode("latin-1").lower(): value.decode("latin-1")
            for key, value in start.get("headers", [])
        }
        body_messages = [
            message for message in messages if message["type"] == "http.response.body"
        ]
        body_bytes = b"".join(message.get("body", b"") for message in body_messages)
        return RawApiResult(
            status_code=int(start["status"]),
            headers=start_headers,
            body=body_bytes,
        )
