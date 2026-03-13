from __future__ import annotations

import sqlite3
from typing import Any, Iterable

from onetruth.application.services.capabilities import (
    DecisionReason,
    Principal,
    claim_decision,
    complete_decision,
    confirm_review_decision,
    download_decision,
    execute_stage06_agent_review_decision,
    execute_weekly_stage04_openai_agent_decision,
    legacy_reason_codes,
    project_available_actions,
    respond_decision,
    transition_decision,
    upload_decision,
)


def build_artifact_link_count_index(
    connection: sqlite3.Connection,
    *,
    workflow_run_id: str,
) -> dict[tuple[str, str], int]:
    rows = connection.execute(
        """
        SELECT
            subject_kind,
            subject_id,
            COUNT(*) AS linked_artifact_count
        FROM artifact_links
        WHERE workflow_run_id = ?
        GROUP BY subject_kind, subject_id
        """,
        (workflow_run_id,),
    ).fetchall()
    index: dict[tuple[str, str], int] = {}
    for row in rows:
        key = (str(row["subject_kind"]), str(row["subject_id"]))
        index[key] = int(row["linked_artifact_count"])
    return index


def compute_human_task_actionability(
    *,
    task: dict[str, Any],
    actor_id: str,
    actor_type: str,
    actor_roles: tuple[str, ...],
    linked_artifact_count: int,
    requirement_state: dict[str, Any] | None = None,
) -> dict[str, Any]:
    principal = Principal(
        actor_id=actor_id,
        actor_type=actor_type,
        actor_roles=actor_roles,
    )
    state = str(task.get("state") or "")
    required_uploads = list((requirement_state or {}).get("required_uploads") or [])
    required_reviews = list((requirement_state or {}).get("required_reviews") or [])
    requirement_reasons = _requirement_reasons(requirement_state)
    missing_required_inputs = list((requirement_state or {}).get("missing_required_inputs") or [])
    has_pending_review_confirmation = any(
        isinstance(review, dict) and str(review.get("status") or "") == "pending_confirmation"
        for review in required_reviews
    )

    claim = claim_decision(task=task, principal=principal)
    complete = complete_decision(
        task=task,
        principal=principal,
        requirement_reasons=requirement_reasons,
    )
    confirm_review = confirm_review_decision(
        task=task,
        principal=principal,
        has_pending_review_confirmation=has_pending_review_confirmation,
    )
    stage06_execute = execute_stage06_agent_review_decision(
        task=task,
        principal=principal,
    )
    weekly_stage04_execute = execute_weekly_stage04_openai_agent_decision(
        task=task,
        principal=principal,
    )
    upload = upload_decision()
    download = download_decision(linked_artifact_count=linked_artifact_count)

    blocking_requirements = _task_blocking_requirements(
        required_uploads=required_uploads,
        required_reviews=required_reviews,
        claim=claim,
        complete=complete,
    )
    blocking_reason_codes = legacy_reason_codes(requirement_reasons)
    if state == "OPEN":
        candidate_role_mismatch = _find_reason(claim.reasons, "candidate_role_mismatch")
        if candidate_role_mismatch is not None:
            blocking_reason_codes.extend(
                _dedup_codes(legacy_reason_codes([candidate_role_mismatch]), blocking_reason_codes)
            )
    claimed_by_other_actor = _find_reason(complete.reasons, "claimed_by_other_actor")
    if claimed_by_other_actor is not None:
        blocking_reason_codes.extend(
            _dedup_codes(legacy_reason_codes([claimed_by_other_actor]), blocking_reason_codes)
        )

    available_actions = project_available_actions(
        [
            ("claim", claim),
            ("confirm_review", confirm_review),
            ("complete", complete),
            ("run_stage06_agent_review", stage06_execute),
            ("run_weekly_stage04_openai_agent", weekly_stage04_execute),
            ("upload_attachment", upload),
            ("download_attachments", download),
        ]
    )

    return {
        "available_actions": available_actions,
        "blocking_requirements": blocking_requirements,
        "required_uploads": required_uploads,
        "required_reviews": required_reviews,
        "blocking_reason_codes": blocking_reason_codes,
        "linked_artifact_count": linked_artifact_count,
        "missing_required_inputs": missing_required_inputs,
        "can_complete": complete.allowed,
        "can_confirm_review": confirm_review.allowed,
        "can_upload_attachment": upload.allowed,
        "can_run_stage06_agent_review": stage06_execute.allowed,
        "can_run_weekly_stage04_openai_agent": weekly_stage04_execute.allowed,
    }


def compute_approval_actionability(
    *,
    approval: dict[str, Any],
    actor_roles: tuple[str, ...],
    linked_artifact_count: int,
) -> dict[str, Any]:
    principal = Principal(
        actor_id="",
        actor_type="human",
        actor_roles=actor_roles,
    )
    respond = respond_decision(approval=approval, principal=principal)
    upload = upload_decision()
    download = download_decision(linked_artifact_count=linked_artifact_count)

    blocking_requirements: list[dict[str, Any]] = []
    role_mismatch = _find_reason(respond.reasons, "approval_role_mismatch")
    if role_mismatch is not None:
        blocking_requirements.append(
            {
                "requirement": "approval_role_match",
                "required_role": role_mismatch.details.get("required_role"),
                "candidate_roles": list(role_mismatch.details.get("candidate_roles") or []),
                "actor_roles": list(role_mismatch.details.get("actor_roles") or []),
                "status": "missing",
            }
        )

    available_actions = project_available_actions(
        [
            ("respond", respond),
            ("upload_attachment", upload),
            ("download_attachments", download),
        ]
    )

    return {
        "available_actions": available_actions,
        "blocking_requirements": blocking_requirements,
        "required_uploads": [],
        "required_reviews": [],
        "blocking_reason_codes": [],
        "linked_artifact_count": linked_artifact_count,
        "missing_required_inputs": [],
        "can_complete": False,
        "can_confirm_review": False,
        "can_upload_attachment": upload.allowed,
        "can_run_stage06_agent_review": False,
        "can_run_weekly_stage04_openai_agent": False,
    }


