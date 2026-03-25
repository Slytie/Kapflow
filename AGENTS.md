# AGENTS.md - Instructions for Codex and Contributors

This repo is built for fresh-session Codex. Assume every session starts with zero memory.

## Read order
Keep the default context small. Only load deeper docs when the task actually touches them.

### Baseline (always)
1. `docs/status/CURRENT_FOCUS.md`
2. `docs/planning/STAGE4_PLAN.md`
3. `docs/planning/RUNTIME_BOOTSTRAP.md`
4. `docs/planning/FIRST_RUNTIME_SLICE.md`
5. `docs/planning/STEP_RUN_SCENARIO_HARNESS.md`
6. `docs/planning/TDD_IMPLEMENTATION_PLAN.md`
7. `docs/architecture/invariants.md`
8. `schemas/events/envelope.schema.json`
9. `schemas/events/event_type_registry.yaml`
10. `scripts/validate_repo.py`

### Workflow pack (task-dependent)
- Default workflow (new agentic scheduling/runtime wedge): logistics family weekly/live surface
  - `docs/workflows/logistics_ops_family/v1/README.md`
  - `docs/workflows/weekly_schedule_planning/v1/WORKFLOW_CONTRACT.yaml`
  - `docs/workflows/live_dispatch/v1/WORKFLOW_CONTRACT.yaml`

- Workpage FE v0 tasks (`EPIC-120`):
  - `docs/planning/LOGISTICS_WORKPAGES_V0_PLAN.md`
  - `docs/planning/LOGISTICS_WORKPAGES_V0_PRODUCT_BRIEF.md`
  - `docs/workflows/weekly_schedule_planning/v1/OPERATING_MODEL.md`
  - `docs/workflows/live_dispatch/v1/OPERATING_MODEL.md` (boundary check only; do not drift into live dispatch)
  - `docs/workflows/weekly_schedule_planning/v1/examples/*`
  - `docs/workflows/dispatch_reporting/v1/WORKFLOW_CONTRACT.yaml`
  - `docs/workflows/dispatch_reporting/v1/OPERATING_MODEL.md`
  - `docs/workflows/dispatch_reporting/v1/examples/*`
  - `fixtures/frontend_contracts/README.md`
  - `fixtures/logistics/workpages/*`

- Load `docs/workflows/schedule_planning/v1/` only for regression/reference coverage:
  - when validating legacy schedule-only behavior against existing traces,
  - or when a shared semantic change must be cross-checked against the legacy authored surface.

- Load `docs/workflows/payroll/v1/` only if:
  - the task is explicitly tagged `payroll`, or
  - the change is to shared semantics that must be validated against a linear approval-heavy reference workflow.

  Payroll golden traces are still placeholder-only. Use Payroll primarily as an authored-surface and governance cross-check, not as the default replay corpus.

### Only when needed (do not load by default)
- Authority / source-of-truth changes:
  - `docs/architecture/AUTHORITY_MODEL.md`
  - `docs/architecture/DOCUMENT_STATUS_MATRIX.md`
  - `docs/architecture/DERIVATION_AND_GENERATION_POLICY.md`
  - `docs/architecture/LOWERING_CONTRACT.md`
- Shared governance / control-plane semantics:
  - `docs/architecture/governance_vocabulary.md`
  - `docs/architecture/orchestration_semantics.md`
  - `docs/architecture/approval_model.md`
  - `docs/architecture/human_task_semantics.md`
  - `docs/architecture/flag_model.md`
  - `docs/architecture/RUNTIME_OBJECT_MODEL.md`
- Shared schema registries:
  - `schemas/policy/governance_vocabulary.yaml`
  - `schemas/policy/permissions.yaml`
  - `schemas/agentic/tool_class_registry.yaml`
  - `schemas/workflows/workflow_contract.schema.json`
  - `schemas/workflows/artifact_map.schema.json`
  - `schemas/runtime/*.schema.json`
  - `schemas/events/payloads/*.schema.json`
- Testing:
  - `docs/planning/TEST_STRATEGY.md`
  - `docs/planning/TEST_MATRIX.md`
  - `docs/planning/TDD_IMPLEMENTATION_PLAN.md`
  - `tests/README.md`
  - `tests/helpers/scenario_catalog.py`
- Production lane / Workflow Lab planning:
  - `docs/planning/PRODUCTION_AND_WORKFLOW_LAB_PLAN.md`
  - `docs/planning/epics/EPIC-100.md`
  - `docs/planning/epics/EPIC-110.md`
  - `codex/context/EPIC-100.md`
  - `codex/context/EPIC-110.md`

## Task-specific context loading
If the task maps to an epic with a context pack:
- read `codex/context/README.md`
- read the relevant `codex/context/EPIC-0XX.md`
- read only the listed pattern card(s) under `docs/patterns/cards/`
- open `docs/patterns/sources/converted/` only if the task directly touches that subsystem

