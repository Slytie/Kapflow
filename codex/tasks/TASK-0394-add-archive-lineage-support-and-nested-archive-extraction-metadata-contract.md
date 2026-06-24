---
id: TASK-0394
epic: EPIC-141
title: "Add archive lineage support and nested-archive extraction metadata contract"
status: DONE
completed_at: "2026-06-23T00:00:00Z"
owners: ["platform"]
reviewers: ["architect", "qa"]
depends_on: ["TASK-0392", "TASK-0393"]
risk: high
context_packs:
  - "codex/context/EPIC-141.md"
patterns: ["capex-v6-planning"]
---

## Why
Imported from CAPEX v6 source task `ARCH-W2-S04` so future work can be executed from repo-native backlog memory without loading the full master package.

## Scope
Metadata only first; no full extractor required

## Out of scope
- Runtime or production activation beyond this task's explicit source scope.
- Copying raw K12, K3, or blind-validation project files into the repository.
- Treating generated artifacts, lab reports, or AI outputs as canonical authority.

## Source files to read first
- `docs/planning/CAPEX_MASTER_V6_INTAKE.md`
- `docs/planning/CAPEX_V6_CONVERSION_MAP.csv`
- `docs/planning/epics/EPIC-141.md`
- `codex/context/EPIC-141.md`
- `docs/status/CURRENT_FOCUS.md`
- `docs/architecture/invariants.md`

## Plan
1. Re-read the CAPEX intake record, this task's epic context, and the source row in the conversion map.
2. Start with the required tests or evidence listed below, then make the smallest repo-native change that satisfies the task.
3. Update docs/status/test evidence only where the source scope requires it.
4. Preserve tenant/domain isolation, artifact immutability, canonical approvals, and append-only event truth.

## Verification
- Source required tests: red/characterization test or executable acceptance evidence before implementation
- Acceptance gate: `W2-accepted-gates + semantic MR gate`
- Run the smallest relevant repo checks for changed code.
- Run `python3 scripts/validate_repo.py` and `git diff --check` before closing the task.

## Acceptance criteria
- Source output satisfied: Implementation artifact(s) implied by W2-S04; source wave W2; CED-linked design note; tests; docs update
- Review focus covered: Tier 3
- Refactor focus covered: explicit refactor/stabilization checkpoint required before closeout
- Docs requirement covered: Update relevant CED/ADR, architecture doc, catalog, and master traceability for W2
- Rollback/recovery posture recorded: disable capability or leave runtime state inert; no destructive rollback of governed state

## Source row mapping
- Source task ID: `ARCH-W2-S04`
- Source phase: `P4/P5 Corpus and effects`
- Source priority: `P0`
- Source area: `corpus/effects/artifacts/validation`
- Original depends_on: `W2-S02/S03`
- Source-only dependency notes: `W2-S02/S03`
- Recommended source branch: `foundation/* or capex-runtime-disabled/*`

## Notes / decisions
- Raw project corpora remain off-repo; use only sanitized fixtures, manifests, hashes, and aggregate evidence approved by the relevant fixture/governance task.
- Closeout evidence: added `docs/planning/capex_source_ingest/ARCHIVE_LINEAGE_METADATA_CONTRACT.yaml` and `src/onetruth/capex_platform/archive_lineage_metadata.py` for deterministic `capex.archive_lineage_register.v1`, `capex.nested_archive_member_metadata.v1`, and wrapper `capex.archive_lineage_metadata.outputs.v1` planning outputs over existing source-occurrence and relation rows.
- The helper validates same tenant/domain/project, known source occurrences, existing archive relation rows, allowed `archive_contains` / `archive_member_of` relation types, no self-links, no archive containment cycles, checked nesting depth, sanitized logical member refs, optional `sha256:` member digests, deterministic ordering/digests, and raw-material bans.
- Evidence: focused archive-lineage unit tests and CAPEX ingest/generated-artifact contract tests cover deterministic output, scope/ref/type/depth/cycle/duplicate failures, raw-content bans, and no runtime/extractor/official truth effects.
- Closeout posture: this task records metadata-only archive lineage evidence. It adds no archive extraction runtime, locator union, parser/OCR/search runtime, queue worker, route, frontend, event-registry change, raw corpus import, reviewed baseline truth, official pointer, workflow activation, or CAPEX product/runtime activation.
