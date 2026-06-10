import type {
  CapxPmFeDemoAction,
  CapxPmFeDemoBlocker,
  CapxPmFeDemoBudgetItem,
  CapxPmFeDemoDocument,
  CapxPmFeDemoGanttItem,
  CapxPmFeDemoMilestone,
  CapxPmFeDemoProject,
  CapxPmFeDemoReport,
  CapxPmFeDemoSiteHandoff,
  CapxPmFeDemoState,
  CapxPmFeDemoStatus,
  CapxPmFeDemoStep,
  CapxPmFeDemoStepId,
  CapxPmFeDemoSupplierQuestion
} from "./capxPmFeDemoTypes";

export const capxPmFeDemoSteps: CapxPmFeDemoStep[] = [
  {
    id: "project-setup",
    number: 1,
    label: "Project setup",
    shortLabel: "Setup",
    question: "Is the project opened, assigned, and safe to track?"
  },
  {
    id: "documents",
    number: 2,
    label: "Documents",
    shortLabel: "Docs",
    question: "Do we have the right proof and latest files?"
  },
  {
    id: "timeline",
    number: 3,
    label: "Timeline",
    shortLabel: "Timeline",
    question: "What moved against plan?"
  },
  {
    id: "budget-orders",
    number: 4,
    label: "Budget & orders",
    shortLabel: "Budget",
    question: "What was approved, ordered, or changed?"
  },
  {
    id: "supplier-questions",
    number: 5,
    label: "Supplier questions",
    shortLabel: "Supplier",
    question: "What does the supplier still owe us?"
  },
  {
    id: "site-handoffs",
    number: 6,
    label: "Site handoffs",
    shortLabel: "Site",
    question: "What must site teams provide or accept?"
  },
  {
    id: "project-report",
    number: 7,
    label: "Project report",
    shortLabel: "Report",
    question: "Can the PM share a credible update?"
  }
];

function action(
  title: string,
  owner: string,
  due: string,
  blocker: string,
  proofNeeded: string,
  consequence: string,
  status: CapxPmFeDemoStatus
): CapxPmFeDemoAction {
  return { title, owner, due, blocker, proofNeeded, consequence, status };
}

function blocker(
  id: string,
  title: string,
  owner: string,
  due: string,
  waitingOn: string,
  proofNeeded: string,
  impact: string,
  status: CapxPmFeDemoStatus
): CapxPmFeDemoBlocker {
  return { id, title, owner, due, waitingOn, proofNeeded, impact, status };
}

function documentRecord(
  id: string,
  name: string,
  type: string,
  versionDate: string,
  usedFor: string,
  status: CapxPmFeDemoStatus,
  owner: string,
  actionText: string,
  detail: string
): CapxPmFeDemoDocument {
  return { id, name, type, versionDate, usedFor, status, owner, action: actionText, detail };
}

function milestone(
  id: string,
  name: string,
  baselineDate: string,
  forecastDate: string,
  deltaDays: number,
  owner: string,
  reason: string,
  confidence: string,
  status: CapxPmFeDemoStatus,
  changedSinceLastReport: boolean
): CapxPmFeDemoMilestone {
  return {
    id,
    name,
    baselineDate,
    forecastDate,
    deltaDays,
    owner,
    reason,
    confidence,
    status,
    changedSinceLastReport
  };
}

function budgetItem(
  id: string,
  item: string,
  approvedAmount: string,
  currentAmount: string,
  delta: string,
  document: string,
  approvalNeeded: string,
  owner: string,
  due: string,
  status: CapxPmFeDemoStatus
): CapxPmFeDemoBudgetItem {
  return { id, item, approvedAmount, currentAmount, delta, document, approvalNeeded, owner, due, status };
}

function supplierQuestion(
  id: string,
  question: string,
  supplier: string,
  due: string,
  blocks: string,
  proof: string,
  nextAction: string,
  status: CapxPmFeDemoStatus
): CapxPmFeDemoSupplierQuestion {
  return { id, question, supplier, due, blocks, proof, nextAction, status };
}

