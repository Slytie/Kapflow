from __future__ import annotations

import sqlite3

import pytest

from onetruth.application.handlers._shared.command_boundary import (
    CommandError,
    _prepare_command_receipt,
)
from onetruth.application.handlers._shared.effect_ledger import (
    EffectPlan,
    effect_payload_hash,
    guarded_effect_mutation,
)
from onetruth.infrastructure.events.event_store import create_sqlite_substrate
from onetruth.infrastructure.repositories.effect_ledger import (
    EffectLedgerError,
    create_effect_ledger_entry,
    effect_ledger_entry_id,
    get_effect_ledger_entry,
)


def _connection() -> sqlite3.Connection:
    connection = sqlite3.connect(":memory:")
    connection.row_factory = sqlite3.Row
    create_sqlite_substrate(connection)
    return connection


def _receipt(*, tenant_id: str = "tenant-a", domain_id: str = "domain-x"):
    receipt = _prepare_command_receipt(
        command_name="tasks.claim",
        payload={
            "human_task_id": "ht-effect-001",
            "idempotency_key": "idem-effect-001",
        },
        fingerprint_payload={
            "human_task_id": "ht-effect-001",
            "actor_id": "agent-a",
        },
        tenant_id=tenant_id,
        domain_id=domain_id,
        workflow_run_id="wr-effect-001",
        idempotency_required=True,
    )
    assert receipt is not None
    return receipt


def _effect_plan(payload: dict[str, object] | None = None) -> EffectPlan:
    return EffectPlan(
        effect_key="task-claim-row",
        effect_kind="db_mutation",
        target_kind="human_task",
        target_ref="human_task:ht-effect-001",
        payload=dict(payload or {"human_task_id": "ht-effect-001", "lease_version": 1}),
    )


def test_effect_payload_hash_and_entry_id_are_deterministic() -> None:
    assert (
        effect_payload_hash({"b": 2, "a": 1})
        == "sha256:43258cff783fe7036d8a43033f830adfc60ec037382473548ac742b888292777"
    )
    assert effect_payload_hash({"a": 1, "b": 2}) == effect_payload_hash({"b": 2, "a": 1})
    assert effect_ledger_entry_id(
        command_name="tasks.claim",
        scope_key='["ht-effect-001"]',
        idempotency_key="idem-effect-001",
        effect_key="task-claim-row",
    ).startswith("effect-ledger:")


def test_guarded_effect_mutation_applies_once_and_replays_matching_effect() -> None:
    connection = _connection()
    receipt = _receipt()
    plan = _effect_plan()
    calls = 0

    def _mutation() -> dict[str, object]:
        nonlocal calls
        calls += 1
        return {"human_task_id": "ht-effect-001", "lease_version": 1}

    first_result, first_replay = guarded_effect_mutation(
        connection,
        receipt=receipt,
        effects=[plan],
        mutation=_mutation,
    )
    second_result, second_replay = guarded_effect_mutation(
        connection,
        receipt=receipt,
        effects=[plan],
        mutation=_mutation,
    )

    assert first_result == second_result
    assert first_replay is False
    assert second_replay is True
    assert calls == 1
    row = get_effect_ledger_entry(
        connection,
        command_name=receipt.command_name,
        scope_key=receipt.scope_key,
        idempotency_key=receipt.idempotency_key,
        effect_key=plan.effect_key,
    )
    assert row is not None
    assert row["status"] == "applied"
    assert row["payload_hash"] == effect_payload_hash(plan.payload)


def test_guarded_effect_mutation_rejects_same_effect_key_with_different_payload() -> None:
    connection = _connection()
    receipt = _receipt()
    guarded_effect_mutation(
        connection,
        receipt=receipt,
        effects=[_effect_plan({"human_task_id": "ht-effect-001", "lease_version": 1})],
        mutation=lambda: {"human_task_id": "ht-effect-001", "lease_version": 1},
    )

    with pytest.raises(CommandError) as excinfo:
        guarded_effect_mutation(
            connection,
            receipt=receipt,
            effects=[_effect_plan({"human_task_id": "ht-effect-001", "lease_version": 2})],
            mutation=lambda: {"human_task_id": "ht-effect-001", "lease_version": 2},
        )

    assert excinfo.value.code == "effect_ledger_conflict"
    rows = connection.execute("SELECT COUNT(*) AS count FROM effect_ledger_entries").fetchone()
    assert rows is not None
    assert int(rows["count"]) == 1


