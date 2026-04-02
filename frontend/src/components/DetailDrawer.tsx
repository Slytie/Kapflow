import {
  type ChangeEvent,
  type KeyboardEvent as ReactKeyboardEvent,
  memo,
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState
} from "react";
import { useQueryClient } from "@tanstack/react-query";
import { Link } from "react-router-dom";

import { InfoDialog } from "@/components/InfoDialog";
import { StatusBadge } from "@/components/StatusBadge";
import { onetruthApi } from "@/lib/api/onetruthApi";
import { errorText } from "@/lib/api/errorText";
import { downloadBinaryToFile } from "@/lib/repositories/artifactAttachments";
import { humanTasksRepository, templatesRepository } from "@/lib/repositories";
import type {
  HumanTaskRow,
  HumanTaskSubgraph,
  HumanTaskSubgraphArtifactRef,
  WorkflowWorkspaceRequiredUpload
} from "@/lib/types/contracts";
import type {
  DrawerArtifact,
  DrawerArtifactSource,
  DrawerDownloadableArtifact,
  DrawerPayload,
  DrawerTaskContext
} from "@/lib/types/ui";
import {
  buildTaskRequiredDocumentRows,
  type TaskDocumentTone
} from "@/lib/workspace/taskDocumentUi";
import { taskDisplayHeading } from "@/lib/workspace/taskLabels";

interface DetailDrawerProps {
  payload: DrawerPayload | null;
  onClose: () => void;
}

type TaskAction =
  | "claim"
  | "complete"
  | "run_stage06_agent_review"
  | "run_weekly_stage04_openai_agent"
  | "confirm_review"
  | "upload_attachment"
  | "upload_required_response"
  | "open_required_review_draft";

interface TaskSubgraphViewProps {
  subgraph: HumanTaskSubgraph;
  onDownloadArtifact: (artifactRef: HumanTaskSubgraphArtifactRef) => Promise<void>;
  downloadingArtifactVersionId: string | null;
}

interface DrawerRequiredUploadActionsProps {
  actionLabel: "Add File" | "Replace";
  disabled: boolean;
  onUpload: (file: File) => void;
}

type TaskProcessTone = "active" | "pending" | "success" | "neutral" | "danger";

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

function taskProcessTone(status: string): TaskProcessTone {
  const normalized = status.trim().toLowerCase();
  if (normalized === "in_progress" || normalized.includes("progress")) {
    return "active";
  }
  if (normalized === "awaiting_approval" || normalized.includes("approval") || normalized.includes("review")) {
    return "pending";
  }
  if (
    normalized === "completed" ||
    normalized === "complete" ||
    normalized === "done" ||
    normalized.includes("success") ||
    normalized.includes("published")
  ) {
    return "success";
  }
  if (
    normalized.includes("failed") ||
    normalized.includes("error") ||
    normalized.includes("blocked") ||
    normalized.includes("degraded")
  ) {
    return "danger";
  }
  return "neutral";
}

function taskDocumentToneClass(tone: TaskDocumentTone): string {
  return `task-modal__document-row task-modal__document-row--${tone}`;
}

function taskDocumentMarker(tone: TaskDocumentTone, kind: "upload" | "review"): string {
  if (tone === "success") {
    return "OK";
  }
  if (kind === "review") {
    return "RV";
  }
  if (tone === "neutral") {
    return "OPT";
  }
  return "!";
}

function humanizeValue(input: string): string {
  return input
    .replace(/[_-]+/g, " ")
    .replace(/\s+/g, " ")
    .trim()
    .replace(/\b\w/g, (char) => char.toUpperCase());
}

function formatTimestamp(timestamp: string | null | undefined): string | null {
  if (!timestamp) {
    return null;
  }
  const value = new Date(timestamp);
  if (Number.isNaN(value.getTime())) {
    return null;
  }
  return value.toLocaleString();
}

function taskBlockingSummary(task: DrawerTaskContext | null): string {
  if (!task) {
    return "No blockers recorded";
  }
  if (task.blocking_reason_codes.length > 0) {
    return task.blocking_reason_codes.map(humanizeValue).join(", ");
  }
  if (task.blocked_on_kind) {
    return humanizeValue(
      task.blocked_on_ref ? `${task.blocked_on_kind} ${task.blocked_on_ref}` : task.blocked_on_kind
    );
  }
  return "No blockers recorded";
}

function taskMissingInputSummary(task: DrawerTaskContext | null): string {
  if (!task || task.missing_required_inputs.length === 0) {
    return "Ready for work";
  }
  return task.missing_required_inputs.join(", ");
}

