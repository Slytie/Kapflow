from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import os
from pathlib import Path
import shlex
import sqlite3
import subprocess
import sys
from typing import Callable, Mapping, Sequence
import zipfile

from onetruth.infrastructure.events.event_store import utc_now_iso

SCENARIO_STAGE06_PUBLISH_READY = "stage06_publish_ready"
SCENARIO_STAGE07_MAJOR_REPLAN = "stage07_major_replan"
SCENARIO_LOGISTICS_WEEKLY_TO_LIVE = "logistics_weekly_to_live_golden_slice"

REPO_ROOT = Path(__file__).resolve().parents[4]
SRC_ROOT = REPO_ROOT / "src"

CANONICAL_SCENARIO_ORDER: tuple[str, ...] = (
    SCENARIO_STAGE06_PUBLISH_READY,
    SCENARIO_STAGE07_MAJOR_REPLAN,
    SCENARIO_LOGISTICS_WEEKLY_TO_LIVE,
)

SCENARIO_LABELS: dict[str, str] = {
    SCENARIO_STAGE06_PUBLISH_READY: "schedule.stage06_publish_ready_workspace_demo",
    SCENARIO_STAGE07_MAJOR_REPLAN: "schedule.stage07_major_replan_workspace_demo",
    SCENARIO_LOGISTICS_WEEKLY_TO_LIVE: "logistics.weekly_to_live_golden_slice",
}


@dataclass(frozen=True)
class CertificationScenarioContext:
    scenario_id: str
    scenario_label: str
    db_url: str
    certification_key: str
    openai_mode: str
    output_root: Path
    scenario_output_dir: Path


ScenarioRunner = Callable[[CertificationScenarioContext], dict[str, object]]


class CertificationCommandError(RuntimeError):
    def __init__(self, *, message: str, command_record: dict[str, object]) -> None:
        super().__init__(message)
        self.command_record = command_record


def deterministic_scenario_labels(
    selected_scenarios: Sequence[str] | None = None,
) -> tuple[str, ...]:
    selected = _normalize_selected_scenarios(selected_scenarios)
    return tuple(SCENARIO_LABELS[scenario_id] for scenario_id in selected)


