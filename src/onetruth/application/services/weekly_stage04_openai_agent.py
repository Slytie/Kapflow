from __future__ import annotations

from copy import deepcopy
import json
import os
from pathlib import Path
import sqlite3
from typing import Any

from onetruth.application.handlers.schedule_control import persist_weekly_stage04_output_payloads
from onetruth.application.handlers.workflow_task_lifecycle import (
    CommandError,
    complete_tool_execution_command,
    create_execution_session_command,
    evaluate_policy_decision_command,
    request_tool_execution_command,
    transition_execution_session_state_command,
)
from onetruth.application.services.execution_evidence import (
    EXECUTION_TRACE_ARTIFACT_KIND,
    RUNTIME_CONTEXT_PACK_ARTIFACT_KIND,
    RUNTIME_TOOL_REQUEST_ARTIFACT_KIND,
    RUNTIME_TOOL_RESULT_ARTIFACT_KIND,
    persist_prepared_execution_evidence_artifacts,
    prepare_execution_trace_artifact,
    prepare_pinned_execution_semantics_artifacts,
    prepare_runtime_json_evidence_artifact,
    prepare_runtime_turn_evidence_artifact,
    resolve_execution_artifact_root,
    stable_execution_id,
)
from onetruth.application.services.schedule_control import (
    PartialWeeklyScheduleState,
    build_stage04_deterministic_outputs,
    build_weekly_schedule_control_bundle,
    execute_next_weekly_allocation_iteration,
    expand_route_slot_requirements,
)
from onetruth.application.services.schedule_control.stage04_input_registry import (
    resolve_weekly_stage04_input_artifacts,
)
from onetruth.infrastructure.definitions.control_layer import (
    compile_control_layer,
    derive_execution_session_payload,
    resolve_stage_execution_spec,
)
from onetruth.infrastructure.repositories.artifact_versions import (
    list_artifact_versions_for_workflow_run,
)
from onetruth.infrastructure.repositories.execution_sessions import get_execution_session
from onetruth.infrastructure.repositories.human_tasks import get_human_task
from onetruth.infrastructure.repositories.task_runs import get_task_run
from onetruth.infrastructure.repositories.workflow_runs import get_workflow_run
from onetruth.integrations.openai import (
    OpenAIResponsesFunctionCallingRunner,
    ResponsesFunctionToolSpec,
    build_openai_function_calling_runner_from_env,
)


WEEKLY_STAGE04_WORKFLOW_ID = "weekly_schedule_planning.v1"
WEEKLY_STAGE04_MODULE_ID = "weekly_schedule_planning"
WEEKLY_STAGE04_STAGE_ID = "Stage04"
WEEKLY_STAGE04_TASK_KIND = "work_item"
OPENAI_TOOL_CLASS = "model.openai.responses.weekly.stage04.agent_runtime"
STAGE04_ALLOWED_ROLES = {"schedule_planner", "operations_manager", "system_worker"}

_REPO_ROOT = Path(__file__).resolve().parents[4]
_FAMILY_PATH = _REPO_ROOT / "docs/workflows/logistics_ops_family/v1/WORKFLOW_FAMILY.yaml"
_TRANSFORMS_PATH = _REPO_ROOT / "docs/workflows/logistics_ops_family/v1/PARTITION_TRANSFORMS.yaml"
_METHOD_PACKAGES_PATH = _REPO_ROOT / "docs/workflows/logistics_ops_family/v1/METHOD_PACKAGES.yaml"


