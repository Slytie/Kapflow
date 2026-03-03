# Taiga Back — Backend Architecture & Pattern Extraction for Human-First Orchestration UI/API

> Scope note: This is a **preliminary architecture extraction** from the provided `taiga-back` checkout, focusing on patterns relevant to enterprise task/case management (permissions, audit/history, timelines, notifications, bulk/queue UX). Every factual claim is backed by **file-path + identifier evidence**.

---

## 1) Repo/Service Overview

### Framework stack

- **Python + Django (monolith, multi-app layout)** with a **custom DRF-inspired API layer** under `taiga.base.api` (not `djangorestframework` as a dependency).  
  **Evidence:** `requirements.txt: django==3.2.25` + custom API framework in `taiga/base/api/views.py:APIView`, `taiga/base/api/viewsets.py:ViewSetMixin`, `taiga/base/api/serializers.py:ModelSerializer`.

- **PostgreSQL as primary DB** (explicit Django backend config + Postgres-specific features used).  
  **Evidence:** `settings/common.py:DATABASES['default']['ENGINE']="django.db.backends.postgresql"`; PostgreSQL NOTIFY in `taiga/events/backends/postgresql.py:EventsPushBackend.emit_event`.

- **Celery for async tasks**, with `CELERY_ENABLED` gating whether signals enqueue tasks on commit or run inline.  
  **Evidence:** `taiga/celery.py:app` + `settings/common.py:CELERY_ENABLED` + on-commit scheduling `taiga/timeline/signals.py:_push_to_timelines` and `taiga/webhooks/signal_handlers.py:create_webhook_on_history_post_save`.

- **JWT + session auth + “Application token” auth** (integrations).  
  **Evidence:** `settings/common.py:REST_FRAMEWORK['DEFAULT_AUTHENTICATION_CLASSES']` lists `taiga.auth.authentication.JWTAuthentication`, `taiga.base.api.authentication.SessionAuthentication`, `taiga.external_apps.auth_backends.Token`; JWT logic in `taiga/auth/authentication.py:JWTAuthentication`.

- **Pluggable event push backend** (Postgres or RabbitMQ).  
  **Evidence:** `settings/common.py:EVENTS_PUSH_BACKEND`; backends in `taiga/events/backends/postgresql.py` and `taiga/events/backends/rabbitmq.py`.

---

### Module layout (macro architecture)

- **Entry points & API routing**
  - Root URL config is `taiga.urls`, mounting API under `/api/v1/` and wiring Swagger.  
    **Evidence:** `settings/common.py:ROOT_URLCONF="taiga.urls"`; `taiga/urls.py:urlpatterns` includes `path("api/v1/", include(router.urls))`.
  - API surface is centrally registered in `taiga/routers.py` via a `DefaultRouter` mapping to per-domain `ViewSet`s.  
    **Evidence:** `taiga/routers.py:router = DefaultRouter(trailing_slash=False)` and many `router.register(...)` entries.

- **Domain modules follow a consistent pattern**: `models.py`, `api.py` (ViewSet), `serializers.py`, `validators.py`, `permissions.py`, `services.py`, and sometimes `signals.py`.  
  **Evidence:** Example: `taiga/projects/tasks/{models.py,api.py,serializers.py,validators.py,permissions.py,services.py,signals.py}`.

- **Cross-cutting “product features” implemented as apps**:
  - History (audit/event log): `taiga.projects.history.*`  
    **Evidence:** `taiga/projects/history/models.py:HistoryEntry`, `taiga/projects/history/services.py:take_snapshot`.
  - Timeline (activity feed): `taiga.timeline.*`  
    **Evidence:** `taiga/timeline/models.py:Timeline`, `taiga/timeline/service.py:push_to_timelines`.
  - Notifications (watchers + web/email): `taiga.projects.notifications.*`  
    **Evidence:** `taiga/projects/notifications/models.py:Watched, WebNotification, HistoryChangeNotification`, `taiga/projects/notifications/services.py:send_notifications`.
  - Webhooks: `taiga.webhooks.*`  
    **Evidence:** `taiga/webhooks/models.py:Webhook, WebhookLog`, `taiga/webhooks/tasks.py:create_webhook`.

