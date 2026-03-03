# Kanboard — Lightweight UI/Plugin Patterns for Orchestration Ops Console

> **Scope note:** This report is based on the *local checkout* of `kanboard/kanboard` (from the provided zip) and cites concrete evidence as **file paths + identifiers** (classes/methods/templates/hooks) per the evidence rule.

---

## 1) Repo & Runtime Topology

### 1.1 “Framework style” in one sentence
Kanboard is a **custom PHP MVC** app with a **Pimple DI container**, a **bespoke router**, a **middleware chain**, and **Symfony EventDispatcher** as the core extension mechanism.  
**Evidence:** `index.php`; `app/common.php`; `app/Core/Http/Router.php::dispatch()`; `app/Core/Controller/Runner.php::execute()`; `app/ServiceProvider/EventDispatcherProvider.php::register()`; `app/Core/Base.php::__get()`.

---

### 1.2 Entry points
- **Web:** `index.php` loads `app/common.php`, dispatches routing, and executes the controller runner.  
  **Evidence:** `index.php` (script body calling `$container['router']->dispatch()` then `$container['runner']->execute()`).

- **JSON-RPC API:** `jsonrpc.php` loads `app/common.php`, dispatches `'app.bootstrap'`, and runs `$container['api']->execute()`.  
  **Evidence:** `jsonrpc.php` (script body calling `$container['dispatcher']->dispatch(..., 'app.bootstrap')` and `$container['api']->execute()`).

- **CLI:** `cli` bootstraps `app/common.php`, optionally dispatches `'app.bootstrap'`, then runs Symfony Console application.  
  **Evidence:** `cli` (script body calling `$container['cli']->run()` and dispatching `'app.bootstrap'` for non-migrate commands).

---

### 1.3 Request lifecycle
A typical **HTTP request** flows like:

1) `index.php` boots container and dispatches router.  
   **Evidence:** `index.php`.

2) Router determines controller/action (and optional plugin).  
   **Evidence:** `app/Core/Http/Router.php::dispatch()`.

3) Runner executes a middleware pipeline, then invokes the controller method.  
   **Evidence:** `app/Core/Controller/Runner.php::execute()`; `app/Core/Controller/Runner.php::executeMiddleware()`; `app/Core/Controller/Runner.php::executeController()`.

4) Middleware stages include bootstrap, auth, and authorization.  
   **Evidence:** `app/Core/Controller/Runner.php::executeMiddleware()` (instantiates middlewares); `app/Middleware/BootstrapMiddleware.php::execute()`; `app/Middleware/AuthenticationMiddleware.php::execute()`; `app/Middleware/ApplicationAuthorizationMiddleware.php::execute()`; `app/Middleware/ProjectAuthorizationMiddleware.php::execute()`.

5) Bootstrap dispatches `'app.bootstrap'` which attaches configured automatic actions and loads language/timezone.  
   **Evidence:** `app/Middleware/BootstrapMiddleware.php::execute()`; `app/Subscriber/BootstrapSubscriber.php::execute()`.

---

### 1.4 Module map (practical)
These are the “interesting seams” for reuse:

- **Controllers (HTTP):** `app/Controller/*` (board, tasks, activity, notifications).  
  **Evidence:** e.g., `app/Controller/BoardViewController.php`, `app/Controller/BoardAjaxController.php`, `app/Controller/ActivityController.php`, `app/Controller/WebNotificationController.php`.

- **Models (DB + domain operations):** `app/Model/*` (tasks, columns, swimlanes, actions, activities, permissions).  
  **Evidence:** e.g., `app/Model/TaskPositionModel.php`, `app/Model/ColumnModel.php`, `app/Model/SwimlaneModel.php`, `app/Model/ActionModel.php`, `app/Model/ProjectActivityModel.php`.

- **Formatters (view-model shaping):** `app/Formatter/*`  
  **Evidence:** `app/Formatter/BoardFormatter.php::format()`; `app/Formatter/BoardSwimlaneFormatter.php::format()`; `app/Formatter/BoardColumnFormatter.php::format()`.

- **Templates (PHP views + hook points):** `app/Template/*`  
  **Evidence:** `app/Template/board/table_container.php`; `app/Template/board/table_column.php`; `app/Template/board/task_private.php`; `app/Template/task/dropdown.php`.

- **Events + Subscribers (cross-cutting):** `app/ServiceProvider/EventDispatcherProvider.php`, `app/Subscriber/*`  
  **Evidence:** `app/Subscriber/NotificationSubscriber.php::getSubscribedEvents()`; `app/Subscriber/ProjectModificationDateSubscriber.php::getSubscribedEvents()`; `app/Subscriber/TransitionSubscriber.php::getSubscribedEvents()`.

- **Automatic actions:** `app/Core/Action/ActionManager.php`, `app/Action/*`, `app/ServiceProvider/ActionProvider.php`  
  **Evidence:** `app/Core/Action/ActionManager.php::attachEvents()`; `app/Action/Base.php::execute()`; `app/ServiceProvider/ActionProvider.php::register()`.

- **Plugin system + hooks:** `app/Core/Plugin/*`, `app/Helper/HookHelper.php`  
  **Evidence:** `app/Core/Plugin/Loader.php::scan()`; `app/Core/Plugin/Base.php::initialize()`; `app/Helper/HookHelper.php::render()`.

---

## 2) Formal Model: Task State as Finite State Machine

Kanboard’s “board state” is primarily **task-in-column**, with **swimlane** as an orthogonal partitioning axis and **open/closed** as a separate status bit.

### 2.1 State set Σ (columns/statuses)

Let a project be \( p \). Define:

- **Columns (board states):**  
  \[
  \Sigma_p = \{ c_1, \dots, c_n \}
  \]
  where each \( c \in \Sigma_p \) corresponds to a row in the `columns` table with `(id, project_id, title, position, task_limit, …)`.  
  **Evidence:** `app/Model/ColumnModel.php::TABLE`; `app/Model/BoardModel.php::create()` (persists to `ColumnModel::TABLE`).

- **Default column set** (when creating a new project):  
  \[
  \Sigma_p^{default} = \{\text{Backlog}, \text{Ready}, \text{Work in progress}, \text{Done}\}
  \]
  created via `BoardModel::getDefaultColumns()` → `BoardModel::getUserColumns()` → `BoardModel::create()` during `ProjectModel::create()`.  
  **Evidence:** `app/Model/BoardModel.php::getDefaultColumns()`; `app/Model/BoardModel.php::getUserColumns()`; `app/Model/ProjectModel.php::create()`.

