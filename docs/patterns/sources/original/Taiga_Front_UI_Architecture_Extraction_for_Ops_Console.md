# Taiga Front — UI Architecture & Interaction Pattern Extraction for Orchestration Ops Console

Repository: `https://github.com/taigaio/taiga-front`  
Assumption: local checkout from `taiga-front-main` (version `6.9.0`). **Evidence:** `package.json#version`.

**GOAL**  
Extract frontend architecture patterns we can reuse for our operator/admin UI:
- high-density status grids/boards
- detail pages with timeline + comments + attachments
- real-time updates / polling strategies
- permission-aware UI states
- scalable state management patterns

---

## 1) Repo & UI Architecture Map

### 1.1 Framework & build toolchain

- Taiga Front is an **AngularJS 1.5.x** SPA (Angular core + `ngRoute` + `ngSanitize` + `ngAnimate`).  
  **Evidence:** `package.json#dependencies.angular`, `package.json#dependencies.angular-route`, `package.json#dependencies.angular-sanitize`, `package.json#dependencies.angular-animate`.

- Primary authoring stack is **CoffeeScript + Jade (Pug) + SCSS**, built with **Gulp**.  
  **Evidence:** `package.json#devDependencies.coffeescript`, `package.json#devDependencies.gulp-coffee`, `package.json#devDependencies.gulp-jade`, `package.json#devDependencies.gulp-sass`.

- “Ops-console relevant” UI libs include:
  - **Immutable.js** (immutable state snapshots),  
    **Evidence:** `package.json#dependencies.immutable`.
  - **Dragula + dom-autoscroller** for drag/drop boards,  
    **Evidence:** `package.json#dependencies.dragula`, `package.json#dependencies.dom-autoscroller`, plus board usage in `app/coffee/modules/kanban/sortable.coffee#dragula(...)` and `#autoScroll(...)`.
  - **ng-infinite-scroll** for event feeds and long lists,  
    **Evidence:** `package.json#dependencies.ng-infinite-scroll`, and global throttle in `app/coffee/app.coffee#angular.module('infinite-scroll').value('THROTTLE_MILLISECONDS', 500)`.

### 1.2 Runtime bootstrapping & configuration (app-loader)

- The app uses an **app-loader** that:
  1) loads `conf.json`, merges into `window.taigaConfig`,  
  2) loads JS bundles (`libs.js`, `templates.js`, optional plugins, `elements.js`, `app.js`),  
  3) then boots Angular manually via `angular.bootstrap(document, ['taiga'])`.  
  **Evidence:** `app-loader/app-loader.coffee#fetch "conf.json" ... Object.assign(...)`, `#loadJS("#{window._version}/js/libs.js")`, `#loadPlugins(window.taigaConfig.contribPlugins)`, `#angular.bootstrap(document, ['taiga'])`.

- `index.jade` references the loader script `js/app-loader.js`.  
  **Evidence:** `app/index.jade#script(src="#{v}/js/app-loader.js")`.

- Taiga exposes a **plugin decorator hook** (`window.addDecorator` / `window.getDecorators`) and plugin list (`window.taigaContribPlugins`).  
  **Evidence:** `app-loader/app-loader.coffee#window.addDecorator`, `#window.getDecorators`, `#window.taigaContribPlugins`.

### 1.3 Module boundaries & folder organization

- There is a **single root Angular module** `"taiga"` which composes many feature modules (base/common/resources/events + feature areas).  
  **Evidence:** `app/coffee/app.coffee#modules = [...]` and `app/coffee/app.coffee#angular.module("taiga", modules)`.

- Source is split into two major strata:
  - `app/coffee/` for many feature controllers/directives/services and app wiring (including routing),  
    **Evidence:** `app/coffee/app.coffee` and subtree `app/coffee/modules/**`.
  - `app/modules/` for newer-ish componentized feature modules (e.g., history, wiki history, attachments, resources2).  
    **Evidence:** `app/modules/history/history.module.coffee#angular.module("taigaHistory")`, `app/modules/resources/resources.module.coffee#angular.module("taigaResources2", [])`, `app/modules/components/attachments-full/attachments-full.service.coffee#angular.module("taigaComponents").service(...)`.

