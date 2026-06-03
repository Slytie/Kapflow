---
id: TASK-0614
epic: EPIC-150
title: Bind BlobRef and SourceOccurrence separation to desktop roots
status: TODO
owners: [capex-platform]
reviewers: [backend, security, capex-architecture]
depends_on: [EPIC-139, EPIC-141, TASK-0608]
risk: critical
context_packs: [codex/context/EPIC-150.md]
patterns: [EPIC-150 desktop source-root observation pipeline]
---

# TASK-0614 — Bind BlobRef and SourceOccurrence separation to desktop roots

## Context

This task is part of EPIC-150, the desktop-folder source-root and AI corpus-structure review workflow. The central invariant is that a desktop folder is an observed source, not project truth. Folder paths, watcher events, AI proposals, and local deletions must not directly mutate reviewed or official CAPEX state.

Mapped CAPEX / research source rows: `DFS-D03; DFS-RISK-002; DFS-TEST-001`.

## Objective

Ensure dedupe reuses storage where safe without collapsing source occurrence context.

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
- `codex/tasks/TASK-0614-bind-blobref-and-sourceoccurrence-separation-to-desktop-roots.md`
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
