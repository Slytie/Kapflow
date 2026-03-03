# EPIC-060 Context Pack — Approvals, policy enforcement, and projection coherence

**Purpose (why you might open this):**

- You’re changing approval semantics, policy enforcement points, or approval-critical packets/projections.
- You’re deciding what happens when an approval packet drifts from authoritative evidence.

## Non-negotiable invariants to keep in mind
- There is one approval system for business decisions, execution gates, and future method-change review.
- Approvals bind to exact evidence refs, actor identity, allowed responses, and recorded outcomes.
- Projections are useful but non-authoritative; coherence failures must be visible and may block approval-critical use.
- Debug-tenant agent principals may act through the same approval path; they may not bypass it.

## Contracts / schemas to treat as authoritative
- `docs/architecture/approval_model.md`
- `docs/architecture/governance_vocabulary.md`
- `docs/planning/RUNTIME_BOOTSTRAP.md`
- `docs/workflows/schedule_planning/v1/DECISION_CATALOG.yaml`
- `docs/workflows/schedule_planning/v1/ACCEPTANCE_CRITERIA.md`
- `schemas/runtime/approval.schema.json`
- `schemas/runtime/projection.schema.json`
- `schemas/runtime/policy_decision.schema.json`

## Relevant pattern cards (read cards first)
- `docs/patterns/cards/PATTERN-002.md`
- `docs/patterns/cards/PATTERN-005.md`
- `docs/patterns/cards/PATTERN-008.md`

## Required test coverage (tests-as-spec)
- Approval binding tests for approve / reject / request-changes paths.
- Negative tests proving a response cannot attach to the wrong artifact snapshot.
- Coherence tests showing approval-critical packets fail visible when canonical fields drift.
- Acceptance coverage proving debug-tenant agent principals still use the same approval path.

## Typical failure modes (red-team prompts)
- “Could someone approve the wrong version?”
- “Can a projection drift from evidence without being detected?”
- “Does an agent-only path accidentally bypass the approval object model?”
- “Are response verbs, recorded outcomes, and permission actions being mixed together?”
