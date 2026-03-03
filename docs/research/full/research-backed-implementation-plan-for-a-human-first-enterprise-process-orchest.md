# Research-Backed Implementation Plan for a Human-First Enterprise Process Orchestration Platform With Progressive Automation

## Executive summary

Your proposed plan is directionally strong and aligns with the highest-leverage patterns for enterprise “human-first, automation-later” orchestration: durable long-running state, explicit human control points, artifact lineage, strict authorization, and replayable audit history. The key improvement is to **turn each research track into explicit, testable architectural invariants** and to **sequence the spikes so you “lock in” the hard constraints early** (orchestration semantics, artifact immutability, isolation/policy, and authorization model), because they are famously expensive to retrofit. This is especially important in “hyperautomation”-adjacent products, where the platform must integrate multiple automation technologies and governance constraints. [\[1\]](https://www.gartner.com/en/information-technology/glossary/hyperautomation?utm_source=chatgpt.com)

A defensible, enterprise-grade conceptual baseline for process/case/decision modeling is the **OMG “triple crown”**: **BPMN** for structured processes, **CMMN** for adaptive case work, and **DMN** for decisions/rules. That triad maps well to your stated product class (BPM + ACM + approvals + flexible loops). [\[2\]](https://www.omg.org/intro/TripleCrown.pdf?utm_source=chatgpt.com)

For orchestration mechanics, your plan correctly identifies the central “engine choice” problem: durable execution vs BPMN engine vs custom. The strongest evidence-based guidance is: - Durable workflow systems emphasize **deterministic orchestration, replay, safe code evolution (versioning), and long-running human waits**, with explicit mitigations for workflow history growth (e.g., “continue-as-new”). [\[3\]](https://docs.temporal.io/develop/go/versioning?utm_source=chatgpt.com)  
- BPMN-oriented systems emphasize **human task management patterns** (group assignment and claim), workflow patterns in BPMN, and disciplined testing/versioning of process definitions. [\[4\]](https://docs.camunda.io/docs/components/best-practices/architecture/understanding-human-tasks-management/?utm_source=chatgpt.com)

For security and safety, the plan is correct to treat (a) LLM outputs and documents as untrusted, and (b) the execution plane as a hostile environment requiring sandboxing and policy. OWASP’s LLM Top 10 provides a widely used LLM risk taxonomy, and the UK NCSC stresses that prompt injection differs fundamentally from SQL injection in ways that can undermine naive mitigations. [\[5\]](https://owasp.org/www-project-top-10-for-large-language-model-applications/?utm_source=chatgpt.com)

The remainder of this report refines your plan into an evidence-based, tactical sequence of spikes with concrete acceptance criteria, plus two reference architecture variants (“BPMN-first” and “durable-execution-first”) and the tradeoffs for human-first enterprise operations.

## Formal mental model and non-negotiable invariants

### Grounding the model in enterprise process/case/decision semantics

Your “graph + FSM” mental model is a strong formal backbone for flexible workflows with loops, rework cycles, and mixed human/automation steps. It also composes cleanly with the enterprise modeling “triple crown”: - **BPMN**: expresses well-defined process flow semantics in a precise diagram form intended to be understandable by stakeholders and translatable into software components. [\[6\]](https://www.omg.org/spec/BPMN/2.0.2/About-BPMN?utm_source=chatgpt.com)  
- **CMMN**: defines metamodel + notation for modeling “cases,” aimed at flexibility and non-linear work. [\[7\]](https://www.omg.org/spec/CMMN/1.1/About-CMMN?utm_source=chatgpt.com)  
- **DMN**: captures decision logic (routing, eligibility, approvals) in a reusable and governable form, complementing BPMN/CMMN. [\[8\]](https://www.omg.org/dmn/?utm_source=chatgpt.com)

A practical interpretation for your platform is:

-   **Process graph (structured)**: BPMN-like, “known” flow with explicit workflow patterns. [\[9\]](https://docs.camunda.io/docs/components/concepts/workflow-patterns/?utm_source=chatgpt.com)
-   **Case graph (adaptive)**: CMMN-like, where tasks can be enabled/disabled by data/conditions and knowledge workers remain in control. Adaptive case management research explicitly frames this as supporting knowledge workers in flexible, judgment-heavy work. [\[10\]](https://scispace.com/pdf/adaptive-case-management-overview-and-research-challenges-2v9emet8ko.pdf?utm_source=chatgpt.com)
-   **Decision layer**: DMN-like rules/decision tables evaluate “who/what/when” for routing and approvals, allowing governance and change control separate from code. [\[8\]](https://www.omg.org/dmn/?utm_source=chatgpt.com)

### Your two key separations are “must-have,” not optional

**Separation of definition from execution** (Task Definition vs Task Run) is the single most important extensibility boundary you named. It aligns with how mature orchestration approaches handle evolution: - Camunda’s operational guidance on versioning highlights the complexity of evolving process definitions and the need to think explicitly about versioning and migration of running instances. [\[11\]](https://docs.camunda.io/docs/components/best-practices/operations/versioning-process-definitions/?utm_source=chatgpt.com)  
- Temporal’s platform requires deterministic workflow code; changes that would break determinism require explicit versioning methods so new runs use new logic while existing ones continue on old logic. [\[12\]](https://docs.temporal.io/develop/go/versioning?utm_source=chatgpt.com)

**Invariant A (definition/run immutability):**  
- Definitions are versioned and editable; runs are immutable records that point to definition versions and artifact versions.

**Invariant B (approval binding):**  
- An approval must be attached to *exactly* (i) the task/run state, (ii) the artifact version(s) reviewed, and (iii) the policy/decision version used to determine approvers.

### Artifact-first must be treated as artifact-centric BPM, not “attachments”

Because spreadsheets/documents are first-class and move through the process, your platform is naturally aligned with artifact-centric BPM ideas. IBM research on “business artifacts/entities with lifecycles” and the Guard–Stage–Milestone (GSM) approach emphasize that artifacts and their lifecycle are central to guiding operations. [\[13\]](https://research.ibm.com/publications/business-artifacts-with-guard-stage-milestone-lifecycles-managing-artifact-interactions-with-conditions-and-events?utm_source=chatgpt.com)

**Invariant C (artifact immutability + lineage):**  
- Every “edit/transform” yields a new artifact version; lineage forms a DAG even if the task graph contains cycles.

This invariant is not just for audit; it is a prerequisite for safe progressive automation (draft → review → execute) because it enables reproducibility, diffing, and rollback.

## Research tracks translated into explicit architectural decisions

This section keeps your track structure, but tightens each one into: (1) what to research, (2) what decision must be recorded, and (3) what acceptance criteria proves the decision is viable.

### Track A: orchestration engine choice (buy/borrow/build)

You correctly frame the “engine choice” as the hardest long-term decision. The evidence to incorporate explicitly in your decision matrix:

**BPMN-first engine (Camunda-style) advantages**  
- Human task management patterns: assign tasks to groups, let individuals “claim” tasks to avoid duplicate work. [\[14\]](https://docs.camunda.io/docs/components/best-practices/architecture/understanding-human-tasks-management/?utm_source=chatgpt.com)  
- Catalog of workflow patterns and how to implement them in BPMN. [\[15\]](https://docs.camunda.io/docs/components/concepts/workflow-patterns/?utm_source=chatgpt.com)  
- Treat executable process definitions like software: unit test with local isolated engines; integration test in environments close to production; include human-driven exploratory integration testing when needed. [\[16\]](https://docs.camunda.io/docs/components/best-practices/development/testing-process-definitions/?utm_source=chatgpt.com)  
- Operational guidance for versioning process definitions (and the migration problem for running instances). [\[11\]](https://docs.camunda.io/docs/components/best-practices/operations/versioning-process-definitions/?utm_source=chatgpt.com)

**Durable-execution engine (Temporal-style) advantages**  
- Workflows are long-running, crash-resilient “durable execution,” with explicit message passing semantics (Signals, Queries, Updates) and guidance for robust handlers (atomicity, idempotency, completion guarantees). [\[17\]](https://docs.temporal.io/encyclopedia/workflow-message-passing?utm_source=chatgpt.com)  
- Deterministic workflow code and explicit versioning methods for safely deploying changes without breaking running workflows. [\[12\]](https://docs.temporal.io/develop/go/versioning?utm_source=chatgpt.com)  
- Event history is first-class, and platform docs explicitly recommend using Continue-As-New to avoid hitting event history limits as histories grow. [\[18\]](https://docs.temporal.io/workflow-execution/event?utm_source=chatgpt.com)  
- Production readiness guidance for self-hosted Temporal emphasizes scaling/metrics/load testing and cautions that running a mission-critical Temporal service has non-trivial operational cost unless managed carefully. [\[19\]](https://docs.temporal.io/self-hosted-guide/production-checklist?utm_source=chatgpt.com)

**Custom orchestration risks**  
Your plan’s warning is historically accurate: custom orchestrators often re-invent retries, idempotency, stuck-run handling, and auditability. A “custom-engine” option should only survive if you can prove you can meet the same determinism/migration/debuggability guarantees you would otherwise outsource to a mature engine. Temporal’s replay testing guidance is also a useful “bar” for what “safe evolution” tends to require in durable workflow systems. [\[20\]](https://docs.temporal.io/develop/safe-deployments?utm_source=chatgpt.com)

**Decision artifact:** ADR: “Orchestration engine decision”  
- Options evaluated: BPMN-first, durable-execution-first, custom, hybrid.  
- Constraints scored: human waits (days/months), loops, migration/versioning, auditability, ops burden, integration complexity.

**Minimum acceptance criteria (engine spike must demonstrate):**  
- A workflow can wait for human approval without polling and resume correctly after simulated failures. (Durable message passing/handlers are an explicit focal point in Temporal docs.) [\[17\]](https://docs.temporal.io/encyclopedia/workflow-message-passing?utm_source=chatgpt.com)  
- Workflow/process definitions can evolve without breaking in-flight instances, with a concrete versioning strategy. [\[21\]](https://docs.temporal.io/develop/go/versioning?utm_source=chatgpt.com)  
- Testing strategy exists (unit + integration) for definitions that mirrors “test executable processes as software.” [\[16\]](https://docs.camunda.io/docs/components/best-practices/development/testing-process-definitions/?utm_source=chatgpt.com)

### Track B: artifact-first architecture for spreadsheets/documents

Your artifact model is well-formed; the biggest improvement is to explicitly align it with artifact-centric lifecycle semantics:

-   GSM/business artifacts framing: artifacts are central conceptual entities with lifecycles; GSM provides operational semantics for how lifecycles evolve via events and conditions. [\[13\]](https://research.ibm.com/publications/business-artifacts-with-guard-stage-milestone-lifecycles-managing-artifact-interactions-with-conditions-and-events?utm_source=chatgpt.com)
-   Triple crown alignment: artifacts are case file contents (CMMN-like), while decisions about approvals/routing are DMN-like and the structured steps are BPMN-like. [\[22\]](https://www.omg.org/intro/TripleCrown.pdf?utm_source=chatgpt.com)

**Decision artifact:** ADR: “Artifact lifecycle and storage strategy”  
- Canonical representation: Excel-as-canonical vs normalized-as-canonical vs hybrid.  
- Versioning rules: immutable versions, diff mechanisms, retention, lineage.

**Minimum acceptance criteria (artifact spike):**  
- Upload enforces a controlled label registry; each run consumes/produces labeled artifacts; lineage graph is queryable.  
- Spreadsheet “edit” produces a new artifact version while UI preserves an “editing” experience.  
- Approval binds to artifact version(s), not mutable “latest.”

### Track C: security, isolation, and policy (LLMs + code execution)

Your plan is correct to front-load sandboxing and LLM threat modeling.

**LLM threat taxonomy**  
- Use OWASP LLM Top 10 to classify and track risks (prompt injection, insecure output handling, model DoS/cost blowups, excessive agency, etc.). [\[23\]](https://owasp.org/www-project-top-10-for-large-language-model-applications/?utm_source=chatgpt.com)  
- Incorporate the UK NCSC premise: prompt injection differs from SQL injection; misunderstanding the difference can undermine mitigations. [\[24\]](https://www.ncsc.gov.uk/blog-post/prompt-injection-is-not-sql-injection?utm_source=chatgpt.com)

**Execution isolation: microVM vs sandboxed containers**  
- Firecracker is positioned as a minimalist microVM VMM using KVM, excluding unnecessary devices/guest functionality to reduce footprint and attack surface area—aimed at improving security and startup performance. [\[25\]](https://github.com/firecracker-microvm/firecracker?utm_source=chatgpt.com)  
- gVisor provides a sandboxed container runtime (OCI runtime `runsc`) designed to integrate with Docker/Kubernetes and reduce host-kernel exposure for untrusted workloads. [\[26\]](https://gvisor.dev/docs/?utm_source=chatgpt.com)  
- NIST’s Application Container Security Guide is a baseline reference for container threat considerations and mitigations. [\[27\]](https://nvlpubs.nist.gov/nistpubs/specialpublications/nist.sp.800-190.pdf?utm_source=chatgpt.com)

**Policy enforcement**  
- OPA (Open Policy Agent) is a general-purpose policy engine that unifies policy enforcement and externalizes policy decisions via declarative “policy as code.” [\[28\]](https://openpolicyagent.org/docs?utm_source=chatgpt.com)

**Decision artifacts:**  
- ADR: “Sandbox isolation strategy” (Firecracker vs gVisor vs plain containers; where each applies).  
- ADR: “Policy enforcement architecture” (OPA placement, policy lifecycle, auditability).

**Minimum acceptance criteria (sandbox + policy spike):**  
- A job can execute in isolation with enforced CPU/memory/time limits, controlled filesystem mounts, and explicit network egress policy. (NIST container guidance makes clear that runtime controls matter, not just image scanning.) [\[27\]](https://nvlpubs.nist.gov/nistpubs/specialpublications/nist.sp.800-190.pdf?utm_source=chatgpt.com)  
- Every policy decision (allow/deny) is logged with tenant, case, run, and policy version identifiers (auditability requirement).

### Track D: authorization and ownership model that scales

Your instinct to design toward a relationship-based model is evidence-based: enterprise work systems rapidly outgrow ad hoc RBAC.

-   Zanzibar is a reference architecture for globally consistent authorization using a uniform data model/config language for expressing access control policies across many services. [\[29\]](https://www.usenix.org/system/files/atc19-pang.pdf?utm_source=chatgpt.com)

**Decision artifact:** ADR: “Authorization model”  
- MVP: workspace/project RBAC plus case/task role bindings.  
- Path to relationship-based authorization: object–relation tuples for workspace/board/task/run/artifact; permissions derived from relationships.

**Minimum acceptance criteria:**  
- A single, testable authorization specification exists for all objects and actions; UI does not contain “shadow policy” beyond what the authz service decides.  
- All permission-sensitive events are audited (who/what/when).

### Track E: event log, auditability, and replay

For human+automation systems, “explainability” is operationally necessary: users and auditors will ask “why did it route this way?” “who approved?” “what changed?” “why did the automation run?”

-   Event sourcing describes storing all state changes as a sequence of events and reconstructing system state from that event log. [\[30\]](https://www.uladshauchenka.com/p/how-to-write-a-good-product-requirements?utm_source=chatgpt.com)
-   Temporal makes event history explicit at the workflow level and documents Continue-As-New as a mitigation once event histories approach limits. [\[18\]](https://docs.temporal.io/workflow-execution/event?utm_source=chatgpt.com)

**Decision artifact:** ADR: “Audit/event model”  
- Define canonical event taxonomy: assignment, claim, approval requested/granted/rejected, run started/ended, artifact produced, policy decision, etc.  
- Define projections for UI (“current state”) and immutable event log for audit/debug.

**Minimum acceptance criteria:**  
- Any case/run is reconstructible from events; the run timeline can answer “what happened and why” using event history and decision/policy references.

## Tactical spike schedule with acceptance criteria and required artifacts

This is a **week-by-week structure** that does not assume team size; it is a dependency-ordered sequence of work packages. If you have more capacity, run packages in parallel *only where they do not entangle unmade core decisions* (engine choice, artifact immutability, sandbox/policy, authz).

### Mermaid: timeline flowchart of the spike sequence

    flowchart TD
      W1[Weeks 1-2: Formal model + reference workflows] --> W2[Weeks 3-6: Orchestration engine spike]
      W2 --> W3[Weeks 5-8: Artifact store + spreadsheet UX spike]
      W3 --> W4[Weeks 7-9: Human tasks + approvals/claim semantics]
      W4 --> W5[Weeks 8-11: Sandbox + policy enforcement spike]
      W5 --> W6[Weeks 10-12: LLM assist spike behind approvals]
      W6 --> W7[Weeks 11-13: Observability + audit timeline]
      W7 --> W8[Weeks 14-16: Pilot tenant hardening + readiness gates]

### Weeks 1–2: formal model + “reference workflow suite”

**Purpose:** Stabilize the semantics before infrastructure choices harden. This reduces the chance that “flexible loops” devolve into un-debuggable behavior.

**Artifacts produced** - Reference workflow suite (3 canonical flows): spreadsheet-heavy approval, document extraction to table, cyclic rework loop (submit/review/revise/review). (This aligns with ACM’s focus on flexible, knowledge-worker-controlled work.) [\[10\]](https://scispace.com/pdf/adaptive-case-management-overview-and-research-challenges-2v9emet8ko.pdf?utm_source=chatgpt.com)  
- State machine definitions for tasks and cases (including invariants).  
- Draft “triple crown mapping”: what uses BPMN vs CMMN vs DMN semantics. [\[2\]](https://www.omg.org/intro/TripleCrown.pdf?utm_source=chatgpt.com)

**Acceptance criteria** - You can simulate workflows (including cycles) and prove invariants like: - “Approved implies previously in NeedsReview” - “A run cannot produce artifacts unless it started Running” - Explicit definitions of “Task Definition vs Task Run” and lifecycle.

### Weeks 3–6: orchestration engine spike (BPMN-first vs durable-execution-first vs minimal custom)

**Purpose:** Prevent accidentally building a bespoke workflow engine.

**What to implement** - Implement the same reference workflow end-to-end in: - BPMN-first style using Camunda patterns: - group assignment and claim for human work queue semantics [\[14\]](https://docs.camunda.io/docs/components/best-practices/architecture/understanding-human-tasks-management/?utm_source=chatgpt.com)  
- at least two workflow patterns from Camunda’s workflow patterns catalog [\[15\]](https://docs.camunda.io/docs/components/concepts/workflow-patterns/?utm_source=chatgpt.com)  
- follow Camunda testing guidance: unit + integration tests for definitions [\[16\]](https://docs.camunda.io/docs/components/best-practices/development/testing-process-definitions/?utm_source=chatgpt.com)  
- Durable-execution-first style using Temporal semantics: - human waits using message passing (Signals/Updates + Queries) [\[31\]](https://docs.temporal.io/encyclopedia/workflow-message-passing?utm_source=chatgpt.com)  
- demonstrate deterministic evolution using versioning methods [\[12\]](https://docs.temporal.io/develop/go/versioning?utm_source=chatgpt.com)  
- demonstrate Continue-As-New in a loop to manage accumulating history [\[18\]](https://docs.temporal.io/workflow-execution/event?utm_source=chatgpt.com)  
- Minimal custom orchestrator: - only enough to illustrate the “true cost” (retries, idempotency, stuck flows, visibility).

**Artifacts produced** - Decision matrix + scored tradeoff table.  
- ADR: orchestration engine decision (with rationale and consequences).  
- Operational “bar” document: what the engine must guarantee (durability, versioning, replayability, stuck-run visibility).

**Acceptance criteria** - Workflow survives injected failures and resumes correctly at the next wait state. (Temporal’s docs explicitly emphasize robust message handlers and safe evolution.) [\[32\]](https://docs.temporal.io/handling-messages?utm_source=chatgpt.com)  
- At least one “breaking” evolution is handled via versioning rather than by “restart everything.” [\[21\]](https://docs.temporal.io/develop/go/versioning?utm_source=chatgpt.com)  
- Testing strategy exists and runs in CI for definitions. [\[16\]](https://docs.camunda.io/docs/components/best-practices/development/testing-process-definitions/?utm_source=chatgpt.com)

### Weeks 5–8: artifact store + spreadsheet UX spike

**Purpose:** Elevate spreadsheets/docs from attachments to typed, versioned artifacts with lineage.

**What to implement** - Artifact registry with controlled label set and validation rules.  
- Artifact versioning + lineage graph (immutable append-only; derived artifacts generated by runs).  
- “Feels like edit, records as new version” UI behavior.

**Evidence grounding** - Artifact-centric BPM research in GSM frames business artifacts as lifecycled entities central to operations; this supports your “artifact-first” emphasis and the need for explicit lifecycle and interactions. [\[13\]](https://research.ibm.com/publications/business-artifacts-with-guard-stage-milestone-lifecycles-managing-artifact-interactions-with-conditions-and-events?utm_source=chatgpt.com)

**Artifacts produced** - ADR: artifact immutability and lineage model.  
- Artifact label registry (initial) + schema rules for tabular artifacts.

**Acceptance criteria** - Upload labeled spreadsheet; transform produces derived artifact; lineage shows “produced-by run X from inputs Y.”  
- Approval payload binds to artifact version(s) not “latest.”

### Weeks 7–9: approvals + assignment/claim semantics

**Purpose:** Make human control points enforceable and scalable.

**Evidence grounding** - Camunda’s best practice explicitly recommends assigning tasks to groups rather than individuals and using claim semantics to avoid duplicate work. [\[14\]](https://docs.camunda.io/docs/components/best-practices/architecture/understanding-human-tasks-management/?utm_source=chatgpt.com)  
- “Workflow patterns” guidance provides the vocabulary for rework cycles, escalations, and control-flow patterns. [\[15\]](https://docs.camunda.io/docs/components/concepts/workflow-patterns/?utm_source=chatgpt.com)

**Artifacts produced** - Approval policy spec (who can approve, how determined, SoD rules if needed).  
- “Human task contract” spec: assignment, claim, unclaim, delegation, escalation timers.

**Acceptance criteria** - Two users in the same group cannot both “own” the same task after claim.  
- Approval gates block execution until approval event arrives; audit log records approver identity and artifact versions.

### Weeks 8–11: sandbox + policy enforcement spike

**Purpose:** Avoid security retrofits.

**Evidence grounding** - Firecracker’s design emphasizes minimalism to reduce footprint and attack surface while improving security and startup characteristics. [\[25\]](https://github.com/firecracker-microvm/firecracker?utm_source=chatgpt.com)  
- gVisor provides an additional sandbox layer via `runsc` integrated with Docker/Kubernetes. [\[26\]](https://gvisor.dev/docs/?utm_source=chatgpt.com)  
- NIST container security guidance provides a baseline for threat considerations and mitigations in containerized environments. [\[27\]](https://nvlpubs.nist.gov/nistpubs/specialpublications/nist.sp.800-190.pdf?utm_source=chatgpt.com)  
- OPA externalizes policy enforcement as “policy as code” with consistent APIs. [\[28\]](https://openpolicyagent.org/docs?utm_source=chatgpt.com)

**Artifacts produced** - ADR: sandbox selection and threat model.  
- ADR: policy enforcement architecture (OPA placement, versioning, audit).  
- Resource policy: CPU/mem/time; filesystem mounts; network egress; secrets injection rules.

**Acceptance criteria** - Execute a job with: - enforced resource limits - denied network egress by default (or restricted allowlist) - no access to other tenants’ storage namespaces - Every policy decision is logged with policy version and correlation IDs.

### Weeks 10–12: LLM assist spike behind approvals (progressive automation stage 1–2)

**Purpose:** Add safe automation assist without unsafe autonomy.

**Evidence grounding** - OWASP LLM Top 10 provides risk categories to drive mitigations (prompt injection, insecure output handling, model DoS, excessive agency, sensitive info exposure). [\[23\]](https://owasp.org/www-project-top-10-for-large-language-model-applications/?utm_source=chatgpt.com)  
- UK NCSC cautions prompt injection differs from SQL injection in ways that can undermine standard mitigation thinking. [\[24\]](https://www.ncsc.gov.uk/blog-post/prompt-injection-is-not-sql-injection?utm_source=chatgpt.com)  
- NIST AI RMF provides risk management framing for AI systems (govern/map/measure/manage), and NIST’s Generative AI profile contextualizes risks for GenAI use. [\[33\]](https://nvlpubs.nist.gov/nistpubs/ai/nist.ai.100-1.pdf?utm_source=chatgpt.com)

**Artifacts produced** - LLM threat model (document-as-untrusted-input).  
- “Safe automation rules”: which actions are suggestion-only vs require human approval.  
- Budget policy: token/cost caps and rate limiting.

**Acceptance criteria** - Model outputs are structured and validated; invalid outputs cannot be executed.  
- Any “execute” step requires explicit approval event and policy checks; the system can degrade to suggestion-only mode.

### Weeks 11–13: observability + audit timeline (operability spike)

**Purpose:** Ensure the system is debuggable and operable from day one.

**Evidence grounding** - SRE: SLO definitions (SLI measured against target) and the “four golden signals” for monitoring (latency, traffic, errors, saturation). [\[34\]](https://sre.google/sre-book/service-level-objectives/?utm_source=chatgpt.com)  
- OpenTelemetry semantic conventions: standard naming/attributes for traces/metrics/logs to unify observability across services. [\[35\]](https://opentelemetry.io/docs/concepts/semantic-conventions/?utm_source=chatgpt.com)

**Artifacts produced** - SLOs for workflow dispatch latency, approval notification latency, run start latency, and artifact read latency. [\[36\]](https://sre.google/sre-book/service-level-objectives/?utm_source=chatgpt.com)  
- Correlation ID spec (case/task/run/artifact).  
- “Run timeline” UX that renders the immutable event history + derived current state.

**Acceptance criteria** - For any run, you can answer: - inputs used (artifact versions) - decisions made (policy and decision versions) - approvals granted (actor, timestamp) - outputs produced and lineage - Dashboards show golden signals broken down by tenant and workflow type. [\[37\]](https://sre.google/sre-book/monitoring-distributed-systems/?utm_source=chatgpt.com)

### Weeks 14–16: pilot tenant readiness and governance hardening

**Purpose:** Turn your platform into something you can safely run for a small set of real enterprise tenants.

**Evidence grounding** - Multi-tenant architecture choices (silo/pool/bridge) are influenced by regulatory, strategic, and cost considerations; AWS SaaS Lens formalizes those models and their implications. [\[38\]](https://docs.aws.amazon.com/wellarchitected/latest/saas-lens/silo-pool-and-bridge-models.html?utm_source=chatgpt.com)  
- Azure’s SaaS tenancy patterns show how sharded multi-tenant databases can scale by keeping each tenant’s data within a shard (common in SaaS). [\[39\]](https://learn.microsoft.com/en-us/azure/azure-sql/database/saas-tenancy-app-design-patterns?view=azuresql&utm_source=chatgpt.com)  
- For secure software lifecycle baseline, NIST SSDF provides a core set of secure development practices intended to integrate into SDLCs. [\[40\]](https://csrc.nist.gov/pubs/sp/800/218/final?utm_source=chatgpt.com)

**Artifacts produced** - Tenant onboarding runbook and “first-3-tenants readiness checklist.”  
- Governance process: ADR lifecycle, review cadence, and release gating.  
- Security and incident response playbooks (minimal set).

**Acceptance criteria** - Tenant isolation tests exist and are part of CI (authz + data partition boundaries).  
- Operational readiness gate: SLOs exist; dashboards exist; on-call escalation exists; sandbox/policy enforcement is not bypassable.

## Reference architecture variants and tradeoffs

This section responds directly to your stated desire for “BPMN-first vs durable-execution-first” clarity for **human-first enterprise workflows**.

### Variant A: BPMN-first (process/case engine as canonical orchestrator)

**Core idea:** Use BPMN/CMMN/DMN runtime as the authoritative orchestration layer for cases, human tasks, and decisions; implement automation as service tasks/workers behind that engine.

**Best fit when** - You need rich human task semantics and BPMN patterns “out of the box,” and you want business stakeholders to heavily participate in modeling and iteration. [\[41\]](https://docs.camunda.io/docs/components/best-practices/architecture/understanding-human-tasks-management/?utm_source=chatgpt.com)  
- The platform’s differentiator is **enterprise process modeling + tasklist/work queues + governance**, with automation as an adjunct.

**Primary risks** - Versioning and migrating in-flight process instances becomes a recurring operational concern in large/long-lived process definitions; Camunda highlights the importance of understanding versioning and potential migrations. [\[11\]](https://docs.camunda.io/docs/components/best-practices/operations/versioning-process-definitions/?utm_source=chatgpt.com)

### Variant B: durable-execution-first (workflow code as canonical orchestrator)

**Core idea:** Use durable execution workflows as the canonical orchestrator; represent cases/tasks as workflow state machines with explicit message passing for human approvals and events.

**Best fit when** - You prioritize reliability of long-running orchestrations and crash-proof execution with replayable history. [\[42\]](https://docs.temporal.io/workflows?utm_source=chatgpt.com)  
- You expect complex automation steps and need robust retries/timeouts and “stateful service” semantics. [\[31\]](https://docs.temporal.io/encyclopedia/workflow-message-passing?utm_source=chatgpt.com)

**Primary risks** - Determinism and safe evolution become core engineering discipline; Temporal emphasizes deterministic workflow code, versioning methods, and replay testing to avoid non-determinism errors. [\[12\]](https://docs.temporal.io/develop/go/versioning?utm_source=chatgpt.com)  
- History growth requires explicit controls such as Continue-As-New. [\[18\]](https://docs.temporal.io/workflow-execution/event?utm_source=chatgpt.com)

### A pragmatic hybrid that often wins in your product class

Many enterprise orchestration platforms converge on a hybrid boundary:

-   **BPMN/CMMN/DMN layer**: canonical for modeling and human workflow semantics (task assignment, claim, work queues, approval policies). [\[43\]](https://www.omg.org/intro/TripleCrown.pdf?utm_source=chatgpt.com)
-   **Durable execution layer**: canonical for complex automation “subflows” that need long-running reliability, retries, and rich event history; return results back to the case layer as artifact outputs and events. [\[42\]](https://docs.temporal.io/workflows?utm_source=chatgpt.com)

This hybrid is consistent with the “triple crown” notion that organizations often need process models for prescriptive workflows, case models for reactive activities, and decision models for complex rules—because your platform also adds a fourth dimension: automation reliability. [\[44\]](https://www.omg.org/dmn/?utm_source=chatgpt.com)

### Decision table: choosing the architecture variant

| Criterion                                       | BPMN-first                                                                                                                                                                            | durable-execution-first                                                                                                               | hybrid default               |
|-------------------------------------------------|---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|---------------------------------------------------------------------------------------------------------------------------------------|------------------------------|
| Human task semantics (group + claim, tasklists) | Strongly aligned [\[14\]](https://docs.camunda.io/docs/components/best-practices/architecture/understanding-human-tasks-management/?utm_source=chatgpt.com)                           | Must build/compose                                                                                                                    | Strong                       |
| Long-running automation reliability             | Depends on engine/implementation                                                                                                                                                      | Strongly aligned [\[42\]](https://docs.temporal.io/workflows?utm_source=chatgpt.com)                                                  | Strong                       |
| Safe evolution/versioning                       | Process definition versioning + migration concerns [\[11\]](https://docs.camunda.io/docs/components/best-practices/operations/versioning-process-definitions/?utm_source=chatgpt.com) | Determinism + explicit versioning + replay testing [\[12\]](https://docs.temporal.io/develop/go/versioning?utm_source=chatgpt.com)    | Both, but bounded            |
| Audit/replay semantics                          | Requires design discipline                                                                                                                                                            | Built-in event history; must manage history growth [\[18\]](https://docs.temporal.io/workflow-execution/event?utm_source=chatgpt.com) | Strong if designed correctly |
| Time-to-MVP                                     | Often faster for human workflow UX                                                                                                                                                    | Often faster for complex automation correctness                                                                                       | Medium                       |

## Pitfalls this plan prevents and the guardrails to keep

This section validates your “pitfall list” with research-based guardrails and makes each pitfall measurable.

### Accidentally building a bespoke workflow engine

**Guardrail:** Don’t proceed past foundation without an evidence-based engine decision and a proven versioning strategy (for in-flight instances).  
- Camunda: emphasizes understanding versioning and migration implications for running instances. [\[11\]](https://docs.camunda.io/docs/components/best-practices/operations/versioning-process-definitions/?utm_source=chatgpt.com)  
- Temporal: requires determinism; safe evolution relies on explicit versioning methods and replay testing. [\[12\]](https://docs.temporal.io/develop/go/versioning?utm_source=chatgpt.com)

### Treating spreadsheets as blobs destroys auditability and automation safety

**Guardrail:** Artifact immutability + lineage is a “platform invariant,” grounded in artifact-centric BPM research. [\[13\]](https://research.ibm.com/publications/business-artifacts-with-guard-stage-milestone-lifecycles-managing-artifact-interactions-with-conditions-and-events?utm_source=chatgpt.com)

### Bolting security on later makes multi-tenant automation unsafe

**Guardrail:** Sandbox + policy must be implemented before meaningful automation is shipped.  
- Firecracker’s design rationale centers on minimizing attack surface for microVM isolation. [\[25\]](https://github.com/firecracker-microvm/firecracker?utm_source=chatgpt.com)  
- gVisor provides a sandboxed runtime integrated with container tooling. [\[45\]](https://gvisor.dev/docs/?utm_source=chatgpt.com)  
- NIST container security provides baseline threat/mitigation guidance. [\[27\]](https://nvlpubs.nist.gov/nistpubs/specialpublications/nist.sp.800-190.pdf?utm_source=chatgpt.com)  
- OPA externalizes policy decisions and supports consistent enforcement. [\[28\]](https://openpolicyagent.org/docs?utm_source=chatgpt.com)

### Permission logic scattered across UI becomes unfixable

**Guardrail:** Centralize authorization semantics; test them like core system logic.  
- Zanzibar demonstrates how complex access control becomes at scale and why uniform, relationship-based models are used for consistency and flexibility. [\[29\]](https://www.usenix.org/system/files/atc19-pang.pdf?utm_source=chatgpt.com)

### LLM-driven automation without constraints invites injection and runaway behavior

**Guardrail:** Treat LLMs as “untrusted and confusable”; use OWASP risk taxonomy and NCSC guidance; require approvals for high-risk actions; enforce budgets. [\[46\]](https://owasp.org/www-project-top-10-for-large-language-model-applications/?utm_source=chatgpt.com)

### Operating the system becomes the bottleneck

**Guardrail:** Bake operability into core deliverables (SLOs, golden signals, consistent telemetry keys).  
- SRE defines SLOs as targets over SLIs and recommends focusing on the four golden signals. [\[34\]](https://sre.google/sre-book/service-level-objectives/?utm_source=chatgpt.com)  
- OpenTelemetry semantic conventions exist to standardize observability attribute naming across code and services. [\[35\]](https://opentelemetry.io/docs/concepts/semantic-conventions/?utm_source=chatgpt.com)

If you want the next refinement, the most valuable “step up” from here is to convert the acceptance criteria above into a **single release-readiness checklist** that gates each progressive automation stage (Assist → Suggest → Draft → Execute), and to pair it with a **minimum viable governance loop** (ADR lifecycle, policy review cadence, and tenant onboarding runbooks) aligned to the multi-tenant SaaS model you choose (silo/pool/bridge). [\[47\]](https://docs.aws.amazon.com/wellarchitected/latest/saas-lens/silo-pool-and-bridge-models.html?utm_source=chatgpt.com)

[\[1\]](https://www.gartner.com/en/information-technology/glossary/hyperautomation?utm_source=chatgpt.com) Definition of Hyperautomation - Gartner Glossary

<https://www.gartner.com/en/information-technology/glossary/hyperautomation?utm_source=chatgpt.com>

[\[2\]](https://www.omg.org/intro/TripleCrown.pdf?utm_source=chatgpt.com) [\[22\]](https://www.omg.org/intro/TripleCrown.pdf?utm_source=chatgpt.com) [\[43\]](https://www.omg.org/intro/TripleCrown.pdf?utm_source=chatgpt.com) Bpmn, cmmn and dmn specifications at omg

<https://www.omg.org/intro/TripleCrown.pdf?utm_source=chatgpt.com>

[\[3\]](https://docs.temporal.io/develop/go/versioning?utm_source=chatgpt.com) [\[12\]](https://docs.temporal.io/develop/go/versioning?utm_source=chatgpt.com) [\[21\]](https://docs.temporal.io/develop/go/versioning?utm_source=chatgpt.com) Versioning - Go SDK \| Temporal Platform Documentation

<https://docs.temporal.io/develop/go/versioning?utm_source=chatgpt.com>

[\[4\]](https://docs.camunda.io/docs/components/best-practices/architecture/understanding-human-tasks-management/?utm_source=chatgpt.com) [\[14\]](https://docs.camunda.io/docs/components/best-practices/architecture/understanding-human-tasks-management/?utm_source=chatgpt.com) [\[41\]](https://docs.camunda.io/docs/components/best-practices/architecture/understanding-human-tasks-management/?utm_source=chatgpt.com) Understanding human task management \| Camunda 8 Docs

<https://docs.camunda.io/docs/components/best-practices/architecture/understanding-human-tasks-management/?utm_source=chatgpt.com>

[\[5\]](https://owasp.org/www-project-top-10-for-large-language-model-applications/?utm_source=chatgpt.com) [\[23\]](https://owasp.org/www-project-top-10-for-large-language-model-applications/?utm_source=chatgpt.com) [\[46\]](https://owasp.org/www-project-top-10-for-large-language-model-applications/?utm_source=chatgpt.com) OWASP Top 10 for Large Language Model Applications

<https://owasp.org/www-project-top-10-for-large-language-model-applications/?utm_source=chatgpt.com>

[\[6\]](https://www.omg.org/spec/BPMN/2.0.2/About-BPMN?utm_source=chatgpt.com) BPMN - Business Process Model and Notation

<https://www.omg.org/spec/BPMN/2.0.2/About-BPMN?utm_source=chatgpt.com>

[\[7\]](https://www.omg.org/spec/CMMN/1.1/About-CMMN?utm_source=chatgpt.com) CMMN – Case Management Modeling Notation

<https://www.omg.org/spec/CMMN/1.1/About-CMMN?utm_source=chatgpt.com>

[\[8\]](https://www.omg.org/dmn/?utm_source=chatgpt.com) [\[44\]](https://www.omg.org/dmn/?utm_source=chatgpt.com) Decision Model and Notation™ (DMN™)

<https://www.omg.org/dmn/?utm_source=chatgpt.com>

[\[9\]](https://docs.camunda.io/docs/components/concepts/workflow-patterns/?utm_source=chatgpt.com) [\[15\]](https://docs.camunda.io/docs/components/concepts/workflow-patterns/?utm_source=chatgpt.com) Workflow patterns \| Camunda 8 Docs

<https://docs.camunda.io/docs/components/concepts/workflow-patterns/?utm_source=chatgpt.com>

[\[10\]](https://scispace.com/pdf/adaptive-case-management-overview-and-research-challenges-2v9emet8ko.pdf?utm_source=chatgpt.com) Adaptive Case Management: Overview and Research ...

<https://scispace.com/pdf/adaptive-case-management-overview-and-research-challenges-2v9emet8ko.pdf?utm_source=chatgpt.com>

[\[11\]](https://docs.camunda.io/docs/components/best-practices/operations/versioning-process-definitions/?utm_source=chatgpt.com) Versioning process definitions

<https://docs.camunda.io/docs/components/best-practices/operations/versioning-process-definitions/?utm_source=chatgpt.com>

[\[13\]](https://research.ibm.com/publications/business-artifacts-with-guard-stage-milestone-lifecycles-managing-artifact-interactions-with-conditions-and-events?utm_source=chatgpt.com) Business artifacts with guard-stage-milestone lifecycles

<https://research.ibm.com/publications/business-artifacts-with-guard-stage-milestone-lifecycles-managing-artifact-interactions-with-conditions-and-events?utm_source=chatgpt.com>

[\[16\]](https://docs.camunda.io/docs/components/best-practices/development/testing-process-definitions/?utm_source=chatgpt.com) Testing process definitions

<https://docs.camunda.io/docs/components/best-practices/development/testing-process-definitions/?utm_source=chatgpt.com>

[\[17\]](https://docs.temporal.io/encyclopedia/workflow-message-passing?utm_source=chatgpt.com) [\[31\]](https://docs.temporal.io/encyclopedia/workflow-message-passing?utm_source=chatgpt.com) Temporal Workflow message passing - Signals, Queries, & ...

<https://docs.temporal.io/encyclopedia/workflow-message-passing?utm_source=chatgpt.com>

[\[18\]](https://docs.temporal.io/workflow-execution/event?utm_source=chatgpt.com) Events and Event History \| Temporal Platform Documentation

<https://docs.temporal.io/workflow-execution/event?utm_source=chatgpt.com>

[\[19\]](https://docs.temporal.io/self-hosted-guide/production-checklist?utm_source=chatgpt.com) Temporal Platform's production readiness checklist

<https://docs.temporal.io/self-hosted-guide/production-checklist?utm_source=chatgpt.com>

[\[20\]](https://docs.temporal.io/develop/safe-deployments?utm_source=chatgpt.com) Safely deploying changes to Workflow code

<https://docs.temporal.io/develop/safe-deployments?utm_source=chatgpt.com>

[\[24\]](https://www.ncsc.gov.uk/blog-post/prompt-injection-is-not-sql-injection?utm_source=chatgpt.com) Prompt injection is not SQL injection (it may be worse)

<https://www.ncsc.gov.uk/blog-post/prompt-injection-is-not-sql-injection?utm_source=chatgpt.com>

[\[25\]](https://github.com/firecracker-microvm/firecracker?utm_source=chatgpt.com) Secure and fast microVMs for serverless computing.

<https://github.com/firecracker-microvm/firecracker?utm_source=chatgpt.com>

[\[26\]](https://gvisor.dev/docs/?utm_source=chatgpt.com) [\[45\]](https://gvisor.dev/docs/?utm_source=chatgpt.com) What is gVisor?

<https://gvisor.dev/docs/?utm_source=chatgpt.com>

[\[27\]](https://nvlpubs.nist.gov/nistpubs/specialpublications/nist.sp.800-190.pdf?utm_source=chatgpt.com) Application Container Security Guide

<https://nvlpubs.nist.gov/nistpubs/specialpublications/nist.sp.800-190.pdf?utm_source=chatgpt.com>

[\[28\]](https://openpolicyagent.org/docs?utm_source=chatgpt.com) Open Policy Agent (OPA)

<https://openpolicyagent.org/docs?utm_source=chatgpt.com>

[\[29\]](https://www.usenix.org/system/files/atc19-pang.pdf?utm_source=chatgpt.com) Zanzibar: Google's Consistent, Global Authorization System

<https://www.usenix.org/system/files/atc19-pang.pdf?utm_source=chatgpt.com>

[\[30\]](https://www.uladshauchenka.com/p/how-to-write-a-good-product-requirements?utm_source=chatgpt.com) How to Write a Good Product Requirements Document (PRD)

<https://www.uladshauchenka.com/p/how-to-write-a-good-product-requirements?utm_source=chatgpt.com>

[\[32\]](https://docs.temporal.io/handling-messages?utm_source=chatgpt.com) Handling Signals, Queries, & Updates

<https://docs.temporal.io/handling-messages?utm_source=chatgpt.com>

[\[33\]](https://nvlpubs.nist.gov/nistpubs/ai/nist.ai.100-1.pdf?utm_source=chatgpt.com) Artificial Intelligence Risk Management Framework (AI ...

<https://nvlpubs.nist.gov/nistpubs/ai/nist.ai.100-1.pdf?utm_source=chatgpt.com>

[\[34\]](https://sre.google/sre-book/service-level-objectives/?utm_source=chatgpt.com) [\[36\]](https://sre.google/sre-book/service-level-objectives/?utm_source=chatgpt.com) Defining slo: service level objective meaning

<https://sre.google/sre-book/service-level-objectives/?utm_source=chatgpt.com>

[\[35\]](https://opentelemetry.io/docs/concepts/semantic-conventions/?utm_source=chatgpt.com) Semantic Conventions

<https://opentelemetry.io/docs/concepts/semantic-conventions/?utm_source=chatgpt.com>

[\[37\]](https://sre.google/sre-book/monitoring-distributed-systems/?utm_source=chatgpt.com) Chapter 6 - Monitoring Distributed Systems

<https://sre.google/sre-book/monitoring-distributed-systems/?utm_source=chatgpt.com>

[\[38\]](https://docs.aws.amazon.com/wellarchitected/latest/saas-lens/silo-pool-and-bridge-models.html?utm_source=chatgpt.com) [\[47\]](https://docs.aws.amazon.com/wellarchitected/latest/saas-lens/silo-pool-and-bridge-models.html?utm_source=chatgpt.com) Silo, Pool, and Bridge Models - SaaS Lens

<https://docs.aws.amazon.com/wellarchitected/latest/saas-lens/silo-pool-and-bridge-models.html?utm_source=chatgpt.com>

[\[39\]](https://learn.microsoft.com/en-us/azure/azure-sql/database/saas-tenancy-app-design-patterns?view=azuresql&utm_source=chatgpt.com) Multitenant SaaS database tenancy patterns - Azure SQL

<https://learn.microsoft.com/en-us/azure/azure-sql/database/saas-tenancy-app-design-patterns?view=azuresql&utm_source=chatgpt.com>

[\[40\]](https://csrc.nist.gov/pubs/sp/800/218/final?utm_source=chatgpt.com) Secure Software Development Framework (SSDF) Version 1.1

<https://csrc.nist.gov/pubs/sp/800/218/final?utm_source=chatgpt.com>

[\[42\]](https://docs.temporal.io/workflows?utm_source=chatgpt.com) Temporal Workflow \| Temporal Platform Documentation

<https://docs.temporal.io/workflows?utm_source=chatgpt.com>
