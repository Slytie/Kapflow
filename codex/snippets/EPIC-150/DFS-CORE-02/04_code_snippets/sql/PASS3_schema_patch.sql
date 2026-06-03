-- DFS-CORE-02 Pass 3 illustrative schema patch.
-- Not a production migration. Adapt naming, types, tenancy, auth, RLS, timestamps,
-- and migration tooling to the CAPEX repo.

CREATE TABLE source_root_sync_health (
    source_root_id TEXT PRIMARY KEY,
    project_id TEXT NOT NULL,
    watcher_status TEXT NOT NULL DEFAULT 'disabled'
        CHECK (watcher_status IN (
            'disabled',
            'reliable',
            'lost_changes',
            'overflow',
            'restarted',
            'unreliable'
        )),
    last_full_snapshot_id TEXT,
    last_complete_snapshot_at TEXT,
    full_reconciliation_required INTEGER NOT NULL DEFAULT 1,
    last_watcher_error_code TEXT,
    last_watcher_error_at TEXT,
    last_scan_error_code TEXT,
    last_scan_error_at TEXT,
    metadata_json TEXT NOT NULL DEFAULT '{}'
);

CREATE TABLE source_root_sync_run (
    sync_run_id TEXT PRIMARY KEY,
    project_id TEXT NOT NULL,
    source_root_id TEXT NOT NULL,
    trigger_kind TEXT NOT NULL
        CHECK (trigger_kind IN (
            'initial_import',
            'manual_reconcile',
            'scheduled_reconcile',
            'watch_reconcile',
            'watcher_uncertain_reconcile',
            'repair_reconcile'
        )),
    requested_scope_hash TEXT,
    effective_scope_hash TEXT,
    state TEXT NOT NULL
        CHECK (state IN (
            'queued',
            'preparing',
            'scanning',
            'staging_snapshot',
            'diffing',
            'classifying',
            'creating_review_tasks',
            'committed',
            'failed'
        )),
    started_at TEXT NOT NULL,
    committed_at TEXT,
    failed_at TEXT,
    failure_code TEXT,
    failure_message_redacted TEXT,
    metadata_json TEXT NOT NULL DEFAULT '{}'
);

CREATE TABLE folder_tree_snapshot (
    snapshot_id TEXT PRIMARY KEY,
    project_id TEXT NOT NULL,
    source_root_id TEXT NOT NULL,
    sync_run_id TEXT NOT NULL,
    snapshot_kind TEXT NOT NULL
        CHECK (snapshot_kind IN (
            'initial',
            'manual_reconcile',
            'scheduled_reconcile',
            'watch_reconcile',
            'watcher_uncertain_reconcile',
            'repair_reconcile'
        )),
    basis_snapshot_id TEXT,
    root_scope_hash TEXT NOT NULL,
    created_at TEXT NOT NULL,
    entry_count INTEGER NOT NULL DEFAULT 0,
    digest_summary TEXT,
    status TEXT NOT NULL
        CHECK (status IN ('complete', 'partial', 'failed')),
    metadata_json TEXT NOT NULL DEFAULT '{}'
);

CREATE TABLE folder_tree_snapshot_scope_status (
    scope_status_id TEXT PRIMARY KEY,
    snapshot_id TEXT NOT NULL,
    source_root_id TEXT NOT NULL,
    scope_path_hash TEXT NOT NULL,
    parent_scope_path_hash TEXT,
    status TEXT NOT NULL
        CHECK (status IN (
            'complete',
            'partial',
            'failed',
            'unreachable',
            'ignored',
            'unsupported'
        )),
    error_code TEXT,
    error_message_redacted TEXT,
    metadata_json TEXT NOT NULL DEFAULT '{}'
);

CREATE INDEX idx_snapshot_scope_status_lookup
    ON folder_tree_snapshot_scope_status(snapshot_id, scope_path_hash, status);

CREATE TABLE folder_tree_snapshot_entry (
    snapshot_entry_id TEXT PRIMARY KEY,
    snapshot_id TEXT NOT NULL,
    project_id TEXT NOT NULL,
    source_root_id TEXT NOT NULL,
    redacted_path TEXT NOT NULL,
    path_hash TEXT NOT NULL,
    parent_path_hash TEXT,
    entry_type TEXT NOT NULL
        CHECK (entry_type IN ('file', 'directory', 'symlink', 'unsupported')),
    content_digest_algorithm TEXT,
    content_digest TEXT,
    size_bytes INTEGER,
    modified_at TEXT,
    stable_file_id TEXT,
    inode TEXT,
    observation_status TEXT NOT NULL DEFAULT 'observed'
        CHECK (observation_status IN (
            'observed',
            'unobserved_parent_unreachable',
            'scan_error',
            'ignored',
            'unsupported',
            'transient'
        )),
    triage_hint TEXT,
    metadata_json TEXT NOT NULL DEFAULT '{}',
    UNIQUE(snapshot_id, path_hash)
);

