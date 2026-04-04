from __future__ import annotations

import copy
from contextlib import ExitStack, contextmanager
from dataclasses import dataclass
from datetime import date
import hashlib
import json
import os
from pathlib import Path
import sqlite3
from typing import Any, Iterable, Sequence
from urllib.parse import urlparse

import yaml

from onetruth.application.handlers._shared.command_boundary import CommandError
from onetruth.application.handlers.approvals import (
    list_approvals_for_workflow_run_command,
)
from onetruth.application.handlers.artifacts import create_artifact_version_command
from onetruth.application.handlers.human_tasks import claim_human_task_command
from onetruth.application.handlers.workflow_task_lifecycle import (
    create_task_run_command,
    create_workflow_run_command,
)
from onetruth.application.read_commands import (
    list_artifacts_for_workflow_run_command,
    list_execution_sessions_for_workflow_run_command,
    list_flags_for_workflow_run_command,
    list_pointers_for_workflow_run_command,
    list_tasks_for_workflow_run_command,
    show_human_task_command,
    show_workflow_run_command,
)
from onetruth.application.services.weekly_stage04_openai_agent import (
    run_weekly_stage04_openai_agent,
)
from onetruth.application.services.schedule_control.route_slot_requirements import (
    expand_route_slot_requirements,
    parse_route_slot_requirements,
)
from onetruth.application.services.workflow_lab_normalization import (
    normalize_weekly_stage04_report,
    write_workflow_lab_artifacts,
)
from onetruth.infrastructure.artifacts.storage import default_storage_root_for_db_url
from onetruth.infrastructure.events.event_store import (
    DuplicateIdempotencyKeyError,
    list_events,
    utc_now_iso,
)
from onetruth.infrastructure.repositories.policy_decisions import (
    get_policy_decision,
    get_policy_decision_for_tool_execution,
)
from onetruth.infrastructure.repositories.tool_executions import (
    list_tool_executions_for_session,
)
from onetruth.integrations.openai import OpenAIResponsesFunctionCallingRunner

WORKFLOW_ID = "weekly_schedule_planning.v1"
WORKFLOW_VERSION = "v1"
TENANT_ID = "tenant-logistics"
DOMAIN_ID = "domain-hub"
REPO_ROOT = Path(__file__).resolve().parents[4]
REALISTIC_WEEKLY_STAGE04_SOURCE_MATERIAL_PATH = (
    REPO_ROOT / "fixtures" / "logistics" / "weekly_stage04_realistic_source_material.yaml"
)
ACTUAL_OPS_WEEKLY_STAGE04_SOURCE_MATERIAL_PATH = (
    REPO_ROOT / "fixtures" / "logistics" / "weekly_stage04_actual_ops_lab_source_material_v3.yaml"
)
ACTUAL_OPS_V4_WEEKLY_STAGE04_SOURCE_MATERIAL_PATH = (
    REPO_ROOT / "fixtures" / "logistics" / "weekly_stage04_actual_ops_lab_source_material_v4.yaml"
)

PILOT_WEEKLY_STAGE04_AGENT = "weekly_stage04_agent_baseline"
PILOT_WEEKLY_STAGE04_REALISTIC_ARTIFACTS = "weekly_stage04_realistic_artifacts"
PILOT_WEEKLY_STAGE04_ACTUAL_OPS_LAB = "weekly_stage04_actual_ops_lab"
PILOT_WEEKLY_STAGE04_ACTUAL_OPS_LAB_V4 = "weekly_stage04_actual_ops_lab_v4"
ALL_PILOT_IDS: tuple[str, ...] = (
    PILOT_WEEKLY_STAGE04_AGENT,
    PILOT_WEEKLY_STAGE04_REALISTIC_ARTIFACTS,
    PILOT_WEEKLY_STAGE04_ACTUAL_OPS_LAB,
    PILOT_WEEKLY_STAGE04_ACTUAL_OPS_LAB_V4,
)
DEFAULT_MOCK_PILOT_IDS: tuple[str, ...] = (
    PILOT_WEEKLY_STAGE04_AGENT,
    PILOT_WEEKLY_STAGE04_REALISTIC_ARTIFACTS,
)
DEFAULT_REAL_OPENAI_PILOT_IDS: tuple[str, ...] = (
    PILOT_WEEKLY_STAGE04_REALISTIC_ARTIFACTS,
)

EVENT_TYPES_OF_INTEREST = {
    "workflow.run.created",
    "task.run.created",
    "task.created",
    "task.claimed",
    "artifact.version.created",
    "execution.session.created",
    "execution.session.state_changed",
    "tool.execution.requested",
    "tool.execution.approved",
    "tool.execution.denied",
    "tool.execution.completed",
}

EXECUTION_SEMANTICS_EVIDENCE_KINDS = {
    "execution.compiled_spec.json",
    "execution.compile_source_manifest.json",
}
RUNTIME_TURN_EVIDENCE_KINDS = {
    "runtime.context_pack.json",
    "runtime.tool_request.json",
    "runtime.tool_result.json",
    "execution.trace.json",
}
STAGE04_OUTPUT_ARTIFACT_KINDS = {
    "planning.input_bundle.doc",
    "planning.candidate_schedule_delta.workbook",
    "planning.validation_summary.doc",
    "planning.draft_weekly_schedule.workbook",
    "planning.draft_weekly_schedule.doc",
}

_ROUTE_SLOT_REQUIREMENTS_METADATA = {
    "columns": [
        "service_date",
        "route_slot_id",
        "route_slot_class",
        "required_skill",
        "vehicle_type",
        "shift_start",
        "shift_end",
        "estimated_hours",
        "required_count",
        "route_id",
        "source_message_id",
        "station_code",
        "service_area",
        "source_snapshot_row_ref",
    ],
    "rows": [
        [
            "2026-03-02",
            "slot-20260302-cx100",
            "cycle1_standard",
            "parcel_delivery",
            "XL_van",
            "11:40",
            "20:10",
            8.5,
            1,
            "CX100",
            "amazon-2026-02-27-1518",
            "DVC4",
            "Pitt Meadows",
            "amazon:row-001",
        ],
        [
            "2026-03-03",
            "slot-20260303-cx086",
            "cycle1_rescue",
            "rescue_support",
            "XL_van",
            "11:45",
            "21:00",
            8.8,
            1,
            "CX086",
            "amazon-2026-02-27-1518",
            "DVC4",
            "Pitt Meadows",
            "amazon:row-002",
        ],
    ],
    "daily_demand_columns": [
        "service_date",
        "planned_route_count",
        "standard_slot_count",
        "rescue_slot_count",
        "overflow_slot_count",
        "source_message_id",
        "source_kind",
        "change_kind",
    ],
    "daily_demand_rows": [
        ["2026-03-02", 1, 1, 0, 0, "amazon-2026-02-27-1518", "weekly_route_update", "decrease"],
        ["2026-03-03", 1, 0, 1, 0, "amazon-2026-02-27-1518", "weekly_route_update", "increase"],
    ],
}

_DRIVER_CAPABILITIES_METADATA = {
    "columns": [
        "driver_id",
        "driver_name",
        "employment_type",
        "home_station",
        "skills",
        "vehicle_certifications",
        "eligible_route_slot_classes",
        "approved_restrictions",
        "policy_tags",
        "notes",
    ],
    "rows": [
        [
            "DRV-01",
            "Brahamvir Singh",
            "full_time",
            "DVC4",
            "parcel_delivery,rescue_support",
            "XL_van",
            "cycle1_standard,cycle1_rescue",
            "max_minutes_rolling7=2400",
            "anchor,can_rescue",
            "Anchor",
        ],
        [
            "DRV-02",
            "Iqbal Singh",
            "full_time",
            "DVC4",
            "parcel_delivery",
            "XL_van",
            "cycle1_standard",
            "no_shift_after_21_30,max_minutes_rolling7=1800",
            "on_call,restricted_close",
            "On-call",
        ],
    ],
}

_APPROVED_AVAILABILITY_METADATA = {
    "columns": [
        "driver_id",
        "driver_name",
        "employment_type",
        "target_shifts_per_week",
        "on_call_eligible",
        "approved_unavailable_dates",
        "regular_pattern",
        "emergency_only",
        "previous_week_blocked_dates",
        "policy_tags",
        "notes",
    ],
    "rows": [
        [
            "DRV-01",
            "Brahamvir Singh",
            "full_time",
            4,
            "no",
            "",
            "Mon,Tue,Wed,Thu",
            "no",
            "",
            "anchor,cycle1",
            "Tiny smoke availability row",
        ],
        [
            "DRV-02",
            "Iqbal Singh",
            "full_time",
            4,
            "yes",
            "",
            "Mon,Tue,Wed,Thu",
            "no",
            "",
            "on_call,restricted_close",
            "Tiny smoke availability row",
        ],
    ],
}

_ACTUAL_HOURS_METADATA = {
    "columns": [
        "service_date",
        "driver_id",
        "driver_name",
        "actual_minutes",
        "route_id",
        "source",
        "source_snapshot_row_ref",
    ],
    "rows": [
        ["2026-02-26", "DRV-01", "Brahamvir Singh", 800, "CX100", "EOS 2026-02-26", "eos:2026-02-26:DRV-01:CX100"],
        ["2026-02-26", "DRV-02", "Iqbal Singh", 1200, "CX086", "EOS 2026-02-26", "eos:2026-02-26:DRV-02:CX086"],
        ["2026-02-27", "DRV-02", "Iqbal Singh", 1800, "CX092", "EOS 2026-02-27", "eos:2026-02-27:DRV-02:CX092"],
    ],
}