def run_weekly_stage04_openai_agent(
    connection: sqlite3.Connection,
    payload: dict[str, Any],
    *,
    runner: OpenAIResponsesFunctionCallingRunner | None = None,
) -> dict[str, Any]:
    _require_fields(
        payload,
        ["human_task_id", "actor_id", "actor_type", "idempotency_key"],
    )
    human_task_id = str(payload["human_task_id"])
    actor_id = str(payload["actor_id"])
    actor_type = str(payload["actor_type"])
    actor_roles = _normalize_actor_roles(payload.get("actor_roles"))
    base_idempotency_key = str(payload["idempotency_key"])

    human_task = get_human_task(connection, human_task_id)
    if human_task is None:
        raise CommandError(
            code="human_task_not_found",
            message="human task not found",
            details={"human_task_id": human_task_id},
        )
    task_run = get_task_run(connection, str(human_task["task_run_id"]))
    if task_run is None:
        raise CommandError(
            code="task_run_not_found",
            message="task run not found for human task",
            details={"human_task_id": human_task_id, "task_run_id": str(human_task["task_run_id"])},
        )
    workflow_run = get_workflow_run(connection, str(human_task["workflow_run_id"]))
    if workflow_run is None:
        raise CommandError(
            code="workflow_run_not_found",
            message="workflow run not found for human task",
            details={"human_task_id": human_task_id, "workflow_run_id": str(human_task["workflow_run_id"])},
        )
    if str(workflow_run.get("workflow_id") or "") != WEEKLY_STAGE04_WORKFLOW_ID:
        raise CommandError(
            code="invalid_weekly_stage04_agent_workflow",
            message="weekly Stage04 OpenAI agent is only supported for weekly_schedule_planning.v1",
            details={
                "workflow_run_id": str(human_task["workflow_run_id"]),
                "workflow_id": str(workflow_run.get("workflow_id") or ""),
            },
        )
    if (
        str(task_run.get("stage_id") or "") != WEEKLY_STAGE04_STAGE_ID
        or str(task_run.get("task_kind") or "") != WEEKLY_STAGE04_TASK_KIND
    ):
        raise CommandError(
            code="invalid_weekly_stage04_agent_task",
            message="weekly Stage04 OpenAI agent is only allowed for Stage04 work_item tasks",
            details={
                "human_task_id": human_task_id,
                "stage_id": str(task_run.get("stage_id") or ""),
                "task_kind": str(task_run.get("task_kind") or ""),
            },
        )
    if str(human_task.get("state") or "") != "CLAIMED":
        raise CommandError(
            code="task_not_completable",
            message="human task must be claimed before weekly Stage04 agent execution",
            details={"human_task_id": human_task_id, "state": str(human_task.get("state") or "")},
        )
    if str(human_task.get("assignee_actor_id") or "") != actor_id:
        raise CommandError(
            code="task_not_completable",
            message="human task must be claimed by requesting actor",
            details={
                "human_task_id": human_task_id,
                "assignee_actor_id": str(human_task.get("assignee_actor_id") or ""),
                "actor_id": actor_id,
            },
        )

    execution_session_id = stable_execution_id(
        prefix="xs",
        raw=f"{human_task['workflow_run_id']}:{human_task['task_run_id']}:{base_idempotency_key}",
    )
    tool_execution_id = stable_execution_id(
        prefix="tx",
        raw=f"{execution_session_id}:{OPENAI_TOOL_CLASS}:{base_idempotency_key}",
    )
    policy_decision_id = stable_execution_id(
        prefix="pd",
        raw=f"{tool_execution_id}:{base_idempotency_key}",
    )
    existing_session = get_execution_session(connection, execution_session_id)
    if existing_session is not None:
        raise CommandError(
            code="duplicate_execution_request",
            message="execution session already exists for idempotent Stage04 agent request",
            details={
                "execution_session_id": execution_session_id,
                "state": str(existing_session.get("state") or ""),
            },
        )

    compiled_control = _compile_logistics_control()
    stage_spec = resolve_stage_execution_spec(
        compiled_control=compiled_control,
        module_id=WEEKLY_STAGE04_MODULE_ID,
        stage_id=WEEKLY_STAGE04_STAGE_ID,
    )
    execution_session_payload = derive_execution_session_payload(
        compiled_control=compiled_control,
        module_id=WEEKLY_STAGE04_MODULE_ID,
        stage_id=WEEKLY_STAGE04_STAGE_ID,
        workflow_run_id=str(human_task["workflow_run_id"]),
        task_run_id=str(human_task["task_run_id"]),
        principal_actor={"type": actor_type, "id": actor_id},
        idempotency_key=f"{base_idempotency_key}:execution-session",
        state="WAITING_POLICY",
        execution_session_id=execution_session_id,
        actor_type=actor_type,
        actor_id=actor_id,
    )
    execution_session = create_execution_session_command(connection, execution_session_payload)
    tool_execution = request_tool_execution_command(
        connection,
        {
            "tool_execution_id": tool_execution_id,
            "execution_session_id": execution_session_id,
            "tool_class": OPENAI_TOOL_CLASS,
            "tool_name": "weekly_stage04_openai_agent",
            "idempotency_key": f"{base_idempotency_key}:tool-request",
            "actor_id": actor_id,
            "actor_type": actor_type,
        },
    )

    decision, reason_code, required_approval_action = _evaluate_weekly_stage04_policy(
        actor_type=actor_type,
        actor_roles=actor_roles,
        payload=payload,
    )
    policy_result = evaluate_policy_decision_command(
        connection,
        {
            "policy_decision_id": policy_decision_id,
            "tool_execution_id": tool_execution_id,
            "decision": decision,
            "reason_code": reason_code,
            "required_approval_action": required_approval_action,
            "principal_actor": {"type": actor_type, "id": actor_id},
            "idempotency_key": f"{base_idempotency_key}:policy-eval",
        },
    )
    policy_decision = policy_result["policy_decision"]
    tool_execution = policy_result["tool_execution"]
    execution_session = policy_result["execution_session"]
    artifact_root = resolve_execution_artifact_root()
    execution_semantics_evidence = persist_prepared_execution_evidence_artifacts(
        connection=connection,
        workflow_run_id=str(human_task["workflow_run_id"]),
        task_run_id=str(human_task["task_run_id"]),
        actor_id=actor_id,
        actor_type=actor_type,
        idempotency_prefix=f"{base_idempotency_key}:execution-semantics",
        artifacts=prepare_pinned_execution_semantics_artifacts(
            workflow_run_id=str(human_task["workflow_run_id"]),
            task_run_id=str(human_task["task_run_id"]),
            execution_session=execution_session,
            tool_execution=tool_execution,
            policy_decision=policy_decision,
            execution_semantics=execution_session_payload.get("execution_semantics"),
        ),
        storage_root=artifact_root,
    )
    if decision != "allow":
        code = "tool_execution_requires_approval" if decision == "require_approval" else "tool_execution_denied"
        raise CommandError(
            code=code,
            message="policy denied weekly Stage04 agent model execution",
            details={
                "execution_session_id": execution_session_id,
                "tool_execution_id": tool_execution_id,
                "policy_decision_id": policy_decision_id,
                "decision": decision,
                "reason_code": reason_code,
                "required_approval_action": required_approval_action,
                "execution_semantics_evidence_artifact_ids": [
                    str(item["artifact_version_id"]) for item in execution_semantics_evidence
                ],
            },
        )

    stage04_inputs = _resolve_stage04_input_artifacts(
        artifacts=list_artifact_versions_for_workflow_run(connection, str(human_task["workflow_run_id"])),
        stage_spec=stage_spec,
    )
    bundle = build_weekly_schedule_control_bundle(
        workflow_run=workflow_run,
        route_slot_requirements_artifact=stage04_inputs["route_slot_requirements"],
        driver_capabilities_artifact=stage04_inputs["driver_capabilities"],
        approved_availability_artifact=stage04_inputs.get("approved_availability"),
        actual_hours_artifact=stage04_inputs.get("actual_hours"),
        route_horizon_artifact=stage04_inputs.get("route_horizon"),
    )
    context_pack = _build_context_pack(
        workflow_run=workflow_run,
        task_run=task_run,
        human_task=human_task,
        stage_spec=stage_spec,
        bundle=bundle,
        input_artifacts=stage04_inputs,
    )
    tool_specs = _stage04_tool_specs(stage_spec)
    tooling = _Stage04DeterministicTooling(
        connection=connection,
        workflow_run=workflow_run,
        workflow_run_id=str(human_task["workflow_run_id"]),
        bundle=bundle,
        stage04_inputs=stage04_inputs,
        context_pack=context_pack,
        idempotency_prefix=f"{base_idempotency_key}:deterministic",
    )

    context_pack_artifact = persist_prepared_execution_evidence_artifacts(
        connection=connection,
        workflow_run_id=str(human_task["workflow_run_id"]),
        task_run_id=str(human_task["task_run_id"]),
        actor_id=actor_id,
        actor_type=actor_type,
        idempotency_prefix=f"{base_idempotency_key}:runtime-evidence",
        artifacts=[
            prepare_runtime_json_evidence_artifact(
                artifact_kind=RUNTIME_CONTEXT_PACK_ARTIFACT_KIND,
                file_name=f"runtime-context-pack-{execution_session_id}.json",
                execution_session_id=execution_session_id,
                tool_execution_id=tool_execution_id,
                policy_decision_id=policy_decision_id,
                relation_kind="stage04_context_pack",
                payload_json=context_pack,
                idempotency_suffix="context-pack",
            )
        ],
        storage_root=artifact_root,
    )[0]

    stop_policy = _stage04_stop_policy_from_stage_spec(stage_spec)
    runtime_evidence_artifacts: list[dict[str, Any]] = []
    runtime_turn_evidence: list[dict[str, Any]] = []
    agent_result: Any | None = None
    stage04_build_result: dict[str, Any] | None = None

    def _persist_turn_evidence(turn: Any) -> None:
        request_artifact, result_artifact = persist_prepared_execution_evidence_artifacts(
            connection=connection,
            workflow_run_id=str(human_task["workflow_run_id"]),
            task_run_id=str(human_task["task_run_id"]),
            actor_id=actor_id,
            actor_type=actor_type,
            idempotency_prefix=f"{base_idempotency_key}:runtime-evidence",
            artifacts=[
                prepare_runtime_turn_evidence_artifact(
                    artifact_kind=RUNTIME_TOOL_REQUEST_ARTIFACT_KIND,
                    execution_session_id=execution_session_id,
                    turn_index=int(turn.turn_index),
                    payload_json=_build_turn_request_payload(
                        execution_session_id=execution_session_id,
                        turn=turn,
                    ),
                    idempotency_suffix_prefix="tool-request",
                    relation_kind="stage04_tool_request_turn",
                    file_stem="runtime-tool-request",
                    tool_execution_id=tool_execution_id,
                    policy_decision_id=policy_decision_id,
                    extra_metadata={
                        "progress_made": bool(turn.progress_made),
                        "no_progress_streak": int(turn.no_progress_streak),
                    },
                ),
                prepare_runtime_turn_evidence_artifact(
                    artifact_kind=RUNTIME_TOOL_RESULT_ARTIFACT_KIND,
                    execution_session_id=execution_session_id,
                    turn_index=int(turn.turn_index),
                    payload_json=_build_turn_result_payload(
                        execution_session_id=execution_session_id,
                        turn=turn,
                        tooling=tooling,
                    ),
                    idempotency_suffix_prefix="tool-result",
                    relation_kind="stage04_tool_result_turn",
                    file_stem="runtime-tool-result",
                    tool_execution_id=tool_execution_id,
                    policy_decision_id=policy_decision_id,
                    extra_metadata={
                        "progress_made": bool(turn.progress_made),
                        "no_progress_streak": int(turn.no_progress_streak),
                        "planner_complete": bool(tooling.planner_complete()),
                    },
                ),
            ],
            storage_root=artifact_root,
        )
        runtime_evidence_artifacts.extend([request_artifact, result_artifact])
        runtime_turn_evidence.append(
            {
                "turn_index": int(turn.turn_index),
                "progress_made": bool(turn.progress_made),
                "no_progress_streak": int(turn.no_progress_streak),
                "request_artifact_version_id": str(request_artifact["artifact_version_id"]),
                "result_artifact_version_id": str(result_artifact["artifact_version_id"]),
            }
        )

    try:
        selected_runner = runner or build_weekly_stage04_openai_agent_runner_from_env()
        agent_result = selected_runner.run_function_calling_loop(
            initial_input=_initial_model_input(context_pack=context_pack, stage_spec=stage_spec),
            tools=tool_specs,
            execute_function=tooling.execute,
            max_turns=int(stop_policy["max_tool_calls"]),
            no_progress_limit=int(stop_policy["no_progress_ticks"]),
            on_turn_complete=_persist_turn_evidence,
        )
        stage04_build_result = tooling.finalized_build_result()
        if stage04_build_result is None:
            raise CommandError(
                code="stage04_finalize_required",
                message="weekly Stage04 run must explicitly call finalize_weekly_stage04_draft_outputs before completion",
                details={
                    "execution_session_id": execution_session_id,
                    "remaining_route_slots": tooling.remaining_route_slot_ids(),
                    "planner_complete": tooling.planner_complete(),
                },
            )

        trace_artifact = _persist_stage04_execution_trace(
            connection=connection,
            workflow_run_id=str(human_task["workflow_run_id"]),
            task_run_id=str(human_task["task_run_id"]),
            actor_id=actor_id,
            actor_type=actor_type,
            idempotency_prefix=f"{base_idempotency_key}:runtime-evidence",
            storage_root=artifact_root,
            execution_session_id=execution_session_id,
            tool_execution_id=tool_execution_id,
            policy_decision_id=policy_decision_id,
            context_pack_artifact=context_pack_artifact,
            runtime_turn_evidence=runtime_turn_evidence,
            planner_state=tooling.planner_state_snapshot(),
            agent_result=agent_result.as_dict(),
            stage04_build_result=stage04_build_result,
            execution_outcome="succeeded",
        )
        runtime_evidence_artifacts.append(trace_artifact)
    except Exception as exc:
        try:
            trace_artifact = _persist_stage04_execution_trace(
                connection=connection,
                workflow_run_id=str(human_task["workflow_run_id"]),
                task_run_id=str(human_task["task_run_id"]),
                actor_id=actor_id,
                actor_type=actor_type,
                idempotency_prefix=f"{base_idempotency_key}:runtime-evidence",
                storage_root=artifact_root,
                execution_session_id=execution_session_id,
                tool_execution_id=tool_execution_id,
                policy_decision_id=policy_decision_id,
                context_pack_artifact=context_pack_artifact,
                runtime_turn_evidence=runtime_turn_evidence,
                planner_state=tooling.planner_state_snapshot(),
                agent_result=agent_result.as_dict() if agent_result is not None else None,
                stage04_build_result=stage04_build_result,
                execution_outcome="failed",
                error_code=str(getattr(exc, "code", exc.__class__.__name__)),
            )
            runtime_evidence_artifacts.append(trace_artifact)
        except Exception:
            pass
        _record_tool_and_session_failure(
            connection=connection,
            tool_execution_id=tool_execution_id,
            execution_session_id=execution_session_id,
            actor_id=actor_id,
            actor_type=actor_type,
            idempotency_base=base_idempotency_key,
            error_code=str(getattr(exc, "code", exc.__class__.__name__)),
        )
        raise

    runtime_evidence_ids = [str(context_pack_artifact["artifact_version_id"])]
    runtime_evidence_ids.extend(
        str(item["artifact_version_id"]) for item in runtime_evidence_artifacts
    )
    assert stage04_build_result is not None
    stage04_output_artifact_ids = [
        str(artifact.get("artifact_version_id") or "")
        for artifact in stage04_build_result["artifacts"].values()
        if str(artifact.get("artifact_version_id") or "").strip()
    ]
    tool_execution = complete_tool_execution_command(
        connection,
        {
            "tool_execution_id": tool_execution_id,
            "result": "succeeded",
            "output_artifact_version_ids": [*runtime_evidence_ids, *stage04_output_artifact_ids],
            "idempotency_key": f"{base_idempotency_key}:tool-complete",
            "actor_id": actor_id,
            "actor_type": actor_type,
        },
    )
    execution_session = transition_execution_session_state_command(
        connection,
        {
            "execution_session_id": execution_session_id,
            "to_state": "SUCCEEDED",
            "reason": "stage04_agent_completed",
            "idempotency_key": f"{base_idempotency_key}:session-succeeded",
            "actor_id": actor_id,
            "actor_type": actor_type,
        },
    )
    return {
        "execution_session": execution_session,
        "tool_execution": tool_execution,
        "policy_decision": policy_decision,
        "execution_semantics_evidence": execution_semantics_evidence,
        "context_pack_artifact": context_pack_artifact,
        "runtime_evidence_artifacts": runtime_evidence_artifacts,
        "runtime_turn_evidence": runtime_turn_evidence,
        "agent_result": agent_result.as_dict(),
        "stage04_build_result": stage04_build_result,
    }