function siteHandoff(
  id: string,
  dependency: string,
  neededFrom: string,
  requiredBy: string,
  provided: string,
  acceptedBy: string,
  blocks: string,
  proof: string,
  nextAction: string,
  status: CapxPmFeDemoStatus
): CapxPmFeDemoSiteHandoff {
  return { id, dependency, neededFrom, requiredBy, provided, acceptedBy, blocks, proof, nextAction, status };
}

function ganttItem(
  id: string,
  workstream: string,
  task: string,
  owner: string,
  baselineLabel: string,
  forecastLabel: string,
  baselineStart: number,
  baselineSpan: number,
  forecastStart: number,
  forecastSpan: number,
  deltaDays: number,
  dependsOn: string,
  criticalPath: boolean,
  changedSinceLastReport: boolean,
  blockerText: string,
  status: CapxPmFeDemoStatus
): CapxPmFeDemoGanttItem {
  return {
    id,
    workstream,
    task,
    owner,
    baselineLabel,
    forecastLabel,
    baselineStart,
    baselineSpan,
    forecastStart,
    forecastSpan,
    deltaDays,
    dependsOn,
    criticalPath,
    changedSinceLastReport,
    blocker: blockerText,
    status
  };
}

const orionReport: CapxPmFeDemoReport = {
  readiness: "Not ready to share",
  currentStatus: "Procurement is blocked by a drawing version decision and a missing production window.",
  changesThisWeek: [
    "Supplier drawing moved from v6 to v7 after the order pack was drafted.",
    "Installation forecast moved three weeks later.",
    "Budget watch increased after revised conveyor controls were priced."
  ],
  topBlockers: [
    "Confirm whether drawing v7 replaces v6 before PO approval.",
    "Production must confirm the shutdown window.",
    "Quality owner must confirm acceptance checklist."
  ],
  scheduleMovement: "Forecast installation moved from 17 Jun to 08 Jul.",
  budgetMovement: "Current estimate is up by 84k in fictional demo values.",
  qualitySiteConfirmation: "Quality check is drafted but not accepted by the site owner.",
  supplierSiteDependencies: "Supplier drawing and production shutdown both remain open.",
  escalationNeeded: "Sponsor decision needed if the revised order must be released this week.",
  proofUsed: ["Supplier drawing v7 email", "Draft order pack", "Shutdown request note"],
  suggestedUpdate:
    "Packaging Line Retrofit remains blocked this week. The PM is waiting on supplier drawing confirmation and production shutdown acceptance before the revised order can be treated as ready.",
  caveats: [
    "Do not report the order as ready.",
    "Do not report the install date as firm.",
    "Budget movement still needs sponsor review."
  ],
  status: "blocked"
};

const orionGantt: CapxPmFeDemoGanttItem[] = [
  ganttItem(
    "gantt-1",
    "Setup",
    "Kickoff and takeover",
    "PM Lead",
    "01 May - 03 May",
    "01 May - 03 May",
    1,
    2,
    1,
    2,
    0,
    "None",
    false,
    false,
    "Complete",
    "on-track"
  ),
  ganttItem(
    "gantt-2",
    "Documents",
    "Supplier drawing confirmation",
    "Supplier A",
    "06 May - 10 May",
    "06 May - 24 May",
    3,
    3,
    3,
    8,
    14,
    "Kickoff",
    true,
    true,
    "Drawing v7 decision is missing",
    "waiting-supplier"
  ),
  ganttItem(
    "gantt-3",
    "Budget",
    "Revised order approval",
    "Finance Owner",
    "13 May - 17 May",
    "27 May - 31 May",
    6,
    3,
    10,
    3,
    14,
    "Supplier drawing confirmation",
    true,
    true,
    "Approval waits for drawing decision",
    "needs-approval"
  ),
  ganttItem(
    "gantt-4",
    "Site",
    "Production shutdown window",
    "Production Lead",
    "20 May - 24 May",
    "03 Jun - 07 Jun",
    9,
    3,
    12,
    3,
    14,
    "Revised order approval",
    true,
    true,
    "Production has not accepted the window",
    "waiting-site"
  ),
  ganttItem(
    "gantt-5",
    "Install",
    "Line installation",
    "Site Engineering",
    "17 Jun - 21 Jun",
    "08 Jul - 12 Jul",
    18,
    4,
    23,
    4,
    21,
    "Shutdown window",
    true,
    true,
    "Install date cannot firm until site accepts",
    "blocked"
  ),
  ganttItem(
    "gantt-6",
    "Closeout",
    "Quality acceptance and PM report",
    "Quality Lead",
    "24 Jun - 28 Jun",
    "15 Jul - 19 Jul",
    22,
    3,
    27,
    3,
    21,
    "Line installation",
    false,
    true,
    "Quality checklist not accepted",
    "watch"
  )
];

