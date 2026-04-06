from __future__ import annotations

from datetime import date, datetime
from functools import lru_cache
import hashlib
from pathlib import Path
import sqlite3
from typing import Any
from zoneinfo import ZoneInfo

import yaml

from onetruth.application.handlers._shared.command_boundary import CommandError
from onetruth.application.handlers.logistics_handoff import prepare_live_dispatch_day_command
from onetruth.application.handlers.workflow_task_lifecycle import (
    create_task_run_command,
    create_workflow_run_command,
)
from onetruth.domain.partition_codec import (
    service_day_to_future_planning_week,
    validate_partition_key,
)
from onetruth.infrastructure.repositories.artifact_pointers import get_pointer
from onetruth.infrastructure.repositories.human_tasks import get_human_task_by_task_run_id
from onetruth.infrastructure.repositories.task_runs import get_task_run_by_activation_key
from onetruth.infrastructure.repositories.workflow_runs import list_workflow_runs


LOGISTICS_OPERATOR_TENANT_ID = "tenant-logistics"
LOGISTICS_OPERATOR_DOMAIN_ID = "domain-hub"
WEEKLY_WORKFLOW_ID = "weekly_schedule_planning.v1"
REPORTING_WORKFLOW_ID = "dispatch_reporting.v1"
LIVE_WORKFLOW_ID = "live_dispatch.v1"
WEEKLY_PUBLISHED_POINTER_KEY = "official:planning.published_weekly_schedule.workbook"
_CADENCE_ACTOR_ID = "system:logistics-cadence"
_CADENCE_ACTOR_TYPE = "system"

_REPO_ROOT = Path(__file__).resolve().parents[4]
_LIVE_DISPATCH_CONTRACT_PATH = (
    _REPO_ROOT / "docs" / "workflows" / "live_dispatch" / "v1" / "WORKFLOW_CONTRACT.yaml"
)


def tick_logistics_operational_cadence(
    connection: sqlite3.Connection,
    *,
    service_date_id: str | None = None,
    actor_id: str = _CADENCE_ACTOR_ID,
    actor_type: str = _CADENCE_ACTOR_TYPE,
) -> dict[str, Any]:
    effective_service_date_id = _resolve_effective_service_date_id(service_date_id)
    effective_service_date = _parse_service_date_id(effective_service_date_id)
    effective_planning_week_id = service_day_to_future_planning_week(effective_service_date_id)

    weekly = _tick_weekly_lane(
        connection,
        planning_week_id=effective_planning_week_id,
        service_date=effective_service_date,
        actor_id=actor_id,
        actor_type=actor_type,
    )
    reporting = _tick_reporting_lane(
        connection,
        service_date_id=effective_service_date_id,
        actor_id=actor_id,
        actor_type=actor_type,
    )
    live_dispatch = _tick_live_dispatch_lane(
        connection,
        planning_week_id=effective_planning_week_id,
        service_date_id=effective_service_date_id,
        actor_id=actor_id,
        actor_type=actor_type,
    )

    return {
        "effective_service_date_id": effective_service_date_id,
        "effective_planning_week_id": effective_planning_week_id,
        "weekly": weekly,
        "reporting": reporting,
        "live_dispatch": live_dispatch,
    }


def _tick_weekly_lane(
    connection: sqlite3.Connection,
    *,
    planning_week_id: str,
    service_date: date,
    actor_id: str,
    actor_type: str,
) -> dict[str, Any]:
    if service_date.weekday() != 4:
        existing_run = _find_partition_workflow_run(
            connection,
            workflow_id=WEEKLY_WORKFLOW_ID,
            partition_key=planning_week_id,
        )
        human_task_id, human_task_state = (
            _resolve_existing_human_task(
                connection,
                workflow_run_id=str(existing_run["workflow_run_id"]),
                activation_key=_weekly_task_activation_key(planning_week_id),
                expected_stage_id="Stage04",
                expected_task_kind="weekly_input_intake",
            )
            if existing_run is not None
            else (None, None)
        )
        return _lane_payload(
            status="skipped",
            workflow_run_id=(
                str(existing_run["workflow_run_id"]) if existing_run is not None else None
            ),
            human_task_id=human_task_id,
            human_task_state=human_task_state,
            skipped_reason="not_planning_day",
        )

    workflow_run, workflow_run_created = _ensure_workflow_run(
        connection,
        workflow_id=WEEKLY_WORKFLOW_ID,
        partition_key=planning_week_id,
        logical_date=_planning_week_start(planning_week_id),
        activation_key=_weekly_run_activation_key(planning_week_id),
        workflow_run_id=_stable_id(
            "wr-logistics-cadence",
            WEEKLY_WORKFLOW_ID,
            planning_week_id,
            LOGISTICS_OPERATOR_TENANT_ID,
            LOGISTICS_OPERATOR_DOMAIN_ID,
        ),
        idempotency_key=f"cadence:runs.create:weekly:{planning_week_id}",
        actor_id=actor_id,
        actor_type=actor_type,
    )
    human_task, human_task_created = _ensure_human_task(
        connection,
        workflow_run_id=str(workflow_run["workflow_run_id"]),
        stage_id="Stage04",
        task_kind="weekly_input_intake",
        activation_key=_weekly_task_activation_key(planning_week_id),
        candidate_roles=["schedule_planner"],
        owner_role="schedule_planner",
        task_run_id=_stable_id(
            "tr-logistics-cadence",
            str(workflow_run["workflow_run_id"]),
            "Stage04",
            "weekly_input_intake",
        ),
        human_task_id=_stable_id(
            "ht-logistics-cadence",
            str(workflow_run["workflow_run_id"]),
            "Stage04",
            "weekly_input_intake",
        ),
        idempotency_key=(
            "cadence:tasks.create:"
            f"weekly:{planning_week_id}:stage04:weekly_input_intake"
        ),
        actor_id=actor_id,
        actor_type=actor_type,
    )
    return _lane_payload(
        status="created" if workflow_run_created or human_task_created else "existing",
        workflow_run_id=str(workflow_run["workflow_run_id"]),
        human_task_id=str(human_task["human_task_id"]),
        human_task_state=str(human_task["state"]),
    )


