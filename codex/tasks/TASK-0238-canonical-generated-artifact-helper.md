---
id: TASK-0238
epic: EPIC-137
title: "Canonical generated-artifact helper"
status: DONE
owners: ["platform"]
reviewers: ["architect", "qa"]
depends_on: ["TASK-0235", "TASK-0236", "TASK-0237"]
risk: high
context_packs:
  - "codex/context/EPIC-137.md"
patterns: ["capex-v6-planning"]
---

## Why
Imported from CAPEX v6 source task `MP-PR005` so future work can be executed from repo-native backlog memory without loading the full master package.

## Scope
Add persist_generated_artifact_effects, canonical_json_bytes, existing-row validation, provenance/event support.

## Out of scope
- Runtime or production activation beyond this task's explicit source scope.
- Copying raw K12, K3, or blind-validation project files into the repository.
- Treating generated artifacts, lab reports, or AI outputs as canonical authority.

## Source files to read first
- `docs/planning/CAPEX_MASTER_V6_INTAKE.md`
- `docs/planning/CAPEX_V6_CONVERSION_MAP.csv`
- `docs/planning/epics/EPIC-137.md`
- `codex/context/EPIC-137.md`
- `docs/status/CURRENT_FOCUS.md`
- `docs/architecture/invariants.md`

## Plan
1. Re-read the CAPEX intake record, this task's epic context, and the source row in the conversion map.
2. Start with the required tests or evidence listed below, then make the smallest repo-native change that satisfies the task.
3. Update docs/status/test evidence only where the source scope requires it.
4. Preserve tenant/domain isolation, artifact immutability, canonical approvals, and append-only event truth.

## Verification
- Source required tests: CR-004 plus regression tests
- Acceptance gate: `Generated artifact helper emits created event, validates digest/partition, enforces storage policy.`
- Run the smallest relevant repo checks for changed code.
- Run `python3 scripts/validate_repo.py` and `git diff --check` before closing the task.

## Acceptance criteria
- Source output satisfied: Generated artifact helper emits created event, validates digest/partition, enforces storage policy.
- Review focus covered: CR-004
- Refactor focus covered: RF-006
- Docs requirement covered: update gate/docs/ADR if behavior changes
- Rollback/recovery posture recorded: documented if production-facing

## Source row mapping
- Source task ID: `MP-PR005`
- Source phase: `P1 Platform Foundation`
- Source priority: `P0`
- Source area: `platform/readiness`
- Original depends_on: `PR002;PR003;PR004`
- Recommended source branch: `foundation/ip5`

## Notes / decisions
- Raw project corpora remain off-repo; use only sanitized fixtures, manifests, hashes, and aggregate evidence approved by the relevant fixture/governance task.

## Closeout evidence
- Added `canonical_json_bytes(value)` for deterministic compact ASCII JSON bytes.
- Added `persist_generated_artifact_effects(...)` in the shared artifact-effects layer, using root-confined blob writes and existing canonical artifact-version/event/provenance effects.
- Helper validates optional expected digest, canonical partition override pairs, existing explicit artifact rows, and conflict cases before duplicate events are emitted.
- Focused generated-artifact helper tests cover creation, event/provenance emission, replay without duplicate events, digest mismatch, conflict detection, root-confined storage, and partition validation.
- This closes `MP-PR005` as a repo platform-readiness helper only; broad generated-artifact migration remains later CAPEX scope.
