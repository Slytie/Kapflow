import { useMemo } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useParams } from "react-router-dom";

import { LegacyScheduleNotice } from "@/components/LegacyScheduleNotice";
import { StatePanel } from "@/components/StatePanel";
import { WorkflowGraph } from "@/components/WorkflowGraph";
import { WorkspaceTaskBoard } from "@/components/WorkspaceTaskBoard";
import { apiConfig } from "@/lib/api/config";
import { errorText } from "@/lib/api/errorText";
import { workflowRunsRepository } from "@/lib/repositories";
import { useDrawer } from "@/lib/state/drawerContext";
import { invalidateWorkspaceViews } from "@/lib/workspace/queryInvalidation";
import {
  buildStageNodeDrawerPayload,
  graphNodesWithResponsibility,
  workspaceTab
} from "@/lib/workspace/runWorkspaceGraph";

export function RunWorkspacePage(): JSX.Element {
  const { workflowRunId } = useParams<{ workflowRunId: string }>();
  const queryClient = useQueryClient();
  const { open } = useDrawer();

  const refreshWorkspaceViews = (): void => {
    void invalidateWorkspaceViews(queryClient, workflowRunId);
  };

  const runDetailQuery = useQuery({
    queryKey: ["run-detail", workflowRunId],
    queryFn: () => workflowRunsRepository.detail(workflowRunId as string),
    enabled: Boolean(workflowRunId),
    refetchInterval: apiConfig.pollIntervalMs
  });

  const isLiveDispatchRun = runDetailQuery.data?.workflow_run.workflow_id === "live_dispatch.v1";
  const shouldLoadWorkspace = Boolean(workflowRunId && runDetailQuery.data && !isLiveDispatchRun);

  const workspaceQuery = useQuery({
    queryKey: ["run-workspace", workflowRunId],
    queryFn: () => workflowRunsRepository.workspace(workflowRunId as string),
    enabled: shouldLoadWorkspace,
    refetchInterval: shouldLoadWorkspace ? apiConfig.pollIntervalMs : false
  });

  const workspace = workspaceQuery.data;
  const runDetail = runDetailQuery.data;
  const graphNodes = useMemo(() => {
    if (!workspace || !runDetail) {
      return [];
    }
    return graphNodesWithResponsibility(workspace.graph.nodes, runDetail.human_tasks);
  }, [workspace, runDetail]);

  if (!workflowRunId) {
    return (
      <StatePanel kind="empty" title="No workflow run id" detail="Open a run first to load workspace." />
    );
  }

  if (runDetailQuery.isLoading || (shouldLoadWorkspace && workspaceQuery.isLoading)) {
    return (
      <StatePanel
        kind="loading"
        title="Loading run workspace"
        detail="Fetching graph projection and board lanes."
      />
    );
  }

  if (runDetailQuery.isError || (shouldLoadWorkspace && workspaceQuery.isError)) {
    const queryError = runDetailQuery.error ?? workspaceQuery.error;
    return (
      <StatePanel
        kind="error"
        title="Run workspace failed to load"
        detail={errorText(queryError, "Unable to load workflow workspace")}
        onRetry={() => {
          void runDetailQuery.refetch();
          if (shouldLoadWorkspace) {
            void workspaceQuery.refetch();
          }
        }}
      />
    );
  }

  if (!runDetail) {
    return <StatePanel kind="empty" title="No run detail available" />;
  }

  if (isLiveDispatchRun) {
    return (
      <StatePanel
        kind="empty"
        title="Live Dispatch workspace removed"
        detail="Live Dispatch no longer exposes the shared workspace surface. Use run detail instead."
      />
    );
  }

  if (!workspace) {
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
      <LegacyScheduleNotice surface="Run workspace" />
      <WorkflowGraph
        nodes={graphNodes}
        edges={workspace.graph.edges}
        freshness={workspace.freshness}
        latestEventSequence={workspace.latest_event_sequence}
        selectedWorkflowTab={workspaceTab(workspace.workflow_run.workflow_id)}
        onNodeSelect={(node) => {
          open(buildStageNodeDrawerPayload(node, runDetail));
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
