# DECISIONS_SINCE_LAST.md

Record any decisions made since the last session so a fresh Codex run can rehydrate quickly.

## 2026-06-23 (EPIC-141/143 async-job and project-snapshot closeout)
- Async job decision: `TASK-0274` records a planning-only async document-processing job runtime contract/helper with deterministic `capex.document_processing_job_register.v1`, `capex.document_processing_job_attempt_register.v1`, and `capex.document_processing_job_progress.v1` outputs from sanitized document-manifest basis rows.
- Runtime-boundary decision: the async job helper models retry, resume, cancel, progress, command receipt, execution-session refs, deterministic idempotency, and no-duplicate planned task/artifact refs without creating durable ingest job tables, queue workers, parser/OCR runtime, extraction execution, migrations, event-registry changes, or public surfaces.
- Project-snapshot decision: `TASK-0289` records a planning-only Project State Snapshot workflow contract/helper with deterministic `project_state_snapshot`, `project_closure_vector`, and `project_state_snapshot_flags` outputs from Corpus Baseline, Lifecycle Stage State, Governance / Commitment Chain, Assumption Closure, Owner Interface Resolution, and sanitized pointer observations.
- Closure-boundary decision: project-state snapshot rows summarize reviewed planning state only. Missing evidence, conflicts, AI-draft-only states, stale/missing pointers, and waivers block or qualify closure readiness; the helper creates no closure snapshot, official project state, reviewed baseline, pointer promotion, or evidence sufficiency claim.
- Dependency decision: `TASK-0274` closes the final imported `INGEST-*` planning tranche row. `TASK-0289` closes the current WFLOW P0 chain prerequisite for later risk/CEO transparency work, while `TASK-0277` remains a separate EPIC-151 blocker for `TASK-0290`.
- Activation decision: this closeout adds helper/contract/test evidence only. It adds no raw corpus import, parser/OCR/search runtime, vector store, durable ingest-job schema, public route, frontend route, authored workflow activation, physical closure snapshot, official pointer creation, production approval, or CAPEX runtime/product activation.

## 2026-06-23 (EPIC-141/143 batch-hydration and lifecycle-navigation closeout)
- Batch hydration decision: `TASK-0273` records bounded artifact page and batch link/provenance hydration evidence through `onetruth.infrastructure.repositories.artifact_relation_hydration`, query-count tests, and a 5k synthetic artifact coverage case. Existing route/read payload shapes are preserved while relation loading no longer loops per artifact for the covered surfaces.
- Query-shape decision: CAPEX artifact page hydration is bounded by page size and chunked relation loading. The task relies on existing artifact/version, link, and provenance indexes and adds no migration, event-registry entry, public route, frontend route, search runtime, vector store, or CAPEX activation.
- Lifecycle-navigation decision: `TASK-0285` records a planning-only Lifecycle Stage State workflow contract/helper with deterministic `lifecycle_stage_state`, `stage_readiness_matrix`, and `lifecycle_navigation_flags` outputs from Corpus Baseline SourceRefs and sanitized stage observations.
- Navigation-boundary decision: lifecycle stage state is derived navigation only, not official project truth or waterfall gate authority. Ready stages require evidence, missing evidence fails open, conflicting evidence flags the stage, and AI drafts cannot set lifecycle readiness.
- Dependency decision: `TASK-0274` is now the next EPIC-141 ingest/runtime task, and `TASK-0289` is unblocked as the next EPIC-143 P0 Project State Snapshot task because `TASK-0285`, `TASK-0286`, `TASK-0287`, and `TASK-0288` are closed.
- Activation decision: this closeout adds helper/contract/test evidence only for CAPEX workflow/navigation behavior and bounded relation hydration. It adds no raw corpus import, parser/OCR runtime, async processing runtime, authored workflow pack, workpage, public route, frontend route, closure snapshot, reviewed baseline creation, official pointer creation, production approval, or CAPEX runtime/product activation.

## 2026-06-23 (EPIC-141/143 chunk-index and owner-interface closeout)
- Chunk/index decision: `TASK-0272` records deterministic `capex.document_chunk_index.v1`, `capex.document_search_index.v1`, and `capex.evidence_binding_index.v1` planning outputs from sanitized text/page manifest basis rows. Chunk/search/evidence outputs are represented by storage refs, digests, parser hashes, spans, SourceRefs, generated-row refs, and metadata rather than inline raw text.
- Runtime-boundary decision: chunk/search outputs are projection/index artifact evidence only. Search service latency proof, vector store activation, retrieval runtime, evidence review runtime, reviewed evidence sufficiency, parser/OCR runtime, async jobs, and production index storage remain later work.
- Owner-interface decision: `TASK-0288` records a planning-only Owner Interface Resolution workflow contract/helper with deterministic `distributed_requirement_register`, `interface_register`, and `owner_interface_flags` outputs from sanitized interface observations, Corpus Baseline refs, and Assumption Closure basis.
- Responsibility-boundary decision: resolved interfaces require evidence; missing responsibility, missing evidence, conflicting responsibility, AI-draft-only resolution, and waiver-only resolution remain non-authoritative flagged states. Responsibility cannot disappear, AI drafts cannot resolve responsibility, and waivers do not assign responsibility.
- Dependency decision: `TASK-0273` is now the next EPIC-141 ingest task. `TASK-0289` remains blocked by `TASK-0285`, because lifecycle navigation is still the remaining EPIC-143 prerequisite for project-state snapshot synthesis.
- Activation decision: this closeout adds helper/contract/test evidence only. It adds no raw corpus import, search runtime, vector store, retrieval runtime, evidence-review runtime, public route, frontend route, authored workflow activation, responsibility assignment authority, physical closure snapshots, reviewed baseline creation, official pointer creation, production approval, or CAPEX runtime/product activation.

## 2026-06-23 (EPIC-141/143 text-page and assumption-closure closeout)
- Text/page decision: `TASK-0271` records deterministic `capex.document_text_extract.v1` and `capex.document_page_manifest.v1` planning outputs from sanitized document-manifest basis rows. Text output is represented by storage refs, digests, parser hashes, spans, page numbers, OCR status, and SourceRefs rather than inline raw text.
- Raw-data decision: text/page manifest inputs reject raw absolute paths, raw filenames, inline/base64 content, raw text fields, raw OCR text, and unrestricted source excerpts. Parser adapters, OCR runtime, async extraction jobs, chunk/search indexes, evidence binding, upload behavior, and reviewed evidence sufficiency remain later work.
- Assumption-closure decision: `TASK-0287` records a planning-only Assumption Closure workflow contract/helper with deterministic `counterparty_assumption_register`, `assumption_closure_matrix`, and `assumption_flags` outputs from sanitized assumption observations, Corpus Baseline refs, and Governance / Commitment Chain basis.
- Closure-boundary decision: supported evidence can close an assumption as `pass`, waiver can only record `satisfied_by_waiver`, missing evidence fails open, contradicted evidence blocks closure, and AI drafts cannot close assumptions. These outputs do not create physical closure snapshots or official pointer truth.
- Dependency decision: `TASK-0272` is now the next EPIC-141 chunk/search/evidence-binding task, and `TASK-0288` is unblocked as the next EPIC-143 owner-interface workflow task. `TASK-0285` remains TODO as lower-priority lifecycle navigation state.
- Activation decision: this closeout adds helper/contract/test evidence only. It adds no raw corpus import, parser/OCR runtime, extraction jobs, public route, frontend route, authored workflow activation, physical closure snapshots, stale/reopen policy, reviewed baseline creation, official pointer creation, production approval, or CAPEX runtime/product activation.

## 2026-06-17 (EPIC-141/143 document-manifest and commitment-chain closeout)
- Document-manifest decision: `TASK-0270` records deterministic `capex.document_manifest.v1` and `capex.extraction_state_register.v1` payloads from sanitized source-inventory rows. It tracks sanitized storage refs, content identity, MIME/media type, byte size, extraction status, progress, retry/failure metadata, and recovery posture without starting extraction jobs.
- Raw-data decision: document-manifest inputs reject raw absolute paths, raw filenames, inline/base64 content, raw logs, unrestricted source excerpts, and sensitive failure text. Text extraction, page manifests, chunk/search indexes, evidence binding, upload behavior, and reviewed evidence sufficiency remain later work.
- Commitment-chain decision: `TASK-0286` records a planning-only Governance / Commitment Chain workflow contract/helper with deterministic `commitment_chain`, `expenditure_ledger`, and `commitment_flags` outputs from sanitized commitment observations and Corpus Baseline refs.
- Boundary decision: order revisions preserve prior revision history, settlement rows cannot close technical/RCA findings, and commercial commitments, technical assumptions, and responsibility shifts stay distinct. External/internal officialness is reviewed metadata only, not pointer truth or approval mutation.
- Dependency decision: `TASK-0271` is now the next EPIC-141 extraction/page-manifest task, and `TASK-0287` is unblocked as the next EPIC-143 assumption-closure workflow task. `TASK-0285` remains TODO as lower-priority lifecycle navigation state.
- Activation decision: this closeout adds helper/contract/test evidence only. It adds no raw corpus import, extraction runtime, parser adapter, upload endpoint, public route, frontend route, authored workflow activation, reviewed baseline creation, approval mutation, official pointer creation, technical RCA closure, production approval, or CAPEX runtime/product activation.

## 2026-06-17 (EPIC-141/143 role-packet and corpus-baseline closeout)
- Role/packet decision: `TASK-0269` records deterministic `capex.role_assignment_register.v1` and `capex.packet_register.v1` payloads from sanitized SourceOccurrence refs. AI suggestions are draft-only, role is not file identity, packet grouping is not reviewed baseline truth, and split/merge packet states remain review metadata.
- Corpus-baseline decision: `TASK-0284` records a planning-only Corpus Baseline workflow contract/helper that composes source inventory, source occurrence register, role register, packet register, generated-artifact validator output, and handoff-manifest refs into deterministic workflow outputs.
- Dependency decision: `TASK-0284` no longer waits on `TASK-0269`; `TASK-0285` is now the next EPIC-143 workflow task. `TASK-0279` meaningful SourceRef/evidence policy remains separate EPIC-142 work.
- Activation decision: this closeout adds helper/contract/test evidence only. It adds no raw corpus import, public route, frontend route, authored workflow activation, reviewed baseline creation, official pointer creation, evidence-sufficiency approval, production approval, or CAPEX runtime/product activation.

## 2026-06-17 (EPIC-141/143 source inventory and intake-router closeout)
- Staged-ingest decision: `TASK-0266` records manifest-first bulk/staged corpus ingest architecture with object, folder, and source-root descriptor modes plus body-limit/idempotency guardrails; the helper validates sanitized descriptors only and has no upload, artifact, SourceOccurrence, pointer, route, or activation side effects.
- Generated-envelope decision: `TASK-0276` records `capex.generated_artifact_envelope.v1`, canonical `capex.<family>.<artifact>.vN.json` naming, and a CAPEX wrapper over the existing generated-artifact helper. Meaningful SourceRef/evidence sufficiency remains `TASK-0279`, and bundle validators remain `TASK-0278`.
- Source-inventory decision: `TASK-0267` records deterministic `capex.source_inventory.v1` payloads, scoped `capex_content_identities` upsert, and digest dedupe groups from sanitized staged descriptors. It does not create SourceOccurrence rows; `TASK-0268` remains the source occurrence binding step.
- Envelope-boundary decision: `capex.source_inventory` may use an empty `source_refs` array only with validation result `inventory_pre_source_occurrence`; other CAPEX generated artifacts still require `source_occurrence:` refs until later policy work tightens meaningful evidence requirements.
- Intake-router decision: `TASK-0283` records a planning-only Project Intake Router contract/helper for new-project, mid-project, issue-escalation, and CEO/sponsor entry modes. Human confirmation is required, AI output is draft-only, and mid-project K12 coverage uses sanitized fixture-tier refs only.
- Activation decision: this closeout adds internal helper/schema/contract/test evidence only. It adds no raw corpus import, upload endpoint, source occurrence binding, workflow pack activation, public API/frontend route, Project Intake workpage, official pointer creation, module activation approval, production approval, or CAPEX runtime/product activation.

## 2026-06-17 (EPIC-141/142 source occurrence and validator closeout)
- Source-occurrence-register decision: `TASK-0268` records deterministic `capex.source_occurrence_register.v1` payloads and creates project-scoped source occurrence rows from sanitized source inventory plus sanitized context descriptors. Content identity, occurrence identity, and future role/packet assignment remain distinct.
- Locator-privacy decision: source occurrence register inputs reject raw absolute paths, raw filenames, inline/base64 content, unrestricted locator text, and raw corpus material. Locator metadata is sanitized context only.
- Generated-validator decision: `TASK-0278` records schema, canonical-name, canonical-digest, and bundle cross-reference validators for CAPEX generated artifacts. It rejects missing SourceRefs, stale input digests, duplicate canonical names, artifact-kind/name mismatches, deprecated names, and empty SourceRefs outside the narrow source-inventory exception.
- Promotion-boundary decision: schema-valid or bundle-valid generated artifacts are not evidence-sufficient or promotable. Meaningful SourceRef/evidence policy remains `TASK-0279`, and pointer promotion policy remains `TASK-0280`.
- Activation decision: this closeout adds internal helper/validator/contract/test evidence only. It adds no raw corpus import, public route, frontend route, authored workflow activation, reviewed baseline creation, official pointer creation, production approval, or CAPEX runtime/product activation.

## 2026-06-17 (EPIC-136 delivery-governance closeout)
- Product-goal decision: `TASK-0582` records the CAPEX Product Goal and guarded metric stack as repo planning-governance evidence under `docs/planning/capex_delivery/`.
- Metric decision: CAPEX delivery metrics must cover outcome, learning, flow, quality, and operability, and no metric may reward velocity alone without a truth, quality, safety, or operability guardrail.
- Slice-ladder decision: `TASK-0583` records `VS-00` through `VS-05` as the first vertical-slice ladder with entry/exit gates, metric refs, repo evidence refs, and planning-only activation posture.
- Dependency decision: `TASK-0584` records the dependency register and risk-based milestone overlay with owner, needed-by milestone, mitigation, risk-if-late, valid status, and planning-only posture.
- Backlog decision: `TASK-0585` records one authoritative backlog hierarchy, product goal -> outcome epic -> feature -> vertical slice -> story -> Given-When-Then acceptance scenario, plus templates that require metrics, slice refs, source/evidence refs, acceptance scenarios, non-activation posture, and rollback or recovery notes.
- Cadence decision: `TASK-0586` records weekly refinement, three-amigos, monthly dependency/risk review, demo/review, and 8-12 week outcome roadmap refresh as a lightweight cadence with explicit inputs, outputs, owners, and decision records.
- Overlay decision: `TASK-0587` records a first-90-days execution overlay using relative windows for goal/metrics, dependency board, CI baseline, first slice demo, first MMF, and roadmap refresh without false date precision.
- DoR/DoD decision: `TASK-0588` records CAPEX Definition of Ready / Done for architecture, runtime, workpage, fixture, agent-lab, and migration/release tasks, and adds a compact CAPEX DoR/DoD consistency checklist to the pull request template.
- Fixture-governance decision: `TASK-0589` records the three-project fixture governance runbook for K12, K3, and blind validation tiers.
- K12 expected-output decision: `TASK-0590` records a sanitized K12 expected-output manifest derived from off-repo pass 9-11 synthesis evidence, with dry-run, pointer, re-review, negative/hardening, gate, and rollback expectations.
- K3 mini-fixture decision: `TASK-0591` records a sanitized K3 expectation catalog derived from off-repo pass 9-11 synthesis evidence, with source identity, artifact role, relation, stale/reopen, pointer-policy, approval-validity, workpage, and schema-freeze expectations.
- Blind-freeze decision: `TASK-0592` records the blind validation freeze protocol for runtime rules, prompts, retrieval recipes, schemas, tool registry, evaluator criteria, access controls, baseline custody, leak scans, and post-blind change classification.
- Scorecard decision: `TASK-0593` records the cross-project invariant scorecard structure across K12, K3 mini/shadow, and blind baseline tiers, with default rollup `blocked_pending_evidence` until score evidence is run or explicitly waived.
- Agent Lab decision: `TASK-0594` records an advisory Agent Lab eval matrix across K12, K3 mini, K3 shadow, and blind baseline tiers; lab output cannot directly create official pointers, approval responses, closure snapshots, runtime truth mutations, fixture release approval, public activation, or product activation.
- Off-repo runbook decision: `TASK-0595` records a full-project Codex runbook for repo-clean preflight, operator-owned quarantine, read-only raw-corpus access, sanitized aggregate outputs, leak scan, reviewed repo-copy, teardown, and rollback/remediation, with capacity and restore evidence still blocked.
- No-overfitting decision: `TASK-0596` records the post-blind-baseline no-overfitting checkpoint structure and reuses the blind-freeze classification vocabulary; the checkpoint remains blocked pending actual blind baseline evidence.
- Oracle-format decision: `TASK-0597` records the cross-tier project-oracle manifest format for expected outputs, negative tests, human oracle approval, re-review triggers, pointer officialness, authority lifecycle, raw-leakage guards, and no-overfitting classification.
- Fixture-tier CI decision: `TASK-0598` records planned PR, merge, nightly, release, and controlled-pilot fixture-tier lanes as planning policy only; it does not modify GitHub required checks or claim hosted branch protection.
- Preflight master-review decision: `TASK-0599` records the production-preflight master review as no-go/blocked pending evidence, with no approved waivers and gate checks initially routed to `TASK-0600..TASK-0606`.
- P0 blocker-review decision: `TASK-0600` records `PROD-PRE-G01` as reviewed but still no-go/blocked because open P0 blocker families have no approved waiver.
- Three-project-review decision: `TASK-0601` records `PROD-PRE-G02..G05` as reviewed but still no-go/blocked pending fixture release, K3 shadow execution, blind baseline/signed-freeze evidence, scorecard pass, or explicit waiver evidence.
- Raw-data-review decision: `TASK-0602` records `PROD-PRE-G06` as reviewed but still no-go/blocked pending complete generated-pack, release-bundle, CI-log, screenshot/log, and off-repo reviewed-copy leak-scan evidence.
- Capacity/restore-review decision: `TASK-0603` records `PROD-PRE-G07` as reviewed but still no-go/blocked pending realistic full-corpus execution, ingest/extraction/projection/search metrics, backup set capture, restore rehearsal, post-restore auth-before-read proof, capacity metrics, and full-corpus no-raw-leakage evidence.
- Release/migration-review decision: `TASK-0604` records `PROD-PRE-G08` as reviewed but still no-go/blocked pending release-candidate review, production migration rehearsal, activation approval, feature-gate pass evidence, rollback/compensation rehearsal, or explicit waiver evidence.
- Semantic/CI-review decision: `TASK-0605` records `PROD-PRE-G09` as reviewed but still no-go/blocked pending hosted branch-protection proof, required-check enforcement evidence, semantic MR gate logs, review-tier enforcement proof, CAPEX runtime-change CI pass records, or explicit waiver evidence.
- Final preflight memo decision: `TASK-0606` records `PROD-PRE-G10` as final no-go evidence with no approved waivers and no engineering, product, data-governance, or security production go-signoff.
- Preflight-routing decision: the master production-preflight review now has supporting review refs for `TASK-0600..TASK-0606`; no production-preflight gate remains routed to a pending task, but the overall recommendation remains no-go and blocked pending evidence.
- Desktop source-root stage decision: `TASK-0607` records the EPIC-150 Stage 1 / Stage 2 / Stage 3 source-root boundary and non-authority rules as planning evidence only. Desktop source-root work may create observations, proposals, review tasks, and reviewed baselines, but folder paths, watcher events, local deletion, and AI proposals cannot become official project truth.
- Desktop source-root state decision: `TASK-0608` adds internal `capex_source_root_bindings`, `capex_source_root_sync_runs`, and `capex_folder_tree_snapshots` state for source-root observations only. This state does not bind SourceOccurrences, create reviewed baselines, mutate official pointers, activate desktop sync, or authorize CAPEX runtime/product behavior.
- Browser import protocol decision: `TASK-0609` records the Stage 1 browser folder/ZIP/user-selected upload protocol as manifest-first and auth-before-upload planning evidence. It does not implement upload endpoints, blob storage, background watchers, manual resync, SourceOccurrence binding, public routes, frontend routes, or activation.
- Progress truth decision: the CAPEX progress generator now includes task sections whose heading ends with `Task Stack`, so the EPIC-150 desktop source-root rows `TASK-0607..TASK-0642` are visible in generated progress data.
- Fixture boundary decision: raw/full corpora remain off-repo and later fixture release, blind baseline execution, final go/no-go approval, and activation gates remain open.
- Production-ready decision: the production-ready milestone remains blocked until restore, capacity, release, storage, raw-corpus, and production-preflight gates close or receive explicit waivers.
- Boundary decision: this closeout adds expected-output, blind-freeze, scorecard, Agent Lab matrix, off-repo runbook, no-overfitting checkpoint, oracle-format, fixture-tier CI policy, and no-go production-preflight review planning evidence only; it adds no runtime code, migrations, routes, workflow pack activation, raw corpus import, fixture release, off-repo corpus execution, restore rehearsal execution, pilot readiness, production readiness, or CAPEX product activation.

## 2026-06-17 (EPIC-142/143 sequence and workflow proposal closeout)
- Sequence-formalism decision: `TASK-0570` records CAPEX closure and pointer transitions as non-commutative; later evidence, basis changes, or pointer activity must create new governed outcomes rather than retroactively rewriting earlier snapshots or pointer generations.
- Workflow-routing decision: `TASK-0571` records procurement and CEO escalation as canonical task/approval-chain planning evidence, not editable workpage status.
- Threshold-boundary decision: the procurement escalation proposal references Annex B threshold families but cannot sign off field/threshold values; `TASK-0659` remains the activation blocker for procurement fields and executive thresholds.
- Activation decision: this closeout adds tests and planning/catalog evidence only; it adds no runtime code, migrations, public CAPEX routes, frontend routes, authored workflow pack activation, raw corpus import, or CAPEX product activation.

## 2026-06-17 (EPIC-140+ review tasks 9-10 repair)
- Control-plane decision: task status truth is now enforced between `docs/planning/TASK_INDEX.md` and task frontmatter, and DONE/COMPLETED tasks may not depend on open tasks unless a valid machine-readable `dependency_exceptions` entry exists.
- Progress-ownership decision: `frontend/src/data/capexEpicProgressData.json` remains the repo-owned generated CAPEX progress data source; `capex-progress-check` validates freshness and is part of the CAPEX semantic verification lane.
- Hygiene decision: the review-identified root editor debris filenames are removed and narrowly forbidden by repo assurance without broadening cleanup to ignored local caches.
- Evidence decision: EPIC-140 second-order review repairs are complete for foundation scope with scoped final-gate evidence; this is not CAPEX runtime activation, public route activation, raw corpus import, or product activation.

## 2026-06-17 (EPIC-140+ review tasks 7-8 repair)
- Workpage-dispatch decision: internal CAPEX workpage command dispatch now requires `activation_state=active` and `activation_policy=workpage_command_dispatch_v1`; planning-only, disabled, or policy-mismatched families fail closed before command effects.
- Idempotency decision: guarded workpage command envelopes use shared command-receipt storage scoped by project/workpage/command/snapshot, replay exact duplicate idempotency keys without handler re-entry, and reject same-key/different-payload attempts.
- Audit decision: CAPEX invariant audit hard-gates workpage activation/idempotency guardrails and first-class red-team regression coverage for revocation, artifact identity, provenance, SourceRef, and official pointer isolation.
- Activation decision: this repair adds internal guardrails and audit/tests only; it adds no public CAPEX workpage API, frontend route, authored CAPEX workflow/workpage activation, raw corpus import, or CAPEX product activation.

## 2026-06-10 (EPIC-140+ review tasks 5-6 repair)
- Artifact-identity decision: project-scoped artifact officialness uses persisted `artifact_versions.project_id`; workflow-run project inference is allowed only for initial stamping/backfill, not for authorization at promotion time.
- Provenance-isolation decision: project-scoped provenance edges persist `artifact_provenance_edges.project_id` and fail closed unless input/output artifacts and any workflow context share the same project.
- SourceRef-isolation decision: current SourceRef resolution remains the active guard for source occurrences; source occurrence relation/locator surfaces remain inactive until a later task implements same tenant/domain/project policy.
- Activation decision: this repair adds migrations and internal guards only; it adds no public routes, frontend routes, raw corpus import, relation surface activation, workpage command activation, or CAPEX product activation.

