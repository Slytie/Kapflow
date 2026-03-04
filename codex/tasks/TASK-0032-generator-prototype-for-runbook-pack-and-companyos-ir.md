---
id: TASK-0032
epic: EPIC-025
title: "Prototype generator for runbook packs and CompanyOS IR from repo-native source"
status: DONE
owners:
  - platform
reviewers:
  - ops
  - security
  - qa
depends_on:
  - TASK-0024
  - TASK-0027
  - TASK-0028
risk: medium
context_packs:
  - codex/context/EPIC-025.md
patterns:
  - PATTERN-001
  - PATTERN-003
  - PATTERN-005
---

## Context
The repo defines the lowering policy and now also defines the concrete runtime architecture and output location strategy. What is still missing is a small generator prototype that proves repo-native source can become generated runbook packs and CompanyOS IR without becoming a second hand-authored truth surface.

Completion scope:
- implemented generator prototype code at `src/onetruth/infrastructure/generation/prototype.py`,
- added CLI wrapper `scripts/generate_prototype.py`,
- generated Schedule Planning outputs under `build/generated/`,
- added freshness enforcement through `make generated-check`,
- added integration tests for lineage, no-invention constraints, and staleness checks.

## Objective
Prototype the source-to-generated path for Stage 4 using Schedule Planning as the first workflow target, including lowering of authored spawn rules and follow-on task semantics into generated runbook guidance without promoting generated output to authority.

## Non-goals
- Do not create a full multi-workflow compiler service.
- Do not hand-author generated IR as if it were source.
- Do not let the prototype invent semantics that are not present in the workflow pack or execution overlay.

## Source files to read first
- `docs/planning/RUNTIME_BOOTSTRAP.md`
- `docs/architecture/LOWERING_CONTRACT.md`
- `docs/architecture/DERIVATION_AND_GENERATION_POLICY.md`
- `docs/workflows/schedule_planning/v1/WORKFLOW_CONTRACT.yaml`
- `docs/workflows/schedule_planning/v1/DECISION_CATALOG.yaml`
- `docs/workflows/schedule_planning/v1/EXECUTION_PROFILE.yaml`
- `docs/workflows/schedule_planning/v1/ACCEPTANCE_CRITERIA.md`
- `docs/planning/STEP_RUN_SCENARIO_HARNESS.md`

## Context packs / patterns to consult
- `codex/context/EPIC-025.md`
- `PATTERN-001`
- `PATTERN-003`
- `PATTERN-005`

## Source files to change
- `docs/planning/GENERATOR_PROTOTYPE_PLAN.md` (new)
- `docs/planning/FIRST_RUNTIME_SLICE.md`
- `docs/architecture/LOWERING_CONTRACT.md` if prototype constraints need clarification
- `docs/architecture/DERIVATION_AND_GENERATION_POLICY.md` if freshness/lineage rules need tightening
- generator code under `src/onetruth/infrastructure/generation/` or `src/onetruth/workers/` once implementation starts

## Generated / downstream artifacts impacted
- generated runbook packs
- generated CompanyOS IR
- source-hash lineage manifests
- generated freshness checks

## Plan
1. Define the prototype input manifest from workflow pack + overlay + hashes.
2. Define the output paths and filenames under a generated-output location.
3. Prototype Schedule Planning generation first.
4. Verify that outputs preserve lineage and do not invent semantics.
5. Ensure generated runbooks reflect authored follow-on task spawn rules and review loops without becoming a second workflow-definition surface.

Completed deliverables:
- `docs/planning/GENERATOR_PROTOTYPE_PLAN.md`
- `src/onetruth/infrastructure/generation/prototype.py`
- `scripts/generate_prototype.py`
- generated outputs:
  - `build/generated/runbooks/schedule_planning.v1/runbook.md`
  - `build/generated/companyos_ir/schedule_planning.v1.json`
  - `build/generated/lineage/schedule_planning.v1.lineage.json`
- freshness check integration: `make generated-check`
- tests: `tests/integration/test_generator_prototype.py`

## Verification
- the prototype consumes repo-native source only
- generated outputs carry source refs and hashes
- freshness checks can tell when a generated artifact is stale
- outputs are clearly marked non-authoritative
- full verification loop passes:
  - `make schema-validate`
  - `make contract`
  - `make replay`
  - `make acceptance`
  - `make runtime`
  - `make generated-check`
  - `pytest -q`

## Acceptance criteria
- a concrete prototype plan exists for generated runbook packs and CompanyOS IR
- output locations, lineage fields, and freshness checks are explicit
- Schedule Planning is the first prototype target
- no part of the prototype implies generated IR becomes peer authority

## Notes / decisions
The first implementation should generate to a dedicated generated-output location rather than mixing generated files back into workflow source paths.
