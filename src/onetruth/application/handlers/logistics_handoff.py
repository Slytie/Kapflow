from __future__ import annotations

import hashlib
import sqlite3
from typing import Any
from uuid import uuid4

from onetruth.application.handlers.workflow_task_lifecycle import CommandError
from onetruth.application.services.logistics_handoff_runtime import apply_partition_transform_by_id
from onetruth.domain.partition_codec import validate_partition_key
from onetruth.infrastructure.events.event_store import utc_now_iso
from onetruth.infrastructure.repositories.artifact_provenance import create_artifact_provenance_edge
from onetruth.infrastructure.repositories.artifact_versions import (
    create_artifact_version,
    get_artifact_version,
)
from onetruth.infrastructure.repositories.edge_executions import (
    create_edge_execution,
    get_edge_execution,
    get_edge_execution_by_correlation,
    list_edge_executions,
    update_edge_execution_activation,
)
from onetruth.infrastructure.repositories.input_bindings import (
    InputBindingConflictError,
    create_workflow_run_input,
)
from onetruth.infrastructure.repositories.workflow_runs import (
    create_workflow_run,
    get_workflow_run,
    list_workflow_runs,
)


EDGE_ID_WEEKLY_TO_LIVE = "weekly_seed_to_live_dispatch"
WEEKLY_WORKFLOW_ID = "weekly_schedule_planning.v1"
LIVE_WORKFLOW_ID = "live_dispatch.v1"
WEEKLY_PUBLISHED_KIND = "planning.published_weekly_schedule.workbook"
WEEKLY_DAILY_SEED_KIND = "planning.daily_dispatch_seed.workbook"
LIVE_SEED_KIND = "dispatch.base_schedule_seed.workbook"
LIVE_ROUTE_DELTA_KIND = "dispatch.route_delta_intake.workbook"
LIVE_ACTUAL_HOURS_KIND = "dispatch.actual_hours_snapshot.workbook"