const orionProject: CapxPmFeDemoProject = {
  id: "P-104",
  name: "Packaging Line Retrofit",
  site: "North Demo Site",
  area: "Line 4",
  pm: "PM Lead",
  sponsor: "Operations Sponsor",
  stage: "Procurement",
  health: "blocked",
  schedule: "+3 weeks",
  budget: "+84k watch",
  quality: "Acceptance open",
  waitingOn: "Supplier A, Production Lead",
  docs: "3 missing",
  escalation: "Sponsor decision",
  lastUpdate: "09 Jun",
  attentionRank: 1,
  activeStep: "documents",
  nextAction: action(
    "Confirm whether drawing v7 replaces v6",
    "Supplier A",
    "Today",
    "PO approval and install date are blocked",
    "Supplier drawing v7 confirmation",
    "PM cannot send a credible weekly report until this is resolved.",
    "waiting-supplier"
  ),
  blockers: [
    blocker(
      "orion-blocker-1",
      "Supplier drawing version decision",
      "Supplier A",
      "Today",
      "Supplier A",
      "Drawing v7 confirmation",
      "Blocks revised order approval.",
      "waiting-supplier"
    ),
    blocker(
      "orion-blocker-2",
      "Production shutdown window",
      "Production Lead",
      "This week",
      "Production Lead",
      "Accepted shutdown window",
      "Blocks installation date confidence.",
      "waiting-site"
    ),
    blocker(
      "orion-blocker-3",
      "Quality acceptance checklist",
      "Quality Lead",
      "Friday",
      "Quality Lead",
      "Accepted checklist",
      "Blocks report readiness.",
      "proof-missing"
    )
  ],
  setupItems: [
    documentRecord(
      "setup-1",
      "Project owner assignment",
      "Setup",
      "01 May",
      "PM ownership",
      "on-track",
      "PM Lead",
      "Keep assigned",
      "PM owner and sponsor are clear."
    ),
    documentRecord(
      "setup-2",
      "Sponsor decision path",
      "Setup",
      "03 May",
      "Escalation",
      "needs-approval",
      "Operations Sponsor",
      "Confirm delegate for budget decision",
      "Budget escalation path is not fully confirmed."
    ),
    documentRecord(
      "setup-3",
      "Document folder access",
      "Setup",
      "06 May",
      "File review",
      "proof-missing",
      "PM Lead",
      "Add site quality owner",
      "Quality owner cannot review the latest checklist."
    )
  ],
  documents: [
    documentRecord(
      "doc-1",
      "Supplier drawing v7",
      "Drawing",
      "07 Jun",
      "Order decision",
      "waiting-supplier",
      "Supplier A",
      "Confirm whether it replaces v6",
      "The latest drawing conflicts with the order draft."
    ),
    documentRecord(
      "doc-2",
      "Draft order pack",
      "Order",
      "05 Jun",
      "PO approval",
      "needs-approval",
      "Finance Owner",
      "Hold until drawing decision",
      "Order amount may change after drawing confirmation."
    ),
    documentRecord(
      "doc-3",
      "Shutdown request note",
      "Site note",
      "06 Jun",
      "Install schedule",
      "waiting-site",
      "Production Lead",
      "Accept or propose a window",
      "No accepted shutdown window is on file."
    ),
    documentRecord(
      "doc-4",
      "Quality acceptance checklist",
      "Checklist",
      "04 Jun",
      "Project closeout",
      "proof-missing",
      "Quality Lead",
      "Confirm required checks",
      "Checklist is drafted but not accepted."
    )
  ],
  milestones: [
    milestone(
      "mile-1",
      "Drawing decision",
      "10 May",
      "24 May",
      14,
      "Supplier A",
      "Supplier changed drawing version",
      "Low",
      "waiting-supplier",
      true
    ),
    milestone(
      "mile-2",
      "Order approval",
      "17 May",
      "31 May",
      14,
      "Finance Owner",
      "Approval waits for drawing decision",
      "Medium",
      "needs-approval",
      true
    ),
    milestone(
      "mile-3",
      "Production shutdown",
      "24 May",
      "07 Jun",
      14,
      "Production Lead",
      "Production window not accepted",
      "Low",
      "waiting-site",
      true
    ),
    milestone(
      "mile-4",
      "Installation",
      "21 Jun",
      "12 Jul",
      21,
      "Site Engineering",
      "Order and shutdown both moved",
      "Low",
      "blocked",
      true
    )
  ],
  budgetItems: [
    budgetItem(
      "budget-1",
      "Base conveyor retrofit",
      "900k",
      "900k",
      "0",
      "Approved budget note",
      "No",
      "Finance Owner",
      "Done",
      "on-track"
    ),
    budgetItem(
      "budget-2",
      "Controls package revision",
      "120k",
      "204k",
      "+84k",
      "Supplier quote revision",
      "Yes",
      "Operations Sponsor",
      "This week",
      "needs-approval"
    ),
    budgetItem(
      "budget-3",
      "Install support shift",
      "45k",
      "TBD",
      "Open",
      "Shutdown request note",
      "Maybe",
      "Production Lead",
      "Friday",
      "waiting-site"
    )
  ],
  supplierQuestions: [
    supplierQuestion(
      "supplier-1",
      "Does drawing v7 replace drawing v6 for the current order?",
      "Supplier A",
      "Today",
      "Order approval",
      "Supplier drawing v7 confirmation",
      "Supplier A must reply with a clear replacement decision.",
      "waiting-supplier"
    ),
    supplierQuestion(
      "supplier-2",
      "Can the revised controls ship before the new shutdown window?",
      "Supplier A",
      "Friday",
      "Install confidence",
      "Delivery confirmation",
      "PM to chase delivery date after drawing decision.",
      "watch"
    ),
    supplierQuestion(
      "supplier-3",
      "Will added controls change quality acceptance checks?",
      "Supplier A",
      "Friday",
      "Quality checklist",
      "Supplier quality note",
      "Quality Lead needs supplier note before accepting checklist.",
      "proof-missing"
    )
  ],
  siteHandoffs: [
    siteHandoff(
      "site-1",
      "Shutdown window",
      "Production Lead",
      "07 Jun",
      "Requested",
      "Not accepted",
      "Installation",
      "Accepted shutdown window",
      "Production Lead to accept or propose a window.",
      "waiting-site"
    ),
    siteHandoff(
      "site-2",
      "Quality acceptance checklist",
      "Quality Lead",
      "14 Jun",
      "Drafted",
      "Not accepted",
      "Project report",
      "Accepted checklist",
      "Quality Lead to confirm required checks.",
      "proof-missing"
    ),
    siteHandoff(
      "site-3",
      "Maintenance training slot",
      "Maintenance Lead",
      "21 Jun",
      "Proposed",
      "Accepted",
      "Closeout",
      "Training invite",
      "Keep training slot aligned to install forecast.",
      "watch"
    )
  ],
  report: orionReport,
  gantt: orionGantt
};

