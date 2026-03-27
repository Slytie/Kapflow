---
id: TASK-0147
epic: EPIC-124
title: "Implement backend requirement-aware artifact linkage and supported-surface policy for workpage flows"
status: DONE
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
- `src/onetruth/application/handlers/workpages.py`
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

## Outcome
- `task_requirements.py` now counts requirement satisfaction by allowed `relation_kind` instead of treating every linked artifact as satisfying by default.
- Legacy `schedule_planning.v1` upload requirements remain attachment-driven, while the first EPIC-124-aware rule lets only submitted `response` links satisfy `weekly_schedule_planning.v1` Stage05 `information_request` for `planning.draft_weekly_schedule.workbook`.
- Canonical workpage create/submit flows now accept one optional `subject_link` object and translate it into the existing artifact-link seam with server-derived `draft` or `response` relation kinds.
- Supported-surface validation now fails closed for unsupported task/approval surfaces and for demo-alias misuse through `invalid_workpage_subject_link`.
- The known pre-existing EOD workbook regression in `dispatch_reporting_workbook.py` remains outside this task; EOD linkage verification was kept focused on the new create/submit subject-link behavior.

## Commands run
- `pytest tests/unit/test_task_requirements.py`
- `pytest tests/runtime/api/test_workpages_artifact_schedule_contract.py::test_schedule_artifact_submit_links_response_to_supported_human_task_surface tests/runtime/api/test_workpages_artifact_schedule_contract.py::test_schedule_artifact_submit_links_response_to_supported_stage06_approval_surface tests/runtime/api/test_workpages_artifact_schedule_contract.py::test_schedule_artifact_submit_rejects_unsupported_subject_surface -vv`
- `pytest tests/runtime/api/test_workpages_artifact_eod_contract.py -k "canonical_eod_draft_create_links_supported_stage04_approval_as_draft or submit_artifact_workpage_links_supported_stage04_approval_as_response or demo_eod_draft_create_rejects_subject_link or canonical_eod_draft_create_rejects_cross_run_approval_subject_link"`
- `python3 scripts/validate_repo.py --schemas-only`

## Follow-ups
- `TASK-0148` should project backend-owned `workpage_actions[]` onto the supported workspace items now that requirement/link truth exists.
- `TASK-0149` should render those projected actions in the workspace UI and pass `subject_context` into create/open flows without widening the route family.
- The pre-existing EOD workbook read/submit regression in `dispatch_reporting_workbook.py` still needs separate reconciliation; it was not broadened into `TASK-0147`.
