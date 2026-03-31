import type { TaskDocumentPreviewCue } from "@/lib/workspace/taskDocumentUi";

interface TaskDocumentCuesProps {
  cues: TaskDocumentPreviewCue[];
  compact?: boolean;
}

export function TaskDocumentCues({
  cues,
  compact = false
}: TaskDocumentCuesProps): JSX.Element | null {
  if (cues.length === 0) {
    return null;
  }

  return (
    <ul className={`task-document-cues${compact ? " task-document-cues--compact" : ""}`}>
      {cues.map((cue) => (
        <li
          key={cue.key}
          className={`task-document-cues__item task-document-cues__item--${cue.tone}`}
        >
          {cue.label}
        </li>
      ))}
    </ul>
  );
}