def materialize_weekly_seeds_command(
    connection: sqlite3.Connection,
    payload: dict[str, Any],
) -> dict[str, Any]:
    _require_fields(
        payload,
        [
            "workflow_run_id",
            "published_artifact_version_id",
            "idempotency_key",
        ],
    )

    workflow_run_id = str(payload["workflow_run_id"])
    published_artifact_version_id = str(payload["published_artifact_version_id"])
    idempotency_key = str(payload["idempotency_key"])

    source_workflow_run = _require_workflow_run(connection, workflow_run_id)
    if str(source_workflow_run["workflow_id"]) != WEEKLY_WORKFLOW_ID:
        raise CommandError(
            code="invalid_source_workflow",
            message="weekly seed materialization requires weekly_schedule_planning.v1 source workflow run",
            details={
                "workflow_run_id": workflow_run_id,
                "workflow_id": str(source_workflow_run["workflow_id"]),
            },
        )

    published_artifact = _require_artifact(connection, published_artifact_version_id)
    if str(published_artifact["workflow_run_id"]) != workflow_run_id:
        raise CommandError(
            code="cross_workflow_artifact_reference",
            message="published artifact belongs to a different workflow_run",
            details={
                "workflow_run_id": workflow_run_id,
                "artifact_workflow_run_id": str(published_artifact["workflow_run_id"]),
                "artifact_version_id": published_artifact_version_id,
            },
        )
    if str(published_artifact["artifact_kind"]) != WEEKLY_PUBLISHED_KIND:
        raise CommandError(
            code="invalid_published_artifact_kind",
            message="published artifact kind must be planning.published_weekly_schedule.workbook",
            details={
                "artifact_version_id": published_artifact_version_id,
                "artifact_kind": str(published_artifact["artifact_kind"]),
            },
        )

    planning_week_id = str(source_workflow_run["partition_key"])
    service_dates = apply_partition_transform_by_id(
        transform_id="planning_week_to_service_days",
        source_partition_key=planning_week_id,
    )
    requested_service_date = payload.get("service_date_id")
    if requested_service_date is not None:
        service_date_id = str(requested_service_date)
        validate_partition_key("ServiceDateID", service_date_id)
        if service_date_id not in service_dates:
            raise CommandError(
                code="service_date_out_of_partition_transform",
                message="service_date_id does not belong to the source planning week",
                details={
                    "service_date_id": service_date_id,
                    "planning_week_id": planning_week_id,
                },
            )
        service_dates = [service_date_id]

    edge_rows: list[dict[str, Any]] = []
    seed_rows: list[dict[str, Any]] = []

    _begin_transaction(connection)
    try:
        for service_date_id in sorted(service_dates):
            correlation_key = _correlation_key(
                edge_id=EDGE_ID_WEEKLY_TO_LIVE,
                workflow_run_id=workflow_run_id,
                published_artifact_version_id=published_artifact_version_id,
                service_date_id=service_date_id,
            )
            existing = get_edge_execution_by_correlation(
                connection,
                edge_id=EDGE_ID_WEEKLY_TO_LIVE,
                correlation_key=correlation_key,
            )
            if existing is not None:
                seed_artifact_id = str(existing.get("seed_artifact_version_id") or "")
                seed_artifact = (
                    _require_artifact(connection, seed_artifact_id)
                    if seed_artifact_id
                    else None
                )
                edge_rows.append(existing)
                if seed_artifact is not None:
                    seed_rows.append(seed_artifact)
                continue

            now = utc_now_iso()
            seed_artifact_version_id = _stable_seed_artifact_id(
                workflow_run_id=workflow_run_id,
                published_artifact_version_id=published_artifact_version_id,
                service_date_id=service_date_id,
            )
            seed_artifact = _create_or_load_artifact_version(
                connection,
                artifact_version_id=seed_artifact_version_id,
                workflow_run_id=workflow_run_id,
                tenant_id=str(source_workflow_run["tenant_id"]),
                domain_id=str(source_workflow_run["domain_id"]),
                dataset_key=WEEKLY_DAILY_SEED_KIND,
                partition_kind="ServiceDateID",
                partition_key=service_date_id,
                artifact_kind=WEEKLY_DAILY_SEED_KIND,
                artifact_role="official_output",
                media_type="application/octet-stream",
                storage_uri=f"inmem://handoff/{workflow_run_id}/{service_date_id}/seed",
                content_digest=f"sha256:{_digest('weekly-seed', workflow_run_id, service_date_id)}",
                metadata_json={
                    "handoff_edge_id": EDGE_ID_WEEKLY_TO_LIVE,
                    "planning_week_id": planning_week_id,
                    "service_date_id": service_date_id,
                    "published_artifact_version_id": published_artifact_version_id,
                    "materialize_idempotency_key": idempotency_key,
                },
                parent_artifact_version_id=published_artifact_version_id,
                supersedes_artifact_version_id=None,
                lineage_note="weekly_to_live_handoff_seed",
                created_at=now,
            )
            _create_or_ignore_provenance_edge(
                connection,
                output_artifact_version_id=str(seed_artifact["artifact_version_id"]),
                input_artifact_version_id=published_artifact_version_id,
                edge_type="derives_from",
                workflow_run_id=workflow_run_id,
                edge_order=0,
                created_at=now,
                edge_id=f"ape-{_digest('seed-provenance', str(seed_artifact['artifact_version_id']), published_artifact_version_id)}",
                metadata_json={"edge_id": EDGE_ID_WEEKLY_TO_LIVE, "service_date_id": service_date_id},
            )

            edge_execution_id = f"ee-{uuid4()}"
            create_edge_execution(
                connection,
                edge_execution_id=edge_execution_id,
                edge_id=EDGE_ID_WEEKLY_TO_LIVE,
                source_workflow_run_id=workflow_run_id,
                source_stage_id="Stage07",
                source_artifact_version_id=str(seed_artifact["artifact_version_id"]),
                source_activation_key=str(source_workflow_run["activation_key"]),
                target_workflow_id=LIVE_WORKFLOW_ID,
                target_stage_id="Stage01",
                target_partition_kind="ServiceDateID",
                target_partition_key=service_date_id,
                target_activation_key=f"{LIVE_WORKFLOW_ID}:{service_date_id}",
                correlation_key=correlation_key,
                materialize_idempotency_key=idempotency_key,
                status="prepared",
                cursor_state={
                    "phase": "prepared",
                    "service_date_id": service_date_id,
                    "planning_week_id": planning_week_id,
                },
                compensation_state={"mode": "mark_stale", "state": "none"},
                input_bindings={
                    "published_artifact_version_id": published_artifact_version_id,
                    "seed_artifact_version_id": str(seed_artifact["artifact_version_id"]),
                },
                trigger_ref=None,
                seed_artifact_version_id=str(seed_artifact["artifact_version_id"]),
                target_workflow_run_id=None,
                activated_at=None,
                created_at=now,
            )
            edge = _require_edge_execution(connection, edge_execution_id)
            edge_rows.append(edge)
            seed_rows.append(seed_artifact)
    except Exception:
        connection.rollback()
        raise
    connection.commit()

    return {
        "edge_executions": edge_rows,
        "seed_artifacts": seed_rows,
    }


