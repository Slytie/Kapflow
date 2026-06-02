from __future__ import annotations

import json
import time
from pathlib import Path

import jwt
import pytest

from tests.runtime.helpers.runtime_api import RuntimeApiClient
from tests.runtime.helpers.runtime_cli import run_cli

pytestmark = pytest.mark.filterwarnings(
    "ignore:The RSA key is 1024 bits long*:jwt.warnings.InsecureKeyLengthWarning"
)

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


def _initialized_db_url(tmp_path: Path, name: str) -> str:
    db_path = tmp_path / f"{name}.db"
    db_url = f"sqlite:///{db_path}"
    run_cli("--db-url", db_url, "init-db")
    return db_url


def _configure_shared_env_jwt(monkeypatch) -> None:
    monkeypatch.setenv("ONETRUTH_SHARED_ENV_JWT_ISSUER", _JWT_ISSUER)
    monkeypatch.setenv("ONETRUTH_SHARED_ENV_JWT_AUDIENCE", _JWT_AUDIENCE)
    monkeypatch.setenv("ONETRUTH_SHARED_ENV_JWT_PUBLIC_KEY_PEM", _JWT_PUBLIC_KEY)


def _jwt_token() -> str:
    claims = {
        "iss": _JWT_ISSUER,
        "aud": _JWT_AUDIENCE,
        "sub": "service:shared-gateway",
        "tenant_id": "tenant-a",
        "domain_id": "domain-x",
        "actor_type": "service",
        "actor_roles": ["dispatch_supervisor"],
        "exp": int(time.time()) + 300,
    }
    return jwt.encode(claims, _JWT_PRIVATE_KEY, algorithm="RS256")


def test_shared_env_uses_attested_identity_and_ignores_trusted_headers(
    tmp_path: Path,
    monkeypatch,
) -> None:
    _configure_shared_env_jwt(monkeypatch)
    client = RuntimeApiClient(
        db_url=_initialized_db_url(tmp_path, "shared-env-attested-identity"),
        tenant_id="tenant-b",
        domain_id="domain-y",
        actor_id="human:header-only-actor",
        actor_type="human",
        actor_roles=["dispatch_supervisor"],
        boundary_profile="shared_env",
    )

    tenant_denied = client.get(
        "/api/v1/workflow-runs",
        query={"tenant_id": "tenant-b"},
        headers={"authorization": f"Bearer {_jwt_token()}"},
    )

    assert tenant_denied.status_code == 403
    assert tenant_denied.payload["error"]["code"] == "scope_filter_denied"
    assert tenant_denied.payload["error"]["details"]["tenant_id"] == "tenant-b"
    assert tenant_denied.payload["error"]["details"]["context_tenant_id"] == "tenant-a"

    domain_denied = client.get(
        "/api/v1/workflow-runs",
        query={"domain_id": "domain-y"},
        headers={"authorization": f"Bearer {_jwt_token()}"},
    )

    assert domain_denied.status_code == 403
    assert domain_denied.payload["error"]["code"] == "scope_filter_denied"
    assert domain_denied.payload["error"]["details"]["domain_id"] == "domain-y"
    assert domain_denied.payload["error"]["details"]["context_domain_id"] == "domain-x"


def test_shared_env_rejects_authoritative_inmem_artifact_download(
    tmp_path: Path,
    monkeypatch,
) -> None:
    _configure_shared_env_jwt(monkeypatch)
    db_url = _initialized_db_url(tmp_path, "shared-env-inmem-download")
    workflow_payload = {
        "workflow_run_id": "wr-shared-env-inmem-download",
        "workflow_id": "schedule_planning.v1",
        "workflow_version": "v1",
        "tenant_id": "tenant-a",
        "domain_id": "domain-x",
        "partition_key": "SD-2026-03-13",
        "logical_date": "2026-03-13",
        "activation_key": "shared-env-inmem-download",
        "idempotency_key": "idem:shared-env-inmem-download:run",
    }
    run_cli("--db-url", db_url, "runs", "create", "--json", json.dumps(workflow_payload))
    artifact_payload = {
        "artifact_version_id": "av-shared-env-inmem-download",
        "workflow_run_id": "wr-shared-env-inmem-download",
        "artifact_kind": "schedule.supervisor_review.doc",
        "artifact_role": "evidence",
        "media_type": "application/octet-stream",
        "storage_uri": "inmem://shared-env/download/probe",
        "content_digest": "sha256:" + ("b" * 64),
        "metadata_json": {"probe": "shared-env-inmem"},
        "idempotency_key": "idem:shared-env-inmem-download:artifact",
    }
    run_cli(
        "--db-url",
        db_url,
        "artifacts",
        "create-version",
        "--json",
        json.dumps(artifact_payload),
    )
    client = RuntimeApiClient(
        db_url=db_url,
        tenant_id="tenant-a",
        domain_id="domain-x",
        actor_id="human:ignored-header-actor",
        actor_type="human",
        actor_roles=["dispatch_supervisor"],
        boundary_profile="shared_env",
    )

    response = client.get(
        "/api/v1/artifacts/av-shared-env-inmem-download/download",
        headers={"authorization": f"Bearer {_jwt_token()}"},
    )

    assert response.status_code == 403
    assert response.payload["error"]["code"] == "artifact_storage_forbidden"
