# PROJECTION_COHERENCE_HARNESS.md

## Purpose
Projection packets are derived and regenerable. They are never a second truth system.

This harness defines how Stage 4 detects and handles projection drift so approval-critical packets fail visibly instead of silently masking canonical mismatches.

## First runtime slice scope
This slice covers three projection kinds that are already used in runtime/operator flows:
- `workspace_official_outputs` (API workspace view)
- `workspace_export_bundle` (ZIP packet export)
- `handoff_operator_view` (`handoffs show/list` operator view)

## Policy matrix (block vs warn)
| Projection kind | Drift policy | Visible behavior |
|---|---|---|
| `workspace_official_outputs` | `warn_visible` | Return payload with explicit failed coherence metadata + warning entry |
| `workspace_export_bundle` | `block` | Export is rejected with `projection_coherence_failed` error payload |
| `handoff_operator_view` | `warn_visible` | Return payload with explicit failed coherence metadata |
| `non_critical_projection/*` (future default class) | `allow` | Render payload and annotate coherence status without blocking |

Rule:
- `block` is used for approval-critical packet surfaces.
- `warn_visible` is used for operator/read surfaces where we must not hide drift but can still render context.

## Canonical-field checklists

### Workspace/export official outputs
Each output row is derived from canonical pointer + artifact rows and must preserve:
- `pointer_id`
- `artifact_version_id`
- `artifact_kind`
- `dataset_key`
- `partition_kind`
- `partition_key`

Drift classes:
- `official_output_pointer_missing`
- `official_output_pointer_lineage_missing`
- `official_output_artifact_missing`
- `official_output_artifact_lineage_missing`
- `official_output_artifact_version_mismatch`
- `official_output_kind_mismatch`
- `official_output_dataset_mismatch`
- `official_output_partition_mismatch`

### Handoff operator view
Each edge row must preserve coherence among:
- `source_workflow_run_id`
- `source_artifact_version_id`
- `seed_artifact_version_id`
- `target_workflow_run_id` (when `status=activated`)
- `target_workflow_id`
- `target_partition_key`
- `trigger_ref` (when `status=activated`)

Drift classes include:
- `handoff_source_workflow_run_missing`
- `handoff_source_artifact_missing`
- `handoff_source_artifact_run_mismatch`
- `handoff_seed_artifact_missing`
- `handoff_target_run_missing`
- `handoff_target_workflow_mismatch`
- `handoff_target_partition_mismatch`
- `handoff_trigger_ref_missing`
- `handoff_trigger_ref_artifact_missing`

## Runtime behavior

### Coherence result payload
Projection responses include:
- `projection_id`
- `projection_kind`
- `coherence_status` (`passed|failed`)
- `policy` (`on_drift`, `emit_event`)
- `failure_code` (first failing rule)
- `issues[]` (all detected issues)
- `source_refs[]` (canonical refs used)

Required source-lineage posture for this slice:
- a failed result is emitted when required pointer lineage fields are missing (`pointer_id`, `artifact_version_id`, `artifact_kind`, `dataset_key`, `partition_kind`, `partition_key`)
- a failed result is emitted when required linked artifact lineage fields are missing (`artifact_version_id`, `artifact_kind`, `dataset_key`, `partition_kind`, `partition_key`)

### Event emission
On failed coherence, runtime emits:
- `projection.coherence_failed`

Event contract:
- no mutation of workflow/task/approval/artifact/pointer objects
- links include `projection`, and `workflow_run` when resolvable
- payload includes `projection_id`, `projection_kind`, `failure_code`
- idempotency-keyed to avoid duplicate event spam for the same failure fingerprint

### Authoritative-state safety
Coherence checks may gate or warn projection rendering, but they do not change canonical business state. The only write side-effect in this slice is explicit `projection.coherence_failed` timeline evidence.

## Test coverage (first slice)
- `tests/runtime/test_projection_coherence.py`
  - drifted workspace official-output view -> warn + event
  - drifted export official-output view -> block + event
  - missing source lineage on export official-output summary -> block + event
  - drifted handoff operator view -> warn + event
  - explicit block-vs-warn policy assertion
