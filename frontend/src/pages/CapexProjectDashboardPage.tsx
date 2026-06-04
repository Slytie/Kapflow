import { useEffect, useMemo } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";

import { StatePanel } from "@/components/StatePanel";
import { apiConfig } from "@/lib/api/config";
import { errorText } from "@/lib/api/errorText";
import { capexProjectsRepository } from "@/lib/repositories";
import type {
  ApprovalRow,
  CapexProject,
  CapexProjectDashboard,
  FlagRow,
  HumanTaskRow,
  WorkflowRunRow
} from "@/lib/types/contracts";

const COUNT_LABELS: Array<keyof CapexProjectDashboard["counts"]> = [
  "workflow_run_count",
  "open_human_task_count",
  "pending_approval_count",
  "active_flag_count",
  "artifact_version_count",
  "pointer_count",
  "timeline_event_count"
];

const COUNT_TITLES: Record<keyof CapexProjectDashboard["counts"], string> = {
  workflow_run_count: "Runs",
  open_human_task_count: "Open tasks",
  pending_approval_count: "Pending approvals",
  active_flag_count: "Active flags",
  artifact_version_count: "Artifacts",
  pointer_count: "Pointers",
  timeline_event_count: "Timeline events"
};

function roleLabel(role: string | null | undefined): string {
  if (!role) {
    return "No role";
  }
  return role.replace(/^project_/, "").replace(/_/g, " ");
}

function projectRoute(projectId: string): string {
  return `/capex/projects/${encodeURIComponent(projectId)}`;
}

function runRoute(run: WorkflowRunRow): string {
  return `/runs/${encodeURIComponent(run.workflow_run_id)}/workspace`;
}

function runDetailRoute(run: WorkflowRunRow): string {
  return `/runs/${encodeURIComponent(run.workflow_run_id)}`;
}

function workQueueRoute(workflowRunId: string): string {
  return `/my-work?run=${encodeURIComponent(workflowRunId)}`;
}

function approvalsRoute(workflowRunId: string): string {
  return `/approvals?run=${encodeURIComponent(workflowRunId)}`;
}

function flagsRoute(workflowRunId: string): string {
  return `/exceptions?run=${encodeURIComponent(workflowRunId)}`;
}

function selectedProjectFromRoute(
  projects: CapexProject[],
  routeProjectId: string | undefined
): CapexProject | null {
  if (routeProjectId) {
    return projects.find((project) => project.project_id === routeProjectId) ?? null;
  }
  return projects[0] ?? null;
}

function ProjectSelector({
  projects,
  selectedProjectId
}: {
  projects: CapexProject[];
  selectedProjectId: string | null;
}): JSX.Element {
  return (
    <nav className="capex-projects-page__selector" aria-label="CAPEX projects">
      {projects.map((project) => (
        <Link
          key={project.project_id}
          className={project.project_id === selectedProjectId ? "is-active" : ""}
          to={projectRoute(project.project_id)}
        >
          <span>{project.project_key}</span>
          <strong>{project.name}</strong>
          <small>{roleLabel(project.caller_role)}</small>
        </Link>
      ))}
    </nav>
  );
}

function CountStrip({ dashboard }: { dashboard: CapexProjectDashboard }): JSX.Element {
  return (
    <section className="capex-projects-page__counts" aria-label="Project counts">
      {COUNT_LABELS.map((key) => (
        <article key={key}>
          <span>{COUNT_TITLES[key]}</span>
          <strong>{dashboard.counts[key]}</strong>
        </article>
      ))}
    </section>
  );
}

function RunRows({ runs }: { runs: WorkflowRunRow[] }): JSX.Element {
  if (runs.length === 0) {
    return <p className="capex-projects-page__empty">No project runs in scope.</p>;
  }
  return (
    <div className="capex-projects-page__rows">
      {runs.slice(0, 6).map((run) => (
        <article key={run.workflow_run_id}>
          <div>
            <span>{run.workflow_id}</span>
            <strong>{run.partition_key}</strong>
            <small>{run.workflow_run_id}</small>
          </div>
          <div className="capex-projects-page__row-actions">
            <Link to={runRoute(run)}>Workspace</Link>
            <Link to={runDetailRoute(run)}>Detail</Link>
          </div>
        </article>
      ))}
    </div>
  );
}

function TaskRows({ tasks }: { tasks: HumanTaskRow[] }): JSX.Element {
  if (tasks.length === 0) {
    return <p className="capex-projects-page__empty">No open tasks.</p>;
  }
  return (
    <div className="capex-projects-page__rows">
      {tasks.slice(0, 5).map((task) => (
        <article key={task.human_task_id}>
          <div>
            <span>{task.stage_id}</span>
            <strong>{task.task_kind.replace(/_/g, " ")}</strong>
            <small>{task.human_task_id}</small>
          </div>
          <Link to={workQueueRoute(task.workflow_run_id)}>Queue</Link>
        </article>
      ))}
    </div>
  );
}