- Route-level templates live in `app/partials/`.  
  **Evidence:** `app/partials/task/task-detail.jade` (detail layout + attachments + history), and route mapping in `app/coffee/app.coffee#$routeProvider.when(... templateUrl: ...)`.

### 1.4 Routing approach (ngRoute + global resolves)

- Taiga uses `ngRoute` and **wraps** `$routeProvider.when` to inject global `resolve` entries:
  - `languageLoad`: ensures translations are ready
  - `projectLoaded`: loads/sets project context (or cleans it).  
  **Evidence:** `app/coffee/app.coffee#originalWhen = $routeProvider.when` and `$routeProvider.when = (path, route) -> ... route.resolve ... languageLoad ... projectLoaded ...`.

- Routes are organized by “screen”: projects, kanban, taskboard, entity detail pages, etc.  
  **Evidence:** examples in `app/coffee/app.coffee` (e.g., `/project/:pslug/t/:ref` handled by `DetailController`).

### 1.5 State management patterns

Taiga does **not** use a centralized Redux store; it uses a pattern that can be summarized as:

> **Service-as-store** + **Immutable snapshots** + **derived indices for fast rendering**.

Concrete evidence:

- Boards maintain normalized state:
  - `usMap`: `id -> viewModel`
  - `usByStatus` / `usByStatusSwimlanes`: `status (and swimlane) -> ordered list of ids`.  
  **Evidence:** `app/coffee/modules/kanban/kanban-usertories.coffee#reset()` initializes `@.usMap`, `@.usByStatus`, `@.usByStatusSwimlanes`.

- Controllers expose store data via `taiga.defineImmutableProperty(...)` so templates read immutable snapshots safely.  
  **Evidence:** `app/coffee/modules/kanban/main.coffee#taiga.defineImmutableProperty @.scope, "usByStatus" ...` and implementation in `app/coffee/utils.coffee#defineImmutableProperty` (throws if return is not immutable).

- Template iteration over immutable collections uses a **custom repeat directive** `tg-repeat` (a modified `ngRepeat`).  
  **Evidence:** implementation `app/js/tg-repeat.js#var ngRepeatDirective ... expression = $attr.tgRepeat` and usage in board template `app/partials/includes/modules/kanban-table.jade#tg-repeat="usId in usByStatus.get(...)"`.

---

## 2) Formal Model: UI as Projection of Event Log + Current State

### 2.1 Formal model

Let:
- \(E_{\text{ws}}(0..t)\): websocket “change” events received up to time \(t\)
- \(E_{\text{ui}}(0..t)\): user intents/actions up to time \(t\)
- \(S_{\text{srv}}(t)\): server snapshot state at time \(t\) (authoritative)
- \(\Delta_{\text{opt}}(t)\): optimistic local overlays applied before server confirmation
- \(P\): persisted user preferences (folded columns, saved filters, etc.)
- \(\Pi_{\theta(t)}\): projection operator defined by route + filters + viewport

Then a useful view definition is:
\[
V(t) = \Pi_{\theta(t)}\Big(S_{\text{srv}}(t) \oplus \Delta_{\text{opt}}(t) \oplus P\Big)
\]
where \(\oplus\) denotes “overlay/merge.”

### 2.2 What Taiga does in this model (consistency strategy)

**Websocket events exist, but boards treat them mainly as invalidation → refetch signals, not as authoritative patches.**

- WebSocket connection, auth, heartbeat ping/pong, and subscription handling are implemented in `EventsService`.  
  **Evidence:** `app/coffee/modules/events.coffee#setupConnection`, `#onOpen` (sends `{cmd:"auth"...}`), `#startHeartBeatMessages` (sends `{cmd:"ping"}`), `#processHeartBeatPongMessage`.

