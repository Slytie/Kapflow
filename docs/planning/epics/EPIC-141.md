# EPIC-141 - CAPEX source occurrence and evidence

## Summary
Build the content identity, source occurrence, extraction, and evidence-binding foundations.

This epic was imported from CAPEX v6 on `2026-06-01` as planning backlog only. It does not activate CAPEX runtime behavior by itself.

## Status
Imported as TODO backlog unless an individual task records completed repo evidence. `TASK-0564` is closed as of 2026-06-08 with physical source occurrence/runtime resolver evidence, and `TASK-0652` is closed with the SME-RP source occurrence context and trust contract. Broader corpus ingest, extraction, evidence binding, and source occurrence relation work remain open.

## In scope
- Source task families/counts: ARCH:38, INGEST:9, NU:1, RF:3, SME-RP:1, V5:1.
- Preserve CAPEX v6 source-row intent while translating work into repo-native tasks and context packs.
- Define generalized occurrence context and evidence-source trust taxonomy rules.
- Keep official claims inside the canonical workflow/task/approval/event/artifact/pointer substrate.

## Out of scope
- Raw K12, K3, or blind-validation corpus commits.
- Direct production activation or live truth mutation from this planning import.
- Treating generated material, agent output, or Workflow Lab evidence as source authority.

## Dependencies
- EPIC-140

Context pack:
- `codex/context/EPIC-141.md`

## Source references
- `docs/planning/CAPEX_MASTER_V6_INTAKE.md`
- `docs/planning/CAPEX_V6_CONVERSION_MAP.csv`
- `docs/planning/CAPEX_V6_GATE_RISK_DECISION_MAP.csv`
- `docs/planning/capex_real_project_acceptance/SME_RP_ACCEPTANCE_REGISTER.yaml`

