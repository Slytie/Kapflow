import { Link, useParams } from "react-router-dom";

import { getCapxPmFeDemoProject } from "@/pages/capx-pm-fe-demo/capxPmFeDemoViewModels";
import { CapxPmV2NotFound, CapxPmV2ProjectBadge, CapxPmV2Section, CapxPmV2Shell, CapxPmV2StatusPill } from "./CapxPmV2Shared";

const ganttScale = ["May W1", "May W2", "May W3", "May W4", "Jun W1", "Jun W2", "Jun W3", "Jun W4", "Jul W1", "Jul W2"];

export function CapxPmV2GanttPage(): JSX.Element {
  const { projectId } = useParams();
  const project = getCapxPmFeDemoProject(projectId);

  if (!project) {
    return (
      <CapxPmV2NotFound
        body="This fake project ID is not in the PM V2 demo data."
        linkHref="/demo/capx/pm-v2/projects"
        linkLabel="Back to PM V2"
        testId="capx-pm-v2-gantt-project-not-found"
        title="Project not found"
      />
    );
  }

  return (
    <CapxPmV2Shell>
      <main className="capx-pm-v2-project" data-testid="capx-pm-v2-gantt-page">
        <section className="capx-pm-v2-project-hero">
          <div>
            <Link className="capx-pm-v2-back" to={`/demo/capx/pm-v2/projects/${project.id}`}>
              Back to V2 workspace
            </Link>
            <CapxPmV2ProjectBadge project={project} />
          </div>
          <div className="capx-pm-v2-project-hero__stats">
            <span>{project.schedule}</span>
            <span>{project.budget}</span>
            <CapxPmV2StatusPill status={project.health} />
          </div>
        </section>

        <CapxPmV2Section
          action={
            <Link className="capx-pm-v2-button capx-pm-v2-button--secondary" to={`/demo/capx/pm-v2/projects/${project.id}/steps/timeline`}>
              Open Timeline step
            </Link>
          }
          eyebrow="Read-only schedule"
          title="Project Gantt"
          note="Baseline and forecast bars are simulated CSS only. No drag, drop, approval, closure, or official schedule change happens here."
        >
          <div className="capx-pm-v2-gantt" aria-label="Read-only baseline and forecast Gantt chart">
            <div className="capx-pm-v2-gantt__scale" aria-hidden="true">
              {ganttScale.map((label) => (
                <span key={label}>{label}</span>
              ))}
            </div>
            {project.gantt.map((item) => (
              <article className="capx-pm-v2-gantt__row" key={item.id}>
                <div className="capx-pm-v2-gantt__meta">
                  <span>{item.workstream}</span>
                  <strong>{item.task}</strong>
                  <p>
                    {item.owner} | Depends on {item.dependsOn}
                  </p>
                  <p>
                    {item.criticalPath ? "Critical path" : "Non-critical"} |{" "}
                    {item.changedSinceLastReport ? "Changed since last report" : "No new movement"}
                  </p>
                  <CapxPmV2StatusPill status={item.status} />
                </div>
                <div className="capx-pm-v2-gantt__bars">
                  <span
                    className="capx-pm-v2-gantt__bar capx-pm-v2-gantt__bar--baseline"
                    style={{ gridColumn: `${item.baselineStart} / span ${item.baselineSpan}` }}
                  >
                    {item.baselineLabel}
                  </span>
                  <span
                    className={`capx-pm-v2-gantt__bar capx-pm-v2-gantt__bar--forecast${
                      item.criticalPath ? " is-critical" : ""
                    }${item.changedSinceLastReport ? " is-changed" : ""}`}
                    style={{ gridColumn: `${item.forecastStart} / span ${item.forecastSpan}` }}
                  >
                    {item.forecastLabel}
                  </span>
                </div>
                <p className="capx-pm-v2-gantt__blocker">
                  {item.deltaDays > 0 ? "+" : ""}
                  {item.deltaDays} days | {item.blocker}
                </p>
              </article>
            ))}
          </div>
        </CapxPmV2Section>

        <CapxPmV2Section eyebrow="Mobile schedule cards" title="Same schedule movement without wide-table review">
          <div className="capx-pm-v2-mobile-cards" data-testid="capx-pm-v2-gantt-mobile-cards">
            {project.gantt.map((item) => (
              <article className="capx-pm-v2-mobile-card" key={item.id}>
                <div className="capx-pm-v2-mobile-card__row">
                  <span>Task</span>
                  <strong>{item.task}</strong>
                </div>
                <div className="capx-pm-v2-mobile-card__row">
                  <span>Owner</span>
                  <strong>{item.owner}</strong>
                </div>
                <div className="capx-pm-v2-mobile-card__row">
                  <span>Baseline</span>
                  <strong>{item.baselineLabel}</strong>
                </div>
                <div className="capx-pm-v2-mobile-card__row">
                  <span>Forecast</span>
                  <strong>{item.forecastLabel}</strong>
                </div>
                <div className="capx-pm-v2-mobile-card__row">
                  <span>Blocker</span>
                  <strong>{item.blocker}</strong>
                </div>
              </article>
            ))}
          </div>
        </CapxPmV2Section>
      </main>
    </CapxPmV2Shell>
  );
}
