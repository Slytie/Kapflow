import { capxPmDemoState } from "./capxPmProjectData";
import { capxPmStatusRank, getCapxPmEvidenceStatus, getCapxPmReadinessStatus } from "./capxPmProjectStatus";
import type {
  CapxPmDemoState,
  CapxPmProject,
  CapxPmStatus,
  CapxPmStepSlug,
  CapxPmStepState,
  CapxPmWorkflowStep
} from "./capxPmProjectTypes";

export interface CapxPmIndexItem {
  project: CapxPmProject;
  activeStep: CapxPmWorkflowStep;
  activeStepState: CapxPmStepState;
  evidenceStatus: CapxPmStatus;
  readinessStatus: CapxPmStatus;
  priorityTaskTitle: string;
  priorityTaskOwner: string;
}

export interface CapxPmIndexViewModel {
  generatedAt: string;
  projects: CapxPmIndexItem[];
  totals: {
    projectCount: number;
    blockerCount: number;
    openTaskCount: number;
    reviewReadyCount: number;
  };
}

export interface CapxPmWorkspaceViewModel {
  generatedAt: string;
  project: CapxPmProject;
  step: CapxPmWorkflowStep;
  stepState: CapxPmStepState;
  steps: Array<{
    step: CapxPmWorkflowStep;
    state: CapxPmStepState;
    href: string;
  }>;
}

export function getCapxPmDemoState(): CapxPmDemoState {
  return capxPmDemoState;
}

export function getCapxPmProject(projectId: string | undefined): CapxPmProject | undefined {
  if (!projectId) {
    return undefined;
  }
  return capxPmDemoState.projects.find((project) => project.id === projectId);
}

export function getCapxPmWorkflowStep(stepSlug: string | undefined): CapxPmWorkflowStep | undefined {
  if (!stepSlug) {
    return undefined;
  }
  return capxPmDemoState.workflowSteps.find((step) => step.slug === stepSlug);
}

export function getCapxPmProjectStep(project: CapxPmProject, stepSlug: string | undefined): CapxPmStepState | undefined {
  if (!stepSlug) {
    return undefined;
  }
  return project.steps.find((stepState) => stepState.slug === stepSlug);
}

export function getCapxPmDefaultStepSlug(project: CapxPmProject): CapxPmStepSlug {
  return project.activeStep;
}

export function buildCapxPmProjectHref(project: CapxPmProject): string {
  return `/demo/capx/pm/projects/${project.id}`;
}

export function buildCapxPmStepHref(project: CapxPmProject, stepSlug: CapxPmStepSlug): string {
  return `/demo/capx/pm/projects/${project.id}/steps/${stepSlug}`;
}

export function buildCapxPmProjectIndexViewModel(): CapxPmIndexViewModel {
  const projects = capxPmDemoState.projects
    .map((project) => {
      const activeStep = getCapxPmWorkflowStep(project.activeStep);
      const activeStepState = getCapxPmProjectStep(project, project.activeStep);
      if (!activeStep || !activeStepState) {
        throw new Error(`CAPX PM mock project ${project.id} has an invalid active step.`);
      }

      const priorityTask = [...activeStepState.tasks].sort((left, right) => {
        return capxPmStatusRank(left.status) - capxPmStatusRank(right.status);
      })[0];

      return {
        project,
        activeStep,
        activeStepState,
        evidenceStatus: getCapxPmEvidenceStatus(project.evidenceFreshness),
        readinessStatus: getCapxPmReadinessStatus(project.snapshotReadiness),
        priorityTaskTitle: priorityTask?.title ?? "No active PM task",
        priorityTaskOwner: priorityTask?.owner ?? "Unassigned"
      };
    })
    .sort((left, right) => {
      const statusDelta = capxPmStatusRank(left.project.status) - capxPmStatusRank(right.project.status);
      if (statusDelta !== 0) {
        return statusDelta;
      }
      if (right.project.openBlockers !== left.project.openBlockers) {
        return right.project.openBlockers - left.project.openBlockers;
      }
      return right.project.openTasks - left.project.openTasks;
    });

  return {
    generatedAt: capxPmDemoState.generatedAt,
    projects,
    totals: {
      projectCount: capxPmDemoState.projects.length,
      blockerCount: capxPmDemoState.projects.reduce((total, project) => total + project.openBlockers, 0),
      openTaskCount: capxPmDemoState.projects.reduce((total, project) => total + project.openTasks, 0),
      reviewReadyCount: capxPmDemoState.projects.filter((project) => project.snapshotReadiness === "review-ready").length
    }
  };
}

export function buildCapxPmWorkspaceViewModel(project: CapxPmProject, stepSlug: CapxPmStepSlug): CapxPmWorkspaceViewModel {
  const step = getCapxPmWorkflowStep(stepSlug);
  const stepState = getCapxPmProjectStep(project, stepSlug);

  if (!step || !stepState) {
    throw new Error(`CAPX PM step ${stepSlug} is not available for project ${project.id}.`);
  }

  return {
    generatedAt: capxPmDemoState.generatedAt,
    project,
    step,
    stepState,
    steps: capxPmDemoState.workflowSteps.map((workflowStep) => {
      const state = getCapxPmProjectStep(project, workflowStep.slug);
      if (!state) {
        throw new Error(`CAPX PM project ${project.id} is missing step ${workflowStep.slug}.`);
      }
      return {
        step: workflowStep,
        state,
        href: buildCapxPmStepHref(project, workflowStep.slug)
      };
    })
  };
}

export function isCapxPmStepSlug(value: string | undefined): value is CapxPmStepSlug {
  return capxPmDemoState.workflowSteps.some((step) => step.slug === value);
}
