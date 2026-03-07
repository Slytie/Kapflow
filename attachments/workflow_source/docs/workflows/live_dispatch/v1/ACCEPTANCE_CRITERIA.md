# ACCEPTANCE_CRITERIA.md - Live Dispatch v1

## Happy path
- [ ] A per-day base seed plus one or more route / staffing events activates a `ServiceDateID` run.
- [ ] The workflow creates issue-scoped triage work keyed by `(workflow_run_id, flag_id, task_kind, generation)` or equivalent.
- [ ] Candidate generation filters out WHC-ineligible options before ranking.
- [ ] Small changes can complete after review confirmation; major changes require approval.
- [ ] Official operational truth changes through ordered delta promotion without mutating the base seed.

## Critical business cases
- [ ] Daily route updates, ERO notices, manual station requests, sick calls, and no-shows are normalized into one event family.
- [ ] Candidate ranking favors on-call drivers, people with fewer shifts, and drivers who recently lost work due to cancellation.
- [ ] Actual hours from recent dispatch actuals can block otherwise-available candidates.

## Negative cases
- [ ] Duplicate wakeups do not duplicate issue tasks.
- [ ] Multiple route-update emails for the same service date are ordered and superseded by received time and source id.
- [ ] If no compliant candidate exists, the workflow raises an explicit `no_candidate` / `whc_block` style flag instead of inventing a hidden override.
- [ ] Major-change approval is visible and linked to the promoted delta.

## Domain constraints
- [ ] The base schedule seed is immutable.
- [ ] Hard constraints are deterministic code; optional LLM help is limited to short rationale or packet drafting.
- [ ] Outbound message sending may remain manual initially, but change-notice artifacts must still be generated.
