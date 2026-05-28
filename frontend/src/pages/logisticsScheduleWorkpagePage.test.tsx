import { act, render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { HttpResponse, http } from "msw";
import { afterEach, vi } from "vitest";

import driverPreferencesRunWorkpageStateSnapshot from "@fixtures/workpage_driver_preferences_v0_run_state.json";
import routeDemandArtifactStateSnapshot from "@fixtures/workpage_route_demand_v0_artifact_state.json";
import routeDemandRunWorkpageStateSnapshot from "@fixtures/workpage_route_demand_v0_run_state.json";
import scheduleArtifactStateSnapshot from "@fixtures/workpage_schedule_v0_artifact_state.json";
import scheduleRunWorkpageStateSnapshot from "@fixtures/workpage_schedule_v0_run_state.json";
import { App } from "@/app/App";
import {
  SCHEDULE_CHECKS_SUMMARY,
  SCHEDULE_CHECK_ITEM_SUMMARIES,
  SCHEDULE_DEPENDENCY_ITEM_SUMMARIES,
  SCHEDULE_DEPENDENCY_STATUS_SUMMARY
} from "@/components/workpages/ScheduleWorkpageSurface";
import { getApiRequestContextHeaders, setApiRequestContextHeaders } from "@/lib/api/config";
import { workpagesRepository } from "@/lib/repositories";
import { server } from "@/test/api/server";
import { mutationLog } from "@/test/api/handlers";
import {
  expectHeatmapHeaderStatusGroups,
  expectHeatmapPreferenceBars,
  expectHeatmapSummaryRailLabels,
  expectSelectedDateHeaderValues,
  scheduleHeatmapSectionIn as heatmapSection
} from "./logisticsScheduleTestHelpers";

function setFrontendOperatorContext(): void {
  const currentContext = getApiRequestContextHeaders();
  setApiRequestContextHeaders({
    ...currentContext,
    actorId: "human:frontend-operator",
    actorType: "human",
    actorRoles: "dispatch_supervisor,schedule_planner,fleet_coordinator,operations_manager"
  });
}

function driverHeatmapRow(section: HTMLElement, driverName: string): HTMLElement {
  const row = within(section).getByText(driverName).closest("tr");
  if (!row) {
    throw new Error(`Heatmap row not found for ${driverName}`);
  }
  return row as HTMLElement;
}

function setTestCurrentServiceDate(serviceDate: string | null): void {
  if (serviceDate) {
    (
      globalThis as {
        __COMPANYOS_TEST_CURRENT_SERVICE_DATE__?: string;
      }
    ).__COMPANYOS_TEST_CURRENT_SERVICE_DATE__ = serviceDate;
    return;
  }
  delete (
    globalThis as {
      __COMPANYOS_TEST_CURRENT_SERVICE_DATE__?: string;
    }
  ).__COMPANYOS_TEST_CURRENT_SERVICE_DATE__;
}

function shiftIsoDate(isoDate: string, days: number): string {
  const date = new Date(`${isoDate}T00:00:00Z`);
  date.setUTCDate(date.getUTCDate() + days);
  return date.toISOString().slice(0, 10);
}

function replaceMappedDateStrings(value: unknown, replacements: Map<string, string>): unknown {
  if (Array.isArray(value)) {
    return value.map((item) => replaceMappedDateStrings(item, replacements));
  }
  if (value && typeof value === "object") {
    return Object.fromEntries(
      Object.entries(value as Record<string, unknown>).map(([key, entryValue]) => [
        key,
        replaceMappedDateStrings(entryValue, replacements)
      ])
    );
  }
  if (typeof value !== "string") {
    return value;
  }
  let nextValue = value;
  for (const [from, to] of replacements) {
    nextValue = nextValue.split(from).join(to);
  }
  return nextValue;
}

function buildFutureScheduleArtifactPayload(
  artifactVersionId: string,
  workflowRunId: string
): Record<string, unknown> {
  const payload = structuredClone(scheduleArtifactStateSnapshot.workpage_state) as Record<string, any>;
  const replacements = new Map<string, string>();
  for (let offset = 0; offset < 7; offset += 1) {
    const fromDate = shiftIsoDate("2026-03-22", offset);
    const toDate = shiftIsoDate("2026-03-29", offset);
    replacements.set(fromDate, toDate);
    replacements.set(fromDate.replaceAll("-", ""), toDate.replaceAll("-", ""));
  }
  const shifted = replaceMappedDateStrings(payload, replacements) as Record<string, any>;
  shifted.freshness.source_version = artifactVersionId;
  shifted.source.source_artifact_version_id = artifactVersionId;
  shifted.artifact_context.workflow_run_id = workflowRunId;
  shifted.artifact_context.artifact_version_id = artifactVersionId;
  shifted.artifact_context.latest_in_chain_artifact_version_id = artifactVersionId;
  shifted.workpage.source_artifact_version_id = artifactVersionId;
  shifted.workpage.summary.operational_week_start = "2026-03-29";
  shifted.calculations.selected_day.service_date = "2026-03-31";
  return shifted;
}

function buildFutureRollingRealityContract(
  workflowRunId: string,
  artifactVersionId: string
): Record<string, unknown> {
  const previousWeekStart = "2026-03-22";
  return {
    artifact_context: {
      artifact_version_id: artifactVersionId,
      workflow_run_id: workflowRunId,
      artifact_kind: "planning.draft_weekly_schedule.workbook",
      supersedes_artifact_version_id: null,
      superseded_by_artifact_version_id: null,
      latest_in_chain_artifact_version_id: artifactVersionId,
      download_path: `/api/v1/artifacts/${artifactVersionId}/download.bin`
    },
    source: {
      mode: "artifact_projection",
      primary_dataset_key: "planning.actual_hours_snapshot.workbook",
      source_dataset_keys: ["planning.actual_hours_snapshot.workbook"],
      source_artifact_version_id: "av-actual-hours-001",
      source_refs: ["/api/v1/artifacts/av-actual-hours-001"]
    },
    freshness: {
      generated_at: "2026-03-25T09:15:00Z",
      source_kind: "frontend-test",
      source_version: "rolling-reality-fixture-future"
    },
    previous_week_reality: {
      workflow_run_id: workflowRunId,
      schedule_artifact_version_id: artifactVersionId,
      actual_hours_artifact_version_id: "av-actual-hours-001",
      planning_week_id: "2026-W14",
      operational_week_start: "2026-03-29",
      previous_week_start: previousWeekStart,
      previous_week_end: "2026-03-28",
      service_dates: ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"].map((weekdayLabel, index) => {
        const serviceDate = shiftIsoDate(previousWeekStart, index);
        return {
          service_date: serviceDate,
          label: serviceDate,
          weekday_label: weekdayLabel
        };
      }),
      drivers: [
        {
          driver_id: "A2TU4ZRI65E1H8",
          driver_name: "Abhiraj Singh",
          employment_type: "FT",
          on_call_eligible: true,
          availability_summary: "Available",
          previous_week_minutes: 1680,
          cells: Array.from({ length: 7 }, (_, index) => {
            const serviceDate = shiftIsoDate(previousWeekStart, index);
            return {
              service_date: serviceDate,
              state: "WORKED",
              normalized_state: "worked",
              blocked_reasons: [],
              actual_minutes: 60 * (index + 1),
              cumulative_week_minutes: ((index + 1) * (index + 2) * 60) / 2,
              route_id: `prev-route-${index + 1}`,
              route_slot_class: "AM",
              source_ref: `reality:${index + 1}`,
              call_in_sick_flag: false,
              cancellation_flag: false,
              non_working_day_flag: false
            };
          })
        }
      ],
      day_summaries: [],
      activity_rows: [],
      note: "Pinned previous-week reality snapshot."
    }
  };
}

