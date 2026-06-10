export type CapxUiOneLifecycleState = "official" | "active" | "review" | "blocked" | "planned";
export type CapxUiOneTaskState = "Open" | "Needs review" | "Not ready" | "Stale" | "Blocked" | "Ready";
export type CapxUiOneJobState = "Complete" | "Running" | "Queued" | "Blocked";

export interface CapxUiOneProject {
  id: string;
  name: string;
  site: string;
  sponsor: string;
  lifecycleContext: string;
  snapshotId: string;
  snapshotFreshness: string;
  forecastability: string;
  staleBadges: string[];
  blockedBadges: string[];
  route: string;
}

export interface CapxUiOnePhase {
  key: string;
  phaseKey: string;
  name: string;
  workspace: string;
  state: CapxUiOneLifecycleState;
  scope: string;
  aiFunctions: string;
  outputs: string;
  readiness: string;
  route: string;
}

export interface CapxUiOneTask {
  id: string;
  title: string;
  type: string;
  owner: string;
  due: string;
  state: CapxUiOneTaskState;
  priority: "P0" | "P1" | "P2";
  boundObject: string;
  basis: string;
  evidence: string;
  policy: string;
  route: string;
}

export interface CapxUiOneEvidence {
  id: string;
  title: string;
  kind: string;
  role: string;
  status: "Reviewed" | "Needs review" | "Draft extraction" | "Stale" | "Missing" | "Quarantined";
  sourceOccurrence: string;
  basis: string;
  provenance: string;
  reviewState: string;
  extractionStatus: string;
  claimsDerived: string[];
}

export interface CapxUiOneAiJob {
  id: string;
  label: string;
  state: CapxUiOneJobState;
  output: string;
  guardrail: string;
}

export interface CapxUiOneDraftOutput {
  id: string;
  title: string;
  state: "Draft" | "In review" | "Approved" | "Official pointer candidate";
  basis: string;
  warning: string;
}

export interface CapxUiOneReport {
  id: string;
  title: string;
  snapshotId: string;
  freshness: string;
  warning: string;
  state: "Generated draft" | "Blocked by stale basis" | "Draft only";
  official: boolean;
  sections: string[];
}

export interface CapxUiOneAuditEvent {
  id: string;
  actor: string;
  command: string;
  target: string;
  outcome: string;
  policy: string;
  recordedAt: string;
}

export interface CapxUiOneSnapshot {
  id: string;
  projectId: string;
  basisVersion: string;
  state: string;
  freshness: string;
  currentLifecycleStage: string;
  forecastability: string;
  stateLabels: string[];
  blockers: Array<{
    id: string;
    label: string;
    severity: string;
    boundTaskId: string;
  }>;
  staleReasons: Array<{
    source: string;
    reason: string;
  }>;
  nextActions: string[];
  officialPointers: Array<{
    label: string;
    value: string;
  }>;
}

export interface CapxUiOneWorkpageProjection {
  id: string;
  name: string;
  inputs: string;
  renderedState: string;
  availableCommands: string;
  guardrailOutcome: string;
}

export interface CapxUiOneCommandReceiptFixture {
  id: string;
  command: string;
  target: string;
  outcome: "accepted" | "rejected";
  policyResult: string;
  detail: string;
  nextRequiredAction: string;
  taskId?: string;
}

export const capxUiOnePrimaryProjectId = "k12-packaging-line-upgrade";
const capxUiOneProjectBaseRoute = `/demo/capx/ui-one/projects/${capxUiOnePrimaryProjectId}`;

export const capxUiOneProject: CapxUiOneProject = {
  id: capxUiOnePrimaryProjectId,
  name: "K12 Packaging Line Upgrade",
  site: "Plant K12",
  sponsor: "Site operations",
  lifecycleContext: "Basic Engineering / Procurement Readiness",
  snapshotId: "capex.project_state_snapshot.v1:k12:001",
  snapshotFreshness: "Stale warning after Order Revision AB-02 changed supplier responsibility wording",
  forecastability: "Limited",
  staleBadges: ["stale_warning", "stale_assumption_matrix"],
  blockedBadges: ["blocked_interface"],
  route: `${capxUiOneProjectBaseRoute}/overview`
};

