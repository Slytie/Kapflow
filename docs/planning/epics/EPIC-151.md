# EPIC-151 - CAPEX transparency and snapshots

## Summary
Define executive snapshots, risk signals, external bindings, freshness, and audit export contracts.

This epic was imported from CAPEX v6 on `2026-06-01` as planning backlog only. It does not activate CAPEX runtime behavior by itself.

## Status
Imported as TODO backlog unless an individual task records completed repo evidence.
`TASK-0569` is closed as of 2026-06-09 with the internal CAPEX interface-burden conservation policy helper, architecture doc, and tests.
`TASK-0659` and `TASK-0663` add SME-RP procurement/escalation and external-system taxonomy obligations for executive transparency and observation boundaries.

## In scope
- Source task families/counts: ARCH:24, ART:1, NU:1, SME-RP:2, WFLOW:1.
- Preserve CAPEX v6 source-row intent while translating work into repo-native tasks and context packs.
- Define procurement, escalation, and external-system observation rules for executive transparency.
- Keep official claims inside the canonical workflow/task/approval/event/artifact/pointer substrate.

## Out of scope
- Raw K12, K3, or blind-validation corpus commits.
- Direct production activation or live truth mutation from this planning import.
- Treating generated material, agent output, or Workflow Lab evidence as source authority.

## Dependencies
- EPIC-142, EPIC-144

Context pack:
- `codex/context/EPIC-151.md`

## Source references
- `docs/planning/CAPEX_MASTER_V6_INTAKE.md`
- `docs/planning/CAPEX_V6_CONVERSION_MAP.csv`
- `docs/planning/CAPEX_V6_GATE_RISK_DECISION_MAP.csv`
- `docs/planning/capex_real_project_acceptance/SME_RP_ACCEPTANCE_REGISTER.yaml`

## Task stack
- `TASK-0277` (`ART-002`) - Add ceo_transparency_snapshot schema and decision
- `TASK-0290` (`WFLOW-008`) - Risk and CEO Transparency workflow
- `TASK-0537` (`ARCH-W8-S01`) - Define reviewed_state_graph contract
- `TASK-0538` (`ARCH-W8-S02`) - Implement SnapshotBuildRun skeleton
- `TASK-0539` (`ARCH-W8-S03`) - Add RiskSignal contract
- `TASK-0540` (`ARCH-W8-S04`) - Add ceo_transparency_snapshot schema
- `TASK-0541` (`ARCH-W8-S05`) - Add ProjectCorpusDocument/Blob/Version design
- `TASK-0542` (`ARCH-W8-S06`) - Add metadata type/value contract
- `TASK-0543` (`ARCH-W8-S07`) - Define packet requirement/member/evaluation schema
- `TASK-0544` (`ARCH-W8-S08`) - Define ArtifactPointerPromotion service contract
- `TASK-0545` (`ARCH-W8-S09`) - Add hold/freeze minimal blocker model
- `TASK-0546` (`ARCH-W8-S10`) - Add AuditExportArtifact contract
- `TASK-0547` (`ARCH-W8-S11`) - Add ExternalSystem schema
- `TASK-0548` (`ARCH-W8-S12`) - Add ExternalProjectBinding schema
- `TASK-0549` (`ARCH-W8-S13`) - Add ExternalObjectPointer schema
- `TASK-0550` (`ARCH-W8-S14`) - Add ExternalObjectSnapshot / SyncObservation
- `TASK-0551` (`ARCH-W8-S15`) - Rename/constrain expenditure ledger
- `TASK-0552` (`ARCH-W8-S16`) - Add raw-file/AI/external-status exclusion tests
- `TASK-0553` (`ARCH-W8-S17`) - Add dossier/promotion negative tests
- `TASK-0554` (`ARCH-W8-S18`) - Add ERP/DMS boundary failure tests
- `TASK-0555` (`ARCH-W8-S19`) - Add snapshot freshness to executive views
- `TASK-0556` (`ARCH-W8-S20`) - Add external observation review queue
- `TASK-0557` (`ARCH-W8-S21`) - Add K12/K3/validation fixture expected outputs
- `TASK-0558` (`ARCH-W8-S22`) - Update architecture docs with W8 terms
- `TASK-0559` (`ARCH-W8-S23`) - Add W8 feature gate/migration lane entries
- `TASK-0560` (`ARCH-W8-S24`) - Run Waves 1-8 formalism regression
- `TASK-0569` (`NU-CB-P1-009`) - Add interface-burden conservation policy and tests
- `TASK-0659` (`SME-RP:TASK-0636`) - Define procurement fields and executive escalation thresholds
- `TASK-0663` (`SME-RP:TASK-0640`) - Define external system mode taxonomy

## SME-RP real-project acceptance addendum
- Procurement fields, executive escalation thresholds, and external-system mode taxonomy are executive transparency and external observation requirements.
- `SME-RP-G006` and `SME-RP-G007` require procurement delay, commitment, and escalation signals to appear as reviewed internal state before they affect executive snapshots.
- `SME-RP-G011` requires external systems to be classified as source mirror, observed system, integration target, external authority, or advisory feed; external status alone never sets official CAPEX status.

## Acceptance criteria
- Every listed task preserves its v6 source row, acceptance gate, dependency notes, and raw-data boundary.
- Implementation tasks update authoritative repo source before generated derivatives.
- CAPEX remains gated until the relevant acceptance gates and production-preflight evidence are closed or explicitly waived.
