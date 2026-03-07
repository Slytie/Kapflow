# Weekly Schedule Planning v1 - operating model

## Why this workflow exists
This pack models the **pre-week / Friday** planning loop:
1. ingest Amazon route horizon updates;
2. merge approved availability and recent actual-hours truth;
3. build a draft weekly base schedule;
4. require manager review;
5. publish the official weekly base schedule;
6. emit one per-day seed for live dispatch.

Day-of replan is **not** owned by this workflow. The handoff is `live_dispatch.v1`.

## First-principles formalism
Let:
- `D` be drivers,
- `T` be service dates in one planning week,
- `R_t` be the exogenous Amazon route count / slot set for date `t`,
- `A_{d,t}` be approved availability,
- `H_d` be recent actual-hours state used for WHC checks.

We solve an assignment problem, not a vehicle-routing problem.

Decision variable:
- `x_{d,r} in {0,1}` meaning driver `d` is assigned to route slot `r`.

Core hard constraints:
- each route slot is assigned to at most one driver;
- each driver is assigned to at most one primary shift per service date unless a specific extra-shift rule allows otherwise;
- `A_{d,t} = 1` for any assigned driver;
- WHC deterministic checks must pass against `H_d` plus the proposed schedule.

Objective (qualitative form):
- minimize uncovered routes,
- minimize WHC risk,
- minimize overtime and instability,
- minimize unfair distribution of extra work.

The important point is that Amazon route supply is upstream truth; the system is deciding **driver-to-route assignment**.

## Key upstream truths
- Amazon sends weekly / horizon route updates, often on Friday, and they may continue to move.
- The Google-Form-based request system is the intake path for time off, but only approved decisions change planning truth.
- Recent EOS / dispatch actuals should influence forecast compliance for the next plan.

## Review and publication boundary
Draft generation may use code plus narrow LLM drafting help for the human-readable ops packet.
Official publication requires:
- review confirmation,
- manager approval,
- pointer promotion.

## Handoff to live dispatch
The published weekly base schedule is immutable.
This workflow produces one daily seed packet per service date. Those seeds are the input state for `live_dispatch.v1`.
