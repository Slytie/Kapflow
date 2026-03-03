# Schedule Planning v1 (same-day delivery workflow)

This folder contains the canonical authored workflow surface for Schedule Planning.

- `WORKFLOW_CONTRACT.yaml` - workflow stages, temporal partition semantics, eligibility hints, and event inventory
- `ARTIFACT_MAP.yaml` - dataset keys mapped to the template pack
- `ACCEPTANCE_CRITERIA.md` - tests-as-spec guidance
- `OPERATING_MODEL.md` - domain assumptions, temporal semantics, optimization decomposition, and review / escalation model
- `DECISION_CATALOG.yaml` - canonical decision IDs and evidence requirements
- `EXECUTION_PROFILE.yaml` - canonical execution pattern and bounded exception-loop semantics

Template pack is in `fixtures/workflows/schedule_planning/template_pack/`.
That template pack already includes both empty templates and synthetic completed examples that should seed future runtime scenario tests.

## Stage 4 note
Schedule Planning is the current primary runtime/debug wedge. The first acceptance target is a fully-agentive Stage03-Stage07 path that still uses the canonical workflow/task/approval/event/pointer substrate.

## Important architectural consequences
- `ScheduleDateID` is not the full runtime time model; service interval start/end and timezone are also pinned.
- Stage07 is issue-scoped and activation-keyed; repeated replan work stays inside one service-day workflow run.
- Replay, stage rerun, retry, and historical backfill are distinct operations.

## Alignment rule
Any external runbook pack, tool matrix, approval log sheet, or generated CompanyOS IR for Schedule Planning must be derived from the files in this folder and must not become a peer source of workflow truth.
