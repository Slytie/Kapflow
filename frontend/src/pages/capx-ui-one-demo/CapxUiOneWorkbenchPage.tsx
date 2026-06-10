import "./capxUiOne.css";

import { useMemo, useState } from "react";
import { Link, Navigate, Route, Routes, useLocation, useParams } from "react-router-dom";

import {
  capxUiOneAcceptanceCriteria,
  capxUiOneAiJobs,
  capxUiOneAuditEvents,
  capxUiOneCommandReceipts,
  capxUiOneDraftOutputs,
  capxUiOneEvidence,
  capxUiOnePhases,
  capxUiOneProject,
  capxUiOneProjects,
  capxUiOneReports,
  capxUiOneSnapshot,
  capxUiOneTasks,
  capxUiOneWorkpageProjections,
  getCapxUiOneEvidence,
  getCapxUiOnePhase,
  getCapxUiOnePriorityCount,
  getCapxUiOneProject,
  getCapxUiOneTask,
  type CapxUiOneEvidence,
  type CapxUiOneProject,
  type CapxUiOneTask
} from "./capxUiOneData";

type CommandTone = "accepted" | "rejected";

interface CommandReceipt {
  command: string;
  detail: string;
  outcome: CommandTone;
  target: string;
  policyResult?: string;
  nextRequiredAction?: string;
  taskId?: string;
}

type DrawerFocus = { kind: "task"; taskId: string } | { kind: "evidence"; evidenceId: string };

interface WorkbenchChildProps {
  onCommand: (receipt: CommandReceipt) => void;
  onFocusEvidence?: (evidenceId: string) => void;
  onFocusTask?: (taskId: string) => void;
}

const shellNavItems = [
  { label: "Home", href: "/demo/capx/ui-one/home" },
  { label: "Work Queue", href: "/demo/capx/ui-one/queue" },
  { label: "Projects", href: "/demo/capx/ui-one/projects" },
  { label: "Reports", href: "/demo/capx/ui-one/reports" },
  { label: "Admin", href: "/demo/capx/ui-one/admin" }
];

const projectNavItems = [
  { label: "State Snapshot", href: "/demo/capx/ui-one/projects/k12-packaging-line-upgrade/overview" },
  { label: "Intake Workspace", href: "/demo/capx/ui-one/projects/k12-packaging-line-upgrade/phases/opportunity" },
  { label: "Evidence Library", href: "/demo/capx/ui-one/projects/k12-packaging-line-upgrade/evidence" },
  { label: "Structuring Review", href: "/demo/capx/ui-one/projects/k12-packaging-line-upgrade/structuring" },
  { label: "Tasks & Approvals", href: "/demo/capx/ui-one/projects/k12-packaging-line-upgrade/tasks" },
  { label: "Reports", href: "/demo/capx/ui-one/projects/k12-packaging-line-upgrade/reports" },
  { label: "Audit", href: "/demo/capx/ui-one/projects/k12-packaging-line-upgrade/audit" }
];

function getProjectIdFromPath(pathname: string): string | undefined {
  const match = pathname.match(/\/projects\/([^/]+)/);
  return match?.[1];
}

function linkClass(pathname: string, href: string): string {
  return pathname === href || pathname.startsWith(`${href}/`) ? "is-active" : "";
}

function buildReceipt(
  command: string,
  target: string,
  outcome: CommandTone,
  detail: string,
  taskId?: string,
  policyResult?: string,
  nextRequiredAction?: string
): CommandReceipt {
  return {
    command,
    detail,
    nextRequiredAction,
    outcome,
    policyResult,
    target,
    taskId
  };
}

function buildFixtureReceipt(receiptId: string): CommandReceipt {
  const receipt = capxUiOneCommandReceipts.find((item) => item.id === receiptId) ?? capxUiOneCommandReceipts[0];

  return {
    command: receipt.command,
    detail: receipt.detail,
    nextRequiredAction: receipt.nextRequiredAction,
    outcome: receipt.outcome === "accepted" ? "accepted" : "rejected",
    policyResult: receipt.policyResult,
    target: receipt.target,
    taskId: receipt.taskId
  };
}

function stateTone(state: string): string {
  return state.toLowerCase().replace(/\s+/g, "-");
}

function CapxUiOneTopBar(): JSX.Element {
  const [searchValue, setSearchValue] = useState("");

  return (
    <header className="capx-ui-one-topbar" aria-label="UI-One top bar">
      <Link aria-label="UI-One CAPEX Workbench" className="capx-ui-one-topbar__brand" to="/demo/capx/ui-one/home">
        <span>UI-One</span>
        <strong>CAPEX Workbench</strong>
      </Link>
      <label className="capx-ui-one-search">
        <span>Search</span>
        <input
          aria-label="Global search"
          onChange={(event) => setSearchValue(event.target.value)}
          placeholder="Project, task, artifact, supplier..."
          type="search"
          value={searchValue}
        />
      </label>
      <div className="capx-ui-one-topbar__meta" aria-label="Tenant role and user context">
        <span>Tenant: DemoCo</span>
        <span>Role: Project manager</span>
        <span>Notifications: 6</span>
        <strong>Lyra PM</strong>
      </div>
    </header>
  );
}

