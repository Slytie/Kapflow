import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";

import { getCapxStatusClass, getCapxStatusLabel } from "./capxCeoCockpitStatus";
import {
  findCapxProjectDetail,
  formatMoneyMillions,
  formatMoneyThousands,
  formatSignedPercent,
  trendAreaPolyline
} from "./capxCeoCockpitViewModels";
import type { CapxProjectDetail, CapxStatus, CapxTrendPoint } from "./capxCeoCockpitTypes";
import { CapxCeoCockpitShell } from "./CapxCeoCockpitShell";

function commentStorageKey(projectId: string): string {
  return `capx-ceo-cockpit-demo-comment:${projectId}`;
}

function readStoredComment(projectId: string): string {
  try {
    return window.sessionStorage.getItem(commentStorageKey(projectId)) ?? "";
  } catch {
    return "";
  }
}

function writeStoredComment(projectId: string, comment: string): void {
  try {
    if (comment.length === 0) {
      window.sessionStorage.removeItem(commentStorageKey(projectId));
      return;
    }
    window.sessionStorage.setItem(commentStorageKey(projectId), comment);
  } catch {
    // Session storage can be unavailable in restricted browser modes.
  }
}

function StatusChip({ status }: { status: CapxStatus }): JSX.Element {
  const label = getCapxStatusLabel(status);
  return (
    <span
      className={`capx-status-chip ${getCapxStatusClass(status)}`}
      aria-label={label}
      title={label}
      data-status-chip
    >
      <span className="capx-visually-hidden">{label}</span>
    </span>
  );
}

function TrendPanel({
  title,
  points,
  suffix
}: {
  title: string;
  points: CapxTrendPoint[];
  suffix: string;
}): JSX.Element {
  const last = points.at(-1);
  return (
    <section className="capx-panel capx-chart-panel" aria-label={title}>
      <div className="capx-panel__header">
        <h2>{title}</h2>
        {last ? <span>{`${last.value}${suffix}`}</span> : null}
      </div>
      <svg className="capx-area-chart" viewBox="0 0 280 112" role="img" aria-label={`${title} trend`}>
        <polyline points={trendAreaPolyline(points)} />
      </svg>
      <div className="capx-chart-panel__labels" aria-hidden="true">
        {points.map((point) => (
          <span key={point.label}>{point.label}</span>
        ))}
      </div>
    </section>
  );
}

function ExposureStrip({ project }: { project: CapxProjectDetail }): JSX.Element {
  const metrics = [
    ["Delay / week", formatMoneyThousands(project.delayExposurePerWeekThousands)],
    ["Probable delay", project.probableDelayLabel],
    ["Exposure at risk", formatMoneyMillions(project.exposureAtRiskMillions)],
    ["Worst case", formatMoneyMillions(project.worstPlausibleExposureMillions)],
    ["Budget var.", formatSignedPercent(project.budgetVariancePercent)],
    ["Schedule var.", `+${Math.round(project.scheduleVariancePercent / 3.7)} wks`],
    ["Board impact", project.boardImpact],
    ["Evidence", project.evidenceFreshnessDays <= 7 ? "Fresh" : `${project.evidenceFreshnessDays}d`]
  ];

  return (
    <dl className="capx-exposure-strip">
      {metrics.map(([label, value]) => (
        <div key={label}>
          <dt>{label}</dt>
          <dd>{value}</dd>
        </div>
      ))}
    </dl>
  );
}

function CeoCommentComposer({
  commentDraft,
  projectId,
  setCommentDraft,
  setSavedComment
}: {
  commentDraft: string;
  projectId: string;
  setCommentDraft: (comment: string) => void;
  setSavedComment: (comment: string) => void;
}): JSX.Element {
  return (
    <form
      className="capx-comment-composer"
      onSubmit={(event) => {
        event.preventDefault();
        const nextComment = commentDraft.trim();
        writeStoredComment(projectId, nextComment);
        setCommentDraft("");
        setSavedComment(nextComment);
      }}
    >
      <label htmlFor="capx-ceo-comment">CEO comment</label>
      <div className="capx-comment-composer__row">
        <textarea
          id="capx-ceo-comment"
          value={commentDraft}
          rows={2}
          maxLength={240}
          placeholder="Add note for this project"
          onChange={(event) => setCommentDraft(event.target.value)}
        />
        <button type="submit" className="capx-command-button">
          Save
        </button>
      </div>
    </form>
  );
}

function StageRail({ project }: { project: CapxProjectDetail }): JSX.Element {
  return (
    <ol className="capx-stage-rail" aria-label="Project stages">
      {project.stageLabels.map((stage, index) => {
        const stageNumber = index + 1;
        const isActive = stageNumber === project.currentStageIndex;
        const isComplete = stageNumber < project.currentStageIndex;
        return (
          <li key={stage} className={isActive ? "is-active" : isComplete ? "is-complete" : undefined}>
            <span>{stageNumber}</span>
            <strong>{stage}</strong>
          </li>
        );
      })}
    </ol>
  );
}

function ProjectNotFound(): JSX.Element {
  return (
    <CapxCeoCockpitShell title="Project Not Found" updatedAt="19 May 2025 09:30">
      <main className="capx-cockpit-page capx-not-found" data-testid="capx-project-not-found">
        <section className="capx-panel">
          <h2>Project not found</h2>
          <p>This mock demo only includes a detailed evidence brief for the sample Orion project.</p>
          <Link className="capx-command-button" to="/demo/capx/ceo-cockpit">
            Back to cockpit
          </Link>
        </section>
      </main>
    </CapxCeoCockpitShell>
  );
}