## 2026-06-10 (EPIC-140 review tasks 3-4 repair)
- Module-specific readiness decision: `TASK-0664` adds `SME-RP-MODULE-READINESS-RULE.v1` to `docs/planning/capex_real_project_acceptance/SME_RP_ACCEPTANCE_REGISTER.yaml`; unresolved business definitions, RACI posture, or workflow-extension classification block only dependent CAPEX modules and surfaces.
- Continuation decision: independent platform hardening, schema parity, security fixes, neutral foundation work, and disabled CAPEX scaffolding may continue while affected modules remain blocked.
- Deployment-parity decision: current CAPEX runtime state uses Alembic migrations plus SQLite bootstrap parity evidence; this repair does not add SQLAlchemy ORM models or authorize CAPEX runtime/product activation.
- Activation decision: this repair adds no public routes, frontend routes, workpage command activation, artifact/provenance/pointer isolation repair, migration approval, raw corpus import, or CAPEX product activation.

## 2026-06-09 (SME-RP source context and workpage generation closeout)
- Source-context decision: `TASK-0652` adds `docs/architecture/CAPEX_SOURCE_OCCURRENCE_CONTEXT_AND_TRUST_CONTRACT.md`; source occurrence context is observed source truth, not reviewed project truth.
- Trust-taxonomy decision: source origin modes are `primary`, `derivative`, `generated`, `external`, and `imported`; evidence-source trust modes are `observed`, `referenced`, `imported`, `reviewed`, and `officially_adopted`.
- Workpage-generation decision: `TASK-0653` adds `docs/architecture/CAPEX_WORKPAGE_TO_TASK_GENERATION_CONTRACT.md`; workpage-originated blockers must route through canonical tasks, flags, approvals, artifact deltas, events, or pointer requests before affecting readiness or closure.
- Workpage authority decision: workpages never set official project status, closure, evidence sufficiency, commercial status, or safety readiness by projection state or generic status command.
- Activation decision: these closeouts add no ingestion runtime, external connector activation, public CAPEX workpage API, frontend route, migration, raw corpus import, or CAPEX product activation.

## 2026-06-09 (SME-RP RACI and evidence-status closeout)
- RACI decision: `TASK-0650` adds `docs/architecture/CAPEX_RACI_ROLE_PERMISSION_MATRIX.md`; RACI is business responsibility only, not runtime authorization authority.
- Permission-source decision: runtime permission authority remains `project_memberships`, `capex_project_authorization`, canonical approvals, audited events, immutable artifacts, and promotion pointers.
- Evidence-status decision: `TASK-0651` adds `docs/architecture/CAPEX_EVIDENCE_STATUS_TRANSITION_CONTRACT.md`; evidence presence is not evidence sufficiency.
- Closure-eligibility decision: `valid` may satisfy closure, `accepted_with_residual_risk` requires explicit residual-risk acceptance or waiver, and every other evidence-link status cannot satisfy closure by itself.
- Activation decision: these closeouts add no runtime authorization logic, evidence-binding runtime, migrations, routes, frontend behavior, raw corpus import, or CAPEX product activation.

## 2026-06-09 (SME-RP sign-off and scope contract closeout)
- Approval-with-conditions decision: `TASK-0648` records `SME-RP-G001` as conditional, module-specific, non-activation, and affected-module-only approval wording.
- Scope-contract decision: `TASK-0649` adds `docs/architecture/CAPEX_SCOPE_HIERARCHY_CONTRACT.md` with the minimum `capex_scope` hierarchy: project, module/workstream, package, discipline, source occurrence, artifact, task, approval, flag, and external binding.
- Identity decision: `capex_projects.project_id` remains the project root; `workflow_run_id` remains execution identity only and is not project or scope identity.
- False-closure decision: one closed scope cannot imply overall closure; `K12-T1` is fixture motivation only.
- Activation decision: these closeouts add no runtime state, migration, route, frontend behavior, raw corpus import, or CAPEX product activation.

## 2026-06-09 (SME-RP real-project acceptance condition import)
- Namespace decision: the source archive used `SME-K12` labels, but repo-native planning uses `SME-RP` for Subject-Matter / Real-Project acceptance conditions.
- Fixture decision: `K12-T1..T10` remain concrete fixture-case IDs for the first binding real-project acceptance slice; K12 is not the top-level acceptance namespace.
- Task-numbering decision: the source archive proposed `TASK-0625..TASK-0641`, which collides with existing repo task IDs, so the tranche is remapped to `TASK-0648..TASK-0664`.
- Gate decision: acceptance gates are `SME-RP-G001..SME-RP-G013`; source-specific SME-K12 gate IDs are invalid.
- Posture decision: this import is planning-only and adds no runtime activation, public routes, migrations, raw corpus import, or source archive mutation.
- EPIC-140 posture decision: the project/access foundation remains closed evidence, but SME-RP scope hierarchy and RACI addendum tasks are open; historical closeouts should not be rewritten.

## 2026-06-09 (EPIC-149/151 semantic gate and interface burden foundation)
- Semantic-gate decision: `TASK-0568` adds `capex_semantic`, `docs/planning/CAPEX_CB2_SEMANTIC_TEST_BACKLOG.yaml`, `make capex-semantic-tests`, a visible GitHub Actions lane, and real-owner CODEOWNERS entries as repo-native quality gate evidence.
- CB2 backlog decision: CB2 rows with current repo evidence are marked `repo_evidence_green`; later fixture/workflow rows remain `tracked_future_phase` rather than being invented or silently closed.
- Interface-burden decision: `TASK-0569` adds `onetruth.capex_platform.interface_burden` and `docs/architecture/CAPEX_INTERFACE_BURDEN_POLICY.md`; interface obligations are conserved only when owned, transferred, waived, accepted residual, or open with a traceable follow-up.
- Activation decision: this tranche adds no migrations, public routes, frontend routes, hosted branch-protection claim, raw corpus material, or CAPEX runtime/product activation.

## 2026-06-08 (EPIC-143/144 handoff and projection foundation)
- Handoff decision: `TASK-0566` adds `capex.workflow_handoff_manifest.v1` and `onetruth.capex_platform.workflow_handoffs` as an internal handoff contract requiring exact artifact versions, pointer generations, meaningful SourceRefs, validation summaries, current closure snapshots, and task/workpage bindings before downstream workflow handoff can be trusted.
- Projection decision: `TASK-0567` adds `capex_workpage_projection_snapshots` and `capex_workpage_projection_rows` as project-scoped read models with deterministic basis hashes, plus signed projection cursors and typed command-envelope guards that reject stale or mismatched commands before mutation.
- Boundary decision: these foundations do not activate CAPEX workflows or workpages, add public routes, add frontend routes, import raw corpus material, or replace canonical artifact/pointer/event truth.

## 2026-06-04 (EPIC-139 redo closure handoff)
- Closure decision: `TASK-0647` records EPIC-139 as State C / repaired after the redo package, with `TASK-0643` through `TASK-0646` as the package repair/reclose chain and `TASK-0647` as post-package handoff evidence only.
- Matrix-boundary decision: `docs/planning/EPIC139_REDO_RECLOSE_MATRIX.md` remains bounded to original EPIC-139 package/source rows, the `TASK-0576` historical alias, and redo package tasks `TASK-0643` through `TASK-0646`; future follow-ups must not be added to that matrix merely because they occur later.
- Next-tranche decision: EPIC-140 is the next gated CAPEX project/access tranche, while CAPEX runtime activation remains blocked by later project/data-governance/capacity/release/production-preflight gates or explicit waivers.

## 2026-06-04 (EPIC-140 project anchor and direct membership foundation)
- Project-anchor decision: `TASK-0261` introduces durable `capex_projects.project_id` as the CAPEX project root; `workflow_run_id` remains an execution identity and is only optionally linked through nullable `workflow_runs.project_id`.
- Event-scope decision: `timeline_events.project_id` is nullable and derived from explicit `capex_project` event links or linked project-bound workflow runs so broad timeline reads can enforce project visibility.
- Membership decision: `TASK-0262` adds direct `project_memberships` with roles `project_viewer`, `project_contributor`, and `project_admin`; direct membership is separate from later authorization projections.
- API decision: the minimal CAPEX project API surface supports project list/create/detail, admin-only membership list/grant, and project-bound workflow-run creation while preserving existing no-project logistics/runtime behavior.
- Boundary decision: project-bound workflow runs and shared read-model rows are hidden from same-tenant non-members; subsequent EPIC-140 work closes the first child-route, selector/dashboard, project-scope helper, and official pointer-family slices, while authorization projections, richer CAPEX workpages, and CAPEX activation remain separate.

## 2026-06-04 (EPIC-140 project child APIs and selector/dashboard)
- Child-route decision: `TASK-0263` adds project-scoped child routes under `/api/v1/capex/projects/{project_id}` that reuse existing global row shapes and command handlers while adding project-scoped command names and `project_id` to project-route rows.
- Guard decision: project child reads require project membership before delegation, verify each child row belongs to the path project, and return not-found style denial for non-members, missing rows, or project mismatches to avoid existence leaks.
- Dashboard decision: `TASK-0264` adds `GET /api/v1/capex/projects/{project_id}/dashboard` as a derived, non-authoritative projection over canonical workflow/task/approval/flag/artifact/pointer/timeline state with `caller_role`, counts, and small excerpts.
- UX decision: `/capex/projects` and `/capex/projects/:projectId` show up to five active assigned projects, display caller role, and link to existing run/work/task queues without root redirects, logistics route changes, raw-corpus use, or CAPEX runtime/product activation.
- Index decision: this tranche does not add a migration; project-route filtering relies on the existing `workflow_runs.project_id`, `timeline_events.project_id`, and child `workflow_run_id` index coverage, with schema parity tests recording that evidence.

## 2026-06-04 (EPIC-140 project helper and official pointer families)
- Helper decision: `TASK-0371` centralizes project viewer resolution, caller role lookup, not-found project denial, project query decoration, project row stamping, and workflow-run-in-project assertions in `onetruth.api.project_scope`; project child routes and shared optional project checks use that helper without changing payloads or command names.
- Pointer-family decision: `TASK-0265` adds CAPEX project official pointer families as policy around the existing `artifact_pointers` substrate: `project_id + pointer_family` maps to `scope_kind=capex_project`, `scope_ref={project_id}`, `pointer_key=official:{pointer_family}`, and `stream_key=capex-project:{project_id}:pointer-family:{pointer_family}`.
- Generation decision: CAPEX project official pointers reuse existing pointer generation and compare-and-set behavior; first promotion creates generation `0`, repoints require `expected_generation`, and the canonical pointer ID format is unchanged.
- Officialness decision: latest artifacts, approval responses, and approved approvals do not move project official pointers by themselves; officialness changes only through explicit promotion after project membership and child ownership checks pass.
- Activation decision: these slices do not activate CAPEX runtime/product behavior, raw-corpus use, authorization projections, richer CAPEX workpages, release/deploy work, or production dashboards.

## 2026-06-04 (EPIC-140 domain runtime skeleton and logistics manifest)
- Registry decision: `TASK-0381` adds `onetruth.capex_platform.domain_runtime` as a neutral manifest loader/registry/composition-report skeleton; the CAPEX platform package must not import logistics/domain modules or domain document trees.
- Manifest decision: `TASK-0382` adds `docs/domains/logistics/domain.yaml` as a ready-state descriptive inventory over existing logistics workflow family modules, workpage descriptor/action packs, approval-response hooks, and workflow-family handoff edges.
- Activation decision: domain manifests are inventory and composition evidence only. They do not register hooks, execute side effects, activate CAPEX runtime/product behavior, add routes, add migrations, or replace workflow packs/workpage packs as source truth.
- Data-boundary decision: raw corpus paths/content remain rejected by manifest contract coverage; the future CAPEX manifest remains separate `TASK-0383` work and should start in incubation/not-ready state.

## 2026-06-05 (EPIC-140 CAPEX manifest and approval-effect registry shadow mode)
- CAPEX manifest decision: `TASK-0383` adds `docs/domains/capex/domain.yaml` in incubation state with empty workflow, workpage, and side-effect inventories plus disabled-capability/readiness-prerequisite rows for later project authorization, storage custody, source governance, workflow catalog, workpage projection, and production-preflight tasks.
- Approval registry decision: `TASK-0384` adds `ApprovalEffectRegistry` and `ApprovalEffectPack` behind the existing approval-response hook substrate; the default registry is empty and platform-neutral.
- Logistics parity decision: the logistics approval-response selector remains the compatibility facade but now delegates to `LOGISTICS_APPROVAL_RESPONSE_EFFECT_REGISTRY`; weekly publish and dispatch-reporting finalize hook selection remains byte-for-byte equivalent for current workflows.
- Activation decision: this tranche adds no CAPEX approval behavior, no hook registration from manifests, no new routes, no migrations, no raw-corpus use, and no CAPEX runtime/product activation.

## 2026-06-05 (EPIC-140 project authorization CED and query prototype)
- CED decision: `TASK-0385` adds `docs/architecture/CAPEX_PROJECT_AUTHORIZATION_CED.md`, recording that `capex_projects.project_id` remains the durable root and `workflow_run_id` remains only an execution identity.
- Projection-boundary decision: direct `project_memberships` remain authoritative runtime grants, while future `capex_project_authorization`, `capex_project_feature`, and `capex_user_project_view` are derived projection/read-model concepts.
- Query-prototype decision: `TASK-0386` adds `AuthorizedProjectsQuery` as a backend-only prototype over direct membership state, returning deterministic authorized active project IDs and caller roles without frontend-only filtering or a global project list.
- Activation decision: this tranche adds no routes, migrations, frontend behavior, raw-corpus use, physical authorization projection runtime state, or CAPEX runtime/product activation.

## 2026-06-05 (EPIC-140 storage/blob custody CED and pilot gate checklist)
- Custody-boundary decision: `TASK-0387` adds `docs/architecture/CAPEX_STORAGE_BLOB_CUSTODY_CED.md`, defining future `BlobRef`, `BlobReplica`, `BlobIngestSession`, `ArtifactVersionBlob`, `DerivedArtifact`, and `DownloadEvent` concepts while keeping `ArtifactVersion` as canonical metadata and `ArtifactPointer` targeted only at `ArtifactVersion`.
- Auth-before-download decision: artifact/workflow/project authorization must happen before blob custody resolution or byte reads; `artifact_versions.storage_uri` remains compatibility state until a later physical custody migration.
- Pilot-gate decision: `TASK-0388` adds `docs/planning/checklists/CAPEX_PILOT_STORAGE_GATE.md` with default result `blocked_pending_evidence`; this task does not pass, waive, or execute the gate.
- Activation decision: this tranche adds no migrations, routes, frontend behavior, storage backend rollout, Postgres rollout, raw-corpus use, pilot readiness, or CAPEX runtime/product activation.

## 2026-06-05 (EPIC-140 W1 pattern register and closeout review)
- Pattern-register decision: `TASK-0389` adds `docs/architecture/CAPEX_W1_CODE_PATTERN_REGISTER.md` with illustrative, non-production patterns for domain-runtime manifests, direct-membership project visibility, and auth-before-download storage custody.
- Overbuild decision: W1 explicitly rejects dynamic domain package loading, frontend-only auth filtering, global project list exposure, blob truth bypassing `ArtifactVersion`, pointer targets to blobs, and storage reads before scope authorization.
- Closeout decision: `TASK-0390` adds `docs/architecture/CAPEX_W1_CLOSEOUT_REVIEW.md`; gates `ARCH-W1-GATE-001` through `ARCH-W1-GATE-009` have repo evidence, while `ARCH-W1-GATE-010` remains `blocked_pending_evidence`.
- Activation decision: this tranche adds no migrations, routes, frontend behavior, storage backend rollout, Postgres rollout, raw-corpus use, source ZIP mutation, pilot readiness, production readiness, or CAPEX runtime/product activation.

## 2026-06-05 (EPIC-140 authorization projection runtime state)
- Projection-state decision: `TASK-0563` adds physical `capex_project_authorization`, `capex_project_feature`, and `capex_user_project_view` read-model tables with SQLite bootstrap, Alembic migration, SQLAlchemy models, runtime schemas, repositories, and schema-parity/backfill tests.
- Authority decision: direct `project_memberships` remain authoritative source state. Authorization and user-view projections are deterministic, rebuildable read models refreshed from active direct memberships by `refresh_project_authorization_projection` and `rebuild_project_authorization_projections`.
- Access-query decision: `AuthorizedProjectsQuery` now reads projection-backed rows while preserving existing project list/detail payloads, caller-role semantics, not-found style project denial, and no-project logistics/runtime read visibility.
- Feature-posture decision: `capex_project_feature` seeds `capex.runtime_activation` as `disabled` with a blocked reason, so closing EPIC-140 does not imply CAPEX runtime/product activation.
- Closeout decision: all EPIC-140 task rows are now closed. CAPEX activation, raw-corpus/source governance, workflow/workpage authoring, real pilot storage evidence or waiver, release/capacity, and production-preflight gates remain later work.

## 2026-06-08 (EPIC-141/142 source occurrence and closure primitive foundation)
- SourceRef decision: `TASK-0564` adds physical `capex_content_identities` and `capex_source_occurrences` runtime state plus `onetruth.capex_platform.source_refs`, using canonical `source_occurrence:{source_occurrence_id}` refs with tenant/domain/project scope checks and non-resolvable status denial.
- Evidence-boundary decision: meaningful SourceRefs require real resolver success. Empty arrays, malformed refs, unresolved refs, cross-scope refs, and quarantined/redacted/superseded/deleted occurrences cannot support closure or official claims.
- Closure-vector decision: `TASK-0565` adds `capex_waivers`, `capex_closure_gate_evaluations`, and `capex_closure_snapshots` plus `onetruth.capex_platform.closure_governance`; absence of evidence fails closure, and waivers are recorded as `satisfied_by_waiver`, not `pass`.
- Stale-recurrence decision: current closure snapshots can be marked stale when source/waiver basis refs change through a deterministic recurrence rule registry; this does not expose public closure commands or UI.
- Activation decision: this tranche adds internal runtime foundation only. No CAPEX runtime/product activation, raw corpus import, HTTP routes, frontend routes, generated artifact validators, public closure/promotion UI, or production/pilot readiness is implied.

## 2026-06-03 (CAPEX RF-002/NU-CB-P0-001 descriptor registry and approval duplicate closeout)
- Descriptor-boundary decision: `TASK-0370` moves active logistics workpage descriptor registrations behind `WorkpageDescriptorRegistry`; the existing descriptor lookup helpers remain compatibility facades and public workpage routes/actions stay unchanged.
- Subject-surface decision: workpage `subject_link` validation now uses the registered workpage action rules for supported human-task and approval surfaces instead of local schedule/EOD matrices in the action-resolution handler.
- Reconciliation decision: `TASK-0561` is closed against the existing `ADR-005` approval-response hook evidence from `TASK-0257`/`TASK-0369`; no new approval handler behavior was added.
- Activation decision: EPIC-139 domain-boundary cleanup is closed without CAPEX runtime/product activation, raw corpus use, production deployment, or new public workpage routes.

## 2026-06-03 (CAPEX CLEAN-004/RF-001 test split and approval extraction reconciliation)
- Test-split decision: `TASK-0260` adds a minimal EPIC-139 `logistics_regression` pytest marker manifest and visible Make/GitHub lanes for `platform-substrate-tests` and `logistics-regression-tests`; this does not replace the broader future marker taxonomy planned under `TASK-0492`.
- Platform-boundary decision: platform substrate coverage may still inspect logistics symbols when proving generic/domain extraction, but tests that depend on logistics fixture roots must live in the logistics regression lane.
- Reconciliation decision: `TASK-0369` is closed against existing `ADR-005` approval-response hook evidence from `TASK-0257`; no new approval handler behavior was added. `TASK-0561` was still untouched in that pass and is now reconciled separately above.
- Activation decision: these closeouts do not activate CAPEX runtime/product behavior, raw corpus use, production deployment, or new approval semantics.

## 2026-06-03 (CAPEX CLEAN-002/CLEAN-003 workpage registry and logistics docs classification)
- Workpage-boundary decision: generic workpage action projection now delegates to a domain-neutral `WorkpageActionRegistry`; logistics workflow IDs, stage/task surfaces, approval scope refs, projection keys, and unavailable-reason strings live in the logistics action pack.
- Payload-compatibility decision: `TASK-0258` preserves the existing public `workpage_actions` wire shape while adding an explicit extension point for future domain packs such as CAPEX.
- Docs-classification decision: logistics-specific planning docs now live under `docs/domains/logistics/`, with `DOC_INVENTORY.yaml` recording normative, descriptive, and historical classifications; workflow packs and operator runbooks remain in their existing authoritative/runbook locations and are inventory-listed.
- Activation decision: `TASK-0258` and `TASK-0259` close domain-boundary and documentation cleanup only; they do not activate CAPEX runtime behavior, raw corpus use, production deployment, or new public workpage routes.

## 2026-06-03 (EPIC-150 desktop source-root pack integration)
- EPIC-150 integration decision: the existing CAPEX release-governance EPIC-150 tranche remains intact, and the separate desktop folder source-root/sync pack is imported as an EPIC-150 draft planning addendum rather than replacing or orphaning the release-governance task stack.
- Task-numbering decision: the pack's proposed `TASK-0589..TASK-0624` range collided with existing repo tasks, so the desktop source-root/sync tasks are renumbered to `TASK-0607..TASK-0642`; generated registers and task briefs record that remap.
- Authority-boundary decision: desktop source-root sync remains observation -> AI proposal -> PM review, snippets under `codex/snippets/EPIC-150/` are context-only references, and no CAPEX runtime/product activation, raw corpus import, local path authority, watcher-event authority, or evidence deletion authority is implied by the planning import.

## 2026-06-02 (CAPEX PR012 schedule-control hardening)
- Stage04 output decision: weekly schedule-control generated outputs now persist through the canonical generated-artifact helper instead of direct `inmem://` artifact rows.
- Receipt decision: `schedule-control.build-weekly` uses workflow-run-scoped command receipts, so idempotent command replay returns stored command truth and does not duplicate Stage04 artifact events.
- Boundary decision: `TASK-0245` closes logistics domain/runtime safety posture only; it does not activate CAPEX production-like runs, raw corpus use, deployment, or broader generated-artifact migration.

## 2026-06-02 (CAPEX PR013 handoff scope scaffold)
- Handoff-scope decision: logistics handoff effects now carry a deterministic scope object containing source artifact truth, target partition, policy version, and a stable scope key.
- Scaffold decision: weekly seed materialization, live-dispatch activation/preparation, and notify-only handoff paths record that scope in metadata, but this does not yet claim behavior-complete seed hardening, republish policy, or notify-only conflict tightening.
- Boundary decision: `TASK-0246` closes auditability of command/effect scopes only; CAPEX production-like activation, raw corpus use, release/deploy work, and later EPIC-139 handoff policies remain blocked.

## 2026-06-02 (CAPEX PR014 weekly seed materialization hardening)
- Seed-storage decision: weekly-to-live daily seed artifacts are now generated, file-backed JSON manifests persisted through the canonical generated-artifact helper rather than authoritative `inmem://` seed rows.
- Replay decision: seed manifest content excludes volatile materialization idempotency keys so retries with a different command key reuse the same immutable seed artifact and EdgeExecution without digest conflicts.
- Boundary decision: `TASK-0247` closes weekly seed materialization hardening only; live-dispatch republish guards, notify-only late-report policy, CAPEX production activation, and deployment remain later gated work.

## 2026-06-02 (CAPEX PR015 live-dispatch republish guard)
- Base-seed decision: once `live_dispatch.v1` has `stage01.base_seed` bound for a service day, later weekly republish attempts must surface explicit stale policy state instead of rebinding that input.
- Activation decision: activating a prepared weekly-to-live edge after its weekly published source is superseded now records `status=stale` with `policy_state=late_weekly_republish_after_live_prepare` and fails closed with `live_dispatch_base_seed_republish_after_prepare`.
- Boundary decision: `TASK-0248` closes the republish-after-prepare guard only; same-week/future-week planning-cycle policy, notify-only late-report policy, CAPEX production activation, and deployment remain gated work.

