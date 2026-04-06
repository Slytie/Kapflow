---
id: TASK-0215
epic: EPIC-133
title: "Move lineage, latest-draft, and accepted queries behind backend-owned workpage seams"
status: TODO
owners: ["backend", "frontend"]
reviewers: ["architect"]
depends_on: ["TASK-0214"]
risk: medium
context_packs:
  - "codex/context/EPIC-133.md"
  - "codex/context/WORKPAGE_FORMAL_MODEL_AND_SETTLEMENT_RATIONALE.md"
  - "codex/context/WORKPAGE_STABILITY_FINDINGS_2026-04-05.md"
patterns: []
---

## Context
Core history rails are still partly client-reconstructed by fetching all workflow-run artifacts and filtering by artifact kind. That works for a small slice, but it makes the client a partial semantic owner of lineage and latest-version logic.

## Objective
Move core workpage history/latest/accepted queries behind backend-owned seams so the frontend consumes server-authored lineage rather than reconstructing it.

## Non-goals
- No new public workpage kinds.
- No new artifact truth model.

## Source files to read first
- `frontend/src/lib/repositories/workpagesRepository.ts`
- workpage contract builders in `src/onetruth/application/services/logistics_workpages.py`
- descriptor definitions in `src/onetruth/application/services/workpage_descriptors.py`
- relevant page tests for schedule/EOD/route-demand/preferences history rails

## Source files to change
- backend workpage query/contracts
- frontend repository/pages that currently build history from `listWorkflowRunArtifacts`
- relevant tests

## Plan
1. Add backend-owned query/contract data for the core history rails the pages need.
2. Use the descriptor/workpage kind seam to keep the history logic bounded per surface.
3. Remove client-side history reconstruction from the primary workpage pages/repository methods.
4. Add regression tests showing the frontend consumes server-authored lineage/latest truth.

## Verification
- backend contract tests
- frontend page tests for history/rail behavior

## Acceptance criteria
- No primary workpage page depends on listing all workflow-run artifacts and filtering client-side to build its history rail.
- Latest-draft and accepted-series truth are owned by backend workpage queries/contracts.
