interface StatePanelProps {
  kind: "loading" | "error" | "empty";
  title: string;
  detail?: string;
  onRetry?: () => void;
  testId?: string;
}

export function StatePanel({ kind, title, detail, onRetry, testId }: StatePanelProps): JSX.Element {
  return (
    <section className={`state-panel state-panel--${kind}`} data-testid={testId}>
      <strong>{title}</strong>
      {detail ? <p>{detail}</p> : null}
      {kind === "error" && onRetry ? (
        <button type="button" className="link-button" onClick={onRetry}>
          Retry
        </button>
      ) : null}
    </section>
  );
}