function CapxUiOneSideNav(): JSX.Element {
  const { pathname } = useLocation();

  return (
    <nav className="capx-ui-one-side" aria-label="UI-One navigation">
      <div className="capx-ui-one-side__primary">
        {shellNavItems.map((item) => (
          <Link className={linkClass(pathname, item.href)} key={item.href} to={item.href}>
            {item.label}
          </Link>
        ))}
      </div>
      <section aria-label="Project routes">
        <p>Project</p>
        {projectNavItems.map((item) => (
          <Link className={linkClass(pathname, item.href)} key={item.href} to={item.href}>
            {item.label}
          </Link>
        ))}
      </section>
      <Link className="capx-ui-one-side__back" to="/demo/capx/ui-versions">
        A/B/C comparison
      </Link>
    </nav>
  );
}

function CapxUiOneProjectContextBar({ project }: { project: CapxUiOneProject }): JSX.Element {
  return (
    <section className="capx-ui-one-context" aria-label="Project context">
      <div className="capx-ui-one-context__identity">
        <p>Project</p>
        <h1>{project.name}</h1>
        <span>{project.site}</span>
      </div>
      <div>
        <p>Lifecycle</p>
        <strong>{project.lifecycleContext}</strong>
      </div>
      <div>
        <p>Snapshot</p>
        <strong>{project.snapshotId}</strong>
        <span>{project.snapshotFreshness}</span>
      </div>
      <div>
        <p>Forecastability</p>
        <strong>{project.forecastability}</strong>
        <span>{[...project.staleBadges, ...project.blockedBadges].join(" / ")}</span>
      </div>
    </section>
  );
}

function CapxUiOneLifecycleRibbon(): JSX.Element {
  return (
    <section className="capx-ui-one-ribbon" aria-label="Ten stage lifecycle context">
      {capxUiOnePhases.map((phase) => (
        <Link className={`is-${phase.state}`} key={phase.phaseKey} to={phase.route}>
          <span>{phase.key}</span>
          <strong>{phase.name}</strong>
          <small>{phase.state}</small>
        </Link>
      ))}
    </section>
  );
}

function CapxUiOneStatusPill({ label, tone }: { label: string; tone: string }): JSX.Element {
  return (
    <span className={`capx-ui-one-pill is-${tone}`} data-testid={`capx-ui-one-pill-${tone}`}>
      {label}
    </span>
  );
}

function CapxUiOneCommandButton({
  children,
  onCommand,
  receipt,
  variant = "accepted"
}: {
  children: string;
  onCommand: (receipt: CommandReceipt) => void;
  receipt: CommandReceipt;
  variant?: CommandTone;
}): JSX.Element {
  return (
    <button
      className={`capx-ui-one-command is-${variant}`}
      onClick={() => onCommand(receipt)}
      type="button"
    >
      {children}
    </button>
  );
}

function CapxUiOneMetricStrip(): JSX.Element {
  return (
    <section className="capx-ui-one-metrics" aria-label="Role dashboard metrics">
      <div>
        <strong>{getCapxUiOnePriorityCount("P0")}</strong>
        <span>P0 decisions</span>
      </div>
      <div>
        <strong>{capxUiOneEvidence.filter((item) => item.status === "Missing").length}</strong>
        <span>missing evidence</span>
      </div>
      <div>
        <strong>{capxUiOneReports.filter((report) => !report.official).length}</strong>
        <span>draft reports</span>
      </div>
      <div>
        <strong>{capxUiOneAiJobs.filter((job) => job.state === "Blocked" || job.state === "Queued").length}</strong>
        <span>guarded AI jobs</span>
      </div>
    </section>
  );
}

function CapxUiOneTaskRow({
  onFocusTask,
  task
}: {
  onFocusTask?: (taskId: string) => void;
  task: CapxUiOneTask;
}): JSX.Element {
  return (
    <Link className="capx-ui-one-task-row" onClick={() => onFocusTask?.(task.id)} to={task.route}>
      <span>
        <strong>{task.id}</strong>
        <small>{task.type}</small>
      </span>
      <span>{task.title}</span>
      <span>{task.owner}</span>
      <CapxUiOneStatusPill label={task.state} tone={stateTone(task.state)} />
      <span>{task.basis}</span>
    </Link>
  );
}

function CapxUiOneTaskTable({
  onFocusTask,
  tasks = capxUiOneTasks
}: {
  onFocusTask?: (taskId: string) => void;
  tasks?: CapxUiOneTask[];
}): JSX.Element {
  return (
    <div className="capx-ui-one-task-table" role="table" aria-label="Role scoped work queue">
      <div role="row">
        <span role="columnheader">ID</span>
        <span role="columnheader">Decision or gap</span>
        <span role="columnheader">Owner</span>
        <span role="columnheader">State</span>
        <span role="columnheader">Basis</span>
      </div>
      {tasks.map((task) => (
        <CapxUiOneTaskRow key={task.id} onFocusTask={onFocusTask} task={task} />
      ))}
    </div>
  );
}

