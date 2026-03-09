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
        title="Loading legacy workspace"
        detail="Resolving the latest schedule-planning run workspace."
      />
    );
  }

  if (query.isError) {
    return (
      <StatePanel
        kind="error"
        title="Legacy workspace failed to load"
        detail={errorText(query.error, "Unable to resolve latest schedule workspace")}
        onRetry={() => void query.refetch()}
      />
    );
  }

  const runs = query.data ?? [];
  if (runs.length === 0) {
    return (
      <StatePanel
        kind="empty"
        title="No schedule runs available"
        detail="Primary demo entrypoint is /demo/logistics; this workspace route is legacy."
      />
    );
  }

  return <Navigate to={`/runs/${runs[0].workflow_run_id}/workspace`} replace />;
}
