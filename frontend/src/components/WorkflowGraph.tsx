import { useMemo } from "react";

import { WorkflowGraphNode } from "@/components/WorkflowGraphNode";
import type {
  WorkflowWorkspaceFreshness,
  WorkflowWorkspaceGraphEdge,
  WorkflowWorkspaceGraphNode
} from "@/lib/types/contracts";

interface WorkflowGraphProps {
  nodes: WorkflowWorkspaceGraphNode[];
  edges: WorkflowWorkspaceGraphEdge[];
  freshness: WorkflowWorkspaceFreshness;
  latestEventSequence: number | null;
  selectedWorkflowTab?: string;
  onNodeSelect?: (node: WorkflowWorkspaceGraphNode) => void;
}

interface PositionedNode {
  node: WorkflowWorkspaceGraphNode;
  x: number;
  y: number;
}

const NODE_WIDTH = 188;
const NODE_HEIGHT = 56;
const HORIZONTAL_SPACING = 230;
const VERTICAL_SPACING = 100;
const PADDING_X = 34;
const PADDING_Y = 12;
const WORKFLOW_TABS = [
  "Payroll Processing",
  "Employee Onboarding",
  "Scheduling Coordination",
  "Expense Reporting"
];

function freshnessLine(
  freshness: WorkflowWorkspaceFreshness,
  latestEventSequence: number | null
): string {
  const parts = [`Freshness: ${freshness.status}`];
  if (freshness.as_of) {
    parts.push(`as of ${new Date(freshness.as_of).toLocaleString()}`);
  }
  if (latestEventSequence !== null) {
    parts.push(`event #${latestEventSequence}`);
  }
  if (freshness.note) {
    parts.push(freshness.note);
  }
  return parts.join(" · ");
}

function edgeStatusClass(
  edge: WorkflowWorkspaceGraphEdge,
  positions: Map<string, PositionedNode>
): "completed" | "warning" | "active" | "muted" {
  const target = positions.get(edge.to_node_id)?.node.status;
  if (target === "completed") {
    return "completed";
  }
  if (target === "warning" || target === "blocked") {
    return "warning";
  }
  if (target === "in_progress" || target === "awaiting_approval") {
    return "active";
  }
  return "muted";
}

function pathForEdge(
  edge: WorkflowWorkspaceGraphEdge,
  positions: Map<string, PositionedNode>
): string {
  const from = positions.get(edge.from_node_id);
  const to = positions.get(edge.to_node_id);
  if (!from || !to) {
    return "";
  }

  const fromX = from.x + NODE_WIDTH;
  const fromY = from.y + NODE_HEIGHT / 2;
  const toX = to.x;
  const toY = to.y + NODE_HEIGHT / 2;

  if (edge.edge_kind === "loopback") {
    const rise = Math.max(70, Math.abs(fromY - toY) + 52);
    const midX = (fromX + toX) / 2;
    return `M ${fromX} ${fromY} C ${fromX + 44} ${fromY - rise}, ${midX} ${toY - rise}, ${toX} ${toY}`;
  }

  if (edge.edge_kind === "branch") {
    const curveX = fromX + (toX - fromX) / 2;
    const curveY = Math.min(fromY, toY) - 34;
    return `M ${fromX} ${fromY} Q ${curveX} ${curveY}, ${toX} ${toY}`;
  }

  const delta = toX - fromX;
  const control = Math.max(20, delta * 0.45);
  return `M ${fromX} ${fromY} C ${fromX + control} ${fromY}, ${toX - control} ${toY}, ${toX} ${toY}`;
}

export function WorkflowGraph({
  nodes,
  edges,
  freshness,
  latestEventSequence,
  selectedWorkflowTab = "Scheduling Coordination",
  onNodeSelect
}: WorkflowGraphProps): JSX.Element {
  const positionedNodes = useMemo(() => {
    return nodes.map((node, index) => ({
      node,
      x: PADDING_X + (Number.isFinite(node.column) ? node.column : index) * HORIZONTAL_SPACING,
      y: PADDING_Y + (Number.isFinite(node.row) ? node.row : 0) * VERTICAL_SPACING
    }));
  }, [nodes]);

  const positionMap = useMemo(
    () => new Map(positionedNodes.map((entry) => [entry.node.node_id, entry])),
    [positionedNodes]
  );

  const maxX =
    Math.max(...positionedNodes.map((entry) => entry.x + NODE_WIDTH), NODE_WIDTH + PADDING_X * 2) +
    8;
  const maxY =
    Math.max(...positionedNodes.map((entry) => entry.y + NODE_HEIGHT), NODE_HEIGHT + PADDING_Y * 2) +
    22;

  return (
    <section className="workspace-graph" data-testid="workflow-graph">
      <div className="workspace-graph__tabs" role="tablist" aria-label="Workflows">
        {WORKFLOW_TABS.map((tab) => (
          <button
            key={tab}
            type="button"
            role="tab"
            aria-selected={tab === selectedWorkflowTab}
            className={tab === selectedWorkflowTab ? "is-active" : ""}
          >
            {tab}
          </button>
        ))}
        <button type="button" className="workspace-graph__tab-step">
          Step 4
          <span aria-hidden="true">✓</span>
        </button>
      </div>

      <div className="workspace-graph__viewport">
        <svg width={maxX} height={maxY} role="img" aria-label="Workflow progression graph">
          <defs>
            <marker
              id="workflow-graph-arrow"
              markerWidth="8"
              markerHeight="8"
              refX="6.5"
              refY="4"
              orient="auto"
            >
              <path d="M 0 0 L 8 4 L 0 8 z" className="workspace-graph__arrow" />
            </marker>
          </defs>
          {edges.map((edge) => (
            <g key={edge.edge_id}>
              <path
                d={pathForEdge(edge, positionMap)}
                className={[
                  "workspace-graph__edge",
                  `workspace-graph__edge--${edge.edge_kind}`,
                  `workspace-graph__edge--${edgeStatusClass(edge, positionMap)}`
                ].join(" ")}
                markerEnd="url(#workflow-graph-arrow)"
                data-testid={`workflow-graph-edge-${edge.edge_id}`}
              />
              {edge.label ? (
                <text
                  x={((positionMap.get(edge.from_node_id)?.x ?? 0) + (positionMap.get(edge.to_node_id)?.x ?? 0)) / 2 + 20}
                  y={((positionMap.get(edge.from_node_id)?.y ?? 0) + (positionMap.get(edge.to_node_id)?.y ?? 0)) / 2 + 8}
                  className="workspace-graph__edge-label"
                >
                  {edge.label}
                </text>
              ) : null}
            </g>
          ))}
          {positionedNodes.map((entry) => (
            <WorkflowGraphNode
              key={entry.node.node_id}
              node={entry.node}
              x={entry.x}
              y={entry.y}
              width={NODE_WIDTH}
              height={NODE_HEIGHT}
              onSelect={onNodeSelect}
            />
          ))}
        </svg>
      </div>
      <p className="workspace-graph__freshness" data-testid="workspace-freshness-line">
        {freshnessLine(freshness, latestEventSequence)}
      </p>
    </section>
  );
}
