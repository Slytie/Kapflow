import { useState } from "react";
import { Link } from "react-router-dom";

import type {
  CapxPmFeDemoBudgetItem,
  CapxPmFeDemoDocument,
  CapxPmFeDemoMilestone,
  CapxPmFeDemoProject,
  CapxPmFeDemoSiteHandoff,
  CapxPmFeDemoStepId,
  CapxPmFeDemoSupplierQuestion
} from "@/pages/capx-pm-fe-demo/capxPmFeDemoTypes";
import {
  CapxPmV2DataGrid,
  CapxPmV2InfoGrid,
  CapxPmV2Section,
  CapxPmV2StatusPill,
  type CapxPmV2Column
} from "./CapxPmV2Shared";

function statusCell(status: CapxPmFeDemoDocument["status"]): JSX.Element {
  return <CapxPmV2StatusPill status={status} />;
}

function ownerDue(owner: string, due: string): JSX.Element {
  return (
    <span className="capx-pm-v2-tight-cell">
      <strong>{owner}</strong>
      <span>{due}</span>
    </span>
  );
}

export function CapxPmV2StepBody({
  project,
  stepId
}: {
  project: CapxPmFeDemoProject;
  stepId: CapxPmFeDemoStepId;
}): JSX.Element {
  switch (stepId) {
    case "project-setup":
      return <CapxPmV2ProjectSetupStep project={project} />;
    case "documents":
      return <CapxPmV2DocumentsStep project={project} />;
    case "timeline":
      return <CapxPmV2TimelineStep project={project} />;
    case "budget-orders":
      return <CapxPmV2BudgetOrdersStep project={project} />;
    case "supplier-questions":
      return <CapxPmV2SupplierQuestionsStep project={project} />;
    case "site-handoffs":
      return <CapxPmV2SiteHandoffsStep project={project} />;
    case "project-report":
      return <CapxPmV2ProjectReportStep project={project} />;
  }
}

function CapxPmV2ProjectSetupStep({ project }: { project: CapxPmFeDemoProject }): JSX.Element {
  const missingSetup = project.setupItems.filter((item) => item.status !== "on-track");
  const columns: CapxPmV2Column<CapxPmFeDemoDocument>[] = [
    { key: "item", header: "Setup item", render: (item) => item.name },
    { key: "used", header: "Used for", render: (item) => item.usedFor },
    { key: "status", header: "Status", render: (item) => statusCell(item.status) },
    { key: "owner", header: "Owner", render: (item) => item.owner },
    { key: "action", header: "Next action", render: (item) => item.action }
  ];

  return (
    <div className="capx-pm-v2-step" data-testid="capx-pm-v2-step-project-setup">
      <CapxPmV2Section
        eyebrow="Step 1"
        title="Project setup"
        note="Kickoff, takeover, and people involved before the PM treats the project as controlled."
      >
        <CapxPmV2InfoGrid
          items={[
            { label: "Kickoff / takeover", value: `${project.stage} handoff owned by ${project.pm}` },
            { label: "Sponsor", value: project.sponsor },
            { label: "Missing setup checklist", value: `${missingSetup.length} open item${missingSetup.length === 1 ? "" : "s"}` },
            { label: "Setup exception", value: missingSetup[0]?.detail ?? "No setup exception in this demo state" }
          ]}
        />
      </CapxPmV2Section>

      <CapxPmV2Section
        eyebrow="People"
        title="People involved"
        note="Who the PM should chase before the weekly update is trusted."
      >
        <div className="capx-pm-v2-card-strip">
          <article>
            <span>PM</span>
            <strong>{project.pm}</strong>
            <p>Owns weekly coordination and proof collection.</p>
          </article>
          <article>
            <span>Sponsor</span>
            <strong>{project.sponsor}</strong>
            <p>Owns budget and escalation decisions.</p>
          </article>
          <article>
            <span>Waiting on</span>
            <strong>{project.waitingOn}</strong>
            <p>Needs to clear the next PM action.</p>
          </article>
        </div>
      </CapxPmV2Section>

      <CapxPmV2Section eyebrow="Checklist" title="Setup exceptions and owners">
        <CapxPmV2DataGrid
          ariaLabel="Project setup checklist"
          columns={columns}
          getKey={(item) => item.id}
          mobileTestId="capx-pm-v2-mobile-project-setup"
          rows={project.setupItems}
        />
      </CapxPmV2Section>
    </div>
  );
}