## 2026-06-02 (CAPEX PR016 notify-only/reporting guard)
- Storage decision: notify-only target input artifacts now use file-backed generated JSON manifests through the canonical generated-artifact helper rather than authoritative `inmem://` handoff rows.
- Late-report decision: reporting-to-planning late feedback cannot replace an existing weekly `stage03.actual_hours_snapshot` binding in the default/shared-env path; it fails closed with `late_reporting_handoff_conflict`.
- Compatibility decision: merge-and-replace for newer reporting feedback remains available only when `ONETRUTH_API_BOUNDARY_PROFILE` is explicitly `local_dev` or `ci_test`; this is local/test compatibility, not production posture.
- Boundary decision: `TASK-0249` closes notify-only/reporting handoff hardening only; planning-cycle policy, CAPEX production activation, and deployment remain gated work.

## 2026-06-02 (CAPEX PR017 planning-cycle policy objects)
- Calendar-policy decision: logistics same-week now means `same_iso_planning_week`, the older `same_week` label is recorded only as deprecated compatibility metadata, and reporting actuals target the next ISO planning week.
- Transform decision: the existing `service_day_to_future_planning_week` transform ID remains stable, but it now resolves through `LogisticsCalendarPolicy`, including Sunday and ISO-year rollover behavior.
- Policy-evidence decision: weekly seed and reporting-to-planning handoff scopes may carry deterministic `policy_context`, and late weekly republish/late reporting errors now include named policy IDs while preserving existing error codes.
- Boundary decision: `TASK-0250` closes planning-cycle policy hardening only; CAPEX production activation, deployment, raw-corpus use, and reconciler apply authorization remain gated work.

## 2026-06-02 (CAPEX PR018 weekly-to-weekly carry-forward)
- Carry-forward decision: route-demand add-next-week now goes through canonical weekly-to-weekly carry-forward that records target run, intake task, target route-demand input binding, artifact provenance, and a `weekly_to_weekly_carry_forward` EdgeExecution.
- Target-run decision: weekly target run reuse fails closed on activation-key drift, and the target seed payload is aligned to the target workflow run planning week.
- Boundary decision: carry-forward prepares target weekly input truth only; it does not complete intake, spawn Stage04 work, run scheduling agents, request approvals, deploy, activate CAPEX production, or authorize reconciler apply mode.

## 2026-06-02 (CAPEX PR010/PR011 lab auth and VM lane)
- Lab-auth decision: `TASK-0243` is closed with a local lab-only `/api/v1/viewer` smoke using the existing `shared_env` RS256 JWT resolver; this tranche intentionally does not add JWKS lookup or pilot-password fallback.
- Identity-boundary decision: lab viewer smoke must prove server-derived JWT identity wins over conflicting browser identity headers and that actor switching remains disabled under `shared_env`.
- Lab-deploy decision: `TASK-0244` now has an operator-gated GCP VM plan/execute lane limited to `gcloud compute scp` and `gcloud compute ssh`; it is lab-only, no-real-users, no production target, no raw corpus, and no CAPEX activation.
- Closeout decision: `TASK-0244` remains `BLOCKED` until actual operator-supplied lab GCP coordinates and a successful live execute-and-smoke run are recorded; stubbed tests and dry-run planning are implementation evidence only.

## 2026-05-26 (schedule comparison mode split and shortcut capture)
- Comparison-mode decision: the editable `schedule-v0` surfaces now distinguish `current_week`, `historical_demo_week`, and `future_week` from the displayed schedule week versus the real `America/Vancouver` service date instead of treating any selected in-week day as an elapsed-day anchor.
- Future-week decision: future weekly drafts keep the previous-week comparison block when pinned reality exists, but all seven scheduled-week columns stay on planned schedule truth with no synthesized dispatch-report substitution or elapsed-day lockout.
- Demo-compat decision: the selected-day fallback remains intentionally enabled only for historical demo weeks so fixture-backed March demos still show inline dispatch-report comparison until a backend-authored comparison mode replaces the frontend inference.
- Follow-up decision: the currently accepted shortcuts for this comparison slice are now tracked in `docs/domains/logistics/archive/LOGISTICS_WORKPAGES_SCHEDULE_COMPARISON_SHORTCUTS_NOTE.md` for later cleanup rather than remaining implicit in the UI implementation.

## 2026-05-25 (schedule main-view history rail removal)
- UI decision: the canonical `schedule-v0` run page and full artifact page no longer render the accepted-series / draft-lineage side rail on the main surface.
- Boundary decision: accepted history and draft lineage remain separate backend-authored metadata, but they should not compete with the main weekly schedule review/edit surface.
- Workflow decision: the embedded quick-edit draft dialog keeps its explicit draft-history affordance; only the full-page side rail is removed.

## 2026-05-19 (route-demand on-call target editing and existing-week coverage boundary)
- Editing decision: the shared `route-demand-v0` editor now treats `on_call_target` as operator-editable truth alongside `planned_route_count` in both the quick-edit popup and the full-page artifact editor.
- Future-week trigger decision: `Save and run scheduling agent` for future-week route-demand seeds now activates when any visible day moves to positive planned-route demand or positive on-call target demand.
- Existing-week boundary decision: on-call-only existing-week route-demand changes are saveable, but they do not unlock or return route-demand coverage recommendations; existing-week coverage remains a positive planned-route-delta tool only.

## 2026-05-11 (dispatch-reporting workbook-only Stage04 review handoff)
- Evidence decision: `dispatch_reporting.v1` `Stage04/final_packet_review` no longer requires a separate `reporting.manager_review.doc` upload; review confirmation on the latest `reporting.upd_draft.workbook` is now the only pre-approval evidence gate for the first operator lane.
- UI decision: the canonical EOD closeout flow now treats Step 3 as workbook-only review confirmation plus task completion, rather than a separate manager-review file upload flow.
- Safety decision: dispatch-reporting finalize still fails closed unless a current draft exists, the confirmed reviewed draft exists, and that reviewed draft remains the latest draft for the run at approval time.

## 2026-05-10 (bounded pre-publish route-demand coverage landing)
- Existing-week decision: editable existing-week `route-demand-v0` artifacts may now expose the existing `workpage.route-demand-v0.save_and_run` action as `Run coverage agent` when a latest weekly draft exists and the visible route-demand edit introduces a positive route-count increase.
- Handoff decision: existing-week `save-and-run` now saves or reuses the successor route-demand artifact, returns backend-authored `route_demand_coverage_context`, and hands off into the canonical `schedule-v0` quick-edit popup without creating a schedule successor at route-demand save time.
- API decision: `schedule-v0` now exposes backend-owned route-demand coverage recommend/apply routes over the current weekly draft; recommend remains read-only, while apply revalidates candidate selections, creates the successor schedule draft, and explicitly repins the new route-demand artifact in the successor dependency manifest.
- Scope decision: this is a bounded pre-publish weekly-draft subset of EPIC-135 only; no live-dispatch-backed replan lane, canonical runtime-status projection, driver-contact bridge, or manual scheduler CTA retirement is implied by this landing.

## 2026-05-03 (dispatch-reporting service-date-selectable closeout import)
- Date-authority decision: the `Upload route activity` popup now treats the operator-selected service date as canonical upload truth; explicit `metadata_json.service_date` outranks filename-derived dates and run fallback during EOS import.
- Run-alignment decision: if the selected service date differs from the current `dispatch_reporting.v1` run `logical_date`, the workpage closeout flow must resolve or create the matching same-scope reporting run and continue review/finalize work there instead of importing mismatched daily truth into the current run.
- API decision: `POST /api/v1/workpages/workflow-runs/{workflow_run_id}/eod-v0/intake-task` now accepts optional `service_date` and returns the resolved `target_workflow_run_id`, `target_route`, and `created_workflow_run` fields so the frontend can switch onto the canonical daily run before draft review and approval.

## 2026-05-03 (route-demand week-by-week future-run activation)
- Surface decision: `route-demand-v0` now presents a single visible operational week at a time; the copied second-week horizon remains an internal compatibility detail and is no longer treated as user-facing editable truth.
- Creation decision: `Add a week` now creates or reuses the real next weekly-planning workflow run and seeds an empty future-week route-demand artifact there instead of editing synthetic future rows inside the current run.
- Trigger decision: `Save and run scheduling agent` is now the explicit greenfield future-week scheduling trigger from route demand; plain route-demand save no longer spawns the legacy refresh task.
- Runtime decision: the future-week activation path must auto-claim the canonical Stage04 work, reuse the existing weekly Stage04 agent runtime, auto-complete Stage04 on success, and hand off to the canonical `schedule-v0` route with the existing quick-edit popup entrypoint.
- Safety decision: `dispatch_reporting.v1` and `eod-v0` remain behaviorally unchanged by this slice except for additive shared typing/test fallout needed to keep the repo compiling.

## 2026-04-25 (EPIC-135 unified replan popup and dynamic scheduling activation correction tranche)
- Selection decision: EPIC-135 is now the selected next app-facing workpage/product tranche after EPIC-134, and the repo now tracks it through `TASK-0225` through `TASK-0232`.
- Lifecycle decision: the shared `Edit Weekly Schedule` popup is the selected operator surface both before and after publish, but backend ownership stays split by lifecycle state: `weekly_schedule_planning.v1` before publish and `live_dispatch.v1` after publish.
- Trigger decision: in-scope route-demand transitions from `0 -> N` now define the selected greenfield auto-scheduling trigger; the old operator-facing manual scheduler task/action may be retired only after the current route-demand refresh-task creation path is replaced and the popup exposes recovery/resume truth.
- Ranking decision: EPIC-135 defaults to deterministic candidate generation and scoring first, with on-call priority only among hard-pass candidates; agent escalation remains bounded and secondary except for greenfield auto-run.
- Status decision: "agent is working" for the popup must be projected from canonical `task_run`, `human_task`, `requirement_state`, `policy_decision`, `execution_session`, and `tool_execution` truth rather than popup-local timers or mutation state.
- Contact decision: driver phone numbers must land in mirrored canonical bridge inputs (`planning.driver_contact_directory.workbook` and `dispatch.driver_contact_directory.workbook`) rather than inside driver capabilities or frontend-local state.
- Sequencing decision: the shared popup redesign should land over weekly/live deterministic truth first; the later live-dispatch agent/runtime task remains explicit work and must author its runtime/actionability surface before any endpoint is added.

## 2026-04-06 (TASK-0157 EPIC-125 closeout and first-demo feedback truth)
- Epic-closeout decision: EPIC-125 is now complete; `TASK-0151` through `TASK-0157` should be treated as completed history rather than as an active operator-loop backlog.
- Reconciliation decision: `TASK-0154` is marked `DONE` from existing live-dispatch runtime truth already visible in handlers, runtime proof, the weekly-first local demo smoke, and the operator runbooks; `TASK-0157` does not add new runtime behavior.
- Feedback-handoff decision: first-demo feedback is now recorded as historical input to the later landed tranches (completed EPIC-126 cleanup history plus EPIC-131, EPIC-132, EPIC-133, and EPIC-134), not as permission to reopen EPIC-125 or speak about EPIC-126 in future tense.

## 2026-04-06 (TASK-0156 external cadence tick and single-node logistics operator runbook)
- Cadence-entrypoint decision: the first continuous logistics operator cadence now runs through the repo-native installed CLI surface `onetruthctl cadence tick-logistics`, not a demo-only seed script and not an embedded scheduler.
- Bounded-orchestration decision: the cadence tick may only ensure due weekly/reporting runs and human tasks plus prepare `live_dispatch.v1` once weekly publish truth exists; it must not upload operator inputs, run weekly Stage04, complete reviews, or auto-approve workflow work.
- Replay decision: cadence replays are keyed by effective `ServiceDateID` and must not duplicate workflow runs, human tasks, edge executions, or live seed artifacts for the first-user logistics lane.

## 2026-04-06 (TASK-0222 supported-env reporting-intake truth correction)
- Repro-source decision: for `TASK-0222`, the only authoritative repro surface is a clean Python `3.11` install bootstrapped with `python3.11 -m pip install -e ".[api,dev]"`; partial local Python `3.11` environments are not sufficient to diagnose the active blocker.
- Scope-gate decision: supported-env verification is green for `tests/runtime/api/test_weekly_stage04_openai_agent_api.py`, `tests/runtime/api/test_dispatch_reporting_finalize_loop_api.py`, `tests/runtime/api/test_logistics_local_demo_smoke_api.py`, and `tests/unit/test_dispatch_reporting_workbook.py`, so Stage04 finalize repair is not the active `TASK-0222` target unless that repro goes red again.
- Failure-classification decision: dispatch-reporting intake completion now treats missing workbook runtime support as `runtime_dependency_missing` with `dependency: openpyxl`; `unsupported_eos_workbook_shape` remains reserved for genuine workbook-family or shape failures after dependencies are available.
- Repo-memory decision: EPIC-134 and `TASK-0222` should describe the remaining gap as reporting-intake dependency honesty and stale-diagnosis correction, not as a current Stage04 calculation-snapshot regression.

## 2026-04-06 (TASK-0221 minimal canonical demo boundary freeze)
- Selection decision: there is still no new app-facing product-expansion epic selected after EPIC-133; EPIC-134 is instead the active demo-enablement tranche for already-landed canonical workpage surfaces.
- Validation-target decision: the demo validates canonical `/runs/:workflowRunId/workpages/*` routes for `schedule-v0`, `route-demand-v0`, `driver-preferences-v0`, and `eod-v0`; `/demo/logistics` may remain launcher/narrative context, but it is not the semantic validation surface.
- Prep-path decision: the default demo-prep target is deterministic and idempotent, should not require OpenAI, and must reuse canonical truth objects rather than introducing a demo-only mode or API path.
- Scope-boundary decision: multi-week accepted-history seeding, route-demand auto-drift seeding, and any second demo mode remain out of scope for the first demo-enablement tranche.

## 2026-04-06 (TASK-0218 workpage concentration split and guardrails)
- Facade decision: the public workpage handler/service entrypoints now stay stable through thin facades at `src/onetruth/application/handlers/workpages.py` and `src/onetruth/application/services/logistics_workpages.py`, while extracted modules own the refactor-heavy internals.
- Frontend-boundary decision: the public workspace board, schedule page, and logistics demo page exports now remain intentionally thin and source-budgeted; extracted model/presentational seams such as `taskBoardModel.ts`, `WorkspaceBoardCard.tsx`, `schedulePageModel.ts`, and `LogisticsScheduleWorkpageView.tsx` protect the moved logic.
- Guardrail decision: `tests/unit/test_workpage_module_guardrails.py` is now the explicit source-budget check for the five historical concentration files, and EPIC-133 closes once those budgets hold alongside the existing smoke/route/contract checks.

## 2026-04-06 (TASK-0217 demo shell launcher-only convergence)
- Surface-boundary decision: `/demo/logistics` remains the logistics story shell, run chooser, family-artifact surface, and drill-down graph, but it no longer hosts editable workpages inline; all create/submit/history behavior now happens only on canonical `/runs/:workflowRunId/workpages/*` and `/runs/:workflowRunId/workspace` routes.
- Navigation decision: the shell brand link now preserves derived logistics `module` and `workflow_run_id` context when returning from canonical logistics routes to `/demo/logistics`, so launcher state is restored instead of resetting to a blank shell.
- Cleanup decision: the duplicate inline mutation engine and its inline-only workpage history repository helpers are retired; remaining EPIC-133 work now centers on concentration-file decomposition and guardrails in `TASK-0218`.

## 2026-04-06 (TASK-0215 backend-owned workpage lineage and accepted navigation)
- Contract-seam decision: canonical artifact-backed workpage GET payloads now own lineage/latest truth through additive `artifact_history`, while run-backed contracts return `artifact_history: null`.
- Navigation decision: accepted schedule history is now fully server-authored per entry, including cross-run `route` values inside `accepted_series.entries[]`; canonical pages must not rebuild accepted-history URLs from the current run id.
- Debt-boundary decision: client-side artifact list/filter helpers remain only as deferred inline demo-shell debt for `TASK-0217`; canonical schedule, EOD, route-demand, and driver-preferences pages no longer use them to build history rails.

## 2026-04-06 (TASK-0216 server-authored workpage action execution)
- Write-seam decision: canonical workpage create/submit flows now prefer additive server-authored `action_ref` payloads; `subject_link` remains a deprecated compatibility fallback only when `action_ref` is absent, and mixed `action_ref` + `subject_link` payloads fail closed as `invalid_payload`.
- Projection decision: workspace `workpage_actions[]` and canonical page `actions[]` now carry server-authored `action_ref` values, while the run-backed EOD landing keeps its frozen `draft_resolution` seam and extends it with `open_action_ref` / `create_action_ref`.
- Frontend-handoff decision: canonical workspace/page navigation now carries `workpageActionRef` router state and canonical repository/page code no longer constructs raw `subject_link`; legacy `subject_context` and `link_policy` remain compatibility metadata for this tranche.

## 2026-04-06 (TASK-0214 frontend verification closeout and EPIC-132 completion)
- Closeout-lane decision: `make frontend-workpages-smoke` is now the dedicated clean-install verification slice for the canonical workpage frontend, wrapping the schedule page, EOD page, and workpages repository tests under the committed Node `20` / `npm ci` baseline.
- CI-truth decision: the main workflow now runs that slice as its own `frontend / workpages-smoke` job while keeping the broader `frontend` job for full typecheck/test/build coverage.
- Epic-closeout decision: EPIC-132 is complete once both targeted closeout lanes are green from clean-checkout truth: `make PYTHON=python3.11 workpage-mutation-smoke` for backend mutation behavior and `make frontend-workpages-smoke` for frontend workpage verification.
- Selection decision: with EPIC-132 closed on 2026-04-06, EPIC-133 is now the selected follow-on workpage tranche.

## 2026-04-06 (TASK-0213 canonical-only wording and compatibility-field sync)
- Contract-copy decision: active canonical workpage docs, snapshots, and route tests now describe run-backed and artifact-backed projections rather than demo-query posture; example wording remains only when it refers to source material.
- Compatibility-seam decision: inner `workpage.mode` and `workpage.source_examples` remain temporary legacy view-model fields during EPIC-132 settlement, but authoritative public posture comes from the canonical run/kind-scoped routes and the outer workpage contract wrapper.
- EOD-truth decision: active run-backed EOD truth must acknowledge the real draft create/submit workbook lane; no active contract should still claim manual closeout is local-only or that no submit/materialize path exists.

## 2026-04-06 (TASK-0212 workpage mutation smoke gate and dependency-readiness baseline)
- Verification-lane decision: `make workpage-mutation-smoke` is now the fast canonical smoke slice for public workpage mutations, covering EOD create/submit replay, schedule submit replay, route-demand submit replay, driver-preferences snapshot replay, and weekly publish happy/drift behavior.
- CI-truth decision: `workpage-mutation-smoke` now runs inside `ci-fast-backend` and as its own `required-fast / workpage-mutation-smoke` job in `.github/workflows/main.yml`.
- Environment-ambiguity decision: supported Python `3.11` clean-install verification confirms the EOD workbook/unit and submit replay flows are green when project dependencies are installed; the smoke gate now fails fast on missing runtime imports like `openpyxl` instead of surfacing that situation later as an ambiguous workpage `500`.

## 2026-04-06 (EPIC-132 selection and post-EPIC-131 settlement-plan import)
- Selection decision: EPIC-132 is now the active follow-on workpage tranche after EPIC-131 and the completed EPIC-126 cleanup trio.
- Plan-routing decision: EPIC-132 and EPIC-133 now supersede EPIC-126 as the active post-EPIC-131 settlement/hardening plan; EPIC-126 remains completed history rather than the current plan of record.
- Reconciliation decision: the 2026-04-05 packet findings are imported as dated settlement evidence, not assumed live repo truth. TASK-0211 must classify them against the current checkout before treating any item as still open.
- Environment-truth decision: supported-environment verification for remaining workpage settlement issues means Python `3.11` with `python3.11 -m pip install -e ".[api,dev]"` and Node `20` with the committed lockfile via `npm ci`; failures from `python3` 3.9 or partially installed environments are not repo regressions.
- Deferral decision: client-carried `subject_link`, client-built history rails, inline demo mutation logic, and large-file decomposition remain explicit EPIC-133 debts unless one of them directly blocks EPIC-132 settlement.

## 2026-04-05 (EPIC-126 cleanup trio closeout)
- Cleanup-closeout decision: `TASK-0158`, `TASK-0159`, and `TASK-0160` are complete, so the Workpages v1 cleanup trio should be treated as landed rather than active follow-on work.
- Active-truth decision: current docs, current snapshots, and current source/test guardrails now describe only the canonical run/kind-scoped workpage posture plus `/demo/logistics` as the shell-only entrypoint.
- Fixture decision: retired frontend contract fixtures `workpage_schedule_v0_state.json`, `workpage_eod_v0_state.json`, and `workpage_eod_v0_artifact_create_response.json` are removed from the committed active set.
- Build-artifact decision: `frontend/dist` is not a tracked repo-truth surface in this workspace and is excluded from active cleanup acceptance.
- Selection decision: after the Workpages v1 cleanup trio, no new app-facing epic is selected yet.

## 2026-04-05 (EPIC-131 closeout and EPIC-126 cleanup activation)
- Closeout decision: EPIC-131 is complete, and `TASK-0202` through `TASK-0207` should be treated as implemented rather than pending.
- Route-posture decision: the active public workpage posture is now canonical-only. Public `/api/v1/workpages/demo/*`, public `/api/v1/workpages/artifacts/*`, and frontend `/demo/logistics/workpages/*` are retired.
- Shell decision: `/demo/logistics` remains the primary logistics shell entrypoint, but it launches only canonical `/runs/:workflowRunId/workpages/*` pages.
- Vocabulary decision: active workspace/workpage action presentation is now `open_route | create_then_open` only.
- Cleanup-epic decision: EPIC-126 is now the active follow-on cleanup epic for internal drift removal, canonical regression hardening, fixture pruning, and active-doc synchronization.
- Selection decision: no new app-facing product-expansion epic is selected after EPIC-131; only EPIC-126 cleanup is active.

## 2026-04-04 (TASK-0201 EPIC-131 boundary freeze and routing selection)
- Next-workpages-epic decision: EPIC-131 is now the selected app-facing workpages follow-on after the first weekly-first local demo clarification, and `TASK-0201` is complete as the doc-only repo-native freeze.
- Boundary decision: `schedule-v0` is explicitly frozen as a driver reassignment/on-call surface plus server recalculation only; route-demand edits belong to a separate `route-demand-v0` surface, and `driver-preferences-v0` is a separate soft/advisory weekly snapshot.
- Navigation decision: accepted-version arrows are accepted-history only, while draft lineage remains separate and must not share traversal semantics.
- Repo-grounding decision: later route-demand UX may rely on backend-owned daily buckets already present in `planning.route_slot_requirements.workbook` example truth; the frontend must not invent slot-allocation heuristics by default.
- Accepted-series decision: current repo review did not find a stable explicit artifact-level accepted-series grouping key on saved/published schedule artifacts, so `TASK-0202` must add that deliberately instead of relying on ad hoc metadata.
- Backlog-routing decision: the remaining EPIC-125 cadence tasks (`TASK-0154`, `TASK-0156`, `TASK-0157`) remain tracked, but they are no longer the next app-facing workpages priority; EPIC-126 remains the later hardening/closeout tranche.

## 2026-03-30 (weekly Stage04 finalize-repair continuation and failure reclassification)
- Finalize-invariant decision: weekly Stage04 still requires an explicit model-invoked `finalize_weekly_stage04_draft_outputs` call before any draft artifacts count as complete; backend auto-finalization remains out of scope.
- Repair-boundary decision: if the deterministic planner is already complete and the first Responses loop ends with final text but no finalize call, the runtime now performs one bounded continuation on the same Responses thread with a finalize-only tool surface and monotonic rebased turn evidence.
- Failure-classification decision: unrepaired weekly Stage04 finalize omission now surfaces as a runtime/model failure (`502`) with `stage04_finalize_required` plus `planner_complete`, `repair_attempted`, and `final_response_id` details, instead of being treated as a `400` bad request.

## 2026-03-29 (TASK-0155 weekly-first local demo seed, runbook, and workspace-first story shell)
- Demo-posture decision: the default local logistics walkthrough now starts from a weekly-first seed with one current weekly run open at `Stage04/weekly_input_intake`, one current reporting run open at `Stage01/eos_input_intake`, one prior reporting-feedback run already finalized, and no current live-dispatch run until the operator explicitly prepares the service day.
- Entry-surface decision: `/demo/logistics` is now workspace-first for the first operator demo, with weekly and reporting workspaces as primary CTAs, live dispatch shown as `Prepare service day` until activation, and workpage links kept contextual/secondary instead of the main starting point.
- Seeder decision: `scripts/run_logistics_local_demo.py` plus `fixtures/scenarios/logistics/weekly_first_local_demo_seed.yaml` are now the user-facing local demo seed contract; the older `three_workflow_demo_story_seed.yaml` remains regression/reference coverage rather than the default start state.
- OpenAI honesty decision: weekly Stage04 local demoing stays on the real OpenAI path; the launcher output and runbook must call out `OPENAI_API_KEY` as required rather than silently downgrading behavior.
- Story-contract decision: the three-workflow demo contract now explicitly allows partial-progress linked runs and official-output summaries during the weekly-first walkthrough, while still preserving the fully linked reference seed for regression coverage.

