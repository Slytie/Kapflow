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

type CompletionTrendPoint = {
  key: string;
  label: string;
  completedOnPoint: number;
  cumulativeCompleted: number;
  percentComplete: number;
  isUndatedBaseline: boolean;
  isAsOfMarker: boolean;
};

type CompletionTrend = {
  points: CompletionTrendPoint[];
  recordedCompletionCount: number;
  undatedDoneCount: number;
};

const progressData = rawProgressData as CapexProgressData;

const MONTH_LABELS = [
  "Jan",
  "Feb",
  "Mar",
  "Apr",
  "May",
  "Jun",
  "Jul",
  "Aug",
  "Sep",
  "Oct",
  "Nov",
  "Dec"
];

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

function formatTrendPercent(value: number): string {
  return `${value.toFixed(1)}%`;
}

function progressWidth(value: number): string {
  return `${Math.min(Math.max(value, 0), 100)}%`;
}

function formatDateKey(dateKey: string): string {
  const [year, month, day] = dateKey.split("-").map(Number);
  if (!year || !month || !day) {
    return dateKey;
  }
  return `${MONTH_LABELS[month - 1]} ${String(day).padStart(2, "0")}`;
}

function etaLabel(dateKey: string): string {
  return `ETA ${formatDateKey(dateKey)}`;
}

