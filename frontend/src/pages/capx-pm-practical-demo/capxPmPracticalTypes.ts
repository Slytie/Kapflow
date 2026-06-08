export type CapxPmPracticalStatus = "blocked" | "needs-work" | "ready-review" | "done" | "not-started";

export type CapxPmPracticalStepSlug =
  | "setup"
  | "documents"
  | "timeline"
  | "budget-orders"
  | "supplier-questions"
  | "site-handoffs"
  | "project-report";

export type CapxPmPracticalFilter = "all" | "missing" | "overdue" | "changed" | "blocked" | "ready-review";

export interface CapxPmPracticalStep {
  number: number;
  slug: CapxPmPracticalStepSlug;
  label: string;
  question: string;
  traceId: string;
}

export interface CapxPmPracticalTask {
  id: string;
  title: string;
  owner: string;
  due: string;
  supportingFile: string;
  consequence: string;
  status: CapxPmPracticalStatus;
  tags: CapxPmPracticalFilter[];
}

export interface CapxPmPracticalRecord {
  id: string;
  item: string;
  owner: string;
  due: string;
  status: CapxPmPracticalStatus;
  supportingFile: string;
  note: string;
}

export interface CapxPmPracticalChecklistItem {
  label: string;
  owner: string;
  status: CapxPmPracticalStatus;
}

export interface CapxPmPracticalCard {
  title: string;
  value: string;
  body: string;
  status: CapxPmPracticalStatus;
}

export interface CapxPmPracticalStepState {
  slug: CapxPmPracticalStepSlug;
  status: CapxPmPracticalStatus;
  headline: string;
  summary: string;
  primaryAction: CapxPmPracticalTask;
  checklistTitle: string;
  checklist: CapxPmPracticalChecklistItem[];
  cardsTitle: string;
  cards: CapxPmPracticalCard[];
  tableTitle: string;
  records: CapxPmPracticalRecord[];
  supportingFiles: string[];
  reportNote: string;
}

export interface CapxPmPracticalProject {
  id: string;
  name: string;
  siteArea: string;
  pm: string;
  sponsor: string;
  phase: string;
  needsAttention: string;
  blockers: number;
  severeBlocker: string;
  tasksDue: number;
  missingDocuments: number;
  budgetOrders: string;
  schedule: string;
  supplierQuestions: string;
  siteHandoffs: string;
  reportStatus: string;
  lastUpdate: string;
  topBlocker: string;
  lastMaterialChange: string;
  activeStep: CapxPmPracticalStepSlug;
  status: CapxPmPracticalStatus;
  filters: CapxPmPracticalFilter[];
  steps: CapxPmPracticalStepState[];
}

export interface CapxPmPracticalDemoState {
  generatedAt: string;
  projects: CapxPmPracticalProject[];
  steps: CapxPmPracticalStep[];
}