## 2026-03-29 (TASK-0153 daily EOS intake, EOD review loop, finalize, and planning feedback)
- Daily-lane decision: the first implemented EPIC-125 reporting operator loop is now `Stage01/eos_input_intake -> deterministic Stage02/Stage03 workbook build -> Stage04/final_packet_review -> Stage04 approval`, and it stays fully inside the existing workflow/task/approval/artifact/pointer/handoff substrate.
- Intake-contract decision: `dispatch_reporting.v1` `Stage01/eos_input_intake` required uploads now carry explicit `artifact_role`; `reporting.eos_raw.workbook` is required `official_input`, while `reporting.eos_raw.doc` remains optional evidence only.
- Build-boundary decision: the first reporting build is intentionally bounded to the known EOS workbook family already represented by the repo's reporting workbook seam; unsupported workbook shapes fail closed instead of widening into a generic spreadsheet ETL engine.
- Review-surface decision: `Stage04/final_packet_review` is now the supported human-task EOD workpage surface, and completion keeps `outcome=complete` at the API boundary while backend lifecycle logic maps it to `draft_ready_for_manager_confirmation`.
- Finalize-trigger decision: approving a `dispatch_reporting.v1` `Stage04` `confirm_dispatch_reporting_packet` approval now auto-finalizes `reporting.final_packet.workbook`, promotes `official:reporting.final_packet.workbook`, and invokes the existing `reporting_actuals_to_future_planning` notify-only handoff.
- Staleness decision: daily finalize fails closed as `stable_base_schedule_required` if the reviewed draft workbook is no longer the latest draft workbook for the run; approval approval must not silently finalize a newer or different draft.

## 2026-03-29 (TASK-0152 weekly Friday intake, Stage04 build/review loop, and auto-publish)
- Weekly-lane decision: the first implemented EPIC-125 weekly operator loop is now `Stage04/weekly_input_intake -> Stage04/work_item -> Stage05/final_review -> Stage06 publish approval`, and it stays fully inside the existing workflow/task/approval/artifact/pointer substrate.
- Intake-contract decision: required-upload rows now carry explicit `artifact_role` and `required` flags; for weekly intake the three Stage04-ready workbook inputs are stored as `official_input`, actual-hours stays optional `official_input`, and route-horizon artifacts remain optional evidence only.
- Completion-semantics decision: the public task-complete API payload stays `outcome=complete`, while backend lifecycle logic now maps weekly intake/build/review completions to `inputs_ready`, `draft_ready_for_review`, and `draft_is_publish_ready` without adding a second UI command shape.
- Publish-trigger decision: approving a weekly `Stage06` `publish_weekly_base_schedule` approval now auto-runs the bounded weekly publish command inside `approvals.respond`, creating `planning.publish_packet.doc`, creating `planning.published_weekly_schedule.workbook`, and promoting `official:planning.published_weekly_schedule.workbook`.
- Staleness decision: weekly publish fails closed as `stable_base_schedule_required` if the reviewed draft is no longer the latest draft workbook; approval approval must not silently promote a newer or different draft.
- Frontend-copy decision: weekly task surfaces now use intake/build/review wording and expose `Run Stage04 Build` plus `Upload Input`/`Required input` copy on the relevant workspace and drawer surfaces, while keeping the existing route family and workpage submit flow unchanged.

## 2026-03-29 (TASK-0151 operational cadence contract, authoritative-input policy, and local-demo milestone)
- Next-epic decision: EPIC-125 is now the active post-EPIC-124 application epic, and `TASK-0151` is complete as the doc-only freeze before any weekly/daily operator-loop coding begins.
- Weekly-input decision: the first operational weekly machine-truth seam is Stage04-ready workbook input, not raw route email/doc parsing; raw route email/doc remains evidence only in EPIC-125.
- Daily-reporting decision: daily actual-routes truth stays in `dispatch_reporting.v1`, and the EOD review workpage remains attached to the generated reporting draft artifact rather than becoming a shortcut around finalization truth.
- Daily-replan decision: day-of schedule change in EPIC-125 is a minimal manual `live_dispatch.v1` delta lane over the existing seed activation and official delta promotion semantics, not widened weekly schedule editing and not live-dispatch candidate generation.
- Milestone decision: the first serious local FE/BE demo milestone is after `TASK-0155`, while the continuous production-shaped cadence/deploy milestone remains after `TASK-0156`.
- Hardening decision: EPIC-126 stays explicitly deferred until after real local-demo feedback exists; importing its planning/task/context memory does not authorize early hardening work.

## 2026-03-27 (TASK-0150 EPIC-124 closeout and regression-truth sync)
- Epic-closeout decision: EPIC-124 is now complete, and repo memory should describe stage-linked workpage actions, supported subject-link semantics, backend workspace projection, and frontend CTA handoff as implemented rather than as a future tranche.
- Boundary decision: closeout reaffirms that `workpage_actions[]` lives only on workspace work items, supported workpage create/submit flows accept at most one optional `subject_link`, graph nodes do not gain workpage actions, no second workpage route family or shell was added, and workpage access never becomes approval finalization.
- Verification-posture decision: the targeted frontend runner remains `npm --prefix frontend run test:run -- --fileParallelism=false ...` until the shared MSW artifact-map harness is parallel-safe; this is a test-harness note, not a product contract change.
- Cleanup decision: EPIC-124 closeout stays repo-tracked only; local untracked residue such as a repo-root `node_modules/` directory is not part of epic completion or source truth.
- Next-step decision: the next post-EPIC-124 app-facing epic remains intentionally unselected, and closing this epic does not imply Stage06/Stage07 widening, EOD finalization, or broader workspace rollout.

## 2026-03-27 (TASK-0147 backend requirement-aware artifact linkage and supported-surface policy)
- Requirement-counting decision: human-task requirement satisfaction is now relation-kind aware instead of raw-link-count based; legacy `schedule_planning.v1` upload requirements remain `attachment`-satisfiable only, while the first EPIC-124 rule allows only submitted `response` links to satisfy `weekly_schedule_planning.v1` Stage05 `information_request` for `planning.draft_weekly_schedule.workbook`.
- Workpage-write-boundary decision: canonical stage-linked workpage create/submit flows now accept at most one optional `subject_link` object (`subject_kind`, `subject_id`) and translate it into the existing artifact `links[]` seam internally; callers do not supply raw `links[]` or `relation_kind` on workpage routes.
- Supported-surface decision: schedule workpage submit may link only to the frozen supported Stage04/Stage05 human-task surfaces or Stage06 approvals, while dispatch-reporting EOD create/submit may link only to Stage04 approvals; unsupported subject surfaces now fail closed as `invalid_workpage_subject_link`.
- Demo-alias decision: `POST /api/v1/workpages/demo/eod-v0/drafts` explicitly rejects `subject_link` so the compatibility alias does not silently widen into a stage-linked truth surface.
- Verification-boundary decision: `TASK-0147` records the pre-existing `dispatch_reporting_workbook.py` `zip(..., strict=True)` EOD submit/read regression as an external baseline caveat and keeps its own EOD linkage verification focused on the new write-boundary behavior rather than broadening into that repair.

## 2026-03-27 (TASK-0148 backend workspace action projection and snapshots)
- Projection-seam decision: supported stage-linked workpage actions are now emitted only on workspace `user_work[]` / `blocking_work[]` items; graph nodes remain stage aggregates with no `workpage_actions[]`.
- Route-truth decision: workspace action routes, create paths, and submit handoff routes now share reusable helpers in `logistics_workpages.py` so the workspace projection cannot drift from canonical run-backed/artifact-backed workpage responses.
- Availability decision: weekly schedule work items now project either an available `open_route` action or an unavailable `schedule_draft_unavailable` action state based on actual Stage04 draft artifact truth, while dispatch-reporting Stage04 approvals project either `create_draft_then_open` or `open_route` based on EOD draft existence.
- Snapshot decision: backend-owned frontend fixtures now include explicit workspace action contract states for weekly available/unavailable and dispatch create/open posture.

## 2026-03-27 (TASK-0149 frontend workspace CTA rendering, handoff, and refresh truth)
- Frontend-contract decision: the frontend now consumes backend `workpage_actions[]` directly on normalized workspace items and defaults missing arrays to `[]`; it no longer infers supported workpage launches from task kind.
- Handoff decision: workspace CTA create flows now POST to backend-provided `create_path` values, and workspace-to-workpage navigation carries `workpageSubjectContext` through router state rather than URL/query params.
- Submit-boundary decision: schedule/EOD artifact submit pages now forward `subject_link` only when router state resolves to a valid same-run subject context; malformed or cross-run state is dropped without breaking direct route access.
- Refresh-truth decision: workspace CTA create success and workpage submit success now reuse one shared workspace invalidation helper so workspace/run-detail/query surfaces refresh together after stage-linked workpage changes.

## 2026-03-27 (TASK-0146 stage-linked workpage contract, supported matrix, and subject-link semantics)
- Contract-seam decision: the first stage-linked workpage action layer is now frozen as additive `workpage_actions[]` on workspace work items returned by `GET /api/v1/workflow-runs/{workflow_run_id}/workspace`; graph nodes do not gain workpage actions, and the repo does not add a separate action map, route family, or shell.
- Supported-surface decision: the first bounded support matrix is now explicit for selected `weekly_schedule_planning.v1` Stage04/Stage05/Stage06 workspace items and `dispatch_reporting.v1` Stage04 approval workspace items only; `/demo/logistics` story work items, `/board`, `/my-work`, `/approvals`, `/runs/:workflowRunId` detail tabs, `live_dispatch.v1`, Stage06 publish editing, Stage07 seed editing, and EOD finalization remain out of scope.
- Relation-kind decision: `draft` is now explicitly reserved for in-progress workpage association and never satisfies required uploads, required reviews, approval response, or completion/finalization truth; `response` is reserved for submitted workpage artifacts and is the only workpage-linked relation kind that later tasks may allow to satisfy supported requirements.
- Approval-boundary decision: opening or submitting a workpage from an approval-linked surface remains distinct from approval response and does not call `POST /api/v1/approvals/{id}/respond`.
- Baseline-caveat decision: the repo now records a pre-existing EOD submit-path regression in `tests/runtime/api/test_workpages_run_eod_contract.py::test_eod_workflow_run_workpage_uses_latest_draft_after_submit`, traced to `dispatch_reporting_workbook.py`, as a baseline reconciliation item rather than broadening `TASK-0146` into behavior work.

## 2026-03-26 (TASK-0143 backend schedule artifact projection, submit, and snapshots)
- Artifact-family decision: the existing generic artifact-backed workpage family now supports the bounded Stage04 schedule draft lane for `weekly_schedule_planning.v1` + `planning.draft_weekly_schedule.workbook`; the response envelope stays the same as EOD (`workpage`, `source`, `freshness`, `artifact_context`) and still leaves `run_context=null` / `draft_resolution=null`.
- Submit-boundary decision: schedule artifact submit is intentionally narrow and JSON-backed; it only allows bounded assignment/reserve row edits, creates a new immutable superseding `planning.draft_weekly_schedule.workbook` version, and keeps iteration deltas read-only.
- Snapshot decision: backend-owned frontend contract fixtures now include `fixtures/frontend_contracts/workpage_schedule_v0_artifact_state.json` and `fixtures/frontend_contracts/workpage_schedule_v0_artifact_submit_response.json`.

## 2026-03-26 (TASK-0144 frontend schedule artifact route, page, and landing handoff)
- Route-posture decision: the canonical schedule artifact route is now live at `/runs/:workflowRunId/workpages/schedule-v0/artifacts/:artifactVersionId`; there is still no demo schedule artifact alias route.
- Landing-handoff decision: the run-backed schedule landing now discovers the newest `planning.draft_weekly_schedule.workbook` from canonical workflow-run artifact truth and offers `Open editable draft` only through that lineage-aware route family.
- UX-boundary decision: the schedule artifact page now supports bounded assignment/reserve edits, explicit submit, recent draft history reopen, stale/conflict reopen, and truthful JSON download, while keeping Stage06 publish, Stage07 seeds, and live-dispatch semantics out of scope.

## 2026-03-26 (TASK-0145 EPIC-123 closeout and doc/demo posture sync)
- Epic-closeout decision: EPIC-123 is now complete. The repo should describe the Stage04 schedule artifact-backed slice as implemented, not as a reserved future posture.
- Scope-preservation decision: closing EPIC-123 does **not** authorize a `schedule-v0/drafts` create route, generic artifact editing, Stage06 publish/pointer semantics, Stage07 seed editing, or live-dispatch control expansion.
- Next-step decision: the next post-EPIC-123 application tranche should be selected deliberately rather than implied by stale workpage planning memory.

## 2026-03-26 (TASK-0142 schedule draft artifact path, route family, and stage boundary freeze)
- Next-epic decision: after EPIC-122 closeout, the repo now chooses **EPIC-123** as the next workpage epic; the next bounded workpage lane is the Stage04 schedule draft artifact path, not broader workspace/human-task integration.
- Artifact-boundary decision: `planning.draft_weekly_schedule.workbook` is now frozen as an immutable draft-review artifact in the canonical run chain, editable in a future workpage slice but not official weekly truth; `planning.manager_review.doc` remains evidence only.
- Route-posture decision: the canonical run-backed landing remains `/runs/:workflowRunId/workpages/schedule-v0`, the reserved canonical artifact route is `/runs/:workflowRunId/workpages/schedule-v0/artifacts/:artifactVersionId`, and the backend should reuse the existing generic `GET /api/v1/workpages/artifacts/{artifact_version_id}` / `POST /api/v1/workpages/artifacts/{artifact_version_id}/submit` family rather than inventing schedule-specific artifact endpoints.
- Creation-boundary decision: the first schedule artifact slice must not add `POST /api/v1/workpages/workflow-runs/{workflow_run_id}/schedule-v0/drafts`; the initial editable draft already exists as a Stage04 output artifact.
- Stop-line decision: Stage06 `planning.published_weekly_schedule.workbook`, Stage07 `planning.daily_dispatch_seed.*`, live-dispatch day-of replan, generic spreadsheet-editor scope, and broad workspace/task modernization all remain out of scope.

## 2026-03-26 (TASK-0141 demo/story drilldowns and workflow-run-backed workpage doc sync)
- Demo-shell discovery decision: `/demo/logistics` now presents canonical run-backed workpage links as the primary workpage entrypoints, derived from the single linked weekly-planning and dispatch-reporting runs in the current story; the old demo workpage routes remain available in a clearly labeled compatibility-alias section instead of the primary header path.
- Drilldown mapping decision: the family-node drilldown card now exposes `Open schedule workpage` for `weekly_schedule_planning.v1` runs and `Open EOD workpage` for `dispatch_reporting.v1` runs, while `live_dispatch.v1` remains workspace/detail-only in this epic.
- Alias-posture decision: `/demo/logistics/workpages/*` remains implemented and truthful for compatibility coverage, but the repo should no longer describe those routes as the primary or only discoverable access model once the canonical `/runs/{workflow_run_id}/workpages/*` surfaces are active.
- Epic-closeout decision: EPIC-122 now closes at canonical run-backed route discoverability plus doc/status sync; the next move should be framed as a new epic choice rather than a hidden `TASK-0142`.

## 2026-03-26 (TASK-0140 frontend workflow-run-backed workpage routes and canonical EOD artifact handoff)
- Frontend-route decision: the canonical workpage surfaces are now active under `/runs/:workflowRunId/workpages/schedule-v0`, `/runs/:workflowRunId/workpages/eod-v0`, and `/runs/:workflowRunId/workpages/eod-v0/artifacts/:artifactVersionId`; the existing `/demo/logistics/workpages/*` pages remain in place as compatibility aliases rather than the primary access model.
- Frontend-contract decision: the frontend now preserves optional `run_context` and optional `draft_resolution` in `WorkpageContract` so the canonical run-backed workpage responses are consumed directly instead of being flattened back into demo-only assumptions.
- Landing-handoff decision: the run-backed EOD landing now follows backend `draft_resolution` truthfully, showing `Create editable draft` only for `no_draft` and `Open latest draft` when a compatible workbook draft already exists for the reporting run.
- Artifact-route decision: artifact-backed EOD submit success and stale/conflict reopen flows now hand off to canonical `/runs/{workflow_run_id}/workpages/eod-v0/artifacts/{artifact_version_id}` routes; the frontend no longer relies on demo-only artifact route truth once the canonical pages are active.
- Scope decision: this tranche intentionally stops at canonical route activation and artifact handoff. Demo-shell header links and story drilldown entrypoints remain for `TASK-0141`.

## 2026-03-26 (TASK-0139 workflow-run-backed EOD landing, latest-draft resolution, and canonical draft create)
- Route implementation decision: the canonical `dispatch_reporting.v1` run-backed workpage access lane is now live at `GET /api/v1/workpages/workflow-runs/{workflow_run_id}/eod-v0` plus `POST /api/v1/workpages/workflow-runs/{workflow_run_id}/eod-v0/drafts`; the existing demo create alias remains in place as a compatibility/entrypoint surface until the frontend migration tranche.
- Landing-contract decision: the run-backed EOD landing route intentionally reuses the existing validated read-only EOD landing body, sets `source.mode=run_projection`, keeps `source.source_artifact_version_id=null`, adds `run_context`, and exposes EOD-only `draft_resolution` without overloading `artifact_context`.
- Latest-draft decision: run-backed EOD resolution now selects the newest compatible `reporting.upd_draft.workbook` artifact inside the supplied workflow run, accepting artifacts with no `demo_workpage_id` tag or `demo_workpage_id=eod-v0`, and returning canonical `/runs/{workflow_run_id}/workpages/eod-v0/artifacts/{artifact_version_id}` reopen routes.
- Freshness/source decision: the run-backed EOD landing now uses `freshness.source_kind=workflow_run_projection` and `freshness.source_version=<latest_draft_artifact_version_id|workflow_run_id>`, while `source.source_refs` point at matching workflow-run artifact-detail routes in EOD source order when those artifacts exist.
- Snapshot decision: backend-owned frontend contract fixtures now include `fixtures/frontend_contracts/workpage_eod_v0_run_state.json` and `fixtures/frontend_contracts/workpage_eod_v0_run_artifact_create_response.json`, generated from a real seeded reporting run.

## 2026-03-26 (TASK-0138 workflow-run-backed schedule route and snapshot)
- Route implementation decision: the first canonical EPIC-122 backend surface is now live at `GET /api/v1/workpages/workflow-runs/{workflow_run_id}/schedule-v0`; the existing demo schedule route remains in place as a curated alias/input surface until the frontend migration tranche.
- Projection-source decision: the run-backed schedule workpage now builds from the latest canonical Stage04 run artifacts on a real `weekly_schedule_planning.v1` workflow run (`planning.route_slot_requirements.workbook`, `planning.driver_capabilities.workbook`, optional `planning.approved_availability.workbook`, optional `planning.actual_hours_snapshot.workbook`) rather than serving a planning fixture verbatim or depending on the logistics story summary.
- Composite-contract decision: the run-backed schedule response uses `source.mode=run_projection`, keeps `source.primary_dataset_key=null`, keeps both `source_artifact_version_id` fields null, exposes `run_context`, leaves `draft_resolution=null`, and uses `freshness.source_kind=workflow_run_projection` plus `freshness.source_version=bundle.bundle_id` so local UI what-if state only resets when canonical source artifacts change.
- Failure-posture decision: unsupported workpage kinds and non-weekly workflow families fail closed as `404 workpage_not_found`, while weekly runs missing required Stage04 inputs now fail cleanly as `409 workpage_projection_unavailable` with explicit missing dataset keys instead of silently falling back to demo defaults.
- Snapshot decision: backend-owned frontend contract fixtures now include `fixtures/frontend_contracts/workpage_schedule_v0_run_state.json`, generated from a real seeded weekly run over canonical Stage04 artifact truth.

## 2026-03-26 (TASK-0137 workflow-run-backed workpage contract, alias posture, and draft-resolution freeze)
- Next-epic decision: after the first artifact-backed EOD slice closed through `TASK-0136`, the next workpage epic is **EPIC-122 workflow-run-backed workpages**, not schedule write-path work, not deeper EOD finalization, and not broader workspace/task modernization.
- Route-family decision: the canonical backend run-backed family is `GET /api/v1/workpages/workflow-runs/{workflow_run_id}/{workpage_kind}` plus `POST /api/v1/workpages/workflow-runs/{workflow_run_id}/eod-v0/drafts`; the existing artifact-backed EOD read/submit routes remain unchanged.
- Frontend-route decision: the canonical frontend posture is `/runs/:workflowRunId/workpages/schedule-v0`, `/runs/:workflowRunId/workpages/eod-v0`, and `/runs/:workflowRunId/workpages/eod-v0/artifacts/:artifactVersionId`, with `/demo/logistics/workpages/*` retained as curated aliases until the canonical routes are proven.
- Contract decision: run-backed workpages keep the existing body/source/freshness contract and add optional `run_context`; only the run-backed EOD landing adds `draft_resolution`, and `artifact_context` remains reserved for artifact-projection responses.
- Scope decision: schedule stays query-backed/composite, the EOD run-backed landing stays distinct from artifact-backed editing, this epic does not add a generic `actions` blob, and final-packet/approval semantics remain out of scope.

## 2026-03-25 (TASK-0136 demo entrypoints, recent draft history, and EPIC-121 close-out)
- Demo-shell entrypoint decision: `/demo/logistics` now exposes `Open EOD preview` and `Create editable EOD draft` in the existing backend-demo-workpages header group; the dispatch-reporting family-node detail card remains a separate reporting/story surface and does not claim that it is already the same artifact-draft lane.
- Landing-page decision: `/demo/logistics/workpages/eod-v0` remains preview/create-only. We still do not invent frontend-local "open latest draft" discovery there without canonical run truth.
- History-surface decision: the artifact-backed EOD page now reuses `GET /api/v1/workflow-runs/{workflow_run_id}/artifacts` for recent-version discovery, with the frontend filtering to `reporting.upd_draft.workbook` plus `demo_workpage_id=eod-v0` when metadata is present, rather than adding a new history route or client-only version list.
- Artifact-list decision: `GET /api/v1/workflow-runs/{workflow_run_id}/artifacts` must surface the canonical EOD draft chain for the bounded demo run so the recent-version panel reads authoritative workflow-run/artifact truth instead of older subject-attachment-only data.
- Epic-closure decision: EPIC-121's first bounded slice is now complete. The next decision should be framed as a new epic choice (deeper dispatch-reporting/workspace integration versus a future schedule artifact boundary), not as hidden widening inside this slice.

## 2026-03-25 (TASK-0135 frontend EOD artifact route migration)
- Route-posture decision: `/demo/logistics/workpages/eod-v0` remains the query-backed EOD landing page, but it is now preview-only with an explicit create-draft affordance; active EOD edits now live only on `/demo/logistics/workpages/eod-v0/artifacts/{artifact_version_id}`.
- Frontend-contract decision: the frontend workpage contract now preserves optional `artifact_context` so the same page composition can render both query-backed landing payloads and artifact-backed EOD state without inventing a second local schema.
- Mutation decision: draft creation and artifact submit now flow through dedicated frontend repository methods with generated idempotency keys, and successful create/submit navigation follows the backend-owned `route` field rather than reconstructing client-side paths.
- Conflict-handling decision: `workpage_artifact_conflict` now preserves current local edits in memory, surfaces an inline reopen panel, and avoids client-side merge/rebase logic in this tranche.
- Lineage/download decision: the first artifact-backed EOD page exposes only bounded lineage truth from `artifact_context` plus workbook download through the existing artifact binary route; richer recent-history discovery remains deferred to `TASK-0136`.

