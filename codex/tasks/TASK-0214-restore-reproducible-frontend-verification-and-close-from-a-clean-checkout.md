---
id: TASK-0214
epic: EPIC-132
title: "Restore reproducible frontend verification and close from a clean checkout"
status: TODO
owners: ["frontend", "qa"]
reviewers: ["architect"]
depends_on: ["TASK-0212", "TASK-0213"]
risk: medium
context_packs:
  - "codex/context/EPIC-132.md"
  - "codex/context/WORKPAGE_STABILITY_FINDINGS_2026-04-05.md"
patterns: []
---

## Context
The repo already contains a meaningful frontend test surface for workpage pages/routes/workspace behavior, but the settlement epic should end with reproducible verification truth, not with machine-local assumptions.

## Objective
Restore a documented, reproducible frontend verification path for the workpage tranche and close EPIC-132 only from a clean checkout.

## Non-goals
- No frontend architecture refactor yet.
- No redesign of the product surface.

## Source files to read first
- `frontend/package.json`
- frontend lockfile and test scripts
- relevant workpage page tests
- active docs that describe setup/verification for the frontend

## Source files to change
- frontend docs/setup/runbook truth
- test scripts/commands/CI targets if needed
- any minimal cleanup needed so targeted workpage FE tests run from clean install

## Plan
1. Re-establish the repo’s clean-install/frontend-test truth: Node 20, `npm ci`, no reliance on archived local state.
2. Document the exact targeted FE test commands for the workpage tranche.
3. Add or update a CI/Make target so the targeted workpage FE suite is easy to run and review.
4. Close EPIC-132 only when the branch is clean and the documented targeted suites pass from a clean environment.

## Verification
- targeted frontend workpage tests from clean install
- targeted backend mutation suite from clean checkout
- clean `git status`

## Acceptance criteria
- Frontend workpage verification is reproducible from documented setup, not dependent on packaged local state.
- The settlement branch is clean when the epic closes.
- EPIC-132 leaves the repo in a trustworthy resting state.