---

### Main request lifecycle (routing → auth → domain → persistence)

Typical CRUD update on a work item like a Task:

1) **Routing**
   - `/api/v1/tasks/:id` resolves to `TaskViewSet`.  
     **Evidence:** `taiga/routers.py:router.register(r"tasks", tasks_api.TaskViewSet, ...)`.

2) **View dispatch**
   - ViewSet resolves HTTP verb → action (`update`, `partial_update`, etc.).  
     **Evidence:** `taiga/base/api/viewsets.py:ViewSetMixin._allowed_methods`.

3) **Authentication**
   - `APIView.initial()` runs `perform_authentication()` using configured classes.  
     **Evidence:** `taiga/base/api/views.py:APIView.initial` and `APIView.perform_authentication`; auth list in `settings/common.py:REST_FRAMEWORK['DEFAULT_AUTHENTICATION_CLASSES']`.

4) **Authorization**
   - Permissions evaluated per action via `check_permissions(request, action, obj)` and `TaigaResourcePermission`.  
     **Evidence:** `taiga/base/api/views.py:APIView.check_permissions`; `taiga/base/api/permissions.py:TaigaResourcePermission`.

5) **Validation**
   - Create/update paths use validator/serializer objects.  
     **Evidence:** `taiga/base/api/mixins.py:CreateModelMixin.create`, `UpdateModelMixin.update`; validators e.g. `taiga/projects/tasks/validators.py:TaskValidator`.

6) **Domain preconditions + concurrency**
   - Blocked/archived gating via mixins; project-consistency checks in `pre_conditions_on_save`.  
     **Evidence:** `taiga/base/api/mixins.py:BlockedByProjectMixin, ArchivedByProjectMixin`; checks in `taiga/projects/tasks/api.py:TaskViewSet.pre_conditions_on_save` and `taiga/projects/userstories/api.py:UserStoryViewSet.pre_conditions_on_save`.
   - Optimistic concurrency via `version` with field-level conflict detection using history.  
     **Evidence:** `taiga/projects/occ/mixins.py:OCCResourceMixin._validate_and_update_version`; `taiga/projects/history/services.py:get_modified_fields`.

7) **Persistence**
   - Serializer save calls `obj.save()` and persists M2M.  
     **Evidence:** `taiga/base/api/serializers.py:ModelSerializer.save_object`.

8) **Audit/history + derived side effects**
   - History snapshots via `HistoryResourceMixin` into `HistoryEntry`.  
     **Evidence:** `taiga/projects/history/mixins.py:HistoryResourceMixin.post_save → take_snapshot`; snapshot logic `taiga/projects/history/services.py:take_snapshot`.
   - Timeline + webhooks triggered off HistoryEntry post-save.  
     **Evidence:** `taiga/timeline/apps.py:TimelineAppConfig.ready`; `taiga/timeline/signals.py:on_new_history_entry`; `taiga/webhooks/apps.py:connect_webhooks_signals`; `taiga/webhooks/signal_handlers.py:on_new_history_entry`.

---

## 2) Formal Model: Work Item State Machines & Event Logs

### Generic formalization

Let a **work item** be \( w \in \mathcal{W} \) with:

- State \( \sigma \in \Sigma \) (finite).
- Commands \( c \in \mathcal{C} \).
- Transition function  
  \[
  \tau: \Sigma \times \mathcal{C} \rightarrow \Sigma
  \]
- Event log \( \mathcal{E}(w) = \langle e_0, e_1, \dots, e_n \rangle \) where each event includes actor/time/type/diff/comment/snapshot.

This supports:
- Timeline projection \( \Pi(\mathcal{E}) \) for UX
- Notification/webhook emission as derived streams

---

### Taiga’s equivalents

#### Work item \(w\)

