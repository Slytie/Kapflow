---
id: TASK-0124
epic: EPIC-120
title: "Run workpage preflight alignment and add the workpage view-model contract + example data seam"
status: DONE
owners: ["platform"]
reviewers: ["qa"]
depends_on: ["TASK-0123"]
risk: medium
context_packs: ["codex/context/EPIC-120.md"]
patterns: ["PATTERN-007", "PATTERN-009"]
---

## Context
The repo needs a stable FE contract for workpages before any page-specific implementation begins. The safest first seam is example data -> `WorkpageViewModel` -> page UI.

## Objective
1. Run the EPIC-120 preflight alignment checks.
2. Add the shared frontend types, example-backed data seam, and small builders needed for schedule and EOD workpages.

## Non-goals
- No backend workpage API.
- No artifact round-trip logic.
- No generic page builder.

## Source files changed
- `frontend/src/lib/types/workpages.ts`
- `frontend/src/lib/repositories/workpagesRepository.ts`
- `frontend/src/lib/repositories/index.ts`
- `frontend/src/lib/workpages/*`
- frontend mapper/repository tests

## Verification
- `npm --prefix frontend run typecheck`
- `npm --prefix frontend run test:run -- workpage`
- `python3 scripts/validate_repo.py --schemas-only`

## Acceptance criteria
- Both first workpages depend on one shared view-model contract.
- The example-backed seam is explicit and replaceable by a future backend adapter.
- The task does not blur workpage fixtures with backend-owned frontend contract snapshots.
- Tests freeze the mapping from repo-native examples into the shared page contract.

## Notes / decisions
Keep the contract small. If a field is page-specific, keep it in page-specific section payloads instead of bloating the top-level view model.
