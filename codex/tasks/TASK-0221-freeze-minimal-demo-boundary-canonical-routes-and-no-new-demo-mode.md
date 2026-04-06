---
id: TASK-0221
epic: EPIC-134
title: "Freeze the minimal workpage demo boundary, canonical-route posture, and no-new-demo-mode rule"
status: DONE
owners: ["architect"]
reviewers: ["pm", "qa"]
depends_on: []
risk: low
context_packs:
  - "codex/context/EPIC-134.md"
  - "codex/context/WORKPAGE_DEMO_GAP_FINDINGS_2026-04-06.md"
patterns: []
---

## Why
We want a demo quickly, but we do not want a new product-development stream disguised as demo work. The repo needs one explicit statement of the minimal demo boundary so later implementation stays small and truth-preserving.

## Scope
- add EPIC-134 to repo-native planning/context memory
- record that demo validation targets the canonical `/runs/:workflowRunId/workpages/*` routes
- record that the default demo-prep path should be deterministic, idempotent, and should not require OpenAI
- record that multi-week accepted-history seeding is intentionally out of scope for this first demo
- record that the demo shell may remain as narrative context, but the validation target is canonical workpage routes

## Out of scope
- code changes to runtime or frontend behavior
- story-shell redesign
- new API surfaces
- OpenAI/agent runtime work

## Frozen assumptions
1. EPIC-131 and the later settlement/hardening work are treated as already landed.
2. The demo validates workpage behavior, not the OpenAI runtime.
3. The first demo only needs one current weekly run with a schedule draft, route-demand truth, optional driver-preferences snapshot, and reporting context.
4. Route-demand drift can be demonstrated live during the demo instead of being pre-seeded.
5. Accepted-history arrows do not require auto-seeding adjacent accepted weeks for this tranche.

## Source files changed
- `docs/planning/epics/EPIC-134.md`
- `docs/planning/LOGISTICS_WORKPAGE_DEMO_ENABLEMENT_PLAN.md`
- `codex/context/EPIC-134.md`
- `codex/context/WORKPAGE_DEMO_GAP_FINDINGS_2026-04-06.md`
- `codex/tasks/TASK-0221-freeze-minimal-demo-boundary-canonical-routes-and-no-new-demo-mode.md`
- `codex/tasks/TASK-0222-repair-weekly-first-local-demo-smoke-and-stage04-finalize-calculation-snapshot-regression.md`
- `codex/tasks/TASK-0223-add-a-one-command-canonical-workpage-demo-prep-script.md`
- `codex/tasks/TASK-0224-add-demo-runbook-and-a-canonical-workpage-demo-prep-regression.md`
- `docs/status/CURRENT_FOCUS.md`
- `docs/status/DECISIONS_SINCE_LAST.md`
- `docs/planning/EPICS.md`
- `docs/planning/TASK_INDEX.md`

## Verification
- `rg -n "EPIC-134|canonical /runs/:workflowRunId/workpages/\\*|deterministic|idempotent|OpenAI|no second demo mode|accepted-history" docs/planning/epics/EPIC-134.md docs/planning/LOGISTICS_WORKPAGE_DEMO_ENABLEMENT_PLAN.md codex/context/EPIC-134.md codex/context/WORKPAGE_DEMO_GAP_FINDINGS_2026-04-06.md codex/tasks/TASK-0221-freeze-minimal-demo-boundary-canonical-routes-and-no-new-demo-mode.md`
- `rg -n "EPIC-134|demo-enablement|product-expansion epic" docs/status/CURRENT_FOCUS.md docs/status/DECISIONS_SINCE_LAST.md docs/planning/EPICS.md docs/planning/TASK_INDEX.md`
- `git diff --check`

## Outcome
One authoritative repo-native statement now exists for the minimal demo boundary, and later demo-enablement tasks can stay small.

## Completion notes
- Completed on `2026-04-06`.
- Imported the EPIC-134 planning doc, demo-enablement plan, context pack, dated gap note, and all four task briefs into repo truth.
- Updated active status/index memory so EPIC-134 is tracked as the active demo-enablement tranche without reopening product scope.
- Recorded the canonical-route validation target, deterministic/no-OpenAI default prep posture, launcher-only `/demo/logistics` role, and first-demo non-goals.
