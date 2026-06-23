# EPIC-141 Context Pack - CAPEX source occurrence and evidence

Purpose:
- Rehydrate the CAPEX v6 task tranche for `EPIC-141` without opening the full master package.
- Keep future work inside the existing one-truth runtime, approval, artifact, pointer, and event model.

## Imported source rows
INGEST-001, INGEST-002, INGEST-003, INGEST-004, INGEST-005, INGEST-006, INGEST-007, INGEST-008, ... plus SME-RP source row `TASK-0629` remapped to repo `TASK-0652` (53 tasks total)

## Historical/reconciled aliases
- `V5-TASK-007` is a reconciled v5 historical alias for `TASK-0564`, `TASK-0428`.

## Closed foundation slice
- `TASK-0564` is closed as of 2026-06-08: runtime state now includes `capex_content_identities` and `capex_source_occurrences`, and `onetruth.capex_platform.source_refs` resolves canonical `source_occurrence:{source_occurrence_id}` refs with meaningful-source-ref checks.
- `TASK-0266` is closed as of 2026-06-17: `docs/planning/capex_source_ingest/BULK_STAGED_CORPUS_INGEST_ARCHITECTURE.yaml` and `onetruth.capex_platform.staged_corpus_ingest` record the staged-ingest architecture and sanitized descriptor guardrails.
- `TASK-0267` is closed as of 2026-06-17: `docs/planning/capex_source_ingest/SOURCE_INVENTORY_PIPELINE_CONTRACT.yaml` and `onetruth.capex_platform.source_inventory` record deterministic content identity, digest-store, and dedupe-group evidence from sanitized staged descriptors.
- `TASK-0268` is closed as of 2026-06-17: `docs/planning/capex_source_ingest/SOURCE_OCCURRENCE_REGISTER_CONTRACT.yaml` and `onetruth.capex_platform.source_occurrence_register` record project-scoped occurrence rows and deterministic `capex.source_occurrence_register.v1` output from sanitized contexts.
- `TASK-0269` is closed as of 2026-06-17: `docs/planning/capex_source_ingest/ROLE_PACKET_REGISTER_CONTRACT.yaml` and `onetruth.capex_platform.role_packet_register` record deterministic role assignment and packet register payloads from sanitized SourceOccurrence refs.
- `TASK-0270` is closed as of 2026-06-17: `docs/planning/capex_source_ingest/DOCUMENT_MANIFEST_CONTRACT.yaml` and `onetruth.capex_platform.document_manifest` record deterministic `capex.document_manifest.v1` and `capex.extraction_state_register.v1` payloads from sanitized source-inventory rows.
- `TASK-0271` is closed as of 2026-06-23: `docs/planning/capex_source_ingest/TEXT_EXTRACTION_PAGE_MANIFEST_CONTRACT.yaml` and `onetruth.capex_platform.text_extraction_page_manifest` record deterministic `capex.document_text_extract.v1` and `capex.document_page_manifest.v1` payloads from sanitized document-manifest basis rows.
- This does not close parser adapters, extraction/OCR runtime, async jobs, chunk/search/evidence-binding indexes, source occurrence relations, source locator unions, upload behavior, or reviewed evidence sufficiency.

## SME-RP addendum rows
- `TASK-0652` is closed with the planning-only source occurrence context and trust taxonomy contract for `SME-RP-G004`.
- Preserve source occurrence context and evidence trust distinctions without converting imported K12 fixture rows into product namespaces.

## Load first
- `docs/planning/epics/EPIC-141.md`
- `docs/planning/CAPEX_MASTER_V6_INTAKE.md`
- `docs/planning/CAPEX_V6_CONVERSION_MAP.csv`
- `docs/planning/capex_real_project_acceptance/SME_RP_ACCEPTANCE_REGISTER.yaml`
- `docs/architecture/invariants.md`
- `docs/status/CURRENT_FOCUS.md`

## Non-negotiable invariants
- One truth system: official claims come only from immutable objects, append-only events, and audited pointers.
- Tenant, domain, and future CAPEX project boundaries must not be crossed in reads, writes, exports, projections, or generated material.
- Raw K12/K3/blind corpus files stay off-repo; only sanitized fixtures, manifests, hashes, and aggregate evidence may be committed.
- Generated artifacts, Workflow Lab reports, and AI output are not source authority.
- Production/lab activation is release-mediated and remains blocked until the relevant gates close or receive explicit waivers.

## Preferred implementation posture
- Start with the source task's required tests or evidence.
- Update repo-native authoritative source before downstream generated artifacts.
- Keep implementation PRs small enough to review against the source row and acceptance gate.
- Preserve logistics weekly/live current focus unless a CAPEX task explicitly changes shared semantics.

## Stop line
- Do not import raw project corpus content.
- Do not activate CAPEX runtime/product behavior merely because a planning task exists.
