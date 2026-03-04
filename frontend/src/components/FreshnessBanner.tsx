interface FreshnessBannerProps {
  lastRefreshedAt: string | null;
  onRefresh: () => void;
  isRefreshing?: boolean;
  pollIntervalMs?: number | false;
}

export function FreshnessBanner({
  lastRefreshedAt,
  onRefresh,
  isRefreshing = false,
  pollIntervalMs
}: FreshnessBannerProps): JSX.Element {
  const refreshedLabel = lastRefreshedAt
    ? `Last refresh ${new Date(lastRefreshedAt).toLocaleTimeString()}`
    : "Waiting for first API payload";

  return (
    <div className="freshness-banner" role="status" aria-live="polite">
      <span>{refreshedLabel}</span>
      {pollIntervalMs ? <span className="freshness-banner__poll">Polling every {pollIntervalMs / 1000}s</span> : null}
      <button type="button" className="link-button" onClick={onRefresh} disabled={isRefreshing}>
        {isRefreshing ? "Refreshing..." : "Refresh"}
      </button>
    </div>
  );
}