- **Open/Closed status bit** (not a column): task status is `TaskModel::STATUS_OPEN` or `TaskModel::STATUS_CLOSED` stored as `tasks.is_active`.  
  **Evidence:** `app/Model/TaskModel.php::STATUS_OPEN` / `STATUS_CLOSED`; `app/Model/TaskStatusModel.php::close()` / `open()`.

So a practical “complete” state space is:
\[
\Sigma'_p = \Sigma_p \times \{\text{open}, \text{closed}\}
\]
with the board rendering focusing on the open slice.  
**Evidence:** `app/Formatter/BoardFormatter.php::format()` filters `TaskModel::TABLE.'.is_active'` to `TaskModel::STATUS_OPEN`.

---

### 2.2 Task state variables and invariants
For a task \( t \):

- Board-state variable:  
  \[
  s(t) = \text{tasks.column\_id} \in \Sigma_p
  \]
- Partition variable (swimlane):  
  \[
  \ell(t) = \text{tasks.swimlane\_id}
  \]
- Ordering within (swimlane, column):  
  \[
  \pi(t) = \text{tasks.position} \in \mathbb{N}
  \]

**Evidence:** `app/Model/TaskCreationModel.php::prepare()` (sets `column_id`, `swimlane_id`, `position`); `app/Model/TaskPositionModel.php::movePosition()` (updates `column_id`, `swimlane_id`, `position`); `app/Model/TaskModel.php` (task fields are used throughout).

---

### 2.3 Transition events \(E\)
Kanboard defines transition-like events on `TaskModel` constants, including:

- \( e = \texttt{task.move.column} \) (`TaskModel::EVENT_MOVE_COLUMN`)  
- \( e = \texttt{task.move.swimlane} \) (`TaskModel::EVENT_MOVE_SWIMLANE`)  
- \( e = \texttt{task.move.position} \) (`TaskModel::EVENT_MOVE_POSITION`)  
- \( e = \texttt{task.close} \) (`TaskModel::EVENT_CLOSE`)  
- \( e = \texttt{task.open} \) (`TaskModel::EVENT_OPEN`)  
- \( e = \texttt{task.create} \) (`TaskModel::EVENT_CREATE`)  

**Evidence:** `app/Model/TaskModel.php` (event constants); `app/Model/TaskPositionModel.php::fireEvents()` (fires MOVE_* events); `app/Model/TaskCreationModel.php::create()` (fires CREATE); `app/Model/TaskStatusModel.php::changeStatus()` (fires OPEN/CLOSE).

---

### 2.4 Transition function δ and how Kanboard encodes it

#### Move within board (column + position + swimlane)
A drag/drop or reorder triggers:

\[
\delta\big((c,\ell,\pi), \texttt{movePosition}(c',\ell',\pi')\big) = (c',\ell',\pi')
\]

Implementation highlights:

- `TaskPositionModel::movePosition()` performs:
  - position compaction / insertion (`TaskPositionModel::savePositions()`),
  - updates `tasks.column_id`, `tasks.swimlane_id`, `tasks.position`, and `tasks.date_moved` (`TaskPositionModel::movePosition()`),
  - fires events for swimlane/column/position changes via `TaskEventJob`.  
  **Evidence:** `app/Model/TaskPositionModel.php::movePosition()`; `app/Model/TaskPositionModel.php::fireEvents()`.

- The event payload is built by `TaskEventBuilder`, which always includes `task_id` and full `task` details (`taskFinderModel->getDetails`), and may include `changes` and extra values (`src_column_id`, `dst_column_id`, …).  
  **Evidence:** `app/EventBuilder/TaskEventBuilder.php::buildEvent()`; `app/Job/TaskEventJob.php::execute()`.

---

#### Open/Close (status bit)
Closing is:
\[
\delta\big((c,\ell,\pi,\text{open}), \texttt{close}\big) = (c,\ell,\pi,\text{closed})
\]
Opening is:
\[
\delta\big((c,\ell,\pi,\text{closed}), \texttt{open}\big) = (c,\ell,\pi,\text{open})
\]

Implementation:
- `TaskStatusModel::close()` updates `tasks.is_active`, sets `date_completed`, updates `date_modification`, and pushes `TaskEventJob` for `TaskModel::EVENT_CLOSE`.  
  **Evidence:** `app/Model/TaskStatusModel.php::close()`; `app/Model/TaskStatusModel.php::changeStatus()`.

- `TaskStatusModel::open()` reverses `is_active` and clears `date_completed`, fires `TaskModel::EVENT_OPEN`.  
  **Evidence:** `app/Model/TaskStatusModel.php::open()`; `app/Model/TaskStatusModel.php::changeStatus()`.

---

### 2.5 Constraints and guards (what makes δ partial)

Kanboard’s board transitions are **not “anything goes”**—they’re restricted by role permissions, per-column rules, and WIP/task limits.

#### Role-based move graph restrictions
- Allowed move destinations can be constrained by role via the **column move restriction** model (`column_has_move_restrictions`).  
  **Evidence:** `app/Model/ColumnMoveRestrictionModel.php::TABLE`; `app/Model/ColumnMoveRestrictionModel.php::getAllByRole()`.

- UI/behavioral enforcement happens via `ProjectRoleHelper::canMoveTask()` and `ProjectRoleHelper::isDraggable()` (used by `BoardTaskFormatter`).  
  **Evidence:** `app/Helper/ProjectRoleHelper.php::canMoveTask()`; `app/Helper/ProjectRoleHelper.php::isDraggable()`; `app/Formatter/BoardTaskFormatter.php::format()`.

- Move restrictions are cached by `ColumnMoveRestrictionCacheDecorator::getSortableColumns()` which is used by the role helper.  
  **Evidence:** `app/Decorator/ColumnMoveRestrictionCacheDecorator.php::getSortableColumns()`; `app/Helper/ProjectRoleHelper.php::canMoveTask()`.

#### Column-level rules (create/open/close)
- Per-role, per-column rules can explicitly allow/block:
  - task creation in a column, and
  - open/close in a column.  
  **Evidence:** `app/Model/ColumnRestrictionModel.php::RULE_*`; `app/Helper/ProjectRoleHelper.php::canCreateTaskInColumn()`; `app/Helper/ProjectRoleHelper.php::canChangeTaskStatusInColumn()`.

#### Project-role restrictions (broad capability toggles)
Custom project roles can be restricted from:
- creating tasks,
- moving tasks,
- changing assignee,
- opening/closing tasks, etc.  
**Evidence:** `app/Model/ProjectRoleRestrictionModel.php::RULE_*`; `app/Helper/ProjectRoleHelper.php::canCreateTask()` / `canMoveTask()` / `canChangeTaskStatus()` / `canChangeAssignee()`.

#### WIP/task limits (capacity constraints)
Kanboard encodes “blocked-by-capacity” as:
- per-project task limit: `projects.task_limit`,
- per-swimlane task limit: `swimlanes.task_limit`,
- per-column task limit: `columns.task_limit`.  
**Evidence:** `app/Model/ProjectModel.php::create()` (converts `task_limit`); `app/Model/SwimlaneModel.php::getAllWithTaskCount()` (selects `task_limit`); `app/Model/ColumnModel.php` (column `task_limit` field usage); `app/Template/board/table_container.php` (project limit visual); `app/Template/board/table_tasks.php` (swimlane+column limit visuals).

---

### 2.6 History: transitions, audit, and time-in-state
Kanboard records “state movement” in two complementary ways:

1) **Transition table** captures time spent moving between columns.  
   - Subscriber saves on move-column events: `TransitionSubscriber` listens to `TaskModel::EVENT_MOVE_COLUMN`.  
     **Evidence:** `app/Subscriber/TransitionSubscriber.php::getSubscribedEvents()`; `app/Subscriber/TransitionSubscriber.php::execute()`.

   - `TransitionModel::save()` persists `(src_column_id, dst_column_id, date, time_spent)` using `task['date_moved']`.  
     **Evidence:** `app/Model/TransitionModel.php::save()`.

   - DB schema explicitly defines `transitions` table.  
     **Evidence:** `app/Schema/Sqlite.php::version_55()` (creates `transitions` table).

