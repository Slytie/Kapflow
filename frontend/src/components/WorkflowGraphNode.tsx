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

type VisualStatus = "completed" | "warning" | "active" | "muted";

function visualStatus(status: WorkflowWorkspaceNodeStatus): VisualStatus {
  if (status === "completed") {
    return "completed";
  }
  if (status === "warning" || status === "blocked") {
    return "warning";
  }
  if (status === "in_progress" || status === "awaiting_approval") {
    return "active";
  }
  return "muted";
}

function iconKind(status: WorkflowWorkspaceNodeStatus): "check" | "warning" | "dot" {
  if (status === "completed") {
    return "check";
  }
  if (status === "warning" || status === "blocked") {
    return "warning";
  }
  return "dot";
}

function stripStagePrefix(label: string): string {
  return label.replace(/^Stage\d+\s+/i, "");
}

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

  const statusClass = visualStatus(node.status);
  const nodeIcon = iconKind(node.status);

  return (
    <g
      className={[
        "workflow-graph-pill",
        `workflow-graph-pill--${statusClass}`,
        node.is_blocking ? "is-blocking" : ""
      ].join(" ")}
      transform={`translate(${x}, ${y})`}
      data-status={node.status}
      data-testid={`workflow-graph-node-${node.node_id}`}
      role="button"
      tabIndex={0}
      aria-label={`Open details for ${stripStagePrefix(node.label)}`}
      onClick={handleSelect}
      onKeyDown={(event) => {
        if (event.key === "Enter" || event.key === " ") {
          event.preventDefault();
          handleSelect();
        }
      }}
    >
      <rect width={width} height={height} rx={height / 2} ry={height / 2} />

      <g className="workflow-graph-pill__icon" transform="translate(14, 12)">
        <circle cx="12" cy="12" r="12" />
        {nodeIcon === "check" ? (
          <path d="M 7 12.5 L 10.5 16 L 17 8.8" />
        ) : null}
        {nodeIcon === "warning" ? (
          <>
            <path d="M 12 5 L 19 18 H 5 Z" />
            <path d="M 12 9.5 V 13" />
            <circle cx="12" cy="15.8" r="1" />
          </>
        ) : null}
        {nodeIcon === "dot" ? <circle cx="12" cy="12" r="4" className="workflow-graph-pill__dot" /> : null}
      </g>

      <text x={46} y={28} className="workflow-graph-pill__label">
        {stripStagePrefix(node.label)}
      </text>
      <text x={46} y={43} className="workflow-graph-pill__stage">
        {node.stage_id}
      </text>
      {node.responsibility_summary ? (
        <text x={46} y={58} className="workflow-graph-pill__responsibility">
          {node.responsibility_summary}
        </text>
      ) : null}
      {node.responsibility_detail ? (
        <text x={46} y={70} className="workflow-graph-pill__task-detail">
          {node.responsibility_detail}
        </text>
      ) : null}
    </g>
  );
}
