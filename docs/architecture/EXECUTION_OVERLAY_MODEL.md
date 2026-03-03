# Execution overlay model

This doc explains how the repo absorbs the useful parts of the CompanyOS method layer without creating a second authored workflow-definition system.

## 1) Why an execution overlay exists
The business contract pack answers:
- what stages exist?
- what artifacts matter?
- what approvals and official outputs exist?

But it does not fully answer:
- which decision points are canonical?
- which tool classes are allowed per stage?
- which execution pattern applies to each stage?
- which approval packets and projections must exist?
- how do we represent bounded exception handling in a workflow like Schedule Planning?

The execution overlay exists to answer those questions in repo-native source.

## 2) Canonical overlay files
Per workflow, Stage 4 uses two canonical overlay files:

### `DECISION_CATALOG.yaml`
Defines:
- decision IDs
- stage bindings
- approval kinds
- who decides
- allowed responses
- evidence requirements
- SLA / escalation defaults

### `EXECUTION_PROFILE.yaml`
Defines:
- stage execution pattern
- allowed tool classes
- side-effect posture
- stop / no-progress rules
- projection requirements
- decision references used by the stage
- bounded exception-loop semantics where needed

## 3) Stable core vs extensible body
The overlay borrows the stable-core rule from CompanyOS.

### Stable core
Fields that runtime and validation may interpret:
- stage_id
- decision_id
- decision_kind
- requested_from_role
- allowed_tool_classes
- execution_pattern
- stop_rules
- side_effect_policy
- required evidence keys
- projection IDs
- decision refs

### Extensible body
Fields that guide humans or future generators but should not silently change execution meaning:
- prompts
- examples
- heuristics
- reviewer guidance
- numeric threshold defaults unless explicitly promoted to policy
- operator-flavor commentary

## 4) Why Stage 4 does not hand-author `WorkflowSpec`
`WorkflowSpec` overlaps too much with the repo workflow contract to be safely hand-authored in parallel.

For Stage 4:
- workflow meaning stays in the workflow pack
- CompanyOS IR is generated from repo-native source
- `ExecutionSpec` is compiled from repo-native source plus policy

That keeps one authored business-definition system.

## 5) Minimal execution algebra
Stage 4 only needs three execution patterns:
- `linear_chain`
- `approval_gate`
- `bounded_exception_loop`

This is enough for:
- Payroll: mostly linear + gated
- Schedule Planning: linear publish path + bounded intraday exception handling

## 6) Relation to CompanyOS
The overlay is deliberately smaller than the full CompanyOS spec family.

It preserves the useful ideas:
- stable core
- extensible body
- bounded method
- generated IR
- pinned execution

But it avoids introducing a second source of workflow truth.

## 7) Generated downstream artifacts
From the workflow pack and execution overlay we should be able to generate:
- external runbook pack
- tool registry spreadsheet
- approval / decision log spreadsheet
- generated CompanyOS IR
- approval packet layouts

## 8) Deferred concepts
The following stay deferred until the runtime and governance layer are mature enough:
- authored `WorkflowSpec`
- authored `ProcessPatch`
- spec store as a first-class runtime surface
- general multi-level studies/programs
- general projection DSLs
- persistent WorkGraph as a product truth surface
