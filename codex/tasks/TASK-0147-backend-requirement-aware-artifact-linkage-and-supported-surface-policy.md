---
id: TASK-0147
epic: EPIC-124
title: "Implement backend requirement-aware artifact linkage and supported-surface policy for workpage flows"
status: TODO
owners: ["backend"]
reviewers: ["qa"]
depends_on: ["TASK-0146"]
risk: high
context_packs: ["codex/context/EPIC-124.md"]
patterns: ["PATTERN-007", "PATTERN-009"]
---

## Context
The repo already has canonical workpage create/read/submit lanes, and artifact creation already supports explicit `links[]` with `relation_kind`. What is still missing is safe backend policy for using those links from supported workpage flows.

## Objective
Implement relation-kind-aware requirement counting and the bounded backend linking policy needed so supported workpage create/submit flows can participate in workflow-stage requirements safely.

## Non-goals
- No workspace projection or frontend CTA work yet.
- No final-packet or publish semantics.
- No broad all-workflow requirement rewrite.

## Source files to read first
- `docs/planning/HITL_HTTP_API_CONTRACTS.md`
- `docs/planning/LOGISTICS_WORKPAGES_STAGE_LINKED_PLAN.md`
- `docs/planning/epics/EPIC-124.md`
- `src/onetruth/application/services/task_requirements.py`
- `src/onetruth/application/services/task_actionability.py`
- `src/onetruth/application/handlers/workpages.py`
- `src/onetruth/application/handlers/_shared/artifact_effects.py`
- `src/onetruth/api/routes/workpages.py`

## Context packs / patterns to consult
- `codex/context/EPIC-124.md`
- `PATTERN-007`
- `PATTERN-009`

## Source files to change
- `src/onetruth/application/services/task_requirements.py`
- `src/onetruth/application/services/task_actionability.py`
- `src/onetruth/application/handlers/workpages.py`
- `src/onetruth/api/routes/workpages.py`
- targeted backend tests
- task-memory / status docs as needed

## Generated / downstream artifacts impacted
- requirement-counting behavior for supported workpage-linked task responses
- backend workpage create/submit payload semantics for subject-linked runs
- regression tests that prove `draft` links do not satisfy requirements

## Plan
1. Modernize requirement counting so only allowed relation kinds satisfy supported workpage-linked requirements.
2. Add bounded subject-link payload support to the relevant workpage create/submit commands and route handlers.
3. Validate that linked subjects belong to the same workflow run and are allowed by the supported-surface policy.
4. Add regression tests proving that `draft` links do not satisfy required uploads while `response` links can.

## Verification
- targeted backend requirement/linkage tests
- targeted workpage route/handler tests
- `python3 scripts/validate_repo.py --schemas-only`

## Acceptance criteria
- Draft-linked artifacts do not satisfy supported workpage-linked requirements.
- Submitted response-linked artifacts can satisfy supported requirements where policy allows it.
- The backend enforces same-run and supported-surface linkage safely.
- No unrelated workflow families are broadened in the process.
