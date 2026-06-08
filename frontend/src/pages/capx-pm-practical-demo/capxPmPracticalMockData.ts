import type {
  CapxPmPracticalCard,
  CapxPmPracticalChecklistItem,
  CapxPmPracticalDemoState,
  CapxPmPracticalFilter,
  CapxPmPracticalProject,
  CapxPmPracticalRecord,
  CapxPmPracticalStatus,
  CapxPmPracticalStep,
  CapxPmPracticalStepSlug,
  CapxPmPracticalTask
} from "./capxPmPracticalTypes";

export const capxPmPracticalSteps: CapxPmPracticalStep[] = [
  {
    number: 1,
    slug: "setup",
    label: "Project setup",
    question: "Is the project correctly opened and assigned?",
    traceId: "WFLOW-001"
  },
  {
    number: 2,
    slug: "documents",
    label: "Documents",
    question: "Do we have the right files and versions?",
    traceId: "WFLOW-002"
  },
  {
    number: 3,
    slug: "timeline",
    label: "Timeline",
    question: "Where are we and what is late?",
    traceId: "WFLOW-003"
  },
  {
    number: 4,
    slug: "budget-orders",
    label: "Budget & orders",
    question: "What changed commercially?",
    traceId: "WFLOW-004"
  },
  {
    number: 5,
    slug: "supplier-questions",
    label: "Supplier questions",
    question: "What does the supplier still owe us?",
    traceId: "WFLOW-005"
  },
  {
    number: 6,
    slug: "site-handoffs",
    label: "Site handoffs",
    question: "What must the site provide or accept?",
    traceId: "WFLOW-006"
  },
  {
    number: 7,
    slug: "project-report",
    label: "Project report",
    question: "Can this be reported upward?",
    traceId: "WFLOW-007"
  }
];

function task(
  id: string,
  title: string,
  owner: string,
  due: string,
  supportingFile: string,
  consequence: string,
  status: CapxPmPracticalStatus,
  tags: CapxPmPracticalFilter[]
): CapxPmPracticalTask {
  return { id, title, owner, due, supportingFile, consequence, status, tags };
}

function record(
  id: string,
  item: string,
  owner: string,
  due: string,
  status: CapxPmPracticalStatus,
  supportingFile: string,
  note: string
): CapxPmPracticalRecord {
  return { id, item, owner, due, status, supportingFile, note };
}

function checklist(label: string, owner: string, status: CapxPmPracticalStatus): CapxPmPracticalChecklistItem {
  return { label, owner, status };
}

function card(title: string, value: string, body: string, status: CapxPmPracticalStatus): CapxPmPracticalCard {
  return { title, value, body, status };
}

