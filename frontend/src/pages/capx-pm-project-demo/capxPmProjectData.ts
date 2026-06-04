import type {
  CapxPmDemoState,
  CapxPmEvidenceFreshness,
  CapxPmEvidencePacket,
  CapxPmFlag,
  CapxPmHandoffManifest,
  CapxPmStepDetail,
  CapxPmRegisterRow,
  CapxPmStatus,
  CapxPmStepSlug,
  CapxPmStepState,
  CapxPmTask,
  CapxPmWorkflowStep
} from "./capxPmProjectTypes";

export const capxPmWorkflowSteps: CapxPmWorkflowStep[] = [
  {
    number: 1,
    slug: "intake",
    workflowId: "WFLOW-001",
    title: "Project Intake Router",
    shortTitle: "Intake",
    pmQuestion: "Can I safely open or resume this project, and which workflow modules must be active?"
  },
  {
    number: 2,
    slug: "corpus",
    workflowId: "WFLOW-002",
    title: "Corpus Baseline / Packet Formation",
    shortTitle: "Corpus",
    pmQuestion: "Do we know exactly what evidence exists, where it came from, and which packets it supports?"
  },
  {
    number: 3,
    slug: "lifecycle",
    workflowId: "WFLOW-003",
    title: "Lifecycle Stage Map",
    shortTitle: "Lifecycle",
    pmQuestion: "Which lifecycle stage is dominant, and which earlier obligations still block readiness?"
  },
  {
    number: 4,
    slug: "commitment",
    workflowId: "WFLOW-004",
    title: "Governance / Commitment Chain",
    shortTitle: "Commitment",
    pmQuestion: "What changed, who owns which responsibility, and which decisions are blocked?"
  },
  {
    number: 5,
    slug: "assumptions",
    workflowId: "WFLOW-005",
    title: "Supplier Assumption Closure",
    shortTitle: "Assumptions",
    pmQuestion: "Which supplier assumptions are open, contradicted, stale, waived, or evidence-backed?"
  },
  {
    number: 6,
    slug: "interfaces",
    workflowId: "WFLOW-006",
    title: "Owner Interface Resolution",
    shortTitle: "Interfaces",
    pmQuestion: "Who must provide each condition, who depends on it, and what evidence is missing?"
  },
  {
    number: 7,
    slug: "snapshot",
    workflowId: "WFLOW-007",
    title: "Project State Snapshot",
    shortTitle: "Snapshot",
    pmQuestion: "Are the reviewed inputs consistent, fresh, and ready for a snapshot candidate?"
  }
];

const stepBySlug = new Map(capxPmWorkflowSteps.map((step) => [step.slug, step]));

function task(
  id: string,
  title: string,
  owner: string,
  due: string,
  evidenceBasis: string,
  consequence: string,
  status: CapxPmStatus
): CapxPmTask {
  return { id, title, owner, due, evidenceBasis, consequence, status };
}

function flag(id: string, label: string, basis: string, status: CapxPmStatus): CapxPmFlag {
  return { id, label, basis, status };
}

function packet(
  id: string,
  title: string,
  freshness: CapxPmEvidenceFreshness,
  sourceCount: number,
  unresolvedRefs: number
): CapxPmEvidencePacket {
  return { id, title, freshness, sourceCount, unresolvedRefs };
}

function row(
  id: string,
  primary: string,
  secondary: string,
  owner: string,
  basis: string,
  status: CapxPmStatus
): CapxPmRegisterRow {
  return { id, primary, secondary, owner, basis, status };
}

function handoff(target: string, requiredBasis: string, nextCheck: string, status: CapxPmStatus): CapxPmHandoffManifest {
  return { target, requiredBasis, nextCheck, status };
}

function metric(label: string, value: string, status: CapxPmStatus) {
  return { label, value, status };
}

function card(title: string, value: string, body: string, status: CapxPmStatus) {
  return { title, value, body, status };
}

function matrix(label: string, current: string, owner: string, basis: string, status: CapxPmStatus) {
  return { label, current, owner, basis, status };
}

function timeline(label: string, marker: string, body: string, status: CapxPmStatus) {
  return { label, marker, body, status };
}