@dataclass(frozen=True)
class WeeklyPilotDefinition:
    pilot_id: str
    partition_key: str
    logical_date: str
    stage_focus: str
    description: str
    source_material_loader: str = "inline"
    source_material_path: Path | None = None
    real_openai_model: str | None = None


PILOT_DEFINITIONS: dict[str, WeeklyPilotDefinition] = {
    PILOT_WEEKLY_STAGE04_AGENT: WeeklyPilotDefinition(
        pilot_id=PILOT_WEEKLY_STAGE04_AGENT,
        partition_key="PW-2026-W10",
        logical_date="2026-03-02",
        stage_focus="Stage04",
        description="Weekly Stage04 bounded OpenAI agent run over deterministic schedule-control inputs.",
    ),
    PILOT_WEEKLY_STAGE04_REALISTIC_ARTIFACTS: WeeklyPilotDefinition(
        pilot_id=PILOT_WEEKLY_STAGE04_REALISTIC_ARTIFACTS,
        partition_key="PW-2026-W12",
        logical_date="2026-03-16",
        stage_focus="Stage04",
        description=(
            "Weekly Stage04 bounded OpenAI agent run over realistic day-resolution planning "
            "artifacts derived from the over-capacity weekly hard-case handoff."
        ),
        source_material_loader="realistic_manifest_enriched",
        source_material_path=REALISTIC_WEEKLY_STAGE04_SOURCE_MATERIAL_PATH,
        real_openai_model="gpt-5-mini",
    ),
    PILOT_WEEKLY_STAGE04_ACTUAL_OPS_LAB: WeeklyPilotDefinition(
        pilot_id=PILOT_WEEKLY_STAGE04_ACTUAL_OPS_LAB,
        partition_key="PW-2026-W13",
        logical_date="2026-03-22",
        stage_focus="Stage04",
        description=(
            "Weekly Stage04 bounded OpenAI agent run over the normalized actual-ops lab "
            "package with explicit Sunday-start operational scope."
        ),
        source_material_loader="manifest_identity",
        source_material_path=ACTUAL_OPS_WEEKLY_STAGE04_SOURCE_MATERIAL_PATH,
    ),
    PILOT_WEEKLY_STAGE04_ACTUAL_OPS_LAB_V4: WeeklyPilotDefinition(
        pilot_id=PILOT_WEEKLY_STAGE04_ACTUAL_OPS_LAB_V4,
        partition_key="PW-2026-W13",
        logical_date="2026-03-22",
        stage_focus="Stage04",
        description=(
            "Weekly Stage04 bounded OpenAI agent rerun over the pilot-local actual-ops "
            "v4 package that removes prior-week-derived 1/2-shift heuristics for the "
            "four low-shift drivers while preserving the same route-count and buffer seam."
        ),
        source_material_loader="manifest_identity",
        source_material_path=ACTUAL_OPS_V4_WEEKLY_STAGE04_SOURCE_MATERIAL_PATH,
    ),
}


def resolve_weekly_stage04_pilot_ids(
    pilot_ids: Sequence[str] | None,
    *,
    openai_mode: str,
) -> tuple[str, ...]:
    if openai_mode not in {"mock", "real"}:
        raise ValueError("openai_mode must be 'mock' or 'real'")

    if not pilot_ids:
        return DEFAULT_REAL_OPENAI_PILOT_IDS if openai_mode == "real" else DEFAULT_MOCK_PILOT_IDS

    normalized = tuple(
        str(pilot_id).strip()
        for pilot_id in pilot_ids
        if str(pilot_id).strip()
    )
    if not normalized:
        return DEFAULT_REAL_OPENAI_PILOT_IDS if openai_mode == "real" else DEFAULT_MOCK_PILOT_IDS
    if "all" in normalized:
        return ALL_PILOT_IDS

    selected = tuple(_dedupe_preserving_order(normalized))
    _validate_selected_pilots(selected)
    return selected


def describe_weekly_stage04_pilot_fixture_profile(pilot_id: str) -> dict[str, Any]:
    _validate_selected_pilots((pilot_id,))
    payloads = _stage04_source_material_for_pilot(pilot_id)
    route_slot_requirements = payloads["route_slot_requirements"]
    driver_capabilities = payloads["driver_capabilities"]
    approved_availability = payloads["approved_availability"]
    actual_hours = payloads["actual_hours"]

    parsed_route_slots = parse_route_slot_requirements(
        columns=[str(column) for column in route_slot_requirements.get("columns") or []],
        rows=list(route_slot_requirements.get("rows") or []),
    )
    availability_columns = {
        str(column).strip()
        for column in approved_availability.get("columns") or []
        if str(column).strip()
    }
    actual_hours_columns = {
        str(column).strip()
        for column in actual_hours.get("columns") or []
        if str(column).strip()
    }

    definition = PILOT_DEFINITIONS[pilot_id]
    source_contract = "weekly_stage04_tiny_smoke_regression"
    source_material_path = None
    if definition.source_material_path is not None:
        source_material = _load_weekly_stage04_source_material(definition.source_material_path)
        source_contract = str(source_material.get("fixture_contract") or source_contract)
        source_material_path = str(definition.source_material_path)

    return {
        "pilot_id": pilot_id,
        "planning_week_id": str(
            route_slot_requirements.get("planning_week_id")
            or definition.partition_key
        ),
        "route_slot_count": len(expand_route_slot_requirements(parsed_route_slots)),
        "driver_count": len(list(driver_capabilities.get("rows") or [])),
        "availability_row_count": len(list(approved_availability.get("rows") or [])),
        "actual_hours_row_count": len(list(actual_hours.get("rows") or [])),
        "has_daily_availability_states": bool(
            {"availability_state", "normalized_availability_state"} & availability_columns
        ),
        "has_previous_week_history": bool(
            {"previous_week_same_day_state", "previous_week_state"} & availability_columns
            or {"historical_state", "normalized_historical_state"} & actual_hours_columns
        ),
        "fixture_contract": source_contract,
        "source_material_path": source_material_path,
    }


def run_logistics_weekly_agent_pilot_suite(
    connection: sqlite3.Connection,
    *,
    db_url: str,
    pilot_key: str,
    output_root: Path,
    artifact_root: Path | None = None,
    pilot_ids: Sequence[str] | None = None,
    openai_mode: str = "mock",
) -> dict[str, Any]:
    if openai_mode not in {"mock", "real"}:
        raise ValueError("openai_mode must be 'mock' or 'real'")
    if openai_mode == "real" and not os.environ.get("OPENAI_API_KEY", "").strip():
        raise ValueError("OPENAI_API_KEY is required when openai_mode='real'")

    selected = resolve_weekly_stage04_pilot_ids(pilot_ids, openai_mode=openai_mode)

    resolved_output_root = output_root.expanduser().resolve() / pilot_key
    resolved_output_root.mkdir(parents=True, exist_ok=True)

    resolved_artifact_root = (
        artifact_root.expanduser().resolve()
        if artifact_root is not None
        else default_storage_root_for_db_url(db_url)
    )
    resolved_artifact_root.mkdir(parents=True, exist_ok=True)
    summary_json_path = resolved_output_root / "pilot_summary.json"
    summary_md_path = resolved_output_root / "pilot_summary.md"

    pilot_results: list[dict[str, Any]] = []
    for pilot_id in selected:
        definition = PILOT_DEFINITIONS[pilot_id]
        workflow_run_id = _deterministic_id("wr", pilot_key, pilot_id, "workflow-run")

        created = _ensure_workflow_run(
            connection,
            definition=definition,
            workflow_run_id=workflow_run_id,
            pilot_key=pilot_key,
        )
        stage04_result: dict[str, Any] | None = None
        if created:
            stage04_result = _run_weekly_stage04_agent_pilot(
                connection,
                definition=definition,
                workflow_run_id=workflow_run_id,
                pilot_key=pilot_key,
                openai_mode=openai_mode,
                storage_root=resolved_artifact_root,
            )

        packet = build_weekly_stage04_inspection_packet(
            connection,
            pilot_id=pilot_id,
            pilot_key=pilot_key,
            workflow_run_id=workflow_run_id,
            definition=definition,
            db_url=db_url,
            openai_mode=openai_mode,
            reused_existing=not created,
            stage04_result=stage04_result,
        )

        pilot_dir = resolved_output_root / pilot_id
        pilot_dir.mkdir(parents=True, exist_ok=True)
        json_path = pilot_dir / "inspection_packet.json"
        md_path = pilot_dir / "inspection_packet.md"
        json_path.write_text(json.dumps(packet, indent=2, sort_keys=True), encoding="utf-8")
        md_path.write_text(_packet_to_markdown(packet), encoding="utf-8")
        workflow_lab_paths = write_workflow_lab_artifacts(
            normalize_weekly_stage04_report(
                {
                    "status": "ok",
                    "pilot_key": pilot_key,
                    "openai_mode": openai_mode,
                },
                packet,
                summary_path=summary_json_path,
                packet_path=json_path,
            ),
            output_dir=pilot_dir,
        )
        pilot_results.append(
            {
                "pilot_id": pilot_id,
                "workflow_run_id": workflow_run_id,
                "reused_existing": not created,
                "inspection_packet_path": str(json_path),
                "inspection_markdown_path": str(md_path),
                **workflow_lab_paths,
            }
        )

    summary = {
        "status": "ok",
        "command": "logistics-weekly-agent-pilot.run",
        "pilot_key": pilot_key,
        "db_url": db_url,
        "openai_mode": openai_mode,
        "artifact_root": str(resolved_artifact_root),
        "output_root": str(resolved_output_root),
        "pilot_runs": pilot_results,
    }
    summary_json_path.write_text(json.dumps(summary, indent=2, sort_keys=True), encoding="utf-8")
    summary_md_path.write_text(_summary_to_markdown(summary), encoding="utf-8")
    summary["summary_json_path"] = str(summary_json_path)
    summary["summary_markdown_path"] = str(summary_md_path)
    return summary


