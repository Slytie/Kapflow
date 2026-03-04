from __future__ import annotations

import hashlib
import html
import io
import json
import os
from pathlib import Path
import re
import sqlite3
from typing import Any
import zipfile

from onetruth.application.handlers.workflow_task_lifecycle import (
    CommandError,
    complete_tool_execution_command,
    create_execution_session_command,
    complete_human_task_command,
    create_artifact_version_command,
    evaluate_policy_decision_command,
    request_tool_execution_command,
    transition_execution_session_state_command,
)
from onetruth.infrastructure.artifacts.storage import read_blob, write_blob
from onetruth.infrastructure.repositories.artifact_versions import (
    list_artifact_versions_for_workflow_run,
)
from onetruth.infrastructure.repositories.human_tasks import get_human_task
from onetruth.infrastructure.repositories.task_runs import get_task_run
from onetruth.infrastructure.repositories.execution_sessions import get_execution_session
from onetruth.integrations.openai import (
    OpenAIResponseMetadata,
    Stage06ReviewClassification,
    Stage06ReviewClassifier,
    build_stage06_review_classifier_from_env,
)

EVIDENCE_ARTIFACT_KIND = "schedule.stage06.review_ai_evidence.json"
EVIDENCE_ARTIFACT_ROLE = "agent_evidence"
EXECUTION_SPEC_ID = "schedule_planning.stage06.openai_review.v1"
OPENAI_TOOL_CLASS = "model.openai.responses.stage06.review"