CREATE INDEX idx_snapshot_entry_digest
    ON folder_tree_snapshot_entry(snapshot_id, content_digest);

CREATE INDEX idx_snapshot_entry_path
    ON folder_tree_snapshot_entry(snapshot_id, path_hash);

CREATE INDEX idx_snapshot_entry_stable_id
    ON folder_tree_snapshot_entry(snapshot_id, stable_file_id);

CREATE TABLE folder_tree_scan_error (
    scan_error_id TEXT PRIMARY KEY,
    sync_run_id TEXT NOT NULL,
    snapshot_id TEXT,
    source_root_id TEXT NOT NULL,
    scope_path_hash TEXT NOT NULL,
    error_code TEXT NOT NULL,
    error_message_redacted TEXT,
    occurred_at TEXT NOT NULL,
    metadata_json TEXT NOT NULL DEFAULT '{}'
);

CREATE TABLE source_root_touched_path_queue (
    queue_id TEXT PRIMARY KEY,
    project_id TEXT NOT NULL,
    source_root_id TEXT NOT NULL,
    redacted_path TEXT NOT NULL,
    path_hash TEXT NOT NULL,
    event_family TEXT NOT NULL
        CHECK (event_family IN ('non_remove', 'remove', 'mixed', 'root_unknown')),
    reliability_reason TEXT
        CHECK (reliability_reason IN (
            'normal',
            'overflow',
            'lost_changes',
            'watcher_restart',
            'watcher_unreliable'
        )),
    first_seen_at TEXT NOT NULL,
    last_seen_at TEXT NOT NULL,
    coalesced_scope_hash TEXT,
    sync_run_id_acknowledged TEXT,
    acknowledged_at TEXT,
    metadata_json TEXT NOT NULL DEFAULT '{}'
);

CREATE INDEX idx_touched_queue_pending
    ON source_root_touched_path_queue(source_root_id, sync_run_id_acknowledged, last_seen_at);

CREATE TABLE source_occurrence_delta_group (
    delta_group_id TEXT PRIMARY KEY,
    sync_run_id TEXT NOT NULL,
    project_id TEXT NOT NULL,
    source_root_id TEXT NOT NULL,
    group_type TEXT NOT NULL
        CHECK (group_type IN (
            'added',
            'modified',
            'moved_candidate',
            'renamed_candidate',
            'deleted_from_source',
            'duplicate_seen',
            'ambiguous_duplicate_or_move',
            'conflict_candidate',
            'observation_incomplete',
            'ignored_transient',
            'resurfaced'
        )),
    review_state TEXT NOT NULL DEFAULT 'requires_review'
        CHECK (review_state IN (
            'requires_review',
            'accepted',
            'rejected',
            'superseded',
            'blocked_conflict'
        )),
    classification_confidence REAL,
    review_required_reason TEXT NOT NULL,
    signals_json TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL,
    reviewed_at TEXT,
    reviewed_by TEXT,
    metadata_json TEXT NOT NULL DEFAULT '{}'
);

CREATE TABLE source_occurrence_delta (
    delta_id TEXT PRIMARY KEY,
    delta_group_id TEXT NOT NULL,
    sync_run_id TEXT NOT NULL,
    project_id TEXT NOT NULL,
    source_root_id TEXT NOT NULL,
    delta_type TEXT NOT NULL
        CHECK (delta_type IN (
            'added',
            'modified',
            'moved_candidate',
            'renamed_candidate',
            'deleted_from_source',
            'duplicate_seen',
            'ambiguous',
            'conflict_candidate',
            'observation_incomplete',
            'ignored_transient',
            'resurfaced'
        )),
    prior_source_occurrence_id TEXT,
    new_source_occurrence_id TEXT,
    prior_snapshot_entry_id TEXT,
    new_snapshot_entry_id TEXT,
    stale_effect TEXT NOT NULL DEFAULT 'not_evaluated'
        CHECK (stale_effect IN (
            'not_evaluated',
            'none',
            'stale_source_warning',
            'downstream_blocked_until_review'
        )),
    notes_redacted TEXT,
    metadata_json TEXT NOT NULL DEFAULT '{}'
);

-- Optional defensive audit trigger pseudo-pattern:
-- enforce in application service as well; SQL trigger syntax will vary by DB.
-- The intent is: source_occurrence_delta insertion must not cascade-delete
-- ArtifactVersion, evidence bindings, or official pointers.
