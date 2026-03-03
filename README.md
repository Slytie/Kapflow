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
   - `make runtime`
   - `make test`

## Quickstart (dev)
1. Install dependencies:
   - `python3 -m pip install -e .`
   - `python3 -m pip install -e .[api]` (to run the HTTP adapter with `uvicorn`)
   - or `uv sync`
2. Run repo validation/tests:
   - `make schema-validate`
   - `make contract`
   - `make replay`
   - `make acceptance`
3. Initialize a local runtime DB:
   - `PYTHONPATH=src python3 -m onetruth.cli --db-url sqlite:///./.tmp/onetruth-smoke.db init-db`
4. Run runtime smoke tests:
   - `make runtime`
   - `make runtime-api`
   - `PYTHONPATH=src pytest -q tests/runtime/scenarios tests/runtime/contracts`
   - `PYTHONPATH=src pytest -q tests/runtime/api`
5. Run full pytest suite:
   - `pytest -q`

## API quickstart (dev)
Run the thin HTTP adapter locally:
- `PYTHONPATH=src onetruth-api --db-url sqlite:///./.tmp/onetruth-api.db --host 127.0.0.1 --port 8080`
- or `PYTHONPATH=src uvicorn onetruth.api.main:app --reload --port 8080`

Required request headers (current internal/admin auth-context model):
- `x-onetruth-tenant-id`
- `x-onetruth-domain-id`
- `x-onetruth-actor-id`
- `x-onetruth-actor-type`
- `x-onetruth-actor-roles`

Current HTTP endpoints:
- `GET /api/v1/human-tasks`
- `GET /api/v1/approvals`
- `GET /api/v1/workflow-runs`
- `GET /api/v1/workflow-runs/{workflow_run_id}`
- `GET /api/v1/pointers`
- `GET /api/v1/board/schedule-planning`
- `POST /api/v1/human-tasks/{human_task_id}/claim`
- `POST /api/v1/human-tasks/{human_task_id}/complete`
- `POST /api/v1/approvals/{approval_id}/respond`

## Runtime scaffold
Runtime scaffold now exists at `src/onetruth/` with migrations under `alembic/` and runtime smoke tests under `tests/runtime/`.

First real Schedule Planning business slice now implemented:
- Stage06 completion outcomes can spawn explicit child tasks transactionally from `tasks complete`
- first Stage06 publish-path scenarios execute step-by-step through the CLI boundary
- board/query read-surface contracts now have implementation-backed tests

Stage06 scenario entrypoints:
- fixtures: `fixtures/scenarios/schedule_planning/`
- scenario tests: `tests/runtime/scenarios/`
- query-contract tests: `tests/runtime/contracts/test_hitl_query_contracts_stage06.py`

Current stable runtime command boundary:
- `python3 -m onetruth.cli --db-url <SQLALCHEMY_DB_URL> init-db`
- `python3 -m onetruth.cli --db-url <SQLALCHEMY_DB_URL> events append --json '<event-envelope-json>'`
- `python3 -m onetruth.cli --db-url <SQLALCHEMY_DB_URL> events list --json [--run-id <run_id>] [--since-event-id <event_id>] [--limit <n>]`
- `python3 -m onetruth.cli --db-url <SQLALCHEMY_DB_URL> runs create --json '<payload-json>'`
- `python3 -m onetruth.cli --db-url <SQLALCHEMY_DB_URL> runs show --workflow-run-id <id> --json`
- `python3 -m onetruth.cli --db-url <SQLALCHEMY_DB_URL> runs list --json [--workflow-id <id>] [--tenant-id <id>] [--domain-id <id>] [--state <state>]`
- `python3 -m onetruth.cli --db-url <SQLALCHEMY_DB_URL> tasks create --json '<payload-json>'`
- `python3 -m onetruth.cli --db-url <SQLALCHEMY_DB_URL> tasks claim --json '<payload-json>'`
- `python3 -m onetruth.cli --db-url <SQLALCHEMY_DB_URL> tasks complete --json '<payload-json>'`
- `python3 -m onetruth.cli --db-url <SQLALCHEMY_DB_URL> tasks show --human-task-id <id> --json`
- `python3 -m onetruth.cli --db-url <SQLALCHEMY_DB_URL> tasks list --workflow-run-id <id> --json`
- `python3 -m onetruth.cli --db-url <SQLALCHEMY_DB_URL> approvals request|respond --json '<payload-json>'`
- `python3 -m onetruth.cli --db-url <SQLALCHEMY_DB_URL> approvals show --approval-id <id> --json`
- `python3 -m onetruth.cli --db-url <SQLALCHEMY_DB_URL> approvals list --workflow-run-id <id> --json`
- `python3 -m onetruth.cli --db-url <SQLALCHEMY_DB_URL> artifacts create-version --json '<payload-json>'`
- `python3 -m onetruth.cli --db-url <SQLALCHEMY_DB_URL> artifacts show --artifact-version-id <id> --json`
- `python3 -m onetruth.cli --db-url <SQLALCHEMY_DB_URL> artifacts list --workflow-run-id <id> --json`
- `python3 -m onetruth.cli --db-url <SQLALCHEMY_DB_URL> pointers promote --json '<payload-json>'`
- `python3 -m onetruth.cli --db-url <SQLALCHEMY_DB_URL> pointers show --pointer-key <key> --workflow-run-id <id> --json`
- `python3 -m onetruth.cli --db-url <SQLALCHEMY_DB_URL> pointers list --workflow-run-id <id> --json`

Query/read contract reference for future HITL board/UI work:
- `docs/planning/HITL_QUERY_CONTRACTS.md`
- `docs/planning/HITL_HTTP_API_CONTRACTS.md`
- `docs/planning/HITL_BOARD_ARCHITECTURE.md`

Runtime idempotency behavior in this scaffold:
- duplicate `idempotency_key` at `events append` fails explicitly with JSON error `duplicate_idempotency_key`
- duplicate command idempotency keys for `runs create`, `tasks create`, `tasks claim`, and `tasks complete` fail explicitly (`duplicate_idempotency_key`)
- non-empty command idempotency keys are required for `approvals request`, `approvals respond`, `artifacts create-version`, and `pointers promote`; duplicates fail explicitly (`duplicate_idempotency_key`)
- no silent dedupe path is used in this PR

Canonical workflow/task/approval/artifact/pointer substrate now implemented:
- `workflow_runs`
- `task_runs`
- `human_tasks`
- `approvals`
- `artifact_versions`
- `artifact_pointers`

Minimal runtime states now in code:
- `workflow_runs`: `OPEN`, `COMPLETED`
- `task_runs`: `READY`, `IN_PROGRESS`, `COMPLETED`
- `human_tasks`: `OPEN`, `CLAIMED`, `COMPLETED`
- `approvals`: `PENDING`, `RESPONDED`

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
- runtime scaffold package roots under `src/onetruth/` and `alembic/`
- runtime command-boundary smoke tests under `tests/runtime/`
- generated-derivative policy describing how external runbook/tool-registry packs and CompanyOS IR must be produced from repo-native source

## What this repo does not do yet
- It now contains a narrow Stage06 business slice (review completion -> explicit child spawn + publish-path scenario coverage), but not the full Stage03->Stage07 runtime flow.
- It does not yet implement full Stage07 issue-loop runtime logic.
- It does not yet implement the full conditional child-task spawn evaluator beyond the first Stage06 mapped outcomes.
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
