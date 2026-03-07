# Live Dispatch v1 - operating model

## Why this workflow exists
This pack models the **day-of** loop after the base schedule is already published:
- daily route-count changes,
- ERO / extra route notices,
- manual station requests,
- sick calls and no-shows,
- rescue / crash-sort style recovery work.

## State model
Let:
- `B_t` be the immutable base schedule seed for service date `t`,
- `E_t` be the ordered stream of day-of events,
- `Delta_t` be the ordered set of promoted replan deltas.

Operational truth for the day is:

`LivePlan_t = B_t ⊕ Delta_t`

where the base seed is never mutated.

## Candidate-generation formalism
For each issue `i`, candidate set `C_i` is built in two steps.

1. Hard filter:
remove any driver that violates
- approved availability,
- minimum rest,
- max daily hours,
- max rolling 7-day hours,
- consecutive-day limits,
- any explicit role / shift-type incompatibility.

2. Soft ranking:
rank remaining drivers by
- on-call eligibility,
- fewer assigned shifts this week,
- lost-work credit from prior cancellations,
- reliability / recent attendance,
- stability of already-communicated assignments.

Hard filters are deterministic code. LLM help, if used at all, is bounded to short rationale or packet drafting.

## Major-change boundary
Small changes may finish after required review confirmation.
Approval is required when the blast radius becomes large enough that dispatcher review alone is not sufficient.
Exact thresholds are still provisional and should be tuned with live operations data.

## Deduplication
Each issue-specific loop must be deduped by an activation key equivalent to:
`(workflow_run_id, flag_id, task_kind, generation)`
