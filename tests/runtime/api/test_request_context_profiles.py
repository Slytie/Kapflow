from __future__ import annotations

import asyncio
import json
import time
from pathlib import Path
from typing import Any

import jwt
import pytest

from onetruth.api.dependencies import RequestContext
from onetruth.api.main import create_app
from tests.runtime.helpers.runtime_cli import run_cli

pytestmark = pytest.mark.filterwarnings(
    "ignore:The RSA key is 1024 bits long*:jwt.warnings.InsecureKeyLengthWarning"
)


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


_JWT_ISSUER = "https://issuer.onetruth.test"
_JWT_AUDIENCE = "onetruth-shared-env"
_JWT_PRIVATE_KEY = """-----BEGIN PRIVATE KEY-----
MIICdwIBADANBgkqhkiG9w0BAQEFAASCAmEwggJdAgEAAoGBAL50ZaBOaoQfcoqO
+JHukgf+eRHeaNGl8UVgKLHtiGAmdGaOlfI//bKA61yHSvOxA6bOmBljdjFA8LbZ
chrYayydB8mYJWD4yleY/+sL8OEtaGB0kclg3Jff8vpouHPoy1Tsuxl0npxfbwKJ
jU7k9xejjQenpvcnyJy2994LFSIlAgMBAAECgYBMyjGPiQ55ZxSPuUWP0Vkf0AKQ
qdQpc3bsOfEujE9INTkJgMQEgLiRmFlNXV9jEiQexX2d/vRQt5ZWoyXWnRvYlwiO
u3t7aW+QC4I188hQUyqTIArFFwDse2QWYHpYGzp4uA/ElsxqWidjD9FBYE01Fztg
3olUjC84dZMd7FJrAQJBAN1t/wi1zglU88VFuWI3C+CdDbK/sSSY3aZua+tBYSkF
RF1+ZYh2bruakgw9z/QyQyzygoPtu2Q9CDiCduBNAo0CQQDcMGfbXpxrv4xVI6og
K7noKg0hyuoaQkxvdLp4CGPX2lU0ZWzxB7FCAFWaVUwU+kGgEHtuzg1wk/uvQJaH
PgP5AkB8cpKwcYVvxzgOOkabhXZ+caY+PPAxMlz4afzrRl518IjgxuYHkRBhDdlh
WegjRZBtlYp23UjBaG/TWre3DnENAkEA15btmXTBYx5hoNsSr/0gQZkq0nODU8Km
ZFq+WNieKbK0ymCkkjsd66m4JyxtGf0OVFLPCGbn8dpzC90JhdHKwQJBAKeiGx4F
Vpm0Ehd7HE0dorIrH5hqz6tabDRHekqc/q4614d8cqUxRepHgMz4Eql1ORf/L4u6
UvE2PJSAIQ0bt9w=
-----END PRIVATE KEY-----"""
_JWT_PUBLIC_KEY = """-----BEGIN PUBLIC KEY-----
MIGfMA0GCSqGSIb3DQEBAQUAA4GNADCBiQKBgQC+dGWgTmqEH3KKjviR7pIH/nkR
3mjRpfFFYCix7YhgJnRmjpXyP/2ygOtch0rzsQOmzpgZY3YxQPC22XIa2GssnQfJ
mCVg+MpXmP/rC/DhLWhgdJHJYNyX3/L6aLhz6MtU7LsZdJ6cX28CiY1O5PcXo40H
p6b3J8ictvfeCxUiJQIDAQAB
-----END PUBLIC KEY-----"""
_WRONG_JWT_PUBLIC_KEY = """-----BEGIN PUBLIC KEY-----
MIGfMA0GCSqGSIb3DQEBAQUAA4GNADCBiQKBgQC/W8cGREfIVmLNbMZuYrBdeAEa
1aY/ZUudttLs4ea7KPOq8abdcasphlYcL52uKZbPf+6TOvFwCbV79njIIzdxx8q1
yfAFjQ6Gj7xQzu4WoDjLTunVUZ4Np3UwYqm+A+I//GQgcxlIU5aFKPbigLpEJNYf
wFucH890LCXoCJQDMQIDAQAB
-----END PUBLIC KEY-----"""


