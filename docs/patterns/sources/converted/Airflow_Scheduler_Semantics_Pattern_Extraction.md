# Airflow — Scheduler Semantics Pattern Extraction

Apache Airflow — Scheduler Semantics & Pattern Extraction for Artifact-First Partitioned Orchestration

Scheduler correctness review with code-level evidence (file paths + identifiers)

Codebase: local checkout of https://github.com/apache/airflow (analyzed snapshot: Airflow 3.2.0 per project metadata).

# 1) Repo & Service Topology

Airflow is a distributed orchestration system centered on a metadata database. The scheduler and other services coordinate through database state and executor event channels.

## Scheduler

Scheduler is implemented as a JobRunner that loops: create runs, schedule runnable task instances, enqueue work, process executor events.

Evidence: airflow-core/src/airflow/jobs/scheduler_job_runner.py:SchedulerJobRunner._run_scheduler_loop; airflow-core/src/airflow/jobs/scheduler_job_runner.py:SchedulerJobRunner._create_dag_runs; airflow-core/src/airflow/jobs/scheduler_job_runner.py:SchedulerJobRunner._schedule_all_dag_runs; airflow-core/src/airflow/jobs/scheduler_job_runner.py:SchedulerJobRunner._critical_section_enqueue_task_instances; airflow-core/src/airflow/jobs/scheduler_job_runner.py:SchedulerJobRunner.process_executor_events

Scheduler reads DAG definitions from the DB via DBDagBag (not by importing DAG files directly in the scheduler loop).

Evidence: airflow-core/src/airflow/jobs/scheduler_job_runner.py:SchedulerJobRunner.__init__; airflow-core/src/airflow/models/dagbag.py:DBDagBag.get_dag_for_run

## DAG Processor (parsing/serialization)

DAG file parsing runs as a distinct job runner using DagFileProcessorManager.

Evidence: airflow-core/src/airflow/jobs/dag_processor_job_runner.py:DagProcessorJobRunner; airflow-core/src/airflow/dag_processing/manager.py:DagFileProcessorManager

Parsed DAGs are persisted as serialized structures in metadata DB (SerializedDagModel).

Evidence: airflow-core/src/airflow/models/serialized_dag.py:SerializedDagModel; airflow-core/src/airflow/models/dagbag.py:DBDagBag.get_dag_for_run

## Webserver / API

Airflow 3 uses FastAPI for the web surface; core API routers are included in the FastAPI app.

Evidence: airflow-core/src/airflow/api_fastapi/core_api/app.py:init_views

Execution API endpoints handle task instance RUNNING and terminal transitions (worker-driven).

Evidence: airflow-core/src/airflow/api_fastapi/execution_api/routes/task_instances.py:ti_run; airflow-core/src/airflow/api_fastapi/execution_api/routes/task_instances.py:ti_update_state

## Executors / Workers

Executors provide a queue_workload + heartbeat interface; scheduler enqueues workloads via executors.

Evidence: airflow-core/src/airflow/executors/base_executor.py:BaseExecutor.queue_workload; airflow-core/src/airflow/executors/base_executor.py:BaseExecutor.heartbeat; airflow-core/src/airflow/executors/workloads.py:ExecuteTask

## Triggerer (deferrable triggers)

Triggerer is a dedicated job that runs asynchronous triggers and resumes deferred tasks.

Evidence: airflow-core/src/airflow/jobs/triggerer_job_runner.py:TriggererJobRunner; airflow-core/src/airflow/api_fastapi/execution_api/routes/task_instances.py:_create_ti_state_update_query_and_update_state (DEFERRED branch)

## Metadata DB (system of record)

Core orchestration state is persisted via SQLAlchemy models: DagRun, TaskInstance, AssetEvent, Backfill, etc.

Evidence: airflow-core/src/airflow/models/dagrun.py:class DagRun; airflow-core/src/airflow/models/taskinstance.py:class TaskInstance; airflow-core/src/airflow/models/asset.py:class AssetEvent; airflow-core/src/airflow/models/backfill.py:class Backfill; airflow-core/src/airflow/utils/session.py:create_session / provide_session

# 2) Formal Model: Partitioned DAG Scheduling