afterEach(() => {
  setTestCurrentServiceDate(null);
  vi.restoreAllMocks();
});

function buildCoverageCandidate(
  coverageTarget: Record<string, any>,
  recommendationRank: number,
  driverId: string,
  driverName: string,
  overrides: Record<string, any> = {}
): Record<string, any> {
  return {
    recommendation_rank: recommendationRank,
    target_id: coverageTarget.target_id,
    route_slot_id: coverageTarget.route_slot_id,
    route_id: coverageTarget.route_id,
    row_kind: "assignment",
    service_date: coverageTarget.service_date,
    driver_id: driverId,
    driver_name: driverName,
    selection_state: "selectable",
    hard_filter_status: "pass",
    hard_filter_reasons: [],
    score_bucket: "best_fit",
    soft_score_total: 98 - recommendationRank,
    projected_minutes: coverageTarget.projected_minutes,
    availability_state: "AVAILABLE",
    current_week_shift_count: 3 + recommendationRank,
    projected_rolling7_minutes: 1800 + recommendationRank * 45,
    remaining_rolling7_minutes: 1800 - recommendationRank * 40,
    fairness_balance: 0.1 + recommendationRank * 0.01,
    target_shift_gap: 1,
    preference_fit: 1,
    preferred_shift_band_fit: 1,
    preferred_route_slot_class_fit: 1,
    seniority_preference_fit: 0.9,
    reliability_score: 0.95,
    previous_week_stability: 0.9,
    baseline_template_state: "white_template",
    planned_driver_day_state: recommendationRank === 1 ? "on_call" : "open",
    new_agreement_required: false,
    new_agreement_trigger_reason: "",
    template_state_preservation_fit: 0.96,
    clear_same_day_on_call_reserve: recommendationRank === 1,
    reserve_route_slot_id: recommendationRank === 1 ? "oncall-20260324#01" : null,
    reserve_route_id: recommendationRank === 1 ? "ON_CALL" : null,
    assignment_action: recommendationRank === 1 ? "promote_reserve" : "assign_open_driver",
    evaluation_kind: recommendationRank === 1 ? "reserve_promotion" : "best_fit",
    ...overrides
  };
}

