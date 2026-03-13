# Approval model

This repo has one canonical approval object model.

Shared vocabulary is defined in:
- `docs/architecture/governance_vocabulary.md`
- `schemas/policy/governance_vocabulary.yaml`

## 1) Approval kinds
Approvals differ by purpose, not by object type.

Allowed kinds:
- `business_decision`
- `execution_gate`
- `method_change`

### Business decision
Approves a business outcome or official state change.
Examples:
- publish schedule
- finalize payroll
- approve major replan

### Execution gate
Approves a runtime action that should not self-execute even if technically possible.
Examples:
- high-impact tool action
- out-of-plan override
- external side effect in a future integration

### Method change
Approves a change to method or capability surface.
Examples:
- future ProcessPatch
- capability expansion
- generator rule changes that broaden execution power

Stage 4 keeps this kind reserved but mostly deferred.

## 2) Core fields
Each approval should at minimum capture:
- `approval_id`
- `approval_kind`
- `workflow_id`
- `workflow_run_id`
- `stage_id` or execution context
- scope `(tenant_id, domain_id)`
- requested action
- requested from role or user
- requester actor
- allowed responses (verbs)
- evidence refs
- projection packet ID if used
- state
- request time
- decision time
- decision actor
- canonical outcome
- rationale / notes
- expiry / SLA metadata
- optional approval token or receipt

## 3) Vocabulary mapping
### Response verbs offered to a reviewer
- `approve`
- `reject`
- `request_changes`
- `cancel`
- `expire`

### Recorded outcomes written onto the timeline
- `approved`
- `rejected`
- `changes_requested`
- `canceled`
- `expired`

Do not mix the two layers.

## 4) Lifecycle
Typical lifecycle:
1. requested
2. pending / claimed if a task is used
3. responded (`approved`, `rejected`, `changes_requested`, `canceled`, or `expired`)
4. if approved, a separate state-changing event or pointer update records the actual effect
5. if the response requires more work, explicit follow-on task runs are created for rework, information requests, or final review

Approvals do not themselves mutate official business state. They authorize another recorded action to do so.
They also do not create hidden queue side effects: if an approval response requires more work, that work must appear through `task.run.created` / `task.created` events in the same truth system.

### Timeline events
Approvals must emit through the canonical timeline:
- `approval.requested`
- `approval.responded`

`approval.responded.payload` must include:
- `approval_id`
- `action`
- `response` (verb)
- `outcome` (past-tense canonical result)
- optional `rationale`

### Capability-lattice freeze
- The authoritative capability lattice is defined in `docs/architecture/human_task_semantics.md`.
- `required_role` is the authoritative responder role when present.
- Approval `candidate_roles` remain routing and fallback responder eligibility only when `required_role` is absent; they do not create a second approval capability layer.
- Override semantics must be represented as explicit approvals, usually `execution_gate` or `business_decision`, not inferred from routing hints or queue presentation.
- Approval response now enforces the same frozen role lattice at the canonical write boundary, with explicit forbidden vs conflict semantics (`approval_respond_forbidden` vs `approval_not_respondable`).

## 5) Approval packets
Approval packets are projections, not truth.
They must:
- show canonical fields
- include drift warnings
- include evidence links
- fail closed when required evidence is missing or coherence fails

## 6) Separation from tasks
A task may prepare or route an approval, but a task is not an approval.
A single approval may be served by:
- a human task
- a queue inbox
- a structured UI packet
- future policy-assisted review

## 7) Agent principals in debug tenants
The fully-agentive Schedule Planning objective allows designated agent principals to act in the same approval path as humans.

That means:
- actor type may be `agent`
- the same approval object is still used
- the same permission action `approval.respond` is still required
- the same evidence snapshot rule still applies

## 8) Permission model
Approval permissions are expressed through exactly two actions:
- `approval.request`
- `approval.respond`

Do not use `approval.grant`.

## 9) Anti-pattern to avoid
Do not create a separate "human decision request" truth system beside the approval model. If a decision matters, it should be represented as an approval of one of the kinds above.
