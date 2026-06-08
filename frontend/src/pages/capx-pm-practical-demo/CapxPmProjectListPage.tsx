import { useMemo, useState } from "react";
import { Link } from "react-router-dom";

import { CapxPmPracticalShell } from "./CapxPmPracticalShell";
import { CapxPmPracticalStatusChip } from "./CapxPmPracticalStatusChip";
import type { CapxPmPracticalFilter, CapxPmPracticalProject } from "./capxPmPracticalTypes";
import {
  buildCapxPmPracticalProjectHref,
  buildCapxPmPracticalProjectListViewModel,
  capxPmPracticalFilters
} from "./capxPmPracticalViewModels";

function ProjectMobileCard({ project }: { project: CapxPmPracticalProject }): JSX.Element {
  return (
    <article className="capx-pm-practical-mobile-card">
      <div className="capx-pm-practical-mobile-card__head">
        <div>
          <Link className="capx-pm-practical-card-link" to={buildCapxPmPracticalProjectHref(project)}>
            {project.id} {project.name}
          </Link>
          <p className="capx-pm-practical-muted">{project.siteArea}</p>
        </div>
        <CapxPmPracticalStatusChip status={project.status} />
      </div>
      <div className="capx-pm-practical-mobile-card__row">
        <span>Needs attention</span>
        <strong>{project.needsAttention}</strong>
      </div>
      <div className="capx-pm-practical-mobile-card__row">
        <span>Blockers / due</span>
        <strong>
          {project.blockers} blockers, {project.tasksDue} due
        </strong>
      </div>
      <div className="capx-pm-practical-mobile-card__row">
        <span>Phase / report</span>
        <strong>
          {project.phase} / {project.reportStatus}
        </strong>
      </div>
      <div className="capx-pm-practical-mobile-card__row">
        <span>Last update</span>
        <strong>{project.lastUpdate}</strong>
      </div>
    </article>
  );
}

export function CapxPmProjectListPage(): JSX.Element {
  const [filter, setFilter] = useState<CapxPmPracticalFilter>("all");
  const viewModel = useMemo(() => buildCapxPmPracticalProjectListViewModel(filter), [filter]);

  return (
    <CapxPmPracticalShell title="PM Project List" updatedAt={viewModel.generatedAt}>
      <main data-testid="capx-pm-practical-index-page">
        <section className="capx-pm-practical-kpis" aria-label="PM project totals">
          <div className="capx-pm-practical-kpi">
            <span>Projects</span>
            <strong>{viewModel.totals.projects}</strong>
          </div>
          <div className="capx-pm-practical-kpi">
            <span>Blocked</span>
            <strong>{viewModel.totals.blocked}</strong>
          </div>
          <div className="capx-pm-practical-kpi">
            <span>Tasks due</span>
            <strong>{viewModel.totals.dueThisWeek}</strong>
          </div>
          <div className="capx-pm-practical-kpi">
            <span>Missing documents</span>
            <strong>{viewModel.totals.missingDocuments}</strong>
          </div>
          <div className="capx-pm-practical-kpi">
            <span>Reports ready</span>
            <strong>{viewModel.totals.readyForReview}</strong>
          </div>
        </section>

        <section className="capx-pm-practical-toolbar" aria-label="Project list controls">
          <p>Filtered project list uses local mock state only.</p>
          <div className="capx-pm-practical-filters" aria-label="Project filters">
            {capxPmPracticalFilters.map((item) => (
              <span className="capx-pm-practical-filter" key={item.id}>
                <button type="button" aria-pressed={filter === item.id} onClick={() => setFilter(item.id)}>
                  {item.label}
                </button>
              </span>
            ))}
          </div>
        </section>

        <section className="capx-pm-practical-section" aria-labelledby="capx-pm-project-table-title">
          <div className="capx-pm-practical-section__head">
            <h2 id="capx-pm-project-table-title">Projects needing PM attention</h2>
            <p>{viewModel.projects.length} shown</p>
          </div>

          <div className="capx-pm-practical-table-wrap">
            <table className="capx-pm-practical-table">
              <thead>
                <tr>
                  <th scope="col">Project</th>
                  <th scope="col">Site / area</th>
                  <th scope="col">PM</th>
                  <th scope="col">Phase</th>
                  <th scope="col">Needs attention</th>
                  <th scope="col">Blockers</th>
                  <th scope="col">Tasks due</th>
                  <th scope="col">Missing documents</th>
                  <th scope="col">Budget & orders</th>
                  <th scope="col">Schedule</th>
                  <th scope="col">Supplier questions</th>
                  <th scope="col">Site handoffs</th>
                  <th scope="col">Report status</th>
                  <th scope="col">Last update</th>
                </tr>
              </thead>
              <tbody>
                {viewModel.projects.map((project) => (
                  <tr key={project.id}>
                    <td>
                      <Link to={buildCapxPmPracticalProjectHref(project)}>
                        {project.id} {project.name}
                      </Link>
                    </td>
                    <td>{project.siteArea}</td>
                    <td>{project.pm}</td>
                    <td>{project.phase}</td>
                    <td>
                      <CapxPmPracticalStatusChip status={project.status} /> {project.needsAttention}
                    </td>
                    <td>{project.blockers}</td>
                    <td>{project.tasksDue}</td>
                    <td>{project.missingDocuments}</td>
                    <td>{project.budgetOrders}</td>
                    <td>{project.schedule}</td>
                    <td>{project.supplierQuestions}</td>
                    <td>{project.siteHandoffs}</td>
                    <td>{project.reportStatus}</td>
                    <td>{project.lastUpdate}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          <div className="capx-pm-practical-mobile-list" data-testid="capx-pm-practical-index-mobile-cards">
            {viewModel.projects.map((project) => (
              <ProjectMobileCard project={project} key={project.id} />
            ))}
          </div>
        </section>
      </main>
    </CapxPmPracticalShell>
  );
}
