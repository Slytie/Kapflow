import { Link } from "react-router-dom";

import {
  CapxPmFeMetricCard,
  CapxPmFeResponsiveTable,
  CapxPmFeSection,
  CapxPmFeStatusChip,
  type CapxPmFeColumn
} from "./CapxPmFeDemoComponents";
import type { CapxPmFeDemoProject } from "./capxPmFeDemoTypes";
import { buildCapxPmFeDemoProjectHref, buildCapxPmFeDemoProjectsViewModel } from "./capxPmFeDemoViewModels";

export function CapxPmProjectsPage(): JSX.Element {
  const viewModel = buildCapxPmFeDemoProjectsViewModel();
  const columns: Array<CapxPmFeColumn<CapxPmFeDemoProject>> = [
    {
      key: "project",
      label: "Project",
      render: (project) => (
        <Link className="capx-pm-fe-table-link" to={buildCapxPmFeDemoProjectHref(project.id)}>
          {project.id} {project.name}
        </Link>
      )
    },
    { key: "next", label: "Next action", render: (project) => project.nextAction.title },
    { key: "due", label: "Due", render: (project) => project.nextAction.due },
    { key: "health", label: "Health", render: (project) => <CapxPmFeStatusChip status={project.health} /> },
    { key: "stage", label: "Stage", render: (project) => project.stage },
    { key: "schedule", label: "Schedule", render: (project) => project.schedule },
    { key: "budget", label: "Budget", render: (project) => project.budget },
    { key: "quality", label: "Quality", render: (project) => project.quality },
    { key: "waiting", label: "Waiting on", render: (project) => project.waitingOn },
    { key: "docs", label: "Docs", render: (project) => project.docs },
    { key: "escalation", label: "Escalation", render: (project) => project.escalation },
    { key: "last", label: "Last update", render: (project) => project.lastUpdate }
  ];

  return (
    <main className="capx-pm-fe-page" data-testid="capx-pm-fe-projects-page">
      <section className="capx-pm-fe-hero">
        <div>
          <p className="capx-pm-fe-eyebrow">My CAPX Projects</p>
          <h2>Open the project that needs PM attention first</h2>
          <p>
            Sorted by blocker pressure, due action, schedule movement, missing proof, and report readiness. All rows use
            local fake project data.
          </p>
        </div>
        <div className="capx-pm-fe-hero__metrics">
          <CapxPmFeMetricCard label="Projects" value={viewModel.totals.projects} />
          <CapxPmFeMetricCard label="Blocked" value={viewModel.totals.blocked} tone="alert" />
          <CapxPmFeMetricCard label="Waiting" value={viewModel.totals.waiting} />
          <CapxPmFeMetricCard label="Ready" value={viewModel.totals.ready} tone="ready" />
          <CapxPmFeMetricCard label="Due today" value={viewModel.totals.dueToday} />
        </div>
      </section>

      <CapxPmFeSection title="Attention-first project list" note={`${viewModel.projects.length} fake projects`}>
        <CapxPmFeResponsiveTable
          columns={columns}
          rows={viewModel.projects}
          testId="capx-pm-fe-project-mobile-cards"
        />
      </CapxPmFeSection>
    </main>
  );
}
