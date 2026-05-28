import type { WorkflowWorkspaceGraphEdge, WorkflowWorkspaceGraphNode } from "@/lib/types/contracts";

interface LogisticsFamilyNavProps {
  nodes: WorkflowWorkspaceGraphNode[];
  edges: WorkflowWorkspaceGraphEdge[];
  activeNodeId?: string | null;
  onNodeSelect: (nodeId: string) => void;
}

function nodeEyebrow(node: WorkflowWorkspaceGraphNode): string {
  if (node.stage_id === "weekly_schedule_planning.v1") {
    return "Planning workflow";
  }
  if (node.stage_id === "dispatch_reporting.v1") {
    return "Reporting workflow";
  }
  return "Workflow module";
}

function nodeStatusClass(status: WorkflowWorkspaceGraphNode["status"]): string {
  if (status === "completed") {
    return "is-completed";
  }
  if (status === "warning" || status === "blocked") {
    return "is-warning";
  }
  if (status === "in_progress" || status === "awaiting_approval") {
    return "is-active";
  }
  if (status === "ready") {
    return "is-ready";
  }
  return "is-idle";
}

export function LogisticsFamilyNav({
  nodes,
  edges,
  activeNodeId = null,
  onNodeSelect
}: LogisticsFamilyNavProps): JSX.Element {
  const orderedNodes = [...nodes].sort((left, right) => {
    const columnCompare = left.column - right.column;
    if (columnCompare !== 0) {
      return columnCompare;
    }
    return left.row - right.row;
  });
  const edgeLookup = new Map(
    edges.map((edge) => [`${edge.from_node_id}->${edge.to_node_id}`, edge.edge_id])
  );

  return (
    <section className="logistics-family-nav" data-testid="logistics-family-nav">
      <nav
        className="logistics-family-nav__graph"
        aria-label="Logistics family navigation"
      >
        {orderedNodes.map((node, index) => {
          const isActive = node.node_id === activeNodeId;
          const eyebrow = nodeEyebrow(node);
          const previousNode = orderedNodes[index - 1];
          const edgeId = previousNode
            ? edgeLookup.get(`${previousNode.node_id}->${node.node_id}`) ??
              `${previousNode.node_id}-${node.node_id}`
            : null;
          return (
            <div key={node.node_id} className="logistics-family-nav__step">
              {edgeId ? (
                <span
                  className="logistics-family-nav__edge"
                  data-testid={`logistics-family-nav-edge-${edgeId}`}
                  aria-hidden="true"
                />
              ) : null}
              <button
                type="button"
                className={[
                  "logistics-family-nav__node",
                  nodeStatusClass(node.status),
                  isActive ? "is-selected" : ""
                ].join(" ")}
                data-testid={`logistics-family-nav-node-${node.node_id}`}
                aria-pressed={isActive}
                aria-label={`Open ${node.label}`}
                onClick={() => {
                  onNodeSelect(node.node_id);
                }}
              >
                <span
                  className={`logistics-family-nav__dot ${nodeStatusClass(node.status)}`}
                  aria-hidden="true"
                />
                <span className="logistics-family-nav__copy">
                  <span className="logistics-family-nav__eyebrow">{eyebrow}</span>
                  <span className="logistics-family-nav__label">{node.label}</span>
                </span>
                {node.responsibility_summary ? (
                  <span className="logistics-family-nav__summary">{node.responsibility_summary}</span>
                ) : null}
              </button>
            </div>
          );
        })}
      </nav>
    </section>
  );
}
