import { Link } from "react-router-dom";

import { CapxPmProjectShell } from "./CapxPmProjectShell";
import { CapxPmStatusChip } from "./CapxPmStatusChip";
import {
  buildCapxPmProjectHref,
  buildCapxPmProjectIndexViewModel
} from "./capxPmProjectViewModels";

export function CapxPmProjectIndexPage(): JSX.Element {
  const viewModel = buildCapxPmProjectIndexViewModel();

  return (
    <CapxPmProjectShell updatedAt={viewModel.generatedAt}>
      <main className="capx-pm-page" data-testid="capx-pm-index-page">
        <section className="capx-pm-index-hero" aria-labelledby="capx-pm-index-title">
          <div>
            <p className="capx-pm-eyebrow">Static PM projection</p>
            <h2 id="capx-pm-index-title">PM Project Index</h2>
            <p>
              Select a project to inspect the seven-step CAPX PM workflow spine. All rows are mock
              projections and do not create approvals, artifacts, or official project state.
            </p>
          </div>
          <dl className="capx-pm-index-metrics">
            <div>
              <dt>Projects</dt>
              <dd>{viewModel.totals.projectCount}</dd>
            </div>
            <div>
              <dt>Blockers</dt>
              <dd>{viewModel.totals.blockerCount}</dd>
            </div>
            <div>
              <dt>Open tasks</dt>
              <dd>{viewModel.totals.openTaskCount}</dd>
            </div>
            <div>
              <dt>Review ready</dt>
              <dd>{viewModel.totals.reviewReadyCount}</dd>
            </div>
          </dl>
        </section>

        <section className="capx-pm-panel capx-pm-project-table-panel" aria-labelledby="capx-pm-projects-title">
          <div className="capx-pm-panel__header">
            <h2 id="capx-pm-projects-title">Projects</h2>
            <span>Sorted by blocker pressure</span>
          </div>
          <div className="capx-pm-project-table-wrap">
            <table className="capx-pm-project-table">
              <thead>
                <tr>
                  <th>Project</th>
                  <th>PM owner</th>
                  <th>Dominant stage</th>
                  <th>Active workflow step</th>
                  <th>Open blockers</th>
                  <th>Open tasks</th>
                  <th>Evidence freshness</th>
                  <th>Snapshot readiness</th>
                  <th>Last material change</th>
                </tr>
              </thead>
              <tbody>
                {viewModel.projects.map((item) => (
                  <tr key={item.project.id} className={item.project.status === "critical" ? "capx-pm-row--critical" : ""}>
                    <td>
                      <Link to={buildCapxPmProjectHref(item.project)}>
                        <strong>{item.project.code}</strong> {item.project.name}
                      </Link>
                      <small>
                        {item.project.site} / {item.project.projectType}
                      </small>
                    </td>
                    <td>
                      <strong>{item.project.pmOwner}</strong>
                      <small>{item.project.ownerRole}</small>
                    </td>
                    <td>{item.project.dominantStage}</td>
                    <td>
                      <span className="capx-pm-chip-row">
                        <CapxPmStatusChip status={item.activeStepState.status} />
                        <span>
                          {item.activeStep.workflowId} {item.activeStep.shortTitle}
                        </span>
                      </span>
                    </td>
                    <td>
                      <strong>{item.project.openBlockers}</strong>
                      <small>{item.project.blockerSummary}</small>
                    </td>
                    <td>{item.project.openTasks}</td>
                    <td>
                      <span className="capx-pm-chip-row">
                        <CapxPmStatusChip status={item.evidenceStatus} />
                        <span>{item.project.evidenceFreshness}</span>
                      </span>
                    </td>
                    <td>
                      <span className="capx-pm-chip-row">
                        <CapxPmStatusChip status={item.readinessStatus} />
                        <span>{item.project.snapshotReadiness}</span>
                      </span>
                    </td>
                    <td>{item.project.lastMaterialChange}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>

        <section className="capx-pm-mobile-projects" aria-label="Mobile project priority cards">
          {viewModel.projects.map((item) => (
            <Link
              key={item.project.id}
              className={`capx-pm-project-card ${item.project.status === "critical" ? "capx-pm-project-card--critical" : ""}`}
              to={buildCapxPmProjectHref(item.project)}
            >
              <div className="capx-pm-project-card__top">
                <span>
                  <strong>{item.project.code}</strong> {item.project.name}
                </span>
                <CapxPmStatusChip status={item.project.status} />
              </div>
              <p>{item.project.blockerSummary}</p>
              <dl>
                <div>
                  <dt>Active step</dt>
                  <dd>{item.activeStep.shortTitle}</dd>
                </div>
                <div>
                  <dt>PM owner</dt>
                  <dd>{item.project.pmOwner}</dd>
                </div>
                <div>
                  <dt>Next task</dt>
                  <dd>{item.priorityTaskTitle}</dd>
                </div>
                <div>
                  <dt>Task owner</dt>
                  <dd>{item.priorityTaskOwner}</dd>
                </div>
              </dl>
            </Link>
          ))}
        </section>
      </main>
    </CapxPmProjectShell>
  );
}
