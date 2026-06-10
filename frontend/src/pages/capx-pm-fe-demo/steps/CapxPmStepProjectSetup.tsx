import { CapxPmFeResponsiveTable, CapxPmFeSection, CapxPmFeStatusChip, type CapxPmFeColumn } from "../CapxPmFeDemoComponents";
import type { CapxPmFeDemoDocument, CapxPmFeDemoProject } from "../capxPmFeDemoTypes";

export function CapxPmStepProjectSetup({ project }: { project: CapxPmFeDemoProject }): JSX.Element {
  const columns: Array<CapxPmFeColumn<CapxPmFeDemoDocument>> = [
    { key: "item", label: "Setup item", render: (item) => item.name },
    { key: "owner", label: "Owner", render: (item) => item.owner },
    { key: "used", label: "Used for", render: (item) => item.usedFor },
    { key: "state", label: "Status", render: (item) => <CapxPmFeStatusChip status={item.status} /> },
    { key: "action", label: "Action", render: (item) => item.action }
  ];

  return (
    <div data-testid="capx-pm-fe-step-project-setup">
      <CapxPmFeSection title="Kickoff and takeover status" note="PM ownership, sponsor path, and working folder">
        <div className="capx-pm-fe-card-grid">
          <article className="capx-pm-fe-card">
            <span>PM</span>
            <strong>{project.pm}</strong>
            <p>Owns daily project chasing and report readiness.</p>
          </article>
          <article className="capx-pm-fe-card">
            <span>Sponsor</span>
            <strong>{project.sponsor}</strong>
            <p>Needed for budget and escalation decisions.</p>
          </article>
          <article className="capx-pm-fe-card">
            <span>Current setup gap</span>
            <strong>Document access</strong>
            <p>Quality owner still needs access to the latest checklist.</p>
          </article>
        </div>
      </CapxPmFeSection>

      <CapxPmFeSection title="Missing setup checklist" note="Every open item shows an owner and next action">
        <CapxPmFeResponsiveTable
          columns={columns}
          rows={project.setupItems}
          testId="capx-pm-fe-setup-mobile-cards"
        />
      </CapxPmFeSection>
    </div>
  );
}
