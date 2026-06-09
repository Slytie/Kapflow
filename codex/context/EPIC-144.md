# EPIC-144 Context Pack - CAPEX workpages and projections

Purpose:
- Rehydrate the CAPEX v6 task tranche for `EPIC-144` without opening the full master package.
- Keep future work inside the existing one-truth runtime, approval, artifact, pointer, and event model.

## Imported source rows
ART-007, WP-001, WP-002, WP-003, WP-004, WP-005, WP-006, WP-007, ... (32 tasks total)

## Closed foundation rows
- `TASK-0567` is closed as of 2026-06-08: internal `capex_workpage_projection_snapshots` / `capex_workpage_projection_rows`, signed projection cursors, typed command envelopes, and stale-command guards exist for future CAPEX workpage mutation safety.
- This does not add public CAPEX workpage APIs, frontend routes, or CAPEX workpage activation.

## Load first
- `docs/planning/epics/EPIC-144.md`
- `docs/planning/CAPEX_MASTER_V6_INTAKE.md`
- `docs/planning/CAPEX_V6_CONVERSION_MAP.csv`
- `docs/architecture/invariants.md`
- `docs/status/CURRENT_FOCUS.md`

## Non-negotiable invariants
- One truth system: official claims come only from immutable objects, append-only events, and audited pointers.
- Tenant, domain, and future CAPEX project boundaries must not be crossed in reads, writes, exports, projections, or generated material.
- Raw K12/K3/blind corpus files stay off-repo; only sanitized fixtures, manifests, hashes, and aggregate evidence may be committed.
- Generated artifacts, Workflow Lab reports, and AI output are not source authority.
- Production/lab activation is release-mediated and remains blocked until the relevant gates close or receive explicit waivers.

## Preferred implementation posture
- Start with the source task's required tests or evidence.
- Update repo-native authoritative source before downstream generated artifacts.
- Keep implementation PRs small enough to review against the source row and acceptance gate.
- Preserve logistics weekly/live current focus unless a CAPEX task explicitly changes shared semantics.

## Stop line
- Do not import raw project corpus content.
- Do not activate CAPEX runtime/product behavior merely because a planning task exists.
