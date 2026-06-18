# EPIC-150 - CAPEX release governance

## Summary
Add release, branch, review, migration, activation, and docs-authority governance for CAPEX work.

This epic was imported from CAPEX v6 on `2026-06-01` as planning backlog only. It does not activate CAPEX runtime behavior by itself.

## Status
Imported as TODO backlog unless an individual task records completed repo evidence.
The desktop source-root addendum is now started for planning scope only:
`TASK-0607` closes the stage/MVP-boundary contract, while `TASK-0608+`
remain open.

## In scope
- Source task families/counts: ARCH:24, DOC:3, RF:2, SAFE:1.
- Preserve CAPEX v6 source-row intent while translating work into repo-native tasks and context packs.
- Keep official claims inside the canonical workflow/task/approval/event/artifact/pointer substrate.

## Out of scope
- Raw K12, K3, or blind-validation corpus commits.
- Direct production activation or live truth mutation from this planning import.
- Treating generated material, agent output, or Workflow Lab evidence as source authority.

## Dependencies
- EPIC-137, EPIC-149

Context pack:
- `codex/context/EPIC-150.md`

## Source references
- `docs/planning/CAPEX_MASTER_V6_INTAKE.md`
- `docs/planning/CAPEX_V6_CONVERSION_MAP.csv`
- `docs/planning/CAPEX_V6_GATE_RISK_DECISION_MAP.csv`
- `docs/planning/capex_desktop_source_roots/EPIC150_STAGE_MODEL_AND_BOUNDARY.yaml`

## Task stack
- `TASK-0308` (`DOC-001`) - Restructure documentation tree
- `TASK-0309` (`DOC-002`) - Development flow and task template adoption
- `TASK-0310` (`DOC-003`) - Code review and refactor gate adoption
- `TASK-0314` (`SAFE-002`) - Safety Pass B: deployment roadmap/branch collision review
- `TASK-0379` (`RF-011`) - Feature flag retirement register
- `TASK-0380` (`RF-012`) - Docs route/status cleanup
- `TASK-0513` (`ARCH-W7-SL-001`) - Branch class manifest and classifier
- `TASK-0514` (`ARCH-W7-SL-002`) - Release bundle manifest schema
- `TASK-0515` (`ARCH-W7-SL-003`) - Migration lane manifest schema
- `TASK-0516` (`ARCH-W7-SL-004`) - Migration compatibility test scaffold
- `TASK-0517` (`ARCH-W7-SL-005`) - Feature gate manifest and activation model
- `TASK-0518` (`ARCH-W7-SL-006`) - Activation guard helper
- `TASK-0519` (`ARCH-W7-SL-007`) - Compensation plan schema
- `TASK-0520` (`ARCH-W7-SL-008`) - Docs authority schema
- `TASK-0521` (`ARCH-W7-SL-009`) - Docs authority linter
- `TASK-0522` (`ARCH-W7-SL-010`) - CED template and lifecycle metadata
- `TASK-0523` (`ARCH-W7-SL-011`) - Semantic task template
- `TASK-0524` (`ARCH-W7-SL-012`) - Semantic MR evidence bundle
- `TASK-0525` (`ARCH-W7-SL-013`) - Semantic CODEOWNERS sketch
- `TASK-0526` (`ARCH-W7-SL-014`) - Path-based semantic merge gate
- `TASK-0527` (`ARCH-W7-SL-015`) - Forbidden state transition lint rules
- `TASK-0528` (`ARCH-W7-SL-016`) - Fixture leakage release gate
- `TASK-0529` (`ARCH-W7-SL-017`) - AI assistance declaration in MR
- `TASK-0530` (`ARCH-W7-SL-018`) - Release readiness gate script
- `TASK-0531` (`ARCH-W7-SL-019`) - Activation approval record
- `TASK-0532` (`ARCH-W7-SL-020`) - Post-activation smoke evidence
- `TASK-0533` (`ARCH-W7-SL-021`) - Quality metrics dashboard spec
- `TASK-0534` (`ARCH-W7-SL-022`) - Refactor work item register integration
- `TASK-0535` (`ARCH-W7-SL-023`) - Implementation history check
- `TASK-0536` (`ARCH-W7-SL-024`) - Wave 7 integration QA

