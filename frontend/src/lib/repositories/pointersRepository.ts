import { onetruthApi } from "@/lib/api/onetruthApi";
import type { PointerRow } from "@/lib/types/contracts";

export interface PointerQuery {
  workflowRunId?: string;
}

export const pointersRepository = {
  async list(query: PointerQuery): Promise<PointerRow[]> {
    return onetruthApi.listPointers({
      workflow_run_id:
        query.workflowRunId && query.workflowRunId !== "all" ? query.workflowRunId : undefined,
      limit: 300,
      offset: 0
    });
  }
};