- Work items include **UserStory**, **Task**, **Issue**, **Epic**, **WikiPage**.  
  **Evidence:** `taiga/projects/userstories/models.py:UserStory`; `taiga/projects/tasks/models.py:Task`; `taiga/projects/issues/models.py:Issue`; `taiga/projects/epics/models.py:Epic`; `taiga/projects/wiki/models.py:WikiPage`.

#### State space \(\Sigma\): project-scoped statuses

- Each work item type has a **project-scoped Status model**.  
  **Evidence:** `taiga/projects/models.py:UserStoryStatus`, `TaskStatus`, `IssueStatus`, `EpicStatus`.

- Work items reference a status FK; effective state is `status_id` (+ derived closedness).  
  **Evidence:** `taiga/projects/userstories/models.py:UserStory.status`; `taiga/projects/tasks/models.py:Task.status`; `taiga/projects/issues/models.py:Issue.status`.

#### Transition function \(\tau\): status assignment + invariants

- Status updates are direct assignment, with invariants such as “status belongs to same project”.  
  **Evidence:** `taiga/projects/userstories/api.py:UserStoryViewSet.pre_conditions_on_save`; `taiga/projects/tasks/api.py:TaskViewSet.pre_conditions_on_save`.

#### Event log \(\mathcal{E}(w)\): HistoryEntry

- `HistoryEntry` stores `key`, `type`, `snapshot`, `diff`, `values`, `comment`, edit metadata.  
  **Evidence:** `taiga/projects/history/models.py:HistoryEntry`; types in `taiga/projects/history/choices.py:HistoryType`.

- Identity uses **string key** `"{typename}:{pk}"` (not FK).  
  **Evidence:** `taiga/projects/history/models.py:HistoryEntry.key`; `taiga/projects/history/services.py:make_key_from_model_object`.

- Snapshots + diffs with periodic full snapshots cap replay length.  
  **Evidence:** `taiga/projects/history/services.py:take_snapshot` (real snapshot decision + `MAX_PARTIAL_DIFFS` logic).

#### Timeline projection \( \Pi(\mathcal{E}) \)

- Timeline entries store `event_type`, `namespace`, `data` JSON.  
  **Evidence:** `taiga/timeline/models.py:Timeline`.

- Populated from HistoryEntry post-save including `values_diff` and `comment`.  
  **Evidence:** `taiga/timeline/signals.py:on_new_history_entry`.

---

## 3) Domain & Data Model

### Identity / tenancy / membership

- User: `taiga.users.models.User`.  
  **Evidence:** `taiga/users/models.py:User`.

- Project: central workspace tenant.  
  **Evidence:** `taiga/projects/models.py:Project`.

- Membership binds user→project with role and `is_admin`.  
  **Evidence:** `taiga/projects/models.py:Membership`.

- Role holds permission string list.  
  **Evidence:** `taiga/users/models.py:Role.permissions`.

- Permission key taxonomy.  
  **Evidence:** `taiga/permissions/choices.py:ANON_PERMISSIONS, MEMBERS_PERMISSIONS, ADMINS_PERMISSIONS`.

### Work items (mutable rows + history)

- UserStory, Task, Issue, Epic, WikiPage store mutable fields and a `status` FK.  
  **Evidence:** `taiga/projects/userstories/models.py:UserStory`; `taiga/projects/tasks/models.py:Task`; `taiga/projects/issues/models.py:Issue`; `taiga/projects/epics/models.py:Epic`; `taiga/projects/wiki/models.py:WikiPage`.

### Attachments

- Generic attachments via `content_type` + `object_id`; attachment changes snapshot parent.  
  **Evidence:** `taiga/projects/attachments/models.py:Attachment`; `taiga/projects/attachments/api.py:BaseAttachmentViewSet.get_object_for_snapshot`.

### History vs mutability tradeoff

- Work item rows are mutable (update-in-place), audit trail lives in `HistoryEntry`.  
  **Evidence:** update path `taiga/base/api/mixins.py:UpdateModelMixin.update`; log path `taiga/projects/history/services.py:take_snapshot`.

