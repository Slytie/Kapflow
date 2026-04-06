import { LaneColumn } from "@/components/LaneColumn";
import { TaskDocumentCues } from "@/components/TaskDocumentCues";
import {
  boardItemMeta,
  boardItemSupportText,
  stateBadgeClass
} from "@/lib/logistics/familyStory";
import { buildTaskDocumentPreviewCues } from "@/lib/workspace/taskDocumentUi";

interface LogisticsDemoEditorialBoardProps {
  boardPresentation: {
    lanes: Array<{
      id: string;
      title: string;
      items: Array<{
        item_id: string;
        item_type: "human_task" | "approval" | "flag";
        title: string;
        state: string;
        workflow_id: string;
      }>;
    }>;
  };
  isExpanded: boolean;
  onToggle: () => void;
  onOpenBoardItemDetail: (item: any) => void;
}

export function LogisticsDemoEditorialBoard({
  boardPresentation,
  isExpanded,
  onToggle,
  onOpenBoardItemDetail
}: LogisticsDemoEditorialBoardProps): JSX.Element {
  return (
    <section
      className="logistics-demo-page__panel logistics-demo-page__panel--task-board"
      data-testid="logistics-task-board-panel"
      data-expanded={isExpanded}
    >
      <header className="logistics-demo-page__panel-header">
        <div>
          <h3>Editorial Task Board</h3>
          <p>
            {boardPresentation.lanes.reduce((count, lane) => count + lane.items.length, 0)} active
            tasks and approvals across weekly, live, and reporting work
          </p>
        </div>
        <button
          type="button"
          className="action-btn"
          aria-expanded={isExpanded}
          onClick={onToggle}
        >
          {isExpanded ? "Hide task board" : "Show task board"}
        </button>
      </header>
      {isExpanded ? (
        <div className="logistics-demo-page__task-board-shell">
          <div className="board-grid board-grid--story">
            {boardPresentation.lanes.map((lane) => (
              <LaneColumn key={lane.id} title={lane.title} count={lane.items.length}>
                {lane.items.length === 0 ? (
                  <p className="logistics-demo-page__empty-lane">No active work in lane.</p>
                ) : null}
                {lane.items.map((item) => (
                  <article
                    key={item.item_id}
                    className={`logistics-demo-page__board-item logistics-demo-page__board-item--${item.item_type}`}
                  >
                    <button
                      type="button"
                      className="logistics-demo-page__board-item-trigger"
                      onClick={() => onOpenBoardItemDetail(item)}
                    >
                      <header>
                        <div>
                          <p className="logistics-demo-page__board-item-kicker">
                            {item.item_type === "human_task"
                              ? "Task"
                              : item.item_type === "approval"
                                ? "Approval"
                                : "Flag"}
                          </p>
                          <h4>{item.title}</h4>
                        </div>
                        <span className={stateBadgeClass(item.state)}>{item.state}</span>
                      </header>
                      <p>{boardItemMeta(item as any)}</p>
                      <p>{item.workflow_id}</p>
                      {boardItemSupportText(item as any) ? (
                        <p>{boardItemSupportText(item as any)}</p>
                      ) : null}
                      <TaskDocumentCues cues={buildTaskDocumentPreviewCues(item as any)} compact />
                    </button>
                  </article>
                ))}
              </LaneColumn>
            ))}
          </div>
        </div>
      ) : (
        <p className="logistics-demo-page__board-collapsed-copy">
          The compact task strip stays pinned in the shell. Expand this board when you need the
          full lane view.
        </p>
      )}
    </section>
  );
}
