import { onetruthApi } from "@/lib/api/onetruthApi";
import type {
  CapexProject,
  CapexProjectDashboard,
  WorkflowRunRow
} from "@/lib/types/contracts";

export const capexProjectsRepository = {
  async listAssigned(limit = 5): Promise<CapexProject[]> {
    const projects = await onetruthApi.listCapexProjects({ limit, offset: 0 });
    return projects.filter((project) => project.state === "active").slice(0, limit);
  },

  async dashboard(projectId: string): Promise<CapexProjectDashboard> {
    return onetruthApi.getCapexProjectDashboard(projectId, { limit: 8, offset: 0 });
  },

  async workflowRuns(projectId: string): Promise<WorkflowRunRow[]> {
    return onetruthApi.listCapexProjectWorkflowRuns(projectId, { limit: 50, offset: 0 });
  }
};
