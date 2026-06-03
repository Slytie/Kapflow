"""Illustrative AI context eligibility gate."""

from __future__ import annotations


ALLOWED_AI_REVIEW_STATES = {
    "pm_reviewed_for_ai",
    "baseline_candidate",
    "reviewed_baseline",
}


def eligible_versions_for_ai(project_id):
    return (
        SourceDocumentVersion.objects
        .filter(
            project_id=project_id,
            occurrence__quarantine_state="cleared",
            occurrence__review_state__in=ALLOWED_AI_REVIEW_STATES,
            license_state="allows_ai_use",
            security_hold=False,
            leak_scan_status="passed",
        )
        .select_related("occurrence")
    )


def assert_ai_context_allowed(version) -> None:
    occurrence = version.occurrence
    if occurrence.quarantine_state != "cleared":
        raise PermissionError("AI_CONTEXT_BLOCKED_QUARANTINE")
    if occurrence.review_state not in ALLOWED_AI_REVIEW_STATES:
        raise PermissionError("AI_CONTEXT_BLOCKED_REVIEW_STATE")
    if version.license_state != "allows_ai_use":
        raise PermissionError("AI_CONTEXT_BLOCKED_LICENSE")
    if version.security_hold:
        raise PermissionError("AI_CONTEXT_BLOCKED_SECURITY_HOLD")
    if version.leak_scan_status != "passed":
        raise PermissionError("AI_CONTEXT_BLOCKED_LEAK_SCAN")


def log_llm_call(*, prompt: str, safe_metadata: dict) -> None:
    # Never log full prompt if it can contain source content.
    logger.info("llm_call", extra={"safe_metadata": safe_metadata})
