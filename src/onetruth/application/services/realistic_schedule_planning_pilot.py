from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass
import hashlib
import json
import os
from pathlib import Path
import sqlite3
from typing import Any, Iterable, Sequence

from onetruth.application.handlers.workflow_task_lifecycle import (
    CommandError,
    activate_stage07_issue_from_flag_command,
    claim_human_task_command,
    complete_human_task_command,
    confirm_human_task_review_command,
    create_flag_command,
    create_task_run_command,
    create_workflow_run_command,
    create_artifact_version_command,
    ingest_artifact_document_command,
    list_approvals_for_workflow_run_command,
    list_artifacts_for_workflow_run_command,
    list_execution_sessions_for_workflow_run_command,
    list_flags_for_workflow_run_command,
    list_pointers_for_workflow_run_command,
    list_tasks_for_workflow_run_command,
    promote_pointer_command,
    request_approval_command,
    respond_approval_command,
    show_human_task_command,
    show_workflow_run_command,
    transition_flag_state_command,
)
from onetruth.application.services.example_document_corpus import (
    ExampleDocumentCorpus,
    load_example_document_corpus,
    seed_payloads_for_set,
)
from onetruth.application.services.stage06_openai_sandbox import (
    run_stage06_openai_review_sandbox,
)
from onetruth.infrastructure.artifacts.storage import (
    default_storage_root_for_db_url,
    encode_base64_content,
)
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
from onetruth.integrations.openai import (
    OpenAIResponseMetadata,
    Stage06ReviewClassification,
    Stage06ReviewClassifier,
)

WORKFLOW_ID = "schedule_planning.v1"
WORKFLOW_VERSION = "v1"
TENANT_ID = "tenant-a"
DOMAIN_ID = "domain-x"

PILOT_STAGE06_PUBLISH_READY = "stage06_publish_ready"
PILOT_STAGE06_NEEDS_INFORMATION = "stage06_needs_information"
PILOT_STAGE07_ISSUE_REPLAN = "stage07_issue_replan"
PILOT_STAGE05_MISSING_WORKBOOK = "stage05_missing_workbook"

ALL_PILOT_IDS: tuple[str, ...] = (
    PILOT_STAGE05_MISSING_WORKBOOK,
    PILOT_STAGE06_PUBLISH_READY,
    PILOT_STAGE06_NEEDS_INFORMATION,
    PILOT_STAGE07_ISSUE_REPLAN,
)

EVENT_TYPES_OF_INTEREST = {
    "workflow.run.created",
    "task.run.created",
    "task.created",
    "task.claimed",
    "task.completed",
    "approval.requested",
    "approval.responded",
    "flag.created",
    "flag.state_changed",
    "artifact.version.created",
    "artifact.pointer.promoted",
    "artifact.pointer.drift_detected",
    "execution.session.created",
    "execution.session.state_changed",
    "tool.execution.requested",
    "tool.execution.approved",
    "tool.execution.denied",
    "tool.execution.completed",
}


@dataclass(frozen=True)
class PilotDefinition:
    pilot_id: str
    partition_key: str
    logical_date: str
    seed_set_id: str
    stage_focus: str
    description: str


PILOT_DEFINITIONS: dict[str, PilotDefinition] = {
    PILOT_STAGE05_MISSING_WORKBOOK: PilotDefinition(
        pilot_id=PILOT_STAGE05_MISSING_WORKBOOK,
        partition_key="SD-2026-03-11",
        logical_date="2026-03-11",
        seed_set_id="",
        stage_focus="Stage05",
        description="Stage05 missing-workbook information-request branch with template-required upload blocking.",
    ),
    PILOT_STAGE06_PUBLISH_READY: PilotDefinition(
        pilot_id=PILOT_STAGE06_PUBLISH_READY,
        partition_key="SD-2026-03-12",
        logical_date="2026-03-12",
        seed_set_id="stage06_review_ready_example_set",
        stage_focus="Stage06",
        description="Stage06 publish-ready branch via bounded agent review, final review, approval, and publish pointer.",
    ),
    PILOT_STAGE06_NEEDS_INFORMATION: PilotDefinition(
        pilot_id=PILOT_STAGE06_NEEDS_INFORMATION,
        partition_key="SD-2026-03-13",
        logical_date="2026-03-13",
        seed_set_id="stage06_needs_information_example_set",
        stage_focus="Stage06",
        description="Stage06 needs-information branch via bounded agent review and spawned information request task.",
    ),
    PILOT_STAGE07_ISSUE_REPLAN: PilotDefinition(
        pilot_id=PILOT_STAGE07_ISSUE_REPLAN,
        partition_key="SD-2026-03-14",
        logical_date="2026-03-14",
        seed_set_id="stage07_issue_replan_example_set",
        stage_focus="Stage07",
        description="Stage07 issue activation/replan branch with approval-gated delta promotion.",
    ),
}


