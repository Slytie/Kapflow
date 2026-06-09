# CURRENT_FOCUS.md

## Stage
Stage 4 - Vertical Slice MVP (repo merged around one truth system)

## Current milestone
Primary runtime/debug work remains the logistics weekly/live family. EPIC-131, the EPIC-126 Workpages v1 cleanup trio, and EPIC-132 are complete, and the public Workpages v1 posture is now canonical-only:
- frontend workpage routes live under `/runs/:workflowRunId/workpages/*`
- backend workpage APIs live under `/api/v1/workpages/workflow-runs/{workflow_run_id}/{workpage_kind}*`
- `/demo/logistics` remains the shell entrypoint, but nested demo workpage routes are retired

The just-completed workpage settlement closeout now leaves the repo with:
- a dedicated backend mutation lane via `make PYTHON=python3.11 workpage-mutation-smoke`
- a dedicated frontend workpage lane via `make frontend-workpages-smoke`
- supported-environment verification truth anchored to Python `3.11` and Node `20` clean installs

The just-completed app-facing workpage tranche is **EPIC-133 - Workpage fragility reduction and extensibility hardening**:
- backend-owned lineage/latest-draft/history seams are complete for canonical workpage pages
- server-authored action execution is complete for canonical create/submit flows
- `/demo/logistics` is now a launcher-only shell that hands off to canonical workpage/workspace routes
- the former concentration files now resolve through thinner facades and explicit source-budget guardrails

The just-completed demo-enablement tranche is **EPIC-134 - Minimal canonical workpage demo enablement**:
- supported-environment truth is corrected for the weekly-first local demo smoke and reporting-intake dependency classification
- `scripts/run_logistics_workpage_demo_prep.py` provides a deterministic, idempotent canonical workpage prep path with machine-readable route output
- `docs/ops/runbooks/logistics_canonical_workpage_demo.md` now documents the supported canonical workpage walkthrough without requiring OpenAI
- prep-script regressions and docs-as-truth guardrails now cover the canonical route walkthrough and runbook discoverability

The just-completed production-shaped cadence milestone is **TASK-0156 - External cadence tick and single-node logistics operator runbook**:
- `onetruthctl cadence tick-logistics` now ensures due weekly/reporting state and prepares live dispatch once weekly publish truth exists
- `docs/ops/runbooks/logistics_single_node_cadence.md` documents the bounded continuous single-node operator posture over the existing release/deploy topology

The current demo-facing weekly-planning enhancement is the landed **route-demand week-by-week activation plus existing-week coverage** slice:
- `route-demand-v0` now shows one editable operational week at a time
- `Add a week` creates or reopens the real next weekly run and seeds an empty future-week route-demand artifact there
- future-week `Save and run scheduling agent` remains the explicit greenfield scheduling trigger from route demand
- the shared route-demand editor now lets operators edit both planned route counts and on-call targets in the popup and full-page artifact view
- future-week scheduling activation now treats positive on-call target demand the same as positive route demand, while existing-week coverage remains route-increase-only
- existing-week positive route-count increases can use `Run coverage agent` to save or reuse successor route-demand truth, then hand off into the canonical `schedule-v0` quick-edit popup with backend-ranked coverage recommendations
- plain route-demand save no longer spawns the legacy refresh task
- successful future-week scheduling activation still hands off to the canonical `schedule-v0` route and reuses the existing quick-edit popup entrypoint
- successful existing-week coverage apply stays in the pre-publish weekly-draft lane and creates the successor `planning.draft_weekly_schedule.workbook` draft only from the backend coverage-apply path

The current dispatch-reporting operator enhancement is the landed **service-date-selectable route-activity upload** slice:
- the `Upload route activity` popup now lets operators pick the reporting service date after choosing the workbook
- the selected service date is authoritative upload metadata, ahead of filename-derived dates
- when the selected date differs from the current EOD run, the popup resolves or creates the matching `dispatch_reporting.v1` run and continues closeout there

EPIC-125 is now completed history:
- `TASK-0154` is reconciled to `DONE` from the already-landed live-dispatch delta lane exercised by runtime handlers, the local demo smoke, and the operator runbooks
- `TASK-0157` records the first-demo feedback handoff in `docs/domains/logistics/archive/LOGISTICS_WORKPAGES_EPIC125_CLOSEOUT_AND_FEEDBACK_NOTE.md`
- no EPIC-125 carry-forward task remains open

EPIC-126 remains completed cleanup history, but it is no longer the active post-EPIC-131 plan.