- Freeze implementations define what is captured.  
  **Evidence:** `taiga/projects/history/freeze_impl.py:{userstory_freezer,task_freezer,...}` and registry in `taiga/projects/history/services.py:register_freeze_implementation`.

---

## 4) Permissions & Roles (Critical)

### RBAC evaluation

- Core check `user_has_perm(user, perm, project)` implements privacy + membership + admin semantics.  
  **Evidence:** `taiga/permissions/services.py:user_has_perm`.

- Membership caching per request.  
  **Evidence:** `taiga/users/models.py:User.cached_membership_for_project`.

### Enforcement in endpoints

- Per-action permission mapping via `TaigaResourcePermission`.  
  **Evidence:** `taiga/base/api/permissions.py:TaigaResourcePermission`.

- Permission composition operators.  
  **Evidence:** `taiga/base/api/permissions.py:PermissionComponent.__or__/__and__/__invert__`.

- Split comment vs modify permissions.  
  **Evidence:** `taiga/permissions/permissions.py:CommentAndOrUpdatePerm`; example usage `taiga/projects/tasks/permissions.py:TaskPermission.update_perms`.

- Query-level gating for list endpoints.  
  **Evidence:** `taiga/base/filters.py:PermissionBasedFilterBackend`.

### Reuse patterns for our platform

- Command endpoints for promotions / operator actions.  
  **Evidence:** `taiga/projects/mixins/promote.py:PromoteToUserStoryMixin.promote_to_user_story` calls `self.check_permissions(..., 'promote_to_us', project)` and persists history.

- Caution: promote permissions differ between work items; treat as “don’t copy blindly”.  
  **Evidence:** `taiga/projects/issues/permissions.py:IssuePermission.promote_to_us_perms = ... HasProjectPerm('add_us')`; `taiga/projects/tasks/permissions.py:TaskPermission.promote_to_us_perms = ... HasProjectPerm('view_tasks')`.

---

## 5) API Design Patterns

### Routing and custom actions

- Custom actions via `@detail_route` / `@list_route`.  
  **Evidence:** `taiga/base/decorators.py:detail_route, list_route`.

- DRF-like custom router.  
  **Evidence:** `taiga/base/routers.py:DefaultRouter`.

### Pagination and UX headers

- Pagination headers include `X-Pagination-Count`; pagination can be disabled by header.  
  **Evidence:** `taiga/base/api/pagination.py:PaginationMixin`.

- CORS exposes pagination and “Taiga-Info” headers.  
  **Evidence:** `taiga/base/middleware/cors.py:ACCESS_CONTROL_EXPOSE_HEADERS`.

- UI “info headers” for backlog counts, etc.  
  **Evidence:** `taiga/projects/userstories/api.py:UserStoryViewSet._add_taiga_info_headers`.

### Filtering / facets and bulk actions

- Filter facets produced server-side (statuses/users/tags) via services + SQL.  
  **Evidence:** `taiga/projects/tasks/api.py:TaskViewSet.filters_data`; `taiga/projects/tasks/services.py:get_tasks_filters_data` and `_get_tasks_statuses`.

- Bulk endpoints exist (create, reorder, milestone updates).  
  **Evidence:** `taiga/projects/tasks/api.py:{bulk_create,bulk_update_order,bulk_update_milestone}`.

### Concurrency control (OCC)

- Version-based OCC, conflict detection using history modified fields.  
  **Evidence:** `taiga/projects/occ/mixins.py:OCCResourceMixin._validate_and_update_version`; `taiga/projects/occ/mixins.py:OCCModelMixin.version`; `taiga/projects/history/services.py:get_modified_fields`.

### Footguns to avoid

- Side-effecting GET via headers.  
  **Evidence:** `taiga/projects/tasks/api.py:TaskViewSet.get_queryset` checks `"set-orders"` header and triggers writes; header allowed in `taiga/base/middleware/cors.py:ACCESS_CONTROL_ALLOW_HEADERS`.

---

## 6) Events/Notifications/Webhooks

