from __future__ import annotations

import sqlite3

import pytest

from onetruth.capex_platform.workpage_projection_commands import (
    WorkpageCommandEnvelope,
    WorkpageCommandEnvelopeError,
    execute_guarded_workpage_command,
    sign_projection_cursor,
    validate_workpage_command_envelope,
)
from onetruth.infrastructure.events.event_store import create_sqlite_substrate
from onetruth.infrastructure.repositories.capex_projects import create_capex_project
from onetruth.infrastructure.repositories.capex_workpage_projections import (
    create_projection_snapshot,
    mark_projection_snapshot_stale,
)


TENANT_ID = "tenant-a"
DOMAIN_ID = "domain-x"
PROJECT_ID = "cp-command"
SNAPSHOT_ID = "wps-command"
WORKPAGE_KIND = "capex-source-review-v0"
NOW = "2026-06-08T00:00:00Z"
EXPIRES = "2026-06-08T01:00:00Z"
SIGNING_KEY = "unit-test-signing-key"


def _connection() -> sqlite3.Connection:
    connection = sqlite3.connect(":memory:")
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON;")
    create_sqlite_substrate(connection)
    create_capex_project(
        connection,
        project_id=PROJECT_ID,
        tenant_id=TENANT_ID,
        domain_id=DOMAIN_ID,
        project_key="CAPEX-COMMAND",
        name="Command project",
        state="active",
        metadata_json={},
        created_by_actor_id="human:admin",
        created_by_actor_type="human",
        created_at=NOW,
    )
    return connection


def _snapshot(connection: sqlite3.Connection) -> dict[str, object]:
    return create_projection_snapshot(
        connection,
        projection_snapshot_id=SNAPSHOT_ID,
        tenant_id=TENANT_ID,
        domain_id=DOMAIN_ID,
        project_id=PROJECT_ID,
        workpage_kind=WORKPAGE_KIND,
        projection_kind="capex.project_source_review",
        renderer_version="capex.projection.renderer.v1",
        basis_version_vector_json={"basis_refs": ["source_occurrence:so-command"]},
        state="current",
        payload_metadata_json={},
        created_by_actor_id="system:projection",
        created_by_actor_type="system",
        created_at=NOW,
    )


def _envelope(snapshot: dict[str, object], *, cursor: str | None = None) -> WorkpageCommandEnvelope:
    signed_cursor = cursor or sign_projection_cursor(
        projection_snapshot_id=SNAPSHOT_ID,
        tenant_id=TENANT_ID,
        domain_id=DOMAIN_ID,
        project_id=PROJECT_ID,
        basis_hash=str(snapshot["basis_hash"]),
        issued_at=NOW,
        expires_at=EXPIRES,
        signing_key=SIGNING_KEY,
    )
    return WorkpageCommandEnvelope(
        tenant_id=TENANT_ID,
        domain_id=DOMAIN_ID,
        project_id=PROJECT_ID,
        workpage_kind=WORKPAGE_KIND,
        command_type="promote_review_basis",
        actor_id="human:reviewer",
        actor_type="human",
        idempotency_key="unit:capex-command",
        projection_snapshot_id=SNAPSHOT_ID,
        signed_cursor=signed_cursor,
        expected_basis_hash=str(snapshot["basis_hash"]),
        payload={"subject_ref": "source_occurrence:so-command"},
    )


def test_valid_command_envelope_allows_mutation_callback() -> None:
    connection = _connection()
    try:
        snapshot = _snapshot(connection)
        calls = 0

        def _operation(validated_snapshot: dict[str, object]) -> dict[str, object]:
            nonlocal calls
            calls += 1
            return {
                "projection_snapshot_id": validated_snapshot["projection_snapshot_id"],
                "mutated": True,
            }

        result = execute_guarded_workpage_command(
            connection,
            _envelope(snapshot),
            signing_key=SIGNING_KEY,
            now_iso=NOW,
            operation=_operation,
        )

        assert calls == 1
        assert result == {"projection_snapshot_id": SNAPSHOT_ID, "mutated": True}
    finally:
        connection.close()


@pytest.mark.parametrize(
    ("mutation", "expected_code"),
    [
        ("tamper_signature", "invalid_projection_cursor_signature"),
        ("expired", "expired_projection_cursor"),
        ("scope_mismatch", "projection_cursor_scope_mismatch"),
        ("basis_mismatch", "stale_projection_basis"),
        ("stale_snapshot", "stale_projection_snapshot"),
    ],
)
def test_command_envelope_rejects_stale_or_invalid_projection_before_mutation(
    mutation: str,
    expected_code: str,
) -> None:
    connection = _connection()
    try:
        snapshot = _snapshot(connection)
        if mutation == "tamper_signature":
            envelope = _envelope(snapshot, cursor=_envelope(snapshot).signed_cursor[:-1] + "x")
        elif mutation == "expired":
            envelope = _envelope(snapshot)
        elif mutation == "scope_mismatch":
            wrong_cursor = sign_projection_cursor(
                projection_snapshot_id=SNAPSHOT_ID,
                tenant_id=TENANT_ID,
                domain_id=DOMAIN_ID,
                project_id="cp-other",
                basis_hash=str(snapshot["basis_hash"]),
                issued_at=NOW,
                expires_at=EXPIRES,
                signing_key=SIGNING_KEY,
            )
            envelope = _envelope(snapshot, cursor=wrong_cursor)
        elif mutation == "basis_mismatch":
            envelope = WorkpageCommandEnvelope(
                **{
                    **_envelope(snapshot).__dict__,
                    "expected_basis_hash": "0" * 64,
                }
            )
        else:
            mark_projection_snapshot_stale(
                connection,
                projection_snapshot_id=SNAPSHOT_ID,
                stale_reason="basis_ref_changed:source_occurrence:so-command",
                stale_at="2026-06-08T00:30:00Z",
            )
            envelope = _envelope(snapshot)

        calls = 0

        def _operation(_snapshot: dict[str, object]) -> dict[str, object]:
            nonlocal calls
            calls += 1
            return {"mutated": True}

        with pytest.raises(WorkpageCommandEnvelopeError) as exc_info:
            execute_guarded_workpage_command(
                connection,
                envelope,
                signing_key=SIGNING_KEY,
                now_iso="2026-06-08T02:00:00Z" if mutation == "expired" else NOW,
                operation=_operation,
            )

        assert exc_info.value.code == expected_code
        assert calls == 0
    finally:
        connection.close()


def test_command_envelope_validation_requires_explicit_signing_key() -> None:
    connection = _connection()
    try:
        snapshot = _snapshot(connection)

        with pytest.raises(WorkpageCommandEnvelopeError) as exc_info:
            validate_workpage_command_envelope(
                connection,
                _envelope(snapshot),
                signing_key="",
                now_iso=NOW,
            )

        assert exc_info.value.code == "missing_projection_cursor_signing_key"
    finally:
        connection.close()