const meridianSteps = [
  {
    slug: "setup",
    status: "needs-work",
    headline: "Sponsor and folder still need confirmation",
    summary:
      "The project is opened and assigned, but the sponsor name and document folder must be confirmed before normal tracking.",
    primaryAction: task(
      "task-setup-1",
      "Confirm sponsor and document folder",
      "PM Alex M.",
      "Today",
      "Project opening note",
      "Project cannot enter normal tracking until both are confirmed.",
      "needs-work",
      ["missing", "overdue"]
    ),
    checklistTitle: "Setup checklist",
    checklist: [
      checklist("PM assigned", "PMO", "done"),
      checklist("Sponsor confirmed", "PM Alex M.", "needs-work"),
      checklist("Budget owner known", "Finance", "done"),
      checklist("Site / area selected", "PM Alex M.", "done"),
      checklist("Document folder chosen", "PM Alex M.", "blocked"),
      checklist("Reporting path selected", "Sponsor", "needs-work")
    ],
    cardsTitle: "Work areas to open",
    cards: [
      card("Documents", "3 missing", "Order and handover files still need chasing.", "blocked"),
      card("Budget & orders", "Quote changed", "Finance must review the changed quote before send-up.", "needs-work"),
      card("Site handoffs", "Production owes date", "Shutdown window is not confirmed.", "blocked")
    ],
    tableTitle: "Setup blockers",
    records: [
      record("setup-1", "Sponsor confirmation", "PM Alex M.", "Today", "needs-work", "Project opening note", "Name is not signed off."),
      record("setup-2", "Document folder", "PM Alex M.", "Today", "blocked", "Shared folder request", "Folder path is not selected."),
      record("setup-3", "Reporting path", "Sponsor", "Tomorrow", "needs-work", "Kickoff minutes", "Send-up owner is not confirmed.")
    ],
    supportingFiles: ["Project opening note", "Kickoff minutes", "Shared folder request"],
    reportNote: "Do not call setup complete until the sponsor and folder are confirmed."
  },
  {
    slug: "documents",
    status: "blocked",
    headline: "Missing order blocks budget reporting",
    summary:
      "The latest quote is attached, but the matching order is missing. Upload the order or mark the work as not ordered yet.",
    primaryAction: task(
      "task-documents-1",
      "Upload missing order attachment",
      "PM Alex M. / Procurement",
      "This week",
      "Supplier quote Q-144",
      "Budget and order status cannot be reported.",
      "blocked",
      ["missing", "blocked"]
    ),
    checklistTitle: "Document checklist",
    checklist: [
      checklist("Business case", "PM Alex M.", "done"),
      checklist("Approved budget", "Finance", "done"),
      checklist("Quote", "Procurement", "done"),
      checklist("Order / PO", "Procurement", "blocked"),
      checklist("Drawing", "Engineering", "needs-work"),
      checklist("Permit / safety document", "Site safety", "needs-work"),
      checklist("Supplier email", "Supplier", "done"),
      checklist("Site handover document", "Production", "not-started")
    ],
    cardsTitle: "Document packs",
    cards: [
      card("Budget pack", "Order missing", "Quote is present, but order file is not attached.", "blocked"),
      card("Supplier pack", "Needs review", "Supplier email is present, drawing revision needs checking.", "needs-work"),
      card("Report pack", "Not ready", "Report pack cannot close while the order is missing.", "blocked")
    ],
    tableTitle: "Files to chase",
    records: [
      record("documents-1", "Order / PO attachment", "Procurement", "This week", "blocked", "Supplier quote Q-144", "Order file is missing."),
      record("documents-2", "Updated drawing", "Engineering", "Friday", "needs-work", "Drawing Rev B", "Drawing version needs PM review."),
      record("documents-3", "Safety permit", "Site safety", "Friday", "needs-work", "Permit request", "Permit is requested but not returned.")
    ],
    supportingFiles: ["Supplier quote Q-144", "Drawing Rev B", "Permit request"],
    reportNote: "Report remains blocked until the order attachment is uploaded or marked not ordered."
  },
  {
    slug: "timeline",
    status: "needs-work",
    headline: "Installation date moved by two weeks",
    summary:
      "Installation moved from 12 June to 26 June. Re-check supplier delivery and production shutdown before sending the report.",
    primaryAction: task(
      "task-timeline-1",
      "Confirm new installation date",
      "PM Alex M. / Supplier",
      "Today",
      "Supplier delivery email",
      "Schedule report may be stale.",
      "needs-work",
      ["changed", "overdue"]
    ),
    checklistTitle: "Timeline check",
    checklist: [
      checklist("Idea", "Sponsor", "done"),
      checklist("Approved", "Sponsor", "done"),
      checklist("Design", "Engineering", "done"),
      checklist("Ordered", "Procurement", "needs-work"),
      checklist("Installation", "PM Alex M.", "blocked"),
      checklist("Commissioning", "Production", "not-started"),
      checklist("Handover", "Production", "not-started")
    ],
    cardsTitle: "Schedule signals",
    cards: [
      card("Next milestone", "Install start", "Current target is 26 June.", "needs-work"),
      card("Delay reason", "Supplier delivery", "Supplier delivery slipped after the last review.", "blocked"),
      card("Needs re-check", "Report date", "Timeline changed after the report was drafted.", "needs-work")
    ],
    tableTitle: "Milestone changes",
    records: [
      record("timeline-1", "Supplier delivery", "Supplier", "Today", "blocked", "Supplier delivery email", "Delivery confirmation is overdue."),
      record("timeline-2", "Installation start", "PM Alex M.", "Today", "needs-work", "Project schedule", "Date moved to 26 June."),
      record("timeline-3", "Production shutdown", "Production", "Friday", "blocked", "Shutdown request", "Production has not confirmed the date.")
    ],
    supportingFiles: ["Project schedule", "Supplier delivery email", "Shutdown request"],
    reportNote: "Re-check timeline before sending any upward report."
  },
  {
    slug: "budget-orders",
    status: "blocked",
    headline: "Quote increased after the order pack was prepared",
    summary:
      "The supplier quote increased by 48k after the order pack was prepared. Finance review is required before this can be reported as approved.",
    primaryAction: task(
      "task-budget-1",
      "Review quote increase",
      "Finance",
      "This week",
      "Revised supplier quote",
      "Approval pack cannot be sent.",
      "blocked",
      ["changed", "blocked"]
    ),
    checklistTitle: "Budget and order check",
    checklist: [
      checklist("Approved budget", "Finance", "done"),
      checklist("Current estimate", "Finance", "needs-work"),
      checklist("Committed spend", "Procurement", "needs-work"),
      checklist("Pending changes", "PM Alex M.", "blocked"),
      checklist("Order placed", "Procurement", "blocked")
    ],
    cardsTitle: "Commercial warnings",
    cards: [
      card("Quote changed", "+48k", "Supplier quote changed after approval pack prep.", "blocked"),
      card("Order missing", "PO not attached", "Order amount cannot be confirmed.", "blocked"),
      card("Finance review", "Required", "Finance must confirm the revised amount.", "needs-work")
    ],
    tableTitle: "Quote and order chain",
    records: [
      record("budget-1", "Original quote", "Procurement", "Done", "done", "Supplier quote Q-144", "Original amount recorded."),
      record("budget-2", "Revised quote", "Finance", "This week", "blocked", "Revised supplier quote", "Increase needs review."),
      record("budget-3", "Order attachment", "Procurement", "This week", "blocked", "Order request", "Matching order is missing.")
    ],
    supportingFiles: ["Supplier quote Q-144", "Revised supplier quote", "Order request"],
    reportNote: "Budget status cannot be reported as approved until Finance reviews the changed quote."
  },
  {
    slug: "supplier-questions",
    status: "blocked",
    headline: "Supplier foundation answer is overdue",
    summary:
      "Supplier has not confirmed whether the existing foundation is sufficient. This blocks final order release.",
    primaryAction: task(
      "task-supplier-1",
      "Confirm foundation assumption",
      "Supplier contact",
      "Friday",
      "Foundation question email",
      "Order release remains blocked.",
      "blocked",
      ["overdue", "blocked"]
    ),
    checklistTitle: "Supplier open points",
    checklist: [
      checklist("Technical question", "Supplier", "blocked"),
      checklist("Delivery question", "Supplier", "needs-work"),
      checklist("Cost question", "Supplier", "done"),
      checklist("Warranty / service question", "Supplier", "needs-work"),
      checklist("Safety question", "Supplier", "ready-review")
    ],
    cardsTitle: "Supplier chase cards",
    cards: [
      card("Foundation answer", "Overdue", "Supplier answer is needed before order release.", "blocked"),
      card("Delivery promise", "Needs review", "Supplier gave a new date; PM must review impact.", "needs-work"),
      card("Safety answer", "Ready", "Safety answer is ready for PM review.", "ready-review")
    ],
    tableTitle: "Supplier question register",
    records: [
      record("supplier-1", "Foundation capacity", "Supplier contact", "Friday", "blocked", "Foundation question email", "No answer received."),
      record("supplier-2", "Delivery lead time", "Supplier contact", "Today", "needs-work", "Delivery reply", "New date needs PM review."),
      record("supplier-3", "Warranty terms", "Supplier contact", "Next week", "needs-work", "Warranty note", "Supplier answer is partial.")
    ],
    supportingFiles: ["Foundation question email", "Delivery reply", "Warranty note"],
    reportNote: "Keep supplier questions visible until foundation capacity is answered."
  },
  {
    slug: "site-handoffs",
    status: "blocked",
    headline: "Production has not confirmed the shutdown window",
    summary:
      "Production has not confirmed the shutdown window. Installation cannot be treated as ready until this is confirmed.",
    primaryAction: task(
      "task-site-1",
      "Confirm shutdown window",
      "Production",
      "Friday",
      "Shutdown request",
      "Installation readiness remains blocked.",
      "blocked",
      ["overdue", "blocked"]
    ),
    checklistTitle: "Site handoff checklist",
    checklist: [
      checklist("Shutdown window", "Production", "blocked"),
      checklist("Access permit", "Site safety", "needs-work"),
      checklist("Utility isolation", "Maintenance", "needs-work"),
      checklist("Production acceptance", "Production", "blocked"),
      checklist("Maintenance training", "Maintenance", "needs-work"),
      checklist("Safety sign-off", "Site safety", "ready-review")
    ],
    cardsTitle: "Acceptance cards",
    cards: [
      card("Production", "Not confirmed", "Shutdown window is still open.", "blocked"),
      card("Maintenance", "Training open", "Training plan has not been accepted.", "needs-work"),
      card("Site safety", "Ready", "Safety sign-off is ready for review.", "ready-review")
    ],
    tableTitle: "Responsibility board",
    records: [
      record("site-1", "Shutdown window", "Production", "Friday", "blocked", "Shutdown request", "Production has not confirmed."),
      record("site-2", "Training plan", "Maintenance", "Next week", "needs-work", "Training plan", "Maintenance has questions."),
      record("site-3", "Safety sign-off", "Site safety", "Today", "ready-review", "Permit request", "Ready for PM review.")
    ],
    supportingFiles: ["Shutdown request", "Training plan", "Permit request"],
    reportNote: "Site handoff must stay blocked until Production confirms the shutdown window."
  },
  {
    slug: "project-report",
    status: "blocked",
    headline: "Report is not ready to send upward",
    summary:
      "Do not send this report yet. The order amount changed after the report was prepared and the production handoff is still unconfirmed.",
    primaryAction: task(
      "task-report-1",
      "Re-check report after changes",
      "PM Alex M.",
      "Before send-up",
      "Draft PM report",
      "Report may be misleading.",
      "blocked",
      ["changed", "blocked"]
    ),
    checklistTitle: "Report readiness checklist",
    checklist: [
      checklist("Setup complete", "PM Alex M.", "needs-work"),
      checklist("Required documents present", "PM Alex M.", "blocked"),
      checklist("Timeline reviewed", "PM Alex M.", "needs-work"),
      checklist("Budget and orders reviewed", "Finance", "blocked"),
      checklist("Supplier questions reviewed", "PM Alex M.", "blocked"),
      checklist("Site handoffs reviewed", "Production", "blocked"),
      checklist("Blockers explained", "PM Alex M.", "needs-work")
    ],
    cardsTitle: "Report preview",
    cards: [
      card("Current phase", "Procurement", "Order and shutdown remain open.", "needs-work"),
      card("Top issue", "Order missing", "Quote changed and order is not attached.", "blocked"),
      card("Confidence", "Low", "Too many open items to send upward.", "blocked")
    ],
    tableTitle: "Cannot-send reasons",
    records: [
      record("report-1", "Missing order", "Procurement", "This week", "blocked", "Order request", "Order file is missing."),
      record("report-2", "Budget change not reviewed", "Finance", "This week", "blocked", "Revised supplier quote", "Finance has not reviewed."),
      record("report-3", "Site handoff not confirmed", "Production", "Friday", "blocked", "Shutdown request", "Production has not confirmed.")
    ],
    supportingFiles: ["Draft PM report", "Order request", "Revised supplier quote", "Shutdown request"],
    reportNote: "Report not ready. Re-check after order, budget, and Production items are cleared."
  }
] satisfies CapxPmPracticalProject["steps"];