def activate_live_dispatch_command(
    connection: sqlite3.Connection,
    payload: dict[str, Any],
) -> dict[str, Any]:
    _require_fields(
        payload,
        [
            "edge_execution_id",
            "route_delta_source_artifact_version_id",
            "actual_hours_source_artifact_version_id",
            "idempotency_key",
        ],
    )

    edge_execution_id = str(payload["edge_execution_id"])
    route_delta_source_artifact_version_id = str(payload["route_delta_source_artifact_version_id"])
    actual_hours_source_artifact_version_id = str(payload["actual_hours_source_artifact_version_id"])
    idempotency_key = str(payload["idempotency_key"])

    edge = _require_edge_execution(connection, edge_execution_id)
    source_workflow_run = _require_workflow_run(connection, str(edge["source_workflow_run_id"]))
    source_scope = {
        "tenant_id": str(source_workflow_run["tenant_id"]),
        "domain_id": str(source_workflow_run["domain_id"]),
    }

    if str(edge["status"]) == "activated" and edge.get("target_workflow_run_id"):
        target_workflow_run = _require_workflow_run(connection, str(edge["target_workflow_run_id"]))
        return {
            "edge_execution": edge,
            "target_workflow_run": target_workflow_run,
        }

    seed_artifact = _require_artifact(connection, str(edge["seed_artifact_version_id"]))
    _assert_same_scope_artifact(
        connection,
        artifact_version_id=str(seed_artifact["artifact_version_id"]),
        expected_scope=source_scope,
    )
    route_delta_source = _assert_same_scope_artifact(
        connection,
        artifact_version_id=route_delta_source_artifact_version_id,
        expected_scope=source_scope,
    )
    if str(route_delta_source["artifact_kind"]) != LIVE_ROUTE_DELTA_KIND:
        raise CommandError(
            code="invalid_route_delta_artifact_kind",
            message="route_delta_source_artifact_version_id must reference dispatch.route_delta_intake.workbook",
            details={
                "artifact_version_id": route_delta_source_artifact_version_id,
                "artifact_kind": str(route_delta_source["artifact_kind"]),
            },
        )
    actual_hours_source = _assert_same_scope_artifact(
        connection,
        artifact_version_id=actual_hours_source_artifact_version_id,
        expected_scope=source_scope,
    )
    if str(actual_hours_source["artifact_kind"]) not in {
        "planning.actual_hours_snapshot.workbook",
        LIVE_ACTUAL_HOURS_KIND,
    }:
        raise CommandError(
            code="invalid_actual_hours_artifact_kind",
            message="actual_hours_source_artifact_version_id must reference a supported actual-hours snapshot kind",
            details={
                "artifact_version_id": actual_hours_source_artifact_version_id,
                "artifact_kind": str(actual_hours_source["artifact_kind"]),
            },
        )

    service_date_id = str(edge["target_partition_key"])
    route_delta_partition = route_delta_source.get("partition_key")
    route_delta_partition_kind = route_delta_source.get("partition_kind")
    if route_delta_partition is not None and str(route_delta_partition) != service_date_id:
        raise CommandError(
            code="handoff_input_partition_mismatch",
            message="route delta source partition does not match edge target service date",
            details={
                "edge_execution_id": edge_execution_id,
                "expected_service_date_id": service_date_id,
                "route_delta_partition_key": str(route_delta_partition),
            },
        )
    if route_delta_partition_kind is not None and str(route_delta_partition_kind) != "ServiceDateID":
        raise CommandError(
            code="handoff_input_partition_mismatch",
            message="route delta source partition kind must be ServiceDateID",
            details={
                "edge_execution_id": edge_execution_id,
                "route_delta_partition_kind": str(route_delta_partition_kind),
            },
        )

    _begin_transaction(connection)
    try:
        now = utc_now_iso()
        target_workflow_run = _resolve_or_create_live_dispatch_run(
            connection,
            tenant_id=source_scope["tenant_id"],
            domain_id=source_scope["domain_id"],
            service_date_id=service_date_id,
            activation_key=str(edge.get("target_activation_key") or f"{LIVE_WORKFLOW_ID}:{service_date_id}"),
            created_at=now,
        )
        target_workflow_run_id = str(target_workflow_run["workflow_run_id"])

        live_seed = _create_or_load_artifact_version(
            connection,
            artifact_version_id=_stable_live_input_artifact_id(edge_execution_id, LIVE_SEED_KIND),
            workflow_run_id=target_workflow_run_id,
            tenant_id=source_scope["tenant_id"],
            domain_id=source_scope["domain_id"],
            dataset_key=LIVE_SEED_KIND,
            partition_kind="ServiceDateID",
            partition_key=service_date_id,
            artifact_kind=LIVE_SEED_KIND,
            artifact_role="official_input",
            media_type="application/octet-stream",
            storage_uri=f"inmem://handoff/{target_workflow_run_id}/{LIVE_SEED_KIND}",
            content_digest=f"sha256:{_digest('live-input', edge_execution_id, LIVE_SEED_KIND)}",
            metadata_json={
                "edge_execution_id": edge_execution_id,
                "source_artifact_version_id": str(seed_artifact["artifact_version_id"]),
                "service_date_id": service_date_id,
            },
            parent_artifact_version_id=str(seed_artifact["artifact_version_id"]),
            supersedes_artifact_version_id=None,
            lineage_note="handoff_live_input",
            created_at=now,
        )
        live_route_delta = _create_or_load_artifact_version(
            connection,
            artifact_version_id=_stable_live_input_artifact_id(edge_execution_id, LIVE_ROUTE_DELTA_KIND),
            workflow_run_id=target_workflow_run_id,
            tenant_id=source_scope["tenant_id"],
            domain_id=source_scope["domain_id"],
            dataset_key=LIVE_ROUTE_DELTA_KIND,
            partition_kind="ServiceDateID",
            partition_key=service_date_id,
            artifact_kind=LIVE_ROUTE_DELTA_KIND,
            artifact_role="official_input",
            media_type="application/octet-stream",
            storage_uri=f"inmem://handoff/{target_workflow_run_id}/{LIVE_ROUTE_DELTA_KIND}",
            content_digest=f"sha256:{_digest('live-input', edge_execution_id, LIVE_ROUTE_DELTA_KIND)}",
            metadata_json={
                "edge_execution_id": edge_execution_id,
                "source_artifact_version_id": route_delta_source_artifact_version_id,
                "service_date_id": service_date_id,
            },
            parent_artifact_version_id=route_delta_source_artifact_version_id,
            supersedes_artifact_version_id=None,
            lineage_note="handoff_live_input",
            created_at=now,
        )
        live_actual_hours = _create_or_load_artifact_version(
            connection,
            artifact_version_id=_stable_live_input_artifact_id(edge_execution_id, LIVE_ACTUAL_HOURS_KIND),
            workflow_run_id=target_workflow_run_id,
            tenant_id=source_scope["tenant_id"],
            domain_id=source_scope["domain_id"],
            dataset_key=LIVE_ACTUAL_HOURS_KIND,
            partition_kind="ServiceDateID",
            partition_key=service_date_id,
            artifact_kind=LIVE_ACTUAL_HOURS_KIND,
            artifact_role="official_input",
            media_type="application/octet-stream",
            storage_uri=f"inmem://handoff/{target_workflow_run_id}/{LIVE_ACTUAL_HOURS_KIND}",
            content_digest=f"sha256:{_digest('live-input', edge_execution_id, LIVE_ACTUAL_HOURS_KIND)}",
            metadata_json={
                "edge_execution_id": edge_execution_id,
                "source_artifact_version_id": actual_hours_source_artifact_version_id,
                "service_date_id": service_date_id,
            },
            parent_artifact_version_id=actual_hours_source_artifact_version_id,
            supersedes_artifact_version_id=None,
            lineage_note="handoff_live_input",
            created_at=now,
        )

        _create_or_ignore_provenance_edge(
            connection,
            output_artifact_version_id=str(live_seed["artifact_version_id"]),
            input_artifact_version_id=str(seed_artifact["artifact_version_id"]),
            edge_type="derives_from",
            workflow_run_id=target_workflow_run_id,
            edge_order=0,
            created_at=now,
            edge_id=f"ape-{_digest('live-seed-provenance', edge_execution_id, str(seed_artifact['artifact_version_id']))}",
            metadata_json={"edge_execution_id": edge_execution_id},
        )
        _create_or_ignore_provenance_edge(
            connection,
            output_artifact_version_id=str(live_route_delta["artifact_version_id"]),
            input_artifact_version_id=route_delta_source_artifact_version_id,
            edge_type="derives_from",
            workflow_run_id=target_workflow_run_id,
            edge_order=0,
            created_at=now,
            edge_id=f"ape-{_digest('live-route-provenance', edge_execution_id, route_delta_source_artifact_version_id)}",
            metadata_json={"edge_execution_id": edge_execution_id},
        )
        _create_or_ignore_provenance_edge(
            connection,
            output_artifact_version_id=str(live_actual_hours["artifact_version_id"]),
            input_artifact_version_id=actual_hours_source_artifact_version_id,
            edge_type="derives_from",
            workflow_run_id=target_workflow_run_id,
            edge_order=0,
            created_at=now,
            edge_id=f"ape-{_digest('live-hours-provenance', edge_execution_id, actual_hours_source_artifact_version_id)}",
            metadata_json={"edge_execution_id": edge_execution_id},
        )

        _create_or_ignore_workflow_input_binding(
            connection,
            workflow_run_id=target_workflow_run_id,
            binding_key="stage01.base_seed",
            source_ref=str(seed_artifact["artifact_version_id"]),
            artifact_version_id=str(live_seed["artifact_version_id"]),
            metadata_json={"edge_execution_id": edge_execution_id, "kind": LIVE_SEED_KIND},
            captured_at=now,
        )
        _create_or_ignore_workflow_input_binding(
            connection,
            workflow_run_id=target_workflow_run_id,
            binding_key="stage01.route_delta_intake",
            source_ref=route_delta_source_artifact_version_id,
            artifact_version_id=str(live_route_delta["artifact_version_id"]),
            metadata_json={"edge_execution_id": edge_execution_id, "kind": LIVE_ROUTE_DELTA_KIND},
            captured_at=now,
        )
        _create_or_ignore_workflow_input_binding(
            connection,
            workflow_run_id=target_workflow_run_id,
            binding_key="stage01.actual_hours_snapshot",
            source_ref=actual_hours_source_artifact_version_id,
            artifact_version_id=str(live_actual_hours["artifact_version_id"]),
            metadata_json={"edge_execution_id": edge_execution_id, "kind": LIVE_ACTUAL_HOURS_KIND},
            captured_at=now,
        )

        updated_edge = update_edge_execution_activation(
            connection,
            edge_execution_id=edge_execution_id,
            target_workflow_run_id=target_workflow_run_id,
            trigger_ref=route_delta_source_artifact_version_id,
            activation_idempotency_key=idempotency_key,
            status="activated",
            cursor_state={
                "phase": "activated",
                "service_date_id": service_date_id,
                "trigger_ref": route_delta_source_artifact_version_id,
            },
            compensation_state={"mode": "mark_stale", "state": "none"},
            input_bindings={
                "base_seed_source_artifact_version_id": str(seed_artifact["artifact_version_id"]),
                "route_delta_source_artifact_version_id": route_delta_source_artifact_version_id,
                "actual_hours_source_artifact_version_id": actual_hours_source_artifact_version_id,
                "live_input_artifact_version_ids": {
                    LIVE_SEED_KIND: str(live_seed["artifact_version_id"]),
                    LIVE_ROUTE_DELTA_KIND: str(live_route_delta["artifact_version_id"]),
                    LIVE_ACTUAL_HOURS_KIND: str(live_actual_hours["artifact_version_id"]),
                },
            },
            activated_at=now,
            updated_at=now,
        )
        if updated_edge is None:
            raise CommandError(
                code="edge_execution_not_found",
                message="edge execution not found during activation update",
                details={"edge_execution_id": edge_execution_id},
            )
    except Exception:
        connection.rollback()
        raise
    connection.commit()

    return {
        "edge_execution": updated_edge,
        "target_workflow_run": target_workflow_run,
    }


