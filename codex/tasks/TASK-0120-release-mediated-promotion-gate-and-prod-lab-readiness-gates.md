---
id: TASK-0120
epic: EPIC-110
title: "Define the release-mediated promotion gate and explicit readiness gates G1/G2"
status: TODO
owners: ["platform"]
reviewers: ["qa"]
depends_on: ["TASK-0113", "TASK-0114", "TASK-0117", "TASK-0118", "TASK-0119"]
risk: medium
context_packs: ["codex/context/EPIC-100.md", "codex/context/EPIC-110.md"]
patterns: []
---

## Context
The current repo is much better suited to release promotion than to live runtime pushing of new workflow/process definitions. Before heavier Workflow Lab execution work begins, the repo needs an explicit promotion gate model and explicit readiness gates so future Codex agents do not treat the lab as a side door into production.

## Objective
Define the release-mediated promotion gate and the explicit G1/G2 readiness checks in repo-native docs/runbooks so productization and Workflow Lab work stay synchronized.

## Non-goals
- No new runtime promotion engine.
- No automatic certification bridge yet.
- No public Workflow Lab control plane.

## Source files to read first
- `docs/planning/PRODUCTION_AND_WORKFLOW_LAB_PLAN.md`
- prod/lab topology and runbook docs
- Workflow Lab docs/schemas
- current release/provenance docs

## Context packs / patterns to consult
- codex/context/EPIC-100.md
- codex/context/EPIC-110.md

## Source files to change
- promotion-gate docs / runbook updates
- readiness-gate docs/checklists
- maybe task-routing updates for future Codex work
- task-memory / epic/context updates

## Generated / downstream artifacts impacted
- docs and checklists only
- no new runtime surfaces by default

## Plan
1. Write the default promotion model: candidate release + lab evidence + review -> tagged release -> prod.
2. Record G1/G2 in a place future agents will actually read.
3. Cross-link productization and Workflow Lab docs so the two lanes stay coupled.
4. Make the blocked status of later Workflow Lab tasks explicit and explain why.

## Verification
- doc review / link integrity
- `python3 scripts/validate_repo.py --schemas-only`

## Acceptance criteria
- A future Codex agent can tell exactly when heavier Workflow Lab work is allowed to begin.
- Promotion guidance no longer sounds like direct runtime mutation from lab to prod.
- The production and lab lanes are documented as a coordinated system rather than two independent projects.

## Notes / decisions
This task is the conceptual bridge between productization and Workflow Lab. It should remain documentation/runbook focused.
