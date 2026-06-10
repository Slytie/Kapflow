import { CapxPmFeResponsiveTable, CapxPmFeSection, CapxPmFeStatusChip, type CapxPmFeColumn } from "../CapxPmFeDemoComponents";
import type { CapxPmFeDemoProject, CapxPmFeDemoSiteHandoff } from "../capxPmFeDemoTypes";

export function CapxPmStepSiteHandoffs({ project }: { project: CapxPmFeDemoProject }): JSX.Element {
  const columns: Array<CapxPmFeColumn<CapxPmFeDemoSiteHandoff>> = [
    { key: "dependency", label: "Dependency", render: (item) => item.dependency },
    { key: "from", label: "Needed from", render: (item) => item.neededFrom },
    { key: "required", label: "Required by", render: (item) => item.requiredBy },
    { key: "provided", label: "Provided", render: (item) => item.provided },
    { key: "accepted", label: "Accepted by", render: (item) => item.acceptedBy },
    { key: "blocks", label: "Blocks", render: (item) => item.blocks },
    { key: "proof", label: "Proof", render: (item) => item.proof },
    { key: "next", label: "Next action", render: (item) => item.nextAction },
    { key: "status", label: "Status", render: (item) => <CapxPmFeStatusChip status={item.status} /> }
  ];

  return (
    <div data-testid="capx-pm-fe-step-site-handoffs">
      <CapxPmFeSection title="Site readiness board" note="Production, quality, maintenance, and site owner dependencies">
        <div className="capx-pm-fe-card-grid">
          <article className="capx-pm-fe-card capx-pm-fe-card--alert">
            <span>Shutdown window</span>
            <strong>Not accepted</strong>
            <p>Installation date remains low confidence until Production accepts a window.</p>
          </article>
          <article className="capx-pm-fe-card">
            <span>Quality check</span>
            <strong>Drafted</strong>
            <p>Quality Lead still owes acceptance of required checks.</p>
          </article>
          <article className="capx-pm-fe-card">
            <span>Maintenance</span>
            <strong>Training proposed</strong>
            <p>Training slot must follow the new installation forecast.</p>
          </article>
        </div>
      </CapxPmFeSection>

      <CapxPmFeSection title="Site handoff register" note="Required, provided, accepted, blocked, and proof needed">
        <CapxPmFeResponsiveTable columns={columns} rows={project.siteHandoffs} testId="capx-pm-fe-site-mobile-cards" />
      </CapxPmFeSection>
    </div>
  );
}
