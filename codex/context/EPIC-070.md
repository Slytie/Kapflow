# EPIC-070 Context Pack — Automation + sandbox baseline (policy-gated tools, containment, audit)

**Purpose (why you might open this):**

- You’re enabling any tool/script execution or LLM-assisted automation.
- You’re changing allowlists/permissions or execution environment constraints.

## Non-negotiable invariants to keep in mind
- Default-deny tool execution; allowlist by capability and require approvals where needed.
- Sandbox is a security boundary: resource limits, egress control, and provenance are mandatory.
- Never pass untrusted text as instructions to tools; treat tool output as data.
- Audit must include: who approved, what ran, with what inputs, and what it produced.
- Tool activity must remain linked to the same canonical execution-session / policy-decision / timeline substrate.

## Contracts / schemas to treat as authoritative
- `docs/security/sandbox-and-approvals.md`
- `docs/workflows/schedule_planning/v1/EXECUTION_PROFILE.yaml`
- `docs/planning/TEST_MATRIX.md`
- `schemas/events/envelope.schema.json`
- `schemas/policy/permissions.yaml`
- `fixtures/workflows/schedule_planning/golden_event_traces/schedule_policy_gate_enforced.jsonl`

## Relevant pattern cards (read cards first)
- `docs/patterns/cards/PATTERN-005.md`
- `docs/patterns/cards/PATTERN-006.md`

## Required test coverage (tests-as-spec)
- Security regression suites (prompt/tool injection corpus).
- Policy-gate trace coverage for AT-SCH-007.
- Redaction tests (no secrets/PII in logs).
- Containment tests (no unexpected network/filesystem access).

## Typical failure modes (red-team prompts)
- “What happens if the worker crashes mid-step?”
- “Can the same request run twice?”
- “Could this leak across tenants/domains?”
- “Does the audit timeline still reconstruct what happened?”
