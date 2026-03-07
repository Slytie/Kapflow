# Availability Request v1 - operating model

## Why this workflow exists
This pack converts a raw time-off request into approved availability truth.

## Current intake reality
The current MVP respects the existing Google Form workflow instead of replacing it.
The visible form asks for:
- employee name,
- weekdays not available,
- dates,
- reason,
- typed signature.

The form also contains policy hints such as:
- lead time improves approval chances,
- weekend requests have lower approval odds,
- peak blackout windows may exist.

## Core rule
Submission is **not** equivalent to approved unavailability.

Formally, if `q` is the raw request and `a` is the approved availability state, then:
- `q` may inform a future decision,
- but `a` changes only after the decision boundary.

## Decision model
Minimum decision statuses:
- `pending`
- `approved`
- `denied`
- `partially_approved`
- `needs_information`

Partial approval must explicitly separate approved dates from denied dates.

## Downstream effects
The official output is an updated approved-availability plan.
That update may trigger:
- future weekly planning rebuilds, or
- a live dispatch review when an already-published day is affected.
