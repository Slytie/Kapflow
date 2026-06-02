from __future__ import annotations

from typing import Any

from onetruth.application.services.task_requirements import (
    REVIEW_CONFIRMATION_ARTIFACT_KIND,
)


def latest_review_confirmation_for_human_task(
    *,
    artifacts: list[dict[str, Any]],
    human_task_id: str,
) -> dict[str, Any] | None:
    latest: dict[str, Any] | None = None
    for artifact in artifacts:
        if str(artifact.get("artifact_kind") or "") != REVIEW_CONFIRMATION_ARTIFACT_KIND:
            continue
        metadata = artifact.get("metadata_json")
        if not isinstance(metadata, dict):
            continue
        if str(metadata.get("human_task_id") or "") != human_task_id:
            continue
        latest = artifact
    return latest


def reviewed_artifact_id_from_confirmation(
    *,
    artifacts: list[dict[str, Any]],
    review_confirmation: dict[str, Any] | None,
    artifact_kind: str,
) -> str | None:
    if review_confirmation is None:
        return None
    metadata = review_confirmation.get("metadata_json")
    if not isinstance(metadata, dict):
        return None
    reviewed_ids = metadata.get("reviewed_artifact_version_ids")
    if not isinstance(reviewed_ids, list):
        return None
    artifacts_by_id = {
        str(artifact.get("artifact_version_id")): artifact for artifact in artifacts
    }
    for raw_reviewed_id in reviewed_ids:
        reviewed_id = str(raw_reviewed_id or "").strip()
        if not reviewed_id:
            continue
        artifact = artifacts_by_id.get(reviewed_id)
        if artifact is None:
            continue
        if str(artifact.get("artifact_kind") or "") == artifact_kind:
            return reviewed_id
    return None