If you need implementation architecture or file-placement guidance:
- read `docs/planning/RUNTIME_BOOTSTRAP.md`
- read `docs/planning/FIRST_RUNTIME_SLICE.md`
- read `docs/planning/STEP_RUN_SCENARIO_HARNESS.md` if the task touches runtime scenario tests or step-by-step agent execution

If you need deeper background or design justification:
- read `docs/research/AGENT_DIGEST.md` first
- open a full research note only as needed

If the task is about productization or Workflow Lab:
- read `docs/planning/PRODUCTION_AND_WORKFLOW_LAB_PLAN.md`
- read the relevant epic file under `docs/planning/epics/`
- read the matching context pack under `codex/context/`
- keep the default promotion model as `lab -> review/certification/release -> prod`, not direct runtime mutation

If the task changes tests, retry/idempotency logic, or acceptance criteria:
- read `docs/planning/TEST_STRATEGY.md`
- read `docs/planning/TEST_MATRIX.md`
- read `docs/planning/TDD_IMPLEMENTATION_PLAN.md`
- read `docs/planning/STEP_RUN_SCENARIO_HARNESS.md` if runtime step tests are in scope
- inspect the relevant scenario trace under `fixtures/workflows/schedule_planning/golden_event_traces/` when legacy regression behavior is in scope

## Stage 4 runtime/debug posture
- For new agentic scheduling work, the implementation/debug wedge is the logistics weekly/live path (`weekly_schedule_planning.v1 -> live_dispatch.v1`).
- The current acceptance objective for new scheduling work is a **fully-agentive** weekly/live logistics slice where designated agent principals execute every in-scope stage without bypassing canonical runtime truth.
- Legacy `schedule_planning.v1` remains regression/reference-only in this posture.
- This objective does **not** authorize a second agent-only truth path. Agents must still operate through the same workflow/task/approval/event/pointer substrate.
- Payroll remains a secondary reference workflow used to validate the same shared semantics against a linear approval-heavy flow.
- The current application-facing FE slice is `EPIC-120`: full-page fixture-backed workpages for weekly schedule review and end-of-day reporting under `/demo/logistics/workpages/*`.
- Keep the schedule page on the weekly-planning side of the boundary; day-of replan belongs to `live_dispatch.v1`.
- Keep the EOD page on the reporting draft/review side of the boundary; do not anchor it to Stage05 final-packet semantics in v0.
- Workpage fixtures are human-authored planning/test fixtures and are intentionally distinct from backend-owned `fixtures/frontend_contracts/` snapshots.

## Non-negotiable invariants
- **One truth system**: official claims come only from immutable objects, append-only events, and audited pointers.
- **Tenant + domain isolation**: never cross tenant/domain boundaries in reads, writes, exports, projections, or generated material.
- **Artifact immutability**: artifacts are immutable versions; officialness is defined only by promotion pointers and explicit deltas.
- **Single event system**: business execution and agentic execution share one timeline envelope and one link model.
- **Single approval system**: business approvals, execution gates, and future method-change approvals are one canonical object model with different kinds.
- **Generated artifacts are not source**: do not hand-edit generated runbooks, tool matrices, approval logs, or generated CompanyOS IR as if they were authoritative workflow definitions.
- **Automation safety**: no side-effecting tool execution without policy, budget, and approval controls. LLM outputs are untrusted.
- **No agent-only state authority**: a fully-agentive test slice is allowed only if it preserves the canonical workflow/task/approval/event model.
- **Workflow Lab is non-authoritative**: lab outputs may evaluate kernel behavior, but may not become a peer workflow-definition or promotion-truth system.
- **Prod and lab do not share live state**: separate DBs, artifact roots, and secrets; tenant/domain separation inside one environment is not an acceptable replacement for prod-vs-lab separation.
- **Promotion is release-mediated by default**: until explicit parallel-version support is proven, promote lab candidates by reviewed release rather than live runtime mutation of production workflow truth.

If you change any of the above, you MUST:
- update `docs/architecture/AUTHORITY_MODEL.md`
- update `docs/architecture/DERIVATION_AND_GENERATION_POLICY.md`
- update affected workflow packs, schemas, and acceptance/test docs
- record the decision in `docs/status/DECISIONS_SINCE_LAST.md`
- add an ADR when the authority chain or runtime contract changes

## How to work here
Follow `LLM_RUNBOOK.md`.

Rules of thumb:
- make small PRs
- update repo-native source before touching any generated derivative
- prefer schema-first and contract-first changes
- start behavior changes by updating the relevant tests and trace oracles
- run `make schema-validate` and the smallest relevant pytest suite before proposing runtime changes
- preserve the distinction between authored source, compiled artifact, generated derivative, and evidence
- put first runtime code under the locations chosen in `docs/planning/FIRST_RUNTIME_SLICE.md`; do not scatter it across `scripts/`, `tests/helpers/`, or ad hoc notebooks
