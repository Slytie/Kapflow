import "./capxDesignAWorkbench.css";

import { useEffect, useMemo, useState } from "react";
import { Link, useParams } from "react-router-dom";

import {
  capxDesignAComponentRules,
  capxDesignALifecycleStages,
  capxDesignAMobileRules,
  capxDesignAPages,
  capxDesignAWorkItems,
  capxDesignAWorkflowGroups,
  getCapxDesignAContractSrc,
  getCapxDesignAPageById,
  getCapxDesignAWireframeSrc,
  type CapxDesignAPage,
  type CapxDesignAWorkItem
} from "./capxDesignAWorkbenchData";

type ContractLoadState =
  | { status: "idle" | "loading"; text: "" }
  | { status: "loaded"; text: string }
  | { status: "error"; text: "" };

interface CommandReceiptState {
  command: string;
  pageId: string;
  tone: "accepted" | "rejected";
  detail: string;
}

const roleFilters = ["All", "PM", "Finance", "Engineering", "Procurement", "Executive"];
const bandFilters = ["All", "MVP", "Near-MVP", "Post-MVP"];

function linkForPage(page: CapxDesignAPage): string {
  return `/demo/capx/ui-versions/design-a/${page.id}`;
}

function normalizeSearchValue(value: string): string {
  return value.trim().toLowerCase();
}

function pageMatchesRole(page: CapxDesignAPage, roleFilter: string): boolean {
  if (roleFilter === "All" || page.role === "All role clusters") {
    return true;
  }

  return page.role.toLowerCase().includes(roleFilter.toLowerCase());
}

function pageMatchesBand(page: CapxDesignAPage, bandFilter: string): boolean {
  return bandFilter === "All" || page.band.toLowerCase().includes(bandFilter.toLowerCase());
}

function pageMatchesSearch(page: CapxDesignAPage, searchValue: string): boolean {
  const normalizedSearch = normalizeSearchValue(searchValue);

  if (!normalizedSearch) {
    return true;
  }

  return [
    page.id,
    page.title,
    page.question,
    page.role,
    page.band,
    page.surfaceGroup,
    page.route,
    ...page.commands,
    ...page.blockedShortcuts
  ]
    .join(" ")
    .toLowerCase()
    .includes(normalizedSearch);
}

function getMarkdownSection(markdown: string, marker: string): string {
  const startIndex = markdown.indexOf(marker);

  if (startIndex === -1) {
    return "";
  }

  const nextSectionIndex = markdown.indexOf("\n## ", startIndex + marker.length);
  return markdown.slice(startIndex, nextSectionIndex === -1 ? undefined : nextSectionIndex);
}

function getBulletsFromSection(markdown: string, marker: string): string[] {
  return getMarkdownSection(markdown, marker)
    .split("\n")
    .map((line) => line.trim())
    .filter((line) => line.startsWith("- "))
    .map((line) => line.slice(2));
}

