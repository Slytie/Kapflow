---
id: TASK-0274
epic: EPIC-141
title: "Async job runtime for document processing"
status: TODO
owners: ["platform"]
reviewers: ["architect", "qa"]
depends_on: ["TASK-0236", "TASK-0239", "TASK-0266"]
risk: high
context_packs:
  - "codex/context/EPIC-141.md"
patterns: ["capex-v6-planning"]
---

## Why
Imported from CAPEX v6 source task `INGEST-009` so future work can be executed from repo-native backlog memory without loading the full master package.

## Scope
Support retry/resume/cancel/progress for large corpus jobs.

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
job model or execution-session adaptation; idempotency keys

## Plan
1. Re-read the CAPEX intake record, this task's epic context, and the source row in the conversion map.
2. Start with the required tests or evidence listed below, then make the smallest repo-native change that satisfies the task.
3. Update docs/status/test evidence only where the source scope requires it.
4. Preserve tenant/domain isolation, artifact immutability, canonical approvals, and append-only event truth.

## Verification
- Source required tests: retry no-duplicate artifacts/tasks tests
- Acceptance gate: `NU-011; AT-AI-RETRY-001`
- Run the smallest relevant repo checks for changed code.
- Run `python3 scripts/validate_repo.py` and `git diff --check` before closing the task.

## Acceptance criteria
- Source output satisfied: job model or execution-session adaptation; idempotency keys
- Review focus covered: side-effect safety; command receipts
- Refactor focus covered: job wrapper abstraction
- Docs requirement covered: job runtime docs
- Rollback/recovery posture recorded: documented if production-facing

## Source row mapping
- Source task ID: `INGEST-009`
- Source phase: `P5 Corpus ingest`
- Source priority: `P0`
- Source area: `workflow/runtime`
- Original depends_on: `PR003; PR006; INGEST-001`
- Converted repo dependencies: TASK-0236, TASK-0239, TASK-0266
- Recommended source branch: `feature/capex-*`

## Notes / decisions
- This task is initially imported as TODO even if the CAPEX master package described expected future outputs.
- Raw project corpora remain off-repo; use only sanitized fixtures, manifests, hashes, and aggregate evidence approved by the relevant fixture/governance task.
