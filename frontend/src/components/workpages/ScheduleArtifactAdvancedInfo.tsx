import type { WorkpageContract } from "@/lib/types/contracts";
import type {
  WorkpageHistorySection as WorkpageHistorySectionModel,
  WorkpageNotePanelSection as WorkpageNotePanelSectionModel,
  WorkpageTableSection as WorkpageTableSectionModel
} from "@/lib/types/workpages";

import {
  WorkpageHistorySection,
  WorkpageNotePanelSection,
  WorkpageTableSection
} from "@/components/workpages/WorkpageContent";

export function ScheduleArtifactAdvancedInfo({
  noteSection,
  historySection,
  assignmentSection,
  reserveSection,
  iterationSection,
  artifactContext
}: {
  noteSection: WorkpageNotePanelSectionModel | null;
  historySection: WorkpageHistorySectionModel | null;
  assignmentSection: WorkpageTableSectionModel | null;
  reserveSection: WorkpageTableSectionModel | null;
  iterationSection: WorkpageTableSectionModel | null;
  artifactContext: WorkpageContract["artifact_context"];
}): JSX.Element {
  return (
    <>
      {noteSection ? <WorkpageNotePanelSection section={noteSection} /> : null}
      {artifactContext ? (
        <section className="workpage-panel">
          <header className="workpage-panel__header">
            <h2>Artifact lineage</h2>
            <p>Technical lineage and raw workbook context stay available here while the main surface focuses on live metrics and version rails.</p>
          </header>
          <div className="workpage-page__source-grid workpage-page__source-grid--metadata">
            <article className="workpage-page__source-item">
              <strong>Current artifact</strong>
              <p>{artifactContext.artifact_version_id}</p>
            </article>
            <article className="workpage-page__source-item">
              <strong>Workflow run</strong>
              <p>{artifactContext.workflow_run_id}</p>
            </article>
            <article className="workpage-page__source-item">
              <strong>Artifact kind</strong>
              <p>{artifactContext.artifact_kind}</p>
            </article>
            <article className="workpage-page__source-item">
              <strong>Latest in chain</strong>
              <p>{artifactContext.latest_in_chain_artifact_version_id}</p>
            </article>
            <article className="workpage-page__source-item">
              <strong>Supersedes</strong>
              <p>{artifactContext.supersedes_artifact_version_id ?? "Initial Stage04 draft"}</p>
            </article>
            <article className="workpage-page__source-item">
              <strong>Superseded by</strong>
              <p>{artifactContext.superseded_by_artifact_version_id ?? "Current latest"}</p>
            </article>
          </div>
        </section>
      ) : null}
      {historySection ? <WorkpageHistorySection section={historySection} /> : null}
      {assignmentSection ? <WorkpageTableSection section={assignmentSection} /> : null}
      {reserveSection ? <WorkpageTableSection section={reserveSection} /> : null}
      {iterationSection ? <WorkpageTableSection section={iterationSection} /> : null}
    </>
  );
}
