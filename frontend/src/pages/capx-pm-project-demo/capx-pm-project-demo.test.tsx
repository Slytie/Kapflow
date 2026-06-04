import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, vi } from "vitest";

import { App } from "@/app/App";
import { resetCapxPmProjectAcknowledgementForTest } from "./CapxPmProjectAccessGate";

const ACKNOWLEDGEMENT_KEY = "capx-pm-project-demo-acknowledged";

async function renderUnlockedCapxPmRoute(route: string) {
  const user = userEvent.setup();
  window.sessionStorage.setItem(ACKNOWLEDGEMENT_KEY, "true");
  window.history.pushState({}, "", route);
  const rendered = render(<App />);
  return { user, rendered };
}

describe("CAPX PM Project Workflow demo", () => {
  beforeEach(() => {
    window.sessionStorage.clear();
    resetCapxPmProjectAcknowledgementForTest();
    window.history.pushState({}, "", "/");
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("shows a local acknowledgement gate before opening the demo", async () => {
    const user = userEvent.setup();
    window.history.pushState({}, "", "/demo/capx/pm/projects");
    render(<App />);

    const gate = screen.getByTestId("capx-pm-access-gate");
    expect(within(gate).getByRole("heading", { name: "CAPX PM Project Workflow" })).toBeInTheDocument();
    expect(within(gate).getByText(/local design-review speed bump/i)).toBeInTheDocument();
    expect(within(gate).getByText(/does not protect bundled javascript/i)).toBeInTheDocument();

    await user.click(within(gate).getByRole("button", { name: /acknowledge and open demo/i }));

    expect(await screen.findByTestId("capx-pm-index-page")).toBeInTheDocument();
  });

  it("renders the PM project index route with required project fields", async () => {
    await renderUnlockedCapxPmRoute("/demo/capx/pm/projects");

    expect(await screen.findByTestId("capx-pm-index-page")).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "PM Project Index" })).toBeInTheDocument();
    expect(screen.getByRole("columnheader", { name: "Project" })).toBeInTheDocument();
    expect(screen.getByRole("columnheader", { name: "PM owner" })).toBeInTheDocument();
    expect(screen.getByRole("columnheader", { name: "Dominant stage" })).toBeInTheDocument();
    expect(screen.getByRole("columnheader", { name: "Active workflow step" })).toBeInTheDocument();
    expect(screen.getByRole("columnheader", { name: "Evidence freshness" })).toBeInTheDocument();
    expect(screen.getByRole("columnheader", { name: "Snapshot readiness" })).toBeInTheDocument();
  });

  it("links project rows and cards into the project workspace route", async () => {
    const { rendered } = await renderUnlockedCapxPmRoute("/demo/capx/pm/projects");
    expect(await screen.findByTestId("capx-pm-index-page")).toBeInTheDocument();

    const projectLinks = rendered.container.querySelectorAll('a[href="/demo/capx/pm/projects/PM-204"]');
    expect(projectLinks.length).toBeGreaterThanOrEqual(1);
  });

  it("defaults a known project route to its active workflow step", async () => {
    await renderUnlockedCapxPmRoute("/demo/capx/pm/projects/PM-204");

    expect(await screen.findByTestId("capx-pm-workspace-page")).toBeInTheDocument();
    expect(screen.getAllByRole("heading", { name: /PM-204 Meridian Mock Line/i }).length).toBeGreaterThanOrEqual(1);
    expect(screen.getByRole("heading", { name: "Corpus Baseline / Packet Formation" })).toBeInTheDocument();
    expect(screen.getByText(/unresolved references/i)).toBeInTheDocument();
  });

  it("renders a known project step route", async () => {
    await renderUnlockedCapxPmRoute("/demo/capx/pm/projects/PM-204/steps/interfaces");

    expect(await screen.findByTestId("capx-pm-workspace-page")).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Owner Interface Resolution" })).toBeInTheDocument();
    expect(screen.getByText("Assign utility tie-in provider and receiver")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /Corpus WFLOW-002/i })).toHaveAttribute(
      "href",
      "/demo/capx/pm/projects/PM-204/steps/corpus"
    );
  });

  it.each([
    {
      step: "intake",
      testId: "capx-pm-step-intake",
      heading: "Project Intake Router",
      concepts: ["Missing sponsor/authorization", "Intake-blocked exception", "CEO-entry decision packet"]
    },
    {
      step: "corpus",
      testId: "capx-pm-step-corpus",
      heading: "Corpus Baseline / Packet Formation",
      concepts: ["Artifact-role review task", "Unresolved SourceRef task", "Sensitive file quarantine"]
    },
    {
      step: "lifecycle",
      testId: "capx-pm-step-lifecycle",
      heading: "Lifecycle Stage Map",
      concepts: ["Stage conflict review", "Recurrence due stale/reopen task", "Handover-with-open-closure warning"]
    },
    {
      step: "commitment",
      testId: "capx-pm-step-commitment",
      heading: "Governance / Commitment Chain",
      concepts: [
        "Quote/order revision mismatch review",
        "Budget/exposure threshold CEO escalation",
        "Commercial-not-technical closure guard"
      ]
    },
    {
      step: "assumptions",
      testId: "capx-pm-step-assumptions",
      heading: "Supplier Assumption Closure",
      concepts: ["Missing evidence", "Supplier clarification", "Waiver approval"]
    },
    {
      step: "interfaces",
      testId: "capx-pm-step-interfaces",
      heading: "Owner Interface Resolution",
      concepts: ["Unassigned owner blocking task", "Required/provided condition conflict", "Authority/operator acceptance task"]
    },
    {
      step: "snapshot",
      testId: "capx-pm-step-snapshot",
      heading: "Project State Snapshot",
      concepts: ["Unresolved SourceRef blocker", "Closure contradiction blocker", "Stale basis rebuild task"]
    }
  ])("renders distinct $step workpage concepts", async ({ step, testId, heading, concepts }) => {
    await renderUnlockedCapxPmRoute(`/demo/capx/pm/projects/PM-204/steps/${step}`);

    expect(await screen.findByTestId(testId)).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: heading })).toBeInTheDocument();
    for (const concept of concepts) {
      expect(screen.getAllByText(concept, { exact: false }).length).toBeGreaterThanOrEqual(1);
    }
    expect(screen.getByRole("button", { name: /simulated/i })).toBeDisabled();
    expect(screen.getByText(/cannot approve, close, promote, publish, or create official CAPX truth/i)).toBeInTheDocument();
  });

  it("renders bounded not-found states for unknown project and step IDs", async () => {
    const { rendered } = await renderUnlockedCapxPmRoute("/demo/capx/pm/projects/PM-999/steps/intake");

    const projectNotFound = await screen.findByTestId("capx-pm-project-not-found");
    expect(within(projectNotFound).getByRole("heading", { name: "Project not found" })).toBeInTheDocument();
    expect(within(projectNotFound).getByRole("link", { name: "Back to PM projects" })).toHaveAttribute(
      "href",
      "/demo/capx/pm/projects"
    );

    rendered.unmount();
    await renderUnlockedCapxPmRoute("/demo/capx/pm/projects/PM-204/steps/not-a-step");

    const stepNotFound = await screen.findByTestId("capx-pm-step-not-found");
    expect(within(stepNotFound).getByRole("heading", { name: "Step not found" })).toBeInTheDocument();
    expect(within(stepNotFound).getByRole("link", { name: "Open active step" })).toHaveAttribute(
      "href",
      "/demo/capx/pm/projects/PM-204/steps/corpus"
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
    }
  });

  it("renders without backend API fetch calls", async () => {
    const fetchMock = vi.fn();
    vi.stubGlobal("fetch", fetchMock);

    await renderUnlockedCapxPmRoute("/demo/capx/pm/projects/PM-204/steps/intake");

    expect(await screen.findByTestId("capx-pm-workspace-page")).toBeInTheDocument();
    expect(fetchMock).not.toHaveBeenCalled();
  });
});
