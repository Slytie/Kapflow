import type { QueryClient } from "@tanstack/react-query";

export function invalidateWorkspaceViews(
  queryClient: QueryClient,
  workflowRunId: string | null | undefined
): Promise<unknown[]> {
  if (!workflowRunId) {
    return Promise.resolve([]);
  }
  return Promise.all([
    queryClient.invalidateQueries({ queryKey: ["run-workspace", workflowRunId] }),
    queryClient.invalidateQueries({ queryKey: ["run-detail", workflowRunId] }),
    queryClient.invalidateQueries({ queryKey: ["board-view"] }),
    queryClient.invalidateQueries({ queryKey: ["my-work"] }),
    queryClient.invalidateQueries({ queryKey: ["approvals"] }),
    queryClient.invalidateQueries({ queryKey: ["exceptions"] }),
    queryClient.invalidateQueries({ queryKey: ["runs"] })
  ]);
}
