---
id: TASK-0121
epic: EPIC-110
title: "Add VariantSpec/RunProfile, freshness guards, and the first Stage04 lab adapter after G1"
status: BLOCKED
owners: ["platform"]
reviewers: ["qa"]
depends_on: ["TASK-0120"]
risk: high
context_packs: ["codex/context/EPIC-110.md", "codex/context/EPIC-100.md"]
patterns: ["PATTERN-003", "PATTERN-005"]
---

## Context
This is the first true Workflow Lab execution-layer task. It should not start until G1 is explicitly met, because otherwise the repo would be building a second execution lane before production is stable enough to justify it.

## Objective
After G1, add the first bounded Workflow Lab execution layer: explicit execution-variant identity (`VariantSpec`), execution conditions (`RunProfile`), freshness guards, and one narrow first execution adapter over weekly Stage04.

## Non-goals
- No semantic-version experimentation engine.
- No public Workflow Lab API/UI.
- No world family/general experiment platform yet.
- No direct production runtime mutation.

## Source files to read first
- `docs/planning/PRODUCTION_AND_WORKFLOW_LAB_PLAN.md`
- `docs/workflow_lab/*`
- `schemas/workflow_lab/*`
- Stage04 runtime/pilot services
- readiness-gate docs proving G1

## Context packs / patterns to consult
- codex/context/EPIC-110.md
- codex/context/EPIC-100.md
- PATTERN-003
- PATTERN-005

## Source files to change
- Workflow Lab runtime/adapter code only if G1 is satisfied
- targeted tests/docs
- task-memory / epic/context updates

## Generated / downstream artifacts impacted
- first bounded lab execution adapter and tests
- updated docs only if the gate is actually cleared

## Plan
1. Verify and record that G1 is satisfied.
2. Add `VariantSpec` and `RunProfile` in executable form.
3. Add freshness guards that fail closed on invalid comparisons.
4. Implement the narrow first Stage04 adapter without broadening into a general experiment system.

## Verification
- targeted adapter/freshness tests
- Stage04-focused runtime checks
- `python3 scripts/validate_repo.py --schemas-only`

## Acceptance criteria
- The repo can evaluate execution variants under fixed semantics for one narrow Stage04 path.
- Freshness invalidity fails closed.
- The task does not start at all unless G1 is explicitly satisfied.

## Notes / decisions
Blocked until G1 is explicitly recorded. The point of this task is disciplined timing, not just feature sequencing.
