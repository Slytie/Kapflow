# Mathematical foundations

This is a repo-native distillation of the CompanyOS mathematical note, adapted to the Stage 4 one-truth merger.

## 1) Truth substrate

Let

\[
\Omega = (\mathcal{O}, \mathcal{E}, \mathcal{R})
\]

where:
- \(\mathcal{O}\) = immutable objects
- \(\mathcal{E}\) = append-only timeline events
- \(\mathcal{R}\) = audited mutable registries / pointers

For this repo, \(\mathcal{O}\) includes at least:
- artifact versions
- workflow contract versions
- decision catalog versions
- execution profile versions
- policy/profile versions
- compiled execution specs
- evidence artifacts

## 2) Scope and partition

Let scope be

\[
s = (t, d) \in \mathcal{S}
\]

where \(t\) is a tenant and \(d\) is a hard domain partition.

Let \(p \in \mathcal{P}\) be the business partition:
- payroll uses `PayPeriodID`
- schedule planning uses `ScheduleDateID`

The address of an official artifact slot is:

\[
(k, p, s) \in \mathcal{K} \times \mathcal{P} \times \mathcal{S}
\]

where \(k\) is a dataset key.

## 3) Officialness via audited pointers

Let \(\mathcal{V}\) be immutable artifact versions.

Officialness is defined by a controlled pointer:

\[
\mathrm{active} : (\mathcal{K}, \mathcal{P}, \mathcal{S}) \rightharpoonup \mathcal{V}
\]

This is the repo's core law:
- edits create new versions,
- promotions update pointers,
- approvals bind to exact versions,
- drift is visible,
- "latest" is never a substitute for an explicit pointer update.

For Schedule Planning, the base published schedule and intraday replans intentionally use distinct official artifact streams:
- base plan pointer for `schedule.published_schedule.workbook`
- ordered delta artifacts for `schedule.replan_delta.workbook`

The operative live-day view is therefore a projection over a base version plus promoted deltas, not mutation of the base artifact.

## 4) Runs

A workflow run is pinned to:
- scope
- partition
- workflow version
- exact input versions

\[
r = (r_{id}, s, p, w, I)
\]

with \(I = \{(k,v)\}\) the exact snapshot of input versions.

A run is stale if upstream official pointers move relative to the pinned input set.

## 5) State transitions

The authoritative transition law is:

\[
S_{t+1} = \delta(S_t, e_{t+1})
\]

where \(e_{t+1} \in \mathcal{E}\) is an append-only event.

This means:
- the event stream is the authoritative narrative,
- current state views are projections,
- replay and audit depend on pinned objects plus strong links.

## 6) One authority chain

The repo should obey the refinement chain:

\[
\text{contract pack} \sqsupseteq \text{execution overlay} \sqsupseteq \text{ExecutionSpec} \sqsupseteq \text{projection}
\]

Read as:
- the business contract pack is broader and more authoritative than the execution overlay,
- the execution overlay is broader and more authoritative than a compiled execution spec,
- projections are the least authoritative.

Refinement obligations include:

\[
\mathrm{OfficialOutputs}(x) \subseteq \mathrm{OfficialOutputs}(b)
\]

\[
\mathrm{DecisionRefs}(x) \subseteq \mathrm{DecisionRefs}(b \cup g)
\]

\[
\mathrm{RequiredEvents}(b) \subseteq \mathrm{EventsGuaranteed}(x)
\]

where \(b\) is the business contract pack, \(g\) is the repo-native execution overlay, and \(x\) is a compiled execution spec.

## 7) Stable core and extensible body

Let \(S\) be the space of full stored specs and \(C\) the runtime-interpreted core.

\[
\phi : S \to C
\]

The stable-core rule requires that compatible engine versions preserve \(\phi(s)\) for pinned historical specs.

This gives the project its "creative but safe" posture:
- runtime meaning lives in a stable core,
- innovation lives in extensions,
- pinned runs remain meaningful later.

## 8) Work as typed transformation

The total work history can be viewed as a typed hypergraph:
- nodes are immutable identities such as artifact versions, approvals, runs, tool executions, and compiled specs
- hyperedges are transformations with multiple inputs and outputs
- strong linking means those transformations are reconstructable from timeline events

This gives a useful intuition:
- workflows are structured subgraphs,
- cases and exception loops are adaptive subgraphs,
- projections are coarse-grainings of the same underlying graph.

## 9) Projection coherence

Approval-critical projections must preserve canonical decision fields.

Let \(\kappa\) extract canonical governance fields from the substrate and let \(\mathrm{Proj}\) be a projection.

\[
\kappa(\Omega) = \kappa(\mathrm{Proj}(\Omega))
\]

If this fails, the projection is not safe for approval.

This is the mathematical statement of "no summary drift."

## 10) Bounded dynamism

We only need a small execution algebra for Stage 4:
- linear chain
- approval gate
- bounded exception loop

A bounded exception loop can be written abstractly as:

\[
L(f, \tau, N)
\]

where:
- \(f\) is the response operator or method,
- \(\tau\) is the incident trigger class,
- \(N\) is the bound / no-progress policy.

This is how Schedule Planning remains flexible without losing auditability.

## 11) Reliability from diversity

If an operator has per-attempt error probability \(p\) and \(k\) semi-independent checks, majority vote yields:

\[
\mathbb{P}(\text{maj error})=\sum_{i=\lceil (k+1)/2\rceil}^{k}\binom{k}{i}p^i(1-p)^{k-i}
\]

In practice, correlation matters more than the raw formula. So reliability in this project comes from diversity:
- different roles
- different validators
- different evidence sources
- hard event and pointer checks that make "plausible but false" progress harder to preserve
