# SME decisions and grey areas — 2026-04-04

## Frozen decisions
1. Route change handling is not EOD-specific.
2. Schedule workpage edits are about moving routes between drivers using the heatmap.
3. Accepted-version arrows are accepted-only.
4. Driver preferences are soft/advisory in v1, but high priority.
5. Route-demand changes should create drift / rerun follow-up, not automatic agentic re-scheduling, in v1.
6. Date-specific driver exceptions are out of scope for this packet.

## Defaults adopted so implementation can proceed
1. “Dispatch workpage” for plus/minus route changes is implemented as a new `route-demand-v0` surface, not by extending `eod-v0`.
2. Accepted-series grouping means official weekly schedules for the same operation / site / team / planning scope, ordered by week.
3. A draft page may display accepted-history navigation, but those controls never traverse draft history.
4. Route-demand +/- intent is day-oriented in UX, but backend-owned in how it maps to slot-based requirement rows.

## Short unresolved questions / grey areas
1. Does the repo already expose a stable explicit scope key for “same operation / site / team / planning scope”?
   - If yes, use it for accepted-series grouping.
   - If not, add one in this epic.
2. Does current route-demand data already contain a stable daily editable bucket for plus/minus operations?
   - If yes, use it.
   - If not, add a backend normalization helper rather than inventing UI heuristics.
3. On draft pages, should accepted-history arrows be visible at all times, or only when an accepted counterpart for the same week exists?
   - Default: visible when the backend can resolve an accepted-series anchor; otherwise disabled.

## Implementation guardrails
- The frontend must not invent workflow meaning for these grey areas.
- The backend should expose resolved answers in workpage contracts once the scope key and route-demand mapping policy are finalized.