2) **Project activity stream** records a higher-level audit trail of events.
   - Activity stream is implemented as a notification type: `ActivityStreamNotification::notifyProject()` calls `projectActivityModel->createEvent(...)`.  
     **Evidence:** `app/Notification/ActivityStreamNotification.php::notifyProject()`; `app/Model/ProjectActivityModel.php::createEvent()`.

   - UI retrieval/formatting: `ActivityController` uses `ProjectActivityHelper`, which queries `projectActivityQuery` and formats with `ProjectActivityEventFormatter`.  
     **Evidence:** `app/Controller/ActivityController.php::project()`; `app/Helper/ProjectActivityHelper.php::getProjectEvents()`; `app/Formatter/ProjectActivityEventFormatter.php::format()`.

   - Event data stored as JSON, with explicit handling for legacy serialized values (refuses to unserialize).  
     **Evidence:** `app/Formatter/ProjectActivityEventFormatter.php::getEventData()` (JSON decode + “ignore legacy serialized activity records”).

---

## 3) Board Rendering & Interaction Model

### 3.1 Rendering pipeline (“formatters as view-model builders”)
Board render is a 3-stage transformation:

1) **Controller:** `BoardViewController::show()` and `::readonly()` build the board data and choose template.  
   **Evidence:** `app/Controller/BoardViewController.php::show()`; `app/Controller/BoardViewController.php::readonly()`.

2) **Formatter 1:** `BoardFormatter` loads swimlanes, columns, tasks, tags, and produces a normalized board structure.  
   **Evidence:** `app/Formatter/BoardFormatter.php::format()`.

3) **Formatter 2:** `BoardSwimlaneFormatter` expands swimlanes into rows and uses `BoardColumnFormatter` to populate each cell.  
   **Evidence:** `app/Formatter/BoardSwimlaneFormatter.php::format()`; `app/Formatter/BoardColumnFormatter.php::format()`.

This is a clean pattern to reuse: **separate “domain query” from “UI shape”** while staying lightweight (no heavy view-model framework).  
**Evidence:** `app/Formatter/BoardFormatter.php::format()` (DB queries + base structure) vs `app/Formatter/BoardSwimlaneFormatter.php::format()` (presentation shaping).

---

### 3.2 Board structure: columns, swimlanes, and task cards

#### Columns
- Columns are project-scoped and fetched with open task counts (`ColumnModel::getAllWithOpenedTaskCount`).  
  **Evidence:** `app/Formatter/BoardFormatter.php::format()` (calls `columnModel->getAllWithOpenedTaskCount()`); `app/Model/ColumnModel.php::getAllWithOpenedTaskCount()`.

- Column header supports a dropdown for bulk actions + ordering modes, and exposes hook points for plugins.  
  **Evidence:** `app/Template/board/table_column.php` (dropdown menu with reorder links and `$this->hook->render(...)` calls like `'template:board:column:dropdown'` and `'template:board:column:header'`).

#### Swimlanes
- Swimlanes are project-scoped lanes with active/inactive status and optional WIP limit.  
  **Evidence:** `app/Model/SwimlaneModel.php::getAllByStatus()`; `app/Model/SwimlaneModel.php` (`task_limit` field usage); `app/Formatter/BoardFormatter.php::format()` (fetches swimlanes); `app/Template/board/table_swimlane.php` (collapse/expand UI).

#### Task cards
- Each task card (`board/task_private.php`) carries a dense set of `data-*` attributes used by JS for drag/drop, navigation, and context.  
  **Evidence:** `app/Template/board/task_private.php` (attributes: `data-task-id`, `data-column-id`, `data-swimlane-id`, `data-position`, `data-owner-id`, `data-task-url`, etc.).

- Card footer uses iconography to surface key “operator signals”: links/dependencies, subtasks progress, attachments, comments, description presence, age, **days in column**, priority, etc.  
  **Evidence:** `app/Template/board/task_footer.php` (icons + tooltips; uses `date_moved` for “days in column”).

---

### 3.3 Filters (board search language)
Board filtering is not ad-hoc SQL; it’s a small **lexer → filter objects → query builder** pipeline:

- `BoardViewController` applies `taskLexer->build($search)->format($boardFormatter->withProjectId(...))`.  
  **Evidence:** `app/Controller/BoardViewController.php::show()`.

- `FilterProvider` constructs `taskLexer` (`LexerBuilder`) with a long list of filter types (project, column, swimlane, assignee, due date, etc.).  
  **Evidence:** `app/ServiceProvider/FilterProvider.php` (definition of `$container['taskLexer']` and added filters).

- `LexerBuilder` tokenizes and applies each filter to the query builder.  
  **Evidence:** `app/Core/Filter/LexerBuilder.php::build()`; `app/Core/Filter/LexerBuilder.php::applyFilter()`.

**Reuse idea for ops console:** a lightweight, composable filter DSL is a strong “operator UX” win (fast narrowing without complex UI).  
**Evidence:** `app/ServiceProvider/FilterProvider.php` (rich filter set); `app/Core/Filter/LexerBuilder.php::applyFilter()` (operator expression handling).

