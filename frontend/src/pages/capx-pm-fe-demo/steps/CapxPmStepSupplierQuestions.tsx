import { CapxPmFeResponsiveTable, CapxPmFeSection, CapxPmFeStatusChip, type CapxPmFeColumn } from "../CapxPmFeDemoComponents";
import type { CapxPmFeDemoProject, CapxPmFeDemoSupplierQuestion } from "../capxPmFeDemoTypes";

export function CapxPmStepSupplierQuestions({ project }: { project: CapxPmFeDemoProject }): JSX.Element {
  const columns: Array<CapxPmFeColumn<CapxPmFeDemoSupplierQuestion>> = [
    { key: "question", label: "Supplier question", render: (item) => item.question },
    { key: "supplier", label: "Supplier", render: (item) => item.supplier },
    { key: "due", label: "Due", render: (item) => item.due },
    { key: "blocks", label: "Blocks", render: (item) => item.blocks },
    { key: "proof", label: "Proof", render: (item) => item.proof },
    { key: "next", label: "Next action", render: (item) => item.nextAction },
    { key: "status", label: "Status", render: (item) => <CapxPmFeStatusChip status={item.status} /> }
  ];

  return (
    <div data-testid="capx-pm-fe-step-supplier-questions">
      <CapxPmFeSection title="Supplier open points" note="Overdue answers and blocked work">
        <div className="capx-pm-fe-card-grid">
          {project.supplierQuestions.map((question) => (
            <article className="capx-pm-fe-card" key={question.id}>
              <span>{question.supplier}</span>
              <strong>{question.blocks}</strong>
              <p>{question.nextAction}</p>
              <CapxPmFeStatusChip status={question.status} />
            </article>
          ))}
        </div>
      </CapxPmFeSection>

      <CapxPmFeSection title="Supplier question register" note="Question, due date, blocker, proof, and next action">
        <CapxPmFeResponsiveTable
          columns={columns}
          rows={project.supplierQuestions}
          testId="capx-pm-fe-supplier-mobile-cards"
        />
      </CapxPmFeSection>
    </div>
  );
}