function detailFor(slug: CapxPmStepSlug, status: CapxPmStatus): CapxPmStepDetail {
  const step = stepBySlug.get(slug);
  if (!step) {
    throw new Error(`Unknown CAPX PM step: ${slug}`);
  }

  return {
    metrics: [
      metric("Open checks", status === "critical" ? "3" : "1", status),
      metric("Evidence packets", "1", status === "neutral" ? "neutral" : "verified"),
      metric("Handoff", status === "critical" ? "blocked" : "mock ready", status)
    ],
    cardsTitle: `${step.shortTitle} focus`,
    cards: [
      card(`${step.shortTitle} PM focus`, step.workflowId, "Compact synthetic display for sparse project routes.", status),
      card("Projection guard", "Mock only", "This surface cannot approve, promote, or create canonical project truth.", "neutral")
    ],
    matrixTitle: `${step.shortTitle} matrix`,
    matrixRows: [
      matrix(`${step.shortTitle} basis`, "Synthetic register row", "Assigned PM", "Mock workflow data", status),
      matrix("Officialness", "No mutation", "Demo shell", "Static projection only", "neutral")
    ],
    timelineTitle: `${step.shortTitle} strip`,
    timelineItems: [
      timeline("Mock input", "T-1", "Static project route loaded.", "verified"),
      timeline("PM review", "Now", "Selected step is open for design review.", status)
    ],
    mockActionLabel: `Simulated ${step.shortTitle.toLowerCase()} review disabled`
  };
}

interface StepOverrides {
  summary?: string;
  registerTitle?: string;
  registerRows?: CapxPmRegisterRow[];
  tasks?: CapxPmTask[];
  evidencePackets?: CapxPmEvidencePacket[];
  flags?: CapxPmFlag[];
  handoff?: CapxPmHandoffManifest;
  detail?: CapxPmStepDetail;
}

function buildStepState(slug: CapxPmStepSlug, status: CapxPmStatus, overrides: StepOverrides = {}): CapxPmStepState {
  const step = stepBySlug.get(slug);
  if (!step) {
    throw new Error(`Unknown CAPX PM step: ${slug}`);
  }

  return {
    slug,
    status,
    summary:
      overrides.summary ??
      `${step.shortTitle} is available as a mock projection. The PM can inspect blockers, evidence basis, and handoff status without creating canonical truth.`,
    registerTitle: overrides.registerTitle ?? `${step.shortTitle} register`,
    registerRows:
      overrides.registerRows ??
      [
        row(`${slug}-row-1`, `${step.shortTitle} basis review`, "Projection row awaiting PM review", "PM desk", "Mock source packet", status),
        row(`${slug}-row-2`, `${step.shortTitle} handoff check`, "Next workflow input basis", "Workflow analyst", "Mock handoff manifest", "neutral")
      ],
    tasks:
      overrides.tasks ??
      [
        task(
          `${slug}-task-1`,
          `${step.shortTitle} exception review`,
          "PM desk",
          "Today",
          "Mock register row",
          "Selected step stays blocked in the demo projection.",
          status
        )
      ],
    evidencePackets:
      overrides.evidencePackets ?? [packet(`${slug}-pkt-1`, `${step.shortTitle} evidence packet`, "aging", 4, status === "critical" ? 1 : 0)],
    flags: overrides.flags ?? [flag(`${slug}-flag-1`, `${step.shortTitle} projection guard`, "Mock basis only; no official state changes.", status)],
    handoff: overrides.handoff ?? handoff("Next PM workflow step", "Selected register version and validation vector", "Before snapshot review", status),
    detail: overrides.detail ?? detailFor(slug, status)
  };
}

