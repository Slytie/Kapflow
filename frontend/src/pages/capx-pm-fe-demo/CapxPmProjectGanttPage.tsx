import { Link, useParams } from "react-router-dom";

import { CapxPmFeNotFound, CapxPmFeSection, CapxPmFeStatusChip } from "./CapxPmFeDemoComponents";
import { buildCapxPmFeDemoProjectHref, buildCapxPmFeDemoStepHref, getCapxPmFeDemoProject } from "./capxPmFeDemoViewModels";

export function CapxPmProjectGanttPage(): JSX.Element {
  const { projectId } = useParams();
  const project = getCapxPmFeDemoProject(projectId);

  if (!project) {
    return (
      <CapxPmFeNotFound
        title="Project not found"
        body="This fake project ID is not in the local CAPX PM demo data."
        linkLabel="Back to My CAPX Projects"
        linkHref="/demo/capx/pm/projects"
        testId="capx-pm-fe-gantt-project-not-found"
      />
    );
  }

  return (
    <main className="capx-pm-fe-page" data-testid="capx-pm-fe-gantt-page">
      <section className="capx-pm-fe-project-header">
        <div>
          <Link className="capx-pm-fe-back-link" to={buildCapxPmFeDemoProjectHref(project.id)}>
            Back to project workspace
          </Link>
          <h2>
            {project.id} {project.name} Project Gantt
          </h2>
          <p>Read-only schedule detail showing baseline, forecast, blockers, and critical path.</p>
        </div>
        <Link className="capx-pm-fe-button" to={buildCapxPmFeDemoStepHref(project.id, "timeline")}>
          Open Timeline step
        </Link>
      </section>

      <CapxPmFeSection title="Baseline vs forecast schedule" note="CSS-rendered bars; no official schedule mutation">
        <div className="capx-pm-fe-gantt" aria-label="Read-only Gantt chart">
          <div className="capx-pm-fe-gantt__scale" aria-hidden="true">
            {["May W1", "May W2", "May W3", "May W4", "Jun W1", "Jun W2", "Jun W3", "Jun W4", "Jul W1", "Jul W2"].map(
              (label) => (
                <span key={label}>{label}</span>
              )
            )}
          </div>
          {project.gantt.map((item) => (
            <article className="capx-pm-fe-gantt__row" key={item.id}>
              <div className="capx-pm-fe-gantt__meta">
                <span>{item.workstream}</span>
                <strong>{item.task}</strong>
                <p>
                  {item.owner} | {item.deltaDays > 0 ? "+" : ""}
                  {item.deltaDays} days | Depends on {item.dependsOn}
                </p>
                <CapxPmFeStatusChip status={item.status} />
              </div>
              <div className="capx-pm-fe-gantt__bars">
                <span
                  className="capx-pm-fe-gantt__bar capx-pm-fe-gantt__bar--baseline"
                  style={{ gridColumn: `${item.baselineStart} / span ${item.baselineSpan}` }}
                >
                  {item.baselineLabel}
                </span>
                <span
                  className={`capx-pm-fe-gantt__bar capx-pm-fe-gantt__bar--forecast${
                    item.criticalPath ? " is-critical" : ""
                  }${item.changedSinceLastReport ? " is-changed" : ""}`}
                  style={{ gridColumn: `${item.forecastStart} / span ${item.forecastSpan}` }}
                >
                  {item.forecastLabel}
                </span>
              </div>
              <p className="capx-pm-fe-gantt__blocker">{item.blocker}</p>
            </article>
          ))}
        </div>
      </CapxPmFeSection>

      <CapxPmFeSection title="Mobile schedule cards" note="Same schedule movement without horizontal scrolling">
        <div className="capx-pm-fe-mobile-cards" data-testid="capx-pm-fe-gantt-mobile-cards">
          {project.gantt.map((item) => (
            <article className="capx-pm-fe-mobile-card" key={item.id}>
              <div className="capx-pm-fe-mobile-card__row">
                <span>Task</span>
                <strong>{item.task}</strong>
              </div>
              <div className="capx-pm-fe-mobile-card__row">
                <span>Baseline</span>
                <strong>{item.baselineLabel}</strong>
              </div>
              <div className="capx-pm-fe-mobile-card__row">
                <span>Forecast</span>
                <strong>{item.forecastLabel}</strong>
              </div>
              <div className="capx-pm-fe-mobile-card__row">
                <span>Blocker</span>
                <strong>{item.blocker}</strong>
              </div>
            </article>
          ))}
        </div>
      </CapxPmFeSection>
    </main>
  );
}
