from __future__ import annotations

from .shared import CapabilityDecision, allow, deny, reason


def upload_decision() -> CapabilityDecision:
    return allow("artifact.upload")


def download_decision(*, linked_artifact_count: int) -> CapabilityDecision:
    if linked_artifact_count > 0:
        return allow("artifact.download")
    return deny(
        "artifact.download",
        reasons=[reason("no_linked_artifacts", linked_artifact_count=linked_artifact_count)],
    )