class _DeterministicStage06Classifier:
    def __init__(self, *, outcome: str, rationale: str, follow_on_task_kind: str | None) -> None:
        self._outcome = outcome
        self._rationale = rationale
        self._follow_on_task_kind = follow_on_task_kind

    def classify_stage06_review(
        self,
        *,
        instruction_context: dict[str, Any],
        artifact_context: list[dict[str, Any]],
        document_text: str,
    ) -> tuple[Stage06ReviewClassification, OpenAIResponseMetadata]:
        if not instruction_context:
            raise ValueError("instruction_context is required")
        if not artifact_context:
            raise ValueError("artifact_context is required")
        if not document_text.strip():
            raise ValueError("document_text is required")
        now = utc_now_iso()
        return (
            Stage06ReviewClassification(
                outcome=self._outcome,
                rationale_summary=self._rationale,
                evidence_refs=["pilot:deterministic:stage06"],
                suggested_follow_on_task_kind=self._follow_on_task_kind,
            ),
            OpenAIResponseMetadata(
                response_id=f"pilot-{self._outcome}-response",
                request_id=f"pilot-{self._outcome}-request",
                model="pilot-mock-openai",
                usage={"input_tokens": 0, "output_tokens": 0},
                attempts=1,
                requested_at=now,
                completed_at=now,
            ),
        )


def run_realistic_schedule_planning_pilot_suite(
    connection: sqlite3.Connection,
    *,
    db_url: str,
    pilot_key: str,
    output_root: Path,
    artifact_root: Path | None = None,
    pilot_ids: Sequence[str] | None = None,
    openai_mode: str = "mock",
    manifest_path: Path | None = None,
) -> dict[str, Any]:
    if openai_mode not in {"mock", "real"}:
        raise ValueError("openai_mode must be 'mock' or 'real'")

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

    corpus = load_example_document_corpus(manifest_path)

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
        if created:
            if pilot_id == PILOT_STAGE05_MISSING_WORKBOOK:
                _run_stage05_missing_workbook(
                    connection,
                    definition=definition,
                    workflow_run_id=workflow_run_id,
                    pilot_key=pilot_key,
                )
            elif pilot_id == PILOT_STAGE06_PUBLISH_READY:
                _run_stage06_publish_ready(
                    connection,
                    corpus=corpus,
                    definition=definition,
                    workflow_run_id=workflow_run_id,
                    pilot_key=pilot_key,
                    storage_root=resolved_artifact_root,
                    openai_mode=openai_mode,
                )
            elif pilot_id == PILOT_STAGE06_NEEDS_INFORMATION:
                _run_stage06_needs_information(
                    connection,
                    corpus=corpus,
                    definition=definition,
                    workflow_run_id=workflow_run_id,
                    pilot_key=pilot_key,
                    storage_root=resolved_artifact_root,
                    openai_mode=openai_mode,
                )
            elif pilot_id == PILOT_STAGE07_ISSUE_REPLAN:
                _run_stage07_issue_replan(
                    connection,
                    corpus=corpus,
                    definition=definition,
                    workflow_run_id=workflow_run_id,
                    pilot_key=pilot_key,
                    storage_root=resolved_artifact_root,
                )

        packet = build_inspection_packet(
            connection,
            pilot_id=pilot_id,
            pilot_key=pilot_key,
            workflow_run_id=workflow_run_id,
            definition=definition,
            seed_set_id=definition.seed_set_id,
            reused_existing=not created,
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
        "command": "schedule-planning-pilot.run",
        "pilot_key": pilot_key,
        "db_url": db_url,
        "artifact_root": str(resolved_artifact_root),
        "output_root": str(resolved_output_root),
        "openai_mode": openai_mode,
        "pilot_runs": pilot_results,
    }
    summary_json_path = resolved_output_root / "pilot_summary.json"
    summary_md_path = resolved_output_root / "pilot_summary.md"
    summary_json_path.write_text(json.dumps(summary, indent=2, sort_keys=True), encoding="utf-8")
    summary_md_path.write_text(_summary_to_markdown(summary), encoding="utf-8")
    summary["summary_json_path"] = str(summary_json_path)
    summary["summary_markdown_path"] = str(summary_md_path)
    return summary


def build_inspection_packet(
    connection: sqlite3.Connection,
    *,
    pilot_id: str,
    pilot_key: str,
    workflow_run_id: str,
    definition: PilotDefinition,
    seed_set_id: str,
    reused_existing: bool,
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
    policy_decision_ids: set[str] = set()
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
            if policy_id in policy_decision_ids:
                continue
            policy_decision_ids.add(policy_id)
            policy_decisions.append(policy_decision)

    timeline_events = list_events(connection, run_id=workflow_run_id, limit=1000)
    timeline_of_interest = [
        _compact_event(event)
        for event in timeline_events
        if str(event.get("event_type")) in EVENT_TYPES_OF_INTEREST
    ]

    routes = _inspection_routes(
        workflow_run_id=workflow_run_id,
        approvals=approvals,
        flags=flags,
        tasks=tasks,
        artifacts=artifacts,
        pointers=pointers,
    )

    return {
        "packet_version": 1,
        "generated_at": utc_now_iso(),
        "pilot_id": pilot_id,
        "pilot_key": pilot_key,
        "description": definition.description,
        "stage_focus": definition.stage_focus,
        "seed_set_id": seed_set_id,
        "reused_existing": reused_existing,
        "workflow_run": workflow_run,
        "linked_ids": {
            "artifact_version_ids": [str(item["artifact_version_id"]) for item in artifacts],
            "pointer_keys": [str(item["pointer_key"]) for item in pointers],
            "approval_ids": [str(item["approval_id"]) for item in approvals],
            "flag_ids": [str(item["flag_id"]) for item in flags],
            "execution_session_ids": [str(item["execution_session_id"]) for item in sessions],
            "tool_execution_ids": [str(item["tool_execution_id"]) for item in tool_executions],
            "policy_decision_ids": [str(item["policy_decision_id"]) for item in policy_decisions],
        },
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
            pilot_id=pilot_id,
            tasks=tasks,
            approvals=approvals,
            flags=flags,
            pointers=pointers,
            sessions=sessions,
            tool_executions=tool_executions,
            policy_decisions=policy_decisions,
            timeline_of_interest=timeline_of_interest,
        ),
    }