def build_weekly_stage04_inspection_packet(
    connection: sqlite3.Connection,
    *,
    pilot_id: str,
    pilot_key: str,
    workflow_run_id: str,
    definition: WeeklyPilotDefinition,
    db_url: str,
    openai_mode: str,
    reused_existing: bool,
    stage04_result: dict[str, Any] | None,
) -> dict[str, Any]:
    workflow_run = show_workflow_run_command(connection, workflow_run_id)
    tasks = list_tasks_for_workflow_run_command(connection, workflow_run_id)
    approvals = list_approvals_for_workflow_run_command(connection, workflow_run_id)
    flags = list_flags_for_workflow_run_command(connection, workflow_run_id)
    artifacts = list_artifacts_for_workflow_run_command(connection, workflow_run_id)
    pointers = list_pointers_for_workflow_run_command(connection, workflow_run_id)
    sessions = list_execution_sessions_for_workflow_run_command(connection, workflow_run_id)

    tool_executions: list[dict[str, Any]] = []
    policy_decisions: list[dict[str, Any]] = []
    seen_policy_ids: set[str] = set()
    for session in sessions:
        session_tools = list_tool_executions_for_session(
            connection,
            str(session["execution_session_id"]),
        )
        tool_executions.extend(session_tools)
        for tool in session_tools:
            policy_decision = None
            if tool.get("policy_decision_id"):
                policy_decision = get_policy_decision(connection, str(tool["policy_decision_id"]))
            if policy_decision is None:
                policy_decision = get_policy_decision_for_tool_execution(
                    connection,
                    tool_execution_id=str(tool["tool_execution_id"]),
                )
            if policy_decision is None:
                continue
            policy_id = str(policy_decision["policy_decision_id"])
            if policy_id in seen_policy_ids:
                continue
            seen_policy_ids.add(policy_id)
            policy_decisions.append(policy_decision)

    timeline_events = list_events(connection, run_id=workflow_run_id, limit=1500)
    timeline_of_interest = [
        _compact_event(event)
        for event in timeline_events
        if str(event.get("event_type")) in EVENT_TYPES_OF_INTEREST
    ]

    linked_ids = {
        "task_run_ids": [str(item["task_run_id"]) for item in tasks],
        "human_task_ids": [str(item["human_task_id"]) for item in tasks],
        "artifact_version_ids": [str(item["artifact_version_id"]) for item in artifacts],
        "pointer_keys": [str(item["pointer_key"]) for item in pointers],
        "approval_ids": [str(item["approval_id"]) for item in approvals],
        "flag_ids": [str(item["flag_id"]) for item in flags],
        "execution_session_ids": [str(item["execution_session_id"]) for item in sessions],
        "tool_execution_ids": [str(item["tool_execution_id"]) for item in tool_executions],
        "policy_decision_ids": [str(item["policy_decision_id"]) for item in policy_decisions],
    }

    evidence_by_kind = _artifact_ids_by_kind(
        artifacts=artifacts,
        kinds=EXECUTION_SEMANTICS_EVIDENCE_KINDS | RUNTIME_TURN_EVIDENCE_KINDS | STAGE04_OUTPUT_ARTIFACT_KINDS,
    )

    canonical_refs = {
        "agent_execution": _agent_execution_refs(
            sessions=sessions,
            tool_executions=tool_executions,
            policy_decisions=policy_decisions,
            stage04_result=stage04_result,
        ),
        "execution_semantics_evidence_by_kind": {
            kind: evidence_by_kind.get(kind, [])
            for kind in sorted(EXECUTION_SEMANTICS_EVIDENCE_KINDS)
        },
        "runtime_turn_evidence_by_kind": {
            kind: evidence_by_kind.get(kind, [])
            for kind in sorted(RUNTIME_TURN_EVIDENCE_KINDS)
        },
        "stage04_output_artifacts_by_kind": {
            kind: evidence_by_kind.get(kind, [])
            for kind in sorted(STAGE04_OUTPUT_ARTIFACT_KINDS)
        },
        "canonical_query_commands": _canonical_query_commands(
            db_url=db_url,
            workflow_run_id=workflow_run_id,
            task_ids=linked_ids["human_task_ids"],
            session_ids=linked_ids["execution_session_ids"],
            tool_ids=linked_ids["tool_execution_ids"],
            policy_ids=linked_ids["policy_decision_ids"],
            artifact_ids=linked_ids["artifact_version_ids"],
        ),
    }

    routes = _inspection_routes(
        workflow_run_id=workflow_run_id,
        tasks=tasks,
        artifacts=artifacts,
    )
    stage04_analysis = _stage04_analysis(artifacts=artifacts)

    return {
        "packet_version": 1,
        "generated_at": utc_now_iso(),
        "pilot_id": pilot_id,
        "pilot_key": pilot_key,
        "description": definition.description,
        "stage_focus": definition.stage_focus,
        "openai_mode": openai_mode,
        "reused_existing": reused_existing,
        "workflow_run": workflow_run,
        "linked_ids": linked_ids,
        "canonical_evidence": canonical_refs,
        "tasks": tasks,
        "approvals": approvals,
        "flags": flags,
        "artifacts": artifacts,
        "pointers": pointers,
        "execution_runtime": {
            "execution_sessions": sessions,
            "tool_executions": tool_executions,
            "policy_decisions": policy_decisions,
        },
        "stage04_analysis": stage04_analysis,
        "timeline": {
            "event_count": len(timeline_events),
            "events_of_interest": timeline_of_interest,
        },
        "inspection": routes,
        "quality_signals": _quality_signals(
            tasks=tasks,
            approvals=approvals,
            flags=flags,
            pointers=pointers,
            artifacts=artifacts,
            sessions=sessions,
            tool_executions=tool_executions,
            policy_decisions=policy_decisions,
            timeline_of_interest=timeline_of_interest,
        ),
    }


def _run_weekly_stage04_agent_pilot(
    connection: sqlite3.Connection,
    *,
    definition: WeeklyPilotDefinition,
    workflow_run_id: str,
    pilot_key: str,
    openai_mode: str,
    storage_root: Path,
) -> dict[str, Any]:
    seeded_inputs = _seed_stage04_inputs(
        connection,
        workflow_run_id=workflow_run_id,
        pilot_key=pilot_key,
        pilot_id=definition.pilot_id,
    )

    stage04 = create_task_run_command(
        connection,
        {
            "task_run_id": _deterministic_id("tr", pilot_key, definition.pilot_id, "stage04-work-item"),
            "human_task_id": _deterministic_id("ht", pilot_key, definition.pilot_id, "stage04-work-item"),
            "workflow_run_id": workflow_run_id,
            "stage_id": "Stage04",
            "task_kind": "work_item",
            "activation_key": f"pilot:{pilot_key}:{definition.pilot_id}:stage04:work_item",
            "candidate_roles": ["schedule_planner"],
            "owner_role": "schedule_planner",
            "create_human_task": True,
            "idempotency_key": f"pilot:{pilot_key}:{definition.pilot_id}:tasks.create:stage04-work-item",
            "actor_id": "system:pilot-runner",
            "actor_type": "system",
        },
    )
    human_task_id = str(stage04["human_task"]["human_task_id"])

    _claim_if_open(
        connection,
        human_task_id=human_task_id,
        actor_id="human:schedule-planner-pilot",
        actor_type="human",
        actor_roles=["schedule_planner"],
        idempotency_key=f"pilot:{pilot_key}:{definition.pilot_id}:tasks.claim:stage04-work-item",
    )

    selected_runner = _mock_stage04_runner() if openai_mode == "mock" else None
    with ExitStack() as stack:
        stack.enter_context(_temporary_env("ONETRUTH_ARTIFACT_ROOT", str(storage_root)))
        if openai_mode == "real" and definition.real_openai_model:
            stack.enter_context(_temporary_env("ONETRUTH_OPENAI_MODEL", definition.real_openai_model))
        result = run_weekly_stage04_openai_agent(
            connection,
            {
                "human_task_id": human_task_id,
                "actor_id": "human:schedule-planner-pilot",
                "actor_type": "human",
                "actor_roles": ["schedule_planner"],
                "idempotency_key": f"pilot:{pilot_key}:{definition.pilot_id}:stage04-openai-agent",
            },
            runner=selected_runner,
        )

    return {
        "seeded_input_ids": {
            key: str(value["artifact_version_id"])
            for key, value in seeded_inputs.items()
        },
        "task_run_id": str(stage04["task_run"]["task_run_id"]),
        "human_task_id": human_task_id,
        "execution_session_id": str(result["execution_session"]["execution_session_id"]),
        "tool_execution_id": str(result["tool_execution"]["tool_execution_id"]),
        "policy_decision_id": str(result["policy_decision"]["policy_decision_id"]),
    }


