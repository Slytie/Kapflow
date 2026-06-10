import { capxPmFeDemoState } from "./capxPmFeDemoMockData";
import { getCapxPmFeDemoStatusRank } from "./capxPmFeDemoStatus";
import type {
  CapxPmFeDemoProject,
  CapxPmFeDemoState,
  CapxPmFeDemoStep,
  CapxPmFeDemoStepId
} from "./capxPmFeDemoTypes";

export interface CapxPmFeDemoProjectsViewModel {
  generatedAt: string;
  projects: CapxPmFeDemoProject[];
  totals: {
    projects: number;
    blocked: number;
    waiting: number;
    ready: number;
    dueToday: number;
  };
}

export interface CapxPmFeDemoWorkspaceViewModel {
  generatedAt: string;
  project: CapxPmFeDemoProject;
  steps: CapxPmFeDemoStep[];
  activeStep: CapxPmFeDemoStep;
}

export function buildCapxPmFeDemoProjectHref(projectId: string): string {
  return `/demo/capx/pm/projects/${projectId}`;
}

export function buildCapxPmFeDemoStepHref(projectId: string, stepId: CapxPmFeDemoStepId): string {
  return `${buildCapxPmFeDemoProjectHref(projectId)}/steps/${stepId}`;
}

export function buildCapxPmFeDemoGanttHref(projectId: string): string {
  return `${buildCapxPmFeDemoProjectHref(projectId)}/gantt`;
}

export function getCapxPmFeDemoProject(
  projectId: string | undefined,
  state: CapxPmFeDemoState = capxPmFeDemoState
): CapxPmFeDemoProject | undefined {
  if (!projectId) {
    return undefined;
  }
  return state.projects.find((project) => project.id === projectId);
}

export function isCapxPmFeDemoStepId(stepId: string | undefined): stepId is CapxPmFeDemoStepId {
  return capxPmFeDemoState.steps.some((step) => step.id === stepId);
}

export function getCapxPmFeDemoStep(stepId: CapxPmFeDemoStepId): CapxPmFeDemoStep {
  const step = capxPmFeDemoState.steps.find((item) => item.id === stepId);
  if (!step) {
    throw new Error(`Unknown PM FE demo step ${stepId}`);
  }
  return step;
}

export function buildCapxPmFeDemoProjectsViewModel(
  state: CapxPmFeDemoState = capxPmFeDemoState
): CapxPmFeDemoProjectsViewModel {
  const projects = [...state.projects].sort(
    (left, right) =>
      left.attentionRank - right.attentionRank ||
      getCapxPmFeDemoStatusRank(left.health) - getCapxPmFeDemoStatusRank(right.health)
  );

  return {
    generatedAt: state.generatedAt,
    projects,
    totals: {
      projects: state.projects.length,
      blocked: state.projects.filter((project) => project.health === "blocked").length,
      waiting: state.projects.filter(
        (project) => project.health === "waiting-site" || project.health === "waiting-supplier"
      ).length,
      ready: state.projects.filter((project) => project.health === "ready-share").length,
      dueToday: state.projects.filter((project) => project.nextAction.due === "Today").length
    }
  };
}

export function buildCapxPmFeDemoWorkspaceViewModel(
  project: CapxPmFeDemoProject,
  stepId: CapxPmFeDemoStepId = project.activeStep,
  state: CapxPmFeDemoState = capxPmFeDemoState
): CapxPmFeDemoWorkspaceViewModel {
  const activeStep = state.steps.find((step) => step.id === stepId);
  if (!activeStep) {
    throw new Error(`Unknown PM FE demo step ${stepId}`);
  }
  return {
    generatedAt: state.generatedAt,
    project,
    steps: state.steps,
    activeStep
  };
}

export function getCapxPmFeDemoRowsForStep(project: CapxPmFeDemoProject, stepId: CapxPmFeDemoStepId) {
  switch (stepId) {
    case "project-setup":
      return project.setupItems;
    case "documents":
      return project.documents;
    case "timeline":
      return project.milestones;
    case "budget-orders":
      return project.budgetItems;
    case "supplier-questions":
      return project.supplierQuestions;
    case "site-handoffs":
      return project.siteHandoffs;
    case "project-report":
      return project.report.proofUsed;
  }
}
