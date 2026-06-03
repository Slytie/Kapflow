> Document classification: historical logistics context. See `docs/domains/logistics/DOC_INVENTORY.yaml` for current authority.

# Logistics Workpages Schedule Comparison Shortcuts Note

## Purpose
This note captures the bounded shortcuts currently used by the editable `schedule-v0` comparison view so they can be replaced deliberately later without re-discovering them from the UI code.

## Active shortcuts
- Historical demo fallback stays frontend-only.
  When the real current service date is outside the displayed week and the displayed week is in the past, the comparison layer falls back to the artifact-selected day so historical March demos still show inline dispatch-report cells.

- Current-week dispatch-report cells are synthesized from the previous-week-reality payload.
  The current scheduled-week past-day cells in the editor reuse the pinned prior-week reality contract as a stand-in for same-week dispatch-report truth instead of reading a dedicated same-week reporting feed.

- Visible heatmap week can override stale summary week metadata.
  If the artifact summary `operational_week_start` disagrees with the visible heatmap dates, the frontend trusts the visible heatmap week to keep the comparison layout aligned with what the operator is editing.

- The far-left previous-week block does not have a true trailing-7 summary window before the displayed history range.
  The bracketed summary metric on that left comparison block still uses the bounded displayed-week accumulation because the current payload does not include history before the shown previous week.

- Comparison mode is inferred in the frontend instead of authored by the backend.
  The editor currently derives `current_week`, `historical_demo_week`, and `future_week` from the displayed week versus the real `America/Vancouver` service date because the workpage contract does not yet expose an explicit comparison or elapsed-day mode.

## Follow-up fixes
- Add a backend-authored comparison-mode signal so the UI does not infer historical-demo versus future-week behavior on its own.
- Introduce a same-week dispatch-report source for elapsed current-week days so those cells no longer depend on the pinned previous-week reality contract.
- Expose enough historical actual-hours context to compute a true rolling 7-day summary for the far-left previous-week block.
- Remove the historical demo selected-day fallback once canonical demo fixtures or backend comparison metadata make it unnecessary.
