---
pattern_id: PATTERN-007
title: "Kanboard \u2014 Lightweight ops-console patterns: boards, plugins, and task-centric\
  \ UX"
source_notes: docs/patterns/sources/converted/Kanboard_Lightweight_UI_Plugin_Patterns_for_Orchestration_Ops_Console.md
tags:
- ui
- ops-console
- boards
- plugins
- task-tracking
- notifications
applies_to_epics:
- EPIC-050
- EPIC-080
use_when:
- Designing the **human task queue UX** (high-density lists/boards + quick filters).
- Designing **extensibility** for ops UI (plugins/modules).
last_updated: '2026-02-28'
status: candidate
---

# PATTERN-007 — Kanboard — Lightweight ops-console patterns: boards, plugins, and task-centric UX

**Why this matters for our Stage 4 MVP**

- This is a *reference pattern*, not a dependency: we borrow semantics and guardrails, not code.
- Read this card first; only open the full source notes if the task is directly touching the affected subsystem.

## When to consult this

- Designing the **human task queue UX** (high-density lists/boards + quick filters).
- Designing **extensibility** for ops UI (plugins/modules).

## Key patterns to borrow

- **Formatter pipeline as a lightweight “view-model layer”**
- Board data is assembled and shaped via dedicated formatter classes (not in templates).
- *Evidence:** `app/Formatter/BoardFormatter.php::format()`; `app/Formatter/BoardSwimlaneFormatter.php::format()`; `app/Formatter/BoardColumnFormatter.php::format()`.
- **Project-level modification timestamp + 304 polling**
- Cheap sync strategy: `check()` returns 304 unless `projects.last_modified` advanced.
- *Evidence:** `app/Controller/BoardAjaxController.php::check()`; `app/Model/ProjectModel.php::isModifiedSince()`.
- **Ensure last_modified is correct via event subscribers**
- Subscriber updates project modification date on task events.
- *Evidence:** `app/Subscriber/ProjectModificationDateSubscriber.php::getSubscribedEvents()`; `app/Subscriber/ProjectModificationDateSubscriber.php::execute()`.
- **Data-* attribute “endpoint wiring” for JS**
- Board container encodes URLs + refresh interval in HTML attributes.
- *Evidence:** `app/Template/board/table_container.php` (`data-check-url`, `data-reload-url`, `data-save-url`, etc.).
- **Card micro-signals via compact icon footer**
- Days-in-column, blockers (links), subtasks progress, attachments, etc.

## Pitfalls / what *not* to copy

_No explicit anti-pattern list extracted; treat source notes as informational only._

## How we map this into our platform (guidance)

- **Artifact-first**: always bind actions to `(dataset_key, partition_key, artifact_version_id)` and record promotion events.
- **Audit timeline**: every state change must emit a strongly-linked TimelineEvent (authoritative, transactional).
- **Tenant + domain isolation**: any queue/topic/index/prefix must be tenant-scoped; add negative tests.
- **Automation safety**: tool execution must be policy/approval gated and sandboxed.

## Source notes

- Full extraction: `docs/patterns/sources/converted/Kanboard_Lightweight_UI_Plugin_Patterns_for_Orchestration_Ops_Console.md`
