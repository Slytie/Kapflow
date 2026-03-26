from __future__ import annotations

import json
from typing import Any

import yaml

from onetruth.application.services.logistics_weekly_agent_pilot import (
    build_actual_ops_weekly_stage04_fixture_payloads,
)

from .runtime_cli import REPO_ROOT, run_cli, stdout_json


_ACTUAL_OPS_SOURCE_MATERIAL_PATH = (
    REPO_ROOT / "fixtures" / "logistics" / "weekly_stage04_actual_ops_lab_source_material_v2.yaml"
)

_DATASET_PAYLOAD_KEYS: tuple[tuple[str, str], ...] = (
    ("planning.route_slot_requirements.workbook", "route_slot_requirements"),
    ("planning.driver_capabilities.workbook", "driver_capabilities"),
    ("planning.approved_availability.workbook", "approved_availability"),
    ("planning.actual_hours_snapshot.workbook", "actual_hours"),
)


def seed_actual_ops_weekly_schedule_run(
    *,
    db_url: str,
    tenant_id: str,
    domain_id: str,
    run_tag: str,
) -> dict[str, Any]:
    source_material = _load_actual_ops_source_material()
    fixture_payloads = build_actual_ops_weekly_stage04_fixture_payloads()

    run_cli("--db-url", db_url, "init-db")
    created_run = run_cli(
        "--db-url",
        db_url,
        "runs",
        "create",
        "--json",
        json.dumps(
            {
                "workflow_id": "weekly_schedule_planning.v1",
                "workflow_version": "v1",
                "tenant_id": tenant_id,
                "domain_id": domain_id,
                "partition_key": str(source_material["planning_week_id"]),
                "logical_date": str(source_material["scope_start"]),
                "activation_key": f"{run_tag}:weekly-schedule-workpage",
                "idempotency_key": f"{run_tag}:runs.create",
            },
            separators=(",", ":"),
        ),
    )
    workflow_run = stdout_json(created_run)["workflow_run"]
    workflow_run_id = str(workflow_run["workflow_run_id"])

    artifacts_by_kind: dict[str, dict[str, Any]] = {}
    for artifact_kind, payload_key in _DATASET_PAYLOAD_KEYS:
        created_artifact = run_cli(
            "--db-url",
            db_url,
            "artifacts",
            "create-version",
            "--json",
            json.dumps(
                {
                    "workflow_run_id": workflow_run_id,
                    "artifact_kind": artifact_kind,
                    "artifact_role": "official_input",
                    "media_type": "application/json",
                    "storage_uri": f"inmem://workpages/{run_tag}/{artifact_kind}",
                    "content_digest": f"sha256:{run_tag}:{artifact_kind}",
                    "metadata_json": fixture_payloads[payload_key],
                    "idempotency_key": f"{run_tag}:artifacts.create:{artifact_kind}",
                },
                separators=(",", ":"),
            ),
        )
        artifacts_by_kind[artifact_kind] = stdout_json(created_artifact)["artifact_version"]

    return {
        "workflow_run": workflow_run,
        "workflow_run_id": workflow_run_id,
        "artifacts_by_kind": artifacts_by_kind,
        "fixture_contract": str(source_material["fixture_contract"]),
    }


def _load_actual_ops_source_material() -> dict[str, Any]:
    loaded = yaml.safe_load(_ACTUAL_OPS_SOURCE_MATERIAL_PATH.read_text(encoding="utf-8"))
    if not isinstance(loaded, dict):
        raise AssertionError("weekly Stage04 actual-ops source material must decode to an object")
    return loaded
