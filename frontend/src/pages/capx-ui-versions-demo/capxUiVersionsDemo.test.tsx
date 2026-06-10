import { fireEvent, render, screen, within } from "@testing-library/react";

import { App } from "@/app/App";
import staticCockpitHtml from "../../../public/capx-ui-versions/k12-pm-cockpit/index.html?raw";
import { capxDesignAPages } from "./capxDesignAWorkbenchData";
import { capxUiScenarioRoutes, capxUiVersionVariants } from "./capxUiVersionsDemoData";

describe("CAPX UI versions side-by-side demo", () => {
  beforeEach(() => {
    window.history.pushState({}, "", "/demo/capx/ui-versions");
  });

  it("mounts all three source prototype versions side by side", () => {
    render(<App />);

    expect(screen.getByTestId("capx-ui-versions-page")).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "CAPEX UI Versions" })).toBeInTheDocument();
    expect(screen.getByText("Governed Workbench")).toBeInTheDocument();
    expect(screen.getByText("State Atlas")).toBeInTheDocument();
    expect(screen.getByText("Playbook OS")).toBeInTheDocument();

    for (const variant of capxUiVersionVariants) {
      expect(screen.getByTestId(`capx-ui-version-frame-${variant.id}`)).toHaveAttribute("src", variant.frameSrc);
      expect(screen.getByRole("link", { name: variant.detailLabel })).toHaveAttribute("href", variant.detailSrc);
    }

    expect(screen.getByRole("link", { name: "Open completed A build" })).toHaveAttribute(
      "href",
      "/demo/capx/ui-versions/design-a"
    );
  });

  it("keeps existing demo routes linked and exposes every A/B/C scenario route", () => {
    render(<App />);

    expect(screen.getByRole("link", { name: "PM V1" })).toHaveAttribute("href", "/demo/capx/pm/projects");
    expect(screen.getByRole("link", { name: "PM V2" })).toHaveAttribute("href", "/demo/capx/pm-v2/projects");
    expect(screen.getByRole("link", { name: "DL1 PM cockpit" })).toHaveAttribute(
      "href",
      "/demo/capx/ui-versions/k12-pm-cockpit"
    );
    expect(screen.getByRole("link", { name: "UI-One OPML build" })).toHaveAttribute(
      "href",
      "/demo/capx/ui-one/home"
    );
    expect(screen.getByRole("link", { name: "CEO cockpit" })).toHaveAttribute("href", "/demo/capx/ceo-cockpit");
    expect(screen.getByRole("link", { name: "Logistics demo" })).toHaveAttribute("href", "/demo/logistics");

    for (const scenario of capxUiScenarioRoutes) {
      expect(screen.getByRole("link", { name: scenario.label })).toHaveAttribute("href", scenario.href);
    }
  });

  it("documents the complete three-version source manifest in code", () => {
    expect(capxUiVersionVariants.map((variant) => variant.shortName)).toEqual(["A", "B", "C"]);
    expect(capxUiVersionVariants.every((variant) => variant.sourceRoutes.length >= 3)).toBe(true);
    expect(capxUiScenarioRoutes).toHaveLength(12);
  });
});

describe("CAPX sanitized static PM cockpit", () => {
  it("renders the wrapper route and embeds the sanitized static HTML", () => {
    window.history.pushState({}, "", "/demo/capx/ui-versions/k12-pm-cockpit");

    render(<App />);

    expect(screen.getByTestId("capx-k12-pm-cockpit-page")).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "DL1 CAPEX PM Cockpit" })).toBeInTheDocument();
    expect(screen.getByText("Sanitized fixture")).toBeInTheDocument();
    expect(screen.getByText("No backend truth")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "A/B/C comparison" })).toHaveAttribute(
      "href",
      "/demo/capx/ui-versions"
    );
    expect(screen.getByRole("link", { name: "Design A build" })).toHaveAttribute(
      "href",
      "/demo/capx/ui-versions/design-a"
    );
    expect(screen.getByRole("link", { name: "UI-One build" })).toHaveAttribute("href", "/demo/capx/ui-one/home");
    expect(screen.getByRole("link", { name: "Open static HTML" })).toHaveAttribute(
      "href",
      "/capx-ui-versions/k12-pm-cockpit/index.html"
    );
    expect(screen.getByTestId("capx-k12-pm-cockpit-frame")).toHaveAttribute(
      "src",
      "/capx-ui-versions/k12-pm-cockpit/index.html"
    );
  });

  it("keeps the repo-served static cockpit sanitized", () => {
    const html = staticCockpitHtml;
    const forbiddenRawLabels = [
      "K12",
      "K12 Refurbishment Winder",
      "Technotrans",
      "Speck",
      "Bilfinger",
      "Eckert",
      "G&H Insulation",
      "BOE-014-00",
      "€1.505m",
      "1.505m"
    ];

    for (const label of forbiddenRawLabels) {
      expect(html).not.toContain(label);
    }

    expect(html).toContain("DL1 CAPEX PM Cockpit");
    expect(html).toContain("Demo Line Refurbishment");
    expect(html).toContain("DEMO-CAPEX-001");
  });
});