## 2026-03-25 (TASK-0134 backend EOD artifact draft/create/read/submit slice)
- Route-surface decision: the first artifact-backed EOD slice now exists as `POST /api/v1/workpages/demo/eod-v0/drafts`, `GET /api/v1/workpages/artifacts/{artifact_version_id}`, and `POST /api/v1/workpages/artifacts/{artifact_version_id}/submit`, while the existing query-backed `GET /api/v1/workpages/demo/eod-v0` landing page remains in place until the frontend migration tranche.
- Canonical-run decision: demo EOD draft creation now resolves or creates exactly one bounded `dispatch_reporting.v1` run for the known `SD-2026-03-16` demo slice using activation key `dispatch_reporting.v1:SD-2026-03-16:eod-v0:artifact-draft`; the backend does not invent a runless workbook lane.
- Artifact-truth decision: the first draft is seeded from `dispatch_reporting.stage03.upd_draft.workbook.empty.v1` and persisted as a normal immutable `artifact_version` with truthful metadata for template provenance, demo workpage scope, service date, station, DSP, and workbook file naming.
- Projection decision: artifact-backed EOD reads keep the existing wrapper and section/field ids stable for the frontend, but authoritative freshness now comes from `artifact_version` lineage and `source.mode=artifact_projection` rather than the older query-only seam.
- Submit decision: EOD submit now creates a new immutable superseding workbook artifact version, maps only bounded UI-backed edits into `ManualCloseout` and `UpdCandidates`, appends a server-managed changelog row, and fails closed with `409 workpage_artifact_conflict` when the base artifact already has a newer descendant.
- Snapshot decision: backend-owned frontend contract fixtures now include committed create/read/submit snapshots for the artifact-backed EOD slice so `TASK-0135` can switch the UI over without inventing frontend-local artifact payloads.

## 2026-03-25 (TASK-0133 reporting template pack, multi-registry support, and EOD workbook adapter)
- Template-pack decision: `dispatch_reporting.v1` now has a real repo-native `template_pack/` tree with a bounded Stage03 `reporting.upd_draft.workbook` workbook pair plus inert authored placeholders for the remaining dispatch-reporting `ARTIFACT_MAP` template paths so assurance can stay honest.
- Registry decision: template discovery is now multi-workflow and deterministic across `fixtures/workflows/*/template_registry.v1.yaml`, while `template_id` uniqueness is enforced across the full catalog and schedule consumers continue to pin `workflow_id="schedule_planning.v1"` explicitly.
- API-surface decision: `GET /api/v1/templates` now reports `registries[]` for the matching workflow packs and only populates singular `registry` metadata when the filtered response resolves to exactly one workflow registry.
- Workbook-seam decision: the first real workbook adapter remains workflow-specific and bounded to `dispatch_reporting.v1` Stage03 semantics; it projects workbook bytes into the EOD semantic tables and materializes explicit edits back to new workbook bytes without becoming a generic editor runtime.
- Dependency decision: `openpyxl` is now a core runtime dependency for the first truthful `.xlsx` round-trip seam, but imports stay isolated to the dispatch-reporting workbook adapter module so package-root lazy imports do not regress.

## 2026-03-25 (TASK-0132 artifact-backed EOD contract and route-family freeze)
- Epic-boundary decision: after the query-backed `EPIC-120` tranche, the next workpage tranche is the **first artifact-backed vertical slice**, not more query/demo polish.
- First-write-path decision: the first artifact-backed workpage is **EOD only**, aligned to `dispatch_reporting.v1` Stage03 draft/review semantics (`reporting.upd_draft.workbook`).
- Route-family decision: keep the existing demo query routes, add `POST /api/v1/workpages/demo/eod-v0/drafts`, `GET /api/v1/workpages/artifacts/{artifact_version_id}`, and `POST /api/v1/workpages/artifacts/{artifact_version_id}/submit`, and keep workflow-run-backed workpages reserved for later.
- Canonical-anchoring decision: do **not** invent runless demo artifacts. The first EOD drafts must live inside a canonical `dispatch_reporting.v1` workflow run, even if that run is resolved or created by a deterministic demo helper for the known service-date example.
- Save-semantics decision: explicit submit/save creates a new immutable artifact version that `supersedes` the prior workbook version. No in-place workbook mutation and no per-keystroke autosave into `artifact_versions`.
- Schedule-boundary decision: the schedule page remains **query-backed and composite** in this epic; do not force schedule into a single-artifact write model yet.
- Template-registry decision: the repo currently has template-pack/registry support concentrated on `schedule_planning.v1`; `TASK-0133` is now the next tranche because this epic needs a bounded `dispatch_reporting.v1` template pack and enough multi-workflow registry support to instantiate `reporting.upd_draft.workbook` truthfully.
- Workflow-integration decision: this epic stops at the first artifact-backed EOD slice and demo-shell entrypoints. Human-task/workspace integration is a later epic unless a bounded existing dispatch-reporting lane already supports it without broadening scope.

## 2026-03-25 (TASK-0131 HTTP-backed frontend workpage migration and local freshness)
- Frontend data-seam decision: the active `/demo/logistics/workpages/schedule-v0` and `/demo/logistics/workpages/eod-v0` routes now read backend demo query contracts through `onetruthApi.getDemoWorkpage()` and `workpagesRepository.schedule()` / `workpagesRepository.eod()` instead of frontend-local example adapters.
- Wrapper-visibility decision: the frontend now keeps the backend workpage wrapper visible instead of stripping it to the inner `WorkpageViewModel`; workpage pages render local `source` / `freshness` metadata because `AppShell` intentionally hides the global shell freshness banner on `/demo/logistics/*`.
- Local-state decision: workpage form/checklist edits remain local-only and are now reset only when the meaningful base contract identity changes; `freshness.generated_at` alone must not wipe local edits during refresh.
- Test-fixture decision: frontend MSW workpage handlers now serve the committed backend-owned snapshots from `fixtures/frontend_contracts/`, not hand-built inline workpage payloads.

## 2026-03-25 (TASK-0130 EOD demo workpage query route and snapshot)
- Query-surface decision: `GET /api/v1/workpages/demo/eod-v0` now exists as the second implemented backend-owned workpage route, reusing the shared `workpages.demo.detail` family instead of introducing a new EOD-specific route seam.
- Source-build decision: the EOD workpage payload is built from the consistent partial 2026-03-16 QDCI/DVC4 dispatch-reporting example family, not by serving `fixtures/logistics/workpages/eod_report_workpage_v0_view_model_example.yaml`.
- Partial-honesty decision: because the sanctioned EOD source family is intentionally partial, the backend contract now surfaces source-derived partial totals plus formula-integrity warnings instead of carrying the fixture's older full-day summary numbers into the authoritative query surface.
- Snapshot decision: `fixtures/frontend_contracts/workpage_eod_v0_state.json` is now a committed backend-generated contract fixture produced through the shared frontend snapshot export/check path.

## 2026-03-25 (TASK-0129 schedule demo workpage query route and snapshot)
- Query-surface decision: `GET /api/v1/workpages/demo/schedule-v0` is now the first implemented backend-owned workpage route, and it remains a read-only derived surface with request-context enforcement but no DB dependency.
- Compatibility decision: the wrapped inner workpage object still keeps `mode=example` and `dataset_key=planning.input_bundle.doc` for the current frontend `WorkpageViewModel` seam, while authoritative query semantics live in the top-level `source` and `freshness` wrapper.
- Source-build decision: the schedule workpage payload is built from the actual-ops weekly Stage04 normalized example pack through the existing schedule-control bundle builder, not by serving `fixtures/logistics/workpages/schedule_workpage_v0_view_model_example.yaml`.
- Snapshot decision: `fixtures/frontend_contracts/workpage_schedule_v0_state.json` is now a committed backend-generated contract fixture produced through the shared frontend snapshot export/check path.

## 2026-03-25 (TASK-0128 workpage query contract and snapshot policy freeze)
- Phase-boundary decision: once the frontend-only workpage tranche was complete, the next batch moved to **server-authoritative query contracts** before any submit/materialize path.
- Route-family decision: the workpage API family now reserves separate subfamilies for `demo`, `artifacts`, and potentially `workflow-runs` because the schedule page is composite and may later be run-oriented while EOD is the better first artifact-backed candidate.
- Composite-source decision: the shared workpage contract must support `primary_dataset_key` plus `source_dataset_keys[]`; a single `dataset_key` is not rich enough for the schedule page.
- Snapshot-policy decision: once backend workpage demo routes exist, their generated contract fixtures belong in `fixtures/frontend_contracts/` because they are backend-owned API snapshots, while the human-authored workpage YAML fixtures remain planning/oracle artifacts under `fixtures/logistics/workpages/`.
- Future-artifact decision: the first artifact-backed workpage should be **EOD**, not schedule, because `dispatch_reporting.v1` has the cleaner single-packet/workbook fit and the schedule page is intentionally composite.

## 2026-03-25 (EPIC-120 logistics workpages v0 implementation)
- Workpage-seam decision: the first workpage contract is an example-backed frontend `WorkpageViewModel` + `workpagesRepository`, not a fake `/api/v1/workpages/*` server contract.
- Route-structure decision: workpages are sibling full-page routes under `AppShell`, and logistics-shell behavior now treats `/demo/logistics/*` as logistics routes rather than matching only the exact `/demo/logistics` path.
- Discovery decision: primary navigation stays unchanged; workpage discoverability comes from the primary `/demo/logistics` shell and preserved logistics secondary-nav treatment across the `/demo/logistics/*` prefix.
- Schedule-boundary decision: the first schedule workpage remains a **weekly planning review + selected-day preview** surface. Any day-of controls in v0 are local what-if inputs only; day-of replan remains owned by `live_dispatch.v1`.
- EOD-boundary decision: the first end-of-day workpage is aligned to **dispatch-reporting draft/review semantics** and anchors to `reporting.upd_draft.workbook`, not `reporting.final_packet.workbook`.
- Fixture-consistency decision: the repo now carries a single partial 2026-03-16 QDCI/DVC4 reporting example family so the EOD prototype no longer mixes one source day's summary with another source day's route rows.
- Fixture-class decision: workpage fixtures remain human-authored planning/test artifacts under `fixtures/logistics/workpages/` and stay distinct from backend-owned generated `fixtures/frontend_contracts/` snapshots.

## 2026-03-17 (next package planning: productization lane + Workflow Lab lane)
- Planning decision: the next package is split into a leading **production lane** (`EPIC-100`) and a thinner **Workflow Lab lane** (`EPIC-110`) instead of treating productionization and experimentation as one blended platform task.
- Promotion decision: until explicit multi-version coexistence is proven, the default promotion model remains `lab evidence + review + tagged release -> production deploy`, not direct runtime transfer of candidate workflows into production.
- Lab-boundary decision: Workflow Lab Phase 0/1 may start now as docs/schemas/normalization over existing outputs, but heavier execution/comparison work is gated on explicit readiness checks (`G1`, `G2`) recorded in `docs/planning/PRODUCTION_AND_WORKFLOW_LAB_PLAN.md`.

## 2026-03-17 (TASK-0110 runtime dependency honesty and lazy package boundaries)
- Dependency-honesty decision: `PyYAML` is a core runtime dependency because repo-authoritative YAML is read by runtime modules under `src/onetruth/`; it must not be hidden behind the `dev` extra.
- Package-boundary decision: bare imports of `onetruth.infrastructure.definitions`, `onetruth.infrastructure.generation`, and `onetruth.integrations.openai` now stay lazy and load their heavy YAML-backed submodules only when exported symbols are actually accessed.
- Workflow Lab prerequisite decision: future thin lab/runtime surfaces should inherit this honest baseline rather than relying on transitive hidden dependencies from package-root imports.

## 2026-03-17 (TASK-0111 server-derived viewer bootstrap and shared-env frontend identity migration)
- Viewer-bootstrap decision: `GET /api/v1/viewer` is now the one read-only backend contract for frontend viewer/bootstrap state, derived directly from the resolved request context plus the frozen API boundary profile.
- Frontend-identity decision: browser-set `x-onetruth-*` identity headers remain available only for `local_dev` and `ci_test`; after shared-env viewer bootstrap, ordinary frontend API requests no longer send browser-owned identity/scope headers.
- UI-surface decision: the AppShell active-user switcher is now explicitly local-dev/demo-only, while shared environments render the server-derived viewer identity instead of implying browser-owned production identity.

## 2026-03-17 (TASK-0112 local_dev loopback guard and unsafe override contract)
- Startup-posture decision: the supported `onetruth-api` startup path now enforces `local_dev` loopback-only binds and refuses non-loopback hosts unless `ONETRUTH_UNSAFE_ALLOW_LOCAL_DEV_NON_LOOPBACK_BIND=1` is set.
- Scope decision: this task hardens the blessed CLI seam only; it does not redefine request-context trust semantics or claim to normalize every ad hoc raw `uvicorn onetruth.api.main:app` invocation style.
- Operator-guidance decision: repo docs now treat non-loopback `local_dev` binds as a controlled unsafe test escape hatch rather than a normal development or shared-environment posture.

## 2026-03-17 (TASK-0113 production/lab topology ADR and single-node deploy reference)
- Topology decision: first-user production and lab are now defined as separate single-node environments over the current implemented substrate (`SQLite + local filesystem artifacts`), not as one runtime with tenant/domain separation.
- Deploy-input decision: `release_source_bundle` is the only operator deploy artifact; `handoff_source_bundle`, `runtime_workspace_bundle`, and raw workspace archives remain non-deploy surfaces.
- Promotion-gate decision: the lab-to-prod connection remains a reviewed release process, not a third runtime/control-plane service, and Workflow Lab remains internal-only/non-authoritative in this tranche.

## 2026-03-17 (TASK-0114 backup/restore/rollback runbooks and rehearsal basis)
- Recovery-unit decision: the first-user recoverable unit is now frozen as the environment-specific SQLite DB file, the environment-specific artifact root, the matching `release_source_bundle` plus `bundle_manifest.json` / `release_provenance.json`, and secret/config references needed to rehydrate that environment.
- Operator-flow decision: rollback and restore are now explicitly separate operations, where rollback means redeploying a previous release against preserved current state, and restore means recovering DB/artifact state from a known backup set before reattaching it to the matching release bundle.
- Gate-honesty decision: the repo now documents a restore rehearsal basis, but it does not claim G1 is satisfied until real rehearsal evidence exists.

## 2026-03-18 (TASK-0115 observability baseline with health/readiness and safe metrics)
- Operability-surface decision: the thin API shell now exposes internal JSON operator endpoints at `GET /api/v1/ops/health`, `GET /api/v1/ops/readiness`, and `GET /api/v1/ops/metrics` without requiring request headers or shared-env principal resolution.
- Readiness decision: first-user readiness now fails only on core substrate unavailability (missing/unusable SQLite DB file or artifact root), while degraded-mode and projection-coherence visibility surface as warnings rather than redefining the node as unavailable.
- Metrics-safety decision: route metrics are process-local aggregates keyed only by `route_name`, `method`, and `status_family`; they intentionally omit request ids, tenant/domain values, actor identity, paths, route params, headers, and payload-derived data.

## 2026-03-18 (TASK-0117 Workflow Lab Phase 0 authority boundary and phased plan)
- Phase-0-boundary decision: Workflow Lab now has an explicit `docs/workflow_lab/` entrypoint, authority boundary, and phased-plan recap, and that Phase 0 surface is docs-only/non-authoritative by design.
- Authority decision: Workflow Lab outputs may exist as evidence or derived material, but they must not become workflow-defining semantics, promotion truth, direct production state, or a second semantics compiler.
- Gating decision: the repo now states more plainly that schema-first TASK-0118 is next, while TASK-0121 and TASK-0122 remain gated on `G1` and `G2`.

## 2026-03-18 (TASK-0118 Workflow Lab report/freshness and core schema pack)
- Schema-pack decision: Workflow Lab now has a thin machine-readable schema family for `freshness`, `variant_spec`, `run_profile`, `world_instance`, `run_report_core`, and `compare_report`, giving future normalization work a stable evidence contract without creating a lab runtime platform.
- Boundary decision: `VariantSpec` is now explicitly reserved for execution variation under fixed semantics, while `RunProfile`, `WorldInstance`, and `CompareReport` stay metadata-only shells rather than submission policy, world-materialization, or semantic-version engines.
- Validation decision: repo schema validation now covers `schemas/workflow_lab/*`, and the next non-gated Workflow Lab step is TASK-0119 normalization over existing Stage04/scheduling/certification outputs.

## 2026-03-18 (TASK-0119 Workflow Lab normalization over existing outputs)
- Normalization decision: the repo now emits adjacent `workflow_lab_run_report.json` and `workflow_lab_review_packet.md` artifacts from three existing output families: weekly Stage04 pilot packets, realistic schedule-planning pilot packets, and current capability certification scenarios.
- Certification-scope decision: capability certification normalization is per scenario row, not one aggregate certification-level `run_report_core`, so each scenario keeps its own evidence/report boundary.
- Boundary decision: TASK-0119 added no `compare_report` generation, no execution adapters, no freshness guards, no public Workflow Lab surface, and no `src/onetruth/workflow_lab/` package; the next Workflow Lab step is TASK-0120 gate/release documentation.

## 2026-03-18 (TASK-0120 Workflow Lab promotion gate and G1/G2 freeze)
- Gate-contract decision: `docs/workflow_lab/PROMOTION_GATE.md` is now the authoritative repo-native reference for the release-mediated promotion gate `G` and the current status of readiness gates `G1` and `G2`.
- Gate-honesty decision: both `G1` and `G2` remain explicitly uncleared; the repo now says plainly that contract/docs alone do not clear an operational gate and that recorded evidence is required where specified.
- Routing decision: `TASK-0121` and `TASK-0122` now point directly at `docs/workflow_lab/PROMOTION_GATE.md` as the first proof source for unblocking, so later Workflow Lab work cannot quietly bypass the recorded-gate requirement.

## 2026-03-18 (TASK-0116 GitHub perimeter hardening and mock-vs-live OpenAI split)
- Workflow-provenance decision: repo-managed GitHub Actions workflows now pin external actions to verified full commit SHAs instead of floating major tags.
- Perimeter-workflow decision: pull requests now have an explicit `dependency_review` workflow, and Python plus JavaScript/TypeScript code scanning now lives in a dedicated `codeql` workflow for pull_request / push-to-main / schedule.
- OpenAI-lane decision: `agent_api.yml` is now the scheduled/manual mock lane over `ci-fast-backend`, while `agent_api_live.yml` is the manual gated real OpenAI workflow that expects live secrets and preserves the existing weekly Stage04 dual gate.

## 2026-03-17 (TASK-0108 structured API boundary logging)
- Boundary-observability decision: the API shell now emits compact JSON-line records through logger `onetruth.api.boundary` with three fixed event names: `request_started`, `request_finished`, and `request_failed`.
- Safety decision: boundary logs keep a strict allowlist of request-context and mutation-correlation fields only, and intentionally do not log bodies, bearer tokens, raw headers, actor roles, large payload fields, `actor_id`, or exception text.
- Correlation decision: finish logs reuse existing route metadata plus existing receipt-backed mutation ids when those ids are already present in API responses, while `x-request-id` remains a header-only seam and is not propagated into JSON payloads or timeline-event correlation.

## 2026-03-17 (TASK-0109 assurance-domain split and truthful validator entrypoints)
- Assurance-structure decision: `scripts/validate_repo.py` remains the one umbrella entrypoint, but the implementation now lives under `scripts/repo_assurance/` with explicit `schema_governance`, `repo_metadata`, `release`, `secrets`, and `traces` modules plus a small shared `core`.
- CLI-truth decision: repo assurance now exposes a repeatable `--domain` selector for exactly `schema`, `governance`, `metadata`, `release`, `secrets`, and `traces`; `--schemas-only`, `--traces-only`, and `--secrets-only` remain compatibility aliases, `make assurance-fast` is the preferred non-trace aggregate, and `make schema-validate` remains an alias for that fast path.
- Release-portability decision: release validation now preflights for a live git checkout, a resolvable git toplevel, and a committed `HEAD`, and reports stable `release validation unavailable: ...` failures instead of surfacing raw clone/git mechanics; this does not relax `release_source_bundle` policy or add support for arbitrary unpacked trees as full release inputs.

## 2026-03-17 (TASK-0107 route-registry modularization)
- Control-plane structure decision: route metadata now lives in resource-scoped `src/onetruth/api/route_specs/*.py` modules plus a tiny shared `_core.py`, while `src/onetruth/api/route_registry.py` remains the single public assembly point for `ROUTES` and `match_route`.
- Parity decision: the assembled registry preserves the exact global route order, suffix precedence, request-body policy metadata, and the current permissive-vs-strict path quirks; no handler, payload, or trust-boundary semantics changed in this tranche.
- Fitness decision: contract coverage now forbids route-spec modules from importing each other, `api.main`, or `route_registry.py`, forbids `route_registry.py` from importing route handlers directly, and keeps route modules plus `main.py` from depending on `route_specs` directly.

## 2026-03-14 (TASK-0101 shared_env JWT principal resolver)
- Shared-env identity decision: when `ONETRUTH_SHARED_ENV_JWT_ISSUER`, `ONETRUTH_SHARED_ENV_JWT_AUDIENCE`, and `ONETRUTH_SHARED_ENV_JWT_PUBLIC_KEY_PEM` are all configured and no explicit resolver is injected, `shared_env` now resolves request context from `Authorization: Bearer <JWT>` using offline `RS256` verification.
- Boundary decision: `local_dev` and `ci_test` keep the existing trusted-header path unchanged, trusted-header CORS remains local-dev-only, and conflicting `x-onetruth-*` headers are ignored in `shared_env`.
- Scope decision: the shared-env attested resolver uses one fixed claim mapping (`sub`, `tenant_id`, `domain_id`, `actor_type`, `actor_roles`) and intentionally does not add JWKS fetch, token introspection, or broader authz changes in this tranche.

## 2026-03-14 (TASK-0100 release bundle only distribution path)
- Distribution-path decision: `release_source_bundle` is now the only endorsed operator/share source artifact; `handoff_source_bundle` remains internal review/Codex-only and raw workspace/manual zips are explicitly non-release.
- Provenance decision: release exports now include a deterministic repo-owned `release_provenance.json` sidecar with bundled-file digests, curated manifest/lockfile entries, and archive/commit metadata instead of escalating to a full SPDX/CycloneDX rollout.
- Operator-path decision: `make clean-source-bundle` now points at the release export path, while `make handoff-source-bundle` preserves the internal working-tree-sensitive review snapshot.

## 2026-03-14 (TASK-0099 CI topology split and security required gates)
- CI-lane decision: pull-request feedback now splits into parallel fast required backend lanes (`lint`, `contract`, `unit`, `security`), one separate `runtime-required` lane, and the standalone `frontend` lane instead of one monolithic backend job.
- Guardrail-workflow decision: `secret_hygiene` remains a separate PR-capable workflow boundary rather than being folded into the main workflow's `security` job, while `release-confidence` is reserved for `push` to `main` and `workflow_dispatch`.
- Aggregate-target decision: local/CI Make truth now uses `ci-fast-backend` and `ci-runtime-required`, `ci-backend` remains the aggregate alias over both, and `agent_api.yml` now reuses only the fast backend aggregate before the existing gated OpenAI tests.

## 2026-03-14 (TASK-0098 frontend transport v2 cutover and clean-install truth)
- Frontend transport decision: frontend/client download flows now call sibling `.bin` routes directly and do not keep a silent client-side fallback to the legacy JSON `/download` endpoints.
- Client-boundary decision: binary download handling now relies on attachment headers (`content-disposition`, `content-type`, `content-length`, `x-request-id`) through a narrow `requestBinary()` seam, while backend error behavior remains the existing JSON `ApiError` envelope.
- Install-truth decision: clean `npm ci` from `frontend/package-lock.json` is the only documented/supported frontend install baseline; vendored `node_modules` is not treated as runnable source truth.

## 2026-03-14 (TASK-0097 binary artifact/template download transport v2)
- Transport-shape decision: binary download v2 ships as sibling `.bin` routes for artifacts and templates, while the existing `/download` JSON+base64 routes remain explicit compatibility surfaces in this tranche.
- Boundary decision: binary success responses now return raw bytes with attachment headers, but failure behavior remains the existing JSON error envelope so scope/cross-tenant denial and not-found contracts stay stable.
- Scope-boundary decision: this tranche improves download transport only; it does not redesign uploads, migrate frontend callers, or reopen artifact metadata, pointer, provenance, or trust semantics.

## 2026-03-14 (TASK-0096 deterministic API payload hardening)
- Boundary-contract decision: JSON POST routes now enforce deterministic media-type and size contracts at the shell boundary, so non-empty wrong/missing media type returns `415 unsupported_media_type`, oversize envelopes return `413 payload_too_large`, and existing empty-body/malformed-body `400` contracts remain intact once those checks pass.
- Route-policy decision: the declarative API route registry now carries explicit request body policies instead of a loose `body_mode`, with a bounded `256 KiB` ceiling for ordinary JSON command routes and a bounded `2 MiB` ceiling for JSON artifact-ingress routes.
- Scope-boundary decision: this tranche hardens JSON boundary parsing only; it does not redesign artifact transport, add multipart/binary upload support, or change trust/profile semantics.