- The app enables events at runtime via `$events.setupConnection()`.  
  **Evidence:** `app/coffee/app.coffee#$events.setupConnection()`.

- **Kanban** subscribes to `changes.project.<id>.userstories` and on events calls `eventsLoadUserstories`, which refetches `userstories.listAll(...)` and updates the store via `replaceModel/add/refresh`.  
  **Evidence:** `app/coffee/modules/kanban/main.coffee#initializeSubscription` (routing key), `app/coffee/modules/kanban/main.coffee#eventsLoadUserstories` (calls `@rs.userstories.listAll` then `replaceModel`, `add`, `refresh(false)`).

- **Taskboard** subscribes to `changes.project.<id>.tasks` and refreshes via `loadTaskboard()` (coarser invalidation), and similarly for issues.  
  **Evidence:** `app/coffee/modules/taskboard/main.coffee#initializeSubscription` (routing keys + `debounceLeading(500, ...)`).

**Optimistic overlays exist for some UI actions:**
- Assigning a user in taskboard updates local model immediately via `replaceModel(...)` before `@repo.save(model)` resolves.  
  **Evidence:** `app/coffee/modules/taskboard/main.coffee#onAssignedToChanged` (mutates `model.assigned_to`, `@taskboardTasksService.replaceModel(model)`, then `@repo.save(model)`).
- Reordering attachments updates local immutable list immediately, then calls a bulk reorder endpoint.  
  **Evidence:** `app/modules/components/attachments-full/attachments-full.service.coffee#reorderAttachment` (reorders `@._attachments` then calls `attachmentsService.bulkUpdateOrder(...)`).

**Activity/history is treated as an event log feed:**
- Activity pagination is driven by `x-pagination-next` and rendered via infinite-scroll.  
  **Evidence:** `app/modules/history/activity/activity.service.coffee#fetchEntries` (uses `result.headers('x-pagination-next')`), and `app/modules/history/history.jade#infinite-scroll="vm.nextActivityPage()"`.

### 2.3 Polling / periodic refresh (when websockets are insufficient)
- Project metadata auto-refresh runs every 10 minutes and **stops when the user becomes inactive**; it restarts when active.  
  **Evidence:** `app/modules/services/project.service.coffee#autoRefresh` (interval `60 * 10 * 1000` + `@userActivityService.onInactive` cancels + `onActive` restarts), and idle detection in `app/modules/services/user-activity.service.coffee#idleTimeout = 60 * 5 * 1000` + `#_fireInactive/_fireActive`.

---

## 3) Core Interaction Patterns

### 3.1 Board/grid rendering strategy (density + performance)

**(A) Normalized ID indices drive rendering**
- Kanban renders cards by iterating IDs from `usByStatus` / `usByStatusSwimlanes` and resolving card data from `usMap.get(id)`.  
  **Evidence:** `app/partials/includes/modules/kanban-table.jade#tg-repeat="usId in usByStatus.get(...)"` and `#item="usMap.get(usId)"`; store structure in `app/coffee/modules/kanban/kanban-usertories.coffee#usByStatus/usMap/usByStatusSwimlanes`.

**(B) Progressive/batched rendering**
- `renderUserStories` builds an interleaved queue by status and renders in batches (initial batch size 100).  
  **Evidence:** `app/coffee/modules/kanban/main.coffee#renderUserStories` (queue logic + `@.batchSize = 100`) and `#renderBatch`.

**(C) Viewport-aware lazy rendering (“micro-virtualization”)**
- `initBoard()` uses `IntersectionObserver` to emit `SHOW_CARD` events for visible cards.  
  **Evidence:** `app/js/boards.js#new IntersectionObserver(... eventsCallback('SHOW_CARD', entries))`.
- The card template only renders inner DOM when `vm.inViewPort` is true.  
  **Evidence:** `app/modules/components/card/card.jade#.card-inner(ng-if="vm.inViewPort")`, and binding `inViewPort: "<"` in `app/modules/components/card/card.directive.coffee#bindToController`.

