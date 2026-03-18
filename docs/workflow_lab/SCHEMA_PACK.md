# Workflow Lab Schema Pack

Workflow Lab now has a thin core schema pack under `schemas/workflow_lab/`.

These schemas are **non-authoritative evidence contracts** for internal lab use. They exist so future normalization work can target one stable machine-readable shape without turning Workflow Lab into a runtime platform or a second truth system.

## What this pack covers
- `freshness.schema.json`: shared freshness and provenance metadata for lab evidence.
- `variant_spec.schema.json`: execution-variant identity under fixed workflow semantics.
- `run_profile.schema.json`: thin metadata about how a lab run is framed.
- `world_instance.schema.json`: world identity and isolation metadata only.
- `run_report_core.schema.json`: normalized report envelope for future lab evidence.
- `compare_report.schema.json`: thin compare-report envelope for later report-to-report comparison.

## What these schemas are for
The next normalization task can map current repo outputs into `run_report_core` without redefining their meaning:
- `pilot_summary`
- `inspection_packet`
- `certification_manifest`

TASK-0119 now uses this schema pack to emit adjacent `workflow_lab_run_report.json` and `workflow_lab_review_packet.md` files over those existing outputs.

Later work may also normalize selected runtime workspace/export bundles, but that does not change the authority boundary.

## What this task does not add
TASK-0118 does **not** add adapters, runtime APIs, execution machinery, or semantic-version comparison.

It also does **not**:
- create a public Workflow Lab surface
- add `src/onetruth/workflow_lab/`
- define a world-materialization engine
- redefine promotion as lab-to-prod runtime mutation

## Boundary reminders
- Lab outputs remain evidence for review, certification, and release. They are not production truth.
- `VariantSpec` captures execution variation under fixed semantics; it is not a semantic-version branch.
- `RunProfile` is framing metadata, not runtime execution policy.
- `WorldInstance` is identity/provenance only in this tranche, not a sanctioned prod-clone workflow.
- `CompareReport` is a report envelope only in this tranche, not a comparison engine.