function cloneLightProject(
  id: string,
  name: string,
  site: string,
  area: string,
  pm: string,
  stage: string,
  health: CapxPmFeDemoStatus,
  activeStep: CapxPmFeDemoStepId,
  attentionRank: number,
  nextActionTitle: string,
  waitingOn: string
): CapxPmFeDemoProject {
  const statusText = health === "ready-share" ? "Ready to share" : health === "on-track" ? "On track" : "Needs PM attention";

  return {
    ...orionProject,
    id,
    name,
    site,
    area,
    pm,
    sponsor: `${pm} sponsor`,
    stage,
    health,
    schedule: health === "on-track" || health === "ready-share" ? "On plan" : "+1 week",
    budget: health === "needs-approval" ? "Approval open" : "No new change",
    quality: health === "waiting-site" ? "Site acceptance open" : "Tracking",
    waitingOn,
    docs: health === "proof-missing" ? "2 missing" : "Reviewed",
    escalation: health === "blocked" || health === "needs-approval" ? "May need sponsor" : "None",
    lastUpdate: `${Math.max(1, 10 - attentionRank)} Jun`,
    attentionRank,
    activeStep,
    nextAction: {
      ...orionProject.nextAction,
      title: nextActionTitle,
      owner: waitingOn,
      status: health,
      blocker: statusText
    },
    blockers: orionProject.blockers.map((item, index) => ({
      ...item,
      id: `${id}-blocker-${index + 1}`,
      title: index === 0 ? nextActionTitle : item.title,
      owner: waitingOn,
      waitingOn,
      status: index === 0 ? health : item.status
    })),
    report: {
      ...orionProject.report,
      readiness: health === "ready-share" ? "Ready to share" : "Needs PM review",
      status: health,
      currentStatus: `${name} is in ${stage}. ${statusText}.`,
      suggestedUpdate: `${name} is in ${stage}. PM next action: ${nextActionTitle}.`
    },
    gantt: orionProject.gantt.map((item) => ({
      ...item,
      id: `${id}-${item.id}`,
      owner: item.criticalPath ? waitingOn : item.owner,
      status: item.criticalPath ? health : item.status
    }))
  };
}