**(D) Column folding/squish persisted as user preference**
- Kanban fold state per status is stored in local storage via `$tgKanbanResourcesProvider`.  
  **Evidence:** `app/coffee/modules/resources/kanban.coffee#storeStatusColumnModes/getStatusColumnModes`.
- The fold toggle lives in `KanbanSquishColumnDirective`.  
  **Evidence:** `app/coffee/modules/kanban/main.coffee#KanbanSquishColumnDirective` (`$scope.foldStatus` uses `rs.kanban.getStatusColumnModes` and `storeStatusColumnModes`).

**(E) WIP limit visualization as an overlay marker**
- WIP limit markers are redrawn on board events and inserted into DOM based on card count vs `status.wip_limit`.  
  **Evidence:** `app/coffee/modules/kanban/main.coffee#KanbanWipLimitDirective` (computes `one-left/reached/exceeded` and inserts `.kanban-wip-limit`).

### 3.2 Drag/drop ordering & stable move payloads
- Kanban DnD uses Dragula containers and auto-scroll.  
  **Evidence:** `app/coffee/modules/kanban/sortable.coffee#drake = dragula(containers, ...)` and `#scroll = autoScroll(containers, ...)`.
- Move payload includes `previousCard` and `nextCard` IDs to allow stable insertion semantics.  
  **Evidence:** `app/coffee/modules/kanban/sortable.coffee#drake.on 'drop' ... previousCard ... nextCard ...` and `#broadcast("kanban:us:move", ..., previousCard, nextCard)`.

### 3.3 Filtering/search patterns
- Filter state is stored in the URL query string with include/exclude support via `exclude_` prefix and `location.noreload(...)`.  
  **Evidence:** `app/coffee/modules/controllerMixins.coffee#class FiltersMixin` (`excludePrefix: "exclude_"`, `selectFilter/unselectFilter`, `location.noreload(@scope)`).
- Kanban merges URL filters into API params and sets `params.q = @.filterQ`.  
  **Evidence:** `app/coffee/modules/kanban/main.coffee#validQueryParams` and `#loadUserstoriesParams` (uses `_.pick(@location.search(), @.validQueryParams)` and `params.q = @.filterQ`).

- Saved custom filters are stored remotely via a `user-storage` keyed by a hash.  
  **Evidence:** `app/modules/components/filter/filter-remote.service.coffee#storeFilters/getFilters` (`url = @urls.resolve("user-storage")`, `hash = generateHash([projectId, ns])`), and usage in `app/coffee/modules/controllerMixins.coffee#UsFiltersMixin.saveCustomFilter`.

### 3.4 Pagination & infinite scroll
- Infinite scroll throttle is set globally to 500ms.  
  **Evidence:** `app/coffee/app.coffee#angular.module('infinite-scroll').value('THROTTLE_MILLISECONDS', 500)`.
- Activity feeds use infinite-scroll to call `nextActivityPage()` and rely on cursor headers.  
  **Evidence:** `app/modules/history/history.jade#infinite-scroll="vm.nextActivityPage()"`, `app/modules/history/activity/activity.service.coffee#disablePagination = !result.headers('x-pagination-next')`.

### 3.5 Detail view patterns (timeline/comments/attachments)
- Task detail page layout is “main detail” + “sidebar actions” and includes both attachments and history modules.  
  **Evidence:** `app/partials/task/task-detail.jade#tg-attachments-full` and `#tg-history-section`, plus sidebar `tg-delete-button`, `tg-promote-to-us-button`, etc.

- History section is tabbed: comments vs activity; activity tab supports infinite scroll.  
  **Evidence:** `app/modules/history/history.jade#tg-history-tabs` and activity wrapper `div(infinite-scroll="vm.nextActivityPage()")`.

