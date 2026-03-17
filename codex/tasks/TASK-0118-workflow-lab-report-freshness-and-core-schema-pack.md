---
id: TASK-0118
epic: EPIC-110
title: "Add Workflow Lab report/freshness and core schema pack"
status: TODO
owners: ["platform"]
reviewers: ["qa"]
depends_on: ["TASK-0110", "TASK-0117"]
risk: medium
context_packs: ["codex/context/EPIC-110.md"]
patterns: ["PATTERN-003"]
---

## Context
Once Workflow Lab concepts are documented, the next high-value step is a schema-first contract for the evidence the lab will normalize and compare. The repo already has rich outputs, but they need a stable report/freshness vocabulary before any adapter logic becomes durable.

## Objective
Create the core Workflow Lab schema pack for normalized reports and freshness semantics without yet introducing a public lab runtime or experiment platform.

## Non-goals
- No full experiment model.
- No adapter execution yet.
- No semantic-version comparison engine.
- No production/runtime behavior changes.

## Source files to read first
- `docs/planning/PRODUCTION_AND_WORKFLOW_LAB_PLAN.md`
- `docs/workflow_lab/*` (from TASK-0117)
- existing pilot/certification output shapes
- any current schema conventions used elsewhere in the repo

## Context packs / patterns to consult
- codex/context/EPIC-110.md
- PATTERN-003

## Source files to change
- new `schemas/workflow_lab/*` schema files
- matching docs in `docs/workflow_lab/`
- validator wiring if appropriate
- task-memory / epic/context updates

## Generated / downstream artifacts impacted
- schema files
- documentation and validator routing updates only

## Plan
1. Define `RunReport.core` and freshness metadata first.
2. Add the minimum supporting contracts needed now (`VariantSpec`, `RunProfile`, `WorldInstance`, `CompareReport`) without pretending later phases are already implemented.
3. Wire validation/documentation so future adapters have a stable target.
4. Keep the schemas compatible with release-mediated promotion and separate-state assumptions.

## Verification
- schema validation checks
- `python3 scripts/validate_repo.py --schemas-only`

## Acceptance criteria
- Workflow Lab report/freshness schemas exist and are documented.
- Future adapters can target a stable machine-readable report shape.
- The schema pack stays thin enough that it does not imply a general experiment platform yet.

## Notes / decisions
Distinguish clearly between execution variants and semantic/version changes in the schema docs.