function getFirstColumnValuesFromTable(markdown: string, marker: string): string[] {
  const rows = getMarkdownSection(markdown, marker)
    .split("\n")
    .map((line) => line.trim())
    .filter((line) => line.startsWith("|") && !line.includes("---"));

  return rows
    .slice(1)
    .map((row) => row.split("|")[1]?.trim().replace(/`/g, ""))
    .filter((value): value is string => Boolean(value));
}

function buildContractSignals(page: CapxDesignAPage, text: string) {
  if (!text) {
    return {
      sections: ["Governed projection", "Basis visibility", "Evidence drawer", "Policy receipt"],
      rowFields: page.commands.slice(0, 6),
      drawerSections: ["Evidence", "Policy checks", "Command receipt", "Audit"],
      acceptanceTests: ["basis_visibility", "drawer_evidence", "blocked_shortcut", "stale_behavior", "mobile_behavior"]
    };
  }

  return {
    sections: getBulletsFromSection(text, "## 4. Primary sections"),
    rowFields: getFirstColumnValuesFromTable(text, "## 5. Primary row/card model"),
    drawerSections: getFirstColumnValuesFromTable(text, "## 6. Detail drawer model"),
    acceptanceTests: getFirstColumnValuesFromTable(text, "## 13. Acceptance tests")
  };
}

function getWorkItemForPage(page: CapxDesignAPage): CapxDesignAWorkItem {
  return capxDesignAWorkItems.find((item) => item.pageId === page.id) ?? capxDesignAWorkItems[0];
}

function CapxDesignAFilterGroup({
  activeValue,
  label,
  onChange,
  values
}: {
  activeValue: string;
  label: string;
  onChange: (value: string) => void;
  values: string[];
}): JSX.Element {
  return (
    <div className="capx-design-a-filter" aria-label={label}>
      <span>{label}</span>
      <div>
        {values.map((value) => (
          <button
            aria-pressed={activeValue === value}
            className={activeValue === value ? "is-active" : ""}
            key={value}
            onClick={() => onChange(value)}
            type="button"
          >
            {value}
          </button>
        ))}
      </div>
    </div>
  );
}

function CapxDesignACompletenessPanel(): JSX.Element {
  const mvpCount = capxDesignAPages.filter((page) => page.band.includes("MVP")).length;
  const commandCount = capxDesignAPages.reduce((total, page) => total + page.commands.length, 0);
  const blockedCount = capxDesignAPages.reduce((total, page) => total + page.blockedShortcuts.length, 0);

  return (
    <section className="capx-design-a-stats" aria-label="Design A completeness">
      <div>
        <strong>{capxDesignAPages.length}</strong>
        <span>page contracts</span>
      </div>
      <div>
        <strong>{mvpCount}</strong>
        <span>MVP-tagged surfaces</span>
      </div>
      <div>
        <strong>{commandCount}</strong>
        <span>allowed commands</span>
      </div>
      <div>
        <strong>{blockedCount}</strong>
        <span>blocked shortcuts</span>
      </div>
    </section>
  );
}

function CapxDesignAWireframePanel({ page }: { page: CapxDesignAPage }): JSX.Element {
  return (
    <section className="capx-design-a-wireframe" aria-label={`${page.id} source wireframe`}>
      <div className="capx-design-a-section-title">
        <p>Source wireframe</p>
        <h3>
          {page.id} / {page.title}
        </h3>
      </div>
      <img alt={`${page.id} ${page.title} wireframe`} src={getCapxDesignAWireframeSrc(page)} />
      <div className="capx-design-a-source-actions">
        <a href={getCapxDesignAContractSrc(page)} rel="noreferrer" target="_blank">
          Open source contract
        </a>
        <a href={getCapxDesignAWireframeSrc(page)} rel="noreferrer" target="_blank">
          Open wireframe
        </a>
      </div>
    </section>
  );
}

function CapxDesignAProjectBanner({ selectedWorkItem }: { selectedWorkItem: CapxDesignAWorkItem }): JSX.Element {
  return (
    <section className="capx-design-a-project-banner" aria-label="Project state banner">
      <div>
        <p>Project</p>
        <h2>Lynx Line Expansion / LYN-42</h2>
        <span>Lifecycle: concept review</span>
      </div>
      <div>
        <p>Official snapshot</p>
        <strong>snap:LYN-42:v31</strong>
        <span>Generated 09:10 / reviewed 10:45</span>
      </div>
      <div>
        <p>Forecastability</p>
        <strong>Conditional</strong>
        <span>2 stale triggers, 1 blocked interface</span>
      </div>
      <div>
        <p>Active item</p>
        <strong>{selectedWorkItem.id}</strong>
        <span>{selectedWorkItem.state}</span>
      </div>
    </section>
  );
}

function CapxDesignALifecycleStrip(): JSX.Element {
  return (
    <section className="capx-design-a-lifecycle" aria-label="Lifecycle stage context">
      {capxDesignALifecycleStages.map((stage) => (
        <span className={`capx-design-a-lifecycle__stage is-${stage.state}`} key={stage.name}>
          <strong>{stage.name}</strong>
          <small>{stage.state}</small>
        </span>
      ))}
    </section>
  );
}

function CapxDesignANav({
  filteredPages,
  selectedPage
}: {
  filteredPages: CapxDesignAPage[];
  selectedPage: CapxDesignAPage;
}): JSX.Element {
  const groupedPages = capxDesignAWorkflowGroups
    .map((group) => ({
      group,
      pages: filteredPages.filter((page) => page.surfaceGroup === group)
    }))
    .filter(({ pages }) => pages.length > 0);

  return (
    <nav className="capx-design-a-nav" aria-label="Design A page contracts">
      <div className="capx-design-a-nav__top">
        <span>{filteredPages.length} shown</span>
        <Link to="/demo/capx/ui-versions">A/B/C comparison</Link>
      </div>
      {groupedPages.map(({ group, pages }) => (
        <section key={group}>
          <h2>{group}</h2>
          {pages.map((page) => (
            <Link
              aria-current={selectedPage.id === page.id ? "page" : undefined}
              className={selectedPage.id === page.id ? "is-selected" : ""}
              key={page.id}
              to={linkForPage(page)}
            >
              <span>{page.id}</span>
              <strong>{page.title}</strong>
              <small>{page.band}</small>
            </Link>
          ))}
        </section>
      ))}
    </nav>
  );
}

function CapxDesignACommandPanels({
  onCommand,
  page
}: {
  onCommand: (receipt: CommandReceiptState) => void;
  page: CapxDesignAPage;
}): JSX.Element {
  return (
    <section className="capx-design-a-command-grid" aria-label="Command policy">
      <div>
        <div className="capx-design-a-section-title">
          <p>Allowed commands</p>
          <h3>Bounded actions</h3>
        </div>
        <div className="capx-design-a-command-list">
          {page.commands.map((command) => (
            <button
              key={command}
              onClick={() =>
                onCommand({
                  command,
                  pageId: page.id,
                  tone: "accepted",
                  detail: "Policy visibility passed in the mock workbench; command receipt is displayed without changing official truth."
                })
              }
              type="button"
            >
              {command}
            </button>
          ))}
        </div>
      </div>
      <div>
        <div className="capx-design-a-section-title">
          <p>Blocked shortcuts</p>
          <h3>Rejected paths</h3>
        </div>
        <div className="capx-design-a-command-list capx-design-a-command-list--blocked">
          {page.blockedShortcuts.map((shortcut) => (
            <button
              key={shortcut}
              onClick={() =>
                onCommand({
                  command: shortcut,
                  pageId: page.id,
                  tone: "rejected",
                  detail:
                    "Rejected by visible command policy. Use the safe action path with basis, evidence, policy result, and audit receipt."
                })
              }
              type="button"
            >
              {shortcut}
            </button>
          ))}
        </div>
      </div>
    </section>
  );
}

function CapxDesignAWorkQueue({ selectedPage }: { selectedPage: CapxDesignAPage }): JSX.Element {
  return (
    <section className="capx-design-a-queue" aria-label="Task-always-visible work queue">
      <div className="capx-design-a-section-title">
        <p>Task queue</p>
        <h3>Assigned decisions and evidence gaps</h3>
      </div>
      <div className="capx-design-a-queue__table" role="table" aria-label="Design A work queue">
        <div role="row">
          <span role="columnheader">Item</span>
          <span role="columnheader">State</span>
          <span role="columnheader">Basis</span>
          <span role="columnheader">Policy</span>
        </div>
        {capxDesignAWorkItems.map((item) => (
          <Link
            className={item.pageId === selectedPage.id ? "is-current" : ""}
            key={item.id}
            role="row"
            to={linkForPage(getCapxDesignAPageById(item.pageId))}
          >
            <span role="cell">
              <strong>{item.id}</strong>
              <small>{item.label}</small>
            </span>
            <span role="cell" data-state={item.state}>
              {item.state}
            </span>
            <span role="cell">{item.basis}</span>
            <span role="cell">{item.policy}</span>
          </Link>
        ))}
      </div>
    </section>
  );
}

function CapxDesignADrawer({
  page,
  selectedWorkItem,
  signals
}: {
  page: CapxDesignAPage;
  selectedWorkItem: CapxDesignAWorkItem;
  signals: ReturnType<typeof buildContractSignals>;
}): JSX.Element {
  return (
    <aside className="capx-design-a-drawer" aria-label="Evidence and policy drawer">
      <div className="capx-design-a-section-title">
        <p>Evidence drawer</p>
        <h3>{selectedWorkItem.id}</h3>
      </div>
      <dl>
        <div>
          <dt>Bound page</dt>
          <dd>
            {page.id} - {page.title}
          </dd>
        </div>
        <div>
          <dt>Evidence</dt>
          <dd>{selectedWorkItem.evidence}</dd>
        </div>
        <div>
          <dt>Policy result</dt>
          <dd>{selectedWorkItem.policy}</dd>
        </div>
        <div>
          <dt>Audit path</dt>
          <dd>actor, command, target version, basis, policy outcome, receipt</dd>
        </div>
      </dl>
      <div className="capx-design-a-drawer__sections">
        {signals.drawerSections.slice(0, 8).map((section) => (
          <span key={section}>{section}</span>
        ))}
      </div>
    </aside>
  );
}

function CapxDesignAContractPanel({
  loadState,
  page,
  signals
}: {
  loadState: ContractLoadState;
  page: CapxDesignAPage;
  signals: ReturnType<typeof buildContractSignals>;
}): JSX.Element {
  return (
    <section className="capx-design-a-contract" aria-label="Selected source contract">
      <div className="capx-design-a-section-title">
        <p>Source contract projection</p>
        <h3>{page.contractFile}</h3>
      </div>
      <div className="capx-design-a-contract__signals">
        <div>
          <strong>Primary sections</strong>
          {signals.sections.slice(0, 8).map((section) => (
            <span key={section}>{section}</span>
          ))}
        </div>
        <div>
          <strong>Row/card fields</strong>
          {signals.rowFields.slice(0, 10).map((field) => (
            <span key={field}>{field}</span>
          ))}
        </div>
        <div>
          <strong>Acceptance hooks</strong>
          {signals.acceptanceTests.slice(0, 8).map((testId) => (
            <span key={testId}>{testId}</span>
          ))}
        </div>
      </div>
      <details className="capx-design-a-contract__source">
        <summary>Full source contract text</summary>
        {loadState.status === "loaded" ? (
          <pre>{loadState.text}</pre>
        ) : (
          <p>Loading the source markdown contract from the static Design A artifact pack.</p>
        )}
      </details>
    </section>
  );
}

export function CapxDesignAWorkbenchPage(): JSX.Element {
  const { pageId } = useParams();
  const selectedPage = getCapxDesignAPageById(pageId);
  const selectedWorkItem = getWorkItemForPage(selectedPage);
  const [roleFilter, setRoleFilter] = useState("All");
  const [bandFilter, setBandFilter] = useState("All");
  const [searchValue, setSearchValue] = useState("");
  const [receipt, setReceipt] = useState<CommandReceiptState | null>(null);
  const [contractLoadState, setContractLoadState] = useState<ContractLoadState>({ status: "idle", text: "" });

  useEffect(() => {
    let isCurrent = true;
    const source = getCapxDesignAContractSrc(selectedPage);

    setContractLoadState({ status: "loading", text: "" });

    if (typeof fetch !== "function") {
      setContractLoadState({ status: "error", text: "" });
      return () => {
        isCurrent = false;
      };
    }

    fetch(source)
      .then((response) => {
        if (!response.ok) {
          throw new Error(`Unable to load ${source}`);
        }
        return response.text();
      })
      .then((text) => {
        if (isCurrent) {
          setContractLoadState({ status: "loaded", text });
        }
      })
      .catch(() => {
        if (isCurrent) {
          setContractLoadState({ status: "error", text: "" });
        }
      });

    return () => {
      isCurrent = false;
    };
  }, [selectedPage]);

  useEffect(() => {
    setReceipt(null);
  }, [selectedPage.id]);

  const filteredPages = useMemo(
    () =>
      capxDesignAPages.filter(
        (page) =>
          pageMatchesRole(page, roleFilter) && pageMatchesBand(page, bandFilter) && pageMatchesSearch(page, searchValue)
      ),
    [bandFilter, roleFilter, searchValue]
  );

  const contractSignals = useMemo(
    () => buildContractSignals(selectedPage, contractLoadState.text),
    [contractLoadState.text, selectedPage]
  );

  return (
    <main className="capx-design-a" data-testid="capx-design-a-workbench">
      <header className="capx-design-a-header">
        <div>
          <p className="capx-design-a-eyebrow">Design A complete build</p>
          <h1>Governed Workbench</h1>
          <p>
            Fixture-backed CAPEX workbench built from the final Design A blueprint: 31 page contracts, static source
            wireframes, visible evidence, policy, command receipts, and audit paths.
          </p>
        </div>
        <nav aria-label="CAPEX UI version routes">
          <Link to="/demo/capx/ui-versions">A/B/C side by side</Link>
          <a href="/capx-ui-versions/design-a-final/prototype/final_clickable_blueprint_index.html" rel="noreferrer" target="_blank">
            Source index
          </a>
          <a href="/demo/capx/pm/projects">PM V1</a>
          <a href="/demo/capx/pm-v2/projects">PM V2</a>
        </nav>
      </header>

      <CapxDesignACompletenessPanel />

      <section className="capx-design-a-controls" aria-label="Design A filters">
        <label>
          <span>Search all 31 contracts</span>
          <input
            onChange={(event) => setSearchValue(event.target.value)}
            placeholder="Search page, command, blocked shortcut, role..."
            type="search"
            value={searchValue}
          />
        </label>
        <CapxDesignAFilterGroup activeValue={roleFilter} label="Role" onChange={setRoleFilter} values={roleFilters} />
        <CapxDesignAFilterGroup activeValue={bandFilter} label="Band" onChange={setBandFilter} values={bandFilters} />
      </section>

      <div className="capx-design-a-shell">
        <CapxDesignANav filteredPages={filteredPages} selectedPage={selectedPage} />

        <div className="capx-design-a-workspace">
          <CapxDesignAProjectBanner selectedWorkItem={selectedWorkItem} />
          <CapxDesignALifecycleStrip />

          <section className="capx-design-a-page-head" aria-label="Selected page contract summary">
            <div>
              <p className="capx-design-a-eyebrow">{selectedPage.surfaceGroup}</p>
              <h2>
                {selectedPage.id} - {selectedPage.title}
              </h2>
              <p>{selectedPage.question}</p>
            </div>
            <dl>
              <div>
                <dt>Route</dt>
                <dd>{selectedPage.route}</dd>
              </div>
              <div>
                <dt>Role</dt>
                <dd>{selectedPage.role}</dd>
              </div>
              <div>
                <dt>Band</dt>
                <dd>{selectedPage.band}</dd>
              </div>
            </dl>
          </section>

          <CapxDesignACommandPanels onCommand={setReceipt} page={selectedPage} />

          {receipt ? (
            <section
              className={`capx-design-a-receipt capx-design-a-receipt--${receipt.tone}`}
              role="status"
              aria-label="Command receipt"
            >
              <strong>
                {receipt.tone === "accepted" ? "Accepted receipt" : "Rejected receipt"} / {receipt.pageId}
              </strong>
              <span>{receipt.command}</span>
              <p>{receipt.detail}</p>
            </section>
          ) : null}

          <div className="capx-design-a-main-grid">
            <div>
              <CapxDesignAWorkQueue selectedPage={selectedPage} />
              <CapxDesignAContractPanel loadState={contractLoadState} page={selectedPage} signals={contractSignals} />
            </div>
            <div>
              <CapxDesignADrawer page={selectedPage} selectedWorkItem={selectedWorkItem} signals={contractSignals} />
              <CapxDesignAWireframePanel page={selectedPage} />
            </div>
          </div>

          <section className="capx-design-a-rules" aria-label="Design A implementation rules">
            <div>
              <div className="capx-design-a-section-title">
                <p>Component state model</p>
                <h3>Always visible safeguards</h3>
              </div>
              {capxDesignAComponentRules.map((rule) => (
                <span key={rule}>{rule}</span>
              ))}
            </div>
            <div>
              <div className="capx-design-a-section-title">
                <p>Responsive model</p>
                <h3>Desktop-first, task-mobile</h3>
              </div>
              {capxDesignAMobileRules.map((rule) => (
                <span key={rule}>{rule}</span>
              ))}
            </div>
          </section>
        </div>
      </div>
    </main>
  );
}
