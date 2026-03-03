# StackStorm st2 — Architecture & Pattern Extraction for Artifact-First Orchestration

**Scope + evidence notation.** This report analyzes the `st2` repository as an **event-condition-action (ECA)** reactive system plus **workflow execution**. Every StackStorm-specific claim is backed by *code evidence* in the form **⟦file/path::Identifier⟧**.

**Our platform context (explicit).** We are designing an **artifact-first, partitioned orchestration** platform where:
- Pipelines are partitioned; artifacts are immutable; **active(d,p)→v** with **promotion gates**.
- Runs are immutable; **staleness detection**; **rerun/backfill**.
- Task code can spawn/execute child tasks with **guardrails**.
- Need **policy controls**, **rate limiting**, **circuit breakers**, and **audit-grade event logs**.

---

## 1) Repo Map & Deployment Topology

### 1.1 Repo map (what lives where)

- **HTTP APIs**
  - `st2api/` — main REST API service, starts an eventlet WSGI server and serves `st2api.app.setup_app()`. ⟦st2api/st2api/cmd/api.py::main⟧ ⟦st2api/st2api/app.py::setup_app⟧  
  - `st2auth/` — auth service for token issuance/validation, also eventlet WSGI. ⟦st2auth/st2auth/cmd/api.py::main⟧ ⟦st2auth/st2auth/app.py::setup_app⟧  
  - `st2stream/` — streaming API service (WSGI) for event streaming, with explicit shutdown behavior for long-running stream requests. ⟦st2stream/st2stream/cmd/api.py::main⟧ ⟦st2stream/st2stream/app.py::setup_app⟧  

- **Reactor (event ingestion + rules)**
  - `st2reactor/` — sensor containers, rules engine, timers engine, garbage collector. ⟦st2reactor/st2reactor/cmd/sensormanager.py::main⟧ ⟦st2reactor/st2reactor/cmd/rulesengine.py::main⟧ ⟦st2reactor/st2reactor/cmd/timersengine.py::main⟧ ⟦st2reactor/st2reactor/cmd/garbagecollector.py::main⟧  

- **Actions + workflow execution**
  - `st2actions/` — scheduler, action runner, workflow engine, notifier. ⟦st2actions/st2actions/cmd/scheduler.py::main⟧ ⟦st2actions/st2actions/cmd/actionrunner.py::main⟧ ⟦st2actions/st2actions/cmd/workflow_engine.py::main⟧ ⟦st2actions/st2actions/cmd/st2notifier.py::main⟧  

- **Shared core**
  - `st2common/` — transport (AMQP via kombu), persistence (Mongo via mongoengine), RBAC types/models, policies engine, metrics, trace model, content/packs bootstrapping. ⟦st2common/st2common/transport/utils.py::get_connection⟧ ⟦st2common/st2common/persistence/db_init.py::db_setup_with_retry⟧ ⟦st2common/st2common/models/db/trace.py::TraceDB⟧ ⟦st2common/st2common/bootstrap/base.py::ResourceRegistrar⟧  

- **Runner implementations (plugins)**
  - `contrib/runners/` — runner plugins including `orquesta_runner`, `inquirer_runner`, `python_runner`, etc. ⟦contrib/runners/orquesta_runner/orquesta_runner/orquesta_runner.py::OrquestaRunner⟧ ⟦contrib/runners/inquirer_runner/inquirer_runner/inquirer_runner.py::Inquirer⟧ ⟦contrib/runners/python_runner/python_runner/python_action_wrapper.py::PythonActionWrapper⟧  

### 1.2 External dependencies implied by code

- **MongoDB** (via mongoengine) for persistence: executions, trigger instances, workflow state, RBAC models, etc. ⟦st2common/st2common/persistence/db_init.py::db_setup_with_retry⟧ ⟦st2common/st2common/models/db/execution.py::ActionExecutionDB⟧  
- **AMQP broker (default `amqp://...`)** via kombu. The default messaging URL is `amqp://guest:guest@127.0.0.1:5672//` in config options. ⟦st2common/st2common/config.py::messaging_opts⟧ ⟦st2common/st2common/transport/utils.py::get_messaging_urls⟧  
- **Eventlet** concurrency / monkey patching across services. ⟦st2common/st2common/util/monkey_patch.py::monkey_patch⟧ ⟦st2api/st2api/cmd/api.py::main⟧ ⟦st2stream/st2stream/cmd/api.py::main⟧  

### 1.3 Core services/processes (what runs in production)

- **st2api**: REST surface + controllers + router middleware. ⟦st2api/st2api/cmd/api.py::main⟧ ⟦st2common/st2common/router.py::Router.add_route⟧  
- **st2auth**: auth endpoints issuing/validating tokens. ⟦st2auth/st2auth/controllers/v1/auth.py::TokenController.post⟧ ⟦st2common/st2common/util/auth.py::validate_token⟧  
- **st2sensorcontainer**: manages + partitions sensors; spawns per-sensor subprocesses. ⟦st2reactor/st2reactor/cmd/sensormanager.py::main⟧ ⟦st2reactor/st2reactor/container/manager.py::SensorContainerManager.run⟧ ⟦st2reactor/st2reactor/container/process_container.py::ProcessSensorContainer.start_sensor_process⟧  
- **st2rulesengine**: consumes trigger instances from AMQP and evaluates rules; requests actions. ⟦st2reactor/st2reactor/rules/worker.py::TriggerInstanceDispatcher.process⟧ ⟦st2reactor/st2reactor/rules/engine.py::RulesEngine.handle_trigger_instance⟧ ⟦st2reactor/st2reactor/rules/enforcer.py::RuleEnforcer.enforce⟧  
- **st2timersengine**: schedules timer-based triggers. ⟦st2reactor/st2reactor/cmd/timersengine.py::main⟧  
- **st2scheduler**: schedules action executions (delays/concurrency), transitions to `scheduled`. ⟦st2actions/st2actions/scheduler/handler.py::ActionExecutionSchedulingQueueHandler.handle_execution_id⟧ ⟦st2actions/st2actions/scheduler/handler.py::_update_to_scheduled⟧  
- **st2actionrunner**: executes scheduled actions, handles cancel/pause/resume. ⟦st2actions/st2actions/worker.py::ActionExecutionDispatcher.process⟧ ⟦st2actions/st2actions/worker.py::_run_action⟧ ⟦st2actions/st2actions/worker.py::_cancel_action⟧  
- **st2workflowengine**: Orquesta workflow engine consuming workflow execution messages and stepping workflows. ⟦st2actions/st2actions/workflows/workflows.py::WorkflowEngine.start⟧ ⟦st2actions/st2actions/workflows/workflows.py::WorkflowExecutionHandler.handle_workflow_execution_db_message⟧  
- **st2notifier**: listens for action execution completion and dispatches internal triggers (reactive chaining). ⟦st2actions/st2actions/notifier/notifier.py::Notifier.process⟧ ⟦st2common/st2common/constants/triggers.py::INTERNAL_TRIGGER_TYPES⟧  
- **st2garbagecollector**: cancels/purges orphaned workflows and old executions. ⟦st2reactor/st2reactor/cmd/garbagecollector.py::main⟧ ⟦st2common/st2common/garbage_collection/executions.py::purge_orphaned_workflow_executions⟧  

