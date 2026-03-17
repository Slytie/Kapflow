---
id: TASK-0103
epic: EPIC-040
title: "Extract the flag and Stage07 issue-loop mutation family"
status: DONE
owners: ["platform"]
reviewers: ["qa"]
depends_on: ["TASK-0102"]
risk: high
context_packs: ["codex/context/EPIC-040.md", "codex/context/EPIC-060.md"]
patterns: ["PATTERN-001", "PATTERN-002", "PATTERN-004"]
---

## Context
After approvals and human tasks moved out, the next orchestration hotspot cluster inside `workflow_task_lifecycle.py` is the flag / Stage07 issue-loop family:
- `create_flag_command`
- `transition_flag_state_command`
- `activate_stage07_issue_from_flag_command`
- `reconcile_stage07_command`

These commands still bind Stage07 mutation semantics to the legacy hotspot even though their aggregate boundaries are already conceptually distinct.

## Objective
Move the flag / Stage07 issue-loop mutation family into a dedicated handler module with the same compatibility posture used for approvals and human tasks.

## Non-goals
- No semantic changes to flag states, transitions, severity, or issue activation rules.
- No redefinition of capability semantics.
- No broad read/query refactor beyond what the extracted family directly requires.

## Source files to read first
- `src/onetruth/application/handlers/workflow_task_lifecycle.py`
- `src/onetruth/api/routes/flags.py`
- `src/onetruth/application/services/capabilities/flags.py`
- `src/onetruth/infrastructure/repositories/flags.py`
- `tests/runtime/api/`
- `tests/security/`
- `docs/architecture/flag_model.md`
- `tests/contract/test_handler_import_boundaries.py`

## Context packs / patterns to consult
- `codex/context/EPIC-040.md`
- `docs/patterns/cards/PATTERN-001.md`
- `docs/patterns/cards/PATTERN-002.md`
- `docs/patterns/cards/PATTERN-004.md`

## Source files to change
- new `src/onetruth/application/handlers/flags.py`
- `src/onetruth/application/handlers/workflow_task_lifecycle.py`
- directly affected route/service/CLI call sites if any should import the extracted module rather than the legacy hotspot
- `tests/contract/test_handler_import_boundaries.py`
- targeted flag/stage07 runtime or security tests

## Generated / downstream artifacts impacted
- Task-memory and epic/context updates only.

## Plan
1. Extract the flag mutation family behind a dedicated module.
2. Preserve compatibility through thin wrappers in `workflow_task_lifecycle.py`.
3. Rewire direct callers where doing so reduces centrality without broad churn.
4. Add import-boundary coverage that forbids the extracted flag module from re-importing the legacy hotspot.

## Verification
- targeted pytest for flag transition / Stage07 activation paths
- `PYTHONPATH=src pytest -q tests/contract/test_handler_import_boundaries.py`
- `python3 scripts/validate_repo.py --schemas-only`

## Acceptance criteria
- Flag and Stage07 issue-loop mutations live in a dedicated handler family.
- The extracted family no longer depends on `workflow_task_lifecycle.py`.
- Existing route/CLI/service behavior is preserved.

## Notes / decisions
Keep Stage07 semantics frozen. This task is structural, not semantic.
- Implemented via `src/onetruth/application/handlers/flags.py`, with API/CLI/pilot callers rewired to the extracted family and `workflow_task_lifecycle.py` reduced to thin compatibility wrappers.
- Shared idempotency-availability checks now live on the neutral command-boundary seam so the extracted flag family does not re-import the legacy hotspot.
