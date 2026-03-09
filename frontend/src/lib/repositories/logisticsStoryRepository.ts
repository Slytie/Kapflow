import { onetruthApi } from "@/lib/api/onetruthApi";
import type { LogisticsThreeWorkflowStoryContract } from "@/lib/types/contracts";

const DEFAULT_PLANNING_WEEK_ID = "PW-2026-W10";

export interface LogisticsStoryQuery {
  planningWeekId?: string;
  serviceDateId?: string;
}

export const logisticsStoryRepository = {
  async view(query: LogisticsStoryQuery = {}): Promise<LogisticsThreeWorkflowStoryContract> {
    const planningWeekId = query.planningWeekId?.trim() || DEFAULT_PLANNING_WEEK_ID;
    const serviceDateId = query.serviceDateId?.trim() || undefined;
    return onetruthApi.getLogisticsThreeWorkflowStory({
      planning_week_id: planningWeekId,
      service_date_id: serviceDateId
    });
  }
};