def run_current_capability_certification(
    *,
    db_url: str,
    certification_key: str,
    output_root: Path,
    openai_mode: str = "mock",
    selected_scenarios: Sequence[str] | None = None,
    scenario_runners: Mapping[str, ScenarioRunner] | None = None,
    now_iso: str | None = None,
    manifest_path: Path | None = None,
) -> dict[str, object]:
    if openai_mode not in {"mock", "real"}:
        raise ValueError("openai_mode must be 'mock' or 'real'")

    selected = _normalize_selected_scenarios(selected_scenarios)
    base_runners = _default_scenario_runners()
    custom_runners = dict(scenario_runners or {})
    runners = dict(base_runners)
    runners.update(custom_runners)
    _validate_runner_coverage(selected, runners)

    resolved_root = output_root.expanduser().resolve() / certification_key
    resolved_root.mkdir(parents=True, exist_ok=True)

    resolved_manifest_path = (
        manifest_path.expanduser().resolve()
        if manifest_path is not None
        else resolved_root / "certification_manifest.json"
    )
    resolved_markdown_path = resolved_manifest_path.with_suffix(".md")

    generated_at = now_iso or utc_now_iso()
    bootstrap_commands: list[dict[str, object]] = []
    if _needs_runtime_bootstrap(selected, custom_runners):
        _, command_record = _run_onetruth_cli_command(
            db_url=db_url,
            cli_args=["init-db"],
        )
        bootstrap_commands.append(command_record)

    scenario_rows: list[dict[str, object]] = []
    for scenario_id in selected:
        label = SCENARIO_LABELS[scenario_id]
        scenario_output_dir = resolved_root / scenario_id
        scenario_output_dir.mkdir(parents=True, exist_ok=True)
        context = CertificationScenarioContext(
            scenario_id=scenario_id,
            scenario_label=label,
            db_url=db_url,
            certification_key=certification_key,
            openai_mode=openai_mode,
            output_root=resolved_root,
            scenario_output_dir=scenario_output_dir,
        )
        scenario_started = now_iso or utc_now_iso()
        try:
            run_result = runners[scenario_id](context)
            invariants = _normalize_invariants(run_result.get("invariants"))
            invariant_summary = _summarize_invariants(invariants)
            scenario_status = (
                "passed" if invariant_summary["failed"] == 0 else "failed"
            )
            scenario_row = {
                "scenario_id": scenario_id,
                "scenario_label": label,
                "status": scenario_status,
                "started_at": scenario_started,
                "completed_at": now_iso or utc_now_iso(),
                "entrypoint_commands": list(run_result.get("entrypoint_commands") or []),
                "run_ids": dict(run_result.get("run_ids") or {}),
                "edge_execution_ids": list(run_result.get("edge_execution_ids") or []),
                "output_bundle_path": _coerce_path_string(
                    run_result.get("output_bundle_path")
                ),
                "artifact_paths": [
                    _coerce_path_string(path)
                    for path in list(run_result.get("artifact_paths") or [])
                    if _coerce_path_string(path)
                ],
                "invariants": invariants,
                "invariant_summary": invariant_summary,
            }
        except Exception as exc:
            scenario_row = {
                "scenario_id": scenario_id,
                "scenario_label": label,
                "status": "failed",
                "started_at": scenario_started,
                "completed_at": now_iso or utc_now_iso(),
                "entrypoint_commands": [],
                "run_ids": {},
                "edge_execution_ids": [],
                "output_bundle_path": None,
                "artifact_paths": [],
                "invariants": [],
                "invariant_summary": {"passed": 0, "failed": 0, "total": 0},
                "error": {
                    "type": type(exc).__name__,
                    "message": str(exc),
                },
            }
            if isinstance(exc, CertificationCommandError):
                scenario_row["entrypoint_commands"] = [exc.command_record]
        scenario_rows.append(scenario_row)

    passed_scenarios = sum(1 for row in scenario_rows if row["status"] == "passed")
    failed_scenarios = len(scenario_rows) - passed_scenarios
    status = "passed" if failed_scenarios == 0 else "failed"

    manifest: dict[str, object] = {
        "manifest_version": 1,
        "command": "current-capability-certification.run",
        "generated_at": generated_at,
        "status": status,
        "certification_key": certification_key,
        "openai_mode": openai_mode,
        "db_url": db_url,
        "output_root": str(resolved_root),
        "selected_scenarios": list(selected),
        "selected_labels": list(deterministic_scenario_labels(selected)),
        "scenario_count": len(scenario_rows),
        "passed_scenarios": passed_scenarios,
        "failed_scenarios": failed_scenarios,
        "bootstrap_commands": bootstrap_commands,
        "scenarios": scenario_rows,
    }
    manifest["manifest_path"] = str(resolved_manifest_path)
    manifest["manifest_markdown_path"] = str(resolved_markdown_path)

    resolved_manifest_path.parent.mkdir(parents=True, exist_ok=True)
    resolved_manifest_path.write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    resolved_markdown_path.write_text(
        _manifest_to_markdown(manifest),
        encoding="utf-8",
    )
    return manifest


def certification_exit_code(manifest: Mapping[str, object]) -> int:
    return 0 if str(manifest.get("status")) == "passed" else 1


def _default_scenario_runners() -> dict[str, ScenarioRunner]:
    return {
        SCENARIO_STAGE06_PUBLISH_READY: _run_stage06_publish_ready_scenario,
        SCENARIO_STAGE07_MAJOR_REPLAN: _run_stage07_major_replan_scenario,
        SCENARIO_LOGISTICS_WEEKLY_TO_LIVE: _run_logistics_weekly_to_live_scenario,
    }


def _run_stage06_publish_ready_scenario(
    context: CertificationScenarioContext,
) -> dict[str, object]:
    return _run_workspace_demo_scenario(
        context,
        demo_scenario="stage06_publish_ready",
        pointer_key_expected="official:schedule.published_schedule.workbook",
        invariant_checks=(
            ("stage06_has_responded_approval", _invariant_stage06_has_responded_approval),
            ("stage06_has_official_published_pointer", _invariant_stage06_has_published_pointer),
            ("stage06_timeline_has_pointer_promotion", _invariant_stage06_timeline_pointer_promoted),
        ),
    )


