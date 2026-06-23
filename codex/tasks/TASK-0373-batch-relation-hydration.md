---
id: TASK-0373
epic: EPIC-141
title: "Batch relation hydration"
status: DONE
completed_at: 2026-06-23T00:00:00Z
owners: ["platform"]
reviewers: ["architect", "qa"]
depends_on: ["TASK-0273", "TASK-0372"]
risk: high
context_packs:
  - "codex/context/EPIC-141.md"
patterns: ["capex-v6-planning"]
---

## Why
Imported from CAPEX v6 source task `RF-005` so future work can be executed from repo-native backlog memory without loading the full master package.

## Scope
Batch load artifact links/provenance/tasks/flags instead of N+1.

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
- Source required tests: As required by quality gates: QG-06;QG-07;QG-08
- Acceptance gate: `QG-06;QG-07;QG-08`
- Run the smallest relevant repo checks for changed code.
- Run `python3 scripts/validate_repo.py` and `git diff --check` before closing the task.

## Acceptance criteria
- Source output satisfied: query/projection refactor PR + tests + docs
- Review focus covered: primary + specialist; gates=QG-06;QG-07;QG-08
- Refactor focus covered: Use conservative refactor policy; separate pure refactor unless local/tiny/justified.
- Docs requirement covered: Update docs/templates/registers as applicable; see QUALITY_OVERLAY.
- Rollback/recovery posture recorded: Required for Tier 3+ or phase closeout; otherwise document not applicable.

## Source row mapping
- Source task ID: `RF-005`
- Source phase: `P5`
- Source priority: `P0`
- Source area: `refactoring/query/projection refactor`
- Original depends_on: `phase preflight and safety net`
- Source-only dependency notes: `phase preflight and safety net`
- Recommended source branch: `feature/capex-rf-005`

## Notes / decisions
- Raw project corpora remain off-repo; use only sanitized fixtures, manifests, hashes, and aggregate evidence approved by the relevant fixture/governance task.

## Closeout evidence
- Extended `onetruth.infrastructure.repositories.artifact_relation_hydration` with workflow-run and subject page helpers that reuse the shared batch relation loader after scoped page selection.
- Added optional internal batch subject-summary hydration for `human_task` and `flag` artifact links without changing default public API response payloads.
- Preserved duplicate-ID rejection, the 5,000 artifact hydration cap, 500-row SQL chunks, scoped relation hydration, and no N+1 relation query posture.
- Added unit coverage for optional task/flag summaries, duplicate/scope guards, 5k chunked hydration, and bounded page adapters; runtime/API tests cover unchanged list envelopes.

## Boundary posture
- No public route shape changes, frontend activation, migrations, event-registry changes, raw corpus import, official pointer creation, reviewed-baseline claim, or CAPEX runtime/product activation.