function CapxPmV2DocumentsStep({ project }: { project: CapxPmFeDemoProject }): JSX.Element {
  const [selectedId, setSelectedId] = useState(project.documents[0]?.id ?? "");
  const selectedDocument = project.documents.find((document) => document.id === selectedId) ?? project.documents[0];
  const conflictCount = project.documents.filter(
    (document) => document.status === "waiting-supplier" || document.status === "proof-missing"
  ).length;
  const columns: CapxPmV2Column<CapxPmFeDemoDocument>[] = [
    { key: "document", header: "Document", render: (document) => document.name },
    { key: "type", header: "Type", render: (document) => document.type },
    { key: "date", header: "Version/date", render: (document) => document.versionDate },
    { key: "used", header: "Used for", render: (document) => document.usedFor },
    { key: "status", header: "Status", render: (document) => statusCell(document.status) },
    { key: "owner", header: "Owner", render: (document) => document.owner },
    {
      key: "action",
      header: "Action",
      render: (document) => (
        <button
          className="capx-pm-v2-inline-button"
          onClick={() => setSelectedId(document.id)}
          type="button"
        >
          {document.action}
        </button>
      )
    }
  ];

  return (
    <div className="capx-pm-v2-step" data-testid="capx-pm-v2-step-documents">
      <CapxPmV2Section
        eyebrow="Step 2"
        title="Documents"
        note="Document checklist, latest files, wrong-version conflicts, and missing proof."
      >
        <CapxPmV2InfoGrid
          items={[
            { label: "Latest files checked", value: project.documents.length },
            { label: "Version conflicts", value: conflictCount },
            { label: "Missing proof", value: project.documents.filter((document) => document.status === "proof-missing").length },
            { label: "Detail behavior", value: "Pick an action to preview local proof detail only" }
          ]}
        />
      </CapxPmV2Section>

      <CapxPmV2Section eyebrow="Files" title="Latest files table">
        <CapxPmV2DataGrid
          ariaLabel="Latest project files"
          columns={columns}
          getKey={(document) => document.id}
          mobileTestId="capx-pm-v2-mobile-documents"
          rows={project.documents}
        />
      </CapxPmV2Section>

      {selectedDocument ? (
        <CapxPmV2Section
          eyebrow="Local detail"
          title={selectedDocument.name}
          note="Simulated proof review; this does not update official project records."
        >
          <p className="capx-pm-v2-callout">{selectedDocument.detail}</p>
        </CapxPmV2Section>
      ) : null}
    </div>
  );
}

function CapxPmV2TimelineStep({ project }: { project: CapxPmFeDemoProject }): JSX.Element {
  const changedCount = project.milestones.filter((milestone) => milestone.changedSinceLastReport).length;
  const columns: CapxPmV2Column<CapxPmFeDemoMilestone>[] = [
    { key: "milestone", header: "Milestone", render: (milestone) => milestone.name },
    { key: "baseline", header: "Baseline", render: (milestone) => milestone.baselineDate },
    { key: "forecast", header: "Forecast", render: (milestone) => milestone.forecastDate },
    {
      key: "delta",
      header: "Delta",
      render: (milestone) => `${milestone.deltaDays > 0 ? "+" : ""}${milestone.deltaDays} days`
    },
    { key: "owner", header: "Owner", render: (milestone) => milestone.owner },
    { key: "reason", header: "Reason", render: (milestone) => milestone.reason },
    { key: "confidence", header: "Confidence", render: (milestone) => milestone.confidence }
  ];

  return (
    <div className="capx-pm-v2-step" data-testid="capx-pm-v2-step-timeline">
      <CapxPmV2Section
        action={
          <Link className="capx-pm-v2-button capx-pm-v2-button--secondary" to={`/demo/capx/pm-v2/projects/${project.id}/gantt`}>
            Open read-only Gantt
          </Link>
        }
        eyebrow="Step 3"
        title="Timeline"
        note="Milestone timeline, baseline versus forecast, slippage reasons, and confidence."
      >
        <CapxPmV2InfoGrid
          items={[
            { label: "Schedule movement", value: project.report.scheduleMovement },
            { label: "Changed since last report", value: `${changedCount} milestone${changedCount === 1 ? "" : "s"}` },
            { label: "Current schedule", value: project.schedule },
            { label: "Critical dependency", value: project.gantt.find((item) => item.criticalPath)?.blocker ?? "None" }
          ]}
        />
      </CapxPmV2Section>

      <CapxPmV2Section eyebrow="Plan movement" title="Baseline vs forecast table">
        <div className="capx-pm-v2-milestone-strip">
          {project.milestones.map((milestone) => (
            <article className={milestone.changedSinceLastReport ? "is-changed" : ""} key={milestone.id}>
              <span>{milestone.name}</span>
              <strong>{milestone.forecastDate}</strong>
              <p>
                {milestone.deltaDays > 0 ? "+" : ""}
                {milestone.deltaDays} days
              </p>
            </article>
          ))}
        </div>
        <CapxPmV2DataGrid
          ariaLabel="Timeline milestone movement"
          columns={columns}
          getKey={(milestone) => milestone.id}
          mobileTestId="capx-pm-v2-mobile-timeline"
          rows={project.milestones}
        />
      </CapxPmV2Section>
    </div>
  );
}

