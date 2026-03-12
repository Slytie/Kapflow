from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import sqlite3
from typing import Any

from onetruth.application.handlers.schedule_control import build_weekly_schedule_control_command
from onetruth.application.handlers.workflow_task_lifecycle import (
    CommandError,
    complete_tool_execution_command,
    create_artifact_version_command,
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
    PreparedExecutionEvidenceArtifact,
    prepare_execution_trace_artifact,
    prepare_pinned_execution_semantics_artifacts,
    prepare_runtime_json_evidence_artifact,
)
from onetruth.application.services.schedule_control import build_weekly_schedule_control_bundle
from onetruth.infrastructure.artifacts.storage import write_blob
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

ROUTE_SLOT_REQUIREMENTS_SUFFIX = "route_slot_requirements.workbook"
DRIVER_CAPABILITIES_SUFFIX = "driver_capabilities.workbook"
APPROVED_AVAILABILITY_KIND = "planning.approved_availability.workbook"
ACTUAL_HOURS_KIND = "planning.actual_hours_snapshot.workbook"
ROUTE_HORIZON_KIND = "planning.route_horizon.workbook"

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

    execution_session_id = _stable_id(
        "xs",
        f"{human_task['workflow_run_id']}:{human_task['task_run_id']}:{base_idempotency_key}",
    )
    tool_execution_id = _stable_id("tx", f"{execution_session_id}:{OPENAI_TOOL_CLASS}:{base_idempotency_key}")
    policy_decision_id = _stable_id("pd", f"{tool_execution_id}:{base_idempotency_key}")
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
    execution_semantics_evidence = _persist_prepared_execution_evidence_artifacts(
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
        storage_root=_artifact_root(),
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
        workflow_run_id=str(human_task["workflow_run_id"]),
        stage04_inputs=stage04_inputs,
        context_pack=context_pack,
        idempotency_prefix=f"{base_idempotency_key}:deterministic",
    )

    context_pack_artifact = _persist_prepared_execution_evidence_artifacts(
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
        storage_root=_artifact_root(),
    )[0]

    max_turns = _max_turns_from_stage_spec(stage_spec)

    try:
        selected_runner = runner or build_weekly_stage04_openai_agent_runner_from_env()
        agent_result = selected_runner.run_function_calling_loop(
            initial_input=_initial_model_input(context_pack=context_pack, stage_spec=stage_spec),
            tools=tool_specs,
            execute_function=tooling.execute,
            max_turns=max_turns,
        )
        stage04_build_result = tooling.materialize_outputs()
        tool_request_payload = {
            "schema_version": "1.0",
            "kind": "runtime_tool_requests",
            "execution_session_id": execution_session_id,
            "request_turns": [
                {
                    "turn_index": turn.turn_index,
                    "request_payload": turn.request_payload,
                    "request_id": turn.request_id,
                    "response_id": turn.response_id,
                    "model": turn.model,
                    "usage": turn.usage,
                }
                for turn in agent_result.turns
            ],
        }
        tool_result_payload = {
            "schema_version": "1.0",
            "kind": "runtime_tool_results",
            "execution_session_id": execution_session_id,
            "turns": [turn.as_dict() for turn in agent_result.turns],
            "final_output_text": agent_result.final_output_text,
            "total_usage": agent_result.total_usage,
            "stage04_build_result": {
                "bundle_id": stage04_build_result["bundle_id"],
                "candidate_count": stage04_build_result["candidate_count"],
                "selected_candidate_count": stage04_build_result["selected_candidate_count"],
                "selected_candidates": stage04_build_result["selected_candidates"],
                "artifacts": stage04_build_result["artifacts"],
            },
        }
        runtime_evidence_artifacts = _persist_prepared_execution_evidence_artifacts(
            connection=connection,
            workflow_run_id=str(human_task["workflow_run_id"]),
            task_run_id=str(human_task["task_run_id"]),
            actor_id=actor_id,
            actor_type=actor_type,
            idempotency_prefix=f"{base_idempotency_key}:runtime-evidence",
            artifacts=[
                prepare_runtime_json_evidence_artifact(
                    artifact_kind=RUNTIME_TOOL_REQUEST_ARTIFACT_KIND,
                    file_name=f"runtime-tool-request-{execution_session_id}.json",
                    execution_session_id=execution_session_id,
                    tool_execution_id=tool_execution_id,
                    policy_decision_id=policy_decision_id,
                    relation_kind="stage04_tool_request",
                    payload_json=tool_request_payload,
                    idempotency_suffix="tool-request",
                ),
                prepare_runtime_json_evidence_artifact(
                    artifact_kind=RUNTIME_TOOL_RESULT_ARTIFACT_KIND,
                    file_name=f"runtime-tool-result-{execution_session_id}.json",
                    execution_session_id=execution_session_id,
                    tool_execution_id=tool_execution_id,
                    policy_decision_id=policy_decision_id,
                    relation_kind="stage04_tool_result",
                    payload_json=tool_result_payload,
                    idempotency_suffix="tool-result",
                ),
                prepare_execution_trace_artifact(
                    execution_session_id=execution_session_id,
                    tool_execution_id=tool_execution_id,
                    policy_decision_id=policy_decision_id,
                    artifact_kind=EXECUTION_TRACE_ARTIFACT_KIND,
                    file_name=f"execution-trace-stage04-{execution_session_id}.json",
                    trace_payload={
                        "context_pack_artifact_version_id": str(context_pack_artifact["artifact_version_id"]),
                        "agent_result": agent_result.as_dict(),
                        "stage04_build_result": {
                            "bundle_id": stage04_build_result["bundle_id"],
                            "candidate_count": stage04_build_result["candidate_count"],
                            "selected_candidate_count": stage04_build_result["selected_candidate_count"],
                            "artifact_ids": {
                                key: str(value.get("artifact_version_id") or "")
                                for key, value in stage04_build_result["artifacts"].items()
                            },
                        },
                    },
                ),
            ],
            storage_root=_artifact_root(),
        )
    except Exception as exc:
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
            "Return compiled Stage04 context, bundle summary, and deterministic guardrails.",
            {
                "type": "object",
                "additionalProperties": False,
                "properties": {},
                "required": [],
            },
        ),
        (
            "materialize_weekly_stage04_draft_outputs",
            "spreadsheet.transform",
            "Execute deterministic Stage04 weekly build and materialize draft output artifacts.",
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
            "Return deterministic validation summary and selected candidate highlights.",
            {
                "type": "object",
                "additionalProperties": False,
                "properties": {},
                "required": [],
            },
        ),
        (
            "render_stage04_ops_packet",
            "projection.render",
            "Return a deterministic ops packet summary for Stage04 draft review.",
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
        "materialize_weekly_stage04_draft_outputs",
        "get_stage04_validation_summary",
        "render_stage04_ops_packet",
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


def _max_turns_from_stage_spec(stage_spec: dict[str, Any]) -> int:
    method_pin = stage_spec.get("method_package_pin")
    if not isinstance(method_pin, dict):
        return 4
    stop_policy = method_pin.get("stop_policy")
    if not isinstance(stop_policy, dict):
        return 4
    max_tool_calls = stop_policy.get("max_tool_calls")
    if not isinstance(max_tool_calls, int) or max_tool_calls <= 0:
        return 4
    return max_tool_calls


def _initial_model_input(
    *,
    context_pack: dict[str, Any],
    stage_spec: dict[str, Any],
) -> list[dict[str, Any]]:
    system_prompt = (
        "You are a bounded Stage04 weekly scheduling agent for weekly_schedule_planning.v1. "
        "You may only use provided deterministic function tools. "
        "Never publish schedules, never perform Stage05/Stage06 actions, and never invent data. "
        "When finished, return a concise JSON object with keys: "
        "summary, selected_candidate_count, recommended_action, warnings."
    )
    user_payload = {
        "task": "Produce Stage04 draft outputs and a review-ready summary using deterministic tools.",
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
        workflow_run_id: str,
        stage04_inputs: dict[str, dict[str, Any] | None],
        context_pack: dict[str, Any],
        idempotency_prefix: str,
    ) -> None:
        self.connection = connection
        self.workflow_run_id = workflow_run_id
        self.stage04_inputs = stage04_inputs
        self.context_pack = context_pack
        self.idempotency_prefix = idempotency_prefix
        self._cached_build_result: dict[str, Any] | None = None

    def execute(self, function_name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        _ = arguments
        if function_name == "get_stage04_context":
            return {
                "bundle_summary": self.context_pack["bundle_summary"],
                "input_artifacts": self.context_pack["input_artifacts"],
                "deterministic_guardrails": self.context_pack["deterministic_guardrails"],
            }
        if function_name == "materialize_weekly_stage04_draft_outputs":
            build_result = self.materialize_outputs()
            return {
                "bundle_id": build_result["bundle_id"],
                "candidate_count": build_result["candidate_count"],
                "selected_candidate_count": build_result["selected_candidate_count"],
                "selected_candidates": build_result["selected_candidates"],
                "artifacts": {
                    key: {
                        "artifact_version_id": value["artifact_version_id"],
                        "artifact_kind": value["artifact_kind"],
                    }
                    for key, value in build_result["artifacts"].items()
                },
            }
        if function_name == "get_stage04_validation_summary":
            build_result = self.materialize_outputs()
            validation = build_result["artifact_payloads"]["planning.validation_summary.doc"]
            return {
                "bundle_id": build_result["bundle_id"],
                "validation_summary": validation,
                "selected_candidate_count": build_result["selected_candidate_count"],
            }
        if function_name == "render_stage04_ops_packet":
            build_result = self.materialize_outputs()
            validation = build_result["artifact_payloads"]["planning.validation_summary.doc"]
            draft_doc = build_result["artifact_payloads"]["planning.draft_weekly_schedule.doc"]
            return {
                "bundle_id": build_result["bundle_id"],
                "ops_packet": {
                    "summary": draft_doc.get("summary"),
                    "validation_summary": validation.get("summary"),
                    "selected_candidates": build_result["selected_candidates"],
                },
            }
        raise CommandError(
            code="unsupported_weekly_stage04_tool",
            message="tool is not supported in weekly Stage04 deterministic toolset",
            details={"function_name": function_name},
        )

    def materialize_outputs(self) -> dict[str, Any]:
        if self._cached_build_result is not None:
            return self._cached_build_result
        command_payload: dict[str, Any] = {
            "workflow_run_id": self.workflow_run_id,
            "route_slot_requirements_artifact_version_id": str(
                self.stage04_inputs["route_slot_requirements"]["artifact_version_id"]  # type: ignore[index]
            ),
            "driver_capabilities_artifact_version_id": str(
                self.stage04_inputs["driver_capabilities"]["artifact_version_id"]  # type: ignore[index]
            ),
            "idempotency_key": f"{self.idempotency_prefix}:build-weekly",
        }
        optional_pairs = [
            ("approved_availability", "approved_availability_artifact_version_id"),
            ("actual_hours", "actual_hours_artifact_version_id"),
            ("route_horizon", "route_horizon_artifact_version_id"),
        ]
        for input_key, payload_key in optional_pairs:
            artifact = self.stage04_inputs.get(input_key)
            if isinstance(artifact, dict):
                command_payload[payload_key] = str(artifact["artifact_version_id"])
        self._cached_build_result = build_weekly_schedule_control_command(self.connection, command_payload)
        return self._cached_build_result


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
            "allowed_functions": [
                "get_stage04_context",
                "materialize_weekly_stage04_draft_outputs",
                "get_stage04_validation_summary",
                "render_stage04_ops_packet",
            ],
        },
    }