export const capxUiOneProjects: CapxUiOneProject[] = [
  capxUiOneProject,
  {
    id: "k3-safety-replacement",
    name: "K3 Safety Replacement",
    site: "Plant K3",
    sponsor: "EHS and maintenance",
    lifecycleContext: "Concept Review",
    snapshotId: "capex.project_state_snapshot.v1:k3:seed",
    snapshotFreshness: "Fixture seed awaiting governed review",
    forecastability: "Monitor",
    staleBadges: [],
    blockedBadges: ["supplier_quote_caveat_open"],
    route: "/demo/capx/ui-one/projects/k3-safety-replacement/overview"
  }
];

export const capxUiOneSnapshot: CapxUiOneSnapshot = {
  id: "snapshot-k12-001",
  projectId: capxUiOnePrimaryProjectId,
  basisVersion: "capex.project_state_snapshot.v1:k12:001",
  state: "blocked",
  freshness: "stale_warning",
  currentLifecycleStage: "Basic Engineering / Procurement Readiness",
  forecastability: "limited",
  stateLabels: [
    "draft_inputs_present",
    "reviewed_commitment_chain",
    "blocked_interface",
    "stale_assumption_matrix"
  ],
  blockers: [
    {
      id: "blocker-compressed-air",
      label: "Compressed-air interface missing current site measurement",
      severity: "critical",
      boundTaskId: "task-001"
    }
  ],
  staleReasons: [
    {
      source: "Order Revision AB-02",
      reason: "Supplier responsibility wording changed; assumption matrix requires re-review."
    }
  ],
  nextActions: [
    "Request current compressed-air measurement from utilities owner",
    "Re-review supplier responsibility caveat in AB-02",
    "Do not promote procurement readiness snapshot yet"
  ],
  officialPointers: [
    {
      label: "Commitment chain",
      value: "capex.commitment_chain.v1:k12:003"
    },
    {
      label: "Assumption matrix",
      value: "capex.assumption_closure_matrix.v1:k12:002-stale"
    },
    {
      label: "Interface register",
      value: "capex.interface_register.v1:k12:004"
    }
  ]
};