## Acceptance criteria
- Every listed task preserves its v6 source row, acceptance gate, dependency notes, and raw-data boundary.
- Implementation tasks update authoritative repo source before generated derivatives.
- CAPEX remains gated until the relevant acceptance gates and production-preflight evidence are closed or explicitly waived.

## Desktop Source-Root Addendum

This addendum restores the EPIC-150 desktop folder source-root pack from
`CAPEX_EPIC150_Separate_Pack.zip`. The source pack used `TASK-0589` through
`TASK-0624`, but those IDs are already occupied in this repo, so the restored
task stack is represented as `TASK-0607` through `TASK-0642`.

Status: planning addendum in progress. `TASK-0607` records the stage model and
MVP/non-MVP boundary as a repo-native planning contract. It does not activate
CAPEX runtime behavior.

Summary: create the PM-facing desktop folder intake and resync experience for
CAPEX project corpora. A PM may select a desktop folder, folder set, ZIP, or
later connector-backed source root. The system observes that source, records
source-root and folder-snapshot state, creates source occurrences, detects
deltas on later resync, and asks AI to propose a draft corpus organization. The
PM must review and confirm the proposed structure before downstream CAPEX
workflows rely on it.

The addendum is deliberately framed as observation, proposal, and PM review, not
automatic project-truth mutation.

In scope:
- Stage 1 MVP: browser-mediated folder/ZIP/manual import into a project-scoped source root.
- Stage 2 MVP+: manual resync of the same source root with snapshot/delta comparison.
- Stage 3 deferred/controlled pilot: optional desktop agent or connector only after activation gates.
- `SourceRootBinding`, `FolderTreeSnapshot`, `SyncRun`, `SnapshotDiff`, `SourceOccurrenceDelta`, and sync-health concepts.
- Preservation of duplicate content as separate source occurrences when folder/path context differs.
- AI `ProposedCorpusStructure` draft organization, including proposed roles, packets, triage, warnings, and confidence.
- PM Corpus Structure Review Workpage and explicit review/confirmation task.
- Local deletion / missing-file semantics that create stale/missing-source review state, not evidence deletion.
- Local path redaction, privacy/leak prevention, untrusted-file triage, and AI-context eligibility rules.
- Negative tests proving folder paths, watcher events, deletion events, and AI proposals cannot mutate governed state directly.

Out of scope:
- Treating folder paths or folder names as project truth.
- Treating AI organization as reviewed or official state.
- Persistent background desktop watcher in the first MVP.
- Bidirectional synchronization or writeback into PM desktop folders.
- Using local deletion to delete governed `BlobRef`, `ArtifactVersion`, `EvidenceBinding`, reviewed corpus baseline, or official pointer.
- Raw K3, K12, or blind-validation project corpus material in repo, CI, logs, screenshots, or generated planning packs.
- Full DMS/sync-platform adoption for this feature.

Additional dependencies:
- EPIC-139 - domain-boundary cleanup and approval/workpage neutrality.
- EPIC-140 - CAPEX project identity, membership, and authorization.
- EPIC-141 - corpus ingest, source occurrence, and SourceRef resolution.
- EPIC-142 - evidence binding, extraction, search, and packet completeness.
- EPIC-144 - CAPEX workpages and stale-command guards.
- EPIC-145 - pointer promotion, waiver, closure, stale/reopen semantics.
- EPIC-147 - no-false-closure, semantic, scale, and AI-agent Lab test harnesses.
- Platform safety prerequisite - artifact/blob custody and auth-before-read must remain proven before desktop source-root evidence can be bound.

