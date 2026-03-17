---
id: TASK-0114
epic: EPIC-100
title: "Add backup/restore/rollback runbooks and rehearsal basis for the first-user production lane"
status: TODO
owners: ["platform"]
reviewers: ["qa"]
depends_on: ["TASK-0113"]
risk: high
context_packs: ["codex/context/EPIC-100.md"]
patterns: []
---

## Context
A single-node first-user production system is acceptable only if it is explicitly recoverable. Today the repo has rollback guidance, but not yet a complete, rehearsable story that ties together DB state, artifact roots, release bundles, and operator actions.

## Objective
Produce concrete backup/restore/rollback runbooks and the minimum rehearsal basis so that production stability is defined by recoverability, not only by code correctness.

## Non-goals
- No multi-region disaster-recovery platform.
- No new persistence substrate by default.
- No attempt to automate every operator step in this tranche.

## Source files to read first
- `docs/ops/runbooks/rollback_and_deploy.md`
- `docs/ops/README.md`
- release/provenance docs
- storage/session substrate modules for current-state assumptions

## Context packs / patterns to consult
- codex/context/EPIC-100.md

## Source files to change
- rollback/deploy runbooks
- backup/restore runbook(s)
- maybe small helper scripts/checklists if justified
- task-memory / epic/context updates

## Generated / downstream artifacts impacted
- operator runbooks
- possibly simple rehearsal artifacts/checklists
- no product/runtime semantics changes by default

## Plan
1. Define what must be backed up and restored in the current single-node substrate.
2. Write the restore and rollback operator flow end to end.
3. Add the smallest rehearsal basis that makes the docs testable.
4. Tie release bundles, manifests, and artifact roots into the recovery story.

## Verification
- runbook consistency review
- any rehearsal check added by the task
- `python3 scripts/validate_repo.py --schemas-only`

## Acceptance criteria
- Operators have a documented path for backup, restore, and rollback.
- The current substrate can be recovered without inventing missing architecture in the middle of an incident.
- Recovery guidance aligns with release-bundle truth.

## Notes / decisions
This task is about operational trust, not platform glamour. Keep it concrete and specific to the actual current substrate.