function CapxUiOneHomeView({ onCommand, onFocusTask }: WorkbenchChildProps): JSX.Element {
  const portfolioExceptions = capxUiOneProjects.filter(
    (project) => project.forecastability !== "Forecastable" || project.blockedBadges.length > 0
  );

  return (
    <div className="capx-ui-one-view" data-testid="capx-ui-one-home">
      <div className="capx-ui-one-view__heading">
        <p>Role Home / Dashboard</p>
        <h2>What needs attention today?</h2>
      </div>
      <CapxUiOneMetricStrip />
      <section className="capx-ui-one-split">
        <div className="capx-ui-one-panel">
          <div className="capx-ui-one-panel__title">
            <p>Work queue</p>
            <h3>Assigned decisions and evidence gaps</h3>
          </div>
          <CapxUiOneTaskTable onFocusTask={onFocusTask} tasks={capxUiOneTasks.slice(0, 3)} />
        </div>
        <div className="capx-ui-one-panel">
          <div className="capx-ui-one-panel__title">
            <p>Portfolio exceptions</p>
            <h3>Blocked or stale projects</h3>
          </div>
          <div className="capx-ui-one-project-list">
            {portfolioExceptions.map((project) => (
              <Link key={project.id} to={project.route}>
                <strong>{project.name}</strong>
                <span>{project.snapshotId}</span>
                <small>{[...project.staleBadges, ...project.blockedBadges].join(" / ")}</small>
              </Link>
            ))}
          </div>
          <CapxUiOneCommandButton
            onCommand={onCommand}
            receipt={buildReceipt(
              "publish_dashboard_status_as_truth",
              capxUiOneProject.snapshotId,
              "rejected",
              "Dashboard status is a projection. Open the governed K12 snapshot and submit a bound command instead.",
              undefined,
              "projection_only",
              "Use the governed snapshot workpage and a current basis token."
            )}
            variant="rejected"
          >
            Publish dashboard status
          </CapxUiOneCommandButton>
        </div>
      </section>
    </div>
  );
}

function CapxUiOneQueueView({ onCommand, onFocusTask }: WorkbenchChildProps): JSX.Element {
  return (
    <div className="capx-ui-one-view" data-testid="capx-ui-one-queue">
      <div className="capx-ui-one-view__heading">
        <p>Work Queue / Inbox</p>
        <h2>Bound decisions, approvals, waivers, and evidence tasks</h2>
      </div>
      <div className="capx-ui-one-panel">
        <CapxUiOneTaskTable onFocusTask={onFocusTask} />
      </div>
      <section className="capx-ui-one-command-band" aria-label="Queue actions">
        <CapxUiOneCommandButton
          onCommand={onCommand}
          receipt={buildReceipt(
            "request_revalidation",
            capxUiOneSnapshot.basisVersion,
            "accepted",
            "Revalidation request accepted for the stale K12 snapshot. It remains stale until the bound evidence task closes.",
            "task-002",
            "revalidation_requested",
            "Review AB-02 responsibility wording and attach current measurement evidence."
          )}
        >
          Request revalidation
        </CapxUiOneCommandButton>
        <CapxUiOneCommandButton
          onCommand={onCommand}
          receipt={buildReceipt(
            "bulk_approve_without_evidence",
            "queue:role-pm",
            "rejected",
            "Bulk approval is blocked because each task needs visible evidence, basis version, and policy result.",
            undefined,
            "missing_bound_evidence",
            "Open the blocked K12 task and resolve its evidence requirements one by one."
          )}
          variant="rejected"
        >
          Bulk approve
        </CapxUiOneCommandButton>
      </section>
    </div>
  );
}

function CapxUiOneProjectsView(): JSX.Element {
  return (
    <div className="capx-ui-one-view" data-testid="capx-ui-one-projects">
      <div className="capx-ui-one-view__heading">
        <p>Project List</p>
        <h2>Role-scoped CAPEX projects</h2>
      </div>
      <section className="capx-ui-one-project-grid" aria-label="CAPEX project list">
        {capxUiOneProjects.map((project) => (
          <Link key={project.id} to={project.route}>
            <span>{project.sponsor}</span>
            <strong>{project.name}</strong>
            <small>{project.site}</small>
            <div>
              <CapxUiOneStatusPill label={project.forecastability} tone={stateTone(project.forecastability)} />
              {project.blockedBadges.map((badge) => (
                <CapxUiOneStatusPill key={badge} label={badge} tone="blocked" />
              ))}
            </div>
          </Link>
        ))}
      </section>
    </div>
  );
}

