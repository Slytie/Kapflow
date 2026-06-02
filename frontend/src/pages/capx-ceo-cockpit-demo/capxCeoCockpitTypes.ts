export type CapxStatus = "critical" | "watch" | "verified" | "neutral";

export type CapxActionLane = "due_today" | "this_week" | "next_two_weeks" | "later";

export interface CapxExecutiveAction {
  id: string;
  title: string;
  projectId: string;
  projectCode: string;
  lane: CapxActionLane;
  status: CapxStatus;
  owner: string;
}

export interface CapxPortfolioRisk {
  exposureAtRiskMillions: number;
  opportunityCostPerWeekMillions: number;
  projectsAtRisk: number;
  totalProjects: number;
  overdueApprovals: number;
  staleEvidence: number;
  boardDriftOverTenK: number;
  supplierAssumptionsHighRisk: number;
  interfaceIssuesOpen: number;
  forecastConfidencePercent: number;
}

export interface CapxProjectOverview {
  id: string;
  code: string;
  name: string;
  subtitle: string;
  projectManager: string;
  stage: string;
  status: CapxStatus;
  riskMode: string;
  exposureAtRiskMillions: number;
  opportunityCostPerWeekThousands: number;
  probableDelayPercent: number;
  budgetVariancePercent: number;
  scheduleVariancePercent: number;
  evidenceFreshnessDays: number;
  boardImpact: "High" | "Medium" | "Low";
  trend: number[];
  lastUpdate: string;
}

export interface CapxOwner {
  role: string;
  name: string;
}

export interface CapxMilestone {
  label: string;
  baseline: string;
  forecast: string;
  variance: string;
  status: CapxStatus;
}

export interface CapxRisk {
  label: string;
  severity: CapxStatus;
}

export interface CapxTrendPoint {
  label: string;
  value: number;
}

export interface CapxFlag {
  type: string;
  description: string;
  severity: CapxStatus;
  raised: string;
  owner: string;
  state: string;
}

export interface CapxEvidenceSection {
  title: string;
  items: string[];
}

export interface CapxProjectDetail extends CapxProjectOverview {
  criticality: string;
  delayExposurePerWeekThousands: number;
  probableDelayLabel: string;
  worstPlausibleExposureMillions: number;
  whyStatus: string;
  ceoNextAction: string;
  owners: CapxOwner[];
  currentStageIndex: number;
  stageLabels: string[];
  milestones: CapxMilestone[];
  topRisks: CapxRisk[];
  delayImpactTrend: CapxTrendPoint[];
  budgetTrend: CapxTrendPoint[];
  latestUpdateBullets: string[];
  flags: CapxFlag[];
  evidenceSections: CapxEvidenceSection[];
}

export interface CapxDemoState {
  generatedAt: string;
  portfolioRisk: CapxPortfolioRisk;
  actions: CapxExecutiveAction[];
  projects: CapxProjectOverview[];
  projectDetails: Record<string, CapxProjectDetail>;
}
