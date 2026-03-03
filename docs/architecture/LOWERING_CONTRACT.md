# Lowering contract

This file defines how repo-native source lowers into generated CompanyOS-style intermediate representation and a pinned `ExecutionSpec` without creating a second truth system.

## 1) Source surface
The canonical source set for one workflow version is:
- `WORKFLOW_CONTRACT.yaml`
- `ARTIFACT_MAP.yaml`
- `DECISION_CATALOG.yaml`
- `EXECUTION_PROFILE.yaml`
- workflow-scoped policy/profile inputs

These files are the only hand-authored semantics inputs for workflow behavior.

## 2) Lowering pipeline
Let:
- \(b\) = workflow contract pack
- \(g\) = execution overlay (`DECISION_CATALOG` + `EXECUTION_PROFILE`)
- \(p\) = policy/profile inputs

Then the lowering contract is:

\[
L(b,g,p) 	o \mathrm{IR}
\]

where `IR` is a generated, typed intermediate representation suitable for:
- generated runbook packs
- generated tool matrices
- generated approval packets
- generated CompanyOS-compatible specs

The compile step is:

\[
C(\mathrm{IR}) 	o \mathrm{ExecutionSpec}
\]

`ExecutionSpec` is a compiled artifact, not hand-authored source.

## 3) Refinement law
Lowering and compilation may refine source, but never broaden it.

Required properties:
- `OfficialOutputs(ExecutionSpec) ⊆ OfficialOutputs(contract pack)`
- `DecisionRefs(ExecutionSpec) ⊆ DecisionRefs(contract pack ∪ execution overlay)`
- `AllowedToolClasses(ExecutionSpec) ⊆ AllowedToolClasses(execution profile ∩ policy)`
- `RequiredEvents(contract pack) ⊆ EventsGuaranteed(ExecutionSpec)`

This means the compiler is a constraint-preserving specialization step, not a semantics author.

## 4) Generated artifacts
Generated derivatives must carry:
- source file paths
- source version hashes
- generator version
- generated-at timestamp
- target workflow version

If a generated artifact cannot prove lineage, it is not trustworthy enough for governance.

## 5) Human-readable runbook generation
Human-readable runbooks should be rendered from the source surface through the same lowering pipeline.
They may add formatting, examples, prompts, and operator guidance, but they may not invent:
- new stage IDs
- new decision IDs
- new official outputs
- new policy-granting semantics

## 6) Runtime emission requirements
A compiled `ExecutionSpec` must be linkable in the canonical timeline via the shared event envelope.
At minimum the runtime must support links to:
- `workflow_run`
- `task_run`
- `execution_session`
- `execution_spec`
- `tool_execution`
- `approval`
- `artifact_version`
- `projection`

## 7) Deferred but preserved
The lowering target may later become a fuller CompanyOS family (`TaskSpec`, `WorkflowSpec`, `CascadeSpec`, `ProjectionSpec`), but those remain generated downstream artifacts until the repo explicitly changes its authority model.
