---
id: TASK-0149
epic: EPIC-124
title: "Implement frontend stage-linked workpage actions, handoffs, and refresh truth on workspace surfaces"
status: TODO
owners: ["frontend"]
reviewers: ["qa"]
depends_on: ["TASK-0148"]
risk: high
context_packs: ["codex/context/EPIC-124.md"]
patterns: ["PATTERN-007", "PATTERN-009"]
---

## Context
After backend action projection exists, the workspace/task surfaces still need to render those actions truthfully and carry subject context through create/open/submit flows without breaking the current canonical route model.

## Objective
Render the projected workpage actions on the supported workspace surfaces, wire their create/open handoffs, and keep workspace requirement truth synchronized after create/submit events.

## Non-goals
- No new workpage kinds.
- No broad run-workspace redesign.
- No schedule write-path widening or EOD finalization.

## Source files to read first
- generated snapshots from `TASK-0148`
- `frontend/src/components/WorkspaceTaskBoard.tsx`
- `frontend/src/pages/RunWorkspacePage.tsx`
- `frontend/src/lib/repositories/workpagesRepository.ts`
- `frontend/src/lib/types/contracts.ts`
- current workpage pages/components/tests
- `docs/planning/FRONTEND_PAGE_MAP.md`

## Context packs / patterns to consult
- `codex/context/EPIC-124.md`
- `PATTERN-007`
- `PATTERN-009`

## Source files to change
- `frontend/src/components/WorkspaceTaskBoard.tsx`
- `frontend/src/pages/RunWorkspacePage.tsx`
- `frontend/src/lib/repositories/workpagesRepository.ts`
- `frontend/src/lib/types/contracts.ts`
- current workpage pages/components only where subject-context handoff requires it
- targeted frontend tests
- task-memory / status docs as needed

## Generated / downstream artifacts impacted
- workspace CTA rendering and create/open handoff UX
- post-create/post-submit refresh truth for supported surfaces
- frontend tests covering draft-vs-response behavior from the user surface

## Plan
1. Render backend-projected workpage actions on the supported workspace/task/approval surfaces.
2. Reuse the existing canonical run-backed or artifact-backed routes for navigation.
3. Carry subject context through create/open/submit flows where required so later response linkage remains truthful.
4. Refresh or invalidate workspace state after create/submit so requirement status and CTA posture stay synchronized.

## Verification
- `npm --prefix frontend run typecheck`
- targeted frontend tests for workspace CTA rendering, create/open handoff, and refresh behavior
- `python3 scripts/validate_repo.py --schemas-only`

## Acceptance criteria
- Supported workspace surfaces display truthful workpage CTAs.
- CTA flows open the correct canonical run-backed or artifact-backed workpage routes.
- Workspace requirement posture updates correctly after create/submit.
- The frontend does not silently infer route semantics that the backend contract does not provide.
