import { Link, Navigate, useParams } from "react-router-dom";

import { CapxPmPracticalShell } from "./CapxPmPracticalShell";
import { CapxPmPracticalStatusChip } from "./CapxPmPracticalStatusChip";
import { CapxPmStepRail } from "./CapxPmStepRail";
import { capxPmPracticalDemoState } from "./capxPmPracticalMockData";
import type {
  CapxPmPracticalChecklistItem,
  CapxPmPracticalProject,
  CapxPmPracticalRecord,
  CapxPmPracticalStepState
} from "./capxPmPracticalTypes";
import {
  buildCapxPmPracticalProjectHref,
  buildCapxPmPracticalStepHref,
  buildCapxPmPracticalWorkspaceViewModel,
  getCapxPmPracticalDefaultStep,
  getCapxPmPracticalProject,
  isCapxPmPracticalStepSlug
} from "./capxPmPracticalViewModels";

function HeaderCell({ label, value }: { label: string; value: string | number }): JSX.Element {
  return (
    <div className="capx-pm-practical-header-cell">
      <span>{label}</span>
      <strong>{value}</strong>
    </div>
  );
}

function NotFoundState({
  testId,
  heading,
  body,
  linkHref,
  linkLabel
}: {
  testId: string;
  heading: string;
  body: string;
  linkHref: string;
  linkLabel: string;
}): JSX.Element {
  return (
    <CapxPmPracticalShell title="PM Project Workspace" updatedAt={capxPmPracticalDemoState.generatedAt}>
      <main className="capx-pm-practical-not-found" data-testid={testId}>
        <h1>{heading}</h1>
        <p>{body}</p>
        <Link to={linkHref}>{linkLabel}</Link>
      </main>
    </CapxPmPracticalShell>
  );
}

function ProjectHeader({ project }: { project: CapxPmPracticalProject }): JSX.Element {
  return (
    <section className="capx-pm-practical-workspace-header" aria-label="Project summary">
      <div className="capx-pm-practical-project-title">
        <Link className="capx-pm-practical-back-link" to="/demo/capx/pm/projects">
          Back to project list
        </Link>
        <h2>
          {project.id} {project.name}
        </h2>
        <p>
          {project.siteArea} | PM {project.pm} | Sponsor {project.sponsor}
        </p>
      </div>
      <div className="capx-pm-practical-header-grid">
        <HeaderCell label="Current phase" value={project.phase} />
        <HeaderCell label="Top blocker" value={project.topBlocker} />
        <HeaderCell label="Tasks due this week" value={project.tasksDue} />
        <HeaderCell label="Report status" value={project.reportStatus} />
        <HeaderCell label="Last material change" value={project.lastMaterialChange} />
        <HeaderCell label="Blockers" value={project.blockers} />
        <HeaderCell label="Missing documents" value={project.missingDocuments} />
        <HeaderCell label="Last update" value={project.lastUpdate} />
      </div>
    </section>
  );
}

function StepCards({ stepState }: { stepState: CapxPmPracticalStepState }): JSX.Element {
  return (
    <section className="capx-pm-practical-section" aria-labelledby="capx-pm-step-card-title">
      <div className="capx-pm-practical-section__head">
        <h2 id="capx-pm-step-card-title">{stepState.cardsTitle}</h2>
        <p>Current PM view</p>
      </div>
      <div className="capx-pm-practical-step-card-grid">
        {stepState.cards.map((card) => (
          <article className="capx-pm-practical-step-card" key={card.title}>
            <h3>{card.title}</h3>
            <strong>{card.value}</strong>
            <p>{card.body}</p>
            <CapxPmPracticalStatusChip status={card.status} />
          </article>
        ))}
      </div>
    </section>
  );
}

function ChecklistMobileCard({ item }: { item: CapxPmPracticalChecklistItem }): JSX.Element {
  return (
    <article className="capx-pm-practical-mobile-card">
      <div className="capx-pm-practical-mobile-card__head">
        <strong>{item.label}</strong>
        <CapxPmPracticalStatusChip status={item.status} />
      </div>
      <div className="capx-pm-practical-mobile-card__row">
        <span>Owner</span>
        <strong>{item.owner}</strong>
      </div>
    </article>
  );
}