Formalization for correctness reasoning and to map Airflow semantics to an artifact-first partitioned system.

Let the workflow DAG be a directed graph G=(V,E). A partition p has an explicit data interval I(p)=[s_p,e_p). A run r is an execution of G for one partition or event. A task instance is TI(v,r,p,m) where v∈V and m is a map index (fanout).

In Airflow, a TaskInstance is uniquely identified by (dag_id, task_id, run_id, map_index).

Evidence: airflow-core/src/airflow/models/taskinstance.py:TaskInstance.__table_args__ (task_instance_composite_key); airflow-core/src/airflow/models/taskinstance.py:TaskInstance.map_index

Define the scheduler decision function S = schedule(G, t, Σ, C), where t is wall-clock time, Σ is persisted state (runs, tasks, events), and C is constraints (concurrency, pools, max_active_runs). Output actions create runs, transition states, and enqueue work.

Evidence: airflow-core/src/airflow/jobs/scheduler_job_runner.py:SchedulerJobRunner._create_dag_runs; airflow-core/src/airflow/models/dagrun.py:DagRun.update_state; airflow-core/src/airflow/jobs/scheduler_job_runner.py:SchedulerJobRunner._critical_section_enqueue_task_instances

## Run state machine δ_DR

Airflow encodes DagRun transitions (including timestamp side effects) in DagRun.set_state and enumerates states in DagRunState.

Evidence: airflow-core/src/airflow/models/dagrun.py:DagRun.set_state; airflow-core/src/airflow/utils/state.py:DagRunState

## TaskInstance state machine δ_TI and retries

TaskInstance states are enumerated in TaskInstanceState. Effective transitions are multi-actor: scheduler sets SCHEDULED/QUEUED, worker (Execution API) sets RUNNING and terminal states. Retry timing is computed by ready_for_retry and next_retry_datetime with optional jitter.

Evidence: airflow-core/src/airflow/utils/state.py:TaskInstanceState; airflow-core/src/airflow/models/dagrun.py:DagRun.schedule_tis (sets SCHEDULED); airflow-core/src/airflow/jobs/scheduler_job_runner.py:SchedulerJobRunner._critical_section_enqueue_task_instances (sets QUEUED); airflow-core/src/airflow/api_fastapi/execution_api/routes/task_instances.py:ti_run (sets RUNNING); airflow-core/src/airflow/api_fastapi/execution_api/routes/task_instances.py:ti_update_state (terminal/retry/deferred); airflow-core/src/airflow/models/taskinstance.py:TaskInstance.ready_for_retry / next_retry_datetime / get_retry_delay

# 3) Data Interval / Logical Date Semantics (Critical)

Airflow’s schedule semantics are built around half-open data intervals and a logical date that represents the interval. This prevents wall-clock confusion by separating: (a) which data interval is being processed vs (b) when the run actually executes.

DataInterval is represented as [start, end) (half-open).

Evidence: airflow-core/src/airflow/timetables/base.py:DataInterval

DagRunInfo packages run_after and data_interval; logical_date is defined as data_interval.start.

Evidence: airflow-core/src/airflow/timetables/base.py:DagRunInfo; airflow-core/src/airflow/timetables/base.py:DagRunInfo.logical_date

For interval schedules, DagRunInfo.interval sets run_after=data_interval.end, i.e., run becomes eligible after interval closes.

Evidence: airflow-core/src/airflow/timetables/base.py:DagRunInfo.interval

Timetable generates the next run using next_dagrun_info; catchup is controlled via TimeRestriction.catchup.

Evidence: airflow-core/src/airflow/timetables/base.py:TimeRestriction; airflow-core/src/airflow/timetables/interval.py:CronDataIntervalTimetable.next_dagrun_info; airflow-core/src/airflow/timetables/interval.py:CronDataIntervalTimetable._skip_to_latest

DagRun stores logical_date, data_interval_start/end, run_after, and (optional) partition_key in the DB.

Evidence: airflow-core/src/airflow/models/dagrun.py:DagRun.logical_date; airflow-core/src/airflow/models/dagrun.py:DagRun.data_interval_start / data_interval_end; airflow-core/src/airflow/models/dagrun.py:DagRun.run_after; airflow-core/src/airflow/models/dagrun.py:DagRun.partition_key