### 1.4 Mermaid: service interaction diagram

```mermaid
flowchart LR
  %% External
  Client[Client / st2client] -->|REST| API[st2api]
  Client -->|REST| Auth[st2auth]
  WebhookCaller[External webhook caller] -->|HTTP POST /webhooks/*| API

  %% Persistence + Bus
  Mongo[(MongoDB)]
  MQ[(AMQP via kombu)]

  %% Reactor
  SensorC[st2sensorcontainer\nSensorContainerManager]
  Rules[st2rulesengine]
  Timers[st2timersengine]
  GC[st2garbagecollector]

  %% Actions
  Sched[st2scheduler]
  Runner[st2actionrunner]
  WFEngine[st2workflowengine]
  Notifier[st2notifier]

  %% Stream
  Stream[st2stream]

  %% DB wiring
  API --> Mongo
  Auth --> Mongo
  Rules --> Mongo
  Sched --> Mongo
  Runner --> Mongo
  WFEngine --> Mongo
  GC --> Mongo

  %% MQ wiring (named exchanges/queues implied by st2common/transport)
  SensorC -->|publish trigger_instance| MQ
  Timers -->|publish trigger_instance| MQ
  MQ -->|RULESENGINE_WORK_QUEUE| Rules

  Rules -->|publish liveaction:create + status=requested| MQ
  MQ -->|ACTIONSCHEDULER_REQUEST_QUEUE (status=requested)| Sched

  Sched -->|publish liveaction.status=scheduled| MQ
  MQ -->|ACTIONRUNNER_WORK_QUEUE (status=scheduled)| Runner

  Runner -->|publish execution updates| MQ
  MQ -->|NOTIFIER_ACTIONUPDATE_WORK_QUEUE| Notifier
  Notifier -->|dispatch internal triggers| MQ
  MQ --> Stream
```

Evidence for the “named exchanges/queues” and their bindings:
- Trigger instance exchange + dispatcher: ⟦st2common/st2common/transport/reactor.py::TRIGGER_INSTANCE_XCHG⟧ ⟦st2common/st2common/transport/reactor.py::TriggerDispatcher.dispatch⟧  
- Rules engine queue: ⟦st2common/st2common/transport/queues.py::RULESENGINE_WORK_QUEUE⟧  
- LiveAction exchanges: ⟦st2common/st2common/transport/liveaction.py::LIVEACTION_XCHG⟧ ⟦st2common/st2common/transport/liveaction.py::LIVEACTION_STATUS_MGMT_XCHG⟧  
- Scheduler + runner queues: ⟦st2common/st2common/transport/queues.py::ACTIONSCHEDULER_REQUEST_QUEUE⟧ ⟦st2common/st2common/transport/queues.py::ACTIONRUNNER_WORK_QUEUE⟧  
- Notifier queue: ⟦st2common/st2common/transport/queues.py::NOTIFIER_ACTIONUPDATE_WORK_QUEUE⟧  

---

## 2) Formal Model: Reactive Automation

### 2.1 Formal definitions

Let:
- **E** be the set of events (trigger occurrences), represented concretely as `TriggerInstanceDB`. ⟦st2common/st2common/models/db/trigger.py::TriggerInstanceDB⟧  
- **C** be the set of conditions/criteria (predicates over event payload + context), represented as `RuleDB.criteria` and evaluated by `RuleFilter`. ⟦st2common/st2common/models/db/rule.py::RuleDB⟧ ⟦st2reactor/st2reactor/rules/filter.py::RuleFilter.filter⟧  
- **A** be the set of actions to enqueue (StackStorm “actions” including workflows), represented by `RuleDB.action` and invoked by `RuleEnforcer` via `action_service.request`. ⟦st2common/st2common/models/db/rule.py::RuleDB⟧ ⟦st2reactor/st2reactor/rules/enforcer.py::RuleEnforcer._invoke_action⟧ ⟦st2common/st2common/services/action.py::request⟧  

A rule is a function:

\\[
r: E \\times \\text{Context} \\rightarrow \\{\\text{fire}, \\text{no-fire}\\}
\\]

In StackStorm terms:
- `RuleMatcher.get_matching_rules()` selects candidate rules by trigger reference. ⟦st2reactor/st2reactor/rules/matcher.py::RuleMatcher.get_matching_rules⟧  
- `RuleFilter.filter()` evaluates criteria to decide fire/no-fire and builds a context for action parameters. ⟦st2reactor/st2reactor/rules/filter.py::RuleFilter.filter⟧  

### 2.2 Reactive transition function

Define an automation transition:

