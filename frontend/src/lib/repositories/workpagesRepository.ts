import { onetruthApi } from "@/lib/api/onetruthApi";
import type { WorkpageContract } from "@/lib/types/contracts";

export const workpagesRepository = {
  async schedule(): Promise<WorkpageContract> {
    return onetruthApi.getDemoWorkpage("schedule-v0");
  },

  async eod(): Promise<WorkpageContract> {
    return onetruthApi.getDemoWorkpage("eod-v0");
  }
};
