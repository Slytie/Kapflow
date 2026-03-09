import { useEffect, useMemo, useState } from "react";
import { useQueryClient } from "@tanstack/react-query";

import { onetruthApi } from "@/lib/api/onetruthApi";
import { errorText } from "@/lib/api/errorText";
import { downloadBase64ToFile } from "@/lib/repositories/artifactAttachments";
import { humanTasksRepository } from "@/lib/repositories";
import type { HumanTaskRow } from "@/lib/types/contracts";
import type {
  DrawerArtifact,
  DrawerArtifactSource,
  DrawerPayload,
  DrawerTaskContext
} from "@/lib/types/ui";

interface DetailDrawerProps {
  payload: DrawerPayload | null;
  onClose: () => void;
}

export function DetailDrawer({ payload, onClose }: DetailDrawerProps): JSX.Element {
  const queryClient = useQueryClient();
  const [downloadError, setDownloadError] = useState<unknown>(null);
  const [downloadingArtifactVersionId, setDownloadingArtifactVersionId] = useState<string | null>(null);
  const [artifacts, setArtifacts] = useState<DrawerArtifact[]>([]);
  const [artifactLoadError, setArtifactLoadError] = useState<unknown>(null);
  const [artifactsLoading, setArtifactsLoading] = useState(false);
  const [taskDetails, setTaskDetails] = useState<DrawerTaskContext | null>(null);
  const [taskLoading, setTaskLoading] = useState(false);
  const [taskLoadError, setTaskLoadError] = useState<unknown>(null);
  const [taskActionError, setTaskActionError] = useState<unknown>(null);
  const [pendingTaskAction, setPendingTaskAction] = useState<"claim" | "complete" | null>(null);

  const taskFromPayload = payload?.task ?? null;

  useEffect(() => {
    setDownloadError(null);
    setDownloadingArtifactVersionId(null);
    setTaskActionError(null);
  }, [payload]);

  useEffect(() => {
    if (!taskFromPayload) {
      setTaskDetails(null);
      setTaskLoading(false);
      setTaskLoadError(null);
      return;
    }
    setTaskDetails(taskFromPayload);
    setTaskLoading(true);
    setTaskLoadError(null);
    let cancelled = false;

    const loadTask = async (): Promise<void> => {
      try {
        const task = await humanTasksRepository.get(taskFromPayload.human_task_id);
        if (!cancelled) {
          setTaskDetails(drawerTaskContext(task));
          setTaskLoadError(null);
        }
      } catch (error) {
        if (!cancelled) {
          setTaskLoadError(error);
        }
      } finally {
        if (!cancelled) {
          setTaskLoading(false);
        }
      }
    };

    void loadTask();
    return () => {
      cancelled = true;
    };
  }, [taskFromPayload]);

  const activeTask = taskDetails ?? taskFromPayload;
  const artifactSources = useMemo(
    () => mergeArtifactSources(payload?.artifact_sources ?? [], activeTask),
    [activeTask, payload?.artifact_sources]
  );

  useEffect(() => {
    if (!payload) {
      setArtifacts([]);
      setArtifactLoadError(null);
      setArtifactsLoading(false);
      return;
    }
    if (payload.artifacts && payload.artifacts.length > 0) {
      setArtifacts(payload.artifacts);
      setArtifactLoadError(null);
      setArtifactsLoading(false);
      return;
    }
    if (artifactSources.length === 0) {
      setArtifacts([]);
      setArtifactLoadError(null);
      setArtifactsLoading(false);
      return;
    }

    let cancelled = false;
    setArtifactsLoading(true);
    setArtifactLoadError(null);

    const loadArtifacts = async (): Promise<void> => {
      try {
        const byArtifactVersionId = new Map<string, DrawerArtifact>();
        for (const source of artifactSources) {
          const rows = await onetruthApi.listArtifactsForSubject({
            workflow_run_id: source.workflow_run_id,
            subject_kind: source.subject_kind,
            subject_id: source.subject_id
          });
          for (const row of rows) {
            if (byArtifactVersionId.has(row.artifact_version_id)) {
              continue;
            }
            const fileName = row.metadata_json?.file_name;
            byArtifactVersionId.set(row.artifact_version_id, {
              artifact_version_id: row.artifact_version_id,
              artifact_kind: row.artifact_kind,
              artifact_role: row.artifact_role ?? null,
              media_type: row.media_type,
              created_at: row.created_at,
              file_name: typeof fileName === "string" && fileName.length > 0 ? fileName : null,
              source_label: source.source_label
            });
          }
        }
        const loaded = Array.from(byArtifactVersionId.values()).sort((left, right) =>
          right.created_at.localeCompare(left.created_at)
        );
        if (!cancelled) {
          setArtifacts(loaded);
          setArtifactLoadError(null);
        }
      } catch (error) {
        if (!cancelled) {
          setArtifacts([]);
          setArtifactLoadError(error);
        }
      } finally {
        if (!cancelled) {
          setArtifactsLoading(false);
        }
      }
    };

    void loadArtifacts();
    return () => {
      cancelled = true;
    };
  }, [artifactSources, payload]);

  if (!payload) {
    return <aside className="detail-drawer" aria-hidden="true" />;
  }

  const handleDownloadArtifact = async (artifact: DrawerArtifact): Promise<void> => {
    setDownloadError(null);
    setDownloadingArtifactVersionId(artifact.artifact_version_id);
    try {
      const downloaded = await onetruthApi.downloadArtifact(artifact.artifact_version_id);
      const metadataName = downloaded.artifact_version.metadata_json?.file_name;
      const fileName =
        artifact.file_name ??
        (typeof metadataName === "string" && metadataName.length > 0
          ? metadataName
          : downloaded.artifact_version.artifact_version_id);
      downloadBase64ToFile(
        downloaded.content_base64,
        fileName,
        downloaded.artifact_version.media_type
      );
    } catch (error) {
      setDownloadError(error);
    } finally {
      setDownloadingArtifactVersionId(null);
    }
  };

  const hasAction = (candidates: string[]): boolean => {
    if (!activeTask) {
      return false;
    }
    const actionSet = new Set((activeTask.available_actions ?? []).map((action) => action.toLowerCase()));
    return candidates.some((candidate) => actionSet.has(candidate.toLowerCase()));
  };

  const handleTaskAction = async (action: "claim" | "complete"): Promise<void> => {
    if (!activeTask) {
      return;
    }
    setTaskActionError(null);
    setPendingTaskAction(action);
    try {
      if (action === "claim") {
        await humanTasksRepository.claim(activeTask.human_task_id);
      } else {
        await humanTasksRepository.complete(activeTask.human_task_id);
      }
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ["logistics-demo-story"] }),
        queryClient.invalidateQueries({ queryKey: ["board-view"] }),
        queryClient.invalidateQueries({ queryKey: ["my-work"] }),
        queryClient.invalidateQueries({ queryKey: ["approvals"] }),
        queryClient.invalidateQueries({ queryKey: ["exceptions"] }),
        queryClient.invalidateQueries({ queryKey: ["runs"] }),
        queryClient.invalidateQueries({ queryKey: ["run-detail", activeTask.workflow_run_id] }),
        queryClient.invalidateQueries({ queryKey: ["run-workspace", activeTask.workflow_run_id] })
      ]);
      const refreshed = await humanTasksRepository.get(activeTask.human_task_id);
      setTaskDetails(drawerTaskContext(refreshed));
    } catch (error) {
      setTaskActionError(error);
    } finally {
      setPendingTaskAction(null);
    }
  };

  return (
    <aside className="detail-drawer detail-drawer--open" aria-label="Details drawer">
      <header>
        <h2>{payload.title}</h2>
        {payload.subtitle ? <p>{payload.subtitle}</p> : null}
        <button type="button" className="link-button" onClick={onClose} aria-label="Close drawer">
          Close
        </button>
      </header>
      {payload.description ? <p className="detail-drawer__description">{payload.description}</p> : null}
      <dl>
        {payload.fields.map((field) => (
          <div key={field.label} className="detail-drawer__field">
            <dt>{field.label}</dt>
            <dd>{field.value}</dd>
          </div>
        ))}
      </dl>

      {activeTask ? (
        <section className="detail-drawer__task" aria-label="Task context">
          <h3>Task Context</h3>
          <dl>
            <div className="detail-drawer__field">
              <dt>Task id</dt>
              <dd>{activeTask.human_task_id}</dd>
            </div>
            <div className="detail-drawer__field">
              <dt>State</dt>
              <dd>{activeTask.state}</dd>
            </div>
            <div className="detail-drawer__field">
              <dt>Assignee</dt>
              <dd>{activeTask.assignee_actor_id ?? "unassigned"}</dd>
            </div>
            <div className="detail-drawer__field">
              <dt>Owner role</dt>
              <dd>{activeTask.owner_role ?? "unknown"}</dd>
            </div>
            <div className="detail-drawer__field">
              <dt>Workflow run</dt>
              <dd>{activeTask.workflow_run_id}</dd>
            </div>
            <div className="detail-drawer__field">
              <dt>Task run</dt>
              <dd>{activeTask.task_run_id}</dd>
            </div>
            <div className="detail-drawer__field">
              <dt>Stage / kind</dt>
              <dd>
                {activeTask.stage_id} · {activeTask.task_kind}
              </dd>
            </div>
            <div className="detail-drawer__field">
              <dt>Blocking reasons</dt>
              <dd>
                {activeTask.blocking_reason_codes.length > 0
                  ? activeTask.blocking_reason_codes.join(", ")
                  : "none"}
              </dd>
            </div>
            <div className="detail-drawer__field">
              <dt>Missing inputs</dt>
              <dd>
                {activeTask.missing_required_inputs.length > 0
                  ? activeTask.missing_required_inputs.join(", ")
                  : "none"}
              </dd>
            </div>
            <div className="detail-drawer__field">
              <dt>Available actions</dt>
              <dd>
                {activeTask.available_actions.length > 0
                  ? activeTask.available_actions.join(", ")
                  : "none"}
              </dd>
            </div>
          </dl>
          <div className="detail-drawer__task-actions">
            {hasAction(["claim", "claim_human_task"]) ? (
              <button
                type="button"
                className="action-btn"
                disabled={pendingTaskAction !== null}
                onClick={() => void handleTaskAction("claim")}
              >
                Claim
              </button>
            ) : null}
            {hasAction(["complete", "complete_human_task"]) ? (
              <button
                type="button"
                className="action-btn action-btn--positive"
                disabled={pendingTaskAction !== null}
                onClick={() => void handleTaskAction("complete")}
              >
                Complete
              </button>
            ) : null}
          </div>
        </section>
      ) : null}

      {artifacts.length > 0 ? (
        <section className="detail-drawer__artifacts" aria-label="Task artifacts">
          <h3>Task Artifacts ({artifacts.length})</h3>
          <ul className="detail-drawer__artifact-list">
            {artifacts.map((artifact) => (
              <li key={artifact.artifact_version_id} className="detail-drawer__artifact-row">
                <div className="detail-drawer__artifact-meta">
                  <p className="detail-drawer__artifact-name">
                    {artifact.file_name ?? artifact.artifact_kind}
                  </p>
                  <p className="detail-drawer__artifact-details">
                    {artifact.artifact_kind}
                    {artifact.artifact_role ? ` · ${artifact.artifact_role}` : ""}
                    {artifact.source_label ? ` · ${artifact.source_label}` : ""}
                  </p>
                </div>
                <button
                  type="button"
                  className="action-btn"
                  onClick={() => void handleDownloadArtifact(artifact)}
                  disabled={downloadingArtifactVersionId === artifact.artifact_version_id}
                >
                  Download
                </button>
              </li>
            ))}
          </ul>
        </section>
      ) : null}

      {artifactsLoading ? (
        <p className="detail-drawer__hint">Loading task artifacts...</p>
      ) : null}

      {!artifactsLoading &&
      artifacts.length === 0 &&
      payload.artifact_sources &&
      payload.artifact_sources.length > 0 ? (
        <p className="detail-drawer__hint">No task artifacts are currently linked.</p>
      ) : null}

      {downloadError ? (
        <p className="detail-drawer__error">
          {errorText(downloadError, "Artifact download failed")}
        </p>
      ) : null}

      {artifactLoadError ? (
        <p className="detail-drawer__error">
          {errorText(artifactLoadError, "Task artifacts failed to load")}
        </p>
      ) : null}

      {taskLoading ? <p className="detail-drawer__hint">Loading task context...</p> : null}

      {taskLoadError ? (
        <p className="detail-drawer__error">{errorText(taskLoadError, "Task details failed to load")}</p>
      ) : null}

      {taskActionError ? (
        <p className="detail-drawer__error">{errorText(taskActionError, "Task action failed")}</p>
      ) : null}
    </aside>
  );
}

