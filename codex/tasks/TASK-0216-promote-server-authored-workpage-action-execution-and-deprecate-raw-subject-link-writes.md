---
id: TASK-0216
epic: EPIC-133
title: "Promote server-authored workpage action execution and deprecate raw subject-link writes"
status: DONE
owners: ["backend", "frontend"]
reviewers: ["architect"]
depends_on: ["TASK-0215"]
risk: high
context_packs:
  - "codex/context/EPIC-133.md"
  - "codex/context/WORKPAGE_FORMAL_MODEL_AND_SETTLEMENT_RATIONALE.md"
patterns: []
---

## Context
The current public write path is safer than before, but workflow intent is still partly client-carried through `subject_link` payloads and router state.

From first principles, the server should resolve the meaning of an action:

\[
M_k : (S, u, a, x) \mapsto (S', \Delta E)
\]

where `a` is a server-recognized action, not a client-invented semantic payload.

## Objective
Move primary workpage create/submit flows toward server-authored action execution so workflow intent and authorization are resolved on the backend.

## Non-goals
- No product-boundary change.
- No new workpage kinds.
- No giant generic action framework.

## Source files to read first
- `frontend/src/lib/repositories/workpagesRepository.ts`
- frontend page/workspace workpage action usage
- `src/onetruth/application/handlers/workpages.py`
- any current action-projection helpers for workspace/task/approval surfaces

## Source files to change
- backend workpage action/command seams
- frontend repositories/pages using raw `subject_link`
- tests covering subject-linked flows

## Plan
1. Define the smallest server-authored action execution seam that can carry current workpage intent.
2. Teach the backend to resolve and re-validate current action semantics from authoritative state and principal context.
3. Migrate primary frontend workpage create/submit paths away from direct raw `subject_link` construction.
4. Keep a narrow compatibility shim only if necessary, and mark it deprecated.

## Verification
- backend tests for subject-linked create/submit flows
- frontend tests showing primary pages/workspace consume server-authored action semantics

## Acceptance criteria
- Primary workpage write flows no longer rely on raw client-carried workflow meaning.
- Server-authored action semantics, not router state, own the meaning of create/submit operations.

## Execution notes
- Added a central backend `action_ref` resolution seam in `src/onetruth/application/handlers/workpages.py`, including authoritative run/workpage/artifact/subject validation, `invalid_workpage_action_ref` failures for mismatches, and `invalid_payload` rejection when callers send both `action_ref` and `subject_link`.
- Workspace `workpage_actions[]`, canonical page `actions[]`, and the run-backed EOD `draft_resolution` surface now project server-authored `action_ref` values; artifact-backed EOD pages also now expose a submit page action so direct canonical page access can submit without workspace router state.
- Canonical frontend workspace/page flows now carry `workpageActionRef` router state, submit/create through repository helpers that send `action_ref`, and stop constructing raw `subject_link` in the primary canonical paths.
- The legacy `subject_link`, `subject_context`, and `link_policy` seams remain in place only as compatibility metadata/fallbacks for this tranche; inline demo-shell mutation convergence remains deferred to `TASK-0217`.
- Backend-owned frontend contract fixtures under `fixtures/frontend_contracts/` were refreshed for the touched workspace and workpage surfaces so snapshot truth now includes the additive `action_ref`, `open_action_ref`, and `create_action_ref` fields.
