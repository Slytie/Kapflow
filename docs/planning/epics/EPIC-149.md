# EPIC-149 - CAPEX QA, semantic tests, and TDD overlay

## Summary
Add the CAPEX semantic test catalog, quality gates, TDD metrics, and review checkpoints across implementation phases.

This epic was imported from CAPEX v6 on `2026-06-01` as planning backlog only. It does not activate CAPEX runtime behavior by itself.

## Status
Imported as TODO backlog. Implementation must proceed through small reviewed tasks and the normal repo verification loop.

## In scope
- Source task families/counts: ARCH:22, NU:1, QD:44, TEST:3.
- Preserve CAPEX v6 source-row intent while translating work into repo-native tasks and context packs.
- Keep official claims inside the canonical workflow/task/approval/event/artifact/pointer substrate.

## Out of scope
- Raw K12, K3, or blind-validation corpus commits.
- Direct production activation or live truth mutation from this planning import.
- Treating generated material, agent output, or Workflow Lab evidence as source authority.

## Dependencies
- EPIC-080, EPIC-145

Context pack:
- `codex/context/EPIC-149.md`

## Source references
- `docs/planning/CAPEX_MASTER_V6_INTAKE.md`
- `docs/planning/CAPEX_V6_CONVERSION_MAP.csv`
- `docs/planning/CAPEX_V6_GATE_RISK_DECISION_MAP.csv`