- Attachments UX supports list/gallery modes, drag/drop upload, reorder, and “deprecated attachments” toggle.  
  **Evidence:** `app/modules/components/attachments-full/attachments-full.jade#button.view-gallery/view-list`, `#tg-attachments-drop`, `#tg-attachments-sortable`, and deprecated toggle `#vm.toggleDeprecatedsVisible()`; service logic in `app/modules/components/attachments-full/attachments-full.service.coffee#toggleDeprecatedsVisible/regenerate`.

---

## 4) Permission-Aware UI

### 4.1 Permission source-of-truth
- Project permissions are stored in `project.my_permissions`, exposed via ProjectService helpers.  
  **Evidence:** `app/modules/services/project.service.coffee#hasPermission(permission)` and `#canEdit(permission)` and uses `@._project.get('my_permissions')`.

- There is a smaller permissions helper for components.  
  **Evidence:** `app/modules/services/check-permissions.service.coffee#check(permission)`.

### 4.2 Hide vs disable/read-only
- Hide: `tg-check-permission` hides elements unless `projectService.canEdit(permission)` returns true.  
  **Evidence:** `app/coffee/modules/common.coffee#CheckPermissionDirective` (`$el.addClass('hidden')` and removes it when `canEdit`).

- Read-only UI: the detail header applies a `.readonly` class and removes edit affordances when `canEdit` is false.  
  **Evidence:** `app/modules/components/detail/header/detail-header.jade#ng-class="{readonly: !vm.permissions.canEdit}"` and `ng-if="vm.permissions.canEdit"`; permission computation in `app/modules/components/detail/header/detail-header.controller.coffee#_checkPermissions`.

### 4.3 Guarded actions pattern (confirm → mutate → toast → broadcast)
- Promote-to-user-story is a concrete example: confirm dialog → POST → success toast → broadcast `promote-...:success`.  
  **Evidence:** `app/modules/components/promote-to-us/promote-to-us.directive.coffee#PromoteToUsButtonDirective` (`$confirm.ask` then `$rs[item._name].promoteToUserStory` then `$confirm.notify("success")` + `$rootScope.$broadcast(...)`), and permission gating in `app/modules/components/promote-to-us/promote-to-us.jade#tg-check-permission="add_us"`.

### 4.4 Error recovery states
- “Blocked” state is enforced via an HTTP interceptor that calls `errorHandlingService.block()` on either `response.data.blocked_code` or HTTP `451`.  
  **Evidence:** `app/coffee/app.coffee#blockingIntercept` and `#redirectToBlockedPage -> errorHandlingService.block()`, plus state in `app/modules/services/error-handling.service.coffee#block`.

- Version conflict shows a specific notification when server returns `400` with a `version` field.  
  **Evidence:** `app/coffee/app.coffee#versionCheckHttpIntercept` (checks `response.status == 400 && response.data.version` and triggers `$tgConfirm.notify`).

---

## 5) Real-Time / Near-Real-Time Updates

### 5.1 How updates propagate
- Websocket connect/auth/heartbeat is centralized in `EventsService`.  
  **Evidence:** `app/coffee/modules/events.coffee#setupConnection`, `#onOpen`, `#startHeartBeatMessages`, `#subscribe`, `#unsubscribe`.

- Boards subscribe to routing keys and debounce refresh work:
  - Kanban uses `debounceLeading` with a randomized timeout (700–1000ms).  
    **Evidence:** `app/coffee/modules/kanban/main.coffee#initializeSubscription` (`randomTimeout = taiga.randomInt(700, 1000)` and `@events.subscribe ... debounceLeading randomTimeout`).
  - Taskboard uses `debounceLeading(500, ...)`.  
    **Evidence:** `app/coffee/modules/taskboard/main.coffee#initializeSubscription`.

### 5.2 Avoiding disruptive refresh during editing
- Kanban defers “project structure changed” refresh while a lightbox is open and performs refresh on close if needed.  
  **Evidence:** `app/coffee/modules/kanban/main.coffee#scope.$on "lightbox:opened"/"lightbox:closed"` and `#isRefreshNeeded` gating in `#initializeSubscription`.

