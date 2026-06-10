import "./capxUiVersionsDemo.css";

import { capxUiScenarioRoutes, capxUiVersionVariants } from "./capxUiVersionsDemoData";

function openInNewTabProps() {
  return {
    rel: "noreferrer",
    target: "_blank"
  };
}

export function CapxUiVersionsDemoPage(): JSX.Element {
  return (
    <main className="capx-ui-versions" data-testid="capx-ui-versions-page">
      <header className="capx-ui-versions__header">
        <div>
          <p className="capx-ui-versions__eyebrow">CAPEX FE user testing</p>
          <h1>CAPEX UI Versions</h1>
          <p>Design A, B, and C source prototypes mounted side by side with static mock artifacts only.</p>
        </div>
        <nav className="capx-ui-versions__demo-links" aria-label="Existing CAPX demo routes">
          <a href="/demo/capx/ui-versions/k12-pm-cockpit">DL1 PM cockpit</a>
          <a href="/demo/capx/ui-one/home">UI-One OPML build</a>
          <a href="/demo/capx/pm/projects">PM V1</a>
          <a href="/demo/capx/pm-v2/projects">PM V2</a>
          <a href="/demo/capx/ceo-cockpit">CEO cockpit</a>
          <a href="/demo/logistics">Logistics demo</a>
        </nav>
      </header>

      <section className="capx-ui-versions__source-bar" aria-label="Prototype source summary">
        <div>
          <strong>{capxUiVersionVariants.length}</strong>
          <span>UI versions</span>
        </div>
        <div>
          <strong>{capxUiScenarioRoutes.length}</strong>
          <span>scenario routes</span>
        </div>
        <a href="/capx-ui-versions/abc-selection/pass3_abc_comparison_index.html" {...openInNewTabProps()}>
          Open A/B/C source index
        </a>
      </section>

      <section className="capx-ui-versions__grid" aria-label="CAPEX UI version side by side comparison">
        {capxUiVersionVariants.map((variant) => (
          <article className={`capx-ui-version capx-ui-version--${variant.id}`} key={variant.id}>
            <div className="capx-ui-version__header">
              <span className="capx-ui-version__letter">{variant.shortName}</span>
              <div>
                <h2>{variant.name}</h2>
                <p>{variant.subtitle}</p>
              </div>
            </div>
            <div className="capx-ui-version__frame-shell">
              <iframe
                data-testid={`capx-ui-version-frame-${variant.id}`}
                src={variant.frameSrc}
                title={`${variant.name} source prototype`}
              />
            </div>
            <div className="capx-ui-version__actions">
              {variant.builtRoute ? (
                <a className="capx-ui-version__built-link" href={variant.builtRoute}>
                  {variant.builtLabel}
                </a>
              ) : null}
              <a href={variant.comparisonSrc} {...openInNewTabProps()}>
                Open test route
              </a>
              <a href={variant.detailSrc} {...openInNewTabProps()}>
                {variant.detailLabel}
              </a>
            </div>
            {variant.buildStatus ? <p className="capx-ui-version__build-status">{variant.buildStatus}</p> : null}
            <dl className="capx-ui-version__meta">
              <div>
                <dt>Source pack</dt>
                <dd>{variant.sourcePack}</dd>
              </div>
            </dl>
            <div className="capx-ui-version__source-links" aria-label={`${variant.name} source routes`}>
              {variant.sourceRoutes.map((route) => (
                <a href={route.href} key={route.href} {...openInNewTabProps()}>
                  {route.label}
                </a>
              ))}
            </div>
          </article>
        ))}
      </section>

      <section className="capx-ui-versions__scenarios" aria-label="A/B/C scenario routes">
        <div>
          <p className="capx-ui-versions__eyebrow">Shared scenario deck</p>
          <h2>A/B/C Scenario Routes</h2>
        </div>
        <div className="capx-ui-versions__scenario-list">
          {capxUiScenarioRoutes.map((route) => (
            <a href={route.href} key={route.href} {...openInNewTabProps()}>
              {route.label}
            </a>
          ))}
        </div>
      </section>
    </main>
  );
}