function taskReadinessSummary(task: DrawerTaskContext | null): string {
  if (!task) {
    return "Loading";
  }
  if (task.missing_required_inputs.length > 0) {
    const count = task.missing_required_inputs.length;
    return `${count} missing input${count === 1 ? "" : "s"}`;
  }
  if ((task.required_reviews ?? []).some((review) => review.status !== "confirmed")) {
    return "Review required";
  }
  if (task.blocking_reason_codes.length > 0 || task.blocked_on_kind) {
    return "Blocked";
  }
  return "Ready for work";
}

function taskPrimaryActionLabel(action: TaskAction): string {
  if (action === "confirm_review") {
    return "Submit for Review";
  }
  if (action === "complete") {
    return "Complete Task";
  }
  if (action === "run_stage06_agent_review") {
    return "Run Stage06 Review";
  }
  if (action === "run_weekly_stage04_openai_agent") {
    return "Run Stage04 Build";
  }
  return humanizeValue(action);
}

function focusableElements(container: HTMLElement | null): HTMLElement[] {
  if (!container) {
    return [];
  }
  return Array.from(
    container.querySelectorAll<HTMLElement>(
      "a[href], button:not([disabled]), input:not([disabled]):not([type='hidden']), select:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex='-1'])"
    )
  ).filter((element) => !element.hasAttribute("disabled") && element.tabIndex !== -1);
}