def build_weekly_stage04_openai_agent_runner_from_env() -> OpenAIResponsesFunctionCallingRunner:
    return build_openai_function_calling_runner_from_env()


def evaluate_weekly_stage04_policy_for_actor(
    *,
    actor_type: str,
    actor_roles: list[str] | tuple[str, ...],
    policy_decision_override: str | None = None,
) -> tuple[str, str | None, str | None]:
    payload: dict[str, Any] = {}
    if policy_decision_override is not None:
        payload["policy_decision"] = policy_decision_override
    return _evaluate_weekly_stage04_policy(
        actor_type=actor_type,
        actor_roles=[str(role) for role in actor_roles],
        payload=payload,
    )


def _compile_logistics_control() -> dict[str, Any]:
    return compile_control_layer(
        repo_root=_REPO_ROOT,
        family_path=_FAMILY_PATH,
        partition_transforms_path=_TRANSFORMS_PATH,
        method_packages_path=_METHOD_PACKAGES_PATH,
    )


def _stage04_tool_specs(stage_spec: dict[str, Any]) -> list[ResponsesFunctionToolSpec]:
    allowed_classes = _allowed_tool_classes(stage_spec)
    catalog = [
        (
            "get_stage04_context",
            "artifact.read",
            "Return compiled Stage04 context, planner progress, and deterministic guardrails.",
            {
                "type": "object",
                "additionalProperties": False,
                "properties": {},
                "required": [],
            },
        ),
        (
            "preview_stage04_next_iteration",
            "spreadsheet.transform",
            "Preview the next deterministic Stage04 allocation iteration without mutating planner state.",
            {
                "type": "object",
                "additionalProperties": False,
                "properties": {},
                "required": [],
            },
        ),
        (
            "apply_stage04_next_iteration",
            "spreadsheet.transform",
            "Apply exactly one deterministic Stage04 allocation iteration, including bounded local repair when applicable.",
            {
                "type": "object",
                "additionalProperties": False,
                "properties": {},
                "required": [],
            },
        ),
        (
            "get_stage04_validation_summary",
            "validation",
            "Return the current deterministic Stage04 validation snapshot and finalize readiness.",
            {
                "type": "object",
                "additionalProperties": False,
                "properties": {},
                "required": [],
            },
        ),
        (
            "get_stage04_iteration_analysis",
            "projection.render",
            "Return deterministic iteration-level route allocation, repair, and tradeoff analysis.",
            {
                "type": "object",
                "additionalProperties": False,
                "properties": {
                    "iteration_index": {
                        "type": "integer",
                        "minimum": 1,
                    }
                },
                "required": [],
            },
        ),
        (
            "finalize_weekly_stage04_draft_outputs",
            "spreadsheet.transform",
            "Persist Stage04 draft artifacts from the current deterministic planner state after all iterations are complete.",
            {
                "type": "object",
                "additionalProperties": False,
                "properties": {},
                "required": [],
            },
        ),
    ]
    specs = [
        ResponsesFunctionToolSpec(
            name=name,
            description=description,
            parameters_schema=parameters_schema,
        )
        for name, tool_class, description, parameters_schema in catalog
        if tool_class in allowed_classes
    ]
    required_names = {
        "get_stage04_context",
        "preview_stage04_next_iteration",
        "apply_stage04_next_iteration",
        "get_stage04_validation_summary",
        "get_stage04_iteration_analysis",
        "finalize_weekly_stage04_draft_outputs",
    }
    present_names = {spec.name for spec in specs}
    if not required_names.issubset(present_names):
        raise CommandError(
            code="invalid_weekly_stage04_tool_profile",
            message="compiled Stage04 tool profile does not allow required deterministic tools",
            details={
                "required_tools": sorted(required_names),
                "present_tools": sorted(present_names),
                "allowed_tool_classes": sorted(allowed_classes),
            },
        )
    return specs