export const capxPmFeDemoState: CapxPmFeDemoState = {
  generatedAt: "09 Jun 2026 11:48",
  steps: capxPmFeDemoSteps,
  projects: [
    orionProject,
    cloneLightProject(
      "P-087",
      "Biologics Fill Line",
      "East Demo Site",
      "Cleanroom B",
      "PM North",
      "Installation",
      "waiting-site",
      "site-handoffs",
      2,
      "Confirm production access window",
      "Production Lead"
    ),
    cloneLightProject(
      "P-102",
      "Cleanroom Airflow Upgrade",
      "South Demo Site",
      "Air Handling",
      "PM South",
      "Design",
      "proof-missing",
      "documents",
      3,
      "Upload revised airflow test proof",
      "Quality Lead"
    ),
    cloneLightProject(
      "P-118",
      "Compressor Tie-In",
      "West Demo Site",
      "Utilities",
      "PM West",
      "Budget review",
      "needs-approval",
      "budget-orders",
      4,
      "Review quote increase with sponsor",
      "Finance Owner"
    ),
    cloneLightProject(
      "P-126",
      "Warehouse Safety Refresh",
      "Central Demo Site",
      "Warehouse",
      "PM Central",
      "Report prep",
      "ready-share",
      "project-report",
      8,
      "Share weekly PM update",
      "PM Central"
    ),
    cloneLightProject(
      "P-131",
      "Controls Spare Kit",
      "North Demo Site",
      "Controls",
      "PM Controls",
      "Setup",
      "on-track",
      "project-setup",
      10,
      "Confirm kickoff notes are filed",
      "PM Controls"
    ),
    cloneLightProject(
      "P-144",
      "Chiller Valve Replacement",
      "West Demo Site",
      "Utilities",
      "PM Utility",
      "Supplier review",
      "waiting-supplier",
      "supplier-questions",
      5,
      "Get valve lead-time answer",
      "Supplier B"
    ),
    cloneLightProject(
      "P-155",
      "Labeler Camera Upgrade",
      "South Demo Site",
      "Packaging",
      "PM Vision",
      "Timeline review",
      "watch",
      "timeline",
      6,
      "Confirm camera install forecast",
      "Site Engineering"
    ),
    cloneLightProject(
      "P-162",
      "Mixer Platform Guarding",
      "East Demo Site",
      "Process",
      "PM Safety",
      "Site readiness",
      "waiting-site",
      "site-handoffs",
      7,
      "Confirm maintenance handoff",
      "Maintenance Lead"
    ),
    cloneLightProject(
      "P-177",
      "Tablet Room Humidity Fix",
      "Central Demo Site",
      "HVAC",
      "PM Facility",
      "Documents",
      "proof-missing",
      "documents",
      9,
      "Attach humidity trend proof",
      "Site Engineering"
    )
  ]
};
