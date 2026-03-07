import { useQuery } from "@tanstack/react-query";
import { Navigate } from "react-router-dom";

import { StatePanel } from "@/components/StatePanel";
import { apiConfig } from "@/lib/api/config";
import { errorText } from "@/lib/api/errorText";
import { workflowRunsRepository } from "@/lib/repositories";

export function WorkspaceHomePage(): JSX.Element {
  const query = useQuery({
    queryKey: ["workspace-home-runs"],
    queryFn: () => workflowRunsRepository.list(),
    refetchInterval: apiConfig.pollIntervalMs
  });

  if (query.isLoading) {
    return (
      <StatePanel
        kind="loading"
        title="Loading workspace"
        detail="Resolving the latest run workspace."
      />
    );
  }

  if (query.isError) {
    return (
      <StatePanel
        kind="error"
        title="Workspace failed to load"
        detail={errorText(query.error, "Unable to resolve latest workspace")}
        onRetry={() => void query.refetch()}
      />
    );
  }

  const runs = query.data ?? [];
  if (runs.length === 0) {
    return (
      <StatePanel
        kind="empty"
        title="No runs available"
        detail="Create a run first to open the workspace."
      />
    );
  }

  return <Navigate to={`/runs/${runs[0].workflow_run_id}/workspace`} replace />;
}
