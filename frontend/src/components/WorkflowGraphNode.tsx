import type {
  WorkflowWorkspaceGraphNode,
  WorkflowWorkspaceNodeStatus
} from "@/lib/types/contracts";

interface WorkflowGraphNodeProps {
  node: WorkflowWorkspaceGraphNode;
  x: number;
  y: number;
  width: number;
  height: number;
  onSelect?: (node: WorkflowWorkspaceGraphNode) => void;
}

const STATUS_LABELS: Record<WorkflowWorkspaceNodeStatus, string> = {
  not_started: "Not Started",
  ready: "Ready",
  in_progress: "In Progress",
  blocked: "Blocked",
  awaiting_approval: "Awaiting Approval",
  completed: "Completed",
  warning: "Warning"
};

export function WorkflowGraphNode({
  node,
  x,
  y,
  width,
  height,
  onSelect
}: WorkflowGraphNodeProps): JSX.Element {
  const handleSelect = (): void => {
    onSelect?.(node);
  };

  return (
    <g
      className={[
        "workflow-graph-node",
        `workflow-graph-node--${node.status}`,
        node.is_blocking ? "is-blocking" : ""
      ].join(" ")}
      transform={`translate(${x}, ${y})`}
      data-testid={`workflow-graph-node-${node.node_id}`}
    >
      <rect
        width={width}
        height={height}
        rx={10}
        ry={10}
        role="button"
        tabIndex={0}
        onClick={handleSelect}
        onKeyDown={(event) => {
          if (event.key === "Enter" || event.key === " ") {
            event.preventDefault();
            handleSelect();
          }
        }}
      />
      <text x={12} y={22} className="workflow-graph-node__stage">
        {node.stage_id}
      </text>
      <text x={12} y={42} className="workflow-graph-node__label">
        {node.label}
      </text>
      <text x={12} y={62} className="workflow-graph-node__status">
        {STATUS_LABELS[node.status]}
      </text>
    </g>
  );
}