const meridianSteps: CapxPmStepState[] = [
  buildStepState("intake", "verified", {
    summary:
      "Project shell, sponsor route, and module activation are resolved. The remaining intake concern is preserving the mid-project import boundary before corpus work continues.",
    registerTitle: "Intake profile and module activation",
    registerRows: [
      row("intake-1", "Entry mode", "Mid-project import", "PM D. Lane", "Project shell profile v0.4", "verified"),
      row("intake-2", "Pressure surfaces", "Budget, supplier interface, handover", "Controls lead", "Initial sponsor note", "watch"),
      row("intake-3", "Active modules", "Corpus, commitment, assumptions, interfaces, snapshot", "PMO analyst", "Activation profile draft", "verified")
    ],
    tasks: [
      task(
        "task-intake-1",
        "Confirm project membership before source packet review",
        "PM D. Lane",
        "Today",
        "Project shell profile v0.4",
        "Unconfirmed membership blocks handoff accountability.",
        "watch"
      )
    ],
    evidencePackets: [packet("pkt-intake-1", "Intake profile packet", "fresh", 6, 0)],
    flags: [flag("flag-intake-1", "Mid-project import boundary preserved", "Activation profile consumes explicit handoff.", "verified")],
    handoff: handoff("Corpus Baseline", "Project shell profile and module activation profile", "Before role assignment", "verified"),
    detail: {
      metrics: [
        metric("Project shell", "bound", "verified"),
        metric("Entry mode", "mid-import", "verified"),
        metric("Active modules", "5", "watch")
      ],
      cardsTitle: "Intake profile cards",
      cards: [
        card("Project shell", "Sponsor route bound", "Site, layer, membership, and PM owner are visible before corpus review.", "verified"),
        card("Entry mode selector", "Mid-project import", "Entry mode drives required corpus and commitment checks.", "verified"),
        card("Pressure surfaces", "Budget / supplier / handover", "Pressure flags steer escalation tasks without becoming hidden state.", "watch"),
        card("Missing sponsor/authorization", "Setup exception", "A missing sponsor creates an assigned intake task, not shadow project state.", "critical"),
        card("Intake-blocked exception", "Policy route", "Blocked intake remains a visible task with owner, due date, and consequence.", "critical"),
        card("CEO-entry decision packet", "Conditional", "High exposure can create a non-authoritative CEO packet for early review.", "watch")
      ],
      matrixTitle: "Module activation checklist",
      matrixRows: [
        matrix("Corpus baseline", "required", "PM D. Lane", "Mid-project import guard", "verified"),
        matrix("Commitment chain", "required", "Commercial lead", "Budget and order pressure", "verified"),
        matrix("Supplier assumptions", "required", "Engineering lead", "Supplier caveats present", "watch"),
        matrix("Owner interfaces", "required", "Site owner", "Utility ownership pressure", "critical"),
        matrix("K12 issue/asset module", "conditional", "PMO analyst", "No issue-driven trigger yet", "neutral")
      ],
      timelineTitle: "Intake handoff manifest",
      timelineItems: [
        timeline("Project shell created", "T-3", "Project metadata and membership were captured in a synthetic shell.", "verified"),
        timeline("Pressure surfaces classified", "T-2", "Budget and supplier-interface pressure were marked for downstream tasks.", "watch"),
        timeline("Intake-blocked exception cleared", "T-1", "Authorization gap was modeled as a setup task before corpus handoff.", "verified"),
        timeline("CEO-entry decision packet held", "Now", "Demo shows the conditional packet without implying executive approval.", "watch")
      ],
      mockActionLabel: "Simulated module activation disabled"
    }
  }),
  buildStepState("corpus", "critical", {
    summary:
      "Source inventory exists, but unresolved references and duplicate occurrences prevent evidence packets from being treated as complete.",
    registerTitle: "Source inventory and packet formation",
    registerRows: [
      row("corpus-1", "Archive occurrence A-17", "Duplicate drawing path preserved", "Evidence analyst", "Blob ingest session GIS-042", "watch"),
      row("corpus-2", "SourceRef SR-88", "Declared reference has no meaningful occurrence", "Document control", "Packet register draft", "critical"),
      row("corpus-3", "Procurement packet", "Quote, order, and revision evidence grouped", "Commercial lead", "Role assignment board", "watch"),
      row("corpus-4", "Sensitive file quarantine", "One training attachment held for review", "Security reviewer", "Quarantine note", "critical")
    ],
    tasks: [
      task(
        "task-corpus-1",
        "Resolve SourceRef SR-88 against source occurrence register",
        "Document control",
        "Today",
        "Source occurrence register draft",
        "Evidence binding and snapshot readiness remain blocked.",
        "critical"
      ),
      task(
        "task-corpus-2",
        "Review quarantined attachment before packet completeness check",
        "Security reviewer",
        "Tomorrow",
        "Ingest custody note",
        "Packet formation cannot claim completeness.",
        "critical"
      )
    ],
    evidencePackets: [
      packet("pkt-corpus-1", "Procurement evidence packet", "conflicting", 12, 1),
      packet("pkt-corpus-2", "Interface evidence packet", "aging", 8, 2)
    ],
    flags: [
      flag("flag-corpus-1", "Unresolved source reference", "SR-88 cannot support downstream evidence binding.", "critical"),
      flag("flag-corpus-2", "Duplicate occurrence preserved", "Dedupe reuse allowed; occurrence identity remains separate.", "verified")
    ],
    handoff: handoff("Lifecycle Stage Map", "Resolved SourceRefs and packet completeness candidates", "Before lifecycle dependency review", "critical"),
    detail: {
      metrics: [
        metric("Ingest session", "GIS-042", "watch"),
        metric("SourceRefs open", "3", "critical"),
        metric("Packet completeness", "blocked", "critical")
      ],
      cardsTitle: "Corpus custody and occurrence",
      cards: [
        card("Governed ingest session", "Quarantine active", "Custody and checksum state are visible before any evidence binding.", "watch"),
        card("Artifact-role review task", "Assigned", "Unclear role candidates stay in a review task instead of defaulting silently.", "critical"),
        card("Duplicate occurrence preserved", "2 contexts", "Dedupe can reuse work, but every occurrence remains visible.", "verified"),
        card("Sensitive file quarantine", "Redaction path", "Sensitive attachments are held out of packet completeness until reviewed.", "critical"),
        card("Unresolved SourceRef task", "SR-88", "A declared reference string is not meaningful evidence until resolved.", "critical")
      ],
      matrixTitle: "Packet formation matrix",
      matrixRows: [
        matrix("Procurement packet", "quote/order/revision grouped", "Commercial lead", "Role assignment board", "watch"),
        matrix("Interface packet", "unresolved SourceRefs", "Document control", "Source occurrence register", "critical"),
        matrix("Closure packet", "missing protocol binding", "Evidence analyst", "Packet register draft", "watch"),
        matrix("Issue packet", "not activated", "PMO analyst", "Activation profile", "neutral")
      ],
      timelineTitle: "Source inventory strip",
      timelineItems: [
        timeline("Blob ingest session", "08:20", "Synthetic files entered quarantine with custody markers.", "watch"),
        timeline("Duplicate group detected", "08:37", "Duplicate drawing kept with both occurrence contexts.", "verified"),
        timeline("SourceRef SR-88 blocked", "09:02", "Downstream evidence binding waits for meaningful occurrence resolution.", "critical"),
        timeline("Sensitive file held", "09:15", "Redaction review blocks packet completeness.", "critical")
      ],
      mockActionLabel: "Simulated packet completeness review disabled"
    }
  }),
  buildStepState("lifecycle", "watch", {
    summary:
      "Execution is the dominant display stage, but earlier assumption and interface obligations still affect readiness.",
    registerTitle: "Lifecycle stage evidence map",
    registerRows: [
      row("lifecycle-1", "Dominant stage", "Execution with commissioning dependency", "PM D. Lane", "Stage evidence map", "watch"),
      row("lifecycle-2", "Backward dependency", "Permit basis depends on unresolved utility interface", "Engineering lead", "Interface register draft", "critical"),
      row("lifecycle-3", "Recurrence trigger", "Operator training evidence expires before handover", "Operations lead", "Training packet", "watch")
    ],
    tasks: [
      task(
        "task-lifecycle-1",
        "Review handover-with-open-closure warning",
        "Operations lead",
        "Tomorrow",
        "Lifecycle recurrence list",
        "Demo snapshot must show closure dimensions as open.",
        "watch"
      )
    ],
    evidencePackets: [packet("pkt-lifecycle-1", "Lifecycle stage packet", "aging", 9, 0)],
    flags: [flag("flag-lifecycle-1", "Display stage is not formal closure", "Open closure dimensions remain visible.", "watch")],
    handoff: handoff("Commitment Chain", "Dominant stage, stale triggers, dependency flags", "Before commitment escalation", "watch"),
    detail: {
      metrics: [
        metric("Dominant stage", "Execution", "watch"),
        metric("Backward deps", "2", "critical"),
        metric("Recurrence", "due", "watch")
      ],
      cardsTitle: "Lifecycle stage context",
      cards: [
        card("Dominant active stage", "Execution", "Navigation stage only; it does not close earlier obligations.", "watch"),
        card("Stage conflict review", "Engineering vs commissioning", "Conflicting evidence is displayed as a review task candidate.", "critical"),
        card("Recurrence due stale/reopen task", "Operator training", "Time can stale earlier closure without a new document.", "watch"),
        card("Handover-with-open-closure warning", "Closure dimensions open", "Handover display cannot imply formal close.", "critical")
      ],
      matrixTitle: "Lifecycle stage evidence map",
      matrixRows: [
        matrix("Engineering", "reviewed basis", "Engineering lead", "Design packet", "verified"),
        matrix("Execution", "dominant display", "PM D. Lane", "Stage evidence map", "watch"),
        matrix("Commissioning", "blocked by interface", "Controls lead", "Interface register draft", "critical"),
        matrix("Handover", "not closed", "Operations lead", "Open closure warning", "critical")
      ],
      timelineTitle: "Stale and recurrence triggers",
      timelineItems: [
        timeline("Design stage evidence accepted", "T-12", "Design basis remains visible as historical context.", "verified"),
        timeline("Execution became dominant", "T-5", "Display stage changed without closing older obligations.", "watch"),
        timeline("Training recurrence due", "Now", "Operator training must be reopened before handover.", "watch")
      ],
      mockActionLabel: "Simulated stage handoff disabled"
    }
  }),
  buildStepState("commitment", "critical", {
    summary:
      "A quote/order revision mismatch and unapproved change request block the commercial basis for PM handoff.",
    registerTitle: "Commitment chain and decision gaps",
    registerRows: [
      row("commitment-1", "Revision chain", "Order revision does not match latest quote basis", "Commercial lead", "Commitment chain draft", "critical"),
      row("commitment-2", "Responsibility transfer", "Utility interface ownership not accepted", "Site owner", "Responsibility transfer map", "critical"),
      row("commitment-3", "Expenditure observation", "Invoice presence only; not technical closure", "Finance observer", "External observation", "watch")
    ],
    tasks: [
      task(
        "task-commitment-1",
        "Package quote/order mismatch for procurement decision",
        "Commercial lead",
        "Today",
        "Commitment chain draft",
        "Procurement decision cannot be represented as a hidden status.",
        "critical"
      )
    ],
    evidencePackets: [packet("pkt-commitment-1", "Commitment chain packet", "conflicting", 10, 1)],
    flags: [
      flag("flag-commitment-1", "Commercial settlement is not technical closure", "Invoice observation cannot close supplier assumption.", "critical")
    ],
    handoff: handoff("Supplier Assumption Closure", "Exact commitment-chain version and gap register", "Before waiver review", "critical"),
    detail: {
      metrics: [
        metric("Revision gaps", "2", "critical"),
        metric("Escalations", "1", "critical"),
        metric("Observation ledger", "not accounting", "watch")
      ],
      cardsTitle: "Commitment chain pressure",
      cards: [
        card("Quote/order revision mismatch review", "Order rev B vs quote rev C", "The PM must package the mismatch for procurement decision.", "critical"),
        card("Budget/exposure threshold CEO escalation", "Threshold crossed", "Exposure is modeled as a task packet, not an editable status cell.", "critical"),
        card("Commercial-not-technical closure guard", "Invoice observed", "A paid invoice or settlement does not close technical assumptions.", "critical"),
        card("Responsibility transfer map", "Utility owner not accepted", "Burden remains visible until accepted by a named actor.", "critical")
      ],
      matrixTitle: "Quote/order revision chain",
      matrixRows: [
        matrix("Quote Q-14", "superseded by Q-15", "Commercial lead", "Quote packet", "verified"),
        matrix("Order AB-22", "basis mismatch", "Procurement owner", "Commitment chain draft", "critical"),
        matrix("Change request CR-07", "unapproved", "PM D. Lane", "Gap register", "critical"),
        matrix("Settlement note", "external observation", "Finance observer", "Observation ledger", "watch")
      ],
      timelineTitle: "Commitment chain timeline",
      timelineItems: [
        timeline("Quote version imported", "T-10", "Candidate extraction created a non-final commitment row.", "verified"),
        timeline("Order revision received", "T-7", "Revision order did not commute cleanly with quote basis.", "critical"),
        timeline("CEO escalation candidate", "Now", "Exposure threshold creates a decision task packet in the demo.", "critical")
      ],
      mockActionLabel: "Simulated procurement escalation disabled"
    }
  }),
  buildStepState("assumptions", "watch", {
    summary:
      "Most supplier assumptions have an evidence basis, but one direct-conformance assumption needs waiver or replacement validation.",
    registerTitle: "Assumption closure matrix",
    registerRows: [
      row("assumptions-1", "Cooling clearance", "Closed by supersession", "Engineering lead", "Revision packet", "verified"),
      row("assumptions-2", "Operator access", "Replacement validation required", "Operations lead", "Site walkdown note", "watch"),
      row("assumptions-3", "Supplier duty caveat", "Contradiction candidate", "PM D. Lane", "Quote caveat", "critical")
    ],
    tasks: [
      task(
        "task-assumptions-1",
        "Decide waiver or replacement path for operator access",
        "Operations lead",
        "This week",
        "Assumption closure matrix",
        "Residual risk remains open until the path is explicit.",
        "watch"
      )
    ],
    evidencePackets: [packet("pkt-assumptions-1", "Assumption closure packet", "aging", 7, 0)],
    flags: [flag("flag-assumptions-1", "Replacement proposal is not validation", "Closure requires reviewed evidence.", "watch")],
    handoff: handoff("Owner Interface Resolution", "Reviewed assumption matrix and residual-risk notes", "Before actor acceptance", "watch"),
    detail: {
      metrics: [
        metric("Open assumptions", "3", "watch"),
        metric("Contradictions", "1", "critical"),
        metric("Waivers", "1 pending", "watch")
      ],
      cardsTitle: "Assumption closure paths",
      cards: [
        card("Missing evidence", "Operator access proof", "Assumption remains open until evidence is bound to a source occurrence.", "critical"),
        card("Supplier clarification", "Duty caveat", "Clarification is assigned as a task because absence of contradiction is not closure.", "watch"),
        card("Waiver approval", "Residual risk path", "Waiver can satisfy a path only after explicit review.", "watch"),
        card("Validated replacement", "Not yet proven", "Replacement proposal is distinct from replacement validation.", "critical")
      ],
      matrixTitle: "Assumption closure matrix",
      matrixRows: [
        matrix("Cooling clearance", "closed by supersession", "Engineering lead", "Revision packet", "verified"),
        matrix("Operator access", "missing evidence", "Operations lead", "Site walkdown note", "critical"),
        matrix("Supplier duty caveat", "supplier clarification", "PM D. Lane", "Quote caveat", "watch"),
        matrix("Residual risk", "waiver approval pending", "PMO reviewer", "Risk acceptance packet", "watch")
      ],
      timelineTitle: "Closure mode strip",
      timelineItems: [
        timeline("Assumptions extracted", "T-8", "Candidates came from quote, protocol, and drawing packets.", "verified"),
        timeline("Contradiction candidate found", "T-4", "Supplier duty caveat conflicts with owner interface evidence.", "critical"),
        timeline("Waiver path opened", "Now", "Residual risk task is visible but cannot be approved in the demo.", "watch")
      ],
      mockActionLabel: "Simulated waiver review disabled"
    }
  }),
  buildStepState("interfaces", "critical", {
    summary:
      "The owner/provider/receiver matrix exposes an unassigned utility condition and missing actor-specific acceptance.",
    registerTitle: "Interface responsibility matrix",
    registerRows: [
      row("interfaces-1", "Utility tie-in", "Provider unassigned", "Site owner", "Interface register draft", "critical"),
      row("interfaces-2", "Control signal readiness", "Required proof missing", "Controls lead", "Evidence vector", "critical"),
      row("interfaces-3", "Operator acceptance", "Acceptance card not returned", "Operations lead", "Handoff checklist", "watch")
    ],
    tasks: [
      task(
        "task-interfaces-1",
        "Assign utility tie-in provider and receiver",
        "Site owner",
        "Today",
        "Interface register draft",
        "Burden remains with project until accepted.",
        "critical"
      ),
      task(
        "task-interfaces-2",
        "Collect actor-specific acceptance for control signal readiness",
        "Controls lead",
        "Tomorrow",
        "Required-vs-provided evidence vector",
        "Commissioning readiness remains blocked.",
        "critical"
      )
    ],
    evidencePackets: [packet("pkt-interfaces-1", "Interface evidence packet", "stale", 11, 1)],
    flags: [flag("flag-interfaces-1", "Interface burden not accepted", "Responsibility transfer is incomplete.", "critical")],
    handoff: handoff("Project State Snapshot", "Interface register, burden flags, and acceptance evidence", "Before snapshot candidate", "critical"),
    detail: {
      metrics: [
        metric("Unassigned owners", "1", "critical"),
        metric("Evidence conflicts", "1", "critical"),
        metric("Acceptances", "2 open", "watch")
      ],
      cardsTitle: "Interface responsibility board",
      cards: [
        card("Unassigned owner blocking task", "Utility tie-in", "No provider has accepted the condition, so burden remains with the project.", "critical"),
        card("Required/provided condition conflict", "Control signal proof", "Provided evidence does not satisfy the required interface condition.", "critical"),
        card("Authority/operator acceptance task", "Actor-specific", "Acceptance must be returned by the right actor, not inferred from file presence.", "watch"),
        card("Burden conservation warning", "Transfer incomplete", "If supplier does not hold the burden, owner/project still does.", "critical")
      ],
      matrixTitle: "Owner/provider/receiver matrix",
      matrixRows: [
        matrix("Utility tie-in", "provider unassigned", "Site owner", "Interface register draft", "critical"),
        matrix("Control signal readiness", "required/provided conflict", "Controls lead", "Evidence vector", "critical"),
        matrix("Operator acceptance", "awaiting actor card", "Operations lead", "Acceptance checklist", "watch"),
        matrix("Authority confirmation", "required", "Authority liaison", "Permit condition", "watch")
      ],
      timelineTitle: "Interface resolution strip",
      timelineItems: [
        timeline("Distributed requirement found", "T-6", "Utility and control requirements were extracted from synthetic packets.", "verified"),
        timeline("Burden transfer failed", "T-3", "Provider did not accept the condition.", "critical"),
        timeline("Actor acceptance pending", "Now", "Operator and authority cards are still open.", "watch")
      ],
      mockActionLabel: "Simulated interface acceptance disabled"
    }
  }),
  buildStepState("snapshot", "watch", {
    summary:
      "Snapshot inputs are visible, but unresolved SourceRefs, open interface burden, and stale evidence block review-ready status.",
    registerTitle: "Snapshot basis vector",
    registerRows: [
      row("snapshot-1", "Reviewed inputs", "Five of seven step packets included", "PM D. Lane", "Snapshot basis vector", "watch"),
      row("snapshot-2", "Stale check", "Interface packet needs refresh", "Workflow analyst", "Validation vector", "critical"),
      row("snapshot-3", "Promotion guard", "Pointer promotion disabled in demo", "PMO reviewer", "Mock gate note", "verified")
    ],
    tasks: [
      task(
        "task-snapshot-1",
        "Refresh snapshot input basis after interface resolution",
        "Workflow analyst",
        "This week",
        "Snapshot validation vector",
        "Project remains blocked from review-ready snapshot projection.",
        "watch"
      )
    ],
    evidencePackets: [packet("pkt-snapshot-1", "Snapshot candidate packet", "aging", 15, 2)],
    flags: [flag("flag-snapshot-1", "Approved is not official without pointer promotion", "Promotion is disabled in this mock demo.", "verified")],
    handoff: handoff("CEO transparency layer", "Reviewed snapshot candidate and open blocker packet", "After all blockers clear", "watch"),
    detail: {
      metrics: [
        metric("Reviewed inputs", "5 / 7", "watch"),
        metric("Blocking checks", "3", "critical"),
        metric("Promotion", "disabled", "neutral")
      ],
      cardsTitle: "Snapshot readiness checks",
      cards: [
        card("Unresolved SourceRef blocker", "SR-88", "Snapshot candidate cannot claim reviewed basis while SourceRefs remain open.", "critical"),
        card("Closure contradiction blocker", "Duty caveat vs interface", "Contradictory evidence must stay visible and block review-ready state.", "critical"),
        card("Stale basis rebuild task", "Interface packet", "A stale pointer generation requires rebuild before review.", "watch"),
        card("Disabled promotion candidate", "Mock only", "The demo can show a candidate, but cannot promote an official pointer.", "neutral")
      ],
      matrixTitle: "Reviewed input basis vector",
      matrixRows: [
        matrix("Intake profile", "included", "PM D. Lane", "Intake handoff", "verified"),
        matrix("Corpus packet", "blocked by SourceRef", "Document control", "Packet register", "critical"),
        matrix("Interface packet", "stale basis", "Workflow analyst", "Validation vector", "watch"),
        matrix("Closure dimensions", "contradiction open", "PMO reviewer", "State graph check", "critical")
      ],
      timelineTitle: "Snapshot build strip",
      timelineItems: [
        timeline("Inputs collected", "T-2", "Reviewed inputs were assembled from the synthetic step packets.", "watch"),
        timeline("Consistency check failed", "T-1", "Contradiction and unresolved SourceRef blockers stayed visible.", "critical"),
        timeline("Promotion held", "Now", "Pointer promotion is disabled in this frontend-only route.", "neutral")
      ],
      mockActionLabel: "Simulated pointer promotion disabled"
    }
  })
];

