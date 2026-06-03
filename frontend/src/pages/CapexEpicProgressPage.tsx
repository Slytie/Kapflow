import { useMemo } from "react";
import { useSearchParams } from "react-router-dom";

import rawProgressData from "@/data/capexEpicProgressData.json";
import "./CapexEpicProgressPage.css";

type ProgressStatus = "done" | "in_progress" | "not_started" | "blocked" | "needs_review";
type CompletionTimestampStatus = "recorded" | "missing_historical" | "not_applicable";
type CompletionTimestampSource = "task_frontmatter" | "grandfathered_missing" | "not_completed";
type EstimateConfidence = "complete" | "insufficient_history" | "low" | "medium";

type CapexEstimate = {
  percentComplete: number;
  completedTasks: number;
  remainingTasks: number;
  remainingBlockedOrReviewTasks: number;
  completedWithTimestamps: number;
  completionTimestampCoverage: number;
  etaDate: string | null;
  etaConfidence: EstimateConfidence;
  etaSource: string;
  label: string;
  caveat: string;
};

type CapexTask = {
  id: string;
  epicId: string;
  title: string;
  plainPurpose: string;
  sourceStatus: string;
  displayStatus: ProgressStatus;
  statusReason: string;
  why: string[];
  scope: string[];
  outOfScope: string[];
  dependsOn: string[];
  owners: string[];
  reviewers: string[];
  risk: string;
  verification: string[];
  acceptanceCriteria: string[];
  sourceRow: Record<string, string>;
  evidence: string[];
  taskPath: string;
  completedAt: string | null;
  completionTimestampStatus: CompletionTimestampStatus;
  completionTimestampSource: CompletionTimestampSource;
};

type CapexEpic = {
  id: string;
  title: string;
  plainPurpose: string;
  displayStatus: ProgressStatus;
  reviewPosture: string;
  dependencies: string[];
  inScope: string[];
  outOfScope: string[];
  sourceReferences: string[];
  counts: Record<ProgressStatus | "total", number>;
  taskCount: number;
  epicPath: string;
  estimate: CapexEstimate;
  tasks: CapexTask[];
};

type CapexProgressData = {
  schemaVersion: string;
  meta: {
    title: string;
    subtitle: string;
    lastUpdated: string;
    sourceNote: string;
    codexRule: string;
  };
  summary: Record<ProgressStatus | "epicCount" | "taskCount" | "total", number> & {
    estimate: CapexEstimate;
  };
  activationBlockers: Array<{ id: string; plain: string; action: string }>;
  epics: CapexEpic[];
};

const progressData = rawProgressData as CapexProgressData;

const STATUS_LABELS: Record<ProgressStatus, string> = {
  done: "Done",
  in_progress: "In progress",
  not_started: "Not started",
  blocked: "Blocked",
  needs_review: "Needs fresh check"
};

const STATUS_FILTERS: Array<ProgressStatus | "all"> = [
  "all",
  "done",
  "in_progress",
  "needs_review",
  "blocked",
  "not_started"
];

const ESTIMATE_CONFIDENCE_LABELS: Record<EstimateConfidence, string> = {
  complete: "Complete",
  insufficient_history: "Needs timestamp history",
  low: "Low confidence",
  medium: "Medium confidence"
};

function statusClass(status: ProgressStatus): string {
  return status.replace("_", "-");
}

function matchesText(value: string, query: string): boolean {
  return value.toLowerCase().includes(query);
}

function taskMatches(task: CapexTask, query: string, statusFilter: string): boolean {
  const statusMatch = statusFilter === "all" || task.displayStatus === statusFilter;
  if (!statusMatch) {
    return false;
  }
  if (!query) {
    return true;
  }
  return [
    task.id,
    task.title,
    task.plainPurpose,
    task.statusReason,
    task.sourceStatus,
    task.taskPath,
    ...task.scope,
    ...task.acceptanceCriteria
  ].some((value) => matchesText(value, query));
}

function epicMatches(epic: CapexEpic, query: string, statusFilter: string): boolean {
  const epicStatusMatch = statusFilter === "all" || epic.displayStatus === statusFilter;
  const matchingTask = epic.tasks.some((task) => taskMatches(task, query, statusFilter));
  if (!query) {
    return epicStatusMatch || matchingTask;
  }
  const textMatch = [
    epic.id,
    epic.title,
    epic.plainPurpose,
    epic.reviewPosture,
    epic.epicPath,
    ...epic.inScope,
    ...epic.outOfScope
  ].some((value) => matchesText(value, query));
  return (epicStatusMatch && textMatch) || matchingTask;
}