def _allowed_tool_classes(stage_spec: dict[str, Any]) -> set[str]:
    runtime_bindings = stage_spec.get("runtime_bindings")
    if not isinstance(runtime_bindings, dict):
        raise CommandError(
            code="invalid_weekly_stage04_control_spec",
            message="stage control metadata is missing runtime_bindings",
            details={},
        )
    tool_execution = runtime_bindings.get("tool_execution")
    if not isinstance(tool_execution, dict):
        raise CommandError(
            code="invalid_weekly_stage04_control_spec",
            message="stage control metadata is missing tool_execution bindings",
            details={},
        )
    allowed = tool_execution.get("allowed_tool_classes")
    if not isinstance(allowed, list):
        raise CommandError(
            code="invalid_weekly_stage04_control_spec",
            message="stage control metadata has invalid allowed_tool_classes",
            details={},
        )
    return {str(item) for item in allowed if str(item).strip()}


def _stage04_stop_policy_from_stage_spec(stage_spec: dict[str, Any]) -> dict[str, int | str]:
    runtime_bindings = stage_spec.get("runtime_bindings")
    execution_session = (
        runtime_bindings.get("execution_session")
        if isinstance(runtime_bindings, dict)
        else None
    )
    if isinstance(execution_session, dict):
        max_tool_calls = execution_session.get("max_tool_calls")
        no_progress_ticks = execution_session.get("no_progress_ticks")
        on_exhaustion = execution_session.get("on_exhaustion")
        if (
            isinstance(max_tool_calls, int)
            and max_tool_calls > 0
            and isinstance(no_progress_ticks, int)
            and no_progress_ticks >= 0
            and isinstance(on_exhaustion, str)
            and on_exhaustion.strip()
        ):
            return {
                "max_tool_calls": max_tool_calls,
                "no_progress_ticks": no_progress_ticks,
                "on_exhaustion": on_exhaustion,
            }

    method_pin = stage_spec.get("method_package_pin")
    stop_policy = method_pin.get("stop_policy") if isinstance(method_pin, dict) else None
    if not isinstance(stop_policy, dict):
        return {"max_tool_calls": 4, "no_progress_ticks": 2, "on_exhaustion": "escalate"}
    max_tool_calls = stop_policy.get("max_tool_calls")
    no_progress_ticks = stop_policy.get("no_progress_ticks")
    on_exhaustion = stop_policy.get("on_exhaustion")
    return {
        "max_tool_calls": max_tool_calls if isinstance(max_tool_calls, int) and max_tool_calls > 0 else 4,
        "no_progress_ticks": no_progress_ticks if isinstance(no_progress_ticks, int) and no_progress_ticks >= 0 else 2,
        "on_exhaustion": str(on_exhaustion or "escalate"),
    }


