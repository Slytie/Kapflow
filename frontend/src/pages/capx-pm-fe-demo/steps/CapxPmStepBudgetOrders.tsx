import { CapxPmFeMetricCard, CapxPmFeResponsiveTable, CapxPmFeSection, CapxPmFeStatusChip, type CapxPmFeColumn } from "../CapxPmFeDemoComponents";
import type { CapxPmFeDemoBudgetItem, CapxPmFeDemoProject } from "../capxPmFeDemoTypes";

export function CapxPmStepBudgetOrders({ project }: { project: CapxPmFeDemoProject }): JSX.Element {
  const columns: Array<CapxPmFeColumn<CapxPmFeDemoBudgetItem>> = [
    { key: "item", label: "Item", render: (item) => item.item },
    { key: "approved", label: "Approved amount", render: (item) => item.approvedAmount },
    { key: "current", label: "Current amount", render: (item) => item.currentAmount },
    { key: "delta", label: "Delta", render: (item) => item.delta },
    { key: "document", label: "Document", render: (item) => item.document },
    { key: "approval", label: "Approval needed", render: (item) => item.approvalNeeded },
    { key: "owner", label: "Owner", render: (item) => item.owner },
    { key: "due", label: "Due", render: (item) => item.due },
    { key: "status", label: "Status", render: (item) => <CapxPmFeStatusChip status={item.status} /> }
  ];

  return (
    <div data-testid="capx-pm-fe-step-budget-orders">
      <CapxPmFeSection title="Budget summary" note="Fictional demo amounts for design review only">
        <div className="capx-pm-fe-hero__metrics">
          <CapxPmFeMetricCard label="Budget movement" value={project.budget} tone="alert" />
          <CapxPmFeMetricCard label="Approval owner" value="Operations Sponsor" />
          <CapxPmFeMetricCard label="Order state" value="Hold for proof" />
        </div>
      </CapxPmFeSection>

      <CapxPmFeSection title="Quote, PO, and change order review" note="What changed and who must approve">
        <CapxPmFeResponsiveTable columns={columns} rows={project.budgetItems} testId="capx-pm-fe-budget-mobile-cards" />
      </CapxPmFeSection>
    </div>
  );
}
