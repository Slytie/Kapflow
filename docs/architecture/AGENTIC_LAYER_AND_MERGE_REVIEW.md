# Agentic layer and merge review

This document is kept as narrative rationale.

## Status
The authoritative merger rules are now defined in:
- `AUTHORITY_MODEL.md`
- `EXECUTION_OVERLAY_MODEL.md`
- `DERIVATION_AND_GENERATION_POLICY.md`

Use this file for historical first-principles reasoning and context, not as the canonical rule source.

## What remains useful from the original review
- the repo already had a strong formal business substrate
- the CompanyOS packet added valuable method, compiler, and projection ideas
- the main merger hazard was dual authorship of workflow semantics
- the clean resolution is:
  - one authored repo-native workflow-definition surface
  - one repo-native execution overlay
  - generated CompanyOS IR and generated runbook packs
  - one event system, one approval system, one run system

## Historical takeaway
The earlier "two planes" framing was directionally useful but not strict enough. The repo now expresses the stronger version directly: one truth system with a single authority chain.
