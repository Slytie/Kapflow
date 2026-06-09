# CAPEX Workpage-To-Task Generation Contract

## Status
Accepted planning contract for `TASK-0653` and `SME-RP-G005`.

## Purpose
CAPEX workpages may surface blockers and command surfaces, but they are
projections over canonical project truth. They never set official project
status by projection update, row state, local UI state, or generic status
command.

This is a planning contract only. It does not add public CAPEX workpage APIs,
frontend routes, runtime command implementation, migrations, schemas, raw
corpus import, or CAPEX product activation.

## Workpage blocker types
The workpage blocker type vocabulary is exactly:

1. `missing_evidence`
2. `missing_responsibility`
3. `revision_required`
4. `commercial_cost_gap`
5. `safety_readiness_gap`
6. `contradictory_evidence`

## Canonical routing
A workpage-originated blocker must become one or more canonical outputs before
it can affect official readiness or closure:

- `task`
- `flag`
- `approval`
- `artifact_delta`
- `event`
- `pointer_request`

Workpages may propose canonical work. They do not create a second state store,
official closure lane, commercial authority, evidence-sufficiency authority, or
project-status authority.

## Required guards
Every future workpage-to-task generation command must require:

- `stale_basis_check`
- `source_binding`
- `actor_authority`
- `audit_evidence`

Invalid signatures, expired cursors, stale or superseded projection snapshots,
basis-hash mismatches, unresolved SourceRefs, missing actor authority, and
missing audit evidence must reject before canonical work is created.

## Officialness guardrails
Workpage projections cannot set closure, evidence sufficiency, commercial
status, safety readiness, or official project status. A workpage row may expose
a blocker, draft command, task proposal, approval prompt, flag, evidence
request, artifact-delta proposal, event proposal, or pointer request only.

Generic status commands are not allowed. Official readiness and closure require
the canonical workflow/task/approval/event/artifact/pointer substrate and the
applicable scope, evidence, RACI, and waiver contracts.

## Activation rule
Public CAPEX workpages, read APIs, command APIs, frontend routes, projection
families, and executive views must not claim SME-RP readiness until they
preserve these workpage-to-task generation rules or record an explicit waiver.