function CapxPmV2BudgetOrdersStep({ project }: { project: CapxPmFeDemoProject }): JSX.Element {
  const columns: CapxPmV2Column<CapxPmFeDemoBudgetItem>[] = [
    { key: "item", header: "Item", render: (item) => item.item },
    { key: "approved", header: "Approved amount", render: (item) => item.approvedAmount },
    { key: "current", header: "Current amount", render: (item) => item.currentAmount },
    { key: "delta", header: "Delta", render: (item) => item.delta },
    { key: "document", header: "Document", render: (item) => item.document },
    { key: "approval", header: "Approval needed", render: (item) => item.approvalNeeded },
    { key: "owner", header: "Owner / due", render: (item) => ownerDue(item.owner, item.due) },
    { key: "status", header: "Status", render: (item) => statusCell(item.status) }
  ];

  return (
    <div className="capx-pm-v2-step" data-testid="capx-pm-v2-step-budget-orders">
      <CapxPmV2Section
        eyebrow="Step 4"
        title="Budget & orders"
        note="Fictional demo values for what was approved, ordered, changed, or still waiting."
      >
        <CapxPmV2InfoGrid
          items={[
            { label: "Budget summary", value: project.budget },
            { label: "Budget movement", value: project.report.budgetMovement },
            { label: "Open approvals", value: project.budgetItems.filter((item) => item.approvalNeeded !== "No").length },
            { label: "Mismatch to resolve", value: "Quote, PO, and change-order chain must match before release" }
          ]}
        />
      </CapxPmV2Section>

      <CapxPmV2Section eyebrow="Order chain" title="Quote / PO / change-order timeline">
        <div className="capx-pm-v2-card-strip">
          {project.budgetItems.map((item) => (
            <article key={item.id}>
              <span>{item.document}</span>
              <strong>{item.delta}</strong>
              <p>{item.item}</p>
            </article>
          ))}
        </div>
        <CapxPmV2DataGrid
          ariaLabel="Budget and order changes"
          columns={columns}
          getKey={(item) => item.id}
          mobileTestId="capx-pm-v2-mobile-budget-orders"
          rows={project.budgetItems}
        />
      </CapxPmV2Section>
    </div>
  );
}

function CapxPmV2SupplierQuestionsStep({ project }: { project: CapxPmFeDemoProject }): JSX.Element {
  const columns: CapxPmV2Column<CapxPmFeDemoSupplierQuestion>[] = [
    { key: "question", header: "Supplier question", render: (item) => item.question },
    { key: "supplier", header: "Supplier", render: (item) => item.supplier },
    { key: "due", header: "Due", render: (item) => item.due },
    { key: "blocks", header: "Blocked work", render: (item) => item.blocks },
    { key: "proof", header: "Proof", render: (item) => item.proof },
    { key: "next", header: "Next action", render: (item) => item.nextAction },
    { key: "status", header: "Answer state", render: (item) => statusCell(item.status) }
  ];

  return (
    <div className="capx-pm-v2-step" data-testid="capx-pm-v2-step-supplier-questions">
      <CapxPmV2Section
        eyebrow="Step 5"
        title="Supplier questions"
        note="Open-points board for overdue answers, blocked work, answer state, and the next chase."
      >
        <CapxPmV2InfoGrid
          items={[
            { label: "Overdue answers", value: project.supplierQuestions.filter((item) => item.due === "Today").length },
            { label: "Blocked work", value: project.supplierQuestions.map((item) => item.blocks).join(", ") },
            { label: "Accepted / rejected", value: "Answers stay open until the PM can use them for the next task" },
            { label: "Next action", value: project.supplierQuestions[0]?.nextAction ?? "No supplier action open" }
          ]}
        />
      </CapxPmV2Section>

      <CapxPmV2Section eyebrow="Open points" title="Supplier open-points board">
        <CapxPmV2DataGrid
          ariaLabel="Supplier open questions"
          columns={columns}
          getKey={(item) => item.id}
          mobileTestId="capx-pm-v2-mobile-supplier-questions"
          rows={project.supplierQuestions}
        />
      </CapxPmV2Section>
    </div>
  );
}