## 2026-03-14 (TASK-0095 declarative route registry)
- Shell-structure decision: API route metadata, match order, body expectations, and dispatch targets now live in one ordered declarative registry instead of parallel handwritten `_match_route()` and `_dispatch_route()` switches.
- Parity decision: the registry preserves current route precedence and the existing permissive-vs-strict slash behavior for selected suffix routes such as `/claim`, `/respond`, `/transition`, and `/timeline`; this tranche does not tighten path semantics.
- Scope-boundary decision: the refactor stays framework-free and shell-only, with no endpoint-module rewrites, no JSON payload changes, no trust-boundary changes, and no request-id/event-correlation expansion.

## 2026-03-14 (TASK-0094 API shell characterization and request-id seam)
- Shell decision: the current hand-rolled API shell now has focused characterization coverage for route misses, malformed JSON, unsupported scopes, and internal-error fallback before any route-registry refactor.
- Correlation decision: every API response now emits a header-only `x-request-id` seam, with safe incoming values echoed and missing/unusable values replaced by generated `httpreq_<hex>` ids.
- Scope-boundary decision: this tranche does not add request ids to JSON payloads, does not propagate them into timeline-event `correlation_id`, and does not change the frozen `shared_env` trust posture.

## 2026-03-14 (TASK-0093 human-task mutation family extraction)
- Extraction decision: `claim_human_task_command`, `complete_human_task_command`, and `confirm_human_task_review_command` now live in `src/onetruth/application/handlers/human_tasks.py` behind lazy compatibility wrappers in `workflow_task_lifecycle.py`.
- Helper-seam decision: the extracted family depends on the neutral command-boundary seam plus a private `src/onetruth/application/handlers/_shared/artifact_effects.py` helper closure for confirm-review support, so no extracted module needs to re-import the legacy hotspot.
- Scope-boundary decision: this tranche moved only the human-task mutation family and its private confirm-review support helpers; read-side task queries, public artifact commands, caller modules, and capability semantics remain unchanged.

## 2026-03-14 (TASK-0092 neutral command-boundary helper seam)
- Helper-seam decision: the extracted approvals family now depends on `src/onetruth/application/handlers/_shared/command_boundary.py` for shared command-boundary primitives instead of importing them from `workflow_task_lifecycle.py`.
- Compatibility decision: `workflow_task_lifecycle.py` remains import-compatible through helper re-exports and lazy approval wrappers, but extracted handlers and `_shared/` modules must not re-import the legacy hotspot directly.
- Scope-boundary decision: only the receipt/error/scope/event-envelope helper cluster moved in this tranche; no additional handler family extraction and no approval/capability semantics changed.

## 2026-03-14 (TASK-0091 dependency automation, secret scanning, and operator-only follow-ups)
- Automation decision: repo-native update automation now exists for the actual mutable dependency surfaces in this repo: Python (`pip` at `/`), frontend (`npm` at `/frontend`), and GitHub Actions metadata.
- Secret-scan decision: tracked-file secret hygiene now has a dedicated workflow boundary via the repo validator's secret-only mode; the current preferred invocation is `python scripts/validate_repo.py --domain secrets`, with `--secrets-only` retained as a compatibility alias.
- Operator-boundary decision: secret revocation confirmation, Git history rewrite, and hosted GitHub push-protection/settings changes remain operator/admin follow-ups and must not be treated as Codex code-task completion.

## 2026-03-14 (TASK-0090 bootstrap/install truth closure and tracked build-artifact ban)
- Baseline decision: the repo's validated package metadata now matches the established dev/CI baseline exactly, so `pyproject.toml` requires Python `>=3.11,<3.12` instead of claiming a broader support floor.
- Install-path decision: local bootstrap guidance, CI workflows, and the compatibility `requirements.txt` shim now all converge on one authoritative backend install path: `python3.11 -m pip install -e ".[api,dev]"`.
- Source-boundary decision: tracked `*.egg-info` content is now explicitly forbidden by repo validation and excluded from release source bundles, while intentionally tracked generated outputs under `build/generated/` remain unchanged.

## 2026-03-13 (truth-alignment backlog sync)
- Numbering-source decision: the external truth-alignment prompt pack is canonical for the new tranche, so `TASK-0076` is board/query-surface stability and `TASK-0077` is the capability-lattice freeze task.
- Backlog-hygiene decision: the duplicate historical cleanup trio was renumbered to `TASK-0087` / `TASK-0088` / `TASK-0089`, while `TASK-0071` / `TASK-0072` / `TASK-0073` now refer only to the Stage04 progression.
- Alias decision: renumbered historical task briefs keep short deprecated-alias notes so future sessions can map old references without reopening the duplicate-ID ambiguity.
- Validation decision: backlog validation now needs to fail on duplicate task-file IDs and duplicate task-index rows so this class of drift cannot hide behind prefix collisions.

## 2026-03-13 (TASK-0086 approvals-first hotspot extraction)
- Extraction decision: the first controlled hotspot move pulls only the approvals family out of `src/onetruth/application/handlers/workflow_task_lifecycle.py` into `src/onetruth/application/handlers/approvals.py`; task, flag, artifact, and execution families stay in place for later tranches.
- Compatibility decision: existing callers keep importing approval commands from `workflow_task_lifecycle.py`, which now re-exports the moved behavior through thin lazy wrappers so the physical extraction proves out without caller churn.
- Characterization decision: direct unit coverage now compares the legacy wrapper surface and the new module surface against the same in-memory runtime substrate, freezing approval request/respond row shapes, event payloads, and forbidden-error semantics before any later helper or import cleanup.

## 2026-03-13 (TASK-0085 bootstrap truth, CI honesty, and governance cleanup)
- Bootstrap decision: `scripts/doctor.py` is now the single blessed local entrypoint for lightweight deterministic environment checks; there is no parallel shell bootstrap path in this tranche.
- Python-baseline decision: the validated dev/CI baseline is Python `3.11`, but the task does not change the broader package metadata support floor; doctor verifies that a Python 3.11 interpreter is available even when the invoking `python3` is older.
- CI-honesty decision: `make lint`, `make ci-backend`, `make frontend-ci`, and `make ci` now describe distinct real check slices instead of overloading lint with contract tests or rerunning blanket `pytest -q` in scheduled OpenAI CI.
- Governance decision: CODEOWNERS now uses only existing root-anchored paths with a real temporary owner target (`@tylerclark`), and the repo now carries explicit MIT and Node 20 declarations via `LICENSE` and `.nvmrc`.

## 2026-03-13 (TASK-0084 explicit bundle kinds and exported-payload validation)
- Bundle-classification decision: source/export packaging now uses three explicit bundle kinds: `handoff_source_bundle` for working-tree-sensitive review/handoff snapshots, `release_source_bundle` for clean tracked commit snapshots, and `runtime_workspace_bundle` for run inspection/evidence exports over canonical runtime truth.
- Release-contract decision: `release_source_bundle` always exports tracked files only, requires `HEAD`, and fails closed unless the tracked worktree is clean under `git status --untracked-files=no` semantics.
- Manifest decision: both source bundles and runtime workspace bundles now write a `bundle_manifest.json` so downstream consumers can classify the archive without inferring semantics from the script name alone.
- Validation decision: `scripts/validate_repo.py` now inspects a real exported `release_source_bundle` payload from a temporary clean clone of `HEAD`, so full-repo validation can verify the actual archive contents without being blocked by a dirty development worktree.

## 2026-03-13 (TASK-0082 scoped command receipts and replay)
- Retry-contract decision: canonical CLI/API command-boundary retries now resolve through scoped `command_receipts`, so same-scope retries with the same normalized request replay committed success with `idempotent_replay=true` and stable `receipt` metadata instead of surfacing `duplicate_idempotency_key`.
- Mismatch decision: reusing the same `(command_name, scope_key, idempotency_key)` tuple with a different normalized request now fails closed as `command_receipt_mismatch` (`409`) rather than replaying or mutating again.
- Scope decision: the same client `idempotency_key` may be reused safely across different command scopes; receipt uniqueness is `(command_name, scope_key, idempotency_key)` rather than a single global key.
- Boundary decision: raw `events append` keeps explicit event-store duplicate failure semantics (`duplicate_idempotency_key`), so receipt replay changes only the public mutation boundary and not low-level event append behavior.

## 2026-03-13 (TASK-0083 shared read-model seam and route-boundary fitness)
- Layering decision: the five shared HITL list/query helpers (`workflow_runs`, `human_tasks`, `approvals`, `flags`, `pointers`) now live under `src/onetruth/api/queries/` instead of being borrowed from sibling route modules.
- Fitness decision: contract coverage now fails if any module under `src/onetruth/api/routes/` imports another route module directly, closing the specific layering smell without introducing a broader API framework.
- Scope decision: this task moved only the shared read-helper seam; board card assembly, logistics story composition, workspace/detail shaping, and public payload contracts remain unchanged, with the logistics story still primary and the schedule-only board still legacy/internal.

## 2026-03-13 (TASK-0081 shared HTTP artifact ingress split)
- Boundary decision: shared HTTP artifact ingress (`/api/v1/artifacts/ingest` and subject upload endpoints) now accepts request bytes only and rejects caller-controlled `source_path` and `storage_root`.
- Provenance decision: shared HTTP ingress records `metadata_json.ingress_kind=request_bytes` and strips caller-supplied `seed_source_path` / `ingress_source_path`, while CLI/scenario/internal local seeding keeps normalized source-path metadata with `ingress_kind=local_source_path`.
- Compatibility decision: CLI `artifacts ingest`, `artifacts seed-corpus`, and scenario-backed local seeding remain on the same canonical artifact path and were not removed or redesigned in this task.

## 2026-03-13 (TASK-0080 write-boundary capability enforcement)
- Enforcement decision: claim, complete, confirm-review, approval respond, and flag transition now consume the frozen shared capability decisions at the canonical write boundary before mutating rows or appending events.
- Error-honesty decision: capability/principal denials now return explicit forbidden codes (`task_claim_forbidden`, `task_complete_forbidden`, `task_confirm_review_forbidden`, `approval_respond_forbidden`, `flag_transition_forbidden`) with structured `capability_id` / `reason_codes` / `reasons`, while state-machine conflicts remain on the existing conflict codes.
- Caller-contract decision: role-gated non-HTTP callers (CLI/scenario/pilot/certification paths) must now pass explicit `actor_roles`; the runtime no longer relies on implicit role inference for `tasks.claim`, `approvals.respond`, or `flags.transition`.
- Collaboration decision: artifact upload remains an intentionally broader collaboration/evidence surface; this task hardens other writes without introducing a new `artifact_upload_forbidden` path.

## 2026-03-13 (TASK-0076 board stability and query-surface classification)
- Compatibility decision: `GET /api/v1/board/schedule-planning` now uses the current pointer-query contract and returns the documented board payload without redesigning that endpoint.
- Surface-classification decision: `GET /api/v1/stories/logistics-three-workflow` and frontend route `/demo/logistics` remain the primary logistics surfaces; the schedule-only board stays legacy/internal regression coverage.
- Layering decision: the route-to-route import seam remains a known smell and is explicitly deferred to `TASK-0083` rather than being broadened inside this board-stability patch.

## 2026-03-13 (TASK-0077 capability lattice freeze)
- Lattice decision: routing, claim, complete, specialized execute, collaborate/upload, approval response, and flag transition are now frozen as distinct capability axes, with one authoritative matrix in `docs/architecture/human_task_semantics.md`.
- Role-semantics decision: `candidate_roles` gate human-task claim and act as fallback approval routing only; `required_role` wins for approval response when present; assignee state anchors completion and specialized execute attempts.
- Drift decision: current write handlers and some role lists are still less strict than the frozen lattice, and that mismatch remains intentionally deferred to `TASK-0078`, `TASK-0080`, and `TASK-0081` rather than being hardened in this semantics-only tranche.

## 2026-03-13 (TASK-0078 API boundary profiles and principal resolver seam)
- Boundary-profile decision: the thin HTTP adapter now has explicit `local_dev`, `ci_test`, and `shared_env` trust profiles, with `shared_env` as the default when nothing is configured.
- Fail-closed decision: `shared_env` no longer falls back to ambient trusted headers; it returns `503 principal_resolver_unavailable` unless a non-header principal resolver is injected at app creation.
- Local-affordance decision: trusted `x-onetruth-*` headers remain available only in `local_dev` and `ci_test`, and trusted-header CORS is reflected only for loopback local-dev origins.
- Test-harness decision: runtime API helpers now opt into `ci_test` explicitly so existing ASGI tests preserve their current semantics while the production/default API posture becomes fail closed.

## 2026-03-13 (TASK-0073 weekly Stage04 live TPM compaction and bounded 429 recovery)
- Model-surface decision: the Stage04 runtime now keeps the same deterministic tool set and canonical artifact/evidence chain, but the model sees compact Stage04 context summaries and compact tool-output deltas instead of repeated full context packs, route allocations, coverage lists, or finalize candidate payloads.
- Evidence decision: full deterministic tool outputs remain persisted verbatim in `runtime.tool_result.json` and execution traces, while the Responses continuation loop records a separate compact `model_output_json` for the `function_call_output` payload actually sent back to the model.
- Retry-safety decision: `rate_limit_exceeded` handling is now narrowly retried inside the same Responses turn with bounded `Retry-After`/message-derived backoff, preserving idempotency by not executing deterministic tools until a model response succeeds.
- Traceability decision: per-turn request evidence and failed execution traces now record retry attempts/history plus the last failed request details so fresh-live 429 failures stay reviewable and distinguishable from deterministic Stage04 failures.

## 2026-03-13 (TASK-0072 weekly Stage04 iterative deterministic allocation)
- Planner-ownership decision: Stage04 weekly allocation remains deterministic-code-owned truth, but now advances through an explicit partial-schedule loop with adaptive 5-10 route batches instead of a single global top-pick pass.
- Repair-boundary decision: bounded local repair moves are allowed inside the deterministic allocator to free capacity or preserve continuity, but repairs stay narrowly scoped to already-selected local assignments rather than broad weekly rewrites.
- Hard-rule decision: driver-day availability state, overlap/rest protection, max shifts, and rolling-7 limits are now evaluated against the evolving partial schedule, not only against static source artifacts.
- Stability decision: previous-week continuity is now a first-class scored term carried through candidate evaluation, final selections, validation summaries, and draft schedule artifacts so week-to-week churn is explicit and reviewable.
- Artifact-shape decision: Stage04 keeps the same final artifact keys (`planning.input_bundle.doc`, `planning.candidate_schedule_delta.workbook`, `planning.validation_summary.doc`, `planning.draft_weekly_schedule.*`), but their payloads now expose per-iteration deltas, coverage gaps, churn/repair counts, and score tradeoffs.

## 2026-03-13 (TASK-0071 weekly Stage04 over-capacity realistic handoff refresh)
- Fixture-contract decision: the default realistic weekly Stage04 pilot now uses the over-capacity `PW-2026-W12` hard case (40 active drivers, 139 route slots, positive daily feasible surplus) instead of the prior `PW-2026-W10` shortage-style fixture.
- Adapter decision: the realistic Stage04 source-material path is now grounded in repo-authored over-capacity example YAMLs and may add deterministic helper fields for bridge/runtime use without changing workflow IDs, stage IDs, or final Stage04 artifact keys.
- Compatibility decision: the tiny two-driver smoke fixture remains unchanged for lightweight deterministic/runtime regression coverage while the realistic contract moves to explicit day-level availability/history semantics.

## 2026-03-13 (TASK-0071 weekly Stage04 realistic artifacts and fixtures bundle)
- Bridge-payload decision: weekly Stage04 keeps the same canonical artifact kinds, but the payloads now support richer day-resolution planning context including per-driver planning-week states, prior-week state, rolling-7 snapshots, daily demand summaries, and policy signals.
- Backward-compatibility decision: the existing tiny two-driver Stage04 scenario and pilot remain the smoke/regression baseline; richer payload parsing is additive and defaults cleanly when those new fields are absent.
- Shared-fixture decision: one deterministic realistic source-material fixture under `fixtures/logistics/weekly_stage04_realistic_source_material.yaml` now drives both the new hard-case pilot seed path and richer test coverage so the 40-driver day-resolution input shape stays reproducible.
- Scope decision: the realistic slice still uses the same Stage04 deterministic build/runtime architecture, draft-only artifact path, and bounded Responses tool loop; no new workflow IDs, stage IDs, truth paths, or iterative planner behavior were introduced.

## 2026-03-13 (TASK-0073 weekly Stage04 iterative agent loop and analysis)
- Tool-boundary decision: weekly Stage04 now exposes iterative deterministic tools (`context`, `preview`, `apply`, `validation`, `iteration_analysis`, `finalize`) instead of a one-shot build tool, and the model remains an orchestration/search controller rather than a schedule allocator.
- Finalization decision: Stage04 draft artifacts are materialized only through an explicit deterministic finalize tool call; the runtime no longer performs unconditional post-loop build/finalization after the model stops requesting tools.
- Evidence decision: canonical runtime evidence now persists per turn/iteration via repeated `runtime.tool_request.json` and `runtime.tool_result.json` artifacts plus an execution trace that links turn evidence refs, progress state, and finalize outcome.
- Stop-policy decision: authored Stage04 `no_progress_ticks` from compiled control metadata is now enforced at runtime, so repeated context/inspection-only turns fail closed with visible evidence instead of silently spinning.
- Inspection-packet decision: realistic weekly pilot packets now surface iteration-level route allocations, uncovered-route carryover, repair moves, runtime turn summaries, and fallback tradeoff notes derived from canonical artifacts/evidence rather than only listing IDs.

## 2026-03-13 (TASK-0089 Stage06 compiled-control alignment and tool-class vocabulary cleanup)
- Control-alignment decision: the bounded Stage06 sandbox now derives its pinned execution semantics from the authored `schedule_planning.v1` Stage06 execution profile plus a registry-backed runtime tool binding instead of a hardcoded `execution_spec_id`.
- Vocabulary decision: authored `allowed_tool_classes` remain capability-level execution-profile vocabulary, while `tool_execution.tool_class` remains the concrete engine/runtime identifier for the bounded executor; these are related through explicit runtime tool bindings, not by reusing the same string set.
- Safety decision: the Stage06 OpenAI runtime binding is validated to use only authored capability classes already allowed by the Stage06 execution profile and fails closed if the binding drifts outside that authored allowlist.
- Scope decision: the legacy Stage06 sandbox remains a regression/reference-only bounded single-call review path; this cleanup aligns metadata and audit shape without broadening Stage06 autonomy or re-promoting `schedule_planning.v1` as the primary agent surface.

## 2026-03-13 (TASK-0074 weekly Stage04 input-resolution hardening)
- Binding-resolution decision: weekly Stage04 bridge inputs are now resolved through an explicit typed dataset-key registry (`route_slot_requirements`, `driver_capabilities`, `approved_availability`, `actual_hours`, `route_horizon`) rather than suffix-scanning `required_evidence_keys`.
- Authored-source decision: the Stage04 input registry is validated against repo-native weekly workflow source (`WORKFLOW_CONTRACT.yaml`, `ARTIFACT_MAP.yaml`, `EXECUTION_PROFILE.yaml`) so control/runtime drift fails closed.
- Control-spec safety decision: compiled Stage04 metadata now rejects missing required bridge bindings and alias-equivalent conflicting keys (for example mixed `planning.*` and `dispatch.*` bridge keys for the same slot) instead of silently picking one by suffix.
- Runtime safety decision: the bounded weekly Stage04 agent still resolves the latest matching artifact version per exact dataset key, but now returns explicit `stage04_input_artifact_missing` errors when required bridge artifacts are absent.

## 2026-03-13 (TASK-0087 repo hygiene cleanup for local state and tracked outputs)
- Repo-boundary decision: the default runtime evidence root (`.onetruth_artifacts/`), local SQLite DBs, `.DS_Store`, and Codex handoff zips are local machine outputs and must not be tracked as repo source.
- Fixture-boundary decision: the tracked `.onetruth_artifacts/` contents audited in this cleanup were live execution evidence only, not golden fixtures; any future reusable evidence must move into an explicit `fixtures/` path.
- Ignore-rule decision: Git ignore coverage now explicitly blocks `.onetruth_artifacts/`, local DB files/journals, and `codex_handoff_packet_*.zip` so local runs stop re-polluting the repo.
- Diff-hygiene decision: normalized the small formatting-only noise spot in `src/onetruth/integrations/openai/responses_agent_runner.py` so the cleanup diff stays `git diff --check` clean.

## 2026-03-12 (TASK-0070 weekly Stage04 pilot + real-network gate hardening)
- Pilot reproducibility decision: added a dedicated logistics weekly Stage04 pilot service/runner (`run_logistics_weekly_agent_pilot_suite`, `scripts/run_logistics_weekly_agent_pilot.py`) with deterministic IDs keyed by `(pilot_key, pilot_id)`, canonical workflow/task/artifact execution, and no ad hoc side-channel state.
- Weekly Stage04 pilot execution posture decision: pilot runs support `--openai-mode mock|real`; mock mode uses a deterministic bounded Responses function-calling runner, and real mode is explicitly key-gated without introducing a second runtime path.
- Inspection packet authority decision: weekly pilot outputs now include canonical-reference-heavy inspection packets (`inspection_packet.json` + `.md`) that center workflow/task/execution/tool/policy/artifact IDs, evidence-by-kind coverage, timeline events of interest, and canonical CLI query commands for debugging.
- Real-network gate decision: weekly Stage04 real e2e coverage now lives in `tests/integration_openai/test_weekly_stage04_openai_real_e2e.py` and requires both `ONETRUTH_RUN_OPENAI_E2E=1` and `ONETRUTH_RUN_OPENAI_WEEKLY_AGENT_E2E=1` (plus `OPENAI_API_KEY`), preserving existing Stage06 real-network coverage.
- CI posture decision: `agent_api.yml` now runs `tests/integration_openai` under one gated step, with weekly Stage04 e2e controlled by the additional weekly env gate rather than a permanently-empty future test directory path.

## 2026-03-12 (TASK-0069 weekly Stage04 OpenAI agent runtime)
- Bounded Stage04 agent-loop decision: weekly Stage04 now runs a synchronous OpenAI Responses function-calling loop (`weekly_schedule_planning.v1`, `Stage04`) with multi-call-per-turn support and `call_id`-bound `function_call_output` continuation semantics; no Assistants API and no background mode were introduced.
- Compiled-control pinning decision: Stage04 execution session semantics now resolve from compiled logistics control metadata (`compile_control_layer` + `derive_execution_session_payload`) rather than hardcoded execution-spec constants.
- Deterministic-tool boundary decision: the model can call only deterministic Stage04 tools (`get_stage04_context`, `materialize_weekly_stage04_draft_outputs`, `get_stage04_validation_summary`, `render_stage04_ops_packet`); no publish/pointer-promotion tool is exposed.
- Evidence traceability decision: context packs, turn-level request/response metadata, function calls, function-call outputs, usage totals, and execution traces are persisted as canonical artifact evidence linked to `execution_session`/`tool_execution`/`policy_decision`.
- API/actionability boundary decision: added one bounded human-task API mutation (`POST /api/v1/human-tasks/{id}/weekly-stage04-openai-agent`) and corresponding actionability affordance for claimed Stage04 work-item tasks without introducing a generalized public agent framework.

## 2026-03-12 (TASK-0068 deterministic weekly schedule-control services)
- Deterministic feasibility decision: Stage04 weekly schedule-control feasibility (route-slot expansion, candidate generation, hard-rule validation, and soft scoring) now lives in dedicated deterministic services under `src/onetruth/application/services/schedule_control/`; it is not owned by `workflow_task_lifecycle.py` and is not delegated to LLM output.
- Runtime execution decision: added bounded runtime command `schedule-control build-weekly` that resolves canonical Stage04 bridge artifacts, executes deterministic weekly build logic, and lowers machine-checkable Stage04 artifacts (`planning.input_bundle.doc`, `planning.candidate_schedule_delta.workbook`, `planning.validation_summary.doc`, `planning.draft_weekly_schedule.*`) idempotently.
- Replay-safety decision: Stage04 deterministic lowering now uses stable artifact identity/content derivation and provenance edges so retries return the same canonical output identities without duplicate truth rows.

