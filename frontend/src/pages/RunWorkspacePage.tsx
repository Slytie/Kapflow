import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useParams } from "react-router-dom";

import { WorkflowGraph } from "@/components/WorkflowGraph";
import { WorkspaceTaskBoard } from "@/components/WorkspaceTaskBoard";
import { StatePanel } from "@/components/StatePanel";
import { apiConfig } from "@/lib/api/config";
import { errorText } from "@/lib/api/errorText";
import { workflowRunsRepository } from "@/lib/repositories";
import { useDrawer } from "@/lib/state/drawerContext";
import type { DrawerArtifact, DrawerArtifactSource } from "@/lib/types/ui";
import type { WorkflowRunDetailContract, WorkflowWorkspaceGraphNode } from "@/lib/types/contracts";

function workflowTab(workflowId: string): string {
  if (workflowId === "schedule_planning.v1") {
    return "Scheduling Coordination";
  }
  return "Scheduling Coordination";
}

function stageArtifactSources(
  node: WorkflowWorkspaceGraphNode,
  runDetail: WorkflowRunDetailContract
): DrawerArtifactSource[] {
  const byKey = new Map<string, DrawerArtifactSource>();

  const addSource = (source: DrawerArtifactSource): void => {
    const key = `${source.subject_kind}:${source.subject_id}`;
    if (!byKey.has(key)) {
      byKey.set(key, source);
    }
  };

  for (const task of runDetail.human_tasks) {
    if (task.stage_id !== node.stage_id) {
      continue;
    }
    addSource({
      workflow_run_id: task.workflow_run_id,
      subject_kind: "human_task",
      subject_id: task.human_task_id,
      source_label: "Stage task attachment"
    });
    addSource({
      workflow_run_id: task.workflow_run_id,
      subject_kind: "task_run",
      subject_id: task.task_run_id,
      source_label: "Stage step output"
    });
  }

  for (const approval of runDetail.approvals) {
    if (approval.scope_ref !== node.stage_id) {
      continue;
    }
    addSource({
      workflow_run_id: approval.workflow_run_id,
      subject_kind: "approval",
      subject_id: approval.approval_id,
      source_label: "Stage approval evidence"
    });
  }

  if (node.stage_id === "Stage07") {
    for (const flag of runDetail.flags) {
      addSource({
        workflow_run_id: flag.workflow_run_id,
        subject_kind: "flag",
        subject_id: flag.flag_id,
        source_label: "Stage flag evidence"
      });
    }
  }

  return Array.from(byKey.values());
}

function artifactFileName(
  artifact: WorkflowRunDetailContract["artifact_versions"][number]
): string | null {
  const fileName = artifact.metadata_json?.file_name;
  if (typeof fileName === "string" && fileName.length > 0) {
    return fileName;
  }
  return null;
}

function stageArtifacts(
  node: WorkflowWorkspaceGraphNode,
  runDetail: WorkflowRunDetailContract
): DrawerArtifact[] {
  const stageTaskIds = new Set<string>();
  const stageTaskRunIds = new Set<string>();
  for (const task of runDetail.human_tasks) {
    if (task.stage_id === node.stage_id) {
      stageTaskIds.add(task.human_task_id);
      stageTaskRunIds.add(task.task_run_id);
    }
  }

  const stageApprovalIds = new Set<string>();
  const stageApprovalTaskRunIds = new Set<string>();
  for (const approval of runDetail.approvals) {
    if (approval.scope_ref === node.stage_id) {
      stageApprovalIds.add(approval.approval_id);
      stageApprovalTaskRunIds.add(approval.task_run_id);
    }
  }

  const stagePointerArtifactIds = new Set<string>();
  for (const pointer of runDetail.pointers) {
    if (pointer.scope_kind === "stage" && pointer.scope_ref === node.stage_id) {
      stagePointerArtifactIds.add(pointer.artifact_version_id);
    }
  }

  const stageFlagIds = new Set<string>();
  if (node.stage_id === "Stage07") {
    for (const flag of runDetail.flags) {
      stageFlagIds.add(flag.flag_id);
    }
  }

  const byArtifactVersionId = new Map<string, DrawerArtifact>();

  for (const artifact of runDetail.artifact_versions) {
    const links = artifact.links ?? [];

    const linkedToStageTask = links.some(
      (link) => link.subject_kind === "human_task" && stageTaskIds.has(link.subject_id)
    );
    const linkedToStageTaskRun = links.some(
      (link) => link.subject_kind === "task_run" && stageTaskRunIds.has(link.subject_id)
    );
    const linkedToStageApproval = links.some(
      (link) => link.subject_kind === "approval" && stageApprovalIds.has(link.subject_id)
    );
    const linkedToStageFlag = links.some(
      (link) => link.subject_kind === "flag" && stageFlagIds.has(link.subject_id)
    );
    const createdByStageTaskRun = artifact.task_run_id ? stageTaskRunIds.has(artifact.task_run_id) : false;
    const createdByStageApprovalTaskRun = artifact.task_run_id
      ? stageApprovalTaskRunIds.has(artifact.task_run_id)
      : false;
    const pointerMatchesStage = stagePointerArtifactIds.has(artifact.artifact_version_id);
    const metadataStageId =
      typeof artifact.metadata_json?.stage_id === "string" ? artifact.metadata_json.stage_id : null;
    const metadataMatchesStage = metadataStageId === node.stage_id;

    if (
      !linkedToStageTask &&
      !linkedToStageTaskRun &&
      !linkedToStageApproval &&
      !linkedToStageFlag &&
      !createdByStageTaskRun &&
      !createdByStageApprovalTaskRun &&
      !pointerMatchesStage &&
      !metadataMatchesStage
    ) {
      continue;
    }

    let sourceLabel = "Stage evidence";
    if (linkedToStageTask) {
      sourceLabel = "Stage task attachment";
    } else if (linkedToStageTaskRun || createdByStageTaskRun || createdByStageApprovalTaskRun) {
      sourceLabel = "Stage step output";
    } else if (linkedToStageApproval) {
      sourceLabel = "Stage approval evidence";
    } else if (linkedToStageFlag) {
      sourceLabel = "Stage flag evidence";
    } else if (pointerMatchesStage) {
      sourceLabel = "Stage official output";
    }

    byArtifactVersionId.set(artifact.artifact_version_id, {
      artifact_version_id: artifact.artifact_version_id,
      artifact_kind: artifact.artifact_kind,
      artifact_role: artifact.artifact_role ?? null,
      media_type: artifact.media_type,
      created_at: artifact.created_at,
      file_name: artifactFileName(artifact),
      source_label: sourceLabel
    });
  }

  return Array.from(byArtifactVersionId.values()).sort((left, right) =>
    right.created_at.localeCompare(left.created_at)
  );
}

