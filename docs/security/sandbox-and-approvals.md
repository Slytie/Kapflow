# Sandbox and approvals

## 1) LLM stance
LLMs are untrusted planners.
The platform is the validator, authorizer, executor, recorder, and promoter.

## 2) Tool execution controls
Side-effecting tool use should require:
- scope validation
- policy decision
- budget checks
- membership in the pinned execution plan or explicit override
- approval when required by decision catalog, execution profile, or policy

## 3) Concrete sandbox policy surface
The repo now carries a concrete sandbox policy schema:
- `schemas/agentic/sandbox_policy.schema.json`

Stage 4 expects the runtime to make policy decisions over at least:
- CPU time
- wall time
- memory
- process count
- open files
- output size
- network egress
- writable mounts

This prevents "sandbox policy" from remaining purely philosophical.

## 4) Approval-critical projections
Approval-critical views should:
- be server-owned
- preserve canonical fields
- include drift and evidence warnings
- fail closed when coherence checks fail

## 5) Transcript rule
Transcripts are evidence, not a state machine.
Tool requests, approvals, pointer updates, and explicit state-change events are the authoritative state transitions.

## 6) Second-truth risk
Security review should treat these as security problems, not just design smells:
- hand-maintained generated runbooks drifting from source
- projection packets used for approval without evidence links
- agent-only state that affects business outcomes
- derived stores without strict scope partitioning

## 7) Method-change governance
Method-change approvals remain a reserved approval kind for future work.
Do not let capability expansion self-promote.
