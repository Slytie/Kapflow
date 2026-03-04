import { useMemo } from "react";

import { WorkflowGraphLegend } from "@/components/WorkflowGraphLegend";
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
  onNodeSelect?: (node: WorkflowWorkspaceGraphNode) => void;
}

interface PositionedNode {
  node: WorkflowWorkspaceGraphNode;
  x: number;
  y: number;
}

const NODE_WIDTH = 190;
const NODE_HEIGHT = 78;
const HORIZONTAL_SPACING = 250;
const VERTICAL_SPACING = 138;
const PADDING_X = 36;
const PADDING_Y = 28;

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
    const rise = Math.max(66, Math.abs(fromY - toY) + 44);
    const midX = (fromX + toX) / 2;
    return `M ${fromX} ${fromY} C ${fromX + 40} ${fromY - rise}, ${midX} ${toY - rise}, ${toX} ${toY}`;
  }

  if (edge.edge_kind === "branch") {
    const curveX = (fromX + toX) / 2;
    const curveY = Math.min(fromY, toY) - 26;
    return `M ${fromX} ${fromY} Q ${curveX} ${curveY}, ${toX} ${toY}`;
  }

  return `M ${fromX} ${fromY} L ${toX} ${toY}`;
}

export function WorkflowGraph({
  nodes,
  edges,
  freshness,
  latestEventSequence,
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
    8;

  return (
    <section className="workflow-graph" data-testid="workflow-graph">
      <header>
        <h3>Live Workflow Graph</h3>
        <WorkflowGraphLegend />
      </header>
      <div className="workflow-graph__viewport">
        <svg width={maxX} height={maxY} role="img" aria-label="Workflow run graph">
          <defs>
            <marker
              id="workflow-graph-arrow"
              markerWidth="10"
              markerHeight="10"
              refX="8"
              refY="5"
              orient="auto"
            >
              <path d="M 0 0 L 10 5 L 0 10 z" className="workflow-graph__arrow" />
            </marker>
          </defs>
          {edges.map((edge) => (
            <g key={edge.edge_id}>
              <path
                d={pathForEdge(edge, positionMap)}
                className={[
                  "workflow-graph__edge",
                  `workflow-graph__edge--${edge.edge_kind}`
                ].join(" ")}
                markerEnd="url(#workflow-graph-arrow)"
                data-testid={`workflow-graph-edge-${edge.edge_id}`}
              />
              {edge.label ? (
                <text
                  x={((positionMap.get(edge.from_node_id)?.x ?? 0) + (positionMap.get(edge.to_node_id)?.x ?? 0)) / 2 + 20}
                  y={((positionMap.get(edge.from_node_id)?.y ?? 0) + (positionMap.get(edge.to_node_id)?.y ?? 0)) / 2 + 8}
                  className="workflow-graph__edge-label"
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
      <p className="workflow-graph__freshness" data-testid="workspace-freshness-line">
        {freshnessLine(freshness, latestEventSequence)}
      </p>
    </section>
  );
}