Important nuance for your platform: Airflow treats partition_key runs as special in get_run_data_interval, potentially returning None for the interval. Your platform should require both a partition key and an explicit interval for every run.

Evidence: airflow-core/src/airflow/models/dag.py:DAG.get_run_data_interval

## Mapping to our platform requirements

Our partition key p: use as a primary index into UI and lineage; do not replace interval semantics.

Explicit interval: store [start,end) for every run; define logical_date = start for stable identity.

Eligibility: gate run creation on artifact promotion active(d,p)→v, not purely on time (Airflow’s run_after).

# 4) Backfill/Catchup

Airflow distinguishes automatic catchup (missed scheduled intervals) from explicit operator-driven backfill (range execution). Both are useful, but Airflow’s run mutability (clear/requeue) conflicts with immutable-run requirements.

## Catchup (automatic)

Catchup behavior is encoded in timetable logic via TimeRestriction.catchup and interval alignment/skip logic.

Evidence: airflow-core/src/airflow/timetables/base.py:TimeRestriction.catchup; airflow-core/src/airflow/timetables/interval.py:CronDataIntervalTimetable.next_dagrun_info; airflow-core/src/airflow/timetables/interval.py:CronDataIntervalTimetable._skip_to_latest

Scheduler selects DAGs needing runs using DagModel.next_dagrun_create_after and creates runs in _create_dag_runs.

Evidence: airflow-core/src/airflow/models/dag.py:DagModel.next_dagrun_create_after; airflow-core/src/airflow/models/dag.py:DagModel.dags_needing_dagruns; airflow-core/src/airflow/jobs/scheduler_job_runner.py:SchedulerJobRunner._create_dag_runs; airflow-core/src/airflow/models/dag.py:DagModel.calculate_dagrun_date_fields

## Backfill (explicit ranges)

Backfill is a first-class DB entity with from_date/to_date and max_active_runs.

Evidence: airflow-core/src/airflow/models/backfill.py:class Backfill

Backfill enumerates partitions via dag.iter_dagrun_infos_between(from_date,to_date), then creates DagRuns with run_type=BACKFILL_JOB and state=QUEUED.

Evidence: airflow-core/src/airflow/models/backfill.py:Backfill._get_info_list; airflow-core/src/airflow/serialization/definitions/dag.py:SerializedDAG.iter_dagrun_infos_between; airflow-core/src/airflow/models/backfill.py:Backfill._create_backfill_dag_run

Scheduler enforces backfill-level concurrency when starting queued runs.

Evidence: airflow-core/src/airflow/jobs/scheduler_job_runner.py:SchedulerJobRunner._start_queued_dagruns

Backfill may clear and requeue existing runs, which violates immutable-run auditing.

Evidence: airflow-core/src/airflow/models/backfill.py:Backfill._handle_clear_run; airflow-core/src/airflow/models/dagrun.py:DagRun.clear_number

# 5) Event-driven Scheduling (Datasets / Sensors / Triggers)

Airflow has two event mechanisms: (1) Assets (datasets) which can trigger DAG runs, and (2) deferrable triggers which resume deferred tasks. Your artifact.promoted(d,p,v) maps most closely to assets/datasets.

## Assets/Datasets: event log → queue → evaluate → create run

On task success, the Execution API registers asset changes in the DB (AssetEvent).

Evidence: airflow-core/src/airflow/api_fastapi/execution_api/routes/task_instances.py:_create_ti_state_update_query_and_update_state (success branch); airflow-core/src/airflow/models/taskinstance.py:TaskInstance.register_asset_changes_in_db; airflow-core/src/airflow/models/asset.py:class AssetEvent

AssetManager queues downstream DAGs via AssetDagRunQueue; partitioned asset DAGs additionally use AssetPartitionDagRun and PartitionedAssetKeyLog.