function CapxPmV2SiteHandoffsStep({ project }: { project: CapxPmFeDemoProject }): JSX.Element {
  const columns: CapxPmV2Column<CapxPmFeDemoSiteHandoff>[] = [
    { key: "dependency", header: "Dependency", render: (item) => item.dependency },
    { key: "from", header: "Needed from", render: (item) => item.neededFrom },
    { key: "required", header: "Required by", render: (item) => item.requiredBy },
    { key: "provided", header: "Provided", render: (item) => item.provided },
    { key: "accepted", header: "Accepted by", render: (item) => item.acceptedBy },
    { key: "blocks", header: "Blocks", render: (item) => item.blocks },
    { key: "proof", header: "Proof", render: (item) => item.proof },
    { key: "next", header: "Next action", render: (item) => item.nextAction },
    { key: "status", header: "Status", render: (item) => statusCell(item.status) }
  ];

  return (
    <div className="capx-pm-v2-step" data-testid="capx-pm-v2-step-site-handoffs">
      <CapxPmV2Section
        eyebrow="Step 6"
        title="Site handoffs"
        note="Site readiness board for production, engineering, quality, maintenance, and site owner dependencies."
      >
        <CapxPmV2InfoGrid
          items={[
            { label: "Production acceptance", value: project.siteHandoffs[0]?.acceptedBy ?? "Not accepted" },
            { label: "Quality check", value: project.siteHandoffs[1]?.acceptedBy ?? "Open" },
            { label: "Shutdown / access window", value: project.siteHandoffs[0]?.provided ?? "No window provided" },
            { label: "PM delivery", value: "PM can request the handoff, site owner must accept it separately" }
          ]}
        />
      </CapxPmV2Section>

      <CapxPmV2Section eyebrow="Readiness" title="Required, provided, and accepted">
        <CapxPmV2DataGrid
          ariaLabel="Site handoff dependencies"
          columns={columns}
          getKey={(item) => item.id}
          mobileTestId="capx-pm-v2-mobile-site-handoffs"
          rows={project.siteHandoffs}
        />
      </CapxPmV2Section>
    </div>
  );
}

function CapxPmV2ProjectReportStep({ project }: { project: CapxPmFeDemoProject }): JSX.Element {
  return (
    <div className="capx-pm-v2-step" data-testid="capx-pm-v2-step-project-report">
      <CapxPmV2Section
        eyebrow="Step 7"
        title="Project report"
        note="Report readiness, cautious PM update text, proof used, and caveats before sharing."
      >
        <CapxPmV2InfoGrid
          items={[
            { label: "Readiness", value: project.report.readiness },
            { label: "Current status", value: project.report.currentStatus },
            { label: "Schedule movement", value: project.report.scheduleMovement },
            { label: "Budget movement", value: project.report.budgetMovement },
            { label: "Quality / site confirmation", value: project.report.qualitySiteConfirmation },
            { label: "Supplier / site dependencies", value: project.report.supplierSiteDependencies },
            { label: "Escalation needed", value: project.report.escalationNeeded }
          ]}
        />
      </CapxPmV2Section>

      <div className="capx-pm-v2-report-grid">
        <CapxPmV2Section eyebrow="Changes" title="What changed this week">
          <ul className="capx-pm-v2-list">
            {project.report.changesThisWeek.map((change) => (
              <li key={change}>{change}</li>
            ))}
          </ul>
        </CapxPmV2Section>

        <CapxPmV2Section eyebrow="Blockers" title="Top blockers">
          <ul className="capx-pm-v2-list">
            {project.report.topBlockers.map((blocker) => (
              <li key={blocker}>{blocker}</li>
            ))}
          </ul>
        </CapxPmV2Section>
      </div>

      <CapxPmV2Section eyebrow="PM text" title="Suggested PM update">
        <blockquote>{project.report.suggestedUpdate}</blockquote>
      </CapxPmV2Section>

      <CapxPmV2Section eyebrow="Proof and caveats" title="Do not overstate the update">
        <div className="capx-pm-v2-report-grid">
          <article>
            <h3>Proof used</h3>
            <ul className="capx-pm-v2-list">
              {project.report.proofUsed.map((proof) => (
                <li key={proof}>{proof}</li>
              ))}
            </ul>
          </article>
          <article>
            <h3>Caveats</h3>
            <ul className="capx-pm-v2-list">
              {project.report.caveats.map((caveat) => (
                <li key={caveat}>{caveat}</li>
              ))}
            </ul>
          </article>
        </div>
      </CapxPmV2Section>
    </div>
  );
}