function compactSteps(activeStep: CapxPmStepSlug, projectCode: string, hotStatus: CapxPmStatus): CapxPmStepState[] {
  return capxPmWorkflowSteps.map((step) => {
    const status = step.slug === activeStep ? hotStatus : step.number < 3 ? "verified" : "neutral";
    return buildStepState(step.slug, status, {
      summary: `${projectCode} has a compact ${step.shortTitle.toLowerCase()} projection for routing review.`,
      registerRows: [
        row(
          `${projectCode}-${step.slug}-row-1`,
          `${step.shortTitle} PM check`,
          step.slug === activeStep ? "Active PM focus" : "No material exception in first tranche mock",
          "Assigned PM",
          "Synthetic workflow register",
          status
        )
      ],
      tasks:
        step.slug === activeStep
          ? [
              task(
                `${projectCode}-${step.slug}-task-1`,
                `${step.shortTitle} next PM action`,
                "Assigned PM",
                "This week",
                "Synthetic workflow register",
                "Demo readiness remains tied to this selected step.",
                status
              )
            ]
          : [],
      flags:
        step.slug === activeStep
          ? [flag(`${projectCode}-${step.slug}-flag-1`, `${step.shortTitle} attention point`, "Synthetic blocker profile", status)]
          : [],
      evidencePackets: [packet(`${projectCode}-${step.slug}-pkt-1`, `${step.shortTitle} packet`, status === "critical" ? "stale" : "fresh", 3, status === "critical" ? 1 : 0)],
      handoff: handoff("Next PM step", "Synthetic register basis", "During demo review", status)
    });
  });
}

