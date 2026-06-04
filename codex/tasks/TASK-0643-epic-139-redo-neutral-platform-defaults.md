---
id: TASK-0643
epic: EPIC-139
title: EPIC-139 redo neutral platform defaults
status: IN_PROGRESS
owners: ["platform"]
reviewers: ["architect", "qa"]
depends_on: ["TASK-0257", "TASK-0258", "TASK-0370", "TASK-0561"]
risk: high
context_packs: ["codex/context/EPIC-139.md"]
patterns: ["neutral platform defaults", "explicit logistics activation"]
---

# TASK-0643 - EPIC-139 Redo: Neutral Platform Defaults

## Context

The EPIC-139 redo package classified this checkout as State B: hook and registry seams exist, but platform defaults still loaded logistics packs. Existing targeted tests and the CAPEX invariant audit passed in that state, so the guardrails needed to be inverted.

Old EPIC-139 task closeouts remain historical evidence. This task records the reopened RED posture and the P0 repair needed before downstream CAPEX work can treat EPIC-139 as clean again.

Mapped source package: `capex_epic139_redo_final_implementation_package_v2_context_aware_updated.zip`.

## Why

The redo package found that EPIC-139 had a false-green State B posture: tests and audit passed even though platform defaults still loaded logistics hooks and workpage packs.

## Scope

Make platform approval and workpage defaults neutral, preserve logistics behavior through explicit activation, and invert tests/audit checks so the old default-logistics pattern fails.

## Objective

Make approval-response hooks and workpage descriptor/action defaults platform-neutral, preserve logistics behavior through explicit activation, and harden tests/audit checks so the old false-green default-import pattern fails.

## Non-goals

- Do not add a broad domain plugin framework.
- Do not add or reshape public HTTP routes.
- Do not rewrite old EPIC-139 closeouts as if they never happened.
- Do not resolve EPIC-150 wording or final Python/Node supported-environment acceptance in this task.

## Source files to change

- `src/onetruth/application/services/approval_response_hooks.py`
- `src/onetruth/application/services/logistics_approval_response_hooks.py`
- `src/onetruth/application/handlers/approvals.py`
- `src/onetruth/api/routes/approvals.py`
- `src/onetruth/application/services/workpage_descriptor_registry_defaults.py`
- `src/onetruth/application/services/workpage_action_registry_defaults.py`
- `src/onetruth/application/services/logistics_workpage_descriptors.py`
- `src/onetruth/application/services/logistics_workpage_action_registry.py`
- `src/onetruth/application/services/workpage_action_projection.py`
- `src/onetruth/application/handlers/workpage_action_resolution.py`
- `src/onetruth/api/routes/workflow_runs.py`
- `src/onetruth/api/routes/human_tasks.py`
- `src/onetruth/api/routes/workpages.py`
- `src/onetruth/application/services/capex_invariant_audit.py`
- Related unit, runtime, and contract tests.

## Acceptance criteria

- `DEFAULT_APPROVAL_RESPONSE_HOOKS == ()`.
- Generic approval response has no logistics imports or inline logistics effects.
- Logistics approval hooks are selected only through an explicit workflow-aware activation path.
- Default workpage descriptor and action registries are empty.
- Logistics workpage descriptor/action registries are exposed through explicit factories and used by logistics call sites.
- CAPEX invariant audit fails if default modules import or load logistics hooks or workpage packs.
- Unknown/CAPEX workflow IDs do not resolve logistics approval hooks, workpage descriptors, or workpage actions by default.
- Logistics regressions still publish weekly schedules and finalize dispatch reporting through explicit activation.

## Verification

- `python3.11 -m pytest -q tests/unit/test_approval_response_hooks.py tests/unit/test_workpage_descriptor_registry.py tests/unit/test_workpage_domain_registry.py tests/contract/test_handler_import_boundaries.py tests/contract/test_capex_invariant_audit.py`
- `python3.11 -m pytest -q tests/runtime/api/test_weekly_publish_loop_api.py::test_weekly_publish_approval_auto_publishes_reviewed_latest_draft tests/runtime/api/test_dispatch_reporting_finalize_loop_api.py::test_dispatch_reporting_happy_path_builds_review_finalizes_and_handoffs`
- `python3.11 scripts/run_capex_invariant_audit.py --output-root /private/tmp/kapflow-epic139-impl-audit --json`
- `python3.11 scripts/validate_repo.py`
- `python3.11 scripts/validate_capex_epic_progress_data.py frontend/src/data/capexEpicProgressData.json`

## Notes / decisions

- Keep the task active/RED until the reopened EPIC-139 gate receives architecture/QA review and follow-up acceptance.
- EPIC-150 wording correction and final supported-environment acceptance remain follow-up work.
