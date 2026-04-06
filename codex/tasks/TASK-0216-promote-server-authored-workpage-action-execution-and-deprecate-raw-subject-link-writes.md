---
id: TASK-0216
epic: EPIC-133
title: "Promote server-authored workpage action execution and deprecate raw subject-link writes"
status: TODO
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
