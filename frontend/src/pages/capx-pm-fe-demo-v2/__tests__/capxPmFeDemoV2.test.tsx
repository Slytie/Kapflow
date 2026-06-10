import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { App } from "@/app/App";
import { resetCapxPmFeDemoAccessForTest } from "@/pages/capx-pm-fe-demo/CapxPmFeDemoAccessGate";
import { resetCapxPmFeDemoV2AccessForTest } from "../CapxPmFeDemoV2AccessGate";

const V1_ACCESS_KEY = "capx_pm_fe_demo_access_granted";
const V2_ACCESS_KEY = "capx_pm_fe_demo_v2_access_granted";

async function renderUnlocked(route: string) {
  window.sessionStorage.setItem(V1_ACCESS_KEY, "true");
  window.sessionStorage.setItem(V2_ACCESS_KEY, "true");
  window.history.pushState({}, "", route);
  return render(<App />);
}

const stepCases = [
  {
    stepId: "project-setup",
    testId: "capx-pm-v2-step-project-setup",
    mobileTestId: "capx-pm-v2-mobile-project-setup",
    concepts: ["Kickoff / takeover", "Missing setup checklist", "Setup exceptions and owners"]
  },
  {
    stepId: "documents",
    testId: "capx-pm-v2-step-documents",
    mobileTestId: "capx-pm-v2-mobile-documents",
    concepts: ["Document checklist", "Latest files table", "Version conflicts", "Local detail"]
  },
  {
    stepId: "timeline",
    testId: "capx-pm-v2-step-timeline",
    mobileTestId: "capx-pm-v2-mobile-timeline",
    concepts: ["Baseline vs forecast table", "slippage reasons", "Confidence", "Open read-only Gantt"]
  },
  {
    stepId: "budget-orders",
    testId: "capx-pm-v2-step-budget-orders",
    mobileTestId: "capx-pm-v2-mobile-budget-orders",
    concepts: ["Budget summary", "Quote / PO / change-order timeline", "Fictional demo values", "Approval needed"]
  },
  {
    stepId: "supplier-questions",
    testId: "capx-pm-v2-step-supplier-questions",
    mobileTestId: "capx-pm-v2-mobile-supplier-questions",
    concepts: ["Supplier open-points board", "Overdue answers", "Blocked work", "Accepted / rejected"]
  },
  {
    stepId: "site-handoffs",
    testId: "capx-pm-v2-step-site-handoffs",
    mobileTestId: "capx-pm-v2-mobile-site-handoffs",
    concepts: ["Site readiness board", "Production acceptance", "Quality check", "Shutdown / access window"]
  },
  {
    stepId: "project-report",
    testId: "capx-pm-v2-step-project-report",
    mobileTestId: null,
    concepts: ["Report readiness", "Suggested PM update", "Proof used", "Caveats"]
  }
] as const;

