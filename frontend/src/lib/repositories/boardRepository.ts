import { onetruthApi } from "@/lib/api/onetruthApi";
import { deriveBoardLanes } from "@/lib/mappers/boardLaneMapper";
import type { BoardViewModel } from "@/lib/types/ui";

export interface BoardQuery {
  workflowRunId?: string;
  state?: string;
  assignee?: string;
}

export const boardRepository = {
  async view(query: BoardQuery): Promise<BoardViewModel> {
    const boardQuery = {
      workflow_id: "schedule_planning.v1",
      workflow_run_id:
        query.workflowRunId && query.workflowRunId !== "all" ? query.workflowRunId : undefined,
      task_state: query.state && query.state !== "all" ? query.state : undefined,
      assignee_actor_id:
        query.assignee && query.assignee !== "all" ? query.assignee : undefined,
      limit: 500,
      offset: 0
    };

    const [board, flags] = await Promise.all([
      onetruthApi.listBoard(boardQuery),
      onetruthApi.listFlags({
        workflow_run_id: boardQuery.workflow_run_id,
        state: query.state && query.state !== "all" ? query.state.toLowerCase() : undefined,
        limit: 300,
        offset: 0
      })
    ]);

    return {
      lanes: deriveBoardLanes({ cards: board.cards, flags }),
      workflowRuns: board.workflow_runs
    };
  }
};
