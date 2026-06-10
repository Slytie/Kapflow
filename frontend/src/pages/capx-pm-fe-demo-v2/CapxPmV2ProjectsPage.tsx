import { Link } from "react-router-dom";

import { capxPmFeDemoState } from "@/pages/capx-pm-fe-demo/capxPmFeDemoMockData";
import { buildCapxPmFeDemoProjectsViewModel } from "@/pages/capx-pm-fe-demo/capxPmFeDemoViewModels";
import { CapxPmV2ProjectBadge, CapxPmV2Shell, CapxPmV2StatusPill } from "./CapxPmV2Shared";

export function CapxPmV2ProjectsPage(): JSX.Element {
  const viewModel = buildCapxPmFeDemoProjectsViewModel();
  const primaryProject = viewModel.projects[0];
  const dueToday = viewModel.projects.filter((project) => project.nextAction.due === "Today");
  const readyProjects = viewModel.projects.filter((project) => project.health === "ready-share");

  return (
    <CapxPmV2Shell>
      <section className="capx-pm-v2-board" data-testid="capx-pm-v2-projects-page">
        <aside className="capx-pm-v2-queue" aria-label="Attention queue">
          <div className="capx-pm-v2-panel-head">
            <p className="capx-pm-v2-eyebrow">Queue</p>
            <h2>What should I open first?</h2>
          </div>
          {viewModel.projects.map((project) => (
            <Link className="capx-pm-v2-queue-card" key={project.id} to={`/demo/capx/pm-v2/projects/${project.id}`}>
              <CapxPmV2ProjectBadge project={project} />
              <CapxPmV2StatusPill status={project.health} />
              <p>{project.nextAction.title}</p>
              <span>
                Due {project.nextAction.due} / Waiting on {project.waitingOn}
              </span>
            </Link>
          ))}
        </aside>

        <section className="capx-pm-v2-focus" aria-labelledby="capx-pm-v2-focus-title">
          <p className="capx-pm-v2-eyebrow">Focus project</p>
          <h2 id="capx-pm-v2-focus-title">{primaryProject.id} next action</h2>
          <article className="capx-pm-v2-action-card">
            <CapxPmV2ProjectBadge project={primaryProject} />
            <h3>{primaryProject.nextAction.title}</h3>
            <dl>
              <div>
                <dt>Owner</dt>
                <dd>{primaryProject.nextAction.owner}</dd>
              </div>
              <div>
                <dt>Due</dt>
                <dd>{primaryProject.nextAction.due}</dd>
              </div>
              <div>
                <dt>Proof needed</dt>
                <dd>{primaryProject.nextAction.proofNeeded}</dd>
              </div>
              <div>
                <dt>Why it matters</dt>
                <dd>{primaryProject.nextAction.consequence}</dd>
              </div>
            </dl>
            <Link className="capx-pm-v2-button" to={`/demo/capx/pm-v2/projects/${primaryProject.id}`}>
              Open V2 workspace
            </Link>
          </article>
        </section>

        <aside className="capx-pm-v2-context" aria-label="Portfolio context">
          <section>
            <p className="capx-pm-v2-eyebrow">Today</p>
            <h2>{dueToday.length} due today</h2>
            <ul>
              {dueToday.map((project) => (
                <li key={project.id}>{project.nextAction.title}</li>
              ))}
            </ul>
          </section>
          <section>
            <p className="capx-pm-v2-eyebrow">Ready</p>
            <h2>{readyProjects.length} ready to share</h2>
            <ul>
              {readyProjects.map((project) => (
                <li key={project.id}>{project.name}</li>
              ))}
            </ul>
          </section>
          <section>
            <p className="capx-pm-v2-eyebrow">Version safety</p>
            <h2>V1 preserved</h2>
            <p>
              V1 remains at `/demo/capx/pm/projects`; this screen is mounted separately at `/demo/capx/pm-v2`.
            </p>
          </section>
          <section>
            <p className="capx-pm-v2-eyebrow">Data</p>
            <h2>{capxPmFeDemoState.projects.length} fake projects</h2>
            <p>No backend calls, no real project records.</p>
          </section>
        </aside>
      </section>
    </CapxPmV2Shell>
  );
}