## Current implemented baseline
- weekly schedule landing, artifact editor, live preview, pinned dependency baselines, backend-authored accepted/draft lineage metadata, and backend-ranked route-demand coverage handoff on canonical schedule routes
- `route-demand-v0` run landing plus artifact-backed immutable day-count editor with next-week activation, existing-week coverage handoff, and explicit save-and-run scheduling paths
- `driver-preferences-v0` run landing, snapshot creation, artifact-backed editor/history, and soft advisory schedule integration
- `eod-v0` run landing plus canonical artifact-backed immutable workbook editing
- backend workspace workpage actions with active vocabulary `open_route | create_then_open`
- backend-owned frontend snapshots for canonical schedule, route-demand, driver-preferences, EOD, workspace, board, run-detail, timeline, and official-output surfaces

Canonical workpage routes now in active use:
- frontend:
  - `/runs/:workflowRunId/workpages/schedule-v0`
  - `/runs/:workflowRunId/workpages/schedule-v0/artifacts/:artifactVersionId`
  - `/runs/:workflowRunId/workpages/route-demand-v0`
  - `/runs/:workflowRunId/workpages/route-demand-v0/artifacts/:artifactVersionId`
  - `/runs/:workflowRunId/workpages/driver-preferences-v0`
  - `/runs/:workflowRunId/workpages/driver-preferences-v0/artifacts/:artifactVersionId`
  - `/runs/:workflowRunId/workpages/eod-v0`
  - `/runs/:workflowRunId/workpages/eod-v0/artifacts/:artifactVersionId`
- backend:
  - `GET /api/v1/workpages/workflow-runs/{workflow_run_id}/{workpage_kind}`
  - `GET /api/v1/workpages/workflow-runs/{workflow_run_id}/{workpage_kind}/artifacts/{artifact_version_id}`
  - `POST /api/v1/workpages/workflow-runs/{workflow_run_id}/{workpage_kind}/artifacts/{artifact_version_id}/submit`
  - `POST /api/v1/workpages/workflow-runs/{workflow_run_id}/schedule-v0/artifacts/{artifact_version_id}/preview`
  - `POST /api/v1/workpages/workflow-runs/{workflow_run_id}/eod-v0/drafts`
  - `POST /api/v1/workpages/workflow-runs/{workflow_run_id}/driver-preferences-v0/snapshots`

Frozen product boundary:
- `schedule-v0` = reassignment/on-call edits plus recalculation only
- `route-demand-v0` = route-demand truth editor
- `driver-preferences-v0` = soft/advisory weekly snapshot
- accepted history and draft lineage remain separate

Still deferred beyond the currently implemented baseline:
- contact-data authoring surfaces
- generalized live-dispatch workpage productization beyond the shared schedule popup
- broader feedback-driven operator hardening beyond the current bounded pre-publish route-demand activation and coverage slice

## Available broader backlog (after EPIC-134)
No EPIC-125 carry-forward backlog item remains open.
Future app-facing product expansion after this landed route-demand slice should still be selected deliberately from later feedback and deferred items, not implied by stale task state.

## Test-first working mode
Before adding runtime services or API surfaces:
1. update authoritative docs / schemas / traces,
2. update the scenario catalog and pytest oracles,
3. then implement runtime code.

Default verification loop:
- `make assurance-fast`
- `make schema-validate`
- `make contract`
- `make replay`
- `make acceptance`
- `make security`

