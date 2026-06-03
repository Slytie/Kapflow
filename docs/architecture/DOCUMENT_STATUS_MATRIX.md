# Document status matrix

This file prevents stale guidance by classifying major documents and directories by authority level.

## Status classes
- **AUTHORITATIVE SOURCE** - hand-authored material that defines business or runtime truth, or the official read-path/routing rules for contributors.
- **COMPILED ARTIFACT** - immutable runtime artifact derived from authoritative source for execution.
- **GENERATED DERIVATIVE** - human-facing or machine-facing material regenerated from authoritative source and never hand-edited as source.
- **HISTORICAL RATIONALE** - preserved context, research, or external patterns explaining why a decision was made; not a rule source.
- **BACKLOG / DEFERRED** - nuance that matters later but is intentionally not in force now.
- **EVIDENCE / FIXTURE** - examples, test traces, or synthetic artifacts used for validation.

## Repo-wide matrix

| Path | Status | Notes |
|---|---|---|
| `README.md` | AUTHORITATIVE SOURCE | entrypoint and repo posture |
| `AGENTS.md` | AUTHORITATIVE SOURCE | read order and non-negotiable guardrails for Codex/humans |
| `LLM_RUNBOOK.md` | AUTHORITATIVE SOURCE | task execution protocol |
| `codex/CODEX_CONTEXT.yaml` | AUTHORITATIVE SOURCE | machine-friendly routing index for Codex |
| `codex/context/README.md` | AUTHORITATIVE SOURCE | how to use context packs |
| `codex/context/*.md` | AUTHORITATIVE SOURCE | epic routing aids; subordinate to cited authoritative contracts if conflicts arise |
| `codex/tasks/*.md` | AUTHORITATIVE SOURCE | active task briefs |
| `docs/status/CURRENT_FOCUS.md` | AUTHORITATIVE SOURCE | current execution priority |
| `docs/status/DECISIONS_SINCE_LAST.md` | AUTHORITATIVE SOURCE | merge-era decision log |
| `docs/vision/PROJECT_VISION.md` | AUTHORITATIVE SOURCE | philosophy and product vision |
| `docs/vision/MATHEMATICAL_FOUNDATIONS.md` | AUTHORITATIVE SOURCE | formal substrate and refinement laws |
| `docs/vision/THREAT_MODEL_ADDENDUM.md` | AUTHORITATIVE SOURCE | security philosophy carried into current repo |
| `docs/vision/SOURCE_LINEAGE.md` | HISTORICAL RATIONALE | maps CompanyOS packet ideas into repo-native documents |
| `docs/architecture/AUTHORITY_MODEL.md` | AUTHORITATIVE SOURCE | single truth system definition |
| `docs/architecture/EXECUTION_OVERLAY_MODEL.md` | AUTHORITATIVE SOURCE | canonical agentic overlay model |
| `docs/architecture/DERIVATION_AND_GENERATION_POLICY.md` | AUTHORITATIVE SOURCE | lowering and generation rules |
| `docs/architecture/LOWERING_CONTRACT.md` | AUTHORITATIVE SOURCE | source-to-IR / source-to-runbook compilation contract |
| `docs/architecture/RUNTIME_OBJECT_MODEL.md` | AUTHORITATIVE SOURCE | canonical runtime object vocabulary |
| `docs/architecture/DOCUMENT_STATUS_MATRIX.md` | AUTHORITATIVE SOURCE | this classification table |
| `docs/architecture/AGENTIC_LAYER_AND_MERGE_REVIEW.md` | HISTORICAL RATIONALE | narrative precursor to the stronger authority model |
| `docs/architecture/MERGER_CHANGESET.md` | HISTORICAL RATIONALE | exact repo-level changes applied during merger |
| `docs/adr/README.md` | AUTHORITATIVE SOURCE | ADR routing index |
| `docs/adr/*.md` | AUTHORITATIVE SOURCE | accepted architecture decisions |
| `docs/planning/STAGE4_PLAN.md` | AUTHORITATIVE SOURCE | current stage plan |
| `docs/planning/RUNTIME_BOOTSTRAP.md` | AUTHORITATIVE SOURCE | chosen Stage 4 runtime stack, persistence model, and repo layout |
| `docs/planning/FIRST_RUNTIME_SLICE.md` | AUTHORITATIVE SOURCE | ordered first coding tranche and target file locations |
| `docs/planning/EPICS.md` | AUTHORITATIVE SOURCE | epic index |
| `docs/planning/TASK_INDEX.md` | AUTHORITATIVE SOURCE | task index |
| `docs/planning/TEST_STRATEGY.md` | AUTHORITATIVE SOURCE | test portfolio and CI rules |
| `docs/planning/TEST_MATRIX.md` | AUTHORITATIVE SOURCE | core invariant-to-test mapping |
| `docs/planning/TDD_IMPLEMENTATION_PLAN.md` | AUTHORITATIVE SOURCE | implementation working mode and test-first rules |
| `docs/planning/MERGER_BACKLOG.md` | BACKLOG / DEFERRED | preserves deferred CompanyOS ideas and caveats |
| `docs/planning/epics/*.md` | AUTHORITATIVE SOURCE | active epic definitions |
| `docs/planning/WORKPAGE_DEVELOPMENT_GUIDE.md` | AUTHORITATIVE SOURCE | workpage registry and extension-point guidance |
| `docs/domains/logistics/DOC_INVENTORY.yaml` | AUTHORITATIVE SOURCE | logistics document classification and routing inventory |
| `docs/domains/logistics/current-state/*.md` | AUTHORITATIVE SOURCE | logistics current-state docs; subordinate to workflow packs and schemas if conflicts arise |
| `docs/domains/logistics/archive/*.md` | HISTORICAL RATIONALE | preserved logistics plans, briefs, audits, and closeout notes |
| `docs/workflows/*/v1/WORKFLOW_CONTRACT.yaml` | AUTHORITATIVE SOURCE | workflow semantics |
| `docs/workflows/*/v1/ARTIFACT_MAP.yaml` | AUTHORITATIVE SOURCE | official artifact surfaces |
| `docs/workflows/*/v1/DECISION_CATALOG.yaml` | AUTHORITATIVE SOURCE | canonical decisions |
| `docs/workflows/*/v1/EXECUTION_PROFILE.yaml` | AUTHORITATIVE SOURCE | canonical execution overlay |
| `docs/workflows/*/v1/ACCEPTANCE_CRITERIA.md` | AUTHORITATIVE SOURCE | proof obligations |
| `docs/workflows/*/v1/OPERATING_MODEL.md` | AUTHORITATIVE SOURCE | operational interpretation of contract |
| `schemas/**` | AUTHORITATIVE SOURCE | schema-level contracts |
| `docs/patterns/README.md` | AUTHORITATIVE SOURCE | usage rules for the pattern library |
| `docs/patterns/PATTERN_INDEX.yaml` | AUTHORITATIVE SOURCE | routing index for external pattern cards |
| `docs/patterns/cards/*.md` | HISTORICAL RATIONALE | curated external patterns mapped back to our invariants |
| `docs/patterns/sources/**` | HISTORICAL RATIONALE | original and converted external reference material |
| `docs/research/README.md` | HISTORICAL RATIONALE | how to use the research library |
| `docs/research/AGENT_DIGEST.md` | HISTORICAL RATIONALE | curated guide to deeper research |
| `docs/research/full/**` | HISTORICAL RATIONALE | full research notes and conversions |
| `fixtures/workflows/**/template_pack/**` | EVIDENCE / FIXTURE | synthetic artifacts and templates |
| `fixtures/workflows/**/golden_event_traces/**` | EVIDENCE / FIXTURE | examples and future acceptance fixtures |
| `tests/README.md` | AUTHORITATIVE SOURCE | test-portfolio entrypoint and directory purpose |
| `Makefile` | AUTHORITATIVE SOURCE | stable validation / acceptance command entrypoint |
| `scripts/**` | AUTHORITATIVE SOURCE | validation and repository consistency checks |
| `tests/**` | AUTHORITATIVE SOURCE | executable specifications and future test suites |
| external runbook packs | GENERATED DERIVATIVE | regenerate from repo source; do not treat as authority |
| tool registry matrices | GENERATED DERIVATIVE | same |
| approval/decision logs | GENERATED DERIVATIVE | same |
| CompanyOS IR specs | GENERATED DERIVATIVE | generated lowering target |
| compiled `ExecutionSpec` | COMPILED ARTIFACT | immutable execution pin for a concrete run |

## Required behavior
- If a document changes repo truth, it must live in an **AUTHORITATIVE SOURCE** path.
- If a document is generated, the source and generation rule must be updated instead of hand-editing the derivative.
- If a document is kept only for context, mark it as **HISTORICAL RATIONALE** or **BACKLOG / DEFERRED**.
- Do not let pattern cards, research notes, or context packs silently override authoritative contracts.
- Do not leave ambiguous documents whose status is unclear.