Evidence: airflow-core/src/airflow/assets/manager.py:AssetManager._queue_dagruns; airflow-core/src/airflow/models/asset.py:class AssetDagRunQueue; airflow-core/src/airflow/models/asset.py:class AssetPartitionDagRun; airflow-core/src/airflow/models/asset.py:class PartitionedAssetKeyLog; airflow-core/src/airflow/assets/manager.py:AssetManager._add_logical_upstream_asset_to_asset_triggered_dags

Scheduler evaluates asset expressions using AssetEvaluator, then creates asset-triggered DagRuns and attaches consumed_asset_events for lineage.

Evidence: airflow-core/src/airflow/assets/evaluation.py:AssetEvaluator.run; airflow-core/src/airflow/jobs/scheduler_job_runner.py:SchedulerJobRunner._create_dag_runs_asset_triggered; airflow-core/src/airflow/models/dagrun.py:DagRun.consumed_asset_events

Partitioned asset DAG runs are created from AssetPartitionDagRun rows with created_dag_run_id is null.

Evidence: airflow-core/src/airflow/jobs/scheduler_job_runner.py:SchedulerJobRunner._create_dagruns_for_partitioned_asset_dags

## Deferrable triggers: avoid polling at task level

DEFERRED transitions create a Trigger row and set trigger_id + continuation method/kwargs.

Evidence: airflow-core/src/airflow/api_fastapi/execution_api/routes/task_instances.py:_create_ti_state_update_query_and_update_state (DEFERRED branch); airflow-core/src/airflow/models/trigger.py:class Trigger; airflow-core/src/airflow/models/taskinstance.py:TaskInstance.trigger_id / next_method / next_kwargs / trigger_timeout

TriggererJobRunner runs triggers and resumes tasks.

Evidence: airflow-core/src/airflow/jobs/triggerer_job_runner.py:TriggererJobRunner

# 6) Persistence Model

## Runs (DagRun)

Uniqueness constraints include (dag_id, run_id) and (dag_id, logical_date).

Evidence: airflow-core/src/airflow/models/dagrun.py:DagRun.__table_args__ (dag_run_dag_id_run_id_key; dag_run_dag_id_logical_date_key)

DagRun stores interval/logical-date fields and optional partition_key; run_after gates eligibility.

Evidence: airflow-core/src/airflow/models/dagrun.py:DagRun.logical_date; airflow-core/src/airflow/models/dagrun.py:DagRun.data_interval_start / data_interval_end; airflow-core/src/airflow/models/dagrun.py:DagRun.run_after; airflow-core/src/airflow/models/dagrun.py:DagRun.partition_key

DagRun references a compiled DAG version via created_dag_version_id and bundle_version.

Evidence: airflow-core/src/airflow/models/dagrun.py:DagRun.created_dag_version_id / bundle_version; airflow-core/src/airflow/models/dag_version.py:class DagVersion

## Tasks (TaskInstance) and attempts

TaskInstance uniqueness: (dag_id, task_id, run_id, map_index).

Evidence: airflow-core/src/airflow/models/taskinstance.py:TaskInstance.__table_args__ (task_instance_composite_key)

Attempt history is stored in TaskInstanceHistory; retry path uses prepare_db_for_next_try.

Evidence: airflow-core/src/airflow/models/taskinstancehistory.py:class TaskInstanceHistory; airflow-core/src/airflow/api_fastapi/execution_api/routes/task_instances.py:_create_ti_state_update_query_and_update_state (retry branch); airflow-core/src/airflow/models/taskinstance.py:TaskInstance.prepare_db_for_next_try

## Lineage and operational logs

AssetEvent is the event log for asset publications; DagRun.consumed_asset_events links triggers to runs.

Evidence: airflow-core/src/airflow/models/asset.py:class AssetEvent; airflow-core/src/airflow/models/dagrun.py:DagRun.consumed_asset_events

Operational log entries can be stored in Log model.

Evidence: airflow-core/src/airflow/models/log.py:class Log

## Idempotency and exactly-once

Airflow provides deduplication for scheduled runs via (dag_id, logical_date) uniqueness, but asset-triggered runs can be created with random run_id when logical_date is None. Task execution is at-least-once under retries and requeueing; exactly-once is not guaranteed.

