# GENERATOR_PROTOTYPE_PLAN.md

This plan defines the first real generator prototype for TASK-0032.

## 1) Prototype inputs

Workflow target:
- `schedule_planning.v1`

Authoritative source inputs (hashed in lineage):
- `docs/workflows/schedule_planning/v1/WORKFLOW_CONTRACT.yaml`
- `docs/workflows/schedule_planning/v1/ARTIFACT_MAP.yaml`
- `docs/workflows/schedule_planning/v1/DECISION_CATALOG.yaml`
- `docs/workflows/schedule_planning/v1/EXECUTION_PROFILE.yaml`
- `docs/workflows/schedule_planning/v1/ACCEPTANCE_CRITERIA.md`

Input rules:
- source paths are repo-native only,
- no generated file is treated as input to the same generation pass,
- every input path is recorded with `sha256:*` in lineage.

## 2) Prototype outputs

Generated outputs for one workflow:
- runbook markdown:
  - `build/generated/runbooks/schedule_planning.v1/runbook.md`
- CompanyOS-style IR JSON:
  - `build/generated/companyos_ir/schedule_planning.v1.json`
- lineage manifest JSON:
  - `build/generated/lineage/schedule_planning.v1.lineage.json`

Lineage manifest fields:
- `workflow_id`
- `workflow_version`
- `generator_version`
- `generated_at`
- `sources[]` with `path` + `sha256`
- `outputs[]` with `path` + `sha256` (runbook + IR)

## 3) Output content scope

Runbook must include:
- explicit generated non-authoritative banner,
- stage list and purpose,
- artifact keys by stage (from `ARTIFACT_MAP.yaml`),
- approvals/decisions (from `DECISION_CATALOG.yaml`),
- spawn-rule and loop semantics (from `WORKFLOW_CONTRACT.yaml` + `EXECUTION_PROFILE.yaml`),
- operator checklist snippets from `ACCEPTANCE_CRITERIA.md`.

IR must include:
- `workflow_id` + `workflow_version`,
- stages and stage-scoped semantics,
- artifacts from artifact map,
- decisions from decision catalog,
- spawn rules from workflow contract semantics,
- required event references from workflow contract event inventory.

## 4) Freshness check strategy (`--check`)

`--check` behavior:
1. load authoritative source files,
2. re-render expected runbook and IR deterministically,
3. compare expected content to existing generated files,
4. recompute source hashes and compare with lineage `sources`,
5. verify lineage `outputs` hashes match current generated runbook/IR files.

Failure conditions:
- missing generated files,
- generated runbook/IR content drift,
- lineage source hash drift,
- lineage output hash mismatch,
- generator/workflow metadata mismatch in lineage.

`make generated-check` runs the freshness check and fails CI on staleness.

## 5) No-invention constraints

Generator must fail closed if source is inconsistent or would imply invented semantics.

Required validation:
- artifact-map stage IDs must exist in workflow contract,
- decision `stage_id` values must exist in workflow contract,
- decision evidence keys must exist in artifact map,
- execution-profile stage IDs must exist in workflow contract,
- execution-profile decision refs must exist in decision catalog,
- execution-profile required evidence keys must exist in artifact map,
- spawn-rule target stage IDs must exist in workflow contract.

Generator must not invent:
- stage IDs,
- dataset keys,
- decision IDs,
- spawn rules,
- required events,
- official output semantics.

## 6) Spawn/follow-on rendering model

Spawn semantics are rendered from authored source only:
- `WORKFLOW_CONTRACT.yaml`:
  - `task_spawn_policy`
  - `spawn_budget`
  - `spawn_rules` (`id`, `when`, `target_stage_id`, `task_kind`, `candidate_roles`)
- `EXECUTION_PROFILE.yaml`:
  - stage `execution_pattern`
  - stage-level bounded-loop guidance where present

Runbook rendering:
- stage-by-stage section showing policy, budgets, and follow-on rules.

IR rendering:
- normalized `spawn_rules[]` list linked to parent stage ID plus rule fields.

## 7) Authority boundary reminder

Generated runbook and IR are non-authoritative derived artifacts.
Authoritative semantics remain in repo-native workflow source + canonical runtime substrate.
