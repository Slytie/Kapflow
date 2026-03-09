---
id: TASK-0064
epic: EPIC-080
title: "Three-workflow logistics demo shell and demotion of legacy schedule-only demo entrypoint"
status: DONE
owners: ["frontend", "platform"]
reviewers: ["qa", "ops"]
depends_on: ["TASK-0063"]
risk: high
context_packs: ["codex/context/EPIC-080.md", "codex/context/EPIC-025.md"]
patterns: ["PATTERN-001", "PATTERN-003", "PATTERN-005"]
---

## Objective
Replace the old schedule-only primary demo path with a logistics-story demo shell built over the canonical backend story seam:
- add a primary `/demo/logistics` entrypoint,
- render the family/process graph and unified cross-workflow action board,
- expose linked runs, official outputs, and handoff activity for the three-workflow story,
- demote legacy schedule-only board/workspace UX from primary navigation while keeping regression coverage.

## Delivered
1. Added frontend primary route `/demo/logistics` and switched app root redirect (`/`) to that route.
2. Added `LogisticsDemoPage` using canonical backend story payload (`GET /api/v1/stories/logistics-three-workflow`) through repository/API boundaries.
3. Rendered required story sections from backend-authored data:
   - family/process graph,
   - unified cross-workflow action board lanes/items,
   - linked runs,
   - official outputs summary,
   - handoff edge activity summary.
4. Demoted schedule-only FE surfaces to legacy labels/copy while preserving route availability.
5. Added/updated FE route/component tests for primary route behavior and logistics shell rendering.
6. Updated repo status/planning/context docs to reflect new primary demo posture.

## Scope boundary retained
- No generalized workflow-family UI framework.
- No client-side second source of truth for graph/board/handoff state.
- No deletion of schedule-only regression routes/tests.
