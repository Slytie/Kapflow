# Source lineage from CompanyOS packet into this repo

This file preserves where the current merged architecture came from so future contributors do not lose the deeper rationale.

## Primary source packet reviewed
- `CompanyOS_Composable_Workflows_Packet_v0_3.zip`

## Source -> repo mapping

| CompanyOS source | Role in source packet | Repo-native merged destination |
|---|---|---|
| `CompanyOS_Context_and_Handoff_v0_3.md` | overall philosophy and handoff | `docs/vision/PROJECT_VISION.md`, `docs/planning/MERGER_BACKLOG.md` |
| `CompanyOS_Mathematical_Note_v0_3.tex/pdf` | formal substrate and stable-core math | `docs/vision/MATHEMATICAL_FOUNDATIONS.md` |
| `ADR_013_Agent_Runtime_Contract_v0_5.md` | agent runtime, pinned execution, tool-plane gating | `docs/architecture/orchestration_semantics.md`, `docs/security/sandbox-and-approvals.md`, `docs/architecture/event_model.md` |
| `ADR_014_WorkGraph_and_Operator_Cascade_v0_3.md` | work-intelligence spec family and composition | `docs/architecture/EXECUTION_OVERLAY_MODEL.md`, `docs/architecture/DERIVATION_AND_GENERATION_POLICY.md` |
| `CompanyOS_Spec_Template_System_v0_2.md` | stable core, extensible body, spec families | `docs/architecture/EXECUTION_OVERLAY_MODEL.md`, `docs/templates/` |
| `S3_A03_Threat_Model_v0_7.md` | abuse cases and controls | `docs/vision/THREAT_MODEL_ADDENDUM.md`, `docs/security/sandbox-and-approvals.md`, signoff checklists |
| `Stage3_SpikesRepo_Impact_Plan_v0_2.md` | migration thoughts for spike runtime | `docs/planning/MERGER_BACKLOG.md`, `docs/architecture/orchestration_semantics.md` |
| `Operator_Catalog_Summary_v0_1.md` | operator/kernel direction | `docs/architecture/EXECUTION_OVERLAY_MODEL.md` |

## Deliberate changes made during merger
The repo does **not** import the CompanyOS packet as a second authored workflow-definition layer.

Instead it keeps:
- the philosophy,
- the mathematics,
- the threat model,
- and the lowering target,

while making the repo itself the only authored business source.

## What is preserved but deferred
The following ideas are preserved in backlog form rather than promoted to Stage 4 source-of-truth artifacts:
- authored `WorkflowSpec`
- `ProcessPatch` lifecycle
- WorkGraph materialization
- general multi-level study/program workflows
- projection DSLs
- cross-tenant learning mechanisms