function drawerTaskContext(task: HumanTaskRow): DrawerTaskContext {
  return {
    human_task_id: task.human_task_id,
    workflow_run_id: task.workflow_run_id,
    task_run_id: task.task_run_id,
    stage_id: task.stage_id,
    task_kind: task.task_kind,
    state: task.state,
    assignee_actor_id: task.assignee_actor_id,
    assignee_actor_type: task.assignee_actor_type,
    owner_role: task.owner_role,
    available_actions: task.available_actions ?? [],
    blocking_reason_codes: task.blocking_reason_codes ?? [],
    missing_required_inputs: task.missing_required_inputs ?? []
  };
}

function mergeArtifactSources(
  artifactSources: DrawerArtifactSource[],
  task: DrawerTaskContext | null
): DrawerArtifactSource[] {
  const merged = [...artifactSources];
  if (task) {
    merged.push({
      workflow_run_id: task.workflow_run_id,
      subject_kind: "human_task",
      subject_id: task.human_task_id,
      source_label: "Task attachment"
    });
    if (task.task_run_id && task.task_run_id !== "loading") {
      merged.push({
        workflow_run_id: task.workflow_run_id,
        subject_kind: "task_run",
        subject_id: task.task_run_id,
        source_label: "Step output"
      });
    }
  }
  const deduped = new Map<string, DrawerArtifactSource>();
  for (const source of merged) {
    const dedupeKey = `${source.subject_kind}:${source.subject_id}:${source.source_label}`;
    if (!deduped.has(dedupeKey)) {
      deduped.set(dedupeKey, source);
    }
  }
  return Array.from(deduped.values());
}