Evidence: airflow-core/src/airflow/models/dagrun.py:DagRun.__table_args__ (logical_date unique); airflow-core/src/airflow/models/dagrun.py:DagRun.generate_run_id (random when logical_date None); airflow-core/src/airflow/jobs/scheduler_job_runner.py:SchedulerJobRunner._handle_tasks_stuck_in_queued

# 7) Mapping to Our Platform (Table)

Need → Airflow concept → evidence → reuse → adaptation → risks/gaps

# 8) Patterns to Steal vs Avoid (10+)

## Patterns to steal

Interval-first semantics: logical_date = data_interval.start; run_after = data_interval.end

Evidence: airflow-core/src/airflow/timetables/base.py:DagRunInfo.logical_date; DagRunInfo.interval

Timetable abstraction + TimeRestriction.catchup for catchup control

Evidence: airflow-core/src/airflow/timetables/base.py:Timetable; TimeRestriction; airflow-core/src/airflow/timetables/interval.py:CronDataIntervalTimetable.next_dagrun_info

Event log + evaluation queue for asset-driven triggering

Evidence: airflow-core/src/airflow/models/asset.py:AssetEvent; AssetDagRunQueue; airflow-core/src/airflow/assets/manager.py:AssetManager._queue_dagruns

Attach triggering events to runs for lineage

Evidence: airflow-core/src/airflow/models/dagrun.py:DagRun.consumed_asset_events; airflow-core/src/airflow/jobs/scheduler_job_runner.py:_create_dag_runs_asset_triggered

Backfill as first-class entity with its own max_active_runs

Evidence: airflow-core/src/airflow/models/backfill.py:Backfill; airflow-core/src/airflow/jobs/scheduler_job_runner.py:_start_queued_dagruns

Admission control in DB critical section with skip_locked

Evidence: airflow-core/src/airflow/jobs/scheduler_job_runner.py:_executable_task_instances_to_queued

Deterministic retry jitter

Evidence: airflow-core/src/airflow/models/taskinstance.py:TaskInstance.get_retry_delay

Idempotent task start for duplicates from same process

Evidence: airflow-core/src/airflow/api_fastapi/execution_api/routes/task_instances.py:ti_run

Separation of definition compilation from scheduling (serialized DAGs, DB dagbag)

Evidence: airflow-core/src/airflow/jobs/dag_processor_job_runner.py:DagProcessorJobRunner; airflow-core/src/airflow/models/serialized_dag.py:SerializedDagModel; airflow-core/src/airflow/models/dagbag.py:DBDagBag

Partition mapping abstraction for partitioned asset DAGs

Evidence: airflow-core/src/airflow/partition_mappers/base.py:PartitionMapper; airflow-core/src/airflow/timetables/simple.py:PartitionedAssetTimetable

## Patterns to avoid or simplify

Mutating TaskInstance primary key on retry (hard to reason about identity)

Evidence: airflow-core/src/airflow/models/taskinstance.py:TaskInstance.prepare_db_for_next_try

Random run_id for asset-triggered runs when logical_date is None (weak semantic dedupe)

Evidence: airflow-core/src/airflow/models/dagrun.py:DagRun.generate_run_id

Partitioned asset placeholder lacking hard DB restriction (race hazard)

Evidence: airflow-core/src/airflow/models/asset.py:AssetPartitionDagRun (docstring note)

Run mutability via clearing and requeueing (conflicts with immutable run audit)

Evidence: airflow-core/src/airflow/models/backfill.py:Backfill._handle_clear_run; airflow-core/src/airflow/models/dagrun.py:DagRun.clear_number

Boolean-only asset gating (no version selection semantics)

Evidence: airflow-core/src/airflow/assets/evaluation.py:AssetEvaluator.run

Overabundance of concurrency knobs for a minimal core

Evidence: airflow-core/src/airflow/jobs/scheduler_job_runner.py:SchedulerJobRunner._executable_task_instances_to_queued

Definition changes impacting in-flight runs (integrity verification updates unfinished TIs)

Evidence: airflow-core/src/airflow/jobs/scheduler_job_runner.py:SchedulerJobRunner._verify_integrity_if_dag_changed; airflow-core/src/airflow/models/dagrun.py:DagRun.verify_integrity

# 9) Actionable Output

## ADRs (proposed)