export const capxUiOnePhases: CapxUiOnePhase[] = [
  {
    key: "1.1",
    phaseKey: "opportunity",
    name: "Opportunity & Project Request",
    workspace: "Intake Workspace",
    state: "official",
    scope: "Sanitized project request, site need, sponsor context, and tenant-scoped intake evidence.",
    aiFunctions: "OCR and intake structuring create draft fields only.",
    outputs: "Reviewed request packet and project identity.",
    readiness: "Official for this fixture; later commands still bind to exact versions.",
    route: `${capxUiOneProjectBaseRoute}/phases/opportunity`
  },
  {
    key: "1.2",
    phaseKey: "feasibility",
    name: "Feasibility & Business Case",
    workspace: "Feasibility Workspace",
    state: "official",
    scope: "Business case, technical feasibility, initial budget, and documented assumptions.",
    aiFunctions: "Benchmark and scenario summaries remain draft until reviewed.",
    outputs: "Reviewed feasibility basis.",
    readiness: "Official basis exists, but downstream procurement readiness is not cleared.",
    route: `${capxUiOneProjectBaseRoute}/phases/feasibility`
  },
  {
    key: "1.3",
    phaseKey: "concept",
    name: "Concept Engineering",
    workspace: "Concept Options Workspace",
    state: "review",
    scope: "Concept variant, utility interfaces, supplier caveats, and owner responsibilities.",
    aiFunctions: "Variant comparison and caveat detection support human review.",
    outputs: "Concept option review packet.",
    readiness: "Supplier responsibility change requires re-review before downstream readiness.",
    route: `${capxUiOneProjectBaseRoute}/phases/concept`
  },
  {
    key: "1.4",
    phaseKey: "basic-engineering",
    name: "Basic Engineering",
    workspace: "Requirements Workspace",
    state: "active",
    scope: "Specifications, interface register, assumption matrix, and requirement completeness.",
    aiFunctions: "Completeness checks and cross-artifact contradiction detection.",
    outputs: "Basic engineering readiness snapshot.",
    readiness: "Active, but the current snapshot carries a stale warning.",
    route: `${capxUiOneProjectBaseRoute}/phases/basic-engineering`
  },
  {
    key: "1.5",
    phaseKey: "procurement",
    name: "Procurement",
    workspace: "Commitment & Procurement Workspace",
    state: "blocked",
    scope: "Commitment chain, procurement readiness, supplier caveats, and purchase decision support.",
    aiFunctions: "Offer comparison and caveat tracing produce non-official draft material.",
    outputs: "Procurement readiness packet.",
    readiness: "Blocked until current compressed-air measurement evidence is attached and reviewed.",
    route: `${capxUiOneProjectBaseRoute}/phases/procurement`
  },
  {
    key: "1.6",
    phaseKey: "detailed-engineering",
    name: "Detailed Engineering & Manufacturing",
    workspace: "Engineering Progress Workspace",
    state: "planned",
    scope: "Supplier engineering progress, detailed drawings, and manufacturing updates.",
    aiFunctions: "Progress monitoring and risk alerts.",
    outputs: "Engineering and manufacturing status.",
    readiness: "Planned after procurement readiness clears.",
    route: `${capxUiOneProjectBaseRoute}/phases/detailed-engineering`
  },
  {
    key: "1.7",
    phaseKey: "installation",
    name: "Construction & Installation",
    workspace: "Installation Workspace",
    state: "planned",
    scope: "Site readiness, contractor coordination, deviations, and daily reporting.",
    aiFunctions: "Photo and daily-report summarization remain evidence-bound.",
    outputs: "Construction status and deviation log.",
    readiness: "Planned.",
    route: `${capxUiOneProjectBaseRoute}/phases/installation`
  },
  {
    key: "1.8",
    phaseKey: "commissioning",
    name: "Commissioning",
    workspace: "Commissioning Workspace",
    state: "planned",
    scope: "Test plans, ramp-up validation, issue tracking, and acceptance evidence.",
    aiFunctions: "Test evaluation and issue clustering.",
    outputs: "Commissioning report and performance evidence.",
    readiness: "Planned.",
    route: `${capxUiOneProjectBaseRoute}/phases/commissioning`
  },
  {
    key: "1.9",
    phaseKey: "handover",
    name: "Handover & Closing",
    workspace: "Handover & Closure Workspace",
    state: "planned",
    scope: "Handover package, training evidence, residual open points, and final acceptance.",
    aiFunctions: "Completeness checks and closure packet drafting.",
    outputs: "Handover package and acceptance report.",
    readiness: "Planned.",
    route: `${capxUiOneProjectBaseRoute}/phases/handover`
  },
  {
    key: "1.10",
    phaseKey: "learning",
    name: "Continuous Improvement",
    workspace: "Learning Workspace",
    state: "planned",
    scope: "Lessons learned, cost and timing analysis, and reusable pattern capture.",
    aiFunctions: "Pattern extraction for reviewed lesson candidates.",
    outputs: "Lesson candidates and reusable governance patterns.",
    readiness: "Planned.",
    route: `${capxUiOneProjectBaseRoute}/phases/learning`
  }
];

