import { Link } from "react-router-dom";

import { getCapxStatusClass, getCapxStatusLabel } from "./capxCeoCockpitStatus";
import {
  buildCapxOverviewViewModel,
  formatMoneyMillions,
  formatMoneyThousands,
  formatPercent,
  formatSignedPercent,
  trendPolyline
} from "./capxCeoCockpitViewModels";
import type { CapxProjectOverview, CapxStatus } from "./capxCeoCockpitTypes";
import { CapxCeoCockpitShell } from "./CapxCeoCockpitShell";

function StatusChip({ status }: { status: CapxStatus }): JSX.Element {
  const label = getCapxStatusLabel(status);
  return (
    <span
      className={`capx-status-chip ${getCapxStatusClass(status)}`}
      aria-label={label}
      title={label}
      data-status-chip
    >
      <span className="capx-visually-hidden">{label}</span>
    </span>
  );
}

function TrendSparkline({ points, status }: { points: number[]; status: CapxStatus }): JSX.Element {
  return (
    <svg className="capx-sparkline" viewBox="0 0 84 28" role="img" aria-label="project trend">
      <polyline className={getCapxStatusClass(status)} points={trendPolyline(points)} />
    </svg>
  );
}

function ProjectMobileCard({ project }: { project: CapxProjectOverview }): JSX.Element {
  return (
    <Link
      className={`capx-mobile-project-card ${project.status === "critical" ? "capx-risk-outline" : ""}`}
      to={`/demo/capx/ceo-cockpit/projects/${project.id}`}
    >
      <div>
        <strong>
          {project.code} {project.name}
        </strong>
        <StatusChip status={project.status} />
      </div>
      <dl>
        <div>
          <dt>Risk mode</dt>
          <dd>{project.riskMode}</dd>
        </div>
        <div>
          <dt>Exposure</dt>
          <dd>{formatMoneyMillions(project.exposureAtRiskMillions)}</dd>
        </div>
        <div>
          <dt>Opp. cost</dt>
          <dd>{formatMoneyThousands(project.opportunityCostPerWeekThousands)}</dd>
        </div>
        <div>
          <dt>Delay</dt>
          <dd>{formatPercent(project.probableDelayPercent)}</dd>
        </div>
      </dl>
    </Link>
  );
}

