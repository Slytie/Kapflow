---
id: TASK-0117
epic: EPIC-110
title: "Create Workflow Lab Phase 0 docs, authority boundary, and phased plan"
status: DONE
owners: ["platform"]
reviewers: ["qa"]
depends_on: []
risk: medium
context_packs: ["codex/context/EPIC-110.md"]
patterns: []
---

## Context
Workflow Lab does not exist yet in the repo. That is good, because we can start it as a thin, non-authoritative documentation-and-schema effort rather than inheriting a half-built platform. Before any adapters or reports exist, future agents need clear language for what Workflow Lab is, what it is not, and how it relates to production.

## Objective
Create the Phase 0 Workflow Lab docs set: overview, authority boundary, concepts/anti-patterns, phased plan, and readiness gates — all consistent with the current authoritative kernel and release-mediated promotion model.

## Non-goals
- No runtime package by default.
- No public API/UI.
- No world/materialization engine.
- No second semantics surface under `docs/workflows/*/v1`.

## Source files to read first
- `docs/planning/PRODUCTION_AND_WORKFLOW_LAB_PLAN.md`
- `docs/architecture/AUTHORITY_MODEL.md`
- `docs/architecture/DERIVATION_AND_GENERATION_POLICY.md`
- logistics workflow packs and compiled control docs
- current pilot/certification service docs where useful

## Context packs / patterns to consult
- codex/context/EPIC-110.md

## Source files to change
- new `docs/workflow_lab/*` docs
- `README.md` / AGENTS / runbook routing if needed
- task-memory / epic/context updates

## Generated / downstream artifacts impacted
- Workflow Lab docs and cross-links only
- no runtime/output artifacts

## Plan
1. Write the minimal authoritative docs set for Workflow Lab.
2. Make the authority boundary explicit: lab outputs are evidence, not production truth.
3. Record the phased plan and readiness gates.
4. Cross-link the docs from planning/context surfaces future Codex runs actually load.

## Verification
- doc link review
- `python3 scripts/validate_repo.py --schemas-only`

## Acceptance criteria
- A fresh contributor can explain Workflow Lab from repo-native docs alone.
- The docs prevent accidental drift toward a second truth system.
- Later Workflow Lab tasks have a stable conceptual base.

## Notes / decisions
Phase 0 should stay deliberately lightweight. The point is to clarify, not to platformize.

## Implementation notes
- Added a thin `docs/workflow_lab/` Phase 0 doc tree with an overview, explicit authority boundary, and phased-plan/gate recap.
- Clarified in the authority and derivation docs that Workflow Lab outputs remain evidence/derived material and must not become production truth or a second semantics compiler.
- Added a contract test to freeze the non-authoritative lab boundary and the current gated task posture.
