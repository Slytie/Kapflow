---
id: TASK-0540
epic: EPIC-151
title: "Add ceo_transparency_snapshot schema"
status: DONE
completed_at: 2026-06-23T00:00:00Z
owners: ["platform"]
reviewers: ["architect", "qa"]
depends_on: ["TASK-0277", "TASK-0290", "TASK-0539"]
risk: high
context_packs:
  - "codex/context/EPIC-151.md"
patterns: ["capex-v6-planning"]
---

## Why
Imported from CAPEX v6 source task `ARCH-W8-S04` so future work can be executed from repo-native backlog memory without loading the full master package.

## Scope
Projection over project/risk snapshots with freshness and caveats

## Out of scope
- Runtime or production activation beyond this task's explicit source scope.
- Copying raw K12, K3, or blind-validation project files into the repository.
- Treating generated artifacts, lab reports, or AI outputs as canonical authority.

## Source files to read first
- `docs/planning/CAPEX_MASTER_V6_INTAKE.md`
- `docs/planning/CAPEX_V6_CONVERSION_MAP.csv`
- `docs/planning/epics/EPIC-151.md`
- `codex/context/EPIC-151.md`
- `docs/status/CURRENT_FOCUS.md`
- `docs/architecture/invariants.md`

## Plan
1. Re-read the CAPEX intake record, this task's epic context, and the source row in the conversion map.
2. Start with the required tests or evidence listed below, then make the smallest repo-native change that satisfies the task.
3. Update docs/status/test evidence only where the source scope requires it.
4. Preserve tenant/domain isolation, artifact immutability, canonical approvals, and append-only event truth.

## Verification
- Source required tests: red test or characterization before implementation
- Acceptance gate: `W8-accepted-gates + semantic MR gate`
- Run the smallest relevant repo checks for changed code.
- Run `python3 scripts/validate_repo.py` and `git diff --check` before closing the task.

## Acceptance criteria
- Source output satisfied: Implementation artifact(s) implied by W8-S04; source wave W8; CED-linked design note; tests; docs update
- Review focus covered: product + architecture reviewer
- Refactor focus covered: separate pure refactor from behavior change unless tiny
- Docs requirement covered: Update relevant CED/ADR, architecture doc, catalog, and master traceability for W8
- Rollback/recovery posture recorded: disable capability or leave runtime state inert; no destructive rollback of governed state

## Source row mapping
- Source task ID: `ARCH-W8-S04`
- Source phase: `P12/P13 Snapshots and external boundary`
- Source priority: `P0/P1`
- Source area: `snapshots/dossiers/external`
- Original depends_on: `architecture CED accepted`
- Source-only dependency notes: `architecture CED accepted`
- Recommended source branch: `foundation/* or capex-runtime-disabled/*`

## Notes / decisions
- Raw project corpora remain off-repo; use only sanitized fixtures, manifests, hashes, and aggregate evidence approved by the relevant fixture/governance task.
- Closeout evidence: added `docs/planning/capex_transparency/CEO_TRANSPARENCY_SNAPSHOT_W8_FRESHNESS_CONTRACT.yaml`, `schemas/runtime/capex_ceo_transparency_snapshot_freshness.schema.json`, and `build_ceo_transparency_snapshot_freshness_outputs(...)` as a companion payload over the existing `capex.ceo_transparency_snapshot.v1` artifact, Risk/CEO workflow outputs, and optional RiskSignal outputs.
- Closeout boundary: this task does not replace the `TASK-0277` CEO snapshot artifact and creates no CEO cockpit/runtime view, runtime risk engine, public or frontend routes, migrations, event-registry changes, official pointers, closure snapshots, external-system activation, raw corpus import, or CAPEX product/runtime activation.