def _tick_reporting_lane(
    connection: sqlite3.Connection,
    *,
    service_date_id: str,
    actor_id: str,
    actor_type: str,
) -> dict[str, Any]:
    workflow_run, workflow_run_created = _ensure_workflow_run(
        connection,
        workflow_id=REPORTING_WORKFLOW_ID,
        partition_key=service_date_id,
        logical_date=service_date_id.removeprefix("SD-"),
        activation_key=_reporting_run_activation_key(service_date_id),
        workflow_run_id=_stable_id(
            "wr-logistics-cadence",
            REPORTING_WORKFLOW_ID,
            service_date_id,
            LOGISTICS_OPERATOR_TENANT_ID,
            LOGISTICS_OPERATOR_DOMAIN_ID,
        ),
        idempotency_key=f"cadence:runs.create:reporting:{service_date_id}",
        actor_id=actor_id,
        actor_type=actor_type,
    )
    human_task, human_task_created = _ensure_human_task(
        connection,
        workflow_run_id=str(workflow_run["workflow_run_id"]),
        stage_id="Stage01",
        task_kind="eos_input_intake",
        activation_key=_reporting_task_activation_key(service_date_id),
        candidate_roles=["dispatch_supervisor"],
        owner_role="dispatch_supervisor",
        task_run_id=_stable_id(
            "tr-logistics-cadence",
            str(workflow_run["workflow_run_id"]),
            "Stage01",
            "eos_input_intake",
        ),
        human_task_id=_stable_id(
            "ht-logistics-cadence",
            str(workflow_run["workflow_run_id"]),
            "Stage01",
            "eos_input_intake",
        ),
        idempotency_key=(
            "cadence:tasks.create:"
            f"reporting:{service_date_id}:stage01:eos_input_intake"
        ),
        actor_id=actor_id,
        actor_type=actor_type,
    )
    return _lane_payload(
        status="created" if workflow_run_created or human_task_created else "existing",
        workflow_run_id=str(workflow_run["workflow_run_id"]),
        human_task_id=str(human_task["human_task_id"]),
        human_task_state=str(human_task["state"]),
    )


def _tick_live_dispatch_lane(
    connection: sqlite3.Connection,
    *,
    planning_week_id: str,
    service_date_id: str,
    actor_id: str,
    actor_type: str,
) -> dict[str, Any]:
    weekly_run = _find_partition_workflow_run(
        connection,
        workflow_id=WEEKLY_WORKFLOW_ID,
        partition_key=planning_week_id,
    )
    if weekly_run is None:
        return _lane_payload(status="skipped", skipped_reason="waiting_on_weekly_publish")

    published_pointer = get_pointer(
        connection,
        workflow_run_id=str(weekly_run["workflow_run_id"]),
        pointer_key=WEEKLY_PUBLISHED_POINTER_KEY,
    )
    if published_pointer is None:
        return _lane_payload(status="skipped", skipped_reason="waiting_on_weekly_publish")

    published_artifact_version_id = str(published_pointer.get("artifact_version_id") or "").strip()
    if not published_artifact_version_id:
        return _lane_payload(status="skipped", skipped_reason="waiting_on_weekly_publish")

    live_run = _find_partition_workflow_run(
        connection,
        workflow_id=LIVE_WORKFLOW_ID,
        partition_key=service_date_id,
    )
    prepared = prepare_live_dispatch_day_command(
        connection,
        {
            "workflow_run_id": str(weekly_run["workflow_run_id"]),
            "published_artifact_version_id": published_artifact_version_id,
            "service_date_id": service_date_id,
            "idempotency_key": (
                "cadence:prepare-live-dispatch:"
                f"{service_date_id}:{published_artifact_version_id}"
            ),
            "actor_id": actor_id,
            "actor_type": actor_type,
        },
    )
    return _lane_payload(
        status="created" if live_run is None else "existing",
        workflow_run_id=str(prepared["target_workflow_run"]["workflow_run_id"]),
        human_task_id=str(prepared["seed_intake_task"]["human_task_id"]),
        edge_execution_id=str(prepared["edge_execution"]["edge_execution_id"]),
    )


