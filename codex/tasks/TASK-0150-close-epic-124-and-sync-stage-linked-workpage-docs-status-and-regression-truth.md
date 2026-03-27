---
id: TASK-0150
epic: EPIC-124
title: "Close EPIC-124 and synchronize stage-linked workpage docs, status, and regression truth"
status: TODO
owners: ["backend", "frontend"]
reviewers: ["qa"]
depends_on: ["TASK-0149"]
risk: medium
context_packs: ["codex/context/EPIC-124.md"]
patterns: ["PATTERN-007", "PATTERN-009"]
---

## Context
Once stage-linked workpage actions are live, repo memory and regression proof must be updated together so fresh sessions do not fall back to the older run-only workpage story.

## Objective
Close EPIC-124 by synchronizing docs/status/task memory and freezing the regression proof for stage-linked workpage actions and relation-kind-aware requirement behavior.

## Non-goals
- No new runtime capabilities beyond the already-implemented stage-linked slice.
- No follow-on finalization or schedule expansion work hidden inside closeout.

## Source files to read first
- `docs/status/CURRENT_FOCUS.md`
- `docs/status/DECISIONS_SINCE_LAST.md`
- `docs/planning/EPICS.md`
- `docs/planning/TASK_INDEX.md`
- `docs/planning/FRONTEND_PAGE_MAP.md`
- `docs/planning/CURRENT_CAPABILITY_AND_CERTIFICATION_MATRIX.md`
- `docs/planning/HITL_HTTP_API_CONTRACTS.md`
- `docs/planning/epics/EPIC-124.md`
- `codex/context/EPIC-124.md`
- updated workspace/workpage tests from `TASK-0147` through `TASK-0149`

## Context packs / patterns to consult
- `codex/context/EPIC-124.md`
- `PATTERN-007`
- `PATTERN-009`

## Source files to change
- `docs/status/CURRENT_FOCUS.md`
- `docs/status/DECISIONS_SINCE_LAST.md`
- `docs/planning/EPICS.md`
- `docs/planning/TASK_INDEX.md`
- `docs/planning/FRONTEND_PAGE_MAP.md`
- `docs/planning/CURRENT_CAPABILITY_AND_CERTIFICATION_MATRIX.md`
- `docs/planning/HITL_HTTP_API_CONTRACTS.md`
- `docs/planning/epics/EPIC-124.md`
- `codex/context/EPIC-124.md`
- relevant task files for `TASK-0147` through `TASK-0150`

## Generated / downstream artifacts impacted
- repo-native memory for the stage-linked workpage layer
- stable regression truth around draft-vs-response semantics and workspace CTA rendering

## Plan
1. Mark EPIC-124 tasks complete in repo memory.
2. Update page-map, capability, contract, and status docs so they describe the implemented stage-linked workpage layer truthfully.
3. Record the closeout decision that workpages are now stage-linked for the supported logistics surfaces, while broader workspace modernization and finalization work remain deferred.
4. Freeze regression proof references so future Codex runs do not drift.

## Verification
- `python3 scripts/validate_repo.py --schemas-only`
- targeted backend/frontend regression checks added in this epic
- snapshot export/checks if touched by the closeout

## Acceptance criteria
- EPIC-124 is recorded as complete in repo memory.
- Docs truthfully describe the supported stage-linked workpage surfaces.
- Regression proof for draft-vs-response semantics and CTA projection is captured in repo-native tests/docs.
- The next epic remains an explicit future choice rather than being smuggled into closeout.