def compute_flag_actionability(
    *,
    flag: dict[str, Any],
    actor_roles: tuple[str, ...],
    linked_artifact_count: int,
) -> dict[str, Any]:
    principal = Principal(
        actor_id="",
        actor_type="human",
        actor_roles=actor_roles,
    )
    transition = transition_decision(flag=flag, principal=principal)
    upload = upload_decision()
    download = download_decision(linked_artifact_count=linked_artifact_count)

    available_actions = project_available_actions(
        [
            ("transition", transition),
            ("upload_attachment", upload),
            ("download_attachments", download),
        ]
    )

    return {
        "available_actions": available_actions,
        "blocking_requirements": [],
        "required_uploads": [],
        "required_reviews": [],
        "blocking_reason_codes": [],
        "linked_artifact_count": linked_artifact_count,
        "missing_required_inputs": [],
        "can_complete": False,
        "can_confirm_review": False,
        "can_upload_attachment": upload.allowed,
        "can_run_stage06_agent_review": False,
        "can_run_weekly_stage04_openai_agent": False,
    }


def _task_blocking_requirements(
    *,
    required_uploads: list[dict[str, Any]],
    required_reviews: list[dict[str, Any]],
    claim,
    complete,
) -> list[dict[str, Any]]:
    blocking_requirements: list[dict[str, Any]] = []
    for upload in required_uploads:
        if not isinstance(upload, dict):
            continue
        blocking_requirements.append(
            {
                "requirement": "required_upload",
                "dataset_key": upload.get("dataset_key"),
                "template_id": upload.get("template_id"),
                "artifact_kind": upload.get("artifact_kind"),
                "required_count": upload.get("required_count"),
                "current_count": upload.get("current_count"),
                "status": upload.get("status"),
            }
        )
    for review in required_reviews:
        if not isinstance(review, dict):
            continue
        blocking_requirements.append(
            {
                "requirement": "required_review",
                "artifact_kind": review.get("artifact_kind"),
                "reviewed_artifact_version_id": review.get("reviewed_artifact_version_id"),
                "review_confirmation_artifact_version_id": review.get("review_confirmation_artifact_version_id"),
                "status": review.get("status"),
            }
        )

    candidate_role_mismatch = _find_reason(claim.reasons, "candidate_role_mismatch")
    if candidate_role_mismatch is not None:
        blocking_requirements.append(
            {
                "requirement": "candidate_role_match",
                "candidate_roles": list(candidate_role_mismatch.details.get("candidate_roles") or []),
                "actor_roles": list(candidate_role_mismatch.details.get("actor_roles") or []),
                "status": "missing",
            }
        )

    claimed_by_other_actor = _find_reason(complete.reasons, "claimed_by_other_actor")
    if claimed_by_other_actor is not None:
        blocking_requirements.append(
            {
                "requirement": "claimed_by_other_actor",
                "assignee_actor_id": claimed_by_other_actor.details.get("assignee_actor_id"),
                "assignee_actor_type": claimed_by_other_actor.details.get("assignee_actor_type"),
                "status": "missing",
            }
        )

    return blocking_requirements


def _requirement_reasons(
    requirement_state: dict[str, Any] | None,
) -> tuple[DecisionReason, ...]:
    if not requirement_state:
        return ()
    structured = requirement_state.get("blocking_reasons")
    if isinstance(structured, list):
        reasons: list[DecisionReason] = []
        for item in structured:
            if not isinstance(item, dict):
                continue
            code = str(item.get("code") or "").strip()
            if not code:
                continue
            details = item.get("details")
            reasons.append(
                DecisionReason(
                    code=code,
                    details=details if isinstance(details, dict) else {},
                )
            )
        if reasons:
            return tuple(reasons)

    legacy_codes = requirement_state.get("blocking_reason_codes")
    if not isinstance(legacy_codes, list):
        return ()
    parsed: list[DecisionReason] = []
    for raw_code in legacy_codes:
        parsed_reason = _parse_legacy_reason(str(raw_code))
        if parsed_reason is not None:
            parsed.append(parsed_reason)
    return tuple(parsed)


def _parse_legacy_reason(raw_code: str) -> DecisionReason | None:
    if not raw_code:
        return None
    if raw_code.startswith("required_upload_missing:"):
        dataset_key = raw_code.split(":", 1)[1]
        return DecisionReason(
            code="required_upload_missing",
            details={"dataset_key": dataset_key},
        )
    if raw_code.startswith("required_review_confirmation_missing:"):
        artifact_kind = raw_code.split(":", 1)[1]
        return DecisionReason(
            code="required_review_confirmation_missing",
            details={"artifact_kind": artifact_kind},
        )
    return DecisionReason(code=raw_code, details={})


def _find_reason(
    reasons: Iterable[DecisionReason],
    code: str,
) -> DecisionReason | None:
    for reason_item in reasons:
        if reason_item.code == code:
            return reason_item
    return None


def _dedup_codes(new_codes: Iterable[str], existing_codes: list[str]) -> list[str]:
    seen = set(existing_codes)
    return [code for code in new_codes if code not in seen]
