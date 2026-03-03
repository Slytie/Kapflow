# ADR-002 - Generated agentic derivatives

## Status
Accepted

## Decision
External runbook packs, tool registry matrices, approval logs, and CompanyOS spec IR must be treated as generated derivatives of repo-native source.

## Why
These artifacts are useful but prone to drift. Treating them as generated preserves utility without creating a rival truth system.

## Consequences
- source-hash lineage is required
- manual edits to generated artifacts are not the primary repair path
- CI should eventually validate freshness and refinement
