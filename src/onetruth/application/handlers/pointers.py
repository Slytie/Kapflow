from __future__ import annotations

import sqlite3
from typing import Any

from onetruth.application.handlers._shared.artifact_effects import (
    _canonical_artifact_scope_fields,
    _capture_artifact_input_binding,
    _capture_input_binding,
    _input_binding_key,
)
from onetruth.application.handlers._shared.command_boundary import (
    CommandError,
    _command_receipt_payload,
    _event_envelope,
    _execute_with_command_receipt,
    _prepare_command_receipt,
    _receipt_event_idempotency_key,
    _require_fields,
    _validate_task_run_belongs_to_workflow,
    _workflow_scope,
)
from onetruth.domain.pointer_address import (
    PartitionRef,
    PointerAddress,
    PointerAddressError,
    PointerId,
    RegistryKind,
    resolve_legacy_pointer_address,
)
from onetruth.infrastructure.events.event_store import append_event, utc_now_iso
from onetruth.infrastructure.repositories.approvals import get_approval
from onetruth.infrastructure.repositories.artifact_pointers import (
    PointerConflictError,
    PointerDefinitionMismatchError,
    PointerGenerationMismatchError,
    get_pointer,
    promote_pointer,
)
from onetruth.infrastructure.repositories.artifact_versions import get_artifact_version


