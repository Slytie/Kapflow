---
id: TASK-0271
epic: EPIC-141
title: "Text extraction and page manifest contracts"
status: DONE
completed_at: 2026-06-23T00:00:00Z
owners: ["platform"]
reviewers: ["architect", "qa"]
depends_on: ["TASK-0270"]
risk: high
context_packs:
  - "codex/context/EPIC-141.md"
patterns: ["capex-v6-planning"]
---

## Why
Imported from CAPEX v6 source task `INGEST-006` so future work can be executed from repo-native backlog memory without loading the full master package.

## Scope
Extract text and page boundaries with provenance.

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
- Source required tests: PDF/page evidence tests
- Acceptance gate: `AT-EVIDENCE-001`
- Run the smallest relevant repo checks for changed code.
- Run `python3 scripts/validate_repo.py` and `git diff --check` before closing the task.

## Acceptance criteria
- Source output satisfied: document_text_extract; document_page_manifest
- Review focus covered: source refs to page/chunk; OCR optional/gated
- Refactor focus covered: separate extractor adapter
- Docs requirement covered: extraction docs
- Rollback/recovery posture recorded: documented if production-facing

## Source row mapping
- Source task ID: `INGEST-006`
- Source phase: `P5 Corpus ingest`
- Source priority: `P0`
- Source area: `document indexing`
- Original depends_on: `INGEST-005`
- Recommended source branch: `feature/capex-*`

## Notes / decisions
- Raw project corpora remain off-repo; use only sanitized fixtures, manifests, hashes, and aggregate evidence approved by the relevant fixture/governance task.

## Closeout evidence
- Added `docs/planning/capex_source_ingest/TEXT_EXTRACTION_PAGE_MANIFEST_CONTRACT.yaml` for the `INGEST-006` text extraction and page manifest planning contract.
- Added `onetruth.capex_platform.text_extraction_page_manifest` to produce deterministic `capex.document_text_extract.v1` and `capex.document_page_manifest.v1` payloads from sanitized document-manifest basis rows.
- Evidence: text extraction/page manifest unit tests and CAPEX ingest/generated-artifact contract tests passed on 2026-06-23.
- Closeout posture: `INGEST-006` closes text/page artifact shape evidence only; parser adapters, extraction/OCR runtime, async jobs, chunk/search/evidence-binding indexes, reviewed evidence sufficiency, public routes, workflow pack activation, raw corpus import, official pointer creation, and CAPEX runtime/product activation remain later gated work.
