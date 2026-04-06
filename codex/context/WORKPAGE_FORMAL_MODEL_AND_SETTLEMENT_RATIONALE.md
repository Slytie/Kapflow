# Workpage formal model and settlement rationale

Use this note when deciding whether a cleanup belongs in EPIC-132 or EPIC-133.

## Canonical state
Treat the authoritative system state as:

\[
S = (R, T, A, P, E)
\]

- \(R\): workflow runs, task runs, execution/runtime objects
- \(T\): human tasks and approvals
- \(A\): immutable artifact versions and their lineage
- \(P\): explicit official pointers / promoted registries
- \(E\): append-only events and audit receipts

A workpage is not truth. It is a projection:

\[
W_k = \Pi_k(S, u)
\]

for workpage kind \(k\) and current principal \(u\).

## Public write model
A public workpage write is a constrained transition:

\[
M_k : (S, u, a, x) \mapsto (S', \Delta E)
\]

where:
- \(a\) is a server-recognized action,
- \(x\) is bounded payload,
- \(S'\) contains new immutable artifact versions and/or runtime mutations,
- \(\Delta E\) is the new audit/event evidence.

The client is allowed to:
- request a projection,
- render server-authored affordances,
- submit bounded edits.

The client is not the authority for:
- canonical route identity,
- lineage truth,
- accepted-vs-draft truth,
- workflow intent,
- authorization or actionability.

## Reliability invariants
A public workpage system is reliable if these are true:

1. **Canonical addressing**
   \[
   (\text{workflow run}, \text{workpage kind}, \text{artifact version}) \rightarrow \text{one canonical public surface}
   \]

2. **Idempotent replay**
   Replaying the same logical command does not create duplicate intended truth.

3. **Lineage/provenance closure**
   Every created artifact version can be explained from parent/supersedes/dependency evidence.

4. **Deterministic validation**
   Preview/save/publish use the same rule family and do not silently diverge.

5. **Server-owned intent**
   The backend resolves the meaning and authorization of actions; the client does not improvise workflow semantics.

## What EPIC-131 improved
EPIC-131 improved invariants 1, 3, and 4 by:
- making canonical run/kind-scoped routes the public posture,
- formalizing schedule calculation and dependency drift,
- separating accepted series from draft lineage,
- making route-demand and preferences explicit truth objects.

## Why EPIC-132 exists
EPIC-132 exists because a system can be architecturally right but still fail the operational theorem of a clean public write boundary.

If a shared helper regression or an out-of-sync test/fixture/doc layer makes \(M_k\) unreliable in practice, then the architecture is not yet settled. EPIC-132 restores that closure.

## Why EPIC-133 exists
EPIC-133 exists because a system can be functionally green but still carry too much accidental complexity.

If lineage is client-reconstructed, workflow intent lives in router state, and demo shells own a second mutation path, then:

\[
\Delta C_{\text{future workpage}} > O(1)
\]

EPIC-133 reduces that slope by moving more semantics behind backend-owned descriptors, queries, and actions.

## Heuristic for deciding where a cleanup belongs
Put a cleanup in **EPIC-132** if it answers:
- “Can the existing public workpage write/read contract be trusted right now?”
- “Can the repo be validated from a clean checkout?”
- “Are tests/fixtures/docs lying about the current surface?”

Put a cleanup in **EPIC-133** if it answers:
- “Why does adding another workpage or workflow feel too expensive?”
- “Why is the client still inferring semantics the server should own?”
- “Why are large files or demo paths acting as second orchestration engines?”