## Desktop Source-Root Task Stack
- `TASK-0607` - Freeze EPIC-150 stage model and MVP/non-MVP boundary. - DONE 2026-06-17.
- `TASK-0608` - Define source-root runtime model and state machine.
- `TASK-0609` - Specify manual folder/ZIP import protocol.
- `TASK-0610` - Specify manual resync and delta reconciliation.
- `TASK-0611` - Define watcher-as-hint semantics and deferred desktop-agent contract.
- `TASK-0612` - Define local deletion / missing-source evidence semantics.
- `TASK-0613` - Define path redaction and local privacy policy.
- `TASK-0614` - Bind BlobRef / SourceOccurrence separation to desktop source roots.
- `TASK-0615` - Define manifest-first auth-before-blob-upload flow.
- `TASK-0616` - Define source-root permissions and user-consent model.
- `TASK-0617` - Define ProposedCorpusStructure AI draft contract.
- `TASK-0618` - Define AI proposal provenance, confidence, and SourceRef requirements.
- `TASK-0619` - Specify Corpus Structure Review Workpage.
- `TASK-0620` - Specify corpus structure review task and blocking semantics.
- `TASK-0621` - Define constrained bulk-accept rules for low-risk proposals.
- `TASK-0622` - Define sensitive/licensed/personal-source triage.
- `TASK-0623` - Define sync conflict review and stale/reopen propagation.
- `TASK-0624` - Specify projection freshness and stale-command guards for sync review.
- `TASK-0625` - Add duplicate digest / multiple occurrence tests.
- `TASK-0626` - Add AI proposal cannot create reviewed baseline tests.
- `TASK-0627` - Add local deletion does not delete evidence tests.
- `TASK-0628` - Add path redaction and leak-sentinel tests.
- `TASK-0629` - Add watcher failure and observation completeness tests.
- `TASK-0630` - Add modified/moved/renamed conflict tests.
- `TASK-0631` - Add content-safe logging and telemetry policy hooks.
- `TASK-0632` - Add leak-scan surfaces for exports, screenshots, generated packs, and CI artifacts.
- `TASK-0633` - Run desktop-agent feasibility spike and activation-gate design.
- `TASK-0634` - Define desktop-agent signing, update, support, permission, and endpoint-security gates.
- `TASK-0635` - Evaluate cloud/server connector path as alternative to desktop agent.
- `TASK-0636` - Add K12/K3/blind validation coverage for desktop source-root behavior.
- `TASK-0637` - Add CODEOWNERS / specialist review gates for desktop source-root code.
- `TASK-0638` - Curate and annotate desktop-sync snippet usage for Codex.
- `TASK-0639` - Define performance and scale smoke tests for source-root snapshot/resync.
- `TASK-0640` - Add overkill guards: no bidirectional sync, no writeback, no full DMS/sync-platform adoption.
- `TASK-0641` - Refine PM UX for Source Roots, Sync Monitor, and Review Queue.
- `TASK-0642` - Define EPIC-150 to EPIC-141 handoff for SourceRef resolution.

Acceptance gates:
- Folder import creates source occurrences without treating folder names as truth.
- Same digest in two folder contexts creates one reusable blob identity, if allowed, and two distinct source occurrences.
- Folder paths are stored only as redacted display/locator hints; they are not semantic truth.
- AI-proposed roles, packets, and triage decisions remain draft until PM review.
- Manual resync creates immutable snapshot/delta observations and review tasks; it does not mutate reviewed corpus baseline automatically.
- Local deletion marks source occurrence missing/stale and creates review state; it does not delete governed evidence history.
- Watcher events, if later introduced, are hints only and must be reconciled against complete snapshots.
- Local paths, usernames, machine names, and sensitive folder labels do not leak into AI prompts, logs, telemetry, screenshots, generated packs, or CI artifacts.
- Persistent desktop-agent mode remains disabled until signing, update, support, security, privacy, and activation gates are approved.

Explicit non-authority rule: EPIC-150 desktop source-root work may create
observations, proposals, review tasks, and reviewed corpus baselines. It may not
directly create official project state. Officialness remains governed by
validation, approval, and pointer promotion.
