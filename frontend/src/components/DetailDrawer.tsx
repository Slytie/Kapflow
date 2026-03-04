import type { DrawerPayload } from "@/lib/types/ui";

interface DetailDrawerProps {
  payload: DrawerPayload | null;
  onClose: () => void;
}

export function DetailDrawer({ payload, onClose }: DetailDrawerProps): JSX.Element {
  if (!payload) {
    return <aside className="detail-drawer" aria-hidden="true" />;
  }

  return (
    <aside className="detail-drawer detail-drawer--open" aria-label="Details drawer">
      <header>
        <h2>{payload.title}</h2>
        {payload.subtitle ? <p>{payload.subtitle}</p> : null}
        <button type="button" className="link-button" onClick={onClose} aria-label="Close drawer">
          Close
        </button>
      </header>
      {payload.description ? <p className="detail-drawer__description">{payload.description}</p> : null}
      <dl>
        {payload.fields.map((field) => (
          <div key={field.label} className="detail-drawer__field">
            <dt>{field.label}</dt>
            <dd>{field.value}</dd>
          </div>
        ))}
      </dl>
    </aside>
  );
}