export function CapxCeoCockpitOverviewPage(): JSX.Element {
  const viewModel = buildCapxOverviewViewModel();
  const projectById = new Map(viewModel.projects.map((project) => [project.id, project]));

  return (
    <CapxCeoCockpitShell updatedAt={viewModel.generatedAt}>
      <main className="capx-cockpit-page" data-testid="capx-overview-page">
        <section className="capx-overview-top">
          <div className="capx-panel capx-action-board" aria-labelledby="capx-actions-title">
            <div className="capx-panel__header">
              <h2 id="capx-actions-title">CEO Actions</h2>
              <span>{viewModel.dueTodayActions.length} due today</span>
            </div>
            <div className="capx-action-board__lanes">
              {viewModel.actionsByLane.map((lane) => (
                <section key={lane.lane} className="capx-action-lane" aria-label={lane.label}>
                  <h3>
                    {lane.label} <span>({lane.actions.length})</span>
                  </h3>
                  <div className="capx-action-lane__items">
                    {lane.actions.slice(0, 4).map((action) => {
                      const project = projectById.get(action.projectId);
                      return (
                        <Link
                          key={action.id}
                          className={`capx-action-card ${getCapxStatusClass(action.status)}`}
                          to={`/demo/capx/ceo-cockpit/projects/${action.projectId}`}
                        >
                          <span className="capx-action-card__project">
                            <span>{project?.name ?? action.projectCode}</span>
                            <strong>{action.projectCode}</strong>
                          </span>
                          <span className="capx-action-card__task">{action.title}</span>
                          {project ? (
                            <small title={`${project.name}; PM ${project.projectManager}`}>PM {project.projectManager}</small>
                          ) : null}
                        </Link>
                      );
                    })}
                  </div>
                </section>
              ))}
            </div>
          </div>

          <div className="capx-panel capx-risk-strip" aria-labelledby="capx-risk-title">
            <div className="capx-panel__header">
              <h2 id="capx-risk-title">Portfolio Risk</h2>
              <span>Static projection</span>
            </div>
            <dl className="capx-risk-strip__grid">
              {viewModel.portfolioMetrics.map((metric) => (
                <div key={metric.label} className={`capx-risk-metric ${getCapxStatusClass(metric.tone)}`}>
                  <dt>{metric.label}</dt>
                  <dd>{metric.value}</dd>
                </div>
              ))}
            </dl>
          </div>
        </section>

        <section className="capx-panel capx-projects-table-panel" aria-labelledby="capx-projects-title">
          <div className="capx-panel__header">
            <h2 id="capx-projects-title">Projects Overview</h2>
            <span>Showing 1-12 of 18 projects</span>
          </div>
          <div className="capx-projects-table-wrap">
            <table className="capx-projects-table">
              <thead>
                <tr>
                  <th>Project</th>
                  <th>Stage</th>
                  <th>Status</th>
                  <th>Risk mode</th>
                  <th>Exposure at risk</th>
                  <th>Opportunity cost per week</th>
                  <th>Probable delay</th>
                  <th>Budget variance</th>
                  <th>Schedule variance</th>
                  <th>Evidence freshness</th>
                  <th>Board impact</th>
                  <th>Trend</th>
                  <th>Last update</th>
                </tr>
              </thead>
              <tbody>
                {viewModel.projects.map((project) => (
                  <tr key={project.id} className={project.status === "critical" ? "capx-project-row--critical" : ""}>
                    <td>
                      <Link to={`/demo/capx/ceo-cockpit/projects/${project.id}`}>
                        <strong>{project.code}</strong> {project.name}
                      </Link>
                    </td>
                    <td>{project.stage}</td>
                    <td>
                      <StatusChip status={project.status} />
                    </td>
                    <td>{project.riskMode}</td>
                    <td>{formatMoneyMillions(project.exposureAtRiskMillions)}</td>
                    <td>{formatMoneyThousands(project.opportunityCostPerWeekThousands)}</td>
                    <td className={project.probableDelayPercent > 55 ? "capx-text-critical" : "capx-text-watch"}>
                      {formatPercent(project.probableDelayPercent)}
                    </td>
                    <td>{formatSignedPercent(project.budgetVariancePercent)}</td>
                    <td>{formatSignedPercent(project.scheduleVariancePercent)}</td>
                    <td>{project.evidenceFreshnessDays}d</td>
                    <td>{project.boardImpact}</td>
                    <td>
                      <TrendSparkline points={project.trend} status={project.status} />
                    </td>
                    <td>{project.lastUpdate}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>

        <section className="capx-mobile-overview" aria-label="CAPX mobile overview">
          <div className="capx-mobile-metrics">
            {viewModel.portfolioMetrics.slice(0, 4).map((metric) => (
              <div key={metric.label}>
                <span>{metric.label}</span>
                <strong>{metric.value}</strong>
              </div>
            ))}
          </div>
          <div className="capx-panel">
            <div className="capx-panel__header">
              <h2>Due Today</h2>
              <span>{viewModel.dueTodayActions.length}</span>
            </div>
            <div className="capx-mobile-action-list">
              {viewModel.dueTodayActions.map((action) => {
                const project = projectById.get(action.projectId);
                return (
                  <Link key={action.id} to={`/demo/capx/ceo-cockpit/projects/${action.projectId}`}>
                    <span>
                      {project ? <b>{project.name}</b> : null}
                      {action.title}
                      {project ? (
                        <small>
                          PM {project.projectManager}
                        </small>
                      ) : null}
                    </span>
                    <strong>{action.projectCode}</strong>
                  </Link>
                );
              })}
            </div>
          </div>
          <div className="capx-panel">
            <div className="capx-panel__header">
              <h2>Top Projects</h2>
              <span>By exposure</span>
            </div>
            <div className="capx-mobile-project-list">
              {viewModel.topProjects.map((project) => (
                <ProjectMobileCard key={project.id} project={project} />
              ))}
            </div>
          </div>
        </section>
      </main>
    </CapxCeoCockpitShell>
  );
}
