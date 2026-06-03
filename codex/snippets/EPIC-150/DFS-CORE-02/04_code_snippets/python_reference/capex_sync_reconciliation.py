"""
CAPEX DFS-CORE-02 reference implementation sketch.

This module is intentionally small enough for Codex to translate into the
CAPEX service layer. It models filesystem observations as candidate deltas;
it never mutates governed evidence state.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Iterable, Optional
from uuid import uuid4


class SnapshotStatus(str, Enum):
    COMPLETE = "complete"
    PARTIAL = "partial"
    FAILED = "failed"


class ObservationStatus(str, Enum):
    OBSERVED = "observed"
    UNOBSERVED_PARENT_UNREACHABLE = "unobserved_parent_unreachable"
    SCAN_ERROR = "scan_error"
    IGNORED = "ignored"
    UNSUPPORTED = "unsupported"
    TRANSIENT = "transient"


class DeltaType(str, Enum):
    ADDED = "added"
    MODIFIED = "modified"
    MOVED_CANDIDATE = "moved_candidate"
    RENAMED_CANDIDATE = "renamed_candidate"
    DELETED_FROM_SOURCE = "deleted_from_source"
    DUPLICATE_SEEN = "duplicate_seen"
    CONFLICT_CANDIDATE = "conflict_candidate"
    OBSERVATION_INCOMPLETE = "observation_incomplete"
    AMBIGUOUS = "ambiguous"


@dataclass(frozen=True)
class SnapshotEntry:
    """One observed filesystem entry.

    path_key should be a source-root-scoped, normalized internal key. In CAPEX
    production code, persist redacted_path + path_hash; do not leak raw paths to
    telemetry.
    """

    snapshot_entry_id: str
    path_key: str
    path_hash: str
    entry_type: str = "file"
    content_digest: Optional[str] = None
    size_bytes: Optional[int] = None
    modified_at: Optional[str] = None
    source_occurrence_id: Optional[str] = None
    stable_file_id: Optional[str] = None
    observation_status: ObservationStatus = ObservationStatus.OBSERVED


@dataclass(frozen=True)
class FolderSnapshot:
    snapshot_id: str
    source_root_id: str
    status: SnapshotStatus
    entries: tuple[SnapshotEntry, ...]
    # Scopes are normalized path_key prefixes. For a full complete snapshot,
    # complete_scopes may be {""}. For partial watcher scans, include the
    # parent/child-expanded scopes actually observed.
    complete_scopes: frozenset[str] = frozenset({""})
    incomplete_scopes: frozenset[str] = frozenset()


@dataclass(frozen=True)
class SourceOccurrenceDelta:
    delta_id: str
    delta_type: DeltaType
    prior_snapshot_entry_id: Optional[str] = None
    new_snapshot_entry_id: Optional[str] = None
    prior_source_occurrence_id: Optional[str] = None
    new_source_occurrence_id: Optional[str] = None
    candidate_group_id: Optional[str] = None
    review_state: str = "requires_review"
    stale_effect: str = "not_evaluated"
    signals: dict[str, object] = field(default_factory=dict)


@dataclass(frozen=True)
class SourceRootHealth:
    watcher_status: str
    last_complete_snapshot_exists: bool
    full_reconciliation_required: bool = False
    lost_changes_since_last_full_snapshot: bool = False
    unresolved_scan_error_scopes: frozenset[str] = frozenset()


def _under(path_key: str, scope: str) -> bool:
    """Return true if path_key is in scope, using normalized slash paths."""
    if scope in {"", ".", "/"}:
        return True
    scope = scope.rstrip("/")
    return path_key == scope or path_key.startswith(scope + "/")


def _under_any(path_key: str, scopes: Iterable[str]) -> bool:
    return any(_under(path_key, scope) for scope in scopes)


def can_partial_reconcile(health: SourceRootHealth, requested_scopes: Iterable[str]) -> bool:
    """Gate watcher-assisted partial reconciliation.

    Mirrors the useful Nextcloud pattern: partial discovery is allowed only when
    watcher health and prior full-discovery state are trustworthy.
    """
    if health.watcher_status != "reliable":
        return False
    if not health.last_complete_snapshot_exists:
        return False
    if health.full_reconciliation_required or health.lost_changes_since_last_full_snapshot:
        return False
    for scope in requested_scopes:
        if _under_any(scope, health.unresolved_scan_error_scopes):
            return False
    return True


def absence_is_authoritative(prior: SnapshotEntry, current: FolderSnapshot) -> bool:
    """Whether absence of prior.path_key in current may be interpreted as delete.

    This is the most important safety guard: if the scan could not observe the
    relevant subtree, absence is incomplete observation, not deletion.
    """
    if current.status == SnapshotStatus.FAILED:
        return False
    if _under_any(prior.path_key, current.incomplete_scopes):
        return False
    if current.status == SnapshotStatus.COMPLETE:
        return True
    return _under_any(prior.path_key, current.complete_scopes)


def classify_snapshot_diff(previous: FolderSnapshot, current: FolderSnapshot) -> list[SourceOccurrenceDelta]:
    """Classify observed differences as reviewable candidate deltas.

    This function never deletes governed evidence, never changes official state,
    and never equates digest equality with source-occurrence identity.
    """
    prev_by_path = {entry.path_key: entry for entry in previous.entries}
    curr_by_path = {entry.path_key: entry for entry in current.entries}

    prev_by_digest: dict[str, list[SnapshotEntry]] = {}
    curr_by_digest: dict[str, list[SnapshotEntry]] = {}
    for entry in previous.entries:
        if entry.content_digest:
            prev_by_digest.setdefault(entry.content_digest, []).append(entry)
    for entry in current.entries:
        if entry.content_digest:
            curr_by_digest.setdefault(entry.content_digest, []).append(entry)

    deltas: list[SourceOccurrenceDelta] = []
    consumed_missing: set[str] = set()

    def add(delta_type: DeltaType, prior: SnapshotEntry | None, new: SnapshotEntry | None, **signals: object) -> None:
        deltas.append(
            SourceOccurrenceDelta(
                delta_id=f"delta_{uuid4().hex}",
                delta_type=delta_type,
                prior_snapshot_entry_id=prior.snapshot_entry_id if prior else None,
                new_snapshot_entry_id=new.snapshot_entry_id if new else None,
                prior_source_occurrence_id=prior.source_occurrence_id if prior else None,
                candidate_group_id=f"group_{uuid4().hex}" if delta_type in {
                    DeltaType.MOVED_CANDIDATE,
                    DeltaType.RENAMED_CANDIDATE,
                    DeltaType.DUPLICATE_SEEN,
                    DeltaType.CONFLICT_CANDIDATE,
                    DeltaType.AMBIGUOUS,
                } else None,
                signals=signals,
            )
        )

    # First pass: current observations. This lets add/modify/move/duplicate
    # consume missing prior paths before emitting plain delete candidates.
    for new in current.entries:
        if new.observation_status != ObservationStatus.OBSERVED:
            continue

        prior_same_path = prev_by_path.get(new.path_key)
        if prior_same_path:
            if prior_same_path.content_digest and new.content_digest and prior_same_path.content_digest != new.content_digest:
                add(
                    DeltaType.MODIFIED,
                    prior_same_path,
                    new,
                    same_path=True,
                    digest_changed=True,
                    size_changed=prior_same_path.size_bytes != new.size_bytes,
                )
            continue

        same_digest_priors = prev_by_digest.get(new.content_digest or "", [])
        if not same_digest_priors:
            add(DeltaType.ADDED, None, new, no_prior_digest_match=True)
            continue

        missing_priors = [p for p in same_digest_priors if p.path_key not in curr_by_path]
        still_present_priors = [p for p in same_digest_priors if p.path_key in curr_by_path]

        if len(missing_priors) == 1 and not still_present_priors and absence_is_authoritative(missing_priors[0], current):
            prior = missing_priors[0]
            consumed_missing.add(prior.path_key)
            delta = DeltaType.RENAMED_CANDIDATE if prior.path_key.rsplit("/", 1)[-1] != new.path_key.rsplit("/", 1)[-1] else DeltaType.MOVED_CANDIDATE
            add(
                delta,
                prior,
                new,
                same_digest=True,
                old_path_absent=True,
                old_absence_authoritative=True,
                stable_file_id_equal=bool(prior.stable_file_id and prior.stable_file_id == new.stable_file_id),
            )
        elif still_present_priors:
            # Same content at an additional path is duplicate occurrence context,
            # not identity collapse.
            add(
                DeltaType.DUPLICATE_SEEN,
                still_present_priors[0],
                new,
                same_digest=True,
                prior_still_present=True,
                candidate_count=len(same_digest_priors),
            )
        else:
            add(
                DeltaType.AMBIGUOUS,
                None,
                new,
                same_digest=True,
                missing_prior_count=len(missing_priors),
                reason="multiple_or_unauthoritative_missing_priors",
            )

    # Second pass: remembered prior entries not currently observed.
    for prior in previous.entries:
        if prior.path_key in curr_by_path or prior.path_key in consumed_missing:
            continue
        if not absence_is_authoritative(prior, current):
            add(
                DeltaType.OBSERVATION_INCOMPLETE,
                prior,
                None,
                absent_from_current=True,
                current_snapshot_status=current.status.value,
                incomplete_scopes=sorted(current.incomplete_scopes),
            )
        else:
            add(
                DeltaType.DELETED_FROM_SOURCE,
                prior,
                None,
                absent_from_current=True,
                governed_evidence_deleted=False,
            )

    return deltas
