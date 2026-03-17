# EPIC-110 - Workflow Lab (thin, non-authoritative candidate-evaluation lane)

## Summary
Create a thin internal Workflow Lab lane that can normalize, evaluate, and compare candidate workflow/process/task behavior outside production without becoming a second authority chain.

## Why this epic exists
We want to keep developing candidate tasks, processes, and workflows in a lab while a first user uses production stably. The repo already has a strong kernel and rich outputs, so the right move is a thin evidence/report-first lab, not a second runtime or semantics platform.

## Scope
### In scope
- Workflow Lab authority-boundary docs and phased plan
- report/freshness/variant/run-profile/world schemas
- normalization of existing repo outputs into a stable report core
- release-mediated promotion guidance and readiness gates
- later gated execution-adapter work only after production gates are met

### Out of scope
- public Workflow Lab UI/API in the first tranche
- direct mutation of production workflow truth from lab artifacts
- raw production DB cloning as a world source
- building a general experiment platform before repeated need exists

## Dependencies
- EPIC-025
- EPIC-080
- EPIC-100

## Key decisions / constraints
- Workflow Lab is non-authoritative. It may evaluate kernel behavior but may not become a peer workflow-definition or promotion-truth system.
- Early Workflow Lab should focus on **execution variants under fixed semantics**.
- Semantic changes remain new workflow versions / release candidates until explicit version-coexistence support is proven.
- Promotion should default to reviewed release promotion (`lab -> gate -> prod`), not runtime transfer.

## Deliverables
- `docs/workflow_lab/*` Phase 0 docs
- Workflow Lab schemas and report/freshness model
- normalization adapters over current repo outputs
- promotion/readiness-gate docs
- later gated execution-adapter tasks

## Definition of Done
- a fresh contributor can explain what Workflow Lab is, what it is not, what may be compared there, and how a lab result can influence production without confusing evidence with authoritative truth.

## Current Repo Status (2026-03-17 planning pass)
- There is currently no `docs/workflow_lab/` tree and no `src/onetruth/workflow_lab/` package; the surface is still cleanly absent.
- The repo already emits strong raw materials for Phase 1: Stage04 inspection packets and pilot summaries, realistic scheduling pilot outputs, current capability certification outputs, and runtime workspace/export bundles.
- Production identity/bootstrap, deploy topology, rollback/restore, and observability are not yet explicit enough to justify a heavier lab execution/comparison layer.

## Tasks
- TASK-0117
- TASK-0118
- TASK-0119
- TASK-0120
- TASK-0121
- TASK-0122