### Realtime events publishing

- Pluggable events backend; emits via `emit_event_for_model`.  
  **Evidence:** `taiga/events/events.py:emit_event_for_model`; config `settings/common.py:EVENTS_PUSH_BACKEND`.

- Postgres NOTIFY backend publishes to channel `"events"`.  
  **Evidence:** `taiga/events/backends/postgresql.py:EventsPushBackend.emit_event`.

- RabbitMQ backend alternative.  
  **Evidence:** `taiga/events/backends/rabbitmq.py:EventsPushBackend.emit_event`.

- SessionID middleware sets per-request session ID.  
  **Evidence:** `taiga/events/middleware.py:SessionIDMiddleware`.

### Notifications

- Watchers and notify policies.  
  **Evidence:** `taiga/projects/notifications/models.py:Watched, NotifyPolicy`.

- Aggregated notifications grouped by object key and owner.  
  **Evidence:** `taiga/projects/notifications/services.py:send_notifications` groups into `HistoryChangeNotification`; model in `taiga/projects/notifications/models.py:HistoryChangeNotification`.

- Live notifications via events.  
  **Evidence:** `taiga/projects/notifications/services.py:send_notifications` calls `events.emit_live_notification_for_model`; implemented in `taiga/events/events.py:emit_live_notification_for_model`.

### Webhooks

- Webhooks configured per project; logs retained.  
  **Evidence:** `taiga/webhooks/models.py:Webhook, WebhookLog`.

- Triggered from HistoryEntry on commit; delivered via Celery; signed with HMAC SHA1.  
  **Evidence:** `taiga/webhooks/signal_handlers.py:create_webhook_on_history_post_save` uses `connection.on_commit`; `taiga/webhooks/tasks.py:create_webhook` signs with `sha1` and header `X-Taiga-Webhook-Signature`.

---

## 7) Mapping to Our Platform (Table)

| Need | Taiga implementation | Evidence | Reuse | Adaptation | Risks |
|---|---|---|---|---|---|
| Activity timeline | `Timeline` table derived from HistoryEntry | `taiga/timeline/models.py:Timeline`; `taiga/timeline/signals.py:on_new_history_entry` | Materialized feed items | Project from immutable event log | Hidden snapshots can omit some diffs (`taiga/projects/history/services.py:is_hidden_snapshot`) |
| Comments | `HistoryEntry.comment` and comment-only perms | `taiga/projects/history/services.py:take_snapshot`; `taiga/permissions/permissions.py:CommentAndOrUpdatePerm` | Comments as events | Consider immutable comment events | Taiga supports editing history comments (`taiga/projects/history/api.py:edit_comment`) |
| Attachments | Generic attachments; snapshot parent on change | `taiga/projects/attachments/models.py:Attachment`; `taiga/projects/attachments/api.py:BaseAttachmentViewSet.get_object_for_snapshot` | Generic attachment subsystem | Attach to artifact versions | GenericForeignKey tradeoffs |
| Roles/assignment | Membership+roles; assigned_to/assigned_users | `taiga/projects/models.py:Membership`; `taiga/projects/tasks/models.py:Task.assigned_to` | RBAC + assignment | Queue claim/assignment commands | Ensure every change emits an event |
| Audit log | `HistoryEntry` snapshot/diff/values | `taiga/projects/history/models.py:HistoryEntry`; `taiga/projects/history/services.py:take_snapshot` | Append-mostly log | Make event log authoritative | Taiga may skip entries when diff+comment empty |
| Notifications | Watchers + notify policies + batching | `taiga/projects/notifications/models.py:*`; `taiga/projects/notifications/services.py:send_notifications` | Subscription levels + batching | Subscriptions to runs/artifacts/queues | Consistency rules must be explicit |
| Webhooks | Signed delivery with logs | `taiga/webhooks/tasks.py:create_webhook`; `taiga/webhooks/models.py:WebhookLog` | HMAC + logs | Add idempotency keys | Retry/idempotency design |
| Boards/queues | Timestamp order keys + bulk reorder + headers | `taiga/base/utils/time.py:timestamp_ms`; `taiga/projects/tasks/api.py:bulk_update_order`; `taiga/projects/userstories/api.py:_add_taiga_info_headers` | Order key strategy | Partition grid + queue ordering | Avoid GET side effects (`set-orders`) |