---

### 3.4 Interaction model: drag/drop, quick actions, tooltips

#### Drag/drop persistence
- Board AJAX save endpoint calls `taskPositionModel->movePosition(...)` after permission checks.  
  **Evidence:** `app/Controller/BoardAjaxController.php::save()`; `app/Model/TaskPositionModel.php::movePosition()`.

- Permissions are enforced at the action boundary: `BoardAjaxController::save()` calls `helper->projectRole->canMoveTask(...)`.  
  **Evidence:** `app/Controller/BoardAjaxController.php::save()`; `app/Helper/ProjectRoleHelper.php::canMoveTask()`.

#### Quick actions: task dropdown
- The task dropdown is essentially an “operator action palette” (assign to me, move/duplicate, comment, attach, close/open, etc.) with many plugin hook points.  
  **Evidence:** `app/Template/task/dropdown.php` (actions + multiple `$this->hook->render(...)` anchors like `'template:task:dropdown:...`).

#### Tooltips as micro-views
- Tooltip content is served by a dedicated controller that returns HTML templates for different task details (subtasks, deps, tags, etc.).  
  **Evidence:** `app/Controller/BoardTooltipController.php::subtasks()` / `::dependencies()` / `::comments()` etc.

- Dependencies tooltip is powered by internal links grouped by label (e.g., “blocks”, “is blocked by”).  
  **Evidence:** `app/Controller/BoardTooltipController.php::dependencies()`; `app/Model/TaskLinkModel.php::getAllGroupedByLabel()`; `app/Schema/Sqlite.php::version_45()` (default `links` include `'blocks'` and `'is blocked by'`).

---

### 3.5 Performance: what Kanboard does (and what it doesn’t)

#### What it does
- **Avoid unnecessary reloads** using a `check` endpoint that returns `304 Not Modified` when the project hasn’t changed since a timestamp.  
  **Evidence:** `app/Controller/BoardAjaxController.php::check()`; `app/Model/ProjectModel.php::isModifiedSince()`.

- **Ensure last_modified stays accurate** by updating it on many task/subtask events.  
  **Evidence:** `app/Subscriber/ProjectModificationDateSubscriber.php::getSubscribedEvents()`; `app/Subscriber/ProjectModificationDateSubscriber.php::execute()`; `app/Model/ProjectModel.php::updateModificationDate()`.

- **Reduce “permission check overhead”** using in-memory caching for ACL decisions.  
  **Evidence:** `app/Helper/UserHelper.php::hasAccess()` / `::hasProjectAccess()` (uses `memoryCache`).

#### What it doesn’t (scaling risk)
- Board queries pull **all open tasks** for the project into memory and then partition into columns/swimlanes (no pagination at board level).  
  **Evidence:** `app/Formatter/BoardFormatter.php::format()` (calls `$this->query->findAll()` after filtering to open tasks).

- The “extended task query” includes multiple per-row subqueries for counts (subtasks/comments/files/links), which is convenient but can become heavy at scale.  
  **Evidence:** `app/Model/TaskFinderModel.php::getExtendedQuery()` (adds multiple `subquery(...)` calls).

---

## 4) Automation/Actions/Plugins

### 4.1 Automatic actions: the core pattern
Kanboard’s **automatic actions** are:
- **code-defined action classes**,
- **configured per project in DB**, and
- **attached to events at bootstrap**.

**Evidence:** `app/Action/Base.php` (action contract + executor); `app/Core/Action/ActionManager.php::attachEvents()`; `app/Model/ActionModel.php::getAll()`; `app/ServiceProvider/ActionProvider.php::register()`.

---

### 4.2 Automatic action contract (what you implement)
Every action extends `Kanboard\Action\Base` and typically defines:

- `getCompatibleEvents()` — event names this action can run on  
- `getActionRequiredParameters()` — user-configured parameters  
- `getEventRequiredParameters()` — required event payload keys  
- `hasRequiredCondition()` — a guard predicate  
- `doAction()` — side-effect  
- Base `execute()` — idempotence guard + `isExecutable` logic.  
**Evidence:** `app/Action/Base.php::execute()`; `app/Action/Base.php::isExecutable()`; `app/Action/Base.php::hasRequiredParameters()`.

**Guardrails worth copying:**
- **In-process idempotence:** action uses `md5(serialize($data).$eventName)` call-stack to avoid double-execution in a single request/worker context.  
  **Evidence:** `app/Action/Base.php::execute()`.

- **Explicit event compatibility + required payload keys** before executing.  
  **Evidence:** `app/Action/Base.php::isExecutable()`; `app/Action/Base.php::hasRequiredParameters()`.

---

### 4.3 Action attachment model (how config meets events)
`ActionManager::attachEvents()`:

1) Reads all configured actions from DB (`ActionModel::getAll()`).
2) Reads parameters from `ActionParameterModel::getAllByActions()`.
3) Clones a registered action instance, sets actionId/projectId/params.
4) Adds a listener for `event_name` to the dispatcher that calls `action->execute($event, $eventName)`.  
**Evidence:** `app/Core/Action/ActionManager.php::attachEvents()`; `app/Model/ActionModel.php::getAll()`; `app/Model/ActionParameterModel.php::getAllByActions()`.

This is a clean, small “rule engine” pattern: **events are the trigger**, **DB row is the configuration**, **code is the executor**.  
**Evidence:** `app/Core/Action/ActionManager.php::attachEvents()`.

---

### 4.4 Concrete action examples (patterns we can reuse)

#### “Time-based guardrails” action (stale/no activity)
Close tasks with no activity in a given column on daily cronjob:

- Compatible event: `TaskModel::EVENT_DAILY_CRONJOB`
- Params: `duration`, `column_id`
- Condition: `count(tasks) > 0`
- Side-effect: loop tasks, close those stale + in column  
**Evidence:** `app/Action/TaskCloseNoActivityColumn.php::getCompatibleEvents()`; `::getActionRequiredParameters()`; `::doAction()`; `::hasRequiredCondition()`.

#### “Transition-triggered computed field” action
Set due date when moving away from a specific column:

- Event: `TaskModel::EVENT_MOVE_COLUMN`
- Condition depends on `src_column_id`
- Side-effect uses `taskModificationModel->update(..., false)` to avoid firing further task events (loop prevention).  
**Evidence:** `app/Action/TaskAssignDueDateOnMoveColumn.php::getCompatibleEvents()`; `::getEventRequiredParameters()`; `::hasRequiredCondition()`; `::doAction()`; `app/Model/TaskModificationModel.php::update()` (`$fire_events` flag).

---