### 5.3 Best-fit adaptation for our statuses (runs + promotions)
Adaptation (our design), grounded in Taiga’s model:

- Prefer **websocket/SSE invalidation** + **targeted snapshot refetch** (per partition/run) rather than trusting event payloads as state.  
  Taiga precedent: invalidation → refetch in kanban via `eventsLoadUserstories`.  
  **Evidence:** `app/coffee/modules/kanban/main.coffee#eventsLoadUserstories`.

- Use **debounced refresh with jitter** to avoid thundering herds during high churn.  
  Taiga precedent: `randomTimeout` + `debounceLeading`.  
  **Evidence:** `app/coffee/modules/kanban/main.coffee#initializeSubscription`.

- Mark “STALE” as an explicit UI state using “last sync” timestamps and TTL (our design), similar to how Taiga persists fold/hide preferences separate from server state.  
  Taiga precedent: persisted folds/hides for statuses and swimlanes.  
  **Evidence:** `app/coffee/modules/resources/kanban.coffee#storeStatusColumnModes/getStatusColumnModes` and hide logic `app/coffee/modules/kanban/kanban-usertories.coffee#hideStatus`.

---

## 6) Mapping to Our UI (Table)

| Our screen requirement | Taiga pattern | Evidence (file#identifier) | Reuse / adapt | Risks |
|---|---|---|---|---|
| Operator: **Pipeline overview grid** (partition_key × step status) | Status-column board driven by normalized store + progressive render + viewport lazy rendering | `app/coffee/modules/kanban/kanban-usertories.coffee#usByStatus/usMap`, `app/coffee/modules/kanban/main.coffee#renderUserStories`, `app/js/boards.js#IntersectionObserver`, `app/modules/components/card/card.jade#ng-if="vm.inViewPort"` | Build `partitionMap` + indices; batch render; lazy-render heavy cell content | Taiga is “micro-virtualized”; for 10k×steps we may need true windowing |
| Operator: **Partition detail** (datasets, versions, runs list, rerun/backfill) | Detail page main+sidebar; embeds attachments + history; guarded sidebar actions | `app/partials/task/task-detail.jade#tg-attachments-full` + `#tg-history-section` + sidebar `tg-delete-button` | Mirror layout; actions in sidebar; runs list uses infinite scroll | Our detail is more “data table” heavy than ticket-like |
| Operator: **Run detail** (inputs/outputs/logs/child runs + timeline/comments/attachments) | History module = comments + activity feed (infinite scroll) + attachments-full | `app/modules/history/history.jade#tg-comments + tg-history`, `app/modules/history/activity/activity.service.coffee#x-pagination-next`, `app/modules/components/attachments-full/attachments-full.jade` | Implement run timeline as event feed with comments + artifacts | Requires a run-event API similar to Taiga history endpoints |
| Operator: **Dataset registry** (version history + promote action) | Version/event list via ActivityService + diff view + guarded promote action | `app/modules/wiki/history/wiki-history.controller.coffee#activityService.init('wiki', ...)`, `app/modules/wiki/history/wiki-history-diff.jade#content_diff`, `app/modules/components/promote-to-us/promote-to-us.directive.coffee#PromoteToUsButtonDirective` | Version history + diff drawer; promote guarded flow | Taiga diff is text/html oriented; dataset diffs are semantic |
| Admin: **Define/edit pipeline DAG** | “Admin list editing” patterns: reorder via dragula + delete w/ replacement choice | `app/coffee/modules/admin/project-values.coffee#linkDragAndDrop` and confirm choice `app/coffee/modules/common/confirm.coffee#askChoice` | Reuse reorder + replacement patterns for list-like config | DAG is graph editing; may require canvas/graph UI |
| Admin: **templates/mappings/validations/guardrails** | Saved views + persisted UI prefs + confirm/notify conventions | prefs local `app/coffee/modules/resources/kanban.coffee#storeStatusColumnModes`, remote saved filters `app/modules/components/filter/filter-remote.service.coffee#storeFilters/getFilters`, confirm `app/coffee/modules/common/confirm.coffee#ask/notify` | Saved admin views; consistent confirm to reduce mistakes | We need stronger validation/preview flows than Taiga CRUD |

---

## 7) Components/UX Patterns to Reuse (10+)

> Each item includes **(Taiga pattern + evidence)**, then **(adaptation)**.

1) **Normalized store: map + indices**  
   - Taiga: `usMap` + `usByStatus` + `usByStatusSwimlanes`.  
     **Evidence:** `app/coffee/modules/kanban/kanban-usertories.coffee#reset()` and usage in `app/partials/includes/modules/kanban-table.jade#item="usMap.get(usId)"`.  
   - Adaptation: `partitionMap` + `partitionIdsByStepStatus`.

