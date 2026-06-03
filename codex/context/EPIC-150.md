# EPIC-150 Context Pack - CAPEX release governance

Purpose:
- Rehydrate the CAPEX v6 task tranche for `EPIC-150` without opening the full master package.
- Keep future work inside the existing one-truth runtime, approval, artifact, pointer, and event model.

## Imported source rows
DOC-001, DOC-002, DOC-003, SAFE-002, RF-011, RF-012, ARCH-W7-SL-001, ARCH-W7-SL-002, ... (30 tasks total)

## Load first
- `docs/planning/epics/EPIC-150.md`
- `docs/planning/CAPEX_MASTER_V6_INTAKE.md`
- `docs/planning/CAPEX_V6_CONVERSION_MAP.csv`
- `docs/architecture/invariants.md`
- `docs/status/CURRENT_FOCUS.md`

## Non-negotiable invariants
- One truth system: official claims come only from immutable objects, append-only events, and audited pointers.
- Tenant, domain, and future CAPEX project boundaries must not be crossed in reads, writes, exports, projections, or generated material.
- Raw K12/K3/blind corpus files stay off-repo; only sanitized fixtures, manifests, hashes, and aggregate evidence may be committed.
- Generated artifacts, Workflow Lab reports, and AI output are not source authority.
- Production/lab activation is release-mediated and remains blocked until the relevant gates close or receive explicit waivers.

## Preferred implementation posture
- Start with the source task's required tests or evidence.
- Update repo-native authoritative source before downstream generated artifacts.
- Keep implementation PRs small enough to review against the source row and acceptance gate.
- Preserve logistics weekly/live current focus unless a CAPEX task explicitly changes shared semantics.

## Stop line
- Do not import raw project corpus content.
- Do not activate CAPEX runtime/product behavior merely because a planning task exists.

## Desktop Source-Root Addendum

This addendum restores the desktop-folder source-root and AI corpus-structure
review pack from `CAPEX_EPIC150_Separate_Pack.zip`. The source pack used
`TASK-0589` through `TASK-0624`; this repo already uses those task IDs, so the
restored EPIC-150 desktop-source-root tasks live at `TASK-0607` through
`TASK-0642`.

Core invariant: a desktop folder is an observed source root, not project truth.

Never collapse:
- folder path into document role
- folder import into evidence sufficiency
- watcher event into truth
- local deletion into evidence deletion
- AI proposal into reviewed corpus baseline
- reviewed corpus baseline into official pointer

Stage model:
- Stage 1 MVP: manual browser folder import, ZIP import, or user-selected folder upload; no persistent background watcher.
- Stage 2 MVP+: manual resync of a previously registered source root; new `FolderTreeSnapshot` and `SourceOccurrenceDelta` objects are produced, and PM review is required before downstream baseline update.
- Stage 3 deferred controlled pilot: desktop companion app, local service, cloud connector, or server-mounted folder. Watcher events are hints only and must be reconciled against snapshots.

Runtime concepts:
- `SourceRootBinding`: project-scoped source-root identity. Path is a redacted locator/display hint.
- `FolderTreeSnapshot`: immutable observation of a source root at one time.
- `SyncRun`: effect-safe job/run that creates or compares snapshots.
- `SnapshotDiff`: comparison between previous and current snapshots.
- `SourceOccurrenceDelta`: created, modified, metadata-only, missing, possible rename, duplicate candidate, ignored, unsupported, permission lost, or quarantine required.
- `ProposedCorpusStructure`: AI draft, not reviewed state.
- `CorpusStructureReviewDecision`: PM decision that confirms, corrects, delegates, ignores, or quarantines.
- `FolderSyncConflict`: reviewable conflict or ambiguity; never direct truth mutation.

Snippet library:
- `codex/snippets/EPIC-150/DFS-CORE-01/supplemental/CAPEX_Data_Model_Sketch.sql`
- `codex/snippets/EPIC-150/DFS-CORE-01/supplemental/CAPEX_SourceRoot_Agent_Contract.md`
- `codex/snippets/EPIC-150/DFS-CORE-02/04_code_snippets/python_reference/capex_sync_reconciliation.py`
- `codex/snippets/EPIC-150/DFS-CORE-02/04_code_snippets/sql/PASS3_schema_patch.sql`
- `codex/snippets/EPIC-150/DFS-CORE-02/04_code_snippets/typescript/reconcile_source_root.ts`
- `codex/snippets/EPIC-150/DFS-CORE-03/SNIPPETS/capex_proposed_corpus_structure.schema.json`
- `codex/snippets/EPIC-150/DFS-CORE-03/SNIPPETS/capex_corpus_review_workpage_command.schema.json`
- `codex/snippets/EPIC-150/DFS-CORE-04/schemas/redacted_path_ref.schema.json`
- `codex/snippets/EPIC-150/DFS-CORE-04/snippets/python/redaction.py`
- `codex/snippets/EPIC-150/DFS-CORE-04/snippets/python/ai_eligibility.py`

These snippets are illustrative patterns only. Do not paste them into production
unchanged. Adapt them to repo models, migrations, route conventions, service
structure, tests, CODEOWNERS, and feature-gate policy.

Required negative tests:
- same digest in two folders creates two `SourceOccurrence` records
- AI proposal exists but reviewed corpus baseline remains absent until PM review
- local delete creates missing/stale review state, not evidence deletion
- absolute path in UI/logs/AI prompt/export fails
- watcher overflow or lost event prevents source root from being marked fresh
- manual resync modified file leaves reviewed baseline unchanged until accepted
- bulk accept high-risk proposal is blocked
- stale projection command is rejected as a no-op

P0 blockers before activation:
- `approval.respond` domain neutrality is resolved
- artifact/blob auth-before-read is resolved
- `capex_project` and `project_membership` exist
- source occurrence runtime exists
- SourceRefs are meaningful and resolved
- workpage stale-command guards exist
- CAPEX semantic tests and CODEOWNERS gates exist
