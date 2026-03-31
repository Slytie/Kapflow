import { Link } from "react-router-dom";

type DraftTimelineTone = "active" | "success" | "neutral";

interface DraftVersionTimelineEntryBase {
  artifactVersionId: string;
  createdAt: string;
  label: string;
  isCurrent: boolean;
  isLatest: boolean;
  isSelected?: boolean;
  note?: string | null;
  testId?: string;
}

type DraftVersionTimelineLinkEntry = DraftVersionTimelineEntryBase & {
  to: string;
  onSelect?: never;
};

type DraftVersionTimelineActionEntry = DraftVersionTimelineEntryBase & {
  to?: never;
  onSelect: () => void;
};

export type DraftVersionTimelineEntry =
  | DraftVersionTimelineLinkEntry
  | DraftVersionTimelineActionEntry;

interface DraftVersionTimelineProps {
  ariaLabel: string;
  entries: DraftVersionTimelineEntry[];
  variant?: "sidebar" | "panel";
  title?: string;
  eyebrow?: string;
  className?: string;
}

function joinClassNames(...values: Array<string | false | null | undefined>): string {
  return values.filter(Boolean).join(" ");
}

function formatDraftTimestamp(timestamp: string): string {
  const value = new Date(timestamp);
  if (Number.isNaN(value.getTime())) {
    return timestamp;
  }
  return value.toLocaleString(undefined, {
    year: "numeric",
    month: "short",
    day: "numeric",
    hour: "numeric",
    minute: "2-digit"
  });
}

function draftVersionTone(entry: DraftVersionTimelineEntry): DraftTimelineTone {
  if (entry.isSelected ?? entry.isCurrent) {
    return "active";
  }
  if (entry.isLatest) {
    return "success";
  }
  return "neutral";
}

function draftVersionBadges(
  entry: DraftVersionTimelineEntry
): Array<{ label: string; tone: DraftTimelineTone }> {
  const badges: Array<{ label: string; tone: DraftTimelineTone }> = [];
  if (entry.isCurrent) {
    badges.push({ label: "Current", tone: "active" });
  }
  if (entry.isLatest) {
    badges.push({ label: "Latest", tone: "success" });
  } else {
    badges.push({ label: "Superseded", tone: "neutral" });
  }
  return badges;
}

export function draftVersionPrimaryLabel(
  artifactVersionId: string,
  options: {
    currentArtifactVersionId: string;
    previousArtifactVersionId: string | null;
  }
): string {
  if (artifactVersionId === options.currentArtifactVersionId) {
    return "Current draft";
  }
  if (options.previousArtifactVersionId && artifactVersionId === options.previousArtifactVersionId) {
    return "Previous draft";
  }
  return "Draft";
}

export function DraftVersionTimeline({
  ariaLabel,
  entries,
  variant = "panel",
  title,
  eyebrow,
  className
}: DraftVersionTimelineProps): JSX.Element {
  const Container = variant === "sidebar" ? "aside" : "div";

  return (
    <Container
      className={joinClassNames("draft-version-timeline", `draft-version-timeline--${variant}`, className)}
      aria-label={ariaLabel}
    >
      {title ? (
        <header className="draft-version-timeline__header">
          {eyebrow ? <p className="timeline-page__eyebrow">{eyebrow}</p> : null}
          <h4>{title}</h4>
        </header>
      ) : null}

      <ol className="draft-version-timeline__list">
        {entries.map((entry) => {
          const tone = draftVersionTone(entry);
          const isSelected = entry.isSelected ?? entry.isCurrent;
          const actionLabel = isSelected ? "Viewing" : "Open";
          const content = (
            <>
              <span
                className={`draft-version-timeline__marker draft-version-timeline__marker--${tone}`}
                aria-hidden="true"
              />
              <span className="draft-version-timeline__content">
                <span className="draft-version-timeline__row">
                  <span className="draft-version-timeline__label">{entry.label}</span>
                  <span className="draft-version-timeline__chips">
                    {draftVersionBadges(entry).map((badge) => (
                      <span
                        key={`${entry.artifactVersionId}:${badge.label}`}
                        className={`draft-version-timeline__chip draft-version-timeline__chip--${badge.tone}`}
                      >
                        {badge.label}
                      </span>
                    ))}
                  </span>
                </span>
                <span className="draft-version-timeline__timestamp">{formatDraftTimestamp(entry.createdAt)}</span>
                {entry.note ? <span className="draft-version-timeline__note">{entry.note}</span> : null}
              </span>
              <span className="draft-version-timeline__action">{actionLabel}</span>
            </>
          );

          return (
            <li
              key={entry.artifactVersionId}
              className={joinClassNames(
                "draft-version-timeline__item",
                `draft-version-timeline__item--${tone}`,
                isSelected && "is-selected"
              )}
              data-testid={entry.testId}
            >
              {entry.to !== undefined ? (
                <Link
                  className="draft-version-timeline__entry"
                  to={entry.to}
                  aria-current={isSelected ? "page" : undefined}
                >
                  {content}
                </Link>
              ) : (
                <button
                  type="button"
                  className="draft-version-timeline__entry"
                  onClick={entry.onSelect}
                  aria-pressed={isSelected}
                >
                  {content}
                </button>
              )}
            </li>
          );
        })}
      </ol>
    </Container>
  );
}