def _ensure_workflow_run(
    connection: sqlite3.Connection,
    *,
    workflow_id: str,
    partition_key: str,
    logical_date: str,
    activation_key: str,
    workflow_run_id: str,
    idempotency_key: str,
    actor_id: str,
    actor_type: str,
) -> tuple[dict[str, Any], bool]:
    existing = _find_partition_workflow_run(
        connection,
        workflow_id=workflow_id,
        partition_key=partition_key,
    )
    if existing is not None:
        return existing, False

    created = create_workflow_run_command(
        connection,
        {
            "workflow_run_id": workflow_run_id,
            "workflow_id": workflow_id,
            "workflow_version": "v1",
            "tenant_id": LOGISTICS_OPERATOR_TENANT_ID,
            "domain_id": LOGISTICS_OPERATOR_DOMAIN_ID,
            "partition_key": partition_key,
            "logical_date": logical_date,
            "activation_key": activation_key,
            "idempotency_key": idempotency_key,
            "actor_id": actor_id,
            "actor_type": actor_type,
        },
        include_receipt=True,
    )
    return created["result"], True


def _ensure_human_task(
    connection: sqlite3.Connection,
    *,
    workflow_run_id: str,
    stage_id: str,
    task_kind: str,
    activation_key: str,
    candidate_roles: list[str],
    owner_role: str | None,
    task_run_id: str,
    human_task_id: str,
    idempotency_key: str,
    actor_id: str,
    actor_type: str,
) -> tuple[dict[str, Any], bool]:
    existing_task_run = get_task_run_by_activation_key(
        connection,
        workflow_run_id=workflow_run_id,
        activation_key=activation_key,
    )
    if existing_task_run is not None:
        if (
            str(existing_task_run.get("stage_id") or "") != stage_id
            or str(existing_task_run.get("task_kind") or "") != task_kind
        ):
            raise CommandError(
                code="duplicate_activation_key_for_other_task",
                message="activation key is already used by another task in this workflow run",
                details={
                    "workflow_run_id": workflow_run_id,
                    "activation_key": activation_key,
                    "task_run_id": str(existing_task_run["task_run_id"]),
                    "expected_stage_id": stage_id,
                    "expected_task_kind": task_kind,
                    "actual_stage_id": str(existing_task_run.get("stage_id") or ""),
                    "actual_task_kind": str(existing_task_run.get("task_kind") or ""),
                },
            )
        existing_human_task = get_human_task_by_task_run_id(
            connection,
            str(existing_task_run["task_run_id"]),
        )
        if existing_human_task is None:
            raise CommandError(
                code="human_task_missing_for_existing_task_run",
                message="existing cadence task run is missing its human task",
                details={
                    "workflow_run_id": workflow_run_id,
                    "task_run_id": str(existing_task_run["task_run_id"]),
                    "activation_key": activation_key,
                },
            )
        return existing_human_task, False

    created = create_task_run_command(
        connection,
        {
            "workflow_run_id": workflow_run_id,
            "task_run_id": task_run_id,
            "human_task_id": human_task_id,
            "stage_id": stage_id,
            "task_kind": task_kind,
            "activation_key": activation_key,
            "candidate_roles": candidate_roles,
            "owner_role": owner_role,
            "create_human_task": True,
            "idempotency_key": idempotency_key,
            "actor_id": actor_id,
            "actor_type": actor_type,
        },
        include_receipt=True,
    )
    return created["result"]["human_task"], True


def _find_partition_workflow_run(
    connection: sqlite3.Connection,
    *,
    workflow_id: str,
    partition_key: str,
) -> dict[str, Any] | None:
    matches = [
        run
        for run in list_workflow_runs(
            connection,
            workflow_id=workflow_id,
            tenant_id=LOGISTICS_OPERATOR_TENANT_ID,
            domain_id=LOGISTICS_OPERATOR_DOMAIN_ID,
            state=None,
        )
        if str(run.get("partition_key") or "") == partition_key
    ]
    if not matches:
        return None
    if len(matches) != 1:
        raise CommandError(
            code="multiple_partition_workflow_runs",
            message="cadence expected one workflow run per partition in the first-user logistics lane",
            details={
                "workflow_id": workflow_id,
                "partition_key": partition_key,
                "workflow_run_ids": [str(run["workflow_run_id"]) for run in matches],
            },
        )
    return matches[0]