def _initial_model_input(
    *,
    context_pack: dict[str, Any],
    stage_spec: dict[str, Any],
) -> list[dict[str, Any]]:
    stop_policy = _stage04_stop_policy_from_stage_spec(stage_spec)
    system_prompt = (
        "You are a bounded Stage04 weekly scheduling agent for weekly_schedule_planning.v1. "
        "You may only use provided deterministic function tools. "
        "Never publish schedules, never perform Stage05/Stage06 actions, and never invent data. "
        "Preview or apply deterministic iterations, review validation/iteration analysis, "
        "and explicitly call finalize_weekly_stage04_draft_outputs before returning a final answer. "
        "A non-progress streak of "
        f"{int(stop_policy['no_progress_ticks'])} "
        "tool turns exhausts the run. "
        "When finished, return a concise JSON object with keys: "
        "summary, selected_candidate_count, recommended_action, warnings."
    )
    user_payload = {
        "task": "Orchestrate deterministic Stage04 iterations, then explicitly finalize draft outputs and return a review-ready summary.",
        "stage_control_digest": stage_spec.get("stage_control_digest"),
        "context_pack": context_pack,
    }
    return [
        {
            "role": "system",
            "content": [{"type": "input_text", "text": system_prompt}],
        },
        {
            "role": "user",
            "content": [{"type": "input_text", "text": json.dumps(user_payload, separators=(",", ":"))}],
        },
    ]