2) **Progressive render batching**  
   - Taiga: `renderUserStories` interleaves statuses and renders in batches.  
     **Evidence:** `app/coffee/modules/kanban/main.coffee#renderUserStories` and `#renderBatch`.  
   - Adaptation: first paint skeleton + above-the-fold partitions; then fill the rest.

3) **Viewport-aware lazy rendering (IntersectionObserver)**  
   - Taiga: `boards.js` emits `SHOW_CARD` for visible cards.  
     **Evidence:** `app/js/boards.js#new IntersectionObserver(...)`.  
   - Taiga: card inner DOM guarded by `ng-if="vm.inViewPort"`.  
     **Evidence:** `app/modules/components/card/card.jade#.card-inner(ng-if="vm.inViewPort")`.  
   - Adaptation: lazy-render logs previews / artifacts.

4) **Persisted fold/squish per column**  
   - Taiga: store folds in local storage via resources provider.  
     **Evidence:** `app/coffee/modules/resources/kanban.coffee#storeStatusColumnModes/getStatusColumnModes`.  
   - Taiga: fold UI in `KanbanSquishColumnDirective`.  
     **Evidence:** `app/coffee/modules/kanban/main.coffee#KanbanSquishColumnDirective`.  
   - Adaptation: fold rarely used pipeline steps; remember per-user.

5) **Dynamic column width based on density (taskboard)**  
   - Taiga: width calculation based on tasks count + fold flags.  
     **Evidence:** `app/coffee/modules/taskboard/main.coffee#TaskboardSquishColumnDirective` (`getCeilWidth`, `recalculateStatusColumnWidth`).  
   - Adaptation: widen “busy” steps showing many runs, shrink idle steps.

6) **Header scroll synchronization**  
   - Taiga: taskboard adjusts header left based on body scroll.  
     **Evidence:** `app/coffee/modules/taskboard/main.coffee#TaskboardDirective` (`tableBodyDom.on "scroll" ... tableHeaderDom.css("left", ...)`).  
   - Adaptation: keep step headers aligned in horizontally scrollable partition grid.

7) **Drag/drop move payload uses neighbor IDs**  
   - Taiga: computes `previousCard` and `nextCard` and broadcasts with move intent.  
     **Evidence:** `app/coffee/modules/kanban/sortable.coffee#previousCard/nextCard` + `$rootScope.$broadcast("kanban:us:move", ..., previousCard, nextCard)`.  
   - Adaptation: reorder partitions or runs; stable insertion without recomputing full order.

8) **Websocket invalidation + debounced refresh + jitter**  
   - Taiga: randomized debounce in kanban.  
     **Evidence:** `app/coffee/modules/kanban/main.coffee#initializeSubscription` (`randomTimeout = taiga.randomInt(700, 1000)` + `debounceLeading randomTimeout`).  
   - Adaptation: avoid refresh storms when many runs update at once.

