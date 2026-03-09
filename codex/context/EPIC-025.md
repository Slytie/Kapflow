# EPIC-025 Context Pack — Execution overlay lowering + generated derivatives

**Purpose (why you might open this):**

- You’re changing decision catalogs, execution profiles, lowering rules, or generated derivative outputs.
- You’re defining how repo-native workflow source becomes generated runbooks, CompanyOS IR, or per-run `ExecutionSpec`.

## Non-negotiable invariants to keep in mind
- The execution overlay refines the workflow contract; it does not invent new business semantics.
- Generated artifacts are downstream and non-authoritative.
- `ExecutionSpec` is compiled and pinned per run; it is not a second hand-authored workflow-definition system.
- Source lineage and content hashes must stay visible so drift can be proven.

## Contracts / schemas to treat as authoritative
- `docs/architecture/EXECUTION_OVERLAY_MODEL.md`
- `docs/architecture/LOWERING_CONTRACT.md`
- `docs/architecture/DERIVATION_AND_GENERATION_POLICY.md`
- `docs/planning/FIRST_RUNTIME_SLICE.md`
- `docs/workflows/schedule_planning/v1/DECISION_CATALOG.yaml`
- `docs/workflows/schedule_planning/v1/EXECUTION_PROFILE.yaml`
- `schemas/agentic/decision_catalog.schema.json`
- `schemas/agentic/execution_profile.schema.json`

## Relevant pattern cards (read cards first)
- `docs/patterns/cards/PATTERN-001.md`
- `docs/patterns/cards/PATTERN-003.md`
- `docs/patterns/cards/PATTERN-005.md`

## Required test coverage (tests-as-spec)
- Contract tests proving decision refs, stage refs, tool classes, and evidence keys resolve against authoritative source.
- Generated-freshness checks once the prototype exists.
- Negative tests proving the generator cannot invent stage IDs, dataset keys, approval actions, or official outputs.

## Typical failure modes (red-team prompts)
- “Did the generated artifact invent semantics that do not exist in repo-native source?”
- “Could two source versions compile to an ambiguous execution spec?”
- “Can a generated output drift silently from its source hashes?”
- “Does the generated artifact accidentally become the place where people edit truth?”

## Current Repo Status (2026-03-08)
- `TASK-0060`, `TASK-0061`, `TASK-0062`, and `TASK-0063` are implemented.
- Composition runtime now includes:
  - first weekly->live `materialize_seed` handoff slice,
  - first bounded `notify_only` reporting->planning slice.
- Keep framing bounded: this is not yet a universal finished composition engine; follow-on observability/query expansion remains future work.
