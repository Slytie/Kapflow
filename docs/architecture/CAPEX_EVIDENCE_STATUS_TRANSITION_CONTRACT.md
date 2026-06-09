# CAPEX Evidence Status Transition Contract

## Status
Accepted planning contract for `TASK-0651` and `SME-RP-G004`.

## Purpose
Evidence presence is not evidence sufficiency. CAPEX evidence-driven modules,
workpages, closure checks, and executive views need a shared evidence-link
status vocabulary before they can claim SME-RP readiness.

This is a planning contract only. It does not add evidence-binding runtime,
search or retrieval indexes, schemas, migrations, APIs, routes, frontend
behavior, raw corpus import, or CAPEX product activation.

## Evidence-link statuses
The evidence-link status vocabulary is exactly:

1. `proposed`
2. `under_review`
3. `valid`
4. `partly_valid`
5. `contradictory`
6. `obsolete`
7. `invalid`
8. `insufficient`
9. `accepted_with_residual_risk`

## Closure eligibility
- `valid` may satisfy closure.
- `accepted_with_residual_risk` may satisfy closure only with explicit
  residual-risk acceptance or waiver.
- `proposed`, `under_review`, `partly_valid`, `contradictory`, `obsolete`,
  `invalid`, and `insufficient` cannot satisfy closure by themselves.

Raw file presence, extracted text, AI output, workpage state, external status,
local folder state, PR/PO/invoice state, handover notes, supplier statements,
and generated artifacts are not reviewed evidence by themselves.

## Allowed transitions
Allowed status transitions are exactly:

| From | Allowed to |
|---|---|
| `proposed` | `under_review`, `invalid`, `obsolete` |
| `under_review` | `valid`, `partly_valid`, `contradictory`, `obsolete`, `invalid`, `insufficient` |
| `valid` | `under_review`, `contradictory`, `obsolete` |
| `partly_valid` | `under_review`, `accepted_with_residual_risk`, `contradictory`, `obsolete`, `invalid`, `insufficient` |
| `accepted_with_residual_risk` | `under_review`, `contradictory`, `obsolete` |
| `contradictory` | `under_review`, `obsolete` |
| `invalid` | `under_review`, `obsolete` |
| `insufficient` | `under_review`, `invalid`, `obsolete` |
| `obsolete` | `under_review` only when a new source occurrence or revision explicitly reopens the evidence link |

## Source and closure binding
Evidence status must bind to meaningful SourceRefs and closure basis. Empty
`source_refs`, unresolved source occurrences, quarantined/redacted/superseded
source occurrences, and stale closure basis refs cannot satisfy official
claims.

## Activation rule
Evidence-driven workflow, workpage, closure, projection, snapshot/export, and
external observation surfaces must not claim SME-RP readiness until they
preserve this vocabulary and transition contract or record an explicit waiver.
