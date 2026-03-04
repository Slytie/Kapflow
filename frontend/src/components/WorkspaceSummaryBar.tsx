import type { WorkflowRunWorkspaceContract } from "@/lib/types/contracts";

interface WorkspaceSummaryBarProps {
  workspace: WorkflowRunWorkspaceContract;
}

export function WorkspaceSummaryBar({ workspace }: WorkspaceSummaryBarProps): JSX.Element {
  const totalNodes = workspace.graph.nodes.length;
  const completedNodes = workspace.graph.nodes.filter((node) => node.status === "completed").length;
  const blockingNodes = workspace.graph.nodes.filter((node) => node.is_blocking).length;
  const actionableItems = workspace.user_work.length;
  const blockingItems = workspace.blocking_work.length;

  return (
    <section className="workspace-summary-bar" aria-label="Workspace summary">
      <div>
        <strong>{workspace.workflow_run.workflow_id}</strong>
        <p>{workspace.workflow_run.workflow_run_id}</p>
      </div>
      <ul>
        <li>{completedNodes}/{totalNodes} completed</li>
        <li>{blockingNodes} blocking node(s)</li>
        <li>{actionableItems} actionable item(s)</li>
        <li>{blockingItems} blocking item(s)</li>
      </ul>
    </section>
  );
}
