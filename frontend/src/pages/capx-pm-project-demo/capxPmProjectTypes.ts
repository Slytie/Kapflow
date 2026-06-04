export type CapxPmStatus = "critical" | "watch" | "verified" | "neutral";

export type CapxPmStepSlug =
  | "intake"
  | "corpus"
  | "lifecycle"
  | "commitment"
  | "assumptions"
  | "interfaces"
  | "snapshot";

export type CapxPmEvidenceFreshness = "fresh" | "aging" | "stale" | "conflicting";

export type CapxPmSnapshotReadiness = "blocked" | "draftable" | "review-ready" | "promoted";

export interface CapxPmWorkflowStep {
  number: number;
  slug: CapxPmStepSlug;
  workflowId: string;
  title: string;
  shortTitle: string;
  pmQuestion: string;
}

export interface CapxPmTask {
  id: string;
  title: string;
  owner: string;
  due: string;
  evidenceBasis: string;
  consequence: string;
  status: CapxPmStatus;
}

export interface CapxPmFlag {
  id: string;
  label: string;
  basis: string;
  status: CapxPmStatus;
}

export interface CapxPmEvidencePacket {
  id: string;
  title: string;
  freshness: CapxPmEvidenceFreshness;
  sourceCount: number;
  unresolvedRefs: number;
}

export interface CapxPmRegisterRow {
  id: string;
  primary: string;
  secondary: string;
  owner: string;
  basis: string;
  status: CapxPmStatus;
}

export interface CapxPmHandoffManifest {
  target: string;
  requiredBasis: string;
  nextCheck: string;
  status: CapxPmStatus;
}

export interface CapxPmDetailMetric {
  label: string;
  value: string;
  status: CapxPmStatus;
}

export interface CapxPmDetailCard {
  title: string;
  value: string;
  body: string;
  status: CapxPmStatus;
}

export interface CapxPmDetailMatrixRow {
  label: string;
  current: string;
  owner: string;
  basis: string;
  status: CapxPmStatus;
}

export interface CapxPmDetailTimelineItem {
  label: string;
  marker: string;
  body: string;
  status: CapxPmStatus;
}

export interface CapxPmStepDetail {
  metrics: CapxPmDetailMetric[];
  cardsTitle: string;
  cards: CapxPmDetailCard[];
  matrixTitle: string;
  matrixRows: CapxPmDetailMatrixRow[];
  timelineTitle: string;
  timelineItems: CapxPmDetailTimelineItem[];
  mockActionLabel: string;
}

export interface CapxPmStepState {
  slug: CapxPmStepSlug;
  status: CapxPmStatus;
  summary: string;
  registerTitle: string;
  registerRows: CapxPmRegisterRow[];
  tasks: CapxPmTask[];
  evidencePackets: CapxPmEvidencePacket[];
  flags: CapxPmFlag[];
  handoff: CapxPmHandoffManifest;
  detail: CapxPmStepDetail;
}

export interface CapxPmProject {
  id: string;
  code: string;
  name: string;
  site: string;
  projectType: string;
  pmOwner: string;
  ownerRole: string;
  dominantStage: string;
  activeStep: CapxPmStepSlug;
  status: CapxPmStatus;
  blockerSummary: string;
  openBlockers: number;
  openTasks: number;
  evidenceFreshness: CapxPmEvidenceFreshness;
  snapshotReadiness: CapxPmSnapshotReadiness;
  lastMaterialChange: string;
  steps: CapxPmStepState[];
}

export interface CapxPmDemoState {
  generatedAt: string;
  projects: CapxPmProject[];
  workflowSteps: CapxPmWorkflowStep[];
}
