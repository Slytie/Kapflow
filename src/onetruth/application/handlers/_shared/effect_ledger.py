from __future__ import annotations

from dataclasses import dataclass, field
import sqlite3
from typing import Any, Callable, Sequence

from onetruth.application.handlers._shared.command_boundary import (
    CommandError,
    CommandReceiptContext,
    command_transaction,
)
from onetruth.infrastructure.repositories.effect_ledger import (
    EffectLedgerError,
    create_effect_ledger_entry,
    get_effect_ledger_entry,
    mark_effect_ledger_entry_applied,
    sha256_digest,
)


@dataclass(frozen=True)
class EffectPlan:
    effect_key: str
    effect_kind: str
    target_kind: str
    target_ref: str
    payload: dict[str, Any]
    metadata: dict[str, Any] = field(default_factory=dict)


def effect_payload_hash(payload: dict[str, Any]) -> str:
    return sha256_digest(payload)


def _as_command_error(error: EffectLedgerError) -> CommandError:
    return CommandError(code=error.code, message=error.message, details=error.details)


def _assert_unique_effect_keys(effects: Sequence[EffectPlan]) -> None:
    seen: set[str] = set()
    duplicates: list[str] = []
    for effect in effects:
        if effect.effect_key in seen:
            duplicates.append(effect.effect_key)
        seen.add(effect.effect_key)
    if duplicates:
        raise CommandError(
            code="effect_ledger_duplicate_effect_key",
            message="effect ledger plans must not repeat effect_key values",
            details={"duplicate_effect_keys": sorted(set(duplicates))},
        )


def _assert_existing_effect_matches(
    existing: dict[str, Any],
    *,
    receipt: CommandReceiptContext,
    effect: EffectPlan,
) -> None:
    expected_payload_hash = effect_payload_hash(effect.payload)
    mismatched_fields = [
        field
        for field, expected in {
            "tenant_id": receipt.tenant_id,
            "domain_id": receipt.domain_id,
            "workflow_run_id": receipt.workflow_run_id,
            "request_fingerprint": receipt.request_fingerprint,
            "request_fingerprint_profile": receipt.request_fingerprint_profile,
            "effect_kind": effect.effect_kind,
            "target_kind": effect.target_kind,
            "target_ref": effect.target_ref,
            "payload_hash": expected_payload_hash,
        }.items()
        if existing.get(field) != expected
    ]
    if mismatched_fields:
        raise CommandError(
            code="effect_ledger_conflict",
            message="effect key already exists with different command scope or payload",
            details={
                "effect_key": effect.effect_key,
                "mismatched_fields": sorted(mismatched_fields),
            },
        )


def guarded_effect_mutation(
    connection: sqlite3.Connection,
    *,
    receipt: CommandReceiptContext,
    effects: Sequence[EffectPlan],
    mutation: Callable[[], dict[str, Any]],
) -> tuple[dict[str, Any], bool]:
    """Reserve effect rows, run the mutation once, and replay matching applied effects."""

    if receipt.tenant_id is None or receipt.domain_id is None:
        raise CommandError(
            code="effect_ledger_scope_required",
            message="guarded mutations require tenant and domain scope",
            details={"tenant_id": receipt.tenant_id, "domain_id": receipt.domain_id},
        )
    if not effects:
        raise CommandError(
            code="effect_ledger_effect_required",
            message="guarded mutations require at least one effect plan",
            details={},
        )
    _assert_unique_effect_keys(effects)

    try:
        with command_transaction(connection):
            existing_entries: list[dict[str, Any] | None] = []
            for effect in effects:
                existing = get_effect_ledger_entry(
                    connection,
                    command_name=receipt.command_name,
                    scope_key=receipt.scope_key,
                    idempotency_key=receipt.idempotency_key,
                    effect_key=effect.effect_key,
                )
                if existing is not None:
                    _assert_existing_effect_matches(existing, receipt=receipt, effect=effect)
                existing_entries.append(existing)

            if all(entry is not None for entry in existing_entries):
                applied_entries = [entry for entry in existing_entries if entry is not None]
                if any(entry["status"] != "applied" for entry in applied_entries):
                    raise CommandError(
                        code="effect_ledger_conflict",
                        message="effect key is reserved but not applied",
                        details={
                            "effect_keys": [
                                str(entry["effect_key"])
                                for entry in applied_entries
                                if entry["status"] != "applied"
                            ]
                        },
                    )
                result = applied_entries[0]["result_json"]
                if result is None:
                    raise CommandError(
                        code="effect_ledger_corrupt",
                        message="applied effect ledger row is missing result_json",
                        details={"effect_key": applied_entries[0]["effect_key"]},
                    )
                return dict(result), True

            if any(entry is not None for entry in existing_entries):
                raise CommandError(
                    code="effect_ledger_conflict",
                    message="effect ledger has a partial reservation for this command",
                    details={
                        "effect_keys": [
                            effect.effect_key
                            for effect, entry in zip(effects, existing_entries)
                            if entry is not None
                        ]
                    },
                )

            for effect in effects:
                create_effect_ledger_entry(
                    connection,
                    tenant_id=receipt.tenant_id,
                    domain_id=receipt.domain_id,
                    workflow_run_id=receipt.workflow_run_id,
                    command_name=receipt.command_name,
                    scope_key=receipt.scope_key,
                    idempotency_key=receipt.idempotency_key,
                    request_fingerprint=receipt.request_fingerprint,
                    request_fingerprint_profile=receipt.request_fingerprint_profile,
                    effect_key=effect.effect_key,
                    effect_kind=effect.effect_kind,
                    target_kind=effect.target_kind,
                    target_ref=effect.target_ref,
                    payload_json=effect.payload,
                    metadata_json=effect.metadata,
                )

            result = mutation()
            for effect in effects:
                mark_effect_ledger_entry_applied(
                    connection,
                    command_name=receipt.command_name,
                    scope_key=receipt.scope_key,
                    idempotency_key=receipt.idempotency_key,
                    effect_key=effect.effect_key,
                    result_json=result,
                )
            return result, False
    except EffectLedgerError as exc:
        raise _as_command_error(exc) from exc
