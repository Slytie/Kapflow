import type { QueryClient } from "@tanstack/react-query";

import { buildBoardItemDrawerPayload } from "@/lib/logistics/familyStory";
import { workflowRunsRepository } from "@/lib/repositories";
import type { LogisticsStoryBoardWorkItem, WorkflowRunWorkspaceContract } from "@/lib/types/contracts";
import type { DrawerPayload } from "@/lib/types/ui";
import {
  buildTaskDetailPayload,
  findWorkspaceTaskItemByHumanTaskId,
  findWorkspaceTaskItemByLinkedApprovalId
} from "@/lib/workspace/taskDetailPayload";

function runWorkspaceQuery(
  queryClient: QueryClient,
  workflowRunId: string
): Promise<WorkflowRunWorkspaceContract> {
  return queryClient.fetchQuery({
    queryKey: ["run-workspace", workflowRunId],
    queryFn: () => workflowRunsRepository.workspace(workflowRunId)
  });
}

export async function resolveLogisticsBoardItemDetail({
  item,
  queryClient
}: {
  item: LogisticsStoryBoardWorkItem;
  queryClient: QueryClient;
}): Promise<DrawerPayload> {
  if (item.item_type === "flag") {
    return buildBoardItemDrawerPayload(item);
  }

  try {
    const workspace = await runWorkspaceQuery(queryClient, item.workflow_run_id);
    const taskItem =
      item.item_type === "human_task"
        ? findWorkspaceTaskItemByHumanTaskId(workspace, item.subject_id)
        : findWorkspaceTaskItemByLinkedApprovalId(workspace, item.subject_id);

    if (taskItem) {
      return buildTaskDetailPayload({
        task: taskItem.human_task,
        item: taskItem,
        description:
          "Inspect context and run authoritative task actions from the centered task modal without leaving the logistics shell.",
        links: [{ label: "Open run detail (secondary)", to: `/runs/${taskItem.human_task.workflow_run_id}` }]
      });
    }
  } catch {
    // Fall back to the lightweight board payload if workspace context cannot be resolved.
  }

  return buildBoardItemDrawerPayload(item);
}
