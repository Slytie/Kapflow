---
id: TASK-0608
epic: EPIC-150
title: Define SourceRootBinding, FolderTreeSnapshot, SyncRun, and source-root state model
status: DONE
completed_at: "2026-06-17T00:00:00Z"
owners: [capex-platform]
reviewers: [backend, security, capex-architecture]
depends_on: [TASK-0607, EPIC-140, EPIC-141]
risk: high
context_packs: [codex/context/EPIC-150.md]
patterns: [SourceRootBinding, FolderTreeSnapshot, SyncRun]
---

# TASK-0608 — Define SourceRootBinding, FolderTreeSnapshot, SyncRun, and source-root state model

## Context

This task is part of EPIC-150, the desktop-folder source-root and AI corpus-structure review workflow. The central invariant is that a desktop folder is an observed source, not project truth. Folder paths, watcher events, AI proposals, and local deletions must not directly mutate reviewed or official CAPEX state.

Mapped CAPEX / research source rows: `DST-002; DFS-D02; DFS-DELTA-001`.

## Objective

Define source-root identity, redacted path hints, snapshot state, sync-run lifecycle, permission basis, and sync health.

## Non-goals

- Do not implement bidirectional desktop synchronization or writeback.
- Do not treat folder paths, folder names, digests, watcher events, or AI proposals as reviewed project truth.
- Do not ingest raw K3/K12/blind-validation project corpora into repo, CI, logs, screenshots, or generated packs.
- Do not copy illustrative snippets into production without adaptation, tests, and review.

## Source files to read first

- `docs/planning/epics/EPIC-150.md`
- `codex/context/EPIC-150.md`
- `MASTER_Codebase_CAPEX_Activation_Blockers.md` from the CAPEX master package
- `MASTER_Nuance_Preservation_Addendum_v2_Final.md` from the CAPEX master package
- EPIC dependencies: EPIC-139, EPIC-140, EPIC-141, EPIC-144, EPIC-145, EPIC-147
- Relevant snippet library files under `codex/snippets/EPIC-150/`

## Source files to change

- `docs/planning/epics/EPIC-150.md`
- `codex/context/EPIC-150.md`
- `codex/tasks/TASK-0608-define-sourcerootbinding-foldertreesnapshot-syncrun-and-source-root-state-model.md`
- `src/**/models or migrations for CAPEX source-root state`
- `tests/**/capex source-root state tests`


Exact repo paths must be confirmed before editing. Use existing repo conventions for routes, models, services, migrations, tests, CODEOWNERS, and documentation.

## Generated / downstream artifacts impacted

- EPIC-150 planning and context documents.
- CAPEX source-root / source-occurrence runtime state, where applicable.
- Corpus Structure Review Workpage or review tasks, where applicable.
- Acceptance tests and negative-test fixtures for folder import/resync behavior.

## Plan

1. Read the EPIC-150 context pack and the relevant CED/snippet references.
2. Characterize existing repo behavior before changing code.
3. Add or update tests first for the required invariant or behavior.
4. Implement the smallest change that satisfies the tests.
5. Run the relevant unit, integration, and semantic guard tests.
6. Update planning/docs only where the behavior or activation gate changes.
7. Route the change through the required specialist review gates.

## Verification

- Unit or contract tests for the local behavior.
- Integration tests where runtime state, blob/auth, workpage commands, or review tasks are involved.
- Negative tests proving the forbidden shortcut does not occur.
- Leak/redaction tests where local paths, sensitive folders, or AI prompts are involved.

## Acceptance criteria

- The task objective is implemented or documented with a clear deferral/waiver.
- The mapped CAPEX source rows remain traceable in the task, tests, and review notes.
- No raw project data is introduced into the repo or CI.
- No AI proposal, folder path, watcher event, local deletion, or digest shortcut can create reviewed or official project truth.
- Required tests are green in the project environment.

## Notes / decisions

- Snippets are patterns, not patches.
- Stage 3 persistent desktop-agent behavior is disabled unless separately activated.
- If this task reveals a contradiction with EPIC-139/140/141/144/145/147, stop and raise an architecture decision before implementation.

## Closeout evidence

- Added internal runtime state for `capex_source_root_bindings`, `capex_source_root_sync_runs`, and `capex_folder_tree_snapshots` through Alembic, SQLite bootstrap, SQLAlchemy models, runtime schemas, and repository helpers.
- Repository behavior validates observer/status vocabularies, rejects obvious raw absolute path hints, enforces tenant/domain/project consistency, blocks terminal sync-run advancement, and updates `latest_snapshot_id` only when a snapshot is explicitly recorded as latest.
- Evidence: unit and schema-parity tests cover source-root creation, invalid values, raw path rejection, sync-run lifecycle, snapshot scope checks, latest-snapshot update behavior, and bootstrap/Alembic/model parity.
- Closeout posture: internal source-root observation state only. No public API, frontend route, desktop sync activation, raw corpus import, blob upload behavior, SourceOccurrence binding, reviewed baseline mutation, official pointer creation, CAPEX runtime activation, or CAPEX product activation is added.
