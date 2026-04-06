# EPIC-133 - Workpage fragility reduction and extensibility hardening

## Summary
Reduce the remaining accidental complexity in the post-EPIC-131 workpage system so future workpages can be added without reintroducing fragility.

This epic starts after EPIC-132 and assumes the repo has a clean, green settlement baseline.

## Status
Selected.

Progress note: `TASK-0215` is complete. Canonical schedule, EOD, route-demand, and driver-preferences pages now consume backend-authored lineage/latest/accepted navigation from the workpage GET contract; the remaining client-side history helpers are deferred inline demo-shell debt for `TASK-0217`.

## First-principles objective
A workpage is a server-authored projection:

\[
W_k = \Pi_k(S, u)
\]

and a client should render and execute server-owned affordances rather than reconstructing workflow semantics locally.

This epic reduces accidental complexity so that adding a new workpage kind changes cost approximately linearly:

\[
\Delta C_{\text{future workpage}} \approx O(1)
\]

instead of forcing repeated edits across backend handlers, frontend route pages, demo shells, and client-side lineage heuristics.

## In scope
- move core workpage lineage/history/latest queries server-side
- promote server-authored action execution over raw `subject_link`/router-state semantics
- converge the demo shell on the canonical host and retire the independent inline mutation engine
- split the remaining large workpage concentration files and add architecture guardrails
- keep the public route posture canonical-only while simplifying how new workpages plug in

## Out of scope
- new product/workpage scope
- auto-rescheduling agent behavior
- date-specific driver exceptions
- generic workpage schema DSL or spreadsheet platform
- reopening the accepted-vs-draft distinction

## Dependencies
- EPIC-132
- EPIC-131
- EPIC-124
- EPIC-100

Context packs:
- `codex/context/EPIC-133.md`
- `codex/context/WORKPAGE_FORMAL_MODEL_AND_SETTLEMENT_RATIONALE.md`
- `codex/context/WORKPAGE_STABILITY_FINDINGS_2026-04-05.md`

## Tasks
- TASK-0215 - Move lineage, latest-draft, and accepted queries behind backend-owned workpage query seams
- TASK-0216 - Promote server-authored workpage action execution and deprecate raw subject-link writes
- TASK-0217 - Converge the demo shell onto canonical workpage hosts and retire inline mutation logic
- TASK-0218 - Split overloaded workpage modules and add architecture guardrails for bounded growth

## Acceptance criteria
- No core workpage page constructs history rails by listing all workflow-run artifacts and filtering client-side.
- Primary workpage create/submit flows derive workflow intent from server-authored actions, not ad hoc router state.
- `/demo/logistics` no longer owns an independent mutating engine for workpage artifacts.
- The largest workpage files are reduced to smaller, purpose-bounded seams with characterization tests or architectural guardrails.
- Adding a new workpage kind primarily requires descriptor/query/host registration rather than repeated special-case branching across many files.

## Key decision
The goal is not to build a general workpage runtime. The goal is to make the current workpage architecture boringly extensible: server-authored semantics, one mutating path, bounded query seams, and concentrated complexity pushed behind explicit modules.