def show_edge_execution_command(
    connection: sqlite3.Connection,
    edge_execution_id: str,
) -> dict[str, Any]:
    return _require_edge_execution(connection, edge_execution_id)


def list_edge_executions_command(
    connection: sqlite3.Connection,
    *,
    edge_id: str | None,
    source_workflow_run_id: str | None,
    status: str | None,
    target_workflow_run_id: str | None,
) -> list[dict[str, Any]]:
    return list_edge_executions(
        connection,
        edge_id=edge_id,
        source_workflow_run_id=source_workflow_run_id,
        status=status,
        target_workflow_run_id=target_workflow_run_id,
    )


def _resolve_or_create_live_dispatch_run(
    connection: sqlite3.Connection,
    *,
    tenant_id: str,
    domain_id: str,
    service_date_id: str,
    activation_key: str,
    created_at: str,
) -> dict[str, Any]:
    existing_runs = list_workflow_runs(
        connection,
        workflow_id=LIVE_WORKFLOW_ID,
        tenant_id=tenant_id,
        domain_id=domain_id,
        state=None,
    )
    for run in existing_runs:
        if str(run["partition_key"]) == service_date_id:
            return run

    workflow_run_id = f"wr-{uuid4()}"
    logical_date = _logical_date_from_service_date_id(service_date_id)
    try:
        create_workflow_run(
            connection,
            workflow_run_id=workflow_run_id,
            workflow_id=LIVE_WORKFLOW_ID,
            workflow_version="v1",
            tenant_id=tenant_id,
            domain_id=domain_id,
            partition_key=service_date_id,
            logical_date=logical_date,
            activation_key=activation_key,
            state="OPEN",
            created_at=created_at,
        )
    except sqlite3.IntegrityError:
        # Another replay may have inserted the run concurrently.
        refreshed = list_workflow_runs(
            connection,
            workflow_id=LIVE_WORKFLOW_ID,
            tenant_id=tenant_id,
            domain_id=domain_id,
            state=None,
        )
        for run in refreshed:
            if str(run["partition_key"]) == service_date_id:
                return run
        raise
    created = get_workflow_run(connection, workflow_run_id)
    if created is None:
        raise CommandError(
            code="workflow_run_not_found",
            message="live dispatch run not found after creation",
            details={"workflow_run_id": workflow_run_id},
        )
    return created