class _Stage04DeterministicTooling:
    def __init__(
        self,
        *,
        connection: sqlite3.Connection,
        workflow_run: dict[str, Any],
        workflow_run_id: str,
        bundle: Any,
        stage04_inputs: dict[str, dict[str, Any] | None],
        context_pack: dict[str, Any],
        idempotency_prefix: str,
    ) -> None:
        self.connection = connection
        self.workflow_run = workflow_run
        self.workflow_run_id = workflow_run_id
        self.bundle = bundle
        self.stage04_inputs = stage04_inputs
        self.context_pack = context_pack
        self.idempotency_prefix = idempotency_prefix
        self.schedule_state = PartialWeeklyScheduleState.from_route_slots(
            expand_route_slot_requirements(bundle.route_slots)
        )
        self.candidate_matrix: list[Any] = []
        self._applied_iterations: list[dict[str, Any]] = []
        self._cached_finalized_build_result: dict[str, Any] | None = None

    def execute(self, function_name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        if function_name == "get_stage04_context":
            return {
                "progress_made": False,
                "planner_complete": self.planner_complete(),
                "bundle_summary": self.context_pack["bundle_summary"],
                "input_artifacts": self.context_pack["input_artifacts"],
                "deterministic_guardrails": self.context_pack["deterministic_guardrails"],
                "planner_state": self.planner_state_snapshot(),
            }
        if function_name == "preview_stage04_next_iteration":
            preview = self.preview_next_iteration()
            return {
                "progress_made": False,
                "planner_complete": self.planner_complete(),
                "planner_state": self.planner_state_snapshot(),
                "iteration_preview": preview,
            }
        if function_name == "apply_stage04_next_iteration":
            return self.apply_next_iteration()
        if function_name == "get_stage04_validation_summary":
            return {
                "progress_made": False,
                "planner_complete": self.planner_complete(),
                "planner_state": self.planner_state_snapshot(),
                "validation_summary": self.validation_snapshot(),
            }
        if function_name == "get_stage04_iteration_analysis":
            requested_iteration = arguments.get("iteration_index")
            return {
                "progress_made": False,
                "planner_complete": self.planner_complete(),
                "planner_state": self.planner_state_snapshot(),
                "iteration_analysis": self.iteration_analysis(requested_iteration),
            }
        if function_name == "finalize_weekly_stage04_draft_outputs":
            return self.finalize_outputs()
        raise CommandError(
            code="unsupported_weekly_stage04_tool",
            message="tool is not supported in weekly Stage04 deterministic toolset",
            details={"function_name": function_name},
        )

    def planner_complete(self) -> bool:
        return self._preview_iteration_result() is None

    def remaining_route_slot_ids(self) -> list[str]:
        return [item.route_slot_id for item in self.schedule_state.remaining_route_slots()]

    def planner_state_snapshot(self) -> dict[str, Any]:
        coverage_summary = self._coverage_summary()
        return {
            "bundle_id": getattr(self.bundle, "bundle_id"),
            "iteration_count": len(self.schedule_state.iteration_summaries),
            "candidate_evaluation_count": len(self.candidate_matrix),
            "planner_complete": self.planner_complete(),
            "finalized": self._cached_finalized_build_result is not None,
            "assigned_route_slots": int(coverage_summary.get("assigned_route_slots") or 0),
            "uncovered_route_slots": int(coverage_summary.get("uncovered_route_slots") or 0),
            "pending_route_slots": int(coverage_summary.get("pending_route_slots") or 0),
            "remaining_route_slot_ids": coverage_summary.get("pending_route_slot_ids") or [],
        }

    def preview_next_iteration(self) -> dict[str, Any]:
        preview = self._preview_iteration_result()
        if preview is None:
            return {
                "planner_complete": True,
                "message": "No further deterministic baseline or improvement moves remain; finalize is available.",
            }
        return self._iteration_payload(preview, preview_only=True)

    def apply_next_iteration(self) -> dict[str, Any]:
        result = execute_next_weekly_allocation_iteration(
            bundle=self.bundle,
            schedule_state=self.schedule_state,
            candidate_matrix=self.candidate_matrix,
        )
        if result is None:
            return {
                "progress_made": False,
                "planner_complete": True,
                "planner_state": self.planner_state_snapshot(),
                "message": "No further deterministic baseline or improvement moves remain; finalize is available.",
            }
        iteration_payload = self._iteration_payload(result, preview_only=False)
        self._applied_iterations.append(iteration_payload)
        return {
            "progress_made": True,
            "planner_complete": self.planner_complete(),
            "planner_state": self.planner_state_snapshot(),
            "iteration_result": iteration_payload,
        }

    def validation_snapshot(self) -> dict[str, Any]:
        build_result = self._render_current_outputs()
        validation = dict(build_result["artifact_payloads"]["planning.validation_summary.doc"])
        summary = (
            dict(validation.get("summary"))
            if isinstance(validation.get("summary"), dict)
            else {}
        )
        if not self.planner_complete():
            summary["hard_rule_result"] = "in_progress"
            summary["recommended_action"] = "continue_stage04_iteration"
            warnings = list(summary.get("warnings") or [])
            warnings.append(
                f"{len(self.remaining_route_slot_ids())} route slots remain unresolved in the deterministic planner."
            )
            summary["warnings"] = warnings
        summary["planner_complete"] = self.planner_complete()
        summary["finalize_available"] = self.planner_complete()
        validation["summary"] = summary
        validation["planner_state"] = self.planner_state_snapshot()
        validation["latest_iteration_index"] = len(self.schedule_state.iteration_summaries)
        return validation

    def iteration_analysis(self, requested_iteration: Any) -> dict[str, Any]:
        if not self._applied_iterations:
            return {
                "available_iteration_indices": [],
                "message": "No Stage04 iterations have been applied yet.",
            }
        if requested_iteration is None:
            return self._applied_iterations[-1]
        try:
            iteration_index = int(requested_iteration)
        except (TypeError, ValueError) as exc:
            raise CommandError(
                code="invalid_stage04_iteration_request",
                message="iteration_index must be an integer",
                details={"iteration_index": requested_iteration},
            ) from exc
        for payload in self._applied_iterations:
            if int(payload["iteration_index"]) == iteration_index:
                return payload
        raise CommandError(
            code="stage04_iteration_not_found",
            message="requested Stage04 iteration analysis is not available",
            details={
                "iteration_index": iteration_index,
                "available_iteration_indices": [
                    int(item["iteration_index"]) for item in self._applied_iterations
                ],
            },
        )

    def finalize_outputs(self) -> dict[str, Any]:
        if self._cached_finalized_build_result is not None:
            return {
                "progress_made": False,
                "planner_complete": True,
                "planner_state": self.planner_state_snapshot(),
                "stage04_build_result": self._build_result_summary(self._cached_finalized_build_result),
            }
        if not self.planner_complete():
            return {
                "progress_made": False,
                "planner_complete": False,
                "planner_state": self.planner_state_snapshot(),
                "finalize_blocked_reason": "planner_incomplete",
                "remaining_route_slot_ids": self.remaining_route_slot_ids(),
            }
        build_result = self._render_current_outputs()
        self._cached_finalized_build_result = self._persist_outputs(build_result)
        return {
            "progress_made": True,
            "planner_complete": True,
            "planner_state": self.planner_state_snapshot(),
            "stage04_build_result": self._build_result_summary(self._cached_finalized_build_result),
        }

    def finalized_build_result(self) -> dict[str, Any] | None:
        return self._cached_finalized_build_result

    def _render_current_outputs(self) -> dict[str, Any]:
        rendered = build_stage04_deterministic_outputs(
            bundle=self.bundle,
            candidate_matrix=list(self.candidate_matrix),
            selected_candidates=[item.to_row() for item in self.schedule_state.final_decisions()],
            iteration_summaries=list(self.schedule_state.iteration_summaries),
            repair_moves=list(self.schedule_state.repair_moves),
            coverage_summary=self._coverage_summary(),
        )
        return {
            "bundle_id": rendered.bundle.bundle_id,
            "candidate_count": len(rendered.candidate_matrix),
            "selected_candidate_count": len(rendered.selected_candidates),
            "selected_candidates": rendered.selected_candidates,
            "iteration_summaries": rendered.iteration_summaries,
            "repair_moves": rendered.repair_moves,
            "coverage_summary": rendered.coverage_summary,
            "artifact_payloads": {
                "planning.input_bundle.doc": rendered.input_bundle_payload,
                "planning.candidate_schedule_delta.workbook": rendered.candidate_delta_payload,
                "planning.validation_summary.doc": rendered.validation_summary_payload,
                "planning.draft_weekly_schedule.workbook": rendered.draft_workbook_payload,
                "planning.draft_weekly_schedule.doc": rendered.draft_doc_payload,
            },
        }

    def _persist_outputs(self, build_result: dict[str, Any]) -> dict[str, Any]:
        artifacts = persist_weekly_stage04_output_payloads(
            self.connection,
            workflow_run=self.workflow_run,
            bundle_id=str(build_result["bundle_id"]),
            output_payloads=dict(build_result["artifact_payloads"]),
            source_input_ids=self._source_input_artifact_ids(),
        )
        return {
            **build_result,
            "artifacts": {
                "input_bundle": artifacts["planning.input_bundle.doc"],
                "candidate_delta": artifacts["planning.candidate_schedule_delta.workbook"],
                "validation_summary": artifacts["planning.validation_summary.doc"],
                "draft_workbook": artifacts["planning.draft_weekly_schedule.workbook"],
                "draft_doc": artifacts["planning.draft_weekly_schedule.doc"],
            },
        }

    def _source_input_artifact_ids(self) -> list[str]:
        artifact_ids: list[str] = []
        for artifact in self.stage04_inputs.values():
            if not isinstance(artifact, dict):
                continue
            artifact_id = str(artifact.get("artifact_version_id") or "")
            if artifact_id:
                artifact_ids.append(artifact_id)
        return artifact_ids

    def _coverage_summary(self) -> dict[str, Any]:
        pending_route_slot_ids = self.remaining_route_slot_ids()
        uncovered_route_slot_ids = [
            *self.schedule_state.uncovered_route_slot_ids(),
            *pending_route_slot_ids,
        ]
        batch_sizes = [item.batch_size for item in self.schedule_state.iteration_summaries]
        repaired_route_slot_ids = {
            route_slot_id
            for move in self.schedule_state.repair_moves
            for route_slot_id in (move.filled_route_slot_id, move.reassigned_route_slot_id)
        }
        return {
            "total_route_slots": len(self.schedule_state.ordered_route_slot_ids),
            "decided_route_slots": len(self.schedule_state.final_decisions()),
            "pending_route_slots": len(pending_route_slot_ids),
            "pending_route_slot_ids": pending_route_slot_ids,
            "assigned_route_slots": self.schedule_state.assigned_count(),
            "uncovered_route_slots": len(uncovered_route_slot_ids),
            "uncovered_route_slot_ids": uncovered_route_slot_ids,
            "iteration_count": len(self.schedule_state.iteration_summaries),
            "batch_size_min": min(batch_sizes) if batch_sizes else 0,
            "batch_size_max": max(batch_sizes) if batch_sizes else 0,
            "repair_move_count": len(self.schedule_state.repair_moves),
            "reallocation_move_count": len(self.schedule_state.repair_moves),
            "repaired_route_slot_count": len(repaired_route_slot_ids),
            "local_repair_posture": "bounded_local_reallocation",
            "phase_counts": {
                "baseline": sum(
                    1 for item in self.schedule_state.iteration_summaries if item.phase == "baseline"
                ),
                "improvement": sum(
                    1
                    for item in self.schedule_state.iteration_summaries
                    if item.phase == "improvement"
                ),
            },
        }

    def _iteration_payload(self, result: Any, *, preview_only: bool) -> dict[str, Any]:
        route_allocations = [
            item.to_row() for item in sorted(result.applied_decisions, key=lambda row: row.route_slot_id)
        ]
        tradeoffs = [
            f"{row['route_slot_id']} -> {row['candidate_driver_id'] or 'unassigned'} ({row['rationale_code']})"
            for row in route_allocations
            if row["assignment_action"] != "unassigned"
        ]
        tradeoffs.extend(
            f"{move.filled_route_slot_id} repaired via {move.replacement_driver_id} ({move.repair_reason})"
            for move in result.repair_moves
        )
        return {
            "iteration_index": int(result.iteration_index),
            "phase": str(result.phase),
            "batch_id": str(result.batch_id),
            "pressure_group_id": str(result.pressure_group_id),
            "pressure_service_date": str(result.pressure_service_date),
            "pressure_station_code": str(result.pressure_station_code),
            "pressure_service_area": str(result.pressure_service_area),
            "preview_only": preview_only,
            "candidate_evaluation_count": len(result.candidate_evaluations),
            "route_allocations": route_allocations,
            "assigned_route_slot_ids": list(result.summary.assigned_route_slot_ids),
            "uncovered_route_slot_ids": list(result.summary.uncovered_route_slot_ids),
            "moved_route_slot_ids": list(result.summary.moved_route_slot_ids),
            "repair_moves": [item.to_payload() for item in result.repair_moves],
            "coverage_summary_after_iteration": dict(result.coverage_summary),
            "soft_objective_delta": float(result.summary.soft_objective_delta),
            "stability_delta": float(result.summary.stability_delta),
            "target_shift_gap_delta": float(result.summary.target_shift_gap_delta),
            "preference_fit_delta": float(result.summary.preference_fit_delta),
            "accepted_move_reasons": list(result.summary.accepted_move_reasons),
            "rejected_move_reasons": list(result.rejected_move_reasons),
            "tradeoffs": tradeoffs,
        }

    def _build_result_summary(self, build_result: dict[str, Any]) -> dict[str, Any]:
        return {
            "bundle_id": build_result["bundle_id"],
            "candidate_count": build_result["candidate_count"],
            "selected_candidate_count": build_result["selected_candidate_count"],
            "coverage_summary": build_result["coverage_summary"],
            "selected_candidates": build_result["selected_candidates"],
            "artifacts": {
                key: {
                    "artifact_version_id": value["artifact_version_id"],
                    "artifact_kind": value["artifact_kind"],
                }
                for key, value in build_result["artifacts"].items()
            },
        }

    def _preview_iteration_result(self) -> Any | None:
        preview_state = deepcopy(self.schedule_state)
        preview_candidates = list(self.candidate_matrix)
        return execute_next_weekly_allocation_iteration(
            bundle=self.bundle,
            schedule_state=preview_state,
            candidate_matrix=preview_candidates,
        )


def _build_turn_request_payload(
    *,
    execution_session_id: str,
    turn: Any,
) -> dict[str, Any]:
    return {
        "schema_version": "1.0",
        "kind": "runtime_tool_request_turn",
        "execution_session_id": execution_session_id,
        "turn_index": int(turn.turn_index),
        "request_payload": turn.request_payload,
        "request_id": turn.request_id,
        "response_id": turn.response_id,
        "model": turn.model,
        "usage": turn.usage,
        "requested_function_names": [item.name for item in turn.function_calls],
    }


def _build_turn_result_payload(
    *,
    execution_session_id: str,
    turn: Any,
    tooling: _Stage04DeterministicTooling,
) -> dict[str, Any]:
    return {
        "schema_version": "1.0",
        "kind": "runtime_tool_result_turn",
        "execution_session_id": execution_session_id,
        "turn_index": int(turn.turn_index),
        "progress_made": bool(turn.progress_made),
        "no_progress_streak": int(turn.no_progress_streak),
        "output_text": turn.output_text,
        "planner_state": tooling.planner_state_snapshot(),
        "function_calls": [
            {
                **item.as_dict(),
                "output": _parse_runtime_output_json(item.output_json),
            }
            for item in turn.function_calls
        ],
    }


def _persist_stage04_execution_trace(
    *,
    connection: sqlite3.Connection,
    workflow_run_id: str,
    task_run_id: str,
    actor_id: str,
    actor_type: str,
    idempotency_prefix: str,
    storage_root: Path,
    execution_session_id: str,
    tool_execution_id: str,
    policy_decision_id: str,
    context_pack_artifact: dict[str, Any],
    runtime_turn_evidence: list[dict[str, Any]],
    planner_state: dict[str, Any],
    agent_result: dict[str, Any] | None,
    stage04_build_result: dict[str, Any] | None,
    execution_outcome: str,
    error_code: str | None = None,
) -> dict[str, Any]:
    summarized_build_result = None
    if isinstance(stage04_build_result, dict):
        summarized_build_result = {
            "bundle_id": stage04_build_result.get("bundle_id"),
            "candidate_count": stage04_build_result.get("candidate_count"),
            "selected_candidate_count": stage04_build_result.get("selected_candidate_count"),
            "coverage_summary": stage04_build_result.get("coverage_summary"),
            "artifact_ids": {
                key: str(value.get("artifact_version_id") or "")
                for key, value in dict(stage04_build_result.get("artifacts") or {}).items()
                if isinstance(value, dict)
            },
        }

    return persist_prepared_execution_evidence_artifacts(
        connection=connection,
        workflow_run_id=workflow_run_id,
        task_run_id=task_run_id,
        actor_id=actor_id,
        actor_type=actor_type,
        idempotency_prefix=idempotency_prefix,
        artifacts=[
            prepare_execution_trace_artifact(
                execution_session_id=execution_session_id,
                tool_execution_id=tool_execution_id,
                policy_decision_id=policy_decision_id,
                artifact_kind=EXECUTION_TRACE_ARTIFACT_KIND,
                file_name=f"execution-trace-stage04-{execution_session_id}.json",
                trace_payload={
                    "execution_outcome": execution_outcome,
                    "error_code": error_code,
                    "context_pack_artifact_version_id": str(
                        context_pack_artifact.get("artifact_version_id") or ""
                    ),
                    "runtime_turn_evidence": runtime_turn_evidence,
                    "planner_state": planner_state,
                    "agent_result": agent_result,
                    "stage04_build_result": summarized_build_result,
                },
            )
        ],
        storage_root=storage_root,
    )[0]


def _parse_runtime_output_json(value: str) -> Any:
    try:
        return json.loads(value)
    except (TypeError, ValueError, json.JSONDecodeError):
        return value


def _build_context_pack(
    *,
    workflow_run: dict[str, Any],
    task_run: dict[str, Any],
    human_task: dict[str, Any],
    stage_spec: dict[str, Any],
    bundle: Any,
    input_artifacts: dict[str, dict[str, Any] | None],
) -> dict[str, Any]:
    execution_bindings = stage_spec.get("runtime_bindings")
    method_pin = stage_spec.get("method_package_pin")
    stop_policy = _stage04_stop_policy_from_stage_spec(stage_spec)
    return {
        "schema_version": "1.0",
        "kind": "weekly_stage04_openai_context_pack",
        "workflow_id": str(workflow_run.get("workflow_id") or ""),
        "workflow_run_id": str(workflow_run.get("workflow_run_id") or ""),
        "task_run_id": str(task_run.get("task_run_id") or ""),
        "human_task_id": str(human_task.get("human_task_id") or ""),
        "partition_key": str(workflow_run.get("partition_key") or ""),
        "stage_control": {
            "module_id": str(stage_spec.get("module_id") or ""),
            "stage_id": str(stage_spec.get("stage_id") or ""),
            "stage_control_digest": str(stage_spec.get("stage_control_digest") or ""),
            "execution_pattern": str(stage_spec.get("execution_pattern") or ""),
            "runtime_bindings": execution_bindings if isinstance(execution_bindings, dict) else {},
            "method_package_pin": method_pin if isinstance(method_pin, dict) else {},
            "required_evidence_keys": list(stage_spec.get("required_evidence_keys") or []),
        },
        "bundle_summary": {
            "bundle_id": getattr(bundle, "bundle_id"),
            "planning_week_id": getattr(bundle, "planning_week_id"),
            "route_slot_count": len(getattr(bundle, "route_slots")),
            "expanded_route_slot_count": len(expand_route_slot_requirements(getattr(bundle, "route_slots"))),
            "driver_count": len(getattr(bundle, "drivers")),
            "availability_driver_count": len(getattr(bundle, "availability_by_driver")),
            "actual_hours_driver_count": len(getattr(bundle, "actual_minutes_by_driver")),
            "referenced_artifacts": list(getattr(bundle, "referenced_artifacts")),
        },
        "input_artifacts": {
            key: (
                {
                    "artifact_version_id": str(value.get("artifact_version_id") or ""),
                    "artifact_kind": str(value.get("artifact_kind") or ""),
                    "content_digest": str(value.get("content_digest") or ""),
                    "media_type": str(value.get("media_type") or ""),
                }
                if isinstance(value, dict)
                else None
            )
            for key, value in input_artifacts.items()
        },
        "deterministic_guardrails": {
            "draft_only": True,
            "publish_blocked": True,
            "stage05_stage06_bypass_blocked": True,
            "explicit_finalize_required": True,
            "stop_policy": stop_policy,
            "allowed_functions": [
                "get_stage04_context",
                "preview_stage04_next_iteration",
                "apply_stage04_next_iteration",
                "get_stage04_validation_summary",
                "get_stage04_iteration_analysis",
                "finalize_weekly_stage04_draft_outputs",
            ],
        },
    }


def _resolve_stage04_input_artifacts(
    *,
    artifacts: list[dict[str, Any]],
    stage_spec: dict[str, Any],
) -> dict[str, dict[str, Any] | None]:
    return resolve_weekly_stage04_input_artifacts(
        artifacts=artifacts,
        stage_spec=stage_spec,
    )


def _normalize_actor_roles(raw_roles: Any) -> list[str]:
    if not isinstance(raw_roles, (list, tuple, set)):
        return []
    return [str(role) for role in raw_roles if str(role).strip()]


def _evaluate_weekly_stage04_policy(
    *,
    actor_type: str,
    actor_roles: list[str],
    payload: dict[str, Any],
) -> tuple[str, str | None, str | None]:
    requested = payload.get("policy_decision")
    if requested is not None:
        decision = str(requested)
        if decision not in {"allow", "deny", "require_approval"}:
            raise CommandError(
                code="invalid_policy_decision",
                message=f"unsupported policy decision override: {decision}",
                details={"allowed_decisions": ["allow", "deny", "require_approval"]},
            )
        if decision == "allow":
            return "allow", "override_allow", None
        if decision == "require_approval":
            return "require_approval", "override_require_approval", "stage04.weekly.openai_agent_execution"
        return "deny", "override_deny", None

    env_decision = os.environ.get("ONETRUTH_WEEKLY_STAGE04_POLICY_DECISION", "").strip()
    if env_decision:
        if env_decision not in {"allow", "deny", "require_approval"}:
            raise CommandError(
                code="invalid_policy_decision",
                message=f"unsupported ONETRUTH_WEEKLY_STAGE04_POLICY_DECISION value: {env_decision}",
                details={"allowed_decisions": ["allow", "deny", "require_approval"]},
            )
        if env_decision == "allow":
            return "allow", "env_allow", None
        if env_decision == "require_approval":
            return "require_approval", "env_require_approval", "stage04.weekly.openai_agent_execution"
        return "deny", "env_deny", None

    if actor_type in {"system", "service"} or any(role in STAGE04_ALLOWED_ROLES for role in actor_roles):
        return "allow", "role_allow", None
    return "deny", "actor_role_not_allowed", None


def _require_fields(payload: dict[str, Any], fields: list[str]) -> None:
    missing = [field for field in fields if payload.get(field) is None]
    if missing:
        raise CommandError(
            code="invalid_payload",
            message=f"missing required fields: {', '.join(missing)}",
            details={"missing_fields": missing},
        )


def _record_tool_and_session_failure(
    *,
    connection: sqlite3.Connection,
    tool_execution_id: str,
    execution_session_id: str,
    actor_id: str,
    actor_type: str,
    idempotency_base: str,
    error_code: str,
) -> None:
    try:
        complete_tool_execution_command(
            connection,
            {
                "tool_execution_id": tool_execution_id,
                "result": "failed",
                "error_code": error_code,
                "idempotency_key": f"{idempotency_base}:tool-complete-failed",
                "actor_id": actor_id,
                "actor_type": actor_type,
            },
        )
    except Exception:
        pass
    try:
        transition_execution_session_state_command(
            connection,
            {
                "execution_session_id": execution_session_id,
                "to_state": "FAILED",
                "reason": "tool_execution_failed",
                "idempotency_key": f"{idempotency_base}:session-failed",
                "actor_id": actor_id,
                "actor_type": actor_type,
            },
        )
    except Exception:
        pass