function buildCompletionTrend(
  tasks: CapexTask[],
  totalTasks: number,
  asOfDate: string
): CompletionTrend {
  const timestampedDoneTasks = tasks.filter(
    (task) => task.displayStatus === "done" && task.completedAt
  );
  const undatedDoneCount = tasks.filter(
    (task) => task.displayStatus === "done" && !task.completedAt
  ).length;
  const completionsByDay = timestampedDoneTasks.reduce<Record<string, number>>(
    (counts, task) => {
      const day = task.completedAt?.slice(0, 10);
      if (!day) {
        return counts;
      }
      return {
        ...counts,
        [day]: (counts[day] ?? 0) + 1
      };
    },
    {}
  );
  let cumulativeCompleted = 0;
  const points: CompletionTrendPoint[] = [];

  if (undatedDoneCount > 0) {
    cumulativeCompleted += undatedDoneCount;
    points.push({
      key: "undated",
      label: "Undated",
      completedOnPoint: undatedDoneCount,
      cumulativeCompleted,
      percentComplete: totalTasks > 0 ? (cumulativeCompleted / totalTasks) * 100 : 0,
      isUndatedBaseline: true,
      isAsOfMarker: false
    });
  }

  const completionDays = Object.keys(completionsByDay).sort();
  completionDays.forEach((day) => {
    const completedOnPoint = completionsByDay[day];
    cumulativeCompleted += completedOnPoint;
    points.push({
      key: day,
      label: formatDateKey(day),
      completedOnPoint,
      cumulativeCompleted,
      percentComplete: totalTasks > 0 ? (cumulativeCompleted / totalTasks) * 100 : 0,
      isUndatedBaseline: false,
      isAsOfMarker: false
    });
  });

  const lastCompletionDay = completionDays[completionDays.length - 1];
  const normalizedAsOfDate = /^\d{4}-\d{2}-\d{2}$/.test(asOfDate) ? asOfDate : "";
  if (normalizedAsOfDate && (!lastCompletionDay || normalizedAsOfDate > lastCompletionDay)) {
    points.push({
      key: `as-of-${normalizedAsOfDate}`,
      label: formatDateKey(normalizedAsOfDate),
      completedOnPoint: 0,
      cumulativeCompleted,
      percentComplete: totalTasks > 0 ? (cumulativeCompleted / totalTasks) * 100 : 0,
      isUndatedBaseline: false,
      isAsOfMarker: true
    });
  }

  if (points.length === 0) {
    points.push({
      key: "no-history",
      label: "No history",
      completedOnPoint: 0,
      cumulativeCompleted: 0,
      percentComplete: 0,
      isUndatedBaseline: false,
      isAsOfMarker: false
    });
  }

  return {
    points,
    recordedCompletionCount: timestampedDoneTasks.length,
    undatedDoneCount
  };
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

function SummaryMetric({ label, value }: { label: string; value: string | number }): JSX.Element {
  return (
    <article>
      <span>{label}</span>
      <strong>{value}</strong>
    </article>
  );
}

function RoadmapProgress({ estimate }: { estimate: CapexEstimate }): JSX.Element {
  return (
    <section className="capex-roadmap-progress" aria-label="CAPEX roadmap progress">
      <div className="capex-roadmap-progress__header">
        <div>
          <p className="capex-progress-page__eyebrow">Roadmap completion</p>
          <h2>{formatPercent(estimate.percentComplete)}</h2>
        </div>
        <span>{estimate.label}</span>
      </div>
      <div
        className="capex-roadmap-progress__bar"
        role="progressbar"
        aria-label="CAPEX roadmap completion"
        aria-valuemin={0}
        aria-valuemax={100}
        aria-valuenow={estimate.percentComplete}
        aria-valuetext={`${formatPercent(estimate.percentComplete)} complete, ${estimate.remainingTasks} remaining`}
      >
        <span style={{ width: progressWidth(estimate.percentComplete) }} />
      </div>
      <div className="capex-roadmap-progress__facts">
        <span>{estimate.completedTasks} completed</span>
        <span>{estimate.remainingTasks} remaining</span>
        <span>{estimate.remainingBlockedOrReviewTasks} blocked / review</span>
      </div>
      <p>{estimate.caveat}</p>
    </section>
  );
}

function CompletionTrendChart({
  trend,
  etaDate
}: {
  trend: CompletionTrend;
  etaDate: string | null;
}): JSX.Element {
  const width = 380;
  const height = 132;
  const margin = {
    top: 14,
    right: 16,
    bottom: 32,
    left: 42
  };
  const innerWidth = width - margin.left - margin.right;
  const innerHeight = height - margin.top - margin.bottom;
  const projectedPoint = etaDate
    ? {
        key: `projected-${etaDate}`,
        label: etaLabel(etaDate),
        percentComplete: 100
      }
    : null;
  const chartPointCount = trend.points.length + (projectedPoint ? 1 : 0);
  const xForPoint = (index: number, pointCount = chartPointCount): number => {
    if (pointCount === 1) {
      return margin.left + innerWidth / 2;
    }
    return margin.left + (index / (pointCount - 1)) * innerWidth;
  };
  const yForPercent = (percent: number): number =>
    margin.top + innerHeight - (Math.min(percent, 100) / 100) * innerHeight;
  const linePath = trend.points
    .map((point, index) => {
      const command = index === 0 ? "M" : "L";
      return `${command} ${xForPoint(index).toFixed(1)} ${yForPercent(point.percentComplete).toFixed(1)}`;
    })
    .join(" ");
  const latestPoint = trend.points[trend.points.length - 1];
  const projectedPath = projectedPoint
    ? [
        `M ${xForPoint(trend.points.length - 1).toFixed(1)} ${yForPercent(latestPoint.percentComplete).toFixed(1)}`,
        `L ${xForPoint(trend.points.length).toFixed(1)} ${yForPercent(projectedPoint.percentComplete).toFixed(1)}`
      ].join(" ")
    : "";

  return (
    <section className="capex-completion-trend" aria-label="CAPEX completion over time">
      <div className="capex-completion-trend__header">
        <div>
          <p className="capex-progress-page__eyebrow">Completion over time</p>
          <h2>{formatTrendPercent(latestPoint.percentComplete)} current</h2>
        </div>
        <span>{trend.recordedCompletionCount} timestamped completions</span>
      </div>
      <div className="capex-completion-trend__chart">
        <svg
          role="img"
          aria-label="CAPEX completion trend line"
          data-testid="capex-completion-trend-line"
          data-point-count={trend.points.length}
          data-projection-date={etaDate ?? ""}
          viewBox={`0 0 ${width} ${height}`}
        >
          <title>CAPEX completion trend line</title>
          <desc>
            Daily cumulative CAPEX completion percentage from recorded completed_at timestamps,
            with undated accepted tasks shown as a baseline and a dashed ETA projection to 100%.
          </desc>
          <line
            className="capex-completion-trend__axis"
            x1={margin.left}
            y1={margin.top}
            x2={margin.left}
            y2={margin.top + innerHeight}
          />
          <line
            className="capex-completion-trend__axis"
            x1={margin.left}
            y1={margin.top + innerHeight}
            x2={margin.left + innerWidth}
            y2={margin.top + innerHeight}
          />
          <line
            className="capex-completion-trend__grid"
            x1={margin.left}
            y1={yForPercent(100)}
            x2={margin.left + innerWidth}
            y2={yForPercent(100)}
          />
          <line
            className="capex-completion-trend__grid"
            x1={margin.left}
            y1={yForPercent(50)}
            x2={margin.left + innerWidth}
            y2={yForPercent(50)}
          />
          <text className="capex-completion-trend__label" x={6} y={yForPercent(100) + 4}>
            100%
          </text>
          <text className="capex-completion-trend__label" x={14} y={yForPercent(50) + 4}>
            50%
          </text>
          <text className="capex-completion-trend__label" x={26} y={margin.top + innerHeight + 4}>
            0%
          </text>
          <path className="capex-completion-trend__line" d={linePath} />
          {projectedPath ? (
            <path className="capex-completion-trend__line capex-completion-trend__line--projected" d={projectedPath} />
          ) : null}
          {trend.points.map((point, index) => {
            const x = xForPoint(index);
            const y = yForPercent(point.percentComplete);
            return (
              <g key={point.key}>
                <circle
                  className={
                    point.isUndatedBaseline
                      ? "capex-completion-trend__point capex-completion-trend__point--baseline"
                      : point.isAsOfMarker
                        ? "capex-completion-trend__point capex-completion-trend__point--as-of"
                      : "capex-completion-trend__point"
                  }
                  cx={x}
                  cy={y}
                  r={point.isUndatedBaseline ? 5 : 4}
                />
                <text
                  className="capex-completion-trend__tick"
                  x={x}
                  y={margin.top + innerHeight + 24}
                  textAnchor="middle"
                >
                  {point.label}
                </text>
                <text
                  className="capex-completion-trend__value"
                  x={x}
                  y={Math.max(14, y - 10)}
                  textAnchor="middle"
                >
                  {formatTrendPercent(point.percentComplete)}
                </text>
              </g>
            );
          })}
          {projectedPoint ? (
            <g key={projectedPoint.key}>
              <circle
                className="capex-completion-trend__point capex-completion-trend__point--projected"
                cx={xForPoint(trend.points.length)}
                cy={yForPercent(projectedPoint.percentComplete)}
                r={4}
              />
              <text
                className="capex-completion-trend__tick"
                x={xForPoint(trend.points.length)}
                y={margin.top + innerHeight + 24}
                textAnchor="middle"
              >
                {projectedPoint.label}
              </text>
            </g>
          ) : null}
        </svg>
      </div>
      <div className="capex-completion-trend__facts">
        <span>{trend.undatedDoneCount} undated baseline</span>
        <span>{latestPoint.cumulativeCompleted} done</span>
        {projectedPoint ? (
          <span>
            {latestPoint.label} to {projectedPoint.label} at 100%
          </span>
        ) : null}
      </div>
    </section>
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
  const completionTrend = useMemo(
    () => buildCompletionTrend(allTasks, progressData.summary.taskCount, progressData.meta.lastUpdated),
    [allTasks]
  );

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
        <div
          className="capex-summary__metrics"
          role="group"
          aria-label="CAPEX progress metrics"
        >
          <div className="capex-summary__stack">
            <SummaryMetric label="Epics" value={progressData.summary.epicCount} />
            <SummaryMetric label="Tasks" value={progressData.summary.taskCount} />
          </div>
          <div className="capex-summary__stack">
            <SummaryMetric label="Done" value={progressData.summary.done} />
            <SummaryMetric
              label="Complete"
              value={formatPercent(progressData.summary.estimate.percentComplete)}
            />
          </div>
          <div className="capex-summary__stack">
            <SummaryMetric
              label="Remaining"
              value={progressData.summary.estimate.remainingTasks}
            />
            <SummaryMetric label="ETA" value={progressData.summary.estimate.etaDate ?? "TBD"} />
          </div>
          <div className="capex-summary__stack">
            <SummaryMetric label="Needs fresh check" value={progressData.summary.needs_review} />
            <SummaryMetric label="Blocked" value={progressData.summary.blocked} />
          </div>
          <div className="capex-summary__stack">
            <SummaryMetric label="Not started" value={progressData.summary.not_started} />
            <SummaryMetric
              label="Timestamped"
              value={progressData.summary.estimate.completedWithTimestamps}
            />
          </div>
        </div>
        <CompletionTrendChart
          trend={completionTrend}
          etaDate={progressData.summary.estimate.etaDate}
        />
      </section>

      <RoadmapProgress estimate={progressData.summary.estimate} />

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
              role="progressbar"
              aria-label={`${formatPercent(selectedEpic.estimate.percentComplete)} complete`}
              aria-valuemin={0}
              aria-valuemax={100}
              aria-valuenow={selectedEpic.estimate.percentComplete}
            >
              <span style={{ width: progressWidth(selectedEpic.estimate.percentComplete) }} />
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