export function RunWorkspacePage(): JSX.Element {
  const { workflowRunId } = useParams<{ workflowRunId: string }>();
  const queryClient = useQueryClient();
  const { open } = useDrawer();

  const refreshWorkspaceViews = (): void => {
    if (!workflowRunId) {
      return;
    }
    void Promise.all([
      queryClient.invalidateQueries({ queryKey: ["run-workspace", workflowRunId] }),
      queryClient.invalidateQueries({ queryKey: ["run-detail", workflowRunId] }),
      queryClient.invalidateQueries({ queryKey: ["board-view"] }),
      queryClient.invalidateQueries({ queryKey: ["my-work"] }),
      queryClient.invalidateQueries({ queryKey: ["approvals"] }),
      queryClient.invalidateQueries({ queryKey: ["exceptions"] }),
      queryClient.invalidateQueries({ queryKey: ["runs"] })
    ]);
  };

  const workspaceQuery = useQuery({
    queryKey: ["run-workspace", workflowRunId],
    queryFn: () => workflowRunsRepository.workspace(workflowRunId as string),
    enabled: Boolean(workflowRunId),
    refetchInterval: apiConfig.pollIntervalMs
  });

  const runDetailQuery = useQuery({
    queryKey: ["run-detail", workflowRunId],
    queryFn: () => workflowRunsRepository.detail(workflowRunId as string),
    enabled: Boolean(workflowRunId),
    refetchInterval: apiConfig.pollIntervalMs
  });

  if (!workflowRunId) {
    return (
      <StatePanel kind="empty" title="No workflow run id" detail="Open a run first to load workspace." />
    );
  }

  if (workspaceQuery.isLoading || runDetailQuery.isLoading) {
    return (
      <StatePanel
        kind="loading"
        title="Loading run workspace"
        detail="Fetching graph projection and board lanes."
      />
    );
  }

  if (workspaceQuery.isError || runDetailQuery.isError) {
    const queryError = workspaceQuery.error ?? runDetailQuery.error;
    return (
      <StatePanel
        kind="error"
        title="Run workspace failed to load"
        detail={errorText(queryError, "Unable to load workflow workspace")}
        onRetry={() => {
          void workspaceQuery.refetch();
          void runDetailQuery.refetch();
        }}
      />
    );
  }

  const workspace = workspaceQuery.data;
  const runDetail = runDetailQuery.data;
  if (!workspace || !runDetail) {
    return <StatePanel kind="empty" title="No workspace projection available" />;
  }

  if (
    workspace.graph.nodes.length === 0 &&
    runDetail.human_tasks.length === 0 &&
    runDetail.approvals.length === 0 &&
    runDetail.flags.length === 0
  ) {
    return (
      <StatePanel
        kind="empty"
        title="Workspace projection is empty"
        detail="No graph or actionable work is currently projected."
      />
    );
  }

  return (
    <section className="workspace-page" data-testid="run-workspace-page">
      <WorkflowGraph
        nodes={workspace.graph.nodes}
        edges={workspace.graph.edges}
        freshness={workspace.freshness}
        latestEventSequence={workspace.latest_event_sequence}
        selectedWorkflowTab={workflowTab(workspace.workflow_run.workflow_id)}
        onNodeSelect={(node) => {
          const stageTasks = runDetail.human_tasks.filter((task) => task.stage_id === node.stage_id);
          const stageSources = stageArtifactSources(node, runDetail);
          const stageArtifactsForDrawer = stageArtifacts(node, runDetail);
          const stageCompletedTasks = stageTasks.filter((task) => task.state === "COMPLETED").length;
          open({
            title: `${node.stage_id} ${node.label}`,
            subtitle: node.node_id,
            description: "Graph node status is projected by the server workspace endpoint.",
            fields: [
              { label: "Status", value: node.status },
              { label: "Row", value: String(node.row) },
              { label: "Column", value: String(node.column) },
              { label: "Blocking", value: node.is_blocking ? "yes" : "no" },
              { label: "Stage tasks", value: String(stageTasks.length) },
              { label: "Completed tasks", value: String(stageCompletedTasks) }
            ],
            artifacts: stageArtifactsForDrawer,
            artifact_sources: stageSources
          });
        }}
      />

      <div className="workspace-page__divider" />

      <WorkspaceTaskBoard
        workflowRunId={workflowRunId}
        workspace={workspace}
        detail={runDetail}
        onRefresh={refreshWorkspaceViews}
        onOpenDetails={open}
      />
    </section>
  );
}