def _ensure_workflow_run(
    connection: sqlite3.Connection,
    *,
    definition: PilotDefinition,
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


def _run_stage05_missing_workbook(
    connection: sqlite3.Connection,
    *,
    definition: PilotDefinition,
    workflow_run_id: str,
    pilot_key: str,
) -> None:
    stage05 = create_task_run_command(
        connection,
        {
            "task_run_id": _deterministic_id("tr", pilot_key, definition.pilot_id, "stage05-information"),
            "human_task_id": _deterministic_id("ht", pilot_key, definition.pilot_id, "stage05-information"),
            "workflow_run_id": workflow_run_id,
            "stage_id": "Stage05",
            "task_kind": "information_request",
            "activation_key": f"pilot:{pilot_key}:{definition.pilot_id}:stage05:information_request",
            "candidate_roles": ["schedule_planner"],
            "owner_role": "dispatch_supervisor",
            "create_human_task": True,
            "idempotency_key": f"pilot:{pilot_key}:{definition.pilot_id}:tasks.create:stage05-information",
            "actor_id": "system:pilot-runner",
            "actor_type": "system",
        },
    )
    _claim_if_open(
        connection,
        human_task_id=str(stage05["human_task"]["human_task_id"]),
        actor_id="human:schedule-planner-pilot",
        actor_type="human",
        idempotency_key=f"pilot:{pilot_key}:{definition.pilot_id}:tasks.claim:stage05-information",
    )


def _run_stage06_publish_ready(
    connection: sqlite3.Connection,
    *,
    corpus: ExampleDocumentCorpus,
    definition: PilotDefinition,
    workflow_run_id: str,
    pilot_key: str,
    storage_root: Path,
    openai_mode: str,
) -> None:
    _seed_from_set(
        connection,
        corpus=corpus,
        workflow_run_id=workflow_run_id,
        seed_set_id=definition.seed_set_id,
        pilot_key=pilot_key,
        pilot_id=definition.pilot_id,
        storage_root=storage_root,
    )

    stage06 = create_task_run_command(
        connection,
        {
            "task_run_id": _deterministic_id("tr", pilot_key, definition.pilot_id, "stage06-review"),
            "human_task_id": _deterministic_id("ht", pilot_key, definition.pilot_id, "stage06-review"),
            "workflow_run_id": workflow_run_id,
            "stage_id": "Stage06",
            "task_kind": "review_packet",
            "activation_key": f"pilot:{pilot_key}:{definition.pilot_id}:stage06:review_packet",
            "candidate_roles": ["dispatch_supervisor"],
            "owner_role": "dispatch_supervisor",
            "create_human_task": True,
            "idempotency_key": f"pilot:{pilot_key}:{definition.pilot_id}:tasks.create:stage06-review",
            "actor_id": "system:pilot-runner",
            "actor_type": "system",
        },
    )
    stage06_human_task_id = str(stage06["human_task"]["human_task_id"])

    _claim_if_open(
        connection,
        human_task_id=stage06_human_task_id,
        actor_id="agent:pilot-stage06",
        actor_type="agent",
        idempotency_key=f"pilot:{pilot_key}:{definition.pilot_id}:tasks.claim:stage06-review",
    )

    classifier = None
    if openai_mode == "mock":
        classifier = _DeterministicStage06Classifier(
            outcome="draft_is_publish_ready",
            rationale="Draft appears publish-ready for planned service interval.",
            follow_on_task_kind="final_review",
        )

    with _temporary_env("ONETRUTH_ARTIFACT_ROOT", str(storage_root)):
        stage06_result = run_stage06_openai_review_sandbox(
            connection,
            {
                "human_task_id": stage06_human_task_id,
                "actor_id": "agent:pilot-stage06",
                "actor_type": "agent",
                "actor_roles": ["dispatch_supervisor"],
                "idempotency_key": f"pilot:{pilot_key}:{definition.pilot_id}:stage06-agent-review",
            },
            classifier=classifier,
        )

    spawned = stage06_result["completion_result"]["spawned_children"]
    if not spawned:
        raise CommandError(
            code="pilot_stage06_missing_spawned_child",
            message="stage06 publish-ready pilot expected a spawned final_review child task",
            details={"workflow_run_id": workflow_run_id},
        )
    final_review_human_task_id = str(spawned[0]["human_task_id"])
    final_review_task_run_id = str(spawned[0]["task_run_id"])

    stage06_publish_packet = _create_json_draft_artifact(
        connection,
        workflow_run_id=workflow_run_id,
        task_run_id=final_review_task_run_id,
        artifact_kind="schedule.stage06.publish_packet",
        artifact_suffix="stage06-publish-packet",
        pilot_key=pilot_key,
        pilot_id=definition.pilot_id,
        storage_root=storage_root,
        payload={
            "pilot_scenario": definition.pilot_id,
            "branch": "publish_ready",
            "kind": "stage06_publish_packet",
        },
    )
    draft_published_workbook = _ingest_fixture(
        connection,
        corpus=corpus,
        workflow_run_id=workflow_run_id,
        fixture_id="schedule.stage06.published_schedule_workbook.completed",
        pilot_key=pilot_key,
        pilot_id=definition.pilot_id,
        artifact_suffix="stage06-published-draft",
        storage_root=storage_root,
        task_run_id=final_review_task_run_id,
        artifact_role="draft_output",
        metadata_json={
            "pilot_scenario": definition.pilot_id,
            "pilot_branch": "publish_ready",
            "lifecycle": "draft",
            "is_draft": True,
        },
    )

    _claim_if_open(
        connection,
        human_task_id=final_review_human_task_id,
        actor_id="human:dispatch-supervisor-pilot",
        actor_type="human",
        idempotency_key=f"pilot:{pilot_key}:{definition.pilot_id}:tasks.claim:stage06-final-review",
    )
    confirm_human_task_review_command(
        connection,
        {
            "human_task_id": final_review_human_task_id,
            "actor_id": "human:dispatch-supervisor-pilot",
            "actor_type": "human",
            "reviewed_artifact_version_ids": [
                str(stage06_publish_packet["artifact_version_id"]),
                str(draft_published_workbook["artifact_version_id"]),
            ],
            "idempotency_key": f"pilot:{pilot_key}:{definition.pilot_id}:tasks.confirm-review:stage06-final-review",
        },
        storage_root=storage_root,
    )
    complete_human_task_command(
        connection,
        {
            "human_task_id": final_review_human_task_id,
            "actor_id": "human:dispatch-supervisor-pilot",
            "actor_type": "human",
            "outcome": "review_complete",
            "idempotency_key": f"pilot:{pilot_key}:{definition.pilot_id}:tasks.complete:stage06-final-review",
        },
    )

    approval = request_approval_command(
        connection,
        {
            "approval_id": _deterministic_id("ap", pilot_key, definition.pilot_id, "stage06-publish-approval"),
            "workflow_run_id": workflow_run_id,
            "task_run_id": final_review_task_run_id,
            "approval_kind": "business_decision",
            "scope_kind": "stage",
            "scope_ref": "Stage06",
            "action": "publish_schedule",
            "candidate_roles": ["dispatch_supervisor"],
            "required_role": "dispatch_supervisor",
            "idempotency_key": f"pilot:{pilot_key}:{definition.pilot_id}:approvals.request:stage06-publish",
            "actor_id": "human:dispatch-supervisor-pilot",
            "actor_type": "human",
        },
    )
    approval_id = str(approval["approval_id"])

    respond_approval_command(
        connection,
        {
            "approval_id": approval_id,
            "actor_id": "human:dispatch-supervisor-pilot",
            "actor_type": "human",
            "response_kind": "approve",
            "response_reason": "Pilot publish-ready branch approved.",
            "idempotency_key": f"pilot:{pilot_key}:{definition.pilot_id}:approvals.respond:stage06-publish",
        },
    )

    promote_pointer_command(
        connection,
        {
            "workflow_run_id": workflow_run_id,
            "scope_kind": "stage",
            "scope_ref": "Stage06",
            "pointer_key": "official:schedule.published_schedule.workbook",
            "artifact_kind": "schedule.published_schedule.workbook",
            "artifact_version_id": str(draft_published_workbook["artifact_version_id"]),
            "promotion_reason": "official_publish",
            "promoted_by_task_run_id": final_review_task_run_id,
            "approved_by_approval_id": approval_id,
            "idempotency_key": f"pilot:{pilot_key}:{definition.pilot_id}:pointers.promote:stage06-publish",
            "actor_id": "human:dispatch-supervisor-pilot",
            "actor_type": "human",
        },
    )


def _run_stage06_needs_information(
    connection: sqlite3.Connection,
    *,
    corpus: ExampleDocumentCorpus,
    definition: PilotDefinition,
    workflow_run_id: str,
    pilot_key: str,
    storage_root: Path,
    openai_mode: str,
) -> None:
    _seed_from_set(
        connection,
        corpus=corpus,
        workflow_run_id=workflow_run_id,
        seed_set_id=definition.seed_set_id,
        pilot_key=pilot_key,
        pilot_id=definition.pilot_id,
        storage_root=storage_root,
    )

    stage06 = create_task_run_command(
        connection,
        {
            "task_run_id": _deterministic_id("tr", pilot_key, definition.pilot_id, "stage06-review"),
            "human_task_id": _deterministic_id("ht", pilot_key, definition.pilot_id, "stage06-review"),
            "workflow_run_id": workflow_run_id,
            "stage_id": "Stage06",
            "task_kind": "review_packet",
            "activation_key": f"pilot:{pilot_key}:{definition.pilot_id}:stage06:review_packet",
            "candidate_roles": ["dispatch_supervisor"],
            "owner_role": "dispatch_supervisor",
            "create_human_task": True,
            "idempotency_key": f"pilot:{pilot_key}:{definition.pilot_id}:tasks.create:stage06-review",
            "actor_id": "system:pilot-runner",
            "actor_type": "system",
        },
    )
    stage06_human_task_id = str(stage06["human_task"]["human_task_id"])

    _claim_if_open(
        connection,
        human_task_id=stage06_human_task_id,
        actor_id="agent:pilot-stage06",
        actor_type="agent",
        idempotency_key=f"pilot:{pilot_key}:{definition.pilot_id}:tasks.claim:stage06-review",
    )

    classifier = None
    if openai_mode == "mock":
        classifier = _DeterministicStage06Classifier(
            outcome="review_requires_more_information",
            rationale="Critical details are missing in the review packet.",
            follow_on_task_kind="information_request",
        )

    with _temporary_env("ONETRUTH_ARTIFACT_ROOT", str(storage_root)):
        run_stage06_openai_review_sandbox(
            connection,
            {
                "human_task_id": stage06_human_task_id,
                "actor_id": "agent:pilot-stage06",
                "actor_type": "agent",
                "actor_roles": ["dispatch_supervisor"],
                "idempotency_key": f"pilot:{pilot_key}:{definition.pilot_id}:stage06-agent-review",
            },
            classifier=classifier,
        )


def _run_stage07_issue_replan(
    connection: sqlite3.Connection,
    *,
    corpus: ExampleDocumentCorpus,
    definition: PilotDefinition,
    workflow_run_id: str,
    pilot_key: str,
    storage_root: Path,
) -> None:
    seeded = _seed_from_set(
        connection,
        corpus=corpus,
        workflow_run_id=workflow_run_id,
        seed_set_id=definition.seed_set_id,
        pilot_key=pilot_key,
        pilot_id=definition.pilot_id,
        storage_root=storage_root,
    )
    base_candidates = [
        item for item in seeded if str(item.get("artifact_kind")) == "schedule.published_schedule.workbook"
    ]
    if not base_candidates:
        raise CommandError(
            code="pilot_stage07_missing_base_artifact",
            message="stage07 pilot expected a seeded published schedule artifact",
            details={"workflow_run_id": workflow_run_id},
        )
    base_artifact = base_candidates[0]

    promote_pointer_command(
        connection,
        {
            "workflow_run_id": workflow_run_id,
            "scope_kind": "stage",
            "scope_ref": "Stage06",
            "pointer_key": "official:schedule.published_schedule.workbook",
            "artifact_kind": "schedule.published_schedule.workbook",
            "artifact_version_id": str(base_artifact["artifact_version_id"]),
            "promotion_reason": "seed_base",
            "idempotency_key": f"pilot:{pilot_key}:{definition.pilot_id}:pointers.promote:stage06-base",
            "actor_id": "system:pilot-runner",
            "actor_type": "system",
        },
    )

    flag = create_flag_command(
        connection,
        {
            "flag_id": _deterministic_id("fl", pilot_key, definition.pilot_id, "stage07-flag"),
            "workflow_run_id": workflow_run_id,
            "kind": "no_show",
            "severity": "high",
            "summary": "Pilot issue: courier no-show requires replan.",
            "details_json": {
                "reason_code": "no_show",
                "zone_id": "berlin-east",
                "pilot_scenario": definition.pilot_id,
            },
            "created_by": {
                "id": "human:dispatcher-pilot",
                "type": "human",
            },
            "idempotency_key": f"pilot:{pilot_key}:{definition.pilot_id}:flags.create:no-show",
        },
    )
    flag_id = str(flag["flag_id"])

    activated = activate_stage07_issue_from_flag_command(
        connection,
        {
            "workflow_run_id": workflow_run_id,
            "flag_id": flag_id,
            "generation": 0,
            "task_run_id": _deterministic_id("tr", pilot_key, definition.pilot_id, "stage07-triage"),
            "human_task_id": _deterministic_id("ht", pilot_key, definition.pilot_id, "stage07-triage"),
            "actor_id": "system:stage07-orchestrator",
            "actor_type": "system",
            "idempotency_key": f"pilot:{pilot_key}:{definition.pilot_id}:stage07.activate-issue",
        },
    )
    triage_human_task_id = str(activated["human_task"]["human_task_id"])

    _claim_if_open(
        connection,
        human_task_id=triage_human_task_id,
        actor_id="human:ops-manager-pilot",
        actor_type="human",
        idempotency_key=f"pilot:{pilot_key}:{definition.pilot_id}:tasks.claim:stage07-triage",
    )
    _ingest_fixture(
        connection,
        corpus=corpus,
        workflow_run_id=workflow_run_id,
        fixture_id="schedule.stage07.exception_board_doc.completed",
        pilot_key=pilot_key,
        pilot_id=definition.pilot_id,
        artifact_suffix="stage07-exception-board-upload",
        storage_root=storage_root,
        task_run_id=str(activated["task_run"]["task_run_id"]),
        human_task_id=triage_human_task_id,
        artifact_role="evidence",
        metadata_json={
            "pilot_scenario": definition.pilot_id,
            "uploaded_for_task_kind": "exception_triage",
        },
    )

    triage_complete = complete_human_task_command(
        connection,
        {
            "human_task_id": triage_human_task_id,
            "actor_id": "human:ops-manager-pilot",
            "actor_type": "human",
            "outcome": "major_replan_is_ready_for_review",
            "idempotency_key": f"pilot:{pilot_key}:{definition.pilot_id}:tasks.complete:stage07-triage",
        },
    )
    spawned = triage_complete["spawned_children"]
    if not spawned:
        raise CommandError(
            code="pilot_stage07_missing_spawned_child",
            message="stage07 issue pilot expected a spawned final_review task",
            details={"workflow_run_id": workflow_run_id, "flag_id": flag_id},
        )
    final_review_human_task_id = str(spawned[0]["human_task_id"])
    final_review_task_run_id = str(spawned[0]["task_run_id"])

    stage07_replan_packet = _create_json_draft_artifact(
        connection,
        workflow_run_id=workflow_run_id,
        task_run_id=final_review_task_run_id,
        artifact_kind="schedule.stage07.replan_packet",
        artifact_suffix="stage07-replan-packet",
        pilot_key=pilot_key,
        pilot_id=definition.pilot_id,
        storage_root=storage_root,
        payload={
            "pilot_scenario": definition.pilot_id,
            "flag_id": flag_id,
            "kind": "stage07_replan_packet",
            "lifecycle": "draft",
            "is_draft": True,
        },
    )
    draft_replan_delta = _ingest_fixture(
        connection,
        corpus=corpus,
        workflow_run_id=workflow_run_id,
        fixture_id="schedule.stage07.replan_delta_workbook.completed",
        pilot_key=pilot_key,
        pilot_id=definition.pilot_id,
        artifact_suffix="stage07-replan-delta-draft",
        storage_root=storage_root,
        task_run_id=final_review_task_run_id,
        artifact_role="draft_output",
        supersedes_artifact_version_id=str(base_artifact["artifact_version_id"]),
        metadata_json={
            "pilot_scenario": definition.pilot_id,
            "flag_id": flag_id,
            "base_artifact_version_id": str(base_artifact["artifact_version_id"]),
            "delta_sequence": 1,
            "lifecycle": "draft",
            "is_draft": True,
        },
    )

    _claim_if_open(
        connection,
        human_task_id=final_review_human_task_id,
        actor_id="human:ops-manager-pilot",
        actor_type="human",
        idempotency_key=f"pilot:{pilot_key}:{definition.pilot_id}:tasks.claim:stage07-final-review",
    )
    confirm_human_task_review_command(
        connection,
        {
            "human_task_id": final_review_human_task_id,
            "actor_id": "human:ops-manager-pilot",
            "actor_type": "human",
            "reviewed_artifact_version_ids": [
                str(stage07_replan_packet["artifact_version_id"]),
                str(draft_replan_delta["artifact_version_id"]),
            ],
            "idempotency_key": f"pilot:{pilot_key}:{definition.pilot_id}:tasks.confirm-review:stage07-final-review",
        },
        storage_root=storage_root,
    )
    complete_human_task_command(
        connection,
        {
            "human_task_id": final_review_human_task_id,
            "actor_id": "human:ops-manager-pilot",
            "actor_type": "human",
            "outcome": "review_complete",
            "idempotency_key": f"pilot:{pilot_key}:{definition.pilot_id}:tasks.complete:stage07-final-review",
        },
    )

    approval = request_approval_command(
        connection,
        {
            "approval_id": _deterministic_id("ap", pilot_key, definition.pilot_id, "stage07-major-replan"),
            "workflow_run_id": workflow_run_id,
            "task_run_id": final_review_task_run_id,
            "approval_kind": "business_decision",
            "scope_kind": "stage",
            "scope_ref": "Stage07",
            "action": "approve_major_replan",
            "candidate_roles": ["operations_manager"],
            "required_role": "operations_manager",
            "idempotency_key": f"pilot:{pilot_key}:{definition.pilot_id}:approvals.request:stage07-major-replan",
            "actor_id": "human:ops-manager-pilot",
            "actor_type": "human",
        },
    )
    approval_id = str(approval["approval_id"])

    respond_approval_command(
        connection,
        {
            "approval_id": approval_id,
            "actor_id": "human:ops-manager-pilot",
            "actor_type": "human",
            "response_kind": "approve",
            "response_reason": "Pilot Stage07 major replan approved.",
            "idempotency_key": f"pilot:{pilot_key}:{definition.pilot_id}:approvals.respond:stage07-major-replan",
        },
    )

    promote_pointer_command(
        connection,
        {
            "workflow_run_id": workflow_run_id,
            "scope_kind": "stage",
            "scope_ref": "Stage07",
            "pointer_key": "official:schedule.replan_delta.workbook",
            "artifact_kind": "schedule.replan_delta.workbook",
            "artifact_version_id": str(draft_replan_delta["artifact_version_id"]),
            "promotion_reason": "official_major_replan",
            "promoted_by_task_run_id": final_review_task_run_id,
            "approved_by_approval_id": approval_id,
            "reviewed_base_artifact_version_id": str(base_artifact["artifact_version_id"]),
            "base_pointer_key": "official:schedule.published_schedule.workbook",
            "idempotency_key": f"pilot:{pilot_key}:{definition.pilot_id}:pointers.promote:stage07-delta",
            "actor_id": "human:ops-manager-pilot",
            "actor_type": "human",
        },
    )

    transition_flag_state_command(
        connection,
        {
            "flag_id": flag_id,
            "to_state": "resolved",
            "reason": "Pilot Stage07 replan published.",
            "actor_id": "human:ops-manager-pilot",
            "actor_type": "human",
            "idempotency_key": f"pilot:{pilot_key}:{definition.pilot_id}:flags.transition:resolved",
        },
    )


def _seed_from_set(
    connection: sqlite3.Connection,
    *,
    corpus: ExampleDocumentCorpus,
    workflow_run_id: str,
    seed_set_id: str,
    pilot_key: str,
    pilot_id: str,
    storage_root: Path,
) -> list[dict[str, Any]]:
    payloads = seed_payloads_for_set(
        corpus=corpus,
        seed_set_id=seed_set_id,
        workflow_run_id=workflow_run_id,
        idempotency_prefix=f"pilot:{pilot_key}:{pilot_id}:seed-set",
    )
    seeded: list[dict[str, Any]] = []
    for payload in payloads:
        metadata_json = dict(payload.get("metadata_json") or {})
        fixture_id = str(metadata_json.get("fixture_id") or "fixture")
        artifact = ingest_artifact_document_command(
            connection,
            {
                **payload,
                "artifact_version_id": _deterministic_id(
                    "av",
                    pilot_key,
                    pilot_id,
                    f"seed:{fixture_id}",
                ),
                "idempotency_key": f"pilot:{pilot_key}:{pilot_id}:artifacts.seed:{fixture_id}",
                "metadata_json": {
                    **metadata_json,
                    "pilot_key": pilot_key,
                    "pilot_id": pilot_id,
                    "seed_set_id": seed_set_id,
                },
                "actor_id": "system:pilot-runner",
                "actor_type": "system",
            },
            storage_root=storage_root,
        )
        seeded.append(artifact["artifact_version"])
    return seeded


def _ingest_fixture(
    connection: sqlite3.Connection,
    *,
    corpus: ExampleDocumentCorpus,
    workflow_run_id: str,
    fixture_id: str,
    pilot_key: str,
    pilot_id: str,
    artifact_suffix: str,
    storage_root: Path,
    task_run_id: str | None = None,
    human_task_id: str | None = None,
    artifact_role: str | None = None,
    metadata_json: dict[str, Any] | None = None,
    supersedes_artifact_version_id: str | None = None,
) -> dict[str, Any]:
    document = corpus.document_by_id(fixture_id)
    metadata = {
        "fixture_id": fixture_id,
        "corpus_id": corpus.corpus_id,
        "corpus_version": corpus.version,
        "category": document.category,
        "description": document.description,
        "pilot_key": pilot_key,
        "pilot_id": pilot_id,
    }
    if metadata_json is not None:
        metadata.update(metadata_json)

    result = ingest_artifact_document_command(
        connection,
        {
            "artifact_version_id": _deterministic_id(
                "av",
                pilot_key,
                pilot_id,
                artifact_suffix,
            ),
            "workflow_run_id": workflow_run_id,
            "task_run_id": task_run_id,
            "artifact_kind": document.artifact_kind,
            "artifact_role": artifact_role if artifact_role is not None else document.artifact_role,
            "media_type": document.media_type,
            "source_path": str(document.source_path),
            "file_name": document.source_path.name,
            "metadata_json": metadata,
            "supersedes_artifact_version_id": supersedes_artifact_version_id,
            "links": (
                [
                    {
                        "subject_kind": "human_task",
                        "subject_id": human_task_id,
                        "relation_kind": "attachment",
                    }
                ]
                if human_task_id is not None
                else None
            ),
            "idempotency_key": f"pilot:{pilot_key}:{pilot_id}:artifacts.ingest:{artifact_suffix}",
            "actor_id": "system:pilot-runner",
            "actor_type": "system",
        },
        storage_root=storage_root,
    )
    return result["artifact_version"]


def _create_json_draft_artifact(
    connection: sqlite3.Connection,
    *,
    workflow_run_id: str,
    task_run_id: str,
    artifact_kind: str,
    artifact_suffix: str,
    pilot_key: str,
    pilot_id: str,
    storage_root: Path,
    payload: dict[str, Any],
) -> dict[str, Any]:
    metadata = {
        "pilot_key": pilot_key,
        "pilot_id": pilot_id,
        "lifecycle": "draft",
        "is_draft": True,
        **payload,
    }
    result = ingest_artifact_document_command(
        connection,
        {
            "artifact_version_id": _deterministic_id("av", pilot_key, pilot_id, artifact_suffix),
            "workflow_run_id": workflow_run_id,
            "task_run_id": task_run_id,
            "artifact_kind": artifact_kind,
            "artifact_role": "draft_output",
            "content_base64": encode_base64_content(
                json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8")
            ),
            "file_name": f"{artifact_suffix}.json",
            "media_type": "application/json",
            "metadata_json": metadata,
            "idempotency_key": f"pilot:{pilot_key}:{pilot_id}:artifacts.ingest:{artifact_suffix}",
            "actor_id": "agent:pilot-draft-generator",
            "actor_type": "agent",
        },
        storage_root=storage_root,
    )
    return result["artifact_version"]


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
        claimed = claim_human_task_command(
            connection,
            {
                "human_task_id": human_task_id,
                "actor_id": actor_id,
                "actor_type": actor_type,
                "lease_seconds": 300,
                "idempotency_key": idempotency_key,
            },
        )
        return claimed
    if state == "CLAIMED":
        if str(current.get("assignee_actor_id") or "") != actor_id:
            raise CommandError(
                code="pilot_claim_conflict",
                message="human task already claimed by a different actor",
                details={
                    "human_task_id": human_task_id,
                    "assignee_actor_id": current.get("assignee_actor_id"),
                    "actor_id": actor_id,
                },
            )
        return current
    return current


def _quality_signals(
    *,
    pilot_id: str,
    tasks: list[dict[str, Any]],
    approvals: list[dict[str, Any]],
    flags: list[dict[str, Any]],
    pointers: list[dict[str, Any]],
    sessions: list[dict[str, Any]],
    tool_executions: list[dict[str, Any]],
    policy_decisions: list[dict[str, Any]],
    timeline_of_interest: list[dict[str, Any]],
) -> dict[str, Any]:
    signals: dict[str, Any] = {
        "task_count": len(tasks),
        "approval_count": len(approvals),
        "flag_count": len(flags),
        "pointer_count": len(pointers),
        "execution_session_count": len(sessions),
        "tool_execution_count": len(tool_executions),
        "policy_decision_count": len(policy_decisions),
        "timeline_events_of_interest_count": len(timeline_of_interest),
    }
    if pilot_id in {PILOT_STAGE06_PUBLISH_READY, PILOT_STAGE06_NEEDS_INFORMATION}:
        signals["stage06_execution_runtime_present"] = bool(sessions and tool_executions and policy_decisions)
        signals["stage06_evidence_artifact_present"] = any(
            str(item.get("artifact_kind")) == "schedule.stage06.review_ai_evidence.json"
            for item in _artifacts_from_timeline(timeline_of_interest)
        )
    if pilot_id == PILOT_STAGE06_PUBLISH_READY:
        signals["stage06_publish_pointer_present"] = any(
            str(item.get("pointer_key")) == "official:schedule.published_schedule.workbook"
            for item in pointers
        )
    if pilot_id == PILOT_STAGE07_ISSUE_REPLAN:
        signals["stage07_flag_resolved"] = any(str(item.get("state")) == "resolved" for item in flags)
        signals["stage07_delta_pointer_present"] = any(
            str(item.get("pointer_key")) == "official:schedule.replan_delta.workbook"
            for item in pointers
        )
    return signals


def _artifacts_from_timeline(events: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for event in events:
        if str(event.get("event_type")) != "artifact.version.created":
            continue
        payload = event.get("payload")
        if isinstance(payload, dict):
            rows.append(payload)
    return rows


def _inspection_routes(
    *,
    workflow_run_id: str,
    approvals: list[dict[str, Any]],
    flags: list[dict[str, Any]],
    tasks: list[dict[str, Any]],
    artifacts: list[dict[str, Any]],
    pointers: list[dict[str, Any]],
) -> dict[str, Any]:
    ui_routes = [
        f"/board?workflow_run_id={workflow_run_id}",
        f"/runs/{workflow_run_id}",
        f"/timeline?workflow_run_id={workflow_run_id}",
        f"/official-outputs?workflow_run_id={workflow_run_id}",
        f"/approvals?workflow_run_id={workflow_run_id}",
        f"/exceptions?workflow_run_id={workflow_run_id}",
    ]

    api_routes = [
        f"/api/v1/workflow-runs/{workflow_run_id}",
        f"/api/v1/board/schedule-planning?workflow_run_id={workflow_run_id}",
        f"/api/v1/timeline-events?workflow_run_id={workflow_run_id}",
        f"/api/v1/human-tasks?workflow_run_id={workflow_run_id}",
        f"/api/v1/approvals?workflow_run_id={workflow_run_id}",
        f"/api/v1/flags?workflow_run_id={workflow_run_id}",
        f"/api/v1/artifacts?workflow_run_id={workflow_run_id}",
        f"/api/v1/pointers?workflow_run_id={workflow_run_id}",
    ]

    api_routes.extend(
        f"/api/v1/approvals/{approval['approval_id']}" for approval in approvals
    )
    api_routes.extend(f"/api/v1/flags/{flag['flag_id']}" for flag in flags)
    api_routes.extend(f"/api/v1/human-tasks/{task['human_task_id']}" for task in tasks)
    api_routes.extend(
        f"/api/v1/artifacts/{artifact['artifact_version_id']}" for artifact in artifacts
    )
    api_routes.extend(
        f"/api/v1/workflow-runs/{workflow_run_id}/artifacts"
        for _ in pointers
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
        f"# Inspection Packet: {packet['pilot_id']}",
        "",
        f"- Pilot key: `{packet['pilot_key']}`",
        f"- Workflow run: `{workflow_run['workflow_run_id']}`",
        f"- Stage focus: `{packet['stage_focus']}`",
        f"- Seed set: `{packet['seed_set_id']}`",
        f"- Reused existing run: `{packet['reused_existing']}`",
        "",
        "## Canonical references",
        f"- Artifacts: {len(linked['artifact_version_ids'])}",
        f"- Pointers: {len(linked['pointer_keys'])}",
        f"- Approvals: {len(linked['approval_ids'])}",
        f"- Flags: {len(linked['flag_ids'])}",
        f"- Execution sessions: {len(linked['execution_session_ids'])}",
        f"- Tool executions: {len(linked['tool_execution_ids'])}",
        f"- Policy decisions: {len(linked['policy_decision_ids'])}",
        "",
        "## Timeline",
        f"- Total events: {packet['timeline']['event_count']}",
        f"- Events of interest: {len(packet['timeline']['events_of_interest'])}",
        "",
        "## Inspection routes",
    ]
    lines.extend(f"- UI: `{route}`" for route in packet["inspection"]["ui_routes"])
    lines.extend(f"- API: `{route}`" for route in packet["inspection"]["api_routes"])
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
        "# Schedule Planning Pilot Summary",
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
