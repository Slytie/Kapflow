# DECISIONS_SINCE_LAST.md

Record any decisions made since the last session so a fresh Codex run can rehydrate quickly.

## 2026-03-03 (conditional task spawning and step-run test planning)
- Stage 4 now explicitly allows **conditional follow-on task spawning**: completing a task may create one or more child task runs for information requests, re-review, final review, or issue-scoped child work.
- Child-task creation must stay inside the same workflow run and remain explicit through `task.run.created` / `task.created`; no new hidden side-effect path or separate `task.spawned` truth system is introduced.
- The first runtime implementation should create deterministically implied child tasks in the same transaction as the parent completion or approval response, reserving the decider/reconciler for timers, flags, and repair.
- Added `docs/planning/STEP_RUN_SCENARIO_HARNESS.md` and TASK-0039 so future runtime work must include step-run tests where an agent executes each step and the test asserts authoritative truth.
- The workflow `template_pack/` folders already contain synthetic completed example artifacts and are now the planned seed inputs for runtime scenario tests; the validator now checks that both empty templates and completed examples exist.

## 2026-03-03 (runtime bootstrap locked for development)
- Stage 4 runtime will start as a **Python modular monolith** under `src/onetruth/`, not as an external workflow engine and not as early microservices.
- The canonical persistence substrate is **PostgreSQL current-state tables + append-only `timeline_events`**, with immutable artifact blobs stored behind a pluggable object-store adapter.
- `timeline_events` will also serve as the **outbox substrate** for derived consumers; wakeups may use notifications/polling, but consumer truth is a cursor over the canonical timeline.
- The first code slice is **core substrate + Schedule Planning Stage06 publish path**, followed by the Stage07 issue-scoped replan loop.
- `docs/planning/RUNTIME_BOOTSTRAP.md` and `docs/planning/FIRST_RUNTIME_SLICE.md` are now the authoritative implementation-architecture entrypoints for fresh-session Codex work.
- Completed TASK-0028 and refreshed stale routing/context so default runtime work no longer incorrectly points fresh agents to Payroll traces.

## 2026-03-03 (test-first harness adoption)
- Adopted a pytest-backed Stage 4 TDD harness rooted in schemas, golden traces, and acceptance scenario oracles rather than prose-only guidance.
- Added `docs/planning/TDD_IMPLEMENTATION_PLAN.md` so fresh-session Codex runs can start from a stable test-first workflow.
- Added a non-authoritative reference replay reducer and stable `AT-SCH-001` .. `AT-SCH-007` scenario catalog under `tests/helpers/` to make the existing traces executable.
- Added a dedicated `schedule_policy_gate_enforced.jsonl` trace so AT-SCH-007 (sandbox/policy gate) now has first-class trace coverage.
- Default verification flow for runtime work is now `make schema-validate`, `make contract`, `make replay`, `make acceptance`, then implementation-specific suites.

## 2026-03-02 (semantic closure before runtime planning)
- Added a shared governance vocabulary and machine-readable registry for actor taxonomy, approval response verbs, approval outcomes, and approval permission actions.
- Canonical actor taxonomy is now `human | agent | service | system`; stale `user` actor types were removed from authoritative schemas.
- Canonical approval permission actions are now `approval.request` and `approval.respond`; stale `approval.grant` wording was removed.
- Schedule Planning now carries explicit temporal partition semantics: service interval, logical date, timezone, catchup policy, backfill policy, and stage-rerun policy.
- Workflow contracts now distinguish `event_inventory.platform_required` from `event_inventory.workflow_required` so runtime/task/execution events are no longer implicit.
- Added a tool-class registry, workflow-pack schemas, runtime object schemas, event payload schemas, and a concrete sandbox policy schema.
- Added a repo validation harness (`scripts/validate_repo.py`) and Makefile targets so a fresh agent can validate contracts and traces before starting runtime work.
- Added Schedule Planning golden traces for happy path, fully-agentive whole flow, drift after review, lease expiry recovery, degraded mode survivability, and cross-scope denial.

## 2026-03-02 (schedule-first Stage 4 pivot)
- Stage 4 now treats `schedule_planning.v1` as the primary runtime/debug wedge.
- The primary Stage 4 acceptance objective is a fully-agentive Schedule Planning flow where designated agent principals can execute every in-scope task while preserving the same canonical task, approval, event, and pointer substrate.
- This fully-agentive objective is a debugging and validation posture, not permission to create a second agent-only truth system.
- Payroll remains in Stage 4 as the secondary reference workflow used to validate the shared substrate against a linear approval-heavy path.
- Added `docs/workflows/payroll/v1/OPERATING_MODEL.md` so both workflow packs now expose the full authored surface declared by the authority model.

## 2026-02-28
- Added `schedule_planning.v1` as a second Stage 4 workflow contract pack for a same-day delivery operator; at that point Payroll remained the primary implementation slice (later superseded by the 2026-03-02 schedule-first pivot).
- Schedule Planning is partitioned by `ScheduleDateID` (`SD-YYYY-MM-DD`) and uses the same `(tenant_id, domain_id)` scoping model as Payroll.
- Published schedules are treated as stable base plans; live-day changes must be recorded as new artifact versions / replan deltas rather than silent edits.
- Availability artifacts for scheduling may store coded leave/absence types, but must not store medical or disciplinary detail.

## 2026-02-28 (merger update)
- The repo now explicitly adopts one truth system: immutable objects + append-only events + audited pointers.
- The CompanyOS packet is preserved as philosophy, mathematics, threat model, and lowering target, not as a second authored workflow-definition system.
- Per-workflow authored semantics now include two repo-native execution-overlay files: `DECISION_CATALOG.yaml` and `EXECUTION_PROFILE.yaml`.
- Generated runbook packs, tool matrices, approval logs, and CompanyOS IR are treated as generated derivatives, not authoritative source.
- Business execution and agentic execution will share one event system, one approval model, and one run model.