function CapxUiOneOverviewView({ onCommand }: WorkbenchChildProps): JSX.Element {
  const { projectId } = useParams();
  const project = getCapxUiOneProject(projectId);

  return (
    <div className="capx-ui-one-view" data-testid="capx-ui-one-overview">
      <div className="capx-ui-one-view__heading">
        <p>Project Overview / State Snapshot</p>
        <h2>Governed current state</h2>
      </div>
      <section className="capx-ui-one-snapshot">
        <div>
          <p>Basis version</p>
          <h3>{capxUiOneSnapshot.basisVersion}</h3>
          <span>{project.snapshotFreshness}</span>
        </div>
        <div>
          <p>Lifecycle stage</p>
          <h3>{capxUiOneSnapshot.currentLifecycleStage}</h3>
          <span>{capxUiOneSnapshot.stateLabels.join(" / ")}</span>
        </div>
        <div>
          <p>Open work</p>
          <h3>{capxUiOneTasks.length} tasks</h3>
          <span>{capxUiOneTasks.filter((task) => task.state === "Not ready" || task.state === "Blocked").length} cannot close yet</span>
        </div>
        <div>
          <p>Forecastability</p>
          <h3>{project.forecastability}</h3>
          <span>{[...project.staleBadges, ...project.blockedBadges].join(" / ") || "No active blockers"}</span>
        </div>
      </section>
      <CapxUiOneLifecycleRibbon />
      <section className="capx-ui-one-split">
        <div className="capx-ui-one-panel">
          <div className="capx-ui-one-panel__title">
            <p>Basis version panel</p>
            <h3>Official pointers remain separate from generated views</h3>
          </div>
          <dl className="capx-ui-one-definition-list">
            {capxUiOneSnapshot.officialPointers.map((pointer) => (
              <div key={pointer.label}>
                <dt>{pointer.label}</dt>
                <dd>{pointer.value}</dd>
              </div>
            ))}
          </dl>
          <div className="capx-ui-one-acceptance">
            {capxUiOneSnapshot.stateLabels.map((label) => (
              <span key={label}>{label}</span>
            ))}
          </div>
        </div>
        <div className="capx-ui-one-panel">
          <div className="capx-ui-one-panel__title">
            <p>Blockers and next actions</p>
            <h3>Stale state blocks mutation until revalidation</h3>
          </div>
          <div className="capx-ui-one-job-list">
            {capxUiOneSnapshot.blockers.map((blocker) => (
              <article key={blocker.id}>
                <div>
                  <strong>{blocker.label}</strong>
                  <span>{blocker.boundTaskId}</span>
                </div>
                <CapxUiOneStatusPill label={blocker.severity} tone="blocked" />
              </article>
            ))}
            {capxUiOneSnapshot.staleReasons.map((reason) => (
              <article key={reason.source}>
                <div>
                  <strong>{reason.source}</strong>
                  <span>{reason.reason}</span>
                </div>
                <CapxUiOneStatusPill label="stale" tone="stale" />
              </article>
            ))}
          </div>
          <ol className="capx-ui-one-path">
            {capxUiOneSnapshot.nextActions.map((action) => (
              <li key={action}>{action}</li>
            ))}
          </ol>
          <div className="capx-ui-one-command-stack">
            <CapxUiOneCommandButton
              onCommand={onCommand}
              receipt={buildFixtureReceipt("receipt-002")}
            >
              Generate report draft
            </CapxUiOneCommandButton>
            <CapxUiOneCommandButton
              onCommand={onCommand}
              receipt={buildReceipt(
                "mark_project_green_directly",
                project.snapshotId,
                "rejected",
                "Direct green status is blocked. Resolve the compressed-air blocker and revalidate the stale snapshot first.",
                "task-001",
                "blocked_open_interface",
                "Request current compressed-air measurement from the utilities owner."
              )}
              variant="rejected"
            >
              Mark green directly
            </CapxUiOneCommandButton>
          </div>
        </div>
      </section>
      <section className="capx-ui-one-panel">
        <div className="capx-ui-one-panel__title">
          <p>Workpage dry-run projections</p>
          <h3>Rendered workpages are projections, not source of truth</h3>
        </div>
        <div className="capx-ui-one-workpage-grid">
          {capxUiOneWorkpageProjections.map((workpage) => (
            <article key={workpage.id}>
              <span>{workpage.id}</span>
              <strong>{workpage.name}</strong>
              <small>{workpage.inputs}</small>
              <p>{workpage.renderedState}</p>
              <p>{workpage.availableCommands}</p>
              <CapxUiOneStatusPill label={workpage.guardrailOutcome} tone="blocked" />
            </article>
          ))}
        </div>
      </section>
    </div>
  );
}

