from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass
from datetime import date, timedelta
import hashlib
import json
import os
from pathlib import Path
import sqlite3
from typing import Any, Iterable, Sequence

import yaml

from onetruth.application.handlers.workflow_task_lifecycle import (
    CommandError,
    claim_human_task_command,
    create_artifact_version_command,
    create_task_run_command,
    create_workflow_run_command,
    list_approvals_for_workflow_run_command,
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

PILOT_WEEKLY_STAGE04_AGENT = "weekly_stage04_agent_baseline"
PILOT_WEEKLY_STAGE04_REALISTIC_ARTIFACTS = "weekly_stage04_realistic_artifacts"
ALL_PILOT_IDS: tuple[str, ...] = (
    PILOT_WEEKLY_STAGE04_AGENT,
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
        partition_key="PW-2026-W10",
        logical_date="2026-03-02",
        stage_focus="Stage04",
        description=(
            "Weekly Stage04 bounded OpenAI agent run over realistic day-resolution planning "
            "artifacts derived from real roster and route-email patterns."
        ),
    ),
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

    selected = tuple(pilot_ids) if pilot_ids else ALL_PILOT_IDS
    _validate_selected_pilots(selected)

    resolved_output_root = output_root.expanduser().resolve() / pilot_key
    resolved_output_root.mkdir(parents=True, exist_ok=True)

    resolved_artifact_root = (
        artifact_root.expanduser().resolve()
        if artifact_root is not None
        else default_storage_root_for_db_url(db_url)
    )
    resolved_artifact_root.mkdir(parents=True, exist_ok=True)

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
        pilot_results.append(
            {
                "pilot_id": pilot_id,
                "workflow_run_id": workflow_run_id,
                "reused_existing": not created,
                "inspection_packet_path": str(json_path),
                "inspection_markdown_path": str(md_path),
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
    summary_json_path = resolved_output_root / "pilot_summary.json"
    summary_md_path = resolved_output_root / "pilot_summary.md"
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
        idempotency_key=f"pilot:{pilot_key}:{definition.pilot_id}:tasks.claim:stage04-work-item",
    )

    selected_runner = _mock_stage04_runner() if openai_mode == "mock" else None
    with _temporary_env("ONETRUTH_ARTIFACT_ROOT", str(storage_root)):
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
    if pilot_id == PILOT_WEEKLY_STAGE04_REALISTIC_ARTIFACTS:
        return build_realistic_weekly_stage04_fixture_payloads()
    return {
        "route_slot_requirements": _ROUTE_SLOT_REQUIREMENTS_METADATA,
        "driver_capabilities": _DRIVER_CAPABILITIES_METADATA,
        "approved_availability": _APPROVED_AVAILABILITY_METADATA,
        "actual_hours": _ACTUAL_HOURS_METADATA,
    }


def build_realistic_weekly_stage04_fixture_payloads() -> dict[str, dict[str, Any]]:
    source = _load_realistic_weekly_stage04_source_material()
    route_demand_rows = source["route_demand_rows"]
    route_demand_columns = source["route_demand_columns"]
    roster_pattern_rows = source["roster_pattern_rows"]
    roster_pattern_columns = source["roster_pattern_columns"]
    capability_pattern_rows = source["capability_pattern_rows"]
    capability_pattern_columns = source["capability_pattern_columns"]
    active_driver_count = int(source["active_driver_count"])
    planning_week_start = date.fromisoformat(str(source["logical_date"]))

    roster_patterns = _rows_to_dicts(roster_pattern_columns, roster_pattern_rows)
    capability_patterns = _rows_to_dicts(capability_pattern_columns, capability_pattern_rows)

    route_slot_rows: list[list[Any]] = []
    for row in _rows_to_dicts(route_demand_columns, route_demand_rows):
        service_date = str(row["service_date"])
        demand_mix = [
            (
                "std",
                "cycle1_standard",
                "parcel_delivery",
                "11:40",
                "20:10",
                8.5,
                _coerce_int(row.get("standard_slot_count"), default=0),
                f"CX{100 + len(route_slot_rows):03d}",
            ),
            (
                "rsc",
                "cycle1_rescue",
                "rescue_support",
                "11:45",
                "20:35",
                8.8,
                _coerce_int(row.get("rescue_slot_count"), default=0),
                f"RS{80 + len(route_slot_rows):03d}",
            ),
            (
                "ovf",
                "cycle1_overflow",
                "parcel_delivery",
                "12:05",
                "21:45",
                8.7,
                _coerce_int(row.get("overflow_slot_count"), default=0),
                f"OV{60 + len(route_slot_rows):03d}",
            ),
        ]
        for slot_suffix, slot_class, skill, shift_start, shift_end, estimated_hours, required_count, route_id in demand_mix:
            if required_count <= 0:
                continue
            service_day_token = service_date.replace("-", "")
            route_slot_rows.append(
                [
                    service_date,
                    f"slot-{service_day_token}-{slot_suffix}",
                    slot_class,
                    skill,
                    "XL_van",
                    shift_start,
                    shift_end,
                    estimated_hours,
                    required_count,
                    route_id,
                    str(row.get("source_message_id") or ""),
                    "DVC4",
                    "Pitt Meadows",
                    f"{row.get('source_message_id') or 'source'}:{service_date}:slot-{service_day_token}-{slot_suffix}",
                ]
            )

    capability_rows: list[list[Any]] = []
    availability_rows: list[list[Any]] = []
    actual_hours_rows: list[list[Any]] = []
    previous_week_dates = [planning_week_start - timedelta(days=7 - offset) for offset in range(7)]
    planning_week_dates = [planning_week_start + timedelta(days=offset) for offset in range(7)]

    for index in range(active_driver_count):
        roster = roster_patterns[index % len(roster_patterns)]
        capability = capability_patterns[index % len(capability_patterns)]
        driver_id = f"RDRV-{index + 1:02d}"
        driver_name = f"{roster['driver_name']} {index // len(roster_patterns) + 1:02d}"
        regular_pattern = _csv_tokens(roster.get("regular_pattern"))
        approved_unavailable_dates = [
            current.isoformat()
            for offset, current in enumerate(planning_week_dates)
            if _weekday_token(current) in regular_pattern
            and ((index + offset) % 11 == 0 or (index % 9 == 0 and _weekday_token(current) == "Wed"))
        ]
        previous_week_blocked_dates = [
            current.isoformat()
            for offset, current in enumerate(previous_week_dates)
            if _weekday_token(current) in regular_pattern and (index + offset) % 13 == 0
        ]

        capability_rows.append(
            [
                driver_id,
                driver_name,
                str(roster.get("employment_type") or ""),
                str(roster.get("home_station") or ""),
                str(capability.get("skills") or ""),
                str(capability.get("vehicle_certifications") or ""),
                str(capability.get("eligible_route_slot_classes") or ""),
                str(capability.get("approved_restrictions") or ""),
                ",".join(
                    dict.fromkeys(
                        [
                            *_csv_tokens(roster.get("policy_tags")),
                            *_csv_tokens(capability.get("policy_tags")),
                        ]
                    )
                ),
                str(capability.get("notes") or ""),
            ]
        )
        availability_rows.append(
            [
                driver_id,
                driver_name,
                str(roster.get("employment_type") or ""),
                _coerce_int(roster.get("target_shifts_per_week"), default=4),
                str(roster.get("regular_pattern") or ""),
                str(roster.get("on_call_eligible") or ""),
                "yes" if index % 14 == 0 else str(roster.get("emergency_only") or ""),
                ",".join(approved_unavailable_dates),
                ",".join(previous_week_blocked_dates),
                str(roster.get("policy_tags") or ""),
                f"Deterministic realistic roster row {index + 1:02d}",
            ]
        )

        worked_days = 0
        for offset, current in enumerate(previous_week_dates):
            weekday = _weekday_token(current)
            if current.isoformat() in previous_week_blocked_dates:
                continue
            if weekday in regular_pattern and (index + offset) % 3 != 0:
                actual_minutes = 510 + ((index * 37 + offset * 13) % 120)
                route_id = f"CX{80 + ((index + offset) % 40):03d}"
                actual_hours_rows.append(
                    [
                        current.isoformat(),
                        driver_id,
                        driver_name,
                        actual_minutes,
                        route_id,
                        f"EOS {current.isoformat()}",
                        f"eos:{current.isoformat()}:{driver_id}:{route_id}",
                    ]
                )
                worked_days += 1
            if worked_days >= (3 if index % 10 == 0 else 2):
                break

    return {
        "route_slot_requirements": {
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
            "rows": route_slot_rows,
            "daily_demand_columns": route_demand_columns,
            "daily_demand_rows": route_demand_rows,
            "planner_notes": [
                "Demand remains below four weekly shifts per active driver across the 40-driver realistic pilot.",
            ],
        },
        "driver_capabilities": {
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
            "rows": capability_rows,
        },
        "approved_availability": {
            "columns": [
                "driver_id",
                "driver_name",
                "employment_type",
                "target_shifts_per_week",
                "regular_pattern",
                "on_call_eligible",
                "emergency_only",
                "approved_unavailable_dates",
                "previous_week_blocked_dates",
                "policy_tags",
                "notes",
            ],
            "rows": availability_rows,
            "planner_notes": [
                "Planning-week daily state is derived from regular-pattern coverage plus explicit blocked dates.",
            ],
        },
        "actual_hours": {
            "columns": [
                "service_date",
                "driver_id",
                "driver_name",
                "actual_minutes",
                "route_id",
                "source",
                "source_snapshot_row_ref",
            ],
            "rows": actual_hours_rows,
            "external_evidence_refs": ["eos-upload-2026-03-03"],
        },
    }


def _load_realistic_weekly_stage04_source_material() -> dict[str, Any]:
    loaded = yaml.safe_load(
        REALISTIC_WEEKLY_STAGE04_SOURCE_MATERIAL_PATH.read_text(encoding="utf-8")
    )
    if not isinstance(loaded, dict):
        raise ValueError("realistic Stage04 source material must decode to an object")
    return loaded


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
                            "call_id": "call_build",
                            "name": "materialize_weekly_stage04_draft_outputs",
                            "arguments": "{}",
                        },
                    ],
                },
                "req_pilot_1",
            )
        if calls["count"] == 2:
            if payload.get("previous_response_id") != "resp_pilot_1":
                raise AssertionError("expected previous_response_id from first pilot turn")
            return (
                200,
                {
                    "id": "resp_pilot_2",
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
                            "call_id": "call_ops_packet",
                            "name": "render_stage04_ops_packet",
                            "arguments": "{}",
                        },
                    ],
                },
                "req_pilot_2",
            )
        if payload.get("previous_response_id") != "resp_pilot_2":
            raise AssertionError("expected previous_response_id from second pilot turn")
        return (
            200,
            {
                "id": "resp_pilot_3",
                "model": "gpt-4.1-mini",
                "usage": {"input_tokens": 13, "output_tokens": 8},
                "output_text": (
                    '{"summary":"pilot run complete","selected_candidate_count":2,'
                    '"recommended_action":"forward_to_stage05_manager_review","warnings":[]}'
                ),
            },
            "req_pilot_3",
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
            "## Timeline",
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