def promote_pointer_command(
    connection: sqlite3.Connection,
    payload: dict[str, Any],
    *,
    include_receipt: bool = False,
) -> dict[str, Any]:
    _require_fields(
        payload,
        [
            "workflow_run_id",
            "scope_kind",
            "scope_ref",
            "pointer_key",
            "artifact_kind",
            "artifact_version_id",
            "idempotency_key",
        ],
    )
    workflow_run_id = str(payload["workflow_run_id"])
    scope_kind = str(payload["scope_kind"])
    scope_ref = str(payload["scope_ref"])
    pointer_key = str(payload["pointer_key"])
    artifact_kind = str(payload["artifact_kind"])
    artifact_version_id = str(payload["artifact_version_id"])
    receipt = _prepare_command_receipt(
        command_name="pointers.promote",
        payload=payload,
        fingerprint_payload={
            "workflow_run_id": workflow_run_id,
            "scope_kind": scope_kind,
            "scope_ref": scope_ref,
            "pointer_key": pointer_key,
            "artifact_kind": artifact_kind,
            "artifact_version_id": artifact_version_id,
            "promotion_reason": payload.get("promotion_reason"),
            "promoted_by_task_run_id": payload.get("promoted_by_task_run_id"),
            "approved_by_approval_id": payload.get("approved_by_approval_id"),
            "expected_generation": payload.get("expected_generation"),
            "stream_key": payload.get("stream_key"),
            "registry_kind": payload.get("registry_kind"),
            "reviewed_artifact_version_id": payload.get("reviewed_artifact_version_id"),
            "reviewed_base_artifact_version_id": payload.get("reviewed_base_artifact_version_id"),
            "base_pointer_key": payload.get("base_pointer_key"),
            "drift_reason": payload.get("drift_reason"),
            "actor_id": payload.get("actor_id", "system:runtime"),
            "actor_type": payload.get("actor_type", "system"),
        },
        tenant_id=None,
        domain_id=None,
        workflow_run_id=workflow_run_id,
        idempotency_required=True,
    )
    event_idempotency = _receipt_event_idempotency_key(
        receipt,
        "pointers.promote.artifact.pointer.promoted",
    )
    drift_idempotency = _receipt_event_idempotency_key(
        receipt,
        "pointers.promote.artifact.pointer.drift_detected",
    )

    def _operation() -> dict[str, Any]:
        workflow_scope = _workflow_scope(connection, workflow_run_id)
        artifact_version = get_artifact_version(connection, artifact_version_id)
        if artifact_version is None:
            raise CommandError(
                code="artifact_version_not_found",
                message="artifact version not found for pointer promotion",
                details={"artifact_version_id": artifact_version_id},
            )
        expected_artifact_scope = _canonical_artifact_scope_fields(
            tenant_id=workflow_scope["tenant_id"],
            domain_id=workflow_scope["domain_id"],
            workflow_partition_key=workflow_scope["partition_key"],
            artifact_kind=artifact_kind,
        )
        artifact_scope = _load_artifact_canonical_scope(
            connection,
            artifact_version_id=artifact_version_id,
        )
        _assert_artifact_matches_expected_scope(
            artifact_version_id=artifact_version_id,
            expected_scope=expected_artifact_scope,
            artifact_scope=artifact_scope,
            context="promotion_target",
        )

        promotion_reason = (
            str(payload["promotion_reason"])
            if payload.get("promotion_reason") is not None
            else None
        )
        actor_type = str(payload.get("actor_type", "system"))
        if promotion_reason in {"official_publish", "official_major_replan"} and actor_type != "human":
            raise CommandError(
                code="official_promotion_requires_human_actor",
                message="official pointer promotion must be performed by a human actor",
                details={"promotion_reason": promotion_reason, "actor_type": actor_type},
            )
        approved_by_approval_id = (
            str(payload["approved_by_approval_id"])
            if payload.get("approved_by_approval_id") is not None
            else None
        )
        if promotion_reason in {"official_publish", "official_major_replan"} and approved_by_approval_id is None:
            raise CommandError(
                code="approval_required_for_promotion",
                message=f"{promotion_reason} promotions require approved_by_approval_id",
                details={"promotion_reason": promotion_reason},
            )
        if approved_by_approval_id is not None:
            approval = get_approval(connection, approved_by_approval_id)
            if approval is None:
                raise CommandError(
                    code="approval_not_found",
                    message="approved_by_approval_id was not found",
                    details={"approved_by_approval_id": approved_by_approval_id},
                )
            if str(approval["workflow_run_id"]) != workflow_run_id:
                raise CommandError(
                    code="cross_workflow_approval_reference",
                    message="approval belongs to a different workflow_run",
                    details={
                        "approved_by_approval_id": approved_by_approval_id,
                        "approval_workflow_run_id": str(approval["workflow_run_id"]),
                        "workflow_run_id": workflow_run_id,
                    },
                )
            if str(approval["state"]) != "RESPONDED" or str(approval.get("response_kind")) != "approve":
                raise CommandError(
                    code="approval_not_approved",
                    message="pointer promotion requires an approved approval response",
                    details={
                        "approved_by_approval_id": approved_by_approval_id,
                        "state": str(approval["state"]),
                        "response_kind": approval.get("response_kind"),
                    },
                )
            if (
                promotion_reason == "official_major_replan"
                and str(approval.get("scope_ref")) != "Stage07"
            ):
                raise CommandError(
                    code="major_replan_approval_required",
                    message="official_major_replan requires a Stage07 approval response",
                    details={
                        "approved_by_approval_id": approved_by_approval_id,
                        "scope_ref": str(approval.get("scope_ref")),
                    },
                )

        promoted_by_task_run_id = (
            str(payload["promoted_by_task_run_id"])
            if payload.get("promoted_by_task_run_id") is not None
            else None
        )
        if promoted_by_task_run_id is not None:
            _validate_task_run_belongs_to_workflow(
                connection,
                task_run_id=promoted_by_task_run_id,
                workflow_run_id=workflow_run_id,
            )

        canonical_pointer_identity = _canonical_pointer_identity_fields(
            tenant_id=workflow_scope["tenant_id"],
            domain_id=workflow_scope["domain_id"],
            workflow_partition_key=workflow_scope["partition_key"],
            workflow_run_id=workflow_run_id,
            pointer_key=pointer_key,
            scope_kind=scope_kind,
            scope_ref=scope_ref,
            artifact_kind=artifact_kind,
            stream_key=(
                str(payload["stream_key"])
                if payload.get("stream_key") is not None
                else None
            ),
            registry_kind=payload.get("registry_kind"),
        )
        if canonical_pointer_identity["pointer_id"] is None:
            raise CommandError(
                code="pointer_identity_unresolved",
                message="canonical pointer identity could not be resolved safely",
                details={
                    "workflow_run_id": workflow_run_id,
                    "pointer_key": pointer_key,
                    "artifact_kind": artifact_kind,
                },
            )
        prior_target_pointer = get_pointer(
            connection,
            workflow_run_id=workflow_run_id,
            pointer_key=pointer_key,
        )
        now = utc_now_iso()
        pointer, changed = promote_pointer(
            connection,
            workflow_run_id=workflow_run_id,
            pointer_key=pointer_key,
            scope_kind=scope_kind,
            scope_ref=scope_ref,
            artifact_kind=artifact_kind,
            artifact_version_id=artifact_version_id,
            promotion_reason=promotion_reason,
            promoted_by_task_run_id=promoted_by_task_run_id,
            approved_by_approval_id=approved_by_approval_id,
            updated_at=now,
            expected_generation=(
                int(payload["expected_generation"])
                if payload.get("expected_generation") is not None
                else None
            ),
            pointer_id=canonical_pointer_identity["pointer_id"],
            tenant_id=canonical_pointer_identity["tenant_id"],
            domain_id=canonical_pointer_identity["domain_id"],
            dataset_key=canonical_pointer_identity["dataset_key"],
            partition_kind=canonical_pointer_identity["partition_kind"],
            partition_key=canonical_pointer_identity["partition_key"],
            stream_key=canonical_pointer_identity["stream_key"],
            registry_kind=canonical_pointer_identity["registry_kind"],
        )
        if not changed:
            raise CommandError(
                code="pointer_already_current",
                message="pointer already targets requested artifact_version_id",
                details={
                    "workflow_run_id": workflow_run_id,
                    "pointer_key": pointer_key,
                    "artifact_version_id": artifact_version_id,
                },
            )
        canonical_pointer_id = str(pointer.get("pointer_id") or "").strip()
        if not canonical_pointer_id:
            raise CommandError(
                code="pointer_identity_unresolved",
                message="canonical pointer identity missing after promotion",
                details={
                    "workflow_run_id": workflow_run_id,
                    "pointer_key": pointer_key,
                },
            )
        canonical_dataset_key = str(
            pointer.get("dataset_key")
            or canonical_pointer_identity.get("dataset_key")
            or ""
        ).strip().lower()
        if not canonical_dataset_key:
            raise CommandError(
                code="pointer_identity_unresolved",
                message="canonical pointer dataset key missing after promotion",
                details={
                    "workflow_run_id": workflow_run_id,
                    "pointer_key": pointer_key,
                },
            )

        if prior_target_pointer is not None:
            _capture_pointer_input_binding(
                connection,
                workflow_run_id=workflow_run_id,
                task_run_id=promoted_by_task_run_id,
                binding_key=_input_binding_key(
                    prefix="pointer.promote.target_before",
                    event_idempotency=event_idempotency,
                    discriminator=pointer_key,
                ),
                pointer_key=pointer_key,
                pointer=prior_target_pointer,
                captured_at=now,
                metadata_json={
                    "capture_reason": "pointer_promotion_target_before_update",
                    "promotion_pointer_key": pointer_key,
                },
            )

        links = [
            {"rel": "subject", "type": "pointer", "id": canonical_pointer_id},
            {"rel": "subject", "type": "workflow_run", "id": workflow_run_id},
            {"rel": "subject", "type": "artifact_version", "id": artifact_version_id},
        ]
        reviewed_artifact_version_id = (
            str(payload["reviewed_artifact_version_id"])
            if payload.get("reviewed_artifact_version_id") is not None
            else (
                str(payload["reviewed_base_artifact_version_id"])
                if payload.get("reviewed_base_artifact_version_id") is not None
                else None
            )
        )
        append_event(
            connection,
            _event_envelope(
                event_type="artifact.pointer.promoted",
                tenant_id=workflow_scope["tenant_id"],
                domain_id=workflow_scope["domain_id"],
                actor_type=actor_type,
                actor_id=str(payload.get("actor_id", "system:runtime")),
                links=links,
                payload={
                    "pointer_id": canonical_pointer_id,
                    "dataset_key": canonical_dataset_key,
                    "promoted_artifact_version_id": artifact_version_id,
                    "reviewed_artifact_version_id": reviewed_artifact_version_id,
                },
                idempotency_key=event_idempotency,
            ),
        )

        if reviewed_artifact_version_id is not None:
            _capture_artifact_input_binding(
                connection,
                workflow_run_id=workflow_run_id,
                task_run_id=promoted_by_task_run_id,
                binding_key=_input_binding_key(
                    prefix="pointer.promote.reviewed_artifact",
                    event_idempotency=event_idempotency,
                    discriminator=reviewed_artifact_version_id,
                ),
                source_ref=reviewed_artifact_version_id,
                artifact_version_id=reviewed_artifact_version_id,
                captured_at=now,
                metadata_json={
                    "capture_reason": "pointer_promotion_reviewed_artifact",
                    "promotion_pointer_key": pointer_key,
                },
            )

        drift_detected = False
        drift_reason = (
            str(payload["drift_reason"])
            if payload.get("drift_reason") is not None
            else None
        )
        reviewed_base_artifact_version_id = (
            str(payload["reviewed_base_artifact_version_id"])
            if payload.get("reviewed_base_artifact_version_id") is not None
            else None
        )
        if reviewed_base_artifact_version_id is not None:
            base_pointer_key = str(
                payload.get("base_pointer_key") or "official:schedule.published_schedule.workbook"
            )
            base_pointer = get_pointer(
                connection,
                workflow_run_id=workflow_run_id,
                pointer_key=base_pointer_key,
            )
            if base_pointer is None:
                raise CommandError(
                    code="base_pointer_not_found",
                    message="base pointer was not found for drift check",
                    details={
                        "workflow_run_id": workflow_run_id,
                        "base_pointer_key": base_pointer_key,
                    },
                )
            _capture_pointer_input_binding(
                connection,
                workflow_run_id=workflow_run_id,
                task_run_id=promoted_by_task_run_id,
                binding_key=_input_binding_key(
                    prefix="pointer.promote.reviewed_base_pointer",
                    event_idempotency=event_idempotency,
                    discriminator=base_pointer_key,
                ),
                pointer_key=base_pointer_key,
                pointer=base_pointer,
                captured_at=now,
                metadata_json={
                    "capture_reason": "pointer_promotion_reviewed_base_pointer",
                    "promotion_pointer_key": pointer_key,
                },
            )
            current_base_artifact_version_id = str(base_pointer["artifact_version_id"])
            if reviewed_base_artifact_version_id != current_base_artifact_version_id:
                drift_detected = True
                if drift_reason is None:
                    drift_reason = "reviewed_base_version_stale_at_promotion"
        elif (
            reviewed_artifact_version_id is not None
            and reviewed_artifact_version_id != artifact_version_id
        ):
            drift_detected = True
            if drift_reason is None:
                drift_reason = "reviewed_version_differs_from_promoted_version"

        if drift_detected:
            append_event(
                connection,
                _event_envelope(
                    event_type="artifact.pointer.drift_detected",
                    tenant_id=workflow_scope["tenant_id"],
                    domain_id=workflow_scope["domain_id"],
                    actor_type=actor_type,
                    actor_id=str(payload.get("actor_id", "system:runtime")),
                    links=links,
                    payload={
                        "pointer_id": canonical_pointer_id,
                        "dataset_key": canonical_dataset_key,
                        "reviewed_artifact_version_id": str(
                            reviewed_artifact_version_id or reviewed_base_artifact_version_id
                        ),
                        "promoted_artifact_version_id": artifact_version_id,
                        "drift_reason": drift_reason,
                    },
                    idempotency_key=drift_idempotency,
                ),
            )
        promoted_pointer = get_pointer(
            connection,
            workflow_run_id=workflow_run_id,
            pointer_key=pointer_key,
        )
        if promoted_pointer is None:
            raise CommandError(
                code="pointer_not_found",
                message="pointer not found after promotion",
                details={
                    "workflow_run_id": workflow_run_id,
                    "pointer_key": pointer_key,
                },
            )
        return promoted_pointer

    try:
        result, replay = _execute_with_command_receipt(
            connection,
            receipt=receipt,
            operation=_operation,
        )
    except (PointerConflictError, PointerGenerationMismatchError, PointerDefinitionMismatchError) as exc:
        if isinstance(exc, PointerConflictError):
            raise CommandError(
                code="pointer_conflict",
                message=str(exc),
                details={
                    "pointer_key": exc.pointer_key,
                    "current_artifact_version_id": exc.current_artifact_version_id,
                    "current_generation": exc.generation,
                },
            ) from exc
        if isinstance(exc, PointerGenerationMismatchError):
            raise CommandError(
                code="pointer_generation_mismatch",
                message=str(exc),
                details={
                    "pointer_key": exc.pointer_key,
                    "expected_generation": exc.expected_generation,
                    "actual_generation": exc.actual_generation,
                },
            ) from exc
        raise CommandError(
            code="pointer_definition_mismatch",
            message=str(exc),
            details={"pointer_key": exc.pointer_key},
        ) from exc
    except sqlite3.IntegrityError as exc:
        raise CommandError(
            code="pointer_conflict",
            message="pointer promotion violated uniqueness constraints",
            details={
                "workflow_run_id": workflow_run_id,
                "pointer_key": pointer_key,
            },
        ) from exc

    return _command_receipt_payload(
        result,
        receipt=receipt,
        replay=replay,
        include_receipt=include_receipt,
    )