function ApprovalRows({ approvals }: { approvals: ApprovalRow[] }): JSX.Element {
  if (approvals.length === 0) {
    return <p className="capex-projects-page__empty">No pending approvals.</p>;
  }
  return (
    <div className="capex-projects-page__rows">
      {approvals.slice(0, 5).map((approval) => (
        <article key={approval.approval_id}>
          <div>
            <span>{approval.approval_kind}</span>
            <strong>{approval.scope_ref}</strong>
            <small>{approval.approval_id}</small>
          </div>
          <Link to={approvalsRoute(approval.workflow_run_id)}>Queue</Link>
        </article>
      ))}
    </div>
  );
}

function FlagRows({ flags }: { flags: FlagRow[] }): JSX.Element {
  if (flags.length === 0) {
    return <p className="capex-projects-page__empty">No active flags.</p>;
  }
  return (
    <div className="capex-projects-page__rows">
      {flags.slice(0, 5).map((flag) => (
        <article key={flag.flag_id}>
          <div>
            <span>{flag.severity}</span>
            <strong>{flag.summary}</strong>
            <small>{flag.flag_id}</small>
          </div>
          <Link to={flagsRoute(flag.workflow_run_id)}>Queue</Link>
        </article>
      ))}
    </div>
  );
}

export function CapexProjectDashboardPage(): JSX.Element {
  const { projectId } = useParams();
  const navigate = useNavigate();

  const projectsQuery = useQuery({
    queryKey: ["capex-projects", "assigned", 5],
    queryFn: () => capexProjectsRepository.listAssigned(5),
    refetchInterval: apiConfig.pollIntervalMs
  });

  const projects = projectsQuery.data ?? [];
  const selectedProject = useMemo(
    () => selectedProjectFromRoute(projects, projectId),
    [projectId, projects]
  );
  const selectedProjectId = selectedProject?.project_id ?? null;

  useEffect(() => {
    if (!projectId && selectedProjectId) {
      navigate(projectRoute(selectedProjectId), { replace: true });
    }
  }, [navigate, projectId, selectedProjectId]);

  const dashboardQuery = useQuery({
    queryKey: ["capex-projects", selectedProjectId, "dashboard"],
    queryFn: () => capexProjectsRepository.dashboard(selectedProjectId ?? ""),
    enabled: Boolean(selectedProjectId),
    refetchInterval: apiConfig.pollIntervalMs
  });

  if (projectsQuery.isLoading) {
    return <StatePanel kind="loading" title="Loading CAPEX projects" detail="Resolving assigned projects." />;
  }

  if (projectsQuery.isError) {
    return (
      <StatePanel
        kind="error"
        title="CAPEX projects failed to load"
        detail={errorText(projectsQuery.error, "Unable to load CAPEX projects")}
        onRetry={() => void projectsQuery.refetch()}
      />
    );
  }

  if (projects.length === 0) {
    return <StatePanel kind="empty" title="No CAPEX projects assigned" detail="No active project memberships are visible." />;
  }

  if (projectId && !selectedProject) {
    return <StatePanel kind="empty" title="CAPEX project unavailable" detail="No assigned project matched this route." />;
  }

  return (
    <main className="capex-projects-page" data-testid="capex-projects-page">
      <header className="capex-projects-page__header">
        <div>
          <p className="timeline-page__eyebrow">CAPEX projects</p>
          <h1>{selectedProject?.name ?? "Assigned projects"}</h1>
          <p>{selectedProject?.project_key ?? "Select a project"}</p>
        </div>
        <strong className="capex-projects-page__role">
          {roleLabel(dashboardQuery.data?.caller_role ?? selectedProject?.caller_role)}
        </strong>
      </header>

      <ProjectSelector projects={projects} selectedProjectId={selectedProjectId} />

      {dashboardQuery.isLoading ? (
        <StatePanel kind="loading" title="Loading dashboard" detail="Resolving project counts and active work." />
      ) : dashboardQuery.isError ? (
        <StatePanel
          kind="error"
          title="CAPEX dashboard failed to load"
          detail={errorText(dashboardQuery.error, "Unable to load CAPEX dashboard")}
          onRetry={() => void dashboardQuery.refetch()}
        />
      ) : dashboardQuery.data ? (
        <>
          <CountStrip dashboard={dashboardQuery.data} />

          <section className="capex-projects-page__queues" aria-label="Project queues">
            <section id="project-runs">
              <header>
                <h2>Recent Runs</h2>
                <Link to={`/runs?project_id=${encodeURIComponent(selectedProjectId ?? "")}`}>Run queue</Link>
              </header>
              <RunRows runs={dashboardQuery.data.workflow_runs} />
            </section>

            <section id="project-work">
              <header>
                <h2>Open Tasks</h2>
                <Link to={`/my-work?project_id=${encodeURIComponent(selectedProjectId ?? "")}`}>Task queue</Link>
              </header>
              <TaskRows tasks={dashboardQuery.data.human_tasks} />
            </section>

            <section>
              <header>
                <h2>Pending Approvals</h2>
                <Link to="/approvals">Approval queue</Link>
              </header>
              <ApprovalRows approvals={dashboardQuery.data.approvals} />
            </section>

            <section>
              <header>
                <h2>Active Flags</h2>
                <Link to="/exceptions">Flag queue</Link>
              </header>
              <FlagRows flags={dashboardQuery.data.flags} />
            </section>
          </section>
        </>
      ) : null}
    </main>
  );
}
