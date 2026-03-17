---
id: TASK-0108
epic: EPIC-080
title: "Add structured API boundary logging and mutation-audit correlation"
status: TODO
owners: ["platform"]
reviewers: ["qa"]
depends_on: ["TASK-0094", "TASK-0095", "TASK-0107"]
risk: medium
context_packs: ["codex/context/EPIC-080.md", "codex/context/EPIC-010.md"]
patterns: ["PATTERN-008", "PATTERN-009"]
---

## Context
The repo now has request IDs and a more disciplined API shell, but it still lacks strong boundary observability. In practice, the system is easier to trust than to diagnose. That is a good intermediate state, but not the end state for a control plane.

## Objective
Add structured request/response boundary logs and mutation-audit correlation, using the existing request-id and route metadata seams without changing runtime semantics.

## Non-goals
- No external telemetry stack.
- No distributed tracing rollout.
- No JSON response body changes just to expose request ids.
- No logging of secrets, bearer tokens, or large request payloads.

## Source files to read first
- `src/onetruth/api/main.py`
- `src/onetruth/api/request_correlation.py`
- `src/onetruth/api/route_registry.py` (or split registry modules after `TASK-0107`)
- representative mutation routes under `src/onetruth/api/routes/`
- `src/onetruth/application/handlers/_shared/command_boundary.py`

## Context packs / patterns to consult
- `codex/context/EPIC-080.md`
- `codex/context/EPIC-010.md`
- `docs/patterns/cards/PATTERN-008.md`
- `docs/patterns/cards/PATTERN-009.md`

## Source files to change
- `src/onetruth/api/main.py`
- one or more new boundary logging helpers under `src/onetruth/api/`
- possibly small route/dispatcher metadata surfaces if needed for route-name logging
- targeted runtime/unit tests
- docs/runbook or operator notes if logging fields become part of the support contract

## Generated / downstream artifacts impacted
- Task-memory and epic/context updates only.

## Plan
1. Emit structured start/finish/error log lines with request id, route name, profile, status, and latency.
2. For mutation paths, correlate boundary logs with command receipt / workflow / subject identifiers when available.
3. Keep body/header logging minimal and safe.
4. Add tests for representative success, denial, and internal-error cases.

## Verification
- targeted runtime/unit tests for logging behavior
- `python3 scripts/validate_repo.py --schemas-only`

## Acceptance criteria
- Representative API requests produce structured correlated logs.
- Mutation paths emit enough identifiers to support incident/debug workflows without exposing secrets.
- Logging stays lightweight and repo-local.

## Notes / decisions
This task improves diagnosability, not correctness semantics.
