# MERGER_BACKLOG.md

These items are intentionally deferred, but the nuance matters and should not be lost.

## 1) Generated CompanyOS IR pipeline
**Why deferred:** the source surface is now defined, but the actual generator does not exist yet.  
**What to preserve:** generated IR must not become a rival authored workflow-definition system.  
**Prerequisites:** stable schemas for decision catalog and execution profile; source-hash lineage rules.

## 2) Pinned `ExecutionSpec` compiler
**Why deferred:** runtime services are not implemented yet.  
**What to preserve:** the compiler may refine source, not reinterpret or broaden it.  
**Prerequisites:** workflow/task/execution-session runtime model, policy profile model, generator contract.

## 3) ProcessPatch lifecycle
**Why deferred:** capability-diff tooling and approval governance do not yet exist.  
**What to preserve:** method changes must never self-promote; capability expansion requires explicit review.

## 4) WorkGraph
**Why deferred:** useful, but easy to turn into a shadow truth layer or privacy leak.  
**What to preserve:** WorkGraph remains derived and rebuildable; scope law still applies.

## 5) Projection DSL / generalized renderer system
**Why deferred:** approval-critical projections need coherence and safe renderers first.  
**What to preserve:** approval packets must remain server-owned and coherence-checked.

## 6) General study/program workflows
**Why deferred:** Stage 4 only needs business workflows plus bounded exception handling.  
**What to preserve:** the mathematical note's multi-level idea remains valid, but should not overcomplicate the MVP.

## 7) Capability diff tooling
**Why deferred:** no spec store or ProcessPatch runtime yet.  
**What to preserve:** future method changes need machine-checked diffing of tool surface, side effects, approvals, and budgets.

## 8) Spike-runtime table translation
**Why deferred:** the stage3 spike repo is an evidence harness, not the final runtime schema.  
**What to preserve:** `agent_runs` and `human_decision_requests` should not be copied literally into the main platform as peer truth systems. They need translation into the canonical run / approval model.

## 9) Cross-tenant learning / generalized operator improvement
**Why deferred:** powerful but high-risk.  
**What to preserve:** default-deny stance; no accidental cross-tenant data mixing in learned methods or generated templates.

## 10) Rich operator catalog
**Why deferred:** useful long term, but Stage 4 only needs small execution algebra plus workflow-specific guidance.  
**What to preserve:** operator vocabulary should emerge from repeated evidence, not speculative taxonomy inflation.