def _seed_stage04_inputs(
    connection: sqlite3.Connection,
    *,
    workflow_run_id: str,
    pilot_key: str,
    pilot_id: str,
) -> dict[str, dict[str, Any]]:
    source_material = _stage04_source_material_for_pilot(pilot_id)
    route_slots = _create_stage04_input_artifact(
        connection,
        workflow_run_id=workflow_run_id,
        pilot_key=pilot_key,
        pilot_id=pilot_id,
        suffix="route-slot-requirements",
        artifact_kind="planning.route_slot_requirements.workbook",
        metadata_json=source_material["route_slot_requirements"],
    )
    driver_caps = _create_stage04_input_artifact(
        connection,
        workflow_run_id=workflow_run_id,
        pilot_key=pilot_key,
        pilot_id=pilot_id,
        suffix="driver-capabilities",
        artifact_kind="planning.driver_capabilities.workbook",
        metadata_json=source_material["driver_capabilities"],
    )
    availability = _create_stage04_input_artifact(
        connection,
        workflow_run_id=workflow_run_id,
        pilot_key=pilot_key,
        pilot_id=pilot_id,
        suffix="approved-availability",
        artifact_kind="planning.approved_availability.workbook",
        metadata_json=source_material["approved_availability"],
    )
    actual_hours = _create_stage04_input_artifact(
        connection,
        workflow_run_id=workflow_run_id,
        pilot_key=pilot_key,
        pilot_id=pilot_id,
        suffix="actual-hours",
        artifact_kind="planning.actual_hours_snapshot.workbook",
        metadata_json=source_material["actual_hours"],
    )
    return {
        "route_slot_requirements": route_slots,
        "driver_capabilities": driver_caps,
        "approved_availability": availability,
        "actual_hours": actual_hours,
    }


def _create_stage04_input_artifact(
    connection: sqlite3.Connection,
    *,
    workflow_run_id: str,
    pilot_key: str,
    pilot_id: str,
    suffix: str,
    artifact_kind: str,
    metadata_json: dict[str, Any],
) -> dict[str, Any]:
    metadata = {
        **metadata_json,
        "pilot_key": pilot_key,
        "pilot_id": pilot_id,
    }
    digest_payload = json.dumps(metadata, separators=(",", ":"), sort_keys=True)
    content_digest = f"sha256:{hashlib.sha256(digest_payload.encode('utf-8')).hexdigest()}"
    result = create_artifact_version_command(
        connection,
        {
            "artifact_version_id": _deterministic_id("av", pilot_key, pilot_id, suffix),
            "workflow_run_id": workflow_run_id,
            "artifact_kind": artifact_kind,
            "artifact_role": "official_input",
            "media_type": "application/json",
            "storage_uri": f"inmem://pilot/logistics-weekly-stage04/{pilot_key}/{pilot_id}/{suffix}.json",
            "content_digest": content_digest,
            "metadata_json": metadata,
            "idempotency_key": f"pilot:{pilot_key}:{pilot_id}:artifacts.create:{suffix}",
            "actor_id": "system:pilot-runner",
            "actor_type": "system",
        },
    )
    return result


def _stage04_source_material_for_pilot(pilot_id: str) -> dict[str, dict[str, Any]]:
    definition = PILOT_DEFINITIONS[pilot_id]
    if definition.source_material_loader == "realistic_manifest_enriched":
        return build_realistic_weekly_stage04_fixture_payloads()
    if definition.source_material_loader == "manifest_identity":
        if definition.source_material_path is None:
            raise ValueError(f"{pilot_id} must declare source_material_path")
        return build_identity_weekly_stage04_fixture_payloads(definition.source_material_path)
    return {
        "route_slot_requirements": _ROUTE_SLOT_REQUIREMENTS_METADATA,
        "driver_capabilities": _DRIVER_CAPABILITIES_METADATA,
        "approved_availability": _APPROVED_AVAILABILITY_METADATA,
        "actual_hours": _ACTUAL_HOURS_METADATA,
    }


def build_realistic_weekly_stage04_fixture_payloads() -> dict[str, dict[str, Any]]:
    source = _load_weekly_stage04_source_material(REALISTIC_WEEKLY_STAGE04_SOURCE_MATERIAL_PATH)
    route_slots, driver_capabilities, approved_availability, actual_hours = _load_weekly_stage04_source_artifacts(
        source,
        source_material_path=REALISTIC_WEEKLY_STAGE04_SOURCE_MATERIAL_PATH,
    )

    return {
        "route_slot_requirements": _enrich_realistic_route_slot_requirements(
            route_slots,
            planning_week_id=str(source.get("planning_week_id") or ""),
        ),
        "driver_capabilities": _enrich_realistic_driver_capabilities(
            driver_capabilities,
            planning_week_id=str(source.get("planning_week_id") or ""),
        ),
        "approved_availability": _enrich_realistic_approved_availability(
            approved_availability,
            planning_week_id=str(source.get("planning_week_id") or ""),
        ),
        "actual_hours": _enrich_realistic_actual_hours(
            actual_hours,
            driver_capabilities=driver_capabilities,
            planning_week_id=str(source.get("planning_week_id") or ""),
        ),
    }


def build_actual_ops_weekly_stage04_fixture_payloads() -> dict[str, dict[str, Any]]:
    return build_identity_weekly_stage04_fixture_payloads(
        ACTUAL_OPS_WEEKLY_STAGE04_SOURCE_MATERIAL_PATH
    )


def build_identity_weekly_stage04_fixture_payloads(
    source_material_path: Path,
) -> dict[str, dict[str, Any]]:
    source = _load_weekly_stage04_source_material(source_material_path)
    route_slots, driver_capabilities, approved_availability, actual_hours = _load_weekly_stage04_source_artifacts(
        source,
        source_material_path=source_material_path,
    )
    return {
        "route_slot_requirements": route_slots,
        "driver_capabilities": driver_capabilities,
        "approved_availability": approved_availability,
        "actual_hours": actual_hours,
    }


def _load_weekly_stage04_source_artifacts(
    source: dict[str, Any],
    *,
    source_material_path: Path,
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any], dict[str, Any]]:
    source_artifacts = source.get("source_artifacts")
    if not isinstance(source_artifacts, dict):
        raise ValueError("weekly Stage04 source material must declare source_artifacts")

    route_slots = _load_weekly_stage04_source_artifact(
        source_artifacts["route_slot_requirements"],
        source_material_path=source_material_path,
    )
    driver_capabilities = _load_weekly_stage04_source_artifact(
        source_artifacts["driver_capabilities"],
        source_material_path=source_material_path,
    )
    approved_availability = _load_weekly_stage04_source_artifact(
        source_artifacts["approved_availability"],
        source_material_path=source_material_path,
    )
    actual_hours = _load_weekly_stage04_source_artifact(
        source_artifacts["actual_hours"],
        source_material_path=source_material_path,
    )
    return route_slots, driver_capabilities, approved_availability, actual_hours


def _load_weekly_stage04_source_artifact(path_text: Any, *, source_material_path: Path) -> dict[str, Any]:
    path = _resolve_source_material_artifact_path(path_text, source_material_path=source_material_path)
    loaded = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(loaded, dict):
        raise ValueError(f"weekly Stage04 example must decode to an object: {path}")
    return copy.deepcopy(loaded)


def _enrich_realistic_route_slot_requirements(
    example: dict[str, Any],
    *,
    planning_week_id: str,
) -> dict[str, Any]:
    columns = [str(column) for column in example.get("columns") or []]
    extra_columns = [
        column
        for column in ("route_family", "preferred_shift_band", "projected_minutes")
        if column not in columns
    ]
    rows = []
    for row in _rows_to_dicts(columns, list(example.get("rows") or [])):
        enriched = dict(row)
        enriched["route_family"] = str(
            row.get("route_family") or _route_family_token(str(row.get("route_slot_class") or ""))
        ).strip()
        enriched["preferred_shift_band"] = str(
            row.get("preferred_shift_band")
            or row.get("slot_band")
            or _preferred_shift_band_token(str(row.get("route_slot_class") or ""))
        ).strip()
        enriched["projected_minutes"] = _coerce_int(
            row.get("projected_minutes"),
            default=int(round(_coerce_float(row.get("estimated_hours"), default=0.0) * 60.0)),
        )
        rows.append([enriched.get(column, "") for column in columns + extra_columns])

    daily_demand_columns = [str(column) for column in example.get("daily_demand_columns") or []]
    daily_demand_extra_columns = (
        ["standard_slot_count"] if "standard_slot_count" not in daily_demand_columns else []
    )
    daily_demand_rows = []
    for row in _rows_to_dicts(daily_demand_columns, list(example.get("daily_demand_rows") or [])):
        enriched = dict(row)
        enriched["standard_slot_count"] = _coerce_int(
            row.get("standard_slot_count"),
            default=(
                _coerce_int(row.get("standard_early_slot_count"), default=0)
                + _coerce_int(row.get("standard_late_slot_count"), default=0)
            ),
        )
        daily_demand_rows.append(
            [enriched.get(column, "") for column in daily_demand_columns + daily_demand_extra_columns]
        )

    notes = [str(item) for item in example.get("planner_notes") or [] if str(item).strip()]
    notes.append(
        "Deterministic realistic adapter adds route_family, preferred_shift_band, and projected_minutes helper fields for Stage04 bridge/runtime use."
    )

    example["planning_week_id"] = planning_week_id
    example["columns"] = columns + extra_columns
    example["rows"] = rows
    example["daily_demand_columns"] = daily_demand_columns + daily_demand_extra_columns
    example["daily_demand_rows"] = daily_demand_rows
    example["planner_notes"] = list(dict.fromkeys(notes))
    return example