describe("LogisticsScheduleWorkpagePage", () => {
  it(
    "renders the canonical run-backed surface without the redundant landing hero",
    async () => {
      const user = userEvent.setup();
      let responseCount = 0;
      server.use(
        http.get("*/api/v1/workpages/workflow-runs/:workflowRunId/schedule-v0", ({ params }) => {
          responseCount += 1;
          const payload = structuredClone(scheduleRunWorkpageStateSnapshot.workpage_state) as Record<
            string,
            any
          >;
          payload.freshness.generated_at =
            responseCount === 1 ? "2026-03-25T08:00:00Z" : "2026-03-25T08:00:30Z";
          payload.run_context.workflow_run_id = String(params.workflowRunId);
          return HttpResponse.json(payload);
        })
      );
      setFrontendOperatorContext();
      window.history.pushState({}, "", "/runs/wr-weekly-001/workpages/schedule-v0");
      render(<App />);

      const page = await screen.findByTestId("schedule-workpage-page");
      expect(page.querySelector(".workpage-page__hero")).toBeNull();
      expect(within(page).queryByRole("heading", { name: "Weekly schedule review" })).not.toBeInTheDocument();
      expect(within(page).queryByText("Weekly Planning Review")).not.toBeInTheDocument();
      expect(
        within(page).queryByText(
          "This landing page stays read-only. Open the backend-selected latest draft when you need live preview and save controls."
        )
      ).not.toBeInTheDocument();
      expect(
        within(page).queryByText(
          "A workflow-backed weekly planning review for bounded draft navigation, live schedule context, and backend-authored metrics."
        )
      ).not.toBeInTheDocument();
      expect(within(page).queryByRole("link", { name: "Open editable draft" })).not.toBeInTheDocument();
      expect(within(page).queryByRole("link", { name: "Open route demand" })).not.toBeInTheDocument();
      expect(within(page).queryByRole("link", { name: "Open driver preferences" })).not.toBeInTheDocument();
      expect(within(page).queryByRole("heading", { name: "Editable draft available" })).not.toBeInTheDocument();
      expect(within(page).queryByRole("heading", { name: "Capacity bar" })).not.toBeInTheDocument();
      const { dependencyGroup, checksGroup } = expectHeatmapHeaderStatusGroups(page);
      expect(within(page).getByRole("heading", { name: "Planned schedule heatmap" })).toBeInTheDocument();
      expect(within(page).queryByRole("heading", { name: "Driver metrics" })).not.toBeInTheDocument();
      expect(within(page).queryByRole("heading", { name: "Accepted history" })).not.toBeInTheDocument();
      expect(within(page).queryByRole("heading", { name: "Draft lineage" })).not.toBeInTheDocument();
      expect(
        within(page).queryByText(
          "Accepted navigation stays on accepted weekly history only and never traverses draft lineage."
        )
      ).not.toBeInTheDocument();
      expect(
        within(page).queryByText(
          "Draft navigation stays within backend-authored draft lineage for this immutable schedule surface."
        )
      ).not.toBeInTheDocument();
      expect(screen.queryByText("Scenario sick calls")).not.toBeInTheDocument();
      expect(screen.queryByRole("textbox", { name: /Planner note/i })).not.toBeInTheDocument();
      expect(screen.queryByRole("spinbutton", { name: /Scenario added routes/i })).not.toBeInTheDocument();
      const routeSlotRequirementsChip = within(dependencyGroup).getByText("Route Slot Requirements");
      expect(routeSlotRequirementsChip.getAttribute("title")).toContain(
        SCHEDULE_DEPENDENCY_ITEM_SUMMARIES.route_slot_requirements
      );
      expect(
        within(dependencyGroup).queryByText("planning.route_slot_requirements.workbook")
      ).not.toBeInTheDocument();
      const scheduledCapacityChip = within(checksGroup).getByText("Routes within scheduled capacity");
      expect(scheduledCapacityChip.getAttribute("title")).toContain(
        SCHEDULE_CHECK_ITEM_SUMMARIES.scheduled_capacity
      );
      expect(within(checksGroup).getAllByText("Blocking").length).toBeGreaterThan(0);
      expect(within(checksGroup).queryByText(/^pass$/i)).not.toBeInTheDocument();
      expect(within(checksGroup).queryByText(/^warn$/i)).not.toBeInTheDocument();
      expect(within(checksGroup).queryByText(/^fail$/i)).not.toBeInTheDocument();
      expect(screen.queryByRole("tooltip")).not.toBeInTheDocument();
      expect(screen.queryByText(SCHEDULE_DEPENDENCY_STATUS_SUMMARY)).not.toBeInTheDocument();
      expect(screen.queryByText(SCHEDULE_CHECKS_SUMMARY)).not.toBeInTheDocument();
      const dependencySummaryButton = within(dependencyGroup).getByRole("button", {
        name: "Show summary for Dependency status"
      });
      const checksSummaryButton = within(checksGroup).getByRole("button", {
        name: "Show summary for Checks"
      });
      await user.hover(dependencySummaryButton);
      expect(await screen.findByRole("tooltip")).toHaveTextContent(SCHEDULE_DEPENDENCY_STATUS_SUMMARY);
      await user.unhover(dependencySummaryButton);
      await waitFor(() => {
        expect(screen.queryByRole("tooltip")).not.toBeInTheDocument();
      });
      act(() => {
        checksSummaryButton.focus();
      });
      expect(await screen.findByRole("tooltip")).toHaveTextContent(SCHEDULE_CHECKS_SUMMARY);
      act(() => {
        checksSummaryButton.blur();
      });
      await waitFor(() => {
        expect(screen.queryByRole("tooltip")).not.toBeInTheDocument();
      });
      const heatmap = heatmapSection(page);
      expectHeatmapSummaryRailLabels(page);
      expectSelectedDateHeaderValues(page);
      expectHeatmapPreferenceBars(page);
      expect(within(heatmap).getByRole("columnheader", { name: /Hours/i })).toBeInTheDocument();
      expect(within(heatmap).getByRole("columnheader", { name: /Routes/i })).toBeInTheDocument();
      expect(within(heatmap).getByRole("columnheader", { name: /On call/i })).toBeInTheDocument();
      expect(within(heatmap).getByRole("columnheader", { name: /Compliance/i })).toBeInTheDocument();
      const abhirajRow = driverHeatmapRow(heatmap, "Abhiraj Singh");
      expect(within(abhirajRow).getByText("18.0 h")).toBeInTheDocument();
      expect(within(abhirajRow).queryByText("Pref Unset")).not.toBeInTheDocument();
      expect(within(abhirajRow).queryByText("Avail Available")).not.toBeInTheDocument();
      const riskTrigger = within(abhirajRow).getByRole("button", {
        name: "Open compliance details for Abhiraj Singh"
      });
      expect(riskTrigger).toHaveClass("schedule-heatmap__risk-trigger");
      expect(riskTrigger).toHaveTextContent("Fail");
      expect(mutationLog()).toEqual([]);
    },
    90000
  );

  it("shows uncovered route additions in red on the main schedule when latest route demand is ahead of the draft", async () => {
    const workflowRunId = "wr-weekly-001";
    const draftArtifactVersionId = "av-schedule-artifact-001";
    const routeDemandArtifactVersionId = "av-route-demand-artifact-002";
    const coverageCandidatesPath =
      `/api/v1/workpages/workflow-runs/${workflowRunId}/schedule-v0/artifacts/` +
      `${draftArtifactVersionId}/route-demand-coverage-candidates`;
    const coverageTargetA = {
      target_id: `${routeDemandArtifactVersionId}:2026-03-24:1`,
      route_slot_id: "slot-20260324-cycle1-standard#18",
      route_id: "ROUTE-20260324-18",
      service_date: "2026-03-24",
      route_slot_class: "standard",
      station_code: "DVC4",
      service_area: "Metro core",
      shift_start: "10:15",
      shift_end: "16:15",
      projected_minutes: 360,
      required_skill: "standard_delivery",
      vehicle_type: "cargo_van"
    };
    const coverageTargetB = {
      target_id: `${routeDemandArtifactVersionId}:2026-03-24:2`,
      route_slot_id: "slot-20260324-cycle1-standard#19",
      route_id: "ROUTE-20260324-19",
      service_date: "2026-03-24",
      route_slot_class: "standard",
      station_code: "DVC4",
      service_area: "Metro core",
      shift_start: "10:30",
      shift_end: "16:30",
      projected_minutes: 360,
      required_skill: "standard_delivery",
      vehicle_type: "cargo_van"
    };
    server.use(
      http.get("*/api/v1/workpages/workflow-runs/:workflowRunId/schedule-v0", ({ params }) => {
        const payload = structuredClone(scheduleRunWorkpageStateSnapshot.workpage_state) as Record<
          string,
          any
        >;
        payload.run_context.workflow_run_id = String(params.workflowRunId);
        payload.route_demand_coverage_context = {
          workflow_run_id: workflowRunId,
          schedule_artifact_version_id: draftArtifactVersionId,
          route_demand_artifact_version_id: routeDemandArtifactVersionId,
          coverage_candidates_path: coverageCandidatesPath,
          coverage_apply_path:
            `/api/v1/workpages/workflow-runs/${workflowRunId}/schedule-v0/artifacts/` +
            `${draftArtifactVersionId}/route-demand-coverage`,
          service_dates: ["2026-03-24"],
          added_route_count: 2,
          deltas: [
            {
              service_date: "2026-03-24",
              previous_planned_route_count: 20,
              planned_route_count: 22,
              delta: 2
            }
          ]
        };
        payload.actions = payload.actions.map((action: Record<string, unknown>) =>
          action.kind === "open_latest_draft"
            ? {
                ...action,
                state: "available",
                artifact_version_id: draftArtifactVersionId,
                route: `/runs/${workflowRunId}/workpages/schedule-v0/artifacts/${draftArtifactVersionId}`
              }
            : action
        );
        return HttpResponse.json(payload);
      }),
      http.post(`*${coverageCandidatesPath}`, () =>
        HttpResponse.json({
          status: "ok",
          route_demand_coverage_recommendations: {
            workflow_run_id: workflowRunId,
            artifact_version_id: draftArtifactVersionId,
            route_demand_artifact_version_id: routeDemandArtifactVersionId,
            dependency_state: "aligned",
            dependencies: [],
            added_route_count: 2,
            target_count: 2,
            max_candidates: 8,
            targets: [coverageTargetA, coverageTargetB],
            candidate_groups: [
              {
                target: coverageTargetA,
                candidate_count: 1,
                pass_candidate_count: 1,
                candidates: [
                  buildCoverageCandidate(
                    coverageTargetA,
                    1,
                    "A2TU4ZRI65E1H8",
                    "Abhiraj Singh"
                  )
                ]
              },
              {
                target: coverageTargetB,
                candidate_count: 1,
                pass_candidate_count: 1,
                candidates: [
                  buildCoverageCandidate(coverageTargetB, 1, "A3M38Z4NGI9OR3", "Akash")
                ]
              }
            ],
            selected_defaults: [],
            diagnostic_reason: null
          }
        })
      )
    );
    setFrontendOperatorContext();
    window.history.pushState({}, "", "/runs/wr-weekly-001/workpages/schedule-v0");
    render(<App />);

    const callout = await screen.findByTestId("schedule-route-demand-recovery-callout");
    expect(callout).toHaveTextContent("2 added routes are still uncovered");
    expect(within(callout).getByRole("link", { name: "Open editable draft" })).toHaveAttribute(
      "href",
      `/runs/${workflowRunId}/workpages/schedule-v0/artifacts/${draftArtifactVersionId}`
    );

    const heatmap = heatmapSection(await screen.findByTestId("schedule-workpage-page"));
    const selectedHeader = heatmap.querySelector(
      ".schedule-heatmap__date-header--selected"
    ) as HTMLElement | null;
    expect(selectedHeader).not.toBeNull();
    expect(selectedHeader).toHaveClass("schedule-heatmap__date-header--uncovered");
    expectHeatmapSummaryRailLabels(await screen.findByTestId("schedule-workpage-page"), {
      includesGap: true
    });
    expect(within(selectedHeader as HTMLElement).getByText("2")).toBeInTheDocument();
  });

  it("shows an error state and retries the canonical run-backed query", async () => {
    const user = userEvent.setup();
    let attempts = 0;
    server.use(
      http.get("*/api/v1/workpages/workflow-runs/:workflowRunId/schedule-v0", () => {
        attempts += 1;
        if (attempts <= 2) {
          return HttpResponse.json(
            {
              status: "error",
              error: {
                code: "workpage_unavailable",
                message: "schedule run unavailable"
              }
            },
            { status: 503 }
          );
        }
        return HttpResponse.json(scheduleRunWorkpageStateSnapshot.workpage_state);
      })
    );
    setFrontendOperatorContext();
    window.history.pushState({}, "", "/runs/wr-weekly-001/workpages/schedule-v0");
    render(<App />);

    expect(
      await screen.findByText("Schedule workpage failed to load", {}, { timeout: 4000 })
    ).toBeInTheDocument();
    expect(screen.getByText(/workpage_unavailable: schedule run unavailable/i)).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "Retry" }));

    expect(await screen.findByTestId("schedule-workpage-page")).toBeInTheDocument();
  });

  it(
    "renders the canonical run-backed schedule page without landing hero CTAs",
    async () => {
      let responseCount = 0;
      server.use(
        http.get("*/api/v1/workpages/workflow-runs/:workflowRunId/schedule-v0", ({ params }) => {
          responseCount += 1;
          const payload = structuredClone(scheduleRunWorkpageStateSnapshot.workpage_state) as Record<
            string,
            any
          >;
          payload.freshness.generated_at =
            responseCount === 1 ? "2026-03-25T08:10:00Z" : "2026-03-25T08:10:30Z";
          payload.run_context.workflow_run_id = String(params.workflowRunId);
          payload.run_context.activation_key = `snapshot:${String(params.workflowRunId)}:weekly`;
          payload.actions = [
            {
              action_id: "workpage.schedule-v0.open_latest_draft",
              artifact_version_id: "av-schedule-artifact-001",
              kind: "open_latest_draft",
              label: "Open schedule draft",
              route: "/runs/wr-weekly-001/workpages/schedule-v0/artifacts/av-schedule-artifact-001",
              state: "available",
              workpage_kind: "schedule-v0"
            },
            {
              action_id: "workpage.route-demand-v0.open_latest",
              artifact_version_id: "av-route-demand-artifact-001",
              kind: "open_latest",
              label: "Open route demand",
              route: "/runs/wr-weekly-001/workpages/route-demand-v0/artifacts/av-route-demand-artifact-001",
              state: "available",
              workpage_kind: "route-demand-v0"
            },
            {
              action_id: "workpage.driver-preferences-v0.create_snapshot",
              action_ref: {
                action_id: "workpage.driver-preferences-v0.create_snapshot",
                artifact_version_id: null,
                subject: null,
                workflow_run_id: "wr-weekly-001",
                workpage_kind: "driver-preferences-v0"
              },
              artifact_version_id: null,
              create_path: "/api/v1/workpages/workflow-runs/wr-weekly-001/driver-preferences-v0/snapshots",
              kind: "create_snapshot",
              label: "Create preferences snapshot",
              route: null,
              state: "available",
              workpage_kind: "driver-preferences-v0"
            }
          ];
          return HttpResponse.json(payload);
        })
      );
      setFrontendOperatorContext();
      window.history.pushState({}, "", "/runs/wr-weekly-001/workpages/schedule-v0");
      render(<App />);

      const page = await screen.findByTestId("schedule-workpage-page");
      expect(page.querySelector(".workpage-page__hero")).toBeNull();
      expect(within(page).queryByRole("heading", { name: "Editable draft available" })).not.toBeInTheDocument();
      expect(within(page).queryByRole("link", { name: "Open editable draft" })).not.toBeInTheDocument();
      expect(within(page).queryByRole("link", { name: "Open route demand" })).not.toBeInTheDocument();
      expect(within(page).queryByRole("button", { name: "Create preferences snapshot" })).not.toBeInTheDocument();
      expect(screen.queryByText("Scenario sick calls")).not.toBeInTheDocument();
      expect(screen.queryByRole("textbox", { name: /Planner note/i })).not.toBeInTheDocument();
      expect(within(page).queryByRole("heading", { name: "Capacity bar" })).not.toBeInTheDocument();
      expect(within(page).queryByRole("heading", { name: "Draft lineage" })).not.toBeInTheDocument();

    },
    60000
  );

  it(
    "opens the weekly schedule quick-edit modal from the top chrome action",
    async () => {
      const user = userEvent.setup();
      setFrontendOperatorContext();
      window.history.pushState({}, "", "/runs/wr-weekly-001/workpages/schedule-v0");
      render(<App />);

      expect(await screen.findByTestId("schedule-workpage-page")).toBeInTheDocument();
      expect(
        screen.queryByRole("heading", { name: "Editable draft available" })
      ).not.toBeInTheDocument();

      await waitFor(() => {
        expect(screen.getByRole("button", { name: "Edit weekly schedule" })).toBeEnabled();
      });
      await user.click(screen.getByRole("button", { name: "Edit weekly schedule" }));

      const dialog = await screen.findByRole("dialog", { name: "Edit Weekly Schedule" });
      expect(dialog).toHaveClass("schedule-quick-edit-modal");
      expect(
        within(dialog).getByText("No editable schedule draft is available for this weekly run yet.")
      ).toBeInTheDocument();
      expect(window.location.pathname).toBe("/runs/wr-weekly-001/workpages/schedule-v0");
    },
    30000
  );

  it("shows current and next week choices and opens the next-week draft from the shell action", async () => {
    const user = userEvent.setup();
    let currentRouteDemandRequests = 0;
    let secondaryScheduleRequests = 0;
    let secondaryRouteDemandRequests = 0;
    setTestCurrentServiceDate("2026-05-26");
    vi.spyOn(workpagesRepository, "scheduleArtifactPreviousWeekReality").mockResolvedValue(
      buildFutureRollingRealityContract("wr-weekly-002", "av-schedule-artifact-002") as never
    );
    server.use(
      http.get("*/api/v1/stories/logistics-three-workflow", () =>
        HttpResponse.json({
          status: "ok",
          command: "api.stories.logistics_three_workflow",
          story: {
            story_id: "logistics_three_workflow_demo.v1",
            family: {
              family_id: "logistics_ops_family.v1",
              family_version: 1,
              contract_version: 1
            },
            partitions: {
              planning_week_id: "PW-2026-W10",
              service_date_ids: ["SD-2026-03-06"]
            },
            family_graph: {
              family_id: "logistics_ops_family.v1",
              family_version: 1,
              modules: [
                {
                  module_id: "dispatch_reporting",
                  workflow_id: "dispatch_reporting.v1",
                  partition_kind: "ServiceDateID",
                  activation_policy: "manual_or_event",
                  status: "active",
                  node_kind: "module",
                  drilldown_kind: "workflow_run",
                  drilldown_refs: [
                    {
                      workflow_run_id: "wr-report-001",
                      workflow_id: "dispatch_reporting.v1",
                      partition_key: "SD-2026-03-06"
                    }
                  ],
                  artifact_refs: [],
                  selection_summary: "1 linked run, 0 downloadable artifacts"
                },
                {
                  module_id: "weekly_schedule_planning",
                  workflow_id: "weekly_schedule_planning.v1",
                  partition_kind: "PlanningWeekID",
                  activation_policy: "manual_or_event",
                  status: "active",
                  node_kind: "module",
                  drilldown_kind: "run_group",
                  drilldown_refs: [
                    {
                      workflow_run_id: "wr-weekly-001",
                      workflow_id: "weekly_schedule_planning.v1",
                      partition_key: "PW-2026-W10"
                    },
                    {
                      workflow_run_id: "wr-weekly-002",
                      workflow_id: "weekly_schedule_planning.v1",
                      partition_key: "PW-2026-W14"
                    }
                  ],
                  artifact_refs: [],
                  selection_summary: "2 linked runs, 0 downloadable artifacts"
                },
                {
                  module_id: "live_dispatch",
                  workflow_id: "live_dispatch.v1",
                  partition_kind: "ServiceDateID",
                  activation_policy: "event_driven",
                  status: "ready",
                  node_kind: "module",
                  drilldown_kind: "none",
                  drilldown_refs: [],
                  artifact_refs: [],
                  selection_summary: "0 linked runs, prepare service day after weekly publish"
                }
              ],
              edges: [
                {
                  edge_id: "reporting_actuals_to_future_planning",
                  source_module_id: "dispatch_reporting",
                  target_module_id: "weekly_schedule_planning",
                  handoff_mode: "notify_only"
                },
                {
                  edge_id: "weekly_seed_to_live_dispatch",
                  source_module_id: "weekly_schedule_planning",
                  target_module_id: "live_dispatch",
                  handoff_mode: "artifact_handoff"
                }
              ]
            },
            linked_workflow_runs: {
              weekly_schedule_planning: [
                {
                  workflow_run_id: "wr-weekly-001",
                  workflow_id: "weekly_schedule_planning.v1",
                  workflow_version: "v1",
                  tenant_id: "tenant-a",
                  domain_id: "domain-x",
                  partition_key: "PW-2026-W10",
                  logical_date: "PW-2026-W10",
                  activation_key: "weekly_schedule_planning.v1:PW-2026-W10",
                  state: "OPEN",
                  active_issue_count: 1,
                  created_at: "2026-03-25T08:00:00Z",
                  updated_at: "2026-03-25T08:00:00Z"
                },
                {
                  workflow_run_id: "wr-weekly-002",
                  workflow_id: "weekly_schedule_planning.v1",
                  workflow_version: "v1",
                  tenant_id: "tenant-a",
                  domain_id: "domain-x",
                  partition_key: "PW-2026-W14",
                  logical_date: "PW-2026-W14",
                  activation_key: "weekly_schedule_planning.v1:PW-2026-W14",
                  state: "OPEN",
                  active_issue_count: 0,
                  created_at: "2026-03-25T08:00:00Z",
                  updated_at: "2026-03-25T08:00:00Z"
                }
              ],
              live_dispatch: [],
              dispatch_reporting: [],
              summary: {
                weekly_schedule_planning_count: 2,
                live_dispatch_count: 0,
                dispatch_reporting_count: 0
              }
            },
            handoff_activity: {
              edges: [],
              summary: {
                edge_execution_count: 0,
                coherence_failed_count: 0
              }
            },
            board: {
              lanes: [],
              work_items: [],
              page: { limit: 100, offset: 0 },
              summary: {
                work_item_count: 0,
                human_task_count: 0,
                approval_count: 0,
                flag_count: 0,
                primary_actionable_count: 0,
                workflow_item_counts: {}
              }
            },
            official_outputs: {
              pointers: [],
              pointer_outputs: [],
              official_output_artifacts: [],
              coherence: {},
              summary: {
                pointer_count: 0,
                pointer_output_count: 0,
                official_output_artifact_count: 0,
                artifact_kind_counts: {}
              }
            },
            freshness: {
              latest_event_sequence: null,
              latest_event_recorded_at: "2026-03-25T08:00:00Z",
              max_workflow_run_updated_at: "2026-03-25T08:00:00Z",
              generated_at: "2026-03-25T08:00:00Z"
            },
            coherence: {
              official_outputs: {},
              handoff_edges: []
            }
          }
        })
      ),
      http.get("*/api/v1/workpages/workflow-runs/wr-weekly-002/schedule-v0", () => {
        secondaryScheduleRequests += 1;
        const payload = structuredClone(scheduleRunWorkpageStateSnapshot.workpage_state) as Record<
          string,
          any
        >;
        payload.run_context.workflow_run_id = "wr-weekly-002";
        payload.actions = [
          {
            action_id: "workpage.schedule-v0.open_latest_draft",
            artifact_version_id: "av-schedule-artifact-002",
            kind: "open_latest_draft",
            label: "Open schedule draft",
            route: "/runs/wr-weekly-002/workpages/schedule-v0/artifacts/av-schedule-artifact-002",
            state: "available",
            workpage_kind: "schedule-v0"
          }
        ];
        return HttpResponse.json(payload);
      }),
      http.get("*/api/v1/workpages/workflow-runs/wr-weekly-002/route-demand-v0", () => {
        secondaryRouteDemandRequests += 1;
        const payload = structuredClone(routeDemandRunWorkpageStateSnapshot.workpage_state) as Record<
          string,
          any
        >;
        payload.run_context.workflow_run_id = "wr-weekly-002";
        const futureServiceDates = [
          "2026-03-29",
          "2026-03-30",
          "2026-03-31",
          "2026-04-01",
          "2026-04-02",
          "2026-04-03",
          "2026-04-04"
        ];
        payload.calculations.day_cards = payload.calculations.day_cards.map(
          (card: Record<string, unknown>, index: number) => ({
            ...card,
            service_date: futureServiceDates[index] ?? card.service_date,
            weekday_label:
              ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"][index] ?? card.weekday_label
          })
        );
        return HttpResponse.json(payload);
      }),
      http.get("*/api/v1/workpages/workflow-runs/wr-weekly-001/route-demand-v0", () => {
        currentRouteDemandRequests += 1;
        const payload = structuredClone(routeDemandRunWorkpageStateSnapshot.workpage_state) as Record<
          string,
          any
        >;
        payload.run_context.workflow_run_id = "wr-weekly-001";
        return HttpResponse.json(payload);
      }),
      http.get(
        "*/api/v1/workpages/workflow-runs/wr-weekly-002/schedule-v0/artifacts/av-schedule-artifact-002",
        () => {
          return HttpResponse.json(
            buildFutureScheduleArtifactPayload("av-schedule-artifact-002", "wr-weekly-002")
          );
        }
      )
    );
    setFrontendOperatorContext();
    window.history.pushState({}, "", "/runs/wr-weekly-001/workpages/schedule-v0");
    render(<App />);

    expect(await screen.findByTestId("schedule-workpage-page")).toBeInTheDocument();
    expect(currentRouteDemandRequests).toBe(0);
    expect(secondaryScheduleRequests).toBe(0);
    expect(secondaryRouteDemandRequests).toBe(0);
    await waitFor(() => {
      expect(screen.getByRole("button", { name: "Edit weekly schedule" })).toBeEnabled();
    });
    await user.click(screen.getByRole("button", { name: "Edit weekly schedule" }));

    const chooser = await screen.findByRole("dialog", { name: "Choose weekly schedule" });
    expect(within(chooser).getByRole("button", { name: /Current week/i })).toBeInTheDocument();
    expect(within(chooser).getByText("2026-03-22 to 2026-03-28")).toBeInTheDocument();
    expect(within(chooser).getByRole("button", { name: /Next week/i })).toBeInTheDocument();
    expect(within(chooser).getByText("2026-03-29 to 2026-04-04")).toBeInTheDocument();
    expect(currentRouteDemandRequests).toBe(1);
    expect(secondaryScheduleRequests).toBe(1);
    expect(secondaryRouteDemandRequests).toBe(1);

    await waitFor(() => {
      expect(within(chooser).getByRole("button", { name: /Next week/i })).toBeEnabled();
    });
    await user.click(within(chooser).getByRole("button", { name: /Next week/i }));

    await waitFor(() => {
      expect(window.location.pathname).toBe("/runs/wr-weekly-002/workpages/schedule-v0");
    });
    const dialog = await screen.findByRole("dialog", { name: "Edit Weekly Schedule" });
    const heatmap = heatmapSection(dialog);
    const futureSundayButton = within(heatmap)
      .getAllByRole("button")
      .find((button) => (button.getAttribute("aria-label") ?? "").includes("2026-03-29: assigned route"));
    const futureTuesdayButton = within(heatmap)
      .getAllByRole("button")
      .find((button) => (button.getAttribute("aria-label") ?? "").includes("2026-03-31: assigned route"));
    expect(within(heatmap).getAllByText("Read-only prior week")).toHaveLength(7);
    expect(
      within(heatmap).queryByText("2026-03-29: dispatch report", {
        exact: false
      })
    ).not.toBeInTheDocument();
    expect(
      within(heatmap).queryByText("2026-03-30: dispatch report", {
        exact: false
      })
    ).not.toBeInTheDocument();
    expect(futureSundayButton).toBeDefined();
    expect(futureSundayButton).toHaveAttribute("aria-disabled", "false");
    expect(futureTuesdayButton).toBeDefined();
    expect(futureTuesdayButton).toHaveAttribute("aria-disabled", "false");
    expect(
      heatmap.querySelector(".schedule-heatmap__date-header--selected")
    ).toHaveTextContent("2026-03-31");
  }, 30000);

  it("shows next week as unavailable in the chooser when no editable draft exists yet", async () => {
    const user = userEvent.setup();
    server.use(
      http.get("*/api/v1/stories/logistics-three-workflow", () =>
        HttpResponse.json({
          status: "ok",
          command: "api.stories.logistics_three_workflow",
          story: {
            story_id: "logistics_three_workflow_demo.v1",
            family: {
              family_id: "logistics_ops_family.v1",
              family_version: 1,
              contract_version: 1
            },
            partitions: {
              planning_week_id: "PW-2026-W10",
              service_date_ids: ["SD-2026-03-06"]
            },
            family_graph: {
              family_id: "logistics_ops_family.v1",
              family_version: 1,
              modules: [
                {
                  module_id: "dispatch_reporting",
                  workflow_id: "dispatch_reporting.v1",
                  partition_kind: "ServiceDateID",
                  activation_policy: "manual_or_event",
                  status: "active",
                  node_kind: "module",
                  drilldown_kind: "workflow_run",
                  drilldown_refs: [],
                  artifact_refs: [],
                  selection_summary: ""
                },
                {
                  module_id: "weekly_schedule_planning",
                  workflow_id: "weekly_schedule_planning.v1",
                  partition_kind: "PlanningWeekID",
                  activation_policy: "manual_or_event",
                  status: "active",
                  node_kind: "module",
                  drilldown_kind: "run_group",
                  drilldown_refs: [
                    {
                      workflow_run_id: "wr-weekly-001",
                      workflow_id: "weekly_schedule_planning.v1",
                      partition_key: "PW-2026-W10"
                    },
                    {
                      workflow_run_id: "wr-weekly-002",
                      workflow_id: "weekly_schedule_planning.v1",
                      partition_key: "PW-2026-W14"
                    }
                  ],
                  artifact_refs: [],
                  selection_summary: "2 linked runs"
                },
                {
                  module_id: "live_dispatch",
                  workflow_id: "live_dispatch.v1",
                  partition_kind: "ServiceDateID",
                  activation_policy: "event_driven",
                  status: "ready",
                  node_kind: "module",
                  drilldown_kind: "none",
                  drilldown_refs: [],
                  artifact_refs: [],
                  selection_summary: ""
                }
              ],
              edges: []
            },
            linked_workflow_runs: {
              weekly_schedule_planning: [
                {
                  workflow_run_id: "wr-weekly-001",
                  workflow_id: "weekly_schedule_planning.v1",
                  workflow_version: "v1",
                  tenant_id: "tenant-a",
                  domain_id: "domain-x",
                  partition_key: "PW-2026-W10",
                  logical_date: "PW-2026-W10",
                  activation_key: "weekly_schedule_planning.v1:PW-2026-W10",
                  state: "OPEN",
                  active_issue_count: 1,
                  created_at: "2026-03-25T08:00:00Z",
                  updated_at: "2026-03-25T08:00:00Z"
                },
                {
                  workflow_run_id: "wr-weekly-002",
                  workflow_id: "weekly_schedule_planning.v1",
                  workflow_version: "v1",
                  tenant_id: "tenant-a",
                  domain_id: "domain-x",
                  partition_key: "PW-2026-W14",
                  logical_date: "PW-2026-W14",
                  activation_key: "weekly_schedule_planning.v1:PW-2026-W14",
                  state: "OPEN",
                  active_issue_count: 0,
                  created_at: "2026-03-25T08:00:00Z",
                  updated_at: "2026-03-25T08:00:00Z"
                }
              ],
              live_dispatch: [],
              dispatch_reporting: [],
              summary: {
                weekly_schedule_planning_count: 2,
                live_dispatch_count: 0,
                dispatch_reporting_count: 0
              }
            },
            handoff_activity: { edges: [], summary: { edge_execution_count: 0, coherence_failed_count: 0 } },
            board: {
              lanes: [],
              work_items: [],
              page: { limit: 100, offset: 0 },
              summary: {
                work_item_count: 0,
                human_task_count: 0,
                approval_count: 0,
                flag_count: 0,
                primary_actionable_count: 0,
                workflow_item_counts: {}
              }
            },
            official_outputs: {
              pointers: [],
              pointer_outputs: [],
              official_output_artifacts: [],
              coherence: {},
              summary: {
                pointer_count: 0,
                pointer_output_count: 0,
                official_output_artifact_count: 0,
                artifact_kind_counts: {}
              }
            },
            freshness: {
              latest_event_sequence: null,
              latest_event_recorded_at: "2026-03-25T08:00:00Z",
              max_workflow_run_updated_at: "2026-03-25T08:00:00Z",
              generated_at: "2026-03-25T08:00:00Z"
            },
            coherence: {
              official_outputs: {},
              handoff_edges: []
            }
          }
        })
      ),
      http.get("*/api/v1/workpages/workflow-runs/wr-weekly-002/schedule-v0", () => {
        const payload = structuredClone(scheduleRunWorkpageStateSnapshot.workpage_state) as Record<
          string,
          any
        >;
        payload.run_context.workflow_run_id = "wr-weekly-002";
        payload.actions = payload.actions.filter(
          (action: Record<string, unknown>) => action.kind !== "open_latest_draft"
        );
        payload.artifact_state.latest_artifact_version_id = null;
        return HttpResponse.json(payload);
      }),
      http.get("*/api/v1/workpages/workflow-runs/wr-weekly-002/route-demand-v0", () => {
        const payload = structuredClone(routeDemandRunWorkpageStateSnapshot.workpage_state) as Record<
          string,
          any
        >;
        payload.run_context.workflow_run_id = "wr-weekly-002";
        payload.calculations.day_cards = payload.calculations.day_cards.map(
          (card: Record<string, unknown>, index: number) => ({
            ...card,
            service_date:
              [
                "2026-03-29",
                "2026-03-30",
                "2026-03-31",
                "2026-04-01",
                "2026-04-02",
                "2026-04-03",
                "2026-04-04"
              ][index] ?? card.service_date
          })
        );
        return HttpResponse.json(payload);
      })
    );
    setFrontendOperatorContext();
    window.history.pushState({}, "", "/runs/wr-weekly-001/workpages/schedule-v0");
    render(<App />);

    expect(await screen.findByTestId("schedule-workpage-page")).toBeInTheDocument();
    await waitFor(() => {
      expect(screen.getByRole("button", { name: "Edit weekly schedule" })).toBeEnabled();
    });
    await user.click(screen.getByRole("button", { name: "Edit weekly schedule" }));

    const chooser = await screen.findByRole("dialog", { name: "Choose weekly schedule" });
    const nextWeekButton = within(chooser).getByRole("button", { name: /Next week/i });
    expect(nextWeekButton).toBeDisabled();
    expect(within(chooser).getAllByText("No draft yet")).toHaveLength(2);
  }, 30000);

  it(
    "opens route-demand editing from the top chrome without client-derived routing",
    async () => {
      const user = userEvent.setup();
      let routeDemandRequests = 0;
      server.use(
        http.get("*/api/v1/workpages/workflow-runs/wr-weekly-001/route-demand-v0", () => {
          routeDemandRequests += 1;
          const payload = structuredClone(routeDemandRunWorkpageStateSnapshot.workpage_state) as any;
          payload.run_context.workflow_run_id = "wr-weekly-001";
          payload.actions = payload.actions.map((action: Record<string, unknown>) =>
            action.kind === "open_latest"
              ? {
                  ...action,
                  artifact_version_id: "av-route-demand-artifact-001",
                  route:
                    "/runs/wr-weekly-001/workpages/route-demand-v0/artifacts/av-route-demand-artifact-001",
                  action_ref: {
                    ...(action.action_ref as Record<string, unknown>),
                    artifact_version_id: "av-route-demand-artifact-001",
                    workflow_run_id: "wr-weekly-001"
                  }
                }
              : action
          );
          return HttpResponse.json(payload);
        })
      );
      server.use(
        http.get(
          "*/api/v1/workpages/workflow-runs/wr-weekly-001/route-demand-v0/artifacts/av-route-demand-artifact-001",
          () => {
            const payload = structuredClone(routeDemandArtifactStateSnapshot.workpage_state) as any;
            payload.artifact_context.workflow_run_id = "wr-weekly-001";
            payload.artifact_context.artifact_version_id = "av-route-demand-artifact-001";
            payload.artifact_context.latest_in_chain_artifact_version_id =
              "av-route-demand-artifact-001";
            payload.freshness.source_version = "av-route-demand-artifact-001";
            payload.workpage.source_artifact_version_id =
              "av-route-demand-artifact-001";
            payload.source.source_artifact_version_id =
              "av-route-demand-artifact-001";
            return HttpResponse.json(payload);
          }
        )
      );
      setFrontendOperatorContext();
      window.history.pushState({}, "", "/runs/wr-weekly-001/workpages/schedule-v0");
      render(<App />);

      expect(await screen.findByTestId("schedule-workpage-page")).toBeInTheDocument();
      expect(routeDemandRequests).toBe(0);
      await waitFor(() => {
        expect(screen.getByRole("button", { name: "Edit route demand" })).toBeEnabled();
      });
      await user.click(screen.getByRole("button", { name: "Edit route demand" }));

      const dialog = await screen.findByRole("dialog", { name: "Edit route demand" });
      expect(await within(dialog).findByTestId("route-demand-quick-edit-editor")).toBeInTheDocument();
      expect(routeDemandRequests).toBe(1);
      expect(window.location.pathname).toBe("/runs/wr-weekly-001/workpages/schedule-v0");
    },
    30000
  );

  it(
    "opens driver preferences from the top chrome without inline preference pills",
    async () => {
      const user = userEvent.setup();
      let driverPreferencesRequests = 0;
      server.use(
        http.get(
          "*/api/v1/workpages/workflow-runs/wr-weekly-001/driver-preferences-v0",
          () => {
            driverPreferencesRequests += 1;
            const payload = structuredClone(
              driverPreferencesRunWorkpageStateSnapshot.workpage_state
            ) as Record<string, any>;
            payload.run_context.workflow_run_id = "wr-weekly-001";
            return HttpResponse.json(payload);
          }
        )
      );
      setFrontendOperatorContext();
      window.history.pushState({}, "", "/runs/wr-weekly-001/workpages/schedule-v0");
      render(<App />);

      const page = await screen.findByTestId("schedule-workpage-page");
      expect(within(heatmapSection(page)).queryByText("Pref Unset")).not.toBeInTheDocument();
      expect(within(heatmapSection(page)).getByText("Abhiraj Singh")).toBeInTheDocument();
      expectHeatmapPreferenceBars(page);
      expect(driverPreferencesRequests).toBe(0);

      await waitFor(() => {
        expect(screen.getByRole("button", { name: "Drivers" })).toBeEnabled();
      });
      await user.click(screen.getByRole("button", { name: "Drivers" }));

      const dialog = await screen.findByRole("dialog", { name: "Drivers" });
      expect(
        await within(dialog).findByRole("heading", {
          name: "Create the first preferences snapshot"
        })
      ).toBeInTheDocument();
      expect(driverPreferencesRequests).toBe(1);
      expect(window.location.pathname).toBe("/runs/wr-weekly-001/workpages/schedule-v0");
    },
    25000
  );
});