export const capxUiOneTasks: CapxUiOneTask[] = [
  {
    id: "task-001",
    title: "Provide current compressed-air measurement",
    type: "Missing evidence",
    owner: "Utilities Engineer",
    due: "Today",
    state: "Blocked",
    priority: "P0",
    boundObject: "interface:int-compressed-air",
    basis: "capex.interface_register.v1:k12:004",
    evidence: "Current pressure measurement and flow-rate measurement are missing; stale 2022 drawing is insufficient.",
    policy: "Task cannot be closed and procurement readiness cannot be promoted until current measurement evidence is attached and reviewed.",
    route: `${capxUiOneProjectBaseRoute}/tasks`
  },
  {
    id: "task-002",
    title: "Review supplier responsibility change in AB-02",
    type: "Needs review",
    owner: "Project Manager",
    due: "Tomorrow",
    state: "Open",
    priority: "P1",
    boundObject: "assumption:owner-supplier-responsibility",
    basis: "capex.assumption_closure_matrix.v1:k12:002-stale",
    evidence: "Order Revision AB-02 changed responsibility wording and reopened the reviewed assumption matrix.",
    policy: "Reviewed does not mean approved; the changed wording must be explicitly re-reviewed.",
    route: `${capxUiOneProjectBaseRoute}/tasks`
  },
  {
    id: "task-003",
    title: "Approve procurement readiness snapshot",
    type: "Approval",
    owner: "CAPEX Approver",
    due: "After blockers clear",
    state: "Not ready",
    priority: "P0",
    boundObject: "snapshot:snapshot-k12-001",
    basis: "capex.project_state_snapshot.v1:k12:001",
    evidence: "Critical compressed-air interface remains open; draft report generation does not create official readiness.",
    policy: "Approved does not mean official, and closed tasks do not change promotion pointers without a guarded command.",
    route: `${capxUiOneProjectBaseRoute}/tasks`
  }
];

export const capxUiOneEvidence: CapxUiOneEvidence[] = [
  {
    id: "ev-001",
    title: "Supplier Quote AB-01",
    kind: "supplier_quote",
    role: "Reviewed commitment-chain evidence",
    status: "Reviewed",
    sourceOccurrence: "source_occurrence:so-001",
    basis: "capex.commitment_chain.v1:k12:003",
    provenance: "Repo-ready fixture source occurrence for the supplier quote packet.",
    reviewState: "reviewed",
    extractionStatus: "complete",
    claimsDerived: ["Supplier offer is represented in the reviewed commitment chain."]
  },
  {
    id: "ev-002",
    title: "Order Revision AB-02",
    kind: "order_revision",
    role: "Changed supplier responsibility wording",
    status: "Needs review",
    sourceOccurrence: "source_occurrence:so-002",
    basis: "capex.assumption_closure_matrix.v1:k12:002-stale",
    provenance: "Repo-ready fixture source occurrence for the supplier revision packet.",
    reviewState: "needs_review",
    extractionStatus: "draft_extraction",
    claimsDerived: ["Responsibility caveat changed after the prior assumption review."]
  },
  {
    id: "ev-003",
    title: "Site Compressed-Air Drawing 2022",
    kind: "site_drawing",
    role: "Historical interface context",
    status: "Stale",
    sourceOccurrence: "source_occurrence:so-003",
    basis: "capex.interface_register.v1:k12:004",
    provenance: "Sanitized historical site drawing reference from the repo-ready fixture.",
    reviewState: "stale",
    extractionStatus: "complete",
    claimsDerived: ["Historical drawing is insufficient for current pressure and flow validation."]
  },
  {
    id: "ev-004",
    title: "Current Compressed-Air Measurement",
    kind: "measurement",
    role: "Required current site measurement",
    status: "Missing",
    sourceOccurrence: "not_available",
    basis: "capex.interface_register.v1:k12:004",
    provenance: "No current measurement evidence has been attached in the fixture.",
    reviewState: "missing",
    extractionStatus: "not_available",
    claimsDerived: ["Current pressure measurement is required.", "Current flow-rate measurement is required."]
  }
];