def _enrich_realistic_driver_capabilities(
    example: dict[str, Any],
    *,
    planning_week_id: str,
) -> dict[str, Any]:
    example["planning_week_id"] = planning_week_id
    example["planner_notes"] = list(
        dict.fromkeys(str(item) for item in example.get("planner_notes") or [] if str(item).strip())
    )
    return example


def _enrich_realistic_approved_availability(
    example: dict[str, Any],
    *,
    planning_week_id: str,
) -> dict[str, Any]:
    columns = [str(column) for column in example.get("columns") or []]
    extra_columns = [
        column
        for column in ("previous_week_state", "normalized_availability_state")
        if column not in columns
    ]
    rows = []
    for row in _rows_to_dicts(columns, list(example.get("rows") or [])):
        enriched = dict(row)
        enriched["previous_week_state"] = _normalized_previous_week_state_label(
            row.get("previous_week_state") or row.get("previous_week_same_day_state")
        )
        enriched["normalized_availability_state"] = _normalized_availability_state_label(
            row.get("availability_state")
        )
        rows.append([enriched.get(column, "") for column in columns + extra_columns])

    notes = [str(item) for item in example.get("planner_notes") or [] if str(item).strip()]
    notes.append(
        "Deterministic realistic adapter adds previous_week_state and normalized_availability_state helper fields while preserving one row per driver per day."
    )

    example["planning_week_id"] = planning_week_id
    example["columns"] = columns + extra_columns
    example["rows"] = rows
    example["planner_notes"] = list(dict.fromkeys(notes))
    return example


def _enrich_realistic_actual_hours(
    example: dict[str, Any],
    *,
    driver_capabilities: dict[str, Any],
    planning_week_id: str,
) -> dict[str, Any]:
    columns = [str(column) for column in example.get("columns") or []]
    extra_columns = [
        column
        for column in (
            "normalized_historical_state",
            "rolling_7_total_minutes",
            "rolling_7_limit_minutes",
            "rolling_7_remaining_minutes",
        )
        if column not in columns
    ]
    limits_by_driver = _rolling_7_limits_by_driver(driver_capabilities)
    total_minutes_by_driver = _actual_minutes_by_driver(example)

    rows = []
    for row in _rows_to_dicts(columns, list(example.get("rows") or [])):
        enriched = dict(row)
        historical_state = _normalized_previous_week_state_label(row.get("historical_state"))
        total_minutes = total_minutes_by_driver.get(str(row.get("driver_id") or "").strip(), 0)
        limit_minutes = limits_by_driver.get(
            str(row.get("driver_id") or "").strip(),
            max(total_minutes, 2400),
        )
        enriched["historical_state"] = historical_state
        enriched["normalized_historical_state"] = _normalized_previous_week_state_category(
            raw_state=historical_state,
            actual_minutes=_coerce_int(row.get("actual_minutes"), default=0),
            call_in_sick_flag=_coerce_bool(row.get("call_in_sick_flag")),
            cancellation_flag=_coerce_bool(row.get("cancellation_flag")),
            non_working_day_flag=_coerce_bool(row.get("non_working_day_flag")),
        )
        enriched["rolling_7_total_minutes"] = total_minutes
        enriched["rolling_7_limit_minutes"] = limit_minutes
        enriched["rolling_7_remaining_minutes"] = max(limit_minutes - total_minutes, 0)
        rows.append([enriched.get(column, "") for column in columns + extra_columns])

    notes = [str(item) for item in example.get("planner_notes") or [] if str(item).strip()]
    notes.append(
        "Deterministic realistic adapter normalizes BLANK history rows to NA and adds rolling_7_* helper fields for Stage04 bridge/runtime use."
    )

    example["planning_week_id"] = planning_week_id
    example["columns"] = columns + extra_columns
    example["rows"] = rows
    example["planner_notes"] = list(dict.fromkeys(notes))
    return example


def _load_weekly_stage04_source_material(path: Path) -> dict[str, Any]:
    loaded = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(loaded, dict):
        raise ValueError(f"weekly Stage04 source material must decode to an object: {path}")
    return loaded


def _resolve_source_material_artifact_path(path_text: Any, *, source_material_path: Path) -> Path:
    relative_to_manifest = (source_material_path.parent / str(path_text)).resolve()
    if relative_to_manifest.exists():
        return relative_to_manifest
    return (REPO_ROOT / str(path_text)).resolve()


def _rolling_7_limits_by_driver(driver_capabilities: dict[str, Any]) -> dict[str, int]:
    columns = [str(column) for column in driver_capabilities.get("columns") or []]
    limits: dict[str, int] = {}
    for row in _rows_to_dicts(columns, list(driver_capabilities.get("rows") or [])):
        driver_id = str(row.get("driver_id") or "").strip()
        if not driver_id:
            continue
        restrictions = _csv_tokens(row.get("approved_restrictions"))
        limits[driver_id] = _restriction_prefixed_int(
            restrictions,
            prefix="max_minutes_rolling7=",
        ) or 2400
    return limits


def _actual_minutes_by_driver(actual_hours: dict[str, Any]) -> dict[str, int]:
    columns = [str(column) for column in actual_hours.get("columns") or []]
    totals: dict[str, int] = {}
    for row in _rows_to_dicts(columns, list(actual_hours.get("rows") or [])):
        driver_id = str(row.get("driver_id") or "").strip()
        if not driver_id:
            continue
        totals[driver_id] = totals.get(driver_id, 0) + _coerce_int(
            row.get("actual_minutes"),
            default=0,
        )
    return totals


def _normalized_previous_week_state_label(value: Any) -> str:
    token = str(value or "").strip().upper()
    if not token or token == "BLANK":
        return "NA"
    return token


def _normalized_availability_state_label(value: Any) -> str:
    token = str(value or "").strip().upper()
    if token in {"PREFERRED", "AVAILABLE", "AVOID_IF_POSSIBLE"}:
        return "available"
    if token == "ON_CALL_ONLY":
        return "emergency_only"
    if token == "CANNOT":
        return "approved_unavailable"
    return token.lower() if token else "unknown"


def _normalized_previous_week_state_category(
    *,
    raw_state: str,
    actual_minutes: int,
    call_in_sick_flag: bool,
    cancellation_flag: bool,
    non_working_day_flag: bool,
) -> str:
    token = _normalized_previous_week_state_label(raw_state)
    if token == "WORKED":
        return "worked"
    if token in {"ON_CALL", "DISPATCH"}:
        return "worked" if actual_minutes > 0 else "available_not_assigned"
    if token in {"SICK_CALL", "CANCELLED"} or call_in_sick_flag or cancellation_flag:
        return "blocked_previous_week"
    if token == "NA" or non_working_day_flag:
        return "pattern_off"
    if actual_minutes > 0:
        return "worked"
    return "available_not_assigned"


def _route_family_token(route_slot_class: str) -> str:
    token = str(route_slot_class or "").strip()
    if "_" in token:
        return token.split("_", maxsplit=1)[0]
    return token


def _preferred_shift_band_token(route_slot_class: str) -> str:
    token = str(route_slot_class or "").strip().lower()
    if token.endswith("_early"):
        return "early"
    if token.endswith("_late"):
        return "late"
    if "rescue" in token:
        return "rescue"
    if "overflow" in token:
        return "overflow"
    return ""


def _rows_to_dicts(columns: list[str], rows: list[Any]) -> list[dict[str, Any]]:
    normalized_columns = [str(column).strip() for column in columns]
    values: list[dict[str, Any]] = []
    for row in rows:
        if isinstance(row, dict):
            values.append({str(key).strip(): value for key, value in row.items()})
            continue
        if isinstance(row, (list, tuple)):
            values.append(
                {
                    normalized_columns[index]: value
                    for index, value in enumerate(row)
                    if index < len(normalized_columns)
                }
            )
    return values


def _csv_tokens(value: Any) -> tuple[str, ...]:
    if value is None:
        return ()
    if isinstance(value, list):
        return tuple(str(item).strip() for item in value if str(item).strip())
    return tuple(part.strip() for part in str(value).split(",") if part.strip())


def _coerce_int(value: Any, *, default: int) -> int:
    if value is None:
        return int(default)
    try:
        return int(value)
    except (TypeError, ValueError):
        return int(default)


def _coerce_float(value: Any, *, default: float) -> float:
    if value is None:
        return float(default)
    try:
        return float(value)
    except (TypeError, ValueError):
        return float(default)


def _coerce_bool(value: Any) -> bool:
    return str(value or "").strip().lower() in {"1", "true", "yes", "y"}


def _restriction_prefixed_int(restrictions: tuple[str, ...], *, prefix: str) -> int | None:
    for restriction in restrictions:
        if not restriction.startswith(prefix):
            continue
        try:
            return int(restriction.removeprefix(prefix))
        except ValueError:
            return None
    return None


def _weekday_token(current: date) -> str:
    return current.strftime("%a")