def _resolve_stage04_input_artifacts(
    *,
    artifacts: list[dict[str, Any]],
    stage_spec: dict[str, Any],
) -> dict[str, dict[str, Any] | None]:
    latest_by_kind: dict[str, dict[str, Any]] = {}
    for artifact in sorted(
        artifacts,
        key=lambda item: (
            str(item.get("created_at") or ""),
            str(item.get("artifact_version_id") or ""),
        ),
    ):
        artifact_kind = str(artifact.get("artifact_kind") or "")
        if not artifact_kind:
            continue
        latest_by_kind[artifact_kind] = artifact

    required_evidence_keys = {
        str(item)
        for item in stage_spec.get("required_evidence_keys") or []
        if str(item).strip()
    }
    route_slot_kind = _match_required_key(required_evidence_keys, ROUTE_SLOT_REQUIREMENTS_SUFFIX)
    driver_cap_kind = _match_required_key(required_evidence_keys, DRIVER_CAPABILITIES_SUFFIX)

    route_slot_artifact = latest_by_kind.get(route_slot_kind)
    if route_slot_artifact is None:
        raise CommandError(
            code="stage04_input_artifact_missing",
            message="route-slot requirements artifact is required for weekly Stage04 agent execution",
            details={"artifact_kind": route_slot_kind},
        )
    driver_caps_artifact = latest_by_kind.get(driver_cap_kind)
    if driver_caps_artifact is None:
        raise CommandError(
            code="stage04_input_artifact_missing",
            message="driver capabilities artifact is required for weekly Stage04 agent execution",
            details={"artifact_kind": driver_cap_kind},
        )

    return {
        "route_slot_requirements": route_slot_artifact,
        "driver_capabilities": driver_caps_artifact,
        "approved_availability": latest_by_kind.get(APPROVED_AVAILABILITY_KIND),
        "actual_hours": latest_by_kind.get(ACTUAL_HOURS_KIND),
        "route_horizon": latest_by_kind.get(ROUTE_HORIZON_KIND),
    }