ADR-1: Canonical partition semantics = (partition_key p, interval [start,end), logical_date=start). Always persist interval even for partition_key runs.

Evidence: airflow-core/src/airflow/timetables/base.py:DagRunInfo.logical_date; airflow-core/src/airflow/models/dag.py:DAG.get_run_data_interval

ADR-2: Immutable runs + captured inputs. Extend Airflow’s consumed_asset_events linkage to store versioned RunInputs.

Evidence: airflow-core/src/airflow/models/dagrun.py:DagRun.consumed_asset_events; airflow-core/src/airflow/models/asset.py:AssetEvent.extra

ADR-3: Event-sourced eligibility via promotion events. Mirror AssetEvent + queue; replace boolean evaluator with version-aware eligibility.

Evidence: airflow-core/src/airflow/assets/manager.py:AssetManager._queue_dagruns; airflow-core/src/airflow/assets/evaluation.py:AssetEvaluator.run

ADR-4: Backfill as first-class object with max_active_runs; backfill emits new immutable runs (no clearing).

Evidence: airflow-core/src/airflow/models/backfill.py:Backfill; airflow-core/src/airflow/jobs/scheduler_job_runner.py:_start_queued_dagruns

ADR-5: Stable TI identity + explicit TaskAttempt table (avoid TI id mutation).

Evidence: airflow-core/src/airflow/models/taskinstance.py:TaskInstance.prepare_db_for_next_try; airflow-core/src/airflow/models/taskinstancehistory.py:TaskInstanceHistory

ADR-6: Admission control in DB critical section using row locks/skip_locked and capacity accounting.

Evidence: airflow-core/src/airflow/jobs/scheduler_job_runner.py:SchedulerJobRunner._critical_section_enqueue_task_instances; _executable_task_instances_to_queued

ADR-7: Separate definition compilation (processor) from scheduler execution; scheduler reads serialized definitions from DB.

Evidence: airflow-core/src/airflow/jobs/dag_processor_job_runner.py:DagProcessorJobRunner; airflow-core/src/airflow/models/serialized_dag.py:SerializedDagModel; airflow-core/src/airflow/models/dagbag.py:DBDagBag

## Minimal scheduler loop pseudocode (artifact-first partitions)

def on_artifact_promoted(d, p, v, ts):
    insert ArtifactEvent(d,p,v,ts,"promoted")
    upsert ActiveArtifact(d,p)=v
    enqueue WorkflowEvaluation for workflows depending on artifact d

def scheduler_loop(now):
    # 1) Consume evaluation queue; create eligible immutable runs
    with db.transaction():
        workflows = select_workflows_for_evaluation(skip_locked=True)
        for wf in workflows:
            for p in compute_candidate_partitions(wf, now):
                inputs = resolve_active_artifact_versions(wf, p)
                if not inputs: continue
                if exists_run(wf, p, hash(inputs), reason="auto"): continue
                run_id = make_run_id(wf, p, hash(inputs))
                create Run(run_id, wf, p, interval(p), run_after=now, state="QUEUED")
                for (art, v) in inputs: insert RunInput(run_id, art, p, v)
                materialize_task_instances(run_id, wf.definition_version)

    # 2) Progress backfills with per-backfill concurrency
    with db.transaction():
        for bf in pick_backfills(skip_locked=True):
            if running_for_backfill(bf) >= bf.max_active_runs: continue
            for p in next_backfill_partitions(bf):
                ...

    # 3) Admission control + enqueue tasks (DB critical section)
    with db.transaction():
        lock_capacity_rows()
        tis = select_schedulable_tasks(skip_locked=True)
        for ti in tis:
            if not deps_met(ti): continue
            if not capacity_allows(ti): continue
            mark_queued(ti)
            send_to_executor(ti)

    # 4) Process worker/executor events (state updates, retries)

Evidence: Airflow analogs: airflow-core/src/airflow/models/asset.py:AssetDagRunQueue; airflow-core/src/airflow/models/dag.py:DagModel.dags_needing_dagruns; Airflow critical section: airflow-core/src/airflow/jobs/scheduler_job_runner.py:SchedulerJobRunner._critical_section_enqueue_task_instances
