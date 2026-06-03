-- Supplemental — CAPEX Data Model Sketch for DFS-CORE-01
-- Purpose: source-root observation and PM-reviewed corpus updates.
-- This is not a final migration. It is a Codex/planning sketch.

create table source_root_binding (
  source_root_id uuid primary key,
  project_id uuid not null,
  owner_user_id uuid not null,
  observer_mode text not null check (observer_mode in (
    'browser_one_time_import',
    'browser_manual_resync',
    'desktop_agent_watch',
    'desktop_agent_manual_scan',
    'cloud_connector',
    'archived_source'
  )),
  display_label text,
  redacted_local_path_hint text,
  permission_basis text,
  root_marker_id text,
  status text not null default 'active' check (status in (
    'active',
    'needs_manual_resync',
    'permission_lost',
    'root_missing',
    'watcher_degraded',
    'archived'
  )),
  latest_observed_snapshot_id uuid,
  created_at timestamptz not null default now(),
  last_observed_at timestamptz
);

create table ingest_run (
  ingest_run_id uuid primary key,
  source_root_id uuid not null references source_root_binding(source_root_id),
  project_id uuid not null,
  started_by_user_id uuid not null,
  observer_mode text not null,
  observation_basis text not null,
  status text not null check (status in ('pending','manifest_received','uploading','finalized','failed','aborted')),
  started_at timestamptz not null default now(),
  finalized_at timestamptz
);

create table observed_folder_snapshot (
  snapshot_id uuid primary key,
  source_root_id uuid not null references source_root_binding(source_root_id),
  ingest_run_id uuid not null references ingest_run(ingest_run_id),
  observation_basis text not null,
  path_scope text not null default 'full',
  observed_at timestamptz not null default now(),
  manifest_digest text,
  file_count integer,
  status text not null check (status in ('complete','partial','failed','degraded'))
);

create table observed_file (
  observed_file_id uuid primary key,
  snapshot_id uuid not null references observed_folder_snapshot(snapshot_id),
  source_root_id uuid not null references source_root_binding(source_root_id),
  relative_path text not null,
  entry_type text not null check (entry_type in ('file','directory','symlink','unsupported')),
  size_bytes bigint,
  mtime timestamptz,
  digest text,
  local_file_id_hint text,
  availability text not null default 'present' check (availability in (
    'present','unreadable','permission_lost','missing','unsupported','ignored'
  )),
  stability_status text not null default 'stable' check (stability_status in (
    'stable','changed_during_read','unknown','retry_required'
  ))
);

create table blob_ref (
  blob_id uuid primary key,
  digest text not null,
  size_bytes bigint not null,
  storage_uri text not null,
  custody_status text not null check (custody_status in ('pending','stored','quarantined','deleted_by_retention_policy')),
  created_at timestamptz not null default now(),
  unique (digest, size_bytes)
);

create table source_occurrence (
  source_occurrence_id uuid primary key,
  source_root_id uuid not null references source_root_binding(source_root_id),
  snapshot_id uuid not null references observed_folder_snapshot(snapshot_id),
  observed_file_id uuid not null references observed_file(observed_file_id),
  blob_id uuid references blob_ref(blob_id),
  relative_path text not null,
  occurrence_status text not null check (occurrence_status in (
    'present',
    'missing_in_latest_snapshot',
    'ignored',
    'unsupported',
    'superseded'
  )),
  review_status text not null default 'unreviewed' check (review_status in (
    'unreviewed','proposed','reviewed','rejected'
  )),
  created_at timestamptz not null default now()
);

create table source_root_delta (
  delta_id uuid primary key,
  source_root_id uuid not null references source_root_binding(source_root_id),
  from_snapshot_id uuid references observed_folder_snapshot(snapshot_id),
  to_snapshot_id uuid not null references observed_folder_snapshot(snapshot_id),
  delta_type text not null check (delta_type in (
    'created',
    'modified_digest_changed',
    'metadata_changed_only',
    'missing_in_latest_snapshot',
    'possible_rename',
    'possible_duplicate',
    'ignored',
    'unsupported',
    'permission_lost'
  )),
  from_occurrence_id uuid references source_occurrence(source_occurrence_id),
  to_occurrence_id uuid references source_occurrence(source_occurrence_id),
  confidence numeric,
  evidence_json jsonb not null default '{}'::jsonb,
  pm_review_status text not null default 'pending' check (pm_review_status in ('pending','accepted','rejected','deferred')),
  created_at timestamptz not null default now()
);

create table ai_proposal (
  ai_proposal_id uuid primary key,
  source_root_id uuid not null references source_root_binding(source_root_id),
  snapshot_id uuid not null references observed_folder_snapshot(snapshot_id),
  proposal_type text not null,
  proposal_json jsonb not null,
  status text not null default 'pending_pm_review' check (status in ('pending_pm_review','accepted','rejected','superseded')),
  created_at timestamptz not null default now()
);

create table pm_review_task (
  task_id uuid primary key,
  project_id uuid not null,
  source_root_id uuid references source_root_binding(source_root_id),
  delta_id uuid references source_root_delta(delta_id),
  ai_proposal_id uuid references ai_proposal(ai_proposal_id),
  task_type text not null,
  status text not null default 'open' check (status in ('open','accepted','rejected','deferred','closed')),
  created_at timestamptz not null default now(),
  resolved_at timestamptz
);

create table reviewed_corpus_baseline (
  reviewed_baseline_id uuid primary key,
  project_id uuid not null,
  previous_baseline_id uuid references reviewed_corpus_baseline(reviewed_baseline_id),
  created_by_user_id uuid not null,
  created_from_review_task_id uuid references pm_review_task(task_id),
  created_at timestamptz not null default now(),
  status text not null default 'active'
);

create table official_evidence_binding (
  official_binding_id uuid primary key,
  project_id uuid not null,
  reviewed_baseline_id uuid references reviewed_corpus_baseline(reviewed_baseline_id),
  approved_by_user_id uuid,
  approval_status text not null check (approval_status in ('draft','approved','official','revoked')),
  created_at timestamptz not null default now()
);