def _resolve_existing_human_task(
    connection: sqlite3.Connection,
    *,
    workflow_run_id: str,
    activation_key: str,
    expected_stage_id: str,
    expected_task_kind: str,
) -> tuple[str | None, str | None]:
    existing_task_run = get_task_run_by_activation_key(
        connection,
        workflow_run_id=workflow_run_id,
        activation_key=activation_key,
    )
    if existing_task_run is None:
        return None, None
    if (
        str(existing_task_run.get("stage_id") or "") != expected_stage_id
        or str(existing_task_run.get("task_kind") or "") != expected_task_kind
    ):
        raise CommandError(
            code="duplicate_activation_key_for_other_task",
            message="activation key is already used by another task in this workflow run",
            details={
                "workflow_run_id": workflow_run_id,
                "activation_key": activation_key,
                "task_run_id": str(existing_task_run["task_run_id"]),
                "expected_stage_id": expected_stage_id,
                "expected_task_kind": expected_task_kind,
                "actual_stage_id": str(existing_task_run.get("stage_id") or ""),
                "actual_task_kind": str(existing_task_run.get("task_kind") or ""),
            },
        )
    existing_human_task = get_human_task_by_task_run_id(
        connection,
        str(existing_task_run["task_run_id"]),
    )
    if existing_human_task is None:
        raise CommandError(
            code="human_task_missing_for_existing_task_run",
            message="existing cadence task run is missing its human task",
            details={
                "workflow_run_id": workflow_run_id,
                "task_run_id": str(existing_task_run["task_run_id"]),
                "activation_key": activation_key,
            },
        )
    return str(existing_human_task["human_task_id"]), str(existing_human_task["state"])


def _lane_payload(
    *,
    status: str,
    workflow_run_id: str | None = None,
    human_task_id: str | None = None,
    human_task_state: str | None = None,
    edge_execution_id: str | None = None,
    skipped_reason: str | None = None,
) -> dict[str, Any]:
    return {
        "status": status,
        "workflow_run_id": workflow_run_id,
        "human_task_id": human_task_id,
        "human_task_state": human_task_state,
        "edge_execution_id": edge_execution_id,
        "skipped_reason": skipped_reason,
    }


def _resolve_effective_service_date_id(service_date_id: str | None) -> str:
    if service_date_id is not None:
        validate_partition_key("ServiceDateID", service_date_id)
        return service_date_id
    current_date = datetime.now(_default_service_timezone()).date()
    return f"SD-{current_date.isoformat()}"


@lru_cache(maxsize=1)
def _default_service_timezone() -> ZoneInfo:
    loaded = yaml.safe_load(_LIVE_DISPATCH_CONTRACT_PATH.read_text(encoding="utf-8"))
    workflow = loaded.get("workflow") or {}
    temporal_partition = workflow.get("temporal_partition") or {}
    service_timezone = temporal_partition.get("service_timezone") or {}
    timezone_name = str(service_timezone.get("default") or "").strip()
    if not timezone_name:
        raise RuntimeError(
            "live_dispatch.v1 WORKFLOW_CONTRACT.yaml is missing workflow.temporal_partition.service_timezone.default"
        )
    return ZoneInfo(timezone_name)


def _parse_service_date_id(service_date_id: str) -> date:
    validate_partition_key("ServiceDateID", service_date_id)
    return date.fromisoformat(service_date_id.removeprefix("SD-"))


def _planning_week_start(planning_week_id: str) -> str:
    validate_partition_key("PlanningWeekID", planning_week_id)
    token = planning_week_id.removeprefix("PW-")
    year_text, week_text = token.split("-W", maxsplit=1)
    return date.fromisocalendar(int(year_text), int(week_text), 1).isoformat()


def _weekly_run_activation_key(planning_week_id: str) -> str:
    return f"logistics-cadence:weekly:{planning_week_id}"


def _weekly_task_activation_key(planning_week_id: str) -> str:
    return f"logistics-cadence:weekly:{planning_week_id}:stage04:weekly_input_intake"


def _reporting_run_activation_key(service_date_id: str) -> str:
    return f"logistics-cadence:reporting:{service_date_id}"


def _reporting_task_activation_key(service_date_id: str) -> str:
    return f"logistics-cadence:reporting:{service_date_id}:stage01:eos_input_intake"


def _stable_id(prefix: str, *parts: str) -> str:
    digest = hashlib.sha256("|".join(parts).encode("utf-8")).hexdigest()[:12]
    return f"{prefix}-{digest}"
