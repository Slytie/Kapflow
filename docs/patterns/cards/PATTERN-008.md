---
pattern_id: PATTERN-008
title: "Taiga Back \u2014 Backend patterns: permissions, timelines, notifications,\
  \ async on-commit"
source_notes: docs/patterns/sources/converted/Taiga_Back_Backend_Architecture_Pattern_Extraction.md
tags:
- backend
- permissions
- timeline
- notifications
- async
- webhooks
applies_to_epics:
- EPIC-010
- EPIC-020
- EPIC-050
use_when:
- Designing **permission-aware APIs** and audit/timeline backends.
- Designing **timeline feeds** (events, comments, attachments) and notifications.
- Designing safe **on-commit** async triggers (outbox-like behavior).
last_updated: '2026-02-28'
status: candidate
---

# PATTERN-008 — Taiga Back — Backend patterns: permissions, timelines, notifications, async on-commit

**Why this matters for our Stage 4 MVP**

- This is a *reference pattern*, not a dependency: we borrow semantics and guardrails, not code.
- Read this card first; only open the full source notes if the task is directly touching the affected subsystem.

## When to consult this

- Designing **permission-aware APIs** and audit/timeline backends.
- Designing **timeline feeds** (events, comments, attachments) and notifications.
- Designing safe **on-commit** async triggers (outbox-like behavior).

## Key patterns to borrow

- **Single audit log → derived streams**
- *Evidence:** `taiga/projects/history/models.py:HistoryEntry`; `taiga/timeline/apps.py:TimelineAppConfig.ready`; `taiga/webhooks/apps.py:connect_webhooks_signals`; `taiga/projects/notifications/services.py:send_notifications`.
- **String-keyed identity for audit entries**
- *Evidence:** `taiga/projects/history/models.py:HistoryEntry.key`; `taiga/projects/history/services.py:make_key_from_model_object`.
- **Snapshots + diffs with bounded replay**
- *Evidence:** `taiga/projects/history/services.py:take_snapshot`.
- **UI-ready `values` / `values_diff`**
- *Evidence:** `taiga/projects/history/services.py:make_diff_values`; `taiga/projects/history/models.py:HistoryEntry.values_diff`.
- **Comment integrated into history/timeline**
- *Evidence:** `taiga/projects/history/services.py:take_snapshot`; `taiga/timeline/signals.py:on_new_history_entry`.
- **Per-action permission mapping + composition**
- *Evidence:** `taiga/base/api/permissions.py:TaigaResourcePermission` and `PermissionComponent` boolean ops.
- **Comment-vs-modify permission split**
- *Evidence:** `taiga/permissions/permissions.py:CommentAndOrUpdatePerm`.

## Pitfalls / what *not* to copy

- **Side-effecting GET via headers**
- *Evidence:** `taiga/projects/tasks/api.py:TaskViewSet.get_queryset` writes when `"set-orders"` header set; header allowed in `taiga/base/middleware/cors.py:ACCESS_CONTROL_ALLOW_HEADERS`.
- **`.extra()` and raw SQL proliferation**
- *Evidence:** `taiga/projects/notifications/utils.py:attach_watchers_to_queryset` uses `.extra`; facet SQL in `taiga/projects/tasks/services.py:_get_tasks_statuses`.
- **Disabling global Django signals during operations**
- *Evidence:** `taiga/projects/services/promote.py:_import_comments` modifies `signals.pre_save.receivers` and restores later.
- **Mutating history rows (comment edits)**
- *Evidence:** `taiga/projects/history/api.py:edit_comment`; edit metadata in `taiga/projects/history/models.py:HistoryEntry`.
- **Read property that writes DB (`values_diff` cache)**
- *Evidence:** `taiga/projects/history/models.py:HistoryEntry.values_diff` updates `values_diff_cache` with `.update(...)`.
- --

## How we map this into our platform (guidance)

- **Artifact-first**: always bind actions to `(dataset_key, partition_key, artifact_version_id)` and record promotion events.
- **Audit timeline**: every state change must emit a strongly-linked TimelineEvent (authoritative, transactional).
- **Tenant + domain isolation**: any queue/topic/index/prefix must be tenant-scoped; add negative tests.
- **Automation safety**: tool execution must be policy/approval gated and sandboxed.

## Source notes

- Full extraction: `docs/patterns/sources/converted/Taiga_Back_Backend_Architecture_Pattern_Extraction.md`
