import "./capxUiVersionsDemo.css";

const k12StaticPrototypeSrc = "/capx-ui-versions/k12-pm-cockpit/index.html";

function openInNewTabProps() {
  return {
    rel: "noreferrer",
    target: "_blank"
  };
}

export function CapxK12PmCockpitPage(): JSX.Element {
  return (
    <main className="capx-ui-versions capx-k12-cockpit" data-testid="capx-k12-pm-cockpit-page">
      <header className="capx-ui-versions__header capx-k12-cockpit__header">
        <div>
          <p className="capx-ui-versions__eyebrow">Sanitized static prototype</p>
          <h1>DL1 CAPEX PM Cockpit</h1>
          <p>
            Frontend-only static PM cockpit mounted from a sanitized standalone HTML prototype. It does not call backend
            APIs or create official project, approval, report, or artifact state.
          </p>
        </div>
        <nav className="capx-ui-versions__demo-links" aria-label="CAPX cockpit review routes">
          <a href="/demo/capx/ui-versions">A/B/C comparison</a>
          <a href="/demo/capx/ui-versions/design-a">Design A build</a>
          <a href="/demo/capx/ui-one/home">UI-One build</a>
          <a href={k12StaticPrototypeSrc} {...openInNewTabProps()}>
            Open static HTML
          </a>
        </nav>
      </header>

      <section className="capx-k12-cockpit__notice" aria-label="Static prototype review notice">
        <div>
          <strong>Sanitized fixture</strong>
          <span>DL1 labels and fake suppliers replace source project identifiers.</span>
        </div>
        <div>
          <strong>Static only</strong>
          <span>Internal tabs, report modal, print, and demo answers run inside the iframe.</span>
        </div>
        <div>
          <strong>No backend truth</strong>
          <span>Use for PM cockpit feedback only, not runtime or schema acceptance.</span>
        </div>
      </section>

      <section className="capx-k12-cockpit__frame-shell" aria-label="DL1 CAPEX PM cockpit static prototype">
        <iframe
          data-testid="capx-k12-pm-cockpit-frame"
          src={k12StaticPrototypeSrc}
          title="DL1 CAPEX PM Cockpit sanitized static prototype"
        />
      </section>
    </main>
  );
}

