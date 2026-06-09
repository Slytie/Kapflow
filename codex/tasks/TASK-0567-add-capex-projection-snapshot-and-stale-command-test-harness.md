---
id: TASK-0567
epic: EPIC-144
title: "Add CAPEX projection snapshot and stale-command test harness"
status: DONE
completed_at: 2026-06-08T00:00:00Z
owners: ["frontend"]
reviewers: ["platform", "qa"]
depends_on: ["TASK-0564", "TASK-0565"]
risk: high
context_packs:
  - "codex/context/EPIC-144.md"
patterns: ["capex-v6-planning"]
---

## Why
Imported from CAPEX v6 source task `NU-CB-P0-007` so future work can be executed from repo-native backlog memory without loading the full master package.

## Scope
Implement project-scoped projection snapshots, signed cursor, typed command envelope, stale command rejection.

## Out of scope
- Runtime or production activation beyond this task's explicit source scope.
- Copying raw K12, K3, or blind-validation project files into the repository.
- Treating generated artifacts, lab reports, or AI outputs as canonical authority.

## Source files to read first
- `docs/planning/CAPEX_MASTER_V6_INTAKE.md`
- `docs/planning/CAPEX_V6_CONVERSION_MAP.csv`
- `docs/planning/epics/EPIC-144.md`
- `codex/context/EPIC-144.md`
- `docs/status/CURRENT_FOCUS.md`
- `docs/architecture/invariants.md`

## Plan
1. Re-read the CAPEX intake record, this task's epic context, and the source row in the conversion map.
2. Start with the required tests or evidence listed below, then make the smallest repo-native change that satisfies the task.
3. Update docs/status/test evidence only where the source scope requires it.
4. Preserve tenant/domain isolation, artifact immutability, canonical approvals, and append-only event truth.

## Verification
- Source required tests: CB2-T009; performance battery; stale command tests
- Acceptance gate: `NU-GATE-007`
- Run the smallest relevant repo checks for changed code.
- Run `python3 scripts/validate_repo.py` and `git diff --check` before closing the task.

## Acceptance criteria
- Source output satisfied: Projection tables; read API contracts; command guards
- Review focus covered: Workpage is projection; UI affordance is advisory
- Refactor focus covered: Isolate from logistics workpages before CAPEX activation
- Docs requirement covered: Update workpage docs and SME routing proposal
- Rollback/recovery posture recorded: Disable CAPEX workpage command mutation until stale guards pass

## Source row mapping
- Source task ID: `NU-CB-P0-007`
- Source phase: `P8 workpages`
- Source priority: `P0`
- Source area: `capex/workpages`
- Original depends_on: `W5; NU-CB-P0-004; NU-CB-P0-005`
- Source-only dependency notes: `W5`
- Recommended source branch: `capex/workpage-projection-foundation`

## Notes / decisions
- Raw project corpora remain off-repo; use only sanitized fixtures, manifests, hashes, and aggregate evidence approved by the relevant fixture/governance task.

## Closeout evidence
- Added migration `20260608_0015_capex_workpage_projection_snapshots.py`, SQLite bootstrap DDL, SQLAlchemy models, runtime schemas, and repositories for `capex_workpage_projection_snapshots` and `capex_workpage_projection_rows`.
- Projection snapshots are project-scoped read models with deterministic `basis_hash`, basis version vector, renderer version, state, payload metadata, and ordered projection rows.
- Added internal signed projection cursor and typed workpage command-envelope guards in `onetruth.capex_platform.workpage_projection_commands`; invalid signatures, expired cursors, project/scope mismatch, stale/superseded snapshots, and basis mismatch reject before mutation callbacks run.
- Existing command receipt scope handling now recognizes CAPEX workpage command-envelope command names so future callers can reuse the shared idempotency/audit path.
- No public CAPEX workpage API, frontend route, logistics workpage change, runtime activation, or raw K12/K3/blind corpus material was introduced.
- Evidence: `PYTHONPATH=src python3.11 -m pytest -q tests/unit/test_capex_workpage_projection_snapshots.py tests/unit/test_capex_workpage_command_envelope.py tests/integration/test_capex_workpage_projection_schema_parity.py tests/unit/test_command_receipts.py` passed on 2026-06-08.
