---
id: TASK-0113
epic: EPIC-100
title: "Define the production/lab topology ADR and a single-node deploy reference"
status: DONE
owners: ["platform"]
reviewers: ["qa"]
depends_on: ["TASK-0111", "TASK-0112"]
risk: high
context_packs: ["codex/context/EPIC-100.md"]
patterns: ["PATTERN-008"]
---

## Context
The repo now has strong internal discipline but still lacks an explicit, operator-friendly answer to: what exactly is production, what exactly is lab, and how are they separated? For a first user, the right answer may still be a single-node system — but it should be explicit, not accidental.

## Objective
Define the first-user reference topology for prod and lab as separate environments with the same kernel and release discipline, choose the deploy artifact/install flow, and write the ADR/runbook basis that future productization and Workflow Lab work can rely on.

## Non-goals
- No forced migration to PostgreSQL/object storage.
- No Kubernetes/platform rewrite.
- No public Workflow Lab service.

## Source files to read first
- `docs/planning/PRODUCTION_AND_WORKFLOW_LAB_PLAN.md`
- `docs/ops/README.md`
- `docs/ops/runbooks/rollback_and_deploy.md`
- release/provenance docs and scripts
- current artifact/database substrate modules for factual grounding

## Context packs / patterns to consult
- codex/context/EPIC-100.md
- PATTERN-008

## Source files to change
- new topology ADR / docs
- deploy/runbook docs
- maybe helper scripts/templates if the task needs them
- task-memory / epic/context updates

## Generated / downstream artifacts impacted
- operator-facing topology and deploy-reference docs
- promotion-lane guidance for future runbooks
- no runtime feature changes required by default

## Plan
1. Write the prod/lab topology in repo-native docs.
2. Define the deploy artifact/install path explicitly.
3. Record the separation rules: DBs, artifact roots, secrets, promotion path.
4. Cross-link the result from current ops/readme documents.

## Verification
- doc link integrity / validation where available
- `python3 scripts/validate_repo.py --schemas-only`
- release/runbook doc review checklist

## Acceptance criteria
- A fresh operator can explain prod vs lab vs promotion gate from repo-native docs alone.
- The first-user deployment model is explicit and supportable.
- Future lab work no longer needs to infer what environment topology it is targeting.

## Notes / decisions
This task should optimize for clarity and operational truth, not for maximal platform sophistication.

## Implementation notes
- Added ADR-004 to define production and lab as separate single-node environments over the current implemented substrate and to supersede ADR-003's first-user deploy-substrate assumption.
- Added an operator-facing topology/deploy reference that ties `release_source_bundle`, `ONETRUTH_DB_URL`, `ONETRUTH_ARTIFACT_ROOT`, `shared_env`, and lab separation rules into one deploy story.
- Upgraded the deploy/rollback runbook from skeleton to a concrete release-bundle-based procedure without pulling backup/restore rehearsal into this task.

## Completion notes
- `release_source_bundle` remains the only operator deploy artifact; `handoff_source_bundle` and `runtime_workspace_bundle` remain non-deploy surfaces.
- This task intentionally leaves backup/restore rehearsal, health/readiness/metrics, and GitHub perimeter hardening to later bounded tasks.