### 4.5 Plugin system: “full trust” in-process extension
Kanboard plugins are loaded from `PLUGINS_DIR`, mapped to namespace `Kanboard\Plugin\*`, and a plugin is expected to expose `\Kanboard\Plugin\<Name>\Plugin` extending `Core\Plugin\Base`.  
**Evidence:** `app/Core/Plugin/Loader.php::scan()` (PSR-4 mapping + class resolution); `app/Core/Plugin/Base.php` (plugin base class).

Notable design points:
- **Version compatibility check** before loading plugin.  
  **Evidence:** `app/Core/Plugin/Loader.php::initialize()` (calls `Version::isCompatible(...)`).

- **Optional schema handler** per plugin.  
  **Evidence:** `app/Core/Plugin/Loader.php::initialize()` (instantiates `SchemaHandler` and calls `->updateSchema()` when file exists).

- **Startup hook:** if plugin defines `onStartup()`, loader registers it on `'app.bootstrap'`.  
  **Evidence:** `app/Core/Plugin/Loader.php::initialize()` (adds listener on `'app.bootstrap'`).

- **DI integration:** plugin can contribute classes/helpers to the container.  
  **Evidence:** `app/Core/Plugin/Loader.php::initialize()` (calls `Tool::buildDIC(...)` and `Tool::buildDICHelpers(...)` with plugin `getClasses()` / `getHelpers()`).

---

### 4.6 UI extension hooks (lightweight + pragmatic)
Kanboard uses named “hook points” in templates:

- Board column header dropdown + header:  
  **Evidence:** `app/Template/board/table_column.php` (hook renders `'template:board:column:dropdown'`, `'template:board:column:header'`, `'template:board:column:before-header-row'`, `'template:board:column:after-header-row'`).

- Task dropdown:  
  **Evidence:** `app/Template/task/dropdown.php` (many `'template:task:dropdown:*'` hook renders).

Hook implementation:
- Hooks are named strings → list of listeners → templates rendered with a unified helper.  
  **Evidence:** `app/Helper/HookHelper.php::attach()`; `app/Helper/HookHelper.php::render()`; `app/Core/Plugin/Hook.php::on()` / `::getListeners()`.

This is the simplest “plugin UI slots” system that still scales.  
**Evidence:** `app/Helper/HookHelper.php::render()` (template binding + iteration).

---

### 4.7 How to map this to our “guardrailed auto-actions”
What to copy directly (conceptually):
- **Action contract**: `compatibleEvents`, `requiredParams`, `requiredPayloadKeys`, `condition`, `doAction`.  
  **Evidence:** `app/Action/Base.php` (contract + execution flow).

- **Attach actions at bootstrap** so the system is consistent in both web requests and background jobs.  
  **Evidence:** `app/Subscriber/BootstrapSubscriber.php::execute()` (calls `$this->actionManager->attachEvents()`); `app/Core/Queue/JobHandler.php::prepareJobEnvironment()` (dispatches `'app.bootstrap'` after `actionManager->removeEvents()`).

What we likely *must* adapt (because our runs are immutable + sandbox needs):
- Kanboard actions are **in-process PHP**; our platform likely needs **sandboxed code execution** and stricter capability boundaries.  
  **Evidence:** `app/Core/Plugin/Loader.php::initialize()` (instantiates arbitrary plugin class + calls `$plugin->initialize()` each request).

---

## 5) Permissions & Audit/History

### 5.1 Permission model: two layers of ACL

#### Layer A: Application-wide roles + controller/action ACL map
- Roles: `app-admin`, `app-manager`, `app-user`, `app-public` and project roles `project-manager`, `project-member`, `project-viewer`.  
  **Evidence:** `app/Core/Security/Role.php::APP_*` and `::PROJECT_*`.

- ACL is defined via `AccessMap` with default role and role hierarchy; rules map `(controller, method)` → minimal role.  
  **Evidence:** `app/Core/Security/AccessMap.php::add()` / `::getRoles()`; `app/ServiceProvider/AuthenticationProvider.php::getApplicationAccessMap()` and `::getProjectAccessMap()`.

- Authorization check is a simple membership test: `Authorization::isAllowed()`.  
  **Evidence:** `app/Core/Security/Authorization.php::isAllowed()`.

#### Layer B: Per-project roles + custom restrictions
Kanboard also has a layer of *project-specific* role restrictions:
- `ProjectRoleRestrictionModel` blocks certain capabilities (move, create, open/close, etc.).  
  **Evidence:** `app/Model/ProjectRoleRestrictionModel.php::RULE_*`.

- `ColumnRestrictionModel` allows/blocks operations per column per role.  
  **Evidence:** `app/Model/ColumnRestrictionModel.php::RULE_*`.

- Runtime enforcement is centralized in `ProjectRoleHelper`.  
  **Evidence:** `app/Helper/ProjectRoleHelper.php::canMoveTask()`; `::canCreateTask()`; `::canChangeTaskStatus()`; `::canCreateTaskInColumn()`; `::canChangeTaskStatusInColumn()`.

---

### 5.2 Enforcement in the request pipeline
- App-wide controller/action enforcement: `ApplicationAuthorizationMiddleware`.  
  **Evidence:** `app/Middleware/ApplicationAuthorizationMiddleware.php::execute()`.

- Project-level enforcement: `ProjectAuthorizationMiddleware` derives `project_id` (from `project_id` param or via `task_id` lookup) and checks project access.  
  **Evidence:** `app/Middleware/ProjectAuthorizationMiddleware.php::execute()`; `app/Model/TaskFinderModel.php::getProjectId()`.

- Authentication gate: `AuthenticationMiddleware` supports public access routes (Role::APP_PUBLIC) and redirects/401s otherwise.  
  **Evidence:** `app/Middleware/AuthenticationMiddleware.php::execute()`; `app/ServiceProvider/AuthenticationProvider.php::getApplicationAccessMap()` (public routes like `BoardViewController::readonly`).

---

### 5.3 Audit logging and activity stream
#### Project activity stream
- `ActivityStreamNotification` writes to `project_activities` via `ProjectActivityModel::createEvent()`.  
  **Evidence:** `app/Notification/ActivityStreamNotification.php::notifyProject()`; `app/Model/ProjectActivityModel.php::createEvent()`.

- Activity UI fetches and formats events, including role-aware comment visibility.  
  **Evidence:** `app/Helper/ProjectActivityHelper.php::getProjectEvents()`; `app/Formatter/ProjectActivityEventFormatter.php::format()`; `app/Formatter/ProjectActivityEventFormatter.php::isVisibleComment()`.

