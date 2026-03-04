export interface ActionItem {
  key: string;
  label: string;
  tone?: "default" | "positive" | "negative";
  onClick?: () => void;
  disabled?: boolean;
}

interface ActionClusterProps {
  actions: ActionItem[];
}

export function ActionCluster({ actions }: ActionClusterProps): JSX.Element {
  return (
    <div className="action-cluster" role="group" aria-label="Inline actions">
      {actions.map((action) => (
        <button
          key={action.key}
          type="button"
          className={`action-btn action-btn--${action.tone ?? "default"}`}
          onClick={action.onClick}
          disabled={action.disabled || !action.onClick}
        >
          {action.label}
        </button>
      ))}
    </div>
  );
}
