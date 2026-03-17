---
id: TASK-0114
epic: EPIC-100
title: "Add backup/restore/rollback runbooks and rehearsal basis for the first-user production lane"
status: DONE
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
- `python3.11 -m pytest -q tests/contract/test_backup_restore_runbook_docs.py`
- `python3.11 -m pytest -q tests/contract/test_production_topology_reference_docs.py`
- `python3.11 -m pytest -q tests/contract/test_source_bundle_distribution_truth.py`

## Acceptance criteria
- Operators have a documented path for backup, restore, and rollback.
- The current substrate can be recovered without inventing missing architecture in the middle of an incident.
- Recovery guidance aligns with release-bundle truth.

## Notes / decisions
This task is about operational trust, not platform glamour. Keep it concrete and specific to the actual current substrate.

## Implementation notes
- Added `docs/ops/runbooks/backup_and_restore.md` as the dedicated recovery runbook for the current single-node `SQLite + local filesystem artifacts` substrate.
- Tightened `docs/ops/runbooks/rollback_and_deploy.md` so rollback is explicitly for code/version regression against preserved state, while missing/corrupt state routes to restore.
- Surfaced backup/restore guidance in the ops index and SRE signoff checklist, including an explicit reminder that rehearsal evidence is still required.

## Completion notes
- The recoverable unit is now frozen as environment-specific DB state + artifact root + matching `release_source_bundle` + provenance sidecars + secret/config references.
- The repo now carries a rehearsal basis, but it does not claim that `G1` restore rehearsal has already been completed in practice.
