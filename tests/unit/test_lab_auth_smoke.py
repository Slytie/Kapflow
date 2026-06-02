from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator
import jwt
import pytest

from scripts.run_lab_auth_smoke import run_lab_auth_smoke

pytestmark = pytest.mark.filterwarnings(
    "ignore:The RSA key is 1024 bits long*:jwt.warnings.InsecureKeyLengthWarning"
)

REPO_ROOT = Path(__file__).resolve().parents[2]
JWT_ISSUER = "https://issuer.onetruth.test"
JWT_AUDIENCE = "onetruth-lab-smoke"
JWT_PRIVATE_KEY = """-----BEGIN PRIVATE KEY-----
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
JWT_PUBLIC_KEY = """-----BEGIN PUBLIC KEY-----
MIGfMA0GCSqGSIb3DQEBAQUAA4GNADCBiQKBgQC+dGWgTmqEH3KKjviR7pIH/nkR
3mjRpfFFYCix7YhgJnRmjpXyP/2ygOtch0rzsQOmzpgZY3YxQPC22XIa2GssnQfJ
mCVg+MpXmP/rC/DhLWhgdJHJYNyX3/L6aLhz6MtU7LsZdJ6cX28CiY1O5PcXo40H
p6b3J8ictvfeCxUiJQIDAQAB
-----END PUBLIC KEY-----"""


def test_lab_auth_smoke_accepts_jwt_and_ignores_spoofed_browser_headers() -> None:
    token = _jwt_token()

    report = run_lab_auth_smoke(
        db_url="sqlite:///:memory:",
        jwt_issuer=JWT_ISSUER,
        jwt_audience=JWT_AUDIENCE,
        jwt_public_key_pem=JWT_PUBLIC_KEY,
        bearer_token=token,
        token_source="env:LAB_VIEWER_SMOKE_TOKEN",
        now_iso="2026-06-02T00:00:00Z",
    )

    _validate_lab_auth_report(report)
    assert report["status"] == "passed"
    assert report["request_context_mode"] == "server_derived"
    assert report["actor_switching_allowed"] is False
    assert report["spoofed_headers_ignored"] is True
    assert report["viewer_session"] == {
        "tenant_id": "tenant-lab",
        "domain_id": "domain-capex-lab",
        "actor_id": "service:lab-gateway",
        "actor_type": "service",
        "actor_roles": ["lab_pilot_viewer"],
    }

    serialized = json.dumps(report, sort_keys=True)
    assert token not in serialized
    assert JWT_PUBLIC_KEY not in serialized


def test_lab_auth_smoke_reports_missing_bearer_token_without_leaking_values() -> None:
    report = run_lab_auth_smoke(
        db_url="sqlite:///:memory:",
        jwt_issuer=JWT_ISSUER,
        jwt_audience=JWT_AUDIENCE,
        jwt_public_key_pem=JWT_PUBLIC_KEY,
        bearer_token=None,
        token_source="env:LAB_VIEWER_SMOKE_TOKEN",
        now_iso="2026-06-02T00:00:00Z",
    )

    _validate_lab_auth_report(report)
    assert report["status"] == "failed"
    assert report["failure_code"] == "missing_bearer_token"
    assert report["token_value_recorded"] is False


def test_lab_auth_smoke_reports_invalid_bearer_token_without_token_echo() -> None:
    token = "not-a-valid-jwt"

    report = run_lab_auth_smoke(
        db_url="sqlite:///:memory:",
        jwt_issuer=JWT_ISSUER,
        jwt_audience=JWT_AUDIENCE,
        jwt_public_key_pem=JWT_PUBLIC_KEY,
        bearer_token=token,
        token_source="env:LAB_VIEWER_SMOKE_TOKEN",
        now_iso="2026-06-02T00:00:00Z",
    )

    _validate_lab_auth_report(report)
    assert report["status"] == "failed"
    assert report["failure_code"] == "invalid_attested_identity"
    assert token not in json.dumps(report, sort_keys=True)


def _jwt_token(
    *,
    issuer: str = JWT_ISSUER,
    audience: str = JWT_AUDIENCE,
    exp: int | None = None,
    extra_claims: dict[str, Any] | None = None,
) -> str:
    claims: dict[str, Any] = {
        "iss": issuer,
        "aud": audience,
        "sub": "service:lab-gateway",
        "tenant_id": "tenant-lab",
        "domain_id": "domain-capex-lab",
        "actor_type": "service",
        "actor_roles": ["lab_pilot_viewer"],
        "exp": exp if exp is not None else int(time.time()) + 300,
    }
    if extra_claims:
        claims.update(extra_claims)
    return jwt.encode(claims, JWT_PRIVATE_KEY, algorithm="RS256")


def _validate_lab_auth_report(report: dict[str, object]) -> None:
    schema = json.loads(
        (REPO_ROOT / "schemas/ops/lab_auth_smoke_report.schema.json").read_text(
            encoding="utf-8"
        )
    )
    Draft202012Validator(schema).validate(report)