def _logical_date_from_service_date_id(service_date_id: str) -> str:
    validate_partition_key("ServiceDateID", service_date_id)
    return service_date_id.removeprefix("SD-")


def _create_or_load_artifact_version(
    connection: sqlite3.Connection,
    *,
    artifact_version_id: str,
    workflow_run_id: str,
    tenant_id: str,
    domain_id: str,
    dataset_key: str,
    partition_kind: str,
    partition_key: str,
    artifact_kind: str,
    artifact_role: str | None,
    media_type: str,
    storage_uri: str,
    content_digest: str,
    metadata_json: dict[str, Any],
    parent_artifact_version_id: str | None,
    supersedes_artifact_version_id: str | None,
    lineage_note: str | None,
    created_at: str,
) -> dict[str, Any]:
    existing = get_artifact_version(connection, artifact_version_id)
    if existing is not None:
        return existing
    create_artifact_version(
        connection,
        artifact_version_id=artifact_version_id,
        workflow_run_id=workflow_run_id,
        tenant_id=tenant_id,
        domain_id=domain_id,
        dataset_key=dataset_key,
        partition_kind=partition_kind,
        partition_key=partition_key,
        task_run_id=None,
        artifact_kind=artifact_kind,
        artifact_role=artifact_role,
        media_type=media_type,
        storage_uri=storage_uri,
        content_digest=content_digest,
        byte_size=None,
        metadata_json=metadata_json,
        parent_artifact_version_id=parent_artifact_version_id,
        supersedes_artifact_version_id=supersedes_artifact_version_id,
        lineage_note=lineage_note,
        created_at=created_at,
    )
    created = get_artifact_version(connection, artifact_version_id)
    if created is None:
        raise CommandError(
            code="artifact_version_not_found",
            message="artifact version not found after creation",
            details={"artifact_version_id": artifact_version_id},
        )
    return created


