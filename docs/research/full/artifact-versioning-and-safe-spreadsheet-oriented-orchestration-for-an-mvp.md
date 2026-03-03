# Artifact Versioning and Safe Spreadsheet-Oriented Orchestration for an MVP

## Executive summary

A spreadsheet-driven orchestration system becomes unsafe when “the spreadsheet” is treated as a mutable file and tasks refer to it by path or name (“latest.xlsx”). Real-world delays (approvals, sick days, missed handoffs) turn “latest” into ambiguity, and retries turn ambiguity into duplication. Mature orchestration systems emphasize the same two safety primitives: (1) **idempotent execution under retries** and (2) **explicit, immutable data intervals / versions** rather than “now” or “latest.” [\[1\]](https://airflow.apache.org/docs/apache-airflow/stable/best-practices.html)

The most practical MVP design is to treat artifacts as **immutable versions** with strong metadata (hash, size, scan status, template identity, extraction mapping hash) and to treat tasks/runs as **append-only provenance events** that *reference* specific artifact versions (not filenames). This mirrors how cloud and office platforms handle version history (you see versions and can restore), while avoiding their retention pitfalls: Google[\[2\]](https://support.microsoft.com/en-us/office/using-structured-references-with-excel-tables-f5ed2452-2337-4f71-bed3-c8ae6d2b276e) Drive can purge non-pinned revisions after \~30 days or 100 newer revisions, and Microsoft[\[3\]](https://support.microsoft.com/en-us/office/view-previous-versions-of-office-files-5c1e076f-a9c9-41b8-8ace-f77b9642e2c2) SharePoint/OneDrive impose version history limits and explicitly warn against setting limits too low because it can cause inadvertent data loss. [\[4\]](https://support.google.com/drive/answer/2409045?co=GENIE.Platform%3DDesktop&hl=en)

For orchestration safety, adopt three guardrail layers: **idempotency keys** (for runs and spawns), **commit discipline** (staging/commit-ledger to avoid partial effects), and **run-chain limits** (depth/budgets/cycle detection using a correlation ID). This aligns with the retry/idempotency guidance in Apache Software Foundation[\[5\]](https://airflow.apache.org/docs/apache-airflow/stable/best-practices.html) Airflow best practices (tasks behave like database transactions; reruns must produce the same outcome and should not read “latest”), and with Prefect[\[6\]](https://datatracker.ietf.org/doc/rfc9865/?utm_source=chatgpt.com)’s explicit support for idempotency keys and run retries that increment attempt counters. [\[7\]](https://airflow.apache.org/docs/apache-airflow/stable/best-practices.html)

Recommended MVP defaults (defensive but not constraining):

-   **Artifact immutability:** enforced (no overwrite; only new versions).
-   **Run chaining:** `max_depth = 3`, `spawn_budget_per_run = 10`, `run_budget_per_run = 10`.
-   **Scheduler backlog:** `max_backlog_periods = 30` (avoid “infinite catch-up storms”).
-   **Retention:** keep artifacts **180 days by default**, but **pin** (keep-forever) any artifact that is referenced by (a) an approval, (b) a completed/terminal task, or (c) an external export. This borrows the “Keep forever” concept directly from Drive’s version UI semantics. [\[8\]](https://support.google.com/drive/answer/2409045?co=GENIE.Platform%3DDesktop&hl=en)
-   **Template matching:** named ranges + structured tables only; require a template identifier (custom property or hidden named range).
-   **Events export:** cursor-based pagination with monotonic per-tenant sequence and at-least-once semantics.

## Design options comparison

| Approach                                                              | Pros                                                                                               | Cons                                                                                                                                                                                                                                       | Complexity | Recommended for MVP?                                                              |
|-----------------------------------------------------------------------|----------------------------------------------------------------------------------------------------|--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|------------|-----------------------------------------------------------------------------------|
| Rely on Drive/OneDrive “version history” as your artifact system      | Familiar UI; native restore/version browsing                                                       | Retention limits/purging; permissions spread across systems; weak provenance linking to tasks/runs; hard to guarantee “which version was used.” [\[4\]](https://support.google.com/drive/answer/2409045?co=GENIE.Platform%3DDesktop&hl=en) | Low        | No (okay as **import/export**, not as source of truth)                            |
| Internal immutable artifact store (versioned objects + metadata DB)   | Strong provenance; stable references; audit-friendly; can pin versions; consistent templates/scans | Requires building storage, metadata, download UX                                                                                                                                                                                           | Medium     | Yes (core)                                                                        |
| Name-based versioning (“report_2026-02-20.xlsx”) without hashing      | Human-readable; easy                                                                               | Collisions, ambiguity, silent overwrite risk; hard dedupe                                                                                                                                                                                  | Low        | No                                                                                |
| Content-addressed storage (CAS) keys (e.g., sha256-based object keys) | Natural dedupe; avoids overwrite; commit is “DB pointer update”                                    | Requires careful UX for human-friendly labels; hash computation                                                                                                                                                                            | Medium     | Yes (best with “friendly labels”)                                                 |
| Lineage as a simple parent pointer (vN → vN+1)                        | Easy; good for “edit previous spreadsheet”                                                         | Breaks for merges/forks (multiple inputs)                                                                                                                                                                                                  | Low        | Yes (MVP), add DAG later                                                          |
| Full provenance graph (W3C PROV-inspired Entities/Activities/Agents)  | Powerful lineage queries; approvals become first-class provenance                                  | More modeling/UI work                                                                                                                                                                                                                      | High       | Later, but start with PROV-shaped IDs now [\[9\]](https://www.w3.org/TR/prov-dm/) |
| Run outputs committed via staging → commit (two-phase)                | Avoid partial artifacts; supports retries safely                                                   | Slightly more code; needs “pending/committed” states                                                                                                                                                                                       | Medium     | Yes                                                                               |
| Run outputs committed “as we go” (no ledger)                          | Simplest                                                                                           | Partial failures create confusing half-states; duplicate spawns on retry                                                                                                                                                                   | Low        | No                                                                                |
| Run-on-spawn without guardrails                                       | Fast chaining                                                                                      | Easy runaway loops                                                                                                                                                                                                                         | Low        | No                                                                                |
| Run-on-spawn with depth/budget/cycle detection using correlation_id   | Safe chaining; reproducible “process instance”                                                     | Some orchestration logic                                                                                                                                                                                                                   | Medium     | Yes                                                                               |

## Artifact versioning and provenance model

### The minimum artifact model that stays safe under delays

Separate “the logical artifact” from “a concrete version of its bytes”:

-   **Artifact (logical):** “Daily Reconciliation Spreadsheet”, stable ID.
-   **ArtifactVersion (concrete):** immutable content. Every upload or generation creates a new version.

This matches how office platforms present a file with “Version history” entries you can view/restore. [\[10\]](https://support.microsoft.com/en-us/office/view-previous-versions-of-office-files-5c1e076f-a9c9-41b8-8ace-f77b9642e2c2)

Key design choice: **tasks/runs only ever reference** `artifact_version_id`, never “artifact name,” never “latest,” never “path.” This is the single biggest way to avoid the “between days” can-of-worms the user described.

### Lineage links: edit-chains plus derived-from

Model lineage with two complementary relations:

1.  **Revision chain (edit of prior version)**  
    `parent_version_id` (single pointer).  
    Good for “yesterday’s file edited into today’s.”

2.  **Derivation edges (outputs derived from multiple inputs)**  
    `derived_from_version_ids[]` (a set).  
    Good for “merge two spreadsheets,” “aggregate weekly from daily.”

This is a practical subset of provenance modeling: artifacts are “Entities,” runs are “Activities,” and users/automation are “Agents,” consistent with the World Wide Web Consortium[\[11\]](https://debezium.io/documentation/reference/stable/transformations/outbox-event-router.html?utm_source=chatgpt.com) PROV framing. [\[9\]](https://www.w3.org/TR/prov-dm/)

### Naming: human-friendly labels + machine identity

Use two names:

-   **Machine identity:** `content_sha256` (or sha256 + size) as immutable identity; also enables dedupe.
-   **Human label:** `display_name` + optional tag(s):
-   `v17 (2026-02-20 EOD)`
-   `Approved`
-   `Sent to regulator`

External systems demonstrate the need for “pinning” important versions: Drive explicitly allows “Keep forever,” and otherwise older revisions may be purged (30 days / 100 new revisions). [\[12\]](https://support.google.com/drive/answer/2409045?co=GENIE.Platform%3DDesktop&hl=en)  
So your internal system should implement: `pinned=true` and a retention policy that never deletes pinned versions.

## Storage, integrity, and security metadata

### Storage backend: object store + metadata DB

Store bytes in an object store and metadata in your DB. This aligns with how major cloud providers implement object versioning: object stores keep multiple versions and allow recovery/restore when versioning is enabled. [\[13\]](https://docs.cloud.google.com/storage/docs/object-versioning)

Avoid patterns that depend on atomic “rename” semantics: object stores are not POSIX filesystems and do not guarantee atomic rename; “move” can be copy+delete and can lose data if copy fails. [\[14\]](https://airflow.apache.org/docs/apache-airflow/stable/core-concepts/objectstorage.html)  
This matters because staging/commit should not rely on renaming a staged file into place. Prefer either:

-   content-addressed immutable keys (no overwrite; no rename), or
-   multipart upload finalize semantics (provider specific).

### Integrity: checksums as first-class fields

Compute and persist checksums at upload time and on generation. Cloud providers also emphasize checksum-based integrity checks; e.g., S3 supports checksums and calculates/validates them server-side. [\[15\]](https://docs.aws.amazon.com/AmazonS3/latest/userguide/checking-object-integrity.html)

Minimum MVP metadata fields per version:

-   `content_sha256` (app computed)
-   `size_bytes`
-   `mime_type` (detected server-side; do not trust client-provided MIME)
-   `storage_provider_etag` (optional)
-   `encryption` (at-rest), `kms_key_id` (if applicable)
-   `scan_status` (pending/clean/suspicious/failed)
-   `created_by` (user/service), `created_at`
-   `parent_version_id`, `derived_from_version_ids[]`

### File upload hardening: defend-in-depth

You are building a system where spreadsheets can be uploaded and later parsed. File upload security should use multiple layers: allowlisted extensions, size limits, content-type/signature validation, safe storage location, and antivirus/sandbox scanning where possible. [\[16\]](https://cheatsheetseries.owasp.org/cheatsheets/File_Upload_Cheat_Sheet.html)

Important details from the OWASP guidance that map directly to your MVP backlog:

-   **Extension allowlist** (e.g., only `.xlsx`, optionally `.csv`) and beware bypasses like double extensions; validate after decoding filename. [\[17\]](https://cheatsheetseries.owasp.org/cheatsheets/File_Upload_Cheat_Sheet.html)
-   **Content-Type cannot be trusted** (client-controlled); use it only as a convenience check. [\[18\]](https://cheatsheetseries.owasp.org/cheatsheets/File_Upload_Cheat_Sheet.html)
-   **File signature validation** (magic bytes) should complement content-type checks. [\[18\]](https://cheatsheetseries.owasp.org/cheatsheets/File_Upload_Cheat_Sheet.html)
-   **Antivirus/sandbox scan** before making artifacts downloadable to others (or before parsing, depending on threat model). [\[19\]](https://cheatsheetseries.owasp.org/cheatsheets/File_Upload_Cheat_Sheet.html)
-   **Upload/download limits** to reduce DoS risk. [\[20\]](https://cheatsheetseries.owasp.org/cheatsheets/File_Upload_Cheat_Sheet.html)

### Access control: artifact-level ACL derived from task/project

Make access checks artifact-aware, not only task-aware:

-   An artifact version can be referenced by multiple tasks; permissions should be evaluated on (tenant, project/case, task role, approval role).
-   Use short-lived signed URLs for download (object store capability), but always gate URL issuance behind your permission checks.

## Template matching, extraction rules, and definition snapshots

### Extraction primitives: named ranges and structured tables only

For spreadsheets, resilience comes from anchoring extraction to “structured names” rather than coordinates:

-   **Excel named ranges** are created and managed explicitly and can be generated from labeled ranges. [\[21\]](https://support.microsoft.com/en-us/office/define-and-use-names-in-formulas-4d0f13ac-53b7-422e-afd2-abd7ff379c64)
-   **Excel tables + structured references** provide stable table/column names, and the references adjust when rows/columns are added/removed, reducing brittleness compared to raw cell references. [\[22\]](https://support.microsoft.com/en-us/office/using-structured-references-with-excel-tables-f5ed2452-2337-4f71-bed3-c8ae6d2b276e)
-   **Google Sheets named ranges** similarly provide explicit named anchors. [\[23\]](https://support.google.com/docs/answer/63175?co=GENIE.Platform%3DDesktop&hl=en)

MVP rule: the admin-defined mapping can only reference:

-   scalar fields: by named range
-   list fields: by table name + column name

Reject “A1:B2”-style mappings because they break when templates evolve.

### Template identification: require a template ID in the workbook

Template matching must be explicit and fast. Two practical options:

1.  **Custom document property** (recommended)  
    Office files can store custom properties. [\[24\]](https://support.microsoft.com/en-us/office/view-or-change-the-properties-for-an-office-file-21d604c2-481e-4379-8e54-1dd4622c6b75)  
    Your templates can embed something like: `orchestrator_template_id = "recon_v3"`.

2.  **Hidden named range**  
    A named range like `_TEMPLATE_ID` containing `recon_v3`.

On upload, validate:

-   required sheet names exist
-   required named ranges/tables exist
-   template id matches expected
-   optional: “mapping hash” matches (see below)

### Snapshot task definitions and mappings at task creation

Even if your product does not expose “versioning UI” for task definitions, stable execution demands that each task instance remembers *what definition/mapping it was created under*.

Minimum viable approach:

-   Store `definition_snapshot` JSON in the task row at creation (or store a `definition_hash` + immutable definition blob).
-   Store `mapping_hash` (and mapping blob) per artifact ingestion, because ingestion rules can change over time.
-   Store `template_id` + `template_hash` (hash of the template file or normalized structure) to make template mismatch explainable.

This avoids the “I can’t reproduce what happened last Tuesday” problem and fits a provenance mindset (what entities/activities produced this entity). [\[9\]](https://www.w3.org/TR/prov-dm/)

## Safe orchestration for runs, chaining, approvals, and failures

### Idempotency: you will retry, so design for retries

Two real-world facts drive this:

-   Workflows retry (transient failures). Airflow explicitly warns that tasks can retry and must produce the same outcome on rerun; do not read “latest” or use `now()` for critical logic; read/write to specific partitions/intervals. [\[1\]](https://airflow.apache.org/docs/apache-airflow/stable/best-practices.html)
-   Event delivery and orchestration often have at-least-once semantics; duplicates happen unless you dedupe. This is a standard messaging reality. [\[25\]](https://docs.confluent.io/kafka/design/delivery-semantics.html?utm_source=chatgpt.com)

Practical MVP rules:

-   Every **Run** has an immutable `run_id`.
-   Every run request accepts an **idempotency key**, similar to Prefect’s `idempotency_key` for scheduled deployment runs. [\[26\]](https://docs.prefect.io/v3/api-ref/rest-api/server/deployments/get-scheduled-flow-runs-for-deployments)
-   Every spawn operation includes a **spawn idempotency key** (see below).

### Commit discipline: staging + commit, or a commit ledger

Because failures can occur after some outputs are produced, you need a policy that prevents “half a run” from becoming the user-facing truth.

Two MVP-feasible patterns:

**Staging → commit (recommended)**

1.  Run produces outputs into `ArtifactVersion` objects marked `commit_status = "staged"`.
2.  When all validations pass, you atomically:
3.  mark outputs as `committed`
4.  attach them to the task/run record
5.  enqueue spawned runs if requested
6.  If the run fails, staged outputs are either:
7.  retained but hidden (for debugging), or
8.  garbage-collected later if not pinned.

This pairs well with content-addressed keys and avoids object-store rename pitfalls. [\[27\]](https://airflow.apache.org/docs/apache-airflow/stable/core-concepts/objectstorage.html)

**Commit ledger (useful when side-effects span systems)**

Maintain a per-run ledger of intended effects:

-   “created artifact version X”
-   “spawned task Y with spawn_key Z”
-   “requested run for task Y”
-   “transitioned state A → B”

This resembles the motivation behind the transactional outbox pattern: avoid inconsistencies between a service’s internal state and externally observed events. [\[28\]](https://debezium.io/documentation/reference/stable/transformations/outbox-event-router.html?utm_source=chatgpt.com)

### Run-on-spawn with guardrails

You explicitly want “task code can execute another task.” To keep that safe, treat downstream execution as enqueueing runs (never inline), and enforce three controls:

1.  **Depth limit** (default 3)
2.  **Budgets** per run (default spawn=10, downstream run=10)
3.  **Cycle detection** based on a correlation/process ID

For correlation IDs, borrow a proven distributed tracing model: a trace identifier propagated across calls. The Internet Engineering Task Force[\[29\]](https://docs.prefect.io/v3/concepts/schedules) W3C Trace Context standard defines `traceparent` with a `trace-id`, and OpenTelemetry aligns its SpanContext/TraceId scheme to that model. [\[30\]](https://www.w3.org/TR/trace-context/?utm_source=chatgpt.com)  
MVP semantics: every run has `correlation_id` (a trace-id-like value) and every child run links to it.

Temporal-style workflow systems also explicitly model conflicts when starting a workflow with an ID that’s already running; they provide policies for Workflow ID reuse/conflict, highlighting why “start same thing twice” must be governed. [\[31\]](https://docs.temporal.io/workflow-execution/workflowid-runid)

### Approval binding and invalidation rules

Approvals must attach to a stable snapshot, otherwise you approve “something” and later the artifact changes underneath you.

Minimum snapshot binding:

-   `(task_id, task_state, field_snapshot_hash, input_artifact_version_ids[], output_artifact_version_ids[])`

Approval invalidation rules:

-   If any referenced artifact version changes (i.e., new version attached), invalidate.
-   If relevant fields change (new extraction/mapping), invalidate.
-   If task definition/mapping hash changes for *this task instance* (it shouldn’t if you snapshot), invalidate.

This makes approvals defensible and consistent with provenance assumptions: approvals are an agent action about a specific entity state. [\[9\]](https://www.w3.org/TR/prov-dm/)

### Failure and recovery strategies for human-in-the-loop pipelines

Failures fall into two buckets:

-   **Automation failures** (transient): retry with idempotency.
-   **Human delays / missing inputs**: do not “retry”; instead transition into waiting/late/escalated states.

Prefect’s server explicitly marks runs as “Late” if not started on time and allows configurable thresholds, which is a useful pattern when humans or capacity delay scheduled runs. [\[32\]](https://docs.prefect.io/v3/api-ref/python/prefect-server-services-late_runs)

## Recurring pipelines with missed runs and delayed humans

### Model “time” as a first-class part of the workflow

Recurring pipelines should never be “run whenever,” because that creates the “what day is this spreadsheet for?” ambiguity.

Adopt the Airflow-style split between:

-   **logical/effective time:** “this run is for interval \[start,end)”
-   **actual execution time:** “started at X, ended at Y”

Airflow documents this as the data interval / logical date concept: the logical date denotes the start of the data interval, not the wall-clock time the DAG ran. [\[33\]](https://airflow.apache.org/docs/apache-airflow/stable/core-concepts/dag-run.html)

In your system, store on every pipeline instance (or on every top-level “period task”):

-   `period_start`, `period_end` (or `as_of_date`)
-   `scheduled_for` (when it was supposed to run)
-   `started_at`, `ended_at`
-   `status` and `lateness`

### Catch-up strategy: bounded catch-up plus operator-visible backlog

Catch-up is valuable when data is partitionable by interval, but dangerous when the workflow implicitly reads “now.” Airflow explicitly notes that if a DAG isn’t written to handle catchup (i.e., limited to the interval rather than “now”), you should turn catchup off; otherwise it will create runs for missed intervals. [\[34\]](https://airflow.apache.org/docs/apache-airflow/stable/core-concepts/dag-run.html)

MVP recommendation:

-   Always create tasks/runs scoped to a specific interval: they *must* read/write specific partitions/versions.
-   Allow catch-up, but cap backlog (`max_backlog_periods = 30`) and show backlog clearly in UI.

Prefect’s scheduler similarly bounds scheduling behavior (e.g., max runs scheduled, max scheduled time horizon), indicating that unbounded scheduling is not desirable. [\[35\]](https://docs.prefect.io/v3/concepts/schedules)

### Artifact handoff across days: deterministic selection rules

When Task B depends on Task A’s output:

-   Default rule: “consume the output artifact version committed by Task A for the same `period_start`.”
-   If humans delay Task A and the pipeline is catching up, each period still has a unique artifact version chain.

UI must avoid a hidden “latest.” Instead:

-   Show “expected input version” (by lineage and period).
-   Allow override (with explicit reason event) to select a different artifact version, but never silently.

This is the core safety improvement over ad-hoc spreadsheet email chains.

## UI behaviors that prevent operational pain

### Operator UI: version history and lineage as a first-class panel

Borrow familiar patterns:

-   Drive’s “Manage versions” supports downloading prior versions and pinning (“Keep forever”), plus uploading a new version. [\[8\]](https://support.google.com/drive/answer/2409045?co=GENIE.Platform%3DDesktop&hl=en)
-   Microsoft’s “Version history” allows opening a prior version and restoring it. [\[10\]](https://support.microsoft.com/en-us/office/view-previous-versions-of-office-files-5c1e076f-a9c9-41b8-8ace-f77b9642e2c2)

Your MVP artifact panel should include:

-   Version list: `vN`, created time, creator, scan status, template id, mapping hash, pinned badge.
-   Actions: download version, mark pinned, compare metadata, “use as input for…” (creates a reference event).
-   Lineage mini-graph: “derived from” and “used by” tasks, at least one hop.

### Run UI: preview of effects + retry semantics that users trust

Users need to understand what “Run automation” will do.

Core patterns:

-   Run states: `queued → running → succeeded/failed/canceled`.
-   “Proposed vs committed” outputs: show staged outputs during a run; show committed outputs after success.
-   Retry: follow the Prefect-style semantics where a retry keeps the same run identity but increments an attempt counter. [\[36\]](https://docs.prefect.io/v3/how-to-guides/workflows/retry-flow-runs)

On failure, show:

-   error summary (human-readable)
-   structured error code
-   retry button
-   “mark blocked / needs input” button
-   link to logs and staged artifacts (if retained)

### Approver UI: approve a snapshot, not a task

Approvers should see exactly what will be bound:

-   Input artifact version IDs (downloadable)
-   Output artifact version IDs (downloadable)
-   Extracted field preview (with mapping hash)
-   Definition hash / template id
-   A single “Approve snapshot” action that writes an immutable approval record

If something changes, show “Approval invalidated” with the change that caused it.

### Backlog UI for recurring pipelines

Include a pipeline dashboard that shows per period:

-   expected vs actual (late / on time)
-   current blocking step
-   “create catch-up tasks” action (bounded)
-   “skip interval” action (requires explicit reason + permission)

This aligns with how orchestration UIs expose backfill/catchup controls (e.g., Airflow’s backfill UI concept). [\[37\]](https://airflow.apache.org/docs/apache-airflow/stable/core-concepts/dag-run.html)

## Concrete API and schema suggestions for an MVP

### ArtifactVersion metadata schema

    {
      "artifact_version_id": "av_01JP7...",
      "artifact_id": "a_01JP7...",
      "display_name": "Daily Recon v17 (2026-02-20 EOD)",
      "content": {
        "sha256": "b7c1...e91a",
        "size_bytes": 842133,
        "mime_type": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        "original_filename": "recon.xlsx"
      },
      "storage": {
        "provider": "s3",
        "bucket": "artifacts-prod",
        "object_key": "sha256/b7/c1/.../recon.xlsx",
        "etag": "\"...\"",
        "encryption": "SSE-KMS"
      },
      "security": {
        "scan_status": "clean",
        "scan_vendor": "clamav",
        "scanned_at": "2026-02-20T18:03:12Z"
      },
      "template": {
        "template_id": "recon_template_v3",
        "template_hash": "sha256:...",
        "mapping_hash": "sha256:..."
      },
      "lineage": {
        "parent_version_id": "av_01JP6...",
        "derived_from_version_ids": ["av_01JP5...", "av_01JP4..."]
      },
      "lifecycle": {
        "commit_status": "committed",
        "pinned": true,
        "retention_until": null
      },
      "created": {
        "created_at": "2026-02-20T18:02:55Z",
        "created_by": {
          "type": "automation",
          "id": "automation_runner"
        }
      }
    }

Design rationale: checksum/integrity is a first-class feature in object stores (e.g., S3 checksum validation), so your schema should make it queryable too. [\[15\]](https://docs.aws.amazon.com/AmazonS3/latest/userguide/checking-object-integrity.html)

### Run creation and idempotency

-   `POST /tasks/{task_id}/runs`
-   body: `{ "trigger": "...", "idempotency_key": "...", "requested_by": "user_..." }`
-   response: `{ "run_id": "...", "state": "queued" }`

This mirrors Prefect’s documented `idempotency_key` for avoiding duplicate run creation. [\[26\]](https://docs.prefect.io/v3/api-ref/rest-api/server/deployments/get-scheduled-flow-runs-for-deployments)

### Run commit ledger schema (if you choose ledger)

    {
      "run_id": "r_01JP7...",
      "task_id": "t_01JP7...",
      "attempt": 2,
      "effects": [
        {
          "effect_id": "e1",
          "type": "create_artifact_version",
          "status": "committed",
          "payload": { "artifact_version_id": "av_..." }
        },
        {
          "effect_id": "e2",
          "type": "spawn_task",
          "status": "committed",
          "payload": { "child_task_id": "t_...", "spawn_key": "review_vendor_ABC" }
        },
        {
          "effect_id": "e3",
          "type": "request_run",
          "status": "queued",
          "payload": { "task_id": "t_..." }
        }
      ]
    }

Ledger rationale: if you ever need to emit events reliably alongside DB changes, outbox-style thinking avoids dual-write inconsistencies. [\[28\]](https://debezium.io/documentation/reference/stable/transformations/outbox-event-router.html?utm_source=chatgpt.com)

### Spawn idempotency key contract

Require: `(parent_task_id, spawn_key)` unique.

    {
      "spawn_key": "daily_recon_for_2026-02-20",
      "child_task_type": "recon_step_2",
      "initial_fields": { "period_start": "2026-02-20", "period_end": "2026-02-21" },
      "input_artifact_version_refs": [
        { "role": "recon_input", "artifact_version_id": "av_..." }
      ],
      "request_run": true
    }

### Approval snapshot schema

    {
      "approval_id": "ap_01JP7...",
      "task_id": "t_01JP7...",
      "snapshot": {
        "task_state": "WaitingApproval",
        "definition_hash": "sha256:...",
        "mapping_hash": "sha256:...",
        "fields_hash": "sha256:...",
        "input_artifact_version_ids": ["av_in_1", "av_in_2"],
        "output_artifact_version_ids": ["av_out_1"]
      },
      "decision": {
        "status": "approved",
        "approved_by": "user_123",
        "approved_at": "2026-02-20T19:10:00Z",
        "comment": "Looks good."
      },
      "invalidation": {
        "invalidated_at": null,
        "invalidated_reason": null
      }
    }

### Event model and cursor semantics for analytics

Use an append-only event log:

-   `event_seq` (monotonic per tenant) as cursor
-   `event_id` (UUID/ULID)
-   `correlation_id` (trace-id-like)
-   `type`, `payload`, `actor`, `initiator`, `created_at`

To export:

-   `GET /events?cursor=EVENT_SEQ&limit=1000`

Cursor-based pagination is standardized in other domains (e.g., SCIM’s cursor pagination RFC), and is generally more stable than offset pagination for changing datasets. [\[38\]](https://datatracker.ietf.org/doc/rfc9865/?utm_source=chatgpt.com)

Correlation IDs: use a trace-id-like value consistent with W3C Trace Context / OpenTelemetry conventions, so you can connect parent run → child run chains robustly. [\[30\]](https://www.w3.org/TR/trace-context/?utm_source=chatgpt.com)

## Mermaid flowcharts for common MVP flows

### Task produces artifact version and child consumes a specific version

    sequenceDiagram
      participant U as Operator
      participant API as Orchestrator API
      participant W as Run Worker
      participant OS as Object Store
      participant DB as Metadata DB

      U->>API: Upload spreadsheet (task=t1)
      API->>OS: Store bytes (immutable key)
      API->>DB: Create ArtifactVersion av1 (scan_status=pending)
      API->>W: Enqueue scan/extract job for av1

      W->>DB: Validate template + named ranges/tables
      W->>DB: Mark av1 committed (or rejected)
      U->>API: Run automation on task t1
      API->>W: Enqueue Run r1 (idempotency_key)

      W->>OS: Write output bytes (staged)
      W->>DB: Create staged ArtifactVersion av2
      W->>DB: Commit run r1 + av2 (atomic DB txn)
      W->>DB: Spawn child task t2 (input_ref = av2)
      W->>API: Request run for t2 (enqueue)

### Recurring pipeline with missed runs and catch-up

    flowchart TD
      S[Scheduler tick] --> P[Compute periods needing work]
      P -->|cap backlog| B{Backlog <= max_backlog_periods?}
      B -- no --> E[Create "Backlog overflow" alert task]
      B -- yes --> C[Create/ensure Period Tasks for each interval]

      C --> W[Wait for inputs/approvals]
      W -->|late threshold exceeded| L[Mark interval as Late]
      W -->|inputs ready| R[Run automation for interval]
      R --> O[Produce committed output ArtifactVersion]
      O --> N[Spawn next-step tasks for same interval]

### Spawn + request_run with depth limits and cycle detection

    flowchart LR
      A[Run r0 on task t0] --> S[Spawn child tasks]
      S --> D{depth < max_depth?}
      D -- no --> X[Stop chaining, emit guardrail event]
      D -- yes --> B{spawn_budget remaining?}
      B -- no --> X
      B -- yes --> C{cycle detected in correlation_id graph?}
      C -- yes --> X
      C -- no --> Q[Enqueue child run requests]
      Q --> R[Worker executes child runs async]

[\[1\]](https://airflow.apache.org/docs/apache-airflow/stable/best-practices.html) [\[5\]](https://airflow.apache.org/docs/apache-airflow/stable/best-practices.html) [\[7\]](https://airflow.apache.org/docs/apache-airflow/stable/best-practices.html) Best Practices — Airflow 3.1.7 Documentation

<https://airflow.apache.org/docs/apache-airflow/stable/best-practices.html>

[\[2\]](https://support.microsoft.com/en-us/office/using-structured-references-with-excel-tables-f5ed2452-2337-4f71-bed3-c8ae6d2b276e) [\[22\]](https://support.microsoft.com/en-us/office/using-structured-references-with-excel-tables-f5ed2452-2337-4f71-bed3-c8ae6d2b276e) Using structured references with Excel tables - Microsoft Support

<https://support.microsoft.com/en-us/office/using-structured-references-with-excel-tables-f5ed2452-2337-4f71-bed3-c8ae6d2b276e>

[\[3\]](https://support.microsoft.com/en-us/office/view-previous-versions-of-office-files-5c1e076f-a9c9-41b8-8ace-f77b9642e2c2) [\[10\]](https://support.microsoft.com/en-us/office/view-previous-versions-of-office-files-5c1e076f-a9c9-41b8-8ace-f77b9642e2c2) View previous versions of Office files - Microsoft Support

<https://support.microsoft.com/en-us/office/view-previous-versions-of-office-files-5c1e076f-a9c9-41b8-8ace-f77b9642e2c2>

[\[4\]](https://support.google.com/drive/answer/2409045?co=GENIE.Platform%3DDesktop&hl=en) [\[8\]](https://support.google.com/drive/answer/2409045?co=GENIE.Platform%3DDesktop&hl=en) [\[12\]](https://support.google.com/drive/answer/2409045?co=GENIE.Platform%3DDesktop&hl=en) Check activity & file versions - Computer - Google Drive Help

<https://support.google.com/drive/answer/2409045?co=GENIE.Platform%3DDesktop&hl=en>

[\[6\]](https://datatracker.ietf.org/doc/rfc9865/?utm_source=chatgpt.com) [\[38\]](https://datatracker.ietf.org/doc/rfc9865/?utm_source=chatgpt.com) RFC 9865 - Cursor-Based Pagination of System of Cross- ...

<https://datatracker.ietf.org/doc/rfc9865/?utm_source=chatgpt.com>

[\[9\]](https://www.w3.org/TR/prov-dm/) PROV-DM: The PROV Data Model

<https://www.w3.org/TR/prov-dm/>

[\[11\]](https://debezium.io/documentation/reference/stable/transformations/outbox-event-router.html?utm_source=chatgpt.com) [\[28\]](https://debezium.io/documentation/reference/stable/transformations/outbox-event-router.html?utm_source=chatgpt.com) Outbox Event Router

<https://debezium.io/documentation/reference/stable/transformations/outbox-event-router.html?utm_source=chatgpt.com>

[\[13\]](https://docs.cloud.google.com/storage/docs/object-versioning) Object Versioning  \|  Cloud Storage  \|  Google Cloud Documentation

<https://docs.cloud.google.com/storage/docs/object-versioning>

[\[14\]](https://airflow.apache.org/docs/apache-airflow/stable/core-concepts/objectstorage.html) [\[27\]](https://airflow.apache.org/docs/apache-airflow/stable/core-concepts/objectstorage.html) Object Storage — Airflow 3.1.7 Documentation

<https://airflow.apache.org/docs/apache-airflow/stable/core-concepts/objectstorage.html>

[\[15\]](https://docs.aws.amazon.com/AmazonS3/latest/userguide/checking-object-integrity.html) Checking object integrity in Amazon S3 - Amazon Simple Storage Service

<https://docs.aws.amazon.com/AmazonS3/latest/userguide/checking-object-integrity.html>

[\[16\]](https://cheatsheetseries.owasp.org/cheatsheets/File_Upload_Cheat_Sheet.html) [\[17\]](https://cheatsheetseries.owasp.org/cheatsheets/File_Upload_Cheat_Sheet.html) [\[18\]](https://cheatsheetseries.owasp.org/cheatsheets/File_Upload_Cheat_Sheet.html) [\[19\]](https://cheatsheetseries.owasp.org/cheatsheets/File_Upload_Cheat_Sheet.html) [\[20\]](https://cheatsheetseries.owasp.org/cheatsheets/File_Upload_Cheat_Sheet.html) File Upload - OWASP Cheat Sheet Series

<https://cheatsheetseries.owasp.org/cheatsheets/File_Upload_Cheat_Sheet.html>

[\[21\]](https://support.microsoft.com/en-us/office/define-and-use-names-in-formulas-4d0f13ac-53b7-422e-afd2-abd7ff379c64) Define and use names in formulas - Microsoft Support

<https://support.microsoft.com/en-us/office/define-and-use-names-in-formulas-4d0f13ac-53b7-422e-afd2-abd7ff379c64>

[\[23\]](https://support.google.com/docs/answer/63175?co=GENIE.Platform%3DDesktop&hl=en) Name a range of cells - Computer - Google Docs Editors Help

<https://support.google.com/docs/answer/63175?co=GENIE.Platform%3DDesktop&hl=en>

[\[24\]](https://support.microsoft.com/en-us/office/view-or-change-the-properties-for-an-office-file-21d604c2-481e-4379-8e54-1dd4622c6b75) View or change the properties for an Office file - Microsoft Support

<https://support.microsoft.com/en-us/office/view-or-change-the-properties-for-an-office-file-21d604c2-481e-4379-8e54-1dd4622c6b75>

[\[25\]](https://docs.confluent.io/kafka/design/delivery-semantics.html?utm_source=chatgpt.com) Message Delivery Guarantees for Apache Kafka

<https://docs.confluent.io/kafka/design/delivery-semantics.html?utm_source=chatgpt.com>

[\[26\]](https://docs.prefect.io/v3/api-ref/rest-api/server/deployments/get-scheduled-flow-runs-for-deployments) Get Scheduled Flow Runs For Deployments - Prefect

<https://docs.prefect.io/v3/api-ref/rest-api/server/deployments/get-scheduled-flow-runs-for-deployments>

[\[29\]](https://docs.prefect.io/v3/concepts/schedules) [\[35\]](https://docs.prefect.io/v3/concepts/schedules) Schedule flow runs - Prefect

<https://docs.prefect.io/v3/concepts/schedules>

[\[30\]](https://www.w3.org/TR/trace-context/?utm_source=chatgpt.com) Trace Context

<https://www.w3.org/TR/trace-context/?utm_source=chatgpt.com>

[\[31\]](https://docs.temporal.io/workflow-execution/workflowid-runid) Workflow Id and Run Id \| Temporal Platform Documentation

<https://docs.temporal.io/workflow-execution/workflowid-runid>

[\[32\]](https://docs.prefect.io/v3/api-ref/python/prefect-server-services-late_runs) late_runs - Prefect

<https://docs.prefect.io/v3/api-ref/python/prefect-server-services-late_runs>

[\[33\]](https://airflow.apache.org/docs/apache-airflow/stable/core-concepts/dag-run.html) [\[34\]](https://airflow.apache.org/docs/apache-airflow/stable/core-concepts/dag-run.html) [\[37\]](https://airflow.apache.org/docs/apache-airflow/stable/core-concepts/dag-run.html) Dag Runs — Airflow 3.1.7 Documentation

<https://airflow.apache.org/docs/apache-airflow/stable/core-concepts/dag-run.html>

[\[36\]](https://docs.prefect.io/v3/how-to-guides/workflows/retry-flow-runs) How to manually retry a flow run - Prefect

<https://docs.prefect.io/v3/how-to-guides/workflows/retry-flow-runs>