export const capxUiOneAiJobs: CapxUiOneAiJob[] = [
  {
    id: "job-k12-001",
    label: "Source occurrence extraction",
    state: "Complete",
    output: "Supplier quote and revision occurrences linked to governed fixture evidence.",
    guardrail: "Raw project files are not surfaced; only sanitized occurrence IDs are displayed."
  },
  {
    id: "job-k12-002",
    label: "Responsibility caveat detector",
    state: "Complete",
    output: "AB-02 responsibility wording changed the assumption matrix basis.",
    guardrail: "Creates a review task; does not promote assumptions."
  },
  {
    id: "job-k12-003",
    label: "Interface measurement completeness check",
    state: "Blocked",
    output: "Current compressed-air pressure and flow-rate measurement are missing.",
    guardrail: "Blocks close-task and procurement-readiness commands."
  },
  {
    id: "job-k12-004",
    label: "Management snapshot draft generator",
    state: "Queued",
    output: "Draft report can be generated with stale warning, not official.",
    guardrail: "Report generation cannot publish or alter official pointers."
  }
];

export const capxUiOneDraftOutputs: CapxUiOneDraftOutput[] = [
  {
    id: "out-k12-report-001",
    title: "K12 Management Snapshot draft",
    state: "Draft",
    basis: "capex.project_state_snapshot.v1:k12:001",
    warning: "Generated report is not official and cannot publish while the interface blocker remains open."
  },
  {
    id: "out-k12-assumption-001",
    title: "Supplier responsibility re-review note",
    state: "In review",
    basis: "capex.assumption_closure_matrix.v1:k12:002-stale",
    warning: "Reviewed commitment chain does not approve the changed responsibility wording."
  },
  {
    id: "out-k12-interface-001",
    title: "Compressed-air interface evidence request",
    state: "Draft",
    basis: "capex.interface_register.v1:k12:004",
    warning: "Evidence request must be completed before the bound task can close."
  }
];

export const capxUiOneReports: CapxUiOneReport[] = [
  {
    id: "report-001",
    title: "K12 Management Snapshot",
    snapshotId: "capex.project_state_snapshot.v1:k12:001",
    freshness: "stale_warning",
    warning: "Generated draft only. The report is not official and cannot be published while the compressed-air blocker remains open.",
    state: "Generated draft",
    official: false,
    sections: ["Status", "Decision Needed", "Forecastability"]
  },
  {
    id: "report-002",
    title: "Procurement Readiness Summary",
    snapshotId: "capex.project_state_snapshot.v1:k12:001",
    freshness: "blocked_by_stale_basis",
    warning: "Procurement readiness remains blocked by missing current interface measurement.",
    state: "Blocked by stale basis",
    official: false,
    sections: ["Blockers", "Required Evidence", "Pointer Status"]
  }
];

export const capxUiOneWorkpageProjections: CapxUiOneWorkpageProjection[] = [
  {
    id: "WP-001",
    name: "Corpus Baseline",
    inputs: "Sanitized source-occurrence inventory",
    renderedState: "projection_only",
    availableCommands: "request review, attach evidence",
    guardrailOutcome: "No source baseline promotion without human review."
  },
  {
    id: "WP-002",
    name: "Governance / Commitment Chain",
    inputs: "Reviewed supplier quote and commitment pointers",
    renderedState: "reviewed_commitment_chain",
    availableCommands: "request pointer validation",
    guardrailOutcome: "Reviewed commitment chain does not approve changed assumptions."
  },
  {
    id: "WP-003",
    name: "Supplier Assumption Closure",
    inputs: "AB-02 supplier responsibility change",
    renderedState: "stale_assumption_matrix",
    availableCommands: "request re-review",
    guardrailOutcome: "Assumption pointer promotion is blocked until re-review closes."
  },
  {
    id: "WP-004",
    name: "Owner Interface Resolution",
    inputs: "Compressed-air interface register and missing current measurement",
    renderedState: "blocked_interface",
    availableCommands: "request measurement evidence",
    guardrailOutcome: "Task close and procurement readiness commands remain blocked."
  }
];

