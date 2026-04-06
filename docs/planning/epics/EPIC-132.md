# EPIC-132 - Workpage reliability settlement and repo-truth closeout

## Summary
Freeze the current post-EPIC-131 baseline, reconcile the 2026-04-05 settlement findings against the live repo, and restore a clean, green, reproducible public workpage boundary from supported environments.

This epic is about settlement, not new product scope.

## Status
Completed on 2026-04-06 through `TASK-0211`, `TASK-0212`, `TASK-0213`, and `TASK-0214`. The settlement epic now leaves the repo on a clean, reproducible baseline and hands the next hardening tranche to EPIC-133.

## First-principles objective
A public workpage mutation is valid only if it behaves like a deterministic, idempotent state transition on canonical truth:

\[
M_k : (S, u, a, x) \mapsto (S', \Delta E)
\]

For the current workpage family, this epic restores the minimum invariants required for that statement to be true in practice:
- clean canonical route ownership,
- no shared-helper regressions in write paths,
- truthful idempotency expectations,
- tests/fixtures/docs consistent with the real public posture,
- reproducible verification from a supported environment.

The first implementation step is not “assume the packet snapshot is still current.” It is:
- freeze the current clean baseline,
- classify what the packet found on 2026-04-05,
- and only then fix any genuine committed or supported-env regression that remains.

## In scope
- import the post-EPIC-131 settlement plan, epic docs, context packs, and task briefs into repo truth
- reconcile the 2026-04-05 findings against the live repo state
- fix committed or current supported-env workpage write-path regressions that still remain after reconciliation
- add a narrow mutating smoke suite for public workpage flows
- finish canonical-only docs, fixtures, and contract-truth synchronization
- restore reproducible frontend verification from the documented Node 20 clean-install baseline
- close the epic only from a clean checkout with the targeted suites green

## Out of scope
- new product/workpage scope
- changing the schedule/route-demand/preferences boundary
- server-authored action execution refactor
- server-side lineage query refactor
- demo-shell architectural convergence
- automatic agentic re-scheduling

## Dependencies
- EPIC-131
- EPIC-124
- EPIC-100

Context packs:
- `codex/context/EPIC-132.md`
- `codex/context/WORKPAGE_FORMAL_MODEL_AND_SETTLEMENT_RATIONALE.md`
- `codex/context/WORKPAGE_STABILITY_FINDINGS_2026-04-05.md`

## Tasks
- TASK-0211 - Freeze the workpage settlement baseline and reconcile historical findings against live repo truth
- TASK-0212 - Restore green workpage mutation flows and add the shared smoke gate
- TASK-0213 - Finish canonical-only docs, fixtures, and contract-truth synchronization
- TASK-0214 - Restore reproducible frontend verification and close from a clean checkout

## Acceptance criteria
- The active workpage repo state is a clean checkout, not an ambiguous WIP tree.
- Supported-environment verification is the truth source for remaining mutation failures:
  - Python `3.11` with `python3.11 -m pip install -e ".[api,dev]"`
  - Node `20` with `npm ci` from the committed lockfile
- Representative public write paths are green:
  - EOD create/replay,
  - EOD submit/replay,
  - schedule submit/replay,
  - route-demand submit plus single refresh-task behavior,
  - driver-preferences create/submit,
  - weekly publish happy path and drift fail-closed path.
- Tests assert the correct semantic quantity rather than accidentally asserting whole-run artifact totals.
- Active docs, fixtures, contract snapshots, and route tests all agree that the public posture is canonical-only.
- Frontend verification is reproducible from documented environment/setup rather than relying on packaged local state.

## Key decision
Do not begin the next architectural hardening tranche until this epic produces a clean, green settlement baseline. Feature-complete but unsettled is not an acceptable resting state for public workpage writes.
