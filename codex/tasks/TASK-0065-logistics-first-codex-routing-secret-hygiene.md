---
id: TASK-0065
epic: EPIC-070
title: "Logistics-first Codex routing, tracked-secret hygiene, and weekly-agent env-gate posture"
status: DONE
owners: ["platform"]
reviewers: ["qa"]
depends_on: ["TASK-0064"]
risk: high
context_packs: ["codex/context/EPIC-070.md", "codex/context/EPIC-025.md"]
patterns: ["PATTERN-005"]
---

## Context
Routing defaults were still pointing fresh Codex/LLM sessions to legacy `schedule_planning.v1`, and tracked repo content contained a real OpenAI API key string. We needed one bounded pass to switch new scheduling-task routing to logistics weekly/live, scrub committed secrets, and add a lightweight tracked-file detector so this class of leak fails fast.

## Objective
1. Land logistics-first routing defaults for new agentic scheduling work (`weekly_schedule_planning.v1 -> live_dispatch.v1`) while keeping `schedule_planning.v1` as regression/reference-only.
2. Remove tracked real OpenAI key material from repository content and move local env posture to safe placeholders.
3. Add a validation gate that detects real OpenAI-style keys in tracked files.
4. Define CI env-gate posture for future weekly-agent real-network suites without adding weekly-agent runtime code.

## Non-goals
- No runtime semantic expansion.
- No new weekly-agent implementation code.
- No second source of truth beyond the existing canonical workflow/task/approval/event/pointer substrate.

## Source files to read first
1. `AGENTS.md`
2. `docs/status/CURRENT_FOCUS.md`
3. `codex/TASK_TEMPLATE.md`
4. `codex/tasks/README.md`
5. `LLM_RUNBOOK.md`
6. `codex/CODEX_CONTEXT.yaml`
7. `codex/context/EPIC-070.md`
8. `codex/context/EPIC-025.md`
9. `docs/patterns/cards/PATTERN-005.md`
10. `docs/workflows/logistics_ops_family/v1/README.md`
11. `docs/workflows/weekly_schedule_planning/v1/WORKFLOW_CONTRACT.yaml`
12. `docs/workflows/live_dispatch/v1/WORKFLOW_CONTRACT.yaml`
13. `README.md`
14. `.github/workflows/agent_api.yml`

## Source files changed
- `AGENTS.md`
- `README.md`
- `LLM_RUNBOOK.md`
- `codex/CODEX_CONTEXT.yaml`
- `.codex.env`
- `.github/workflows/agent_api.yml`
- `scripts/validate_repo.py`
- `docs/status/CURRENT_FOCUS.md`
- `docs/status/DECISIONS_SINCE_LAST.md`
- `docs/planning/TASK_INDEX.md`
- `codex/tasks/TASK-0065-logistics-first-codex-routing-secret-hygiene.md`
- `src/onetruth_runtime.egg-info/PKG-INFO`

## Generated / downstream artifacts impacted
- `src/onetruth_runtime.egg-info/PKG-INFO` (tracked derivative mirrored leaked key content from README tail)

## Plan
1. Read required context files in exact order.
2. Scrub real OpenAI key material from tracked files and local `.codex.env` posture.
3. Add tracked-file secret detector to repo validator.
4. Refresh routing docs and status memory to logistics-first posture for new scheduling tasks.
5. Add future weekly-agent real-network env gate in CI workflow.
6. Run targeted validation/tests and record outcomes.

## Verification
- `rg -n "sk-proj-[A-Za-z0-9_-]{20,}|\bsk-[A-Za-z0-9]{20,}\b" .`
- `python3 scripts/validate_repo.py --schemas-only`
- `pytest -q tests/contract/test_validation_harness.py`

Results:
- PASS - `rg -n "sk-proj-[A-Za-z0-9_-]{20,}|\bsk-[A-Za-z0-9]{20,}\b" .` returned no matches.
- PASS - `python3 scripts/validate_repo.py --schemas-only` returned `VALIDATION PASSED` and reported `secret hygiene scan passed across 804 tracked text files`.
- PASS - `pytest -q tests/contract/test_validation_harness.py` returned `... [100%]` with exit code `0`.

## Acceptance criteria
- No real OpenAI key remains in tracked files.
- Validator fails on detected real OpenAI-style keys in tracked files.
- Routing docs default new scheduling tasks to logistics weekly/live with schedule_planning explicitly regression/reference-only.
- CI workflow documents and enforces env-gated posture for future weekly-agent real-network suites.

## Completion notes
- Completed in one bounded pass with no runtime semantic expansion and no weekly-agent code additions.
- Schedule Planning routing remains available as regression/reference-only, preserving single-truth substrate invariants.
- Verified tracked-file secret hygiene, routing updates, and validation harness behavior in-repo.
