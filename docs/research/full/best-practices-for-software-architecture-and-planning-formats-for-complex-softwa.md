# Best Practices for Software Architecture and Planning Formats for Complex Software Projects

## Executive summary

Modern software architecture is best understood as a *set of decisions*—made to satisfy stakeholder concerns under constraints—plus the evidence that those decisions are sound and evolvable. Standards such as IEEE 1471 and ISO/IEC/IEEE 42010 formalize this stakeholder- and viewpoint-centric framing: architecture descriptions are inherently multi-view, and they exist to communicate, evaluate, guide change, and support governance. [\[1\]](https://people.eecs.ku.edu/~hossein/810/Project/IEEE-Stds/1471.pdf)

Top practitioners converge on a small number of durable mental models: modularity via information hiding (to localize change), quality attributes as first-class requirements (because they drive structure and trade-offs), distributed-systems realism (partitions exist; “consistency” must be defined precisely), and “production is the truth” (observability, resilience testing, and operational readiness are architecture work—not afterthoughts). [\[2\]](https://prl.khoury.northeastern.edu/img/p-tr-1971.pdf)

For decision-making, high-performing teams institutionalize lightweight-but-disciplined artifacts: Architecture Decision Records (ADRs) as an append-only memory (with alternatives and consequences), scenario-based tradeoff assessment (e.g., ATAM-style reasoning), and active risk management (risk registers and security-by-design evidence). [\[3\]](https://learn.microsoft.com/en-us/azure/well-architected/architect-role/architecture-decision-record)

Document formats in wide use cluster into: (a) viewpoint/view standards (IEEE 1471, ISO/IEC/IEEE 42010), (b) pragmatic templates (arc42), (c) diagramming models (C4), (d) operational excellence / “well-architected” review frameworks (AWS, Azure, Google Cloud), and (e) narrative proposal formats for product and project initiation (e.g., Amazon’s Working Backwards PR/FAQ). Their differences are less about “right vs wrong” and more about what decisions they’re optimized to surface and who needs to read them. [\[4\]](https://people.eecs.ku.edu/~hossein/810/Project/IEEE-Stds/1471.pdf)

Governance works best when it is continuous, blame-free, and proportionate to risk—emphasizing peer review, automation, and time-boxed reviews rather than heavyweight gates. Concrete exemplars include AWS’s guidance that reviews should be “hours not days” and a conversation, Google SRE’s Production Readiness Review (PRR) model, and decentralized “architecture advice process” approaches (seek advice from those affected and those with expertise). [\[5\]](https://docs.aws.amazon.com/wellarchitected/latest/framework/the-review-process.html)

## Core principles and mental models used by top practitioners

### Modularity and the “information hiding” change-localization model

A core architectural move is to decompose systems so that each module hides volatile design decisions behind stable interfaces—reducing the blast radius of change. David L. Parnas’ classic articulation of modularization argues that decomposition criteria should be chosen to improve flexibility and comprehensibility, explicitly motivating “information hiding” as a criterion. [\[6\]](https://prl.khoury.northeastern.edu/img/p-tr-1971.pdf)

From the viewpoint-based standards perspective, “separation of concerns” is operationalized via *views* (representations addressing particular concerns) and *viewpoints* (the conventions/templates for constructing views). IEEE 1471 explicitly centers stakeholders, concerns, views, and viewpoints as the structure of an architecture description, reflecting that no single representation can address all stakeholder concerns. [\[7\]](https://people.eecs.ku.edu/~hossein/810/Project/IEEE-Stds/1471.pdf)

A practical implication: your architecture documents should not be “one big narrative.” They should be a curated set of stable interfaces, clear ownership boundaries, and a small number of views that match recurring stakeholder questions (security, reliability, data flow, deployment, cost). This mirrors the ISO/IEC/IEEE 42010 framing that architecture descriptions are structured to address stakeholder concerns through viewpoints and model kinds. [\[8\]](https://www.iso.org/standard/74393.html)

### Quality attributes as first-class, scenario-driven requirements

Senior architects treat quality attributes (e.g., performance, modifiability, reliability, security) as primary drivers of structure and trade-offs—not as “non-functional leftovers.” The SEI’s Architecture Tradeoff Analysis Method (ATAM) is explicitly designed to reason about fitness with respect to multiple competing quality attributes, identify tradeoff points, and facilitate communication among stakeholders around those attributes. [\[9\]](https://www.sei.cmu.edu/library/file_redirect/1998_005_001_16646.pdf/)

Quantitatively, “reliability” and “availability” are often managed as measurable targets. A widely used engineering approximation expresses steady-state availability as $A = \\frac{MTBF}{MTBF + MTTR}$, connecting design and operations choices to expected uptime. [\[10\]](https://ocw.mit.edu/courses/2-611-marine-power-and-propulsion-fall-2006/8fd4b50ef794af75294c44aa555196c3_23reliability.pdf)

SRE-style practice makes this concrete through Service Level Objectives (SLOs) and error budgets: an error budget is 1 − *S**L**O*, turning reliability goals into a managed budget for change and experimentation. [\[11\]](https://sre.google/workbook/error-budget-policy/)

### Distributed-systems realism: CAP, precise consistency, and “don’t do bumper-sticker architecture”

In real distributed systems, network partitions (or, more generally, uncertain delay/loss in asynchronous networks) are not hypothetical. The CAP impossibility result formalizes a tradeoff under particular definitions and a specific system model. The Gilbert–Lynch proof frames its result in an asynchronous network model and clarifies that “consistency” corresponds to a strong notion (often discussed as linearizability). [\[12\]](https://www.cs.princeton.edu/courses/archive/spr22/cos418/papers/cap.pdf)

Practitioners emphasize that CAP is frequently misunderstood. For example, Martin Kleppmann argues you must use the proof’s precise definitions (e.g., availability as “every request to a non-failing node gets a non-error response”) or CAP-based labels become misleading; he argues CP/AP bucket labels oversimplify real systems. [\[13\]](https://martin.kleppmann.com/2015/05/11/please-stop-calling-databases-cp-or-ap.html)

A durable architectural heuristic emerges: replace slogans with explicit, testable semantics (e.g., “linearizable reads for balance updates,” “at-least-once event delivery with idempotent consumers,” “bounded staleness under partition”). This aligns with “architecture as decisions with consequences,” and it pairs naturally with decision logs and scenario-based review. [\[14\]](https://learn.microsoft.com/en-us/azure/well-architected/architect-role/architecture-decision-record)

### Resilience and graceful degradation as design obligations

Reliability and resilience are not only operational concerns; they shape topology, redundancy, failure domains, and recovery pathways. The Google Cloud reliability pillar explicitly defines reliability and resilience, recommends redundancy, fault-tolerant design, monitoring, and automated recovery, and maps guidance to principles including graceful degradation, testing recovery from failures, and postmortems. [\[15\]](https://docs.cloud.google.com/architecture/framework/reliability)

SRE launch readiness guidance shows how deeply architectural this becomes in practice—covering failure modes (machine/rack/cluster/datacenter/network), detection and backend failure handling, timeouts/retries, backup/restore, disaster recovery, and “monitoring the monitoring.” [\[16\]](https://sre.google/sre-book/launch-checklist/)

Chaos engineering is widely used as a resilience discipline: deliberately introducing failures under controlled conditions to uncover weaknesses before incidents. Both the “Principles of Chaos Engineering” and large-scale practice discussions emphasize empirical validation of system robustness. [\[17\]](https://principlesofchaos.org/)

### Observability and production thinking: architecture must be debuggable

Modern systems must be designed to be understood in production. OpenTelemetry defines itself as a vendor-neutral observability framework for instrumenting and exporting telemetry (traces, metrics, logs), and its observability primer explicitly frames telemetry as emitted behavioral data. [\[18\]](https://opentelemetry.io/docs/)

Google SRE monitoring guidance operationalizes observability into actionable signals: latency, traffic, errors, and saturation (the “four golden signals”), emphasizing that you can’t troubleshoot distributed systems without correlating perspectives (e.g., client vs server vs network). [\[19\]](https://sre.google/sre-book/monitoring-distributed-systems/)

A pragmatic architectural implication: any “architecture plan” is incomplete unless it specifies (a) the primary failure modes and detection signals, (b) the SLO/SLI definitions and dashboards, and (c) rollout/rollback and incident response mechanics. This is reiterated in both launch checklists and well-architected operational excellence guidance. [\[20\]](https://sre.google/sre-book/launch-checklist/)

### Ownership boundaries via domain-driven design and event-driven thinking

Domain-Driven Design motivates defining modeling boundaries where a consistent vocabulary and rules apply (bounded contexts), explicitly acknowledging that large domains cannot feasibly share a single unified model. This supports architectural decomposition that matches how teams reason about the business domain. [\[21\]](https://www.martinfowler.com/bliki/BoundedContext.html)

In service-oriented systems, data ownership becomes a central architecture constraint. The microservices literature explicitly discusses decentralizing data management (service-owned persistence) and the resulting implications: cross-service updates often require transactionless coordination, acceptance of eventual consistency, and compensating operations. [\[22\]](https://martinfowler.com/articles/microservices.html)

Event-driven architecture provides a structural approach to creation, processing, and consumption of events; CNCF’s glossary defines EDA in these terms, and CloudEvents standardizes event metadata for interoperability across platforms. [\[23\]](https://glossary.cncf.io/event-driven-architecture/)

A useful synthesis: treat “data ownership + events” as a contract boundary. Architectural documents should specify event schemas, delivery semantics, consumer idempotency expectations, and failure handling—because these choices set consistency and coupling properties more than the programming language does. [\[24\]](https://martinfowler.com/articles/microservices.html)

### Socio-technical constraints: Conway’s law and organizational design

Architectural outcomes reflect communication structures. Melvin E. Conway’s original paper states the thesis (often called Conway’s Law) that organizations designing systems produce designs that mirror their communication structures; the paper even frames the mapping as a homomorphism between organizational and system graphs. [\[25\]](https://www.melconway.com/research/committees.html)

Modern governance guidance often responds to this by emphasizing team interfaces and coupling. DORA research discusses “loosely coupled teams” as a performance capability, and DORA’s guidance on streamlining approvals argues for peer review and automation rather than slow, centralized approval gates. [\[26\]](https://dora.dev/capabilities/loosely-coupled-teams/)

Thoughtworks’ “architecture advice process” similarly advocates decentralized decision-making with a requirement to seek advice from those affected and those with expertise, supported by ADRs and advisory forums—explicitly challenging traditional architecture review boards as a default mechanism. [\[27\]](https://www.thoughtworks.com/en-de/radar/techniques/architecture-advice-process)

## Decision-making frameworks and core artifacts

### Architecture Decision Records as the “append-only memory” of architecture

An ADR is a compact record capturing an architecturally significant decision, its context, alternatives, and consequences. Microsoft’s guidance calls ADRs “one of the most important deliverables” for solution architects and recommends maintaining an ADR log from the onset through the workload lifespan as an append-only record. [\[28\]](https://learn.microsoft.com/en-us/azure/well-architected/architect-role/architecture-decision-record)

Thoughtworks popularized “lightweight architecture decision records,” recommending they be stored in source control so they remain in sync with code and survive team changes—a key evolutionary-architecture practice. [\[29\]](https://www.thoughtworks.com/radar/techniques/lightweight-architecture-decision-records)

The ADR community site and templates (including MADR) emphasize ADRs as justified design choices addressing architecturally significant requirements and provide standardized structures for decision logs. [\[30\]](https://adr.github.io/)

A practical ADR “anatomy” that is strongly supported by Microsoft’s recommended elements is:

-   Problem statement with context
-   Options considered
-   Decision outcome (including key tradeoffs)
-   Consequences (including risks and follow-up work), plus confidence level and links to supporting evidence [\[31\]](https://learn.microsoft.com/en-us/azure/well-architected/architect-role/architecture-decision-record)

### Scenario- and tradeoff-based evaluation: ATAM-style reasoning

ATAM is a structured method to understand tradeoffs and risks relative to multiple quality attributes. It is explicitly oriented toward identifying tradeoff points among attributes (e.g., performance vs modifiability), clarifying requirements, and structuring stakeholder communication about architectural fitness. [\[9\]](https://www.sei.cmu.edu/library/file_redirect/1998_005_001_16646.pdf/)

Even if you do not run a full ATAM workshop, the mental model is valuable: write scenarios (stimulus → environment → response measure), identify architectural approaches that address them, then locate sensitivity points and risks. The “ATAM-lite checklist” style is also echoed in industry guidance as a practical compromise for fast-moving teams. [\[32\]](https://www.sei.cmu.edu/library/file_redirect/1998_005_001_16646.pdf/)

### Tradeoff matrices and “pillar-based” decision scoring

A common lightweight decision technique is to score options against a stable rubric (often the same categories used in well-architected frameworks). For example, Microsoft’s Azure Architecture Blog explicitly frames tradeoffs via the five Azure Well-Architected pillars and suggests decision matrices to rate options across pillars. [\[33\]](https://techcommunity.microsoft.com/blog/azurearchitectureblog/how-great-engineers-make-architectural-decisions-%E2%80%94-adrs-trade-offs-and-an-atam-l/4463013)

AWS similarly frames architectural thinking around a consistent set of best-practice questions and pillars, and the Well-Architected Tool provides a repeatable assessment mechanism that produces improvement actions—functionally akin to an organization-level tradeoff and risk maturity loop. [\[34\]](https://docs.aws.amazon.com/wellarchitected/latest/framework/welcome.html)

### Risk registers and evidence-based security artifacts

Risk management standards emphasize repeatable processes: ISO 31000 describes identifying, analyzing, evaluating, treating, monitoring, and communicating risks, and NIST SP 800-30 provides guidance for conducting risk assessments to inform courses of action in response to identified risks. [\[35\]](https://www.iso.org/standard/65694.html)

In project and program practice, the “risk register” is a central output artifact; PMI materials explicitly describe the risk register as a major output containing listed risks, with attributes such as description and ownership (and often probability/impact, triggers, and response strategies). [\[36\]](https://www.pmi.org/learning/library/project-risk-management-success-tool-6078)

For software security, top organizations treat *design review and threat modeling* as first-class artifacts. Microsoft’s SDL makes threat modeling a core engineering technique to identify threats, vulnerabilities, and countermeasures and to shape design. NIST’s SSDF frames secure software development as a set of fundamental practices and explicitly discusses artifacts as evidence of secure practices. [\[37\]](https://www.microsoft.com/en-us/securityengineering/sdl/threatmodeling)

    flowchart TD
    A[Trigger: architecturally significant decision] --> B[Write problem statement & constraints]
    B --> C[Identify stakeholders & quality attributes]
    C --> D[Generate 2-4 viable options]
    D --> E[Evaluate trade-offs via scenarios, cost, and risk]
    E --> F{One-way door / hard to reverse?}
    F -->|Yes| G[Deeper review: prototype, security review, ATAM-lite]
    F -->|No| H[Lightweight review: peer advice, quick scoring]
    G --> I[Select option]
    H --> I
    I --> J[Record ADR: decision + rationale + consequences]
    J --> K[Implement: flags, staged rollout, rollback plan]
    K --> L[Observe in production: SLIs/SLOs, alerts, logs/traces]
    L --> M{New data or constraints changed?}
    M -->|Yes| N[Supersede ADR; revisit options]
    M -->|No| O[Archive evidence; continue monitoring]

## Concrete document formats and project-plan templates

### Comparing common formats

The following table focuses on “what question does this format force you to answer?”—because that is the practical differentiator across templates.

| Format / family                               | Primary forcing function                                                            | Typical output                                                                       | Typical audience                         | Best fit                                                                                                                                                                                       |
|-----------------------------------------------|-------------------------------------------------------------------------------------|--------------------------------------------------------------------------------------|------------------------------------------|------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| ISO/IEC/IEEE 42010, IEEE 1471                 | Stakeholders & concerns → viewpoints → views; multi-view consistency; rationale     | Architecture Description with defined viewpoints/views and inconsistencies/rationale | Mixed stakeholders, auditors, architects | Complex systems, regulated environments, multi-team programs [\[38\]](https://www.iso.org/standard/74393.html)                                                                                 |
| C4 model                                      | Consistent, hierarchical architectural diagrams (context→container→component→code)  | Diagram set; optionally dynamic/deployment diagrams                                  | Engineers + broader stakeholders         | Communicating structure quickly and consistently [\[39\]](https://c4model.com/)                                                                                                                |
| arc42                                         | “Cabinet of drawers” template: a complete but tailorable set of architecture topics | 12-section architecture doc (quality goals, views, decisions, risks, glossary)       | Broad: devs, ops, PM, auditors           | Teams needing completeness with pragmatic structure [\[40\]](https://arc42.org/overview)                                                                                                       |
| Well-Architected (AWS / Azure / Google Cloud) | Pillar-based quality review and improvement actions                                 | Answers to pillar checklists + action backlog                                        | Architects + platform/ops + leadership   | Ongoing governance and continuous improvement [\[41\]](https://docs.aws.amazon.com/wellarchitected/latest/framework/welcome.html)                                                              |
| Working Backwards PR/FAQ (Amazon)             | Customer-centric narrative → feasibility & cost/risk clarity                        | 1-page PR + ≤5-page FAQ (iterated drafts)                                            | Leadership + cross-functional reviewers  | New products/initiatives; decision readiness [\[42\]](https://www.aboutamazon.com/news/workplace/an-insider-look-at-amazons-culture-and-processes)                                             |
| ADR log (MADR / similar)                      | Preserve decision rationale and alternatives; enable evolution                      | Append-only decisions in repo                                                        | Engineers, future maintainers            | Ongoing architecture evolution at feature cadence [\[43\]](https://learn.microsoft.com/en-us/azure/well-architected/architect-role/architecture-decision-record)                               |
| Open-source RFC/KEP templates                 | Community governance; explicit tradeoffs, rollout, risks                            | Proposal docs with standard sections                                                 | Maintainers + contributors               | Large-scale change proposals; transparent review [\[44\]](https://raw.githubusercontent.com/kubernetes/enhancements/a86942e8ba802d0035ec7d4a9c992f03bca7dce9/keps/NNNN-kep-template/README.md) |
| IEEE 1058 SPMP                                | Standardized software project management plan contents                              | Software Project Management Plan                                                     | PM, engineering leads, QA                | Large projects needing formal planning structure [\[45\]](https://standards.ieee.org/standard/1058-1998.html)                                                                                  |

### Exemplar outlines for major standards and company formats

#### IEEE 1471 style architecture description outline

IEEE 1471 specifies a conceptual framework (stakeholders, concerns, viewpoints, views) and a set of required constituents for a conforming architectural description, including identification/version info, stakeholder concerns, viewpoint specifications with rationale, views, known inconsistencies, and architecture rationale. [\[7\]](https://people.eecs.ku.edu/~hossein/810/Project/IEEE-Stds/1471.pdf)

A pragmatic outline that mirrors those required constituents is:

-   Architecture description identification (system scope, version, status)
-   Stakeholders and their concerns (quality attributes, constraints, goals)
-   Selected viewpoints (what concerns each addresses; notations/models used; rationale)
-   Views produced under each viewpoint (key models and explanations)
-   Known inconsistencies / open issues across views
-   Rationale and decision record pointers (e.g., ADR index) [\[46\]](https://people.eecs.ku.edu/~hossein/810/Project/IEEE-Stds/1471.pdf)

#### ISO/IEC/IEEE 42010 style architecture description outline

ISO/IEC/IEEE 42010:2022 specifies requirements for the structure and expression of an architecture description and introduces requirements for architecture description frameworks, languages, viewpoints, and model kinds. It also distinguishes the architecture of an entity from an architecture description of it. [\[8\]](https://www.iso.org/standard/74393.html)

A minimal “42010-compliant-in-spirit” outline (useful even if you don’t fully implement the standard) is:

-   Entity of interest, scope, and context boundaries
-   Stakeholders, concerns, and priorities (including regulatory concerns if applicable)
-   Architecture viewpoints and model kinds (definition and applicability)
-   Architecture views (the actual models/diagrams/specs)
-   Decision and rationale recording (often by linking to ADRs)
-   Cross-view correspondences, inconsistencies, and resolution plan [\[47\]](https://www.iso.org/standard/74393.html)

#### C4 model architecture communication packet

The C4 model explicitly defines hierarchical abstractions (software system, container, component, code) and matching hierarchical diagrams (context, container, component, code), plus supporting diagrams (landscape, dynamic, deployment). [\[39\]](https://c4model.com/)

A practical “C4 packet” for projects is:

-   System context diagram + narrative (users, external systems, trust boundaries)
-   Container diagram + narrative (major runtime units; data stores; protocols)
-   Component diagrams for key containers (only where complexity warrants it)
-   Deployment diagram(s) for key environments (prod, staging)
-   Dynamic diagram(s) for key sequences (critical flows, failure cases)
-   Link each diagram set to ADRs for major choices and tradeoffs [\[48\]](https://c4model.com/)

#### arc42 architecture documentation template outline

arc42 provides an explicit 12-section template covering goals, constraints, context, solution strategy, building blocks, runtime, deployment, crosscutting concepts, decisions, quality requirements, risks/tech debt, and glossary. [\[40\]](https://arc42.org/overview)

A key strength is that it already includes architecture decisions and risks as first-class sections, aligning naturally with ADR logs and risk registers. [\[49\]](https://arc42.org/overview)

#### Well-Architected frameworks as living review artifacts

AWS frames the Well-Architected Framework as a way to understand tradeoffs and evaluate architectures consistently, and it explicitly positions the review process as blame-free, lightweight (“hours not days”), and a conversation rather than an audit—with outcomes as prioritized improvement actions. [\[50\]](https://docs.aws.amazon.com/wellarchitected/latest/framework/welcome.html)

Azure describes its Well-Architected Framework as quality-driven tenets plus decision points and review tools, organized around five pillars (reliability, security, cost optimization, operational excellence, performance efficiency), emphasizing balancing tradeoffs and iterative improvement over time. [\[51\]](https://learn.microsoft.com/en-us/azure/well-architected/)

Google Cloud’s Well-Architected Framework similarly organizes guidance into pillars (operations, security/privacy/compliance, reliability, cost, performance, sustainability) and cross-pillar perspectives, providing core principles such as “design for change.” [\[52\]](https://docs.cloud.google.com/architecture/framework)

A practical outline that works across all three is:

-   Workload overview + business objectives
-   Pillar-by-pillar assessment (current state, risks, gaps)
-   Tradeoffs explicitly accepted (and why)
-   Improvement backlog (ranked by user impact and risk reduction)
-   Evidence links (diagrams, dashboards, incident history, ADRs) [\[53\]](https://docs.aws.amazon.com/wellarchitected/latest/framework/the-review-process.html)

#### Working Backwards PR/FAQ and narrative memos

Amazon’s Working Backwards process is described as a systematic way to vet ideas and create products, starting from the customer experience and iterating backward to achieve clarity. The primary tool is a PR/FAQ narrative, and the About Amazon excerpt specifies norms such as a PR portion under one page and an FAQ portion of five pages or less, with multiple drafts and reviews to refine, debate, and clarify feasibility and cost. [\[42\]](https://www.aboutamazon.com/news/workplace/an-insider-look-at-amazons-culture-and-processes)

A practical PR/FAQ outline (as reflected in Working Backwards guidance) is:

-   Press release: product name, customer segment, benefit headline, launch framing, problem statement (customer perspective), solution summary
-   FAQ: customer FAQs, internal feasibility questions, cost/complexity, risks, dependencies, operational considerations, and success metrics [\[54\]](https://workingbackwards.com/concepts/working-backwards-pr-faq-process/)

This narrative style is consistent with the broader claim (attributed to leadership practice) that narrative memos force clearer thinking than slides by requiring coherent connected reasoning. [\[55\]](https://www.businessinsider.com/jeff-bezos-email-against-powerpoint-presentations-2015-7)

### Project-plan standards and regulated templates

For formal project planning, IEEE 1058-1998 defines expected content for Software Project Management Plans (SPMPs) and identifies required plan elements applicable across project types and sizes. [\[45\]](https://standards.ieee.org/standard/1058-1998.html)

ISO/IEC/IEEE 12207 defines software lifecycle processes (as processes rather than prescribing one lifecycle model), and ISO/IEC/IEEE 15289 specifies purpose and content of lifecycle information items (documentation), supporting organizations that need consistent, auditable documentation sets. [\[56\]](https://www.iso.org/standard/63712.html)

For high-assurance environments, NASA publishes software management plan templates and supporting products aligned to NASA software engineering requirements, illustrating how plan templates become compliance evidence. [\[57\]](https://sw-eng.larc.nasa.gov/supporting-products/)

### Recommended templates

The sections below are designed to be adaptable to project size, domain, regulatory requirements, and team maturity; the intent is to provide “default structures” that you tailor by risk and stakeholder needs rather than adopting rigidly. [\[58\]](https://www.iso.org/standard/65694.html)

#### Lightweight agile plan template

| Section                        | Purpose                                           | Expected audience       | Typical length                                                                                                                                                                     |
|--------------------------------|---------------------------------------------------|-------------------------|------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| Problem statement and goals    | Align on what is being solved and why             | All stakeholders        | 0.25–0.5 page [\[28\]](https://learn.microsoft.com/en-us/azure/well-architected/architect-role/architecture-decision-record)                                                       |
| Non-goals / out of scope       | Prevent scope creep and hidden expectations       | PM, eng, reviewers      | 0.25 page [\[59\]](https://www.industrialempathy.com/posts/design-docs-at-google/)                                                                                                 |
| Context and system boundary    | Clarify external dependencies and interfaces      | Eng, ops, security      | 0.5 page + diagram [\[60\]](https://c4model.com/)                                                                                                                                  |
| Proposed approach (high level) | Describe the “shape” of the solution              | Eng                     | 0.5–1 page [\[39\]](https://c4model.com/)                                                                                                                                          |
| Alternatives considered        | Make tradeoffs explicit; reduce re-litigation     | Eng, future maintainers | 0.5 page [\[61\]](https://learn.microsoft.com/en-us/azure/well-architected/architect-role/architecture-decision-record)                                                            |
| Key tradeoffs (rubric)         | Show what was optimized and what wasn’t           | Leadership, reviewers   | 0.5 page [\[62\]](https://techcommunity.microsoft.com/blog/azurearchitectureblog/how-great-engineers-make-architectural-decisions-%E2%80%94-adrs-trade-offs-and-an-atam-l/4463013) |
| Risks and mitigations          | Surface “unknowns” and plan to reduce them        | Eng leads, PM           | 0.5 page [\[63\]](https://www.iso.org/standard/65694.html)                                                                                                                         |
| Observability & ops notes      | Define initial SLIs/SLOs, telemetry, and runbooks | Ops/SRE                 | 0.5 page [\[64\]](https://sre.google/sre-book/monitoring-distributed-systems/)                                                                                                     |
| Rollout & rollback             | Reduce “launch uncertainty”; ensure reversibility | Eng, ops                | 0.25–0.5 page [\[65\]](https://sre.google/sre-book/launch-checklist/)                                                                                                              |
| ADR pointer                    | Record the core decision(s) as ADR(s)             | Eng                     | 1–3 ADRs [\[66\]](https://learn.microsoft.com/en-us/azure/well-architected/architect-role/architecture-decision-record)                                                            |

#### Comprehensive architecture + delivery plan template

| Section                                 | Purpose                                            | Expected audience     | Typical length                                                                                                             |
|-----------------------------------------|----------------------------------------------------|-----------------------|----------------------------------------------------------------------------------------------------------------------------|
| Architecture description identification | Versioning, scope, status                          | All                   | 0.5 page [\[67\]](https://people.eecs.ku.edu/~hossein/810/Project/IEEE-Stds/1471.pdf)                                      |
| Stakeholders, concerns, constraints     | Make concerns explicit; anchor viewpoints          | All                   | 1–3 pages [\[68\]](https://people.eecs.ku.edu/~hossein/810/Project/IEEE-Stds/1471.pdf)                                     |
| Quality attribute scenarios             | Quantify “ilities” via measurable scenarios        | Architects, reviewers | 2–6 pages [\[69\]](https://www.sei.cmu.edu/library/file_redirect/1998_005_001_16646.pdf/)                                  |
| Views and viewpoints (model set)        | Produce multi-view description and ensure coverage | Architects, engineers | 5–20 pages [\[67\]](https://people.eecs.ku.edu/~hossein/810/Project/IEEE-Stds/1471.pdf)                                    |
| C4 diagram set (where applicable)       | Provide consistent structural diagrams             | Engineers             | 3–10 diagrams [\[39\]](https://c4model.com/)                                                                               |
| Data ownership and contracts            | Define bounded contexts, APIs/events, schema rules | Eng, data, security   | 2–10 pages [\[70\]](https://www.martinfowler.com/bliki/BoundedContext.html)                                                |
| Security architecture & threat modeling | Identify threats, trust boundaries, mitigations    | Security, eng         | 2–8 pages [\[71\]](https://www.microsoft.com/en-us/securityengineering/sdl/threatmodeling)                                 |
| Operational readiness plan              | SLOs, monitoring, incident response, capacity plan | SRE/ops, eng          | 3–10 pages [\[72\]](https://sre.google/sre-book/evolving-sre-engagement-model/)                                            |
| Architecture decision log               | Full ADR log; supersession strategy                | Eng, auditors         | 10–100 ADRs [\[61\]](https://learn.microsoft.com/en-us/azure/well-architected/architect-role/architecture-decision-record) |
| Risk register                           | Track risks, owners, triggers, treatments          | PMO, leads            | 1–5 pages + ongoing [\[73\]](https://www.iso.org/standard/65694.html)                                                      |
| Project management plan (SPMP-style)    | Staffing, schedule, controls, standards            | PMO, leadership       | 10–40 pages [\[45\]](https://standards.ieee.org/standard/1058-1998.html)                                                   |
| Review cadence and governance           | Define review types, gates, and evolution model    | Leadership, eng       | 1–3 pages [\[74\]](https://docs.aws.amazon.com/wellarchitected/latest/framework/the-review-process.html)                   |

## Governance, reviews, and architecture evolution

### Governance archetypes and when they fit

A useful taxonomy is “centralized board” vs “federated guidance” vs “fully decentralized with advice obligations,” with each model’s viability depending on risk, regulatory pressure, and team maturity.

-   **Centralized review board (heavyweight)** can be appropriate when external regulation demands formal approval evidence, but it risks becoming a bottleneck if it is decoupled from delivery teams—an issue repeatedly cautioned against in modern governance research and practice. [\[75\]](https://www.thoughtworks.com/en-de/radar/techniques/architecture-advice-process)
-   **Federated review (lightweight, continuous)** matches AWS guidance: reviews should be consistent, blame-free, lightweight, and continuous as the architecture evolves, producing prioritized actions rather than audit outcomes. [\[76\]](https://docs.aws.amazon.com/wellarchitected/latest/framework/the-review-process.html)
-   **Decentralized “advice process”** pushes decisions to those closest to the work but requires structured advice-seeking and durable decision records to prevent fragmentation; Thoughtworks explicitly positions this as an alternative to ARBs and emphasizes ADRs and advisory forums as stabilizers. [\[77\]](https://www.thoughtworks.com/en-de/radar/techniques/architecture-advice-process)

### Review cadences that scale

In practice, high-performing organizations combine cadence types rather than relying on one “big review”:

-   **Per-decision**: ADR created/superseded when architecturally significant decisions occur; Microsoft recommends consistent record anatomy and storing ADRs with workload documentation as a single source of truth. [\[28\]](https://learn.microsoft.com/en-us/azure/well-architected/architect-role/architecture-decision-record)
-   **Per-milestone**: pre-launch and go-live readiness reviews. Google’s launch checklist and PRR model show milestone-driven rigor focused on failure handling, monitoring, capacity, and operational readiness prerequisites. [\[78\]](https://sre.google/sre-book/launch-checklist/)
-   **Periodic hygiene**: AWS recommends Well-Architected reviews at key milestones (early design, before go-live) and ongoing hygiene to prevent architectural degradation, explicitly tying this to how AWS internal RCA learnings feed back into review questions. [\[76\]](https://docs.aws.amazon.com/wellarchitected/latest/framework/the-review-process.html)
-   **Incident-driven evolution**: postmortems and reliability learning loops are treated as architecture inputs (e.g., new controls, new observability requirements, simplification mandates). This is consistent with Google Cloud reliability practices around learning and postmortems and AWS’s RCA feedback loop framing. [\[79\]](https://docs.cloud.google.com/architecture/framework/reliability)

### Governance principles that reduce friction

Three governance principles appear consistently across authoritative sources:

Blame-free, learning-oriented reviews (AWS explicitly recommends blame-free review conversations; SRE culture emphasizes learning from failure) reduce defensive behavior and increase disclosure of real risks. [\[80\]](https://docs.aws.amazon.com/wellarchitected/latest/framework/the-review-process.html)

Prefer peer review and automation over slow centralized approvals. DORA’s guidance on streamlining approvals argues for embedding approvals into the development process with peer review plus automation for early detection. [\[81\]](https://dora.dev/capabilities/streamlining-change-approval/)

Treat governance outputs as actionable backlogs, not “pass/fail.” AWS frames the output as a set of actions to improve customer experience and recommends prioritizing issues based on business context. [\[76\]](https://docs.aws.amazon.com/wellarchitected/latest/framework/the-review-process.html)

## Examples of real-world architecture documents and primary-source exemplars

### Kubernetes Enhancement Proposals

Kubernetes’ KEP process and template illustrate how large ecosystems standardize architectural change proposals. The KEP template structure explicitly drives authors to articulate risks and mitigations, rollout/upgrade/rollback planning, monitoring requirements (including SLOs/SLIs), scalability considerations, and troubleshooting—embedding production concerns into design proposals. [\[82\]](https://github.com/kubernetes/enhancements/blob/master/keps/sig-architecture/0000-kep-process/README.md)

### Rust RFCs

Rust’s RFC template provides a strongly structured format (summary, motivation, guide-level explanation, reference-level explanation, drawbacks, rationale and alternatives, unresolved questions), and later evolution explicitly adds a “future possibilities” section—demonstrating how proposal formats evolve to capture long-term consequences. [\[83\]](https://github.com/rust-lang/rfcs/blob/master/0000-template.md)

### Google SRE launch and readiness artifacts

Google’s Launch Coordination Checklist is a concrete, checklist-form architecture+ops artifact that explicitly enumerates architecture sketching, redundancy expectations, failure mode responses, monitoring strategy, security review, rollout mechanics, and scalability growth planning. [\[16\]](https://sre.google/sre-book/launch-checklist/)

Google’s PRR model shows a governance process that starts with reliability needs, assesses maturity across production axes (instrumentation, capacity planning, change management, etc.), identifies improvements, and transitions operational responsibility when readiness standards are met. [\[84\]](https://sre.google/sre-book/evolving-sre-engagement-model/)

### AWS Well-Architected reviews as governance-in-document-form

AWS’s review process guidance is an unusually explicit primary source for how a large provider operationalizes architectural governance: it calls reviews conversational and blame-free, recommends “hours not days,” encourages continuous review over one-time audits, and ties review questions to recurring RCA themes. [\[76\]](https://docs.aws.amazon.com/wellarchitected/latest/framework/the-review-process.html)

### ADRs as an institutional memory artifact

Microsoft’s ADR guidance provides a primary-source outline of what an ADR should contain (problem context, options, decision outcome, tradeoffs, confidence level) and where it should live (openly with workload documentation; linked to operational excellence practices). [\[28\]](https://learn.microsoft.com/en-us/azure/well-architected/architect-role/architecture-decision-record)

Thoughtworks’ Technology Radar entry provides a primary-source rationale for ADRs in evolutionary architecture and a concrete recommendation to store ADRs in source control rather than a separate wiki. [\[29\]](https://www.thoughtworks.com/radar/techniques/lightweight-architecture-decision-records)

## Common pitfalls and mitigation strategies

### Treating architecture as a one-time document instead of a living decision system

Pitfall: teams produce a “big design doc” that goes stale, while decisions continue informally. Mitigation: make ADRs append-only and created at the time of decision; link ADRs to code changes and keep them where engineers work (repo). [\[85\]](https://learn.microsoft.com/en-us/azure/well-architected/architect-role/architecture-decision-record)

### Over-reliance on a single view or a single diagram type

Pitfall: forcing everything into one diagram or one narrative loses stakeholder concerns. Mitigation: adopt a viewpoint/view approach (IEEE 1471 / ISO 42010 mindset), using a small set of recurring views and explicitly recording inconsistencies and open issues. [\[67\]](https://people.eecs.ku.edu/~hossein/810/Project/IEEE-Stds/1471.pdf)

### “CAP theater” and ambiguous consistency language

Pitfall: labeling systems “CP/AP” without defining semantics leads to poor tradeoffs and miscommunication. Mitigation: define consistency requirements precisely (e.g., linearizability vs bounded staleness) and reason in scenarios; use ADRs to preserve the chosen semantics and their costs. [\[86\]](https://martin.kleppmann.com/2015/05/11/please-stop-calling-databases-cp-or-ap.html)

### Ignoring production readiness until late

Pitfall: architecture documents omit failure modes, observability, rollout/rollback, and capacity planning. Mitigation: adopt readiness checklists (SRE launch checklist elements), implement PRR-style reviews for high-criticality systems, and ensure well-architected reviews are done early and before go-live. [\[87\]](https://sre.google/sre-book/launch-checklist/)

### Heavy governance that becomes a delivery bottleneck

Pitfall: centralized ARBs/CABs slow teams, create shadow decisions, and reduce learning velocity. Mitigation: shift toward peer review + automation and advice-based processes; keep reviews lightweight and action-oriented; escalate only “one-way door” decisions. [\[88\]](https://dora.dev/capabilities/streamlining-change-approval/)

### Unclear domain boundaries and data ownership

Pitfall: cross-team coupling increases because bounded contexts and ownership are vague; shared databases and distributed transactions become “accidental coupling.” Mitigation: define bounded contexts explicitly and map interrelationships; prefer explicit integration contracts and document eventual consistency/compensation flows. [\[89\]](https://www.martinfowler.com/bliki/BoundedContext.html)

### Security treated as a downstream testing activity

Pitfall: design choices create irreversible exposure (e.g., missing trust boundaries, weak identity assumptions). Mitigation: institutionalize threat modeling and security design review as architecture artifacts; use SSDF-style evidence artifacts and map them to your SDLC. [\[37\]](https://www.microsoft.com/en-us/securityengineering/sdl/threatmodeling)

## Adoption playbook and first 90 days

### Adoption guidelines that scale to unknown constraints

Because project size, domain criticality, regulatory environment, and team maturity are unspecified, the safest strategy is to adopt a *portfolio of artifacts* with explicit tailoring rules: “default lightweight, escalate by risk.” This is consistent with ISO 31000’s risk-based approach and with SSDF’s explicit stance that practices must be adopted based on relevance and effectiveness for your threats. [\[90\]](https://www.iso.org/standard/65694.html)

A practical adoption stance:

Define “architecturally significant” as “a decision that materially impacts one or more quality attributes, team boundaries, cost profile, or long-term evolvability,” aligning ADR use to architecturally significant requirements. [\[91\]](https://learn.microsoft.com/en-us/azure/well-architected/architect-role/architecture-decision-record)

Standardize a small set of document types. For many organizations, an effective minimal set is: (1) a lightweight design/architecture plan (C4 + goals + risks), (2) ADRs, (3) readiness checklist (for production/go-live), and (4) periodic well-architected review results and action backlog. [\[92\]](https://c4model.com/)

Create a “traceability triangle”: every major decision should link to (a) the problem/goal, (b) the evidence (measurements, prototypes, incidents), and (c) the operational signals (SLIs/SLOs). This is directly supported by SRE error-budget and monitoring guidance and by ADR guidance emphasizing context and implications. [\[93\]](https://sre.google/workbook/error-budget-policy/)

### First 90 days checklist

**Days 1–30: establish the minimum viable architecture practice** - Publish a single repo- or workspace-wide template set: Lightweight Plan template + ADR template + review checklist skeleton, and define what counts as “architecturally significant.” [\[94\]](https://learn.microsoft.com/en-us/azure/well-architected/architect-role/architecture-decision-record)  
- Choose a diagram standard (often C4) and mandate “at least system context + container diagrams” for any significant project, linked to owners and interfaces. [\[60\]](https://c4model.com/)  
- Define baseline telemetry expectations (logs/metrics/traces) and a minimal reliability rubric (e.g., golden signals + initial SLO draft). [\[95\]](https://opentelemetry.io/docs/)

**Days 31–60: run the first governance loops** - Pilot ADRs on one high-visibility initiative; require alternatives + tradeoffs + explicit consequences; store in repo. [\[85\]](https://learn.microsoft.com/en-us/azure/well-architected/architect-role/architecture-decision-record)  
- Run one lightweight architecture review modeled on AWS guidance (blame-free, conversational, “hours not days”), producing an action list. [\[76\]](https://docs.aws.amazon.com/wellarchitected/latest/framework/the-review-process.html)  
- Add a production readiness checklist gate for “go-live critical” services (use SRE launch checklist categories as seeds). [\[78\]](https://sre.google/sre-book/launch-checklist/)

**Days 61–90: scale safely** - Establish a review cadence: per-decision ADRs + milestone readiness reviews + quarterly well-architected hygiene for critical workloads. [\[96\]](https://learn.microsoft.com/en-us/azure/well-architected/architect-role/architecture-decision-record)  
- Add risk register discipline for programs with significant uncertainty or compliance exposure (owners, triggers, treatments). [\[73\]](https://www.iso.org/standard/65694.html)  
- Embed security-by-design: threat modeling for new trust boundaries and sensitive data flows; collect SSDF-aligned evidence artifacts. [\[71\]](https://www.microsoft.com/en-us/securityengineering/sdl/threatmodeling)

### Bibliography of prioritized sources

Primary standards and authoritative methods: - IEEE Std 1471-2000[\[97\]](https://learn.microsoft.com/en-us/azure/well-architected/architect-role/architecture-decision-record) (architecture description conceptual framework; conformance elements). [\[7\]](https://people.eecs.ku.edu/~hossein/810/Project/IEEE-Stds/1471.pdf)  
- ISO/IEC/IEEE 42010:2022[\[98\]](https://www.martinfowler.com/bliki/BoundedContext.html) (architecture description requirements; viewpoints, frameworks, ADLs). [\[8\]](https://www.iso.org/standard/74393.html)  
- Software Engineering Institute[\[99\]](https://people.eecs.ku.edu/~hossein/810/Project/IEEE-Stds/1471.pdf) ATAM technical report (quality attribute tradeoff method). [\[9\]](https://www.sei.cmu.edu/library/file_redirect/1998_005_001_16646.pdf/)  
- ISO 31000:2018[\[100\]](https://learn.microsoft.com/en-us/azure/well-architected/architect-role/architecture-decision-record) risk management overview (process framing). [\[101\]](https://www.iso.org/standard/65694.html)  
- NIST SP 800-30 Rev. 1[\[102\]](https://learn.microsoft.com/en-us/azure/well-architected/architect-role/architecture-decision-record) risk assessment guidance. [\[103\]](https://csrc.nist.gov/pubs/sp/800/30/r1/final)

Seminal papers and enduring theory: - David L. Parnas[\[104\]](https://learn.microsoft.com/en-us/azure/well-architected/architect-role/architecture-decision-record) on information hiding modularity. [\[6\]](https://prl.khoury.northeastern.edu/img/p-tr-1971.pdf)  
- Melvin E. Conway[\[105\]](https://learn.microsoft.com/en-us/azure/well-architected/architect-role/architecture-decision-record) on organizational communication structure mirroring system design. [\[25\]](https://www.melconway.com/research/committees.html)  
- Seth Gilbert[\[106\]](https://martin.kleppmann.com/2015/05/11/please-stop-calling-databases-cp-or-ap.html) and Nancy Lynch[\[107\]](https://prl.khoury.northeastern.edu/img/p-tr-1971.pdf) on CAP feasibility in asynchronous networks. [\[12\]](https://www.cs.princeton.edu/courses/archive/spr22/cos418/papers/cap.pdf)  
- Philippe Kruchten[\[108\]](https://www.thoughtworks.com/radar/techniques/lightweight-architecture-decision-records) on the 4+1 view model. [\[109\]](https://www.cs.ubc.ca/~gregor/teaching/papers/4%2B1view-architecture.pdf)

Company and ecosystem “how we do it” primary sources: - Amazon Web Services[\[110\]](https://www.sei.cmu.edu/library/file_redirect/1998_005_001_16646.pdf/) Well-Architected Framework and review process guidance. [\[50\]](https://docs.aws.amazon.com/wellarchitected/latest/framework/welcome.html)  
- Google Cloud[\[111\]](https://github.com/kubernetes/enhancements/blob/master/keps/sig-architecture/0000-kep-process/README.md) Well-Architected Framework pillars and core principles. [\[112\]](https://docs.cloud.google.com/architecture/framework)  
- Microsoft[\[113\]](https://c4model.com/) Azure Well-Architected Framework and ADR guidance; SDL/threat modeling. [\[114\]](https://learn.microsoft.com/en-us/azure/well-architected/)  
- NIST SP 800-218[\[115\]](https://sre.google/sre-book/launch-checklist/) (SSDF) for secure-by-design evidence practices. [\[116\]](https://nvlpubs.nist.gov/nistpubs/specialpublications/nist.sp.800-218.pdf)  
- Site Reliability Engineering[\[117\]](https://www.iso.org/standard/65694.html) (PRR model, monitoring golden signals, launch checklist, error budgets). [\[118\]](https://sre.google/sre-book/evolving-sre-engagement-model/)

Templates and concrete documentation formats: - arc42[\[119\]](https://learn.microsoft.com/en-us/azure/well-architected/architect-role/architecture-decision-record) (12-section architecture template). [\[40\]](https://arc42.org/overview)  
- Simon Brown[\[120\]](https://www.iso.org/standard/65694.html) C4 model official documentation. [\[39\]](https://c4model.com/)  
- Cloud Native Computing Foundation[\[121\]](https://csrc.nist.gov/pubs/sp/800/30/r1/final) event-driven architecture and CloudEvents references. [\[122\]](https://glossary.cncf.io/event-driven-architecture/)  
- OpenTelemetry[\[123\]](https://www.iso.org/standard/63712.html) telemetry and observability primer. [\[18\]](https://opentelemetry.io/docs/)  
- Kubernetes[\[124\]](https://www.iso.org/standard/74393.html) KEP process and template. [\[82\]](https://github.com/kubernetes/enhancements/blob/master/keps/sig-architecture/0000-kep-process/README.md)

Decision logging and evolutionary architecture: - Thoughtworks[\[125\]](https://www.melconway.com/research/committees.html) ADR technique rationale and architecture advice process. [\[126\]](https://www.thoughtworks.com/radar/techniques/lightweight-architecture-decision-records)  
- DORA[\[127\]](https://github.com/kubernetes/enhancements/blob/master/keps/sig-architecture/0000-kep-process/README.md) governance-related capabilities (peer review + automation for approvals). [\[128\]](https://dora.dev/capabilities/streamlining-change-approval/)

[\[1\]](https://people.eecs.ku.edu/~hossein/810/Project/IEEE-Stds/1471.pdf) [\[4\]](https://people.eecs.ku.edu/~hossein/810/Project/IEEE-Stds/1471.pdf) [\[7\]](https://people.eecs.ku.edu/~hossein/810/Project/IEEE-Stds/1471.pdf) [\[46\]](https://people.eecs.ku.edu/~hossein/810/Project/IEEE-Stds/1471.pdf) [\[67\]](https://people.eecs.ku.edu/~hossein/810/Project/IEEE-Stds/1471.pdf) [\[68\]](https://people.eecs.ku.edu/~hossein/810/Project/IEEE-Stds/1471.pdf) [\[99\]](https://people.eecs.ku.edu/~hossein/810/Project/IEEE-Stds/1471.pdf) https://people.eecs.ku.edu/\~hossein/810/Project/IEEE-Stds/1471.pdf

<https://people.eecs.ku.edu/~hossein/810/Project/IEEE-Stds/1471.pdf>

[\[2\]](https://prl.khoury.northeastern.edu/img/p-tr-1971.pdf) [\[6\]](https://prl.khoury.northeastern.edu/img/p-tr-1971.pdf) [\[107\]](https://prl.khoury.northeastern.edu/img/p-tr-1971.pdf) https://prl.khoury.northeastern.edu/img/p-tr-1971.pdf

<https://prl.khoury.northeastern.edu/img/p-tr-1971.pdf>

[\[3\]](https://learn.microsoft.com/en-us/azure/well-architected/architect-role/architecture-decision-record) [\[14\]](https://learn.microsoft.com/en-us/azure/well-architected/architect-role/architecture-decision-record) [\[28\]](https://learn.microsoft.com/en-us/azure/well-architected/architect-role/architecture-decision-record) [\[31\]](https://learn.microsoft.com/en-us/azure/well-architected/architect-role/architecture-decision-record) [\[43\]](https://learn.microsoft.com/en-us/azure/well-architected/architect-role/architecture-decision-record) [\[61\]](https://learn.microsoft.com/en-us/azure/well-architected/architect-role/architecture-decision-record) [\[66\]](https://learn.microsoft.com/en-us/azure/well-architected/architect-role/architecture-decision-record) [\[85\]](https://learn.microsoft.com/en-us/azure/well-architected/architect-role/architecture-decision-record) [\[91\]](https://learn.microsoft.com/en-us/azure/well-architected/architect-role/architecture-decision-record) [\[94\]](https://learn.microsoft.com/en-us/azure/well-architected/architect-role/architecture-decision-record) [\[96\]](https://learn.microsoft.com/en-us/azure/well-architected/architect-role/architecture-decision-record) [\[97\]](https://learn.microsoft.com/en-us/azure/well-architected/architect-role/architecture-decision-record) [\[100\]](https://learn.microsoft.com/en-us/azure/well-architected/architect-role/architecture-decision-record) [\[102\]](https://learn.microsoft.com/en-us/azure/well-architected/architect-role/architecture-decision-record) [\[104\]](https://learn.microsoft.com/en-us/azure/well-architected/architect-role/architecture-decision-record) [\[105\]](https://learn.microsoft.com/en-us/azure/well-architected/architect-role/architecture-decision-record) [\[119\]](https://learn.microsoft.com/en-us/azure/well-architected/architect-role/architecture-decision-record) https://learn.microsoft.com/en-us/azure/well-architected/architect-role/architecture-decision-record

<https://learn.microsoft.com/en-us/azure/well-architected/architect-role/architecture-decision-record>

[\[5\]](https://docs.aws.amazon.com/wellarchitected/latest/framework/the-review-process.html) [\[53\]](https://docs.aws.amazon.com/wellarchitected/latest/framework/the-review-process.html) [\[74\]](https://docs.aws.amazon.com/wellarchitected/latest/framework/the-review-process.html) [\[76\]](https://docs.aws.amazon.com/wellarchitected/latest/framework/the-review-process.html) [\[80\]](https://docs.aws.amazon.com/wellarchitected/latest/framework/the-review-process.html) https://docs.aws.amazon.com/wellarchitected/latest/framework/the-review-process.html

<https://docs.aws.amazon.com/wellarchitected/latest/framework/the-review-process.html>

[\[8\]](https://www.iso.org/standard/74393.html) [\[38\]](https://www.iso.org/standard/74393.html) [\[47\]](https://www.iso.org/standard/74393.html) [\[124\]](https://www.iso.org/standard/74393.html) https://www.iso.org/standard/74393.html

<https://www.iso.org/standard/74393.html>

[\[9\]](https://www.sei.cmu.edu/library/file_redirect/1998_005_001_16646.pdf/) [\[32\]](https://www.sei.cmu.edu/library/file_redirect/1998_005_001_16646.pdf/) [\[69\]](https://www.sei.cmu.edu/library/file_redirect/1998_005_001_16646.pdf/) [\[110\]](https://www.sei.cmu.edu/library/file_redirect/1998_005_001_16646.pdf/) https://www.sei.cmu.edu/library/file_redirect/1998_005_001_16646.pdf/

<https://www.sei.cmu.edu/library/file_redirect/1998_005_001_16646.pdf/>

[\[10\]](https://ocw.mit.edu/courses/2-611-marine-power-and-propulsion-fall-2006/8fd4b50ef794af75294c44aa555196c3_23reliability.pdf) https://ocw.mit.edu/courses/2-611-marine-power-and-propulsion-fall-2006/8fd4b50ef794af75294c44aa555196c3_23reliability.pdf

<https://ocw.mit.edu/courses/2-611-marine-power-and-propulsion-fall-2006/8fd4b50ef794af75294c44aa555196c3_23reliability.pdf>

[\[11\]](https://sre.google/workbook/error-budget-policy/) [\[93\]](https://sre.google/workbook/error-budget-policy/) https://sre.google/workbook/error-budget-policy/

<https://sre.google/workbook/error-budget-policy/>

[\[12\]](https://www.cs.princeton.edu/courses/archive/spr22/cos418/papers/cap.pdf) https://www.cs.princeton.edu/courses/archive/spr22/cos418/papers/cap.pdf

<https://www.cs.princeton.edu/courses/archive/spr22/cos418/papers/cap.pdf>

[\[13\]](https://martin.kleppmann.com/2015/05/11/please-stop-calling-databases-cp-or-ap.html) [\[86\]](https://martin.kleppmann.com/2015/05/11/please-stop-calling-databases-cp-or-ap.html) [\[106\]](https://martin.kleppmann.com/2015/05/11/please-stop-calling-databases-cp-or-ap.html) https://martin.kleppmann.com/2015/05/11/please-stop-calling-databases-cp-or-ap.html

<https://martin.kleppmann.com/2015/05/11/please-stop-calling-databases-cp-or-ap.html>

[\[15\]](https://docs.cloud.google.com/architecture/framework/reliability) [\[79\]](https://docs.cloud.google.com/architecture/framework/reliability) https://docs.cloud.google.com/architecture/framework/reliability

<https://docs.cloud.google.com/architecture/framework/reliability>

[\[16\]](https://sre.google/sre-book/launch-checklist/) [\[20\]](https://sre.google/sre-book/launch-checklist/) [\[65\]](https://sre.google/sre-book/launch-checklist/) [\[78\]](https://sre.google/sre-book/launch-checklist/) [\[87\]](https://sre.google/sre-book/launch-checklist/) [\[115\]](https://sre.google/sre-book/launch-checklist/) https://sre.google/sre-book/launch-checklist/

<https://sre.google/sre-book/launch-checklist/>

[\[17\]](https://principlesofchaos.org/) https://principlesofchaos.org/

<https://principlesofchaos.org/>

[\[18\]](https://opentelemetry.io/docs/) [\[95\]](https://opentelemetry.io/docs/) https://opentelemetry.io/docs/

<https://opentelemetry.io/docs/>

[\[19\]](https://sre.google/sre-book/monitoring-distributed-systems/) [\[64\]](https://sre.google/sre-book/monitoring-distributed-systems/) https://sre.google/sre-book/monitoring-distributed-systems/

<https://sre.google/sre-book/monitoring-distributed-systems/>

[\[21\]](https://www.martinfowler.com/bliki/BoundedContext.html) [\[70\]](https://www.martinfowler.com/bliki/BoundedContext.html) [\[89\]](https://www.martinfowler.com/bliki/BoundedContext.html) [\[98\]](https://www.martinfowler.com/bliki/BoundedContext.html) https://www.martinfowler.com/bliki/BoundedContext.html

<https://www.martinfowler.com/bliki/BoundedContext.html>

[\[22\]](https://martinfowler.com/articles/microservices.html) [\[24\]](https://martinfowler.com/articles/microservices.html) https://martinfowler.com/articles/microservices.html

<https://martinfowler.com/articles/microservices.html>

[\[23\]](https://glossary.cncf.io/event-driven-architecture/) [\[122\]](https://glossary.cncf.io/event-driven-architecture/) https://glossary.cncf.io/event-driven-architecture/

<https://glossary.cncf.io/event-driven-architecture/>

[\[25\]](https://www.melconway.com/research/committees.html) [\[125\]](https://www.melconway.com/research/committees.html) https://www.melconway.com/research/committees.html

<https://www.melconway.com/research/committees.html>

[\[26\]](https://dora.dev/capabilities/loosely-coupled-teams/) https://dora.dev/capabilities/loosely-coupled-teams/

<https://dora.dev/capabilities/loosely-coupled-teams/>

[\[27\]](https://www.thoughtworks.com/en-de/radar/techniques/architecture-advice-process) [\[75\]](https://www.thoughtworks.com/en-de/radar/techniques/architecture-advice-process) [\[77\]](https://www.thoughtworks.com/en-de/radar/techniques/architecture-advice-process) https://www.thoughtworks.com/en-de/radar/techniques/architecture-advice-process

<https://www.thoughtworks.com/en-de/radar/techniques/architecture-advice-process>

[\[29\]](https://www.thoughtworks.com/radar/techniques/lightweight-architecture-decision-records) [\[108\]](https://www.thoughtworks.com/radar/techniques/lightweight-architecture-decision-records) [\[126\]](https://www.thoughtworks.com/radar/techniques/lightweight-architecture-decision-records) https://www.thoughtworks.com/radar/techniques/lightweight-architecture-decision-records

<https://www.thoughtworks.com/radar/techniques/lightweight-architecture-decision-records>

[\[30\]](https://adr.github.io/) https://adr.github.io/

<https://adr.github.io/>

[\[33\]](https://techcommunity.microsoft.com/blog/azurearchitectureblog/how-great-engineers-make-architectural-decisions-%E2%80%94-adrs-trade-offs-and-an-atam-l/4463013) [\[62\]](https://techcommunity.microsoft.com/blog/azurearchitectureblog/how-great-engineers-make-architectural-decisions-%E2%80%94-adrs-trade-offs-and-an-atam-l/4463013) https://techcommunity.microsoft.com/blog/azurearchitectureblog/how-great-engineers-make-architectural-decisions-%E2%80%94-adrs-trade-offs-and-an-atam-l/4463013

<https://techcommunity.microsoft.com/blog/azurearchitectureblog/how-great-engineers-make-architectural-decisions-%E2%80%94-adrs-trade-offs-and-an-atam-l/4463013>

[\[34\]](https://docs.aws.amazon.com/wellarchitected/latest/framework/welcome.html) [\[41\]](https://docs.aws.amazon.com/wellarchitected/latest/framework/welcome.html) [\[50\]](https://docs.aws.amazon.com/wellarchitected/latest/framework/welcome.html) https://docs.aws.amazon.com/wellarchitected/latest/framework/welcome.html

<https://docs.aws.amazon.com/wellarchitected/latest/framework/welcome.html>

[\[35\]](https://www.iso.org/standard/65694.html) [\[58\]](https://www.iso.org/standard/65694.html) [\[63\]](https://www.iso.org/standard/65694.html) [\[73\]](https://www.iso.org/standard/65694.html) [\[90\]](https://www.iso.org/standard/65694.html) [\[101\]](https://www.iso.org/standard/65694.html) [\[117\]](https://www.iso.org/standard/65694.html) [\[120\]](https://www.iso.org/standard/65694.html) https://www.iso.org/standard/65694.html

<https://www.iso.org/standard/65694.html>

[\[36\]](https://www.pmi.org/learning/library/project-risk-management-success-tool-6078) https://www.pmi.org/learning/library/project-risk-management-success-tool-6078

<https://www.pmi.org/learning/library/project-risk-management-success-tool-6078>

[\[37\]](https://www.microsoft.com/en-us/securityengineering/sdl/threatmodeling) [\[71\]](https://www.microsoft.com/en-us/securityengineering/sdl/threatmodeling) https://www.microsoft.com/en-us/securityengineering/sdl/threatmodeling

<https://www.microsoft.com/en-us/securityengineering/sdl/threatmodeling>

[\[39\]](https://c4model.com/) [\[48\]](https://c4model.com/) [\[60\]](https://c4model.com/) [\[92\]](https://c4model.com/) [\[113\]](https://c4model.com/) https://c4model.com/

<https://c4model.com/>

[\[40\]](https://arc42.org/overview) [\[49\]](https://arc42.org/overview) https://arc42.org/overview

<https://arc42.org/overview>

[\[42\]](https://www.aboutamazon.com/news/workplace/an-insider-look-at-amazons-culture-and-processes) https://www.aboutamazon.com/news/workplace/an-insider-look-at-amazons-culture-and-processes

<https://www.aboutamazon.com/news/workplace/an-insider-look-at-amazons-culture-and-processes>

[\[44\]](https://raw.githubusercontent.com/kubernetes/enhancements/a86942e8ba802d0035ec7d4a9c992f03bca7dce9/keps/NNNN-kep-template/README.md) https://raw.githubusercontent.com/kubernetes/enhancements/a86942e8ba802d0035ec7d4a9c992f03bca7dce9/keps/NNNN-kep-template/README.md

<https://raw.githubusercontent.com/kubernetes/enhancements/a86942e8ba802d0035ec7d4a9c992f03bca7dce9/keps/NNNN-kep-template/README.md>

[\[45\]](https://standards.ieee.org/standard/1058-1998.html) https://standards.ieee.org/standard/1058-1998.html

<https://standards.ieee.org/standard/1058-1998.html>

[\[51\]](https://learn.microsoft.com/en-us/azure/well-architected/) [\[114\]](https://learn.microsoft.com/en-us/azure/well-architected/) https://learn.microsoft.com/en-us/azure/well-architected/

<https://learn.microsoft.com/en-us/azure/well-architected/>

[\[52\]](https://docs.cloud.google.com/architecture/framework) [\[112\]](https://docs.cloud.google.com/architecture/framework) https://docs.cloud.google.com/architecture/framework

<https://docs.cloud.google.com/architecture/framework>

[\[54\]](https://workingbackwards.com/concepts/working-backwards-pr-faq-process/) https://workingbackwards.com/concepts/working-backwards-pr-faq-process/

<https://workingbackwards.com/concepts/working-backwards-pr-faq-process/>

[\[55\]](https://www.businessinsider.com/jeff-bezos-email-against-powerpoint-presentations-2015-7) https://www.businessinsider.com/jeff-bezos-email-against-powerpoint-presentations-2015-7

<https://www.businessinsider.com/jeff-bezos-email-against-powerpoint-presentations-2015-7>

[\[56\]](https://www.iso.org/standard/63712.html) [\[123\]](https://www.iso.org/standard/63712.html) https://www.iso.org/standard/63712.html

<https://www.iso.org/standard/63712.html>

[\[57\]](https://sw-eng.larc.nasa.gov/supporting-products/) https://sw-eng.larc.nasa.gov/supporting-products/

<https://sw-eng.larc.nasa.gov/supporting-products/>

[\[59\]](https://www.industrialempathy.com/posts/design-docs-at-google/) https://www.industrialempathy.com/posts/design-docs-at-google/

<https://www.industrialempathy.com/posts/design-docs-at-google/>

[\[72\]](https://sre.google/sre-book/evolving-sre-engagement-model/) [\[84\]](https://sre.google/sre-book/evolving-sre-engagement-model/) [\[118\]](https://sre.google/sre-book/evolving-sre-engagement-model/) https://sre.google/sre-book/evolving-sre-engagement-model/

<https://sre.google/sre-book/evolving-sre-engagement-model/>

[\[81\]](https://dora.dev/capabilities/streamlining-change-approval/) [\[88\]](https://dora.dev/capabilities/streamlining-change-approval/) [\[128\]](https://dora.dev/capabilities/streamlining-change-approval/) https://dora.dev/capabilities/streamlining-change-approval/

<https://dora.dev/capabilities/streamlining-change-approval/>

[\[82\]](https://github.com/kubernetes/enhancements/blob/master/keps/sig-architecture/0000-kep-process/README.md) [\[111\]](https://github.com/kubernetes/enhancements/blob/master/keps/sig-architecture/0000-kep-process/README.md) [\[127\]](https://github.com/kubernetes/enhancements/blob/master/keps/sig-architecture/0000-kep-process/README.md) https://github.com/kubernetes/enhancements/blob/master/keps/sig-architecture/0000-kep-process/README.md

<https://github.com/kubernetes/enhancements/blob/master/keps/sig-architecture/0000-kep-process/README.md>

[\[83\]](https://github.com/rust-lang/rfcs/blob/master/0000-template.md) https://github.com/rust-lang/rfcs/blob/master/0000-template.md

<https://github.com/rust-lang/rfcs/blob/master/0000-template.md>

[\[103\]](https://csrc.nist.gov/pubs/sp/800/30/r1/final) [\[121\]](https://csrc.nist.gov/pubs/sp/800/30/r1/final) https://csrc.nist.gov/pubs/sp/800/30/r1/final

<https://csrc.nist.gov/pubs/sp/800/30/r1/final>

[\[109\]](https://www.cs.ubc.ca/~gregor/teaching/papers/4%2B1view-architecture.pdf) https://www.cs.ubc.ca/\~gregor/teaching/papers/4%2B1view-architecture.pdf

<https://www.cs.ubc.ca/~gregor/teaching/papers/4%2B1view-architecture.pdf>

[\[116\]](https://nvlpubs.nist.gov/nistpubs/specialpublications/nist.sp.800-218.pdf) https://nvlpubs.nist.gov/nistpubs/specialpublications/nist.sp.800-218.pdf

<https://nvlpubs.nist.gov/nistpubs/specialpublications/nist.sp.800-218.pdf>
