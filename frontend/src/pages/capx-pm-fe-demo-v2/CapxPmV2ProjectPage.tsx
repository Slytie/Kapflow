import { Link, useParams } from "react-router-dom";

import { capxPmFeDemoState } from "@/pages/capx-pm-fe-demo/capxPmFeDemoMockData";
import type { CapxPmFeDemoStepId } from "@/pages/capx-pm-fe-demo/capxPmFeDemoTypes";
import { getCapxPmFeDemoProject } from "@/pages/capx-pm-fe-demo/capxPmFeDemoViewModels";
import {
  CapxPmV2InfoGrid,
  CapxPmV2NotFound,
  CapxPmV2ProjectBadge,
  CapxPmV2Section,
  CapxPmV2Shell,
  CapxPmV2StatusPill
} from "./CapxPmV2Shared";
import { CapxPmV2StepBody } from "./CapxPmV2StepPanels";

export function CapxPmV2ProjectPage(): JSX.Element {
  const { projectId, stepId } = useParams();
  const project = getCapxPmFeDemoProject(projectId);

  if (!project) {
    return (
      <CapxPmV2NotFound
        body="This fake project ID is not in the PM V2 demo data."
        linkHref="/demo/capx/pm-v2/projects"
        linkLabel="Back to PM V2"
        testId="capx-pm-v2-project-not-found"
        title="Project not found"
      />
    );
  }

  if (stepId && !capxPmFeDemoState.steps.some((step) => step.id === stepId)) {
    return (
      <CapxPmV2NotFound
        body="This practical PM step is not part of the local V2 demo."
        linkHref={`/demo/capx/pm-v2/projects/${project.id}`}
        linkLabel="Back to project workspace"
        testId="capx-pm-v2-step-not-found"
        title="Step not found"
      />
    );
  }

  const activeStepId = (stepId ?? project.activeStep) as CapxPmFeDemoStepId;
  const activeStep = capxPmFeDemoState.steps.find((step) => step.id === activeStepId) ?? capxPmFeDemoState.steps[0];
  const missingProof = project.documents.filter(
    (document) => document.status === "proof-missing" || document.status === "waiting-supplier" || document.status === "waiting-site"
  );
  const lateTasks = project.blockers.filter((blocker) => blocker.due === "Today" || blocker.due === "This week");

  return (
    <CapxPmV2Shell>
      <main className="capx-pm-v2-project" data-testid="capx-pm-v2-project-page">
        <section className="capx-pm-v2-project-hero">
          <div>
            <Link className="capx-pm-v2-back" to="/demo/capx/pm-v2/projects">
              Back to V2 queue
            </Link>
            <CapxPmV2ProjectBadge project={project} />
          </div>
          <div className="capx-pm-v2-project-hero__stats">
            <span>{project.stage}</span>
            <span>{project.schedule}</span>
            <span>{project.budget}</span>
            <span>{project.quality}</span>
            <CapxPmV2StatusPill status={project.health} />
          </div>
        </section>

        <section className="capx-pm-v2-next-band" aria-label="Urgent PM next action">
          <div>
            <p className="capx-pm-v2-eyebrow">Next action</p>
            <h2>{project.nextAction.title}</h2>
            <p>{project.nextAction.consequence}</p>
          </div>
          <CapxPmV2InfoGrid
            items={[
              { label: "Owner", value: project.nextAction.owner },
              { label: "Due", value: project.nextAction.due },
              { label: "Blocker", value: project.nextAction.blocker },
              { label: "Proof needed", value: project.nextAction.proofNeeded }
            ]}
          />
        </section>

        <section className="capx-pm-v2-workbench" data-testid="capx-pm-v2-workspace-shell">
          <aside className="capx-pm-v2-step-rail" aria-label="PM project steps">
            <div className="capx-pm-v2-panel-head">
              <p className="capx-pm-v2-eyebrow">Steps</p>
              <h2>Practical PM flow</h2>
            </div>
            <nav>
              {capxPmFeDemoState.steps.map((step) => (
                <Link
                  aria-current={step.id === activeStepId ? "page" : undefined}
                  className={step.id === activeStepId ? "is-active" : undefined}
                  key={step.id}
                  to={`/demo/capx/pm-v2/projects/${project.id}/steps/${step.id}`}
                >
                  <span>{step.number}</span>
                  <strong>{step.label}</strong>
                  <small>{step.question}</small>
                </Link>
              ))}
              <Link className="capx-pm-v2-step-rail__gantt" to={`/demo/capx/pm-v2/projects/${project.id}/gantt`}>
                <span>G</span>
                <strong>Project Gantt</strong>
                <small>Read-only schedule bars and blockers</small>
              </Link>
            </nav>
          </aside>

          <section className="capx-pm-v2-step-main" aria-labelledby="capx-pm-v2-active-step-title">
            <CapxPmV2Section
              eyebrow={`Active step ${activeStep.number}`}
              title={activeStep.label}
              note={activeStep.question}
              testId="capx-pm-v2-active-step-summary"
            >
              <CapxPmV2InfoGrid
                items={[
                  { label: "Project", value: project.name },
                  { label: "PM owner", value: project.pm },
                  { label: "Waiting on", value: project.waitingOn },
                  { label: "Last material change", value: project.lastUpdate }
                ]}
              />
            </CapxPmV2Section>
            <h2 className="capx-pm-v2-visually-hidden" id="capx-pm-v2-active-step-title">
              {activeStep.label}
            </h2>
            <CapxPmV2StepBody project={project} stepId={activeStepId} />
          </section>

          <aside className="capx-pm-v2-right-rail" aria-label="Project pressure rail">
            <CapxPmV2Section eyebrow="Blockers" title="Open decisions">
              <ul className="capx-pm-v2-list">
                {project.blockers.map((blocker) => (
                  <li key={blocker.id}>
                    <strong>{blocker.title}</strong>
                    <span>
                      {blocker.owner} | {blocker.due}
                    </span>
                    <p>{blocker.impact}</p>
                  </li>
                ))}
              </ul>
            </CapxPmV2Section>

            <CapxPmV2Section eyebrow="Late tasks" title={`${lateTasks.length} urgent`}>
              <ul className="capx-pm-v2-list">
                {lateTasks.map((task) => (
                  <li key={task.id}>
                    <strong>{task.title}</strong>
                    <span>{task.waitingOn}</span>
                    <p>{task.proofNeeded}</p>
                  </li>
                ))}
              </ul>
            </CapxPmV2Section>

            <CapxPmV2Section eyebrow="Proof" title={`${missingProof.length} missing or waiting`}>
              <ul className="capx-pm-v2-list">
                {missingProof.map((document) => (
                  <li key={document.id}>
                    <strong>{document.name}</strong>
                    <span>{document.owner}</span>
                    <p>{document.action}</p>
                  </li>
                ))}
              </ul>
            </CapxPmV2Section>

            <CapxPmV2Section eyebrow="Escalation" title={project.escalation}>
              <p>{project.report.escalationNeeded}</p>
              <div className="capx-pm-v2-rail-links">
                <Link className="capx-pm-v2-button capx-pm-v2-button--secondary" to={`/demo/capx/pm-v2/projects/${project.id}/steps/project-report`}>
                  Open report step
                </Link>
                <Link className="capx-pm-v2-button capx-pm-v2-button--secondary" to={`/demo/capx/pm/projects/${project.id}`}>
                  Open V1 workspace
                </Link>
              </div>
            </CapxPmV2Section>
          </aside>
        </section>
      </main>
    </CapxPmV2Shell>
  );
}
