# EPIC-050 Context Pack — Human task queue semantics (assignment, claim leases, approvals)

**Purpose (why you might open this):**

- You’re implementing human task lifecycle, claim, reassignment, deadlines/escalations.
- You’re changing group membership, task visibility rules, or the way agent-owned debug work still uses the canonical task queue.

## Non-negotiable invariants to keep in mind
- Claim is a concurrency control mechanism (lease/heartbeat/timeout), not mere UI metadata.
- Agent-owned debug tasks still travel through the same `task_run` / `human_task` / approval path.
- Approvals must bind to a snapshot: artifact version(s) + policy version + approver identity.
- Tenant/domain scoping is strict; no cross-tenant work queues.

## Contracts / schemas to treat as authoritative
- `docs/architecture/human_task_semantics.md`
- `docs/architecture/approval_model.md`
- `docs/planning/FIRST_RUNTIME_SLICE.md`
- `docs/workflows/schedule_planning/v1/WORKFLOW_CONTRACT.yaml`
- `docs/workflows/schedule_planning/v1/OPERATING_MODEL.md`

## Relevant pattern cards (read cards first)
- `docs/patterns/cards/PATTERN-002.md`
- `docs/patterns/cards/PATTERN-007.md`
- `docs/patterns/cards/PATTERN-008.md`

## Required test coverage (tests-as-spec)
- Lease/concurrency tests (two claimers, lease expiry, reopen/escalate).
- Negative authz tests (cross-tenant visibility).
- Acceptance coverage for AT-SCH-003 and AT-SCH-004.
- Approval-gating tests for the Stage06 publish decision and conditional Stage07 major-replan decision.

## Typical failure modes (red-team prompts)
- “What happens if the worker crashes mid-claim?”
- “Can the same task be claimed twice?”
- “Could this leak across tenants/domains?”
- “Does the audit timeline still reconstruct who owned the work and when?”
