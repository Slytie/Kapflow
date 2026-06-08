---
id: TASK-0564
epic: EPIC-141
title: "Add physical source_occurrence and sourceRef resolver"
status: DONE
completed_at: 2026-06-08T00:00:00Z
owners: ["platform"]
reviewers: ["architect", "qa"]
depends_on: ["TASK-0563"]
risk: high
context_packs:
  - "codex/context/EPIC-141.md"
patterns: ["capex-v6-planning"]
---

## Why
Imported from CAPEX v6 source task `NU-CB-P0-004` so future work can be executed from repo-native backlog memory without loading the full master package.

## Scope
Implement source occurrence runtime state and resolver; generated registers become attestations/exports.

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
- Source required tests: CB2-T005; sourceRef resolution tests
- Acceptance gate: `NU-GATE-004`
- Run the smallest relevant repo checks for changed code.
- Run `python3 scripts/validate_repo.py` and `git diff --check` before closing the task.

## Acceptance criteria
- Source output satisfied: source_occurrence table/model; sourceRef resolver; occurrence status enum
- Review focus covered: Meaningful source refs; no empty array / presence-only evidence
- Refactor focus covered: Additive schema; batch migration from fixture manifests only
- Docs requirement covered: Update corpus/evidence docs
- Rollback/recovery posture recorded: Disable evidence binding and closure gates until resolver passes

## Source row mapping
- Source task ID: `NU-CB-P0-004`
- Source phase: `P4 corpus foundation`
- Source priority: `P0`
- Source area: `capex/corpus/evidence`
- Original depends_on: `NU-CB-P0-003; W2 CED-005; W3 CED-011`
- Source-only dependency notes: `W2 CED-005; W3 CED-011`
- Recommended source branch: `capex/source-occurrence-foundation`

## Notes / decisions
- Raw project corpora remain off-repo; use only sanitized fixtures, manifests, hashes, and aggregate evidence approved by the relevant fixture/governance task.

## Closeout evidence
- Added ordered migration `20260608_0013_capex_source_occurrence_resolver.py`, SQLAlchemy models, SQLite bootstrap DDL, runtime schemas, and repositories for `capex_content_identities` and `capex_source_occurrences`.
- Added the CAPEX SourceRef resolver at `onetruth.capex_platform.source_refs` with canonical `source_occurrence:{source_occurrence_id}` parsing, scope checks, non-resolvable status denial, and meaningful-source-ref rejection for empty, malformed, unresolved, cross-scope, or non-resolvable refs.
- Source occurrences are sanitized runtime truth; generated registers remain exports/attestations only, and no raw K12/K3/blind corpus material was introduced.
- Evidence: `PYTHONPATH=src python3.11 -m pytest -q tests/unit/test_capex_source_occurrence_resolver.py` and `PYTHONPATH=src python3.11 -m pytest -q tests/integration/test_capex_source_occurrence_schema_parity.py` passed on 2026-06-08.