export const capxUiOneCommandReceipts: CapxUiOneCommandReceiptFixture[] = [
  {
    id: "receipt-001",
    command: "close_task_with_evidence",
    target: "task-001",
    outcome: "rejected",
    policyResult: "missing_evidence",
    detail: "Current compressed-air measurement is missing. Stale 2022 drawing is insufficient for pressure and flow validation.",
    nextRequiredAction: "Upload or request current pressure and flow-rate measurement from the utilities owner.",
    taskId: "task-001"
  },
  {
    id: "receipt-002",
    command: "generate_management_report_draft",
    target: "report-001",
    outcome: "accepted",
    policyResult: "draft_only",
    detail: "Report draft generated from capex.project_state_snapshot.v1:k12:001 with stale warning attached.",
    nextRequiredAction: "Keep the report marked not official until blockers clear and a publish command is allowed.",
    taskId: "task-003"
  },
  {
    id: "receipt-003",
    command: "publish_management_report",
    target: "report-001",
    outcome: "rejected",
    policyResult: "blocked_open_interface",
    detail: "Report generated does not mean published. The compressed-air interface blocker prevents official publication.",
    nextRequiredAction: "Resolve task-001, re-review stale assumptions, then request a governed publication command.",
    taskId: "task-003"
  }
];

export const capxUiOneAuditEvents: CapxUiOneAuditEvent[] = [
  {
    id: "aud-k12-001",
    actor: "agent.extraction",
    command: "create_draft_extraction",
    target: "source_occurrence:so-002",
    outcome: "accepted",
    policy: "draft extraction only; review remains required",
    recordedAt: "09:10"
  },
  {
    id: "aud-k12-002",
    actor: "pm.mira",
    command: "request_revalidation",
    target: "capex.assumption_closure_matrix.v1:k12:002-stale",
    outcome: "accepted",
    policy: "stale warning preserved on snapshot",
    recordedAt: "09:42"
  },
  {
    id: "aud-k12-003",
    actor: "pm.mira",
    command: "close_task_with_evidence",
    target: "task-001",
    outcome: "rejected",
    policy: "missing_evidence",
    recordedAt: "10:05"
  },
  {
    id: "aud-k12-004",
    actor: "agent.reporting",
    command: "generate_management_report_draft",
    target: "report-001",
    outcome: "accepted",
    policy: "draft_only",
    recordedAt: "10:18"
  }
];

export const capxUiOneAcceptanceCriteria = [
  "Latest document does not mean official.",
  "Reviewed does not mean approved.",
  "Approved does not mean official.",
  "Report generated does not mean published.",
  "Closed task does not mean official pointer changed.",
  "Stale state blocks mutation until revalidation.",
  "Every command receipt records target, outcome, policy result, and next required action."
];

export function getCapxUiOneProject(projectId: string | undefined): CapxUiOneProject {
  return capxUiOneProjects.find((project) => project.id === projectId) ?? capxUiOneProject;
}

export function getCapxUiOnePhase(phaseKey: string | undefined): CapxUiOnePhase {
  return capxUiOnePhases.find((phase) => phase.phaseKey === phaseKey) ?? capxUiOnePhases[0];
}

export function getCapxUiOneTask(taskId: string | undefined): CapxUiOneTask {
  return capxUiOneTasks.find((task) => task.id === taskId) ?? capxUiOneTasks[0];
}

export function getCapxUiOneEvidence(evidenceId: string | undefined): CapxUiOneEvidence {
  return capxUiOneEvidence.find((item) => item.id === evidenceId) ?? capxUiOneEvidence[0];
}

export function getCapxUiOnePriorityCount(priority: CapxUiOneTask["priority"]): number {
  return capxUiOneTasks.filter((task) => task.priority === priority).length;
}