def _canonical_pointer_identity_fields(
    *,
    tenant_id: str,
    domain_id: str,
    workflow_partition_key: str,
    workflow_run_id: str,
    pointer_key: str,
    scope_kind: str,
    scope_ref: str,
    artifact_kind: str,
    stream_key: str | None,
    registry_kind: Any,
) -> dict[str, str | None]:
    canonical_scope = _canonical_artifact_scope_fields(
        tenant_id=tenant_id,
        domain_id=domain_id,
        workflow_partition_key=workflow_partition_key,
        artifact_kind=artifact_kind,
    )
    normalized_stream_key = str(stream_key) if stream_key is not None else None
    try:
        normalized_registry_kind = RegistryKind.parse(registry_kind).value
    except PointerAddressError:
        normalized_registry_kind = RegistryKind.SINGLETON.value

    try:
        resolved = resolve_legacy_pointer_address(
            workflow_run_id=workflow_run_id,
            pointer_key=pointer_key,
            scope_kind=scope_kind,
            scope_ref=scope_ref,
            artifact_kind=artifact_kind,
            tenant_id=tenant_id,
            domain_id=domain_id,
            workflow_partition_key=workflow_partition_key,
            stream_key=normalized_stream_key,
            registry_kind=normalized_registry_kind,
        )
        return {
            "pointer_id": str(resolved.pointer_id),
            "tenant_id": resolved.address.tenant_id,
            "domain_id": resolved.address.domain_id,
            "dataset_key": resolved.address.dataset_key,
            "partition_kind": resolved.address.partition_ref.key,
            "partition_key": resolved.address.partition_ref.value,
            "stream_key": resolved.address.stream_key,
            "registry_kind": resolved.registry_kind.value,
        }
    except PointerAddressError:
        fallback_pointer_id: str | None = None
        if canonical_scope["partition_kind"] is not None and canonical_scope["partition_key"] is not None:
            try:
                fallback_address = PointerAddress(
                    tenant_id=str(canonical_scope["tenant_id"]),
                    domain_id=str(canonical_scope["domain_id"]),
                    dataset_key=str(canonical_scope["dataset_key"]),
                    partition_ref=PartitionRef(
                        key=str(canonical_scope["partition_kind"]),
                        value=str(canonical_scope["partition_key"]),
                    ),
                    stream_key=normalized_stream_key,
                )
                fallback_pointer_id = str(PointerId.from_address(fallback_address))
            except PointerAddressError:
                fallback_pointer_id = None
        return {
            "pointer_id": fallback_pointer_id,
            "tenant_id": canonical_scope["tenant_id"],
            "domain_id": canonical_scope["domain_id"],
            "dataset_key": canonical_scope["dataset_key"],
            "partition_kind": canonical_scope["partition_kind"],
            "partition_key": canonical_scope["partition_key"],
            "stream_key": normalized_stream_key,
            "registry_kind": normalized_registry_kind,
        }


