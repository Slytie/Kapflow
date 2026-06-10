import { Link, useParams } from "react-router-dom";

import { CapxPmFeMetricCard, CapxPmFeNotFound, CapxPmFeSection, CapxPmFeStatusChip } from "./CapxPmFeDemoComponents";
import { CapxPmStepBudgetOrders } from "./steps/CapxPmStepBudgetOrders";
import { CapxPmStepDocuments } from "./steps/CapxPmStepDocuments";
import { CapxPmStepProjectReport } from "./steps/CapxPmStepProjectReport";
import { CapxPmStepProjectSetup } from "./steps/CapxPmStepProjectSetup";
import { CapxPmStepSiteHandoffs } from "./steps/CapxPmStepSiteHandoffs";
import { CapxPmStepSupplierQuestions } from "./steps/CapxPmStepSupplierQuestions";
import { CapxPmStepTimeline } from "./steps/CapxPmStepTimeline";
import type { CapxPmFeDemoProject, CapxPmFeDemoStepId } from "./capxPmFeDemoTypes";
import {
  buildCapxPmFeDemoGanttHref,
  buildCapxPmFeDemoProjectHref,
  buildCapxPmFeDemoStepHref,
  buildCapxPmFeDemoWorkspaceViewModel,
  getCapxPmFeDemoProject,
  getCapxPmFeDemoStep,
  isCapxPmFeDemoStepId
} from "./capxPmFeDemoViewModels";

function ProjectHeader({ project }: { project: CapxPmFeDemoProject }): JSX.Element {
  return (
    <section className="capx-pm-fe-project-header" aria-label="Project workspace header">
      <div>
        <Link className="capx-pm-fe-back-link" to="/demo/capx/pm/projects">
          Back to My CAPX Projects
        </Link>
        <h2>
          {project.id} {project.name}
        </h2>
        <p>
          {project.site} | {project.area} | PM {project.pm} | Sponsor {project.sponsor}
        </p>
      </div>
      <div className="capx-pm-fe-pressure-row">
        <CapxPmFeStatusChip status={project.health} />
        <span>{project.schedule}</span>
        <span>{project.budget}</span>
        <span>{project.waitingOn}</span>
      </div>
    </section>
  );
}

function NextActionBand({ project }: { project: CapxPmFeDemoProject }): JSX.Element {
  const action = project.nextAction;
  return (
    <section className="capx-pm-fe-next-action" aria-label="Next PM action">
      <div>
        <p className="capx-pm-fe-eyebrow">Next PM action</p>
        <h2>{action.title}</h2>
      </div>
      <div className="capx-pm-fe-next-action__grid">
        <CapxPmFeMetricCard label="Owner" value={action.owner} />
        <CapxPmFeMetricCard label="Due" value={action.due} tone={action.due === "Today" ? "alert" : "neutral"} />
        <CapxPmFeMetricCard label="Proof needed" value={action.proofNeeded} />
        <CapxPmFeMetricCard label="Blocker" value={action.blocker} tone="alert" />
      </div>
      <p>{action.consequence}</p>
    </section>
  );
}

function StepNav({ project, selectedStepId }: { project: CapxPmFeDemoProject; selectedStepId?: string }): JSX.Element {
  const viewModel = buildCapxPmFeDemoWorkspaceViewModel(project);
  return (
    <nav className="capx-pm-fe-step-nav" aria-label="PM project steps">
      {viewModel.steps.map((step) => (
        <Link
          aria-current={selectedStepId === step.id ? "page" : undefined}
          key={step.id}
          to={buildCapxPmFeDemoStepHref(project.id, step.id)}
        >
          <span>{step.number}</span>
          <strong>{step.label}</strong>
          <em>{step.question}</em>
        </Link>
      ))}
      <Link aria-current={selectedStepId === "gantt" ? "page" : undefined} to={buildCapxPmFeDemoGanttHref(project.id)}>
        <span>G</span>
        <strong>Project Gantt</strong>
        <em>Read-only schedule detail</em>
      </Link>
    </nav>
  );
}

