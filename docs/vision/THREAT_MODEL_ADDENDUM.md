# Threat model addendum for the merger

This is the condensed threat-model guidance carried forward from the CompanyOS packet.

## The key merger threats

### 1) Second truth system
If workflow semantics are hand-authored in both repo workflow packs and CompanyOS spec files, the system will drift into dual constitutions.

Control:
- one authored workflow-definition surface in the repo
- CompanyOS IR generated from repo-native source
- generated artifacts never define official business truth

### 2) Summary drift
If projections, dashboards, or approval packets omit critical warnings, approvers may approve the wrong thing.

Control:
- server-owned renderers for approval-critical projections
- canonical field lists
- coherence checks against the authoritative substrate
- drill-down to evidence

### 3) Out-of-plan execution
If an agent can call tools outside the pinned method envelope, capabilities silently expand during execution.

Control:
- execution profile -> compiled ExecutionSpec
- membership checks
- deny-by-default for out-of-plan actions unless explicitly approved

### 4) Process or capability expansion without governance
If future method-change artifacts can self-promote, the system becomes unsafe.

Control:
- method-change approvals are a separate approval kind
- capability expansion requires explicit review
- ProcessPatch remains deferred until governance and diff tooling exist

### 5) Cross-tenant leakage through derived stores
Derived graphs, indices, or projections can become shadow leak surfaces.

Control:
- same scope law as the substrate
- derived stores rebuildable from source
- isolation checks for caches and indices

### 6) Runtime semantic drift
If engine updates reinterpret historical specs or runbooks, pinned runs stop meaning what they originally meant.

Control:
- stable-core rule
- pinned compiled execution artifacts
- renderer versioning for approval-critical projections

## Practical message for future development
The threat model is not mainly about malicious users. It is also about architectural sloppiness:
- duplicate authoring surfaces
- stale templates
- summary-first governance
- untracked runtime interpretation changes

Those are the merger hazards to keep front-of-mind.