- Event data is JSON; formatter explicitly refuses unsafe legacy serialized records.  
  **Evidence:** `app/Formatter/ProjectActivityEventFormatter.php::getEventData()`.

#### Column transition history
- Column moves are logged in `transitions` table and include `time_spent`.  
  **Evidence:** `app/Subscriber/TransitionSubscriber.php::execute()`; `app/Model/TransitionModel.php::save()`; `app/Schema/Sqlite.php::version_55()`.

---

### 5.4 Notifications
- Notification fan-out is event-driven: `NotificationSubscriber` subscribes to task, comment, file, subtask, link events and pushes `NotificationJob`.  
  **Evidence:** `app/Subscriber/NotificationSubscriber.php::getSubscribedEvents()`; `app/Subscriber/NotificationSubscriber.php::notify()`.

- `NotificationJob` routes to:
  - per-user notifications (`UserNotificationModel::notifyUser()` / `::notifyUsers()`), and
  - per-project notifications (`ProjectNotificationModel::notifyProject()`).  
  **Evidence:** `app/Job/NotificationJob.php::execute()`.

- Notification types are registered in `NotificationProvider`:
  - user: Mail + Web
  - project: Webhook + ActivityStream  
  **Evidence:** `app/ServiceProvider/NotificationProvider.php::register()`.

- Web notifications are persisted into `user_has_unread_notifications`.  
  **Evidence:** `app/Notification/WebNotification.php::notifyUser()`; `app/Model/UserUnreadNotificationModel.php::create()`; `app/Schema/Sqlite.php::version_85()`.

---

## 6) Mapping to Our Platform

| Need | Kanboard approach | Evidence (file::identifier) | Reuse (what to copy) | Adaptation for immutable runs | Risks |
|---|---|---|---|---|---|
| Operator board with status columns | Project-scoped columns; tasks have `column_id`; board renders by columns | `app/Model/ColumnModel.php::TABLE`; `app/Formatter/BoardFormatter.php::format()`; `app/Model/TaskPositionModel.php::movePosition()` | Column = stage; clear per-stage WIP limits | Replace “move card” with “create promotion/rerun event” (card represents immutable run/artifact) | Users may expect drag/drop to mutate; need explicit “promote” semantics |
| Swimlanes | Swimlanes per project; board is matrix of swimlane×column | `app/Model/SwimlaneModel.php::getAllByStatus()`; `app/Template/board/table_tasks.php` | Swimlane = partition / tenant / service / pipeline | Decide axis: swimlane=partition, column=step or vice versa | Too many partitions can blow up vertical space |
| Quick actions on cards | Task dropdown + column dropdown bulk ops | `app/Template/task/dropdown.php`; `app/Template/board/table_column.php` | “Action palette” per card + per-column bulk ops | Actions become “promote artifact”, “rerun”, “backfill”, “acknowledge incident” | Permission complexity + accidental triggering |
| “Why blocked” on card | Internal links with “blocks/is blocked by”; deps tooltip | `app/Schema/Sqlite.php::version_45()` (links labels); `app/Controller/BoardTooltipController.php::dependencies()`; `app/Model/TaskLinkModel.php::getAllGroupedByLabel()` | Model blockers as typed edges; show blockers in tooltip | Blockers become upstream run/artifact constraints and policy checks | Need stable identifiers across immutable runs |
| Auto-actions | DB-configured actions attached to events at bootstrap | `app/Core/Action/ActionManager.php::attachEvents()`; `app/Action/Base.php::execute()`; `app/Model/ActionModel.php::TABLE` | Declarative “rule actions” with conditions | Action should emit orchestration events, not mutate runs | Surprise/automation risk if actions are not transparent |
| Notifications | Subscriber + job → user/project notification types | `app/Subscriber/NotificationSubscriber.php`; `app/Job/NotificationJob.php::execute()`; `app/ServiceProvider/NotificationProvider.php::register()` | Central fan-out via event bus | Add durable delivery + routing for oncall | Noise amplification if events too granular |
| Activity stream / audit | `project_activities` JSON events + formatter | `app/Model/ProjectActivityModel.php::createEvent()`; `app/Formatter/ProjectActivityEventFormatter.php::format()` | Append-only ops timeline with rich context | Make it immutable + schema-versioned; link to run IDs | JSON schema drift; need retention + indexing |
| Transition analytics | `transitions` table stores time spent between columns | `app/Subscriber/TransitionSubscriber.php`; `app/Model/TransitionModel.php::save()` | Time-in-state metrics | For immutable runs, compute time-in-state from events | Event completeness becomes critical |
| Role-based permissions | AccessMap + role hierarchy + per-project restrictions | `app/Core/Security/AccessMap.php`; `app/ServiceProvider/AuthenticationProvider.php::getProjectAccessMap()`; `app/Helper/ProjectRoleHelper.php::*` | Simple, inspectable ACL for small codebase | Map to RBAC for ops actions (promote/rerun/backfill) | Policy explosion if per-step/partition rules too granular |
| Plugin UI extension | Named hook points in templates; hook helper renders listeners | `app/Template/board/table_column.php` (hook calls); `app/Helper/HookHelper.php::render()` | Slot-based UI extension | Prefer declarative UI extensions or signed bundles | Kanboard plugins are full-trust (not sandboxed) |

---

## 7) Patterns to Steal vs Avoid

### 7.1 Patterns to steal (12)

1) **Formatter pipeline as a lightweight “view-model layer”**  
   - Board data is assembled and shaped via dedicated formatter classes (not in templates).  
   **Evidence:** `app/Formatter/BoardFormatter.php::format()`; `app/Formatter/BoardSwimlaneFormatter.php::format()`; `app/Formatter/BoardColumnFormatter.php::format()`.

2) **Project-level modification timestamp + 304 polling**  
   - Cheap sync strategy: `check()` returns 304 unless `projects.last_modified` advanced.  
   **Evidence:** `app/Controller/BoardAjaxController.php::check()`; `app/Model/ProjectModel.php::isModifiedSince()`.

3) **Ensure last_modified is correct via event subscribers**  
   - Subscriber updates project modification date on task events.  
   **Evidence:** `app/Subscriber/ProjectModificationDateSubscriber.php::getSubscribedEvents()`; `app/Subscriber/ProjectModificationDateSubscriber.php::execute()`.

4) **Data-* attribute “endpoint wiring” for JS**  
   - Board container encodes URLs + refresh interval in HTML attributes.  
   **Evidence:** `app/Template/board/table_container.php` (`data-check-url`, `data-reload-url`, `data-save-url`, etc.).

