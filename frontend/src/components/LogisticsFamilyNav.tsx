import type {
  LogisticsStoryBoardWorkItem,
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
  onTaskSelect: (item: LogisticsStoryBoardWorkItem) => void;
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
        {taskCards.map((card) => (
          <article
            key={card.lane_id}
            className={`logistics-family-nav__task-card${
              card.count === 0 ? " is-empty" : " has-items"
            }`}
            data-testid={`logistics-task-strip-card-${card.lane_id}`}
            aria-label={
              card.count === 0
                ? `${card.title}: no active work`
                : `${card.title}: ${card.count} active task${card.count === 1 ? "" : "s"}`
            }
          >
            <span className="logistics-family-nav__task-card-header">
              <strong>{card.title}</strong>
              <span
                className={`logistics-family-nav__task-count${
                  card.count > 0 ? " has-items" : ""
                }`}
                data-testid={`logistics-task-strip-count-${card.lane_id}`}
              >
                {card.count}
              </span>
            </span>
            {card.items.length > 0 ? (
              <ul
                className="logistics-family-nav__task-list"
                aria-label={`${card.title} active tasks`}
              >
                {card.items.map((item) => (
                  <li key={item.item_id}>
                    <button
                      type="button"
                      className="logistics-family-nav__task-item is-urgent"
                      data-testid={`logistics-task-strip-task-${card.lane_id}-${item.subject_id}`}
                      aria-label={`Open ${item.title}`}
                      onClick={() => {
                        onTaskSelect(item);
                      }}
                    >
                      {item.title}
                    </button>
                  </li>
                ))}
              </ul>
            ) : (
              <span className="logistics-family-nav__task-card-title is-empty-message">
                No active work
              </span>
            )}
          </article>
        ))}
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
