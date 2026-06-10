import { CapxPmFeSection, CapxPmFeStatusChip } from "../CapxPmFeDemoComponents";
import type { CapxPmFeDemoProject } from "../capxPmFeDemoTypes";

export function CapxPmStepProjectReport({ project }: { project: CapxPmFeDemoProject }): JSX.Element {
  const report = project.report;

  return (
    <div data-testid="capx-pm-fe-step-project-report">
      <CapxPmFeSection title="Report readiness" note="Can the PM send a credible update?">
        <div className="capx-pm-fe-report-grid">
          <article className="capx-pm-fe-card capx-pm-fe-card--alert">
            <span>Readiness</span>
            <strong>{report.readiness}</strong>
            <CapxPmFeStatusChip status={report.status} />
          </article>
          <article className="capx-pm-fe-card">
            <span>Schedule movement</span>
            <strong>{report.scheduleMovement}</strong>
          </article>
          <article className="capx-pm-fe-card">
            <span>Budget movement</span>
            <strong>{report.budgetMovement}</strong>
          </article>
          <article className="capx-pm-fe-card">
            <span>Quality / site</span>
            <strong>{report.qualitySiteConfirmation}</strong>
          </article>
        </div>
      </CapxPmFeSection>

      <CapxPmFeSection title="Suggested PM update" note="Mock copy for feedback review">
        <blockquote className="capx-pm-fe-report-quote">{report.suggestedUpdate}</blockquote>
      </CapxPmFeSection>

      <CapxPmFeSection title="What changed this week" note="Schedule, budget, supplier, and site movement">
        <div className="capx-pm-fe-two-column">
          <article>
            <h3>Changes</h3>
            <ul>
              {report.changesThisWeek.map((change) => (
                <li key={change}>{change}</li>
              ))}
            </ul>
          </article>
          <article>
            <h3>Top blockers</h3>
            <ul>
              {report.topBlockers.map((blocker) => (
                <li key={blocker}>{blocker}</li>
              ))}
            </ul>
          </article>
          <article>
            <h3>Proof used</h3>
            <ul>
              {report.proofUsed.map((proof) => (
                <li key={proof}>{proof}</li>
              ))}
            </ul>
          </article>
          <article>
            <h3>Caveats</h3>
            <ul>
              {report.caveats.map((caveat) => (
                <li key={caveat}>{caveat}</li>
              ))}
            </ul>
          </article>
        </div>
      </CapxPmFeSection>
    </div>
  );
}