## 2026-03-12 (TASK-0067 schedule-control authored semantics + canonical bridge artifacts)
- Artifact-authority decision: added canonical bridge artifact semantics for weekly/live schedule-control (`route_slot_requirements`, `driver_capabilities`, `input_bundle`, `candidate_schedule_delta`) and bounded Stage04/Stage02 validation evidence artifacts without introducing a second schedule truth path.
- Derived-view decision: current operative schedule remains a derived materialization from canonical base seed + ordered promoted deltas; it is explicitly non-authoritative.
- Exception-authority decision: open-exception packets remain derived from canonical `flags` and timeline state; no peer `planning.open_exceptions` store is authorized.
- Method-package decision: Stage04 weekly build and Stage02 live replan packages now reference shared schedule-control family refs while keeping deterministic hard/soft rule posture and bounded optional LLM rationale.

## 2026-03-12 (TASK-0066 execution-runtime hardening for compiled agent control traceability)
- Execution semantics evidence decision: Stage06 bounded execution now persists pinned immutable semantics artifacts (`execution.compiled_spec.json`, `execution.compile_source_manifest.json`) linked to canonical execution runtime objects; no second execution truth subsystem was introduced.
- Artifact-link subject decision: canonical artifact linkage validation now supports `execution_session`, `tool_execution`, and `policy_decision` subjects with workflow-scope checks resolved through existing execution/session relationships.
- Event safety decision: runtime event append now enforces registry-defined `required_links` semantics at write time (not only offline validation), and execution-session creation now emits an explicit `execution_spec` link required by the registry.
- Reuse decision: added a shared execution-evidence helper surface (`src/onetruth/application/services/execution_evidence.py`) that prepares pinned semantics artifacts and reusable execution-facet evidence links for future agent-trace slices.

## 2026-03-12 (TASK-0065 logistics-first Codex routing + secret hygiene)
- Routing decision: new agentic scheduling task intake now defaults to logistics weekly/live (`weekly_schedule_planning.v1 -> live_dispatch.v1`) across Codex/LLM routing docs; legacy `schedule_planning.v1` remains regression/reference-only.
- Secret hygiene decision: committed real OpenAI key material is removed from tracked repo content, and local `.codex.env` posture is documented as local-only placeholders with real-network gates defaulted off.
- Validation decision: `scripts/validate_repo.py` now scans tracked UTF-8 files for real OpenAI key patterns (`sk-proj-...` / `sk-...`) and fails validation on detection.
- CI gate posture decision: `.github/workflows/agent_api.yml` keeps current OpenAI gating and adds an explicit future weekly-agent real-network gate controlled by repository variable `ONETRUTH_RUN_WEEKLY_AGENT_E2E=1` plus `OPENAI_API_KEY` presence (later superseded in TASK-0070 by `ONETRUTH_RUN_OPENAI_WEEKLY_AGENT_E2E` dual-gate posture).

## 2026-03-09 (TASK-0068 composite-task subgraphs + drawer hardening)
- Human-task drill-down contract decision: keep `GET /api/v1/human-tasks/{id}` as the canonical detail seam and extend it with optional composite metadata (`is_composite`, `expansion_kind`, `subgraph_ref`) while keeping non-composite tasks unchanged.
- Task-subgraph endpoint decision: add `GET /api/v1/human-tasks/{id}/subgraph` for lazy, server-authored composite task process graphs; frontend loads this only when the operator chooses `Expand process`.
- Bounded rollout decision: composite expansion is enabled only for known logistics demo task kinds in this slice (`actual_hours_review`/`planning_feedback_review`, `dispatcher_review`/`dispatch_seed_intake`, `final_packet_review`/`finalize_reporting_packet`).
- Artifact boundary decision: task subgraph payloads remain reference-only (`artifact_version_id`, label, source label) and all bytes are still downloaded exclusively through canonical artifact download APIs.

## 2026-03-09 (TASK-0066 family-graph drilldown contract closure)
- Logistics story contract decision: `GET /api/v1/stories/logistics-three-workflow` now emits server-authored family-module drilldown metadata (`node_kind`, `drilldown_kind`, `drilldown_refs`, `artifact_refs`, `selection_summary`) so frontend drilldown does not guess run/artifact targets.
- Multiple-run disambiguation decision: when a module maps to more than one linked run in story scope, `drilldown_kind=run_group` and all candidate runs are returned in `drilldown_refs`; the backend does not silently choose one run.
- Artifact-reference decision: family-node artifact metadata stays reference-only (`artifact_version_id`, label, source label) and download bytes remain behind canonical artifact download APIs.

## 2026-03-09 (logistics drawer-first interaction hardening)
- Logistics-board interaction decision: in `/demo/logistics`, human-task board cards are now primary-click drawer surfaces; task inspection/action no longer uses `/runs/:workflowRunId` navigation as the primary path.
- Drawer action-surface decision: `DetailDrawer` now executes backend-authoritative human-task actions when present in `available_actions` (`claim`, `complete`, `run_stage06_agent_review`, `confirm_review`, `upload_attachment`) and keeps artifact download in-drawer.
- Secondary navigation decision: run-detail drill-down is retained only as a secondary drawer link from selected tasks; stale per-card run-detail links were removed from the unified board to reduce legacy-route confusion.

## 2026-03-09 (TASK-0064 logistics demo shell + legacy schedule demotion)
- Frontend primary-demo decision: `/demo/logistics` is now the preferred operator/demo entrypoint for the three-workflow logistics walkthrough; app root (`/`) redirects to this route.
- Composition decision: the logistics shell is backend-authored and story-driven only (`GET /api/v1/stories/logistics-three-workflow`); family graph, unified board lanes/items, linked runs, official-output summary, and handoff activity are rendered directly from canonical story payload sections.
- Task-interaction decision: task transitions are drawer-first for this demo slice; task cards/rows in logistics story and supporting queue surfaces open `DetailDrawer`, and canonical `claim`/`complete` actions execute from the drawer against authoritative task APIs.
- Supersession note: this drawer-first task-transition decision supersedes the earlier 2026-03-04 inline-task-action posture for `/board` and `/my-work`; inline attachment affordances remain unchanged.
- Legacy-surface decision: schedule-only board/workspace/runs/timeline views remain available for regression/internal use but are removed from primary navigation and treated as secondary/legacy surfaces via page-level notices.
- Scope-boundary decision: this frontend slice intentionally stays bounded to the canonical three-workflow story contract and does not introduce a generalized client-side family graph/query engine or a second UI truth store.

## 2026-03-09 (repo-truth alignment + capability certification matrix)
- Added `docs/planning/CURRENT_CAPABILITY_AND_CERTIFICATION_MATRIX.md` as the snapshot-backed authority for current capability status (`implemented` / `partial` / `missing`) across schedule demo paths, logistics handoff slices, workspace/export surfaces, and projection coherence.
- Hardening decision: capability claims are considered certified only when matrix rows include all of: canonical command/entrypoint, authoritative tests, human-inspectable artifacts, and invariants.
- Scope-boundary decision: this alignment pass introduces no new runtime semantics; bounded slices and unresolved ambiguities are recorded explicitly instead of being promoted to DONE claims.

## 2026-03-09 (TASK-0063 three-workflow story seam closure)
- Added canonical three-workflow demo story contract source at `docs/planning/THREE_WORKFLOW_DEMO_STORY.yaml` plus aligned template/example artifacts under `templates/`.
- Added first backend-authored logistics story query seam `GET /api/v1/stories/logistics-three-workflow`; payload is derived from canonical runtime state only (compiled family graph + `edge_executions` summaries + linked runs + board-ready work + official outputs + freshness/coherence metadata).
- Demo-entrypoint decision: for logistics three-workflow walkthroughs the new story endpoint is primary; `/api/v1/board/schedule-planning` remains legacy/internal regression surface.
- Scope-boundary decision: this closure remains intentionally narrow to the first story slice (`weekly_schedule_planning`, `live_dispatch`, `dispatch_reporting` with `reporting_actuals_to_future_planning` `notify_only`), and does not claim a universal logistics composition engine.

## 2026-03-08 (TASK-0063 notify_only reporting->planning + TASK-0031 status closure)
- Status authority decision: TASK-0031 is DONE. Projection coherence authored/runtime surfaces now exist in-repo (`docs/planning/PROJECTION_COHERENCE_HARNESS.md`, `tests/runtime/test_projection_coherence.py`, and runtime `projection.coherence_failed` behavior over derived projection views).
- Composition runtime decision: TASK-0063 is DONE as a bounded first `notify_only` slice over existing `edge_executions` + compiled family edges; landed scope is `dispatch_reporting.Stage05 -> weekly_schedule_planning.Stage03` with deterministic typed transform usage, target run resolve/create, canonical target input materialization, exact input binding capture, and duplicate-notification idempotency.
- Scope-boundary decision: keep later logistics composition work (observability/query surfaces, additional edges) as future tranche work; do not represent TASK-0063 as a fully general finished composition engine.

## 2026-03-07 (TASK-0061 logistics control layer + method packages)
- Chosen control-layer authority boundary: compiled logistics control metadata drives only existing canonical runtime activation objects (`workflow_runs`, `task_runs`, `human_tasks`, `execution_sessions`, `tool_executions`); no second activation ontology/table set is introduced.
- Chosen method-package pinning posture: first-slice stages require authored method packages with deterministic replay fields, explicit stop policy, and a content digest; execution-spec identities are derived from these pinned package digests.
- Chosen fail-closed rule for first-slice control semantics: missing method package coverage for required first-slice stages, stage/pattern mismatches, or incomplete activation-input bindings are hard compile/validation failures.
- Chosen activation-request contract: activation requests are validated from compiled stage metadata plus canonical pointer-address inputs (`ptr/v1/...`) scoped by tenant/domain/partition; no hidden activation side state is permitted.
- Chosen bounded-stochastic rule for first-slice dispatch triage: deterministic ranking remains primary and optional LLM rationale is non-authoritative support only.

## 2026-03-04 (TASK-0057 workflow workspace projection + graph/actionability/demo bundle)
- Chosen workspace authority boundary: `GET /api/v1/workflow-runs/{workflow_run_id}/workspace` is a read-only derived projection over canonical run/task/approval/flag/artifact/pointer/event state; no second workflow-engine state path is introduced.
- Chosen graph posture for this slice: schedule-planning-specific minimal node set (Stage03 readiness through Stage07 delta publish) with explicit branch/loopback edges and canonically explainable statuses (`not_started`, `ready`, `in_progress`, `blocked`, `awaiting_approval`, `completed`, `warning`).
- Chosen actionability posture: workspace mutation affordances are server-computed (`available_actions`, `blocking_requirements`, `missing_required_inputs`) for tasks/approvals/flags; frontend does not infer completion or policy eligibility.
- Chosen information-request rule for workspace actionability: `information_request` tasks require at least one linked artifact before `complete` becomes available in workspace projection.
- Chosen Stage06 actionability rule: `run_stage06_agent_review` is exposed only when task scope/assignment and policy-role gate allow it.
- Chosen demo/export posture:
  - demo runner seeds canonical realistic state by delegating to the existing pilot runner/service and emits `workflow_run_id` plus recommended workspace URL,
  - export bundle is generated from canonical detail/workspace projections and includes mandatory JSON files + README summarizing scenario, graph status, first actions, upload-unblock signal, and OpenAI-path usage.

## 2026-03-04 (TASK-0058 frontend workspace page + live graph)
- Added a dedicated single-run workspace route `/runs/:workflowRunId/workspace` that keeps graph projection and actionable work in one polling query path.
- Chosen frontend contract boundary for this slice:
  - repository/API method `workflowRunsRepository.workspace(workflowRunId)` backed by `GET /api/v1/workflow-runs/{workflow_run_id}/workspace`,
  - workspace item actionability is driven by server fields `available_actions` and `missing_required_inputs`.
- Chosen graph rendering strategy: lightweight SVG + CSS components (`WorkflowGraph*`) with support for linear, branch, and loopback edges; no heavyweight graph library introduced.
- Chosen interaction model for workspace actions:
  - reuse existing task/approval/flag cards and attachment affordances,
  - keep detail depth in drawer,
  - render Stage06 AI action only when `run_stage06_agent_review` is present.
- Chosen refresh behavior: inline mutation success invalidates workspace and related queue/run queries so graph and actionable work stay visibly synchronized under polling.

## 2026-03-04 (TASK-0056 CI/hygiene stabilization + TASK-0031 status reconcile)
- Chosen hygiene posture: local editor/runtime/cache/build noise (`.DS_Store`, `.idea/`, `.tmp/`, `artifacts/`, frontend `node_modules`/`dist`, env/log cache files) is ignored and removed from Git index when previously tracked.
- Chosen CI posture: backend PR checks include `frontend-snapshots-check`; frontend PR checks run `npm ci`, typecheck, and non-watch frontend tests; OpenAI real-network tests remain gated in scheduled/dispatch workflow only.
- Historical note (superseded by 2026-03-08): at this date TASK-0031 was still tracked as TODO pending authored/runtime coherence harness delivery.

## 2026-03-04 (TASK-0055 stabilization pass 1 for frontend typecheck + snapshot determinism)
- Chosen path-sanitization rule for artifact ingress metadata: normalize separators to `/`, store repo-relative `fixtures/...` when the path includes `fixtures`, otherwise store only the file basename.
- Applied the same sanitization rule to `seed_source_path` metadata during ingress so scenario-backed snapshot exports cannot leak machine-local absolute paths.
- Added an explicit snapshot drift-check command target (`make frontend-snapshots-check`) and linked it into `make test` so deterministic snapshot enforcement is part of the primary CI/test gate.

## 2026-03-04 (TASK-0032 generator prototype for runbook + CompanyOS IR)
- Chosen prototype scope: generate only from repo-native Schedule Planning source (`WORKFLOW_CONTRACT`, `ARTIFACT_MAP`, `DECISION_CATALOG`, `EXECUTION_PROFILE`, `ACCEPTANCE_CRITERIA`) with no secondary authored semantics.
- Chosen output contract under `build/generated/`:
  - runbook markdown at `runbooks/schedule_planning.v1/runbook.md`,
  - CompanyOS-style IR JSON at `companyos_ir/schedule_planning.v1.json`,
  - lineage manifest at `lineage/schedule_planning.v1.lineage.json`.
- Chosen freshness strategy: deterministic runbook/IR render plus lineage source/output hash checks via `--check`; stale or drifted generated artifacts fail closed.
- Chosen no-invention guardrails in generator code:
  - reject unknown stage IDs, dataset keys, decision refs, evidence refs, and spawn-rule target stage IDs,
  - emit only authored IDs/keys into generated IR/runbook sections.
- Chosen CI integration posture: `make generated-check` now runs full repo validation plus generator `--check` freshness enforcement.

## 2026-03-04 (TASK-0030 artifact-store and schedule-delta design closure)
- Locked artifact-store authority boundary: canonical truth for artifacts is `artifact_versions` + `artifact_pointers` + `artifact_links` + timeline events; blob/object storage bytes remain non-authoritative payload storage.
- Locked Stage06/Stage07 schedule semantics:
  - Stage06 publishes immutable base schedule versions,
  - Stage07 publishes immutable ordered deltas and never mutates base artifacts in place,
  - operative live-day reconstruction is read-only from base pointer + ordered official Stage07 deltas.
- Locked ordered-delta lineage requirements: Stage07 deltas must carry explicit lineage (`supersedes_artifact_version_id`, `base_artifact_version_id`, `delta_sequence`) so reconstruction order/anomalies are auditable.
- Locked idempotency posture for artifact uploads/promotions: duplicate idempotency must not duplicate canonical effects; same-target promotion remains non-duplicating; pointer repoints require generation checks.
- Locked mismatch recovery rule: when blob bytes and canonical metadata disagree, metadata/events/pointers remain authoritative; remediation is new immutable version + explicit pointer move, never row mutation.
- Added explicit read-only reconstruction contract and named required helper surfaces/tests in `docs/planning/ARTIFACT_STORE_DESIGN.md` and `docs/planning/TEST_MATRIX.md`.

## 2026-03-04 (realistic Schedule Planning pilot + inspection packet milestone)
- Chosen pilot shape: three reproducible Schedule Planning scenarios (`stage06_publish_ready`, `stage06_needs_information`, `stage07_issue_replan`) executed through canonical handlers, seeded from the real corpus seed sets.
- Chosen Stage06 pilot execution posture: Stage06 review in pilot scenarios must use the bounded Stage06 agent path (`run_stage06_openai_review_sandbox`) so execution session/tool execution/policy decision rows and events are always part of the pilot truth.
- Chosen reproducibility/idempotency strategy for pilot runs: deterministic workflow/object IDs derived from `(pilot_key, pilot_id)` with run reuse on repeated pilot key invocation; repeat runs must not duplicate canonical side effects.
- Chosen inspection artifact contract: each pilot run exports `inspection_packet.json` and `inspection_packet.md` containing canonical IDs, lifecycle states, timeline events of interest, and suggested UI/API inspection routes.
- Chosen operator visibility rule: pilot packets are walkthrough artifacts only; authoritative truth remains canonical runtime rows/events/artifacts/pointers.

## 2026-03-04 (policy-gate state hardening and reconcile dedupe coverage)
- Chosen bounded Stage06 session posture: execution sessions now start in `WAITING_POLICY` and transition to `RUNNING` only after an explicit policy allow decision is persisted and emitted as authoritative evidence.
- Chosen policy-allow evidence rule: `evaluate_policy_decision` now emits `execution.session.state_changed` for allow transitions when session state changes (for example `WAITING_POLICY -> RUNNING`), not only for deny/require-approval branches.
- Chosen reconcile safety expectation: stale-session reconciliation may fail stale sessions, but it must not duplicate already-completed tool/evidence effects; runtime coverage now explicitly asserts no duplicate `tool.execution.completed` or `artifact.version.created` for completed tool outputs.

## 2026-03-04 (execution-session runtime and policy-gated sandbox hardening)
- Added canonical execution-runtime current-state tables: `execution_sessions`, `tool_executions`, and `policy_decisions`; execution truth is now persisted in runtime rows plus authoritative events, not implied by service-only side effects.
- Chosen Stage06 bounded execution ID strategy: deterministic IDs derived from `(workflow_run_id, task_run_id, base_idempotency_key)` for `execution_session_id`, `tool_execution_id`, and `policy_decision_id` to prevent duplicate canonical effects on replay.
- Chosen policy-gate rule for bounded Stage06 sandbox:
  - explicit policy decision is required before model execution,
  - default allows only trusted actor-role set (`dispatch_supervisor`, `operations_manager`, `system_worker`) or `system/service` actor types,
  - optional bounded override via request payload/env for testability (`allow|deny|require_approval`),
  - denied/require-approval paths fail closed with canonical denial evidence.
- Chosen failure mapping:
  - model/config/provider failures map to `tool_executions.state=FAILED` and `execution_sessions.state=FAILED` with emitted lifecycle events,
  - workflow-transition failure after a successful model call marks session failed without erasing already-canonical tool/evidence results.
- Chosen reconcile behavior for this slice: `maintenance reconcile-executions` marks stale open sessions and open tool requests as failed with visible timeout evidence, avoiding duplicate terminal effects on repeated runs.

## 2026-03-04 (example document corpus + canonical artifact ingress)
- Promoted template-pack completed examples into an executable corpus manifest at `fixtures/example_document_corpus/manifest.yaml`; fixture inputs are now stable by `fixture_id` and grouped by deterministic `seed_set_id`.
- Chosen corpus authority boundary: fixture files are test inputs only; authoritative truth remains canonical `artifact_versions` + `timeline_events` + audited pointers.
- Chosen ingress rule: example docs must enter through canonical artifact ingress (`artifacts ingest`, subject upload endpoints, or `artifacts seed-corpus`) with digest/byte-size metadata captured and `artifact.version.created` emitted in the same transaction.
- Added canonical `artifact_links` current-state table to represent attachment/linkage to `workflow_run`, `human_task`, `approval`, and `flag` subjects; no separate attachment truth subsystem is introduced.
- Chosen frontend inline attachment posture for v1: upload/download actions are inline on queue/board surfaces and delegate to canonical API endpoints; client stores no attachment workflow semantics.
- Chosen snapshot/corpus coupling rule: backend-owned frontend snapshots continue to be exported from real scenario-backed states seeded through canonical artifact ingress, not hand-authored mock documents.

## 2026-03-04 (bounded OpenAI Responses API Stage06 sandbox spike)
- Added a narrow OpenAI integration boundary under `src/onetruth/integrations/openai/` using the Responses API for new model work; no raw provider calls are scattered through handlers/routes.
- Locked the first real model-assisted use case to Stage06 `review_packet` outcome classification only, with strict structured output fields:
  - `outcome` in `{draft_is_publish_ready, review_requires_more_information, review_requests_changes}`
  - `rationale_summary`
  - `evidence_refs`
  - nullable schema-bound `suggested_follow_on_task_kind`
- Chosen canonical persistence path for model evidence: create immutable artifact versions (`artifact_kind=schedule.stage06.review_ai_evidence.json`) containing model metadata + input artifact refs; no log-only evidence path.
- Chosen workflow-authority rule for this spike: model output may select only existing canonical completion outcomes; follow-on truth still comes exclusively from existing `tasks.complete` completion/spawn handlers.
- Added bounded HTTP mutation endpoint `POST /api/v1/human-tasks/{human_task_id}/stage06-agent-review` with explicit scope checks and normalized config/provider error mapping.
- Added test strategy split:
  - always-on structural coverage (adapter schema/failure tests + runtime API sandbox path with mocked classifier),
  - gated real-network e2e slice under `tests/integration_openai/` requiring `ONETRUTH_RUN_OPENAI_E2E=1` and `OPENAI_API_KEY`.

## 2026-03-04 (frontend real API integration and board/list/detail hardening)
- Replaced frontend snapshot/mock repository reads with real HTTP adapters under `frontend/src/lib/api/` and repository implementations under `frontend/src/lib/repositories/`; frontend pages/components no longer read fixture files directly.
- Kept frontend presentation-only authority boundary: filters, drawer state, local selection, and visual affordances remain client-owned while workflow semantics and transition validity remain server-authoritative.
- Chosen frontend request-context model for dev/internal slice: Vite env-configured tenant/domain/actor headers (`VITE_ONETRUTH_*`) emitted by a centralized HTTP client.
- Chosen polling model: TanStack Query interval polling with explicit freshness indicator and query invalidation on successful mutations; no websocket/live-sync in this slice.
- Added thin API read routes `GET /api/v1/flags` and `GET /api/v1/timeline-events` plus runtime API contract tests so exceptions/timeline views stay API-backed rather than client-reconstructed mocks.
- Chosen frontend integration-test approach: contract-aligned MSW test server for `/api/v1` read/mutation surfaces, including claim/complete/respond round-trips and forbidden-response handling.

## 2026-03-04 (frontend snapshot fixtures for Stage06/Stage07)
- Added backend-owned frontend snapshot fixtures under `fixtures/frontend_contracts/` and made them derived from real Stage06/Stage07 scenario-backed runtime states, not hand-authored JSON.
- Chosen snapshot refresh workflow: `make frontend-snapshots` (runs `scripts/export_frontend_snapshots.py`) and deterministic drift check via `python3 scripts/export_frontend_snapshots.py --check`.
- Chosen snapshot stability approach: deterministic ID/timestamp tokenization during export so fixtures remain stable while preserving server-owned contract shapes and lane/state semantics.
- Added a contract guard (`tests/runtime/contracts/test_frontend_snapshot_fixtures.py`) that regenerates snapshots from runtime scenarios and asserts committed fixtures match.

## 2026-03-04 (first frontend shell + mock repository boundary)
- Chosen frontend stack for the first HITL UI slice: React + TypeScript + Vite + React Router + TanStack Query + Vitest/Testing Library.
- Chosen server-authoritative client posture: the frontend may manage only presentation state (filters, drawer visibility, selection, refresh affordances) and must not own workflow/task/approval/flag/pointer semantics.
- Chosen data-access seam: route pages consume repository interfaces (`humanTasksRepository`, `approvalsRepository`, `flagsRepository`, `workflowRunsRepository`, `pointersRepository`, `timelineRepository`, `boardRepository`) while fixture parsing remains centralized in `mockContractService`.
- Chosen interaction model lock for v1: explicit inline actions + inline attachment affordances + hidden-by-default descriptions with drawer-first detail; no drag-to-transition semantics.
- Chosen route surface for first operator workflows: `/board`, `/my-work`, `/approvals`, `/exceptions`, `/runs`, `/runs/:workflowRunId`, `/official-outputs`, `/timeline`.

