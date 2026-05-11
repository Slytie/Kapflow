import { act, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { HttpResponse, http } from "msw";

import appCss from "@/app/app.css?raw";
import scheduleArtifactStateSnapshot from "@fixtures/workpage_schedule_v0_artifact_state.json";
import { App } from "@/app/App";
import {
  SCHEDULE_CHECKS_SUMMARY,
  SCHEDULE_CHECK_ITEM_SUMMARIES,
  SCHEDULE_DEPENDENCY_ITEM_SUMMARIES,
  SCHEDULE_DEPENDENCY_STATUS_SUMMARY
} from "@/components/workpages/ScheduleWorkpageSurface";
import { mutationLog, resetApiState } from "@/test/api/handlers";
import { server } from "@/test/api/server";
import {
  expectHeatmapHeaderStatusGroups,
  expectHeatmapPreferenceBars,
  expectSelectedDateHeaderStats,
  scheduleHeatmapSectionIn as heatmapSectionIn
} from "./logisticsScheduleTestHelpers";

function escapeRegExp(value: string): string {
  return value.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
}

function heatmapSection(): HTMLElement {
  const section = screen.getByRole("heading", { name: "Planned schedule heatmap" }).closest("section");
  if (!section) {
    throw new Error("Heatmap section not found");
  }
  return section as HTMLElement;
}

function heatmapButton(
  section: HTMLElement,
  predicate: (label: string) => boolean
): HTMLButtonElement {
  const button = within(section)
    .getAllByRole("button")
    .find((candidate) => predicate(candidate.getAttribute("aria-label") ?? ""));
  if (!button) {
    throw new Error("Matching heatmap cell not found");
  }
  return button as HTMLButtonElement;
}

function personNameFromLabel(label: string): string {
  return label.split(" on ")[0] ?? label;
}

function driverHeatmapRow(section: HTMLElement, driverName: string): HTMLElement {
  const row = within(section).getByText(driverName).closest("tr");
  if (!row) {
    throw new Error(`Heatmap row not found for ${driverName}`);
  }
  return row as HTMLElement;
}

function buildScheduleArtifactPayload(
  artifactVersionId: string,
  workflowRunId = "wr-weekly-001",
  customize?: (payload: Record<string, any>) => void
): Record<string, unknown> {
  const payload = structuredClone(scheduleArtifactStateSnapshot.workpage_state) as Record<string, any>;
  payload.freshness.generated_at = "2026-03-25T09:15:00Z";
  payload.freshness.source_version = artifactVersionId;
  payload.source.source_artifact_version_id = artifactVersionId;
  payload.artifact_context.artifact_version_id = artifactVersionId;
  payload.artifact_context.workflow_run_id = workflowRunId;
  payload.artifact_context.download_path = `/api/v1/artifacts/${artifactVersionId}/download.bin`;
  payload.artifact_context.latest_in_chain_artifact_version_id = artifactVersionId;
  payload.artifact_context.supersedes_artifact_version_id = null;
  payload.artifact_context.superseded_by_artifact_version_id = null;
  payload.workpage.source_artifact_version_id = artifactVersionId;
  payload.artifact_state.current_artifact_version_id = artifactVersionId;
  payload.artifact_state.latest_artifact_version_id = artifactVersionId;
  payload.artifact_history = {
    current_artifact_version_id: artifactVersionId,
    latest_artifact_version_id: artifactVersionId,
    previous_artifact_version_id: null,
    next_artifact_version_id: null,
    entries: [
      {
        artifact_version_id: artifactVersionId,
        workflow_run_id: workflowRunId,
        artifact_kind: "planning.draft_weekly_schedule.workbook",
        created_at: "2026-03-25T09:15:00Z",
        lineage_note: "Initial Stage04 draft weekly schedule artifact.",
        supersedes_artifact_version_id: null,
        route: `/runs/${workflowRunId}/workpages/schedule-v0/artifacts/${artifactVersionId}`
      }
    ]
  };
  payload.draft_lineage.current_artifact_version_id = artifactVersionId;
  payload.draft_lineage.latest_artifact_version_id = artifactVersionId;
  payload.draft_lineage.previous_artifact_version_id = null;
  payload.draft_lineage.recent_versions = [
    {
      artifact_version_id: artifactVersionId,
      supersedes_artifact_version_id: null
    }
  ];
  payload.actions = payload.actions.map((action: Record<string, unknown>) => {
    if (action.kind === "preview_recalc") {
      return {
        ...action,
        artifact_version_id: artifactVersionId,
        preview_path: `/api/v1/workpages/workflow-runs/${workflowRunId}/schedule-v0/artifacts/${artifactVersionId}/preview`,
        action_ref: {
          action_id: String(action.action_id),
          workpage_kind: "schedule-v0",
          workflow_run_id: workflowRunId,
          artifact_version_id: artifactVersionId,
          subject: null
        }
      };
    }
    if (action.kind === "submit_artifact") {
      return {
        ...action,
        artifact_version_id: artifactVersionId,
        submit_path: `/api/v1/workpages/workflow-runs/${workflowRunId}/schedule-v0/artifacts/${artifactVersionId}/submit`,
        action_ref: {
          action_id: String(action.action_id),
          workpage_kind: "schedule-v0",
          workflow_run_id: workflowRunId,
          artifact_version_id: artifactVersionId,
          subject: null
        }
      };
    }
    return action;
  });
  const history = payload.workpage.sections.find(
    (section: Record<string, unknown>) => section.kind === "history_stub"
  ) as { entries: Array<{ label: string; value: string }> };
  history.entries = [
    { label: "Current artifact version", value: artifactVersionId },
    { label: "Supersedes", value: "Initial Stage04 draft" },
    { label: "Latest draft in chain", value: artifactVersionId }
  ];
  customize?.(payload);
  return payload;
}

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
    reserve_route_slot_id: recommendationRank === 1 ? "oncall-20260328#01" : null,
    reserve_route_id: recommendationRank === 1 ? "ON_CALL" : null,
    assignment_action: recommendationRank === 1 ? "promote_reserve" : "assign_open_driver",
    evaluation_kind: recommendationRank === 1 ? "reserve_promotion" : "best_fit",
    ...overrides
  };
}

