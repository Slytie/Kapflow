import { useQuery, useQueryClient } from "@tanstack/react-query";
import { Link, useParams } from "react-router-dom";

import { WorkflowGraph } from "@/components/WorkflowGraph";
import { WorkspaceActionPanel } from "@/components/WorkspaceActionPanel";
import { WorkspaceSummaryBar } from "@/components/WorkspaceSummaryBar";
import { StatePanel } from "@/components/StatePanel";
import { apiConfig } from "@/lib/api/config";
import { errorText } from "@/lib/api/errorText";
import { workflowRunsRepository } from "@/lib/repositories";
import { useDrawer } from "@/lib/state/drawerContext";

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

  if (!workflowRunId) {
    return (
      <StatePanel kind="empty" title="No workflow run id" detail="Open a run first to load workspace." />
    );
  }

  if (workspaceQuery.isLoading) {
    return (
      <StatePanel
        kind="loading"
        title="Loading run workspace"
        detail="Fetching graph projection and actionable work."
      />
    );
  }

  if (workspaceQuery.isError) {
    return (
      <StatePanel
        kind="error"
        title="Run workspace failed to load"
        detail={errorText(workspaceQuery.error, "Unable to load workflow workspace")}
        onRetry={() => void workspaceQuery.refetch()}
      />
    );
  }

  const workspace = workspaceQuery.data;
  if (!workspace) {
    return <StatePanel kind="empty" title="No workspace projection available" />;
  }

  if (workspace.graph.nodes.length === 0 && workspace.user_work.length === 0) {
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
      <header className="workspace-page__header">
        <div>
          <h2>Run Workspace</h2>
          <p>{workspace.workflow_run.workflow_run_id}</p>
        </div>
        <div className="workspace-page__links">
          <Link className="link-button" to={`/runs/${workflowRunId}`}>
            View run detail
          </Link>
          <Link className="link-button" to="/official-outputs">
            Open official outputs
          </Link>
        </div>
      </header>

      <WorkspaceSummaryBar workspace={workspace} />

      <WorkflowGraph
        nodes={workspace.graph.nodes}
        edges={workspace.graph.edges}
        freshness={workspace.freshness}
        latestEventSequence={workspace.latest_event_sequence}
        onNodeSelect={(node) =>
          open({
            title: `${node.stage_id} ${node.label}`,
            subtitle: node.node_id,
            description: "Graph node status is projected by the server workspace endpoint.",
            fields: [
              { label: "Status", value: node.status },
              { label: "Row", value: String(node.row) },
              { label: "Column", value: String(node.column) },
              { label: "Blocking", value: node.is_blocking ? "yes" : "no" }
            ]
          })
        }
      />

      <WorkspaceActionPanel
        workflowRunId={workflowRunId}
        userWork={workspace.user_work}
        blockingWork={workspace.blocking_work}
        onRefresh={refreshWorkspaceViews}
        onOpenDetails={open}
      />
    </section>
  );
}