def _configure_shared_env_jwt(monkeypatch, *, public_key: str = _JWT_PUBLIC_KEY) -> None:
    monkeypatch.setenv("ONETRUTH_SHARED_ENV_JWT_ISSUER", _JWT_ISSUER)
    monkeypatch.setenv("ONETRUTH_SHARED_ENV_JWT_AUDIENCE", _JWT_AUDIENCE)
    monkeypatch.setenv("ONETRUTH_SHARED_ENV_JWT_PUBLIC_KEY_PEM", public_key)


def _jwt_token(
    *,
    issuer: str = _JWT_ISSUER,
    audience: str = _JWT_AUDIENCE,
    exp: int | None = None,
    extra_claims: dict[str, Any] | None = None,
) -> str:
    claims: dict[str, Any] = {
        "iss": issuer,
        "aud": audience,
        "sub": "service:shared-gateway",
        "tenant_id": "tenant-a",
        "domain_id": "domain-x",
        "actor_type": "service",
        "actor_roles": ["dispatch_supervisor"],
        "exp": exp if exp is not None else int(time.time()) + 300,
    }
    if extra_claims:
        claims.update(extra_claims)
    return jwt.encode(claims, _JWT_PRIVATE_KEY, algorithm="RS256")


def _authorization_headers(token: str | None) -> dict[str, str]:
    headers = dict(_trusted_headers())
    if token is not None:
        headers["authorization"] = f"Bearer {token}"
    return headers


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


def test_shared_env_accepts_configured_bearer_jwt(
    tmp_path: Path,
    monkeypatch,
) -> None:
    _configure_shared_env_jwt(monkeypatch)
    db_url = _initialized_db_url(tmp_path, "shared-env-jwt-resolver")
    app = create_app(db_url=db_url)

    status, headers, body = _invoke(
        app,
        method="GET",
        path="/api/v1/workflow-runs",
        headers=_authorization_headers(_jwt_token()),
    )

    parsed = _parsed_json(body)
    assert status == 200
    assert parsed["status"] == "ok"
    assert parsed["workflow_runs"] == []
    assert headers["x-request-id"].startswith("httpreq_")
    assert "access-control-allow-origin" not in headers


def test_shared_env_configured_jwt_requires_bearer_token(
    monkeypatch,
) -> None:
    _configure_shared_env_jwt(monkeypatch)
    app = create_app(db_url="sqlite:///:memory:")

    status, headers, body = _invoke(
        app,
        method="GET",
        path="/api/v1/workflow-runs",
        headers=_trusted_headers(),
    )

    parsed = _parsed_json(body)
    assert status == 401
    assert parsed["status"] == "error"
    assert parsed["error"]["code"] == "missing_bearer_token"
    assert headers["x-request-id"].startswith("httpreq_")
    assert "access-control-allow-origin" not in headers


def test_shared_env_configured_jwt_rejects_invalid_tokens(
    monkeypatch,
) -> None:
    cases = (
        ("invalid_signature", _WRONG_JWT_PUBLIC_KEY, _jwt_token()),
        ("invalid_issuer", _JWT_PUBLIC_KEY, _jwt_token(issuer="https://wrong-issuer.test")),
        ("invalid_audience", _JWT_PUBLIC_KEY, _jwt_token(audience="wrong-audience")),
        ("expired", _JWT_PUBLIC_KEY, _jwt_token(exp=int(time.time()) - 60)),
        ("missing_claims", _JWT_PUBLIC_KEY, _jwt_token(extra_claims={"actor_roles": None})),
    )

    for _, public_key, token in cases:
        _configure_shared_env_jwt(monkeypatch, public_key=public_key)
        app = create_app(db_url="sqlite:///:memory:")

        status, headers, body = _invoke(
            app,
            method="GET",
            path="/api/v1/workflow-runs",
            headers=_authorization_headers(token),
        )

        parsed = _parsed_json(body)
        assert status == 401
        assert parsed["status"] == "error"
        assert parsed["error"]["code"] == "invalid_attested_identity"
        assert parsed["error"]["details"]["boundary_profile"] == "shared_env"
        assert headers["x-request-id"].startswith("httpreq_")


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