function Checklist({ stepState }: { stepState: CapxPmPracticalStepState }): JSX.Element {
  return (
    <section className="capx-pm-practical-section" aria-labelledby="capx-pm-checklist-title">
      <div className="capx-pm-practical-section__head">
        <h2 id="capx-pm-checklist-title">{stepState.checklistTitle}</h2>
        <p>Owner and current state</p>
      </div>
      <div className="capx-pm-practical-table-wrap">
        <table className="capx-pm-practical-table">
          <thead>
            <tr>
              <th scope="col">Item</th>
              <th scope="col">Owner</th>
              <th scope="col">State</th>
            </tr>
          </thead>
          <tbody>
            {stepState.checklist.map((item) => (
              <tr key={item.label}>
                <td>{item.label}</td>
                <td>{item.owner}</td>
                <td>
                  <CapxPmPracticalStatusChip status={item.status} />
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <div className="capx-pm-practical-mobile-list" data-testid="capx-pm-practical-mobile-checklist">
        {stepState.checklist.map((item) => (
          <ChecklistMobileCard item={item} key={item.label} />
        ))}
      </div>
    </section>
  );
}

function RecordMobileCard({ record }: { record: CapxPmPracticalRecord }): JSX.Element {
  return (
    <article className="capx-pm-practical-mobile-card">
      <div className="capx-pm-practical-mobile-card__head">
        <strong>{record.item}</strong>
        <CapxPmPracticalStatusChip status={record.status} />
      </div>
      <div className="capx-pm-practical-mobile-card__row">
        <span>Owner</span>
        <strong>{record.owner}</strong>
      </div>
      <div className="capx-pm-practical-mobile-card__row">
        <span>Due</span>
        <strong>{record.due}</strong>
      </div>
      <div className="capx-pm-practical-mobile-card__row">
        <span>Supporting file</span>
        <strong>{record.supportingFile}</strong>
      </div>
      <p className="capx-pm-practical-muted">{record.note}</p>
    </article>
  );
}

function Records({ stepState }: { stepState: CapxPmPracticalStepState }): JSX.Element {
  return (
    <section className="capx-pm-practical-section" aria-labelledby="capx-pm-records-title">
      <div className="capx-pm-practical-section__head">
        <h2 id="capx-pm-records-title">{stepState.tableTitle}</h2>
        <p>What is wrong, who owns it, and why it matters</p>
      </div>
      <div className="capx-pm-practical-table-wrap">
        <table className="capx-pm-practical-table">
          <thead>
            <tr>
              <th scope="col">What is wrong or missing</th>
              <th scope="col">Owner</th>
              <th scope="col">Due date</th>
              <th scope="col">Supporting file / reason</th>
              <th scope="col">Consequence</th>
              <th scope="col">State</th>
            </tr>
          </thead>
          <tbody>
            {stepState.records.map((record) => (
              <tr key={record.id}>
                <td>{record.item}</td>
                <td>{record.owner}</td>
                <td>{record.due}</td>
                <td>{record.supportingFile}</td>
                <td>{record.note}</td>
                <td>
                  <CapxPmPracticalStatusChip status={record.status} />
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <div className="capx-pm-practical-mobile-list" data-testid="capx-pm-practical-mobile-records">
        {stepState.records.map((record) => (
          <RecordMobileCard record={record} key={record.id} />
        ))}
      </div>
    </section>
  );
}

function StepBody({
  selectedStepLabel,
  selectedStepQuestion,
  stepState
}: {
  selectedStepLabel: string;
  selectedStepQuestion: string;
  stepState: CapxPmPracticalStepState;
}): JSX.Element {
  return (
    <div className="capx-pm-practical-step-main" data-testid={`capx-pm-practical-step-${stepState.slug}`}>
      <section className="capx-pm-practical-step-hero">
        <p className="capx-pm-practical-eyebrow">{selectedStepQuestion}</p>
        <h2>{selectedStepLabel}</h2>
        <strong className="capx-pm-practical-step-headline">{stepState.headline}</strong>
        <p>{stepState.summary}</p>
        <div className="capx-pm-practical-urgent">
          <span>Next PM action</span>
          <strong>{stepState.primaryAction.title}</strong>
          <p>
            Owner {stepState.primaryAction.owner} | Due {stepState.primaryAction.due} | File{" "}
            {stepState.primaryAction.supportingFile}
          </p>
        </div>
      </section>
      <StepCards stepState={stepState} />
      <Checklist stepState={stepState} />
      <Records stepState={stepState} />
    </div>
  );
}

function RightRail({ stepState }: { stepState: CapxPmPracticalStepState }): JSX.Element {
  const task = stepState.primaryAction;

  return (
    <aside className="capx-pm-practical-right-rail" aria-label="PM action details">
      <section className="capx-pm-practical-right-card">
        <h3>Next action detail</h3>
        <div className="capx-pm-practical-task-detail">
          <div>
            <span>Task</span>
            <strong>{task.title}</strong>
          </div>
          <div>
            <span>Owner</span>
            <strong>{task.owner}</strong>
          </div>
          <div>
            <span>Due</span>
            <strong>{task.due}</strong>
          </div>
          <div>
            <span>File / reason</span>
            <strong>{task.supportingFile}</strong>
          </div>
          <div>
            <span>Consequence</span>
            <strong>{task.consequence}</strong>
          </div>
        </div>
      </section>

      <section className="capx-pm-practical-right-card">
        <h3>Supporting files</h3>
        <ul>
          {stepState.supportingFiles.map((file) => (
            <li key={file}>{file}</li>
          ))}
        </ul>
      </section>

      <section className="capx-pm-practical-right-card">
        <h3>Report note</h3>
        <p>{stepState.reportNote}</p>
      </section>

      <section className="capx-pm-practical-right-card">
        <h3>Read-only demo</h3>
        <p>Simulated only. This button does not update project records or send a report.</p>
        <button type="button" disabled data-testid="capx-pm-practical-disabled-action">
          Simulated action
        </button>
      </section>
    </aside>
  );
}

export function CapxPmProjectWorkspacePage(): JSX.Element {
  const { projectId, stepId } = useParams();
  const project = getCapxPmPracticalProject(projectId);

  if (!project) {
    return (
      <NotFoundState
        testId="capx-pm-practical-project-not-found"
        heading="Project not found"
        body="This mock project ID is not in the local PM demo data."
        linkHref="/demo/capx/pm/projects"
        linkLabel="Back to PM projects"
      />
    );
  }

  if (!stepId) {
    return <Navigate to={buildCapxPmPracticalStepHref(project, getCapxPmPracticalDefaultStep(project))} replace />;
  }

  if (!isCapxPmPracticalStepSlug(stepId)) {
    return (
      <NotFoundState
        testId="capx-pm-practical-step-not-found"
        heading="Step not found"
        body="This mock step is not part of the seven-step PM project workspace."
        linkHref={buildCapxPmPracticalStepHref(project, getCapxPmPracticalDefaultStep(project))}
        linkLabel="Open active step"
      />
    );
  }

  const viewModel = buildCapxPmPracticalWorkspaceViewModel(project, stepId);

  return (
    <CapxPmPracticalShell title="PM Project Workspace" updatedAt={viewModel.generatedAt}>
      <main data-testid="capx-pm-practical-workspace-page">
        <ProjectHeader project={viewModel.project} />
        <CapxPmStepRail project={viewModel.project} selectedStepSlug={viewModel.selectedStep.slug} />
        <div className="capx-pm-practical-workbench">
          <StepBody
            selectedStepLabel={viewModel.selectedStep.label}
            selectedStepQuestion={viewModel.selectedStep.question}
            stepState={viewModel.selectedStepState}
          />
          <RightRail stepState={viewModel.selectedStepState} />
        </div>
        <div className="capx-pm-practical-visually-hidden">
          <Link to={buildCapxPmPracticalProjectHref(project)}>Project route</Link>
        </div>
      </main>
    </CapxPmPracticalShell>
  );
}
