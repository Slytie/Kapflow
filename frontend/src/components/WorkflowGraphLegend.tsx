export function WorkflowGraphLegend(): JSX.Element {
  const items = [
    { key: "not_started", label: "Not started" },
    { key: "ready", label: "Ready" },
    { key: "in_progress", label: "In progress" },
    { key: "blocked", label: "Blocked" },
    { key: "awaiting_approval", label: "Awaiting approval" },
    { key: "completed", label: "Completed" },
    { key: "warning", label: "Warning" }
  ];

  return (
    <ul className="workflow-graph-legend" aria-label="Workflow graph legend">
      {items.map((item) => (
        <li key={item.key}>
          <span className={`workflow-graph-legend__swatch workflow-graph-node--${item.key}`} />
          {item.label}
        </li>
      ))}
    </ul>
  );
}