def run_stage06_openai_review_sandbox(
    connection: sqlite3.Connection,
    payload: dict[str, Any],
    *,
    classifier: Stage06ReviewClassifier | None = None,
) -> dict[str, Any]:
    _require_fields(
        payload,
        ["human_task_id", "actor_id", "actor_type", "idempotency_key"],
    )

    human_task_id = str(payload["human_task_id"])
    actor_id = str(payload["actor_id"])
    actor_type = str(payload["actor_type"])
    base_idempotency_key = str(payload["idempotency_key"])
    actor_roles = _normalize_actor_roles(payload.get("actor_roles"))

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

    if str(task_run.get("stage_id")) != "Stage06" or str(task_run.get("task_kind")) != "review_packet":
        raise CommandError(
            code="invalid_stage06_sandbox_task",
            message="stage06 sandbox is only allowed for Stage06 review_packet tasks",
            details={
                "human_task_id": human_task_id,
                "stage_id": str(task_run.get("stage_id")),
                "task_kind": str(task_run.get("task_kind")),
            },
        )

    execution_session_id = _stable_id(
        "xs",
        f"{human_task['workflow_run_id']}:{human_task['task_run_id']}:{base_idempotency_key}",
    )
    tool_execution_id = _stable_id(
        "tx",
        f"{execution_session_id}:{OPENAI_TOOL_CLASS}:{base_idempotency_key}",
    )
    policy_decision_id = _stable_id(
        "pd",
        f"{tool_execution_id}:{base_idempotency_key}",
    )

    existing_session = get_execution_session(connection, execution_session_id)
    if existing_session is not None:
        raise CommandError(
            code="duplicate_execution_request",
            message="execution session already exists for idempotent Stage06 sandbox request",
            details={
                "execution_session_id": execution_session_id,
                "state": str(existing_session.get("state")),
            },
        )

    if str(human_task.get("state")) != "CLAIMED":
        raise CommandError(
            code="task_not_completable",
            message="human task must be claimed before sandbox completion",
            details={"human_task_id": human_task_id, "state": str(human_task.get("state"))},
        )

    if str(human_task.get("assignee_actor_id") or "") != actor_id:
        raise CommandError(
            code="task_not_completable",
            message="human task must be claimed by requesting actor",
            details={
                "human_task_id": human_task_id,
                "assignee_actor_id": human_task.get("assignee_actor_id"),
                "actor_id": actor_id,
            },
        )

    execution_session = create_execution_session_command(
        connection,
        {
            "execution_session_id": execution_session_id,
            "workflow_run_id": str(human_task["workflow_run_id"]),
            "task_run_id": str(human_task["task_run_id"]),
            "execution_spec_id": EXECUTION_SPEC_ID,
            "owner_mode": "agent",
            "state": "RUNNING",
            "principal_actor": {"type": actor_type, "id": actor_id},
            "budget": {"max_tool_calls": 1, "max_wall_time_seconds": 120},
            "idempotency_key": f"{base_idempotency_key}:execution-session",
            "actor_id": actor_id,
            "actor_type": actor_type,
        },
    )

    tool_execution = request_tool_execution_command(
        connection,
        {
            "tool_execution_id": tool_execution_id,
            "execution_session_id": execution_session_id,
            "tool_class": OPENAI_TOOL_CLASS,
            "tool_name": "stage06_review_classifier",
            "idempotency_key": f"{base_idempotency_key}:tool-request",
            "actor_id": actor_id,
            "actor_type": actor_type,
        },
    )

    decision, reason_code, required_approval_action = _evaluate_stage06_policy(
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
    if decision != "allow":
        code = "tool_execution_requires_approval" if decision == "require_approval" else "tool_execution_denied"
        raise CommandError(
            code=code,
            message="policy denied Stage06 sandbox model execution",
            details={
                "execution_session_id": execution_session_id,
                "tool_execution_id": tool_execution_id,
                "policy_decision_id": policy_decision_id,
                "decision": decision,
                "reason_code": reason_code,
                "required_approval_action": required_approval_action,
            },
        )

    artifacts = list_artifact_versions_for_workflow_run(
        connection,
        str(human_task["workflow_run_id"]),
    )
    input_artifacts = _resolve_input_artifacts(artifacts)
    if not input_artifacts:
        raise CommandError(
            code="stage06_sandbox_input_artifact_missing",
            message="no Stage06 input artifacts were available for sandbox classification",
            details={
                "workflow_run_id": str(human_task["workflow_run_id"]),
                "required_artifact_kind": "schedule.supervisor_review.doc",
            },
        )

    primary_artifact = input_artifacts[0]
    document_text = _extract_document_text(primary_artifact)
    if not document_text.strip():
        raise CommandError(
            code="stage06_sandbox_input_unreadable",
            message="Stage06 input artifact did not yield readable text",
            details={
                "artifact_version_id": str(primary_artifact["artifact_version_id"]),
                "media_type": str(primary_artifact["media_type"]),
            },
        )

    selected_classifier = classifier or build_stage06_review_classifier_from_env()
    instruction_context = {
        "workflow_run_id": str(human_task["workflow_run_id"]),
        "task_run_id": str(human_task["task_run_id"]),
        "human_task_id": human_task_id,
        "stage_id": str(task_run.get("stage_id")),
        "task_kind": str(task_run.get("task_kind")),
    }
    artifact_context = [
        {
            "artifact_version_id": str(item["artifact_version_id"]),
            "artifact_kind": str(item["artifact_kind"]),
            "media_type": str(item["media_type"]),
            "content_digest": str(item["content_digest"]),
            "metadata_json": item.get("metadata_json") if isinstance(item.get("metadata_json"), dict) else {},
        }
        for item in input_artifacts
    ]

    try:
        classification, model_metadata = selected_classifier.classify_stage06_review(
            instruction_context=instruction_context,
            artifact_context=artifact_context,
            document_text=document_text,
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

    evidence_payload = _build_evidence_payload(
        classification=classification,
        model_metadata=model_metadata,
        instruction_context=instruction_context,
        artifact_context=artifact_context,
        input_excerpt_char_count=len(document_text),
    )

    storage_root = _artifact_root()
    evidence_storage_uri, evidence_digest, evidence_size = write_blob(
        storage_root=storage_root,
        workflow_run_id=str(human_task["workflow_run_id"]),
        file_name=f"stage06-review-openai-{human_task_id}.json",
        content=json.dumps(evidence_payload, separators=(",", ":"), sort_keys=True).encode("utf-8"),
    )

    evidence_create = create_artifact_version_command(
        connection,
        {
            "workflow_run_id": str(human_task["workflow_run_id"]),
            "task_run_id": str(human_task["task_run_id"]),
            "artifact_kind": EVIDENCE_ARTIFACT_KIND,
            "artifact_role": EVIDENCE_ARTIFACT_ROLE,
            "media_type": "application/json",
            "storage_uri": evidence_storage_uri,
            "content_digest": evidence_digest,
            "byte_size": evidence_size,
            "metadata_json": {
                "source": "stage06_openai_sandbox",
                "classification_outcome": classification.outcome,
                "openai_model": model_metadata.model,
                "openai_response_id": model_metadata.response_id,
                "openai_request_id": model_metadata.request_id,
                "input_artifact_version_ids": [
                    str(item["artifact_version_id"]) for item in input_artifacts
                ],
                "execution_session_id": execution_session_id,
                "tool_execution_id": tool_execution_id,
                "policy_decision_id": policy_decision_id,
            },
            "idempotency_key": f"{base_idempotency_key}:stage06.openai.evidence",
            "actor_id": actor_id,
            "actor_type": actor_type,
        },
    )

    tool_execution = complete_tool_execution_command(
        connection,
        {
            "tool_execution_id": tool_execution_id,
            "result": "succeeded",
            "output_artifact_version_ids": [str(evidence_create["artifact_version_id"])],
            "idempotency_key": f"{base_idempotency_key}:tool-complete",
            "actor_id": actor_id,
            "actor_type": actor_type,
        },
    )

    try:
        completion_result = complete_human_task_command(
            connection,
            {
                "human_task_id": human_task_id,
                "actor_id": actor_id,
                "actor_type": actor_type,
                "outcome": classification.outcome,
                "idempotency_key": f"{base_idempotency_key}:stage06.openai.complete",
            },
        )
    except Exception as exc:
        transition_execution_session_state_command(
            connection,
            {
                "execution_session_id": execution_session_id,
                "to_state": "FAILED",
                "reason": "workflow_transition_failed",
                "idempotency_key": f"{base_idempotency_key}:session-failed",
                "actor_id": actor_id,
                "actor_type": actor_type,
            },
        )
        raise exc

    execution_session = transition_execution_session_state_command(
        connection,
        {
            "execution_session_id": execution_session_id,
            "to_state": "SUCCEEDED",
            "reason": "workflow_transition_completed",
            "idempotency_key": f"{base_idempotency_key}:session-succeeded",
            "actor_id": actor_id,
            "actor_type": actor_type,
        },
    )

    return {
        "classification": classification.as_dict(),
        "model_metadata": model_metadata.as_dict(),
        "input_artifacts": artifact_context,
        "execution_session": execution_session,
        "tool_execution": tool_execution,
        "policy_decision": policy_decision,
        "evidence_artifact": evidence_create,
        "completion_result": completion_result,
    }


def _require_fields(payload: dict[str, Any], fields: list[str]) -> None:
    missing = [field for field in fields if payload.get(field) is None]
    if missing:
        raise CommandError(
            code="invalid_payload",
            message=f"missing required fields: {', '.join(missing)}",
            details={"missing_fields": missing},
        )


def _artifact_root() -> Path:
    raw = os.environ.get("ONETRUTH_ARTIFACT_ROOT", ".onetruth_artifacts").strip()
    path = Path(raw).expanduser().resolve()
    path.mkdir(parents=True, exist_ok=True)
    return path


def _resolve_input_artifacts(artifacts: list[dict[str, Any]]) -> list[dict[str, Any]]:
    preferred_order = [
        "schedule.supervisor_review.doc",
        "schedule.draft_schedule.doc",
        "schedule.draft_schedule.workbook",
    ]

    by_kind: dict[str, dict[str, Any]] = {}
    for artifact in artifacts:
        kind = str(artifact.get("artifact_kind") or "")
        if kind not in preferred_order:
            continue
        by_kind[kind] = artifact

    return [by_kind[kind] for kind in preferred_order if kind in by_kind]


def _extract_document_text(artifact: dict[str, Any]) -> str:
    media_type = str(artifact.get("media_type") or "")
    storage_uri = str(artifact.get("storage_uri") or "")
    content = read_blob(storage_uri)

    if media_type in {
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "application/msword",
    }:
        return _extract_docx_text(content)

    decoded = content.decode("utf-8", errors="ignore")
    return _compact_whitespace(decoded)


def _extract_docx_text(content: bytes) -> str:
    try:
        with zipfile.ZipFile(io.BytesIO(content), "r") as archive:
            raw_xml = archive.read("word/document.xml").decode("utf-8", errors="ignore")
    except Exception as exc:
        raise CommandError(
            code="stage06_sandbox_input_unreadable",
            message="unable to parse DOCX artifact content",
            details={"error": exc.__class__.__name__},
        ) from exc

    no_tags = re.sub(r"<[^>]+>", " ", raw_xml)
    return _compact_whitespace(html.unescape(no_tags))


def _compact_whitespace(text: str) -> str:
    return " ".join(text.split())


def _build_evidence_payload(
    *,
    classification: Stage06ReviewClassification,
    model_metadata: OpenAIResponseMetadata,
    instruction_context: dict[str, Any],
    artifact_context: list[dict[str, Any]],
    input_excerpt_char_count: int,
) -> dict[str, Any]:
    return {
        "schema_version": "1.0",
        "kind": "stage06_openai_review_sandbox_evidence",
        "sandbox_path": "stage06.review_outcome_classification",
        "instruction_context": instruction_context,
        "artifact_context": artifact_context,
        "input_excerpt_char_count": input_excerpt_char_count,
        "classification": classification.as_dict(),
        "model_metadata": model_metadata.as_dict(),
    }


def _stable_id(prefix: str, raw: str) -> str:
    digest = hashlib.sha256(raw.encode("utf-8")).hexdigest()[:24]
    return f"{prefix}-{digest}"


def _normalize_actor_roles(raw_roles: Any) -> list[str]:
    if not isinstance(raw_roles, (list, tuple, set)):
        return []
    return [str(role) for role in raw_roles if str(role).strip()]


def _evaluate_stage06_policy(
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
            return "require_approval", "override_require_approval", "stage06.review.openai_execution"
        return "deny", "override_deny", None

    env_decision = os.environ.get("ONETRUTH_STAGE06_POLICY_DECISION", "").strip()
    if env_decision:
        if env_decision not in {"allow", "deny", "require_approval"}:
            raise CommandError(
                code="invalid_policy_decision",
                message=f"unsupported ONETRUTH_STAGE06_POLICY_DECISION value: {env_decision}",
                details={"allowed_decisions": ["allow", "deny", "require_approval"]},
            )
        if env_decision == "allow":
            return "allow", "env_allow", None
        if env_decision == "require_approval":
            return "require_approval", "env_require_approval", "stage06.review.openai_execution"
        return "deny", "env_deny", None

    allowed_roles = {"dispatch_supervisor", "operations_manager", "system_worker"}
    if actor_type in {"system", "service"} or any(role in allowed_roles for role in actor_roles):
        return "allow", "role_allow", None
    return "deny", "actor_role_not_allowed", None


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