export const capxPmDemoState: CapxPmDemoState = {
  generatedAt: "19 May 10:05",
  workflowSteps: capxPmWorkflowSteps,
  projects: [
    {
      id: "PM-204",
      code: "PM-204",
      name: "Meridian Mock Line",
      site: "Site Delta",
      projectType: "Production cell upgrade",
      pmOwner: "D. Lane",
      ownerRole: "Project manager",
      dominantStage: "Execution",
      activeStep: "corpus",
      status: "critical",
      blockerSummary: "Unresolved SourceRef and utility interface ownership",
      openBlockers: 4,
      openTasks: 8,
      evidenceFreshness: "conflicting",
      snapshotReadiness: "blocked",
      lastMaterialChange: "19 May - SourceRef exception opened",
      steps: meridianSteps
    },
    {
      id: "PM-318",
      code: "PM-318",
      name: "Solstice Utility Tie-In",
      site: "Site Kappa",
      projectType: "Utility readiness",
      pmOwner: "M. Ivers",
      ownerRole: "Interface PM",
      dominantStage: "Commissioning",
      activeStep: "interfaces",
      status: "critical",
      blockerSummary: "Provider acceptance not assigned",
      openBlockers: 3,
      openTasks: 6,
      evidenceFreshness: "stale",
      snapshotReadiness: "blocked",
      lastMaterialChange: "18 May - Burden transfer disputed",
      steps: compactSteps("interfaces", "PM-318", "critical")
    },
    {
      id: "PM-142",
      code: "PM-142",
      name: "Northstar Packaging Cell",
      site: "Site Vega",
      projectType: "Packaging automation",
      pmOwner: "R. Holt",
      ownerRole: "Project manager",
      dominantStage: "Procurement",
      activeStep: "assumptions",
      status: "watch",
      blockerSummary: "Replacement validation path pending",
      openBlockers: 1,
      openTasks: 5,
      evidenceFreshness: "aging",
      snapshotReadiness: "draftable",
      lastMaterialChange: "17 May - Supplier caveat superseded",
      steps: compactSteps("assumptions", "PM-142", "watch")
    },
    {
      id: "PM-277",
      code: "PM-277",
      name: "Horizon Test Bay",
      site: "Site Lumen",
      projectType: "Validation bay",
      pmOwner: "S. Park",
      ownerRole: "Project manager",
      dominantStage: "Engineering",
      activeStep: "lifecycle",
      status: "watch",
      blockerSummary: "Lifecycle recurrence check due",
      openBlockers: 1,
      openTasks: 3,
      evidenceFreshness: "aging",
      snapshotReadiness: "draftable",
      lastMaterialChange: "17 May - Stage map refreshed",
      steps: compactSteps("lifecycle", "PM-277", "watch")
    },
    {
      id: "PM-331",
      code: "PM-331",
      name: "Quartz Transfer Hub",
      site: "Site Orion",
      projectType: "Material transfer",
      pmOwner: "A. Vale",
      ownerRole: "Project manager",
      dominantStage: "Handover",
      activeStep: "snapshot",
      status: "verified",
      blockerSummary: "Snapshot review packet ready",
      openBlockers: 0,
      openTasks: 2,
      evidenceFreshness: "fresh",
      snapshotReadiness: "review-ready",
      lastMaterialChange: "16 May - Snapshot candidate rebuilt",
      steps: compactSteps("snapshot", "PM-331", "verified")
    },
    {
      id: "PM-109",
      code: "PM-109",
      name: "Vector Metering Upgrade",
      site: "Site Nova",
      projectType: "Metering refresh",
      pmOwner: "K. Rowan",
      ownerRole: "Project coordinator",
      dominantStage: "Initiation",
      activeStep: "intake",
      status: "neutral",
      blockerSummary: "Awaiting initial module selection",
      openBlockers: 0,
      openTasks: 2,
      evidenceFreshness: "fresh",
      snapshotReadiness: "draftable",
      lastMaterialChange: "16 May - Project shell created",
      steps: compactSteps("intake", "PM-109", "neutral")
    }
  ]
};