5) **Card micro-signals via compact icon footer**  
   - Days-in-column, blockers (links), subtasks progress, attachments, etc.  
   **Evidence:** `app/Template/board/task_footer.php` (icons + `date_moved` days).

6) **Tooltips as dedicated mini-views**  
   - Tooltip controller returns HTML partials for specific detail facets.  
   **Evidence:** `app/Controller/BoardTooltipController.php::*` (subtasks, dependencies, comments, etc.).

7) **Typed dependency edges with opposite relations**  
   - Links have `opposite_id`; tasks store symmetric edges; defaults include “blocks/is blocked by”.  
   **Evidence:** `app/Model/LinkModel.php::getOppositeLinkId()`; `app/Model/TaskLinkModel.php::create()`; `app/Schema/Sqlite.php::version_45()`.

8) **Automatic actions as event-triggered, DB-configured rules**  
   - Actions attach to events at bootstrap via `ActionManager::attachEvents`.  
   **Evidence:** `app/Subscriber/BootstrapSubscriber.php::execute()`; `app/Core/Action/ActionManager.php::attachEvents()`; `app/Model/ActionModel.php::getAll()`.

9) **Guardrails for auto-actions: required payload keys + condition**  
   - Actions declare required event payload keys and conditions before running.  
   **Evidence:** `app/Action/Base.php::hasRequiredParameters()`; `app/Action/Base.php::isExecutable()`.

10) **Loop prevention: allow “silent updates”**  
   - Some actions update tasks with `$fire_events=false` to avoid cascading loops.  
   **Evidence:** `app/Action/TaskAssignDueDateOnMoveColumn.php::doAction()`; `app/Model/TaskModificationModel.php::update()`.

11) **Simple, inspectable ACL via AccessMap**  
   - Controller/action → role mapping is explicitly defined in a single place.  
   **Evidence:** `app/ServiceProvider/AuthenticationProvider.php::getProjectAccessMap()`; `app/Core/Security/AccessMap.php::add()`.

12) **Reusable CSRF token for repeated AJAX**  
   - Board container embeds a reusable CSRF token for DnD saves.  
   **Evidence:** `app/Template/board/table_container.php` (calls `$this->app->getToken()->getReusableCSRFToken()`).

---

### 7.2 Patterns to avoid (or adapt carefully)

1) **Board loads all open tasks (no pagination/windowing)**  
   - Scaling risk on very large projects/queues.  
   **Evidence:** `app/Formatter/BoardFormatter.php::format()` (calls `$this->query->findAll()` on open tasks).

2) **Extended task query uses many subqueries per row**  
   - Great for convenience; potentially expensive for “operator scale” boards.  
   **Evidence:** `app/Model/TaskFinderModel.php::getExtendedQuery()` (multiple `subquery(...)` for counts).

3) **In-memory-only idempotence for actions**  
   - `callStack` hash prevents duplicates only in the current process/request, not across workers/retries.  
   **Evidence:** `app/Action/Base.php::execute()` (uses `$this->callStack` with `md5(serialize(...))`).

4) **Plugin execution is full-trust, in-process**  
   - Unsafe for your “sandboxed code execution” requirement unless heavily constrained.  
   **Evidence:** `app/Core/Plugin/Loader.php::initialize()` (instantiates plugin class and calls `$plugin->initialize()`).

5) **Magic DI via `__get` hides dependencies**  
   - Makes refactoring/static analysis harder vs explicit constructor injection.  
   **Evidence:** `app/Core/Base.php::__get()`.

6) **Template-level permission logic is pervasive**  
   - Templates call access checks (`hasProjectAccess`, role helper methods) directly.  
   **Evidence:** `app/Template/task/dropdown.php` (checks `$this->user->hasProjectAccess(...)` and `$this->projectRole->canChangeTaskStatus(...)`).

7) **Activity payload schema is “mostly implicit”**  
   - Stored as JSON string without explicit schema/version fields (though legacy serialization is handled).  
   **Evidence:** `app/Model/ProjectActivityModel.php::createEvent()` (stores `json_encode($data)`); `app/Formatter/ProjectActivityEventFormatter.php::getEventData()` (expects JSON).

8) **JSON-RPC API shape may not match your platform**  
   - If you prefer REST/gRPC/event APIs, this is a divergence.  
   **Evidence:** `jsonrpc.php` (executes `$container['api']->execute()`).

---

## 8) Actionable Output

### 8.1 Three UX prototypes inspired by Kanboard

#### Prototype 1 — “Partition × Step Board” (matrix board)
**Concept:** Use **swimlanes = partitions** and **columns = orchestration steps** (or vice versa, depending on which dimension is smaller). Each card represents the *latest attempt* pointer for an immutable run/partition/step tuple.

**Kanboard inspirations to copy**
- Matrix rendering of swimlane×column.  
  **Evidence:** `app/Template/board/table_tasks.php`; `app/Formatter/BoardSwimlaneFormatter.php::format()`.
- Card micro-signals + tooltip drilldowns (blockers, logs, diffs).  
  **Evidence:** `app/Template/board/task_footer.php`; `app/Controller/BoardTooltipController.php::*`.
- Action palette dropdown on each card (promote, rerun, backfill).  
  **Evidence:** `app/Template/task/dropdown.php` (action palette pattern + hook points).

**Adaptation for immutable runs**
- Drag/drop becomes **“propose transition”** (creates a new orchestration event) rather than mutating the existing run record.  
  (Kanboard equivalent is mutating `tasks.column_id` via `TaskPositionModel::movePosition()`.)  
  **Evidence for Kanboard mutability:** `app/Model/TaskPositionModel.php::movePosition()`.

---

#### Prototype 2 — “Run Queue + Incident Triage Board”
**Concept:** Columns are operational states: `Queued → Running → Failed → Needs action → Done`. Swimlanes are pipelines/services/environments. Cards are *run groups* (immutable runs aggregated by key).

**Kanboard inspirations to copy**
- Cheap “board refresh” via last_modified polling.  
  **Evidence:** `app/Controller/BoardAjaxController.php::check()`; `app/Model/ProjectModel.php::isModifiedSince()`.
- Highlight “recently changed” cards (operator attention).  
  **Evidence:** `app/Template/board/task_private.php` (adds `task-board-recent` class based on `date_modification` + `board_highlight_period`).

**Adaptation**
- “Needs action” should show *why* via explicit blockers: policy gate, missing artifact, upstream failure. Use dependency-edge tooltip model.  
  **Evidence for deps tooltip model:** `app/Controller/BoardTooltipController.php::dependencies()`; `app/Schema/Sqlite.php::version_45()`.

---

