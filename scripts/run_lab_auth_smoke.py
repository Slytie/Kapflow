#!/usr/bin/env python3
from __future__ import annotations

import argparse
import asyncio
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import sys
from typing import Any, Mapping

from onetruth.api.main import create_app
from onetruth.api.shared_env_principal_resolver import (
    build_shared_env_jwt_principal_resolver,
)


LAB_AUTH_SMOKE_REPORT_VERSION = 1


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Run a lab-only shared_env JWT smoke against /api/v1/viewer. "
            "The bearer token is read from an env var or file and is never printed."
        )
    )
    parser.add_argument("--db-url", required=True)
    parser.add_argument("--jwt-issuer", required=True)
    parser.add_argument("--jwt-audience", required=True)
    parser.add_argument("--jwt-public-key-pem-file", required=True)
    token = parser.add_mutually_exclusive_group(required=True)
    token.add_argument("--bearer-token-env")
    token.add_argument("--bearer-token-file")
    parser.add_argument("--json", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    token, token_source = _read_token(
        bearer_token_env=args.bearer_token_env,
        bearer_token_file=Path(args.bearer_token_file) if args.bearer_token_file else None,
    )
    report = run_lab_auth_smoke(
        db_url=str(args.db_url),
        jwt_issuer=str(args.jwt_issuer),
        jwt_audience=str(args.jwt_audience),
        jwt_public_key_pem=Path(args.jwt_public_key_pem_file).read_text(
            encoding="utf-8"
        ),
        bearer_token=token,
        token_source=token_source,
    )
    if args.json:
        sys.stdout.write(json.dumps(report, indent=2, sort_keys=True) + "\n")
    else:
        sys.stdout.write(f"{report['status']}\n")
    return 0 if report["status"] == "passed" else 1


def run_lab_auth_smoke(
    *,
    db_url: str,
    jwt_issuer: str,
    jwt_audience: str,
    jwt_public_key_pem: str,
    bearer_token: str | None,
    token_source: str,
    now_iso: str | None = None,
) -> dict[str, object]:
    resolver = build_shared_env_jwt_principal_resolver(
        issuer=jwt_issuer,
        audience=jwt_audience,
        public_key_pem=jwt_public_key_pem,
    )
    app = create_app(
        db_url=db_url,
        boundary_profile="shared_env",
        principal_resolver=resolver,
    )
    headers = _spoofed_browser_headers()
    if bearer_token is not None and bearer_token.strip():
        headers["authorization"] = f"Bearer {bearer_token.strip()}"

    status_code, _response_headers, body = _invoke_asgi_json(
        app,
        method="GET",
        path="/api/v1/viewer",
        headers=headers,
    )
    payload = json.loads(body.decode("utf-8")) if body else {}
    base_report: dict[str, object] = {
        "manifest_version": LAB_AUTH_SMOKE_REPORT_VERSION,
        "command": "lab.auth.smoke",
        "generated_at": now_iso or _utc_now_iso(),
        "status_code": status_code,
        "token_source": token_source,
        "token_value_recorded": False,
        "public_key_value_recorded": False,
        "conflicting_browser_identity_headers_sent": True,
    }

    if status_code != 200:
        error = payload.get("error") if isinstance(payload, dict) else None
        if not isinstance(error, dict):
            error = {"code": "unexpected_response", "message": "unexpected response"}
        return {
            **base_report,
            "status": "failed",
            "failure_code": str(error.get("code", "unexpected_response")),
            "failure_message": str(error.get("message", "unexpected response")),
        }

    if not isinstance(payload, dict):
        return {
            **base_report,
            "status": "failed",
            "failure_code": "unexpected_response",
            "failure_message": "viewer response was not a JSON object",
        }

    viewer_session = payload.get("viewer_session")
    if not isinstance(viewer_session, dict):
        return {
            **base_report,
            "status": "failed",
            "failure_code": "missing_viewer_session",
            "failure_message": "viewer response did not include viewer_session",
        }

    request_context_mode = viewer_session.get("request_context_mode")
    actor_switching_allowed = viewer_session.get("actor_switching_allowed")
    spoofed_headers_ignored = (
        viewer_session.get("tenant_id") != headers["x-onetruth-tenant-id"]
        and viewer_session.get("domain_id") != headers["x-onetruth-domain-id"]
        and viewer_session.get("actor_id") != headers["x-onetruth-actor-id"]
    )
    assertions = {
        "request_context_mode_server_derived": request_context_mode == "server_derived",
        "actor_switching_disabled": actor_switching_allowed is False,
        "spoofed_headers_ignored": spoofed_headers_ignored,
    }
    passed = all(assertions.values())
    report: dict[str, object] = {
        **base_report,
        "status": "passed" if passed else "failed",
        "boundary_profile": viewer_session.get("boundary_profile"),
        "request_context_mode": request_context_mode,
        "actor_switching_allowed": actor_switching_allowed,
        "spoofed_headers_ignored": spoofed_headers_ignored,
        "viewer_session": {
            "tenant_id": viewer_session.get("tenant_id"),
            "domain_id": viewer_session.get("domain_id"),
            "actor_id": viewer_session.get("actor_id"),
            "actor_type": viewer_session.get("actor_type"),
            "actor_roles": viewer_session.get("actor_roles"),
        },
        "assertions": assertions,
    }
    if not passed:
        report["failure_code"] = "lab_auth_smoke_assertion_failed"
        report["failure_message"] = "shared_env viewer identity assertions failed"
    return report


def _read_token(
    *,
    bearer_token_env: str | None,
    bearer_token_file: Path | None,
) -> tuple[str | None, str]:
    if bearer_token_env is not None:
        return os.environ.get(bearer_token_env), f"env:{bearer_token_env}"
    if bearer_token_file is None:
        raise SystemExit("either --bearer-token-env or --bearer-token-file is required")
    return bearer_token_file.read_text(encoding="utf-8").strip(), (
        f"file:{bearer_token_file.name}"
    )


def _spoofed_browser_headers() -> dict[str, str]:
    return {
        "x-onetruth-tenant-id": "spoofed-browser-tenant",
        "x-onetruth-domain-id": "spoofed-browser-domain",
        "x-onetruth-actor-id": "human:spoofed-browser-actor",
        "x-onetruth-actor-type": "human",
        "x-onetruth-actor-roles": "admin,operator",
    }


def _invoke_asgi_json(
    app,
    *,
    method: str,
    path: str,
    headers: Mapping[str, str],
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
        "client": ("lab-auth-smoke", 0),
        "server": ("lab-auth-smoke", 80),
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
    response_headers = {
        key.decode("latin-1").lower(): value.decode("latin-1")
        for key, value in start.get("headers", [])
    }
    body = b"".join(
        message.get("body", b"")
        for message in messages
        if message["type"] == "http.response.body"
    )
    return int(start["status"]), response_headers, body


def _utc_now_iso() -> str:
    return (
        datetime.now(timezone.utc)
        .replace(microsecond=0)
        .isoformat()
        .replace("+00:00", "Z")
    )


if __name__ == "__main__":
    raise SystemExit(main())
