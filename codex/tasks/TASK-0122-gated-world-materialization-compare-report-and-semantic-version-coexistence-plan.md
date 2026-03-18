---
id: TASK-0122
epic: EPIC-110
title: "Plan world materialization, comparison, and semantic-version coexistence after G2"
status: BLOCKED
owners: ["platform"]
reviewers: ["qa"]
depends_on: ["TASK-0121"]
risk: high
context_packs: ["codex/context/EPIC-110.md", "codex/context/EPIC-100.md"]
patterns: ["PATTERN-003"]
---

## Context
This is the first truly broad Workflow Lab expansion task. It should wait until the production lane is stable in practice and the thin lab has already proven useful. Otherwise the repo risks overbuilding a second platform before the comparison problems are even real.

## Objective
After G2, plan and (only if justified) begin the world-materialization, comparison, and semantic-version coexistence work needed for broader Workflow Lab experimentation.

## Non-goals
- No direct prod DB cloning into lab.
- No automatic promotion from experiment success to production truth.
- No assumption that semantic changes are just execution variants.
- No public Workflow Lab product surface by default.

## Source files to read first
- `docs/workflow_lab/PROMOTION_GATE.md`
- `docs/planning/PRODUCTION_AND_WORKFLOW_LAB_PLAN.md`
- `docs/workflow_lab/*`
- readiness-gate evidence proving G2, with `docs/workflow_lab/PROMOTION_GATE.md` as the first proof source
- any evidence from actual lab usage and release cycles
- workflow/version docs and current `workflow_version` handling

## Context packs / patterns to consult
- codex/context/EPIC-110.md
- codex/context/EPIC-100.md
- PATTERN-003

## Source files to change
- maybe new design docs / tasks / tests only if G2 is satisfied
- task-memory / epic/context updates

## Generated / downstream artifacts impacted
- planning/docs and maybe follow-on task generation; implementation is intentionally not assumed up front

## Plan
1. Verify and record that G2 is satisfied.
2. Decide whether world materialization and compare reports are truly needed now.
3. Separate execution-variant comparison from semantic-version coexistence.
4. If the need is real, generate the next bounded follow-on tasks instead of trying to build the whole platform at once.

## Verification
- doc review and gate check
- any design-validation checks appropriate to the resulting follow-on tasks

## Acceptance criteria
- The repo does not start broad Workflow Lab platform work before there is real production/lab signal justifying it.
- Any later world/compare/semantic-version work starts from an explicit problem statement, not platform enthusiasm.
- G2 remains a real gate, not ceremonial text.

## Notes / decisions
Blocked until G2 is explicitly recorded in `docs/workflow_lab/PROMOTION_GATE.md`. This task exists mostly to protect the repo from premature generalization.