def test_guarded_effect_mutation_rollback_leaves_no_partial_effects() -> None:
    connection = _connection()
    receipt = _receipt()

    def _boom() -> dict[str, object]:
        raise RuntimeError("mutation failed")

    with pytest.raises(RuntimeError):
        guarded_effect_mutation(
            connection,
            receipt=receipt,
            effects=[_effect_plan()],
            mutation=_boom,
        )

    rows = connection.execute("SELECT COUNT(*) AS count FROM effect_ledger_entries").fetchone()
    assert rows is not None
    assert int(rows["count"]) == 0


def test_guarded_effect_mutation_rejects_scope_mismatch_for_existing_effect() -> None:
    connection = _connection()
    receipt = _receipt(tenant_id="tenant-a")
    guarded_effect_mutation(
        connection,
        receipt=receipt,
        effects=[_effect_plan()],
        mutation=lambda: {"human_task_id": "ht-effect-001", "lease_version": 1},
    )
    mismatched_receipt = _receipt(tenant_id="tenant-b")

    with pytest.raises(CommandError) as excinfo:
        guarded_effect_mutation(
            connection,
            receipt=mismatched_receipt,
            effects=[_effect_plan()],
            mutation=lambda: {"human_task_id": "ht-effect-001", "lease_version": 1},
        )

    assert excinfo.value.code == "effect_ledger_conflict"
    assert "tenant_id" in excinfo.value.details["mismatched_fields"]


def test_guarded_effect_mutation_rejects_duplicate_effect_keys() -> None:
    connection = _connection()

    with pytest.raises(CommandError) as excinfo:
        guarded_effect_mutation(
            connection,
            receipt=_receipt(),
            effects=[_effect_plan(), _effect_plan()],
            mutation=lambda: {},
        )

    assert excinfo.value.code == "effect_ledger_duplicate_effect_key"


def test_guarded_effect_mutation_rejects_raw_material_and_invalid_refs() -> None:
    connection = _connection()
    with pytest.raises(CommandError) as raw_excinfo:
        guarded_effect_mutation(
            connection,
            receipt=_receipt(),
            effects=[_effect_plan({"raw_text": "do not store me"})],
            mutation=lambda: {},
        )
    assert raw_excinfo.value.code == "effect_ledger_raw_material"

    with pytest.raises(CommandError) as ref_excinfo:
        guarded_effect_mutation(
            connection,
            receipt=_receipt(),
            effects=[
                EffectPlan(
                    effect_key="bad-ref",
                    effect_kind="db_mutation",
                    target_kind="human_task",
                    target_ref="/tmp/raw/source.pdf",
                    payload={"human_task_id": "ht-effect-001"},
                )
            ],
            mutation=lambda: {},
        )
    assert ref_excinfo.value.code == "effect_ledger_invalid_target_ref"


def test_effect_ledger_repository_rejects_bad_digest() -> None:
    connection = _connection()
    receipt = _receipt()

    with pytest.raises(EffectLedgerError) as excinfo:
        create_effect_ledger_entry(
            connection,
            tenant_id=receipt.tenant_id,
            domain_id=receipt.domain_id,
            workflow_run_id=receipt.workflow_run_id,
            command_name=receipt.command_name,
            scope_key=receipt.scope_key,
            idempotency_key=receipt.idempotency_key,
            request_fingerprint="bad-digest",
            request_fingerprint_profile=receipt.request_fingerprint_profile,
            effect_key="bad-digest-row",
            effect_kind="db_mutation",
            target_kind="human_task",
            target_ref="human_task:ht-effect-001",
            payload_json={"human_task_id": "ht-effect-001"},
        )

    assert excinfo.value.code == "effect_ledger_bad_digest"
