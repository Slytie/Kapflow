import { Link, Navigate, useParams } from "react-router-dom";

import { CapxPmProjectShell } from "./CapxPmProjectShell";
import { CapxPmProjectStepRail } from "./CapxPmProjectStepRail";
import { CapxPmStatusChip } from "./CapxPmStatusChip";
import { CapxPmStepAssumptionsPage } from "./CapxPmStepAssumptionsPage";
import { CapxPmStepCommitmentPage } from "./CapxPmStepCommitmentPage";
import { CapxPmStepCorpusPage } from "./CapxPmStepCorpusPage";
import { CapxPmStepIntakePage } from "./CapxPmStepIntakePage";
import { CapxPmStepInterfacesPage } from "./CapxPmStepInterfacesPage";
import { CapxPmStepLifecyclePage } from "./CapxPmStepLifecyclePage";
import { CapxPmStepSnapshotPage } from "./CapxPmStepSnapshotPage";
import { capxPmStatusRank, getCapxPmEvidenceStatus } from "./capxPmProjectStatus";
import {
  buildCapxPmStepHref,
  buildCapxPmWorkspaceViewModel,
  type CapxPmWorkspaceViewModel,
  getCapxPmDefaultStepSlug,
  getCapxPmProject,
  getCapxPmProjectStep,
  isCapxPmStepSlug
} from "./capxPmProjectViewModels";

function ProjectNotFound(): JSX.Element {
  return (
    <CapxPmProjectShell title="Project not found" updatedAt="static">
      <main className="capx-pm-page capx-pm-not-found" data-testid="capx-pm-project-not-found">
        <section className="capx-pm-panel">
          <h2>Project not found</h2>
          <p>The requested CAPX PM mock project is not available in this disposable demo state.</p>
          <Link className="capx-pm-command-button" to="/demo/capx/pm/projects">
            Back to PM projects
          </Link>
        </section>
      </main>
    </CapxPmProjectShell>
  );
}

function StepNotFound({ projectId }: { projectId: string }): JSX.Element {
  const project = getCapxPmProject(projectId);
  const fallbackHref = project ? buildCapxPmStepHref(project, getCapxPmDefaultStepSlug(project)) : "/demo/capx/pm/projects";

  return (
    <CapxPmProjectShell title="Step not found" updatedAt="static">
      <main className="capx-pm-page capx-pm-not-found" data-testid="capx-pm-step-not-found">
        <section className="capx-pm-panel">
          <h2>Step not found</h2>
          <p>The requested workflow step is outside WFLOW-001 through WFLOW-007 for this PM demo.</p>
          <Link className="capx-pm-command-button" to={fallbackHref}>
            Open active step
          </Link>
        </section>
      </main>
    </CapxPmProjectShell>
  );
}

function CapxPmSelectedStepPage({ viewModel }: { viewModel: CapxPmWorkspaceViewModel }): JSX.Element {
  switch (viewModel.step.slug) {
    case "intake":
      return <CapxPmStepIntakePage viewModel={viewModel} />;
    case "corpus":
      return <CapxPmStepCorpusPage viewModel={viewModel} />;
    case "lifecycle":
      return <CapxPmStepLifecyclePage viewModel={viewModel} />;
    case "commitment":
      return <CapxPmStepCommitmentPage viewModel={viewModel} />;
    case "assumptions":
      return <CapxPmStepAssumptionsPage viewModel={viewModel} />;
    case "interfaces":
      return <CapxPmStepInterfacesPage viewModel={viewModel} />;
    case "snapshot":
      return <CapxPmStepSnapshotPage viewModel={viewModel} />;
  }
}