## Task stack
- `TASK-0304` (`TEST-001`) - Consolidated acceptance matrix implementation mapping
- `TASK-0305` (`TEST-002`) - No-false-closure negative test suite
- `TASK-0307` (`TEST-004`) - Projection consistency and no-hidden-truth tests
- `TASK-0325` (`QD-001`) - Install conservative PR/task templates
- `TASK-0326` (`QD-002`) - Define review tiers and specialist map
- `TASK-0327` (`QD-003`) - Add code review policy to master docs
- `TASK-0328` (`QD-004`) - Add refactor policy to master docs
- `TASK-0329` (`QD-005`) - Add PR-size and scope check script as advisory
- `TASK-0330` (`QD-006`) - Add architecture boundary forbidden-pattern checks
- `TASK-0331` (`QD-007`) - Create review metrics register
- `TASK-0332` (`QD-008`) - Create phase closeout template
- `TASK-0333` (`QD-P2-A`) - P2 phase preflight quality review
- `TASK-0334` (`QD-P2-B`) - P2 stabilization/refactor pass
- `TASK-0335` (`QD-P2-C`) - P2 phase closeout evidence
- `TASK-0336` (`QD-P3-A`) - P3 phase preflight quality review
- `TASK-0337` (`QD-P3-B`) - P3 stabilization/refactor pass
- `TASK-0338` (`QD-P3-C`) - P3 phase closeout evidence
- `TASK-0339` (`QD-P4-A`) - P4 phase preflight quality review
- `TASK-0340` (`QD-P4-B`) - P4 stabilization/refactor pass
- `TASK-0341` (`QD-P4-C`) - P4 phase closeout evidence
- `TASK-0342` (`QD-P4A-A`) - P4A phase preflight quality review
- `TASK-0343` (`QD-P4A-B`) - P4A stabilization/refactor pass
- `TASK-0344` (`QD-P4A-C`) - P4A phase closeout evidence
- `TASK-0345` (`QD-P5-A`) - P5 phase preflight quality review
- `TASK-0346` (`QD-P5-B`) - P5 stabilization/refactor pass
- `TASK-0347` (`QD-P5-C`) - P5 phase closeout evidence
- `TASK-0348` (`QD-P6-A`) - P6 phase preflight quality review
- `TASK-0349` (`QD-P6-B`) - P6 stabilization/refactor pass
- `TASK-0350` (`QD-P6-C`) - P6 phase closeout evidence
- `TASK-0351` (`QD-P7-A`) - P7 phase preflight quality review
- `TASK-0352` (`QD-P7-B`) - P7 stabilization/refactor pass
- `TASK-0353` (`QD-P7-C`) - P7 phase closeout evidence
- `TASK-0354` (`QD-P8-A`) - P8 phase preflight quality review
- `TASK-0355` (`QD-P8-B`) - P8 stabilization/refactor pass
- `TASK-0356` (`QD-P8-C`) - P8 phase closeout evidence
- `TASK-0357` (`QD-P9-A`) - P9 phase preflight quality review
- `TASK-0358` (`QD-P9-B`) - P9 stabilization/refactor pass
- `TASK-0359` (`QD-P9-C`) - P9 phase closeout evidence
- `TASK-0360` (`QD-P10-A`) - P10 phase preflight quality review
- `TASK-0361` (`QD-P10-B`) - P10 stabilization/refactor pass
- `TASK-0362` (`QD-P10-C`) - P10 phase closeout evidence
- `TASK-0363` (`QD-P11-A`) - P11 phase preflight quality review
- `TASK-0364` (`QD-P11-B`) - P11 stabilization/refactor pass
- `TASK-0365` (`QD-P11-C`) - P11 phase closeout evidence
- `TASK-0366` (`QD-P12-A`) - P12 phase preflight quality review
- `TASK-0367` (`QD-P12-B`) - P12 stabilization/refactor pass
- `TASK-0368` (`QD-P12-C`) - P12 phase closeout evidence
- `TASK-0491` (`ARCH-W75-SLICE-01`) - Define CAPEX invariant test catalog
- `TASK-0492` (`ARCH-W75-SLICE-02`) - Add test suite markers and CI stages
- `TASK-0493` (`ARCH-W75-SLICE-03`) - Create fixture manifest schemas
- `TASK-0494` (`ARCH-W75-SLICE-04`) - Create K12 sanitized scenario slice 0
- `TASK-0495` (`ARCH-W75-SLICE-05`) - Create K12 commitment/assumption scenario tests
- `TASK-0496` (`ARCH-W75-SLICE-06`) - Create K12 no-false-closure scenario tests
- `TASK-0497` (`ARCH-W75-SLICE-07`) - Create K3 mini-fixture design tests
- `TASK-0498` (`ARCH-W75-SLICE-08`) - Create validation-project blind baseline protocol
- `TASK-0499` (`ARCH-W75-SLICE-09`) - Add logistics characterization tests
- `TASK-0500` (`ARCH-W75-SLICE-10`) - Add AI-agent task contract schema
- `TASK-0501` (`ARCH-W75-SLICE-11`) - Build thin agent eval harness
- `TASK-0502` (`ARCH-W75-SLICE-12`) - Add false-closure agent evals
- `TASK-0503` (`ARCH-W75-SLICE-13`) - Add raw-data leak evals
- `TASK-0504` (`ARCH-W75-SLICE-14`) - Add tool-proposal eval tests
- `TASK-0505` (`ARCH-W75-SLICE-15`) - Add workpage stale-command tests
- `TASK-0506` (`ARCH-W75-SLICE-16`) - Add effect-safety crash tests
- `TASK-0507` (`ARCH-W75-SLICE-17`) - Add projection rebuild invariance tests
- `TASK-0508` (`ARCH-W75-SLICE-18`) - Add performance smoke tests
- `TASK-0509` (`ARCH-W75-SLICE-19`) - Add TDD metrics dashboard draft
- `TASK-0510` (`ARCH-W75-SLICE-20`) - Add Lab promotion gate
- `TASK-0511` (`ARCH-W75-SLICE-21`) - Add reviewer test-first checklist
- `TASK-0512` (`ARCH-W75-SLICE-22`) - Add flake quarantine policy
- `TASK-0568` (`NU-CB-P0-008`) - Add CAPEX semantic test suite and CODEOWNERS gates

## Acceptance criteria
- Every listed task preserves its v6 source row, acceptance gate, dependency notes, and raw-data boundary.
- Implementation tasks update authoritative repo source before generated derivatives.
- CAPEX remains gated until the relevant acceptance gates and production-preflight evidence are closed or explicitly waived.
