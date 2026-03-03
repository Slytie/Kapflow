from __future__ import annotations

from collections import Counter
from copy import deepcopy
from typing import Any


def _link_id(event: dict[str, Any], link_type: str) -> str | None:
    for link in event.get("links", []):
        if link.get("type") == link_type:
            return link.get("id")
    return None


def reduce_events(events: list[dict[str, Any]]) -> dict[str, Any]:
    state: dict[str, Any] = {
        "workflow_runs": {},
        "task_runs": {},
        "human_tasks": {},
        "approvals": {},
        "artifact_versions": {},
        "pointers": {},
        "pointer_targets_by_dataset": {},
        "flags": {},
        "execution_sessions": {},
        "tool_executions": {},
        "degraded_components": {},
        "event_counts": Counter(),
        "actor_counts": Counter(),
        "stage_ids": set(),
    }

    for event in events:
        event_type = event["event_type"]
        payload = event.get("payload", {})
        actor = event.get("actor", {})
        state["event_counts"][event_type] += 1
        state["actor_counts"][actor.get("type", "unknown")] += 1

        if event_type == "workflow.run.created":
            run_id = _link_id(event, "workflow_run")
            if not run_id:
                continue
            state["workflow_runs"][run_id] = {
                "workflow_id": payload["workflow_id"],
                "partition_key": payload["partition_key"],
                "activation_key": payload["activation_key"],
                "logical_date": payload["logical_date"],
                "service_timezone": payload["service_timezone"],
                "service_interval_start": payload["service_interval_start"],
                "service_interval_end": payload["service_interval_end"],
                "state": "ACTIVE",
            }
        elif event_type == "workflow.run.state_changed":
            run_id = payload["workflow_run_id"]
            run = state["workflow_runs"].setdefault(run_id, {"state": payload["from_state"]})
            run["state"] = payload["to_state"]
            run["last_transition_reason"] = payload.get("reason")
        elif event_type == "task.run.created":
            task_run_id = payload["task_run_id"]
            state["task_runs"][task_run_id] = {
                "task_run_id": task_run_id,
                "run_id": _link_id(event, "workflow_run"),
                "stage_id": payload["stage_id"],
                "task_kind": payload["task_kind"],
                "activation_key": payload["activation_key"],
                "generation": payload.get("generation", 0),
                "spawned_from_flag_id": payload.get("spawned_from_flag_id"),
                "spawned_from_task_run_id": payload.get("spawned_from_task_run_id"),
                "resume_parent_task_run_id": payload.get("resume_parent_task_run_id"),
                "spawn_rule_id": payload.get("spawn_rule_id"),
                "spawn_cause_kind": payload.get("spawn_cause_kind"),
                "spawn_cause_event_id": payload.get("spawn_cause_event_id"),
                "spawn_budget_key": payload.get("spawn_budget_key"),
                "spawn_depth": payload.get("spawn_depth", 0),
                "state": "READY",
            }
            state["stage_ids"].add(payload["stage_id"])
        elif event_type == "task.run.state_changed":
            task_run_id = payload["task_run_id"]
            task = state["task_runs"].setdefault(task_run_id, {"task_run_id": task_run_id})
            task["state"] = payload["to_state"]
            task["last_transition_reason"] = payload.get("reason")
        elif event_type == "task.created":
            human_task_id = payload["human_task_id"]
            state["human_tasks"][human_task_id] = {
                "human_task_id": human_task_id,
                "run_id": _link_id(event, "workflow_run"),
                "task_run_id": _link_id(event, "task_run"),
                "task_kind": payload["task_kind"],
                "candidate_roles": list(payload.get("candidate_roles", [])),
                "state": payload["state"],
            }
        elif event_type == "task.claimed":
            human_task_id = payload["human_task_id"]
            task = state["human_tasks"].setdefault(human_task_id, {"human_task_id": human_task_id})
            task["state"] = "CLAIMED"
            task["lease_version"] = payload["lease_version"]
            task["claimed_until"] = payload["claimed_until"]
            task["claimed_by"] = actor.get("id")
        elif event_type == "task.lease_expired":
            human_task_id = payload["human_task_id"]
            task = state["human_tasks"].setdefault(human_task_id, {"human_task_id": human_task_id})
            task["state"] = "EXPIRED"
            task["lease_version"] = payload["lease_version"]
            task["expiry_kind"] = payload["expiry_kind"]
            task["reopened"] = payload["reopened"]
            task["escalated"] = payload["escalated"]
        elif event_type == "task.completed":
            human_task_id = payload["human_task_id"]
            task = state["human_tasks"].setdefault(human_task_id, {"human_task_id": human_task_id})
            task["state"] = "COMPLETED"
            task["completion_code"] = payload["completion_code"]
            task["completed_by"] = actor.get("id")
        elif event_type == "approval.requested":
            approval_id = payload["approval_id"]
            state["approvals"][approval_id] = {
                "approval_id": approval_id,
                "approval_kind": payload["approval_kind"],
                "action": payload["action"],
                "allowed_responses": list(payload["allowed_responses"]),
                "requested_from_role": payload.get("requested_from_role"),
                "state": "REQUESTED",
            }
        elif event_type == "approval.responded":
            approval_id = payload["approval_id"]
            approval = state["approvals"].setdefault(approval_id, {"approval_id": approval_id, "action": payload["action"]})
            approval["response"] = payload["response"]
            approval["outcome"] = payload["outcome"]
            approval["rationale"] = payload.get("rationale")
            approval["state"] = payload["outcome"]
            approval["responded_by"] = actor.get("id")
            approval["responded_actor_type"] = actor.get("type")
        elif event_type == "artifact.version.created":
            artifact_version_id = payload["artifact_version_id"]
            state["artifact_versions"][artifact_version_id] = {
                "artifact_version_id": artifact_version_id,
                "dataset_key": payload["dataset_key"],
                "supersedes_artifact_version_id": payload.get("supersedes_artifact_version_id"),
            }
        elif event_type == "artifact.pointer.promoted":
            pointer_id = payload["pointer_id"]
            pointer = state["pointers"].setdefault(pointer_id, {"pointer_id": pointer_id})
            pointer["dataset_key"] = payload["dataset_key"]
            pointer["promoted_artifact_version_id"] = payload["promoted_artifact_version_id"]
            pointer["reviewed_artifact_version_id"] = payload.get("reviewed_artifact_version_id")
            state["pointer_targets_by_dataset"][payload["dataset_key"]] = payload["promoted_artifact_version_id"]
        elif event_type == "artifact.pointer.drift_detected":
            pointer_id = payload["pointer_id"]
            pointer = state["pointers"].setdefault(pointer_id, {"pointer_id": pointer_id})
            pointer["dataset_key"] = payload["dataset_key"]
            pointer["reviewed_artifact_version_id"] = payload["reviewed_artifact_version_id"]
            pointer["promoted_artifact_version_id"] = payload["promoted_artifact_version_id"]
            pointer["drift_reason"] = payload["drift_reason"]
            pointer["drift_detected"] = True
        elif event_type == "flag.created":
            flag_id = payload["flag_id"]
            state["flags"][flag_id] = {
                "flag_id": flag_id,
                "flag_type": payload["flag_type"],
                "state": payload["state"],
                "summary": payload.get("summary"),
            }
        elif event_type == "flag.state_changed":
            flag_id = payload["flag_id"]
            flag = state["flags"].setdefault(flag_id, {"flag_id": flag_id})
            flag["state"] = payload["to_state"]
            flag["last_transition_reason"] = payload.get("reason")
        elif event_type == "execution.session.created":
            execution_session_id = payload["execution_session_id"]
            state["execution_sessions"][execution_session_id] = {
                "execution_session_id": execution_session_id,
                "task_run_id": _link_id(event, "task_run"),
                "execution_spec_id": payload["execution_spec_id"],
                "owner_mode": payload["owner_mode"],
                "principal_actor_type": payload.get("principal_actor_type"),
                "state": "CREATED",
            }
        elif event_type == "execution.session.state_changed":
            execution_session_id = payload["execution_session_id"]
            session = state["execution_sessions"].setdefault(execution_session_id, {"execution_session_id": execution_session_id})
            session["state"] = payload["to_state"]
            session["last_transition_reason"] = payload.get("reason")
        elif event_type == "tool.execution.requested":
            tool_execution_id = payload["tool_execution_id"]
            state["tool_executions"][tool_execution_id] = {
                "tool_execution_id": tool_execution_id,
                "execution_session_id": _link_id(event, "execution_session"),
                "tool_class": payload["tool_class"],
                "idempotency_key": payload["idempotency_key"],
                "tool_name": payload.get("tool_name"),
                "state": "REQUESTED",
            }
        elif event_type == "tool.execution.approved":
            tool_execution_id = payload["tool_execution_id"]
            tool = state["tool_executions"].setdefault(tool_execution_id, {"tool_execution_id": tool_execution_id})
            tool["tool_class"] = payload["tool_class"]
            tool["policy_decision_id"] = payload["policy_decision_id"]
            tool["state"] = "APPROVED"
        elif event_type == "tool.execution.completed":
            tool_execution_id = payload["tool_execution_id"]
            tool = state["tool_executions"].setdefault(tool_execution_id, {"tool_execution_id": tool_execution_id})
            tool["tool_class"] = payload["tool_class"]
            tool["result"] = payload["result"]
            tool["output_artifact_version_ids"] = list(payload.get("output_artifact_version_ids", []))
            tool["state"] = "COMPLETED"
        elif event_type == "tool.execution.denied":
            tool_execution_id = payload["tool_execution_id"]
            tool = state["tool_executions"].setdefault(tool_execution_id, {"tool_execution_id": tool_execution_id})
            tool["tool_class"] = payload["tool_class"]
            tool["policy_decision_id"] = payload["policy_decision_id"]
            tool["denial_reason"] = payload["denial_reason"]
            tool["state"] = "DENIED"
        elif event_type == "audit.degraded_mode.changed":
            state["degraded_components"][payload["component"]] = payload["to_state"]
        elif event_type == "projection.coherence_failed":
            state.setdefault("projection_failures", []).append(payload)

    return state


def canonicalize_state(state: dict[str, Any]) -> dict[str, Any]:
    frozen = deepcopy(state)
    frozen["event_counts"] = dict(sorted(frozen["event_counts"].items()))
    frozen["actor_counts"] = dict(sorted(frozen["actor_counts"].items()))
    frozen["stage_ids"] = sorted(frozen["stage_ids"])
    for key in [
        "workflow_runs",
        "task_runs",
        "human_tasks",
        "approvals",
        "artifact_versions",
        "pointers",
        "pointer_targets_by_dataset",
        "flags",
        "execution_sessions",
        "tool_executions",
        "degraded_components",
    ]:
        if isinstance(frozen[key], dict):
            frozen[key] = {k: frozen[key][k] for k in sorted(frozen[key])}
    return frozen


def event_types(events: list[dict[str, Any]]) -> set[str]:
    return {event["event_type"] for event in events}