def _create_or_ignore_provenance_edge(
    connection: sqlite3.Connection,
    *,
    output_artifact_version_id: str,
    input_artifact_version_id: str,
    edge_type: str,
    workflow_run_id: str,
    edge_order: int,
    created_at: str,
    edge_id: str,
    metadata_json: dict[str, Any],
) -> None:
    try:
        create_artifact_provenance_edge(
            connection,
            edge_id=edge_id,
            output_artifact_version_id=output_artifact_version_id,
            input_artifact_version_id=input_artifact_version_id,
            edge_type=edge_type,
            workflow_run_id=workflow_run_id,
            edge_order=edge_order,
            metadata_json=metadata_json,
            created_at=created_at,
        )
    except sqlite3.IntegrityError:
        return


def _create_or_ignore_workflow_input_binding(
    connection: sqlite3.Connection,
    *,
    workflow_run_id: str,
    binding_key: str,
    source_ref: str,
    artifact_version_id: str,
    metadata_json: dict[str, Any],
    captured_at: str,
) -> None:
    try:
        create_workflow_run_input(
            connection,
            workflow_run_id=workflow_run_id,
            binding_key=binding_key,
            source_kind="artifact_version",
            source_ref=source_ref,
            artifact_version_id=artifact_version_id,
            pointer_key=None,
            pointer_generation=None,
            pointer_artifact_version_id=None,
            captured_by_task_run_id=None,
            captured_at=captured_at,
            metadata_json=metadata_json,
        )
    except InputBindingConflictError:
        return