function RightRail({ project }: { project: CapxPmFeDemoProject }): JSX.Element {
  return (
    <aside className="capx-pm-fe-right-rail" aria-label="Open blockers and proof">
      <section>
        <h2>Open blockers</h2>
        <ul>
          {project.blockers.map((blocker) => (
            <li key={blocker.id}>
              <strong>{blocker.title}</strong>
              <span>
                {blocker.owner} | Due {blocker.due}
              </span>
              <p>{blocker.impact}</p>
              <CapxPmFeStatusChip status={blocker.status} />
            </li>
          ))}
        </ul>
      </section>
      <section>
        <h2>Missing proof</h2>
        <ul>
          {project.documents
            .filter((document) => document.status === "proof-missing" || document.status === "waiting-supplier")
            .map((document) => (
              <li key={document.id}>
                <strong>{document.name}</strong>
                <span>{document.action}</span>
              </li>
            ))}
        </ul>
      </section>
      <section>
        <h2>Escalation</h2>
        <p>{project.escalation}</p>
        <button type="button" disabled>
          Simulated only - no official action
        </button>
      </section>
    </aside>
  );
}

function WorkspaceOverview({ project }: { project: CapxPmFeDemoProject }): JSX.Element {
  const activeStep = getCapxPmFeDemoStep(project.activeStep);
  return (
    <div data-testid="capx-pm-fe-workspace-overview">
      <CapxPmFeSection title="Project workspace" note="Daily PM control surface">
        <div className="capx-pm-fe-card-grid">
          <article className="capx-pm-fe-card capx-pm-fe-card--alert">
            <span>Active step</span>
            <strong>{activeStep.label}</strong>
            <p>{activeStep.question}</p>
            <Link className="capx-pm-fe-button" to={buildCapxPmFeDemoStepHref(project.id, activeStep.id)}>
              Open active step
            </Link>
          </article>
          <article className="capx-pm-fe-card">
            <span>Report readiness</span>
            <strong>{project.report.readiness}</strong>
            <p>{project.report.currentStatus}</p>
          </article>
          <article className="capx-pm-fe-card">
            <span>Schedule</span>
            <strong>{project.schedule}</strong>
            <p>{project.report.scheduleMovement}</p>
          </article>
        </div>
      </CapxPmFeSection>
    </div>
  );
}

function StepBody({ project, stepId }: { project: CapxPmFeDemoProject; stepId: CapxPmFeDemoStepId }): JSX.Element {
  switch (stepId) {
    case "project-setup":
      return <CapxPmStepProjectSetup project={project} />;
    case "documents":
      return <CapxPmStepDocuments project={project} />;
    case "timeline":
      return <CapxPmStepTimeline project={project} />;
    case "budget-orders":
      return <CapxPmStepBudgetOrders project={project} />;
    case "supplier-questions":
      return <CapxPmStepSupplierQuestions project={project} />;
    case "site-handoffs":
      return <CapxPmStepSiteHandoffs project={project} />;
    case "project-report":
      return <CapxPmStepProjectReport project={project} />;
  }
}

export function CapxPmProjectWorkspacePage(): JSX.Element {
  const { projectId, stepId } = useParams();
  const project = getCapxPmFeDemoProject(projectId);

  if (!project) {
    return (
      <CapxPmFeNotFound
        title="Project not found"
        body="This fake project ID is not in the local CAPX PM demo data."
        linkLabel="Back to My CAPX Projects"
        linkHref="/demo/capx/pm/projects"
        testId="capx-pm-fe-project-not-found"
      />
    );
  }

  if (stepId && !isCapxPmFeDemoStepId(stepId)) {
    return (
      <CapxPmFeNotFound
        title="Step not found"
        body="This step is not part of the seven-step PM demo route family."
        linkLabel="Open project workspace"
        linkHref={buildCapxPmFeDemoProjectHref(project.id)}
        testId="capx-pm-fe-step-not-found"
      />
    );
  }
  const selectedStepId = stepId && isCapxPmFeDemoStepId(stepId) ? stepId : undefined;

  return (
    <main className="capx-pm-fe-page" data-testid="capx-pm-fe-workspace-page">
      <ProjectHeader project={project} />
      <NextActionBand project={project} />
      <StepNav project={project} selectedStepId={selectedStepId} />
      <div className="capx-pm-fe-workspace-grid">
        <div>
          {selectedStepId ? <StepBody project={project} stepId={selectedStepId} /> : <WorkspaceOverview project={project} />}
        </div>
        <RightRail project={project} />
      </div>
    </main>
  );
}