def _run_stage07_major_replan_scenario(
    context: CertificationScenarioContext,
) -> dict[str, object]:
    return _run_workspace_demo_scenario(
        context,
        demo_scenario="stage07_major_replan",
        pointer_key_expected="official:schedule.replan_delta.workbook",
        invariant_checks=(
            ("stage07_has_resolved_flag", _invariant_stage07_has_resolved_flag),
            ("stage07_has_major_replan_pointer", _invariant_stage07_has_replan_pointer),
            ("stage07_has_responded_approval", _invariant_stage07_has_responded_approval),
            ("stage07_timeline_has_pointer_promotion", _invariant_stage07_timeline_pointer_promoted),
        ),
    )


def _run_workspace_demo_scenario(
    context: CertificationScenarioContext,
    *,
    demo_scenario: str,
    pointer_key_expected: str,
    invariant_checks: Sequence[
        tuple[str, Callable[[dict[str, object]], dict[str, object]]]
    ],
) -> dict[str, object]:
    command_records: list[dict[str, object]] = []
    output_json_path = context.scenario_output_dir / "workspace_demo_result.json"
    demo_output_root = context.scenario_output_dir / "workspace_demo_artifacts"

    demo_payload, command_record = _run_python_script_command(
        script_rel_path="scripts/run_schedule_workspace_demo.py",
        script_args=[
            "--db-url",
            context.db_url,
            "--scenario",
            demo_scenario,
            "--pilot-key",
            context.certification_key,
            "--output-root",
            str(demo_output_root),
            "--output-json",
            str(output_json_path),
            "--openai-mode",
            context.openai_mode,
        ],
    )
    command_records.append(command_record)

    workflow_run_id = str(demo_payload["workflow_run_id"])
    bundle_path = context.scenario_output_dir / "workspace_bundle.zip"
    export_payload, command_record = _run_python_script_command(
        script_rel_path="scripts/export_run_workspace_bundle.py",
        script_args=[
            "--db-url",
            context.db_url,
            "--workflow-run-id",
            workflow_run_id,
            "--output",
            str(bundle_path),
        ],
    )
    command_records.append(command_record)

    if str(export_payload.get("status")) != "ok":
        raise RuntimeError(f"workspace export did not succeed: {export_payload}")
    if not bundle_path.exists():
        raise RuntimeError(f"workspace bundle was not created: {bundle_path}")

    approvals = _read_zip_json(bundle_path, "approvals.json")
    flags = _read_zip_json(bundle_path, "flags.json")
    pointers = _read_zip_json(bundle_path, "official_pointers.json")
    timeline = _read_zip_json(bundle_path, "timeline_excerpt.json")

    parsed_bundle = {
        "approvals": approvals,
        "flags": flags,
        "pointers": pointers,
        "timeline": timeline,
        "pointer_key_expected": pointer_key_expected,
    }
    invariants = [
        _invariant_result(invariant_id=invariant_id, **invariant_fn(parsed_bundle))
        for invariant_id, invariant_fn in invariant_checks
    ]

    return {
        "entrypoint_commands": command_records,
        "run_ids": {"workflow_run_id": workflow_run_id},
        "edge_execution_ids": [],
        "output_bundle_path": str(bundle_path),
        "artifact_paths": [
            str(output_json_path),
            str(demo_payload.get("inspection_packet_path")),
            str(demo_payload.get("inspection_markdown_path")),
            str(bundle_path),
        ],
        "invariants": invariants,
    }


