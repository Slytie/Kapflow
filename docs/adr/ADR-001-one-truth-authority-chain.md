# ADR-001 - One truth authority chain

## Status
Accepted

## Decision
The repo will use one truth system:
- immutable objects
- append-only events
- audited pointers / registries

Business contract packs and execution-overlay files are the only hand-authored workflow-definition surfaces in Stage 4.
Generated runbooks, generated CompanyOS IR, projections, and transcripts are downstream and non-authoritative.

## Why
The merger with CompanyOS introduced valuable method and compiler ideas but also a high risk of dual workflow-definition systems.

## Consequences
- CompanyOS IR becomes a lowering target
- runbook packs become generated derivatives
- approvals, runs, and events remain single canonical systems