\\[
(\\sigma, e) \\rightarrow (\\sigma', Q)
\\]

Where:
- \\(\\sigma\\) is persisted system state (MongoDB collections: triggers, rules, executions, traces, workflow state). ⟦st2common/st2common/persistence/db_init.py::db_setup_with_retry⟧ ⟦st2common/st2common/models/db/execution.py::ActionExecutionDB⟧ ⟦st2common/st2common/models/db/workflow.py::WorkflowExecutionDB⟧  
- \\(Q\\) is the set of “enqueued” actions (materialized as `LiveActionDB` / `ActionExecutionDB` plus AMQP publications). ⟦st2common/st2common/services/action.py::request⟧ ⟦st2common/st2common/persistence/base.py::Access.publish_create⟧  

**Where this is implemented (end-to-end):**
1. AMQP message is consumed and converted into a persisted `TriggerInstanceDB` record (state update). ⟦st2reactor/st2reactor/rules/worker.py::TriggerInstanceDispatcher.pre_ack_process⟧ ⟦st2reactor/st2reactor/container/utils.py::create_trigger_instance⟧  
2. `RulesEngine.handle_trigger_instance()` matches rules and calls `RuleEnforcer.enforce()` for those that fire. ⟦st2reactor/st2reactor/rules/engine.py::RulesEngine.handle_trigger_instance⟧ ⟦st2reactor/st2reactor/rules/enforcer.py::RuleEnforcer.enforce⟧  
3. `RuleEnforcer._invoke_action()` calls `action_service.request()`, creating `LiveActionDB`/`ActionExecutionDB` and publishing to queues (enqueue). ⟦st2reactor/st2reactor/rules/enforcer.py::RuleEnforcer._invoke_action⟧ ⟦st2common/st2common/services/action.py::request⟧ ⟦st2common/st2common/services/action.py::publish_request⟧  

---

## 3) Event Ingestion & Sensors

### 3.1 How sensors are authored (developer model)

- Sensors subclass `Sensor` (or `PollingSensor`) and implement `setup()`, `run()`, `cleanup()`, plus trigger lifecycle hooks (`add_trigger`, `update_trigger`, `remove_trigger`). ⟦st2reactor/st2reactor/sensor/base.py::Sensor⟧ ⟦st2reactor/st2reactor/sensor/base.py::PollingSensor⟧  
- Sensor metadata (YAML) declares `class_name`, `entry_point`, and `trigger_types` with `payload_schema`. This is converted into `SensorTypeDB` and `TriggerTypeDB` at registration time. ⟦contrib/examples/sensors/sample_sensor.yaml::(YAML fields)⟧ ⟦st2common/st2common/bootstrap/sensorsregistrar.py::SensorsRegistrar._register_resource⟧ ⟦st2common/st2common/bootstrap/triggersregistrar.py::TriggersRegistrar.register_from_pack⟧  

### 3.2 How sensors are run (runtime model)

- `st2sensorcontainer` is a **manager** that partitions sensors across container instances and supervises them. ⟦st2reactor/st2reactor/cmd/sensormanager.py::main⟧ ⟦st2reactor/st2reactor/container/manager.py::SensorContainerManager.run⟧  
- Partitioning uses a hash partitioner: a sensor ref is hashed and mapped into `[0,1)` ranges assigned to container IDs (horizontal scaling). ⟦st2reactor/st2reactor/container/hash_partitioner.py::HashPartitioner.get_partition_for_item⟧  
- Each sensor is run in its own subprocess (greenlets only in parent), with **pack-specific Python** (virtualenv) and a **temporary service token** exported via env vars. ⟦st2reactor/st2reactor/container/process_container.py::ProcessSensorContainer.spawn_sensor_process⟧ ⟦st2reactor/st2reactor/container/process_container.py::ProcessSensorContainer.start_sensor_process⟧  

### 3.3 How a sensor emits events (trigger instances)

- Sensors dispatch trigger instances via a `SensorService.dispatch()` helper which routes through `TriggerDispatcherService.dispatch_with_context()`. ⟦st2reactor/st2reactor/container/sensor_wrapper.py::SensorService.dispatch⟧ ⟦st2common/st2common/services/trigger_dispatcher.py::TriggerDispatcherService.dispatch_with_context⟧  
- Trigger payloads can be validated against `payload_schema`; validation may be disabled by config (`system.validate_trigger_payload`). ⟦st2common/st2common/services/trigger_dispatcher.py::TriggerDispatcherService._validate_payload⟧ ⟦st2common/st2common/validators/api/reactor.py::validate_trigger_payload⟧  

### 3.4 Delivery semantics (at-least-once? ordering? dedup?)

**Acknowledgement semantics (critical):**
- Queue consumers **always acknowledge messages in `finally:`**, even if handler raises. This is true for both `QueueConsumer.process()` and `StagedQueueConsumer.process()`. ⟦st2common/st2common/transport/consumers.py::QueueConsumer.process⟧ ⟦st2common/st2common/transport/consumers.py::StagedQueueConsumer.process⟧  
- Therefore, the AMQP consumption path is **not “retry by redelivery on failure”**; failures after message receipt won’t trigger broker redelivery from these consumers. ⟦st2common/st2common/transport/consumers.py::StagedQueueConsumer.process⟧  

**Mitigation pattern StackStorm uses: staged persistence**
- The rules engine uses `TriggerInstanceDispatcher` which persists a `TriggerInstanceDB` *before* “post-ack” processing, via `pre_ack_process()`. ⟦st2reactor/st2reactor/rules/worker.py::TriggerInstanceDispatcher.pre_ack_process⟧ ⟦st2reactor/st2reactor/container/utils.py::create_trigger_instance⟧  
- This enables **manual/explicit re-fire** of a stored trigger instance ID via `trigger_re_fire`. ⟦st2reactor/st2reactor/cmd/trigger_re_fire.py::main⟧ ⟦st2reactor/st2reactor/cmd/trigger_re_fire.py::_refire_trigger_instance⟧  

**Ordering**
- Consumers set `prefetch_count=1`, meaning a consumer will fetch one message at a time (helps per-consumer fairness), but ordering across multiple consumers/workers is not globally guaranteed. ⟦st2common/st2common/transport/consumers.py::StagedQueueConsumer.get_consumers⟧  

**Dedup**
- Trigger instance creation is a straight insert of a new `TriggerInstanceDB` record; there is no check in `create_trigger_instance()` to collapse duplicates. ⟦st2reactor/st2reactor/container/utils.py::create_trigger_instance⟧ ⟦st2common/st2common/persistence/trigger.py::TriggerInstance.add⟧  
  *Implication for our platform:* if we require at-least-once delivery, we must design idempotency/dedup (e.g., event IDs) at the artifact event layer.

### 3.5 Mapping to our event: `artifact.promoted(d,p,v)`

**StackStorm-equivalent shape:** treat `artifact.promoted(d,p,v)` as a TriggerType + TriggerInstance payload.

- TriggerType definition belongs in a sensor metadata `trigger_types` block with a `payload_schema` (just like the example sensor). ⟦contrib/examples/sensors/sample_sensor.yaml::trigger_types⟧ ⟦st2common/st2common/bootstrap/sensorsregistrar.py::SensorsRegistrar._register_resource⟧  
- A sensor would dispatch:
  - `trigger`: e.g. `artifact.promoted`
  - `payload`: `{ "dataset": d, "partition": p, "version": v, ... }`  
  via `SensorService.dispatch()` → `TriggerDispatcherService.dispatch_with_context()`. ⟦st2reactor/st2reactor/container/sensor_wrapper.py::SensorService.dispatch⟧ ⟦st2common/st2common/services/trigger_dispatcher.py::TriggerDispatcherService.dispatch_with_context⟧  

**Two implementation paths (both native to st2 patterns):**
1. **Sensor pattern (pull or subscribe)** — implement a pack sensor that subscribes to promotion events (your internal bus / DB change stream) and emits the trigger instance. This matches the standard sensor execution model (subprocess + pack venv). ⟦st2reactor/st2reactor/container/process_container.py::ProcessSensorContainer.start_sensor_process⟧  
2. **Webhook pattern (push)** — use StackStorm’s webhook controller to accept promotion callbacks and dispatch triggers with trace-tag support. ⟦st2api/st2api/controllers/v1/webhooks.py::WebhooksController.post⟧ ⟦st2api/st2api/controllers/v1/webhooks.py::WebhooksController._create_trace_context⟧  

**Relevance to our artifact-first orchestration**
- We can use `trace_tag` (or equivalent) to bind `artifact.promoted(d,p,v)` to a full run graph (promotion → eligibility computation → downstream tasks). StackStorm supports trace context propagation through trigger dispatch and rule enforcement. ⟦st2common/st2common/transport/reactor.py::TriggerDispatcher.dispatch⟧ ⟦st2reactor/st2reactor/rules/enforcer.py::RuleEnforcer._invoke_action⟧ ⟦st2common/st2common/models/db/trace.py::TraceDB⟧  

---

## 4) Rules Engine & Workflows

### 4.1 Rule evaluation and action enqueueing

**Rule data model**
- A rule binds a `trigger` ref string to an `action` dict and `criteria` dict; it also has `enabled` flag. ⟦st2common/st2common/models/db/rule.py::RuleDB⟧  

**Rule matching + filtering**
- Candidate selection: `RuleMatcher.get_matching_rules(trigger_instance)` returns rules for the trigger ref and runs `RuleFilter` checks. ⟦st2reactor/st2reactor/rules/matcher.py::RuleMatcher.get_matching_rules⟧  
- Criteria evaluation + context construction: `RuleFilter.filter()` checks rule criteria and sets `self.context` used for parameter rendering. ⟦st2reactor/st2reactor/rules/filter.py::RuleFilter.filter⟧  

**Enforcement**
- `RulesEngine.handle_trigger_instance()` loops rules and calls `RuleEnforcer.enforce()`; it also updates trigger instance status at end. ⟦st2reactor/st2reactor/rules/engine.py::RulesEngine.handle_trigger_instance⟧  
- `RuleEnforcer._invoke_action()` calls `action_service.request()` to create `LiveActionDB` and corresponding execution, and publishes request messages. ⟦st2reactor/st2reactor/rules/enforcer.py::RuleEnforcer._invoke_action⟧ ⟦st2common/st2common/services/action.py::request⟧ ⟦st2common/st2common/services/action.py::publish_request⟧  

### 4.2 Workflow support: Orquesta

StackStorm in this repo supports workflows via **Orquesta**, with both:
- an **Orquesta runner** (a runner plugin that starts/resumes/cancels workflow executions), and  
- a **workflow engine service** (`st2workflowengine`) that steps workflow state.

**Runner: OrquestaRunner**
- Reads the workflow definition file (from action `entry_point`), decides whether this is initial run vs rerun, and calls `workflow_service.request()` / `request_rerun()`. ⟦contrib/runners/orquesta_runner/orquesta_runner/orquesta_runner.py::OrquestaRunner.run⟧ ⟦st2common/st2common/services/workflows.py::request⟧ ⟦st2common/st2common/services/workflows.py::request_rerun⟧  
- Propagates pause/resume/cancel to child workflow executions recorded in `execution.children`. ⟦contrib/runners/orquesta_runner/orquesta_runner/orquesta_runner.py::OrquestaRunner.pause⟧ ⟦contrib/runners/orquesta_runner/orquesta_runner/orquesta_runner.py::OrquestaRunner.resume⟧ ⟦contrib/runners/orquesta_runner/orquesta_runner/orquesta_runner.py::OrquestaRunner.cancel⟧  
- Workflow action executions track `parent` and `children` relationships at the execution record level. ⟦st2common/st2common/models/db/execution.py::ActionExecutionDB.parent⟧ ⟦st2common/st2common/models/db/execution.py::ActionExecutionDB.children⟧  

**Workflow engine: message-driven stepper**
- Consumes workflow execution “create/resume” and action-execution-update messages from workflow queues. ⟦st2actions/st2actions/workflows/workflows.py::WORKFLOW_EXECUTION_QUEUES⟧ ⟦st2actions/st2actions/workflows/workflows.py::WorkflowEngine.start⟧  
- On workflow execution messages: loads `WorkflowExecutionDB` and requests next tasks. ⟦st2actions/st2actions/workflows/workflows.py::WorkflowExecutionHandler.handle_workflow_execution_db_message⟧  
- On action completion messages: correlates to workflow and continues stepping. ⟦st2actions/st2actions/workflows/workflows.py::WorkflowExecutionHandler.handle_action_execution_db_message⟧  

### 4.3 Workflow definition format

- Orquesta workflows are defined in YAML files referenced by an action with `runner_type: "orquesta"` and `entry_point: "workflows/<name>.yaml"`. ⟦contrib/examples/actions/orquesta-basic.yaml::runner_type⟧ ⟦contrib/examples/actions/orquesta-basic.yaml::entry_point⟧  
- A workflow spec contains `version`, `input`, `tasks`, transitions (`next`), `publish`, and `output`. ⟦contrib/examples/actions/workflows/orquesta-basic.yaml::tasks⟧  

### 4.4 Durable state persistence

- Workflow executions persist:
  - `spec`, `graph`, `context`, `state`, `status`, timestamps in `WorkflowExecutionDB`. ⟦st2common/st2common/models/db/workflow.py::WorkflowExecutionDB⟧  
  - task-level execution state in `TaskExecutionDB` including `items_count` and `items_concurrency`. ⟦st2common/st2common/models/db/workflow.py::TaskExecutionDB⟧  
- The workflow service creates and publishes workflow execution records as part of `workflow_service.request()`. ⟦st2common/st2common/services/workflows.py::request⟧  
- Workflow execution records are also published over AMQP (`WorkflowExecution.publish_*`). ⟦st2common/st2common/persistence/workflow.py::WorkflowExecution.publish_create⟧ ⟦st2common/st2common/transport/workflow.py::WORKFLOW_EXECUTION_XCHG⟧  

### 4.5 Child workflow semantics

- “Subworkflow” is simply an Orquesta task that calls another Orquesta action (runner). ⟦contrib/examples/actions/workflows/orquesta-subworkflow.yaml::tasks⟧  
- Parent/child linkage is materialized in execution records (`ActionExecutionDB.children`) and honored by OrquestaRunner’s pause/resume/cancel propagation. ⟦st2common/st2common/models/db/execution.py::ActionExecutionDB.children⟧ ⟦contrib/runners/orquesta_runner/orquesta_runner/orquesta_runner.py::OrquestaRunner.cancel⟧  

### 4.6 Retries and timeouts

- Orquesta supports **task-level retries** in spec (`retry`, `delay`). ⟦contrib/examples/actions/workflows/orquesta-task-retry.yaml::retry⟧  
- StackStorm also provides an **action execution retry policy**, implemented as a post-run policy using an eventlet timer and explicitly noted as not crash-safe. ⟦st2actions/st2actions/policies/retry.py::RetryPolicy.post_run⟧  

---

## 5) Plugin/Packs Architecture (Critical)

### 5.1 Pack structure, metadata, versioning

- Pack metadata file names and layout are centralized as constants (`pack.yaml`, `config.schema.yaml`, etc). ⟦st2common/st2common/constants/pack.py::MANIFEST_FILE_NAME⟧ ⟦st2common/st2common/constants/pack.py::PACK_CONFIG_SCHEMA_FILENAME⟧  
- Packs are discovered/registered by `ResourceRegistrar.register_packs()` which reads pack metadata and persists `PackDB` (including file lists). ⟦st2common/st2common/bootstrap/base.py::ResourceRegistrar.register_packs⟧ ⟦st2common/st2common/bootstrap/base.py::ResourceRegistrar._register_pack_db⟧ ⟦st2common/st2common/models/db/pack.py::PackDB⟧  
- Pack versions are stored on `PackDB.version` and come from metadata read by `pack_utils.get_pack_metadata()`. ⟦st2common/st2common/models/db/pack.py::PackDB.version⟧ ⟦st2common/st2common/util/pack.py::get_pack_metadata⟧  

### 5.2 Content loading and registration

- `ContentPackLoader` provides filesystem traversal for pack content types (actions, sensors, rules, etc.) and supports overrides. ⟦st2common/st2common/content/loader.py::ContentPackLoader.get_content⟧  
- Registrars convert YAML -> DB models:
  - Sensors: ⟦st2common/st2common/bootstrap/sensorsregistrar.py::SensorsRegistrar._register_resource⟧  
  - Triggers from sensor metadata: ⟦st2common/st2common/bootstrap/triggersregistrar.py::TriggersRegistrar.register_from_pack⟧  
  - Actions: ⟦st2common/st2common/bootstrap/actionsregistrar.py::ActionsRegistrar._register_resource⟧  
  - Rules: ⟦st2common/st2common/bootstrap/rulesregistrar.py::RulesRegistrar.register_from_pack⟧  

### 5.3 Execution model for third-party code (safety posture)

**Isolation boundary is “process + virtualenv”, not a hard sandbox/container:**
- Sensors run in a subprocess and use per-pack python binary/venv (`get_sandbox_python_binary_path(pack)`). ⟦st2reactor/st2reactor/container/process_container.py::ProcessSensorContainer.spawn_sensor_process⟧ ⟦st2common/st2common/util/sandboxing.py::get_sandbox_python_binary_path⟧  
- Actions expose `ST2_ACTION_*` env vars including `ST2_ACTION_AUTH_TOKEN` for API access, created as temporary token by the container. ⟦st2common/st2common/runners/base.py::ActionRunner._get_common_action_env_variables⟧ ⟦st2actions/st2actions/container/base.py::RunnerContainerBase._get_action_auth_token⟧  
- Pack virtualenv creation and dependency installation is part of the system’s model (`setup_pack_virtualenv`). ⟦st2common/st2common/util/virtualenvs.py::setup_pack_virtualenv⟧  

**Validation + secret hygiene**
- Trigger payload schema validation exists (optional) for sensor/webhook dispatched triggers. ⟦st2common/st2common/validators/api/reactor.py::validate_trigger_payload⟧  
- Action parameter schema validation happens in API validator. ⟦st2common/st2common/validators/api/action.py::validate_action_parameters⟧  
- Config schema includes secret flags and `ConfigDB.mask_secrets()` masks config values. ⟦st2common/st2common/models/db/pack.py::ConfigDB.mask_secrets⟧  
- Execution records have masking for secret params/output schema (`ActionExecutionDB.mask_secrets`). ⟦st2common/st2common/models/db/execution.py::ActionExecutionDB.mask_secrets⟧  

**Filesystem safety**
- Pack file path resolution attempts to prevent traversal by enforcing “path stays under pack root”. ⟦st2common/st2common/content/utils.py::get_pack_file_abs_path⟧  

### 5.4 Pattern extraction for our “task type SDK” + connectors ecosystem

**What StackStorm gives us conceptually:**
- A “task type” is analogous to an **Action** with:
  - a runner type (execution backend)
  - an input schema
  - optional config schema
  - versioned packaging in packs  
  Evidence: action registration and schema/runner coupling. ⟦st2common/st2common/bootstrap/actionsregistrar.py::ActionsRegistrar._register_resource⟧ ⟦st2common/st2common/validators/api/action.py::validate_action_parameters⟧  

**How to adapt to our artifact-first platform**
- Treat each connector/validator/exporter as a **pack-like unit** with:
  - immutable versioned artifact (pack version, our `v`)
  - declared input schema and capability metadata
  - isolated runtime env (venv/container)  
  Evidence for pack version + venv model. ⟦st2common/st2common/models/db/pack.py::PackDB.version⟧ ⟦st2common/st2common/util/virtualenvs.py::setup_pack_virtualenv⟧  

**Safety model we should strengthen**
- StackStorm’s isolation is not a hardened sandbox; it’s best-effort process + venv + token scoping. ⟦st2reactor/st2reactor/container/process_container.py::ProcessSensorContainer.start_sensor_process⟧ ⟦st2common/st2common/runners/base.py::ActionRunner._get_common_action_env_variables⟧  

---

## 6) AuthN/AuthZ & Multi-Tenancy Boundaries

### 6.1 AuthN components

- Token issuance/validation flows through the auth controller and token utilities. ⟦st2auth/st2auth/controllers/v1/auth.py::TokenController.post⟧ ⟦st2common/st2common/util/auth.py::validate_token⟧  
- Token objects are persisted in Mongo as `TokenDB` and include expiry fields. ⟦st2common/st2common/models/db/auth.py::TokenDB⟧  

### 6.2 AuthZ / RBAC model

- RBAC core concepts:
  - `RoleDB` containing `PermissionGrantDB` entries with `resource_uid` and `permission_types`. ⟦st2common/st2common/models/db/rbac.py::RoleDB⟧ ⟦st2common/st2common/models/db/rbac.py::PermissionGrantDB⟧  
  - `PermissionType` enumerates typed permissions (including webhooks, inquiries, etc.). ⟦st2common/st2common/rbac/types.py::PermissionType⟧  
- RBAC enforcement is integrated at request routing time via `Router.add_route()` which attaches RBAC permission checks. ⟦st2common/st2common/router.py::Router.add_route⟧  
- RBAC APIs exist for managing roles and assignments with constraints (e.g., non-admin restrictions). ⟦st2api/st2api/controllers/v1/rbac.py::RolesController.post⟧ ⟦st2api/st2api/controllers/v1/rbac.py::RoleAssignmentsController.get_all⟧  

### 6.3 Multi-tenancy-ish boundaries

StackStorm is not “hard multi-tenant” at the storage layer (single DB), but it supports *soft boundaries*:

- **Per-user identity** carried in execution context (`context.user`) and indexed. ⟦st2common/st2common/models/db/execution.py::ActionExecutionDB.context⟧  
- **Datastore scope** supports system scope vs user scope semantics (`KeyValuePair.scope`). ⟦st2common/st2common/models/db/keyvalue.py::KeyValuePairDB.scope⟧ ⟦st2common/st2common/constants/keyvalue.py::USER_SCOPE_SEPARATOR⟧  
- **RBAC resource UIDs** provide resource-level partitioning for authorization. ⟦st2common/st2common/models/db/rbac.py::PermissionGrantDB.resource_uid⟧  

### 6.4 Mapping to our needs: promotion permissions + operator/admin + audit

**Dataset-level promotion permissions**
- StackStorm’s RBAC is fundamentally “permission over resource_uid”, which maps well to a resource uid like `artifact:<d>:<p>` or `promotion_gate:<d>:<p>` in our platform. ⟦st2common/st2common/models/db/rbac.py::PermissionGrantDB.resource_uid⟧  

**Operator vs admin**
- Role/role-assignment controllers explicitly differentiate behavior for admin vs non-admin (e.g., only admin can create certain roles). ⟦st2api/st2api/controllers/v1/rbac.py::RolesController.post⟧  

**Audit logging**
- StackStorm uses a dedicated `AUDIT` logging level and many components emit `LOG.audit()` with structured `extra` metadata including liveaction/execution details. ⟦st2common/st2common/log.py::AUDIT⟧ ⟦st2reactor/st2reactor/rules/enforcer.py::RuleEnforcer.enforce⟧ ⟦st2actions/st2actions/worker.py::_run_action⟧  
- For “audit-grade” event lineage, StackStorm provides a persisted trace graph (`TraceDB`) plus a trace API. ⟦st2common/st2common/models/db/trace.py::TraceDB⟧ ⟦st2api/st2api/controllers/v1/traces.py::TracesController.get_all⟧  

---

## 7) Observability & Operations

### 7.1 Logs + audit logs

- `AUDIT` is a first-class log level (`logging.addLevelName`) and filtering behavior can hide audit logs when loglevel is above INFO. ⟦st2common/st2common/log.py::AUDIT⟧ ⟦st2common/st2common/service_setup.py::setup⟧  
- Key execution points log audit events:
  - rule enforcement: ⟦st2reactor/st2reactor/rules/enforcer.py::RuleEnforcer.enforce⟧  
  - action launch/cancel/pause/resume: ⟦st2actions/st2actions/worker.py::_run_action⟧ ⟦st2actions/st2actions/worker.py::_cancel_action⟧  

### 7.2 Metrics

- Metrics are abstracted behind a pluggable driver system; code uses `CounterWithTimer` / `Timer` helpers. ⟦st2common/st2common/metrics/base.py::get_driver⟧ ⟦st2actions/st2actions/scheduler/handler.py::ActionExecutionSchedulingQueueHandler.handle_execution_id⟧ ⟦st2actions/st2actions/notifier/notifier.py::Notifier.process⟧  

### 7.3 Tracing (lineage graph)

- `TraceDB` contains references to trigger instances, rules, and executions; trace service updates trace context during rule enforcement. ⟦st2common/st2common/models/db/trace.py::TraceDB⟧ ⟦st2common/st2common/services/trace.py::TraceService.update_trigger_instance⟧ ⟦st2reactor/st2reactor/rules/enforcer.py::RuleEnforcer.enforce⟧  

### 7.4 Preventing runaway automations (limits/quotas/concurrency)

**Concurrency control (policy-driven)**
- Action concurrency policies exist (including attribute-based), and can delay/cancel scheduling when thresholds exceeded. ⟦st2actions/st2actions/policies/concurrency.py::ConcurrencyApplicator.apply_before⟧ ⟦st2actions/st2actions/policies/concurrency_by_attr.py::ConcurrencyByAttributeApplicator.apply_before⟧  
- Coordination/locking primitives exist via tooz-based coordination. ⟦st2common/st2common/services/coordination.py::CoordinatorService.get_coordinator⟧ ⟦st2common/st2common/policies/concurrency.py::ConcurrencyPolicyBase⟧  

**Scheduler queue “lease/handling”**
- Scheduling requests are persisted as `ActionExecutionSchedulingQueueItemDB` with a `handling` flag to coordinate schedulers. ⟦st2common/st2common/models/db/execution_queue.py::ActionExecutionSchedulingQueueItemDB.handling⟧  
- Scheduler code uses a lock/claim pattern (`_acquire_lock()` and setting `handling=True`) to avoid duplicate scheduling work. ⟦st2actions/st2actions/scheduler/handler.py::ActionExecutionSchedulingQueueHandler._acquire_lock⟧  

**Staleness detection / orphan cleanup**
- Workflow service can identify orphaned workflows based on idle time and task states. ⟦st2common/st2common/services/workflows.py::identify_orphaned_workflows⟧  
- Garbage collection cancels orphaned workflows accordingly. ⟦st2common/st2common/garbage_collection/executions.py::purge_orphaned_workflow_executions⟧  

**Operational circuit-breaker primitives**
- Action runner supports `canceling`, `pausing`, `resuming` dispatch paths. ⟦st2actions/st2actions/worker.py::ActionExecutionDispatcher.process⟧  
- Orquesta runner propagates pause/resume/cancel to child workflows. ⟦contrib/runners/orquesta_runner/orquesta_runner/orquesta_runner.py::OrquestaRunner.pause⟧ ⟦contrib/runners/orquesta_runner/orquesta_runner/orquesta_runner.py::OrquestaRunner.cancel⟧  

---

## 8) Mapping to Our Platform (Table)

| Our invariant | StackStorm concept | Evidence | Reuse | Adaptation | Risks |
|---|---|---|---|---|---|
| Event-driven orchestration from `artifact.promoted(d,p,v)` | TriggerType + TriggerInstance + rules engine pipeline | ⟦st2common/st2common/models/db/trigger.py::TriggerTypeDB⟧ ⟦st2common/st2common/models/db/trigger.py::TriggerInstanceDB⟧ ⟦st2reactor/st2reactor/rules/engine.py::RulesEngine.handle_trigger_instance⟧ | Strong: clear ECA pipeline | Define `artifact.promoted` as TriggerType; treat payload as immutable event | Consumers ack unconditionally; event loss unless we add dedup/replay |
| Partitioned pipelines (by dataset/partition) | Sensor partitioning + concurrency-by-attribute | ⟦st2reactor/st2reactor/container/hash_partitioner.py::HashPartitioner⟧ ⟦st2actions/st2actions/policies/concurrency_by_attr.py::ConcurrencyByAttributeApplicator⟧ | Strong conceptual fit | Hash partition key = `(d,p)`; concurrency-by-attr over `(d,p)` | Partitioning applies to sensors, not end-to-end ownership |
| Artifacts immutable; promotion gates | Inquiry runner + workflow pause | ⟦contrib/runners/inquirer_runner/inquirer_runner/inquirer_runner.py::Inquirer.run⟧ ⟦st2api/st2api/controllers/v1/inquiries.py::InquiriesController.put⟧ | Good gating pattern | Model promotion gate task as inquiry-like pending | Inquiry borrows ActionExecutionDB; may need dedicated gate model |
| Runs immutable; rerun/backfill | Execution records + explicit rerun API | ⟦st2common/st2common/models/db/execution.py::ActionExecutionDB⟧ ⟦st2api/st2api/controllers/v1/actionexecutions.py::ActionExecutionReRunController.post⟧ | Strong reuse | Implement rerun/backfill for downstream runs | Execution objects mutate status/result in place |
| Staleness detection | Orphan workflow detection + GC | ⟦st2common/st2common/services/workflows.py::identify_orphaned_workflows⟧ ⟦st2common/st2common/garbage_collection/executions.py::purge_orphaned_workflow_executions⟧ | Useful pattern | Implement partition/run staleness monitor | Needs careful invariants to avoid false cancels |
| Child tasks + guardrails | Orquesta subworkflows + parent/children | ⟦st2common/st2common/models/db/execution.py::ActionExecutionDB.children⟧ ⟦contrib/runners/orquesta_runner/orquesta_runner/orquesta_runner.py::OrquestaRunner.cancel⟧ | Good lineage | Add spawn budget policy with hard enforcement | StackStorm lacks explicit spawn budgets |
| Policy controls | Policy engine + concurrency + cancel/pause | ⟦st2common/st2common/services/policies.py::apply_pre_run_policies⟧ ⟦st2actions/st2actions/policies/concurrency.py::ConcurrencyApplicator⟧ ⟦st2actions/st2actions/worker.py::_cancel_action⟧ | Partial | Add rate limiting + circuit breakers as policies | Retry policy not crash-safe |
| Audit-grade logs | TraceDB + Trace API + AUDIT level | ⟦st2common/st2common/models/db/trace.py::TraceDB⟧ ⟦st2api/st2api/controllers/v1/traces.py::TracesController.get_all⟧ ⟦st2common/st2common/log.py::AUDIT⟧ | Strong | Treat trace graph as audit lineage | Trace propagation must be enforced |

---

## 9) Patterns to Steal vs Avoid

### 9.1 Patterns to steal (>= 10), each with evidence

1. **Centralized queue/exchange contract** — ⟦st2common/st2common/transport/queues.py::(queue constants)⟧ ⟦st2common/st2common/transport/reactor.py::TRIGGER_INSTANCE_XCHG⟧  
2. **Persist-before-process staging** — ⟦st2reactor/st2reactor/rules/worker.py::TriggerInstanceDispatcher.pre_ack_process⟧  
3. **Hash partitioning for ingestion scaling** — ⟦st2reactor/st2reactor/container/hash_partitioner.py::HashPartitioner.get_partition_for_item⟧  
4. **Per-pack virtualenv isolation** — ⟦st2common/st2common/util/virtualenvs.py::setup_pack_virtualenv⟧  
5. **Ephemeral per-execution auth tokens** — ⟦st2actions/st2actions/container/base.py::RunnerContainerBase._get_action_auth_token⟧  
6. **Policy engine hooks pre/post run** — ⟦st2common/st2common/services/policies.py::apply_pre_run_policies⟧  
7. **Concurrency-by-attribute** — ⟦st2actions/st2actions/policies/concurrency_by_attr.py::ConcurrencyByAttributeApplicator.apply_before⟧  
8. **Durable scheduler queue with claim/lease** — ⟦st2common/st2common/models/db/execution_queue.py::ActionExecutionSchedulingQueueItemDB.handling⟧  
9. **Durable workflow state + message-driven stepping** — ⟦st2common/st2common/models/db/workflow.py::WorkflowExecutionDB⟧ ⟦st2actions/st2actions/workflows/workflows.py::WorkflowExecutionHandler.handle_workflow_execution_db_message⟧  
10. **Trace graph for lineage** — ⟦st2common/st2common/models/db/trace.py::TraceDB⟧  
11. **Internal triggers from execution updates** — ⟦st2actions/st2actions/notifier/notifier.py::Notifier.process⟧ ⟦st2common/st2common/constants/triggers.py::INTERNAL_TRIGGER_TYPES⟧  
12. **Human-in-the-loop gates (Inquiry runner)** — ⟦contrib/runners/inquirer_runner/inquirer_runner/inquirer_runner.py::Inquirer.run⟧  

### 9.2 Design traps to avoid (>= 3), each with evidence

1. **Pickle on the message bus** — ⟦st2common/st2common/transport/publishers.py::PoolPublisher.publish⟧  
2. **Unconditional ACK in consumers** — ⟦st2common/st2common/transport/consumers.py::QueueConsumer.process⟧ ⟦st2common/st2common/transport/consumers.py::StagedQueueConsumer.process⟧  
3. **Retry policy not crash-safe** — ⟦st2actions/st2actions/policies/retry.py::RetryPolicy.post_run⟧  
4. **Inquiry borrows ActionExecutionDB (no dedicated gate model)** — ⟦st2api/st2api/controllers/v1/inquiries.py::InquiriesController⟧  

---

## 10) Actionable Output

### 10.1 ADR candidates (5–8)

1. **Persist-first replayable event model** — ⟦st2reactor/st2reactor/rules/worker.py::TriggerInstanceDispatcher.pre_ack_process⟧  
2. **Deterministic `(d,p)` partition ownership** — ⟦st2reactor/st2reactor/container/hash_partitioner.py::HashPartitioner.get_partition_for_item⟧  
3. **Guardrails as pre-run policies** — ⟦st2common/st2common/services/policies.py::apply_pre_run_policies⟧  
4. **Partition budgets via concurrency-by-attr** — ⟦st2actions/st2actions/policies/concurrency_by_attr.py::ConcurrencyByAttributeApplicator.apply_before⟧  
5. **Durable workflows stepped via queues** — ⟦st2actions/st2actions/workflows/workflows.py::WorkflowExecutionHandler.handle_workflow_execution_db_message⟧  
6. **Promotion gates as inquiry-like tasks** — ⟦contrib/runners/inquirer_runner/inquirer_runner/inquirer_runner.py::Inquirer.run⟧  
7. **Audit lineage as persisted trace graph** — ⟦st2common/st2common/models/db/trace.py::TraceDB⟧  

### 10.2 Three implementation spikes (with success criteria)

**Spike 1 — `artifact.promoted` sensor → eligibility computation**  
Evidence: ⟦st2reactor/st2reactor/container/sensor_wrapper.py::SensorService.dispatch⟧ ⟦st2reactor/st2reactor/rules/enforcer.py::RuleEnforcer._invoke_action⟧  
Success: N promotions ⇒ N immutable events ⇒ deterministic downstream run; idempotent on replay.

**Spike 2 — Partitioned spawn budget guardrail**  
Evidence: ⟦st2actions/st2actions/policies/concurrency_by_attr.py::ConcurrencyByAttributeApplicator.apply_before⟧ ⟦st2common/st2common/models/db/execution.py::ActionExecutionDB.children⟧  
Success: attempts to spawn beyond budget produce controlled failure + audit event; no unbounded queue growth.

**Spike 3 — Promotion gate workflow (human approval)**  
Evidence: ⟦contrib/runners/inquirer_runner/inquirer_runner/inquirer_runner.py::Inquirer.post_run⟧ ⟦st2api/st2api/controllers/v1/inquiries.py::InquiriesController.put⟧  
Success: gate enforces authorization; produces durable decision linked to run lineage.

---

### Focus questions (code-backed)

- **Delivery/consistency semantics:** Consumers ACK in `finally`; durability relies on staged DB persistence + explicit replay. ⟦st2common/st2common/transport/consumers.py::StagedQueueConsumer.process⟧ ⟦st2reactor/st2reactor/container/utils.py::create_trigger_instance⟧ ⟦st2reactor/st2reactor/cmd/trigger_re_fire.py::_refire_trigger_instance⟧  
- **Isolation/security:** process + pack virtualenv + ephemeral tokens via env vars; not a hardened sandbox. ⟦st2common/st2common/util/virtualenvs.py::setup_pack_virtualenv⟧ ⟦st2common/st2common/runners/base.py::ActionRunner._get_common_action_env_variables⟧ ⟦st2actions/st2actions/container/base.py::RunnerContainerBase._get_action_auth_token⟧  
- **Packs for task types/validators:** schema-validated, versioned units with isolated deps is a strong template; harden by avoiding pickle and adding containerization. ⟦st2common/st2common/bootstrap/base.py::ResourceRegistrar.register_packs⟧ ⟦st2common/st2common/validators/api/action.py::validate_action_parameters⟧ ⟦st2common/st2common/transport/publishers.py::PoolPublisher.publish⟧  
- **Policies/limits:** emulate pre-run hook + concurrency-by-attr; replace non-durable retry with durable scheduling; add rate limiting + circuit breakers. ⟦st2common/st2common/services/policies.py::apply_pre_run_policies⟧ ⟦st2actions/st2actions/policies/concurrency_by_attr.py::ConcurrencyByAttributeApplicator.apply_before⟧ ⟦st2actions/st2actions/policies/retry.py::RetryPolicy.post_run⟧  
