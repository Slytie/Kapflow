# CAPEX Backlog Taxonomy And Decomposition Guide

## Status
- Status: `AUTHORITATIVE_SOURCE`
- Owner task: `TASK-0585`
- Acceptance gate: `SD-GATE-004`
- Activation posture: `planning_only_no_capex_activation`

This guide defines the planning backlog hierarchy for CAPEX delivery work. It
does not activate runtime behavior, public routes, frontend workpages, workflow
packs, corpus import, pilot readiness, production readiness, or product use.

## Authoritative Hierarchy
The one authoritative backlog hierarchy is:

`product goal -> outcome epic -> feature -> vertical slice -> story -> given-when-then acceptance scenario`

Do not create duplicate backlog systems for CAPEX planning. Repo task files,
the CAPEX progress data generator, and the documents in this directory are
the planning evidence path for this tranche.

## Decomposition Rules
- Outcome epics must name the product-goal metric refs they intend to move.
- Features must identify the vertical slice or risk milestone they serve.
- Near-term stories must be vertical, testable, metric-linked, and tied to a
  slice or milestone.
- Every story must carry source/evidence refs before it can claim a governed
  blocker, readiness, closure, or officialness outcome.
- Given-When-Then acceptance scenarios must name the canonical truth surface:
  task, approval, artifact version, event, pointer, SourceRef, closure
  snapshot, or projection read model.
- Demo-only success criteria are invalid. A story succeeds only when its
  evidence can be replayed or inspected through repo-native contracts.
- Rollback or recovery notes are required for any story that changes runtime
  behavior in a future task.

## Template Set
Use these templates for new CAPEX planning work:

- `templates/outcome_epic_template.md`
- `templates/feature_template.md`
- `templates/vertical_story_template.md`
- `templates/gwt_acceptance_scenario_template.md`

The templates require metric refs, slice refs, source/evidence refs,
Given-When-Then acceptance, non-activation posture, and rollback or recovery
notes.

## Non-Activation Boundary
Closing `TASK-0585` records a backlog planning contract only. It is not CAPEX
runtime activation, product activation, public route approval, workflow pack
activation, corpus import approval, pilot approval, production approval, or a
substitute for later DoR and DoD work under `TASK-0588`.