9) **Pause refresh while modal editing**  
   - Taiga: lightbox gating defers refresh and applies on close.  
     **Evidence:** `app/coffee/modules/kanban/main.coffee#lightbox:opened/lightbox:closed` and `#isRefreshNeeded`.  
   - Adaptation: prevent live status churn from resetting operator edits.

10) **Guarded actions: confirm → mutate → toast → broadcast**  
   - Taiga: promote-to-us flow.  
     **Evidence:** `app/modules/components/promote-to-us/promote-to-us.directive.coffee#PromoteToUsButtonDirective` and template gating `app/modules/components/promote-to-us/promote-to-us.jade#tg-check-permission="add_us"`.  
   - Adaptation: rerun/backfill/promote with guardrails confirmation + global refresh event.

11) **Serialized model saves to avoid race conditions**  
   - Taiga: `$tgQueueModelTransformation.save()` serializes changes using a queue.  
     **Evidence:** `app/coffee/modules/common.coffee#class QueueModelTransformation` and `#save`.  
   - Adaptation: serialize run mutations (notes, tags, promote metadata).

12) **Event-log timeline with infinite scroll**  
   - Taiga: activity uses `x-pagination-next` cursor header.  
     **Evidence:** `app/modules/history/activity/activity.service.coffee#fetchEntries` and `app/modules/history/history.jade#infinite-scroll`.  
   - Adaptation: run timeline = ordered events; fetch older pages on scroll.

---

## 8) Actionable Output

### 8.1 Proposed information architecture for our UI (routes + main components)

**Operator UI**
- `/ops/pipelines` → `PipelinesIndexPage` (search + saved views)
- `/ops/pipelines/:pipelineId/overview` → `PipelineOverviewGridPage`
  - `PartitionStatusGrid` (normalized store + batching + lazy details)
  - `GridFiltersBar` (URL-synced include/exclude filters; saved presets)
- `/ops/pipelines/:pipelineId/partitions/:partitionKey` → `PartitionDetailPage`
  - `DatasetsAndVersionsPanel`, `RunsList` (cursor pagination + infinite scroll)
  - `PartitionActions` (rerun/backfill/promote guarded)
- `/ops/runs/:runId` → `RunDetailPage`
  - `RunInputsOutputsPanel`, `RunLogsPanel`, `ChildRunsPanel`
  - `RunTimeline` (activity feed + comments) + `RunArtifacts/Attachments`

**Admin UI**
- `/admin/pipelines` → `AdminPipelinesIndex`
- `/admin/pipelines/:pipelineId/dag` → `PipelineDagEditorPage`
- `/admin/pipelines/:pipelineId/templates` → `TemplatesListEditor`
- `/admin/pipelines/:pipelineId/guardrails` → `GuardrailsConfigEditor`

(These are our proposals, not claims about Taiga.)

### 8.2 Three UI spikes to prototype (with Taiga anchors)

1) **Spike A — Partition status grid**  
   - Taiga anchors: normalized board store + batching + viewport lazy render.  
     **Evidence:** `app/coffee/modules/kanban/kanban-usertories.coffee#usMap/usByStatus`, `app/coffee/modules/kanban/main.coffee#renderUserStories`, `app/js/boards.js#IntersectionObserver`.

2) **Spike B — Run detail timeline (event log + comments + attachments)**  
   - Taiga anchors: history module + ActivityService + attachments-full.  
     **Evidence:** `app/modules/history/history.jade`, `app/modules/history/activity/activity.service.coffee#fetchEntries`, `app/modules/components/attachments-full/attachments-full.jade`.

3) **Spike C — Dataset registry version history + diff + promote**  
   - Taiga anchors: wiki history paging + diff template + promote guarded action.  
     **Evidence:** `app/modules/wiki/history/wiki-history.controller.coffee#initializeHistory`, `app/modules/wiki/history/wiki-history-diff.jade#content_diff`, `app/modules/components/promote-to-us/promote-to-us.directive.coffee#PromoteToUsButtonDirective`.

---

*End of report.*