describe("LogisticsScheduleArtifactWorkpagePage", () => {
  it(
    "opens Edit weekly schedule as a modal, saves a draft, and stays on the background page",
    async () => {
      const user = userEvent.setup();
      window.history.pushState({}, "", "/runs/wr-weekly-001/workpages/schedule-v0");
      render(<App />);

      expect(await screen.findByTestId("schedule-workpage-page")).toBeInTheDocument();
      await user.click(await screen.findByRole("button", { name: "Edit weekly schedule" }));

      const dialog = await screen.findByRole("dialog", { name: "Edit Weekly Schedule" });
      expect(dialog).toHaveClass("schedule-quick-edit-modal");
      const editor = await within(dialog).findByTestId("schedule-quick-edit-editor");
      expect(within(dialog).queryByTestId("route-demand-coverage-panel")).not.toBeInTheDocument();
      expect(within(editor).getByRole("heading", { name: "Weekly Schedule Draft" })).toBeInTheDocument();
      expect(within(editor).queryByText("Weekly Schedule Draft Artifact")).not.toBeInTheDocument();
      expect(
        within(editor).queryByText(
          "Live preview recalculates in place. Save creates the next immutable draft in this weekly lineage."
        )
      ).not.toBeInTheDocument();
      expect(
        within(editor).queryByText(
          "A bounded Stage04 draft workbook edit lane with live backend preview and explicit save into a new immutable draft version."
        )
      ).not.toBeInTheDocument();
      expect(within(editor).queryByText(/^Week /)).not.toBeInTheDocument();
      expect(within(editor).queryByText(/^Artifact /)).not.toBeInTheDocument();
      expect(within(editor).queryByText("155 assignments")).not.toBeInTheDocument();
      expect(within(editor).queryByText("<bundle_id:10>")).not.toBeInTheDocument();
      expect(within(editor).queryByRole("heading", { name: "Capacity bar" })).not.toBeInTheDocument();
      expectHeatmapHeaderStatusGroups(editor);
      expect(within(editor).queryByRole("heading", { name: "Draft lineage" })).not.toBeInTheDocument();
      const heatmap = heatmapSectionIn(editor);
      expectSelectedDateHeaderStats(editor);
      expectHeatmapPreferenceBars(editor);
      expect(heatmap).toHaveClass("schedule-heatmap--compact");
      expect(within(heatmap).getByRole("columnheader", { name: "Hrs" })).toBeInTheDocument();
      expect(within(heatmap).getByRole("columnheader", { name: "Rt" })).toBeInTheDocument();
      expect(within(heatmap).getByRole("columnheader", { name: "OC" })).toBeInTheDocument();
      expect(within(heatmap).getByRole("columnheader", { name: "Risk" })).toBeInTheDocument();
      expect(within(heatmap).queryByText("Available on selected day")).not.toBeInTheDocument();

      await user.click(within(editor).getByRole("button", { name: "History" }));
      const historyDialog = await screen.findByRole("dialog", { name: "Draft lineage" });
      expect(
        within(historyDialog).getByText(
          "Draft navigation stays within backend-authored draft lineage for this immutable schedule surface."
        )
      ).toBeInTheDocument();
      await user.click(within(historyDialog).getByRole("button", { name: "Close" }));
      await waitFor(() => {
        expect(screen.queryByRole("dialog", { name: "Draft lineage" })).not.toBeInTheDocument();
      });

      const sourceCell = heatmapButton(
        heatmap,
        (label) => label.includes("2026-03-22: assigned route")
      );
      const targetCell = heatmapButton(
        heatmap,
        (label) => label.includes("2026-03-22: no planned work")
      );

      await user.click(sourceCell);
      await user.click(targetCell);
      await waitFor(() => {
        expect(within(dialog).getByRole("button", { name: "Save draft" })).toBeEnabled();
      });

      await user.click(within(dialog).getByRole("button", { name: "Save draft" }));

      await waitFor(() => {
        expect(
          screen.queryByRole("dialog", { name: "Edit Weekly Schedule" })
        ).not.toBeInTheDocument();
      });
      expect(window.location.pathname).toBe("/runs/wr-weekly-001/workpages/schedule-v0");
      expect(mutationLog()).toContain(
        "workpage-schedule-artifact-submit:av-schedule-artifact-001:av-schedule-artifact-002"
      );
    },
    120000
  );

  it(
    "normalizes duplicate same-day defaults into distinct drivers and re-enables released choices",
    async () => {
      const user = userEvent.setup();
      resetApiState();
      const workflowRunId = "wr-weekly-001";
      const artifactVersionId = "av-schedule-artifact-001";
      const nextArtifactVersionId = "av-schedule-artifact-route-demand-002";
      const routeDemandArtifactVersionId = "av-route-demand-artifact-002";
      const coverageCandidatesPath =
        `/api/v1/workpages/workflow-runs/${workflowRunId}/schedule-v0/artifacts/` +
        `${artifactVersionId}/route-demand-coverage-candidates`;
      const coverageApplyPath =
        `/api/v1/workpages/workflow-runs/${workflowRunId}/schedule-v0/artifacts/` +
        `${artifactVersionId}/route-demand-coverage`;
      const coverageTargetA = {
        target_id: `${routeDemandArtifactVersionId}:2026-03-28:1`,
        route_slot_id: "slot-20260328-cycle1-standard#18",
        route_id: "ROUTE-20260328-18",
        service_date: "2026-03-28",
        route_slot_class: "standard",
        station_code: "DVC4",
        service_area: "Metro core",
        shift_start: "10:15",
        shift_end: "18:45",
        projected_minutes: 510,
        required_skill: "standard_delivery",
        vehicle_type: "cargo_van"
      };
      const coverageTargetB = {
        target_id: `${routeDemandArtifactVersionId}:2026-03-28:2`,
        route_slot_id: "slot-20260328-cycle1-standard#19",
        route_id: "ROUTE-20260328-19",
        service_date: "2026-03-28",
        route_slot_class: "standard",
        station_code: "DVC4",
        service_area: "Metro core",
        shift_start: "10:30",
        shift_end: "19:00",
        projected_minutes: 525,
        required_skill: "standard_delivery",
        vehicle_type: "cargo_van"
      };
      const recommendedCandidateA = buildCoverageCandidate(
        coverageTargetA,
        1,
        "A2S2SO4XUULX7H",
        "June Tate",
        {
          soft_score_total: 97.5,
          current_week_shift_count: 4,
          projected_rolling7_minutes: 2010,
          remaining_rolling7_minutes: 1590
        }
      );
      const alternateCandidateA = buildCoverageCandidate(
        coverageTargetA,
        2,
        "A7ZT4LME2WJQ9B",
        "Maya Chen"
      );
      const blockedCandidateA = buildCoverageCandidate(
        coverageTargetA,
        3,
        "A3OYGBYE20UA2R",
        "Eli Rowe",
        {
          selection_state: "blocked",
          hard_filter_status: "fail",
          hard_filter_reasons: ["already_assigned_that_day"],
          score_bucket: "blocked",
          soft_score_total: 0,
          clear_same_day_on_call_reserve: false,
          reserve_route_slot_id: null,
          reserve_route_id: null,
          assignment_action: "blocked",
          evaluation_kind: "same_day_conflict"
        }
      );
      const conflictingCandidateB = buildCoverageCandidate(
        coverageTargetB,
        1,
        "A2S2SO4XUULX7H",
        "June Tate",
        {
          soft_score_total: 96.75,
          current_week_shift_count: 4,
          projected_rolling7_minutes: 2055,
          remaining_rolling7_minutes: 1545
        }
      );
      const recommendedCandidateB = buildCoverageCandidate(
        coverageTargetB,
        2,
        "AZ39S2G5M8PX4T",
        "Nia Grant",
        {
          soft_score_total: 96.25,
          current_week_shift_count: 5,
          projected_rolling7_minutes: 2145,
          remaining_rolling7_minutes: 1455
        }
      );
      const alternateCandidateB = buildCoverageCandidate(
        coverageTargetB,
        3,
        "A5NS7VGK2MTL8P",
        "Omar Diaz"
      );
      const applyBodies: Array<Record<string, unknown>> = [];
      server.use(
        http.post(`*${coverageCandidatesPath}`, async () =>
          HttpResponse.json({
            status: "ok",
            route_demand_coverage_recommendations: {
              workflow_run_id: workflowRunId,
              artifact_version_id: artifactVersionId,
              route_demand_artifact_version_id: routeDemandArtifactVersionId,
              dependency_state: "aligned",
              dependencies: [
                {
                  dependency_key: "route_slot_requirements",
                  artifact_kind: "planning.route_slot_requirements.workbook",
                  artifact_version_id: routeDemandArtifactVersionId,
                  impact_class: "hard",
                  state: "aligned",
                  source_ref: `/api/v1/artifacts/${routeDemandArtifactVersionId}`
                }
              ],
              added_route_count: 2,
              target_count: 2,
              max_candidates: 8,
              targets: [coverageTargetA, coverageTargetB],
              candidate_groups: [
                {
                  target: coverageTargetA,
                  candidate_count: 3,
                  pass_candidate_count: 2,
                  candidates: [
                    recommendedCandidateA,
                    alternateCandidateA,
                    blockedCandidateA
                  ]
                },
                {
                  target: coverageTargetB,
                  candidate_count: 3,
                  pass_candidate_count: 3,
                  candidates: [
                    conflictingCandidateB,
                    recommendedCandidateB,
                    alternateCandidateB
                  ]
                }
              ],
              selected_defaults: [
                {
                  target_id: coverageTargetA.target_id,
                  route_slot_id: coverageTargetA.route_slot_id,
                  driver_id: recommendedCandidateA.driver_id,
                  row_kind: "assignment"
                },
                {
                  target_id: coverageTargetB.target_id,
                  route_slot_id: coverageTargetB.route_slot_id,
                  driver_id: conflictingCandidateB.driver_id,
                  row_kind: "assignment"
                }
              ],
              diagnostic_reason: null
            }
          })
        ),
        http.post(`*${coverageApplyPath}`, async ({ request }) => {
          applyBodies.push((await request.json()) as Record<string, unknown>);
          return HttpResponse.json({
            status: "ok",
            submitted: {
              workflow_run_id: workflowRunId,
              artifact_version_id: nextArtifactVersionId,
              supersedes_artifact_version_id: artifactVersionId,
              route: `/runs/${workflowRunId}/workpages/schedule-v0/artifacts/${nextArtifactVersionId}`
            },
            route_demand_coverage: {
              route_demand_artifact_version_id: routeDemandArtifactVersionId,
              assigned_count: 2,
              appended_assignment_count: 2,
              cleared_same_day_reserve_count: 1,
              selected: [alternateCandidateA, recommendedCandidateB]
            }
          });
        }),
        http.get(
          `*/api/v1/workpages/workflow-runs/${workflowRunId}/schedule-v0/artifacts/${nextArtifactVersionId}`,
          () =>
            HttpResponse.json(
              buildScheduleArtifactPayload(nextArtifactVersionId, workflowRunId)
            )
        )
      );

      window.history.pushState(
        {},
        "",
        `/runs/${workflowRunId}/workpages/route-demand-v0/artifacts/av-route-demand-artifact-001`
      );
      render(<App />);

      const routeDemandPage = await screen.findByTestId("route-demand-artifact-workpage-page");
      await user.click(
        within(routeDemandPage).getByRole("button", {
          name: "Increase planned routes for 2026-03-28"
        })
      );
      await user.click(
        within(routeDemandPage).getByRole("button", {
          name: "Increase planned routes for 2026-03-28"
        })
      );
      await user.click(
        within(routeDemandPage).getByRole("button", { name: "Run coverage agent" })
      );

      const dialog = await screen.findByRole("dialog", { name: "Edit Weekly Schedule" });
      const panel = await within(dialog).findByTestId("route-demand-coverage-panel");
      const daySection = await within(panel).findByTestId("route-demand-coverage-day-2026-03-28");
      const inlineTable = await within(daySection).findByTestId(
        "route-demand-coverage-day-table-2026-03-28"
      );
      const overflow = await within(daySection).findByTestId(
        "route-demand-coverage-day-overflow-2026-03-28"
      );
      expect(panel).toHaveTextContent("Route-demand coverage recommendations");
      expect(panel).toHaveTextContent("2026-03-28: 17 -> 19 (+2)");
      expect(
        within(panel).queryByTestId(`route-demand-coverage-target-${coverageTargetA.route_slot_id}`)
      ).not.toBeInTheDocument();
      expect(within(inlineTable).getByRole("table")).toBeInTheDocument();
      expect(within(inlineTable).getAllByRole("row")).toHaveLength(3);
      expect(inlineTable).toHaveTextContent("ROUTE-20260328-18");
      expect(inlineTable).toHaveTextContent("ROUTE-20260328-19");
      expect(inlineTable).toHaveTextContent("June Tate");
      expect(inlineTable).toHaveTextContent("Nia Grant");
      expect(within(inlineTable).getAllByText("June Tate")).toHaveLength(1);
      expect(inlineTable).not.toHaveTextContent("Maya Chen");
      expect(inlineTable).not.toHaveTextContent("Omar Diaz");
      expect(inlineTable).not.toHaveTextContent("Eli Rowe");
      expect(overflow).not.toHaveAttribute("open");
      expect(overflow).toHaveTextContent("Show 4 more options across 2 routes (1 blocked)");

      await user.click(within(overflow).getByText("Show 4 more options across 2 routes (1 blocked)"));
      expect(overflow).toHaveAttribute("open");
      expect(
        within(overflow).getByRole("radio", {
          name: /Select June Tate for ROUTE-20260328-19 on 2026-03-28/
        })
      ).toBeDisabled();
      expect(
        within(overflow).getByText("Already selected for ROUTE-20260328-18")
      ).toBeInTheDocument();
      expect(
        await within(overflow).findByRole("radio", {
          name: /Select Maya Chen for ROUTE-20260328-18 on 2026-03-28/
        })
      ).toBeInTheDocument();
      await user.click(
        within(overflow).getByRole("radio", {
          name: /Select Maya Chen for ROUTE-20260328-18 on 2026-03-28/
        })
      );
      await waitFor(() => {
        expect(inlineTable).toHaveTextContent("Maya Chen");
      });
      expect(inlineTable).toHaveTextContent("Nia Grant");
      expect(inlineTable).not.toHaveTextContent("June Tate");
      expect(
        within(overflow).getByRole("radio", {
          name: /Select June Tate for ROUTE-20260328-19 on 2026-03-28/
        })
      ).toBeInTheDocument();
      await waitFor(() => {
        expect(
          within(overflow).getByRole("radio", {
            name: /Select June Tate for ROUTE-20260328-19 on 2026-03-28/
          })
        ).toBeEnabled();
      });
      expect(within(overflow).getByText("Eli Rowe")).toBeInTheDocument();
      expect(within(overflow).getByText("already_assigned_that_day")).toBeInTheDocument();
      expect(
        within(panel).getByRole("button", { name: "Apply 2 coverage selections" })
      ).toBeEnabled();

      await user.click(
        within(panel).getByRole("button", { name: "Apply 2 coverage selections" })
      );

      await waitFor(() => {
        expect(applyBodies).toHaveLength(1);
      });
      expect(applyBodies[0]).toMatchObject({
        route_demand_artifact_version_id: routeDemandArtifactVersionId,
      });
      expect(applyBodies[0].selections).toEqual(
        expect.arrayContaining([
          {
            target_id: coverageTargetA.target_id,
            route_slot_id: coverageTargetA.route_slot_id,
            driver_id: alternateCandidateA.driver_id,
            row_kind: "assignment"
          },
          {
            target_id: coverageTargetB.target_id,
            route_slot_id: coverageTargetB.route_slot_id,
            driver_id: recommendedCandidateB.driver_id,
            row_kind: "assignment"
          }
        ])
      );
      await waitFor(() => {
        expect(screen.queryByTestId("route-demand-coverage-panel")).not.toBeInTheDocument();
      });
      expect(screen.getByTestId("schedule-quick-edit-editor")).toBeInTheDocument();
    },
    90000
  );

  it(
    "keeps apply disabled when same-day targets do not have enough distinct selectable drivers",
    async () => {
      const user = userEvent.setup();
      resetApiState();
      const workflowRunId = "wr-weekly-001";
      const artifactVersionId = "av-schedule-artifact-001";
      const routeDemandArtifactVersionId = "av-route-demand-artifact-002";
      const coverageCandidatesPath =
        `/api/v1/workpages/workflow-runs/${workflowRunId}/schedule-v0/artifacts/` +
        `${artifactVersionId}/route-demand-coverage-candidates`;
      const coverageTargetA = {
        target_id: `${routeDemandArtifactVersionId}:2026-03-28:1`,
        route_slot_id: "slot-20260328-cycle1-standard#18",
        route_id: "ROUTE-20260328-18",
        service_date: "2026-03-28",
        route_slot_class: "standard",
        station_code: "DVC4",
        service_area: "Metro core",
        shift_start: "10:15",
        shift_end: "18:45",
        projected_minutes: 510,
        required_skill: "standard_delivery",
        vehicle_type: "cargo_van"
      };
      const coverageTargetB = {
        target_id: `${routeDemandArtifactVersionId}:2026-03-28:2`,
        route_slot_id: "slot-20260328-cycle1-standard#19",
        route_id: "ROUTE-20260328-19",
        service_date: "2026-03-28",
        route_slot_class: "standard",
        station_code: "DVC4",
        service_area: "Metro core",
        shift_start: "10:30",
        shift_end: "19:00",
        projected_minutes: 525,
        required_skill: "standard_delivery",
        vehicle_type: "cargo_van"
      };
      const sharedCandidateA = buildCoverageCandidate(
        coverageTargetA,
        1,
        "A2S2SO4XUULX7H",
        "June Tate"
      );
      const sharedCandidateB = buildCoverageCandidate(
        coverageTargetB,
        1,
        "A2S2SO4XUULX7H",
        "June Tate"
      );

      server.use(
        http.post(`*${coverageCandidatesPath}`, async () =>
          HttpResponse.json({
            status: "ok",
            route_demand_coverage_recommendations: {
              workflow_run_id: workflowRunId,
              artifact_version_id: artifactVersionId,
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
                  candidates: [sharedCandidateA]
                },
                {
                  target: coverageTargetB,
                  candidate_count: 1,
                  pass_candidate_count: 1,
                  candidates: [sharedCandidateB]
                }
              ],
              selected_defaults: [
                {
                  target_id: coverageTargetA.target_id,
                  route_slot_id: coverageTargetA.route_slot_id,
                  driver_id: sharedCandidateA.driver_id,
                  row_kind: "assignment"
                },
                {
                  target_id: coverageTargetB.target_id,
                  route_slot_id: coverageTargetB.route_slot_id,
                  driver_id: sharedCandidateB.driver_id,
                  row_kind: "assignment"
                }
              ],
              diagnostic_reason: null
            }
          })
        )
      );

      window.history.pushState(
        {},
        "",
        `/runs/${workflowRunId}/workpages/route-demand-v0/artifacts/av-route-demand-artifact-001`
      );
      render(<App />);

      const routeDemandPage = await screen.findByTestId("route-demand-artifact-workpage-page");
      await user.click(
        within(routeDemandPage).getByRole("button", {
          name: "Increase planned routes for 2026-03-28"
        })
      );
      await user.click(
        within(routeDemandPage).getByRole("button", {
          name: "Increase planned routes for 2026-03-28"
        })
      );
      await user.click(
        within(routeDemandPage).getByRole("button", { name: "Run coverage agent" })
      );

      const dialog = await screen.findByRole("dialog", { name: "Edit Weekly Schedule" });
      const panel = await within(dialog).findByTestId("route-demand-coverage-panel");
      const inlineTable = await within(panel).findByTestId(
        "route-demand-coverage-day-table-2026-03-28"
      );

      expect(inlineTable).toHaveTextContent("ROUTE-20260328-18");
      expect(inlineTable).toHaveTextContent("ROUTE-20260328-19");
      expect(within(inlineTable).getAllByText("June Tate")).toHaveLength(2);
      expect(
        within(inlineTable).getByRole("radio", {
          name: /Select June Tate for ROUTE-20260328-19 on 2026-03-28/
        })
      ).toBeDisabled();
      expect(
        within(inlineTable).getByText("Already selected for ROUTE-20260328-18")
      ).toBeInTheDocument();
      expect(
        within(panel).getByRole("button", { name: "Apply 1 coverage selection" })
      ).toBeDisabled();
    },
    90000
  );

  it(
    "shows unresolved route additions in red and auto-picks the top unresolved route from an empty heatmap cell",
    async () => {
    const user = userEvent.setup();
    resetApiState();
    const workflowRunId = "wr-weekly-001";
    const artifactVersionId = "av-schedule-artifact-001";
    const routeDemandArtifactVersionId = "av-route-demand-artifact-004";
    const coverageCandidatesPath =
      `/api/v1/workpages/workflow-runs/${workflowRunId}/schedule-v0/artifacts/` +
      `${artifactVersionId}/route-demand-coverage-candidates`;
    const coverageContext = {
      workflow_run_id: workflowRunId,
      schedule_artifact_version_id: artifactVersionId,
      route_demand_artifact_version_id: routeDemandArtifactVersionId,
      coverage_candidates_path: coverageCandidatesPath,
      coverage_apply_path:
        `/api/v1/workpages/workflow-runs/${workflowRunId}/schedule-v0/artifacts/` +
        `${artifactVersionId}/route-demand-coverage`,
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
    const coverageTargetA = {
      target_id: `${routeDemandArtifactVersionId}:2026-03-24:1`,
      route_slot_id: "slot-20260324-cycle1-standard#18",
      route_id: "ROUTE-20260324-18",
      service_date: "2026-03-24",
      route_slot_class: "standard",
      station_code: "DVC4",
      service_area: "Metro core",
      shift_start: "10:15",
      shift_end: "18:45",
      projected_minutes: 510,
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
      shift_end: "19:00",
      projected_minutes: 525,
      required_skill: "standard_delivery",
      vehicle_type: "cargo_van"
    };
    const sharedTopCandidateA = buildCoverageCandidate(
      coverageTargetA,
      1,
      "A2TU4ZRI65E1H8",
      "Abhiraj Singh"
    );
    const alternateCandidateA = buildCoverageCandidate(
      coverageTargetA,
      2,
      "A149421ZGG7QED",
      "Balwinder Singh"
    );
    const sharedTopCandidateB = buildCoverageCandidate(
      coverageTargetB,
      1,
      "A2TU4ZRI65E1H8",
      "Abhiraj Singh"
    );
    const alternateCandidateB = buildCoverageCandidate(
      coverageTargetB,
      2,
      "A3M38Z4NGI9OR3",
      "Akash"
    );

    server.use(
      http.get(
        `*/api/v1/workpages/workflow-runs/${workflowRunId}/schedule-v0/artifacts/${artifactVersionId}`,
        () =>
          HttpResponse.json(
            buildScheduleArtifactPayload(artifactVersionId, workflowRunId, (payload) => {
              payload.route_demand_coverage_context = coverageContext;
            })
          )
      ),
      http.post(`*${coverageCandidatesPath}`, async () =>
        HttpResponse.json({
          status: "ok",
          route_demand_coverage_recommendations: {
            workflow_run_id: workflowRunId,
            artifact_version_id: artifactVersionId,
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
                candidate_count: 2,
                pass_candidate_count: 2,
                candidates: [sharedTopCandidateA, alternateCandidateA]
              },
              {
                target: coverageTargetB,
                candidate_count: 2,
                pass_candidate_count: 2,
                candidates: [sharedTopCandidateB, alternateCandidateB]
              }
            ],
            selected_defaults: [],
            diagnostic_reason: null
          }
        })
      )
    );

    window.history.pushState(
      {},
      "",
      `/runs/${workflowRunId}/workpages/schedule-v0/artifacts/${artifactVersionId}`
    );
    render(<App />);

    const page = await screen.findByTestId("schedule-artifact-workpage-page");
    const panel = await screen.findByTestId("route-demand-coverage-panel");
    const heatmap = heatmapSectionIn(page);
    const selectedHeader = heatmap.querySelector(
      ".schedule-heatmap__date-header--selected"
    ) as HTMLElement | null;
    expect(selectedHeader).not.toBeNull();
    expect(selectedHeader).toHaveClass("schedule-heatmap__date-header--uncovered");
    expect(within(selectedHeader as HTMLElement).getByText("Gap")).toBeInTheDocument();
    expect(within(selectedHeader as HTMLElement).getByText("2")).toBeInTheDocument();

    const abhirajCell = heatmapButton(
      heatmap,
      (label) => label.startsWith("Abhiraj Singh on 2026-03-24")
    );
    await user.click(abhirajCell);

    expect(abhirajCell).toHaveTextContent("Pending route");
    expect(abhirajCell.getAttribute("aria-label")).toContain("ROUTE-20260324-18");
    expect(
      within(panel).getByRole("radio", {
        name: /Select Abhiraj Singh for ROUTE-20260324-18 on 2026-03-24/
      })
    ).toBeChecked();
    expect(
      within(panel).getByRole("radio", {
        name: /Select Abhiraj Singh for ROUTE-20260324-19 on 2026-03-24/
      })
    ).toBeDisabled();
    expect(within(selectedHeader as HTMLElement).getByText("1")).toBeInTheDocument();

    await user.click(abhirajCell);
    expect(abhirajCell).toHaveTextContent("Open");
    expect(
      within(panel).getByRole("radio", {
        name: /Select Abhiraj Singh for ROUTE-20260324-18 on 2026-03-24/
      })
    ).not.toBeChecked();
    expect(within(selectedHeader as HTMLElement).getByText("2")).toBeInTheDocument();
    },
    10000
  );

  it(
    "applies pending heatmap route adds through the coverage apply endpoint",
    async () => {
      const user = userEvent.setup();
      resetApiState();
      const workflowRunId = "wr-weekly-001";
      const artifactVersionId = "av-schedule-artifact-001";
      const nextArtifactVersionId = "av-schedule-artifact-route-add-002";
      const routeDemandArtifactVersionId = "av-route-demand-artifact-005";
      const coverageCandidatesPath =
        `/api/v1/workpages/workflow-runs/${workflowRunId}/schedule-v0/artifacts/` +
        `${artifactVersionId}/route-demand-coverage-candidates`;
      const coverageApplyPath =
        `/api/v1/workpages/workflow-runs/${workflowRunId}/schedule-v0/artifacts/` +
        `${artifactVersionId}/route-demand-coverage`;
      const coverageContext = {
        workflow_run_id: workflowRunId,
        schedule_artifact_version_id: artifactVersionId,
        route_demand_artifact_version_id: routeDemandArtifactVersionId,
        coverage_candidates_path: coverageCandidatesPath,
        coverage_apply_path: coverageApplyPath,
        service_dates: ["2026-03-24"],
        added_route_count: 1,
        deltas: [
          {
            service_date: "2026-03-24",
            previous_planned_route_count: 20,
            planned_route_count: 21,
            delta: 1
          }
        ]
      };
      const coverageTarget = {
        target_id: `${routeDemandArtifactVersionId}:2026-03-24:1`,
        route_slot_id: "slot-20260324-cycle1-standard#20",
        route_id: "ROUTE-20260324-20",
        service_date: "2026-03-24",
        route_slot_class: "standard",
        station_code: "DVC4",
        service_area: "Metro core",
        shift_start: "10:45",
        shift_end: "19:15",
        projected_minutes: 535,
        required_skill: "standard_delivery",
        vehicle_type: "cargo_van"
      };
      const recommendedCandidate = buildCoverageCandidate(
        coverageTarget,
        1,
        "A149421ZGG7QED",
        "Balwinder Singh"
      );
      const applyBodies: Array<Record<string, any>> = [];

      server.use(
        http.get(
          `*/api/v1/workpages/workflow-runs/${workflowRunId}/schedule-v0/artifacts/${artifactVersionId}`,
          () =>
            HttpResponse.json(
              buildScheduleArtifactPayload(artifactVersionId, workflowRunId, (payload) => {
                payload.route_demand_coverage_context = coverageContext;
              })
            )
        ),
        http.post(`*${coverageCandidatesPath}`, async () =>
          HttpResponse.json({
            status: "ok",
            route_demand_coverage_recommendations: {
              workflow_run_id: workflowRunId,
              artifact_version_id: artifactVersionId,
              route_demand_artifact_version_id: routeDemandArtifactVersionId,
              dependency_state: "aligned",
              dependencies: [],
              added_route_count: 1,
              target_count: 1,
              max_candidates: 8,
              targets: [coverageTarget],
              candidate_groups: [
                {
                  target: coverageTarget,
                  candidate_count: 1,
                  pass_candidate_count: 1,
                  candidates: [recommendedCandidate]
                }
              ],
              selected_defaults: [],
              diagnostic_reason: null
            }
          })
        ),
        http.post(`*${coverageApplyPath}`, async ({ request }) => {
          const body = (await request.json()) as Record<string, any>;
          applyBodies.push(body);
          return HttpResponse.json({
            status: "ok",
            submitted: {
              workflow_run_id: workflowRunId,
              artifact_version_id: nextArtifactVersionId,
              supersedes_artifact_version_id: artifactVersionId,
              route: `/runs/${workflowRunId}/workpages/schedule-v0/artifacts/${nextArtifactVersionId}`
            },
            route_demand_coverage: {
              selected: [
                {
                  route_slot_id: coverageTarget.route_slot_id,
                  driver_id: recommendedCandidate.driver_id
                }
              ],
              assigned_count: 1,
              appended_assignment_count: 1,
              cleared_same_day_reserve_count: 0
            }
          });
        }),
        http.get(
          `*/api/v1/workpages/workflow-runs/${workflowRunId}/schedule-v0/artifacts/${nextArtifactVersionId}`,
          () => HttpResponse.json(buildScheduleArtifactPayload(nextArtifactVersionId, workflowRunId))
        )
      );

      window.history.pushState(
        {},
        "",
        `/runs/${workflowRunId}/workpages/schedule-v0/artifacts/${artifactVersionId}`
      );
      render(<App />);

      const page = await screen.findByTestId("schedule-artifact-workpage-page");
      await screen.findByRole("radio", {
        name: /Select Balwinder Singh for ROUTE-20260324-20 on 2026-03-24/
      });
      const heatmap = heatmapSectionIn(page);
      const balwinderCell = heatmapButton(
        heatmap,
        (label) => label.startsWith("Balwinder Singh on 2026-03-24")
      );
      await user.click(balwinderCell);

      const applyButton = await screen.findByRole("button", { name: "Apply 1 route addition" });
      expect(applyButton).toBeEnabled();
      await user.click(applyButton);

      await waitFor(() => {
        expect(applyBodies).toHaveLength(1);
      });
      expect(applyBodies[0].route_demand_artifact_version_id).toBe(routeDemandArtifactVersionId);
      expect(applyBodies[0].selections).toEqual([
        {
          target_id: coverageTarget.target_id,
          route_slot_id: coverageTarget.route_slot_id,
          driver_id: recommendedCandidate.driver_id,
          row_kind: "assignment"
        }
      ]);
      await waitFor(() => {
        expect(screen.queryByTestId("route-demand-coverage-panel")).not.toBeInTheDocument();
      });
    },
    15000
  );

  it(
    "keeps a single-target backend default inline inside the day-grouped coverage layout",
    async () => {
      const user = userEvent.setup();
      resetApiState();
      const workflowRunId = "wr-weekly-001";
      const artifactVersionId = "av-schedule-artifact-001";
      const routeDemandArtifactVersionId = "av-route-demand-artifact-002";
      const coverageCandidatesPath =
        `/api/v1/workpages/workflow-runs/${workflowRunId}/schedule-v0/artifacts/` +
        `${artifactVersionId}/route-demand-coverage-candidates`;
      const coverageTarget = {
        target_id: `${routeDemandArtifactVersionId}:2026-03-28:1`,
        route_slot_id: "slot-20260328-cycle1-standard#18",
        route_id: "ROUTE-20260328-18",
        service_date: "2026-03-28",
        route_slot_class: "standard",
        station_code: "DVC4",
        service_area: "Metro core",
        shift_start: "10:15",
        shift_end: "18:45",
        projected_minutes: 510,
        required_skill: "standard_delivery",
        vehicle_type: "cargo_van"
      };
      const firstCandidate = buildCoverageCandidate(
        coverageTarget,
        1,
        "A2S2SO4XUULX7H",
        "June Tate"
      );
      const secondCandidate = buildCoverageCandidate(
        coverageTarget,
        2,
        "A7ZT4LME2WJQ9B",
        "Maya Chen"
      );
      const thirdCandidate = buildCoverageCandidate(
        coverageTarget,
        3,
        "A4PWB7DY0TKR6M",
        "Leo Park"
      );
      const overflowDefaultCandidate = buildCoverageCandidate(
        coverageTarget,
        4,
        "A5NS7VGK2MTL8P",
        "Omar Diaz"
      );

      server.use(
        http.post(`*${coverageCandidatesPath}`, async () =>
          HttpResponse.json({
            status: "ok",
            route_demand_coverage_recommendations: {
              workflow_run_id: workflowRunId,
              artifact_version_id: artifactVersionId,
              route_demand_artifact_version_id: routeDemandArtifactVersionId,
              dependency_state: "aligned",
              dependencies: [],
              added_route_count: 1,
              target_count: 1,
              max_candidates: 8,
              targets: [coverageTarget],
              candidate_groups: [
                {
                  target: coverageTarget,
                  candidate_count: 4,
                  pass_candidate_count: 4,
                  candidates: [
                    firstCandidate,
                    secondCandidate,
                    thirdCandidate,
                    overflowDefaultCandidate
                  ]
                }
              ],
              selected_defaults: [
                {
                  target_id: coverageTarget.target_id,
                  route_slot_id: coverageTarget.route_slot_id,
                  driver_id: overflowDefaultCandidate.driver_id,
                  row_kind: "assignment"
                }
              ],
              diagnostic_reason: null
            }
          })
        )
      );

      window.history.pushState(
        {},
        "",
        `/runs/${workflowRunId}/workpages/route-demand-v0/artifacts/av-route-demand-artifact-001`
      );
      render(<App />);

      const routeDemandPage = await screen.findByTestId("route-demand-artifact-workpage-page");
      await user.click(
        within(routeDemandPage).getByRole("button", {
          name: "Increase planned routes for 2026-03-28"
        })
      );
      await user.click(
        within(routeDemandPage).getByRole("button", { name: "Run coverage agent" })
      );

      const dialog = await screen.findByRole("dialog", { name: "Edit Weekly Schedule" });
      const panel = await within(dialog).findByTestId("route-demand-coverage-panel");
      const inlineTable = await within(panel).findByTestId(
        "route-demand-coverage-day-table-2026-03-28"
      );
      const overflow = await within(panel).findByTestId(
        "route-demand-coverage-day-overflow-2026-03-28"
      );

      expect(inlineTable).toHaveTextContent("ROUTE-20260328-18");
      expect(inlineTable).toHaveTextContent("Omar Diaz");
      expect(inlineTable).not.toHaveTextContent("June Tate");
      expect(inlineTable).not.toHaveTextContent("Maya Chen");
      expect(inlineTable).not.toHaveTextContent("Leo Park");
      expect(overflow).not.toHaveAttribute("open");
      expect(overflow).toHaveTextContent("Show 3 more options across 1 route");
      expect(
        within(inlineTable).getByRole("radio", {
          name: /Select Omar Diaz for ROUTE-20260328-18 on 2026-03-28/
        })
      ).toBeChecked();
      await user.click(within(overflow).getByText("Show 3 more options across 1 route"));
      expect(overflow).toHaveAttribute("open");
      expect(
        within(overflow).getByRole("radio", {
          name: /Select June Tate for ROUTE-20260328-18 on 2026-03-28/
        })
      ).toBeInTheDocument();
    },
    90000
  );

  it(
    "marks a driver Sick / No Show from the weekly schedule quick-edit heatmap",
    async () => {
      const user = userEvent.setup();
      resetApiState();
      window.history.pushState({}, "", "/runs/wr-weekly-001/workpages/schedule-v0");
      render(<App />);

      expect(await screen.findByTestId("schedule-workpage-page")).toBeInTheDocument();
      await user.click(await screen.findByRole("button", { name: "Edit weekly schedule" }));

      const dialog = await screen.findByRole("dialog", { name: "Edit Weekly Schedule" });
      const editor = await within(dialog).findByTestId("schedule-quick-edit-editor");
      const heatmap = heatmapSectionIn(editor);
      const assignedCell = heatmapButton(
        heatmap,
        (label) => label.includes("2026-03-22: assigned route")
      );
      const assignedLabel = assignedCell.getAttribute("aria-label") ?? "";
      const driverName = personNameFromLabel(assignedLabel);
      const cellContainer = assignedCell.closest("td");
      expect(cellContainer).not.toBeNull();
      const sickButton = within(cellContainer as HTMLElement).getByRole("button", {
        name: `Mark Sick / No Show: ${driverName} on 2026-03-22`
      });
      expect(sickButton).toBeInTheDocument();
      fireEvent.click(sickButton);

      const confirmDialog = await screen.findByRole("dialog", { name: "Mark Sick / No Show" });
      expect(confirmDialog).toHaveTextContent(
        `${driverName} will be marked unavailable on 2026-03-22`
      );
      await user.type(within(confirmDialog).getByLabelText("Optional note"), "Called in sick");
      await user.click(within(confirmDialog).getByRole("button", { name: "Confirm Sick / No Show" }));

      await waitFor(() => {
        expect(mutationLog().some((entry) => entry.includes("workpage-schedule-sick-no-show"))).toBe(
          true
        );
      });
      expect(screen.getByRole("dialog", { name: "Edit Weekly Schedule" })).toBeInTheDocument();
      await waitFor(() => {
        expect(
          screen.queryByRole("dialog", { name: "Mark Sick / No Show" })
        ).not.toBeInTheDocument();
      });
    },
    120000
  );

  it("reveals the Sick action only for the hovered or focused heatmap cell", () => {
    expect(appCss).toMatch(
      /\.schedule-heatmap__sick-button\s*{[\s\S]*?opacity:\s*0;[\s\S]*?pointer-events:\s*none;[\s\S]*?transform:\s*translateY\(-2px\);/
    );
    expect(appCss).toMatch(
      /\.schedule-heatmap__cell-wrap:hover \.schedule-heatmap__sick-button:not\(:disabled\),\s*\.schedule-heatmap__cell-wrap:focus-within \.schedule-heatmap__sick-button:not\(:disabled\),\s*\.schedule-heatmap__sick-button:focus-visible\s*{[\s\S]*?opacity:\s*1;[\s\S]*?pointer-events:\s*auto;[\s\S]*?transform:\s*translateY\(0\);/
    );
    expect(appCss).toMatch(
      /\.schedule-heatmap__sick-button:disabled\s*{[\s\S]*?opacity:\s*0;[\s\S]*?pointer-events:\s*none;/
    );
  });

  it(
    "opens the standalone latest draft artifact, auto-previews heatmap edits, saves a superseding version, and downloads JSON",
    async () => {
      const user = userEvent.setup();
      window.history.pushState(
        {},
        "",
        "/runs/wr-weekly-001/workpages/schedule-v0/artifacts/av-schedule-artifact-001"
      );
      render(<App />);

      const artifactPage = await screen.findByTestId("schedule-artifact-workpage-page");
      const artifactTitleBar = artifactPage.querySelector(".workpage-page__hero-title-bar");
      const artifactHeroActions = artifactPage.querySelector(".workpage-page__hero-actions");
      expect(artifactTitleBar).not.toBeNull();
      expect(artifactTitleBar).toHaveClass("workpage-page__hero-title-bar--sticky");
      expect(
        within(artifactTitleBar as HTMLElement).getByRole("button", { name: "Save draft" })
      ).toBeInTheDocument();
      expect(
        within(artifactTitleBar as HTMLElement).getByRole("button", { name: "Download draft JSON" })
      ).toBeInTheDocument();
      expect(artifactHeroActions).not.toBeNull();
      expect(
        within(artifactHeroActions as HTMLElement).getByRole("link", { name: "Back to query landing" })
      ).toBeInTheDocument();
      expect(within(artifactPage).getByRole("heading", { name: "Accepted history" })).toBeInTheDocument();
      expect(within(artifactPage).getByRole("heading", { name: "Draft lineage" })).toBeInTheDocument();
      expect(within(artifactPage).getByRole("heading", { name: "Live preview" })).toBeInTheDocument();
      const { dependencyGroup, checksGroup } = expectHeatmapHeaderStatusGroups(artifactPage);
      expect(within(artifactPage).queryByRole("heading", { name: "Driver metrics" })).not.toBeInTheDocument();
      expect(within(artifactPage).getByText("No accepted schedule history is available for this surface yet.")).toBeInTheDocument();
      expect(screen.queryByRole("tooltip")).not.toBeInTheDocument();
      const dependencySummaryButton = within(dependencyGroup).getByRole("button", {
        name: "Show summary for Dependency status"
      });
      const checksSummaryButton = within(checksGroup).getByRole("button", {
        name: "Show summary for Checks"
      });
      const routeSlotRequirementsChip = within(dependencyGroup).getByText("Route Slot Requirements");
      expect(routeSlotRequirementsChip.getAttribute("title")).toContain(
        SCHEDULE_DEPENDENCY_ITEM_SUMMARIES.route_slot_requirements
      );
      const scheduledCapacityChip = within(checksGroup).getByText("Routes within scheduled capacity");
      expect(scheduledCapacityChip.getAttribute("title")).toContain(
        SCHEDULE_CHECK_ITEM_SUMMARIES.scheduled_capacity
      );
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

      const heatmap = heatmapSection();
      const selectedHeatmapDate = heatmap.querySelector(".schedule-heatmap__date-header--selected");
      expect(selectedHeatmapDate).not.toBeNull();
      expect(selectedHeatmapDate).toHaveTextContent("2026-03-24");
      expectSelectedDateHeaderStats(artifactPage);
      expectHeatmapPreferenceBars(artifactPage);
      const abhirajRow = driverHeatmapRow(heatmap, "Abhiraj Singh");
      expect(within(abhirajRow).getByText("25.5 h")).toBeInTheDocument();
      expect(within(abhirajRow).queryByText("Pref Unset")).not.toBeInTheDocument();
      expect(within(abhirajRow).queryByText("Avail Available")).not.toBeInTheDocument();
      const riskTrigger = within(abhirajRow).getByRole("button", {
        name: "Open compliance details for Abhiraj Singh"
      });
      expect(riskTrigger).toHaveClass("schedule-heatmap__risk-trigger");
      expect(riskTrigger).toHaveTextContent(/Pass|Warn|Fail/);
      expect(riskTrigger).toHaveTextContent("i");
      await user.click(riskTrigger);
      const complianceDialog = await screen.findByRole("dialog", {
        name: "Compliance details for Abhiraj Singh"
      });
      expect(within(complianceDialog).getByText("route_slot_not_in_pinned_baseline")).toBeInTheDocument();
      expect(within(complianceDialog).getByText("rolling_7_day_limit")).toBeInTheDocument();
      await user.click(
        screen.getByRole("button", { name: "Close Compliance details for Abhiraj Singh" })
      );
      const sourceCell = heatmapButton(
        heatmap,
        (label) => label.includes("2026-03-22: assigned route")
      );
      const targetCell = heatmapButton(
        heatmap,
        (label) => label.includes("2026-03-22: no planned work")
      );
      const targetName = personNameFromLabel(targetCell.getAttribute("aria-label") ?? "");

      await user.click(sourceCell);
      await user.click(targetCell);

      expect(
        within(heatmap).getByRole("button", {
          name: new RegExp(`^${escapeRegExp(targetName)} on 2026-03-22: assigned route, manually overridden$`)
        })
      ).toBeInTheDocument();

      await waitFor(() => {
        expect(mutationLog()).toContain("workpage-schedule-artifact-preview:av-schedule-artifact-001");
      });
      expect(await screen.findByText("Preview applied")).toBeInTheDocument();

      await user.click(screen.getByRole("button", { name: "Save draft" }));

      await waitFor(() => {
        expect(window.location.pathname).toBe(
          "/runs/wr-weekly-001/workpages/schedule-v0/artifacts/av-schedule-artifact-002"
        );
      });

      expect(await screen.findByTestId("schedule-artifact-workpage-page")).toBeInTheDocument();
      const historyPanel = screen.getByTestId("schedule-draft-history-rail");
      expect(within(historyPanel as HTMLElement).getByText("Current draft")).toBeInTheDocument();
      expect(within(historyPanel as HTMLElement).getAllByText("Previous draft").length).toBeGreaterThan(0);

      await user.click(screen.getByRole("button", { name: "Download draft JSON" }));
      await waitFor(() => {
        expect(mutationLog()).toContain("artifact-download-bin:av-schedule-artifact-002");
      });
    },
    120000
  );

  it(
    "reopens the previous draft from the draft rail and shows the stale-version guidance",
    async () => {
      const user = userEvent.setup();
      window.history.pushState(
        {},
        "",
        "/runs/wr-weekly-001/workpages/schedule-v0/artifacts/av-schedule-artifact-001"
      );
      render(<App />);

      expect(await screen.findByTestId("schedule-artifact-workpage-page")).toBeInTheDocument();
      await user.click(screen.getByRole("button", { name: "Save draft" }));

      await waitFor(() => {
        expect(window.location.pathname).toBe(
          "/runs/wr-weekly-001/workpages/schedule-v0/artifacts/av-schedule-artifact-002"
        );
      });

      await user.click(
        within(screen.getByTestId("schedule-draft-history-av-schedule-artifact-001")).getByRole("link", {
          name: /Previous draft/i
        })
      );

      await waitFor(() => {
        expect(window.location.pathname).toBe(
          "/runs/wr-weekly-001/workpages/schedule-v0/artifacts/av-schedule-artifact-001"
        );
      });
      expect(await screen.findByRole("heading", { name: "Latest draft available" })).toBeInTheDocument();
    },
    45000
  );

  it(
    "shows conflict reopen UX and keeps local edits until the operator navigates",
    async () => {
      const user = userEvent.setup();
      server.use(
        http.post(
          "*/api/v1/workpages/workflow-runs/:workflowRunId/schedule-v0/artifacts/:artifactVersionId/submit",
          ({ params }) =>
            HttpResponse.json(
              {
                status: "error",
                error: {
                  code: "workpage_artifact_conflict",
                  message: "artifact-backed workpage already has a newer draft",
                  details: {
                    artifact_version_id: String(params.artifactVersionId),
                    latest_artifact_version_id: "av-schedule-artifact-latest",
                    workflow_run_id: "wr-weekly-001",
                    route:
                      "/runs/wr-weekly-001/workpages/schedule-v0/artifacts/av-schedule-artifact-latest"
                  }
                }
              },
              { status: 409 }
            )
        ),
        http.get(
          "*/api/v1/workpages/workflow-runs/:workflowRunId/schedule-v0/artifacts/av-schedule-artifact-latest",
          () => HttpResponse.json(buildScheduleArtifactPayload("av-schedule-artifact-latest"))
        )
      );

      window.history.pushState(
        {},
        "",
        "/runs/wr-weekly-001/workpages/schedule-v0/artifacts/av-schedule-artifact-001"
      );
      render(<App />);

      expect(await screen.findByTestId("schedule-artifact-workpage-page")).toBeInTheDocument();

      const heatmap = heatmapSection();
      const sourceCell = heatmapButton(
        heatmap,
        (label) => label.includes("2026-03-22: assigned route")
      );
      const targetCell = heatmapButton(
        heatmap,
        (label) => label.includes("2026-03-22: no planned work")
      );
      const targetName = personNameFromLabel(targetCell.getAttribute("aria-label") ?? "");

      await user.click(sourceCell);
      await user.click(targetCell);

      await user.click(screen.getByRole("button", { name: "Save draft" }));

      expect(await screen.findByRole("heading", { name: "Latest draft already exists" })).toBeInTheDocument();
      expect(
        screen.getByRole("button", {
          name: new RegExp(`^${escapeRegExp(targetName)} on 2026-03-22: assigned route, manually overridden$`)
        })
      ).toBeInTheDocument();

      await user.click(screen.getByRole("link", { name: "Open latest draft" }));

      expect(await screen.findByTestId("schedule-artifact-workpage-page")).toBeInTheDocument();
      expect(window.location.pathname).toBe(
        "/runs/wr-weekly-001/workpages/schedule-v0/artifacts/av-schedule-artifact-latest"
      );
    },
    90000
  );

  it("uses accepted-series navigation without traversing the draft rail", async () => {
    const user = userEvent.setup();
    server.use(
      http.get(
        "*/api/v1/workpages/workflow-runs/:workflowRunId/schedule-v0/artifacts/av-schedule-accepted-002",
        () =>
        HttpResponse.json(
          buildScheduleArtifactPayload("av-schedule-accepted-002", "wr-weekly-001", (payload) => {
            payload.actions = [];
            payload.artifact_context.artifact_kind = "planning.published_weekly_schedule.workbook";
            payload.artifact_state = {
              ...payload.artifact_state,
              artifact_kind: "planning.published_weekly_schedule.workbook",
              state_kind: "accepted",
              editable: false,
              current_artifact_version_id: "av-schedule-accepted-002",
              accepted_artifact_version_id: "av-schedule-accepted-002"
            };
            payload.accepted_series = {
              series_key: "weekly_schedule_planning.v1:dvc4:pitt-meadows",
              current_artifact_version_id: "av-schedule-accepted-002",
              previous_artifact_version_id: "av-schedule-accepted-001",
              next_artifact_version_id: null,
              entries: [
                {
                  artifact_version_id: "av-schedule-accepted-001",
                  workflow_run_id: "wr-weekly-000",
                  partition_key: "PW-2026-W12",
                  logical_date: "2026-03-15",
                  artifact_kind: "planning.published_weekly_schedule.workbook",
                  route: "/runs/wr-weekly-000/workpages/schedule-v0/artifacts/av-schedule-accepted-001"
                },
                {
                  artifact_version_id: "av-schedule-accepted-002",
                  workflow_run_id: "wr-weekly-001",
                  partition_key: "PW-2026-W13",
                  logical_date: "2026-03-22",
                  artifact_kind: "planning.published_weekly_schedule.workbook",
                  route: "/runs/wr-weekly-001/workpages/schedule-v0/artifacts/av-schedule-accepted-002"
                }
              ]
            };
            payload.draft_lineage = {
              current_artifact_version_id: "av-schedule-draft-011",
              latest_artifact_version_id: "av-schedule-draft-011",
              previous_artifact_version_id: "av-schedule-draft-010",
              recent_versions: [
                {
                  artifact_version_id: "av-schedule-draft-011",
                  supersedes_artifact_version_id: "av-schedule-draft-010"
                },
                {
                  artifact_version_id: "av-schedule-draft-010",
                  supersedes_artifact_version_id: null
                }
              ]
            };
            payload.artifact_history = {
              current_artifact_version_id: "av-schedule-draft-011",
              latest_artifact_version_id: "av-schedule-draft-011",
              previous_artifact_version_id: "av-schedule-draft-010",
              next_artifact_version_id: null,
              entries: [
                {
                  artifact_version_id: "av-schedule-draft-011",
                  workflow_run_id: "wr-weekly-001",
                  artifact_kind: "planning.draft_weekly_schedule.workbook",
                  created_at: "2026-03-22T18:00:00Z",
                  lineage_note: "Published from latest draft.",
                  supersedes_artifact_version_id: "av-schedule-draft-010",
                  route: "/runs/wr-weekly-001/workpages/schedule-v0/artifacts/av-schedule-draft-011"
                },
                {
                  artifact_version_id: "av-schedule-draft-010",
                  workflow_run_id: "wr-weekly-001",
                  artifact_kind: "planning.draft_weekly_schedule.workbook",
                  created_at: "2026-03-21T18:00:00Z",
                  lineage_note: "Initial Stage04 draft weekly schedule artifact.",
                  supersedes_artifact_version_id: null,
                  route: "/runs/wr-weekly-001/workpages/schedule-v0/artifacts/av-schedule-draft-010"
                }
              ]
            };
          })
        )
      ),
      http.get(
        "*/api/v1/workpages/workflow-runs/:workflowRunId/schedule-v0/artifacts/av-schedule-accepted-001",
        () =>
        HttpResponse.json(
          buildScheduleArtifactPayload("av-schedule-accepted-001", "wr-weekly-000", (payload) => {
            payload.actions = [];
            payload.artifact_context.artifact_kind = "planning.published_weekly_schedule.workbook";
            payload.artifact_state = {
              ...payload.artifact_state,
              artifact_kind: "planning.published_weekly_schedule.workbook",
              state_kind: "accepted",
              editable: false,
              current_artifact_version_id: "av-schedule-accepted-001",
              accepted_artifact_version_id: "av-schedule-accepted-001"
            };
            payload.accepted_series = {
              series_key: "weekly_schedule_planning.v1:dvc4:pitt-meadows",
              current_artifact_version_id: "av-schedule-accepted-001",
              previous_artifact_version_id: null,
              next_artifact_version_id: "av-schedule-accepted-002",
              entries: [
                {
                  artifact_version_id: "av-schedule-accepted-001",
                  workflow_run_id: "wr-weekly-000",
                  partition_key: "PW-2026-W12",
                  logical_date: "2026-03-15",
                  artifact_kind: "planning.published_weekly_schedule.workbook",
                  route: "/runs/wr-weekly-000/workpages/schedule-v0/artifacts/av-schedule-accepted-001"
                },
                {
                  artifact_version_id: "av-schedule-accepted-002",
                  workflow_run_id: "wr-weekly-001",
                  partition_key: "PW-2026-W13",
                  logical_date: "2026-03-22",
                  artifact_kind: "planning.published_weekly_schedule.workbook",
                  route: "/runs/wr-weekly-001/workpages/schedule-v0/artifacts/av-schedule-accepted-002"
                }
              ]
            };
          })
        )
      )
    );

    window.history.pushState(
      {},
      "",
      "/runs/wr-weekly-001/workpages/schedule-v0/artifacts/av-schedule-accepted-002"
    );
    render(<App />);

    expect(await screen.findByTestId("schedule-artifact-workpage-page")).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Accepted history" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Draft lineage" })).toBeInTheDocument();

    await user.click(screen.getByRole("link", { name: "Previous accepted" }));

    await waitFor(() => {
      expect(window.location.pathname).toBe(
        "/runs/wr-weekly-000/workpages/schedule-v0/artifacts/av-schedule-accepted-001"
      );
    });
  }, 30000);

  it(
    "keeps the last successful preview visible when a later preview fails",
    async () => {
      const user = userEvent.setup();
      window.history.pushState(
        {},
        "",
        "/runs/wr-weekly-001/workpages/schedule-v0/artifacts/av-schedule-artifact-001"
      );
      render(<App />);

      expect(await screen.findByTestId("schedule-artifact-workpage-page")).toBeInTheDocument();

      const heatmap = heatmapSection();
      const sourceCell = heatmapButton(
        heatmap,
        (label) => label.includes("2026-03-22: assigned route")
      );
      const targetCell = heatmapButton(
        heatmap,
        (label) => label.includes("2026-03-22: no planned work")
      );
      const sourceName = personNameFromLabel(sourceCell.getAttribute("aria-label") ?? "");
      const targetName = personNameFromLabel(targetCell.getAttribute("aria-label") ?? "");

      await user.click(sourceCell);
      await user.click(targetCell);

      await waitFor(() => {
        expect(mutationLog()).toContain("workpage-schedule-artifact-preview:av-schedule-artifact-001");
      });
      expect(await screen.findByText("Preview applied")).toBeInTheDocument();

      server.use(
        http.post(
          "*/api/v1/workpages/workflow-runs/:workflowRunId/schedule-v0/artifacts/:artifactVersionId/preview",
          () =>
            HttpResponse.json(
              {
                status: "error",
                error: {
                  code: "preview_unavailable",
                  message: "preview calculation failed"
                }
              },
              { status: 422 }
            )
        )
      );

      const secondSourceCell = heatmapButton(
        heatmap,
        (label) => label.includes(`${targetName} on 2026-03-22: assigned route`)
      );
      const secondTargetCell = heatmapButton(
        heatmap,
        (label) => label.includes(`${sourceName} on 2026-03-22: no planned work`)
      );

      await user.click(secondSourceCell);
      await user.click(secondTargetCell);

      expect(await screen.findByText(/preview_unavailable: preview calculation failed/i)).toBeInTheDocument();
      const selectedHeatmapDate = heatmap.querySelector(".schedule-heatmap__date-header--selected");
      expect(selectedHeatmapDate).not.toBeNull();
      expect(selectedHeatmapDate).toHaveTextContent("2026-03-24");
    },
    50000
  );

  it(
    "drops mismatched workspace subject context when saving schedule drafts directly",
    async () => {
      const user = userEvent.setup();
      const submitBodies: Array<Record<string, unknown>> = [];
      server.use(
        http.get(
          "*/api/v1/workpages/workflow-runs/:workflowRunId/schedule-v0/artifacts/av-schedule-artifact-001",
          () => HttpResponse.json(buildScheduleArtifactPayload("av-schedule-artifact-001"))
        ),
        http.post(
          "*/api/v1/workpages/workflow-runs/:workflowRunId/schedule-v0/artifacts/:artifactVersionId/submit",
          async ({ params, request }) => {
            submitBodies.push((await request.json()) as Record<string, unknown>);
            return HttpResponse.json({
              status: "ok",
              command: "api.workpages.artifact.submit",
              submitted: {
                workflow_run_id: "wr-weekly-001",
                artifact_version_id: "av-schedule-artifact-010",
                supersedes_artifact_version_id: String(params.artifactVersionId),
                route: "/runs/wr-weekly-001/workpages/schedule-v0/artifacts/av-schedule-artifact-010"
              }
            });
          }
        ),
        http.get(
          "*/api/v1/workpages/workflow-runs/:workflowRunId/schedule-v0/artifacts/av-schedule-artifact-010",
          () => HttpResponse.json(buildScheduleArtifactPayload("av-schedule-artifact-010"))
        )
      );

      window.history.pushState(
        {
          workpageActionRef: {
            action_id: "workpage.schedule-v0.open_latest_draft",
            workpage_kind: "schedule-v0",
            workflow_run_id: "wr-other-run",
            artifact_version_id: "av-schedule-artifact-001",
            subject: {
              subject_kind: "human_task",
              subject_id: "ht-stage04-001"
            }
          }
        },
        "",
        "/runs/wr-weekly-001/workpages/schedule-v0/artifacts/av-schedule-artifact-001"
      );
      render(<App />);

      await screen.findByTestId("schedule-artifact-workpage-page");
      await user.click(screen.getByRole("button", { name: "Save draft" }));

      await waitFor(() => {
        expect(window.location.pathname).toBe(
          "/runs/wr-weekly-001/workpages/schedule-v0/artifacts/av-schedule-artifact-010"
        );
      });

      expect(submitBodies).toHaveLength(1);
      expect(submitBodies[0]).toMatchObject({
        action_ref: {
          action_id: "workpage.schedule-v0.save_draft",
          workpage_kind: "schedule-v0",
          workflow_run_id: "wr-weekly-001",
          artifact_version_id: "av-schedule-artifact-001",
          subject: null
        }
      });
    },
    60000
  );

  it(
    "supports same-day assignment to reserve swaps in the heatmap",
    async () => {
      const user = userEvent.setup();
      window.history.pushState(
        {},
        "",
        "/runs/wr-weekly-001/workpages/schedule-v0/artifacts/av-schedule-artifact-001"
      );
      render(<App />);

      expect(await screen.findByTestId("schedule-artifact-workpage-page")).toBeInTheDocument();

      const heatmap = heatmapSection();
      const assignmentCell = heatmapButton(
        heatmap,
        (label) => label.includes("2026-03-22: assigned route")
      );
      const reserveCell = heatmapButton(
        heatmap,
        (label) => label.includes("2026-03-22: on call")
      );
      const assignmentName = personNameFromLabel(assignmentCell.getAttribute("aria-label") ?? "");
      const reserveName = personNameFromLabel(reserveCell.getAttribute("aria-label") ?? "");

      await user.click(assignmentCell);
      await user.click(reserveCell);

      expect(
        within(heatmap).getByRole("button", {
          name: new RegExp(`^${escapeRegExp(reserveName)} on 2026-03-22: assigned route, manually overridden$`)
        })
      ).toBeInTheDocument();
      expect(
        within(heatmap).getByRole("button", {
          name: new RegExp(`^${escapeRegExp(assignmentName)} on 2026-03-22: on call, manually overridden$`)
        })
      ).toBeInTheDocument();
    },
    30000
  );
});