## 2026-03-03 (Stage07 issue-scoped replan loop)
- Added canonical `flags` substrate with runtime states `open`, `triage`, `blocked`, `resolved`, `closed`, `waived`; transitions are enforced server-side and recorded via `flag.created` / `flag.state_changed`.
- Chosen Stage07 issue activation key and dedupe model: `(workflow_run_id, flag_id, task_kind, generation)`; duplicate wakeups/activation retries return existing canonical issue task instead of creating a second root issue task.
- Implemented Stage07 completion outcome mappings in the authoritative `tasks complete` transaction path:
  - `replan_requires_missing_information` -> Stage07 `information_request`
  - `resolution_creates_child_issue` -> Stage07 `exception_triage`
  - `major_replan_is_ready_for_review` -> Stage07 `final_review`
- Chosen major-replan approval gate: `pointers.promote` with `promotion_reason=official_major_replan` requires a canonical approved response and Stage07 approval scope; otherwise promotion fails closed.
- Chosen drift-detection rule for Stage07 promotion: compare `reviewed_base_artifact_version_id` against the current base pointer target (`base_pointer_key`, defaulting to `official:schedule.published_schedule.workbook`); emit `artifact.pointer.drift_detected` when stale, while allowing promotion.
- Chosen lease-expiry recovery behavior: reopen the same claimed human-task row (clear assignee/lease, increment reopen counters/version), emit `task.lease_expired`, and move task run `IN_PROGRESS -> READY` with `task.run.state_changed` evidence.
- Added Stage07 reconcile path to recover dropped wakeups by ensuring open flags have issue-root tasks via activation-key dedupe, without duplicating canonical root tasks.

## 2026-03-03 (HITL HTTP/query adapter + backlog reconciliation)
- Added the first thin HTTP adapter over canonical runtime/query surfaces under `src/onetruth/api/`; API routes delegate mutation semantics to existing canonical handlers (`claim_human_task_command`, `complete_human_task_command`, `respond_approval_command`) rather than reimplementing business lifecycle logic.
- Chosen board lane derivation rules for initial Schedule Planning board aggregate:
  - human tasks: `OPEN -> human_tasks.open`, `CLAIMED -> human_tasks.claimed`, `COMPLETED -> human_tasks.completed`
  - approvals: `PENDING -> approvals.pending`, `RESPONDED -> approvals.responded`
- Chosen board/query pagination strategy: offset/limit (`limit` default 100, max 500; `offset` default 0) for initial stable contracts.
- Chosen API auth-context approach for this internal/dev slice: explicit request headers `x-onetruth-tenant-id`, `x-onetruth-domain-id`, `x-onetruth-actor-id`, `x-onetruth-actor-type`, `x-onetruth-actor-roles` with mandatory server-side scope enforcement and no unscoped fallback.
- Chosen refresh model: polling-friendly stateless GET contracts first; websocket/live-sync intentionally deferred.
- Reconciled stale backlog status to match implemented runtime reality:
  - TASK-0029 moved to DONE (event emission matrix now implementation-backed in runtime handlers/tests)
  - TASK-0039 moved to DONE (scenario harness now implemented in fixtures/tests/docs)
  - TASK-0030 narrowed to remaining Stage07/base+delta artifact-store design work and moved to IN_PROGRESS.

## 2026-03-03 (Stage06 publish slice + scenario harness)
- Implemented the first narrow Schedule Planning Stage06 runtime behavior inside canonical `tasks complete`: parent completion can now create explicit child tasks in the same transaction with persisted lineage fields (`spawned_from_task_run_id`, `spawn_rule_id`, `spawn_cause_kind`, `spawn_cause_event_id`, `spawn_depth`, `spawn_budget_key`).
- Finalized first Stage06 completion outcome names in code:
  - `review_requires_more_information` -> child Stage06 `information_request`
  - `review_requests_changes` -> child Stage05 `work_item`
  - `draft_is_publish_ready` -> child Stage06 `final_review`
- Chosen retry behavior for parent completion replays remains explicit-failure idempotency: retrying the same completion command idempotency key fails with `duplicate_idempotency_key`, and no duplicate child task rows/events are emitted.
- Added implementation-backed Stage06 scenario fixtures and CLI-driven scenario harness tests; harness seeds synthetic template-pack completed examples into temp storage and registers canonical artifact versions before scenario steps.
- Query-contract stability approach is now test-backed via runtime contract tests that assert stable JSON row shapes for human task queue, approval queue, pointer summary, and workflow run summary surfaces.

## 2026-03-03 (approvals + artifact versions + pointer promotions substrate)
- Added canonical substrate tables for `approvals`, `artifact_versions`, and `artifact_pointers` with matching migration and SQLite bootstrap DDL support.
- Chosen minimal approval state set in the first implementation:
  - `PENDING`
  - `RESPONDED`
- Approval responses are single-finalization: only `PENDING -> RESPONDED` is allowed, and duplicate/conflicting second responses are rejected (`approval_not_respondable`).
- Chosen artifact-version idempotency behavior: `artifacts create-version` requires non-empty command `idempotency_key`; duplicate keys fail explicitly (`duplicate_idempotency_key`) with no duplicate canonical row and no duplicate `artifact.version.created` event.
- Chosen pointer conflict/race behavior:
  - first promotion wins for an uninitialized pointer key,
  - conflicting promotion without `expected_generation` fails closed (`pointer_conflict`),
  - repoint requires optimistic generation match (`pointer_generation_mismatch` on mismatch).
- Chosen minimal pointer policy gate: `promotion_reason=official_publish` requires `approved_by_approval_id` bound to a `RESPONDED` approval with `response_kind=approve`; otherwise promotion fails closed.
- Added stable CLI list/show read surfaces (`runs/tasks/approvals/artifacts/pointers`) and documented them as HITL query contracts to unblock parallel board/UI work without introducing a second truth path.

## 2026-03-03 (workflow/task core substrate + transactional lifecycle events)
- Added canonical current-state tables for the first workflow/task substrate slice: `workflow_runs`, `task_runs`, and `human_tasks` (with lineage-ready spawn fields on `task_runs`).
- Chosen minimal first-implementation states:
  - `workflow_runs`: `OPEN`, `COMPLETED`
  - `task_runs`: `READY`, `IN_PROGRESS`, `COMPLETED`
  - `human_tasks`: `OPEN`, `CLAIMED`, `COMPLETED`
- Lifecycle commands now commit canonical row changes and authoritative event appends in the same transaction for:
  - `runs create`
  - `tasks create`
  - `tasks claim`
  - `tasks complete`
- Claim and complete command idempotency keys are required and duplicate keys fail explicitly (`duplicate_idempotency_key`) with no duplicate canonical effect and no duplicate emitted lifecycle events.
- Completion flow is explicitly structured to support future same-transaction child task emission (`task.run.created`, `task.created`) without introducing a second truth path; full spawn-evaluator semantics remain out of scope for this slice.

## 2026-03-03 (runtime scaffold command boundary + smoke substrate)
- Added the first concrete runtime scaffold under `src/onetruth/`, `alembic/`, and `tests/runtime/` as TASK-0040.
- Established the first stable runtime CLI command boundary: `init-db`, `events append --json`, and `events list --json`.
- Chose explicit idempotency behavior for timeline append in this scaffold: duplicate `idempotency_key` fails with a machine-parseable error (`duplicate_idempotency_key`); no silent dedupe path is used.
- Local smoke tests use SQLite by default and initialize substrate tables through Alembic when available, with a SQLite bootstrap fallback when Alembic/SQLAlchemy are unavailable in constrained environments. PostgreSQL remains the primary target architecture.

## 2026-03-03 (conditional task spawning and step-run test planning)
- Stage 4 now explicitly allows **conditional follow-on task spawning**: completing a task may create one or more child task runs for information requests, re-review, final review, or issue-scoped child work.
- Child-task creation must stay inside the same workflow run and remain explicit through `task.run.created` / `task.created`; no new hidden side-effect path or separate `task.spawned` truth system is introduced.
- The first runtime implementation should create deterministically implied child tasks in the same transaction as the parent completion or approval response, reserving the decider/reconciler for timers, flags, and repair.
- Added `docs/planning/STEP_RUN_SCENARIO_HARNESS.md` and TASK-0039 so future runtime work must include step-run tests where an agent executes each step and the test asserts authoritative truth.
- The workflow `template_pack/` folders already contain synthetic completed example artifacts and are now the planned seed inputs for runtime scenario tests; the validator now checks that both empty templates and completed examples exist.

## 2026-03-03 (runtime bootstrap locked for development)
- Stage 4 runtime will start as a **Python modular monolith** under `src/onetruth/`, not as an external workflow engine and not as early microservices.
- The canonical persistence substrate is **PostgreSQL current-state tables + append-only `timeline_events`**, with immutable artifact blobs stored behind a pluggable object-store adapter.
- `timeline_events` will also serve as the **outbox substrate** for derived consumers; wakeups may use notifications/polling, but consumer truth is a cursor over the canonical timeline.
- The first code slice is **core substrate + Schedule Planning Stage06 publish path**, followed by the Stage07 issue-scoped replan loop.
- `docs/planning/RUNTIME_BOOTSTRAP.md` and `docs/planning/FIRST_RUNTIME_SLICE.md` are now the authoritative implementation-architecture entrypoints for fresh-session Codex work.
- Completed TASK-0028 and refreshed stale routing/context so default runtime work no longer incorrectly points fresh agents to Payroll traces.

## 2026-03-03 (test-first harness adoption)
- Adopted a pytest-backed Stage 4 TDD harness rooted in schemas, golden traces, and acceptance scenario oracles rather than prose-only guidance.
- Added `docs/planning/TDD_IMPLEMENTATION_PLAN.md` so fresh-session Codex runs can start from a stable test-first workflow.
- Added a non-authoritative reference replay reducer and stable `AT-SCH-001` .. `AT-SCH-007` scenario catalog under `tests/helpers/` to make the existing traces executable.
- Added a dedicated `schedule_policy_gate_enforced.jsonl` trace so AT-SCH-007 (sandbox/policy gate) now has first-class trace coverage.
- Default verification flow for runtime work is now `make assurance-fast`, `make contract`, `make replay`, `make acceptance`, then implementation-specific suites (`make schema-validate` remains a compatibility alias).

## 2026-03-02 (semantic closure before runtime planning)
- Added a shared governance vocabulary and machine-readable registry for actor taxonomy, approval response verbs, approval outcomes, and approval permission actions.
- Canonical actor taxonomy is now `human | agent | service | system`; stale `user` actor types were removed from authoritative schemas.
- Canonical approval permission actions are now `approval.request` and `approval.respond`; stale `approval.grant` wording was removed.
- Schedule Planning now carries explicit temporal partition semantics: service interval, logical date, timezone, catchup policy, backfill policy, and stage-rerun policy.
- Workflow contracts now distinguish `event_inventory.platform_required` from `event_inventory.workflow_required` so runtime/task/execution events are no longer implicit.
- Added a tool-class registry, workflow-pack schemas, runtime object schemas, event payload schemas, and a concrete sandbox policy schema.
- Added a repo validation harness (`scripts/validate_repo.py`) and Makefile targets so a fresh agent can validate contracts and traces before starting runtime work.
- Added Schedule Planning golden traces for happy path, fully-agentive whole flow, drift after review, lease expiry recovery, degraded mode survivability, and cross-scope denial.

## 2026-03-02 (schedule-first Stage 4 pivot)
- Stage 4 now treats `schedule_planning.v1` as the primary runtime/debug wedge.
- The primary Stage 4 acceptance objective is a fully-agentive Schedule Planning flow where designated agent principals can execute every in-scope task while preserving the same canonical task, approval, event, and pointer substrate.
- This fully-agentive objective is a debugging and validation posture, not permission to create a second agent-only truth system.
- Payroll remains in Stage 4 as the secondary reference workflow used to validate the shared substrate against a linear approval-heavy path.
- Added `docs/workflows/payroll/v1/OPERATING_MODEL.md` so both workflow packs now expose the full authored surface declared by the authority model.

## 2026-02-28
- Added `schedule_planning.v1` as a second Stage 4 workflow contract pack for a same-day delivery operator; at that point Payroll remained the primary implementation slice (later superseded by the 2026-03-02 schedule-first pivot).
- Schedule Planning is partitioned by `ScheduleDateID` (`SD-YYYY-MM-DD`) and uses the same `(tenant_id, domain_id)` scoping model as Payroll.
- Published schedules are treated as stable base plans; live-day changes must be recorded as new artifact versions / replan deltas rather than silent edits.
- Availability artifacts for scheduling may store coded leave/absence types, but must not store medical or disciplinary detail.

## 2026-02-28 (merger update)
- The repo now explicitly adopts one truth system: immutable objects + append-only events + audited pointers.
- The CompanyOS packet is preserved as philosophy, mathematics, threat model, and lowering target, not as a second authored workflow-definition system.
- Per-workflow authored semantics now include two repo-native execution-overlay files: `DECISION_CATALOG.yaml` and `EXECUTION_PROFILE.yaml`.
- Generated runbook packs, tool matrices, approval logs, and CompanyOS IR are treated as generated derivatives, not authoritative source.
- Business execution and agentic execution will share one event system, one approval model, and one run model.

## 2026-03-14 - Planned next package after TASK-0101
- We are treating the next tranche as a **centrality + operability** package, not another trust-semantics package.
- Primary next risks are now:
  - residual centrality around `workflow_task_lifecycle.py`,
  - package-boundary leaks in `onetruth.api`,
  - control-plane framework creep around `route_registry.py`,
  - and assurance-kernel concentration in `scripts/validate_repo.py`.
- The next queued tasks are `TASK-0102` through `TASK-0109`.
- Explicit deferrals for this tranche:
  - no PostgreSQL/object-store migration,
  - no broader auth/policy redesign,
  - no streaming upload rewrite,
  - no large logistics-story or weekly-agent service decomposition yet.

## 2026-03-17 (TASK-0102 neutral read/error seam)
- Centrality-retirement decision: shared runtime reads now live in `src/onetruth/application/read_commands/` instead of being sourced only from `workflow_task_lifecycle.py`.
- Boundary decision: API/query/service layers now consume `CommandError` from `src/onetruth/application/handlers/_shared/command_boundary.py`, while read-side approvals still import from `src/onetruth/application/handlers/approvals.py` and legacy `workflow_task_lifecycle.py` stays import-compatible through thin wrappers.
- Guardrail decision: contract coverage now forbids API/query/service layers from importing shared read/error surfaces from the legacy hotspot, while allowing remaining mutation-family imports to retire in later tasks.

## 2026-03-17 (TASK-0103 flag and Stage07 extraction)
- Extraction decision: `create_flag_command`, `transition_flag_state_command`, `activate_stage07_issue_from_flag_command`, and `reconcile_stage07_command` now live in `src/onetruth/application/handlers/flags.py` behind thin compatibility wrappers in `workflow_task_lifecycle.py`.
- Caller decision: API flag routes, the realistic scheduling pilot, and the CLI now import the extracted flag family directly instead of routing those mutations through the legacy hotspot.
- Helper-seam decision: shared event-idempotency availability checks now live on `src/onetruth/application/handlers/_shared/command_boundary.py` so the extracted flag family can stay free of legacy imports without broadening semantics.

## 2026-03-17 (TASK-0104 artifact and pointer extraction)
- Extraction decision: artifact-version creation/ingress/download now live in `src/onetruth/application/handlers/artifacts.py`, and pointer promotion now lives in `src/onetruth/application/handlers/pointers.py`, behind thin compatibility wrappers in `workflow_task_lifecycle.py`.
- Helper-seam decision: shared artifact support remains explicit in `src/onetruth/application/handlers/_shared/artifact_effects.py` instead of leaving artifact lineage concerns embedded in the hotspot.
- Scope decision: the extraction stayed structural only; artifact officialness, pointer promotion semantics, release-bundle truth, and binary transport behavior were not reopened.

## 2026-03-17 (TASK-0105 execution runtime extraction)
- Extraction decision: `create_execution_session_command`, `request_tool_execution_command`, `evaluate_policy_decision_command`, `complete_tool_execution_command`, `transition_execution_session_state_command`, and `reconcile_executions_command` now live in `src/onetruth/application/handlers/execution_runtime.py` behind thin compatibility wrappers in `workflow_task_lifecycle.py`.
- Caller decision: `stage06_openai_sandbox.py`, `weekly_stage04_openai_agent.py`, CLI execution commands, and the direct execution runtime tests now import the extracted execution seam directly instead of routing those mutations through the legacy hotspot.
- Guardrail decision: contract coverage now forbids extracted handlers plus API/service/CLI layers from drifting back to legacy execution mutation imports, while execution read surfaces remain on `read_commands`.

## 2026-03-17 (TASK-0106 optional API import honesty)
- Packaging-boundary decision: `src/onetruth/api/__init__.py` and `src/onetruth/api/main.py` now keep `onetruth.api` imports lazy, so lightweight API modules no longer pull in optional `api` dependencies at import time.
- Dependency-localization decision: `src/onetruth/api/shared_env_principal_resolver.py` now imports `PyJWT` only when the configured shared-env JWT resolver path is actually activated.
- Compatibility decision: `from onetruth.api import app`, `from onetruth.api import create_app`, `from onetruth.api.main import app`, `from onetruth.api.main import create_app`, and `onetruth.api.main:app` remain supported surfaces.
- Scope decision: this task did not change boundary-profile defaults, attested-principal claim mapping, trusted-header rules, route behavior, or error payload semantics for valid configured runtimes.

## 2026-03-24 (Minimal on-call buffer rerun)
- Planner decision: Stage04 on-call demand is now allocated through the same deterministic candidate-generation, hard-validation, and ranking path as route demand, with an internal demand-kind marker rather than authored fixture-schema changes.
- Fairness decision: post-coverage soft-improvement moves now account for zero-shift drivers so the deterministic allocator does not trade away a driver's only shift to gain a small soft-score bump.
- Runtime-budget decision: the authored weekly Stage04 stop policy now allows `28` tool turns so the actual-ops mock/runtime slice can complete the longer deterministic rerun, finalize outputs, and return a final response without exhausting the control-plane budget.

## 2026-06-01 (CAPEX v6 planning import)
- Source decision: `CAPEX_Master_Plan_Three_Project_Testing_Production_Preflight_Final_v6.zip` is the active CAPEX planning baseline; v5 and earlier packages are superseded history.
- Boundary decision: raw K12/K3/blind project corpora remain off-repo; only ZIP basenames, hashes, aggregate counts, fixture-role labels, and repo-native planning artifacts may be committed.
- Activation decision: imported CAPEX tasks do not activate runtime behavior until the relevant gates close or are explicitly waived.

## 2026-06-02 (CAPEX PR002/PR003 safety hardening)
- Artifact safety decision: authoritative artifact downloads must authorize by DB metadata and workflow-run scope before blob reads, and file-backed blob reads/writes must remain confined to the configured artifact root.
- Shared-env decision: authoritative artifact download rejects `inmem://` storage in `shared_env` instead of treating memory-backed blobs as downloadable production-like truth.
- Transaction decision: command handlers that may compose under an outer transaction use the shared savepoint-aware `command_transaction(connection)` helper rather than local `BEGIN` helpers.
- Activation decision: `TASK-0235` and `TASK-0236` close repo runtime safety gates only; CAPEX production-like activation remains blocked by the imported gate set.

## 2026-06-02 (CAPEX PR004/PR005 platform-readiness gates)
- Audit decision: CAPEX invariant audit entries use `hard_gate`, `known_gap`, and `advisory` modes; only resolved P0 safety invariants hard-fail, while known imported gaps are reported without permanently red CI.
- Generated-artifact decision: new generated artifacts should use deterministic `canonical_json_bytes` plus `persist_generated_artifact_effects(...)` when a task needs canonical JSON bytes, root-confined storage, digest validation, and canonical `artifact.version.created` emission.
- Migration decision: broad generated-artifact call-site migration is deferred to later CAPEX generated-artifact tasks; `TASK-0238` adds the foundation helper and focused proof only.
- Activation decision: `TASK-0237` and `TASK-0238` close repo platform-readiness gates only; CAPEX production-like activation remains blocked by the imported gate set.

## 2026-06-02 (CAPEX PR006/PR007 Platform Foundation v0)
- Shared-effect decision: workflow-run resolution, workflow artifact input binding replay/conflict/replace behavior, and edge execution replay validation now live in shared runtime effects instead of private logistics-only helper code.
- Drift decision: logistics target-run resolution fails closed with `activation_key_drift_detected` when an existing same-scope, same-partition run has a different activation key.
- Branch-gate decision: `docs/planning/CAPEX_PLATFORM_FOUNDATION_V0.md` declares PF0 for repo platform readiness only and records `foundation/ip5` as the platform-foundation branch class.
- Activation decision: PF0 does not activate CAPEX production-like runtime, pilot readiness, raw corpus use, release/deploy work, project membership runtime, or SourceRef/source-occurrence runtime.

## 2026-06-02 (CAPEX PR008/PR009 release and backup readiness)
- Release-build decision: `scripts/build_release_image.py` builds an API-runtime image from the canonical `release_source_bundle`, can push to operator-supplied registry coordinates, and records digest-addressed release evidence in `release_manifest.json`.
- Deploy-boundary decision: the pushed API image is release evidence/build output only; `release_source_bundle` remains the deploy input until later release/deploy gates explicitly change the operator contract.
- Backup-skeleton decision: `scripts/prepare_predeploy_backup.py` writes validate-only `backup_manifest.json` evidence for the DB/artifact/release tuple and secret/config references, without copying live state or claiming restore proof.
- Activation decision: `TASK-0241` and `TASK-0242` close release/backup readiness gates only; CAPEX production-like activation, pilot readiness, deployment approval, raw corpus use, and restore proof remain blocked.

## 2026-06-02 (CAPEX PR019 reconciler dry-run)
- Reconciler decision: logistics reconciliation is introduced as `logistics_reconciler_dry_run.v1`, a deterministic read-only report over canonical workflow runs, artifact versions, edge executions, and workflow input bindings.
- CLI decision: `handoffs reconcile-dry-run` opens SQLite in read-only mode and exposes no apply or repair option in this tranche.
- Boundary decision: missing seed/run/input findings, late reporting conflicts, and stale/drifted handoff rows are reported without mutation; repair/apply mode remains deferred to the later gated reconciler-apply task.
- Activation decision: `TASK-0252` closes dry-run reporting only; it does not authorize CAPEX production activation, deployment approval, raw corpus use, or target-side repair.

## 2026-06-02 (CAPEX PR020 operator home)
- Root-route decision: `/` now renders the operator home posture surface instead of redirecting to `/demo/logistics`; the demo route remains an explicit launcher.
- Operator-visibility decision: `GET /api/v1/operator/home` exposes current server-derived viewer posture plus the logistics reconciler dry-run failure-state report scoped to the request tenant/domain.
- Shared-env decision: when `actor_switching_allowed=false`, the frontend hides actor-switching controls and the switcher affordance entirely.
- Boundary decision: operator-home findings show missing seeds, stale edges, late reports, drift, and missing blobs without applying repairs or exposing local blob paths.
- Activation decision: `TASK-0253` closes operator visibility only; it does not authorize CAPEX production activation, deployment approval, raw corpus use, or reconciler apply mode.

## 2026-06-02 (CAPEX CLEAN-001 approval response hooks)
- Boundary decision: generic `approval.respond` records the approval transition and emits `approval.responded`; domain-specific logistics publish/finalize consequences live in registered approval-response hooks.
- ADR decision: `docs/adr/ADR-005-approval-response-domain-hooks.md` records the hook boundary, generic-handler forbidden imports, and transactional rollback posture.
- Audit decision: CAPEX invariant audit now hard-gates approval-response hook extraction instead of reporting approval side-effect coupling as a known gap.
- Activation decision: `TASK-0257` closes approval domain-boundary cleanup only; it does not authorize CAPEX production activation, deployment approval, raw corpus use, or new CAPEX runtime behavior.

## 2026-06-03 (CAPEX v5 carry-forward reconciliation)
- Source-lineage decision: `V5-TASK-*` rows embedded in the CAPEX v6 planning package are preserved as historical aliases only; they are not active backlog under the v6 baseline.
- Backlog decision: `TASK-0572` through `TASK-0581` are closed as reconciled v5 carry-forward aliases, with canonical remaining work owned by the v6/native task refs recorded in `canonical_task_refs`.
- Gate-map decision: `V5-GATE-*`, `V5-RISK-*`, and `V5-OD-*` rows remain in the gate/risk/decision map as `historical_reference` provenance, not independent activation gates.
