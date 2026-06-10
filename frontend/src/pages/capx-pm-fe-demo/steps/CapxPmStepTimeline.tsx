import { Link } from "react-router-dom";

import { CapxPmFeResponsiveTable, CapxPmFeSection, CapxPmFeStatusChip, type CapxPmFeColumn } from "../CapxPmFeDemoComponents";
import type { CapxPmFeDemoMilestone, CapxPmFeDemoProject } from "../capxPmFeDemoTypes";
import { buildCapxPmFeDemoGanttHref } from "../capxPmFeDemoViewModels";

export function CapxPmStepTimeline({ project }: { project: CapxPmFeDemoProject }): JSX.Element {
  const columns: Array<CapxPmFeColumn<CapxPmFeDemoMilestone>> = [
    { key: "name", label: "Milestone", render: (item) => item.name },
    { key: "baseline", label: "Baseline date", render: (item) => item.baselineDate },
    { key: "forecast", label: "Forecast date", render: (item) => item.forecastDate },
    { key: "delta", label: "Delta", render: (item) => `${item.deltaDays > 0 ? "+" : ""}${item.deltaDays} days` },
    { key: "owner", label: "Owner", render: (item) => item.owner },
    { key: "reason", label: "Reason", render: (item) => item.reason },
    { key: "confidence", label: "Confidence", render: (item) => item.confidence },
    { key: "state", label: "Status", render: (item) => <CapxPmFeStatusChip status={item.status} /> }
  ];

  return (
    <div data-testid="capx-pm-fe-step-timeline">
      <CapxPmFeSection title="Milestone movement" note="Changed since last report is highlighted">
        <div className="capx-pm-fe-timeline-strip" aria-label="Milestone timeline">
          {project.milestones.map((milestone) => (
            <article className={milestone.changedSinceLastReport ? "is-changed" : ""} key={milestone.id}>
              <span>{milestone.name}</span>
              <strong>{milestone.forecastDate}</strong>
              <p>{milestone.reason}</p>
            </article>
          ))}
        </div>
        <Link className="capx-pm-fe-button capx-pm-fe-button--secondary" to={buildCapxPmFeDemoGanttHref(project.id)}>
          Open Project Gantt
        </Link>
      </CapxPmFeSection>

      <CapxPmFeSection title="Baseline vs forecast" note="What moved, why, and who owns the next check">
        <CapxPmFeResponsiveTable columns={columns} rows={project.milestones} testId="capx-pm-fe-timeline-mobile-cards" />
      </CapxPmFeSection>
    </div>
  );
}