## Task stack
- `TASK-0266` (`INGEST-001`) - Design bulk/staged corpus ingest architecture
- `TASK-0267` (`INGEST-002`) - Implement digest, dedupe and source inventory pipeline
- `TASK-0268` (`INGEST-003`) - Implement source occurrence register
- `TASK-0269` (`INGEST-004`) - Implement role assignment and packet register artifacts
- `TASK-0270` (`INGEST-005`) - Document manifest and extraction-state artifact
- `TASK-0271` (`INGEST-006`) - Text extraction and page manifest contracts
- `TASK-0272` (`INGEST-007`) - Chunk/search/evidence-binding index
- `TASK-0273` (`INGEST-008`) - Batch artifact link/provenance hydration
- `TASK-0274` (`INGEST-009`) - Async job runtime for document processing
- `TASK-0372` (`RF-004`) - Artifact list pagination adapter
- `TASK-0373` (`RF-005`) - Batch relation hydration
- `TASK-0374` (`RF-006`) - Bulk ingest adapter seam
- `TASK-0391` (`ARCH-W2-S01`) - Create content_identity and capex_source_occurrence runtime schema
- `TASK-0392` (`ARCH-W2-S02`) - Add source_occurrence_relation with duplicate/archive/derivative/redaction relation types
- `TASK-0393` (`ARCH-W2-S03`) - Add ingest_batch, ingest_job, ingest_attempt, ingest_job_log state model
- `TASK-0394` (`ARCH-W2-S04`) - Add archive lineage support and nested-archive extraction metadata contract
- `TASK-0395` (`ARCH-W2-S05`) - Add manifest_generation attestation model for generated corpus registers
- `TASK-0396` (`ARCH-W2-S06`) - Implement CommandReceipt canonical input hash and corrupted-idempotency rejection
- `TASK-0397` (`ARCH-W2-S07`) - Implement EffectLedger and guarded mutation helper
- `TASK-0398` (`ARCH-W2-S08`) - Split ToolExecution from ToolExecutionAttempt with lease-token stale completion rejection
- `TASK-0399` (`ARCH-W2-S09`) - Add ProjectConcurrencyPolicy and ProjectRuntimeSlot minimal implementation
- `TASK-0400` (`ARCH-W2-S10`) - Add RuntimeOutbox after-commit dispatch scaffold
- `TASK-0401` (`ARCH-W2-S11`) - Define ArtifactVersionIdentityContract and add identity fields
- `TASK-0402` (`ARCH-W2-S12`) - Harden ArtifactProvenanceEdge as runtime-computed immutable typed edge
- `TASK-0403` (`ARCH-W2-S13`) - Define ArtifactPointerEvent and PointerFamilyPolicy minimal schema
- `TASK-0404` (`ARCH-W2-S14`) - Implement PointerPromotionService guarded transaction
- `TASK-0405` (`ARCH-W2-S15`) - Define SubmittedGeneratedArtifact and RuntimeGeneratedArtifactView schemas
- `TASK-0406` (`ARCH-W2-S16`) - Implement ValidationRun / ValidationItem vector contract
- `TASK-0407` (`ARCH-W2-S17`) - Implement sourceRef resolver and edge-emission contract
- `TASK-0408` (`ARCH-W2-S18`) - Add canonicalization profile and hash test vectors
- `TASK-0409` (`ARCH-W2-S19`) - Create Wave 2 crash/stale-basis test suite
- `TASK-0410` (`ARCH-W2-S20`) - Wave 2 docs/catalog/refactor closeout
- `TASK-0411` (`ARCH-W3-S001`) - Design extraction_run physical schema
- `TASK-0412` (`ARCH-W3-S002`) - Implement parser_config_hash helper
- `TASK-0413` (`ARCH-W3-S003`) - Extraction state machine
- `TASK-0414` (`ARCH-W3-S004`) - Extraction asset bundle manifest
- `TASK-0415` (`ARCH-W3-S005`) - Source occurrence locator union
- `TASK-0416` (`ARCH-W3-S006`) - Source occurrence resolver adapter
- `TASK-0417` (`ARCH-W3-S007`) - Chunk projection generation schema
- `TASK-0418` (`ARCH-W3-S008`) - Search projection generation schema
- `TASK-0419` (`ARCH-W3-S009`) - Retrieval candidate persistence
- `TASK-0420` (`ARCH-W3-S010`) - Evidence binding schema/status model
- `TASK-0421` (`ARCH-W3-S011`) - Evidence review task command
- `TASK-0422` (`ARCH-W3-S012`) - Partial extraction policy gate
- `TASK-0423` (`ARCH-W3-S013`) - Fuzzy grounding candidate gate
- `TASK-0424` (`ARCH-W3-S014`) - Projection rebuild invariance test suite
- `TASK-0425` (`ARCH-W3-S015`) - Evidence side-panel projection contract
- `TASK-0426` (`ARCH-W3-S016`) - Sanitized fixture evidence-lineage enforcement
- `TASK-0427` (`ARCH-W3-S017`) - Extraction QA report artifact
- `TASK-0428` (`ARCH-W3-S018`) - SourceRef resolution validation vector
- `TASK-0564` (`NU-CB-P0-004`) - Add physical source_occurrence and sourceRef resolver - DONE 2026-06-08
- `TASK-0652` (`SME-RP:TASK-0629`) - DONE - Add occurrence context profile and source trust taxonomy

## Historical/reconciled aliases
- `TASK-0578` (`V5-TASK-007`) -> `TASK-0564`, `TASK-0428` - Add SourceRef resolution contract/tests

## SME-RP real-project acceptance addendum
- Source occurrence context and trust taxonomy are general evidence-source rules, not K12-specific row logic.
- `TASK-0652` records source occurrence context as observed source truth, not reviewed project truth, with exact origin and trust modes for later implementation.
- `SME-RP-G004` binds evidence trust to officialness checks: raw files, external statuses, AI drafts, and generated artifacts cannot become official claims without canonical artifact, event, pointer, and review evidence.

## Acceptance criteria
- Every listed task preserves its v6 source row, acceptance gate, dependency notes, and raw-data boundary.
- Implementation tasks update authoritative repo source before generated derivatives.
- CAPEX remains gated until the relevant acceptance gates and production-preflight evidence are closed or explicitly waived.