describe("CAPX Design A governed workbench build", () => {
  it("renders the completed Design A route without iframe wrappers", () => {
    window.history.pushState({}, "", "/demo/capx/ui-versions/design-a");

    const { container } = render(<App />);

    expect(screen.getByTestId("capx-design-a-workbench")).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Governed Workbench" })).toBeInTheDocument();
    expect(within(screen.getByLabelText("Design A completeness")).getByText("page contracts")).toBeInTheDocument();
    expect(container.querySelector("iframe")).toBeNull();

    expect(screen.getByRole("navigation", { name: "Design A page contracts" })).toBeInTheDocument();
    const pageLinks = Array.from(
      container.querySelectorAll<HTMLAnchorElement>('.capx-design-a-nav a[href*="/demo/capx/ui-versions/design-a/P"]')
    );
    expect(pageLinks.map((link) => link.getAttribute("href"))).toEqual(
      capxDesignAPages.map((page) => `/demo/capx/ui-versions/design-a/${page.id}`)
    );
  });

  it("deep-links to page-level commands, blocked shortcuts, wireframes, and source contracts", () => {
    window.history.pushState({}, "", "/demo/capx/ui-versions/design-a/P17");

    render(<App />);

    expect(screen.getByRole("heading", { name: "P17 - Assumption Closure" })).toBeInTheDocument();
    expect(screen.getByText("Which assumptions are open, closed, contradicted, waived, or stale?")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "close_assumption_with_evidence" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "close_without_evidence" })).toBeInTheDocument();
    expect(screen.getByAltText("P17 Assumption Closure wireframe")).toHaveAttribute(
      "src",
      "/capx-ui-versions/design-a-final/wireframes/P17_assumption_closure.svg"
    );
    expect(screen.getByRole("link", { name: "Open source contract" })).toHaveAttribute(
      "href",
      "/capx-ui-versions/design-a-final/workflow_pages/P17_assumption_closure.md"
    );
  });

  it("shows visible command receipts for allowed and rejected Design A actions", () => {
    window.history.pushState({}, "", "/demo/capx/ui-versions/design-a/P20");

    render(<App />);

    fireEvent.click(screen.getByRole("button", { name: "approve" }));
    expect(screen.getByRole("status", { name: "Command receipt" })).toHaveTextContent("Accepted receipt / P20");
    expect(screen.getByRole("status", { name: "Command receipt" })).toHaveTextContent("approve");

    fireEvent.click(screen.getByRole("button", { name: "approve_stale_artifact" }));
    expect(screen.getByRole("status", { name: "Command receipt" })).toHaveTextContent("Rejected receipt / P20");
    expect(screen.getByRole("status", { name: "Command receipt" })).toHaveTextContent("approve_stale_artifact");
  });

  it("keeps the Design A source manifest complete in code", () => {
    expect(capxDesignAPages).toHaveLength(31);
    expect(capxDesignAPages.map((page) => page.id)).toEqual(
      Array.from({ length: 31 }, (_, index) => `P${String(index + 1).padStart(2, "0")}`)
    );
    expect(capxDesignAPages.every((page) => page.commands.length > 0)).toBe(true);
    expect(capxDesignAPages.every((page) => page.blockedShortcuts.length > 0)).toBe(true);
    expect(capxDesignAPages.every((page) => page.contractFile.endsWith(".md"))).toBe(true);
    expect(capxDesignAPages.every((page) => page.wireframeFile.endsWith(".svg"))).toBe(true);
  });
});
