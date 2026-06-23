---
id: TASK-0270
epic: EPIC-141
title: "Document manifest and extraction-state artifact"
status: DONE
completed_at: "2026-06-17T00:00:00Z"
owners: ["platform"]
reviewers: ["architect", "qa"]
depends_on: ["TASK-0267"]
risk: high
context_packs:
  - "codex/context/EPIC-141.md"
patterns: ["capex-v6-planning"]
---

## Why
Imported from CAPEX v6 source task `INGEST-005` so future work can be executed from repo-native backlog memory without loading the full master package.

## Scope
Track storage refs, MIME, extraction status and failures.

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
- Source required tests: failure/retry/progress tests
- Acceptance gate: `AT-SCALE-004`
- Run the smallest relevant repo checks for changed code.
- Run `python3 scripts/validate_repo.py` and `git diff --check` before closing the task.

## Acceptance criteria
- Source output satisfied: capex.document_manifest.v1.json
- Review focus covered: no raw sensitive data in logs
- Refactor focus covered: extraction state machine
- Docs requirement covered: document corpus docs
- Rollback/recovery posture recorded: documented if production-facing

## Source row mapping
- Source task ID: `INGEST-005`
- Source phase: `P5 Corpus ingest`
- Source priority: `P0`
- Source area: `document indexing`
- Original depends_on: `INGEST-002`
- Recommended source branch: `feature/capex-*`

## Notes / decisions
- Raw project corpora remain off-repo; use only sanitized fixtures, manifests, hashes, and aggregate evidence approved by the relevant fixture/governance task.

## Completion evidence
- Added `docs/planning/capex_source_ingest/DOCUMENT_MANIFEST_CONTRACT.yaml` for the `INGEST-005` document manifest and extraction-state artifact contract.
- Added `onetruth.capex_platform.document_manifest` to build deterministic `capex.document_manifest.v1` and `capex.extraction_state_register.v1` outputs from sanitized source-inventory rows.
- Added unit and contract coverage for extraction status/progress/failure/retry states, unknown and duplicate descriptors, raw path/filename/inline-content/log rejection, and non-activation boundaries.
- This closes planning artifact shape evidence only; extraction runtime, parser adapters, page manifests, chunk/evidence indexes, public routes, raw corpus import, reviewed evidence sufficiency, official pointers, and CAPEX runtime/product activation remain blocked.
