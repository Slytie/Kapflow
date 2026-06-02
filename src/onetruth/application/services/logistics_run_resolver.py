from __future__ import annotations

from dataclasses import dataclass
from datetime import date
import sqlite3
from typing import Any

from onetruth.application.handlers._shared.runtime_effects import (
    resolve_or_create_workflow_run_effects,
)
from onetruth.domain.partition_codec import validate_partition_key


@dataclass(frozen=True)
class LogisticsRunResolver:
    workflow_version: str = "v1"

    def resolve_or_create(
        self,
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
        return resolve_or_create_workflow_run_effects(
            connection,
            workflow_id=workflow_id,
            workflow_version=self.workflow_version,
            tenant_id=tenant_id,
            domain_id=domain_id,
            partition_kind=partition_kind,
            partition_key=partition_key,
            logical_date=logistics_logical_date_from_partition_key(
                partition_kind=partition_kind,
                partition_key=partition_key,
            ),
            activation_key=activation_key,
            state="OPEN",
            created_at=created_at,
        )

    def resolve_or_create_live_dispatch(
        self,
        connection: sqlite3.Connection,
        *,
        tenant_id: str,
        domain_id: str,
        workflow_id: str,
        service_date_id: str,
        activation_key: str,
        created_at: str,
    ) -> dict[str, Any]:
        return self.resolve_or_create(
            connection,
            workflow_id=workflow_id,
            tenant_id=tenant_id,
            domain_id=domain_id,
            partition_kind="ServiceDateID",
            partition_key=service_date_id,
            activation_key=activation_key,
            created_at=created_at,
        )


def logistics_logical_date_from_partition_key(
    *,
    partition_kind: str,
    partition_key: str,
) -> str:
    validate_partition_key(partition_kind, partition_key)
    if partition_kind == "ServiceDateID":
        return partition_key.removeprefix("SD-")
    if partition_kind in {"PlanningWeekID", "PayPeriodID"}:
        token = (
            partition_key.removeprefix("PW-")
            if partition_kind == "PlanningWeekID"
            else partition_key.removeprefix("PP-")
        )
        year_text, week_text = token.split("-W", maxsplit=1)
        return date.fromisocalendar(int(year_text), int(week_text), 1).isoformat()
    return partition_key
