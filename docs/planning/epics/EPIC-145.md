# EPIC-145 - CAPEX real-project fixture governance

## Summary
Govern real-project fixture roles, quarantine, redaction, expected outputs, and release checks without raw corpus commits. K12, K3, and blind-validation labels remain valid where they identify fixture tiers, imported source rows, or raw-data safety boundaries.

This epic was imported from CAPEX v6 on `2026-06-01` as planning backlog only. It does not activate CAPEX runtime behavior by itself.

## Status
Imported as TODO backlog unless an individual task records completed repo evidence.

## In scope
- Source task families/counts: ARCH:22, K12:4, RF:1, SAFE:2, SPB2:7.
- Preserve CAPEX v6 source-row intent while translating work into repo-native tasks and context packs.
- Preserve K12/K3/blind labels where they identify fixture source rows, fixture roles, or raw-data boundaries, while using SME-RP for new real-project acceptance gates.
- Keep official claims inside the canonical workflow/task/approval/event/artifact/pointer substrate.

## Out of scope
- Raw K12, K3, or blind-validation corpus commits.
- Direct production activation or live truth mutation from this planning import.
- Treating generated material, agent output, or Workflow Lab evidence as source authority.

## Dependencies
- EPIC-141

Context pack:
- `codex/context/EPIC-145.md`

## Source references
- `docs/planning/CAPEX_MASTER_V6_INTAKE.md`
- `docs/planning/CAPEX_V6_CONVERSION_MAP.csv`
- `docs/planning/CAPEX_V6_GATE_RISK_DECISION_MAP.csv`
- `docs/planning/capex_real_project_acceptance/SME_RP_ACCEPTANCE_REGISTER.yaml`

## Task stack
- `TASK-0300` (`K12-001`) - Raw K12 quarantine and sensitivity manifest
- `TASK-0301` (`K12-002`) - Sanitized K12 fixture extraction
- `TASK-0302` (`K12-003`) - K12 expected-output manifest
- `TASK-0303` (`K12-004`) - K12 mid-project import demo script
- `TASK-0313` (`SAFE-001`) - Safety Pass A: raw K12 verification and sanitization QA
- `TASK-0315` (`SPB2-T001`) - Generalize fixture governance from K12-only to all real project corpora
- `TASK-0316` (`SPB2-T002`) - Implement source triage state model
- `TASK-0317` (`SPB2-T003`) - Add split/nested archive handling with provenance
- `TASK-0318` (`SPB2-T004`) - Add shortcut reference policy
- `TASK-0319` (`SPB2-T005`) - Reserve K3 authority/lifecycle module contracts
- `TASK-0320` (`SPB2-T006`) - Create K3 shadow-regression plan
- `TASK-0321` (`SPB2-T007`) - Add K3 negative guardrail tests
- `TASK-0322` (`SAFE-B3-001`) - Run post-research formalism regression before adopting external architecture patterns
- `TASK-0378` (`RF-010`) - Fixture quarantine utility
- `TASK-0469` (`ARCH-W6-SLICE-001`) - Add fixture compiler architecture CED and schema skeletons
- `TASK-0470` (`ARCH-W6-SLICE-002`) - Define capex.sensitivity_manifest.v1 schema
- `TASK-0471` (`ARCH-W6-SLICE-003`) - Define capex.redaction_manifest.v1 schema
- `TASK-0472` (`ARCH-W6-SLICE-004`) - Define approved redaction operator registry
- `TASK-0473` (`ARCH-W6-SLICE-005`) - Define fixture_generation_run and expected_output_manifest schemas
- `TASK-0474` (`ARCH-W6-SLICE-006`) - Define leak_scan_report and fixture_release_manifest schemas
- `TASK-0475` (`ARCH-W6-SLICE-007`) - Implement leak-scan wrapper contract, no scanner engine yet
- `TASK-0476` (`ARCH-W6-SLICE-008`) - Create K12 fixture release gate checklist
- `TASK-0477` (`ARCH-W6-SLICE-009`) - Define UntrustedDocumentRailBundle schema
- `TASK-0478` (`ARCH-W6-SLICE-010`) - Define RailVerdict and SecurityRailRejection schemas
- `TASK-0479` (`ARCH-W6-SLICE-011`) - Implement mandatory rail bundle validator
- `TASK-0480` (`ARCH-W6-SLICE-012`) - Define ToolProposal schema and state machine
- `TASK-0481` (`ARCH-W6-SLICE-013`) - Define ToolExecutionCommand guard
- `TASK-0482` (`ARCH-W6-SLICE-014`) - Define static action registry interface
- `TASK-0483` (`ARCH-W6-SLICE-015`) - Define ToolResultIngestPolicy
- `TASK-0484` (`ARCH-W6-SLICE-016`) - Add AI draft artifact status model
- `TASK-0485` (`ARCH-W6-SLICE-017`) - Add content-safe telemetry policy
- `TASK-0486` (`ARCH-W6-SLICE-018`) - Add no raw prompt/completion in normal traces tests
- `TASK-0487` (`ARCH-W6-SLICE-019`) - Add stream buffering rule for sensitive workflows
- `TASK-0488` (`ARCH-W6-SLICE-020`) - Add expected-output no-raw-excerpt test pattern
- `TASK-0489` (`ARCH-W6-SLICE-021`) - Update workpage family catalog for fixture release and AI draft review
- `TASK-0490` (`ARCH-W6-SLICE-022`) - Prepare Wave 6 master patch instructions

## SME-RP real-project acceptance addendum
- EPIC-145 is the fixture-governance home for real-project validation material. Existing K12/K3 task rows remain intact because they are source-row and fixture-tier identifiers.
- New acceptance gates for real-project subject-matter validation must use `SME-RP`, not a K12-specific namespace.
- Raw K12, K3, and blind-validation corpora remain out of repo unless a later source-freeze and redaction release path explicitly authorizes sanitized derivatives.

## Acceptance criteria
- Every listed task preserves its v6 source row, acceptance gate, dependency notes, and raw-data boundary.
- Implementation tasks update authoritative repo source before generated derivatives.
- CAPEX remains gated until the relevant acceptance gates and production-preflight evidence are closed or explicitly waived.
