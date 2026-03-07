# Logistics Ops Family v1

This folder contains the authored workflow-family surface for the logistics domain.

Files:
- `WORKFLOW_FAMILY.yaml` - canonical family/module/edge definition over workflow packs
- `PARTITION_TRANSFORMS.yaml` - typed partition-transform registry for family edges

Design posture:
- this is a definitions-layer extension over the fixed Strategy A substrate seam,
- family edges compile deterministically and fail closed on underspecified semantics,
- first runtime slice is `weekly_schedule_planning.v1 -> live_dispatch.v1`,
- other family members stay visible as staged extension/deferred modules.
