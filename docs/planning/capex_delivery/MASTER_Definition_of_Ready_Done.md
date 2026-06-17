# CAPEX Definition Of Ready And Done

## Status
- Status: `AUTHORITATIVE_SOURCE`
- Owner task: `TASK-0588`
- Acceptance gate: `SD-GATE-007`
- Activation posture: `planning_only_no_capex_activation`

This planning source defines Definition of Ready and Definition of Done checks
for CAPEX task classes. It does not activate CAPEX runtime behavior, public
routes, frontend workpages, workflow packs, corpus import, pilot readiness,
production readiness, or product use.

## Common Definition Of Ready
- Source truth is identified before implementation begins.
- Scope, non-goals, tenant/domain/project boundary, raw corpus boundary, and
  activation boundary are explicit.
- TDD posture is chosen: test first, contract first, or accepted test-gap with
  reviewer-visible reason.
- Code review expectations and required specialist reviewers are named.
- Refactor separation is decided before mixing cleanup with behavior work.
- Rollback or recovery expectation is known for governed runtime, release, or
  migration changes.

## Common Definition Of Done
- Authoritative source changes are updated before generated or derived
  artifacts.
- Tests, contract checks, or accepted test-gap evidence match the affected task
  class.
- Raw corpus material remains outside repo, CI, logs, screenshots, and
  generated packs.
- Activation boundary is restated in task closeout evidence.
- Rollback/recovery notes are present for governed behavior or release changes.
- CAPEX progress data and generated evidence are fresh when touched.

## Task Class Matrix
| Task class | Definition of Ready | Definition of Done |
|---|---|---|
| architecture | Decision surface, invariants, affected docs, and ADR need are identified | Architecture doc or explicit not-needed decision records source truth, tests/contracts, review owner, and non-activation posture |
| runtime | Command boundary, schema/migration impact, idempotency, authorization, and failure modes are named | Runtime tests cover positive and fail-closed paths; migrations/schema parity and rollback/recovery notes are recorded |
| workpage | Projection source, cursor/basis, command activation, and canonical output path are named | Workpage tests prove no hidden truth, stale basis protection, command guardrails, and non-activation unless separately approved |
| fixture | Fixture tier, manifest shape, release approval, leak-scan, and source boundary are named | Sanitized fixtures or aggregate evidence only; no raw corpus material; manifest/version evidence and no-overfitting notes are recorded |
| agent-lab | Evaluation scope, tool authority, prompt/evaluator freeze, and non-authority boundary are named | Lab output remains advisory; ToolProposal/approval boundaries and false-closure or leak checks are recorded |
| migration/release | Migration lane, release bundle, feature-gate, rollback, compensation, and operator evidence are named | Release or migration evidence includes validation, rollback/recovery, activation approval if applicable, and no product activation by implication |

## PR Template Consistency Check
The repository pull request template includes a CAPEX DoR/DoD consistency
checklist for source truth, tests or accepted test-gap, raw-data boundary,
activation boundary, rollback/recovery, and generated/progress freshness.

## Non-Activation Boundary
Closing `TASK-0588` records delivery-quality planning evidence only. It is not
CAPEX runtime activation, product activation, public route approval, workflow
pack activation, corpus import approval, pilot approval, production approval,
or production-ready evidence.
