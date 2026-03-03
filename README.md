# Workflow Orchestration Platform - Stage 4 MVP Repo (Codex-ready)

This repository is the Stage 4 contract-first scaffold for an enterprise, multi-tenant orchestration platform.

The repo is designed for fresh-session Codex development and for human contributors joining mid-stream. The central rule is simple:

> There is one truth system.

Official claims must be derivable from:
- immutable versioned artifacts,
- append-only timeline events,
- and audited mutable pointers / registries.

Current Stage 4 implementation/debug focus:
- **Primary runtime/debug wedge:** Schedule Planning v1
- **Primary first code slice:** canonical runtime substrate plus the Schedule Planning Stage06 publish path and conditional follow-on review/info loops, then Stage07 issue-scoped replans
- **Primary test objective:** a fully-agentive end-to-end workflow path where designated agent principals can execute every in-scope task without bypassing the canonical task, approval, event, or pointer model, including explicit spawned child-task lineage
- **Secondary reference workflow:** Payroll v1 as the linear approval-heavy governance benchmark

Everything else - runbooks, dashboards, summaries, generated CompanyOS specs, projections, transcripts, research notes, and external pattern references - is derived, compiled, generated, or evidentiary material layered on top of that substrate.

## Start here
1. `AGENTS.md`
2. `docs/status/CURRENT_FOCUS.md`
3. `docs/planning/STAGE4_PLAN.md`
4. `docs/planning/RUNTIME_BOOTSTRAP.md`
5. `docs/planning/FIRST_RUNTIME_SLICE.md`
6. `docs/planning/STEP_RUN_SCENARIO_HARNESS.md`
7. `docs/planning/TDD_IMPLEMENTATION_PLAN.md`
8. `docs/architecture/AUTHORITY_MODEL.md`
9. `docs/architecture/governance_vocabulary.md`
10. workflow packs:
   - `docs/workflows/schedule_planning/v1/`
   - `docs/workflows/payroll/v1/`
11. validation commands:
   - `make schema-validate`
   - `make contract`
   - `make replay`
   - `make acceptance`
   - `make test`

## What is in this repo right now?
This scaffold contains:
- a Codex context plane (`codex/`)
- epic context packs for targeted re-entry (`codex/context/`)
- a reference pattern library (`docs/patterns/`)
- a research digest and full research notes (`docs/research/`)
- vision and mathematical foundations curated from the CompanyOS packet (`docs/vision/`)
- a single-truth authority model and execution-overlay architecture (`docs/architecture/`)
- Stage 4 planning, epics, tasks, test strategy, TDD plan, and merger backlog (`docs/planning/`)
- a concrete runtime bootstrap, first implementation-slice plan, and step-run scenario harness plan
- a Schedule Planning workflow pack and a Payroll workflow pack
- canonical execution-overlay files for both workflows:
  - `DECISION_CATALOG.yaml`
  - `EXECUTION_PROFILE.yaml`
- shared governance and permission vocabularies
- workflow-pack schemas, runtime object schemas, payload schemas, and a tool-class registry
- fixture packs for Schedule Planning and Payroll, including synthetic completed example artifacts for every templated stage
- a repo validation harness (`scripts/validate_repo.py`)
- a real pytest-backed test portfolio (`tests/`) with scenario catalog + replay oracles
- generated-derivative policy describing how external runbook/tool-registry packs and CompanyOS IR must be produced from repo-native source

## What this repo does not do yet
- It does not contain implementation services yet.
- It does not yet contain the runtime scaffold under `src/onetruth/` and `alembic/`; those target locations are now chosen and documented.
- It does not treat external runbook packs as source of truth.
- It does not hand-author CompanyOS `WorkflowSpec` as a second workflow-definition system.
- It does not allow method changes or capability expansions to self-promote.
- It does not allow an agent-only execution path to outrank the canonical workflow/task/approval/event substrate.
- It does not yet provide Payroll golden traces beyond a placeholder README; Payroll remains the secondary semantic/governance cross-check until runtime work reaches that wedge.

## Guiding idea
The project should stay creative without becoming semantically loose:
- business truth stays contract-first and auditable,
- agentic method stays flexible but bounded,
- generated artifacts stay useful but non-authoritative,
- context aids stay small and discoverable for fresh sessions,
- runtime work stays maintainable because the authority chain is explicit and machine-checkable.

## Additional context guidance
- `docs/architecture/DOCUMENT_STATUS_MATRIX.md` tells you which documents are authoritative, generated, historical, or deferred.
- `codex/context/` contains short epic context packs; use them before opening long reference material.
- `docs/patterns/` contains external architecture patterns in card form; read cards first.
- `docs/research/AGENT_DIGEST.md` points to deeper research only when you need more justification.
- `docs/planning/RUNTIME_BOOTSTRAP.md` locks the first concrete runtime stack, persistence model, and repo layout.
- `docs/planning/FIRST_RUNTIME_SLICE.md` tells you what code should be written first, where it should live, and what to defer.
- `docs/architecture/LOWERING_CONTRACT.md` explains how repo-native source lowers into generated CompanyOS-style artifacts and a compiled `ExecutionSpec`.
- `docs/architecture/RUNTIME_OBJECT_MODEL.md` defines the canonical runtime vocabulary so implementation work does not accidentally fork into a second truth model.
- `docs/planning/TDD_IMPLEMENTATION_PLAN.md` explains how to use the schemas, golden traces, synthetic example artifacts, and pytest suites as the first development harness.
- `docs/planning/STEP_RUN_SCENARIO_HARNESS.md` explains how future runtime scenario tests should drive the real command boundary step by step.