def _assert_same_scope_artifact(
    connection: sqlite3.Connection,
    *,
    artifact_version_id: str,
    expected_scope: dict[str, str],
) -> dict[str, Any]:
    artifact = _require_artifact(connection, artifact_version_id)
    artifact_workflow_run = _require_workflow_run(connection, str(artifact["workflow_run_id"]))
    if (
        str(artifact_workflow_run["tenant_id"]) != expected_scope["tenant_id"]
        or str(artifact_workflow_run["domain_id"]) != expected_scope["domain_id"]
    ):
        raise CommandError(
            code="cross_scope_handoff_input",
            message="handoff input artifact must remain in the same tenant/domain scope",
            details={
                "artifact_version_id": artifact_version_id,
                "expected_tenant_id": expected_scope["tenant_id"],
                "expected_domain_id": expected_scope["domain_id"],
                "actual_tenant_id": str(artifact_workflow_run["tenant_id"]),
                "actual_domain_id": str(artifact_workflow_run["domain_id"]),
            },
        )
    return artifact


def _stable_seed_artifact_id(
    *,
    workflow_run_id: str,
    published_artifact_version_id: str,
    service_date_id: str,
) -> str:
    return f"av-{_digest('weekly-seed-id', workflow_run_id, published_artifact_version_id, service_date_id)}"


def _stable_live_input_artifact_id(edge_execution_id: str, artifact_kind: str) -> str:
    return f"av-{_digest('live-input-id', edge_execution_id, artifact_kind)}"


def _correlation_key(
    *,
    edge_id: str,
    workflow_run_id: str,
    published_artifact_version_id: str,
    service_date_id: str,
) -> str:
    return _digest(edge_id, workflow_run_id, published_artifact_version_id, service_date_id)


def _digest(*parts: str) -> str:
    joined = "|".join(parts)
    return hashlib.sha256(joined.encode("utf-8")).hexdigest()[:32]


def _require_workflow_run(connection: sqlite3.Connection, workflow_run_id: str) -> dict[str, Any]:
    workflow_run = get_workflow_run(connection, workflow_run_id)
    if workflow_run is None:
        raise CommandError(
            code="workflow_run_not_found",
            message="workflow run not found",
            details={"workflow_run_id": workflow_run_id},
        )
    return workflow_run


def _require_artifact(connection: sqlite3.Connection, artifact_version_id: str) -> dict[str, Any]:
    artifact = get_artifact_version(connection, artifact_version_id)
    if artifact is None:
        raise CommandError(
            code="artifact_version_not_found",
            message="artifact version not found",
            details={"artifact_version_id": artifact_version_id},
        )
    return artifact


def _require_edge_execution(connection: sqlite3.Connection, edge_execution_id: str) -> dict[str, Any]:
    edge = get_edge_execution(connection, edge_execution_id)
    if edge is None:
        raise CommandError(
            code="edge_execution_not_found",
            message="edge execution not found",
            details={"edge_execution_id": edge_execution_id},
        )
    return edge


def _require_fields(payload: dict[str, Any], fields: list[str]) -> None:
    missing = [field for field in fields if payload.get(field) is None]
    if missing:
        raise CommandError(
            code="invalid_payload",
            message=f"missing required fields: {', '.join(missing)}",
            details={"missing_fields": missing},
        )


def _begin_transaction(connection: sqlite3.Connection) -> None:
    connection.execute("BEGIN IMMEDIATE")