## CAPEX v6 imported planning backlog
- CAPEX v6 is imported as gated planning backlog only: `TASK-0233` through `TASK-0606`, with `TASK-0233` through `TASK-0243` completed as prerequisite planning/platform hygiene, runtime safety hardening, PF0 repo-readiness declaration, release/backup readiness evidence, and lab-only auth smoke readiness.
- The EPIC-150 desktop source-root/sync separate pack is now integrated as gated planning backlog only: source-pack `TASK-0589..TASK-0624` was renumbered to repo-native `TASK-0607..TASK-0642` to avoid collisions with existing `TASK-0589..TASK-0606`; snippets under `codex/snippets/EPIC-150/` are context-only and not production patches.
- The SME-RP real-project acceptance-condition tranche is integrated as planning-only backlog: source archive labels used `SME-K12` and source rows `TASK-0625..TASK-0641`, while this repo uses generalized `SME-RP` labels, gates `SME-RP-G001..SME-RP-G013`, and remapped tasks `TASK-0648..TASK-0664`. `K12-T1..T10` remain fixture-case IDs only.
- `TASK-0648` and `TASK-0649` are closed as planning-only SME-RP closeouts: approval-with-conditions is conditional/module-specific/non-activation, and the `capex_scope` contract records the minimum scope hierarchy without adding runtime state.
- `TASK-0650` and `TASK-0651` are closed as planning-only SME-RP closeouts: RACI is a business-responsibility overlay rather than authorization authority, and evidence presence is not evidence sufficiency.
- `TASK-0235` closes artifact storage confinement and auth-before-read as repo runtime safety posture; `TASK-0236` closes transaction composition safety for schedule-control and logistics-handoff handlers.
- `TASK-0237` adds a non-permanent-red CAPEX invariant audit over resolved safety gates and known gaps; `TASK-0238` adds the canonical generated-artifact helper foundation; `TASK-0239` adds shared run/input/edge helpers plus activation-key drift detection; `TASK-0240` declares PF0 for repo platform readiness only; `TASK-0241` adds digest-addressed API image release evidence; `TASK-0242` adds validate-only predeploy backup manifest evidence; `TASK-0243` adds a lab-only shared-env JWT viewer smoke.
- `TASK-0244` is implemented as a lab VM deploy plan/execute lane but remains `BLOCKED` until an operator supplies live lab GCP target details and a real execute-and-smoke run records evidence.
- EPIC-139 redo acceptance is closed as of `TASK-0645`, with task-by-task reclose evidence in `TASK-0646` and closure handoff evidence in `TASK-0647`: the checkout is now classified as State C / repaired after the prior State B false-green finding. Approval and workpage defaults are platform-neutral, logistics behavior activates explicitly, tests/audit reject the old default-logistics pattern, EPIC-150 wording is corrected, and final validation ran under Python 3.11 / Node 20. Old EPIC-139 task closeouts remain historical evidence; do not rewrite them.
- Downstream EPIC-139 RED-only interlocks from `TASK-0644` are lifted after neutral-default acceptance. EPIC-139 cleanup should not be reopened without a new concrete defect; CAPEX runtime activation still remains blocked by the later project/data-governance/capacity/release/production-preflight gates below.
- EPIC-140 project/access foundation plus SME-RP scope/RACI addenda are closed. `TASK-0261` through `TASK-0265`, `TASK-0371`, `TASK-0381` through `TASK-0390`, `TASK-0563`, `TASK-0649`, and `TASK-0650` are closed with durable `capex_projects`, direct `project_memberships`, minimal project APIs, project-bound workflow-run creation, project-scoped child routes, the first max-five project selector/dashboard, a shared project-scope helper, project-scoped official pointer families, neutral/ready/incubation domain manifests, approval-effect registry shadow parity, project authorization CED, projection-backed `AuthorizedProjectsQuery`, storage/blob custody CED, W1 evidence, physical authorization projection runtime state, planning-only `capex_scope` hierarchy contract, and RACI role-permission matrix. CAPEX activation remains blocked by later source-governance, workflow/workpage, storage evidence or waiver, release/capacity, and production-preflight gates.
- The first post-EPIC-140 P0 chain pair is now closed across EPIC-141/142: `TASK-0564` adds physical `capex_content_identities` / `capex_source_occurrences` runtime truth plus a meaningful SourceRef resolver, and `TASK-0565` adds internal waiver, closure-gate evaluation, closure-snapshot, and stale recurrence primitives. CAPEX runtime activation remains blocked until remaining imported P0, three-project, data-governance, capacity/restore, release, and production-preflight gates close or receive explicit waivers.
- The next P0 chain pair is now closed across EPIC-143/144: `TASK-0566` adds the internal CAPEX workflow handoff manifest contract and validation guard over exact artifact/pointer/source/closure basis, and `TASK-0567` adds internal project-scoped workpage projection snapshot state plus signed projection cursors and stale-command guards. CAPEX workflow/workpage runtime activation, public CAPEX workpage APIs, frontend CAPEX workpage routes, and raw corpus use remain blocked.
- The next dependency pair is now closed across EPIC-149/151: `TASK-0568` adds the CAPEX semantic test marker, CB2 backlog manifest, focused Make/GitHub lane, and real-owner CODEOWNERS evidence; `TASK-0569` adds the internal interface-burden conservation policy helper and doc. These are quality/governance foundations only; CAPEX runtime activation, public CAPEX workflow/workpage behavior, raw corpus use, hosted branch-protection claims, and production/pilot readiness remain blocked.
- Logistics weekly/live/workpages remain the current implementation focus unless a CAPEX task explicitly changes shared platform semantics.