def _load_artifact_canonical_scope(
    connection: sqlite3.Connection,
    *,
    artifact_version_id: str,
) -> dict[str, str | None]:
    row = connection.execute(
        """
        SELECT tenant_id, domain_id, dataset_key, partition_kind, partition_key
        FROM artifact_versions
        WHERE artifact_version_id = ?
        """,
        (artifact_version_id,),
    ).fetchone()
    if row is None:
        raise CommandError(
            code="artifact_version_not_found",
            message="artifact version not found for scope validation",
            details={"artifact_version_id": artifact_version_id},
        )
    return {
        "tenant_id": (
            str(row["tenant_id"]).strip() if row["tenant_id"] is not None else None
        ),
        "domain_id": (
            str(row["domain_id"]).strip() if row["domain_id"] is not None else None
        ),
        "dataset_key": (
            str(row["dataset_key"]).strip() if row["dataset_key"] is not None else None
        ),
        "partition_kind": (
            str(row["partition_kind"]).strip()
            if row["partition_kind"] is not None
            else None
        ),
        "partition_key": (
            str(row["partition_key"]).strip()
            if row["partition_key"] is not None
            else None
        ),
    }


def _assert_artifact_matches_expected_scope(
    *,
    artifact_version_id: str,
    expected_scope: dict[str, str | None],
    artifact_scope: dict[str, str | None],
    context: str,
) -> None:
    required = ("tenant_id", "domain_id", "dataset_key", "partition_kind", "partition_key")
    missing_expected = [field for field in required if expected_scope.get(field) is None]
    if missing_expected:
        raise CommandError(
            code="artifact_scope_unresolved",
            message="expected canonical scope could not be resolved for artifact validation",
            details={
                "artifact_version_id": artifact_version_id,
                "context": context,
                "missing_expected_fields": missing_expected,
            },
        )

    missing_actual = [field for field in required if artifact_scope.get(field) is None]
    if missing_actual:
        raise CommandError(
            code="artifact_scope_unresolved",
            message="artifact canonical scope is not fully populated",
            details={
                "artifact_version_id": artifact_version_id,
                "context": context,
                "missing_artifact_fields": missing_actual,
            },
        )

    mismatches: dict[str, dict[str, str]] = {}
    for field in required:
        expected_value = str(expected_scope[field])
        actual_value = str(artifact_scope[field])
        if actual_value != expected_value:
            mismatches[field] = {
                "expected": expected_value,
                "actual": actual_value,
            }
    if mismatches:
        raise CommandError(
            code="artifact_scope_mismatch",
            message="artifact canonical scope does not match expected workflow scope",
            details={
                "artifact_version_id": artifact_version_id,
                "context": context,
                "mismatches": mismatches,
            },
        )


def _capture_pointer_input_binding(
    connection: sqlite3.Connection,
    *,
    workflow_run_id: str,
    task_run_id: str | None,
    binding_key: str,
    pointer_key: str,
    pointer: dict[str, Any],
    captured_at: str,
    metadata_json: dict[str, Any],
) -> None:
    pointer_artifact_version_id = str(pointer["artifact_version_id"])
    _capture_input_binding(
        connection,
        workflow_run_id=workflow_run_id,
        task_run_id=task_run_id,
        binding_key=binding_key,
        source_kind="pointer",
        source_ref=pointer_key,
        artifact_version_id=pointer_artifact_version_id,
        pointer_key=pointer_key,
        pointer_generation=int(pointer["generation"]),
        pointer_artifact_version_id=pointer_artifact_version_id,
        captured_at=captured_at,
        metadata_json=metadata_json,
    )
