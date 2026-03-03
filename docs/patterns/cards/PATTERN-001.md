---
pattern_id: PATTERN-001
title: "Netflix Conductor \u2014 Decider queue + sweeper reconciliation loops for\
  \ durable orchestration"
source_notes: docs/patterns/sources/converted/Netflix_Conductor_Architecture_Pattern_Extraction.md
tags:
- durable-orchestration
- queueing
- sweeper
- reconciliation
- idempotency
- worker-polling
applies_to_epics:
- EPIC-020
- EPIC-040
- EPIC-050
- EPIC-090
use_when:
- "Designing the orchestrator\u2019s **decider loop** (evaluate \u2192 schedule \u2192\
  \ persist \u2192 requeue)."
- Implementing **reconciliation / sweeper** logic for timeouts and stuck runs.
- Defining queue semantics like **unack timeout / postpone / retry** for long-running
  work.
last_updated: '2026-02-28'
status: candidate
---

# PATTERN-001 — Netflix Conductor — Decider queue + sweeper reconciliation loops for durable orchestration

**Why this matters for our Stage 4 MVP**

- This is a *reference pattern*, not a dependency: we borrow semantics and guardrails, not code.
- Read this card first; only open the full source notes if the task is directly touching the affected subsystem.

## When to consult this

- Designing the orchestrator’s **decider loop** (evaluate → schedule → persist → requeue).
- Implementing **reconciliation / sweeper** logic for timeouts and stuck runs.
- Defining queue semantics like **unack timeout / postpone / retry** for long-running work.

## Key patterns to borrow

- Separate decision from effects
- Evidence: `core/.../DeciderService.java#decide` versus `core/.../WorkflowExecutor.java#decide`.
- Per-run execution lock
- Evidence: `WorkflowExecutor.decideWithLock` (`core/.../WorkflowExecutor.java`); `ExecutionLockService` (`core/.../ExecutionLockService.java`); `RedisLock` (`redis-lock/.../RedisLock.java`).
- Idempotent task identity refName plus retryCount
- Evidence: `ExecutionDAO.createTasks` Javadoc (`core/.../ExecutionDAO.java`); `WorkflowExecutor.dedupAndAddTasks` (`core/.../WorkflowExecutor.java`); `RedisExecutionDAO.createTasks` (`redis-persistence/.../RedisExecutionDAO.java`).
- Queue abstraction with explicit ack and unack semantics
- Evidence: `QueueDAO` (`core/.../QueueDAO.java`).
- Repair loop for DB and queue mismatches
- Evidence: `WorkflowExecutor.scheduleTask` try catch and comment (`core/.../WorkflowExecutor.java`); `WorkflowRepairService.verifyAndRepairTask` (`core/.../WorkflowRepairService.java`).
- System tasks run on internal worker plane
- Evidence: `SystemTaskWorker` (`core/.../SystemTaskWorker.java`); `AsyncSystemTaskExecutor` (`core/.../AsyncSystemTaskExecutor.java`).
- Async-complete system task abstraction
- Evidence: `WorkflowSystemTask.isAsyncComplete` (`core/.../WorkflowSystemTask.java`).

## Pitfalls / what *not* to copy

- Latest workflow definition when version is omitted
- Evidence: `MetadataMapperService.lookupForWorkflowDefinition` uses `lookupLatestWorkflowDefinition` when version is null (`core/.../MetadataMapperService.java`).
- Mismatch: artifact immutability requires pinning.
- Mutation-based state as primary source of truth
- Evidence: `WorkflowExecutor.updateTask` mutates task status and output data and writes back (`core/.../WorkflowExecutor.java`).
- Mismatch: audit-first event log requires append-only transitions.
- No native stale detection
- Evidence: no artifact pointer or version fields on `WorkflowModel` (`core/.../WorkflowModel.java`).
- No explicit spawn budgets or cycle prevention in decider
- Evidence: `WorkflowExecutor.decide` and `DeciderService.decide` do not contain such checks (`core/.../WorkflowExecutor.java`, `core/.../DeciderService.java`).
- --

## How we map this into our platform (guidance)

- **Artifact-first**: always bind actions to `(dataset_key, partition_key, artifact_version_id)` and record promotion events.
- **Audit timeline**: every state change must emit a strongly-linked TimelineEvent (authoritative, transactional).
- **Tenant + domain isolation**: any queue/topic/index/prefix must be tenant-scoped; add negative tests.
- **Automation safety**: tool execution must be policy/approval gated and sandboxed.

## Source notes

- Full extraction: `docs/patterns/sources/converted/Netflix_Conductor_Architecture_Pattern_Extraction.md`
