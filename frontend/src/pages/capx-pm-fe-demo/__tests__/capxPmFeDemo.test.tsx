/// <reference types="vite/client" />

import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, vi } from "vitest";

import { App } from "@/app/App";
import { resetCapxPmFeDemoAccessForTest } from "../CapxPmFeDemoAccessGate";

const ACCESS_STORAGE_KEY = "capx_pm_fe_demo_access_granted";
const demoSourceModules = import.meta.glob("../**/*.{css,ts,tsx}", {
  eager: true,
  import: "default",
  query: "?raw"
}) as Record<string, string>;

async function renderUnlocked(route: string) {
  const user = userEvent.setup();
  window.sessionStorage.setItem(ACCESS_STORAGE_KEY, "true");
  window.history.pushState({}, "", route);
  const rendered = render(<App />);
  return { user, rendered };
}

describe("CAPX PM FE complete demo", () => {
  beforeEach(() => {
    window.sessionStorage.clear();
    resetCapxPmFeDemoAccessForTest();
    window.history.pushState({}, "", "/");
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("shows and unlocks the local design review gate", async () => {
    const user = userEvent.setup();
    window.history.pushState({}, "", "/demo/capx/pm/projects");
    render(<App />);

    const gate = screen.getByTestId("capx-pm-fe-access-gate");
    expect(within(gate).getByRole("heading", { name: "Private design review" })).toBeInTheDocument();
    expect(within(gate).getByText(/speed bump for design sessions/i)).toBeInTheDocument();

    await user.type(within(gate).getByLabelText("Local review code"), "capx-demo-local");
    await user.click(within(gate).getByRole("button", { name: "Open demo" }));

    expect(await screen.findByTestId("capx-pm-fe-projects-page")).toBeInTheDocument();
  });

  it("renders the attention-first project list with required PM columns", async () => {
    await renderUnlocked("/demo/capx/pm/projects");

    expect(await screen.findByTestId("capx-pm-fe-projects-page")).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Open the project that needs PM attention first" })).toBeInTheDocument();
    for (const header of [
      "Project",
      "Next action",
      "Due",
      "Health",
      "Stage",
      "Schedule",
      "Budget",
      "Quality",
      "Waiting on",
      "Docs",
      "Escalation",
      "Last update"
    ]) {
      expect(screen.getByRole("columnheader", { name: header })).toBeInTheDocument();
    }
    expect(screen.getAllByText("P-104 Packaging Line Retrofit").length).toBeGreaterThanOrEqual(1);
    expect(screen.getAllByRole("row").length).toBeGreaterThanOrEqual(11);
  });

  it("links project rows into the workspace", async () => {
    const { rendered } = await renderUnlocked("/demo/capx/pm/projects");
    expect(await screen.findByTestId("capx-pm-fe-projects-page")).toBeInTheDocument();

    expect(rendered.container.querySelectorAll('a[href="/demo/capx/pm/projects/P-104"]').length).toBeGreaterThanOrEqual(1);
  });

  it("renders the known project workspace with next action, blockers, and step navigation", async () => {
    await renderUnlocked("/demo/capx/pm/projects/P-104");

    expect(await screen.findByTestId("capx-pm-fe-workspace-page")).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: /P-104 Packaging Line Retrofit/i })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Confirm whether drawing v7 replaces v6" })).toBeInTheDocument();
    expect(screen.getByText("Open blockers")).toBeInTheDocument();
    expect(screen.getAllByRole("link", { name: /Project Gantt/i })[0]).toHaveAttribute(
      "href",
      "/demo/capx/pm/projects/P-104/gantt"
    );
  });

  it.each([
    {
      route: "project-setup",
      testId: "capx-pm-fe-step-project-setup",
      heading: "Kickoff and takeover status",
      concepts: ["Document access", "Sponsor decision path", "Missing setup checklist"]
    },
    {
      route: "documents",
      testId: "capx-pm-fe-step-documents",
      heading: "Document checklist",
      concepts: ["Supplier drawing v7", "Wrong versions, missing files", "Proof detail"]
    },
    {
      route: "timeline",
      testId: "capx-pm-fe-step-timeline",
      heading: "Milestone movement",
      concepts: ["Baseline vs forecast", "Open Project Gantt", "Installation"]
    },
    {
      route: "budget-orders",
      testId: "capx-pm-fe-step-budget-orders",
      heading: "Budget summary",
      concepts: ["Quote, PO, and change order review", "Controls package revision", "Approval needed"]
    },
    {
      route: "supplier-questions",
      testId: "capx-pm-fe-step-supplier-questions",
      heading: "Supplier open points",
      concepts: ["Supplier question register", "Does drawing v7 replace drawing v6", "Supplier A must reply"]
    },
    {
      route: "site-handoffs",
      testId: "capx-pm-fe-step-site-handoffs",
      heading: "Site readiness board",
      concepts: ["Site handoff register", "Shutdown window", "Accepted by"]
    },
    {
      route: "project-report",
      testId: "capx-pm-fe-step-project-report",
      heading: "Report readiness",
      concepts: ["Suggested PM update", "What changed this week", "Do not report the order as ready"]
    }
  ])("renders the $route step with distinct practical PM content", async ({ route, testId, heading, concepts }) => {
    await renderUnlocked(`/demo/capx/pm/projects/P-104/steps/${route}`);

    expect(await screen.findByTestId(testId)).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: heading })).toBeInTheDocument();
    for (const concept of concepts) {
      expect(screen.getAllByText(concept, { exact: false }).length).toBeGreaterThanOrEqual(1);
    }
    expect(screen.getByRole("button", { name: /Simulated only/i })).toBeDisabled();
  });

  it("renders the read-only project Gantt and mobile schedule cards", async () => {
    await renderUnlocked("/demo/capx/pm/projects/P-104/gantt");

    expect(await screen.findByTestId("capx-pm-fe-gantt-page")).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: /P-104 Packaging Line Retrofit Project Gantt/i })).toBeInTheDocument();
    expect(screen.getByText("Baseline vs forecast schedule")).toBeInTheDocument();
    expect(screen.getByText("Read-only schedule detail showing baseline, forecast, blockers, and critical path.")).toBeInTheDocument();
    expect(screen.getByTestId("capx-pm-fe-gantt-mobile-cards")).toBeInTheDocument();
  });

  it("renders bounded not-found states for unknown project, step, and route", async () => {
    let current = await renderUnlocked("/demo/capx/pm/projects/P-999");

    expect(await screen.findByTestId("capx-pm-fe-project-not-found")).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Project not found" })).toBeInTheDocument();

    current.rendered.unmount();
    current = await renderUnlocked("/demo/capx/pm/projects/P-104/steps/not-a-step");
    expect(await screen.findByTestId("capx-pm-fe-step-not-found")).toBeInTheDocument();

    screen.getByText("Step not found");

    current.rendered.unmount();
    await renderUnlocked("/demo/capx/pm/not-in-family");
    expect(await screen.findByTestId("capx-pm-fe-route-not-found")).toBeInTheDocument();
  });

  it("uses semantic status chips and does not visibly render color-name labels", async () => {
    const { rendered } = await renderUnlocked("/demo/capx/pm/projects");

    const chips = Array.from(rendered.container.querySelectorAll("[data-status-chip]"));
    expect(chips.length).toBeGreaterThan(0);
    expect(screen.queryByText(/\b(red|yellow|green|amber)\b/i)).not.toBeInTheDocument();
    for (const chip of chips) {
      expect(chip).toHaveAttribute("aria-label");
      expect(chip).toHaveAttribute("title");
      expect(chip.textContent).not.toMatch(/\b(red|yellow|green|amber)\b/i);
    }
  });

  it("renders without backend fetch calls", async () => {
    const fetchMock = vi.fn();
    vi.stubGlobal("fetch", fetchMock);

    await renderUnlocked("/demo/capx/pm/projects/P-104/steps/documents");

    expect(await screen.findByTestId("capx-pm-fe-step-documents")).toBeInTheDocument();
    expect(fetchMock).not.toHaveBeenCalled();
  });

  it("keeps bundled PM demo source free of guarded terms and browser-exposed credential patterns", () => {
    const guardedTerms = [
      ["WF", "LOW"].join(""),
      ["cor", "pus"].join(""),
      ["source", " occurrence"].join(""),
      ["artifact", " role assignment"].join(""),
      ["artifact", " packet"].join(""),
      ["basis", " vector"].join(""),
      ["state", " graph"].join(""),
      ["pointer", " promotion"].join(""),
      ["provenance", " edge"].join(""),
      ["interface", " burden conservation"].join(""),
      ["snapshot", " build run"].join(""),
      ["schema", "-governed artifact"].join("")
    ];
    const credentialPattern = new RegExp(`${"VITE_.*PASS"}${"WORD"}|${"pass"}${"word"}|${"sec"}${"ret"}`, "i");
    const guardedPattern = new RegExp(guardedTerms.join("|"), "i");
    const matches = Object.entries(demoSourceModules)
      .filter(([path]) => !path.endsWith("capxPmFeDemo.test.tsx"))
      .flatMap(([path, text]) => (credentialPattern.test(text) || guardedPattern.test(text) ? [path] : []));

    expect(matches).toEqual([]);
  });
});
