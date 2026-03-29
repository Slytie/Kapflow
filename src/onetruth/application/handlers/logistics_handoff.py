from __future__ import annotations

from datetime import date
from functools import lru_cache
import hashlib
import json
from pathlib import Path
import sqlite3
from typing import Any
from uuid import uuid4

from onetruth.application.handlers._shared.command_boundary import CommandError, _event_envelope
from onetruth.application.services.logistics_handoff_runtime import apply_partition_transform_by_id
from onetruth.domain.partition_codec import validate_partition_key
from onetruth.infrastructure.definitions.family_compiler import (
    DefinitionCompileError,
    compile_workflow_family,
)
from onetruth.infrastructure.events.event_store import append_event, utc_now_iso
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
from onetruth.infrastructure.repositories.human_tasks import (
    create_human_task,
    get_human_task_by_task_run_id,
)
from onetruth.infrastructure.repositories.task_runs import (
    create_task_run,
    get_task_run_by_activation_key,
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
LIVE_STAGE01_TASK_KIND = "dispatch_seed_intake"
NOTIFY_ONLY_MODE = "notify_only"
WRITER_MODE_SOURCE_ONLY = "source_only"

_REPO_ROOT = Path(__file__).resolve().parents[4]
_LOGISTICS_FAMILY_PATH = (
    _REPO_ROOT / "docs" / "workflows" / "logistics_ops_family" / "v1" / "WORKFLOW_FAMILY.yaml"
)
_LOGISTICS_TRANSFORMS_PATH = (
    _REPO_ROOT / "docs" / "workflows" / "logistics_ops_family" / "v1" / "PARTITION_TRANSFORMS.yaml"
)


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
                source_workflow_run_id=workflow_run_id,
                source_artifact_version_id=published_artifact_version_id,
                target_partition_key=service_date_id,
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

    edge_status = str(edge.get("status") or "")
    if edge_status not in {"prepared", "activated"}:
        raise CommandError(
            code="edge_execution_status_transition_invalid",
            message="edge execution status cannot transition to activated from the current state",
            details={
                "edge_execution_id": edge_execution_id,
                "status": edge_status,
                "allowed_statuses": ["prepared", "activated"],
            },
        )

    if edge_status == "activated":
        target_workflow_run_id = str(edge.get("target_workflow_run_id") or "")
        if not target_workflow_run_id:
            raise CommandError(
                code="edge_execution_status_transition_invalid",
                message="activated edge execution is missing target_workflow_run_id",
                details={
                    "edge_execution_id": edge_execution_id,
                    "status": edge_status,
                },
            )
        _assert_activation_replay_input_matches(
            connection,
            edge=edge,
            target_workflow_run_id=target_workflow_run_id,
            route_delta_source_artifact_version_id=route_delta_source_artifact_version_id,
            actual_hours_source_artifact_version_id=actual_hours_source_artifact_version_id,
        )
        target_workflow_run = _require_workflow_run(connection, target_workflow_run_id)
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
    _assert_handoff_source_not_superseded(
        connection,
        edge_execution_id=edge_execution_id,
        artifact_version_id=route_delta_source_artifact_version_id,
        artifact_kind=str(route_delta_source["artifact_kind"]),
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
    _assert_handoff_source_not_superseded(
        connection,
        edge_execution_id=edge_execution_id,
        artifact_version_id=actual_hours_source_artifact_version_id,
        artifact_kind=str(actual_hours_source["artifact_kind"]),
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


def prepare_live_dispatch_day_command(
    connection: sqlite3.Connection,
    payload: dict[str, Any],
) -> dict[str, Any]:
    _require_fields(
        payload,
        [
            "workflow_run_id",
            "published_artifact_version_id",
            "service_date_id",
            "idempotency_key",
        ],
    )

    weekly_run_id = str(payload["workflow_run_id"])
    published_artifact_version_id = str(payload["published_artifact_version_id"])
    service_date_id = str(payload["service_date_id"])
    idempotency_key = str(payload["idempotency_key"])

    materialized = materialize_weekly_seeds_command(
        connection,
        {
            "workflow_run_id": weekly_run_id,
            "published_artifact_version_id": published_artifact_version_id,
            "service_date_id": service_date_id,
            "idempotency_key": idempotency_key,
        },
    )
    edge_rows = list(materialized.get("edge_executions") or [])
    seed_rows = list(materialized.get("seed_artifacts") or [])
    if len(edge_rows) != 1 or len(seed_rows) != 1:
        raise CommandError(
            code="prepare_live_dispatch_failed",
            message="prepare-live-dispatch-day requires exactly one service-day seed edge",
            details={
                "workflow_run_id": weekly_run_id,
                "service_date_id": service_date_id,
                "edge_execution_count": len(edge_rows),
                "seed_artifact_count": len(seed_rows),
            },
        )

    edge = edge_rows[0]
    seed_artifact = seed_rows[0]
    source_workflow_run = _require_workflow_run(connection, weekly_run_id)
    scope = {
        "tenant_id": str(source_workflow_run["tenant_id"]),
        "domain_id": str(source_workflow_run["domain_id"]),
    }

    edge_status = str(edge.get("status") or "")
    if edge_status == "activated":
        target_workflow_run_id = str(edge.get("target_workflow_run_id") or "").strip()
        if not target_workflow_run_id:
            raise CommandError(
                code="edge_execution_status_transition_invalid",
                message="activated live-dispatch edge is missing a target workflow run",
                details={"edge_execution_id": str(edge.get("edge_execution_id") or "")},
            )
        target_workflow_run = _require_workflow_run(connection, target_workflow_run_id)
        seed_intake_task = _ensure_live_dispatch_seed_intake_task(
            connection,
            workflow_run_id=target_workflow_run_id,
            actor_id=str(payload.get("actor_id") or "system:runtime"),
            actor_type=str(payload.get("actor_type") or "system"),
            scope={
                "tenant_id": str(target_workflow_run["tenant_id"]),
                "domain_id": str(target_workflow_run["domain_id"]),
            },
            created_at=utc_now_iso(),
        )
        return {
            "edge_execution": edge,
            "target_workflow_run": target_workflow_run,
            "live_seed_artifact": _require_artifact(
                connection,
                _stable_live_input_artifact_id(str(edge["edge_execution_id"]), LIVE_SEED_KIND),
            ),
            "seed_intake_task": seed_intake_task,
        }

    if edge_status != "prepared":
        raise CommandError(
            code="edge_execution_status_transition_invalid",
            message="prepare-live-dispatch-day requires a prepared weekly seed edge",
            details={
                "edge_execution_id": str(edge.get("edge_execution_id") or ""),
                "status": edge_status,
            },
        )

    edge_execution_id = str(edge["edge_execution_id"])
    _begin_transaction(connection)
    try:
        now = utc_now_iso()
        target_workflow_run = _resolve_or_create_live_dispatch_run(
            connection,
            tenant_id=scope["tenant_id"],
            domain_id=scope["domain_id"],
            service_date_id=service_date_id,
            activation_key=str(edge.get("target_activation_key") or f"{LIVE_WORKFLOW_ID}:{service_date_id}"),
            created_at=now,
        )
        target_workflow_run_id = str(target_workflow_run["workflow_run_id"])

        live_seed = _create_or_load_artifact_version(
            connection,
            artifact_version_id=_stable_live_input_artifact_id(edge_execution_id, LIVE_SEED_KIND),
            workflow_run_id=target_workflow_run_id,
            tenant_id=scope["tenant_id"],
            domain_id=scope["domain_id"],
            dataset_key=LIVE_SEED_KIND,
            partition_kind="ServiceDateID",
            partition_key=service_date_id,
            artifact_kind=LIVE_SEED_KIND,
            artifact_role="official_input",
            media_type=str(seed_artifact.get("media_type") or "application/octet-stream"),
            storage_uri=str(seed_artifact["storage_uri"]),
            content_digest=str(seed_artifact["content_digest"]),
            metadata_json={
                "edge_execution_id": edge_execution_id,
                "source_artifact_version_id": str(seed_artifact["artifact_version_id"]),
                "service_date_id": service_date_id,
                "prepared_via": "prepare_live_dispatch_day",
            },
            parent_artifact_version_id=str(seed_artifact["artifact_version_id"]),
            supersedes_artifact_version_id=None,
            lineage_note="handoff_live_seed_prepared",
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
            edge_id=(
                "ape-"
                f"{_digest('live-seed-prepared-provenance', edge_execution_id, str(seed_artifact['artifact_version_id']))}"
            ),
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

        updated_edge = update_edge_execution_activation(
            connection,
            edge_execution_id=edge_execution_id,
            target_workflow_run_id=target_workflow_run_id,
            trigger_ref=str(seed_artifact["artifact_version_id"]),
            activation_idempotency_key=idempotency_key,
            status="activated",
            cursor_state={
                "phase": "seed_prepared",
                "service_date_id": service_date_id,
                "trigger_ref": str(seed_artifact["artifact_version_id"]),
            },
            compensation_state={"mode": "mark_stale", "state": "none"},
            input_bindings={
                "base_seed_source_artifact_version_id": str(seed_artifact["artifact_version_id"]),
                "live_input_artifact_version_ids": {
                    LIVE_SEED_KIND: str(live_seed["artifact_version_id"]),
                },
            },
            activated_at=now,
            updated_at=now,
        )
        if updated_edge is None:
            raise CommandError(
                code="edge_execution_not_found",
                message="edge execution not found during live-day preparation update",
                details={"edge_execution_id": edge_execution_id},
            )
        seed_intake_task = _ensure_live_dispatch_seed_intake_task(
            connection,
            workflow_run_id=target_workflow_run_id,
            actor_id=str(payload.get("actor_id") or "system:runtime"),
            actor_type=str(payload.get("actor_type") or "system"),
            scope={
                "tenant_id": str(target_workflow_run["tenant_id"]),
                "domain_id": str(target_workflow_run["domain_id"]),
            },
            created_at=now,
        )
    except Exception:
        connection.rollback()
        raise
    connection.commit()

    return {
        "edge_execution": updated_edge,
        "target_workflow_run": target_workflow_run,
        "live_seed_artifact": live_seed,
        "seed_intake_task": seed_intake_task,
    }


def notify_only_handoff_command(
    connection: sqlite3.Connection,
    payload: dict[str, Any],
) -> dict[str, Any]:
    _require_fields(
        payload,
        [
            "edge_id",
            "source_workflow_run_id",
            "source_artifact_version_id",
            "idempotency_key",
        ],
    )

    edge_id = str(payload["edge_id"])
    source_workflow_run_id = str(payload["source_workflow_run_id"])
    source_artifact_version_id = str(payload["source_artifact_version_id"])
    idempotency_key = str(payload["idempotency_key"])

    edge_descriptor = _require_notify_only_edge_descriptor(edge_id)
    source_workflow_run = _require_workflow_run(connection, source_workflow_run_id)
    if str(source_workflow_run["workflow_id"]) != edge_descriptor["source_workflow_id"]:
        raise CommandError(
            code="invalid_source_workflow",
            message="source workflow does not match compiled notify_only edge source module",
            details={
                "edge_id": edge_id,
                "expected_source_workflow_id": edge_descriptor["source_workflow_id"],
                "actual_source_workflow_id": str(source_workflow_run["workflow_id"]),
            },
        )

    source_artifact = _require_artifact(connection, source_artifact_version_id)
    if str(source_artifact["workflow_run_id"]) != source_workflow_run_id:
        raise CommandError(
            code="cross_workflow_artifact_reference",
            message="source artifact belongs to a different workflow_run",
            details={
                "edge_id": edge_id,
                "workflow_run_id": source_workflow_run_id,
                "artifact_workflow_run_id": str(source_artifact["workflow_run_id"]),
                "artifact_version_id": source_artifact_version_id,
            },
        )
    if str(source_artifact["artifact_kind"]) != edge_descriptor["source_dataset_key"]:
        raise CommandError(
            code="invalid_source_artifact_kind",
            message="source artifact kind does not match compiled edge source output dataset",
            details={
                "edge_id": edge_id,
                "artifact_version_id": source_artifact_version_id,
                "expected_artifact_kind": edge_descriptor["source_dataset_key"],
                "actual_artifact_kind": str(source_artifact["artifact_kind"]),
            },
        )

    source_partition_key = str(source_workflow_run["partition_key"])
    try:
        target_partition_keys = sorted(
            set(
                apply_partition_transform_by_id(
                    transform_id=edge_descriptor["partition_transform_id"],
                    source_partition_key=source_partition_key,
                )
            )
        )
    except ValueError as exc:
        raise CommandError(
            code="partition_transform_unsupported",
            message="notify_only partition transform is unsupported by runtime",
            details={
                "edge_id": edge_id,
                "transform_id": edge_descriptor["partition_transform_id"],
                "source_partition_key": source_partition_key,
                "error": str(exc),
            },
        ) from exc
    if not target_partition_keys:
        raise CommandError(
            code="partition_transform_empty",
            message="notify_only partition transform returned no target partitions",
            details={
                "edge_id": edge_id,
                "transform_id": edge_descriptor["partition_transform_id"],
                "source_partition_key": source_partition_key,
            },
        )

    target_workflow_runs: list[dict[str, Any]] = []
    target_input_artifacts: list[dict[str, Any]] = []
    edge_rows: list[dict[str, Any]] = []
    source_scope = {
        "tenant_id": str(source_workflow_run["tenant_id"]),
        "domain_id": str(source_workflow_run["domain_id"]),
    }
    target_binding_key = _workflow_input_binding_key(
        stage_id=edge_descriptor["target_stage_id"],
        dataset_key=edge_descriptor["target_dataset_key"],
    )

    started_transaction = not connection.in_transaction
    if started_transaction:
        _begin_transaction(connection)
    try:
        for target_partition_key in target_partition_keys:
            validate_partition_key(edge_descriptor["target_partition_kind"], target_partition_key)
            correlation_key = _correlation_key(
                edge_id=edge_id,
                source_workflow_run_id=source_workflow_run_id,
                source_artifact_version_id=source_artifact_version_id,
                target_partition_key=target_partition_key,
            )
            existing = get_edge_execution_by_correlation(
                connection,
                edge_id=edge_id,
                correlation_key=correlation_key,
            )
            if existing is not None:
                edge_rows.append(existing)
                existing_target_run_id = str(existing.get("target_workflow_run_id") or "")
                if existing_target_run_id:
                    target_run = _require_workflow_run(connection, existing_target_run_id)
                    target_workflow_runs.append(target_run)
                existing_target_input_artifact_id = _target_input_artifact_id_from_edge(existing)
                if existing_target_input_artifact_id is not None:
                    target_input_artifacts.append(
                        _require_artifact(connection, existing_target_input_artifact_id)
                    )
                continue

            now = utc_now_iso()
            target_workflow_run = _resolve_or_create_workflow_run(
                connection,
                workflow_id=edge_descriptor["target_workflow_id"],
                tenant_id=source_scope["tenant_id"],
                domain_id=source_scope["domain_id"],
                partition_kind=edge_descriptor["target_partition_kind"],
                partition_key=target_partition_key,
                activation_key=f"{edge_descriptor['target_workflow_id']}:{target_partition_key}",
                created_at=now,
            )
            target_workflow_run_id = str(target_workflow_run["workflow_run_id"])

            target_input_artifact = _create_or_load_artifact_version(
                connection,
                artifact_version_id=_stable_notify_input_artifact_id(
                    edge_id=edge_id,
                    source_artifact_version_id=source_artifact_version_id,
                    target_partition_key=target_partition_key,
                    target_dataset_key=edge_descriptor["target_dataset_key"],
                ),
                workflow_run_id=target_workflow_run_id,
                tenant_id=source_scope["tenant_id"],
                domain_id=source_scope["domain_id"],
                dataset_key=edge_descriptor["target_dataset_key"],
                partition_kind=edge_descriptor["target_partition_kind"],
                partition_key=target_partition_key,
                artifact_kind=edge_descriptor["target_dataset_key"],
                artifact_role="official_input",
                media_type=str(source_artifact.get("media_type") or "application/octet-stream"),
                storage_uri=(
                    "inmem://handoff/"
                    f"{target_workflow_run_id}/{edge_descriptor['target_dataset_key']}/{source_artifact_version_id}"
                ),
                content_digest=f"sha256:{_digest('notify-input', edge_id, source_artifact_version_id, target_partition_key)}",
                metadata_json={
                    "handoff_edge_id": edge_id,
                    "handoff_mode": NOTIFY_ONLY_MODE,
                    "source_workflow_run_id": source_workflow_run_id,
                    "source_artifact_version_id": source_artifact_version_id,
                    "source_partition_key": source_partition_key,
                    "target_partition_key": target_partition_key,
                    "target_input_dataset_key": edge_descriptor["target_dataset_key"],
                    "materialize_idempotency_key": idempotency_key,
                },
                parent_artifact_version_id=source_artifact_version_id,
                supersedes_artifact_version_id=None,
                lineage_note="notify_only_handoff_input",
                created_at=now,
            )
            _create_or_ignore_provenance_edge(
                connection,
                output_artifact_version_id=str(target_input_artifact["artifact_version_id"]),
                input_artifact_version_id=source_artifact_version_id,
                edge_type="derives_from",
                workflow_run_id=target_workflow_run_id,
                edge_order=0,
                created_at=now,
                edge_id=(
                    "ape-"
                    f"{_digest('notify-provenance', edge_id, str(target_input_artifact['artifact_version_id']), source_artifact_version_id)}"
                ),
                metadata_json={
                    "edge_id": edge_id,
                    "handoff_mode": NOTIFY_ONLY_MODE,
                    "target_partition_key": target_partition_key,
                },
            )
            _create_or_ignore_workflow_input_binding(
                connection,
                workflow_run_id=target_workflow_run_id,
                binding_key=target_binding_key,
                source_ref=source_artifact_version_id,
                artifact_version_id=str(target_input_artifact["artifact_version_id"]),
                metadata_json={
                    "edge_id": edge_id,
                    "handoff_mode": NOTIFY_ONLY_MODE,
                    "target_dataset_key": edge_descriptor["target_dataset_key"],
                },
                captured_at=now,
                replace_on_conflict=True,
            )

            edge_execution_id = f"ee-{uuid4()}"
            create_edge_execution(
                connection,
                edge_execution_id=edge_execution_id,
                edge_id=edge_id,
                source_workflow_run_id=source_workflow_run_id,
                source_stage_id=edge_descriptor["source_stage_id"],
                source_artifact_version_id=source_artifact_version_id,
                source_activation_key=str(source_workflow_run["activation_key"]),
                target_workflow_id=edge_descriptor["target_workflow_id"],
                target_stage_id=edge_descriptor["target_stage_id"],
                target_partition_kind=edge_descriptor["target_partition_kind"],
                target_partition_key=target_partition_key,
                target_activation_key=f"{edge_descriptor['target_workflow_id']}:{target_partition_key}",
                correlation_key=correlation_key,
                materialize_idempotency_key=idempotency_key,
                status="prepared",
                cursor_state={
                    "phase": "notified",
                    "handoff_mode": NOTIFY_ONLY_MODE,
                    "source_partition_key": source_partition_key,
                    "target_partition_key": target_partition_key,
                },
                compensation_state={
                    "mode": edge_descriptor["compensation_mode"],
                    "state": "none",
                },
                input_bindings={
                    "source_artifact_version_id": source_artifact_version_id,
                    "target_dataset_key": edge_descriptor["target_dataset_key"],
                    "target_input_artifact_version_id": str(
                        target_input_artifact["artifact_version_id"]
                    ),
                    "target_binding_key": target_binding_key,
                },
                trigger_ref=source_artifact_version_id,
                seed_artifact_version_id=None,
                target_workflow_run_id=target_workflow_run_id,
                activated_at=None,
                created_at=now,
            )
            edge_rows.append(_require_edge_execution(connection, edge_execution_id))
            target_workflow_runs.append(target_workflow_run)
            target_input_artifacts.append(target_input_artifact)
    except Exception:
        if started_transaction:
            connection.rollback()
        raise
    if started_transaction:
        connection.commit()

    return {
        "edge_executions": edge_rows,
        "target_workflow_runs": target_workflow_runs,
        "target_input_artifacts": target_input_artifacts,
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


@lru_cache(maxsize=1)
def _compiled_notify_only_edge_descriptors() -> dict[str, dict[str, str]]:
    try:
        compiled = compile_workflow_family(
            repo_root=_REPO_ROOT,
            family_path=_LOGISTICS_FAMILY_PATH,
            partition_transforms_path=_LOGISTICS_TRANSFORMS_PATH,
        )
    except DefinitionCompileError as exc:
        raise CommandError(
            code="family_compilation_failed",
            message="failed to compile logistics workflow family for notify_only dispatch",
            details={"error": str(exc)},
        ) from exc

    modules_raw = compiled.get("compiled_modules")
    edges_raw = compiled.get("compiled_edges")
    if not isinstance(modules_raw, list) or not isinstance(edges_raw, list):
        raise CommandError(
            code="family_compilation_invalid",
            message="compiled logistics family is missing compiled_modules/compiled_edges",
            details={},
        )

    modules: dict[str, dict[str, str]] = {}
    for module in modules_raw:
        if not isinstance(module, dict):
            continue
        module_id = str(module.get("module_id") or "").strip()
        source_workflow = module.get("source_workflow")
        partition = module.get("partition")
        if not isinstance(source_workflow, dict) or not isinstance(partition, dict):
            continue
        workflow_id = str(source_workflow.get("workflow_id") or "").strip()
        partition_kind = str(partition.get("kind") or "").strip()
        if module_id and workflow_id and partition_kind:
            modules[module_id] = {
                "workflow_id": workflow_id,
                "partition_kind": partition_kind,
            }

    descriptors: dict[str, dict[str, str]] = {}
    for edge in edges_raw:
        if not isinstance(edge, dict):
            continue
        edge_id = str(edge.get("edge_id") or "").strip()
        source_module_id = str(edge.get("source_module_id") or "").strip()
        target_module_id = str(edge.get("target_module_id") or "").strip()
        partition_transform = edge.get("partition_transform") or {}
        source_ref = edge.get("source_output_ref") or {}
        target_ref = edge.get("target_input_ref") or {}
        source_module = modules.get(source_module_id)
        target_module = modules.get(target_module_id)
        if (
            not edge_id
            or source_module is None
            or target_module is None
            or not isinstance(partition_transform, dict)
            or not isinstance(source_ref, dict)
            or not isinstance(target_ref, dict)
        ):
            continue
        descriptors[edge_id] = {
            "edge_id": edge_id,
            "handoff_mode": str(edge.get("handoff_mode") or ""),
            "writer_mode": str(edge.get("writer_mode") or ""),
            "compensation_mode": str(edge.get("compensation_mode") or ""),
            "source_workflow_id": source_module["workflow_id"],
            "source_partition_kind": source_module["partition_kind"],
            "source_stage_id": str(source_ref.get("stage_id") or ""),
            "source_dataset_key": str(source_ref.get("dataset_key") or ""),
            "target_workflow_id": target_module["workflow_id"],
            "target_partition_kind": target_module["partition_kind"],
            "target_stage_id": str(target_ref.get("stage_id") or ""),
            "target_dataset_key": str(target_ref.get("dataset_key") or ""),
            "partition_transform_id": str(partition_transform.get("id") or ""),
        }
    return descriptors


def _require_notify_only_edge_descriptor(edge_id: str) -> dict[str, str]:
    descriptor = _compiled_notify_only_edge_descriptors().get(edge_id)
    if descriptor is None:
        raise CommandError(
            code="edge_not_found",
            message="edge_id not found in compiled logistics workflow family",
            details={"edge_id": edge_id},
        )
    if descriptor["handoff_mode"] != NOTIFY_ONLY_MODE:
        raise CommandError(
            code="handoff_mode_mismatch",
            message="edge does not use handoff_mode=notify_only",
            details={
                "edge_id": edge_id,
                "handoff_mode": descriptor["handoff_mode"],
            },
        )
    if descriptor["writer_mode"] != WRITER_MODE_SOURCE_ONLY:
        raise CommandError(
            code="writer_mode_mismatch",
            message="notify_only runtime requires writer_mode=source_only",
            details={
                "edge_id": edge_id,
                "writer_mode": descriptor["writer_mode"],
            },
        )
    return descriptor


def _resolve_or_create_workflow_run(
    connection: sqlite3.Connection,
    *,
    workflow_id: str,
    tenant_id: str,
    domain_id: str,
    partition_kind: str,
    partition_key: str,
    activation_key: str,
    created_at: str,
) -> dict[str, Any]:
    existing_runs = list_workflow_runs(
        connection,
        workflow_id=workflow_id,
        tenant_id=tenant_id,
        domain_id=domain_id,
        state=None,
    )
    for run in existing_runs:
        if str(run["partition_key"]) == partition_key:
            return run

    workflow_run_id = f"wr-{uuid4()}"
    try:
        create_workflow_run(
            connection,
            workflow_run_id=workflow_run_id,
            workflow_id=workflow_id,
            workflow_version="v1",
            tenant_id=tenant_id,
            domain_id=domain_id,
            partition_key=partition_key,
            logical_date=_logical_date_from_partition_key(
                partition_kind=partition_kind,
                partition_key=partition_key,
            ),
            activation_key=activation_key,
            state="OPEN",
            created_at=created_at,
        )
    except sqlite3.IntegrityError:
        refreshed = list_workflow_runs(
            connection,
            workflow_id=workflow_id,
            tenant_id=tenant_id,
            domain_id=domain_id,
            state=None,
        )
        for run in refreshed:
            if str(run["partition_key"]) == partition_key:
                return run
        raise
    created = get_workflow_run(connection, workflow_run_id)
    if created is None:
        raise CommandError(
            code="workflow_run_not_found",
            message="workflow run not found after creation",
            details={"workflow_run_id": workflow_run_id},
        )
    return created


def _resolve_or_create_live_dispatch_run(
    connection: sqlite3.Connection,
    *,
    tenant_id: str,
    domain_id: str,
    service_date_id: str,
    activation_key: str,
    created_at: str,
) -> dict[str, Any]:
    return _resolve_or_create_workflow_run(
        connection,
        workflow_id=LIVE_WORKFLOW_ID,
        tenant_id=tenant_id,
        domain_id=domain_id,
        partition_kind="ServiceDateID",
        partition_key=service_date_id,
        activation_key=activation_key,
        created_at=created_at,
    )


def _ensure_live_dispatch_seed_intake_task(
    connection: sqlite3.Connection,
    *,
    workflow_run_id: str,
    actor_id: str,
    actor_type: str,
    scope: dict[str, str],
    created_at: str,
) -> dict[str, Any]:
    activation_key = f"live:{workflow_run_id}:stage01:dispatch-seed-intake"
    existing_task_run = get_task_run_by_activation_key(
        connection,
        workflow_run_id=workflow_run_id,
        activation_key=activation_key,
    )
    if existing_task_run is not None:
        if (
            str(existing_task_run.get("stage_id") or "") != "Stage01"
            or str(existing_task_run.get("task_kind") or "") != LIVE_STAGE01_TASK_KIND
        ):
            raise CommandError(
                code="duplicate_spawned_task_activation",
                message="live-dispatch seed-intake activation key is already used by another task",
                details={
                    "workflow_run_id": workflow_run_id,
                    "activation_key": activation_key,
                    "task_run_id": str(existing_task_run["task_run_id"]),
                },
            )
        existing_human_task = get_human_task_by_task_run_id(
            connection,
            str(existing_task_run["task_run_id"]),
        )
        if existing_human_task is not None:
            return {
                "task_run_id": str(existing_task_run["task_run_id"]),
                "human_task_id": str(existing_human_task["human_task_id"]),
                "stage_id": "Stage01",
                "task_kind": LIVE_STAGE01_TASK_KIND,
                "activation_key": activation_key,
                "generation": int(existing_task_run.get("generation") or 0),
            }

    task_run_id = (
        str(existing_task_run["task_run_id"])
        if existing_task_run is not None
        else f"tr-{uuid4()}"
    )
    human_task_id = f"ht-{uuid4()}"

    if existing_task_run is None:
        create_task_run(
            connection,
            task_run_id=task_run_id,
            workflow_run_id=workflow_run_id,
            stage_id="Stage01",
            task_kind=LIVE_STAGE01_TASK_KIND,
            state="READY",
            generation=0,
            activation_key=activation_key,
            blocked_on_kind=None,
            blocked_on_ref=None,
            spawned_from_flag_id=None,
            spawned_from_task_run_id=None,
            spawn_rule_id=None,
            spawn_cause_kind="handoff_activation",
            spawn_cause_event_id=None,
            spawn_depth=0,
            spawn_budget_key=None,
            created_at=created_at,
        )
        append_event(
            connection,
            _event_envelope(
                event_type="task.run.created",
                tenant_id=scope["tenant_id"],
                domain_id=scope["domain_id"],
                actor_type=actor_type,
                actor_id=actor_id,
                links=[
                    {"rel": "subject", "type": "workflow_run", "id": workflow_run_id},
                    {"rel": "subject", "type": "task_run", "id": task_run_id},
                ],
                payload={
                    "task_run_id": task_run_id,
                    "stage_id": "Stage01",
                    "task_kind": LIVE_STAGE01_TASK_KIND,
                    "activation_key": activation_key,
                    "generation": 0,
                    "spawned_from_flag_id": None,
                    "spawned_from_task_run_id": None,
                    "spawn_rule_id": None,
                    "spawn_cause_kind": "handoff_activation",
                    "spawn_cause_event_id": None,
                    "spawn_budget_key": None,
                    "spawn_depth": 0,
                },
                idempotency_key=None,
            ),
        )

    create_human_task(
        connection,
        human_task_id=human_task_id,
        workflow_run_id=workflow_run_id,
        task_run_id=task_run_id,
        task_kind=LIVE_STAGE01_TASK_KIND,
        state="OPEN",
        candidate_roles=["dispatch_supervisor"],
        owner_role="dispatch_supervisor",
        due_at=None,
        escalation_at=None,
        generation=0,
        created_at=created_at,
    )
    append_event(
        connection,
        _event_envelope(
            event_type="task.created",
            tenant_id=scope["tenant_id"],
            domain_id=scope["domain_id"],
            actor_type=actor_type,
            actor_id=actor_id,
            links=[
                {"rel": "subject", "type": "workflow_run", "id": workflow_run_id},
                {"rel": "subject", "type": "task_run", "id": task_run_id},
                {"rel": "subject", "type": "human_task", "id": human_task_id},
            ],
            payload={
                "human_task_id": human_task_id,
                "task_kind": LIVE_STAGE01_TASK_KIND,
                "state": "OPEN",
                "candidate_roles": ["dispatch_supervisor"],
            },
            idempotency_key=None,
        ),
    )
    return {
        "task_run_id": task_run_id,
        "human_task_id": human_task_id,
        "stage_id": "Stage01",
        "task_kind": LIVE_STAGE01_TASK_KIND,
        "activation_key": activation_key,
        "generation": 0,
    }


def _logical_date_from_service_date_id(service_date_id: str) -> str:
    validate_partition_key("ServiceDateID", service_date_id)
    return service_date_id.removeprefix("SD-")


def _logical_date_from_partition_key(*, partition_kind: str, partition_key: str) -> str:
    validate_partition_key(partition_kind, partition_key)
    if partition_kind == "ServiceDateID":
        return _logical_date_from_service_date_id(partition_key)
    if partition_kind in {"PlanningWeekID", "PayPeriodID"}:
        if partition_kind == "PlanningWeekID":
            token = partition_key.removeprefix("PW-")
        else:
            token = partition_key.removeprefix("PP-")
        year_text, week_text = token.split("-W", maxsplit=1)
        week_start = date.fromisocalendar(int(year_text), int(week_text), 1)
        return week_start.isoformat()
    return partition_key


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
    replace_on_conflict: bool = False,
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
        existing = _get_workflow_run_input_binding(
            connection,
            workflow_run_id=workflow_run_id,
            binding_key=binding_key,
        )
        if (
            existing is not None
            and str(existing.get("source_ref") or "") == source_ref
            and str(existing.get("artifact_version_id") or "") == artifact_version_id
        ):
            return
        if replace_on_conflict and existing is not None:
            _update_workflow_run_input_binding(
                connection,
                workflow_run_id=workflow_run_id,
                binding_key=binding_key,
                source_ref=source_ref,
                artifact_version_id=artifact_version_id,
                metadata_json=metadata_json,
                captured_at=captured_at,
            )
            return
        raise CommandError(
            code="handoff_input_binding_conflict",
            message="existing workflow input binding conflicts with handoff replay inputs",
            details={
                "workflow_run_id": workflow_run_id,
                "binding_key": binding_key,
                "expected_source_ref": source_ref,
                "expected_artifact_version_id": artifact_version_id,
                "existing_source_ref": (
                    str(existing.get("source_ref"))
                    if existing is not None and existing.get("source_ref") is not None
                    else None
                ),
                "existing_artifact_version_id": (
                    str(existing.get("artifact_version_id"))
                    if existing is not None and existing.get("artifact_version_id") is not None
                    else None
                ),
            },
        )


def _update_workflow_run_input_binding(
    connection: sqlite3.Connection,
    *,
    workflow_run_id: str,
    binding_key: str,
    source_ref: str,
    artifact_version_id: str,
    metadata_json: dict[str, Any],
    captured_at: str,
) -> None:
    connection.execute(
        """
        UPDATE workflow_run_inputs
        SET
            source_kind = 'artifact_version',
            source_ref = ?,
            artifact_version_id = ?,
            pointer_key = NULL,
            pointer_generation = NULL,
            pointer_artifact_version_id = NULL,
            captured_by_task_run_id = NULL,
            captured_at = ?,
            metadata_json = ?
        WHERE workflow_run_id = ? AND binding_key = ?
        """,
        (
            source_ref,
            artifact_version_id,
            captured_at,
            json.dumps(metadata_json, separators=(",", ":")),
            workflow_run_id,
            binding_key,
        ),
    )


def _get_workflow_run_input_binding(
    connection: sqlite3.Connection,
    *,
    workflow_run_id: str,
    binding_key: str,
) -> dict[str, Any] | None:
    row = connection.execute(
        """
        SELECT
            workflow_run_id,
            binding_key,
            source_kind,
            source_ref,
            artifact_version_id
        FROM workflow_run_inputs
        WHERE workflow_run_id = ? AND binding_key = ?
        LIMIT 1
        """,
        (workflow_run_id, binding_key),
    ).fetchone()
    if row is None:
        return None
    return dict(row)


def _assert_activation_replay_input_matches(
    connection: sqlite3.Connection,
    *,
    edge: dict[str, Any],
    target_workflow_run_id: str,
    route_delta_source_artifact_version_id: str,
    actual_hours_source_artifact_version_id: str,
) -> None:
    bindings = edge.get("input_bindings")
    if not isinstance(bindings, dict):
        raise CommandError(
            code="handoff_activation_input_mismatch",
            message="activated edge execution is missing canonical input bindings",
            details={"edge_execution_id": str(edge.get("edge_execution_id") or "")},
        )

    expected_route = str(bindings.get("route_delta_source_artifact_version_id") or "")
    expected_actual_hours = str(bindings.get("actual_hours_source_artifact_version_id") or "")
    if not expected_route:
        route_binding = _get_workflow_run_input_binding(
            connection,
            workflow_run_id=target_workflow_run_id,
            binding_key="stage01.route_delta_intake",
        )
        expected_route = str(route_binding.get("source_ref") or "") if route_binding is not None else ""
    if not expected_actual_hours:
        hours_binding = _get_workflow_run_input_binding(
            connection,
            workflow_run_id=target_workflow_run_id,
            binding_key="stage01.actual_hours_snapshot",
        )
        expected_actual_hours = (
            str(hours_binding.get("source_ref") or "")
            if hours_binding is not None
            else ""
        )

    route_matches = expected_route and expected_route == route_delta_source_artifact_version_id
    hours_matches = (
        expected_actual_hours
        and expected_actual_hours == actual_hours_source_artifact_version_id
    )
    if route_matches and hours_matches:
        return

    raise CommandError(
        code="handoff_activation_input_mismatch",
        message="activation retry must reuse the same canonical route-delta and actual-hours source bindings",
        details={
            "edge_execution_id": str(edge.get("edge_execution_id") or ""),
            "target_workflow_run_id": target_workflow_run_id,
            "expected_route_delta_source_artifact_version_id": expected_route or None,
            "provided_route_delta_source_artifact_version_id": route_delta_source_artifact_version_id,
            "expected_actual_hours_source_artifact_version_id": expected_actual_hours or None,
            "provided_actual_hours_source_artifact_version_id": actual_hours_source_artifact_version_id,
        },
    )


def _assert_handoff_source_not_superseded(
    connection: sqlite3.Connection,
    *,
    edge_execution_id: str,
    artifact_version_id: str,
    artifact_kind: str,
) -> None:
    superseding = connection.execute(
        """
        SELECT artifact_version_id
        FROM artifact_versions
        WHERE supersedes_artifact_version_id = ?
        ORDER BY created_at DESC, artifact_version_id DESC
        LIMIT 1
        """,
        (artifact_version_id,),
    ).fetchone()
    if superseding is None:
        return
    raise CommandError(
        code="handoff_source_artifact_superseded",
        message="handoff activation input references a superseded source artifact version",
        details={
            "edge_execution_id": edge_execution_id,
            "artifact_version_id": artifact_version_id,
            "artifact_kind": artifact_kind,
            "superseding_artifact_version_id": str(superseding["artifact_version_id"]),
        },
    )


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


def _stable_notify_input_artifact_id(
    *,
    edge_id: str,
    source_artifact_version_id: str,
    target_partition_key: str,
    target_dataset_key: str,
) -> str:
    return (
        "av-"
        f"{_digest('notify-input-id', edge_id, source_artifact_version_id, target_partition_key, target_dataset_key)}"
    )


def _workflow_input_binding_key(*, stage_id: str, dataset_key: str) -> str:
    stage_token = stage_id.strip().lower()
    dataset_tail = dataset_key.strip().split(".", maxsplit=1)[-1]
    if dataset_tail.endswith(".workbook"):
        dataset_tail = dataset_tail[: -len(".workbook")]
    if dataset_tail.endswith(".doc"):
        dataset_tail = dataset_tail[: -len(".doc")]
    return f"{stage_token}.{dataset_tail}"


def _target_input_artifact_id_from_edge(edge_execution: dict[str, Any]) -> str | None:
    bindings = edge_execution.get("input_bindings")
    if not isinstance(bindings, dict):
        return None
    target_input_artifact_id = bindings.get("target_input_artifact_version_id")
    if target_input_artifact_id is None:
        return None
    return str(target_input_artifact_id)


def _correlation_key(
    *,
    edge_id: str,
    source_workflow_run_id: str,
    source_artifact_version_id: str,
    target_partition_key: str,
) -> str:
    return _digest(edge_id, source_workflow_run_id, source_artifact_version_id, target_partition_key)


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