export function CapxCeoCockpitProjectPage(): JSX.Element {
  const { projectId } = useParams();
  const project = findCapxProjectDetail(projectId);
  const [commentDraft, setCommentDraft] = useState("");
  const [savedComment, setSavedComment] = useState("");

  useEffect(() => {
    if (!project) {
      setCommentDraft("");
      setSavedComment("");
      return;
    }
    const storedComment = readStoredComment(project.id);
    setCommentDraft("");
    setSavedComment(storedComment);
  }, [project]);

  if (!project) {
    return <ProjectNotFound />;
  }

  return (
    <CapxCeoCockpitShell title={project.name} updatedAt={project.lastUpdate}>
      <main className="capx-cockpit-page capx-project-page" data-testid="capx-project-page">
        <div className="capx-project-header">
          <div className="capx-project-header__identity">
            <Link to="/demo/capx/ceo-cockpit">Projects</Link>
            <h2>
              {project.code} {project.name}
            </h2>
            <p>{project.subtitle}</p>
          </div>
          <div className="capx-project-header__comment">
            <span className="capx-criticality">{project.criticality}</span>
            <CeoCommentComposer
              commentDraft={commentDraft}
              projectId={project.id}
              setCommentDraft={setCommentDraft}
              setSavedComment={setSavedComment}
            />
          </div>
        </div>

        <ExposureStrip project={project} />

        <div className="capx-project-grid">
          <aside className="capx-project-sidebar">
            <section className="capx-panel">
              <h2>Why this status?</h2>
              <p>{project.whyStatus}</p>
            </section>
            <section className="capx-panel capx-next-action">
              <h2>CEO Next Action</h2>
              <p>{project.ceoNextAction}</p>
              <button type="button" className="capx-command-button">
                View action details
              </button>
            </section>
            <section className="capx-panel capx-comment-panel">
              <div className="capx-panel__header">
                <h2>Saved CEO Comment</h2>
                <span>Local note</span>
              </div>
              <p className="capx-comment-panel__empty">
                Saved only in this browser session. Not canonical project truth.
              </p>
              {savedComment ? (
                <>
                  <blockquote aria-label="Saved CEO comment">{savedComment}</blockquote>
                  <button
                    type="button"
                    className="capx-command-button capx-command-button--subtle"
                    onClick={() => {
                      writeStoredComment(project.id, "");
                      setCommentDraft("");
                      setSavedComment("");
                    }}
                  >
                    Clear saved comment
                  </button>
                </>
              ) : (
                <p className="capx-comment-panel__empty">No saved CEO comment yet.</p>
              )}
            </section>
            <section className="capx-panel">
              <h2>Key Owners</h2>
              <dl className="capx-owner-list">
                {project.owners.map((owner) => (
                  <div key={owner.role}>
                    <dt>{owner.role}</dt>
                    <dd>{owner.name}</dd>
                  </div>
                ))}
              </dl>
            </section>
          </aside>

          <section className="capx-panel capx-stage-panel">
            <div className="capx-panel__header">
              <h2>Stage & Milestones</h2>
              <span>{project.stage}</span>
            </div>
            <StageRail project={project} />
            <table className="capx-milestone-table">
              <thead>
                <tr>
                  <th>Milestone</th>
                  <th>Baseline</th>
                  <th>Forecast</th>
                  <th>Variance</th>
                  <th>Status</th>
                </tr>
              </thead>
              <tbody>
                {project.milestones.map((milestone) => (
                  <tr key={milestone.label}>
                    <td>{milestone.label}</td>
                    <td>{milestone.baseline}</td>
                    <td>{milestone.forecast}</td>
                    <td>{milestone.variance}</td>
                    <td>
                      <StatusChip status={milestone.status} />
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </section>

          <section className="capx-panel capx-risk-list" aria-label="Top risks">
            <div className="capx-panel__header">
              <h2>Top Risks</h2>
              <span>Open</span>
            </div>
            <ol>
              {project.topRisks.map((risk) => (
                <li key={risk.label}>
                  <span>{risk.label}</span>
                  <StatusChip status={risk.severity} />
                </li>
              ))}
            </ol>
          </section>

          <TrendPanel title="Delay Impact (Weekly)" points={project.delayImpactTrend} suffix="K" />
          <TrendPanel title="Budget Over Time" points={project.budgetTrend} suffix="M" />

          <section className="capx-panel capx-latest-update">
            <h2>Latest Update</h2>
            <ul>
              {project.latestUpdateBullets.map((item) => (
                <li key={item}>{item}</li>
              ))}
            </ul>
          </section>
        </div>

        <section className="capx-panel capx-flags-panel" aria-labelledby="capx-flags-title">
          <div className="capx-panel__header">
            <h2 id="capx-flags-title">Current Flags & Triggers</h2>
            <span>{project.flags.length} open</span>
          </div>
          <div className="capx-flags-table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Type</th>
                  <th>Description</th>
                  <th>Severity</th>
                  <th>Raised</th>
                  <th>Owner</th>
                  <th>Status</th>
                </tr>
              </thead>
              <tbody>
                {project.flags.map((flag) => (
                  <tr key={flag.type}>
                    <td>{flag.type}</td>
                    <td>{flag.description}</td>
                    <td>
                      <StatusChip status={flag.severity} />
                    </td>
                    <td>{flag.raised}</td>
                    <td>{flag.owner}</td>
                    <td>{flag.state}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>

        <section className="capx-evidence-grid" aria-label="Evidence, assumptions, and interfaces">
          {project.evidenceSections.map((section) => (
            <article key={section.title} className="capx-panel">
              <h2>{section.title}</h2>
              <ul>
                {section.items.map((item) => (
                  <li key={item}>{item}</li>
                ))}
              </ul>
            </article>
          ))}
        </section>
      </main>
    </CapxCeoCockpitShell>
  );
}