def _match_required_key(required_keys: set[str], suffix: str) -> str:
    for candidate in sorted(required_keys):
        if candidate.endswith(suffix):
            return candidate
    raise CommandError(
        code="invalid_weekly_stage04_control_spec",
        message="compiled Stage04 metadata is missing required artifact key",
        details={"required_suffix": suffix, "required_keys": sorted(required_keys)},
    )


def _artifact_root() -> Path:
    raw = os.environ.get("ONETRUTH_ARTIFACT_ROOT", ".onetruth_artifacts").strip()
    path = Path(raw).expanduser().resolve()
    path.mkdir(parents=True, exist_ok=True)
    return path


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


def _persist_prepared_execution_evidence_artifacts(
    *,
    connection: sqlite3.Connection,
    workflow_run_id: str,
    task_run_id: str,
    actor_id: str,
    actor_type: str,
    idempotency_prefix: str,
    artifacts: list[PreparedExecutionEvidenceArtifact],
    storage_root: Path,
) -> list[dict[str, Any]]:
    created: list[dict[str, Any]] = []
    for artifact in artifacts:
        storage_uri, content_digest, byte_size = write_blob(
            storage_root=storage_root,
            workflow_run_id=workflow_run_id,
            file_name=artifact.file_name,
            content=artifact.payload_bytes(),
        )
        created_artifact = create_artifact_version_command(
            connection,
            {
                "workflow_run_id": workflow_run_id,
                "task_run_id": task_run_id,
                "artifact_kind": artifact.artifact_kind,
                "artifact_role": artifact.artifact_role,
                "media_type": artifact.media_type,
                "storage_uri": storage_uri,
                "content_digest": content_digest,
                "byte_size": byte_size,
                "metadata_json": artifact.metadata_json,
                "links": artifact.links,
                "idempotency_key": f"{idempotency_prefix}:{artifact.idempotency_suffix}",
                "actor_id": actor_id,
                "actor_type": actor_type,
            },
        )
        created.append(created_artifact)
    return created


def _stable_id(prefix: str, raw: str) -> str:
    digest = hashlib.sha256(raw.encode("utf-8")).hexdigest()[:24]
    return f"{prefix}-{digest}"
