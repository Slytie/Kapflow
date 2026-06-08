import { capxPmPracticalDemoState } from "./capxPmPracticalMockData";
import { capxPmPracticalStatusRank } from "./capxPmPracticalStatus";
import type {
  CapxPmPracticalDemoState,
  CapxPmPracticalFilter,
  CapxPmPracticalProject,
  CapxPmPracticalStep,
  CapxPmPracticalStepSlug
} from "./capxPmPracticalTypes";

export const capxPmPracticalFilters: Array<{ id: CapxPmPracticalFilter; label: string }> = [
  { id: "all", label: "All" },
  { id: "blocked", label: "Blocked" },
  { id: "missing", label: "Missing" },
  { id: "overdue", label: "Overdue" },
  { id: "changed", label: "Changed" },
  { id: "ready-review", label: "Ready for review" }
];

export interface CapxPmPracticalProjectListViewModel {
  generatedAt: string;
  filter: CapxPmPracticalFilter;
  projects: CapxPmPracticalProject[];
  totals: {
    projects: number;
    blocked: number;
    dueThisWeek: number;
    missingDocuments: number;
    readyForReview: number;
  };
}

export interface CapxPmPracticalWorkspaceViewModel {
  generatedAt: string;
  project: CapxPmPracticalProject;
  steps: CapxPmPracticalStep[];
  selectedStep: CapxPmPracticalStep;
  selectedStepState: CapxPmPracticalProject["steps"][number];
  urgentTask: CapxPmPracticalProject["steps"][number]["primaryAction"];
}

export function buildCapxPmPracticalProjectHref(project: CapxPmPracticalProject): string {
  return `/demo/capx/pm/projects/${project.id}`;
}

export function buildCapxPmPracticalStepHref(project: CapxPmPracticalProject, stepSlug: CapxPmPracticalStepSlug): string {
  return `${buildCapxPmPracticalProjectHref(project)}/steps/${stepSlug}`;
}

export function getCapxPmPracticalProject(
  projectId: string | undefined,
  state: CapxPmPracticalDemoState = capxPmPracticalDemoState
): CapxPmPracticalProject | undefined {
  if (!projectId) {
    return undefined;
  }
  return state.projects.find((project) => project.id === projectId);
}

export function getCapxPmPracticalDefaultStep(project: CapxPmPracticalProject): CapxPmPracticalStepSlug {
  return project.activeStep;
}

export function isCapxPmPracticalStepSlug(stepId: string | undefined): stepId is CapxPmPracticalStepSlug {
  return capxPmPracticalDemoState.steps.some((step) => step.slug === stepId);
}

export function getCapxPmPracticalStepState(
  project: CapxPmPracticalProject,
  stepSlug: CapxPmPracticalStepSlug
): CapxPmPracticalProject["steps"][number] | undefined {
  return project.steps.find((step) => step.slug === stepSlug);
}

export function buildCapxPmPracticalProjectListViewModel(
  filter: CapxPmPracticalFilter = "all",
  state: CapxPmPracticalDemoState = capxPmPracticalDemoState
): CapxPmPracticalProjectListViewModel {
  const sortedProjects = [...state.projects].sort(
    (left, right) =>
      capxPmPracticalStatusRank(left.status) - capxPmPracticalStatusRank(right.status) ||
      right.blockers - left.blockers ||
      right.tasksDue - left.tasksDue
  );
  const projects = filter === "all" ? sortedProjects : sortedProjects.filter((project) => project.filters.includes(filter));

  return {
    generatedAt: state.generatedAt,
    filter,
    projects,
    totals: {
      projects: state.projects.length,
      blocked: state.projects.filter((project) => project.status === "blocked").length,
      dueThisWeek: state.projects.reduce((total, project) => total + project.tasksDue, 0),
      missingDocuments: state.projects.reduce((total, project) => total + project.missingDocuments, 0),
      readyForReview: state.projects.filter((project) => project.status === "ready-review" || project.status === "done").length
    }
  };
}

export function buildCapxPmPracticalWorkspaceViewModel(
  project: CapxPmPracticalProject,
  stepSlug: CapxPmPracticalStepSlug,
  state: CapxPmPracticalDemoState = capxPmPracticalDemoState
): CapxPmPracticalWorkspaceViewModel {
  const selectedStep = state.steps.find((step) => step.slug === stepSlug);
  const selectedStepState = getCapxPmPracticalStepState(project, stepSlug);

  if (!selectedStep || !selectedStepState) {
    throw new Error(`Unknown PM practical step ${stepSlug}`);
  }

  const urgentTask =
    selectedStepState.primaryAction ??
    project.steps
      .flatMap((step) => step.primaryAction)
      .sort((left, right) => capxPmPracticalStatusRank(left.status) - capxPmPracticalStatusRank(right.status))[0];

  return {
    generatedAt: state.generatedAt,
    project,
    steps: state.steps,
    selectedStep,
    selectedStepState,
    urgentTask
  };
}
