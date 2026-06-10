export type CapxPmFeDemoStatus =
  | "blocked"
  | "watch"
  | "on-track"
  | "needs-approval"
  | "waiting-supplier"
  | "waiting-site"
  | "proof-missing"
  | "ready-share";

export type CapxPmFeDemoStepId =
  | "project-setup"
  | "documents"
  | "timeline"
  | "budget-orders"
  | "supplier-questions"
  | "site-handoffs"
  | "project-report";

export interface CapxPmFeDemoStep {
  id: CapxPmFeDemoStepId;
  number: number;
  label: string;
  shortLabel: string;
  question: string;
}

export interface CapxPmFeDemoAction {
  title: string;
  owner: string;
  due: string;
  blocker: string;
  proofNeeded: string;
  consequence: string;
  status: CapxPmFeDemoStatus;
}

export interface CapxPmFeDemoBlocker {
  id: string;
  title: string;
  owner: string;
  due: string;
  waitingOn: string;
  proofNeeded: string;
  impact: string;
  status: CapxPmFeDemoStatus;
}

export interface CapxPmFeDemoDocument {
  id: string;
  name: string;
  type: string;
  versionDate: string;
  usedFor: string;
  status: CapxPmFeDemoStatus;
  owner: string;
  action: string;
  detail: string;
}

export interface CapxPmFeDemoMilestone {
  id: string;
  name: string;
  baselineDate: string;
  forecastDate: string;
  deltaDays: number;
  owner: string;
  reason: string;
  confidence: string;
  status: CapxPmFeDemoStatus;
  changedSinceLastReport: boolean;
}

export interface CapxPmFeDemoBudgetItem {
  id: string;
  item: string;
  approvedAmount: string;
  currentAmount: string;
  delta: string;
  document: string;
  approvalNeeded: string;
  owner: string;
  due: string;
  status: CapxPmFeDemoStatus;
}

export interface CapxPmFeDemoSupplierQuestion {
  id: string;
  question: string;
  supplier: string;
  due: string;
  blocks: string;
  proof: string;
  nextAction: string;
  status: CapxPmFeDemoStatus;
}

export interface CapxPmFeDemoSiteHandoff {
  id: string;
  dependency: string;
  neededFrom: string;
  requiredBy: string;
  provided: string;
  acceptedBy: string;
  blocks: string;
  proof: string;
  nextAction: string;
  status: CapxPmFeDemoStatus;
}

export interface CapxPmFeDemoReport {
  readiness: string;
  currentStatus: string;
  changesThisWeek: string[];
  topBlockers: string[];
  scheduleMovement: string;
  budgetMovement: string;
  qualitySiteConfirmation: string;
  supplierSiteDependencies: string;
  escalationNeeded: string;
  proofUsed: string[];
  suggestedUpdate: string;
  caveats: string[];
  status: CapxPmFeDemoStatus;
}

export interface CapxPmFeDemoGanttItem {
  id: string;
  workstream: string;
  task: string;
  owner: string;
  baselineLabel: string;
  forecastLabel: string;
  baselineStart: number;
  baselineSpan: number;
  forecastStart: number;
  forecastSpan: number;
  deltaDays: number;
  dependsOn: string;
  criticalPath: boolean;
  changedSinceLastReport: boolean;
  blocker: string;
  status: CapxPmFeDemoStatus;
}

export interface CapxPmFeDemoProject {
  id: string;
  name: string;
  site: string;
  area: string;
  pm: string;
  sponsor: string;
  stage: string;
  health: CapxPmFeDemoStatus;
  schedule: string;
  budget: string;
  quality: string;
  waitingOn: string;
  docs: string;
  escalation: string;
  lastUpdate: string;
  attentionRank: number;
  activeStep: CapxPmFeDemoStepId;
  nextAction: CapxPmFeDemoAction;
  blockers: CapxPmFeDemoBlocker[];
  setupItems: CapxPmFeDemoDocument[];
  documents: CapxPmFeDemoDocument[];
  milestones: CapxPmFeDemoMilestone[];
  budgetItems: CapxPmFeDemoBudgetItem[];
  supplierQuestions: CapxPmFeDemoSupplierQuestion[];
  siteHandoffs: CapxPmFeDemoSiteHandoff[];
  report: CapxPmFeDemoReport;
  gantt: CapxPmFeDemoGanttItem[];
}

export interface CapxPmFeDemoState {
  generatedAt: string;
  projects: CapxPmFeDemoProject[];
  steps: CapxPmFeDemoStep[];
}
