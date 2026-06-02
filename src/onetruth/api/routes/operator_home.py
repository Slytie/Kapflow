from __future__ import annotations

import sqlite3
from typing import Any

from onetruth.api.dependencies import BoundaryProfile, RequestContext
from onetruth.application.services.logistics_reconciler import (
    run_logistics_reconciler_dry_run,
)


def get_operator_home_endpoint(
    connection: sqlite3.Connection,
    *,
    context: RequestContext,
    boundary_profile: BoundaryProfile,
) -> dict[str, Any]:
    report = run_logistics_reconciler_dry_run(
        connection,
        tenant_id=context.tenant_id,
        domain_id=context.domain_id,
        boundary_profile=boundary_profile,
    )
    summary = report["summary"]
    status = "attention" if int(summary.get("finding_count") or 0) > 0 else "clear"
    return {
        "status": "ok",
        "command": "api.operator.home",
        "operator_home": {
            "schema_version": "operator_home.v1",
            "status": status,
            "viewer": {
                "tenant_id": context.tenant_id,
                "domain_id": context.domain_id,
                "actor_id": context.actor_id,
                "actor_type": context.actor_type,
                "actor_roles": list(context.actor_roles),
                "boundary_profile": boundary_profile,
                "actor_switching_allowed": boundary_profile in {"local_dev", "ci_test"},
            },
            "failure_state": {
                "schema_version": report["schema_version"],
                "mode": report["mode"],
                "summary": summary,
                "findings": report["findings"],
            },
        },
    }
