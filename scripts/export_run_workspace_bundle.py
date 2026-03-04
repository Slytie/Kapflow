#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
import zipfile

from onetruth.api.dependencies import RequestContext
from onetruth.api.routes.workflow_runs import (
    get_workflow_run_detail_endpoint,
    get_workflow_run_workspace_endpoint,
)
from onetruth.application.handlers.workflow_task_lifecycle import (
    list_execution_sessions_for_workflow_run_command,
    show_workflow_run_command,
)
from onetruth.infrastructure.db.session import DEFAULT_DB_URL, open_sqlite_connection
from onetruth.infrastructure.repositories.policy_decisions import (
    get_policy_decision,
    get_policy_decision_for_tool_execution,
)
from onetruth.infrastructure.repositories.tool_executions import (
    list_tool_executions_for_session,
)

REQUIRED_BUNDLE_FILES = (
    "README.md",
    "workspace_projection.json",
    "workflow_summary.json",
    "tasks.json",
    "approvals.json",
    "flags.json",
    "execution_sessions.json",
    "tool_executions.json",
    "policy_decisions.json",
    "timeline_excerpt.json",
    "artifact_manifest.json",
    "official_outputs.json",
    "graph_nodes.json",
    "graph_edges.json",
)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Export a workflow-run workspace inspection bundle ZIP.",
    )
    parser.add_argument(
        "--db-url",
        default=DEFAULT_DB_URL,
        help="SQLite database URL used for canonical runtime state.",
    )
    parser.add_argument(
        "--workflow-run-id",
        required=True,
        help="Workflow run ID to export.",
    )
    parser.add_argument(
        "--output",
        required=True,
        help="Output ZIP path.",
    )
    parser.add_argument(
        "--actor-id",
        default="human:workspace-exporter",
        help="Actor ID used for actionability projection context.",
    )
    parser.add_argument(
        "--actor-type",
        default="human",
        choices=["human", "agent", "service", "system"],
        help="Actor type used for actionability projection context.",
    )
    parser.add_argument(
        "--actor-roles",
        default="dispatch_supervisor,operations_manager,schedule_planner,fleet_coordinator",
        help="Comma-separated actor roles used for actionability projection context.",
    )
    parser.add_argument(
        "--timeline-limit",
        type=int,
        default=50,
        help="Number of recent timeline events included in workspace excerpt.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    output_path = Path(str(args.output)).expanduser()
    output_path.parent.mkdir(parents=True, exist_ok=True)

    connection = open_sqlite_connection(str(args.db_url))
    try:
        workflow_run = show_workflow_run_command(connection, str(args.workflow_run_id))
        actor_roles = tuple(
            role.strip()
            for role in str(args.actor_roles).split(",")
            if role.strip()
        )
        context = RequestContext(
            tenant_id=str(workflow_run["tenant_id"]),
            domain_id=str(workflow_run["domain_id"]),
            actor_id=str(args.actor_id),
            actor_type=str(args.actor_type),
            actor_roles=actor_roles,
        )
        workspace_projection = get_workflow_run_workspace_endpoint(
            connection,
            context=context,
            workflow_run_id=str(args.workflow_run_id),
            query={"timeline_limit": str(int(args.timeline_limit))},
        )
        run_detail = get_workflow_run_detail_endpoint(
            connection,
            context=context,
            workflow_run_id=str(args.workflow_run_id),
        )
        execution_sessions = list_execution_sessions_for_workflow_run_command(
            connection,
            str(args.workflow_run_id),
        )
        tool_executions: list[dict[str, object]] = []
        policy_decisions_by_id: dict[str, dict[str, object]] = {}
        for session in execution_sessions:
            session_tools = list_tool_executions_for_session(
                connection,
                str(session["execution_session_id"]),
            )
            tool_executions.extend(session_tools)
            for tool_execution in session_tools:
                policy_decision = None
                if tool_execution.get("policy_decision_id") is not None:
                    policy_decision = get_policy_decision(
                        connection,
                        str(tool_execution["policy_decision_id"]),
                    )
                if policy_decision is None:
                    policy_decision = get_policy_decision_for_tool_execution(
                        connection,
                        tool_execution_id=str(tool_execution["tool_execution_id"]),
                    )
                if policy_decision is None:
                    continue
                policy_decisions_by_id[str(policy_decision["policy_decision_id"])] = policy_decision
        policy_decisions = list(policy_decisions_by_id.values())
    finally:
        connection.close()

    workflow_summary = {
        "workflow_run": run_detail["workflow_run"],
        "summary": run_detail["summary"],
        "freshness": workspace_projection["freshness"],
    }
    scenario_name = _infer_scenario_name(run_detail["artifact_versions"])
    openai_path_used, openai_real_used = _infer_openai_usage(run_detail["artifact_versions"])
    readme_text = _build_bundle_readme(
        workflow_run_id=str(args.workflow_run_id),
        scenario_name=scenario_name,
        graph=workspace_projection["graph"],
        user_work=workspace_projection["user_work"],
        blocking_work=workspace_projection["blocking_work"],
        openai_path_used=openai_path_used,
        openai_real_used=openai_real_used,
    )

    files_payload = {
        "README.md": readme_text,
        "workspace_projection.json": workspace_projection,
        "workflow_summary.json": workflow_summary,
        "tasks.json": run_detail["human_tasks"],
        "approvals.json": run_detail["approvals"],
        "flags.json": run_detail["flags"],
        "execution_sessions.json": execution_sessions,
        "tool_executions.json": tool_executions,
        "policy_decisions.json": policy_decisions,
        "timeline_excerpt.json": workspace_projection["timeline_excerpt"],
        "artifact_manifest.json": run_detail["artifact_versions"],
        "official_outputs.json": workspace_projection["official_outputs"],
        "graph_nodes.json": workspace_projection["graph"]["nodes"],
        "graph_edges.json": workspace_projection["graph"]["edges"],
    }

    with zipfile.ZipFile(output_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for file_name in REQUIRED_BUNDLE_FILES:
            payload = files_payload[file_name]
            if isinstance(payload, str):
                archive.writestr(file_name, payload)
            else:
                archive.writestr(
                    file_name,
                    json.dumps(payload, indent=2, sort_keys=True) + "\n",
                )

    result = {
        "status": "ok",
        "command": "workspace-bundle.export",
        "workflow_run_id": str(args.workflow_run_id),
        "scenario_name": scenario_name,
        "output": str(output_path),
        "bundle_files": list(REQUIRED_BUNDLE_FILES),
        "openai_path_used": openai_path_used,
        "openai_real_used": openai_real_used,
    }
    sys.stdout.write(json.dumps(result, indent=2, sort_keys=True) + "\n")
    return 0


def _infer_scenario_name(artifact_versions: list[dict[str, object]]) -> str:
    for artifact in artifact_versions:
        metadata_json = artifact.get("metadata_json")
        if not isinstance(metadata_json, dict):
            continue
        pilot_scenario = metadata_json.get("pilot_scenario")
        if isinstance(pilot_scenario, str) and pilot_scenario:
            if pilot_scenario == "stage07_issue_replan":
                return "stage07_major_replan"
            return pilot_scenario
        scenario_id = metadata_json.get("scenario_id")
        if isinstance(scenario_id, str) and scenario_id:
            return scenario_id
        seed_set_id = metadata_json.get("seed_set_id")
        if isinstance(seed_set_id, str) and seed_set_id:
            return seed_set_id
    return "unknown"


def _infer_openai_usage(artifact_versions: list[dict[str, object]]) -> tuple[bool, bool]:
    evidence_artifacts = [
        artifact
        for artifact in artifact_versions
        if str(artifact.get("artifact_kind")) == "schedule.stage06.review_ai_evidence.json"
    ]
    if not evidence_artifacts:
        return False, False
    for artifact in evidence_artifacts:
        metadata_json = artifact.get("metadata_json")
        if not isinstance(metadata_json, dict):
            continue
        model_name = str(metadata_json.get("openai_model") or "").strip()
        if model_name and model_name != "pilot-mock-openai":
            return True, True
    return True, False


def _build_bundle_readme(
    *,
    workflow_run_id: str,
    scenario_name: str,
    graph: dict[str, object],
    user_work: list[dict[str, object]],
    blocking_work: list[dict[str, object]],
    openai_path_used: bool,
    openai_real_used: bool,
) -> str:
    nodes = graph.get("nodes")
    if not isinstance(nodes, list):
        nodes = []
    completed_nodes = [node["node_id"] for node in nodes if node.get("status") == "completed"]
    blocked_nodes = [
        node["node_id"]
        for node in nodes
        if node.get("status") in {"blocked", "awaiting_approval", "warning"}
    ]
    first_actions = _first_action_lines(user_work=user_work, blocking_work=blocking_work)
    upload_required = any(
        "linked_artifact" in (item.get("missing_required_inputs") or [])
        for item in blocking_work
        if isinstance(item, dict)
    )

    lines = [
        "# Workflow Workspace Bundle",
        "",
        f"- Workflow run ID: `{workflow_run_id}`",
        f"- Scenario: `{scenario_name}`",
        f"- OpenAI path used: `{openai_path_used}`",
        f"- Real OpenAI path used: `{openai_real_used}`",
        "",
        "## Graph status",
        "- Completed nodes:",
    ]
    if completed_nodes:
        lines.extend([f"  - `{node_id}`" for node_id in completed_nodes])
    else:
        lines.append("  - none")
    lines.append("- Blocked/warning nodes:")
    if blocked_nodes:
        lines.extend([f"  - `{node_id}`" for node_id in blocked_nodes])
    else:
        lines.append("  - none")

    lines.extend(
        [
            "",
            "## First actions to take",
        ]
    )
    if first_actions:
        lines.extend([f"- {line}" for line in first_actions])
    else:
        lines.append("- No immediate action items were detected in this projection.")

    lines.extend(
        [
            "",
            "## Unblocking note",
            f"- Uploading a document required to unblock: `{upload_required}`",
            "",
            "## Inspect next",
            "- `workspace_projection.json` for user_work/blocking_work/actionability",
            "- `graph_nodes.json` and `graph_edges.json` for derived graph status",
            "- `timeline_excerpt.json` for freshness/progress evidence",
            "- `official_outputs.json` and `artifact_manifest.json` for canonical output lineage",
        ]
    )
    return "\n".join(lines) + "\n"


def _first_action_lines(
    *,
    user_work: list[dict[str, object]],
    blocking_work: list[dict[str, object]],
) -> list[str]:
    combined: list[dict[str, object]] = []
    for item in user_work:
        if isinstance(item, dict):
            combined.append(item)
    for item in blocking_work:
        if isinstance(item, dict):
            combined.append(item)

    lines: list[str] = []
    seen: set[str] = set()
    for item in combined:
        stable_id = str(item.get("id") or "")
        if not stable_id or stable_id in seen:
            continue
        seen.add(stable_id)
        actions = item.get("available_actions")
        if not isinstance(actions, list) or not actions:
            continue
        action = str(actions[0])
        metadata = item.get("metadata")
        if not isinstance(metadata, dict):
            metadata = {}
        label = metadata.get("task_kind") or metadata.get("approval_kind") or metadata.get("kind") or stable_id
        lines.append(
            f"`{stable_id}` ({label}) -> `{action}`"
        )
        if len(lines) >= 5:
            break
    return lines


if __name__ == "__main__":
    raise SystemExit(main())