#### Prototype 3 — “Artifact Promotion Board”
**Concept:** Columns are promotion stages: `Built → Verified → Staged → Prod`. Swimlanes are services/tenants. Cards are immutable artifact versions.

**Kanboard inspirations to copy**
- Columns as state set; “move across columns” conceptually matches promotion.  
  **Evidence:** `app/Model/BoardModel.php::getDefaultColumns()` (columns-as-states); `app/Model/TaskPositionModel.php::fireEvents()` (move-column event).
- Automatic actions for guardrails: e.g., auto-mark stale, auto-trigger rerun on promotion.  
  **Evidence:** `app/Core/Action/ActionManager.php::attachEvents()`; `app/Action/Base.php::isExecutable()`.

**Adaptation**
- Promotions are *append-only* events; board reflects derived “latest stage” per artifact. (Kanboard directly mutates column.)  
  **Evidence for Kanboard mutation:** `app/Model/TaskPositionModel.php::movePosition()`.

---

### 8.2 ADR candidates

#### ADR-1: Event-driven action framework (DB-configured rules)
**Decision to consider:** Build a Kanboard-like action system:
- `Action` interface: compatible events + required params + required payload keys + condition + execute
- DB stores enabled actions + parameters per scope (project/pipeline)
- Attach actions at bootstrap to the event bus

**Kanboard evidence to anchor ADR**
- `ActionManager::attachEvents()` reads DB actions and binds them to dispatcher events.  
  **Evidence:** `app/Core/Action/ActionManager.php::attachEvents()`.
- Action guardrails + call-stack idempotence.  
  **Evidence:** `app/Action/Base.php::execute()`; `app/Action/Base.php::isExecutable()`.

**Key adaptation for us**
- Action executors must run in a **sandbox** (or as declarative policies) rather than arbitrary code.  
  **Evidence that Kanboard is full-trust (what we must change):** `app/Core/Plugin/Loader.php::initialize()`.

---

#### ADR-2: Append-only audit log (activity stream) with schema versioning
**Decision to consider:** Store a durable event stream for every operator action + automatic action effect.

**Kanboard evidence**
- Activity stream implemented via `project_activities` with JSON payload and formatter-based rendering.  
  **Evidence:** `app/Model/ProjectActivityModel.php::createEvent()`; `app/Formatter/ProjectActivityEventFormatter.php::format()`.

**Key adaptation**
- Add explicit `schema_version` and strong typing for event payloads (Kanboard handles legacy but payload schema is implicit).  
  **Evidence for implicit JSON payload:** `app/Model/ProjectActivityModel.php::createEvent()`.

---

#### ADR-3: Minimal, inspectable RBAC using “AccessMap + role hierarchy”
**Decision to consider:** Keep controller/action policy explicit and auditable in code (plus per-scope overrides).

**Kanboard evidence**
- Single-location ACL maps and hierarchy.  
  **Evidence:** `app/ServiceProvider/AuthenticationProvider.php::getApplicationAccessMap()` / `::getProjectAccessMap()`; `app/Core/Security/AccessMap.php::setRoleHierarchy()`.

**Key adaptation**
- Add resource-scoped permissions for “promote/rerun/backfill” operations.

---

#### ADR-4: UI extension hooks via named slots
**Decision to consider:** Provide a simple “slot-based UI extension” mechanism for operators and internal plugins.

**Kanboard evidence**
- Hook points in templates + hook helper renderer.  
  **Evidence:** `app/Template/board/table_column.php` (hook calls); `app/Template/task/dropdown.php` (hook calls); `app/Helper/HookHelper.php::render()`.

**Key adaptation**
- Use signed/validated extensions (or server-side feature flags) to stay safe.

---

### 8.3 Focus questions (direct answers)

#### What is the simplest board model that still scales to our partition×step grid?
A minimal scalable model is a **2D matrix**:
- one axis = the smaller cardinality dimension (usually **steps** → columns),
- the other axis = the larger dimension but grouped (usually **partitions** → swimlanes with collapsing + filtering).

Kanboard’s evidence-based analog is:
- columns define the state set, swimlanes define partitions, and tasks are placed by `(swimlane_id, column_id, position)`.  
**Evidence:** `app/Model/TaskCreationModel.php::prepare()` (sets `column_id`, `swimlane_id`, `position`); `app/Formatter/BoardSwimlaneFormatter.php::format()` (matrix shaping); `app/Template/board/table_tasks.php` (matrix render).

#### How can “automatic actions” map to event-driven orchestration without surprising users?
Copy Kanboard’s guardrails, then add transparency:
- Explicit compatible events + required payload keys + condition checks before executing.  
  **Evidence:** `app/Action/Base.php::isExecutable()`; `app/Action/Base.php::hasRequiredParameters()`; `app/Action/Base.php::execute()`.
- Actions are configured and visible in UI (DB-backed), not hidden code paths.  
  **Evidence:** `app/Core/Action/ActionManager.php::attachEvents()`; `app/Model/ActionModel.php::getAll()`; `app/Model/ActionParameterModel.php::getAllByActions()`.

Adaptation for “no surprises”:
- Provide “explain why this happened” by logging every auto-action decision into an audit stream (Kanboard does this broadly via project activity + notifications).  
  **Evidence:** `app/Notification/ActivityStreamNotification.php::notifyProject()`; `app/Model/ProjectActivityModel.php::createEvent()`.

#### What plugin boundaries are safe given our sandboxed code execution needs?
Kanboard’s plugin system is **not sandboxed** (plugins run arbitrary PHP in-process).  
**Evidence:** `app/Core/Plugin/Loader.php::initialize()` (instantiates plugin class, calls `->initialize()`, can register listeners).

Safe boundaries to adopt *conceptually* (but sandboxed):
- **UI slot extensions** (render-only, declarative) modeled after template hooks.  
  **Evidence:** `app/Helper/HookHelper.php::render()`; `app/Template/task/dropdown.php` (hook slots).
- **Declarative auto-actions** (configuration + condition language) modeled after `ActionManager` but executed in a controlled runtime.  
  **Evidence:** `app/Core/Action/ActionManager.php::attachEvents()`; `app/Action/Base.php::isExecutable()`.

---

If you want, I can also produce a **“cheat sheet” of the exact hook names** (e.g., all `template:*` slots in board/task UIs + all `model:*` hook references) so we can directly mirror the extension surface area. That list is mechanically extractable from files like `app/Template/*` and `app/Model/*` where `$this->hook->render(...)` / `$this->hook->reference(...)` appear (e.g., `app/Template/task/dropdown.php`, `app/Template/board/table_column.php`, `app/Model/TaskCreationModel.php`).
