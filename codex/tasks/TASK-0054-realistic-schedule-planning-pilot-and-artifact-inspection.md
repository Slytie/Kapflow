---
id: TASK-0054
epic: EPIC-040
title: "Realistic Schedule Planning pilot and operator inspection packet"
status: DONE
owners: ["platform"]
reviewers: ["ops", "qa", "security"]
depends_on: ["TASK-0051", "TASK-0052", "TASK-0053"]
risk: high
context_packs: ["codex/context/EPIC-040.md", "codex/context/EPIC-070.md", "codex/context/EPIC-080.md"]
patterns: ["PATTERN-007", "PATTERN-009"]
---

## Objective
Deliver the first realistic, reproducible Schedule Planning pilot flow so an operator can:
- seed realistic service-day runs from the example corpus through canonical ingress,
- run the bounded Stage06 agent review at the correct stage through execution/runtime rows,
- inspect artifacts, approvals, flags, pointers, execution evidence, and timeline,
- verify that outputs are correct enough for a practical pilot-style walkthrough.

This is an experiential/operator-inspection milestone and the first realistic pilot target is Schedule Planning.

## Non-goals
- No generalized demo framework.
- No multi-agent orchestration layer.
- No expansion to all workflow packs.
- No synthetic truth path outside canonical rows/events/artifacts/pointers.
- No frontend-authoritative semantics.

## Source Files To Read First
- `docs/status/CURRENT_FOCUS.md`
- `docs/planning/FIRST_RUNTIME_SLICE.md`
- `docs/planning/EXAMPLE_DOCUMENT_CORPUS_AND_ARTIFACT_INGRESS.md`
- `docs/planning/OPENAI_API_E2E_SANDBOX_SPIKE.md`
- `docs/planning/EXECUTION_SESSION_RUNTIME_MODEL.md`
- `docs/planning/HITL_HTTP_API_CONTRACTS.md`
- `docs/planning/HITL_QUERY_CONTRACTS.md`
- `docs/planning/STAGE07_RUNTIME_MODEL.md`
- `docs/workflows/schedule_planning/v1/OPERATING_MODEL.md`
- `fixtures/example_document_corpus/manifest.yaml`
- `fixtures/example_document_corpus/seed_sets.json`
- `src/onetruth/application/services/example_document_corpus.py`
- `src/onetruth/application/services/stage06_openai_sandbox.py`

## Source Files To Change
- `docs/planning/REALISTIC_SCHEDULE_PLANNING_PILOT.md`
- `src/onetruth/application/services/realistic_schedule_planning_pilot.py`
- `scripts/run_schedule_planning_pilot.py`
- `tests/runtime/test_realistic_schedule_planning_pilot.py`
- `README.md`
- `docs/planning/FIRST_RUNTIME_SLICE.md`
- `docs/planning/TEST_MATRIX.md`
- `docs/status/DECISIONS_SINCE_LAST.md`
- `docs/planning/TASK_INDEX.md`
- `docs/status/CURRENT_FOCUS.md`

## Verification Commands
- `make schema-validate`
- `make contract`
- `make replay`
- `make acceptance`
- `make runtime`
- `pytest -q`
- `PYTHONPATH=src pytest -q tests/runtime/test_realistic_schedule_planning_pilot.py`
- `ONETRUTH_RUN_OPENAI_E2E=1 PYTHONPATH=src pytest -q tests/integration_openai` (gated)
- frontend checks (if toolchain installed):
  - `cd frontend && npm run typecheck`
  - `cd frontend && npm run test:run`
  - `cd frontend && npm run build`

## Acceptance Criteria
- Reproducible pilot runner exists and seeds runs from the real example corpus via canonical ingress.
- Pilot suite includes:
  - one Stage06 publish-ready path,
  - one Stage06 needs-information path,
  - one Stage07 issue/replan path.
- Stage06 pilot invokes bounded OpenAI-backed review through canonical execution session/tool/policy records.
- Each pilot run emits a human-inspectable packet (JSON + markdown) with canonical references and inspection routes.
- Pilot runner/idempotency behavior prevents duplicate canonical effects on repeated runs with reused pilot key.
- Runtime tests cover pilot seeding determinism, Stage06 evidence/execution linkage, Stage07 coherence, packet completeness, and rerun idempotency.
- README and planning/status docs are updated so pilot operations and inspection criteria are not stale.

## Source Files Changed
- `src/onetruth/application/services/realistic_schedule_planning_pilot.py`
- `scripts/run_schedule_planning_pilot.py`
- `tests/runtime/test_realistic_schedule_planning_pilot.py`
- `docs/planning/REALISTIC_SCHEDULE_PLANNING_PILOT.md`
- `README.md`
- `docs/planning/FIRST_RUNTIME_SLICE.md`
- `docs/planning/TEST_MATRIX.md`
- `docs/status/DECISIONS_SINCE_LAST.md`
- `docs/planning/TASK_INDEX.md`
- `docs/status/CURRENT_FOCUS.md`

## Verification Results
- `make schema-validate` ✅
- `make contract` ✅
- `make replay` ✅
- `make acceptance` ✅
- `make runtime` ✅
- `pytest -q` ✅
- `PYTHONPATH=src pytest -q tests/runtime/test_realistic_schedule_planning_pilot.py` ✅
- `PYTHONPATH=src pytest -q tests/integration_openai` ✅ (gated test skipped because env gate not enabled)