---

## 8) Patterns to Steal vs Avoid

### Patterns to steal

1) **Single audit log → derived streams**  
   **Evidence:** `taiga/projects/history/models.py:HistoryEntry`; `taiga/timeline/apps.py:TimelineAppConfig.ready`; `taiga/webhooks/apps.py:connect_webhooks_signals`; `taiga/projects/notifications/services.py:send_notifications`.

2) **String-keyed identity for audit entries**  
   **Evidence:** `taiga/projects/history/models.py:HistoryEntry.key`; `taiga/projects/history/services.py:make_key_from_model_object`.

3) **Snapshots + diffs with bounded replay**  
   **Evidence:** `taiga/projects/history/services.py:take_snapshot`.

4) **UI-ready `values` / `values_diff`**  
   **Evidence:** `taiga/projects/history/services.py:make_diff_values`; `taiga/projects/history/models.py:HistoryEntry.values_diff`.

5) **Comment integrated into history/timeline**  
   **Evidence:** `taiga/projects/history/services.py:take_snapshot`; `taiga/timeline/signals.py:on_new_history_entry`.

6) **Per-action permission mapping + composition**  
   **Evidence:** `taiga/base/api/permissions.py:TaigaResourcePermission` and `PermissionComponent` boolean ops.

7) **Comment-vs-modify permission split**  
   **Evidence:** `taiga/permissions/permissions.py:CommentAndOrUpdatePerm`.

8) **History-aware OCC with disjoint edit merges**  
   **Evidence:** `taiga/projects/occ/mixins.py:OCCResourceMixin._validate_and_update_version`; `taiga/projects/history/services.py:get_modified_fields`.

9) **on_commit for external side effects**  
   **Evidence:** `taiga/timeline/signals.py:_push_to_timelines`; `taiga/webhooks/signal_handlers.py:create_webhook_on_history_post_save`.

10) **Debounced notification aggregation**  
   **Evidence:** `taiga/projects/notifications/services.py:send_notifications` + `CHANGE_NOTIFICATIONS_MIN_INTERVAL`.

11) **Generic attachments w/ parent snapshotting**  
   **Evidence:** `taiga/projects/attachments/api.py:BaseAttachmentViewSet.get_object_for_snapshot`.

12) **Per-tenant short refs via sequences**  
   **Evidence:** `taiga/projects/references/models.py:make_unique_reference_id`; `taiga/projects/references/sequences.py:next_value`.

### Anti-patterns to avoid/redesign

1) **Side-effecting GET via headers**  
   **Evidence:** `taiga/projects/tasks/api.py:TaskViewSet.get_queryset` writes when `"set-orders"` header set; header allowed in `taiga/base/middleware/cors.py:ACCESS_CONTROL_ALLOW_HEADERS`.

2) **`.extra()` and raw SQL proliferation**  
   **Evidence:** `taiga/projects/notifications/utils.py:attach_watchers_to_queryset` uses `.extra`; facet SQL in `taiga/projects/tasks/services.py:_get_tasks_statuses`.

3) **Disabling global Django signals during operations**  
   **Evidence:** `taiga/projects/services/promote.py:_import_comments` modifies `signals.pre_save.receivers` and restores later.

4) **Mutating history rows (comment edits)**  
   **Evidence:** `taiga/projects/history/api.py:edit_comment`; edit metadata in `taiga/projects/history/models.py:HistoryEntry`.

5) **Read property that writes DB (`values_diff` cache)**  
   **Evidence:** `taiga/projects/history/models.py:HistoryEntry.values_diff` updates `values_diff_cache` with `.update(...)`.

---

## 9) Actionable Output

### 5 ADRs (API/permission/audit design)

