# Workpage dependency and calculation rationale

## Why the schedule page and route-demand page must stay separate
The domain objects are different.

Let:
- `A_r^v` = route-demand artifact version
- `A_s^k` = schedule draft artifact version
- `A_p^u` = driver-preferences artifact version
- `I_h` = other hard inputs such as approved availability, capabilities, and actual hours

Then:

```text
W_route_demand = Projection(route_demand_artifact)
W_schedule = Projection(schedule_artifact, route_demand_artifact, hard_inputs, soft_inputs)
```

The schedule page can display route-demand-derived counts, but it should not become the canonical editor for route demand.

## Why live recalculation belongs on the schedule page
The SME asks for immediate operator confidence while moving work between drivers.
That means the page needs deterministic preview semantics:

```text
preview_state = Calculate(schedule_draft + in_page_reassignment_delta, route_demand, hard_inputs, soft_inputs)
```

`preview_state` should include:
- top-bar day totals,
- per-driver hours,
- scheduled routes,
- on-call counts,
- compliance / capacity checks,
- available-driver counts and optional highlighting.

## Why a machine-readable calculation snapshot is worth storing
If the page shows rich derived state, then saved draft versions need pinned evidence of that derived state.
Otherwise the UI is forced either to:
- recompute against today’s dependencies, which can be historically wrong, or
- duplicate calculation logic in the client, which is fragile.

So on save:

```text
schedule_draft + edits -> new_schedule_draft + calculation_snapshot_evidence
```

This does not violate one-truth, because it is derived evidence tied to a saved draft version, not a competing source of business truth.

## Why dependency drift must be explicit
If route demand changes from `A_r^v` to `A_r^(v+1)`, existing schedule drafts built against `A_r^v` become stale relative to current operational demand.

The correct response is not silent mutation. It is:

```text
new_route_demand -> drift detected on existing schedule draft -> rerun / refresh follow-up
```

That keeps artifact lineage immutable and makes operational refresh explicit.

## Why accepted history differs from draft history
Draft history is a supersedes chain:

```text
draft_1 -> draft_2 -> draft_3
```

Accepted history is an official weekly series across time:

```text
published_week_minus_1, published_week, published_week_plus_1
```

These answer different questions and must not share navigation semantics.