function compactProject(
  id: string,
  name: string,
  siteArea: string,
  pm: string,
  sponsor: string,
  phase: string,
  needsAttention: string,
  severeBlocker: string,
  activeStep: CapxPmPracticalStepSlug,
  status: CapxPmPracticalStatus,
  filters: CapxPmPracticalFilter[]
): CapxPmPracticalProject {
  return {
    id,
    name,
    siteArea,
    pm,
    sponsor,
    phase,
    needsAttention,
    blockers: status === "blocked" ? 2 : status === "needs-work" ? 1 : 0,
    severeBlocker,
    tasksDue: status === "blocked" ? 5 : status === "needs-work" ? 3 : 1,
    missingDocuments: filters.includes("missing") ? 3 : 0,
    budgetOrders: filters.includes("changed") ? "Quote changed" : "No change",
    schedule: filters.includes("overdue") ? "+2 weeks" : "On plan",
    supplierQuestions: filters.includes("overdue") ? "Open" : "Reviewed",
    siteHandoffs: status === "blocked" ? "Not confirmed" : "Tracking",
    reportStatus: status === "ready-review" || status === "done" ? "Ready for review" : "Not ready",
    lastUpdate: "18 May",
    topBlocker: severeBlocker,
    lastMaterialChange: filters.includes("changed") ? "Quote or date changed since last review" : "No major change",
    activeStep,
    status,
    filters,
    steps: meridianSteps.map((step) => ({
      ...step,
      status: step.slug === activeStep ? status : step.status === "blocked" && status !== "blocked" ? "needs-work" : step.status,
      primaryAction:
        step.slug === activeStep
          ? step.primaryAction
          : {
              ...step.primaryAction,
              id: `${id}-${step.primaryAction.id}`,
              owner: pm,
              due: status === "done" ? "Done" : step.primaryAction.due
            }
    }))
  };
}

