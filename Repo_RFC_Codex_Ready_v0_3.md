# Repo_RFC_Codex_Ready_v0_3.md

## Purpose
Define a repository structure and working protocol that supports:
- Stage 4 vertical-slice MVP delivery,
- fresh-session Codex development,
- and a single authoritative truth system even as the repo absorbs a richer agentic / CompanyOS method layer.

## Core idea: one truth system, two repo concerns
This repo still has two practical concerns:
1. **Runtime concern** - services, packages, schemas, tests, and eventually implementation code.
2. **Context concern** - docs, contracts, planning, workflow packs, and agent guidance.

But it must not have two authorities.

The single authority chain is:
1. truth substrate - immutable objects + append-only events + audited pointers
2. business contract packs - workflow contract, artifact map, acceptance criteria, operating model
3. canonical execution overlay - decision catalog + execution profile
4. compiled execution artifacts - generated CompanyOS IR, pinned ExecutionSpec
5. generated or derived views - runbooks, matrices, projections, dashboards, transcripts

Lower layers constrain upper layers. Upper layers may refine, never contradict.

## Why this matters
Semantic mistakes are existential in this project:
- isolation bugs
- missing audit truth
- silent promotion drift
- second truth stores in dashboards or summaries
- unbounded agentic behavior
- stale runbooks that diverge from the repo contract

Therefore the repo must encode semantics in:
- schemas
- workflow packs
- execution-overlay files
- architecture docs that define authority and derivation rules
- acceptance and refinement checks

## Governance
- CODEOWNERS on sensitive paths
- PR template requires risk notes and verification
- CI must eventually validate:
  - schema correctness
  - overlay-to-contract refinement
  - generated-artifact freshness
  - acceptance and isolation tests

## Key directories
- `docs/vision/` - philosophy, mathematics, source lineage, threat-model context
- `docs/architecture/` - authority model, execution overlay, event/approval/orchestration semantics
- `docs/planning/` - Stage 4 plan, epics, backlog, merger backlog, test matrix
- `docs/workflows/*/v1/` - workflow contract packs and canonical execution overlays
- `docs/templates/` - templates for future workflow packs
- `schemas/` - machine-checkable source contracts
- `codex/tasks/` - the unit of agent memory and execution
- `fixtures/` - synthetic examples and golden-trace placeholders

## What changed in this RFC revision
This revision folds in the CompanyOS merger lessons:
- preserve the philosophy and mathematical note inside the repo,
- keep one authored workflow-definition system,
- represent agentic method through a smaller repo-native execution overlay,
- treat CompanyOS specs and external runbook packs as generated / compiled derivatives rather than rival source systems.

## Next step
Freeze the authority model and execution-overlay source surfaces before implementation code deepens. After that, compile generated derivatives and ExecutionSpec from repo-native source rather than hand-maintaining parallel definitions.