const TaskSubgraphView = memo(function TaskSubgraphView({
  subgraph,
  onDownloadArtifact,
  downloadingArtifactVersionId
}: TaskSubgraphViewProps): JSX.Element {
  const [expandedNodeIds, setExpandedNodeIds] = useState<string[]>([]);
  const nodeButtonRefs = useRef<Array<HTMLButtonElement | null>>([]);

  useEffect(() => {
    setExpandedNodeIds([]);
    nodeButtonRefs.current = [];
  }, [subgraph.graph_id, subgraph.nodes]);

  const expandedNodeIdSet = useMemo(() => new Set(expandedNodeIds), [expandedNodeIds]);
  const nodeLabelById = useMemo(
    () => new Map(subgraph.nodes.map((node) => [node.node_id, node.label])),
    [subgraph.nodes]
  );

  const toggleExpanded = (nodeId: string): void => {
    setExpandedNodeIds((current) =>
      current.includes(nodeId)
        ? current.filter((candidate) => candidate !== nodeId)
        : [...current, nodeId]
    );
  };

  return (
    <div className="task-process-timeline">
      <ul className="task-process-timeline__list" aria-label="Process steps">
        {subgraph.nodes.map((node, index) => {
          const expanded = expandedNodeIdSet.has(node.node_id);
          const tone = taskProcessTone(node.status);
          const statusLabel = humanReadableNodeStatus(node.status);
          const connectedEdges = subgraph.edges.filter(
            (edge) => edge.from_node_id === node.node_id || edge.to_node_id === node.node_id
          );
          const detailId = `task-process-node-${node.node_id}`;

          return (
            <li
              key={node.node_id}
              className={`task-process-timeline__item task-process-timeline__item--${tone}${expanded ? " is-expanded" : ""}`}
            >
              <button
                ref={(element) => {
                  nodeButtonRefs.current[index] = element;
                }}
                type="button"
                className="task-process-timeline__toggle"
                aria-expanded={expanded}
                aria-controls={detailId}
                onClick={() => toggleExpanded(node.node_id)}
                onKeyDown={(event) => {
                  if (event.key !== "ArrowDown" && event.key !== "ArrowUp") {
                    return;
                  }
                  event.preventDefault();
                  const delta = event.key === "ArrowDown" ? 1 : -1;
                  const nextIndex = (index + delta + subgraph.nodes.length) % subgraph.nodes.length;
                  nodeButtonRefs.current[nextIndex]?.focus();
                }}
              >
                <span
                  className={`task-process-timeline__marker task-process-timeline__marker--${tone}`}
                  aria-hidden="true"
                />
                <span className="task-process-timeline__header">
                  <span className="task-process-timeline__label">{node.label}</span>
                  <span className={`task-process-timeline__status task-process-timeline__status--${tone}`}>
                    {statusLabel}
                  </span>
                </span>
              </button>
              {expanded ? (
                <div id={detailId} className="task-process-timeline__detail">
                  <p className="task-process-timeline__meta">
                    {humanizeValue(node.node_kind)} · {statusLabel}
                  </p>
                  {connectedEdges.length > 0 ? (
                    <ul className="task-process-timeline__edge-list" aria-label={`Transitions for ${node.label}`}>
                      {connectedEdges.map((edge) => {
                        const fromLabel = nodeLabelById.get(edge.from_node_id) ?? edge.from_node_id;
                        const toLabel = nodeLabelById.get(edge.to_node_id) ?? edge.to_node_id;
                        return (
                          <li key={edge.edge_id}>
                            {edge.from_node_id === node.node_id ? `Flows to ${toLabel}` : `Receives from ${fromLabel}`}
                          </li>
                        );
                      })}
                    </ul>
                  ) : (
                    <p className="detail-drawer__hint">No linked transitions for this step.</p>
                  )}
                </div>
              ) : null}
            </li>
          );
        })}
      </ul>

      <div className="task-process-timeline__footer">
        <p className="task-process-timeline__freshness">
          Freshness: {subgraph.freshness.status}
          {subgraph.freshness.as_of ? ` · as of ${new Date(subgraph.freshness.as_of).toLocaleString()}` : ""}
        </p>

        {subgraph.artifact_refs.length > 0 ? (
          <ul className="task-process-timeline__artifact-list" aria-label="Process artifacts">
            {subgraph.artifact_refs.map((artifactRef) => (
              <li key={artifactRef.artifact_version_id} className="task-process-timeline__artifact-item">
                <div className="task-process-timeline__artifact-copy">
                  <p className="task-process-timeline__artifact-label">{artifactRef.label}</p>
                  <p className="task-process-timeline__artifact-meta">{artifactRef.source_label}</p>
                </div>
                <button
                  type="button"
                  className="task-process-timeline__artifact-action"
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
    </div>
  );
});

function DrawerRequiredUploadActions({
  actionLabel,
  disabled,
  onUpload
}: DrawerRequiredUploadActionsProps): JSX.Element {
  const inputRef = useRef<HTMLInputElement | null>(null);

  const openFilePicker = (): void => {
    if (disabled) {
      return;
    }
    inputRef.current?.click();
  };

  const onInputChanged = (event: ChangeEvent<HTMLInputElement>): void => {
    const file = event.currentTarget.files?.[0];
    if (file) {
      onUpload(file);
    }
    event.currentTarget.value = "";
  };

  return (
    <div className="detail-drawer__requirement-actions">
      <input
        ref={inputRef}
        type="file"
        onChange={onInputChanged}
        tabIndex={-1}
        style={{ display: "none" }}
      />
      <button
        type="button"
        className="action-btn"
        onClick={openFilePicker}
        disabled={disabled}
      >
        {actionLabel}
      </button>
    </div>
  );
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
  const [pendingTaskAction, setPendingTaskAction] = useState<TaskAction | null>(null);
  const [activeRequirementKey, setActiveRequirementKey] = useState<string | null>(null);
  const [downloadingTemplateId, setDownloadingTemplateId] = useState<string | null>(null);
  const uploadInputRef = useRef<HTMLInputElement | null>(null);
  const taskDialogRef = useRef<HTMLElement | null>(null);
  const taskCloseButtonRef = useRef<HTMLButtonElement | null>(null);
  const taskModalTriggerRef = useRef<HTMLElement | null>(null);
  const taskModalWasOpenRef = useRef(false);
  const [subgraphLoading, setSubgraphLoading] = useState(false);
  const [subgraphError, setSubgraphError] = useState<unknown>(null);
  const [subgraph, setSubgraph] = useState<HumanTaskSubgraph | null>(null);
  const activeTaskIdRef = useRef<string | null>(null);

  const taskFromPayload = payload?.task ?? null;
  const isTaskPayload = Boolean(taskFromPayload);

  useEffect(() => {
    setDownloadError(null);
    setDownloadingArtifactVersionId(null);
    setTaskActionError(null);
    setActiveRequirementKey(null);
    setDownloadingTemplateId(null);
  }, [payload]);

  useEffect(() => {
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
          setTaskDetails(drawerTaskContext(task, taskFromPayload));
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

  useEffect(() => {
    if (isTaskPayload && !taskModalWasOpenRef.current) {
      taskModalTriggerRef.current =
        document.activeElement instanceof HTMLElement ? document.activeElement : null;
      requestAnimationFrame(() => {
        taskCloseButtonRef.current?.focus();
      });
    }

    if (!isTaskPayload && taskModalWasOpenRef.current) {
      taskModalTriggerRef.current?.focus();
      taskModalTriggerRef.current = null;
    }

    taskModalWasOpenRef.current = isTaskPayload;
  }, [isTaskPayload]);

  const requiredUploads = activeTask?.required_uploads ?? [];
  const requiredReviews = activeTask?.required_reviews ?? [];
  const requiredDocumentRows = useMemo(
    () =>
      buildTaskRequiredDocumentRows({
        required_uploads: requiredUploads,
        required_reviews: requiredReviews
      }),
    [requiredReviews, requiredUploads]
  );
  const workpageActions = activeTask?.workpage_actions ?? [];
  const downloadableArtifacts = payload?.downloadable_artifacts ?? [];
  const requiredReviewArtifactVersionIds = requiredReviews
    .map((review) => review.reviewed_artifact_version_id)
    .filter((value): value is string => Boolean(value));
  const hasPendingReviewConfirmation = requiredReviews.some(
    (review) => review.status === "pending_confirmation"
  );

  const isCompositeTask =
    Boolean(activeTask?.is_composite) && activeTask?.expansion_kind === "task_subgraph";

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

  const handleDownloadLightweightArtifact = async (
    artifact: DrawerDownloadableArtifact
  ): Promise<void> => {
    await downloadArtifactVersion({
      artifactVersionId: artifact.artifact_version_id,
      preferredFileName: artifact.label || null
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

  useEffect(() => {
    if (!isCompositeTask) {
      return;
    }
    if (!activeTask || subgraph || subgraphLoading || subgraphError) {
      return;
    }
    void loadTaskSubgraph(activeTask.human_task_id);
  }, [activeTask, isCompositeTask, loadTaskSubgraph, subgraph, subgraphError, subgraphLoading]);

  const hasAction = (candidates: string[]): boolean => {
    if (!activeTask) {
      return false;
    }
    const actionSet = new Set((activeTask.available_actions ?? []).map((action) => action.toLowerCase()));
    return candidates.some((candidate) => actionSet.has(candidate.toLowerCase()));
  };

  const primaryTaskAction = (() => {
    if (hasAction(["confirm_review"])) {
      return "confirm_review";
    }
    if (hasAction(["complete", "complete_human_task"])) {
      return "complete";
    }
    if (hasAction(["run_stage06_agent_review"])) {
      return "run_stage06_agent_review";
    }
    if (hasAction(["run_weekly_stage04_openai_agent"])) {
      return "run_weekly_stage04_openai_agent";
    }
    return null;
  })();

  const primaryTaskActionDisabled =
    primaryTaskAction === "confirm_review"
      ? pendingTaskAction !== null ||
        (requiredReviewArtifactVersionIds.length === 0 && artifacts.length === 0) ||
        (requiredReviews.length > 0 && !hasPendingReviewConfirmation)
      : pendingTaskAction !== null;

  const supportingRouteActions = workpageActions.filter((action) => action.state === "available" && action.route);
  const workspaceLink = useMemo(() => {
    const explicitWorkspaceLink = payload?.links?.find((link) => /workspace/i.test(link.label));
    if (explicitWorkspaceLink) {
      return {
        ...explicitWorkspaceLink,
        label: "Open Workspace"
      };
    }
    if (!activeTask) {
      return null;
    }
    return {
      label: "Open Workspace",
      to: `/runs/${activeTask.workflow_run_id}/workspace`
    };
  }, [activeTask, payload?.links]);
  const secondaryLinks = (payload?.links ?? []).filter(
    (link) => !workspaceLink || link.to !== workspaceLink.to
  );

  const handleTaskModalKeyDown = (event: ReactKeyboardEvent<HTMLDivElement>): void => {
    if (event.key === "Escape") {
      event.preventDefault();
      onClose();
      return;
    }

    if (event.key !== "Tab") {
      return;
    }

    const focusable = focusableElements(taskDialogRef.current);
    if (focusable.length === 0) {
      event.preventDefault();
      taskDialogRef.current?.focus();
      return;
    }

    const first = focusable[0];
    const last = focusable[focusable.length - 1];
    if (event.shiftKey && document.activeElement === first) {
      event.preventDefault();
      last.focus();
      return;
    }
    if (!event.shiftKey && document.activeElement === last) {
      event.preventDefault();
      first.focus();
    }
  };

  const refreshTaskContext = async (
    humanTaskId: string,
    fallback: DrawerTaskContext | null = activeTask
  ): Promise<void> => {
    const refreshed = await humanTasksRepository.get(humanTaskId);
    setTaskDetails(drawerTaskContext(refreshed, fallback));
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
    let nextTaskContext = activeTask;
    try {
      if (action === "claim") {
        await humanTasksRepository.claim(activeTask.human_task_id);
      } else if (action === "complete") {
        await humanTasksRepository.complete(activeTask.human_task_id);
      } else if (action === "run_stage06_agent_review") {
        await humanTasksRepository.runStage06AgentReview(activeTask.human_task_id);
      } else if (action === "run_weekly_stage04_openai_agent") {
        await humanTasksRepository.runWeeklyStage04OpenAIAgent(activeTask.human_task_id);
      } else if (action === "confirm_review") {
        const reviewedArtifactVersionIds =
          requiredReviewArtifactVersionIds.length > 0
            ? requiredReviewArtifactVersionIds
            : artifacts.map((artifact) => artifact.artifact_version_id);
        if (reviewedArtifactVersionIds.length === 0) {
          throw new Error("No linked artifacts are available to confirm review.");
        }
        await humanTasksRepository.confirmReview(activeTask.human_task_id, reviewedArtifactVersionIds);
        nextTaskContext = withConfirmedRequiredReviews(activeTask);
        setTaskDetails(nextTaskContext);
      }
      await invalidateTaskViews(activeTask.workflow_run_id);
      await refreshTaskContext(activeTask.human_task_id, nextTaskContext);
    } catch (error) {
      setTaskActionError(error);
    } finally {
      setPendingTaskAction(null);
    }
  };

  const handleUploadRequiredResponse = async (
    requirement: WorkflowWorkspaceRequiredUpload,
    file: File
  ): Promise<void> => {
    if (!activeTask) {
      return;
    }
    const requirementKey = `${requirement.dataset_key}:${requirement.artifact_kind}`;
    setTaskActionError(null);
    setPendingTaskAction("upload_required_response");
    setActiveRequirementKey(requirementKey);
    try {
      await humanTasksRepository.uploadRequiredResponse(activeTask.human_task_id, requirement, file);
      const nextTaskContext = withSatisfiedRequiredUpload(activeTask, requirement);
      setTaskDetails(nextTaskContext);
      await invalidateTaskViews(activeTask.workflow_run_id);
      await refreshTaskContext(activeTask.human_task_id, nextTaskContext);
    } catch (error) {
      setTaskActionError(error);
    } finally {
      setPendingTaskAction(null);
      setActiveRequirementKey(null);
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
      await refreshTaskContext(activeTask.human_task_id, activeTask);
    } catch (error) {
      setTaskActionError(error);
    } finally {
      setPendingTaskAction(null);
    }
  };

  const handleDownloadRequirementTemplate = async (templateId: string): Promise<void> => {
    setTaskActionError(null);
    setDownloadingTemplateId(templateId);
    try {
      await templatesRepository.download(templateId);
    } catch (error) {
      setTaskActionError(error);
    } finally {
      setDownloadingTemplateId(null);
    }
  };

  const handleOpenRequiredReviewDraft = async (artifactVersionId: string): Promise<void> => {
    setTaskActionError(null);
    setPendingTaskAction("open_required_review_draft");
    try {
      await humanTasksRepository.openDraftArtifact(artifactVersionId);
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
    return <aside className="detail-drawer detail-drawer--closed" aria-hidden="true" />;
  }

  if (isTaskPayload && activeTask) {
    return (
      <div
        className="task-modal-backdrop"
        onClick={(event) => {
          if (event.target === event.currentTarget) {
            onClose();
          }
        }}
      >
        <section
          ref={taskDialogRef}
          className="task-modal"
          role="dialog"
          aria-modal="true"
          aria-labelledby="task-modal-title"
          aria-describedby="task-modal-description"
          onKeyDown={handleTaskModalKeyDown}
          tabIndex={-1}
        >
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
          <header className="task-modal__header">
            <div className="task-modal__headline">
              <div className="task-modal__title-row">
                <div>
                  <h2 id="task-modal-title">{payload.title}</h2>
                  {taskDetails?.updated_at ? (
                    <p className="task-modal__updated">
                      Last updated {formatTimestamp(taskDetails.updated_at)}
                    </p>
                  ) : null}
                </div>
                <StatusBadge status={activeTask.state} />
              </div>
            </div>
            <div className="task-modal__header-actions">
              <button
                ref={taskCloseButtonRef}
                type="button"
                className="link-button"
                onClick={onClose}
                aria-label="Close task modal"
              >
                Close
              </button>
              <InfoDialog
                triggerLabel="Show task technical details"
                dialogTitle="Task technical details"
                dialogDescription="Identifiers and runtime references for this task."
                className="task-modal__info-button"
              >
                <dl className="task-modal__technical-grid">
                  <div>
                    <dt>Task ID</dt>
                    <dd>{activeTask.human_task_id}</dd>
                  </div>
                  <div>
                    <dt>Run ID</dt>
                    <dd>{activeTask.workflow_run_id}</dd>
                  </div>
                  {activeTask.task_run_id ? (
                    <div>
                      <dt>Task Run ID</dt>
                      <dd>{activeTask.task_run_id}</dd>
                    </div>
                  ) : null}
                </dl>
              </InfoDialog>
            </div>
          </header>

          <div className="task-modal__body">
            <section className="task-modal__narrative">
              <p id="task-modal-description">
                {payload.description ??
                  "Review the task context, confirm evidence readiness, and run authoritative actions without leaving the current workflow view."}
              </p>
            </section>

            <section className="task-modal__section task-modal__section--summary" aria-label="Task overview">
              <dl className="task-modal__summary-grid">
                <div>
                  <dt>Owner</dt>
                  <dd>{activeTask.owner_role ?? "Unknown"}</dd>
                </div>
                <div>
                  <dt>Assignee</dt>
                  <dd>{activeTask.assignee_actor_id ?? "Unassigned"}</dd>
                </div>
                <div>
                  <dt>Stage / kind</dt>
                  <dd>
                    {taskDisplayHeading(activeTask)}
                  </dd>
                </div>
                <div>
                  <dt>Readiness</dt>
                  <dd>{taskReadinessSummary(activeTask)}</dd>
                </div>
              </dl>
            </section>

            <section className="task-modal__section" aria-label="Required documents">
              <header className="task-modal__section-header">
                <h3>Required Documents</h3>
              </header>
              {requiredDocumentRows.length > 0 ? (
                <ul className="task-modal__document-list">
                  {requiredDocumentRows.map((row) => {
                    const requirementBusy =
                      row.kind === "upload" &&
                      pendingTaskAction === "upload_required_response" &&
                      activeRequirementKey === `${row.requirement.dataset_key}:${row.requirement.artifact_kind}`;

                    return (
                      <li key={row.key} className={taskDocumentToneClass(row.tone)}>
                        <div className="task-modal__document-indicator" aria-hidden="true">
                          {taskDocumentMarker(row.tone, row.kind)}
                        </div>
                        <div className="task-modal__document-main">
                          <p className="task-modal__document-label">{row.display.label}</p>
                          <p className="task-modal__document-meta">{row.meta}</p>
                          {row.kind === "upload" && row.templateLabel ? (
                            <button
                              type="button"
                              className="task-modal__document-tertiary"
                              disabled={pendingTaskAction !== null || downloadingTemplateId !== null}
                              onClick={() => {
                                if (row.requirement.template_id) {
                                  void handleDownloadRequirementTemplate(row.requirement.template_id);
                                }
                              }}
                            >
                              {row.templateLabel}
                            </button>
                          ) : null}
                        </div>
                        <div className="task-modal__document-actions">
                          <span className={`task-modal__document-chip task-modal__document-chip--${row.tone}`}>
                            {row.statusLabel}
                          </span>
                          {row.kind === "upload" ? (
                            <DrawerRequiredUploadActions
                              actionLabel={row.actionLabel}
                              disabled={pendingTaskAction !== null || downloadingTemplateId !== null}
                              onUpload={(file) => {
                                void handleUploadRequiredResponse(row.requirement, file);
                              }}
                            />
                          ) : row.actionLabel ? (
                            <button
                              type="button"
                              className="action-btn action-btn--ghost"
                              disabled={pendingTaskAction !== null || !row.review.reviewed_artifact_version_id}
                              onClick={() => {
                                if (row.review.reviewed_artifact_version_id) {
                                  void handleOpenRequiredReviewDraft(row.review.reviewed_artifact_version_id);
                                }
                              }}
                            >
                              {row.actionLabel}
                            </button>
                          ) : null}
                          {requirementBusy ? (
                            <span className="detail-drawer__inline-status">Uploading…</span>
                          ) : null}
                        </div>
                      </li>
                    );
                  })}
                </ul>
              ) : (
                <p className="detail-drawer__hint">No required documents for this task.</p>
              )}
              {hasPendingReviewConfirmation ? (
                <p className="detail-drawer__hint">
                  Confirm review once all required draft artifacts have been checked.
                </p>
              ) : null}
            </section>

            {isCompositeTask ? (
              <section className="task-modal__section" aria-label="Task process">
                <header className="task-modal__section-header">
                  <h3>Task Process</h3>
                </header>
                {subgraphLoading ? <p className="detail-drawer__hint">Loading task process...</p> : null}
                {!subgraphLoading && subgraphError ? (
                  <div>
                    <p className="detail-drawer__error">
                      {errorText(subgraphError, "Task process failed to load")}
                    </p>
                    <button
                      type="button"
                      className="action-btn"
                      onClick={() => {
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

            <section className="task-modal__section" aria-label="Task artifacts">
              <header className="task-modal__section-header">
                <h3>Task Artifacts</h3>
                {hasAction(["upload_attachment"]) ? (
                  <button
                    type="button"
                    className="task-modal__document-tertiary"
                    disabled={pendingTaskAction !== null}
                    onClick={openUploadPicker}
                  >
                    Add supporting attachment
                  </button>
                ) : null}
              </header>
              {artifacts.length > 0 ? (
                <ul className="task-modal__artifact-chip-list">
                  {artifacts.map((artifact) => (
                    <li key={artifact.artifact_version_id}>
                      <button
                        type="button"
                        className="task-modal__artifact-chip"
                        onClick={() => void handleDownloadArtifact(artifact)}
                        disabled={downloadingArtifactVersionId === artifact.artifact_version_id}
                        aria-label={`Download ${artifact.file_name ?? artifact.artifact_kind}`}
                      >
                        <span className="task-modal__artifact-chip-label">
                          {artifact.file_name ?? artifact.artifact_kind}
                        </span>
                        <span className="task-modal__artifact-chip-meta">
                          {[artifact.source_label, artifact.artifact_role].filter(Boolean).join(" · ")}
                        </span>
                      </button>
                    </li>
                  ))}
                </ul>
              ) : artifactsLoading ? (
                <p className="detail-drawer__hint">Loading task artifacts...</p>
              ) : payload.artifact_sources && payload.artifact_sources.length > 0 ? (
                <p className="detail-drawer__hint">No task artifacts are currently linked.</p>
              ) : (
                <p className="detail-drawer__hint">No task artifacts are currently linked.</p>
              )}
            </section>

            <footer className="task-modal__footer">
              <dl className="task-modal__footer-meta">
                <div>
                  <dt>Candidate roles</dt>
                  <dd>
                    {activeTask.candidate_roles && activeTask.candidate_roles.length > 0
                      ? activeTask.candidate_roles.join(", ")
                      : "None"}
                  </dd>
                </div>
                <div>
                  <dt>Blocking / inputs</dt>
                  <dd>
                    {taskBlockingSummary(activeTask)}
                    {taskMissingInputSummary(activeTask) !== "Ready for work"
                      ? ` · ${taskMissingInputSummary(activeTask)}`
                      : ""}
                  </dd>
                </div>
              </dl>

              <div className="task-modal__footer-actions">
                <div className="task-modal__footer-actions-left">
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
                </div>
                <div className="task-modal__footer-actions-right">
                  {workspaceLink ? (
                    <Link className="action-btn action-btn--ghost" to={workspaceLink.to}>
                      {workspaceLink.label}
                    </Link>
                  ) : null}
                  {secondaryLinks.map((link) => (
                    <Link
                      key={`${link.label}:${link.to}`}
                      className="action-btn action-btn--ghost"
                      to={link.to}
                    >
                      {link.label}
                    </Link>
                  ))}
                  {supportingRouteActions.map((action) => (
                    <Link
                      key={action.action_id}
                      className="action-btn action-btn--ghost"
                      to={action.route as string}
                    >
                      {action.label}
                    </Link>
                  ))}
                  {primaryTaskAction ? (
                    <button
                      type="button"
                      className="action-btn action-btn--hero"
                      disabled={primaryTaskActionDisabled}
                      onClick={() => void handleTaskAction(primaryTaskAction)}
                    >
                      {taskPrimaryActionLabel(primaryTaskAction)}
                    </button>
                  ) : null}
                </div>
              </div>
            </footer>

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
              <p className="detail-drawer__error">
                {errorText(taskLoadError, "Task details failed to load")}
              </p>
            ) : null}
            {taskActionError ? (
              <p className="detail-drawer__error">
                {errorText(taskActionError, "Task action failed")}
              </p>
            ) : null}
          </div>
        </section>
      </div>
    );
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

      {downloadableArtifacts.length > 0 ? (
        <section className="detail-drawer__artifacts" aria-label="Downloadable artifacts">
          <h3>Downloadable Artifacts ({downloadableArtifacts.length})</h3>
          <ul className="detail-drawer__artifact-list">
            {downloadableArtifacts.map((artifact) => (
              <li
                key={`downloadable-artifact:${artifact.artifact_version_id}`}
                className="detail-drawer__artifact-row"
              >
                <div className="detail-drawer__artifact-meta">
                  <p className="detail-drawer__artifact-name">{artifact.label}</p>
                  <p className="detail-drawer__artifact-details">{artifact.source_label}</p>
                </div>
                <button
                  type="button"
                  className="action-btn"
                  onClick={() => void handleDownloadLightweightArtifact(artifact)}
                  disabled={downloadingArtifactVersionId === artifact.artifact_version_id}
                >
                  Download
                </button>
              </li>
            ))}
          </ul>
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

      {artifactsLoading ? <p className="detail-drawer__hint">Loading task artifacts...</p> : null}

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
    </aside>
  );
}

function uniqueStrings(values: string[]): string[] {
  return Array.from(new Set(values.filter(Boolean)));
}

function mergeTaskActions(
  primary: string[] | null | undefined,
  fallback: string[] | null | undefined
): string[] {
  return uniqueStrings([...(fallback ?? []), ...(primary ?? [])]);
}

function mergeTaskArray<T>(primary: T[] | null | undefined, fallback: T[] | null | undefined): T[] {
  const primaryValues = primary ?? [];
  if (primaryValues.length > 0) {
    return primaryValues;
  }
  return fallback ?? [];
}

function withSatisfiedRequiredUpload(
  task: DrawerTaskContext,
  requirement: WorkflowWorkspaceRequiredUpload
): DrawerTaskContext {
  const requiredUploads = task.required_uploads ?? [];
  const requiredReviews = task.required_reviews ?? [];
  const updatedUploads = requiredUploads.map((row) => {
    if (
      row.dataset_key !== requirement.dataset_key ||
      row.artifact_kind !== requirement.artifact_kind
    ) {
      return row;
    }
    return {
      ...row,
      current_count: Math.max(row.current_count, row.required_count, 1),
      status: "satisfied"
    };
  });
  const remainingMissingInputs = task.missing_required_inputs.filter(
    (value) => value !== requirement.dataset_key && value !== requirement.artifact_kind
  );
  const remainingBlockingReasons = task.blocking_reason_codes.filter(
    (code) =>
      code !== `required_upload_missing:${requirement.dataset_key}` &&
      code !== `required_upload_missing:${requirement.artifact_kind}`
  );
  const hasPendingReviewConfirmation = requiredReviews.some(
    (review) => review.status !== "confirmed"
  );
  const nextActions = task.available_actions.filter(
    (action) => action.toLowerCase() !== "complete"
  );
  if (hasPendingReviewConfirmation) {
    nextActions.push("confirm_review");
  } else if (remainingMissingInputs.length === 0) {
    nextActions.push("complete");
  }

  return {
    ...task,
    required_uploads: updatedUploads,
    missing_required_inputs: remainingMissingInputs,
    blocking_reason_codes: remainingBlockingReasons,
    available_actions: uniqueStrings(nextActions)
  };
}

function withConfirmedRequiredReviews(task: DrawerTaskContext): DrawerTaskContext {
  const requiredUploads = task.required_uploads ?? [];
  const requiredReviews = task.required_reviews ?? [];
  const updatedReviews = requiredReviews.map((review) => ({
    ...review,
    status: "confirmed" as const,
    review_confirmation_artifact_version_id:
      review.review_confirmation_artifact_version_id ?? "confirmed"
  }));
  const reviewKeys = new Set(
    requiredReviews.flatMap((review) =>
      [review.dataset_key, review.artifact_kind].filter((value): value is string => Boolean(value))
    )
  );
  const remainingMissingInputs = task.missing_required_inputs.filter((value) => !reviewKeys.has(value));
  const remainingBlockingReasons = task.blocking_reason_codes.filter(
    (code) => !code.startsWith("required_review_confirmation_missing:")
  );
  const hasMissingRequiredUpload = requiredUploads.some(
    (requirement) =>
      requirement.required !== false &&
      requirement.status !== "satisfied" &&
      requirement.current_count < requirement.required_count
  );
  const nextActions = task.available_actions.filter(
    (action) => action.toLowerCase() !== "confirm_review"
  );
  if (!hasMissingRequiredUpload && remainingMissingInputs.length === 0 && task.state !== "COMPLETED") {
    nextActions.push("complete");
  }

  return {
    ...task,
    required_reviews: updatedReviews,
    missing_required_inputs: remainingMissingInputs,
    blocking_reason_codes: remainingBlockingReasons,
    available_actions: uniqueStrings(nextActions)
  };
}

function drawerTaskContext(
  task: HumanTaskRow,
  fallback: DrawerTaskContext | null = null
): DrawerTaskContext {
  return {
    human_task_id: task.human_task_id,
    workflow_run_id: task.workflow_run_id,
    task_run_id: task.task_run_id,
    stage_id: task.stage_id,
    task_kind: task.task_kind,
    state: task.state,
    created_at: task.created_at,
    updated_at: task.updated_at,
    assignee_actor_id: task.assignee_actor_id,
    assignee_actor_type: task.assignee_actor_type,
    owner_role: task.owner_role,
    candidate_roles: task.candidate_roles ?? fallback?.candidate_roles ?? [],
    linked_approval_id: task.linked_approval_id,
    blocked_on_kind: task.blocked_on_kind,
    blocked_on_ref: task.blocked_on_ref,
    available_actions: mergeTaskActions(task.available_actions, fallback?.available_actions),
    blocking_reason_codes: mergeTaskArray(task.blocking_reason_codes, fallback?.blocking_reason_codes),
    missing_required_inputs: mergeTaskArray(
      task.missing_required_inputs,
      fallback?.missing_required_inputs
    ),
    required_uploads: mergeTaskArray(task.required_uploads, fallback?.required_uploads),
    required_reviews: mergeTaskArray(task.required_reviews, fallback?.required_reviews),
    workpage_actions: mergeTaskArray(task.workpage_actions, fallback?.workpage_actions),
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