function CapxUiOnePhaseWorkspaceView({ onCommand }: WorkbenchChildProps): JSX.Element {
  const { phaseKey } = useParams();
  const phase = getCapxUiOnePhase(phaseKey);
  const [draftNote, setDraftNote] = useState("AB-02 supplier responsibility wording needs human re-review.");

  return (
    <div className="capx-ui-one-view" data-testid="capx-ui-one-phase-workspace">
      <div className="capx-ui-one-view__heading">
        <p>{phase.workspace}</p>
        <h2>{phase.name}</h2>
      </div>
      <CapxUiOneLifecycleRibbon />
      <section className={`capx-ui-one-phase-head is-${phase.state}`} aria-label="Phase header">
        <div>
          <p>Purpose</p>
          <strong>{phase.scope}</strong>
        </div>
        <div>
          <p>State</p>
          <CapxUiOneStatusPill label={phase.state} tone={phase.state} />
        </div>
        <div>
          <p>Readiness gate</p>
          <strong>{phase.readiness}</strong>
        </div>
      </section>
      <section className="capx-ui-one-workspace-grid" aria-label="Phase workspace panels">
        <div className="capx-ui-one-panel">
          <div className="capx-ui-one-panel__title">
            <p>Inputs panel</p>
            <h3>Evidence and manual fields</h3>
          </div>
          <div className="capx-ui-one-evidence-list">
            {capxUiOneEvidence.slice(0, 3).map((item) => (
              <article key={item.id}>
                <strong>{item.title}</strong>
                <span>{item.role}</span>
                <CapxUiOneStatusPill label={item.status} tone={stateTone(item.status)} />
              </article>
            ))}
          </div>
        </div>
        <div className="capx-ui-one-panel">
          <div className="capx-ui-one-panel__title">
            <p>AI processing panel</p>
            <h3>{phase.aiFunctions}</h3>
          </div>
          <div className="capx-ui-one-job-list">
            {capxUiOneAiJobs.map((job) => (
              <article key={job.id}>
                <div>
                  <strong>{job.label}</strong>
                  <span>{job.output}</span>
                </div>
                <CapxUiOneStatusPill label={job.state} tone={stateTone(job.state)} />
              </article>
            ))}
          </div>
        </div>
        <div className="capx-ui-one-panel">
          <div className="capx-ui-one-panel__title">
            <p>Draft output panel</p>
            <h3>{phase.outputs}</h3>
          </div>
          <label className="capx-ui-one-draft-note">
            <span>Reviewer note</span>
            <textarea onChange={(event) => setDraftNote(event.target.value)} value={draftNote} />
          </label>
          {capxUiOneDraftOutputs.slice(0, 2).map((output) => (
            <article className="capx-ui-one-output-row" key={output.id}>
              <strong>{output.title}</strong>
              <span>{output.basis}</span>
              <small>{output.warning}</small>
            </article>
          ))}
        </div>
        <div className="capx-ui-one-panel">
          <div className="capx-ui-one-panel__title">
            <p>Review and decision panel</p>
            <h3>Human review before official state</h3>
          </div>
          <div className="capx-ui-one-command-stack">
            <CapxUiOneCommandButton
              onCommand={onCommand}
              receipt={buildReceipt(
                "submit_for_human_review",
                "out-k12-assumption-001",
                "accepted",
                "Supplier responsibility re-review note submitted with the K12 evidence basis and reviewer note preserved.",
                "task-002",
                "review_requested",
                "Review AB-02 before any assumption pointer promotion is attempted."
              )}
            >
              Submit for human review
            </CapxUiOneCommandButton>
            <CapxUiOneCommandButton
              onCommand={onCommand}
              receipt={buildReceipt(
                "publish_ai_output_directly",
                "out-k12-assumption-001",
                "rejected",
                "AI output is untrusted draft material. Review, approval, and pointer promotion are required.",
                "task-002",
                "draft_only",
                "Keep the generated note in review until a human approves the exact version."
              )}
              variant="rejected"
            >
              Publish AI output
            </CapxUiOneCommandButton>
          </div>
          <div className="capx-ui-one-acceptance">
            {capxUiOneAcceptanceCriteria.slice(0, 4).map((criterion) => (
              <span key={criterion}>{criterion}</span>
            ))}
          </div>
        </div>
      </section>
    </div>
  );
}

function CapxUiOneEvidenceView({ onCommand, onFocusEvidence }: WorkbenchChildProps): JSX.Element {
  return (
    <div className="capx-ui-one-view" data-testid="capx-ui-one-evidence">
      <div className="capx-ui-one-view__heading">
        <p>Documents / Evidence Library</p>
        <h2>Source occurrences, extracted claims, and basis versions</h2>
      </div>
      <section className="capx-ui-one-panel">
        <div className="capx-ui-one-evidence-table" role="table" aria-label="Evidence library">
          <div role="row">
            <span role="columnheader">Evidence</span>
            <span role="columnheader">Role</span>
            <span role="columnheader">Status</span>
            <span role="columnheader">Occurrence</span>
            <span role="columnheader">Basis</span>
          </div>
          {capxUiOneEvidence.map((item) => (
            <div key={item.id} role="row">
              <span role="cell">
                <strong>{item.title}</strong>
                <small>{item.kind}</small>
                <button
                  aria-label={`Open evidence drawer for ${item.title}`}
                  className="capx-ui-one-inline-button"
                  onClick={() => onFocusEvidence?.(item.id)}
                  type="button"
                >
                  Open drawer
                </button>
              </span>
              <span role="cell">{item.role}</span>
              <span role="cell">{item.status}</span>
              <span role="cell">{item.sourceOccurrence}</span>
              <span role="cell">{item.basis}</span>
            </div>
          ))}
        </div>
      </section>
      <section className="capx-ui-one-command-band">
        <CapxUiOneCommandButton
          onCommand={onCommand}
          receipt={buildReceipt(
            "request_extraction",
            "ev-002",
            "accepted",
            "Extraction job requested for Order Revision AB-02. Result remains draft until reviewed.",
            "task-002",
            "draft_extraction",
            "Complete human review before treating the changed wording as approved."
          )}
        >
          Request extraction
        </CapxUiOneCommandButton>
        <CapxUiOneCommandButton
          onCommand={onCommand}
          receipt={buildReceipt(
            "treat_file_as_truth",
            "ev-001",
            "rejected",
            "A file is evidence, not official state. Official claims require reviewed artifacts and pointers.",
            undefined,
            "evidence_not_truth",
            "Promote only through reviewed artifact and pointer commands."
          )}
          variant="rejected"
        >
          Treat file as truth
        </CapxUiOneCommandButton>
      </section>
    </div>
  );
}

