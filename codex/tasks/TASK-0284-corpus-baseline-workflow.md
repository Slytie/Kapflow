---
id: TASK-0284
epic: EPIC-143
title: "Corpus Baseline workflow"
status: DONE
completed_at: "2026-06-17T00:00:00Z"
owners: ["platform"]
reviewers: ["architect", "qa"]
depends_on: ["TASK-0269", "TASK-0278"]
risk: high
context_packs:
  - "codex/context/EPIC-143.md"
patterns: ["capex-v6-planning"]
---

## Why
Imported from CAPEX v6 source task `WFLOW-002` so future work can be executed from repo-native backlog memory without loading the full master package.

## Scope
Build inventory, occurrences, duplicates, roles, packets and handoff manifest.

## Out of scope
- Runtime or production activation beyond this task's explicit source scope.
- Copying raw K12, K3, or blind-validation project files into the repository.
- Treating generated artifacts, lab reports, or AI outputs as canonical authority.

## Source files to read first
- `docs/planning/CAPEX_MASTER_V6_INTAKE.md`
- `docs/planning/CAPEX_V6_CONVERSION_MAP.csv`
- `docs/planning/epics/EPIC-143.md`
- `codex/context/EPIC-143.md`
- `docs/status/CURRENT_FOCUS.md`
- `docs/architecture/invariants.md`

## Plan
1. Re-read the CAPEX intake record, this task's epic context, and the source row in the conversion map.
2. Start with the required tests or evidence listed below, then make the smallest repo-native change that satisfies the task.
3. Update docs/status/test evidence only where the source scope requires it.
4. Preserve tenant/domain isolation, artifact immutability, canonical approvals, and append-only event truth.

## Verification
- Source required tests: K12 source occurrence tests
- Acceptance gate: `AT-BRIDGE-005`
- Run the smallest relevant repo checks for changed code.
- Run `python3 scripts/validate_repo.py` and `git diff --check` before closing the task.

## Acceptance criteria
- Source output satisfied: source/occurrence/duplicate/role/packet artifacts
- Review focus covered: content!=occurrence!=role; no raw truth
- Refactor focus covered: packet builder extraction
- Docs requirement covered: corpus workflow docs
- Rollback/recovery posture recorded: documented if production-facing

## Source row mapping
- Source task ID: `WFLOW-002`
- Source phase: `P7 Workflows`
- Source priority: `P0`
- Source area: `workflow`
- Original depends_on: `INGEST-004; ART-003`
- Recommended source branch: `feature/capex-*`

## Notes / decisions
- Raw project corpora remain off-repo; use only sanitized fixtures, manifests, hashes, and aggregate evidence approved by the relevant fixture/governance task.

## Completion evidence
- Added `docs/planning/capex_workflow_catalog/corpus_baseline_workflow.yaml` as the planning-only Corpus Baseline workflow contract for `WFLOW-002`.
- Added `onetruth.capex_platform.corpus_baseline_workflow` to compose source inventory, occurrence register, role register, packet register, generated-artifact validators, and handoff-manifest references into deterministic workflow outputs.
- Added unit and contract coverage for a valid corpus baseline chain, missing role/packet prerequisites, scope mismatches, generated artifact envelope names, validator success, and non-activation boundaries.
- This closes the workflow prerequisite for downstream EPIC-143 workflow rows, but does not activate authored workflow packs, public routes, workpages, reviewed baseline truth, official pointers, raw corpus import, or CAPEX runtime/product behavior.