def _mock_stage04_runner() -> OpenAIResponsesFunctionCallingRunner:
    calls = {"count": 0}

    def transport(payload, _timeout):
        calls["count"] += 1
        if calls["count"] == 1:
            return (
                200,
                {
                    "id": "resp_pilot_1",
                    "model": "gpt-4.1-mini",
                    "usage": {"input_tokens": 28, "output_tokens": 12},
                    "output": [
                        {
                            "type": "function_call",
                            "call_id": "call_ctx",
                            "name": "get_stage04_context",
                            "arguments": "{}",
                        },
                        {
                            "type": "function_call",
                            "call_id": "call_preview",
                            "name": "preview_stage04_next_iteration",
                            "arguments": "{}",
                        },
                    ],
                },
                "req_pilot_1",
            )
        if payload.get("previous_response_id") != f"resp_pilot_{calls['count'] - 1}":
            raise AssertionError("expected previous_response_id from prior pilot turn")
        outputs = [
            json.loads(str(item.get("output") or "{}"))
            for item in payload.get("input", [])
            if isinstance(item, dict) and str(item.get("type") or "") == "function_call_output"
        ]
        if any(isinstance(item, dict) and item.get("stage04_build_result") for item in outputs):
            return (
                200,
                {
                    "id": f"resp_pilot_{calls['count']}",
                    "model": "gpt-4.1-mini",
                    "usage": {"input_tokens": 13, "output_tokens": 8},
                    "output_text": (
                        '{"summary":"pilot run complete","selected_candidate_count":2,'
                        '"recommended_action":"forward_to_stage05_manager_review","warnings":[]}'
                    ),
                },
                f"req_pilot_{calls['count']}",
            )
        if any(
            isinstance(item, dict)
            and item.get("planner_complete") is True
            and item.get("iteration_result")
            for item in outputs
        ):
            latest_iteration = max(
                int((item.get("iteration_result") or {}).get("iteration_index") or 1)
                for item in outputs
                if isinstance(item, dict) and item.get("iteration_result")
            )
            return (
                200,
                {
                    "id": f"resp_pilot_{calls['count']}",
                    "model": "gpt-4.1-mini",
                    "usage": {"input_tokens": 21, "output_tokens": 10},
                    "output": [
                        {
                            "type": "function_call",
                            "call_id": "call_validation",
                            "name": "get_stage04_validation_summary",
                            "arguments": "{}",
                        },
                        {
                            "type": "function_call",
                            "call_id": "call_iteration",
                            "name": "get_stage04_iteration_analysis",
                            "arguments": json.dumps({"iteration_index": latest_iteration}),
                        },
                        {
                            "type": "function_call",
                            "call_id": "call_finalize",
                            "name": "finalize_weekly_stage04_draft_outputs",
                            "arguments": "{}",
                        },
                    ],
                },
                f"req_pilot_{calls['count']}",
            )
        return (
            200,
            {
                "id": f"resp_pilot_{calls['count']}",
                "model": "gpt-4.1-mini",
                "usage": {"input_tokens": 17, "output_tokens": 7},
                "output": [
                    {
                        "type": "function_call",
                        "call_id": "call_apply",
                        "name": "apply_stage04_next_iteration",
                        "arguments": "{}",
                    }
                ],
            },
            f"req_pilot_{calls['count']}",
        )

    return OpenAIResponsesFunctionCallingRunner(
        api_key="sk-test",
        model="gpt-4.1-mini",
        base_url="https://api.openai.test/v1",
        timeout_seconds=5.0,
        max_retries=0,
        transport=transport,
    )


def _ensure_workflow_run(
    connection: sqlite3.Connection,
    *,
    definition: WeeklyPilotDefinition,
    workflow_run_id: str,
    pilot_key: str,
) -> bool:
    try:
        show_workflow_run_command(connection, workflow_run_id)
        return False
    except CommandError as exc:
        if exc.code != "workflow_run_not_found":
            raise

    payload = {
        "workflow_run_id": workflow_run_id,
        "workflow_id": WORKFLOW_ID,
        "workflow_version": WORKFLOW_VERSION,
        "tenant_id": TENANT_ID,
        "domain_id": DOMAIN_ID,
        "partition_key": definition.partition_key,
        "logical_date": definition.logical_date,
        "activation_key": f"pilot:{pilot_key}:{definition.pilot_id}",
        "idempotency_key": f"pilot:{pilot_key}:{definition.pilot_id}:runs.create",
        "actor_id": "system:pilot-runner",
        "actor_type": "system",
    }
    try:
        create_workflow_run_command(connection, payload)
    except DuplicateIdempotencyKeyError:
        show_workflow_run_command(connection, workflow_run_id)
    return True


def _claim_if_open(
    connection: sqlite3.Connection,
    *,
    human_task_id: str,
    actor_id: str,
    actor_type: str,
    actor_roles: list[str],
    idempotency_key: str,
) -> dict[str, Any]:
    current = show_human_task_command(connection, human_task_id)
    state = str(current["state"])
    if state == "OPEN":
        return claim_human_task_command(
            connection,
            {
                "human_task_id": human_task_id,
                "actor_id": actor_id,
                "actor_type": actor_type,
                "actor_roles": actor_roles,
                "lease_seconds": 300,
                "idempotency_key": idempotency_key,
            },
        )
    if state == "CLAIMED":
        assignee = str(current.get("assignee_actor_id") or "")
        if assignee and assignee != actor_id:
            raise CommandError(
                code="pilot_claim_conflict",
                message="human task already claimed by a different actor",
                details={
                    "human_task_id": human_task_id,
                    "assignee_actor_id": assignee,
                    "actor_id": actor_id,
                },
            )
    return current


def _agent_execution_refs(
    *,
    sessions: list[dict[str, Any]],
    tool_executions: list[dict[str, Any]],
    policy_decisions: list[dict[str, Any]],
    stage04_result: dict[str, Any] | None,
) -> dict[str, Any]:
    refs = {
        "execution_session_id": str(sessions[0]["execution_session_id"]) if sessions else "",
        "tool_execution_id": str(tool_executions[0]["tool_execution_id"]) if tool_executions else "",
        "policy_decision_id": str(policy_decisions[0]["policy_decision_id"]) if policy_decisions else "",
    }
    if stage04_result is not None:
        refs["human_task_id"] = str(stage04_result.get("human_task_id") or "")
        refs["task_run_id"] = str(stage04_result.get("task_run_id") or "")
    return refs


def _canonical_query_commands(
    *,
    db_url: str,
    workflow_run_id: str,
    task_ids: list[str],
    session_ids: list[str],
    tool_ids: list[str],
    policy_ids: list[str],
    artifact_ids: list[str],
) -> list[str]:
    commands = [
        f"python3 -m onetruth.cli --db-url {db_url} runs show --workflow-run-id {workflow_run_id} --json",
        f"python3 -m onetruth.cli --db-url {db_url} tasks list --workflow-run-id {workflow_run_id} --json",
        f"python3 -m onetruth.cli --db-url {db_url} artifacts list --workflow-run-id {workflow_run_id} --json",
        f"python3 -m onetruth.cli --db-url {db_url} pointers list --workflow-run-id {workflow_run_id} --json",
        f"python3 -m onetruth.cli --db-url {db_url} events list --run-id {workflow_run_id} --limit 1000 --json",
        f"python3 -m onetruth.cli --db-url {db_url} execution-sessions list --workflow-run-id {workflow_run_id} --json",
    ]
    commands.extend(
        f"python3 -m onetruth.cli --db-url {db_url} tasks show --human-task-id {task_id} --json"
        for task_id in task_ids
    )
    commands.extend(
        f"python3 -m onetruth.cli --db-url {db_url} execution-sessions show --execution-session-id {session_id} --json"
        for session_id in session_ids
    )
    commands.extend(
        f"python3 -m onetruth.cli --db-url {db_url} tool-executions show --tool-execution-id {tool_id} --json"
        for tool_id in tool_ids
    )
    commands.extend(
        f"python3 -m onetruth.cli --db-url {db_url} policy-decisions show --policy-decision-id {policy_id} --json"
        for policy_id in policy_ids
    )
    commands.extend(
        f"python3 -m onetruth.cli --db-url {db_url} artifacts show --artifact-version-id {artifact_id} --json"
        for artifact_id in artifact_ids
    )
    return _dedupe_preserving_order(commands)


def _artifact_ids_by_kind(
    *,
    artifacts: list[dict[str, Any]],
    kinds: set[str],
) -> dict[str, list[str]]:
    rows: dict[str, list[str]] = {kind: [] for kind in kinds}
    for artifact in artifacts:
        kind = str(artifact.get("artifact_kind") or "")
        if kind not in rows:
            continue
        rows[kind].append(str(artifact.get("artifact_version_id") or ""))
    return rows


def _artifact_metadata_by_kind(
    *,
    artifacts: list[dict[str, Any]],
    artifact_kind: str,
) -> dict[str, Any]:
    for artifact in artifacts:
        if str(artifact.get("artifact_kind") or "") != artifact_kind:
            continue
        metadata = artifact.get("metadata_json")
        if isinstance(metadata, dict):
            return dict(metadata)
        if isinstance(metadata, str):
            try:
                parsed = json.loads(metadata)
            except json.JSONDecodeError:
                return {}
            return dict(parsed) if isinstance(parsed, dict) else {}
    return {}