function countByStatus(items: Array<{ displayStatus: ProgressStatus }>): Record<ProgressStatus, number> {
  return items.reduce(
    (counts, item) => ({
      ...counts,
      [item.displayStatus]: counts[item.displayStatus] + 1
    }),
    {
      done: 0,
      in_progress: 0,
      not_started: 0,
      blocked: 0,
      needs_review: 0
    }
  );
}

function formatPercent(value: number): string {
  return `${Number.isInteger(value) ? value.toFixed(0) : value.toFixed(1)}%`;
}

function completionTimestampLabel(task: CapexTask): string {
  if (task.completedAt) {
    return task.completedAt;
  }
  if (task.completionTimestampStatus === "missing_historical") {
    return "Completion timestamp missing for historical DONE task";
  }
  return "Not completed yet";
}

function setSearchParam(
  searchParams: URLSearchParams,
  updates: Record<string, string | null>
): URLSearchParams {
  const next = new URLSearchParams(searchParams);
  Object.entries(updates).forEach(([key, value]) => {
    if (value === null || value === "") {
      next.delete(key);
      return;
    }
    next.set(key, value);
  });
  return next;
}

function DetailList({ title, items }: { title: string; items: string[] }): JSX.Element | null {
  if (items.length === 0) {
    return null;
  }
  return (
    <section className="capex-task-detail__section">
      <h4>{title}</h4>
      <ul>
        {items.map((item) => (
          <li key={item}>{item}</li>
        ))}
      </ul>
    </section>
  );
}

function StatusChip({ status }: { status: ProgressStatus }): JSX.Element {
  return (
    <span className={`capex-status capex-status--${statusClass(status)}`}>
      {STATUS_LABELS[status]}
    </span>
  );
}

function EstimateStrip({ estimate }: { estimate: CapexEstimate }): JSX.Element {
  return (
    <div className="capex-estimate-strip" aria-label="Completion estimate">
      <span>{formatPercent(estimate.percentComplete)} complete</span>
      <span>{estimate.remainingTasks} remaining</span>
      <span>{estimate.label}</span>
    </div>
  );
}

