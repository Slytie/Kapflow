import { capxStatusRank } from "./capxCeoCockpitStatus";
import { capxDemoState } from "./capxCeoCockpitData";
import type {
  CapxActionLane,
  CapxDemoState,
  CapxExecutiveAction,
  CapxPortfolioRisk,
  CapxProjectDetail,
  CapxProjectOverview,
  CapxTrendPoint
} from "./capxCeoCockpitTypes";

export const actionLaneLabels: Record<CapxActionLane, string> = {
  due_today: "Due Today",
  this_week: "This Week",
  next_two_weeks: "Next 2 Weeks",
  later: "Later"
};

const actionLaneOrder: CapxActionLane[] = ["due_today", "this_week", "next_two_weeks", "later"];

export interface PortfolioMetric {
  label: string;
  value: string;
  tone: "critical" | "watch" | "verified" | "neutral";
}

export interface CapxOverviewViewModel {
  generatedAt: string;
  portfolioMetrics: PortfolioMetric[];
  actionsByLane: Array<{
    lane: CapxActionLane;
    label: string;
    actions: CapxExecutiveAction[];
  }>;
  projects: CapxProjectOverview[];
  topProjects: CapxProjectOverview[];
  dueTodayActions: CapxExecutiveAction[];
}

export function buildCapxOverviewViewModel(state: CapxDemoState = capxDemoState): CapxOverviewViewModel {
  const projects = [...state.projects].sort(
    (left, right) =>
      right.exposureAtRiskMillions - left.exposureAtRiskMillions ||
      capxStatusRank(left.status) - capxStatusRank(right.status)
  );

  return {
    generatedAt: state.generatedAt,
    portfolioMetrics: buildPortfolioMetrics(state.portfolioRisk),
    actionsByLane: actionLaneOrder.map((lane) => ({
      lane,
      label: actionLaneLabels[lane],
      actions: state.actions
        .filter((action) => action.lane === lane)
        .sort((left, right) => capxStatusRank(left.status) - capxStatusRank(right.status))
    })),
    projects,
    topProjects: projects.slice(0, 5),
    dueTodayActions: state.actions.filter((action) => action.lane === "due_today")
  };
}

export function findCapxProjectDetail(
  projectId: string | undefined,
  state: CapxDemoState = capxDemoState
): CapxProjectDetail | undefined {
  if (!projectId) {
    return undefined;
  }
  return state.projectDetails[projectId];
}

export function formatMoneyMillions(value: number): string {
  return `$${value.toFixed(1)}M`;
}

export function formatMoneyThousands(value: number): string {
  return `$${Math.round(value)}K`;
}

export function formatPercent(value: number): string {
  return `${value}%`;
}

export function formatSignedPercent(value: number): string {
  const sign = value > 0 ? "+" : "";
  return `${sign}${value.toFixed(1)}%`;
}

export function trendPolyline(points: number[], width = 84, height = 28): string {
  if (points.length === 0) {
    return "";
  }

  const min = Math.min(...points);
  const max = Math.max(...points);
  const range = max - min || 1;

  return points
    .map((point, index) => {
      const x = (index / Math.max(points.length - 1, 1)) * width;
      const y = height - ((point - min) / range) * height;
      return `${x.toFixed(1)},${y.toFixed(1)}`;
    })
    .join(" ");
}

export function trendAreaPolyline(points: CapxTrendPoint[], width = 280, height = 112): string {
  return trendPolyline(
    points.map((point) => point.value),
    width,
    height
  );
}

function buildPortfolioMetrics(risk: CapxPortfolioRisk): PortfolioMetric[] {
  return [
    {
      label: "Exposure at risk",
      value: formatMoneyMillions(risk.exposureAtRiskMillions),
      tone: "critical"
    },
    {
      label: "Opp. cost / week",
      value: `$${risk.opportunityCostPerWeekMillions.toFixed(2)}M`,
      tone: "watch"
    },
    {
      label: "Projects at risk",
      value: `${risk.projectsAtRisk} / ${risk.totalProjects}`,
      tone: "critical"
    },
    {
      label: "Overdue approvals",
      value: String(risk.overdueApprovals),
      tone: "critical"
    },
    {
      label: "Stale evidence",
      value: String(risk.staleEvidence),
      tone: "watch"
    },
    {
      label: "Board drift >10K",
      value: String(risk.boardDriftOverTenK),
      tone: "verified"
    },
    {
      label: "Supplier assumptions high risk",
      value: String(risk.supplierAssumptionsHighRisk),
      tone: "watch"
    },
    {
      label: "Interface issues open",
      value: String(risk.interfaceIssuesOpen),
      tone: "watch"
    },
    {
      label: "Forecast confidence",
      value: `${risk.forecastConfidencePercent}%`,
      tone: "neutral"
    }
  ];
}
