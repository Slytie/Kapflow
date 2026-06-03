> Document classification: historical logistics context. See `docs/domains/logistics/DOC_INVENTORY.yaml` for current authority.

# Workpages post-EPIC-131 stabilization and settlement plan

## Purpose
The workpage architecture moved in the right direction during EPIC-131, but the repo is not yet fully settled. This plan splits the follow-on work into two epics with different fixed points:

- **EPIC-132** restores a clean, green, reproducible workpage boundary.
- **EPIC-133** reduces the remaining accidental complexity so future workpages do not make the system fragile again.

These epics supersede EPIC-126 as the active post-EPIC-131 settlement plan.

Status on 2026-04-06:
- `EPIC-132` is complete.
- `EPIC-133` is now the selected follow-on tranche.

## Executive summary
From first principles, the public workpage system is a family of server-authored resources:

\[
S = (R, T, A, P, E)
\]

where:
- \(R\) = workflow/task runtime objects,
- \(T\) = human-task and approval truth,
- \(A\) = immutable artifact versions,
- \(P\) = mutable official pointers/registries,
- \(E\) = append-only event/audit state.

A workpage of kind \(k\) for principal \(u\) is a projection:

\[
W_k = \Pi_k(S, u)
\]

A public write is a constrained state transition:

\[
M_k : (S, u, a, x) \mapsto (S', \Delta E)
\]

where \(a\) is a server-recognized action and \(x\) is bounded payload.

For the system to be reliable, each public workpage write path must satisfy five invariants:

1. **Canonical addressing**: one authoritative route family per public surface.
2. **Idempotent replay**: the same logical command cannot create duplicate truth.
3. **Provenance closure**: every new artifact version carries enough lineage to reconstruct why it exists.
4. **Deterministic validation**: preview/save/publish derive from the same authoritative rules.
5. **Server-owned intent**: the client renders affordances but does not invent workflow meaning.

EPIC-131 materially improved invariants 1, 3, and 4. The remaining settlement work now splits cleanly:
- EPIC-132 validates and restores the current public boundary from supported environments.
- EPIC-133 removes the still-real client-owned and large-file fragility that remains after the boundary is settled.

## Current findings that motivate the split
### What got stronger
- Canonical run/kind-scoped workpage routing is the public posture.
- `schedule-v0`, `route-demand-v0`, and `driver-preferences-v0` are explicit and not collapsed into one ambiguous surface.
- Schedule drafts carry calculation, dependency, and accepted-vs-draft semantics more honestly.
- Backend runtime coverage exists around run-backed routes, artifact-backed routes, drift, and publish behavior.

### What still needs settlement or hardening
- The 2026-04-05 packet findings captured real instability, but some of those items have already been resolved in the live repo and must now be treated as dated evidence rather than current truth.
- Supported-environment verification still needs to be the authoritative basis for classifying remaining workpage reliability gaps.
- Client-side lineage/history reconstruction, raw `subject_link` mutation intent, the inline demo mutation path, and several concentration files remain live architectural debt.

## Why two epics instead of one
If the repo tries to do “reconcile historical findings”, “restore green write paths”, “finish active docs/fixtures synchronization”, and “simplify client/server intent” in one tranche, the state space grows too quickly.

So the split is deliberate:

### EPIC-132 - Reliability settlement and repo-truth closeout
Goal:

\[
\text{restore closure of } M_k \text{ for the current public workpage family}
\]

This epic ends only when the repo has a clean settlement baseline:
- clean checkout,
- green targeted mutation checks in the supported environment,
- docs/fixtures/tests aligned with canonical-only posture,
- reproducible backend/frontend verification instructions.

### EPIC-133 - Fragility reduction and extensibility hardening
Goal:

\[
\Delta C_{\text{future workpage}} \approx O(1)
\]

This epic reduces accidental complexity by moving lineage, action semantics, and demo-shell behavior behind stronger backend-owned seams.

## Recommended implementation order
1. **Run EPIC-132 first.**
   - Start by freezing the current clean baseline and classifying which packet findings are already resolved, still open, or explicitly deferred.
2. **Run EPIC-133 second.**
   - Only start after EPIC-132 proves the current surface is settled.

## Non-goals for both epics
- No new workpage kinds beyond the EPIC-131 boundary.
- No date-specific driver-exception product work.
- No automatic agentic re-scheduling.
- No generic spreadsheet/runtime platform.
- No reopening of the canonical route decision.

## Deliverables in this plan
- `docs/planning/epics/EPIC-132.md`
- `docs/planning/epics/EPIC-133.md`
- `codex/context/EPIC-132.md`
- `codex/context/EPIC-133.md`
- `codex/context/WORKPAGE_FORMAL_MODEL_AND_SETTLEMENT_RATIONALE.md`
- `codex/context/WORKPAGE_STABILITY_FINDINGS_2026-04-05.md`
- `codex/tasks/TASK-0211` .. `TASK-0218`

## Practical stop line
Treat this document as the active settlement plan for the follow-on workpage tranche:
- EPIC-131 remains the completed feature epic.
- EPIC-126 remains completed cleanup history.
- EPIC-132 and EPIC-133 are now the active post-EPIC-131 settlement and hardening plan.