function CapxUiOneStructuringView({ onCommand }: WorkbenchChildProps): JSX.Element {
  return (
    <div className="capx-ui-one-view" data-testid="capx-ui-one-structuring">
      <div className="capx-ui-one-view__heading">
        <p>Structuring Engine Review</p>
        <h2>AI-classified intake outputs under human review</h2>
      </div>
      <section className="capx-ui-one-split">
        <div className="capx-ui-one-panel">
          <div className="capx-ui-one-panel__title">
            <p>Draft artifacts</p>
            <h3>Generated outputs</h3>
          </div>
          {capxUiOneDraftOutputs.map((output) => (
            <article className="capx-ui-one-output-row" key={output.id}>
              <strong>{output.title}</strong>
              <span>{output.state}</span>
              <small>{output.warning}</small>
            </article>
          ))}
        </div>
        <div className="capx-ui-one-panel">
          <div className="capx-ui-one-panel__title">
            <p>Decision packet</p>
            <h3>Review path</h3>
          </div>
          <dl className="capx-ui-one-definition-list">
            <div>
              <dt>Target version</dt>
              <dd>out-k12-assumption-001</dd>
            </div>
            <div>
              <dt>Evidence basis</dt>
              <dd>capex.assumption_closure_matrix.v1:k12:002-stale</dd>
            </div>
            <div>
              <dt>Downstream consequence</dt>
              <dd>Procurement readiness stays blocked until re-review and current measurement evidence pass.</dd>
            </div>
          </dl>
          <div className="capx-ui-one-command-stack">
            <CapxUiOneCommandButton
              onCommand={onCommand}
              receipt={buildReceipt(
                "review_artifact",
                "out-k12-assumption-001",
                "accepted",
                "Human review action accepted. The draft is still not official until approval and promotion conditions pass.",
                "task-002",
                "review_recorded",
                "Request pointer validation only after all blockers clear."
              )}
            >
              Review artifact
            </CapxUiOneCommandButton>
            <CapxUiOneCommandButton
              onCommand={onCommand}
              receipt={buildReceipt(
                "promote_unreviewed_draft",
                "out-k12-assumption-001",
                "rejected",
                "Promotion is blocked because the artifact is draft and lacks review approval.",
                "task-002",
                "draft_only",
                "Review and approve the exact artifact version before promotion."
              )}
              variant="rejected"
            >
              Promote unreviewed draft
            </CapxUiOneCommandButton>
          </div>
        </div>
      </section>
    </div>
  );
}

function CapxUiOneTasksView({ onCommand, onFocusTask }: WorkbenchChildProps): JSX.Element {
  return (
    <div className="capx-ui-one-view" data-testid="capx-ui-one-tasks">
      <div className="capx-ui-one-view__heading">
        <p>Tasks & Approvals</p>
        <h2>Project-scoped review and pointer promotion queue</h2>
      </div>
      <section className="capx-ui-one-panel">
        <CapxUiOneTaskTable onFocusTask={onFocusTask} />
      </section>
      <section className="capx-ui-one-command-band">
        <CapxUiOneCommandButton
          onCommand={onCommand}
          receipt={buildFixtureReceipt("receipt-001")}
          variant="rejected"
        >
          Close without evidence
        </CapxUiOneCommandButton>
        <CapxUiOneCommandButton
          onCommand={onCommand}
          receipt={buildReceipt(
            "request_current_measurement",
            "task-001",
            "accepted",
            "Current compressed-air pressure and flow-rate measurement requested from the utilities owner.",
            "task-001",
            "evidence_request_created",
            "Attach the measurement evidence before attempting task close or procurement readiness."
          )}
        >
          Request measurement evidence
        </CapxUiOneCommandButton>
      </section>
    </div>
  );
}

