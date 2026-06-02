---
id: TASK-0276
epic: EPIC-142
title: "Implement generated artifact envelope and canonical naming"
status: TODO
owners: ["platform"]
reviewers: ["architect", "qa"]
depends_on: ["TASK-0238"]
risk: high
context_packs:
  - "codex/context/EPIC-142.md"
patterns: ["capex-v6-planning"]
---

## Why
Imported from CAPEX v6 source task `ART-001` so future work can be executed from repo-native backlog memory without loading the full master package.

## Scope
Every capex.* artifact uses canonical envelope, kind, schema_version, source_refs, input digests, validation summary.

## Out of scope
- Runtime or production activation beyond this task's explicit source scope.
- Copying raw K12, K3, or blind-validation project files into the repository.
- Treating generated artifacts, lab reports, or AI outputs as canonical authority.

## Source files to read first
- `docs/planning/CAPEX_MASTER_V6_INTAKE.md`
- `docs/planning/CAPEX_V6_CONVERSION_MAP.csv`
- `docs/planning/epics/EPIC-142.md`
- `codex/context/EPIC-142.md`
- `docs/status/CURRENT_FOCUS.md`
- `docs/architecture/invariants.md`

## Source files to change
- Repo-native source files required by the source scope and the `EPIC-142` context pack.
- Do not edit generated derivatives before updating their authoritative source.

## Generated / downstream artifacts impacted
generated artifact helper integration; schema registry

## Plan
1. Re-read the CAPEX intake record, this task's epic context, and the source row in the conversion map.
2. Start with the required tests or evidence listed below, then make the smallest repo-native change that satisfies the task.
3. Update docs/status/test evidence only where the source scope requires it.
4. Preserve tenant/domain isolation, artifact immutability, canonical approvals, and append-only event truth.

## Verification
- Source required tests: canonical name tests; deprecated name rejection
- Acceptance gate: `IMP-004; V-002`
- Run the smallest relevant repo checks for changed code.
- Run `python3 scripts/validate_repo.py` and `git diff --check` before closing the task.

## Acceptance criteria
- Source output satisfied: generated artifact helper integration; schema registry
- Review focus covered: no second truth; deterministic bytes
- Refactor focus covered: common helper; remove duplicates
- Docs requirement covered: generated artifact guide
- Rollback/recovery posture recorded: documented if production-facing

## Source row mapping
- Source task ID: `ART-001`
- Source phase: `P6 Generated artifacts`
- Source priority: `P0`
- Source area: `schemas/backend`
- Original depends_on: `PR005`
- Converted repo dependencies: TASK-0238
- Recommended source branch: `feature/capex-*`

## Notes / decisions
- This task is initially imported as TODO even if the CAPEX master package described expected future outputs.
- Raw project corpora remain off-repo; use only sanitized fixtures, manifests, hashes, and aggregate evidence approved by the relevant fixture/governance task.
