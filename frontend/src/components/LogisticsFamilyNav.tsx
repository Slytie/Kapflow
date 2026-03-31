import type {
  WorkflowWorkspaceGraphEdge,
  WorkflowWorkspaceGraphNode
} from "@/lib/types/contracts";
import type { LogisticsTaskStripCardModel } from "@/lib/logistics/familyStory";

interface LogisticsFamilyNavProps {
  nodes: WorkflowWorkspaceGraphNode[];
  edges: WorkflowWorkspaceGraphEdge[];
  activeNodeId?: string | null;
  taskCards: LogisticsTaskStripCardModel[];
  onNodeSelect: (nodeId: string) => void;
  onTaskSelect: (laneId: LogisticsTaskStripCardModel["lane_id"]) => void;
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
  taskCards,
  onNodeSelect,
  onTaskSelect
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
      <div
        className="logistics-family-nav__tasks"
        aria-label="Persistent task strip"
        data-testid="logistics-task-strip"
      >
        {taskCards.map((card) => {
          const title = card.top_item?.title ?? "No active work";
          return (
            <button
              key={card.lane_id}
              type="button"
              className={`logistics-family-nav__task-card${
                card.count === 0 ? " is-empty" : ""
              }`}
              data-testid={`logistics-task-strip-card-${card.lane_id}`}
              disabled={card.count === 0}
              onClick={() => {
                onTaskSelect(card.lane_id);
              }}
              aria-label={
                card.count === 0
                  ? `${card.title}: no active work`
                  : `${card.title}: ${card.count} items, top item ${title}`
              }
            >
              <span className="logistics-family-nav__task-card-header">
                <strong>{card.title}</strong>
                <span>{card.count}</span>
              </span>
              <span className="logistics-family-nav__task-card-title">{title}</span>
              {card.extra_count > 0 ? (
                <span className="logistics-family-nav__task-card-more">
                  +{card.extra_count}
                </span>
              ) : null}
            </button>
          );
        })}
      </div>

      <nav
        className="logistics-family-nav__graph"
        aria-label="Logistics family navigation"
      >
        {orderedNodes.map((node, index) => {
          const isActive = node.node_id === activeNodeId;
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
                <span className="logistics-family-nav__label">{node.label}</span>
              </button>
            </div>
          );
        })}
      </nav>
    </section>
  );
}
