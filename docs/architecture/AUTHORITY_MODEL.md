# Authority model

This repo uses one truth system.

## 1) Authoritative substrate

The authoritative substrate is:

\[
\Omega = (\mathcal{O}, \mathcal{E}, \mathcal{R})
\]

where:
- \(\mathcal{O}\) = immutable objects
- \(\mathcal{E}\) = append-only timeline events
- \(\mathcal{R}\) = audited mutable registries and pointers

For Stage 4, authoritative object kinds include:
- workflow contract versions
- artifact map versions
- decision catalog versions
- execution profile versions
- policy/profile versions
- artifact versions
- approvals
- workflow runs
- task runs
- compiled execution specs
- evidence artifacts explicitly linked from authoritative events

## 2) What is authoritative vs non-authoritative

### Authoritative
- workflow contracts
- artifact maps
- acceptance criteria
- operating models
- decision catalogs
- execution profiles
- event envelope and event-type registry
- artifact metadata schema
- immutable events and versions written at runtime
- audited pointers / promotions

### Compiled but authoritative once pinned
- per-run `ExecutionSpec`
- source-hash manifests that prove what was compiled from what

### Generated and non-authoritative
- external runbook packs
- tool registry spreadsheets
- approval / decision log spreadsheets
- generated CompanyOS spec IR
- UI packets / render outputs

### Derived and non-authoritative
- dashboards
- search indices
- WorkGraph
- summarized approval views
- "current operative schedule" views reconstructed from base + deltas
- raw object-store/blob presence without canonical metadata rows/events/pointers

### Evidence, not state
- transcripts
- sandbox logs
- model reasoning summaries
- scratch reports unless explicitly versioned and linked as artifacts

## 3) Single authority chain

The repo obeys the following precedence:

1. **Truth substrate**
2. **Business contract pack**
   - `WORKFLOW_CONTRACT.yaml`
   - `ARTIFACT_MAP.yaml`
   - `ACCEPTANCE_CRITERIA.md`
   - `OPERATING_MODEL.md`
3. **Execution overlay**
   - `DECISION_CATALOG.yaml`
   - `EXECUTION_PROFILE.yaml`
4. **Compiled execution artifacts**
   - `ExecutionSpec`
   - generated CompanyOS IR
5. **Generated and derived views**

Lower layers constrain upper layers. Upper layers may refine, never contradict.

## 4) Refinement laws

The execution overlay may not invent business semantics outside the contract pack.

Examples:
- no new stage IDs
- no new dataset keys
- no new official outputs
- no removal of required business approvals
- no bypass of required event emission

A compiled `ExecutionSpec` may not broaden capabilities relative to:
- workflow contract
- decision catalog
- execution profile
- pinned policy

Projections may not define official business state.

## 5) One run system, one approval system, one event system

### One run system
There are not separate peer universes for "business runs" and "agent runs".

The canonical runtime model is:
- `workflow_run`
- `task_run`
- optional `execution_session` as an execution facet linked to a task run

### One approval system
There are not separate peer systems for approvals and human decision requests.

The canonical object is one approval model with kinds:
- `business_decision`
- `execution_gate`
- `method_change`

### One event system
There is one timeline envelope and one link model. Business execution, agentic execution, tool activity, and projection rendering all emit events into the same substrate.

## 6) What this means for workflow authoring

Per workflow family, the canonical authored surface is:

- `WORKFLOW_CONTRACT.yaml`
- `ARTIFACT_MAP.yaml`
- `ACCEPTANCE_CRITERIA.md`
- `OPERATING_MODEL.md`
- `DECISION_CATALOG.yaml`
- `EXECUTION_PROFILE.yaml`

This is the entire hand-authored semantics surface for Stage 4.

Anything downstream of these files must be generated, compiled, or derived.

## 7) Anti-patterns to avoid

Do not:
- hand-author CompanyOS `WorkflowSpec` as if it were the source of business workflow truth
- treat runbook prose as authoritative semantics
- let dashboard state or projection packets become the place where "what is official" is decided
- model transcripts as the driver of state transition
- store live-day schedule updates by mutating the published base schedule
- treat object/blob storage as authoritative state over metadata + timeline + pointers

## 8) Practical rule
If two files disagree, prefer the one higher in the authority chain and fix the lower one.
