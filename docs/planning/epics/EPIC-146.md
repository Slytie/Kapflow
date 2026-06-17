# EPIC-146 - CAPEX three-project validation

## Summary
Use the three approved ZIP fixture roles for validation planning without importing raw corpora.

This epic was imported from CAPEX v6 on `2026-06-01` as planning backlog only. It does not activate CAPEX runtime behavior by itself.

## Status
Imported as TODO backlog unless an individual task records completed repo evidence. `TASK-0589` is closed with the three-project fixture governance runbook; `TASK-0661` adds the first binding SME-RP fixture-case catalogue while keeping K12 as a fixture tier.

## In scope
- Source task families/counts: SME-RP:1, TP:4.
- Preserve CAPEX v6 source-row intent while translating work into repo-native tasks and context packs.
- Treat K12, K3, and blind validation as fixture tiers under generalized real-project validation.
- Keep official claims inside the canonical workflow/task/approval/event/artifact/pointer substrate.

## Out of scope
- Raw K12, K3, or blind-validation corpus commits.
- Direct production activation or live truth mutation from this planning import.
- Treating generated material, agent output, or Workflow Lab evidence as source authority.

## Dependencies
- EPIC-145

Context pack:
- `codex/context/EPIC-146.md`

## Source references
- `docs/planning/CAPEX_MASTER_V6_INTAKE.md`
- `docs/planning/CAPEX_V6_CONVERSION_MAP.csv`
- `docs/planning/CAPEX_V6_GATE_RISK_DECISION_MAP.csv`
- `docs/planning/capex_real_project_acceptance/SME_RP_ACCEPTANCE_REGISTER.yaml`

## Task stack
- `TASK-0589` (`TP-TASK-001`) - Create three-project fixture governance runbook - DONE 2026-06-17
- `TASK-0590` (`TP-TASK-002`) - Build K12 expected-output manifest from pass11 artifacts
- `TASK-0591` (`TP-TASK-003`) - Build K3 mini-fixture expectation catalog from pass11 artifacts
- `TASK-0597` (`TP-TASK-009`) - Add project-oracle manifest format
- `TASK-0661` (`SME-RP:TASK-0638`) - Promote K12 fixture cases into binding real-project catalogue

## SME-RP real-project acceptance addendum
- `K12-T1..T10` are the first binding fixture-case IDs for real-project validation. They are not top-level gate IDs and do not define the product namespace.
- K12, K3, and blind-validation fixtures remain tiers under general SME-RP validation, with `SME-RP-G010` binding the first K12 case catalogue.
- Future fixture tiers must map to SME-RP gates or later generalized gate families instead of creating K12-specific acceptance namespaces.

## Three-project fixture governance addendum
- `TASK-0589` records `docs/planning/capex_three_project_validation/THREE_PROJECT_FIXTURE_GOVERNANCE_RUNBOOK.md` as planning evidence for `TP-TASK-001`.
- K12, K3, and blind validation raw/full corpora remain off-repo; repo evidence is limited to sanitized fixtures, manifests, hashes, aggregate evidence, and release approvals.
- The runbook maps `TP-G01..TP-G12` but does not pass downstream fixture, oracle, blind baseline, scorecard, capacity, or expected-output gates.

## Acceptance criteria
- Every listed task preserves its v6 source row, acceptance gate, dependency notes, and raw-data boundary.
- Implementation tasks update authoritative repo source before generated derivatives.
- CAPEX remains gated until the relevant acceptance gates and production-preflight evidence are closed or explicitly waived.
