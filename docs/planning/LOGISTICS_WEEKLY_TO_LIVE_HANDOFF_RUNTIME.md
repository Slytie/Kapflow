# LOGISTICS_WEEKLY_TO_LIVE_HANDOFF_RUNTIME.md

## Purpose
Define the first explicit composition/handoff runtime (`H`) slice for logistics:

\[
\Omega_2 = (\Omega_1, \mathcal D, \mathcal C, \mathcal H)
\]

This note lands only the first `H` execution surface:
- `weekly_schedule_planning.Stage07 -> live_dispatch.Stage01`
- fixture-only ingress
- deterministic first-slice behavior
- no second officialness path.

Status note (2026-03-09):
- this document remains scoped to the TASK-0062 weekly->live `materialize_seed` slice.
- a separate bounded TASK-0063 `notify_only` reporting->planning slice now exists (`dispatch_reporting.Stage05 -> weekly_schedule_planning.Stage03`) and should not be inferred from this note alone.

## Runtime object: edge execution
The first handoff state object is an explicit runtime row (not cursor-only state):

\[
EdgeExec=(edge\_id,source\_activation,target\_activation,correlation\_key,idempotency\_key,status,cursor\_state,compensation\_state)
\]

Required first-slice fields:
- `edge_execution_id`
- `edge_id` (`weekly_seed_to_live_dispatch`)
- `source_workflow_run_id`
- `source_stage_id` (`Stage07`)
- `source_artifact_version_id` (daily seed artifact)
- `target_workflow_run_id` (nullable until lazy activation)
- `target_workflow_id` (`live_dispatch.v1`)
- `target_partition_kind` (`ServiceDateID`)
- `target_partition_key` (`SD-YYYY-MM-DD`)
- `correlation_key` (deterministic per edge/source/day)
- `idempotency_key` (deterministic row identity)
- `trigger_ref` (first qualifying day-of trigger ref, optional before activation)
- `status` (`prepared|activated|consumed|stale|failed`)
- `cursor_state` (JSON for stream progress metadata)
- `compensation_state` (JSON, first-slice default `mark_stale`)

## Idempotency and recovery semantics
First-slice idempotency law:
- one logical handoff execution per `(edge_id, source_artifact_version_id, target_partition_key)`,
- retries with the same logical key return/update the same `edge_execution_id`,
- retries must not duplicate daily seed rows, live activation runs, or handoff rows.

Recovery posture:
- if seed materialization succeeded and activation failed, replay resumes from the existing `prepared` edge execution,
- if activation already succeeded, replay returns canonical `target_workflow_run_id` without duplicate run creation,
- duplicate trigger attempts for the same logical day update the same handoff execution state instead of creating a second row.

## Partition transform law
Typed transform remains authoritative from the logistics partition registry:

\[
\tau_{week\to day}: PlanningWeekID \to \mathcal P(ServiceDateID)
\]

Concrete first-slice transform:
- `planning_week_to_service_days`
- deterministic expansion to ISO week service-day IDs (`Mon..Sun`).

Materialization rule:
- Stage07 daily seeds are emitted as one logical seed per transformed `ServiceDateID`,
- each seed carries deterministic linkage back to the same published weekly schedule artifact version.

## Lazy live-dispatch activation
First-slice activation policy is `lazy` for `live_dispatch.v1`:
- Stage07 seed materialization creates `prepared` handoff executions only,
- live dispatch activation is created/resumed on first qualifying day-of operational trigger for the same `ServiceDateID`,
- activation uses canonical `workflow_runs` only (no second activation model).

## Exact lineage chain
The required lineage chain is:
1. Stage06 published weekly schedule (`planning.published_weekly_schedule.workbook`, official pointer).
2. Stage07 daily seed artifact (`planning.daily_dispatch_seed.workbook`) with explicit parent/provenance to the published weekly version.
3. Handoff execution row linking source seed to target `ServiceDateID` activation.
4. Live dispatch Stage01 inputs bound exactly for:
   - base seed,
   - day-of route delta event,
   - actual-hours snapshot.
5. Live dispatch official delta artifact (`dispatch.official_replan_delta.workbook`) promoted in ordered sequence with explicit lineage to the same seed/base chain.

Input-binding rule:
- live activation captures canonical workflow/task input bindings for seed/event/actual-hours artifacts with same-scope enforcement (`tenant_id`, `domain_id`, partition compatibility).

## First-slice policy defaults
- activation policy: lazy
- Stage07 seed shape: one logical seed per `ServiceDateID`
- live operational truth: ordered immutable delta history
- candidate ranking: deterministic ordering only (optional LLM rationale stays non-authoritative/off by default)
- major-replan threshold: policy-configured conservative defaults
- connectors: fixture-only

## Non-goals
- no availability-request automation handoff,
- no reporting handoff edges in this TASK-0062 slice,
- no timecard-audit runtime,
- no live external integrations.
