import type { KeyboardEvent, MouseEvent, ReactNode } from "react";

import {
  initials,
  isInteractiveTarget,
  type WorkspaceBoardCard as WorkspaceBoardCardModel
} from "@/lib/workspace/taskBoardModel";

interface WorkspaceBoardCardProps {
  card: WorkspaceBoardCardModel;
  menu: ReactNode;
  body?: ReactNode;
  footerHint?: ReactNode;
  secondaryHint?: ReactNode;
  onOpen?: () => void;
}

export function WorkspaceBoardCard({
  card,
  menu,
  body,
  footerHint,
  secondaryHint,
  onOpen
}: WorkspaceBoardCardProps): JSX.Element {
  const interactive = typeof onOpen === "function";
  const handleClick = (event: MouseEvent<HTMLElement>): void => {
    if (!interactive || !onOpen || isInteractiveTarget(event.target)) {
      return;
    }
    onOpen();
  };
  const handleKeyDown = (event: KeyboardEvent<HTMLElement>): void => {
    if (!interactive || !onOpen || isInteractiveTarget(event.target)) {
      return;
    }
    if (event.key !== "Enter" && event.key !== " ") {
      return;
    }
    event.preventDefault();
    onOpen();
  };

  return (
    <article
      className={`workspace-board-card${interactive ? " workspace-board-card--interactive" : ""}`}
      data-testid="workspace-task-card"
      tabIndex={interactive ? 0 : undefined}
      aria-label={interactive ? `Open ${card.title} details` : undefined}
      onClick={interactive ? handleClick : undefined}
      onKeyDown={interactive ? handleKeyDown : undefined}
    >
      <header>
        <h4>{card.title}</h4>
        {menu}
      </header>

      <div className="workspace-board-card__meta">
        <span className={`workspace-board-tag workspace-board-tag--${card.tag.toLowerCase()}`}>
          {card.tag}
        </span>
      </div>

      {body}

      <footer>
        <div className="workspace-avatar-stack">
          {card.avatars.length === 0 ? (
            <span className="workspace-avatar">CO</span>
          ) : (
            card.avatars.map((avatar, index) => (
              <span
                key={`${card.cardId}:avatar:${index}:${avatar}`}
                className="workspace-avatar"
                style={{ zIndex: card.avatars.length - index }}
              >
                {initials(avatar)}
              </span>
            ))
          )}
        </div>
        <span className="workspace-board-counter">{card.primaryCount}</span>
        <span className="workspace-board-counter">{card.secondaryCount}</span>
      </footer>

      {footerHint ? <p className="workspace-board-card__hint">{footerHint}</p> : null}
      {secondaryHint ? <p className="workspace-board-card__hint">{secondaryHint}</p> : null}
    </article>
  );
}