**ADR-001: Append-only event log as the system of record**  
**Taiga reference:** `taiga/projects/history/models.py:HistoryEntry`; `taiga/projects/history/services.py:take_snapshot`; fan-out: `taiga/timeline/signals.py:on_new_history_entry`, `taiga/webhooks/signal_handlers.py:on_new_history_entry`.

**ADR-002: RBAC with per-action permission mapping + queryset gating**  
**Taiga reference:** `taiga/users/models.py:Role.permissions`; `taiga/projects/models.py:Membership`; `taiga/permissions/services.py:user_has_perm`; `taiga/base/api/permissions.py:TaigaResourcePermission`; `taiga/base/filters.py:PermissionBasedFilterBackend`.

**ADR-003: Command endpoints for promotions/reruns/backfills**  
**Taiga reference:** `taiga/projects/mixins/promote.py:PromoteToUserStoryMixin.promote_to_user_story`; `taiga/projects/services/promote.py:promote_to_us`.

**ADR-004: OCC for mutable control-plane records**  
**Taiga reference:** `taiga/projects/occ/mixins.py:OCCResourceMixin._validate_and_update_version` + `taiga/projects/history/services.py:get_modified_fields`.

**ADR-005: Post-commit fan-out pipeline**  
**Taiga reference:** `taiga/timeline/signals.py:_push_to_timelines` uses `connection.on_commit`; `taiga/webhooks/signal_handlers.py:create_webhook_on_history_post_save` uses `connection.on_commit`.

---

### Proposed event taxonomy (Taiga-inspired)

Taiga timeline keys follow `"{typename}.{create|change|delete}"`.  
**Evidence:** `taiga/timeline/service.py:_get_impl_key_from_model`; registry usage in `taiga/timeline/timeline_implementations.py:@register_timeline_implementation`.

For our system:

**Run lifecycle**
- `run.queued`, `run.started`, `run.succeeded`, `run.failed`, `run.canceled`
- `run.stale_detected`, `run.rerun_initiated`, `run.backfill_initiated`

**Artifact versions**
- `artifact_version.uploaded`, `artifact_version.validation_failed`
- `artifact_version.promotion_requested`, `artifact_version.promoted`, `artifact_version.rejected`, `artifact_version.deprecated`

**Approvals**
- `approval.requested`, `approval.granted`, `approval.denied`, `approval.expired`, `approval.overridden`

**Human collaboration**
- `comment.created`, `comment.edited` (optional; consider immutable supersedes)
- `attachment.added`, `attachment.removed`
- `watch.subscribed`, `watch.unsubscribed`
- `assignment.claimed`, `assignment.released`

**Envelope fields**
- `event_id`, `occurred_at`, `actor`, `tenant_id`, `subject{type,id}`, `kind`, `data`, `correlation_id`  
**Taiga analog:** `taiga/timeline/models.py:Timeline` stores `event_type`, `namespace`, `data`, `created`; data is populated in `taiga/timeline/signals.py:on_new_history_entry`.

---

### Focus question answers (grounded)

**History for timelines:** `HistoryEntry` captures diffs/comments/snapshots; `Timeline` materializes UI feed items from `HistoryEntry` with `values_diff` and comment metadata.  
**Evidence:** `taiga/projects/history/models.py:HistoryEntry`; `taiga/timeline/signals.py:on_new_history_entry`; `taiga/timeline/models.py:Timeline`.

**Consistent permission enforcement:** per-action permission mapping + shared RBAC evaluator + queryset gating.  
**Evidence:** `taiga/base/api/permissions.py:TaigaResourcePermission`; `taiga/permissions/services.py:user_has_perm`; `taiga/base/filters.py:PermissionBasedFilterBackend`.

**Boards/backlogs scalability:** order keys + bulk reorder endpoints + UI metadata headers.  
**Evidence:** `taiga/base/utils/time.py:timestamp_ms`; `taiga/projects/tasks/api.py:bulk_update_order`; `taiga/projects/userstories/api.py:_add_taiga_info_headers`.