def _run_logistics_weekly_to_live_scenario(
    context: CertificationScenarioContext,
) -> dict[str, object]:
    command_records: list[dict[str, object]] = []

    weekly_run_id = _deterministic_id(
        "wr",
        context.certification_key,
        context.scenario_id,
        "weekly-run",
    )

    weekly_run_payload = {
        "workflow_run_id": weekly_run_id,
        "workflow_id": "weekly_schedule_planning.v1",
        "workflow_version": "v1",
        "tenant_id": "tenant-logistics",
        "domain_id": "domain-hub",
        "partition_key": "PW-2026-W10",
        "logical_date": "2026-03-02",
        "activation_key": f"cert:{context.certification_key}:{context.scenario_id}:weekly-run",
        "idempotency_key": f"cert:{context.certification_key}:{context.scenario_id}:runs.create",
    }
    runs_create, record = _run_onetruth_cli_command(
        db_url=context.db_url,
        cli_args=["runs", "create", "--json", json.dumps(weekly_run_payload, separators=(",", ":"))],
    )
    command_records.append(record)
    weekly_run_id = str(runs_create["workflow_run"]["workflow_run_id"])

    publish_payload = {
        "workflow_run_id": weekly_run_id,
        "artifact_kind": "planning.published_weekly_schedule.workbook",
        "artifact_role": "official_output",
        "media_type": "application/octet-stream",
        "storage_uri": f"inmem://certification/{weekly_run_id}/weekly-publish",
        "content_digest": f"sha256:{_deterministic_id('dgst', context.certification_key, context.scenario_id, 'weekly-publish')}",
        "metadata_json": {"scenario_id": context.scenario_id},
        "idempotency_key": f"cert:{context.certification_key}:{context.scenario_id}:artifact:weekly-publish",
    }
    publish_result, record = _run_onetruth_cli_command(
        db_url=context.db_url,
        cli_args=["artifacts", "create-version", "--json", json.dumps(publish_payload, separators=(",", ":"))],
    )
    command_records.append(record)
    published_artifact_version_id = str(
        publish_result["artifact_version"]["artifact_version_id"]
    )

    approval_request_payload = {
        "workflow_run_id": weekly_run_id,
        "approval_kind": "business_decision",
        "scope_kind": "stage",
        "scope_ref": "Stage06",
        "candidate_roles": ["operations_manager"],
        "required_role": "operations_manager",
        "idempotency_key": f"cert:{context.certification_key}:{context.scenario_id}:approval:request",
    }
    approval_requested, record = _run_onetruth_cli_command(
        db_url=context.db_url,
        cli_args=[
            "approvals",
            "request",
            "--json",
            json.dumps(approval_request_payload, separators=(",", ":")),
        ],
    )
    command_records.append(record)
    approval_id = str(approval_requested["approval"]["approval_id"])

    approval_respond_payload = {
        "approval_id": approval_id,
        "actor_id": "human:ops-manager-1",
        "actor_type": "human",
        "actor_roles": ["operations_manager"],
        "response_kind": "approve",
        "idempotency_key": f"cert:{context.certification_key}:{context.scenario_id}:approval:respond",
    }
    _, record = _run_onetruth_cli_command(
        db_url=context.db_url,
        cli_args=[
            "approvals",
            "respond",
            "--json",
            json.dumps(approval_respond_payload, separators=(",", ":")),
        ],
    )
    command_records.append(record)

    pointer_promote_payload = {
        "workflow_run_id": weekly_run_id,
        "scope_kind": "stage",
        "scope_ref": "Stage06",
        "pointer_key": "official:planning.published_weekly_schedule.workbook",
        "artifact_kind": "planning.published_weekly_schedule.workbook",
        "artifact_version_id": published_artifact_version_id,
        "promotion_reason": "official_publish",
        "approved_by_approval_id": approval_id,
        "actor_id": "human:ops-manager-1",
        "actor_type": "human",
        "idempotency_key": f"cert:{context.certification_key}:{context.scenario_id}:pointer:promote",
    }
    _, record = _run_onetruth_cli_command(
        db_url=context.db_url,
        cli_args=[
            "pointers",
            "promote",
            "--json",
            json.dumps(pointer_promote_payload, separators=(",", ":")),
        ],
    )
    command_records.append(record)

    materialize_payload = {
        "workflow_run_id": weekly_run_id,
        "published_artifact_version_id": published_artifact_version_id,
        "service_date_id": "SD-2026-03-06",
        "idempotency_key": f"cert:{context.certification_key}:{context.scenario_id}:handoff:materialize",
    }
    materialized, record = _run_onetruth_cli_command(
        db_url=context.db_url,
        cli_args=[
            "handoffs",
            "materialize-weekly-seeds",
            "--json",
            json.dumps(materialize_payload, separators=(",", ":")),
        ],
    )
    command_records.append(record)
    edge_execution_id = str(
        materialized["result"]["edge_executions"][0]["edge_execution_id"]
    )

    route_delta_payload = {
        "workflow_run_id": weekly_run_id,
        "artifact_kind": "dispatch.route_delta_intake.workbook",
        "artifact_role": "official_input",
        "media_type": "application/octet-stream",
        "storage_uri": f"inmem://certification/{weekly_run_id}/route-delta",
        "content_digest": f"sha256:{_deterministic_id('dgst', context.certification_key, context.scenario_id, 'route-delta')}",
        "canonical_partition_kind": "ServiceDateID",
        "canonical_partition_key": "SD-2026-03-06",
        "metadata_json": {"service_date_id": "SD-2026-03-06"},
        "idempotency_key": f"cert:{context.certification_key}:{context.scenario_id}:artifact:route-delta",
    }
    route_delta_result, record = _run_onetruth_cli_command(
        db_url=context.db_url,
        cli_args=[
            "artifacts",
            "create-version",
            "--json",
            json.dumps(route_delta_payload, separators=(",", ":")),
        ],
    )
    command_records.append(record)
    route_delta_artifact_version_id = str(
        route_delta_result["artifact_version"]["artifact_version_id"]
    )

    actual_hours_payload = {
        "workflow_run_id": weekly_run_id,
        "artifact_kind": "planning.actual_hours_snapshot.workbook",
        "artifact_role": "official_input",
        "media_type": "application/octet-stream",
        "storage_uri": f"inmem://certification/{weekly_run_id}/actual-hours",
        "content_digest": f"sha256:{_deterministic_id('dgst', context.certification_key, context.scenario_id, 'actual-hours')}",
        "metadata_json": {"service_date_id": "SD-2026-03-06"},
        "idempotency_key": f"cert:{context.certification_key}:{context.scenario_id}:artifact:actual-hours",
    }
    actual_hours_result, record = _run_onetruth_cli_command(
        db_url=context.db_url,
        cli_args=[
            "artifacts",
            "create-version",
            "--json",
            json.dumps(actual_hours_payload, separators=(",", ":")),
        ],
    )
    command_records.append(record)
    actual_hours_artifact_version_id = str(
        actual_hours_result["artifact_version"]["artifact_version_id"]
    )

    activate_payload = {
        "edge_execution_id": edge_execution_id,
        "route_delta_source_artifact_version_id": route_delta_artifact_version_id,
        "actual_hours_source_artifact_version_id": actual_hours_artifact_version_id,
        "idempotency_key": f"cert:{context.certification_key}:{context.scenario_id}:handoff:activate",
    }
    activated, record = _run_onetruth_cli_command(
        db_url=context.db_url,
        cli_args=[
            "handoffs",
            "activate-live-dispatch",
            "--json",
            json.dumps(activate_payload, separators=(",", ":")),
        ],
    )
    command_records.append(record)

    handoff_list, record = _run_onetruth_cli_command(
        db_url=context.db_url,
        cli_args=[
            "handoffs",
            "list",
            "--source-workflow-run-id",
            weekly_run_id,
            "--json",
        ],
    )
    command_records.append(record)

    target_workflow_run_id = str(
        activated["result"]["target_workflow_run"]["workflow_run_id"]
    )
    input_binding_count = _count_workflow_run_inputs(
        db_url=context.db_url,
        workflow_run_id=target_workflow_run_id,
    )

    invariants = [
        _invariant_result(
            invariant_id="logistics_materialized_one_edge_execution",
            description="materialize-weekly-seeds yields exactly one edge execution for one service day",
            passed=len(materialized["result"]["edge_executions"]) == 1,
            details={
                "edge_execution_count": len(materialized["result"]["edge_executions"]),
            },
        ),
        _invariant_result(
            invariant_id="logistics_activation_status_activated",
            description="activate-live-dispatch transitions edge execution to activated",
            passed=str(activated["result"]["edge_execution"]["status"]) == "activated",
            details={
                "edge_execution_id": edge_execution_id,
                "status": activated["result"]["edge_execution"]["status"],
            },
        ),
        _invariant_result(
            invariant_id="logistics_target_workflow_is_live_dispatch",
            description="activation creates or resolves a live_dispatch.v1 target workflow run",
            passed=str(activated["result"]["target_workflow_run"]["workflow_id"]) == "live_dispatch.v1",
            details={
                "target_workflow_id": activated["result"]["target_workflow_run"]["workflow_id"],
            },
        ),
        _invariant_result(
            invariant_id="logistics_handoff_list_contains_activated_edge",
            description="handoffs.list returns the same activated edge execution",
            passed=any(
                str(item.get("edge_execution_id")) == edge_execution_id
                and str(item.get("status")) == "activated"
                for item in handoff_list.get("edge_executions", [])
            ),
            details={
                "edge_execution_id": edge_execution_id,
                "listed_edge_count": len(handoff_list.get("edge_executions", [])),
            },
        ),
        _invariant_result(
            invariant_id="logistics_target_run_input_bindings_created",
            description="target live dispatch run records canonical workflow_run_inputs bindings",
            passed=input_binding_count >= 3,
            details={
                "workflow_run_id": target_workflow_run_id,
                "workflow_run_input_count": input_binding_count,
            },
        ),
    ]

    bundle_payload = {
        "scenario_id": context.scenario_id,
        "workflow_run_id": weekly_run_id,
        "target_workflow_run_id": target_workflow_run_id,
        "edge_execution_id": edge_execution_id,
        "materialize_result": materialized["result"],
        "activation_result": activated["result"],
        "handoffs_list": handoff_list.get("edge_executions", []),
        "workflow_run_input_count": input_binding_count,
    }
    bundle_path = context.scenario_output_dir / "logistics_handoff_bundle.json"
    bundle_path.write_text(
        json.dumps(bundle_payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    return {
        "entrypoint_commands": command_records,
        "run_ids": {
            "workflow_run_id": weekly_run_id,
            "target_workflow_run_id": target_workflow_run_id,
        },
        "edge_execution_ids": [edge_execution_id],
        "output_bundle_path": str(bundle_path),
        "artifact_paths": [str(bundle_path)],
        "invariants": invariants,
    }


def _invariant_stage06_has_responded_approval(
    bundle: dict[str, object],
) -> dict[str, object]:
    approvals = list(bundle["approvals"])
    passed = any(str(row.get("state")) == "RESPONDED" for row in approvals)
    return {
        "description": "Stage06 demo includes a responded approval record",
        "passed": passed,
        "details": {"approval_count": len(approvals)},
    }


def _invariant_stage06_has_published_pointer(
    bundle: dict[str, object],
) -> dict[str, object]:
    pointers = list(bundle["pointers"])
    expected = str(bundle["pointer_key_expected"])
    passed = any(str(row.get("pointer_key")) == expected for row in pointers)
    return {
        "description": "Stage06 demo promotes official publish pointer",
        "passed": passed,
        "details": {"pointer_key_expected": expected, "pointer_count": len(pointers)},
    }


def _invariant_stage06_timeline_pointer_promoted(
    bundle: dict[str, object],
) -> dict[str, object]:
    timeline = list(bundle["timeline"])
    passed = any(str(row.get("event_type")) == "artifact.pointer.promoted" for row in timeline)
    return {
        "description": "Stage06 timeline excerpt includes artifact.pointer.promoted",
        "passed": passed,
        "details": {"timeline_event_count": len(timeline)},
    }


def _invariant_stage07_has_resolved_flag(
    bundle: dict[str, object],
) -> dict[str, object]:
    flags = list(bundle["flags"])
    passed = any(str(row.get("state")) == "resolved" for row in flags)
    return {
        "description": "Stage07 demo resolves at least one issue flag",
        "passed": passed,
        "details": {"flag_count": len(flags)},
    }


def _invariant_stage07_has_replan_pointer(
    bundle: dict[str, object],
) -> dict[str, object]:
    pointers = list(bundle["pointers"])
    expected = str(bundle["pointer_key_expected"])
    passed = any(str(row.get("pointer_key")) == expected for row in pointers)
    return {
        "description": "Stage07 demo promotes official replan pointer",
        "passed": passed,
        "details": {"pointer_key_expected": expected, "pointer_count": len(pointers)},
    }


def _invariant_stage07_has_responded_approval(
    bundle: dict[str, object],
) -> dict[str, object]:
    approvals = list(bundle["approvals"])
    passed = any(str(row.get("state")) == "RESPONDED" for row in approvals)
    return {
        "description": "Stage07 demo includes responded major replan approval",
        "passed": passed,
        "details": {"approval_count": len(approvals)},
    }


def _invariant_stage07_timeline_pointer_promoted(
    bundle: dict[str, object],
) -> dict[str, object]:
    timeline = list(bundle["timeline"])
    passed = any(str(row.get("event_type")) == "artifact.pointer.promoted" for row in timeline)
    return {
        "description": "Stage07 timeline excerpt includes artifact.pointer.promoted",
        "passed": passed,
        "details": {"timeline_event_count": len(timeline)},
    }


def _count_workflow_run_inputs(*, db_url: str, workflow_run_id: str) -> int:
    db_path = _sqlite_db_path(db_url)
    connection = sqlite3.connect(db_path)
    try:
        row = connection.execute(
            "SELECT COUNT(*) FROM workflow_run_inputs WHERE workflow_run_id = ?",
            (workflow_run_id,),
        ).fetchone()
        if row is None:
            return 0
        return int(row[0])
    finally:
        connection.close()


def _sqlite_db_path(db_url: str) -> Path:
    prefix = "sqlite:///"
    if not db_url.startswith(prefix):
        raise ValueError(f"only sqlite db_url is supported for certification harness: {db_url}")
    return Path(db_url[len(prefix):]).expanduser().resolve()


def _run_python_script_command(
    *,
    script_rel_path: str,
    script_args: Sequence[str],
) -> tuple[dict[str, object], dict[str, object]]:
    script_path = REPO_ROOT / script_rel_path
    return _execute_json_command(
        argv=[sys.executable, str(script_path), *script_args],
        entrypoint=script_rel_path,
    )


def _run_onetruth_cli_command(
    *,
    db_url: str,
    cli_args: Sequence[str],
) -> tuple[dict[str, object], dict[str, object]]:
    return _execute_json_command(
        argv=[sys.executable, "-m", "onetruth.cli", "--db-url", db_url, *cli_args],
        entrypoint="onetruth.cli",
    )


def _execute_json_command(
    *,
    argv: Sequence[str],
    entrypoint: str,
) -> tuple[dict[str, object], dict[str, object]]:
    env = _pythonpath_env()
    command_str = shlex.join([str(item) for item in argv])
    completed = subprocess.run(
        [str(item) for item in argv],
        cwd=REPO_ROOT,
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )
    command_record: dict[str, object] = {
        "entrypoint": entrypoint,
        "command": command_str,
        "argv": [str(item) for item in argv],
        "exit_code": int(completed.returncode),
    }
    if completed.returncode != 0:
        message = completed.stderr.strip() or completed.stdout.strip() or "command failed"
        command_record["stderr"] = completed.stderr.strip()
        command_record["stdout"] = completed.stdout.strip()
        raise CertificationCommandError(
            message=f"{entrypoint} command failed: {message}",
            command_record=command_record,
        )

    stdout = completed.stdout.strip()
    if not stdout:
        return {}, command_record
    try:
        payload = json.loads(stdout)
    except json.JSONDecodeError as exc:
        command_record["stdout"] = stdout
        raise CertificationCommandError(
            message=f"{entrypoint} output was not valid JSON: {exc}",
            command_record=command_record,
        ) from exc
    return payload, command_record


def _pythonpath_env() -> dict[str, str]:
    env = os.environ.copy()
    src_value = str(SRC_ROOT)
    existing = env.get("PYTHONPATH")
    if existing:
        env["PYTHONPATH"] = f"{src_value}{os.pathsep}{existing}"
    else:
        env["PYTHONPATH"] = src_value
    return env


def _read_zip_json(bundle_path: Path, file_name: str) -> list[dict[str, object]]:
    with zipfile.ZipFile(bundle_path, "r") as archive:
        content = archive.read(file_name).decode("utf-8")
    parsed = json.loads(content)
    if isinstance(parsed, list):
        return parsed
    if isinstance(parsed, dict):
        if file_name == "timeline_excerpt.json":
            events = parsed.get("events")
            if isinstance(events, list):
                return events
        return [parsed]
    raise RuntimeError(f"unexpected JSON payload shape for {file_name}")


def _normalize_selected_scenarios(
    selected_scenarios: Sequence[str] | None,
) -> tuple[str, ...]:
    if selected_scenarios is None or not selected_scenarios:
        return CANONICAL_SCENARIO_ORDER
    requested = list(dict.fromkeys(str(item) for item in selected_scenarios))
    unknown = [item for item in requested if item not in SCENARIO_LABELS]
    if unknown:
        raise ValueError(f"unknown scenario id(s): {', '.join(sorted(unknown))}")
    requested_set = set(requested)
    return tuple(
        scenario_id
        for scenario_id in CANONICAL_SCENARIO_ORDER
        if scenario_id in requested_set
    )


def _validate_runner_coverage(
    selected_scenarios: Sequence[str],
    runners: Mapping[str, ScenarioRunner],
) -> None:
    missing = [scenario_id for scenario_id in selected_scenarios if scenario_id not in runners]
    if missing:
        raise ValueError(f"missing scenario runner(s): {', '.join(missing)}")


def _needs_runtime_bootstrap(
    selected_scenarios: Sequence[str],
    custom_runners: Mapping[str, ScenarioRunner],
) -> bool:
    return any(scenario_id not in custom_runners for scenario_id in selected_scenarios)


def _normalize_invariants(raw: object) -> list[dict[str, object]]:
    if raw is None:
        return []
    if not isinstance(raw, list):
        raise ValueError("runner invariants must be a list")
    normalized: list[dict[str, object]] = []
    for index, item in enumerate(raw):
        if not isinstance(item, dict):
            raise ValueError(f"invariant at index {index} must be an object")
        invariant_id = str(item.get("invariant_id") or f"invariant_{index + 1}")
        description = str(item.get("description") or invariant_id)
        status_raw = str(item.get("status") or "failed").lower()
        status = "passed" if status_raw == "passed" else "failed"
        normalized.append(
            {
                "invariant_id": invariant_id,
                "description": description,
                "status": status,
                "details": item.get("details") if isinstance(item.get("details"), dict) else {},
            }
        )
    return normalized


def _summarize_invariants(invariants: Sequence[Mapping[str, object]]) -> dict[str, int]:
    passed = sum(1 for item in invariants if str(item.get("status")) == "passed")
    total = len(invariants)
    failed = total - passed
    return {"passed": passed, "failed": failed, "total": total}


def _invariant_result(
    *,
    invariant_id: str,
    description: str,
    passed: bool,
    details: dict[str, object],
) -> dict[str, object]:
    return {
        "invariant_id": invariant_id,
        "description": description,
        "status": "passed" if passed else "failed",
        "details": details,
    }


def _deterministic_id(prefix: str, *parts: str, length: int = 24) -> str:
    seed = "|".join(parts).encode("utf-8")
    digest = hashlib.sha256(seed).hexdigest()[:length]
    return f"{prefix}-{digest}"


def _coerce_path_string(value: object) -> str | None:
    if value is None:
        return None
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, str):
        return value
    return str(value)


def _manifest_to_markdown(manifest: Mapping[str, object]) -> str:
    lines = [
        "# Current Capability Certification Manifest",
        "",
        f"- Status: `{manifest['status']}`",
        f"- Certification key: `{manifest['certification_key']}`",
        f"- Generated at: `{manifest['generated_at']}`",
        f"- DB URL: `{manifest['db_url']}`",
        f"- OpenAI mode: `{manifest['openai_mode']}`",
        f"- Scenario count: `{manifest['scenario_count']}`",
        f"- Passed scenarios: `{manifest['passed_scenarios']}`",
        f"- Failed scenarios: `{manifest['failed_scenarios']}`",
        "",
        "## Scenario Results",
        "",
        "| Scenario | Label | Status | Run IDs | Edge IDs | Bundle | Invariants (pass/fail) |",
        "| --- | --- | --- | --- | --- | --- | --- |",
    ]
    for scenario in manifest["scenarios"]:
        run_ids = scenario.get("run_ids") or {}
        run_id_text = ", ".join(
            f"{key}={value}" for key, value in run_ids.items()
        ) or "-"
        edge_ids = ", ".join(str(item) for item in (scenario.get("edge_execution_ids") or [])) or "-"
        bundle = scenario.get("output_bundle_path") or "-"
        summary = scenario.get("invariant_summary") or {}
        inv_text = f"{summary.get('passed', 0)}/{summary.get('failed', 0)}"
        lines.append(
            "| {scenario_id} | {label} | {status} | {run_ids} | {edge_ids} | {bundle} | {inv_text} |".format(
                scenario_id=scenario["scenario_id"],
                label=scenario["scenario_label"],
                status=scenario["status"],
                run_ids=run_id_text,
                edge_ids=edge_ids,
                bundle=bundle,
                inv_text=inv_text,
            )
        )

    lines.extend(["", "## Notes", ""])
    if manifest.get("status") == "passed":
        lines.append("- All certified scenarios passed their invariant checks.")
    else:
        lines.append("- One or more certified scenarios failed. Inspect `certification_manifest.json` for details.")
    return "\n".join(lines) + "\n"