export function CapxPmProjectWorkspacePage(): JSX.Element {
  const { projectId, stepId } = useParams();
  const project = getCapxPmProject(projectId);

  if (!project) {
    return <ProjectNotFound />;
  }

  if (!stepId) {
    return <Navigate to={buildCapxPmStepHref(project, getCapxPmDefaultStepSlug(project))} replace />;
  }

  if (!isCapxPmStepSlug(stepId) || !getCapxPmProjectStep(project, stepId)) {
    return <StepNotFound projectId={project.id} />;
  }

  const viewModel = buildCapxPmWorkspaceViewModel(project, stepId);
  const priorityTask = [...viewModel.stepState.tasks].sort(
    (left, right) => capxPmStatusRank(left.status) - capxPmStatusRank(right.status)
  )[0];

  return (
    <CapxPmProjectShell title={`${project.code} ${project.name}`} updatedAt={viewModel.generatedAt}>
      <main className="capx-pm-page capx-pm-workspace" data-testid="capx-pm-workspace-page">
        <div className="capx-pm-workspace__breadcrumb">
          <Link to="/demo/capx/pm/projects">PM projects</Link>
          <span>/</span>
          <span>{project.code}</span>
        </div>

        <section className="capx-pm-project-header" aria-labelledby="capx-pm-project-title">
          <div>
            <p className="capx-pm-eyebrow">Project workflow workspace</p>
            <h2 id="capx-pm-project-title">
              {project.code} {project.name}
            </h2>
            <p>
              {project.site} / {project.projectType} / PM {project.pmOwner}
            </p>
          </div>
          <dl className="capx-pm-project-header__stats">
            <div>
              <dt>Dominant stage</dt>
              <dd>{project.dominantStage}</dd>
            </div>
            <div>
              <dt>Blockers</dt>
              <dd>{project.openBlockers}</dd>
            </div>
            <div>
              <dt>Open tasks</dt>
              <dd>{project.openTasks}</dd>
            </div>
            <div>
              <dt>Evidence</dt>
              <dd>
                <span className="capx-pm-chip-row">
                  <CapxPmStatusChip status={getCapxPmEvidenceStatus(project.evidenceFreshness)} />
                  <span>{project.evidenceFreshness}</span>
                </span>
              </dd>
            </div>
            <div>
              <dt>Snapshot</dt>
              <dd>{project.snapshotReadiness}</dd>
            </div>
          </dl>
        </section>

        <section className="capx-pm-mobile-priority" aria-label="Mobile PM priority">
          <article>
            <p className="capx-pm-eyebrow">Urgent blocker</p>
            <div>
              <CapxPmStatusChip status={project.status} />
              <strong>{project.blockerSummary}</strong>
            </div>
          </article>
          <article>
            <p className="capx-pm-eyebrow">Next PM task</p>
            {priorityTask ? (
              <div>
                <CapxPmStatusChip status={priorityTask.status} />
                <span>
                  <strong>{priorityTask.title}</strong>
                  {priorityTask.owner} / {priorityTask.due}
                </span>
              </div>
            ) : (
              <div>
                <CapxPmStatusChip status="neutral" />
                <strong>No active PM task in this mock step.</strong>
              </div>
            )}
          </article>
        </section>

        <CapxPmProjectStepRail steps={viewModel.steps} />

        <section className="capx-pm-step-summary" aria-labelledby="capx-pm-step-title">
          <div>
            <p className="capx-pm-eyebrow">{viewModel.step.workflowId}</p>
            <h2 id="capx-pm-step-title">{viewModel.step.title}</h2>
            <p>{viewModel.step.pmQuestion}</p>
          </div>
          <div className="capx-pm-step-summary__status">
            <CapxPmStatusChip status={viewModel.stepState.status} />
            <span>{viewModel.stepState.summary}</span>
          </div>
        </section>

        <section className="capx-pm-workspace-grid">
          <section className="capx-pm-step-main" aria-label={`${viewModel.step.shortTitle} workpage`}>
            <CapxPmSelectedStepPage viewModel={viewModel} />
          </section>

          <aside className="capx-pm-right-rail" aria-label="CAPX PM task, evidence, and handoff rail">
            <section className="capx-pm-panel">
              <div className="capx-pm-panel__header">
                <h2>Assigned tasks</h2>
                <span>{viewModel.stepState.tasks.length}</span>
              </div>
              <div className="capx-pm-task-list">
                {viewModel.stepState.tasks.length > 0 ? (
                  viewModel.stepState.tasks.map((task) => (
                    <article key={task.id} className={`capx-pm-task-card capx-pm-task-card--${task.status}`}>
                      <div>
                        <strong>{task.title}</strong>
                        <CapxPmStatusChip status={task.status} />
                      </div>
                      <dl>
                        <div>
                          <dt>Owner</dt>
                          <dd>{task.owner}</dd>
                        </div>
                        <div>
                          <dt>Due</dt>
                          <dd>{task.due}</dd>
                        </div>
                        <div>
                          <dt>Basis</dt>
                          <dd>{task.evidenceBasis}</dd>
                        </div>
                        <div>
                          <dt>Consequence</dt>
                          <dd>{task.consequence}</dd>
                        </div>
                      </dl>
                    </article>
                  ))
                ) : (
                  <p className="capx-pm-empty-note">No active PM task in this mock step.</p>
                )}
              </div>
            </section>

            <section className="capx-pm-panel">
              <div className="capx-pm-panel__header">
                <h2>Evidence packets</h2>
                <span>{viewModel.stepState.evidencePackets.length}</span>
              </div>
              <div className="capx-pm-evidence-list">
                {viewModel.stepState.evidencePackets.map((packet) => (
                  <article key={packet.id}>
                    <strong>{packet.title}</strong>
                    <dl>
                      <div>
                        <dt>Freshness</dt>
                        <dd>{packet.freshness}</dd>
                      </div>
                      <div>
                        <dt>Sources</dt>
                        <dd>{packet.sourceCount}</dd>
                      </div>
                      <div>
                        <dt>Unresolved refs</dt>
                        <dd>{packet.unresolvedRefs}</dd>
                      </div>
                    </dl>
                  </article>
                ))}
              </div>
            </section>

            <section className="capx-pm-panel">
              <div className="capx-pm-panel__header">
                <h2>Flags & handoff</h2>
                <span>{viewModel.stepState.flags.length}</span>
              </div>
              <div className="capx-pm-flag-list">
                {viewModel.stepState.flags.map((flag) => (
                  <article key={flag.id}>
                    <CapxPmStatusChip status={flag.status} />
                    <span>
                      <strong>{flag.label}</strong>
                      {flag.basis}
                    </span>
                  </article>
                ))}
              </div>
              <dl className="capx-pm-handoff">
                <div>
                  <dt>Target</dt>
                  <dd>{viewModel.stepState.handoff.target}</dd>
                </div>
                <div>
                  <dt>Required basis</dt>
                  <dd>{viewModel.stepState.handoff.requiredBasis}</dd>
                </div>
                <div>
                  <dt>Next check</dt>
                  <dd>{viewModel.stepState.handoff.nextCheck}</dd>
                </div>
              </dl>
            </section>
          </aside>
        </section>
      </main>
    </CapxPmProjectShell>
  );
}
