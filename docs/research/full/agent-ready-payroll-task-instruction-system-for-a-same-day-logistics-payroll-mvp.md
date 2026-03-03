# Agent-Ready Payroll Task Instruction System for a Same-Day Logistics Payroll MVP

## Executive summary

An autonomous or semi-autonomous agent can safely execute a payroll workflow **one task at a time** only if the system provides (a) **task-scoped instruction artifacts** that make intent, boundaries, and success criteria explicit; (b) a **bounded tool execution plane** where the agent proposes actions but the application enforces schema, authorization, and side-effect controls; and (c) **evidence-grade logging and provenance** linking every output artifact back to validated inputs and approvals. This “model proposes → system executes → model synthesizes” loop is the canonical tool-calling pattern used by modern function/tool calling APIs. [\[1\]](https://developers.openai.com/api/docs/guides/function-calling/)

For payroll specifically (jurisdiction still **unspecified**), the agentic design must also enforce internal-control fundamentals: **segregation of duties** (e.g., preparation vs approval vs payment release) and alternative controls when segregation is not practical. [\[2\]](https://www.gao.gov/assets/gao-14-704g.pdf) This is essential because payroll steps include multiple high-impact, partially irreversible actions (locking pay periods, finalizing payroll runs, submitting payments), where errors can cause under/overpayment, regulatory noncompliance, or fraud.

The recommended system architecture is therefore a **task-run orchestrator** plus a **policy-gated tool router** plus an **immutable audit/provenance trail**:

-   **Tool safety & gating**: tools are selected and shaped at run start and re-validated at invocation time (schema normalization, allow/deny policies, loop detection, abort propagation), consistent with modern agent runtime patterns used in production tool-use systems.
-   **Deterministic execution + replay**: all side-effecting steps must be idempotent or guarded by idempotency keys and state checks; workflow code changes should be verified using replay tests to avoid breaking in-flight runs. [\[3\]](https://docs.temporal.io/develop/safe-deployments)
-   **Audit record content & privacy**: audit records must capture event descriptions, timestamps, addresses, user/process identifiers, outcomes, and impacted objects; and must consider privacy by limiting PII in logs. [\[4\]](https://csf.tools/reference/nist-sp-800-53/r5/au/au-3/)
-   **Least privilege**: the agent must run with the minimum privileges required for the current task; privileged actions must be logged and access tightly scoped. [\[5\]](https://csf.tools/reference/nist-sp-800-53/r5/ac/ac-6/)
-   **Standardized provenance & events**: represent “who did what, using which inputs, producing which outputs” using provenance primitives (entity/activity/agent) and/or standardized event envelopes (e.g., CloudEvents) for interoperability and traceability. [\[6\]](https://www.w3.org/TR/prov-dm/)

This report defines the **artifacts, schemas, task contracts, decision prompts, validations, access controls, and retry logic** required to run an agent per payroll stage (as previously defined in the payroll MVP workflow and template set).

## Scope and baseline assumptions

The payroll pipeline stages assumed here are the previously defined 11-stage workflow (configuration → worker master → capture → timesheet build → manager approval → pre-run reconciliation/lock → calculation/register → finance approval → payments & payslips → post‑payroll close → corrections/off‑cycle).

Jurisdiction-specific payroll compliance (tax withholding, statutory filing formats, payslip legal fields, and due dates) remains **unspecified** and must be parameterized. Therefore, this report focuses on **agent task instruction structures** and **controls** that are portable across jurisdictions, explicitly flagging the points where jurisdictional rules must be injected.

Key terms used:

-   **Agent**: an autonomous/semi-autonomous software component that executes exactly one task-run at a time under a constrained tool policy.
-   **Orchestrator**: the application component that constructs the task-run context, supplies tools and policies, executes tool calls, persists state, and requests human input when required.
-   **Task-run**: a single execution instance of a payroll task type (e.g., “pre‑payroll reconciliation & lock for Pay Period 2026‑W08”).

## Reference architecture for agent-per-task payroll execution

The dominant production pattern for tool-using agents is a multi-step loop where the application sends tool schemas, the model emits tool calls, the application executes them, and the model continues with tool outputs until a final response is produced. [\[1\]](https://developers.openai.com/api/docs/guides/function-calling/) In addition, production tool-use systems split responsibilities across a **model gateway**, a **tool execution plane**, retrieval, and governance controls (audit logging, policy enforcement, human-in-the-loop for high-impact actions).

### Core components and control points

1.  **Task-run constructor (Orchestrator)**

2.  Creates `TaskRun` record, assigns an owner, sets allowed tools, and attaches input artifact references and required approvals.

3.  Computes an `idempotency_scope` (task-type + pay period + environment) and generates an `idempotency_key` namespace to prevent duplicate side effects.

4.  **Tool registry + policy pipeline**

5.  Tools are defined contract-first (name, JSON schema, auth scope, idempotency class, expected latency, and side-effect category), then filtered by policy and normalized for provider constraints.

6.  Tool safety is enforced twice: (a) when building the tool list; (b) right before each invocation (loop detection, parameter mutation/blocking hooks).

7.  **Tool executor (bounded side effects)**

8.  Executes tool calls deterministically and returns structured results including provenance metadata.

9.  Requires idempotency keys for side-effecting calls. Retry behavior differs by idempotency class (see “Error handling and retries”).

10. **Human decision service**

11. When a task reaches a decision point (approval, exception disposition, threshold override), the orchestrator pauses the run, issues a human prompt, and resumes only after response is validated against allowed options.

12. **Audit/provenance sink**

13. Emits immutable audit events with required content (event description, time, actor, outcome, objects), while limiting PII in logs and mitigating privacy risks. [\[4\]](https://csf.tools/reference/nist-sp-800-53/r5/au/au-3/)

14. Stores provenance links (inputs used → outputs produced) using provenance primitives that model entities, activities, and agents. [\[7\]](https://www.w3.org/TR/prov-dm/)

### Agent–human interaction flow

    flowchart TD
      A[TaskRun created by Orchestrator] --> B[Agent loads TaskCard + Input Manifest]
      B --> C[Agent proposes tool calls per ToolPlan]
      C --> D{Tool call allowed? policy + schema + ACL}
      D -->|No| E[Block + log + request human or re-plan]
      D -->|Yes| F[Tool Executor runs call with idempotency key]
      F --> G[Persist ToolResult + audit/provenance event]
      G --> H{Decision needed?}
      H -->|Yes| I[Create HumanDecisionRequest]
      I --> J[Human responds in allowed set]
      J --> K[Orchestrator validates response + resumes run]
      H -->|No| L{Task acceptance criteria met?}
      L -->|No| C
      L -->|Yes| M[Write output artifacts + finalize TaskRun]
      M --> N[Emit completion event + archive bundle refs]

The pattern above is consistent with (a) tool-calling flows where the model emits tool calls and the application executes them before the final response, and (b) production tool-gating pipelines that filter tools at creation time and enforce invocation-time checks and loop detection. [\[8\]](https://developers.openai.com/api/docs/guides/function-calling/)

## Standard instruction artifacts and schemas for agent task-runs

To instruct an agent reliably, you need **two layers** of artifacts:

-   **Task type (static) artifacts**: human-authored runbooks/templates that define how a task should be done.
-   **Task-run (dynamic) artifacts**: per-execution manifests, tool plans, decision logs, validation reports, and output bundles.

These artifacts must be designed to survive: partial failures, retries, human approvals, audits, and disputes—especially in exception-heavy same-day logistics payroll.

### Standard artifacts required for every agent-invoked payroll task

| Artifact                  | Purpose                                                                                        | Format                              | System of record | Key governance requirement                                                                                                                                |
|---------------------------|------------------------------------------------------------------------------------------------|-------------------------------------|------------------|-----------------------------------------------------------------------------------------------------------------------------------------------------------|
| TaskCard                  | Human-authored “contract” for the task type (objective, steps, controls, approvals)            | DOCX                                | Document store   | Version-controlled; changes reviewed; referenced by TaskRun.                                                                                              |
| Task Instruction Workbook | Machine-checkable manifests: inputs, outputs, tool plan, validations, decision points, run log | XLSX                                | Artifact store   | Structured fields; exportable to JSON; supports audit evidence. [\[4\]](https://csf.tools/reference/nist-sp-800-53/r5/au/au-3/)                           |
| Input Bundle Manifest     | Enumerates required inputs with versions/hashes and PII classification                         | XLSX + JSON export                  | Artifact store   | Ensures reproducibility and provenance traceability. [\[7\]](https://www.w3.org/TR/prov-dm/)                                                              |
| ToolPlan                  | Explicit allow-list of tool calls and constraints (idempotency, retries, ACL scope)            | XLSX + JSON export                  | Orchestrator DB  | Enforced at invocation time (policy gating, schema validation).                                                                                           |
| HumanDecisionRequest      | Standardized prompt + allowed responses + who must decide                                      | DOCX (human-facing) + JSON (system) | Orchestrator DB  | Mandatory for high-impact actions; logged. [\[9\]](https://www.gao.gov/assets/gao-14-704g.pdf)                                                            |
| Validation Report         | Evidence of checks executed, thresholds, pass/fail, overrides                                  | XLSX + JSON export                  | Artifact store   | Required before moving to next stage; links to queries/evidence. [\[10\]](https://csf.tools/reference/nist-sp-800-53/r5/au/au-3/)                         |
| Audit Events              | Append-only record of all tool calls, decisions, and state transitions                         | JSON                                | Audit sink       | Must include required audit record content and consider privacy/PII minimization. [\[10\]](https://csf.tools/reference/nist-sp-800-53/r5/au/au-3/)        |
| Provenance record         | Links inputs → activity → outputs; supports explainability of outputs                          | JSON-LD (PROV-O) or PROV-N          | Provenance store | Uses entity/activity/agent model for traceability. [\[11\]](https://www.w3.org/TR/prov-dm/)                                                               |
| Event envelope            | Standard notification for downstream consumers (e.g., “timesheet locked”)                      | CloudEvents JSON                    | Event bus        | Required context attributes and uniqueness constraints (source+id). [\[12\]](https://raw.githubusercontent.com/cloudevents/spec/main/cloudevents/spec.md) |

### Audit logging content and privacy constraints

A payroll agent must produce audit events that meet minimum audit record content expectations: event description, timestamps, source/destination (where relevant), user/process identifiers, success/failure, and affected objects/files; and should mitigate privacy risks by limiting PII captured in audit trails. [\[4\]](https://csf.tools/reference/nist-sp-800-53/r5/au/au-3/)

Log management practices should protect the confidentiality, integrity, and availability of logs, and ensure administrators can perform effective analysis. [\[13\]](https://nvlpubs.nist.gov/nistpubs/legacy/sp/nistspecialpublication800-92.pdf)

### Use provenance primitives for “explainable payroll”

The provenance data model treats “a thing” as an **entity**, “a process” as an **activity**, and “who/what performed it” as an **agent**, and models how entities are used/generated by activities associated with agents. [\[7\]](https://www.w3.org/TR/prov-dm/) This maps directly to payroll explainability:

-   Entity: Timesheet v3, Payroll Register v1, Payment Batch v1
-   Activity: “PrePayrollReconciliationAndLock”
-   Agent: “PayrollAgent” + Manager approver

### Event envelope for stage transitions

When emitting stage transition events (e.g., timesheet approved, payroll locked), using CloudEvents improves interoperability. The CloudEvents specification requires `id`, `source`, `specversion`, and `type`, and states producers must ensure `source` + `id` uniqueness; it also notes duplicates may share the same `id` in a resend scenario. [\[12\]](https://raw.githubusercontent.com/cloudevents/spec/main/cloudevents/spec.md)

### Data objects ERD for agent task execution

    erDiagram
      TASK_RUN ||--o{ TASK_ATTEMPT : has
      TASK_RUN ||--o{ HUMAN_DECISION : requests
      TASK_RUN ||--o{ TOOL_CALL : issues
      TASK_RUN ||--o{ ARTIFACT_REF : produces

      TASK_TYPE ||--o{ TASK_RUN : instantiates

      TOOL_CALL ||--|| TOOL_RESULT : returns
      TOOL_CALL }o--|| TOOL_DEFINITION : conforms_to

      ARTIFACT_REF }o--|| ARTIFACT : points_to
      ARTIFACT ||--o{ PROVENANCE_EDGE : participates

      PROVENANCE_EDGE }o--|| PROV_ENTITY : entity
      PROVENANCE_EDGE }o--|| PROV_ACTIVITY : activity
      PROVENANCE_EDGE }o--|| PROV_AGENT : agent

      AUDIT_EVENT }o--|| TASK_RUN : references
      AUDIT_EVENT }o--|| TOOL_CALL : references
      AUDIT_EVENT }o--|| HUMAN_DECISION : references

### Agent instruction templates

These are “templates for the agent to follow” and are designed so a human can author/approve them and the orchestrator can enforce them. They are **documents/spreadsheets-first**, with JSON exports for tool calls.

#### Template: TaskCard (DOCX) — empty

    TASKCARD (Agent Instruction Contract) — [Task Type Name]
    Task Type ID: [PR-XX]     Version: [x.y]     Status: [Draft/Approved]
    Owner: [Role]             Approved By: [Role(s)]     Effective Date: [YYYY-MM-DD]

    Objective
    - [What the task must accomplish; measurable outcome]

    Scope
    - In-scope:
    - Out-of-scope:

    Preconditions (must be TRUE before execution)
    - [ ] Required upstream stages completed: [list]
    - [ ] Required input artifacts present & validated: [list]
    - [ ] Required tool permissions granted (least privilege): [roles/scopes]
    - [ ] Human approvers available within SLA: [roles]

    Inputs (artifacts + schemas)
    - Artifact A: [name], format: [DOCX/XLSX/JSON], required fields: [...]
    - Artifact B: ...

    Outputs (artifacts + formats)
    - Output A: [name], format: [DOCX/XLSX/JSON], storage path: [...]
    - Output B: ...

    Step-by-step procedure (agent actions)
    1) ...
    2) ...

    Decision points requiring human input
    - Decision D1: [description]
      Prompt:
      Allowed responses:
      Default:
      Timeout + escalation:

    Validation checks & controls
    - Control C1: [what is checked, threshold, evidence artifact]
    - Audit logging requirements (AU-3 content):
      - event_description, timestamp, actor_id, object_ids, outcome, ...

    Error handling, retry logic, idempotency
    - Tool call classes: [read-only, idempotent write, non-idempotent side effect]
    - Idempotency key rules:
    - Backoff rules:
    - Safe re-run rules:

    Security & privacy considerations
    - Data classification:
    - PII handling:
    - Logging redaction:

    Risks & mitigations
    - R1:
    - R2:

    Acceptance criteria (task completes only if)
    - [ ] ...
    - [ ] ...

#### Template: Task Instruction Workbook (XLSX) — empty (structure)

Workbook tabs (columns shown; include as table schema for XLSX):

| Tab               | Required columns (minimum)                                                                                                                                           |
|-------------------|----------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| `Inputs_Manifest` | `artifact_name`, `artifact_id`, `version`, `format`, `storage_uri`, `checksum_sha256`, `pii_class`, `owner_role`, `validated_by`, `validated_at`                     |
| `ToolPlan`        | `step_no`, `tool_name`, `operation_class`, `idempotency_class`, `required_scope`, `arg_schema_version`, `arg_constraints`, `retry_policy`, `timeout_s`, `human_gate` |
| `DecisionPoints`  | `decision_id`, `trigger_condition`, `prompt_text`, `allowed_responses`, `response_schema`, `decision_owner_role`, `timeout_s`, `escalation_role`                     |
| `Validations`     | `check_id`, `check_description`, `query_or_method`, `threshold`, `result`, `evidence_ref`, `override_allowed`, `override_reason`                                     |
| `Outputs`         | `artifact_name`, `artifact_id`, `version`, `format`, `storage_uri`, `checksum_sha256`, `approved_by`, `approved_at`                                                  |
| `Run_Log`         | `timestamp`, `actor`, `action`, `tool_call_id`, `status`, `notes`                                                                                                    |

#### Completed example: TaskCard for Pre‑Payroll Reconciliation & Lock (PR‑06)

    TASKCARD — Pre-Payroll Reconciliation & Pay-Period Lock
    Task Type ID: PR-06     Version: 1.0     Status: Approved
    Owner: Payroll Ops Lead  Approved By: Controller  Effective Date: 2026-01-15

    Objective
    - Produce a locked, reproducible pay-period dataset snapshot and a reconciliation report showing:
      (a) completeness (coverage for all active workers),
      (b) reasonableness (variance/outlier checks),
      (c) exception disposition,
      and obtain required lock approvals.

    Scope
    - In-scope: approved timesheets, roster reconciliation, lock snapshot creation, variance report
    - Out-of-scope: statutory tax calculation rules (jurisdiction unspecified)

    Preconditions
    - [x] PR-05 (Timesheet approvals) completed for the pay period
    - [x] Worker master snapshot available for the pay period
    - [x] Tool scopes: payroll.read, payroll.lock, audit.write (scoped to pay_period_id)
    - [x] Controller available for lock approval within 8 hours

    Inputs
    - Approved timesheets (XLSX/CSV exports + system record refs)
    - Worker roster snapshot (XLSX export)
    - Open exception queue disposition list (XLSX)
    - Prior period totals for variance baseline (XLSX)

    Outputs
    - Reconciliation_Report_PR06.xlsx (artifact store)
    - Locked_Dataset_Manifest_PR06.json (artifact store)
    - Approval_Attestation_PR06.docx (artifact store)

    Procedure
    1) Read roster snapshot + approved timesheets; compute set difference.
    2) If missing approvals: create HumanDecisionRequest “Proceed with documented exceptions?”.
    3) Run variance checks: hours, pieces, gross estimate vs trailing baseline.
    4) Generate reconciliation report workbook; include evidence refs.
    5) Create immutable lock snapshot with dataset hash; write manifest JSON.
    6) Submit lock package to Controller for approval.
    7) On approval, set pay period state to LOCKED and emit CloudEvent.
    8) Append audit events for lock + approval + artifacts.

    Decision points
    - D1: Missing approvals or unresolved exceptions.
      Prompt: “Approve lock with X unresolved items? Choose: [Reject], [Approve with listed exceptions], [Extend cutoff].”
      Allowed responses: Reject | ApproveWithExceptions | ExtendCutoff
      Timeout: 8 hours; escalate to Finance Ops Manager.

    Validation & controls
    - Completeness: all active workers accounted for (approved timesheet or documented no-work/exception).
    - Integrity: locked dataset hash recorded and stored with manifest.
    - Segregation of duties: Payroll prepares; Controller approves. [2]
    - Audit records must capture required content and consider PII minimization. [4]

    Error handling
    - Read-only calls: retry with exponential backoff (jitter).
    - Lock operation: idempotency_key required; do not retry unless server confirms lock not applied.

The controls above explicitly implement segregation of duties for approval and require audit record content and privacy consideration per audit guidance. [\[9\]](https://www.gao.gov/assets/gao-14-704g.pdf)

## Agent-invoked task types mapped to payroll stages

This section defines **one task type per payroll stage**. Each task type is designed so a task-run can be executed independently, paused for human decisions, and safely retried.

### Shared tool and retry semantics used by all tasks

**Tool calling**: The agent may propose tool calls, but execution is performed by your application; the tooling loop is multi-step (request with tools → model tool call → execute → send tool output → final response or further tool calls). [\[1\]](https://developers.openai.com/api/docs/guides/function-calling/)

**Retry and idempotency**:

-   A request is “idempotent” if repeating it has the same intended effect as performing it once; clients should not automatically retry non-idempotent requests unless they have a means to know the semantics are idempotent or detect that the original was never applied. [\[14\]](https://www.rfc-editor.org/rfc/rfc9110.html)
-   Use exponential backoff (with jitter) for transient failures *only* when response and idempotency criteria are met; avoid unconditional retries of non-idempotent operations. [\[15\]](https://docs.cloud.google.com/storage/docs/retry-strategy)
-   For rate limiting, exponential backoff is recommended to space requests and reduce repeat failures. [\[16\]](https://help.openai.com/en/articles/5955604-how-can-i-solve-429-too-many-requests-errors)

**Access control**:

-   The agent must run under least privilege: only authorized accesses necessary to accomplish the assigned task. [\[5\]](https://csf.tools/reference/nist-sp-800-53/r5/ac/ac-6/)
-   Privileged functions (e.g., pay-period lock, payment submission) are high-risk and must be logged and gated.

**Audit logging**:

-   Audit events must contain sufficient record content (description, time, identifiers, outcomes, objects) and limit PII. [\[4\]](https://csf.tools/reference/nist-sp-800-53/r5/au/au-3/)
-   Logs must be protected for confidentiality, integrity, availability, and usable for analysis. [\[13\]](https://nvlpubs.nist.gov/nistpubs/legacy/sp/nistspecialpublication800-92.pdf)

### Task type specifications

Below, each task is specified with: objective, preconditions, agent actions, inputs/outputs, decision prompts, validation/controls, timing, dependencies, error handling, security/privacy, and risks. “Tool names” shown are **example contracts**; map them to your actual APIs/portals.

#### PR‑01 Configure payroll calendar and rules

| Dimension                  | Specification                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                           |
|----------------------------|-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| Objective                  | Create or update payroll calendar entries and rule configuration for a pay cycle; produce a versioned “rules package” that downstream tasks reference.                                                                                                                                                                                                                                                                                                                                                                                                                                                                  |
| Preconditions              | \(a\) Jurisdictional requirements **unspecified** → only configure generic calendar/rule placeholders; (b) Finance approves any new earning/deduction codes; (c) agent has scoped access `payroll.config.write` and `audit.write` only for configuration objects. [\[17\]](https://csf.tools/reference/nist-sp-800-53/r5/ac/ac-6/)                                                                                                                                                                                                                                                                                      |
| Step-by-step agent actions | 1\) Read existing payroll calendar and current rules version (`payroll.config.get`). 2) Load proposed changes from input DOCX/XLSX. 3) Validate schema: earning/deduction codes unique; effective dates not overlapping. 4) Generate `RulesPackage` draft (JSON + XLSX summary). 5) Request human approval for changes affecting pay outcomes (Controller approval). 6) On approval: write new rules version (`payroll.config.publish`) and record version ID. 7) Emit audit events and provenance “RulesPackage vN generated from ConfigProposal vM.” [\[18\]](https://csf.tools/reference/nist-sp-800-53/r5/au/au-3/) |
| Inputs                     | Config proposal doc (DOCX), config workbook (XLSX) listing pay periods and codes.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                       |
| Outputs                    | \(a\) Rules package summary (XLSX + JSON), (b) Updated payroll calendar export (XLSX), (c) Approval attestation (DOCX).                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                 |
| Human decisions            | Prompt: “Approve publishing RulesPackage vN effective \[date\]? \[Approve\], \[Reject\], \[Approve with edits\].” Allowed responses must be enumerated and validated by orchestrator. [\[2\]](https://www.gao.gov/assets/gao-14-704g.pdf)                                                                                                                                                                                                                                                                                                                                                                               |
| Validation/controls        | Segregation of duties: agent drafts; human approves publication. [\[2\]](https://www.gao.gov/assets/gao-14-704g.pdf) Audit record content logged; limit PII (config should be non-PII). [\[4\]](https://csf.tools/reference/nist-sp-800-53/r5/au/au-3/)                                                                                                                                                                                                                                                                                                                                                                 |
| Timing/frequency           | At onboarding; whenever pay codes/calendar change (frequency unspecified).                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                              |
| Error handling             | Publication is side-effecting: require idempotency key; do not auto-retry unless state check confirms not applied. Principles follow idempotency guidance. [\[19\]](https://www.rfc-editor.org/rfc/rfc9110.html)                                                                                                                                                                                                                                                                                                                                                                                                        |
| Security/privacy           | Low PII; still protect access because config affects pay outcomes. Least privilege enforced. [\[5\]](https://csf.tools/reference/nist-sp-800-53/r5/ac/ac-6/)                                                                                                                                                                                                                                                                                                                                                                                                                                                            |
| Risks                      | Misconfigured calendar/codes → late/incorrect pay; insufficient review → fraud. [\[2\]](https://www.gao.gov/assets/gao-14-704g.pdf)                                                                                                                                                                                                                                                                                                                                                                                                                                                                                     |

#### PR‑02 Maintain worker master data

| Dimension                  | Specification                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                        |
|----------------------------|------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| Objective                  | Create/update worker master records and effective-dated pay rates; ensure completeness for downstream payroll runs.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                  |
| Preconditions              | HR authorization for new/changed worker identity, pay rates, and bank details; dual control for bank account changes (segregation of duties). [\[20\]](https://www.gao.gov/assets/gao-14-704g.pdf)                                                                                                                                                                                                                                                                                                                                                                                                   |
| Step-by-step agent actions | 1\) Load Worker Master Update Request (DOCX/XLSX). 2) Fetch existing worker record (`hr.get_worker`). 3) Validate required fields present; flag missing. 4) If bank/payment method change: create HumanDecisionRequest requiring two-person approval (HR + Finance). 5) Apply permitted updates (`hr.update_worker`) with idempotency key; write before/after hash to audit. 6) Export updated worker master snapshot (XLSX). 7) Append audit record with required fields and minimal PII in logs (e.g., mask account identifiers). [\[10\]](https://csf.tools/reference/nist-sp-800-53/r5/au/au-3/) |
| Inputs                     | Worker update workbook (XLSX); approval request doc (DOCX).                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                          |
| Outputs                    | Updated master snapshot (XLSX); change log (XLSX); approval attestation (DOCX).                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                      |
| Human decisions            | Prompt: “Approve bank detail change for Worker W123? \[Approve\], \[Reject\].” Response requires identity verification steps (unspecified).                                                                                                                                                                                                                                                                                                                                                                                                                                                          |
| Validation/controls        | Least privilege for agent: cannot export full bank details unless required; privileged actions logged. [\[21\]](https://csf.tools/reference/nist-sp-800-53/r5/ac/ac-6/)                                                                                                                                                                                                                                                                                                                                                                                                                              |
| Timing/frequency           | Onboarding and changes (frequency unspecified).                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                      |
| Error handling             | Update calls must be idempotent by `worker_id + effective_date + field_set`; retry only if server indicates no update applied. [\[19\]](https://www.rfc-editor.org/rfc/rfc9110.html)                                                                                                                                                                                                                                                                                                                                                                                                                 |
| Security/privacy           | High PII; enforce minimization and masking; logs protected for CIA. [\[22\]](https://nvlpubs.nist.gov/nistpubs/legacy/sp/nistspecialpublication800-92.pdf)                                                                                                                                                                                                                                                                                                                                                                                                                                           |
| Risks                      | Payment diversion fraud; misapplied pay rates; privacy breach. [\[23\]](https://www.gao.gov/assets/gao-14-704g.pdf)                                                                                                                                                                                                                                                                                                                                                                                                                                                                                  |

#### PR‑03 Capture raw time and piece evidence

| Dimension                  | Specification                                                                                                                                                                                                                                                                                                                                                                                                                                                                       |
|----------------------------|-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| Objective                  | Ingest/validate raw time and piece events; produce daily/period evidence exports and an exception queue for missing/invalid events.                                                                                                                                                                                                                                                                                                                                                 |
| Preconditions              | Source systems connected; event schemas defined; agent has `time.read` and `time.ingest` scopes.                                                                                                                                                                                                                                                                                                                                                                                    |
| Step-by-step agent actions | 1\) Pull raw event batches (`time.ingest.pull`). 2) Validate against event schema; deduplicate by `event_id`. 3) Persist immutable raw batch reference. 4) Generate coverage report (who has no events). 5) Create exception tickets for missing clock-outs/overlaps. 6) Emit event notifications using CloudEvents envelope for downstream tasks (e.g., `type=payroll.time_batch.ingested`). [\[12\]](https://raw.githubusercontent.com/cloudevents/spec/main/cloudevents/spec.md) |
| Inputs                     | Raw event batch export (JSON), ingestion config (XLSX).                                                                                                                                                                                                                                                                                                                                                                                                                             |
| Outputs                    | Validated raw events export (JSON), coverage report (XLSX), exception queue export (XLSX).                                                                                                                                                                                                                                                                                                                                                                                          |
| Human decisions            | Typically none; if schema errors exceed threshold → request Ops lead decision to pause ingestion (threshold unspecified).                                                                                                                                                                                                                                                                                                                                                           |
| Validation/controls        | CloudEvents required context attributes; `source+id` uniqueness; duplicates allowed on resend. [\[12\]](https://raw.githubusercontent.com/cloudevents/spec/main/cloudevents/spec.md) Audit logging on ingestion outcomes. [\[4\]](https://csf.tools/reference/nist-sp-800-53/r5/au/au-3/)                                                                                                                                                                                           |
| Timing/frequency           | Continuous or daily; aligned to payroll cutoff (unspecified).                                                                                                                                                                                                                                                                                                                                                                                                                       |
| Error handling             | Pull/validate is retryable; ingestion writes must be idempotent by batch ID; exponential backoff for transient source errors. [\[24\]](https://docs.cloud.google.com/storage/docs/retry-strategy)                                                                                                                                                                                                                                                                                   |
| Security/privacy           | Events may contain location/time/worker identifiers; protect logs and restrict visibility. [\[25\]](https://nvlpubs.nist.gov/nistpubs/legacy/sp/nistspecialpublication800-92.pdf)                                                                                                                                                                                                                                                                                                   |
| Risks                      | Loss/duplication of time evidence; tampering; downstream incorrect pay.                                                                                                                                                                                                                                                                                                                                                                                                             |

#### PR‑04 Build timesheets and triage exceptions

| Dimension                  | Specification                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                    |
|----------------------------|----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| Objective                  | Convert raw events into payable timesheets (per worker per period) with evidence references and an explicit exception disposition list.                                                                                                                                                                                                                                                                                                                                                                                                                                          |
| Preconditions              | Raw evidence ingested and validated; pay period defined and open; worker roster snapshot available.                                                                                                                                                                                                                                                                                                                                                                                                                                                                              |
| Step-by-step agent actions | 1\) Read pay period definition (`payroll.get_pay_period`). 2) Retrieve raw events subset for period (`time.query`). 3) Aggregate into draft timesheet lines (hours, pieces). 4) Link each line to evidence refs (event IDs/batches). 5) Generate exceptions for missing data and out-of-policy patterns. 6) Write draft timesheets to artifact store (XLSX) and/or system-of-record. 7) Request Ops/Payroll decision for unresolved exceptions above threshold. 8) Emit provenance links “TimesheetDraft generated from RawEventsBatch.” [\[7\]](https://www.w3.org/TR/prov-dm/) |
| Inputs                     | Raw events (JSON), worker roster (XLSX), rules version (from PR‑01).                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                             |
| Outputs                    | Timesheet workbook(s) (XLSX), exception triage report (XLSX), summary memo (DOCX).                                                                                                                                                                                                                                                                                                                                                                                                                                                                                               |
| Human decisions            | Prompt: “Resolve exception E‑###: choose \[Approve as-is\], \[Edit payable units\], \[Mark no-work\], \[Escalate\].”                                                                                                                                                                                                                                                                                                                                                                                                                                                             |
| Validation/controls        | Traceability requirement: each payable line references underlying evidence (provenance). [\[7\]](https://www.w3.org/TR/prov-dm/) Audit record content for edits/resolutions; limit PII. [\[4\]](https://csf.tools/reference/nist-sp-800-53/r5/au/au-3/)                                                                                                                                                                                                                                                                                                                          |
| Timing/frequency           | Daily rolling or end-of-period (policy choice; unspecified).                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                     |
| Error handling             | Aggregation is deterministic and replayable; write operations idempotent by `worker_id + pay_period_id + version`.                                                                                                                                                                                                                                                                                                                                                                                                                                                               |
| Security/privacy           | Timesheets contain payroll data (sensitive); least privilege, encrypted storage, limited logs. [\[26\]](https://csf.tools/reference/nist-sp-800-53/r5/ac/ac-6/)                                                                                                                                                                                                                                                                                                                                                                                                                  |
| Risks                      | Incorrect aggregation; unresolved exceptions; missing evidence for disputes.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                     |

#### PR‑05 Timesheet approval (manager approval task)

| Dimension                  | Specification                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                            |
|----------------------------|--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| Objective                  | Obtain manager approval for payable units and lock timesheets against edits; route post-approval changes through controlled adjustment workflow.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                         |
| Preconditions              | Draft timesheets produced; manager approver assigned; approval window open.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                              |
| Step-by-step agent actions | 1\) Load timesheets requiring approval (`payroll.timesheets.list status=draft`). 2) For each worker: compute summary and highlight exceptions/outliers. 3) Generate Manager Approval Packet (DOCX + XLSX). 4) Request manager decisions (approve/reject/request edits). 5) If edits requested: apply changes via controlled tool (creates adjustment record, not silent overwrite). 6) On approval: set timesheet status=APPROVED and lock (`payroll.timesheets.lock`). 7) Emit audit events including approver ID, timestamp, outcome, and object IDs; avoid logging full wage amounts unless required. [\[4\]](https://csf.tools/reference/nist-sp-800-53/r5/au/au-3/) |
| Inputs                     | Timesheet workbook(s) (XLSX), exception list (XLSX), approval packet template (DOCX).                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                    |
| Outputs                    | Approved timesheet snapshot (PDF/DOCX export optional), approval log (XLSX), lock token/manifest (JSON).                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                 |
| Human decisions            | Prompt: “Approve Timesheet TS‑### for Worker W###? \[Approve\], \[Reject\], \[Approve with edits\], \[Escalate\].”                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                       |
| Validation/controls        | Segregation of duties: agent prepares packet; manager approves; edits after approval require adjustment record. [\[2\]](https://www.gao.gov/assets/gao-14-704g.pdf)                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                      |
| Timing/frequency           | Per pay period; aligned to cutoff.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                       |
| Error handling             | Approvals are mutating but should be idempotent by `(timesheet_id, target_status)` with optimistic concurrency. Do not auto-retry if state ambiguous. [\[19\]](https://www.rfc-editor.org/rfc/rfc9110.html)                                                                                                                                                                                                                                                                                                                                                                                                                                                              |
| Security/privacy           | Manager visibility limited to direct reports; agent must enforce ACL filters. [\[5\]](https://csf.tools/reference/nist-sp-800-53/r5/ac/ac-6/)                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                            |
| Risks                      | Rubber-stamping; approvals without evidence; late approvals delaying payroll.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                            |

#### PR‑06 Pre‑payroll reconciliation & pay-period lock

(Template example provided earlier in this report; this task is the canonical “lock gate.”)

Key control emphasis: management must consider segregation of duties and design alternatives if not practical. [\[2\]](https://www.gao.gov/assets/gao-14-704g.pdf) Logging must include required audit record content and protect log CIA. [\[10\]](https://csf.tools/reference/nist-sp-800-53/r5/au/au-3/)

#### PR‑07 Payroll calculation run & payroll register generation

| Dimension                  | Specification                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                       |
|----------------------------|-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| Objective                  | Produce a draft payroll run from locked payable inputs; generate payroll register and payslip drafts; compute funding requirements. (Statutory calculation content remains jurisdiction-specific and **unspecified**.)                                                                                                                                                                                                                                                                                                                              |
| Preconditions              | Pay period locked (PR‑06); rules version fixed; authorized deductions configured (jurisdiction unspecified).                                                                                                                                                                                                                                                                                                                                                                                                                                        |
| Step-by-step agent actions | 1\) Load locked dataset manifest and rules version. 2) Call payroll engine/provider to compute draft (`payroll.run.calculate_draft`). 3) Retrieve draft outputs: payroll register, payslip drafts, liability summaries. 4) Validate internal consistency: totals, negative net pay flags, outlier detection. 5) Generate Payroll Register Packet (XLSX + DOCX narrative). 6) Prepare finance approval request for PR‑08. 7) Emit provenance: “PayrollRunDraft generated from LockedDataset + RulesPackage.” [\[7\]](https://www.w3.org/TR/prov-dm/) |
| Inputs                     | Locked dataset manifest (JSON), rules package ID, worker master snapshot, authorized adjustments.                                                                                                                                                                                                                                                                                                                                                                                                                                                   |
| Outputs                    | Draft payroll register (XLSX), payslip drafts (PDF bundle or list), funding summary (XLSX), run manifest (JSON).                                                                                                                                                                                                                                                                                                                                                                                                                                    |
| Human decisions            | Typically none at PR‑07; decision gates occur at PR‑08 (finance) unless anomalies exceed configured thresholds (thresholds unspecified).                                                                                                                                                                                                                                                                                                                                                                                                            |
| Validation/controls        | Audit record includes tool calls and outcomes; limit PII in audit logs. [\[4\]](https://csf.tools/reference/nist-sp-800-53/r5/au/au-3/)                                                                                                                                                                                                                                                                                                                                                                                                             |
| Timing/frequency           | Per pay period; may run multiple drafts.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                            |
| Error handling             | Draft calculation is retryable if idempotent by `(pay_period_id, rules_version, locked_dataset_hash)`; avoid double creation of draft runs by using idempotency keys. [\[19\]](https://www.rfc-editor.org/rfc/rfc9110.html)                                                                                                                                                                                                                                                                                                                         |
| Security/privacy           | Payroll register and payslips are highly sensitive; strict ACL and encryption; do not expose via logs. [\[25\]](https://nvlpubs.nist.gov/nistpubs/legacy/sp/nistspecialpublication800-92.pdf)                                                                                                                                                                                                                                                                                                                                                       |
| Risks                      | Wrong gross-to-net due to misconfig; inability to explain outputs without provenance.                                                                                                                                                                                                                                                                                                                                                                                                                                                               |

#### PR‑08 Finance approval & payroll finalization

| Dimension                  | Specification                                                                                                                                                                                                                                                                                                                                                                                                                                              |
|----------------------------|------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| Objective                  | Obtain finance sign-off and finalize payroll run; freeze outputs for payment execution.                                                                                                                                                                                                                                                                                                                                                                    |
| Preconditions              | Draft payroll run generated; funding availability check process exists (unspecified).                                                                                                                                                                                                                                                                                                                                                                      |
| Step-by-step agent actions | 1\) Present finance with payroll register + variance report + adjustment list. 2) Request explicit approval (Approve/Reject/Approve-with-conditions). 3) On approval, call `payroll.run.finalize`. 4) Generate immutable “Final Run Package” manifest (hashes of register/payslips/payment instructions). 5) Emit audit events for approval and finalization with required record content. [\[4\]](https://csf.tools/reference/nist-sp-800-53/r5/au/au-3/) |
| Inputs                     | Draft run manifest (JSON), payroll register (XLSX), variance report (XLSX), adjustment log (XLSX).                                                                                                                                                                                                                                                                                                                                                         |
| Outputs                    | Final payroll run manifest (JSON), signed approval doc (DOCX), final register (PDF/XLSX).                                                                                                                                                                                                                                                                                                                                                                  |
| Human decisions            | Finance prompt: “Approve payroll finalization for Pay Period P? \[Approve\], \[Reject\], \[Return for correction\].”                                                                                                                                                                                                                                                                                                                                       |
| Validation/controls        | Segregation of duties: preparer vs approver; consider alternative controls if limited staffing. [\[2\]](https://www.gao.gov/assets/gao-14-704g.pdf)                                                                                                                                                                                                                                                                                                        |
| Timing/frequency           | Per pay period.                                                                                                                                                                                                                                                                                                                                                                                                                                            |
| Error handling             | Finalize is side-effecting: use idempotency key and state check; never auto-retry if ambiguous outcome. [\[19\]](https://www.rfc-editor.org/rfc/rfc9110.html)                                                                                                                                                                                                                                                                                              |
| Security/privacy           | Finance approval is a privileged operation; log privileged function use. [\[5\]](https://csf.tools/reference/nist-sp-800-53/r5/ac/ac-6/)                                                                                                                                                                                                                                                                                                                   |
| Risks                      | Approving incorrect payroll; insufficient funding; override fraud. [\[2\]](https://www.gao.gov/assets/gao-14-704g.pdf)                                                                                                                                                                                                                                                                                                                                     |

#### PR‑09 Payment submission & payslip delivery

| Dimension                  | Specification                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                    |
|----------------------------|----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| Objective                  | Submit payment batch to banking/payment rail and deliver payslips; record confirmations and failures for remediation.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                            |
| Preconditions              | Final payroll run approved; payment method data complete; bank file format and rails **unspecified**; treasury approval policy exists (unspecified).                                                                                                                                                                                                                                                                                                                                                                                                                                                                             |
| Step-by-step agent actions | 1\) Generate payment instructions (`payments.batch.create`) from final run package. 2) Present treasury/finance with batch totals; request “release payment” approval. 3) On approval, submit batch (`payments.batch.submit`) with idempotency key. 4) Poll or fetch settlement status (`payments.batch.status`). 5) Generate payslip delivery list and publish payslips (`payroll.payslips.publish`). 6) Create remediation queue for failed payments. 7) Emit audit events; ensure logs protect confidentiality/integrity/availability. [\[27\]](https://nvlpubs.nist.gov/nistpubs/legacy/sp/nistspecialpublication800-92.pdf) |
| Inputs                     | Final run package manifest; payment method snapshot; payslip PDFs.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                               |
| Outputs                    | Payment batch file/API receipt (JSON/PDF), settlement report (XLSX), payslip delivery report (XLSX), failed payment cases (XLSX/JSON).                                                                                                                                                                                                                                                                                                                                                                                                                                                                                           |
| Human decisions            | Treasury prompt: “Release payment batch PB‑### total $X? \[Release\], \[Hold\], \[Release partial\].”                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                            |
| Validation/controls        | High-impact step: explicit approval gating; segregation of duties; privileged function use logged. [\[20\]](https://www.gao.gov/assets/gao-14-704g.pdf)                                                                                                                                                                                                                                                                                                                                                                                                                                                                          |
| Timing/frequency           | On pay day; off-cycle as needed.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                 |
| Error handling             | Submission must be idempotent; if network failure occurs, reconcile by calling `batch.status` rather than resubmitting blindly (avoid non-idempotent harm). [\[19\]](https://www.rfc-editor.org/rfc/rfc9110.html) Backoff on transient API errors/rate limits. [\[28\]](https://help.openai.com/en/articles/5955604-how-can-i-solve-429-too-many-requests-errors)                                                                                                                                                                                                                                                                |
| Security/privacy           | Strict handling of bank details; mask sensitive fields in logs; protect log CIA. [\[13\]](https://nvlpubs.nist.gov/nistpubs/legacy/sp/nistspecialpublication800-92.pdf)                                                                                                                                                                                                                                                                                                                                                                                                                                                          |
| Risks                      | Duplicate payments, missed payments, data leakage of pay/bank info.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                              |

#### PR‑10 Post‑payroll close, accounting export, filings/remittance package, archiving

| Dimension                  | Specification                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                   |
|----------------------------|---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| Objective                  | Reconcile payments, export/post GL entries, assemble statutory filing package (jurisdiction unspecified), and archive all artifacts with retention policies.                                                                                                                                                                                                                                                                                                                                                                    |
| Preconditions              | Payments executed; bank confirmations available; accounting integration defined (unspecified).                                                                                                                                                                                                                                                                                                                                                                                                                                  |
| Step-by-step agent actions | 1\) Fetch settlement confirmations and reconcile totals. 2) Generate GL journal export (`ledger.journal.create`). 3) Post journal or stage for accounting approval (`ledger.journal.post` gated). 4) Assemble statutory package placeholders (forms unspecified). 5) Archive artifact bundle with hashes; store retention metadata. 6) Ensure audit logs and retained evidence are protected and analyzable per log management guidance. [\[13\]](https://nvlpubs.nist.gov/nistpubs/legacy/sp/nistspecialpublication800-92.pdf) |
| Inputs                     | Bank confirmations, final payroll register, payment batch record, run manifest.                                                                                                                                                                                                                                                                                                                                                                                                                                                 |
| Outputs                    | Reconciliation workbook (XLSX), GL export (CSV/XLSX), archive manifest (JSON).                                                                                                                                                                                                                                                                                                                                                                                                                                                  |
| Human decisions            | Accounting prompt for posting: “Post payroll journal J‑###? \[Post\], \[Reject\], \[Hold\].”                                                                                                                                                                                                                                                                                                                                                                                                                                    |
| Validation/controls        | Audit events for archive and posting; protect confidentiality, integrity, availability of logs and archived payroll artifacts. [\[22\]](https://nvlpubs.nist.gov/nistpubs/legacy/sp/nistspecialpublication800-92.pdf)                                                                                                                                                                                                                                                                                                           |
| Timing/frequency           | After each pay period; filings per calendar (unspecified).                                                                                                                                                                                                                                                                                                                                                                                                                                                                      |
| Error handling             | Posting is side-effecting; idempotency key required; retries only after state check.                                                                                                                                                                                                                                                                                                                                                                                                                                            |
| Security/privacy           | Archive contains sensitive payroll; encryption, ACL, retention controls required. [\[26\]](https://csf.tools/reference/nist-sp-800-53/r5/ac/ac-6/)                                                                                                                                                                                                                                                                                                                                                                              |
| Risks                      | Unreconciled differences; late filings; inability to produce records; privacy harm.                                                                                                                                                                                                                                                                                                                                                                                                                                             |

#### PR‑11 Corrections, retro pay, off‑cycle payroll

| Dimension                  | Specification                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                  |
|----------------------------|--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| Objective                  | Process payroll corrections without mutating locked historical artifacts; create adjustment lines and execute off-cycle or next-cycle remediation with full traceability.                                                                                                                                                                                                                                                                                                                                                                                                      |
| Preconditions              | Correction case exists; evidence provided; policy on retro/off-cycle triggers **unspecified**; approvals defined (manager + finance thresholds unspecified).                                                                                                                                                                                                                                                                                                                                                                                                                   |
| Step-by-step agent actions | 1\) Create/ingest Correction Request (DOCX/XLSX). 2) Retrieve impacted prior-period artifacts (timesheet, payroll run, payment status). 3) Validate evidence link and compute adjustment proposal. 4) Request approvals based on correction type and amount. 5) Create adjustment lines (`payroll.adjustments.create`) referencing prior run IDs. 6) Run off-cycle payroll (`payroll.run.offcycle`) or schedule for next cycle. 7) Submit payment if required (reuse PR‑09 patterns). 8) Close case and emit provenance/audit events. [\[29\]](https://www.w3.org/TR/prov-dm/) |
| Inputs                     | Correction request form, evidence refs, prior run manifest.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                    |
| Outputs                    | Adjustment register (XLSX), off-cycle run manifest (JSON), updated payslip(s), case closure memo (DOCX).                                                                                                                                                                                                                                                                                                                                                                                                                                                                       |
| Human decisions            | Prompt: “Approve correction C‑### amount $X reason \[..\]? \[Approve\], \[Reject\], \[Request more evidence\].”                                                                                                                                                                                                                                                                                                                                                                                                                                                                |
| Validation/controls        | Must not overwrite locked artifacts; corrections are additive; approvals enforce segregation of duties. [\[2\]](https://www.gao.gov/assets/gao-14-704g.pdf)                                                                                                                                                                                                                                                                                                                                                                                                                    |
| Timing/frequency           | As needed; can be frequent in exception-heavy operations.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                      |
| Error handling             | Off-cycle payment is high impact; idempotency keys and reconciliation checks required; avoid blind retries. [\[19\]](https://www.rfc-editor.org/rfc/rfc9110.html)                                                                                                                                                                                                                                                                                                                                                                                                              |
| Security/privacy           | Corrections often involve disputes; store evidence securely; limit PII in logs. [\[10\]](https://csf.tools/reference/nist-sp-800-53/r5/au/au-3/)                                                                                                                                                                                                                                                                                                                                                                                                                               |
| Risks                      | Repeated correction churn; inconsistent adjustments; worker dissatisfaction; audit exposure.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                   |

## Templates for agent tool-call payloads and sample invocation sequences

This section provides (a) a standard JSON envelope for tool calls; and (b) fully worked example sequences for the five common tasks you requested.

### Standard tool-call envelope template

A contract-first tool plane is central to robust agent architectures. The envelope below is designed to support: schema validation, least privilege scoping, idempotency, and audit logging.

    {
      "tool_name": "payroll.timesheets.lock",
      "tool_version": "2026-01-01",
      "operation_class": "mutating",
      "idempotency_class": "idempotent_write",
      "idempotency_key": "PR-05|P2026-W08|timesheet:TS-000123|lock",
      "actor": {
        "actor_type": "agent",
        "actor_id": "payroll-agent-prod-01",
        "on_behalf_of_user_id": "U-04567"
      },
      "correlation": {
        "task_run_id": "TR-2026W08-PR05-001",
        "attempt_id": "A-003",
        "trace_id": "trace-abc123"
      },
      "args": {
        "timesheet_id": "TS-000123",
        "lock_reason": "manager_approved",
        "expected_current_status": "approved"
      },
      "expected_side_effects": [
        "timesheet_status becomes locked",
        "lock_token issued"
      ],
      "audit": {
        "audit_event_type": "tool_call.executed",
        "pii_fields_redaction": ["args.bank_account", "args.ssn"]
      }
    }

### Sample invocation sequence: Timesheet approval (PR‑05)

    [
      {
        "tool_name": "payroll.timesheets.list",
        "operation_class": "read_only",
        "idempotency_key": "PR-05|P2026-W08|list|draft",
        "args": { "pay_period_id": "P2026-W08", "status": "draft" }
      },
      {
        "tool_name": "payroll.timesheets.get_summary",
        "operation_class": "read_only",
        "idempotency_key": "PR-05|P2026-W08|summary|TS-000123",
        "args": { "timesheet_id": "TS-000123" }
      },
      {
        "tool_name": "human_decision.request",
        "operation_class": "side_effect",
        "idempotency_key": "PR-05|P2026-W08|decision|TS-000123",
        "args": {
          "decision_id": "D1",
          "owner_role": "manager_approver",
          "prompt": "Approve Timesheet TS-000123 for Worker W-112? Options: Approve | Reject | ApproveWithEdits | Escalate",
          "allowed_responses": ["Approve", "Reject", "ApproveWithEdits", "Escalate"],
          "timeout_s": 28800
        }
      },
      {
        "tool_name": "payroll.timesheets.apply_adjustment",
        "operation_class": "mutating",
        "idempotency_key": "PR-05|P2026-W08|adjust|TS-000123|adj-01",
        "args": {
          "timesheet_id": "TS-000123",
          "adjustment": { "code": "REG_HOURS", "delta": 1.5, "reason": "manager_edit" },
          "approval_ref": "HD-D1-APPROVEWITHEDITS"
        }
      },
      {
        "tool_name": "payroll.timesheets.lock",
        "operation_class": "mutating",
        "idempotency_key": "PR-05|P2026-W08|lock|TS-000123",
        "args": { "timesheet_id": "TS-000123", "expected_current_status": "approved" }
      }
    ]

This sequence implements explicit human decision capture and avoids silent edits after approval, aligning with segregation-of-duties expectations. [\[2\]](https://www.gao.gov/assets/gao-14-704g.pdf)

### Sample invocation sequence: Pre‑payroll reconciliation & lock (PR‑06)

    [
      {
        "tool_name": "payroll.roster.snapshot_get",
        "operation_class": "read_only",
        "idempotency_key": "PR-06|P2026-W08|roster",
        "args": { "pay_period_id": "P2026-W08" }
      },
      {
        "tool_name": "payroll.timesheets.list",
        "operation_class": "read_only",
        "idempotency_key": "PR-06|P2026-W08|timesheets|approved",
        "args": { "pay_period_id": "P2026-W08", "status": "approved" }
      },
      {
        "tool_name": "payroll.reconciliation.compute",
        "operation_class": "read_only",
        "idempotency_key": "PR-06|P2026-W08|recon|v1",
        "args": {
          "pay_period_id": "P2026-W08",
          "checks": ["roster_coverage", "missing_approvals", "variance_outliers"]
        }
      },
      {
        "tool_name": "human_decision.request",
        "operation_class": "side_effect",
        "idempotency_key": "PR-06|P2026-W08|decision|lock",
        "args": {
          "decision_id": "LOCK_APPROVAL",
          "owner_role": "finance_controller",
          "prompt": "Approve Pay Period Lock for P2026-W08? Options: Approve | Reject | ApproveWithExceptions | ExtendCutoff",
          "allowed_responses": ["Approve", "Reject", "ApproveWithExceptions", "ExtendCutoff"]
        }
      },
      {
        "tool_name": "payroll.pay_period.lock",
        "operation_class": "side_effect",
        "idempotency_key": "PR-06|P2026-W08|lock",
        "args": {
          "pay_period_id": "P2026-W08",
          "locked_dataset_hash": "sha256:...",
          "approval_ref": "HD-LOCK_APPROVAL-APPROVE"
        }
      }
    ]

Locking must be treated as a privileged, high-impact action: approve explicitly and log. [\[30\]](https://www.gao.gov/assets/gao-14-704g.pdf)

### Sample invocation sequence: Payroll calculation run (PR‑07)

    [
      {
        "tool_name": "payroll.locked_dataset.get_manifest",
        "operation_class": "read_only",
        "idempotency_key": "PR-07|P2026-W08|manifest",
        "args": { "pay_period_id": "P2026-W08" }
      },
      {
        "tool_name": "payroll.run.calculate_draft",
        "operation_class": "mutating",
        "idempotency_key": "PR-07|P2026-W08|draft|hash:abc|rules:v12",
        "args": {
          "pay_period_id": "P2026-W08",
          "locked_dataset_hash": "sha256:abc",
          "rules_version": "v12"
        }
      },
      {
        "tool_name": "payroll.run.export_register",
        "operation_class": "read_only",
        "idempotency_key": "PR-07|P2026-W08|register|draft",
        "args": { "payroll_run_id": "RUN-DRAFT-778", "format": "xlsx" }
      }
    ]

### Sample invocation sequence: Payment submission (PR‑09)

    [
      {
        "tool_name": "payments.batch.create",
        "operation_class": "mutating",
        "idempotency_key": "PR-09|P2026-W08|create|RUN-FINAL-901",
        "args": { "payroll_run_id": "RUN-FINAL-901" }
      },
      {
        "tool_name": "human_decision.request",
        "operation_class": "side_effect",
        "idempotency_key": "PR-09|P2026-W08|decision|release",
        "args": {
          "decision_id": "PAYMENT_RELEASE",
          "owner_role": "treasury",
          "prompt": "Release payment batch PB-445 total 182,400.55? Options: Release | Hold | ReleasePartial",
          "allowed_responses": ["Release", "Hold", "ReleasePartial"]
        }
      },
      {
        "tool_name": "payments.batch.submit",
        "operation_class": "side_effect",
        "idempotency_key": "PR-09|P2026-W08|submit|PB-445",
        "args": { "payment_batch_id": "PB-445", "approval_ref": "HD-PAYMENT_RELEASE-RELEASE" }
      },
      {
        "tool_name": "payments.batch.status",
        "operation_class": "read_only",
        "idempotency_key": "PR-09|P2026-W08|status|PB-445",
        "args": { "payment_batch_id": "PB-445" }
      }
    ]

Because idempotent methods can be retried when failures occur before receiving a response, while non-idempotent operations should not be automatically retried without safeguards, the correct pattern after ambiguous submission is to **check status** rather than blindly resubmit. [\[19\]](https://www.rfc-editor.org/rfc/rfc9110.html)

### Sample invocation sequence: Correction handling (PR‑11)

    [
      {
        "tool_name": "cases.create",
        "operation_class": "side_effect",
        "idempotency_key": "PR-11|case|create|W-112|P2026-W07",
        "args": { "worker_id": "W-112", "pay_period_id": "P2026-W07", "reason": "missed_hours" }
      },
      {
        "tool_name": "payroll.adjustments.calculate_proposal",
        "operation_class": "read_only",
        "idempotency_key": "PR-11|proposal|C-778",
        "args": { "case_id": "C-778" }
      },
      {
        "tool_name": "human_decision.request",
        "operation_class": "side_effect",
        "idempotency_key": "PR-11|decision|C-778",
        "args": {
          "decision_id": "CORRECTION_APPROVAL",
          "owner_role": "finance_controller",
          "prompt": "Approve correction C-778 amount 120.00? Options: Approve | Reject | RequestMoreEvidence",
          "allowed_responses": ["Approve", "Reject", "RequestMoreEvidence"]
        }
      },
      {
        "tool_name": "payroll.adjustments.create",
        "operation_class": "mutating",
        "idempotency_key": "PR-11|adjust|C-778|v1",
        "args": { "case_id": "C-778", "approval_ref": "HD-CORRECTION_APPROVAL-APPROVE" }
      },
      {
        "tool_name": "payroll.run.offcycle",
        "operation_class": "side_effect",
        "idempotency_key": "PR-11|offcycle|C-778",
        "args": { "case_id": "C-778" }
      }
    ]

## RACI and implementation checklist for integrating agents into the payroll MVP

### RACI mapping per task type

This RACI assumes one agent executes the operational steps, but humans remain accountable for approvals and high-impact actions (consistent with segregation-of-duties guidance). [\[2\]](https://www.gao.gov/assets/gao-14-704g.pdf)

| Task type                | Agent    | Payroll Specialist | Manager Approver  | Finance Controller | Treasury    | Systems Admin | Compliance/Audit |
|--------------------------|----------|--------------------|-------------------|--------------------|-------------|---------------|------------------|
| PR‑01 Config             | R        | A                  | I                 | A                  | I           | C             | I                |
| PR‑02 Worker master      | R        | A                  | C                 | A (bank/pay)       | I           | C             | I                |
| PR‑03 Capture            | R        | A                  | I                 | I                  | I           | C             | I                |
| PR‑04 Build timesheets   | R        | A                  | C                 | I                  | I           | C             | I                |
| PR‑05 Approve timesheets | R (prep) | C                  | A                 | I                  | I           | C             | I                |
| PR‑06 Recon & lock       | R (prep) | A                  | I                 | A                  | I           | C             | I                |
| PR‑07 Calc draft         | R        | A                  | I                 | C                  | I           | C             | I                |
| PR‑08 Finalize           | R (prep) | C                  | I                 | A                  | I           | C             | I                |
| PR‑09 Payments           | R (prep) | C                  | I                 | A                  | A           | C             | I                |
| PR‑10 Close & archive    | R (prep) | C                  | I                 | A (GL)             | I           | C             | A                |
| PR‑11 Corrections        | R (prep) | A                  | A (work evidence) | A (materiality)    | A (if paid) | C             | I                |

Legend: R=Responsible, A=Accountable, C=Consulted, I=Informed.

### Minimal automation scope recommended for MVP

Given jurisdictional payroll computations and filings are highly variable and change over time, the MVP should automate the **workflow controls and artifacts** while delegating statutory calculations and filings to a payroll provider module if possible (jurisdiction unspecified).

Automate first: - Task-run orchestration, artifact generation, exception detection, approvals workflow, lock manifests, register packaging, payment batch preparation, audit/provenance capture.

Require human approvals (non-negotiable in MVP): - Rules publication (PR‑01), bank detail changes (PR‑02), timesheet approvals (PR‑05), pay period lock (PR‑06), payroll finalization (PR‑08), payment release (PR‑09), GL posting (PR‑10), material corrections (PR‑11). [\[20\]](https://www.gao.gov/assets/gao-14-704g.pdf)

### Required validation tests for an agent-enabled payroll run

Design these as deterministic checks producing evidence artifacts and audit events:

1.  **Tool policy enforcement test**: verify only ToolPlan-listed tools execute; unauthorized tools are blocked and logged (policy at build-time and invocation-time).
2.  **Idempotency test**: repeat each side-effecting tool call with same idempotency key and verify no duplicate effects; ensure ambiguous outcomes trigger state checks, not blind resubmits. [\[19\]](https://www.rfc-editor.org/rfc/rfc9110.html)
3.  **Audit record completeness test**: for each critical event (lock, approval, finalize, submit payment), confirm audit records include required content and avoid excessive PII. [\[4\]](https://csf.tools/reference/nist-sp-800-53/r5/au/au-3/)
4.  **Log protection test**: verify logs are protected for confidentiality, integrity, availability and can be analyzed. [\[13\]](https://nvlpubs.nist.gov/nistpubs/legacy/sp/nistspecialpublication800-92.pdf)
5.  **Segregation-of-duties test**: ensure the same principal cannot both prepare and approve privileged steps unless documented alternative controls are applied. [\[20\]](https://www.gao.gov/assets/gao-14-704g.pdf)
6.  **Workflow replay test (deployment safety)**: run replay verification on historical task-runs before deploying workflow code changes. [\[3\]](https://docs.temporal.io/develop/safe-deployments)
7.  **Event-envelope conformance test**: emitted events include CloudEvents required attributes and preserve uniqueness constraints. [\[12\]](https://raw.githubusercontent.com/cloudevents/spec/main/cloudevents/spec.md)
8.  **Provenance trace test**: every output artifact can be traced to input artifacts and approvals using entity/activity/agent relationships. [\[11\]](https://www.w3.org/TR/prov-dm/)

### Implementation checklist

1.  Define the **TaskRun schema** and state machine (`created → executing → waiting_for_human → completed/failed`) and require one-task-at-a-time execution per agent identity.
2.  Build a **tool registry** with JSON schemas, idempotency classes, and privilege scopes; enforce policy gating at run start and before every tool call.
3.  Implement **HumanDecisionRequest** as a first-class artifact and state transition; validate responses against allowed options and log decisions. [\[9\]](https://www.gao.gov/assets/gao-14-704g.pdf)
4.  Implement **audit logging** meeting minimum content requirements and limit PII captured; ensure log CIA and analysis capability. [\[31\]](https://csf.tools/reference/nist-sp-800-53/r5/au/au-3/)
5.  Implement **idempotency key strategy** and “status-check before resubmit” patterns for side-effecting calls; adopt exponential backoff only where safe. [\[32\]](https://www.rfc-editor.org/rfc/rfc9110.html)
6.  Add **provenance emission** (PROV) for all artifact transformations and approvals; add CloudEvents for cross-service notifications of stage transitions. [\[6\]](https://www.w3.org/TR/prov-dm/)
7.  Add **deployment replay tests** for workflow/task code changes to prevent nondeterminism breaking running task-runs. [\[3\]](https://docs.temporal.io/develop/safe-deployments)

All agent-per-task designs above assume the previously defined payroll workflow stages and artifacts exist and remain the authoritative pipeline definition for pay processing.

[\[1\]](https://developers.openai.com/api/docs/guides/function-calling/) [\[8\]](https://developers.openai.com/api/docs/guides/function-calling/) https://developers.openai.com/api/docs/guides/function-calling/

<https://developers.openai.com/api/docs/guides/function-calling/>

[\[2\]](https://www.gao.gov/assets/gao-14-704g.pdf) [\[9\]](https://www.gao.gov/assets/gao-14-704g.pdf) [\[20\]](https://www.gao.gov/assets/gao-14-704g.pdf) [\[23\]](https://www.gao.gov/assets/gao-14-704g.pdf) [\[30\]](https://www.gao.gov/assets/gao-14-704g.pdf) https://www.gao.gov/assets/gao-14-704g.pdf

<https://www.gao.gov/assets/gao-14-704g.pdf>

[\[3\]](https://docs.temporal.io/develop/safe-deployments) https://docs.temporal.io/develop/safe-deployments

<https://docs.temporal.io/develop/safe-deployments>

[\[4\]](https://csf.tools/reference/nist-sp-800-53/r5/au/au-3/) [\[10\]](https://csf.tools/reference/nist-sp-800-53/r5/au/au-3/) [\[18\]](https://csf.tools/reference/nist-sp-800-53/r5/au/au-3/) [\[31\]](https://csf.tools/reference/nist-sp-800-53/r5/au/au-3/) https://csf.tools/reference/nist-sp-800-53/r5/au/au-3/

<https://csf.tools/reference/nist-sp-800-53/r5/au/au-3/>

[\[5\]](https://csf.tools/reference/nist-sp-800-53/r5/ac/ac-6/) [\[17\]](https://csf.tools/reference/nist-sp-800-53/r5/ac/ac-6/) [\[21\]](https://csf.tools/reference/nist-sp-800-53/r5/ac/ac-6/) [\[26\]](https://csf.tools/reference/nist-sp-800-53/r5/ac/ac-6/) https://csf.tools/reference/nist-sp-800-53/r5/ac/ac-6/

<https://csf.tools/reference/nist-sp-800-53/r5/ac/ac-6/>

[\[6\]](https://www.w3.org/TR/prov-dm/) [\[7\]](https://www.w3.org/TR/prov-dm/) [\[11\]](https://www.w3.org/TR/prov-dm/) [\[29\]](https://www.w3.org/TR/prov-dm/) https://www.w3.org/TR/prov-dm/

<https://www.w3.org/TR/prov-dm/>

[\[12\]](https://raw.githubusercontent.com/cloudevents/spec/main/cloudevents/spec.md) https://raw.githubusercontent.com/cloudevents/spec/main/cloudevents/spec.md

<https://raw.githubusercontent.com/cloudevents/spec/main/cloudevents/spec.md>

[\[13\]](https://nvlpubs.nist.gov/nistpubs/legacy/sp/nistspecialpublication800-92.pdf) [\[22\]](https://nvlpubs.nist.gov/nistpubs/legacy/sp/nistspecialpublication800-92.pdf) [\[25\]](https://nvlpubs.nist.gov/nistpubs/legacy/sp/nistspecialpublication800-92.pdf) [\[27\]](https://nvlpubs.nist.gov/nistpubs/legacy/sp/nistspecialpublication800-92.pdf) https://nvlpubs.nist.gov/nistpubs/legacy/sp/nistspecialpublication800-92.pdf

<https://nvlpubs.nist.gov/nistpubs/legacy/sp/nistspecialpublication800-92.pdf>

[\[14\]](https://www.rfc-editor.org/rfc/rfc9110.html) [\[19\]](https://www.rfc-editor.org/rfc/rfc9110.html) [\[32\]](https://www.rfc-editor.org/rfc/rfc9110.html) https://www.rfc-editor.org/rfc/rfc9110.html

<https://www.rfc-editor.org/rfc/rfc9110.html>

[\[15\]](https://docs.cloud.google.com/storage/docs/retry-strategy) [\[24\]](https://docs.cloud.google.com/storage/docs/retry-strategy) https://docs.cloud.google.com/storage/docs/retry-strategy

<https://docs.cloud.google.com/storage/docs/retry-strategy>

[\[16\]](https://help.openai.com/en/articles/5955604-how-can-i-solve-429-too-many-requests-errors) [\[28\]](https://help.openai.com/en/articles/5955604-how-can-i-solve-429-too-many-requests-errors) https://help.openai.com/en/articles/5955604-how-can-i-solve-429-too-many-requests-errors

<https://help.openai.com/en/articles/5955604-how-can-i-solve-429-too-many-requests-errors>