describe("CAPX PM FE demo V2", () => {
  beforeEach(() => {
    window.sessionStorage.clear();
    resetCapxPmFeDemoAccessForTest();
    resetCapxPmFeDemoV2AccessForTest();
    window.history.pushState({}, "", "/");
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("keeps V1 available at the original PM route", async () => {
    await renderUnlocked("/demo/capx/pm/projects");

    expect(await screen.findByTestId("capx-pm-fe-projects-page")).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Open the project that needs PM attention first" })).toBeInTheDocument();
  });

  it("shows a separate V2 gate and unlocks without touching V1 gate state", async () => {
    const user = userEvent.setup();
    window.history.pushState({}, "", "/demo/capx/pm-v2/projects");
    render(<App />);

    const gate = screen.getByTestId("capx-pm-v2-access-gate");
    expect(within(gate).getByRole("heading", { name: "Private design review" })).toBeInTheDocument();
    expect(within(gate).getByText(/first PM demo route remains available/i)).toBeInTheDocument();

    await user.type(within(gate).getByLabelText("Local handoff phrase"), "capx-demo-local");
    await user.click(within(gate).getByRole("button", { name: "Open V2" }));

    expect(await screen.findByTestId("capx-pm-v2-projects-page")).toBeInTheDocument();
    expect(window.sessionStorage.getItem(V2_ACCESS_KEY)).toBe("true");
    expect(window.sessionStorage.getItem(V1_ACCESS_KEY)).toBeNull();
  });

  it("renders the V2 attention cockpit and links to V2 project detail", async () => {
    const rendered = await renderUnlocked("/demo/capx/pm-v2/projects");

    expect(await screen.findByTestId("capx-pm-v2-projects-page")).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "What should I open first?" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "P-104 next action" })).toBeInTheDocument();
    expect(screen.getByText("V1 preserved")).toBeInTheDocument();
    expect(rendered.container.querySelectorAll('a[href="/demo/capx/pm-v2/projects/P-104"]').length).toBeGreaterThanOrEqual(1);
  });

  it("renders the V2 workspace shell and defaults to the active project step", async () => {
    await renderUnlocked("/demo/capx/pm-v2/projects/P-104");

    expect(await screen.findByTestId("capx-pm-v2-project-page")).toBeInTheDocument();
    expect(screen.getByTestId("capx-pm-v2-workspace-shell")).toBeInTheDocument();
    expect(screen.getByTestId("capx-pm-v2-active-step-summary")).toBeInTheDocument();
    expect(screen.getByTestId("capx-pm-v2-step-documents")).toBeInTheDocument();
    expect(screen.getByText("Practical PM flow")).toBeInTheDocument();
    expect(screen.getByText("Next action")).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Open decisions" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Open V1 workspace" })).toHaveAttribute(
      "href",
      "/demo/capx/pm/projects/P-104"
    );
  });

  it.each(stepCases)("renders the V2 $stepId step with its practical concepts and mobile card surface", async (stepCase) => {
    await renderUnlocked(`/demo/capx/pm-v2/projects/P-104/steps/${stepCase.stepId}`);

    expect(await screen.findByTestId(stepCase.testId)).toBeInTheDocument();
    for (const concept of stepCase.concepts) {
      expect(screen.getAllByText(concept, { exact: false }).length).toBeGreaterThan(0);
    }
    if (stepCase.mobileTestId) {
      expect(screen.getByTestId(stepCase.mobileTestId)).toBeInTheDocument();
    }
  });

  it("renders the V2 read-only Gantt with desktop bars and mobile cards", async () => {
    await renderUnlocked("/demo/capx/pm-v2/projects/P-104/gantt");

    expect(await screen.findByTestId("capx-pm-v2-gantt-page")).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Project Gantt" })).toBeInTheDocument();
    expect(screen.getAllByText("Critical path", { exact: false }).length).toBeGreaterThan(0);
    expect(screen.getAllByText("Changed since last report", { exact: false }).length).toBeGreaterThan(0);
    expect(screen.getByTestId("capx-pm-v2-gantt-mobile-cards")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Open Timeline step" })).toHaveAttribute(
      "href",
      "/demo/capx/pm-v2/projects/P-104/steps/timeline"
    );
  });

  it("renders bounded V2 not-found states", async () => {
    await renderUnlocked("/demo/capx/pm-v2/projects/not-real");

    expect(await screen.findByTestId("capx-pm-v2-project-not-found")).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Project not found" })).toBeInTheDocument();
  });

  it("renders bounded V2 step, Gantt-project, and route not-found states", async () => {
    const stepRoute = await renderUnlocked("/demo/capx/pm-v2/projects/P-104/steps/not-real");
    expect(await screen.findByTestId("capx-pm-v2-step-not-found")).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Step not found" })).toBeInTheDocument();
    stepRoute.unmount();

    window.history.pushState({}, "", "/demo/capx/pm-v2/projects/nope/gantt");
    const ganttRoute = render(<App />);
    expect(await screen.findByTestId("capx-pm-v2-gantt-project-not-found")).toBeInTheDocument();
    ganttRoute.unmount();

    window.history.pushState({}, "", "/demo/capx/pm-v2/not-a-route");
    render(<App />);
    expect(await screen.findByTestId("capx-pm-v2-route-not-found")).toBeInTheDocument();
  });

  it("does not visibly render color-name labels for status chips", async () => {
    await renderUnlocked("/demo/capx/pm-v2/projects/P-104/steps/documents");

    expect(screen.queryByText(/\b(red|yellow|green|amber)\b/i)).not.toBeInTheDocument();
  });

  it("renders V2 without backend fetch calls", async () => {
    const fetchSpy = vi.fn();
    vi.stubGlobal("fetch", fetchSpy);

    await renderUnlocked("/demo/capx/pm-v2/projects/P-104/steps/budget-orders");

    expect(fetchSpy).not.toHaveBeenCalled();
  });
});