function CapxUiOneReportsView({ onCommand }: WorkbenchChildProps): JSX.Element {
  return (
    <div className="capx-ui-one-view" data-testid="capx-ui-one-reports">
      <div className="capx-ui-one-view__heading">
        <p>Reports & Management Slides</p>
        <h2>Generate reports from governed snapshots</h2>
      </div>
      <section className="capx-ui-one-report-grid" aria-label="Report builder">
        {capxUiOneReports.map((report) => (
          <article key={report.id}>
            <span>{report.id}</span>
            <h3>{report.title}</h3>
            <CapxUiOneStatusPill label={report.official ? "Official" : "Not official"} tone={report.official ? "official" : "blocked"} />
            <dl>
              <div>
                <dt>Snapshot ID</dt>
                <dd>{report.snapshotId}</dd>
              </div>
              <div>
                <dt>Freshness</dt>
                <dd>{report.freshness}</dd>
              </div>
              <div>
                <dt>State</dt>
                <dd>{report.state}</dd>
              </div>
              <div>
                <dt>Sections</dt>
                <dd>{report.sections.join(" / ")}</dd>
              </div>
            </dl>
            <p>{report.warning}</p>
          </article>
        ))}
      </section>
      <section className="capx-ui-one-command-band">
        <CapxUiOneCommandButton
          onCommand={onCommand}
          receipt={buildFixtureReceipt("receipt-002")}
        >
          Generate report draft
        </CapxUiOneCommandButton>
        <CapxUiOneCommandButton
          onCommand={onCommand}
          receipt={buildFixtureReceipt("receipt-003")}
          variant="rejected"
        >
          Publish report as official
        </CapxUiOneCommandButton>
      </section>
    </div>
  );
}

function CapxUiOneAuditView(): JSX.Element {
  return (
    <div className="capx-ui-one-view" data-testid="capx-ui-one-audit">
      <div className="capx-ui-one-view__heading">
        <p>Audit / History</p>
        <h2>Command receipts and state transitions</h2>
      </div>
      <section className="capx-ui-one-timeline" aria-label="Audit timeline">
        {capxUiOneAuditEvents.map((event) => (
          <article className={`is-${event.outcome}`} key={event.id}>
            <span>{event.recordedAt}</span>
            <div>
              <strong>{event.command}</strong>
              <p>{event.actor} to {event.target}</p>
              <small>{event.policy}</small>
            </div>
            <CapxUiOneStatusPill label={event.outcome} tone={event.outcome} />
          </article>
        ))}
      </section>
    </div>
  );
}

function CapxUiOneAdminView(): JSX.Element {
  return (
    <div className="capx-ui-one-view" data-testid="capx-ui-one-admin">
      <div className="capx-ui-one-view__heading">
        <p>Admin / AI / Integrations</p>
        <h2>Minimal configuration status</h2>
      </div>
      <section className="capx-ui-one-admin-grid">
        {[
          ["AI provider", "Queue-backed workers only", "No long-running UI calls"],
          ["SAP sync", "Readiness pending", "External sync is not official CAPEX state"],
          ["Teams notifications", "Notify-only", "Critical decisions remain task-bound"],
          ["Role policy", "Separation of duties enforced", "Self-approval is blocked"]
        ].map(([label, state, note]) => (
          <article key={label}>
            <span>{label}</span>
            <strong>{state}</strong>
            <p>{note}</p>
          </article>
        ))}
      </section>
    </div>
  );
}

