# Workflow Lab Normalization

TASK-0119 adds the first thin normalization seam for Workflow Lab.

These outputs remain non-authoritative evidence. They are derived from repo outputs the system already knows how to emit; they do not create a second runtime, a public lab surface, or a new promotion path.

## Normalized source families
- Weekly Stage04 pilot outputs from `logistics_weekly_agent_pilot.py`
- Realistic schedule-planning pilot outputs from `realistic_schedule_planning_pilot.py`
- Current capability certification outputs from `current_capability_certification.py`

## Emitted filenames
Each normalized source now emits two adjacent derived artifacts:
- `workflow_lab_run_report.json`
- `workflow_lab_review_packet.md`

For weekly Stage04 and realistic schedule-planning pilots, those files live beside each per-pilot `inspection_packet.json`.

For current capability certification, those files live in each scenario output directory. Certification emits one normalized report per scenario row; it does not emit one aggregate certification-level `run_report_core`.

## Current normalization targets
The normalization layer maps existing repo outputs into `schemas/workflow_lab/run_report_core.schema.json` using the thin shared schema pack from [SCHEMA_PACK.md](/Users/tylerclark/git/pythonProject/companyos/docs/workflow_lab/SCHEMA_PACK.md).

Current source-to-report mapping is intentionally narrow:
- weekly Stage04 inspection packets and pilot summaries normalize to `source_kind = weekly_stage04_pilot`
- realistic schedule-planning inspection packets and pilot summaries normalize to `source_kind = schedule_planning_pilot`
- certification manifest scenarios normalize to `source_kind = current_capability_certification`

The derived review packet is rendered only from the normalized report shape, so the human-readable review artifact and the machine-readable report stay aligned to the same evidence contract.

## What this task does not add
TASK-0119 does **not**:
- add execution adapters or a general Workflow Lab runner
- add freshness guards or readiness enforcement
- add `compare_report` generation
- add a public Workflow Lab API or UI
- add `src/onetruth/workflow_lab/`
- add world materialization or semantic-version coexistence machinery

## Next step
With normalization now in place, the next Workflow Lab step is TASK-0120: document the release-mediated promotion gate and freeze the explicit `G1` / `G2` stop lines.
