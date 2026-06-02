---
id: TASK-0266
epic: EPIC-141
title: "Design bulk/staged corpus ingest architecture"
status: TODO
owners: ["platform"]
reviewers: ["architect", "qa"]
depends_on: ["TASK-0235", "TASK-0236", "TASK-0261"]
risk: high
context_packs:
  - "codex/context/EPIC-141.md"
patterns: ["capex-v6-planning"]
---

## Why
Imported from CAPEX v6 source task `INGEST-001` so future work can be executed from repo-native backlog memory without loading the full master package.

## Scope
Do not use JSON/base64 command route for project corpora.

## Out of scope
- Runtime or production activation beyond this task's explicit source scope.
- Copying raw K12, K3, or blind-validation project files into the repository.
- Treating generated artifacts, lab reports, or AI outputs as canonical authority.

## Source files to read first
- `docs/planning/CAPEX_MASTER_V6_INTAKE.md`
- `docs/planning/CAPEX_V6_CONVERSION_MAP.csv`
- `docs/planning/epics/EPIC-141.md`
- `codex/context/EPIC-141.md`
- `docs/status/CURRENT_FOCUS.md`
- `docs/architecture/invariants.md`

## Source files to change
- Repo-native source files required by the source scope and the `EPIC-141` context pack.
- Do not edit generated derivatives before updating their authoritative source.

## Generated / downstream artifacts impacted
bulk ingest design; staging API; object/folder import option

## Plan
1. Re-read the CAPEX intake record, this task's epic context, and the source row in the conversion map.
2. Start with the required tests or evidence listed below, then make the smallest repo-native change that satisfies the task.
3. Update docs/status/test evidence only where the source scope requires it.
4. Preserve tenant/domain isolation, artifact immutability, canonical approvals, and append-only event truth.

## Verification
- Source required tests: 1k synthetic ingest route; body-limit tests
- Acceptance gate: `AT-SCALE-001; AT-SCALE-002`
- Run the smallest relevant repo checks for changed code.
- Run `python3 scripts/validate_repo.py` and `git diff --check` before closing the task.

## Acceptance criteria
- Source output satisfied: bulk ingest design; staging API; object/folder import option
- Review focus covered: streaming/staging safety; idempotency
- Refactor focus covered: separate ingest from artifact command route
- Docs requirement covered: bulk ingest docs
- Rollback/recovery posture recorded: documented if production-facing

## Source row mapping
- Source task ID: `INGEST-001`
- Source phase: `P5 Corpus ingest`
- Source priority: `P0`
- Source area: `backend/ingest`
- Original depends_on: `PROJ-001; PR002; PR003`
- Converted repo dependencies: TASK-0235, TASK-0236, TASK-0261
- Recommended source branch: `feature/capex-*`

## Notes / decisions
- This task is initially imported as TODO even if the CAPEX master package described expected future outputs.
- Raw project corpora remain off-repo; use only sanitized fixtures, manifests, hashes, and aggregate evidence approved by the relevant fixture/governance task.