def _runtime_turn_analysis(artifacts: list[dict[str, Any]]) -> list[dict[str, Any]]:
    turn_rows = [
        artifact
        for artifact in artifacts
        if str(artifact.get("artifact_kind") or "") == "runtime.tool_result.json"
    ]
    parsed_turns: list[dict[str, Any]] = []
    for artifact in turn_rows:
        parsed_uri = urlparse(str(artifact.get("storage_uri") or ""))
        if not parsed_uri.path:
            continue
        payload_path = Path(parsed_uri.path)
        if not payload_path.exists():
            continue
        try:
            payload = json.loads(payload_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        metadata = artifact.get("metadata_json") if isinstance(artifact.get("metadata_json"), dict) else {}
        parsed_turns.append(
            {
                "turn_index": int(payload.get("turn_index") or metadata.get("turn_index") or 0),
                "progress_made": bool(payload.get("progress_made")),
                "no_progress_streak": int(payload.get("no_progress_streak") or 0),
                "planner_state": payload.get("planner_state") or {},
                "function_names": [
                    str(item.get("name") or "")
                    for item in payload.get("function_calls") or []
                    if isinstance(item, dict)
                ],
            }
        )
    return sorted(parsed_turns, key=lambda item: int(item["turn_index"]))


def _stage04_analysis(
    *,
    artifacts: list[dict[str, Any]],
) -> dict[str, Any]:
    candidate_delta = _artifact_metadata_by_kind(
        artifacts=artifacts,
        artifact_kind="planning.candidate_schedule_delta.workbook",
    )
    validation_summary = _artifact_metadata_by_kind(
        artifacts=artifacts,
        artifact_kind="planning.validation_summary.doc",
    )
    draft_doc = _artifact_metadata_by_kind(
        artifacts=artifacts,
        artifact_kind="planning.draft_weekly_schedule.doc",
    )
    if not candidate_delta or not validation_summary:
        return {}

    summary = validation_summary.get("summary") if isinstance(validation_summary, dict) else {}
    summary = dict(summary) if isinstance(summary, dict) else {}
    iteration_rows = _rows_to_dicts(
        list(candidate_delta.get("columns") or []),
        list(candidate_delta.get("rows") or []),
    )
    iteration_summaries = [
        dict(item)
        for item in candidate_delta.get("iteration_deltas") or []
        if isinstance(item, dict)
    ]
    repair_moves = [
        dict(item)
        for item in candidate_delta.get("repair_moves") or []
        if isinstance(item, dict)
    ]
    tradeoffs = [str(item) for item in summary.get("tradeoffs") or []]
    warnings = [str(item) for item in summary.get("warnings") or []]
    coverage_summary = dict(candidate_delta.get("coverage_summary") or {})
    coverage_summary.update(summary.get("coverage_summary") or {})
    contract_change_summary = {
        "new_agreement_required_count": int(summary.get("new_agreement_required_count") or 0),
        "new_agreement_driver_day_count": int(
            summary.get("new_agreement_driver_day_count") or 0
        ),
        "new_agreement_driver_ids": list(summary.get("new_agreement_driver_ids") or []),
        "new_agreement_by_service_date": dict(
            summary.get("new_agreement_by_service_date") or {}
        ),
        "new_agreement_by_driver_id": dict(
            summary.get("new_agreement_by_driver_id") or {}
        ),
        "new_agreement_transition_counts": dict(
            summary.get("new_agreement_transition_counts") or {}
        ),
        "new_agreement_rows": list(summary.get("new_agreement_rows") or []),
    }
    if not tradeoffs:
        uncovered_count = int(coverage_summary.get("uncovered_route_slots") or 0)
        pending_count = int(coverage_summary.get("pending_route_slots") or 0)
        previous_week_stability = float(
            (summary.get("soft_score_totals") or {}).get("previous_week_stability") or 0.0
        )
        if uncovered_count > 0:
            tradeoffs.append(
                f"{uncovered_count} route slots remain uncovered because deterministic hard rules and bounded repair preserved compliance over artificial fill-ins."
            )
        if pending_count > 0:
            tradeoffs.append(
                f"{pending_count} route slots were still pending before explicit finalize, so the packet highlights iteration progress instead of pretending the weekly draft was complete early."
            )
        if previous_week_stability > 0.0 and (uncovered_count > 0 or pending_count > 0):
            tradeoffs.append(
                "Previous-week stability contributed positively, but coverage and policy constraints still forced visible weekly tradeoffs."
            )

    iterations: list[dict[str, Any]] = []
    for item in iteration_summaries:
        iteration_index = int(item.get("iteration_index") or 0)
        route_allocations = [
            row
            for row in iteration_rows
            if int(row.get("iteration_index") or 0) == iteration_index
        ]
        iteration_repairs = [
            move
            for move in repair_moves
            if int(move.get("iteration_index") or 0) == iteration_index
        ]
        iterations.append(
            {
                "iteration_index": iteration_index,
                "phase": str(item.get("phase") or "baseline"),
                "pressure_group_id": str(item.get("pressure_group_id") or ""),
                "pressure_service_date": str(item.get("pressure_service_date") or ""),
                "pressure_station_code": str(item.get("pressure_station_code") or ""),
                "pressure_service_area": str(item.get("pressure_service_area") or ""),
                "batch_size": int(item.get("batch_size") or 0),
                "assigned_route_slot_ids": list(item.get("assigned_route_slot_ids") or []),
                "uncovered_route_slot_ids": list(item.get("uncovered_route_slot_ids") or []),
                "moved_route_slot_ids": list(item.get("moved_route_slot_ids") or []),
                "repair_move_count": int(item.get("repair_move_count") or 0),
                "candidate_evaluation_count": int(item.get("candidate_evaluation_count") or 0),
                "soft_objective_delta": float(item.get("soft_objective_delta") or 0.0),
                "stability_delta": float(item.get("stability_delta") or 0.0),
                "target_shift_gap_delta": float(item.get("target_shift_gap_delta") or 0.0),
                "preference_fit_delta": float(item.get("preference_fit_delta") or 0.0),
                "accepted_move_reasons": list(item.get("accepted_move_reasons") or []),
                "rejected_move_reasons": list(item.get("rejected_move_reasons") or []),
                "route_allocations": route_allocations,
                "repair_moves": iteration_repairs,
                "tradeoffs": [
                    tradeoff for tradeoff in tradeoffs if f"iteration {iteration_index}" in tradeoff
                ],
            }
        )

    return {
        "coverage_summary": coverage_summary,
        "phase_counts": dict(coverage_summary.get("phase_counts") or {}),
        "soft_score_totals": summary.get("soft_score_totals") or {},
        "contract_change_summary": contract_change_summary,
        "reserve_summary": dict(summary.get("reserve_summary") or {}),
        "excess_capacity_summary": dict(summary.get("excess_capacity_summary") or {}),
        "tradeoffs": tradeoffs,
        "warnings": warnings,
        "draft_summary": (
            dict(draft_doc.get("summary"))
            if isinstance(draft_doc, dict) and isinstance(draft_doc.get("summary"), dict)
            else {}
        ),
        "iterations": iterations,
        "runtime_turns": _runtime_turn_analysis(artifacts),
    }


def _quality_signals(
    *,
    tasks: list[dict[str, Any]],
    approvals: list[dict[str, Any]],
    flags: list[dict[str, Any]],
    pointers: list[dict[str, Any]],
    artifacts: list[dict[str, Any]],
    sessions: list[dict[str, Any]],
    tool_executions: list[dict[str, Any]],
    policy_decisions: list[dict[str, Any]],
    timeline_of_interest: list[dict[str, Any]],
) -> dict[str, Any]:
    artifact_kinds = {str(item.get("artifact_kind") or "") for item in artifacts}
    timeline_types = {str(item.get("event_type") or "") for item in timeline_of_interest}
    return {
        "task_count": len(tasks),
        "approval_count": len(approvals),
        "flag_count": len(flags),
        "pointer_count": len(pointers),
        "artifact_count": len(artifacts),
        "execution_session_count": len(sessions),
        "tool_execution_count": len(tool_executions),
        "policy_decision_count": len(policy_decisions),
        "timeline_events_of_interest_count": len(timeline_of_interest),
        "execution_session_succeeded": bool(sessions)
        and all(str(item.get("state") or "") == "SUCCEEDED" for item in sessions),
        "tool_execution_completed": bool(tool_executions)
        and all(str(item.get("state") or "") == "COMPLETED" for item in tool_executions),
        "policy_allow_recorded": bool(policy_decisions)
        and all(str(item.get("decision") or "") == "allow" for item in policy_decisions),
        "execution_semantics_evidence_present": EXECUTION_SEMANTICS_EVIDENCE_KINDS.issubset(artifact_kinds),
        "runtime_turn_evidence_present": RUNTIME_TURN_EVIDENCE_KINDS.issubset(artifact_kinds),
        "stage04_output_artifacts_present": STAGE04_OUTPUT_ARTIFACT_KINDS.issubset(artifact_kinds),
        "no_pointer_promotions": len(pointers) == 0,
        "timeline_has_execution_lifecycle": {
            "execution.session.created",
            "tool.execution.requested",
            "tool.execution.approved",
            "tool.execution.completed",
            "execution.session.state_changed",
        }.issubset(timeline_types),
    }


def _inspection_routes(
    *,
    workflow_run_id: str,
    tasks: list[dict[str, Any]],
    artifacts: list[dict[str, Any]],
) -> dict[str, Any]:
    ui_routes = [
        "/demo/logistics",
        f"/runs/{workflow_run_id}",
        f"/timeline?workflow_run_id={workflow_run_id}",
        f"/board?workflow_run_id={workflow_run_id}",
    ]
    api_routes = [
        f"/api/v1/workflow-runs/{workflow_run_id}",
        f"/api/v1/workflow-runs/{workflow_run_id}/workspace",
        f"/api/v1/human-tasks?workflow_run_id={workflow_run_id}",
        f"/api/v1/artifacts?workflow_run_id={workflow_run_id}",
        f"/api/v1/timeline-events?workflow_run_id={workflow_run_id}",
        f"/api/v1/pointers?workflow_run_id={workflow_run_id}",
    ]
    api_routes.extend(
        f"/api/v1/human-tasks/{task['human_task_id']}"
        for task in tasks
    )
    api_routes.extend(
        f"/api/v1/artifacts/{artifact['artifact_version_id']}"
        for artifact in artifacts
    )
    return {
        "ui_routes": _dedupe_preserving_order(ui_routes),
        "api_routes": _dedupe_preserving_order(api_routes),
    }


def _compact_event(event: dict[str, Any]) -> dict[str, Any]:
    return {
        "sequence_no": event.get("sequence_no"),
        "event_id": event.get("event_id"),
        "event_type": event.get("event_type"),
        "occurred_at": event.get("occurred_at"),
        "links": event.get("links"),
        "payload": event.get("payload"),
    }


def _packet_to_markdown(packet: dict[str, Any]) -> str:
    workflow_run = packet["workflow_run"]
    linked = packet["linked_ids"]
    stage04_analysis = packet.get("stage04_analysis") or {}
    lines = [
        f"# Logistics Weekly Stage04 Inspection Packet: {packet['pilot_id']}",
        "",
        f"- Pilot key: `{packet['pilot_key']}`",
        f"- OpenAI mode: `{packet['openai_mode']}`",
        f"- Workflow run: `{workflow_run['workflow_run_id']}`",
        f"- Reused existing run: `{packet['reused_existing']}`",
        "",
        "## Canonical object references",
        f"- Human tasks: {len(linked['human_task_ids'])}",
        f"- Task runs: {len(linked['task_run_ids'])}",
        f"- Artifacts: {len(linked['artifact_version_ids'])}",
        f"- Execution sessions: {len(linked['execution_session_ids'])}",
        f"- Tool executions: {len(linked['tool_execution_ids'])}",
        f"- Policy decisions: {len(linked['policy_decision_ids'])}",
        "",
        "## Canonical evidence coverage",
    ]
    for kind, ids in packet["canonical_evidence"]["execution_semantics_evidence_by_kind"].items():
        lines.append(f"- `{kind}`: {len(ids)}")
    for kind, ids in packet["canonical_evidence"]["runtime_turn_evidence_by_kind"].items():
        lines.append(f"- `{kind}`: {len(ids)}")
    for kind, ids in packet["canonical_evidence"]["stage04_output_artifacts_by_kind"].items():
        lines.append(f"- `{kind}`: {len(ids)}")
    lines.extend(
        [
            "",
            "## Stage04 analysis",
        ]
    )
    if stage04_analysis:
        coverage_summary = stage04_analysis.get("coverage_summary") or {}
        contract_change_summary = stage04_analysis.get("contract_change_summary") or {}
        reserve_summary = stage04_analysis.get("reserve_summary") or {}
        excess_capacity_summary = stage04_analysis.get("excess_capacity_summary") or {}
        lines.extend(
            [
                f"- Iterations: {len(stage04_analysis.get('iterations') or [])}",
                f"- Assigned route slots: {coverage_summary.get('assigned_route_slots', 0)}",
                f"- Uncovered route slots: {coverage_summary.get('uncovered_route_slots', 0)}",
                f"- Pending route slots: {coverage_summary.get('pending_route_slots', 0)}",
                (
                    "- Selected excess-capacity baseline shift rows: "
                    f"{excess_capacity_summary.get('selected_excess_capacity_total', 0)}"
                ),
                (
                    "- Selected On-Call buffer rows: "
                    f"{reserve_summary.get('selected_on_call_total', 0)}"
                ),
                (
                    "- New agreement required rows: "
                    f"{contract_change_summary.get('new_agreement_required_count', 0)}"
                ),
                (
                    "- New agreement driver-days: "
                    f"{contract_change_summary.get('new_agreement_driver_day_count', 0)}"
                ),
            ]
        )
        if contract_change_summary.get("new_agreement_driver_ids"):
            lines.append(
                "- New agreement driver IDs: "
                + ", ".join(contract_change_summary.get("new_agreement_driver_ids") or [])
            )
        if contract_change_summary.get("new_agreement_by_service_date"):
            lines.append(
                "- New agreement by service date: "
                + ", ".join(
                    f"{service_date}={count}"
                    for service_date, count in sorted(
                        (contract_change_summary.get("new_agreement_by_service_date") or {}).items()
                    )
                )
            )
        if reserve_summary.get("selected_on_call_by_service_date"):
            lines.append(
                "- On-call buffer by service date: "
                + ", ".join(
                    f"{service_date}={count}/{(reserve_summary.get('on_call_target_by_service_date') or {}).get(service_date, 0)}"
                    for service_date, count in sorted(
                        (reserve_summary.get("selected_on_call_by_service_date") or {}).items()
                    )
                )
            )
        if excess_capacity_summary.get("selected_excess_capacity_by_service_date"):
            lines.append(
                "- Excess-capacity baseline shifts by service date: "
                + ", ".join(
                    f"{service_date}={count}/{(excess_capacity_summary.get('excess_capacity_target_by_service_date') or {}).get(service_date, 0)}"
                    for service_date, count in sorted(
                        (
                            excess_capacity_summary.get("selected_excess_capacity_by_service_date")
                            or {}
                        ).items()
                    )
                )
            )
        for tradeoff in stage04_analysis.get("tradeoffs") or []:
            lines.append(f"- Tradeoff: {tradeoff}")
        for iteration in stage04_analysis.get("iterations") or []:
            lines.append(
                "- Iteration {iteration_index}: batch={batch_size}, assigned={assigned}, uncovered={uncovered}, repairs={repairs}".format(
                    iteration_index=iteration["iteration_index"],
                    batch_size=iteration["batch_size"],
                    assigned=len(iteration.get("assigned_route_slot_ids") or []),
                    uncovered=len(iteration.get("uncovered_route_slot_ids") or []),
                    repairs=len(iteration.get("repair_moves") or []),
                )
            )
        lines.append("")
        lines.append("## Runtime turns")
        for turn in stage04_analysis.get("runtime_turns") or []:
            lines.append(
                "- Turn {turn_index}: progress={progress}, streak={streak}, functions={functions}".format(
                    turn_index=turn["turn_index"],
                    progress=turn["progress_made"],
                    streak=turn["no_progress_streak"],
                    functions=",".join(turn.get("function_names") or []),
                )
            )
        lines.append("")
        lines.append("## Timeline")
    else:
        lines.extend(
            [
                "- Stage04 analysis artifacts not available.",
                "",
                "## Timeline",
            ]
        )
    lines.extend(
        [
            f"- Total events: {packet['timeline']['event_count']}",
            f"- Events of interest: {len(packet['timeline']['events_of_interest'])}",
            "",
            "## Inspection routes",
        ]
    )
    lines.extend(f"- UI: `{route}`" for route in packet["inspection"]["ui_routes"])
    lines.extend(f"- API: `{route}`" for route in packet["inspection"]["api_routes"])
    lines.extend(
        [
            "",
            "## Canonical query commands",
        ]
    )
    lines.extend(f"- `{command}`" for command in packet["canonical_evidence"]["canonical_query_commands"])
    lines.extend(
        [
            "",
            "## Correct-enough signals",
        ]
    )
    for key, value in sorted(packet["quality_signals"].items()):
        lines.append(f"- {key}: `{value}`")
    return "\n".join(lines) + "\n"


def _summary_to_markdown(summary: dict[str, Any]) -> str:
    lines = [
        "# Logistics Weekly Stage04 Pilot Summary",
        "",
        f"- Pilot key: `{summary['pilot_key']}`",
        f"- OpenAI mode: `{summary['openai_mode']}`",
        f"- Artifact root: `{summary['artifact_root']}`",
        f"- Output root: `{summary['output_root']}`",
        "",
        "## Pilot runs",
        "| Pilot | Workflow Run | Reused Existing | Packet |",
        "|---|---|---|---|",
    ]
    for run in summary["pilot_runs"]:
        lines.append(
            "| {pilot_id} | `{workflow_run_id}` | `{reused_existing}` | `{inspection_packet_path}` |".format(
                **run,
            )
        )
    return "\n".join(lines) + "\n"


def _validate_selected_pilots(pilot_ids: Sequence[str]) -> None:
    invalid = [pilot_id for pilot_id in pilot_ids if pilot_id not in PILOT_DEFINITIONS]
    if invalid:
        raise ValueError(f"unknown pilot ids: {', '.join(sorted(invalid))}")


def _dedupe_preserving_order(values: Iterable[str]) -> list[str]:
    seen: set[str] = set()
    ordered: list[str] = []
    for value in values:
        if value in seen:
            continue
        seen.add(value)
        ordered.append(value)
    return ordered


def _deterministic_id(prefix: str, *parts: str) -> str:
    raw = "|".join(parts)
    digest = hashlib.sha256(raw.encode("utf-8")).hexdigest()[:24]
    return f"{prefix}-{digest}"


@contextmanager
def _temporary_env(name: str, value: str):
    prior = os.environ.get(name)
    os.environ[name] = value
    try:
        yield
    finally:
        if prior is None:
            os.environ.pop(name, None)
        else:
            os.environ[name] = prior