export function CapexEpicProgressPage(): JSX.Element {
  const [searchParams, setSearchParams] = useSearchParams();
  const query = searchParams.get("q")?.trim().toLowerCase() ?? "";
  const statusFilter = searchParams.get("status") ?? "all";
  const requestedEpicId = searchParams.get("epic") ?? "";
  const requestedTaskId = searchParams.get("task") ?? "";

  const allTasks = useMemo(() => progressData.epics.flatMap((epic) => epic.tasks), []);
  const requestedTask = allTasks.find((task) => task.id === requestedTaskId) ?? null;
  const selectedEpic =
    progressData.epics.find((epic) => epic.id === requestedEpicId) ??
    progressData.epics.find((epic) => epic.id === requestedTask?.epicId) ??
    progressData.epics[0];
  const selectedTask =
    selectedEpic.tasks.find((task) => task.id === requestedTaskId) ?? null;

  const filteredEpics = progressData.epics.filter((epic) =>
    epicMatches(epic, query, statusFilter)
  );
  const filteredTasks = selectedEpic.tasks.filter((task) =>
    taskMatches(task, query, statusFilter)
  );
  const epicStatusCounts = countByStatus(progressData.epics);

  const selectEpic = (epicId: string): void => {
    setSearchParams(setSearchParam(searchParams, { epic: epicId, task: null }));
  };
  const selectTask = (taskId: string): void => {
    setSearchParams(
      setSearchParam(searchParams, {
        epic: selectedEpic.id,
        task: taskId
      })
    );
  };

  return (
    <main className="capex-progress-page" data-testid="capex-epic-progress-page">
      <header className="capex-progress-page__header">
        <div>
          <p className="capex-progress-page__eyebrow">Local CAPEX roadmap</p>
          <h1>{progressData.meta.title}</h1>
          <p>{progressData.meta.subtitle}</p>
        </div>
        <div className="capex-progress-page__meta">
          <strong>Local only</strong>
          <span>Updated {progressData.meta.lastUpdated}</span>
        </div>
      </header>

      <section className="capex-summary" aria-label="CAPEX progress summary">
        <article>
          <span>Epics</span>
          <strong>{progressData.summary.epicCount}</strong>
        </article>
        <article>
          <span>Tasks</span>
          <strong>{progressData.summary.taskCount}</strong>
        </article>
        <article>
          <span>Done</span>
          <strong>{progressData.summary.done}</strong>
        </article>
        <article>
          <span>Needs fresh check</span>
          <strong>{progressData.summary.needs_review}</strong>
        </article>
        <article>
          <span>Blocked</span>
          <strong>{progressData.summary.blocked}</strong>
        </article>
        <article>
          <span>Not started</span>
          <strong>{progressData.summary.not_started}</strong>
        </article>
        <article>
          <span>Complete</span>
          <strong>{formatPercent(progressData.summary.estimate.percentComplete)}</strong>
        </article>
        <article>
          <span>Remaining</span>
          <strong>{progressData.summary.estimate.remainingTasks}</strong>
        </article>
        <article>
          <span>ETA</span>
          <strong>{progressData.summary.estimate.etaDate ?? "TBD"}</strong>
        </article>
      </section>

      <section className="capex-controls" aria-label="CAPEX filters">
        <label>
          <span>Search</span>
          <input
            type="search"
            value={searchParams.get("q") ?? ""}
            placeholder="EPIC, TASK, title, evidence"
            onChange={(event) => {
              setSearchParams(setSearchParam(searchParams, { q: event.target.value }));
            }}
          />
        </label>
        <div className="capex-filter-buttons" role="group" aria-label="Status filter">
          {STATUS_FILTERS.map((status) => (
            <button
              key={status}
              type="button"
              className={statusFilter === status ? "is-active" : ""}
              onClick={() => {
                setSearchParams(
                  setSearchParam(searchParams, {
                    status: status === "all" ? null : status
                  })
                );
              }}
            >
              {status === "all" ? "All" : STATUS_LABELS[status]}
            </button>
          ))}
        </div>
      </section>

      <section className="capex-roadmap">
        <aside className="capex-roadmap__timeline" aria-label="CAPEX epic timeline">
          <div className="capex-roadmap__section-heading">
            <h2>Epic Timeline</h2>
            <span>{filteredEpics.length} shown</span>
          </div>
          <div className="capex-timeline-rail" data-testid="capex-epic-timeline">
            {filteredEpics.map((epic) => (
              <button
                key={epic.id}
                type="button"
                className={`capex-epic-card ${
                  epic.id === selectedEpic.id ? "is-selected" : ""
                }`}
                onClick={() => selectEpic(epic.id)}
              >
                <span className="capex-epic-card__id">{epic.id}</span>
                <strong>{epic.title.replace(/^CAPEX\s+/i, "")}</strong>
                <span>{epic.plainPurpose}</span>
                <EstimateStrip estimate={epic.estimate} />
                <StatusChip status={epic.displayStatus} />
              </button>
            ))}
          </div>
          <div className="capex-epic-status-summary" aria-label="Epic status summary">
            {STATUS_FILTERS.filter((status): status is ProgressStatus => status !== "all").map(
              (status) => (
                <span key={status}>
                  {STATUS_LABELS[status]}: {epicStatusCounts[status]}
                </span>
              )
            )}
          </div>
        </aside>

        <section className="capex-roadmap__tasks" aria-label="Selected epic tasks">
          <div className="capex-roadmap__section-heading">
            <div>
              <p className="capex-progress-page__eyebrow">{selectedEpic.id}</p>
              <h2>{selectedEpic.title}</h2>
            </div>
            <StatusChip status={selectedEpic.displayStatus} />
          </div>
          <p className="capex-epic-purpose">{selectedEpic.plainPurpose}</p>
          <p className="capex-review-posture">{selectedEpic.reviewPosture}</p>
          <section className="capex-estimate-panel" aria-label={`${selectedEpic.id} completion estimate`}>
            <div className="capex-estimate-panel__header">
              <div>
                <p className="capex-progress-page__eyebrow">Completion estimate</p>
                <h3>{selectedEpic.estimate.label}</h3>
              </div>
              <strong>{formatPercent(selectedEpic.estimate.percentComplete)}</strong>
            </div>
            <div
              className="capex-estimate-bar"
              aria-label={`${formatPercent(selectedEpic.estimate.percentComplete)} complete`}
            >
              <span style={{ width: `${selectedEpic.estimate.percentComplete}%` }} />
            </div>
            <dl className="capex-estimate-facts">
              <div>
                <dt>Completed</dt>
                <dd>{selectedEpic.estimate.completedTasks}</dd>
              </div>
              <div>
                <dt>Remaining</dt>
                <dd>{selectedEpic.estimate.remainingTasks}</dd>
              </div>
              <div>
                <dt>Blocked / review</dt>
                <dd>{selectedEpic.estimate.remainingBlockedOrReviewTasks}</dd>
              </div>
              <div>
                <dt>Timestamp coverage</dt>
                <dd>
                  {selectedEpic.estimate.completedWithTimestamps} done task(s),{" "}
                  {formatPercent(selectedEpic.estimate.completionTimestampCoverage)}
                </dd>
              </div>
              <div>
                <dt>ETA confidence</dt>
                <dd>{ESTIMATE_CONFIDENCE_LABELS[selectedEpic.estimate.etaConfidence]}</dd>
              </div>
            </dl>
            <p>{selectedEpic.estimate.caveat}</p>
          </section>
          <div className="capex-task-counts" aria-label={`${selectedEpic.id} task counts`}>
            {STATUS_FILTERS.filter((status): status is ProgressStatus => status !== "all").map(
              (status) => (
                <span key={status}>
                  {STATUS_LABELS[status]} {selectedEpic.counts[status]}
                </span>
              )
            )}
          </div>

          <div className="capex-task-list" data-testid="capex-task-list">
            {filteredTasks.length === 0 ? (
              <p className="capex-empty">No tasks match the current filter.</p>
            ) : (
              filteredTasks.map((task) => (
                <button
                  key={task.id}
                  type="button"
                  className={`capex-task-row ${
                    task.id === selectedTask?.id ? "is-selected" : ""
                  }`}
                  onClick={() => selectTask(task.id)}
                >
                  <span>{task.id}</span>
                  <strong>{task.title}</strong>
                  <small>{task.plainPurpose}</small>
                  <StatusChip status={task.displayStatus} />
                </button>
              ))
            )}
          </div>
        </section>

        <aside className="capex-task-detail" aria-label="Task details">
          {selectedTask ? (
            <>
              <div className="capex-task-detail__header">
                <p className="capex-progress-page__eyebrow">{selectedTask.id}</p>
                <h2>{selectedTask.title}</h2>
                <StatusChip status={selectedTask.displayStatus} />
              </div>
              <p className="capex-task-detail__purpose">{selectedTask.plainPurpose}</p>
              <dl className="capex-task-detail__facts">
                <div>
                  <dt>Source status</dt>
                  <dd>{selectedTask.sourceStatus}</dd>
                </div>
                <div>
                  <dt>Reason</dt>
                  <dd>{selectedTask.statusReason}</dd>
                </div>
                <div>
                  <dt>Risk</dt>
                  <dd>{selectedTask.risk}</dd>
                </div>
                <div>
                  <dt>Completed at</dt>
                  <dd>{completionTimestampLabel(selectedTask)}</dd>
                </div>
                <div>
                  <dt>Task file</dt>
                  <dd>{selectedTask.taskPath}</dd>
                </div>
              </dl>
              <DetailList title="Why" items={selectedTask.why} />
              <DetailList title="Scope" items={selectedTask.scope} />
              <DetailList title="Verification" items={selectedTask.verification} />
              <DetailList title="Acceptance Criteria" items={selectedTask.acceptanceCriteria} />
              <DetailList title="Evidence" items={selectedTask.evidence} />
              <DetailList title="Out Of Scope" items={selectedTask.outOfScope} />
              {Object.keys(selectedTask.sourceRow).length > 0 ? (
                <section className="capex-task-detail__section">
                  <h4>Source Row</h4>
                  <dl className="capex-task-detail__source-row">
                    {Object.entries(selectedTask.sourceRow).map(([key, value]) => (
                      <div key={key}>
                        <dt>{key.replace(/_/g, " ")}</dt>
                        <dd>{value}</dd>
                      </div>
                    ))}
                  </dl>
                </section>
              ) : null}
            </>
          ) : (
            <div className="capex-task-detail__empty">
              <h2>Task Details</h2>
              <p>Select a task from {selectedEpic.id} to inspect its scope and evidence context.</p>
            </div>
          )}
        </aside>
      </section>

      <section className="capex-blockers" aria-label="Known activation blockers">
        <div className="capex-roadmap__section-heading">
          <h2>Known Safety Blockers</h2>
          <span>CAPEX activation remains gated</span>
        </div>
        <div className="capex-blockers__grid">
          {progressData.activationBlockers.map((blocker) => (
            <article key={blocker.id}>
              <strong>{blocker.id}</strong>
              <p>{blocker.plain}</p>
              <small>{blocker.action}</small>
            </article>
          ))}
        </div>
      </section>

      <footer className="capex-progress-page__footer">
        <p>{progressData.meta.sourceNote}</p>
        <p>{progressData.meta.codexRule}</p>
      </footer>
    </main>
  );
}