function CapxUiOneRightDrawer({
  focus,
  receipt
}: {
  focus: DrawerFocus;
  receipt: CommandReceipt | null;
}): JSX.Element {
  const focusTask = useMemo(() => {
    if (receipt?.taskId) {
      return getCapxUiOneTask(receipt.taskId);
    }

    return focus.kind === "task" ? getCapxUiOneTask(focus.taskId) : capxUiOneTasks[0];
  }, [focus, receipt]);

  const focusEvidence = useMemo<CapxUiOneEvidence | null>(() => {
    return focus.kind === "evidence" ? getCapxUiOneEvidence(focus.evidenceId) : null;
  }, [focus]);

  const decisionBasis = focusEvidence?.basis ?? focusTask.basis;
  const decisionTarget = receipt?.target ?? focusEvidence?.sourceOccurrence ?? focusTask.boundObject;

  return (
    <aside className="capx-ui-one-drawer" aria-label="Evidence policy decision and audit drawer">
      {focusEvidence ? (
        <>
          <section>
            <p>Evidence drawer</p>
            <h2>{focusEvidence.id}</h2>
            <strong>{focusEvidence.title}</strong>
            <span>{focusEvidence.role}</span>
          </section>
          <section>
            <p>Extraction and review</p>
            <h2>{focusEvidence.status}</h2>
            <dl>
              <div>
                <dt>Review state</dt>
                <dd>{focusEvidence.reviewState}</dd>
              </div>
              <div>
                <dt>Extraction</dt>
                <dd>{focusEvidence.extractionStatus}</dd>
              </div>
              <div>
                <dt>Provenance</dt>
                <dd>{focusEvidence.provenance}</dd>
              </div>
            </dl>
            <ol className="capx-ui-one-path">
              {focusEvidence.claimsDerived.map((claim) => (
                <li key={claim}>{claim}</li>
              ))}
            </ol>
          </section>
        </>
      ) : (
        <>
          <section>
            <p>Task drawer</p>
            <h2>{focusTask.id}</h2>
            <strong>{focusTask.title}</strong>
            <span>{focusTask.evidence}</span>
          </section>
          <section>
            <p>Policy checks</p>
            <h2>{focusTask.state}</h2>
            <span>{focusTask.policy}</span>
          </section>
        </>
      )}
      <section>
        <p>Decision packet</p>
        <dl>
          <div>
            <dt>Target</dt>
            <dd>{decisionTarget}</dd>
          </div>
          <div>
            <dt>Basis</dt>
            <dd>{decisionBasis}</dd>
          </div>
          <div>
            <dt>Consequence</dt>
            <dd>Officialness changes only through reviewed approvals and governed pointer promotion.</dd>
          </div>
        </dl>
      </section>
      {receipt ? (
        <section
          className={`capx-ui-one-receipt is-${receipt.outcome}`}
          role="status"
          aria-label="Command receipt"
        >
          <p>{receipt.outcome === "accepted" ? "Accepted receipt" : "Blocked receipt"}</p>
          <h2>{receipt.command}</h2>
          <span>{receipt.detail}</span>
          {receipt.policyResult ? <strong>{receipt.policyResult}</strong> : null}
          {receipt.nextRequiredAction ? <small>{receipt.nextRequiredAction}</small> : null}
          {receipt.outcome === "rejected" ? (
            <div className="capx-ui-one-policy-panel" aria-label="Policy Check Panel">
              <strong>Policy Check Panel</strong>
              <small>{receipt.nextRequiredAction ?? "Use a bound review, approval, or promotion command with a current basis token."}</small>
            </div>
          ) : null}
        </section>
      ) : null}
      <section>
        <p>Audit trail</p>
        <span>{capxUiOneAuditEvents[0].actor} / {capxUiOneAuditEvents[0].command} / {capxUiOneAuditEvents[0].policy}</span>
      </section>
    </aside>
  );
}

export function CapxUiOneWorkbenchPage(): JSX.Element {
  const { pathname } = useLocation();
  const project = getCapxUiOneProject(getProjectIdFromPath(pathname));
  const [receipt, setReceipt] = useState<CommandReceipt | null>(null);
  const [drawerFocus, setDrawerFocus] = useState<DrawerFocus>({ kind: "task", taskId: "task-001" });

  function handleCommand(nextReceipt: CommandReceipt): void {
    setReceipt(nextReceipt);
    if (nextReceipt.taskId) {
      setDrawerFocus({ kind: "task", taskId: nextReceipt.taskId });
    }
  }

  function handleFocusEvidence(evidenceId: string): void {
    setReceipt(null);
    setDrawerFocus({ kind: "evidence", evidenceId });
  }

  function handleFocusTask(taskId: string): void {
    setReceipt(null);
    setDrawerFocus({ kind: "task", taskId });
  }

  return (
    <main className="capx-ui-one" data-testid="capx-ui-one-workbench">
      <CapxUiOneTopBar />
      <div className="capx-ui-one-shell">
        <CapxUiOneSideNav />
        <section className="capx-ui-one-main" aria-label="UI-One workbench main area">
          <CapxUiOneProjectContextBar project={project} />
          <Routes>
            <Route index element={<Navigate to="home" replace />} />
            <Route path="home" element={<CapxUiOneHomeView onCommand={handleCommand} onFocusTask={handleFocusTask} />} />
            <Route path="queue" element={<CapxUiOneQueueView onCommand={handleCommand} onFocusTask={handleFocusTask} />} />
            <Route path="projects" element={<CapxUiOneProjectsView />} />
            <Route path="projects/:projectId" element={<Navigate to="overview" replace />} />
            <Route path="projects/:projectId/overview" element={<CapxUiOneOverviewView onCommand={handleCommand} />} />
            <Route
              path="projects/:projectId/phases/:phaseKey"
              element={<CapxUiOnePhaseWorkspaceView onCommand={handleCommand} />}
            />
            <Route
              path="projects/:projectId/evidence"
              element={<CapxUiOneEvidenceView onCommand={handleCommand} onFocusEvidence={handleFocusEvidence} />}
            />
            <Route
              path="projects/:projectId/structuring"
              element={<CapxUiOneStructuringView onCommand={handleCommand} />}
            />
            <Route
              path="projects/:projectId/tasks"
              element={<CapxUiOneTasksView onCommand={handleCommand} onFocusTask={handleFocusTask} />}
            />
            <Route path="projects/:projectId/reports" element={<CapxUiOneReportsView onCommand={handleCommand} />} />
            <Route path="projects/:projectId/audit" element={<CapxUiOneAuditView />} />
            <Route path="reports" element={<CapxUiOneReportsView onCommand={handleCommand} />} />
            <Route path="admin" element={<CapxUiOneAdminView />} />
            <Route path="*" element={<Navigate to="home" replace />} />
          </Routes>
        </section>
        <CapxUiOneRightDrawer focus={drawerFocus} receipt={receipt} />
      </div>
    </main>
  );
}
