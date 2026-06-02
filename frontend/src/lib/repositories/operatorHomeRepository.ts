import { onetruthApi } from "@/lib/api/onetruthApi";
import type { OperatorHomeContract } from "@/lib/types/contracts";

export const operatorHomeRepository = {
  async get(): Promise<OperatorHomeContract> {
    return onetruthApi.getOperatorHome();
  }
};
