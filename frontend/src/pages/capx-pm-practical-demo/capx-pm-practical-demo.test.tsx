/// <reference types="vite/client" />

import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, vi } from "vitest";

import { App } from "@/app/App";
import { resetCapxPmPracticalAcknowledgementForTest } from "./CapxPmPracticalAccessGate";

const ACKNOWLEDGEMENT_KEY = "capx-pm-practical-demo-acknowledged";
const demoSourceModules = import.meta.glob("./*.{css,ts,tsx}", {
  eager: true,
  import: "default",
  query: "?raw"
}) as Record<string, string>;

async function renderUnlockedCapxPmRoute(route: string) {
  const user = userEvent.setup();
  window.sessionStorage.setItem(ACKNOWLEDGEMENT_KEY, "true");
  window.history.pushState({}, "", route);
  const rendered = render(<App />);
  return { user, rendered };
}

describe("CAPX PM Practical Project Workspace demo", () => {
  beforeEach(() => {
    window.sessionStorage.clear();
    resetCapxPmPracticalAcknowledgementForTest();
    window.history.pushState({}, "", "/");
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("shows a local acknowledgement gate before opening the practical demo", async () => {
    const user = userEvent.setup();
    window.history.pushState({}, "", "/demo/capx/pm/projects");
    render(<App />);

    const gate = screen.getByTestId("capx-pm-practical-access-gate");
    expect(within(gate).getByRole("heading", { name: "CAPX PM Project Workspace" })).toBeInTheDocument();
    expect(within(gate).getByText(/local design-review screen/i)).toBeInTheDocument();
    expect(within(gate).getByText(/does not protect bundled javascript/i)).toBeInTheDocument();

    await user.click(within(gate).getByRole("button", { name: /acknowledge and open demo/i }));

    expect(await screen.findByTestId("capx-pm-practical-index-page")).toBeInTheDocument();
  });

  it("renders the practical project list route with package-required fields", async () => {
    await renderUnlockedCapxPmRoute("/demo/capx/pm/projects");

    expect(await screen.findByTestId("capx-pm-practical-index-page")).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "PM Project List" })).toBeInTheDocument();
    for (const header of [
      "Project",
      "Site / area",
      "PM",
      "Phase",
      "Needs attention",
      "Blockers",
      "Tasks due",
      "Missing documents",
      "Budget & orders",
      "Schedule",
      "Supplier questions",
      "Site handoffs",
      "Report status",
      "Last update"
    ]) {
      expect(screen.getByRole("columnheader", { name: header })).toBeInTheDocument();
    }
    expect(screen.getAllByText("Supplier answer overdue").length).toBeGreaterThanOrEqual(1);
    expect(screen.getAllByText("Production not confirmed").length).toBeGreaterThanOrEqual(1);
    expect(screen.getAllByText("Not ready").length).toBeGreaterThanOrEqual(1);
  });

  it("links project rows and cards into the default workspace route", async () => {
    const { rendered } = await renderUnlockedCapxPmRoute("/demo/capx/pm/projects");
    expect(await screen.findByTestId("capx-pm-practical-index-page")).toBeInTheDocument();

    const projectLinks = rendered.container.querySelectorAll('a[href="/demo/capx/pm/projects/P-104"]');
    expect(projectLinks.length).toBeGreaterThanOrEqual(1);
  });

  it("toggles the isolated practical shell theme with session-only state", async () => {
    const { user } = await renderUnlockedCapxPmRoute("/demo/capx/pm/projects");

    const shell = await screen.findByTestId("capx-pm-practical-shell");
    expect(shell).toHaveAttribute("data-theme", "practical");

    await user.click(screen.getByRole("button", { name: "Command theme" }));

    expect(shell).toHaveAttribute("data-theme", "command");
    expect(shell).toHaveClass("capx-pm-practical-demo--command");
    expect(window.sessionStorage.getItem("capx-pm-practical-demo-theme")).toBe("command");

    await user.click(screen.getByRole("button", { name: "Practical theme" }));

    expect(shell).toHaveAttribute("data-theme", "practical");
    expect(shell).not.toHaveClass("capx-pm-practical-demo--command");
  });

  it("defaults a known project route to its active practical step", async () => {
    await renderUnlockedCapxPmRoute("/demo/capx/pm/projects/P-104");

    expect(await screen.findByTestId("capx-pm-practical-workspace-page")).toBeInTheDocument();
    expect(screen.getAllByRole("heading", { name: /P-104 Orion Facility/i }).length).toBeGreaterThanOrEqual(1);
    expect(screen.getByRole("heading", { name: "Documents" })).toBeInTheDocument();
    expect(screen.getAllByText("Upload missing order attachment").length).toBeGreaterThanOrEqual(1);
    expect(screen.getByText(/Missing order blocks budget reporting/i)).toBeInTheDocument();
  });

  it("renders a known project step route with the practical step rail", async () => {
    await renderUnlockedCapxPmRoute("/demo/capx/pm/projects/P-104/steps/site-handoffs");

    expect(await screen.findByTestId("capx-pm-practical-workspace-page")).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Site handoffs" })).toBeInTheDocument();
    expect(screen.getAllByText("Confirm shutdown window").length).toBeGreaterThanOrEqual(1);
    expect(screen.getByRole("link", { name: /2 Documents/i })).toHaveAttribute(
      "href",
      "/demo/capx/pm/projects/P-104/steps/documents"
    );
  });

  it("renders mobile card fallbacks for checklist and record content", async () => {
    await renderUnlockedCapxPmRoute("/demo/capx/pm/projects/P-104/steps/documents");

    const checklistCards = await screen.findByTestId("capx-pm-practical-mobile-checklist");
    const recordCards = await screen.findByTestId("capx-pm-practical-mobile-records");

    expect(within(checklistCards).getByText("Order / PO")).toBeInTheDocument();
    expect(within(recordCards).getByText("Order / PO attachment")).toBeInTheDocument();
    expect(within(recordCards).getByText("Order file is missing.")).toBeInTheDocument();
  });

  it.each([
    {
      step: "setup",
      heading: "Project setup",
      concepts: ["Confirm sponsor and document folder", "Document folder", "Project opening note"]
    },
    {
      step: "documents",
      heading: "Documents",
      concepts: ["Upload missing order attachment", "Order / PO attachment", "Supplier quote Q-144"]
    },
    {
      step: "timeline",
      heading: "Timeline",
      concepts: ["Confirm new installation date", "Installation date moved by two weeks", "Shutdown request"]
    },
    {
      step: "budget-orders",
      heading: "Budget & orders",
      concepts: ["Review quote increase", "Revised supplier quote", "Finance review is required"]
    },
    {
      step: "supplier-questions",
      heading: "Supplier questions",
      concepts: ["Confirm foundation assumption", "Foundation capacity", "Supplier answer is needed"]
    },
    {
      step: "site-handoffs",
      heading: "Site handoffs",
      concepts: ["Confirm shutdown window", "Production has not confirmed", "Training plan"]
    },
    {
      step: "project-report",
      heading: "Project report",
      concepts: ["Re-check report after changes", "Missing order", "Report not ready"]
    }
  ])("renders distinct practical $step workpage concepts", async ({ step, heading, concepts }) => {
    await renderUnlockedCapxPmRoute(`/demo/capx/pm/projects/P-104/steps/${step}`);

    expect(await screen.findByTestId(`capx-pm-practical-step-${step}`)).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: heading })).toBeInTheDocument();
    for (const concept of concepts) {
      expect(screen.getAllByText(concept, { exact: false }).length).toBeGreaterThanOrEqual(1);
    }
    expect(screen.getByTestId("capx-pm-practical-disabled-action")).toBeDisabled();
    expect(screen.getByText(/simulated only/i)).toBeInTheDocument();
    expect(screen.getByText(/does not update project records/i)).toBeInTheDocument();
  });

  it("renders bounded not-found states for unknown project and step IDs", async () => {
    const { rendered } = await renderUnlockedCapxPmRoute("/demo/capx/pm/projects/P-999/steps/documents");

    const projectNotFound = await screen.findByTestId("capx-pm-practical-project-not-found");
    expect(within(projectNotFound).getByRole("heading", { name: "Project not found" })).toBeInTheDocument();
    expect(within(projectNotFound).getByRole("link", { name: "Back to PM projects" })).toHaveAttribute(
      "href",
      "/demo/capx/pm/projects"
    );

    rendered.unmount();
    await renderUnlockedCapxPmRoute("/demo/capx/pm/projects/P-104/steps/not-a-step");

    const stepNotFound = await screen.findByTestId("capx-pm-practical-step-not-found");
    expect(within(stepNotFound).getByRole("heading", { name: "Step not found" })).toBeInTheDocument();
    expect(within(stepNotFound).getByRole("link", { name: "Open active step" })).toHaveAttribute(
      "href",
      "/demo/capx/pm/projects/P-104/steps/documents"
    );
  });

  it("uses filled status chips without visible color-name labels", async () => {
    const { rendered } = await renderUnlockedCapxPmRoute("/demo/capx/pm/projects");

    const chips = Array.from(rendered.container.querySelectorAll("[data-status-chip]"));
    expect(chips.length).toBeGreaterThan(0);
    expect(screen.queryByText(/\b(red|yellow|green|amber)\b/i)).not.toBeInTheDocument();
    for (const chip of chips) {
      expect(chip.textContent).not.toMatch(/\b(red|yellow|green|amber)\b/i);
      expect(chip).toHaveAttribute("aria-label");
      expect(chip).toHaveAttribute("title");
    }
  });

  it("renders without backend API fetch calls", async () => {
    const fetchMock = vi.fn();
    vi.stubGlobal("fetch", fetchMock);

    await renderUnlockedCapxPmRoute("/demo/capx/pm/projects/P-104/steps/budget-orders");

    expect(await screen.findByTestId("capx-pm-practical-workspace-page")).toBeInTheDocument();
    expect(fetchMock).not.toHaveBeenCalled();
  });

  it("does not include bundled credential patterns or forbidden PM wording in practical demo source", () => {
    const vitePrefix = "VITE_.*";
    const credentialWord = ["pass", "word"].join("");
    const guardedWord = ["sec", "ret"].join("");
    const credentialPattern = new RegExp(`${vitePrefix}${"PASS"}${"WORD"}|${credentialWord}|${guardedWord}`, "i");
    const forbiddenTerms = [
      ["cor", "pus baseline"].join(""),
      ["source", " occurrence"].join(""),
      ["pro", "jection"].join(""),
      ["pointer", " promotion"].join(""),
      ["canonical", " state"].join(""),
      ["artifact", " graph"].join(""),
      ["workflow", " substrate"].join(""),
      ["provenance", " edge"].join("")
    ];
    const forbiddenPattern = new RegExp(forbiddenTerms.join("|"), "i");
    const matches = Object.entries(demoSourceModules)
      .filter(([path]) => !path.endsWith("capx-pm-practical-demo.test.tsx"))
      .flatMap(([path, text]) => (credentialPattern.test(text) || forbiddenPattern.test(text) ? [path] : []));

    expect(matches).toEqual([]);
  });
});
