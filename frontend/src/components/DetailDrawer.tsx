import { memo, useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { Link } from "react-router-dom";

import { onetruthApi } from "@/lib/api/onetruthApi";
import { errorText } from "@/lib/api/errorText";
import { downloadBinaryToFile } from "@/lib/repositories/artifactAttachments";
import { humanTasksRepository } from "@/lib/repositories";
import type {
  HumanTaskRow,
  HumanTaskSubgraph,
  HumanTaskSubgraphArtifactRef,
  HumanTaskSubgraphNode
} from "@/lib/types/contracts";
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

type TaskAction =
  | "claim"
  | "complete"
  | "run_stage06_agent_review"
  | "confirm_review"
  | "upload_attachment";

interface TaskSubgraphViewProps {
  subgraph: HumanTaskSubgraph;
  onDownloadArtifact: (artifactRef: HumanTaskSubgraphArtifactRef) => Promise<void>;
  downloadingArtifactVersionId: string | null;
}

function humanReadableNodeStatus(status: string): string {
  if (status === "in_progress") {
    return "In progress";
  }
  if (status === "not_started") {
    return "Not started";
  }
  if (status === "awaiting_approval") {
    return "Awaiting approval";
  }
  return status.replace(/_/g, " ");
}

const TaskSubgraphView = memo(function TaskSubgraphView({
  subgraph,
  onDownloadArtifact,
  downloadingArtifactVersionId
}: TaskSubgraphViewProps): JSX.Element {
  const [selectedNodeId, setSelectedNodeId] = useState<string | null>(
    subgraph.nodes[0]?.node_id ?? null
  );
  const nodeButtonRefs = useRef<Array<HTMLButtonElement | null>>([]);

  useEffect(() => {
    setSelectedNodeId(subgraph.nodes[0]?.node_id ?? null);
    nodeButtonRefs.current = [];
  }, [subgraph.graph_id, subgraph.nodes]);

  const selectedNode = useMemo<HumanTaskSubgraphNode | null>(() => {
    if (!selectedNodeId) {
      return subgraph.nodes[0] ?? null;
    }
    return subgraph.nodes.find((node) => node.node_id === selectedNodeId) ?? subgraph.nodes[0] ?? null;
  }, [selectedNodeId, subgraph.nodes]);

  const selectedNodeEdges = useMemo(
    () =>
      selectedNode
        ? subgraph.edges.filter(
            (edge) =>
              edge.from_node_id === selectedNode.node_id || edge.to_node_id === selectedNode.node_id
          )
        : [],
    [selectedNode, subgraph.edges]
  );

  return (
    <div className="detail-drawer__subgraph-contents">
      <div className="detail-drawer__subgraph-layout">
        <ul className="detail-drawer__subgraph-node-list" aria-label="Process steps">
          {subgraph.nodes.map((node, index) => {
            const isSelected = selectedNode?.node_id === node.node_id;
            return (
              <li key={node.node_id}>
                <button
                  ref={(element) => {
                    nodeButtonRefs.current[index] = element;
                  }}
                  type="button"
                  className={`detail-drawer__subgraph-node-btn${isSelected ? " is-selected" : ""}`}
                  aria-pressed={isSelected}
                  onClick={() => setSelectedNodeId(node.node_id)}
                  onKeyDown={(event) => {
                    if (event.key !== "ArrowDown" && event.key !== "ArrowUp") {
                      return;
                    }
                    event.preventDefault();
                    const delta = event.key === "ArrowDown" ? 1 : -1;
                    const nextIndex = (index + delta + subgraph.nodes.length) % subgraph.nodes.length;
                    nodeButtonRefs.current[nextIndex]?.focus();
                    setSelectedNodeId(subgraph.nodes[nextIndex]?.node_id ?? null);
                  }}
                >
                  <span>{node.label}</span>
                  <span className="detail-drawer__subgraph-node-status">
                    {humanReadableNodeStatus(node.status)}
                  </span>
                </button>
              </li>
            );
          })}
        </ul>

        <div className="detail-drawer__subgraph-node-detail" aria-live="polite">
          {selectedNode ? (
            <>
              <p className="detail-drawer__subgraph-node-title">{selectedNode.label}</p>
              <p className="detail-drawer__subgraph-node-meta">
                {humanReadableNodeStatus(selectedNode.status)} · {selectedNode.node_kind}
              </p>
              {selectedNodeEdges.length > 0 ? (
                <ul className="detail-drawer__subgraph-edge-list" aria-label="Connected transitions">
                  {selectedNodeEdges.map((edge) => (
                    <li key={edge.edge_id}>
                      {edge.from_node_id} → {edge.to_node_id}
                    </li>
                  ))}
                </ul>
              ) : (
                <p className="detail-drawer__hint">No linked transitions for this step.</p>
              )}
            </>
          ) : (
            <p className="detail-drawer__hint">No process step selected.</p>
          )}
        </div>
      </div>

      <p className="detail-drawer__subgraph-freshness">
        Freshness: {subgraph.freshness.status}
        {subgraph.freshness.as_of ? ` · as of ${new Date(subgraph.freshness.as_of).toLocaleString()}` : ""}
      </p>

      {subgraph.artifact_refs.length > 0 ? (
        <ul className="detail-drawer__artifact-list">
          {subgraph.artifact_refs.map((artifactRef) => (
            <li
              key={artifactRef.artifact_version_id}
              className="detail-drawer__artifact-row detail-drawer__artifact-row--subgraph"
            >
              <div className="detail-drawer__artifact-meta">
                <p className="detail-drawer__artifact-name">{artifactRef.label}</p>
                <p className="detail-drawer__artifact-details">{artifactRef.source_label}</p>
              </div>
              <button
                type="button"
                className="action-btn"
                onClick={() => void onDownloadArtifact(artifactRef)}
                disabled={downloadingArtifactVersionId === artifactRef.artifact_version_id}
              >
                Download
              </button>
            </li>
          ))}
        </ul>
      ) : (
        <p className="detail-drawer__hint">No process artifacts are currently linked.</p>
      )}
    </div>
  );
});

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
  const [pendingTaskAction, setPendingTaskAction] = useState<TaskAction | null>(null);
  const uploadInputRef = useRef<HTMLInputElement | null>(null);
  const expandProcessButtonRef = useRef<HTMLButtonElement | null>(null);
  const subgraphHeadingRef = useRef<HTMLHeadingElement | null>(null);
  const [subgraphExpanded, setSubgraphExpanded] = useState(false);
  const [subgraphLoading, setSubgraphLoading] = useState(false);
  const [subgraphError, setSubgraphError] = useState<unknown>(null);
  const [subgraph, setSubgraph] = useState<HumanTaskSubgraph | null>(null);
  const activeTaskIdRef = useRef<string | null>(null);

  const taskFromPayload = payload?.task ?? null;

  useEffect(() => {
    setDownloadError(null);
    setDownloadingArtifactVersionId(null);
    setTaskActionError(null);
  }, [payload]);

  useEffect(() => {
    setSubgraphExpanded(false);
    setSubgraphLoading(false);
    setSubgraphError(null);
    setSubgraph(null);
  }, [payload?.task?.human_task_id]);

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
  useEffect(() => {
    activeTaskIdRef.current = activeTask?.human_task_id ?? null;
  }, [activeTask?.human_task_id]);

  const isCompositeTask =
    Boolean(activeTask?.is_composite) && activeTask?.expansion_kind === "task_subgraph";

  useEffect(() => {
    if (isCompositeTask) {
      return;
    }
    setSubgraphExpanded(false);
  }, [isCompositeTask]);

  useEffect(() => {
    if (!subgraphExpanded) {
      return;
    }
    subgraphHeadingRef.current?.focus();
  }, [subgraphExpanded, subgraphLoading, subgraphError, subgraph]);

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

  const downloadArtifactVersion = useCallback(
    async ({
      artifactVersionId,
      preferredFileName
    }: {
      artifactVersionId: string;
      preferredFileName: string | null;
    }): Promise<void> => {
      setDownloadError(null);
      setDownloadingArtifactVersionId(artifactVersionId);
      try {
        const downloaded = await onetruthApi.downloadArtifact(artifactVersionId);
        const fileName =
          preferredFileName && preferredFileName.length > 0 ? preferredFileName : artifactVersionId;
        downloadBinaryToFile(downloaded, fileName);
      } catch (error) {
        setDownloadError(error);
      } finally {
        setDownloadingArtifactVersionId(null);
      }
    },
    []
  );

  const handleDownloadArtifact = async (artifact: DrawerArtifact): Promise<void> => {
    await downloadArtifactVersion({
      artifactVersionId: artifact.artifact_version_id,
      preferredFileName: artifact.file_name
    });
  };

  const handleDownloadSubgraphArtifact = async (
    artifactRef: HumanTaskSubgraphArtifactRef
  ): Promise<void> => {
    await downloadArtifactVersion({
      artifactVersionId: artifactRef.artifact_version_id,
      preferredFileName: artifactRef.label || null
    });
  };

  const loadTaskSubgraph = useCallback(async (humanTaskId: string): Promise<void> => {
    setSubgraphLoading(true);
    setSubgraphError(null);
    try {
      const loaded = await humanTasksRepository.getSubgraph(humanTaskId);
      if (activeTaskIdRef.current !== humanTaskId) {
        return;
      }
      setSubgraph(loaded);
      setSubgraphError(null);
    } catch (error) {
      if (activeTaskIdRef.current !== humanTaskId) {
        return;
      }
      setSubgraphError(error);
    } finally {
      if (activeTaskIdRef.current !== humanTaskId) {
        return;
      }
      setSubgraphLoading(false);
    }
  }, []);

  const hasAction = (candidates: string[]): boolean => {
    if (!activeTask) {
      return false;
    }
    const actionSet = new Set((activeTask.available_actions ?? []).map((action) => action.toLowerCase()));
    return candidates.some((candidate) => actionSet.has(candidate.toLowerCase()));
  };

  const toggleTaskSubgraph = (): void => {
    if (!activeTask || !isCompositeTask) {
      return;
    }
    if (subgraphExpanded) {
      setSubgraphExpanded(false);
      expandProcessButtonRef.current?.focus();
      return;
    }
    setSubgraphExpanded(true);
    if (!subgraph && !subgraphLoading) {
      void loadTaskSubgraph(activeTask.human_task_id);
    }
  };

  const refreshTaskContext = async (humanTaskId: string): Promise<void> => {
    const refreshed = await humanTasksRepository.get(humanTaskId);
    setTaskDetails(drawerTaskContext(refreshed));
  };

  const invalidateTaskViews = async (workflowRunId: string): Promise<void> => {
    await Promise.all([
      queryClient.invalidateQueries({ queryKey: ["logistics-demo-story"] }),
      queryClient.invalidateQueries({ queryKey: ["board-view"] }),
      queryClient.invalidateQueries({ queryKey: ["my-work"] }),
      queryClient.invalidateQueries({ queryKey: ["approvals"] }),
      queryClient.invalidateQueries({ queryKey: ["exceptions"] }),
      queryClient.invalidateQueries({ queryKey: ["runs"] }),
      queryClient.invalidateQueries({ queryKey: ["run-detail", workflowRunId] }),
      queryClient.invalidateQueries({ queryKey: ["run-workspace", workflowRunId] })
    ]);
  };

  const handleTaskAction = async (action: TaskAction): Promise<void> => {
    if (!activeTask) {
      return;
    }
    setTaskActionError(null);
    setPendingTaskAction(action);
    try {
      if (action === "claim") {
        await humanTasksRepository.claim(activeTask.human_task_id);
      } else if (action === "complete") {
        await humanTasksRepository.complete(activeTask.human_task_id);
      } else if (action === "run_stage06_agent_review") {
        await humanTasksRepository.runStage06AgentReview(activeTask.human_task_id);
      } else if (action === "confirm_review") {
        const reviewedArtifactVersionIds = artifacts.map((artifact) => artifact.artifact_version_id);
        if (reviewedArtifactVersionIds.length === 0) {
          throw new Error("No linked artifacts are available to confirm review.");
        }
        await humanTasksRepository.confirmReview(activeTask.human_task_id, reviewedArtifactVersionIds);
      }
      await invalidateTaskViews(activeTask.workflow_run_id);
      await refreshTaskContext(activeTask.human_task_id);
    } catch (error) {
      setTaskActionError(error);
    } finally {
      setPendingTaskAction(null);
    }
  };

  const handleUploadAttachment = async (file: File): Promise<void> => {
    if (!activeTask) {
      return;
    }
    setTaskActionError(null);
    setPendingTaskAction("upload_attachment");
    try {
      await humanTasksRepository.uploadAttachment(activeTask.human_task_id, file);
      await invalidateTaskViews(activeTask.workflow_run_id);
      await refreshTaskContext(activeTask.human_task_id);
    } catch (error) {
      setTaskActionError(error);
    } finally {
      setPendingTaskAction(null);
    }
  };

  const openUploadPicker = (): void => {
    if (pendingTaskAction !== null) {
      return;
    }
    uploadInputRef.current?.click();
  };

  if (!payload) {
    return <aside className="detail-drawer" aria-hidden="true" />;
  }

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
      {payload.links && payload.links.length > 0 ? (
        <div className="detail-drawer__links" aria-label="Drawer links">
          {payload.links.map((link) => (
            <Link key={`${link.label}:${link.to}`} className="link-button" to={link.to}>
              {link.label}
            </Link>
          ))}
        </div>
      ) : null}

      {activeTask ? (
        <section className="detail-drawer__task" aria-label="Task context">
          <h3>Task Context</h3>
          <input
            ref={uploadInputRef}
            type="file"
            style={{ display: "none" }}
            tabIndex={-1}
            onChange={(event) => {
              const file = event.currentTarget.files?.[0];
              if (file) {
                void handleUploadAttachment(file);
              }
              event.currentTarget.value = "";
            }}
          />
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
              <dt>Candidate roles</dt>
              <dd>
                {activeTask.candidate_roles && activeTask.candidate_roles.length > 0
                  ? activeTask.candidate_roles.join(", ")
                  : "none"}
              </dd>
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
              <dt>Linked approval</dt>
              <dd>{activeTask.linked_approval_id ?? "none"}</dd>
            </div>
            <div className="detail-drawer__field">
              <dt>Blocked on</dt>
              <dd>
                {activeTask.blocked_on_kind
                  ? `${activeTask.blocked_on_kind}${activeTask.blocked_on_ref ? `:${activeTask.blocked_on_ref}` : ""}`
                  : "none"}
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
            {hasAction(["run_stage06_agent_review"]) ? (
              <button
                type="button"
                className="action-btn"
                disabled={pendingTaskAction !== null}
                onClick={() => void handleTaskAction("run_stage06_agent_review")}
              >
                Run Stage06 Review
              </button>
            ) : null}
            {hasAction(["confirm_review"]) ? (
              <button
                type="button"
                className="action-btn"
                disabled={pendingTaskAction !== null}
                onClick={() => void handleTaskAction("confirm_review")}
              >
                Confirm Review
              </button>
            ) : null}
            {hasAction(["upload_attachment"]) ? (
              <button
                type="button"
                className="action-btn"
                disabled={pendingTaskAction !== null}
                onClick={openUploadPicker}
              >
                Upload attachment
              </button>
            ) : null}
            {isCompositeTask ? (
              <button
                ref={expandProcessButtonRef}
                type="button"
                className="action-btn"
                aria-expanded={subgraphExpanded}
                aria-controls="task-subgraph-panel"
                disabled={subgraphLoading}
                onClick={toggleTaskSubgraph}
              >
                {subgraphExpanded ? "Collapse process" : "Expand process"}
              </button>
            ) : null}
          </div>

          {isCompositeTask && subgraphExpanded ? (
            <section
              id="task-subgraph-panel"
              className="detail-drawer__subgraph"
              aria-label="Task process"
              onKeyDown={(event) => {
                if (event.key !== "Escape") {
                  return;
                }
                event.preventDefault();
                setSubgraphExpanded(false);
                expandProcessButtonRef.current?.focus();
              }}
            >
              <h4 ref={subgraphHeadingRef} tabIndex={-1}>
                Task process
              </h4>
              {subgraphLoading ? (
                <p className="detail-drawer__hint">Loading task process...</p>
              ) : null}
              {!subgraphLoading && subgraphError ? (
                <div>
                  <p className="detail-drawer__error">
                    {errorText(subgraphError, "Task process failed to load")}
                  </p>
                  <button
                    type="button"
                    className="action-btn"
                    onClick={() => {
                      if (!activeTask) {
                        return;
                      }
                      void loadTaskSubgraph(activeTask.human_task_id);
                    }}
                  >
                    Retry process load
                  </button>
                </div>
              ) : null}
              {!subgraphLoading && !subgraphError && subgraph ? (
                <TaskSubgraphView
                  subgraph={subgraph}
                  onDownloadArtifact={handleDownloadSubgraphArtifact}
                  downloadingArtifactVersionId={downloadingArtifactVersionId}
                />
              ) : null}
              {!subgraphLoading && !subgraphError && !subgraph ? (
                <p className="detail-drawer__hint">No process graph is currently available.</p>
              ) : null}
            </section>
          ) : null}
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
    candidate_roles: task.candidate_roles ?? [],
    linked_approval_id: task.linked_approval_id,
    blocked_on_kind: task.blocked_on_kind,
    blocked_on_ref: task.blocked_on_ref,
    available_actions: task.available_actions ?? [],
    blocking_reason_codes: task.blocking_reason_codes ?? [],
    missing_required_inputs: task.missing_required_inputs ?? [],
    is_composite: task.is_composite ?? false,
    expansion_kind: task.expansion_kind ?? "none",
    subgraph_ref: task.subgraph_ref ?? null
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