const projects: CapxPmPracticalProject[] = [
  {
    id: "P-104",
    name: "Orion Facility",
    siteArea: "Line 4 / Packaging",
    pm: "Alex M.",
    sponsor: "Dana K.",
    phase: "Procurement",
    needsAttention: "Supplier answer overdue",
    blockers: 4,
    severeBlocker: "Missing order and shutdown window",
    tasksDue: 5,
    missingDocuments: 3,
    budgetOrders: "Quote changed",
    schedule: "+2 weeks",
    supplierQuestions: "4 open",
    siteHandoffs: "Production not confirmed",
    reportStatus: "Not ready",
    lastUpdate: "18 May",
    topBlocker: "Order missing and Production has not confirmed shutdown",
    lastMaterialChange: "Quote increased and install date moved",
    activeStep: "documents",
    status: "blocked",
    filters: ["missing", "overdue", "changed", "blocked"],
    steps: meridianSteps
  },
  compactProject(
    "P-087",
    "Helios Cleanroom Upgrade",
    "Cleanroom B / Utilities",
    "Maya R.",
    "Chris V.",
    "Installation",
    "Site access permit overdue",
    "Access permit not returned",
    "site-handoffs",
    "blocked",
    ["missing", "overdue", "blocked"]
  ),
  compactProject(
    "P-102",
    "Atlas Packing Cell",
    "Cell 2 / Packing",
    "Nico S.",
    "Priya T.",
    "Design",
    "Drawing changed after review",
    "Drawing update needs Engineering review",
    "timeline",
    "needs-work",
    ["changed"]
  ),
  compactProject(
    "P-118",
    "Nova Compressor Tie-in",
    "Utility Corridor / Plant 2",
    "Rina P.",
    "Sam G.",
    "Budget review",
    "Finance review waiting",
    "Changed quote needs Finance review",
    "budget-orders",
    "needs-work",
    ["changed", "blocked"]
  ),
  compactProject(
    "P-126",
    "Lyra Safety Refresh",
    "Warehouse / Safety",
    "Owen L.",
    "Jamie N.",
    "Report prep",
    "Ready for PM review",
    "Report pack is ready for review",
    "project-report",
    "ready-review",
    ["ready-review"]
  ),
  compactProject(
    "P-131",
    "Vega Controls Spare Kit",
    "Line 1 / Controls",
    "Elena Q.",
    "Morgan C.",
    "Setup",
    "Project opened cleanly",
    "No blocker",
    "setup",
    "done",
    ["ready-review"]
  )
];

export const capxPmPracticalDemoState: CapxPmPracticalDemoState = {
  generatedAt: "19 May 2025 10:15",
  projects,
  steps: capxPmPracticalSteps
};
