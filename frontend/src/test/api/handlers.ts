import { http, HttpResponse } from "msw";
import type {
  ArtifactVersionRow,
  HumanTaskRow,
  HumanTaskSubgraph
} from "@/lib/types/contracts";
import eodRunArtifactCreateResponseSnapshot from "@fixtures/workpage_eod_v0_run_artifact_create_response.json";
import eodRunWorkpageStateSnapshot from "@fixtures/workpage_eod_v0_run_state.json";
import driverPreferencesArtifactCreateResponseSnapshot from "@fixtures/workpage_driver_preferences_v0_artifact_create_response.json";
import driverPreferencesArtifactStateSnapshot from "@fixtures/workpage_driver_preferences_v0_artifact_state.json";
import driverPreferencesArtifactSubmitResponseSnapshot from "@fixtures/workpage_driver_preferences_v0_artifact_submit_response.json";
import driverPreferencesRunWorkpageStateSnapshot from "@fixtures/workpage_driver_preferences_v0_run_state.json";
import routeDemandArtifactStateSnapshot from "@fixtures/workpage_route_demand_v0_artifact_state.json";
import routeDemandArtifactSubmitResponseSnapshot from "@fixtures/workpage_route_demand_v0_artifact_submit_response.json";
import routeDemandRunWorkpageStateSnapshot from "@fixtures/workpage_route_demand_v0_run_state.json";
import scheduleArtifactStateSnapshot from "@fixtures/workpage_schedule_v0_artifact_state.json";
import scheduleArtifactSubmitResponseSnapshot from "@fixtures/workpage_schedule_v0_artifact_submit_response.json";
import scheduleRunWorkpageStateSnapshot from "@fixtures/workpage_schedule_v0_run_state.json";
import {
  buildEodArtifactSubmitResponse,
  buildEodArtifactWorkpageState
} from "@/test/workpages/eodArtifactFixture";

import {
  buildBoardContract,
  buildWorkflowRunDetail,
  buildWorkflowRunWorkspace,
  createContractState
} from "@/test/api/contractState";

const ok = (payload: Record<string, unknown>) => HttpResponse.json({ status: "ok", ...payload });

let state = createContractState();
let eodArtifactVersionCounter = 0;
let scheduleArtifactVersionCounter = 0;
let routeDemandArtifactVersionCounter = 0;
let driverPreferencesArtifactVersionCounter = 0;
let driverAvailabilityExceptionCounter = 0;
const eodArtifactVersions = new Map<string, EodArtifactVersionState>();
const scheduleArtifactVersions = new Map<string, ScheduleArtifactVersionState>();
const routeDemandArtifactVersions = new Map<string, RouteDemandArtifactVersionState>();
const driverPreferencesArtifactVersions = new Map<string, DriverPreferencesArtifactVersionState>();
const driverAvailabilityExceptions = new Map<string, DriverAvailabilityExceptionState>();
const EOD_WORKFLOW_RUN_ID = "wr-eod-artifact-001";
const SCHEDULE_WORKFLOW_RUN_ID = "wr-weekly-001";
const FUTURE_ROUTE_DEMAND_WORKFLOW_RUN_ID = "wr-weekly-002";
const CURRENT_WEEKLY_PLANNING_WEEK_ID = "PW-2026-W10";
const FUTURE_WEEKLY_PLANNING_WEEK_ID = "PW-2026-W14";

interface ArtifactWorkpageVersionState {
  artifactVersionId: string;
  workflowRunId: string;
  fileName: string;
  createdAt: string;
  lineageNote: string | null;
  payload: Record<string, unknown>;
  supersedesArtifactVersionId: string | null;
  supersededByArtifactVersionId: string | null;
  latestInChainArtifactVersionId: string;
}

type EodArtifactVersionState = ArtifactWorkpageVersionState;

interface ScheduleArtifactVersionState extends ArtifactWorkpageVersionState {
  workbookPayload: {
    columns: string[];
    rows: Array<Array<unknown>>;
    reserve_rows: Array<Record<string, unknown>>;
    iteration_deltas: Array<Record<string, unknown>>;
  };
}

interface RouteDemandArtifactVersionState extends ArtifactWorkpageVersionState {
  dayCards: Array<Record<string, unknown>>;
  scheduleImpact: Record<string, unknown>;
  futureWeekSeed?: boolean;
}

interface DriverPreferencesArtifactVersionState extends ArtifactWorkpageVersionState {
  preferenceGrid: {
    service_dates: Array<Record<string, unknown>>;
    weekdays: string[];
    drivers: Array<Record<string, unknown>>;
  };
  scheduleImpact: Record<string, unknown>;
}

interface DriverAvailabilityExceptionState {
  exception_id: string;
  driver_id: string;
  driver_name: string;
  start_date: string;
  end_date: string;
  reason_code: string;
  reason_note: string;
  status: "approved";
  source_workflow_run_id: string;
  source_artifact_version_id: string;
  affected_planning_week_ids: string[];
  source_weekly_workflow_run_id: string;
}

function nowIso(): string {
  return new Date().toISOString();
}

function cloneJson<T>(value: T): T {
  return structuredClone(value);
}

function nextEodArtifactVersionId(): string {
  eodArtifactVersionCounter += 1;
  return `av-eod-artifact-${String(eodArtifactVersionCounter).padStart(3, "0")}`;
}

function nextScheduleArtifactVersionId(): string {
  scheduleArtifactVersionCounter += 1;
  return `av-schedule-artifact-${String(scheduleArtifactVersionCounter).padStart(3, "0")}`;
}

function nextRouteDemandArtifactVersionId(): string {
  routeDemandArtifactVersionCounter += 1;
  return `av-route-demand-artifact-${String(routeDemandArtifactVersionCounter).padStart(3, "0")}`;
}

function nextDriverPreferencesArtifactVersionId(): string {
  driverPreferencesArtifactVersionCounter += 1;
  return `av-driver-preferences-artifact-${String(driverPreferencesArtifactVersionCounter).padStart(3, "0")}`;
}

function nextDriverAvailabilityExceptionId(): string {
  driverAvailabilityExceptionCounter += 1;
  return `ae-driver-availability-${String(driverAvailabilityExceptionCounter).padStart(3, "0")}`;
}

function artifactRoute(artifactVersionId: string, workflowRunId: string): string {
  return `/runs/${workflowRunId}/workpages/eod-v0/artifacts/${artifactVersionId}`;
}

function scheduleArtifactRoute(artifactVersionId: string, workflowRunId: string): string {
  return `/runs/${workflowRunId}/workpages/schedule-v0/artifacts/${artifactVersionId}`;
}

function routeDemandArtifactRoute(artifactVersionId: string, workflowRunId: string): string {
  return `/runs/${workflowRunId}/workpages/route-demand-v0/artifacts/${artifactVersionId}`;
}

function driverPreferencesArtifactRoute(
  artifactVersionId: string,
  workflowRunId: string
): string {
  return `/runs/${workflowRunId}/workpages/driver-preferences-v0/artifacts/${artifactVersionId}`;
}

function driverPreferencesSnapshotCreatePath(workflowRunId: string): string {
  return `/api/v1/workpages/workflow-runs/${workflowRunId}/driver-preferences-v0/snapshots`;
}

function sortArtifactRowsAscending(left: ArtifactVersionRow, right: ArtifactVersionRow): number {
  const createdAtCompare = left.created_at.localeCompare(right.created_at);
  if (createdAtCompare !== 0) {
    return createdAtCompare;
  }
  return left.artifact_version_id.localeCompare(right.artifact_version_id);
}

function sortArtifactRowsDescending(left: ArtifactVersionRow, right: ArtifactVersionRow): number {
  return sortArtifactRowsAscending(right, left);
}

function buildArtifactHistoryPayload(
  rows: ArtifactVersionRow[],
  currentArtifactVersionId: string | null,
  routeBuilder: (row: ArtifactVersionRow) => string
): Record<string, unknown> {
  const sortedRows = [...rows].sort(sortArtifactRowsDescending);
  const currentIndex =
    currentArtifactVersionId === null
      ? -1
      : sortedRows.findIndex((row) => row.artifact_version_id === currentArtifactVersionId);
  return {
    current_artifact_version_id: currentArtifactVersionId,
    latest_artifact_version_id: sortedRows[0]?.artifact_version_id ?? null,
    previous_artifact_version_id:
      currentIndex >= 0 && currentIndex + 1 < sortedRows.length
        ? sortedRows[currentIndex + 1]?.artifact_version_id ?? null
        : null,
    next_artifact_version_id:
      currentIndex > 0 ? sortedRows[currentIndex - 1]?.artifact_version_id ?? null : null,
    entries: sortedRows.map((row) => ({
      artifact_version_id: row.artifact_version_id,
      workflow_run_id: row.workflow_run_id,
      artifact_kind: row.artifact_kind,
      created_at: row.created_at,
      lineage_note: row.lineage_note,
      supersedes_artifact_version_id: row.supersedes_artifact_version_id,
      route: routeBuilder(row)
    }))
  };
}

function eodArtifactFileName(artifactVersionId: string): string {
  return `dispatch_reporting_stage03_${artifactVersionId}.xlsx`;
}

function scheduleArtifactFileName(artifactVersionId: string): string {
  return `weekly_schedule_stage04_${artifactVersionId}.json`;
}

function routeDemandArtifactFileName(artifactVersionId: string): string {
  return `route_demand_stage04_${artifactVersionId}.json`;
}

function driverPreferencesArtifactFileName(artifactVersionId: string): string {
  return `driver_preferences_stage04_${artifactVersionId}.json`;
}

function findSectionByKind(payload: Record<string, unknown>, kind: string): Record<string, unknown> | null {
  const workpage = payload.workpage;
  if (!workpage || typeof workpage !== "object" || Array.isArray(workpage)) {
    return null;
  }
  const sections = (workpage as Record<string, unknown>).sections;
  if (!Array.isArray(sections)) {
    return null;
  }
  return (
    sections.find(
      (section) =>
        section &&
        typeof section === "object" &&
        !Array.isArray(section) &&
        (section as Record<string, unknown>).kind === kind
    ) as Record<string, unknown> | undefined
  ) ?? null;
}

function findTableSectionById(
  payload: Record<string, unknown>,
  tableId: string
): Record<string, unknown> | null {
  const workpage = payload.workpage;
  if (!workpage || typeof workpage !== "object" || Array.isArray(workpage)) {
    return null;
  }
  const sections = (workpage as Record<string, unknown>).sections;
  if (!Array.isArray(sections)) {
    return null;
  }
  return (
    sections.find(
      (section) =>
        section &&
        typeof section === "object" &&
        !Array.isArray(section) &&
        (section as Record<string, unknown>).table_id === tableId
    ) as Record<string, unknown> | undefined
  ) ?? null;
}

function asString(value: unknown): string {
  return typeof value === "string" ? value : String(value ?? "");
}

function asStringOrNull(value: unknown): string | null {
  return typeof value === "string" ? value : null;
}

function asNumber(value: unknown): number {
  if (typeof value === "number" && Number.isFinite(value)) {
    return value;
  }
  const parsed = Number(asString(value));
  return Number.isFinite(parsed) ? parsed : 0;
}

function asObject(value: unknown): Record<string, unknown> | null {
  return value && typeof value === "object" && !Array.isArray(value)
    ? (value as Record<string, unknown>)
    : null;
}

function asObjectArray(value: unknown): Array<Record<string, unknown>> {
  return Array.isArray(value)
    ? value.filter(
        (entry): entry is Record<string, unknown> =>
          Boolean(entry) && typeof entry === "object" && !Array.isArray(entry)
      )
    : [];
}

function weekdayKeyForServiceDate(serviceDate: string): string | null {
  const parsed = new Date(`${serviceDate}T00:00:00Z`);
  if (Number.isNaN(parsed.getTime())) {
    return null;
  }
  return ["sun", "mon", "tue", "wed", "thu", "fri", "sat"][parsed.getUTCDay()] ?? null;
}

function driverPreferenceStateForServiceDate(
  preferenceGrid: DriverPreferencesArtifactVersionState["preferenceGrid"] | null,
  driverId: string,
  serviceDate: string
): string {
  if (!preferenceGrid) {
    return "neutral";
  }
  const weekdayKey = weekdayKeyForServiceDate(serviceDate);
  if (!weekdayKey) {
    return "unset";
  }
  const driverRow = preferenceGrid.drivers.find(
    (row) => asString(row.driver_id) === driverId
  );
  const preferencesByWeekday = asObject(driverRow?.preferences_by_weekday);
  const rawValue = weekdayKey ? asStringOrNull(preferencesByWeekday?.[weekdayKey]) : null;
  return rawValue ?? "unset";
}

function cloneDriverPreferenceGrid(
  value: DriverPreferencesArtifactVersionState["preferenceGrid"]
): DriverPreferencesArtifactVersionState["preferenceGrid"] {
  return {
    service_dates: value.service_dates.map((serviceDate) => ({ ...serviceDate })),
    weekdays: [...value.weekdays],
    drivers: value.drivers.map((row) => ({
      ...row,
      preferences_by_weekday: { ...asObject(row.preferences_by_weekday) }
    }))
  };
}

function buildDriverPreferencesGrid(
  preferenceGrid?: DriverPreferencesArtifactVersionState["preferenceGrid"]
): DriverPreferencesArtifactVersionState["preferenceGrid"] {
  const baseGrid = cloneJson(
    (driverPreferencesArtifactStateSnapshot.workpage_state.preference_grid ?? {
      service_dates: [],
      weekdays: ["sun", "mon", "tue", "wed", "thu", "fri", "sat"],
      drivers: []
    }) as DriverPreferencesArtifactVersionState["preferenceGrid"]
  );
  const nextGrid = preferenceGrid ?? baseGrid;
  return cloneDriverPreferenceGrid(nextGrid);
}

function buildDriverPreferencesScheduleImpact(
  scheduleImpact?: Record<string, unknown>
): Record<string, unknown> {
  return cloneJson(
    scheduleImpact ?? driverPreferencesArtifactStateSnapshot.workpage_state.schedule_impact
  ) as Record<string, unknown>;
}

function driverPreferencesVersionsForRun(
  workflowRunId: string
): DriverPreferencesArtifactVersionState[] {
  return Array.from(driverPreferencesArtifactVersions.values())
    .filter((version) => version.workflowRunId === workflowRunId)
    .sort((left, right) => {
      const createdAtCompare = right.createdAt.localeCompare(left.createdAt);
      if (createdAtCompare !== 0) {
        return createdAtCompare;
      }
      return right.artifactVersionId.localeCompare(left.artifactVersionId);
    });
}

function scheduleVersionsForRun(workflowRunId: string): ScheduleArtifactVersionState[] {
  return Array.from(scheduleArtifactVersions.values())
    .filter((version) => version.workflowRunId === workflowRunId)
    .sort((left, right) => {
      const createdAtCompare = right.createdAt.localeCompare(left.createdAt);
      if (createdAtCompare !== 0) {
        return createdAtCompare;
      }
      return right.artifactVersionId.localeCompare(left.artifactVersionId);
    });
}

function scheduleWorkbookPayloadFromPayload(
  payload: Record<string, unknown>
): ScheduleArtifactVersionState["workbookPayload"] {
  const assignmentSection = findTableSectionById(payload, "assignment_rows");
  const reserveSection = findTableSectionById(payload, "reserve_rows");
  const iterationSection = findTableSectionById(payload, "iteration_deltas");
  const columns = Array.isArray(assignmentSection?.columns)
    ? assignmentSection.columns
        .map((column) =>
          column && typeof column === "object" && !Array.isArray(column)
            ? String((column as Record<string, unknown>).key ?? "")
            : ""
        )
        .filter((value): value is string => value.length > 0)
    : [];
  const assignmentRows = asObjectArray(assignmentSection?.rows);
  return {
    columns,
    rows: assignmentRows.map((row) => columns.map((column) => row[column] ?? null)),
    reserve_rows: asObjectArray(reserveSection?.rows).map((row) => ({ ...row })),
    iteration_deltas: asObjectArray(iterationSection?.rows).map((row) => ({ ...row }))
  };
}

function buildWorkpageActionRef(input: {
  actionId: string;
  workpageKind: string;
  workflowRunId: string;
  artifactVersionId: string | null;
}): Record<string, unknown> {
  return {
    action_id: input.actionId,
    workpage_kind: input.workpageKind,
    workflow_run_id: input.workflowRunId,
    artifact_version_id: input.artifactVersionId,
    subject: null
  };
}

function buildDriverPreferencesScheduleAction(
  workflowRunId: string
): Record<string, unknown> {
  const latestVersion = latestDriverPreferencesArtifactForRun(workflowRunId);
  if (latestVersion) {
    return {
      action_id: "workpage.driver-preferences-v0.open_latest",
      artifact_version_id: latestVersion.artifactVersionId,
      kind: "open_latest",
      label: "Open driver preferences",
      route: driverPreferencesArtifactRoute(latestVersion.artifactVersionId, workflowRunId),
      state: "available",
      workpage_kind: "driver-preferences-v0",
      action_ref: buildWorkpageActionRef({
        actionId: "workpage.driver-preferences-v0.open_latest",
        workpageKind: "driver-preferences-v0",
        workflowRunId,
        artifactVersionId: latestVersion.artifactVersionId
      })
    };
  }
  return {
    action_id: "workpage.driver-preferences-v0.create_snapshot",
    artifact_version_id: null,
    kind: "create_snapshot",
    label: "Create driver preferences snapshot",
    create_path: driverPreferencesSnapshotCreatePath(workflowRunId),
    state: "available",
    workpage_kind: "driver-preferences-v0",
    action_ref: buildWorkpageActionRef({
      actionId: "workpage.driver-preferences-v0.create_snapshot",
      workpageKind: "driver-preferences-v0",
      workflowRunId,
      artifactVersionId: null
    })
  };
}

function driverAvailabilityExceptionCreatePath(workflowRunId: string): string {
  return `/api/v1/workpages/workflow-runs/${workflowRunId}/driver-preferences-v0/availability-exceptions`;
}

function buildDriverAvailabilityExceptionAction(workflowRunId: string): Record<string, unknown> {
  return {
    action_id: "workpage.driver-preferences-v0.add_availability_exception",
    artifact_version_id: null,
    kind: "add_availability_exception",
    label: "Add availability exception",
    create_path: driverAvailabilityExceptionCreatePath(workflowRunId),
    state: "available",
    workpage_kind: "driver-preferences-v0",
    action_ref: buildWorkpageActionRef({
      actionId: "workpage.driver-preferences-v0.add_availability_exception",
      workpageKind: "driver-preferences-v0",
      workflowRunId,
      artifactVersionId: null
    })
  };
}

function buildScheduleSickNoShowAction(
  workflowRunId: string,
  artifactVersionId: string
): Record<string, unknown> {
  return {
    action_id: "workpage.schedule-v0.mark_sick_no_show",
    artifact_version_id: artifactVersionId,
    kind: "mark_sick_no_show",
    label: "Mark Sick / No Show",
    sick_no_show_path: `/api/v1/workpages/workflow-runs/${workflowRunId}/schedule-v0/artifacts/${artifactVersionId}/sick-no-show`,
    state: "available",
    workpage_kind: "schedule-v0",
    action_ref: buildWorkpageActionRef({
      actionId: "workpage.schedule-v0.mark_sick_no_show",
      workpageKind: "schedule-v0",
      workflowRunId,
      artifactVersionId
    })
  };
}

function serializeDriverAvailabilityException(
  item: DriverAvailabilityExceptionState
): Record<string, unknown> {
  return {
    exception_id: item.exception_id,
    driver_id: item.driver_id,
    driver_name: item.driver_name,
    start_date: item.start_date,
    end_date: item.end_date,
    reason_code: item.reason_code,
    reason_note: item.reason_note,
    status: item.status,
    source_workflow_run_id: item.source_workflow_run_id,
    source_artifact_version_id: item.source_artifact_version_id,
    affected_planning_week_ids: item.affected_planning_week_ids
  };
}

function buildDriverAvailabilityExceptionsPayload(
  workflowRunId = SCHEDULE_WORKFLOW_RUN_ID
): Record<string, unknown> {
  const serviceDates =
    latestDriverPreferencesArtifactForRun(workflowRunId)?.preferenceGrid.service_dates.map((item) =>
      asString(item.service_date)
    ) ?? buildDriverPreferencesGrid().service_dates.map((item) => asString(item.service_date));
  const weeklyStartDate = serviceDates[0] ?? "";
  const weeklyEndDate = serviceDates[serviceDates.length - 1] ?? "";
  const sortedItems = Array.from(driverAvailabilityExceptions.values()).sort((left, right) => {
    const dateCompare = left.start_date.localeCompare(right.start_date);
    if (dateCompare !== 0) {
      return dateCompare;
    }
    return left.driver_name.localeCompare(right.driver_name);
  });
  return {
    items: sortedItems
      .filter((item) => {
        if (!weeklyStartDate || !weeklyEndDate) {
          return true;
        }
        return item.start_date <= weeklyEndDate && item.end_date >= weeklyStartDate;
      })
      .map(serializeDriverAvailabilityException),
    future_items: sortedItems
      .filter((item) => {
        if (!weeklyStartDate || !weeklyEndDate) {
          return false;
        }
        return (
          item.start_date > weeklyEndDate &&
          item.source_weekly_workflow_run_id === workflowRunId
        );
      })
      .map(serializeDriverAvailabilityException)
  };
}

function scheduleActionPath(
  workflowRunId: string,
  artifactVersionId: string,
  action: "preview" | "submit"
): string {
  return `/api/v1/workpages/workflow-runs/${workflowRunId}/schedule-v0/artifacts/${artifactVersionId}/${action}`;
}

function scheduleHeatmapPeople(
  payload: Record<string, unknown>
): Array<{ driver_id: string; driver_name: string }> {
  const heatmapSection = findSectionByKind(payload, "schedule_heatmap");
  return asObjectArray(heatmapSection?.people).map((person) => ({
    driver_id: asString(person.driver_id),
    driver_name: asString(person.driver_name)
  }));
}

function scheduleAssignmentRows(
  workbookPayload: ScheduleArtifactVersionState["workbookPayload"]
): Array<Record<string, unknown>> {
  return workbookPayload.rows.map((row) =>
    workbookPayload.columns.reduce<Record<string, unknown>>((record, column, columnIndex) => {
      record[column] = row[columnIndex] ?? null;
      return record;
    }, {})
  );
}

function updateScheduleCalculations(
  payload: Record<string, unknown>,
  workbookPayload: ScheduleArtifactVersionState["workbookPayload"],
  preferenceGrid?: DriverPreferencesArtifactVersionState["preferenceGrid"] | null
): void {
  const calculations = asObject(payload.calculations);
  if (!calculations) {
    return;
  }
  const topBar = asObject(calculations.top_bar);
  const selectedDay = asObject(calculations.selected_day);
  const topBarDays = asObjectArray(topBar?.days);
  const people = scheduleHeatmapPeople(payload);
  const assignmentRows = scheduleAssignmentRows(workbookPayload);
  const reserveRows = workbookPayload.reserve_rows.map((row) => ({ ...row }));
  const selectedServiceDate =
    asString(selectedDay?.service_date) || asString(topBarDays[0]?.service_date);
  const baseDriverMetrics = new Map(
    asObjectArray(calculations.driver_metrics).map((metric) => [asString(metric.driver_id), metric])
  );
  const driverIdsFromRows = new Set<string>();
  assignmentRows.forEach((row) => {
    const driverId = asString(row.assigned_driver_id).trim();
    if (driverId) {
      driverIdsFromRows.add(driverId);
    }
  });
  reserveRows.forEach((row) => {
    const driverId = asString(row.assigned_driver_id).trim();
    if (driverId) {
      driverIdsFromRows.add(driverId);
    }
  });
  const peopleById = new Map(
    [...people, ...Array.from(driverIdsFromRows).map((driverId) => ({ driver_id: driverId, driver_name: driverId }))].map(
      (person) => [person.driver_id, person]
    )
  );

  calculations.top_bar = {
    days: topBarDays.map((day) => {
      const serviceDate = asString(day.service_date);
      const routesRequired = asNumber(day.routes_required);
      const assignmentsForDay = assignmentRows.filter(
        (row) => asString(row.service_date) === serviceDate
      );
      const reservesForDay = reserveRows.filter(
        (row) => asString(row.service_date) === serviceDate
      );
      const staffedDrivers = new Set(
        [...assignmentsForDay, ...reservesForDay]
          .map((row) => asString(row.assigned_driver_id).trim())
          .filter((driverId) => driverId.length > 0)
      );
      const routesScheduled = assignmentsForDay.length;
      const onCallDrivers = reservesForDay.length;
      return {
        ...day,
        routes_scheduled: routesScheduled,
        on_call_drivers: onCallDrivers,
        total_staff: staffedDrivers.size,
        available_driver_count: Math.max(peopleById.size - staffedDrivers.size, 0),
        excess_capacity: routesScheduled + onCallDrivers - routesRequired,
        capacity_state: routesScheduled >= routesRequired ? "pass" : "fail",
        excess_capacity_target: asNumber(day.excess_capacity_target)
      };
    })
  };

  const selectedAssignments = assignmentRows.filter(
    (row) => asString(row.service_date) === selectedServiceDate
  );
  const selectedReserves = reserveRows.filter(
    (row) => asString(row.service_date) === selectedServiceDate
  );
  const busyDriverIds = new Set(
    [...selectedAssignments, ...selectedReserves]
      .map((row) => asString(row.assigned_driver_id).trim())
      .filter((driverId) => driverId.length > 0)
  );
  const availableDriverIds = Array.from(peopleById.keys()).filter(
    (driverId) => !busyDriverIds.has(driverId)
  );
  const availablePreferenceBuckets = {
    open_to_work: [] as string[],
    prefer_not_to_work: [] as string[],
    definitely_can_not_work: [] as string[],
    unset: [] as string[]
  };
  availableDriverIds.forEach((driverId) => {
    const preferenceState = driverPreferenceStateForServiceDate(
      preferenceGrid ?? null,
      driverId,
      selectedServiceDate
    );
    if (preferenceState === "open_to_work") {
      availablePreferenceBuckets.open_to_work.push(driverId);
      return;
    }
    if (preferenceState === "prefer_not_to_work") {
      availablePreferenceBuckets.prefer_not_to_work.push(driverId);
      return;
    }
    if (preferenceState === "definitely_can_not_work") {
      availablePreferenceBuckets.definitely_can_not_work.push(driverId);
      return;
    }
    availablePreferenceBuckets.unset.push(driverId);
  });
  calculations.selected_day = {
    ...selectedDay,
    service_date: selectedServiceDate,
    routes_required: asNumber(selectedDay?.routes_required),
    routes_scheduled: selectedAssignments.length,
    on_call_target: asNumber(selectedDay?.on_call_target),
    on_call_drivers: selectedReserves.length,
    available_driver_count: availableDriverIds.length,
    available_driver_ids: availableDriverIds,
    available_preference_buckets: availablePreferenceBuckets,
    drivers_available: availableDriverIds.length,
    projected_on_call_needed: Math.max(
      asNumber(selectedDay?.on_call_target) - selectedReserves.length,
      0
    ),
    open_questions:
      selectedAssignments.length < asNumber(selectedDay?.routes_required)
        ? "Review unfilled route coverage and confirm the final on-call posture before saving."
        : asString(selectedDay?.open_questions)
  };

  calculations.driver_metrics = Array.from(peopleById.values()).map((person) => {
    const assignmentsForDriver = assignmentRows.filter(
      (row) => asString(row.assigned_driver_id).trim() === person.driver_id
    );
    const reservesForDriver = reserveRows.filter(
      (row) => asString(row.assigned_driver_id).trim() === person.driver_id
    );
    const baseMetric = baseDriverMetrics.get(person.driver_id);
    const scheduledHours =
      assignmentsForDriver.reduce((total, row) => total + asNumber(row.projected_minutes), 0) / 60;
    const isBusyOnSelectedDay = busyDriverIds.has(person.driver_id);
    const availabilityState =
      !isBusyOnSelectedDay
        ? "available"
        : asString(baseMetric?.availability_state) || "scheduled";
    const availabilityConflict =
      asString(baseMetric?.availability_state) === "approved_unavailable" &&
      assignmentsForDriver.length > 0;
    const preferenceState = driverPreferenceStateForServiceDate(
      preferenceGrid ?? null,
      person.driver_id,
      selectedServiceDate
    );
    const scheduledHoursRounded = Number(scheduledHours.toFixed(1));
    const baseIssues = Array.isArray(baseMetric?.issues)
      ? baseMetric.issues.map((issue) => asString(issue)).filter((issue) => issue.length > 0)
      : [];
    return {
      driver_id: person.driver_id,
      driver_name: person.driver_name,
      scheduled_hours: scheduledHoursRounded,
      scheduled_routes: assignmentsForDriver.length,
      on_call_shifts: reservesForDriver.length,
      preference_state:
        preferenceGrid != null
          ? preferenceState
          : asString(baseMetric?.preference_state) || "neutral",
      availability_state: availabilityState,
      compliance_state: availabilityConflict ? "fail" : "pass",
      issues: availabilityConflict ? ["assigned_while_unavailable"] : baseIssues
    };
  });

  const topBarResults = asObjectArray(asObject(calculations.top_bar)?.days);
  const routesMissingDates = topBarResults
    .filter((day) => asNumber(day.routes_scheduled) < asNumber(day.routes_required))
    .map((day) => asString(day.service_date));
  const onCallMissingDates = topBarResults
    .filter((day) => asNumber(day.on_call_drivers) < asNumber(day.on_call_target))
    .map((day) => asString(day.service_date));
  const hardBlockedDrivers = asObjectArray(calculations.driver_metrics)
    .filter((metric) => asString(metric.compliance_state) !== "pass")
    .map((metric) => asString(metric.driver_id))
    .filter((driverId) => driverId.length > 0);
  const preferenceConflictDrivers = asObjectArray(calculations.driver_metrics)
    .filter((metric) => {
      const driverId = asString(metric.driver_id);
      if (!busyDriverIds.has(driverId)) {
        return false;
      }
      const preferenceState = asString(metric.preference_state);
      return (
        preferenceState === "prefer_not_to_work" ||
        preferenceState === "definitely_can_not_work"
      );
    })
    .map((metric) => asString(metric.driver_id))
    .filter((driverId) => driverId.length > 0);
  calculations.checks = [
    {
      check_id: "scheduled_capacity",
      label: "Routes within scheduled capacity",
      state: routesMissingDates.length > 0 ? "fail" : "pass",
      blocking: true,
      affected_service_dates: routesMissingDates
    },
    {
      check_id: "on_call_buffer",
      label: "On-call target coverage",
      state: onCallMissingDates.length > 0 ? "warn" : "pass",
      blocking: false,
      affected_service_dates: onCallMissingDates
    },
    {
      check_id: "hard_constraint_compliance",
      label: "Hard assignment compliance",
      state: hardBlockedDrivers.length > 0 ? "fail" : "pass",
      blocking: true,
      affected_driver_ids: hardBlockedDrivers
    },
    {
      check_id: "driver_preferences_alignment",
      label: "Driver preferences alignment",
      state: preferenceConflictDrivers.length > 0 ? "warn" : "pass",
      blocking: false,
      affected_driver_ids: preferenceConflictDrivers
    }
  ];
}

function patchArtifactPayloadLineage(version: ArtifactWorkpageVersionState): void {
  const payload = version.payload;
  const artifactContext = payload.artifact_context;
  if (artifactContext && typeof artifactContext === "object" && !Array.isArray(artifactContext)) {
    const artifactContextRecord = artifactContext as Record<string, unknown>;
    artifactContextRecord.artifact_version_id = version.artifactVersionId;
    artifactContextRecord.workflow_run_id = version.workflowRunId;
    artifactContextRecord.supersedes_artifact_version_id = version.supersedesArtifactVersionId;
    artifactContextRecord.superseded_by_artifact_version_id = version.supersededByArtifactVersionId;
    artifactContextRecord.latest_in_chain_artifact_version_id = version.latestInChainArtifactVersionId;
    artifactContextRecord.download_path = `/api/v1/artifacts/${version.artifactVersionId}/download.bin`;
  }

  const freshness = payload.freshness;
  if (freshness && typeof freshness === "object" && !Array.isArray(freshness)) {
    const freshnessRecord = freshness as Record<string, unknown>;
    freshnessRecord.generated_at = nowIso();
    freshnessRecord.source_version = version.artifactVersionId;
  }

  const source = payload.source;
  if (source && typeof source === "object" && !Array.isArray(source)) {
    (source as Record<string, unknown>).source_artifact_version_id = version.artifactVersionId;
  }

  const workpage = payload.workpage;
  if (workpage && typeof workpage === "object" && !Array.isArray(workpage)) {
    (workpage as Record<string, unknown>).source_artifact_version_id = version.artifactVersionId;
  }

  const historySection = findSectionByKind(payload, "history_stub");
  if (historySection) {
    historySection.entries = [
      {
        label: "Current artifact version",
        value: version.artifactVersionId
      },
      {
        label: "Supersedes",
        value: version.supersedesArtifactVersionId ?? "Initial draft"
      },
      {
        label: "Latest draft in chain",
        value: version.latestInChainArtifactVersionId
      }
    ];
  }

  if ("workbookPayload" in version) {
    patchScheduleArtifactContractState(version as ScheduleArtifactVersionState);
  }
}

function applyArtifactDraftEdits(
  payload: Record<string, unknown>,
  formValues: Record<string, unknown>,
  checklistValues: Array<{ item_id: string; selected: boolean; note: string }>
): void {
  const formSection = findSectionByKind(payload, "form");
  if (formSection) {
    const fields = formSection.fields;
    if (Array.isArray(fields)) {
      formSection.fields = fields.map((field) => {
        if (!field || typeof field !== "object" || Array.isArray(field)) {
          return field;
        }
        const fieldRecord = { ...(field as Record<string, unknown>) };
        const key = typeof fieldRecord.key === "string" ? fieldRecord.key : "";
        if (key && key in formValues) {
          fieldRecord.value = formValues[key];
        }
        return fieldRecord;
      });
    }
  }

  const checklistSection = findSectionByKind(payload, "checklist");
  if (checklistSection) {
    const items = checklistSection.items;
    if (Array.isArray(items) && items.length > 0) {
      const checklistById = new Map(checklistValues.map((value) => [value.item_id, value]));
      checklistSection.items = items.map((item) => {
        if (!item || typeof item !== "object" || Array.isArray(item)) {
          return item;
        }
        const itemRecord = { ...(item as Record<string, unknown>) };
        const itemId = typeof itemRecord.item_id === "string" ? itemRecord.item_id : "";
        const next = checklistById.get(itemId);
        if (next) {
          itemRecord.selected = next.selected;
          itemRecord.note = next.note;
        }
        return itemRecord;
      });
    }
  }
}

function buildEodArtifactPayload(input: {
  artifactVersionId: string;
  workflowRunId: string;
  supersedesArtifactVersionId: string | null;
  supersededByArtifactVersionId: string | null;
  latestInChainArtifactVersionId: string;
  formValues?: Record<string, unknown>;
  checklistValues?: Array<{ item_id: string; selected: boolean; note: string }>;
}): Record<string, unknown> {
  const payload = buildEodArtifactWorkpageState({
    artifactVersionId: input.artifactVersionId,
    workflowRunId: input.workflowRunId,
    supersedesArtifactVersionId: input.supersedesArtifactVersionId,
    supersededByArtifactVersionId: input.supersededByArtifactVersionId,
    latestArtifactVersionId: input.latestInChainArtifactVersionId,
    generatedAt: nowIso()
  });

  patchArtifactPayloadLineage({
    artifactVersionId: input.artifactVersionId,
    workflowRunId: input.workflowRunId,
    fileName: eodArtifactFileName(input.artifactVersionId),
    createdAt: nowIso(),
    lineageNote: input.supersedesArtifactVersionId
      ? "Submitted artifact-backed EOD draft version."
      : "Initial artifact-backed EOD draft seeded from Stage03 template.",
    payload,
    supersedesArtifactVersionId: input.supersedesArtifactVersionId,
    supersededByArtifactVersionId: input.supersededByArtifactVersionId,
    latestInChainArtifactVersionId: input.latestInChainArtifactVersionId
  });

  applyArtifactDraftEdits(payload, input.formValues ?? {}, input.checklistValues ?? []);
  return payload;
}

function patchEodArtifactContractState(version: EodArtifactVersionState): void {
  version.payload.artifact_history = buildArtifactHistoryPayload(
    Array.from(eodArtifactVersions.values())
      .filter((candidate) => candidate.workflowRunId === version.workflowRunId)
      .map(eodArtifactVersionRow),
    version.artifactVersionId,
    (row) => artifactRoute(row.artifact_version_id, row.workflow_run_id)
  );
}

function buildScheduleWorkbookPayload(
  assignmentRows?: Array<Record<string, unknown>>,
  reserveRows?: Array<Record<string, unknown>>
): ScheduleArtifactVersionState["workbookPayload"] {
  const payload = cloneJson(scheduleArtifactStateSnapshot.workpage_state) as Record<string, unknown>;
  const assignmentSection = findTableSectionById(payload, "assignment_rows");
  const reserveSection = findTableSectionById(payload, "reserve_rows");
  const iterationSection = findTableSectionById(payload, "iteration_deltas");
  const columns = Array.isArray(assignmentSection?.columns)
    ? assignmentSection.columns
        .map((column) =>
          column && typeof column === "object" && !Array.isArray(column)
            ? String((column as Record<string, unknown>).key ?? "")
            : ""
        )
        .filter((value): value is string => value.length > 0)
    : [];
  const baseAssignmentRows = Array.isArray(assignmentSection?.rows)
    ? assignmentSection.rows.map((row) =>
        row && typeof row === "object" && !Array.isArray(row) ? { ...(row as Record<string, unknown>) } : {}
      )
    : [];
  const baseReserveRows = Array.isArray(reserveSection?.rows)
    ? reserveSection.rows.map((row) =>
        row && typeof row === "object" && !Array.isArray(row) ? { ...(row as Record<string, unknown>) } : {}
      )
    : [];
  const baseIterationRows = Array.isArray(iterationSection?.rows)
    ? iterationSection.rows.map((row) =>
        row && typeof row === "object" && !Array.isArray(row) ? { ...(row as Record<string, unknown>) } : {}
      )
    : [];
  const nextAssignmentRows = assignmentRows ?? baseAssignmentRows;
  const nextReserveRows = reserveRows ?? baseReserveRows;
  return {
    columns,
    rows: nextAssignmentRows.map((row) => columns.map((column) => row[column] ?? null)),
    reserve_rows: nextReserveRows.map((row) => ({ ...row })),
    iteration_deltas: baseIterationRows.map((row) => ({ ...row })),
  };
}

function applyScheduleArtifactEdits(
  payload: Record<string, unknown>,
  workbookPayload: ScheduleArtifactVersionState["workbookPayload"],
  preferenceGrid?: DriverPreferencesArtifactVersionState["preferenceGrid"] | null
): void {
  const assignmentRows = scheduleAssignmentRows(workbookPayload);
  const assignmentSection = findTableSectionById(payload, "assignment_rows");
  if (assignmentSection) {
    assignmentSection.rows = assignmentRows.map((row) => ({ ...row }));
  }

  const reserveSection = findTableSectionById(payload, "reserve_rows");
  if (reserveSection) {
    reserveSection.rows = workbookPayload.reserve_rows.map((row) => ({ ...row }));
  }

  const iterationSection = findTableSectionById(payload, "iteration_deltas");
  if (iterationSection) {
    iterationSection.rows = workbookPayload.iteration_deltas.map((row) => ({ ...row }));
  }

  const workpage = payload.workpage;
  if (workpage && typeof workpage === "object" && !Array.isArray(workpage)) {
    const summary = (workpage as Record<string, unknown>).summary;
    if (summary && typeof summary === "object" && !Array.isArray(summary)) {
      const summaryRecord = summary as Record<string, unknown>;
      summaryRecord.route_assignment_count = assignmentRows.length;
      summaryRecord.reserve_assignment_count = workbookPayload.reserve_rows.length;
      summaryRecord.iteration_count = workbookPayload.iteration_deltas.length;
    }
  }

  updateScheduleCalculations(payload, workbookPayload, preferenceGrid);
}

function markSchedulePayloadSickNoShow(
  payload: Record<string, unknown>,
  {
    driverId,
    serviceDate,
  }: {
    driverId: string;
    serviceDate: string;
  }
): void {
  const heatmapSection = findSectionByKind(payload, "schedule_heatmap");
  const people = asObjectArray(heatmapSection?.people);
  people.forEach((person) => {
    if (asString(person.driver_id) !== driverId) {
      return;
    }
    asObjectArray(person.cells).forEach((cell) => {
      if (asString(cell.service_date) !== serviceDate) {
        return;
      }
      cell.availability_state = "approved_unavailable";
      cell.availability_reason_code = "sick_no_show";
      cell.availability_source_ref = `availability_exception:${driverId}:${serviceDate}`;
    });
  });

  const calculations = asObject(payload.calculations);
  const selectedDay = asObject(calculations?.selected_day);
  if (selectedDay && asString(selectedDay.service_date) === serviceDate) {
    selectedDay.available_driver_ids = (Array.isArray(selectedDay.available_driver_ids)
      ? selectedDay.available_driver_ids
      : []
    )
      .map((item) => asString(item))
      .filter((item) => item && item !== driverId);
    selectedDay.available_driver_count = Array.isArray(selectedDay.available_driver_ids)
      ? selectedDay.available_driver_ids.length
      : asNumber(selectedDay.available_driver_count);
  }
}

function buildScheduleArtifactPayload(input: {
  artifactVersionId: string;
  workflowRunId: string;
  supersedesArtifactVersionId: string | null;
  supersededByArtifactVersionId: string | null;
  latestInChainArtifactVersionId: string;
  workbookPayload: ScheduleArtifactVersionState["workbookPayload"];
}): Record<string, unknown> {
  const payload = cloneJson(scheduleArtifactStateSnapshot.workpage_state) as Record<string, unknown>;
  const workpage = payload.workpage as Record<string, unknown>;
  const source = payload.source as Record<string, unknown>;
  const freshness = payload.freshness as Record<string, unknown>;
  const artifactContext = payload.artifact_context as Record<string, unknown>;

  workpage.source_artifact_version_id = input.artifactVersionId;
  source.source_artifact_version_id = input.artifactVersionId;
  freshness.generated_at = nowIso();
  freshness.source_version = input.artifactVersionId;
  artifactContext.artifact_version_id = input.artifactVersionId;
  artifactContext.workflow_run_id = input.workflowRunId;
  artifactContext.supersedes_artifact_version_id = input.supersedesArtifactVersionId;
  artifactContext.superseded_by_artifact_version_id = input.supersededByArtifactVersionId;
  artifactContext.latest_in_chain_artifact_version_id = input.latestInChainArtifactVersionId;
  artifactContext.download_path = `/api/v1/artifacts/${input.artifactVersionId}/download.bin`;

  patchArtifactPayloadLineage({
    artifactVersionId: input.artifactVersionId,
    workflowRunId: input.workflowRunId,
    fileName: scheduleArtifactFileName(input.artifactVersionId),
    createdAt: nowIso(),
    lineageNote: input.supersedesArtifactVersionId
      ? "Submitted schedule draft artifact version."
      : "Initial Stage04 draft weekly schedule artifact.",
    payload,
    supersedesArtifactVersionId: input.supersedesArtifactVersionId,
    supersededByArtifactVersionId: input.supersededByArtifactVersionId,
    latestInChainArtifactVersionId: input.latestInChainArtifactVersionId
  });

  applyScheduleArtifactEdits(payload, input.workbookPayload);
  return payload;
}

function patchScheduleArtifactContractState(version: ScheduleArtifactVersionState): void {
  const payload = version.payload;
  ensureRouteDemandArtifactDraft(version.workflowRunId);
  const latestRouteDemandVersion = latestRouteDemandArtifactForRun(version.workflowRunId);
  const latestDriverPreferencesVersion = latestDriverPreferencesArtifactForRun(version.workflowRunId);
  const actions = Array.isArray(payload.actions) ? payload.actions : [];
  const mappedActions = actions
    .filter((action) => asObject(action)?.workpage_kind !== "driver-preferences-v0")
    .map((action) => {
    if (!action || typeof action !== "object" || Array.isArray(action)) {
      return action;
    }
    const record = { ...(action as Record<string, unknown>) };
    const kind = asString(record.kind);
    record.artifact_version_id = version.artifactVersionId;
    if (kind === "preview_recalc") {
      record.preview_path = scheduleActionPath(
        version.workflowRunId,
        version.artifactVersionId,
        "preview"
      );
      record.action_ref = buildWorkpageActionRef({
        actionId: asString(record.action_id),
        workpageKind: "schedule-v0",
        workflowRunId: version.workflowRunId,
        artifactVersionId: version.artifactVersionId
      });
    }
    if (kind === "submit_artifact") {
      record.submit_path = scheduleActionPath(
        version.workflowRunId,
        version.artifactVersionId,
        "submit"
      );
      record.action_ref = buildWorkpageActionRef({
        actionId: asString(record.action_id),
        workpageKind: "schedule-v0",
        workflowRunId: version.workflowRunId,
        artifactVersionId: version.artifactVersionId
      });
    }
    if (kind === "mark_sick_no_show") {
      record.sick_no_show_path =
        `/api/v1/workpages/workflow-runs/${version.workflowRunId}/schedule-v0/artifacts/${version.artifactVersionId}/sick-no-show`;
      record.action_ref = buildWorkpageActionRef({
        actionId: asString(record.action_id),
        workpageKind: "schedule-v0",
        workflowRunId: version.workflowRunId,
        artifactVersionId: version.artifactVersionId
      });
    }
    if (record.workpage_kind === "route-demand-v0" && kind === "open_latest") {
      record.artifact_version_id = latestRouteDemandVersion?.artifactVersionId ?? null;
      record.route = latestRouteDemandVersion
        ? routeDemandArtifactRoute(latestRouteDemandVersion.artifactVersionId, version.workflowRunId)
        : null;
      record.state = latestRouteDemandVersion ? "available" : "unavailable";
      record.action_ref = buildWorkpageActionRef({
        actionId: asString(record.action_id),
        workpageKind: "route-demand-v0",
        workflowRunId: version.workflowRunId,
        artifactVersionId: latestRouteDemandVersion?.artifactVersionId ?? null
      });
    }
    return record;
  });
  payload.actions = [
    ...mappedActions,
    ...(mappedActions.some((action) => asObject(action)?.kind === "mark_sick_no_show")
      ? []
      : [buildScheduleSickNoShowAction(version.workflowRunId, version.artifactVersionId)]),
    buildDriverPreferencesScheduleAction(version.workflowRunId)
  ];

  const artifactState = asObject(payload.artifact_state);
  if (artifactState) {
    artifactState.current_artifact_version_id = version.artifactVersionId;
    artifactState.latest_artifact_version_id = version.latestInChainArtifactVersionId;
    artifactState.accepted_artifact_version_id = null;
    artifactState.editable = true;
    artifactState.state_kind = "draft";
  }

  const draftLineage = asObject(payload.draft_lineage);
  if (draftLineage) {
    const recentVersions = scheduleVersionsForRun(version.workflowRunId)
      .slice(0, 5)
      .map((item) => ({
        artifact_version_id: item.artifactVersionId,
        supersedes_artifact_version_id: item.supersedesArtifactVersionId
      }));
    draftLineage.current_artifact_version_id = version.artifactVersionId;
    draftLineage.latest_artifact_version_id = version.latestInChainArtifactVersionId;
    draftLineage.previous_artifact_version_id = version.supersedesArtifactVersionId;
    draftLineage.recent_versions = recentVersions;
  }

  payload.artifact_history = buildArtifactHistoryPayload(
    scheduleVersionsForRun(version.workflowRunId).map(scheduleArtifactVersionRow),
    version.artifactVersionId,
    (row) => scheduleArtifactRoute(row.artifact_version_id, row.workflow_run_id)
  );

  const acceptedSeries = asObject(payload.accepted_series);
  if (acceptedSeries) {
    acceptedSeries.current_artifact_version_id = null;
    acceptedSeries.previous_artifact_version_id = null;
    acceptedSeries.next_artifact_version_id = null;
    acceptedSeries.entries = [];
  }

  const driverPreferencesDependency = asObjectArray(payload.dependencies).find(
    (row) => asString(row.dependency_key) === "driver_preferences"
  );
  if (driverPreferencesDependency) {
    const pinnedArtifactVersionId = asStringOrNull(driverPreferencesDependency.artifact_version_id);
    if (pinnedArtifactVersionId) {
      driverPreferencesDependency.state =
        latestDriverPreferencesVersion?.artifactVersionId === pinnedArtifactVersionId
          ? "aligned"
          : "drifted";
      driverPreferencesDependency.artifact_version_id = pinnedArtifactVersionId;
      driverPreferencesDependency.source_ref = `/api/v1/artifacts/${pinnedArtifactVersionId}`;
    } else if (latestDriverPreferencesVersion) {
      driverPreferencesDependency.state = "not_pinned";
      driverPreferencesDependency.artifact_version_id = null;
      driverPreferencesDependency.source_ref = null;
    } else {
      driverPreferencesDependency.state = "not_available";
      driverPreferencesDependency.artifact_version_id = null;
      driverPreferencesDependency.source_ref = null;
    }
  }

  const effectivePreferenceGrid =
    driverPreferencesDependency && asStringOrNull(driverPreferencesDependency.artifact_version_id)
      ? driverPreferencesArtifactVersions.get(
          asString(driverPreferencesDependency.artifact_version_id)
        )?.preferenceGrid ?? null
      : null;
  applyScheduleArtifactEdits(payload, version.workbookPayload, effectivePreferenceGrid);
}

function patchRunSchedulePayloadContractState(
  payload: Record<string, unknown>,
  workflowRunId: string
): void {
  const latestVersion = latestScheduleArtifactForRun(workflowRunId);
  ensureRouteDemandArtifactDraft(workflowRunId);
  const latestRouteDemandVersion = latestRouteDemandArtifactForRun(workflowRunId);
  const latestDriverPreferencesVersion = latestDriverPreferencesArtifactForRun(workflowRunId);
  const actions = Array.isArray(payload.actions) ? payload.actions : [];
  const mappedActions = actions
    .filter((action) => asObject(action)?.workpage_kind !== "driver-preferences-v0")
    .map((action) => {
    if (!action || typeof action !== "object" || Array.isArray(action)) {
      return action;
    }
    const record = { ...(action as Record<string, unknown>) };
    if (asString(record.kind) === "open_latest_draft") {
      record.state = latestVersion ? "available" : "unavailable";
      record.route = latestVersion
        ? scheduleArtifactRoute(latestVersion.artifactVersionId, workflowRunId)
        : null;
      record.artifact_version_id = latestVersion?.artifactVersionId ?? null;
      record.action_ref = buildWorkpageActionRef({
        actionId: asString(record.action_id),
        workpageKind: "schedule-v0",
        workflowRunId,
        artifactVersionId: latestVersion?.artifactVersionId ?? null
      });
    }
    if (record.workpage_kind === "route-demand-v0" && asString(record.kind) === "open_latest") {
      record.state = latestRouteDemandVersion ? "available" : "unavailable";
      record.route = latestRouteDemandVersion
        ? routeDemandArtifactRoute(latestRouteDemandVersion.artifactVersionId, workflowRunId)
        : null;
      record.artifact_version_id = latestRouteDemandVersion?.artifactVersionId ?? null;
      record.action_ref = buildWorkpageActionRef({
        actionId: asString(record.action_id),
        workpageKind: "route-demand-v0",
        workflowRunId,
        artifactVersionId: latestRouteDemandVersion?.artifactVersionId ?? null
      });
    }
    return record;
  });
  payload.actions = [...mappedActions, buildDriverPreferencesScheduleAction(workflowRunId)];

  const artifactState = asObject(payload.artifact_state);
  if (artifactState) {
    artifactState.current_artifact_version_id = null;
    artifactState.latest_artifact_version_id = latestVersion?.artifactVersionId ?? null;
    artifactState.accepted_artifact_version_id = null;
    artifactState.state_kind = "run_projection";
    artifactState.editable = false;
  }

  const driverPreferencesDependency = asObjectArray(payload.dependencies).find(
    (row) => asString(row.dependency_key) === "driver_preferences"
  );
  if (driverPreferencesDependency) {
    driverPreferencesDependency.artifact_version_id = latestDriverPreferencesVersion?.artifactVersionId ?? null;
    driverPreferencesDependency.source_ref = latestDriverPreferencesVersion
      ? `/api/v1/artifacts/${latestDriverPreferencesVersion.artifactVersionId}`
      : null;
    driverPreferencesDependency.state = latestDriverPreferencesVersion ? "resolved" : "not_available";
  }

  applyScheduleArtifactEdits(
    payload,
    latestVersion?.workbookPayload ?? scheduleWorkbookPayloadFromPayload(payload),
    latestDriverPreferencesVersion?.preferenceGrid ?? null
  );
}

function addEodArtifactVersion(input: {
  artifactVersionId: string;
  workflowRunId: string;
  supersedesArtifactVersionId: string | null;
  supersededByArtifactVersionId?: string | null;
  latestInChainArtifactVersionId: string;
  formValues?: Record<string, unknown>;
  checklistValues?: Array<{ item_id: string; selected: boolean; note: string }>;
}): EodArtifactVersionState {
  const createdAt = nowIso();
  const version: EodArtifactVersionState = {
    artifactVersionId: input.artifactVersionId,
    workflowRunId: input.workflowRunId,
    fileName: eodArtifactFileName(input.artifactVersionId),
    createdAt,
    lineageNote: input.supersedesArtifactVersionId
      ? "Submitted artifact-backed EOD draft version."
      : "Initial artifact-backed EOD draft seeded from Stage03 template.",
    payload: buildEodArtifactPayload({
      artifactVersionId: input.artifactVersionId,
      workflowRunId: input.workflowRunId,
      supersedesArtifactVersionId: input.supersedesArtifactVersionId,
      supersededByArtifactVersionId: input.supersededByArtifactVersionId ?? null,
      latestInChainArtifactVersionId: input.latestInChainArtifactVersionId,
      formValues: input.formValues,
      checklistValues: input.checklistValues
    }),
    supersedesArtifactVersionId: input.supersedesArtifactVersionId,
    supersededByArtifactVersionId: input.supersededByArtifactVersionId ?? null,
    latestInChainArtifactVersionId: input.latestInChainArtifactVersionId
  };
  eodArtifactVersions.set(version.artifactVersionId, version);
  patchEodArtifactContractState(version);
  return version;
}

function eodArtifactVersionRow(version: EodArtifactVersionState): ArtifactVersionRow {
  return {
    artifact_version_id: version.artifactVersionId,
    workflow_run_id: version.workflowRunId,
    task_run_id: null,
    artifact_kind: "reporting.upd_draft.workbook",
    artifact_role: "",
    media_type: "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    storage_uri: `memory://workpages/${version.fileName}`,
    content_digest: `sha256:${version.artifactVersionId}`,
    byte_size: 1024,
    metadata_json: {
      file_name: version.fileName,
      service_date: "2026-03-16",
      station_code: "DVC4",
      dsp_name: "QDCI"
    },
    parent_artifact_version_id: version.supersedesArtifactVersionId,
    supersedes_artifact_version_id: version.supersedesArtifactVersionId,
    lineage_note: version.lineageNote,
    created_at: version.createdAt,
    links: [
      {
        artifact_version_id: version.artifactVersionId,
        workflow_run_id: version.workflowRunId,
        subject_kind: "workflow_run",
        subject_id: version.workflowRunId,
        relation_kind: "subject",
        created_at: version.createdAt,
        created_by_actor_id: null,
        created_by_actor_type: null
      }
    ]
  };
}

function addScheduleArtifactVersion(input: {
  artifactVersionId: string;
  workflowRunId: string;
  supersedesArtifactVersionId: string | null;
  supersededByArtifactVersionId?: string | null;
  latestInChainArtifactVersionId: string;
  assignmentRows?: Array<Record<string, unknown>>;
  reserveRows?: Array<Record<string, unknown>>;
}): ScheduleArtifactVersionState {
  const createdAt = nowIso();
  const workbookPayload = buildScheduleWorkbookPayload(input.assignmentRows, input.reserveRows);
  const version: ScheduleArtifactVersionState = {
    artifactVersionId: input.artifactVersionId,
    workflowRunId: input.workflowRunId,
    fileName: scheduleArtifactFileName(input.artifactVersionId),
    createdAt,
    lineageNote: input.supersedesArtifactVersionId
      ? "Submitted schedule draft artifact version."
      : "Initial Stage04 draft weekly schedule artifact.",
    payload: buildScheduleArtifactPayload({
      artifactVersionId: input.artifactVersionId,
      workflowRunId: input.workflowRunId,
      supersedesArtifactVersionId: input.supersedesArtifactVersionId,
      supersededByArtifactVersionId: input.supersededByArtifactVersionId ?? null,
      latestInChainArtifactVersionId: input.latestInChainArtifactVersionId,
      workbookPayload
    }),
    workbookPayload,
    supersedesArtifactVersionId: input.supersedesArtifactVersionId,
    supersededByArtifactVersionId: input.supersededByArtifactVersionId ?? null,
    latestInChainArtifactVersionId: input.latestInChainArtifactVersionId
  };
  scheduleArtifactVersions.set(version.artifactVersionId, version);
  patchScheduleArtifactContractState(version);
  return version;
}

function scheduleArtifactVersionRow(version: ScheduleArtifactVersionState): ArtifactVersionRow {
  return {
    artifact_version_id: version.artifactVersionId,
    workflow_run_id: version.workflowRunId,
    task_run_id: null,
    artifact_kind: "planning.draft_weekly_schedule.workbook",
    artifact_role: "",
    media_type: "application/json",
    storage_uri: `memory://workpages/${version.fileName}`,
    content_digest: `sha256:${version.artifactVersionId}`,
    byte_size: JSON.stringify(version.workbookPayload).length,
    metadata_json: {
      file_name: version.fileName,
      planning_week_id: "PW-2026-W13",
      station_code: "DVC4",
      workflow_family: "weekly_schedule_planning.v1"
    },
    parent_artifact_version_id: version.supersedesArtifactVersionId,
    supersedes_artifact_version_id: version.supersedesArtifactVersionId,
    lineage_note: version.lineageNote,
    created_at: version.createdAt,
    links: [
      {
        artifact_version_id: version.artifactVersionId,
        workflow_run_id: version.workflowRunId,
        subject_kind: "workflow_run",
        subject_id: version.workflowRunId,
        relation_kind: "subject",
        created_at: version.createdAt,
        created_by_actor_id: null,
        created_by_actor_type: null
      }
    ]
  };
}

function listWorkflowRunArtifacts(workflowRunId: string): ArtifactVersionRow[] {
  if (workflowRunId === SCHEDULE_WORKFLOW_RUN_ID) {
    ensureScheduleArtifactDraft(workflowRunId);
    ensureRouteDemandArtifactDraft(workflowRunId);
  }
  const eodArtifacts = Array.from(eodArtifactVersions.values())
    .filter((version) => version.workflowRunId === workflowRunId)
    .map(eodArtifactVersionRow);
  const scheduleArtifacts = Array.from(scheduleArtifactVersions.values())
    .filter((version) => version.workflowRunId === workflowRunId)
    .map(scheduleArtifactVersionRow);
  const routeDemandArtifacts = Array.from(routeDemandArtifactVersions.values())
    .filter((version) => version.workflowRunId === workflowRunId)
    .map(routeDemandArtifactVersionRow);
  const driverPreferencesArtifacts = Array.from(driverPreferencesArtifactVersions.values())
    .filter((version) => version.workflowRunId === workflowRunId)
    .map(driverPreferencesArtifactVersionRow);
  return [
    ...listArtifactsForSubject("workflow_run", workflowRunId),
    ...eodArtifacts,
    ...scheduleArtifacts,
    ...routeDemandArtifacts,
    ...driverPreferencesArtifacts
  ].sort(sortArtifactRowsAscending);
}

function updateEodArtifactChainLatest(artifactVersionId: string, latestArtifactVersionId: string): void {
  let currentArtifactVersionId: string | null = artifactVersionId;
  while (currentArtifactVersionId) {
    const version = eodArtifactVersions.get(currentArtifactVersionId);
    if (!version) {
      break;
    }
    version.latestInChainArtifactVersionId = latestArtifactVersionId;
    patchArtifactPayloadLineage(version);
    patchEodArtifactContractState(version);
    currentArtifactVersionId = version.supersedesArtifactVersionId;
  }
}

function latestEodArtifactForRun(workflowRunId: string): EodArtifactVersionState | null {
  return Array.from(eodArtifactVersions.values())
    .filter((version) => version.workflowRunId === workflowRunId)
    .sort((left, right) => {
      const createdAtCompare = right.createdAt.localeCompare(left.createdAt);
      if (createdAtCompare !== 0) {
        return createdAtCompare;
      }
      return right.artifactVersionId.localeCompare(left.artifactVersionId);
    })[0] ?? null;
}

function updateScheduleArtifactChainLatest(
  artifactVersionId: string,
  latestArtifactVersionId: string
): void {
  let currentArtifactVersionId: string | null = artifactVersionId;
  while (currentArtifactVersionId) {
    const version = scheduleArtifactVersions.get(currentArtifactVersionId);
    if (!version) {
      break;
    }
    version.latestInChainArtifactVersionId = latestArtifactVersionId;
    patchArtifactPayloadLineage(version);
    patchScheduleArtifactContractState(version);
    currentArtifactVersionId = version.supersedesArtifactVersionId;
  }
}

function latestScheduleArtifactForRun(workflowRunId: string): ScheduleArtifactVersionState | null {
  return Array.from(scheduleArtifactVersions.values())
    .filter((version) => version.workflowRunId === workflowRunId)
    .sort((left, right) => {
      const createdAtCompare = right.createdAt.localeCompare(left.createdAt);
      if (createdAtCompare !== 0) {
        return createdAtCompare;
      }
      return right.artifactVersionId.localeCompare(left.artifactVersionId);
    })[0] ?? null;
}

function ensureEodArtifactDraft(workflowRunId = EOD_WORKFLOW_RUN_ID): EodArtifactVersionState {
  const artifactVersionId = nextEodArtifactVersionId();
  return addEodArtifactVersion({
    artifactVersionId,
    workflowRunId,
    supersedesArtifactVersionId: null,
    latestInChainArtifactVersionId: artifactVersionId
  });
}

function ensureScheduleArtifactDraft(
  workflowRunId = SCHEDULE_WORKFLOW_RUN_ID
): ScheduleArtifactVersionState {
  ensureWeeklyPlanningRunState(workflowRunId);
  const existing = latestScheduleArtifactForRun(workflowRunId);
  if (existing) {
    return existing;
  }
  const artifactVersionId = nextScheduleArtifactVersionId();
  return addScheduleArtifactVersion({
    artifactVersionId,
    workflowRunId,
    supersedesArtifactVersionId: null,
    latestInChainArtifactVersionId: artifactVersionId
  });
}

function latestOrSeedScheduleArtifactForRun(
  workflowRunId: string
): ScheduleArtifactVersionState | null {
  const existing = latestScheduleArtifactForRun(workflowRunId);
  if (existing) {
    return existing;
  }
  if (workflowRunId === SCHEDULE_WORKFLOW_RUN_ID) {
    return ensureScheduleArtifactDraft(workflowRunId);
  }
  return null;
}

function eodArtifactCreateResponse(
  version: EodArtifactVersionState,
  workflowRunId: string
): Record<string, unknown> {
  const payload = cloneJson(eodRunArtifactCreateResponseSnapshot.create_response) as Record<
    string,
    unknown
  >;
  payload.draft = {
    artifact_version_id: version.artifactVersionId,
    route: artifactRoute(version.artifactVersionId, workflowRunId),
    workflow_run_id: version.workflowRunId
  };
  return payload;
}

function eodArtifactSubmitResponse(
  version: EodArtifactVersionState,
  supersedesArtifactVersionId: string
): Record<string, unknown> {
  return buildEodArtifactSubmitResponse({
    artifactVersionId: version.artifactVersionId,
    workflowRunId: version.workflowRunId,
    supersedesArtifactVersionId
  });
}

function scheduleArtifactSubmitResponse(
  version: ScheduleArtifactVersionState,
  supersedesArtifactVersionId: string
): Record<string, unknown> {
  const payload = cloneJson(
    scheduleArtifactSubmitResponseSnapshot.submit_response
  ) as Record<string, unknown>;
  payload.submitted = {
    artifact_version_id: version.artifactVersionId,
    route: scheduleArtifactRoute(version.artifactVersionId, version.workflowRunId),
    supersedes_artifact_version_id: supersedesArtifactVersionId,
    workflow_run_id: version.workflowRunId
  };
  return payload;
}

function schedulePreviewResponse(
  version: ScheduleArtifactVersionState,
  workbookPayload: ScheduleArtifactVersionState["workbookPayload"]
): Record<string, unknown> {
  const previewPayload = cloneJson(version.payload) as Record<string, unknown>;
  const driverPreferencesDependency = asObjectArray(previewPayload.dependencies).find(
    (row) => asString(row.dependency_key) === "driver_preferences"
  );
  const preferenceGrid =
    driverPreferencesDependency && asStringOrNull(driverPreferencesDependency.artifact_version_id)
      ? driverPreferencesArtifactVersions.get(
          asString(driverPreferencesDependency.artifact_version_id)
        )?.preferenceGrid ?? null
      : null;
  applyScheduleArtifactEdits(previewPayload, workbookPayload, preferenceGrid);
  const calculations = asObject(previewPayload.calculations) ?? {};
  const dependencies = Array.isArray(previewPayload.dependencies) ? previewPayload.dependencies : [];
  return {
    preview: {
      workflow_run_id: version.workflowRunId,
      artifact_version_id: version.artifactVersionId,
      dirty: true,
      dependency_state: "aligned",
      dependencies,
      calculations
    }
  };
}

function buildRouteDemandDayCards(
  dayCards?: Array<Record<string, unknown>>
): Array<Record<string, unknown>> {
  const baseCards = asObjectArray(routeDemandArtifactStateSnapshot.workpage_state.calculations.day_cards);
  const nextCards = dayCards ?? baseCards;
  return nextCards.map((card) => ({
    ...card,
    planned_route_count: asNumber(card.planned_route_count),
    standard_slot_count: asNumber(card.standard_slot_count),
    standard_early_slot_count: asNumber(card.standard_early_slot_count),
    standard_late_slot_count: asNumber(card.standard_late_slot_count),
    rescue_slot_count: asNumber(card.rescue_slot_count),
    overflow_slot_count: asNumber(card.overflow_slot_count),
    on_call_target: asNumber(card.on_call_target),
    excess_capacity_target: asNumber(card.excess_capacity_target)
  }));
}

function visibleRouteDemandDayCards(
  dayCards: Array<Record<string, unknown>>
): Array<Record<string, unknown>> {
  return dayCards.slice(0, 7);
}

function shiftIsoDate(date: string, days: number): string {
  const shifted = new Date(`${date}T00:00:00Z`);
  shifted.setUTCDate(shifted.getUTCDate() + days);
  return shifted.toISOString().slice(0, 10);
}

function zeroRouteDemandDayCard(
  card: Record<string, unknown>,
  serviceDate: string
): Record<string, unknown> {
  return {
    ...card,
    service_date: serviceDate,
    planned_route_count: 0,
    standard_slot_count: 0,
    standard_early_slot_count: 0,
    standard_late_slot_count: 0,
    rescue_slot_count: 0,
    overflow_slot_count: 0,
    on_call_target: 0,
    excess_capacity_target: 0,
    delta_from_previous_version: null
  };
}

function buildFutureRouteDemandSeedDayCards(
  sourceDayCards: Array<Record<string, unknown>>
): Array<Record<string, unknown>> {
  const currentVisibleWeek = visibleRouteDemandDayCards(sourceDayCards);
  const nextVisibleWeek =
    sourceDayCards.length >= 14
      ? sourceDayCards.slice(7, 14)
      : currentVisibleWeek.map((card) => ({
          ...card,
          service_date: shiftIsoDate(asString(card.service_date), 7)
        }));
  const hiddenHorizonWeek = nextVisibleWeek.map((card) => ({
    ...card,
    service_date: shiftIsoDate(asString(card.service_date), 7)
  }));
  return [
    ...nextVisibleWeek.map((card) => zeroRouteDemandDayCard(card, asString(card.service_date))),
    ...hiddenHorizonWeek.map((card) => zeroRouteDemandDayCard(card, asString(card.service_date)))
  ];
}

function buildRouteDemandFutureWeekOptions(workflowRunId: string): Array<Record<string, unknown>> {
  void workflowRunId;
  return [
    {
      option_id: "next_week",
      label: "Week 2",
      planning_week_id: "PW-2026-W14",
      start_date: "2026-03-29",
      end_date: "2026-04-04",
      date_range_label: "2026-03-29 to 2026-04-04"
    }
  ];
}

function buildRouteDemandFutureWeekActivation(input?: {
  workflowRunId?: string;
  state?: "idle" | "running" | "succeeded" | "failed";
  targetScheduleArtifactVersionId?: string | null;
  errorCode?: string | null;
  errorMessage?: string | null;
}): Record<string, unknown> {
  return {
    state: input?.state ?? "idle",
    status_label:
      input?.state === "running"
        ? "Agent working"
        : input?.state === "succeeded"
          ? "Draft ready"
          : input?.state === "failed"
            ? "Scheduling failed"
          : null,
    human_task_id: null,
    task_run_id: null,
    blocked_reason: input?.state === "failed" ? input?.errorCode ?? "stage04_run_failed" : null,
    target_workflow_run_id: input?.workflowRunId ?? null,
    target_schedule_route: input?.workflowRunId
      ? `/runs/${input.workflowRunId}/workpages/schedule-v0`
      : null,
    target_schedule_artifact_version_id: input?.targetScheduleArtifactVersionId ?? null,
    error_code: input?.errorCode ?? null,
    error_message: input?.errorMessage ?? null
  };
}

function patchRouteDemandArtifactContractState(version: RouteDemandArtifactVersionState): void {
  const payload = version.payload;
  const latestScheduleVersion = latestScheduleArtifactForRun(version.workflowRunId);
  const visibleDayCards = visibleRouteDemandDayCards(version.dayCards);
  const editable = version.latestInChainArtifactVersionId === version.artifactVersionId;
  payload.actions = [
    {
      action_id: "workpage.route-demand-v0.save",
      kind: "save",
      label: "Save route demand",
      state: editable ? "available" : "blocked",
      workpage_kind: "route-demand-v0",
      artifact_version_id: version.artifactVersionId,
      submit_path: `/api/v1/workpages/workflow-runs/${version.workflowRunId}/route-demand-v0/artifacts/${version.artifactVersionId}/submit`,
      action_ref: buildWorkpageActionRef({
        actionId: "workpage.route-demand-v0.save",
        workpageKind: "route-demand-v0",
        workflowRunId: version.workflowRunId,
        artifactVersionId: version.artifactVersionId
      }),
      disabled_reason: editable ? null : "historical_artifact_read_only"
    },
    ...(version.futureWeekSeed
      ? [
          {
            action_id: "workpage.route-demand-v0.save_and_run",
            kind: "save_and_run",
            label: "Save and run scheduling agent",
            state: editable ? "available" : "blocked",
            workpage_kind: "route-demand-v0",
            artifact_version_id: version.artifactVersionId,
            submit_path: `/api/v1/workpages/workflow-runs/${version.workflowRunId}/route-demand-v0/artifacts/${version.artifactVersionId}/save-and-run`,
            action_ref: buildWorkpageActionRef({
              actionId: "workpage.route-demand-v0.save_and_run",
              workpageKind: "route-demand-v0",
              workflowRunId: version.workflowRunId,
              artifactVersionId: version.artifactVersionId
            }),
            disabled_reason: editable ? null : "historical_artifact_read_only"
          }
        ]
      : editable
        ? [
            ...(latestScheduleVersion
              ? [
                  {
                    action_id: "workpage.route-demand-v0.save_and_run",
                    kind: "save_and_run",
                    label: "Run coverage agent",
                    state: "available",
                    workpage_kind: "route-demand-v0",
                    artifact_version_id: version.artifactVersionId,
                    submit_path:
                      `/api/v1/workpages/workflow-runs/${version.workflowRunId}/route-demand-v0/artifacts/` +
                      `${version.artifactVersionId}/save-and-run`,
                    action_ref: buildWorkpageActionRef({
                      actionId: "workpage.route-demand-v0.save_and_run",
                      workpageKind: "route-demand-v0",
                      workflowRunId: version.workflowRunId,
                      artifactVersionId: version.artifactVersionId
                    }),
                    disabled_reason: null
                  }
                ]
              : []),
            {
              action_id: "workpage.route-demand-v0.add_next_week",
              kind: "add_next_week",
              label: "Add a week",
              state: "available",
              workpage_kind: "route-demand-v0",
              artifact_version_id: null,
              create_path: `/api/v1/workpages/workflow-runs/${version.workflowRunId}/route-demand-v0/next-week`,
              action_ref: buildWorkpageActionRef({
                actionId: "workpage.route-demand-v0.add_next_week",
                workpageKind: "route-demand-v0",
                workflowRunId: version.workflowRunId,
                artifactVersionId: null
              }),
              disabled_reason: null
            }
          ]
        : [])
  ];

  const artifactState = asObject(payload.artifact_state);
  if (artifactState) {
    artifactState.current_artifact_version_id = version.artifactVersionId;
    artifactState.latest_artifact_version_id = version.latestInChainArtifactVersionId;
    artifactState.editable = editable;
    artifactState.state_kind = "artifact_projection";
  }

  const calculations = asObject(payload.calculations);
  if (calculations) {
    calculations.day_cards = version.dayCards.map((card) => ({ ...card }));
  }

  const workpage = asObject(payload.workpage);
  if (workpage) {
    const summary = asObject(workpage.summary);
    if (summary) {
      summary.service_day_count = visibleDayCards.length;
      summary.planned_route_total = visibleDayCards.reduce(
        (total, card) => total + asNumber(card.planned_route_count),
        0
      );
    }
  }

  const dailyRowsSection = findTableSectionById(payload, "route_demand_daily_rows");
  if (dailyRowsSection) {
    dailyRowsSection.rows = visibleDayCards.map((card) => ({
      service_date: asString(card.service_date),
      planned_route_count: asNumber(card.planned_route_count),
      standard_slot_count: asNumber(card.standard_slot_count),
      rescue_slot_count: asNumber(card.rescue_slot_count),
      overflow_slot_count: asNumber(card.overflow_slot_count),
      on_call_target: asNumber(card.on_call_target),
      excess_capacity_target: asNumber(card.excess_capacity_target)
    }));
  }

  const historySection = findSectionByKind(payload, "history_stub");
  if (historySection) {
    historySection.entries = [
      {
        label: "Current artifact version",
        value: version.artifactVersionId
      },
      {
        label: "Supersedes",
        value: version.supersedesArtifactVersionId ?? "Initial route demand version"
      },
      {
        label: "Latest route demand version",
        value: version.latestInChainArtifactVersionId
      }
    ];
  }

  payload.schedule_impact = {
    ...version.scheduleImpact,
    latest_schedule_draft_artifact_version_id: latestScheduleVersion?.artifactVersionId ?? null,
    latest_route_demand_artifact_version_id: version.latestInChainArtifactVersionId
  };
  payload.future_week_options = version.futureWeekSeed
    ? []
    : buildRouteDemandFutureWeekOptions(version.workflowRunId);
  payload.future_week_activation = buildRouteDemandFutureWeekActivation({
    workflowRunId: version.workflowRunId,
    targetScheduleArtifactVersionId: latestScheduleVersion?.artifactVersionId ?? null
  });
  payload.artifact_history = buildArtifactHistoryPayload(
    Array.from(routeDemandArtifactVersions.values())
      .filter((candidate) => candidate.workflowRunId === version.workflowRunId)
      .map(routeDemandArtifactVersionRow),
    version.artifactVersionId,
    (row) => routeDemandArtifactRoute(row.artifact_version_id, row.workflow_run_id)
  );
}

function buildRouteDemandArtifactPayload(input: {
  artifactVersionId: string;
  workflowRunId: string;
  supersedesArtifactVersionId: string | null;
  supersededByArtifactVersionId: string | null;
  latestInChainArtifactVersionId: string;
  dayCards: Array<Record<string, unknown>>;
  scheduleImpact: Record<string, unknown>;
  futureWeekSeed?: boolean;
}): Record<string, unknown> {
  const payload = cloneJson(routeDemandArtifactStateSnapshot.workpage_state) as Record<string, unknown>;
  const workpage = asObject(payload.workpage) ?? {};
  const source = asObject(payload.source) ?? {};
  const freshness = asObject(payload.freshness) ?? {};
  const artifactContext = asObject(payload.artifact_context) ?? {};

  workpage.source_artifact_version_id = input.artifactVersionId;
  source.source_artifact_version_id = input.artifactVersionId;
  freshness.generated_at = nowIso();
  freshness.source_version = input.artifactVersionId;
  artifactContext.artifact_version_id = input.artifactVersionId;
  artifactContext.workflow_run_id = input.workflowRunId;
  artifactContext.supersedes_artifact_version_id = input.supersedesArtifactVersionId;
  artifactContext.superseded_by_artifact_version_id = input.supersededByArtifactVersionId;
  artifactContext.latest_in_chain_artifact_version_id = input.latestInChainArtifactVersionId;
  artifactContext.download_path = `/api/v1/artifacts/${input.artifactVersionId}/download.bin`;

  payload.workpage = workpage;
  payload.source = source;
  payload.freshness = freshness;
  payload.artifact_context = artifactContext;
  payload.future_week_options = input.futureWeekSeed
    ? []
    : buildRouteDemandFutureWeekOptions(input.workflowRunId);
  payload.future_week_activation = buildRouteDemandFutureWeekActivation({
    workflowRunId: input.workflowRunId
  });

  const version: RouteDemandArtifactVersionState = {
    artifactVersionId: input.artifactVersionId,
    workflowRunId: input.workflowRunId,
    fileName: routeDemandArtifactFileName(input.artifactVersionId),
    createdAt: nowIso(),
    lineageNote: input.supersedesArtifactVersionId
      ? "Submitted route-demand artifact version."
      : "Initial Stage04 route-demand artifact.",
    payload,
    dayCards: input.dayCards.map((card) => ({ ...card })),
    scheduleImpact: { ...input.scheduleImpact },
    futureWeekSeed: Boolean(input.futureWeekSeed),
    supersedesArtifactVersionId: input.supersedesArtifactVersionId,
    supersededByArtifactVersionId: input.supersededByArtifactVersionId,
    latestInChainArtifactVersionId: input.latestInChainArtifactVersionId
  };

  patchArtifactPayloadLineage(version);
  patchRouteDemandArtifactContractState(version);
  return payload;
}

function addRouteDemandArtifactVersion(input: {
  artifactVersionId: string;
  workflowRunId: string;
  supersedesArtifactVersionId: string | null;
  supersededByArtifactVersionId?: string | null;
  latestInChainArtifactVersionId: string;
  dayCards?: Array<Record<string, unknown>>;
  scheduleImpact?: Record<string, unknown>;
  futureWeekSeed?: boolean;
}): RouteDemandArtifactVersionState {
  const createdAt = nowIso();
  const dayCards = buildRouteDemandDayCards(input.dayCards);
  const scheduleImpact = cloneJson(
    input.scheduleImpact ?? routeDemandArtifactStateSnapshot.workpage_state.schedule_impact
  ) as Record<string, unknown>;
  const version: RouteDemandArtifactVersionState = {
    artifactVersionId: input.artifactVersionId,
    workflowRunId: input.workflowRunId,
    fileName: routeDemandArtifactFileName(input.artifactVersionId),
    createdAt,
    lineageNote: input.supersedesArtifactVersionId
      ? "Submitted route-demand artifact version."
      : "Initial Stage04 route-demand artifact.",
    payload: buildRouteDemandArtifactPayload({
      artifactVersionId: input.artifactVersionId,
      workflowRunId: input.workflowRunId,
      supersedesArtifactVersionId: input.supersedesArtifactVersionId,
      supersededByArtifactVersionId: input.supersededByArtifactVersionId ?? null,
      latestInChainArtifactVersionId: input.latestInChainArtifactVersionId,
      dayCards,
      scheduleImpact,
      futureWeekSeed: input.futureWeekSeed
    }),
    dayCards,
    scheduleImpact,
    futureWeekSeed: Boolean(input.futureWeekSeed),
    supersedesArtifactVersionId: input.supersedesArtifactVersionId,
    supersededByArtifactVersionId: input.supersededByArtifactVersionId ?? null,
    latestInChainArtifactVersionId: input.latestInChainArtifactVersionId
  };
  routeDemandArtifactVersions.set(version.artifactVersionId, version);
  patchRouteDemandArtifactContractState(version);
  return version;
}

function routeDemandArtifactVersionRow(version: RouteDemandArtifactVersionState): ArtifactVersionRow {
  return {
    artifact_version_id: version.artifactVersionId,
    workflow_run_id: version.workflowRunId,
    task_run_id: null,
    artifact_kind: "planning.route_slot_requirements.workbook",
    artifact_role: "",
    media_type: "application/json",
    storage_uri: `memory://workpages/${version.fileName}`,
    content_digest: `sha256:${version.artifactVersionId}`,
    byte_size: JSON.stringify(version.dayCards).length,
    metadata_json: {
      file_name: version.fileName,
      planning_week_id: "PW-2026-W13",
      station_code: "DVC4",
      workflow_family: "weekly_schedule_planning.v1"
    },
    parent_artifact_version_id: version.supersedesArtifactVersionId,
    supersedes_artifact_version_id: version.supersedesArtifactVersionId,
    lineage_note: version.lineageNote,
    created_at: version.createdAt,
    links: [
      {
        artifact_version_id: version.artifactVersionId,
        workflow_run_id: version.workflowRunId,
        subject_kind: "workflow_run",
        subject_id: version.workflowRunId,
        relation_kind: "subject",
        created_at: version.createdAt,
        created_by_actor_id: null,
        created_by_actor_type: null
      }
    ]
  };
}

function updateRouteDemandArtifactChainLatest(
  artifactVersionId: string,
  latestArtifactVersionId: string
): void {
  let currentArtifactVersionId: string | null = artifactVersionId;
  while (currentArtifactVersionId) {
    const version = routeDemandArtifactVersions.get(currentArtifactVersionId);
    if (!version) {
      break;
    }
    version.latestInChainArtifactVersionId = latestArtifactVersionId;
    patchArtifactPayloadLineage(version);
    patchRouteDemandArtifactContractState(version);
    currentArtifactVersionId = version.supersedesArtifactVersionId;
  }
}

function latestRouteDemandArtifactForRun(workflowRunId: string): RouteDemandArtifactVersionState | null {
  return Array.from(routeDemandArtifactVersions.values())
    .filter((version) => version.workflowRunId === workflowRunId)
    .sort((left, right) => {
      const createdAtCompare = right.createdAt.localeCompare(left.createdAt);
      if (createdAtCompare !== 0) {
        return createdAtCompare;
      }
      return right.artifactVersionId.localeCompare(left.artifactVersionId);
    })[0] ?? null;
}

function ensureRouteDemandArtifactDraft(
  workflowRunId = SCHEDULE_WORKFLOW_RUN_ID
): RouteDemandArtifactVersionState {
  ensureWeeklyPlanningRunState(workflowRunId);
  const existing = latestRouteDemandArtifactForRun(workflowRunId);
  if (existing) {
    return existing;
  }
  const artifactVersionId = nextRouteDemandArtifactVersionId();
  return addRouteDemandArtifactVersion({
    artifactVersionId,
    workflowRunId,
    supersedesArtifactVersionId: null,
    latestInChainArtifactVersionId: artifactVersionId
  });
}

function ensureFutureRouteDemandArtifactDraft(
  sourceWorkflowRunId: string
): RouteDemandArtifactVersionState {
  ensureWeeklyPlanningRunState(sourceWorkflowRunId);
  ensureWeeklyPlanningRunState(FUTURE_ROUTE_DEMAND_WORKFLOW_RUN_ID);
  const existing = latestRouteDemandArtifactForRun(FUTURE_ROUTE_DEMAND_WORKFLOW_RUN_ID);
  if (existing) {
    return existing;
  }
  const sourceVersion = ensureRouteDemandArtifactDraft(sourceWorkflowRunId);
  const artifactVersionId = nextRouteDemandArtifactVersionId();
  return addRouteDemandArtifactVersion({
    artifactVersionId,
    workflowRunId: FUTURE_ROUTE_DEMAND_WORKFLOW_RUN_ID,
    supersedesArtifactVersionId: null,
    latestInChainArtifactVersionId: artifactVersionId,
    dayCards: buildFutureRouteDemandSeedDayCards(sourceVersion.dayCards),
    futureWeekSeed: true
  });
}

function routeDemandArtifactSubmitResponse(
  version: RouteDemandArtifactVersionState,
  supersedesArtifactVersionId: string
): Record<string, unknown> {
  const payload = cloneJson(
    routeDemandArtifactSubmitResponseSnapshot.submit_response
  ) as Record<string, unknown>;
  payload.submitted = {
    artifact_version_id: version.artifactVersionId,
    route: routeDemandArtifactRoute(version.artifactVersionId, version.workflowRunId),
    supersedes_artifact_version_id: supersedesArtifactVersionId,
    workflow_run_id: version.workflowRunId
  };
  return payload;
}

function routeDemandCoverageCandidatesPath(
  workflowRunId: string,
  artifactVersionId: string
): string {
  return (
    `/api/v1/workpages/workflow-runs/${workflowRunId}/schedule-v0/artifacts/` +
    `${artifactVersionId}/route-demand-coverage-candidates`
  );
}

function routeDemandCoverageApplyPath(
  workflowRunId: string,
  artifactVersionId: string
): string {
  return (
    `/api/v1/workpages/workflow-runs/${workflowRunId}/schedule-v0/artifacts/` +
    `${artifactVersionId}/route-demand-coverage`
  );
}

function buildRouteDemandDayCardsFromRequestedCounts(
  dayCards: Array<Record<string, unknown>>,
  dailyDemandRows?: Array<{
    service_date?: string;
    planned_route_count?: number;
  }>
): Array<Record<string, unknown>> {
  const requestedCounts = new Map(
    (dailyDemandRows ?? []).map((row) => [
      asString(row.service_date),
      asNumber(row.planned_route_count)
    ])
  );
  return dayCards.map((card) => {
    const serviceDate = asString(card.service_date);
    const currentCount = asNumber(card.planned_route_count);
    const nextCount = serviceDate && requestedCounts.has(serviceDate)
      ? Math.max(asNumber(requestedCounts.get(serviceDate)), 0)
      : currentCount;
    const delta = nextCount - currentCount;
    return {
      ...card,
      planned_route_count: nextCount,
      standard_slot_count: Math.max(asNumber(card.standard_slot_count) + delta, 0),
      delta_from_previous_version: {
        planned_route_count_delta: delta
      }
    };
  });
}

function routeDemandCoverageDeltas(
  version: RouteDemandArtifactVersionState,
  requestedServiceDates?: string[]
): Array<{
  service_date: string;
  previous_planned_route_count: number;
  planned_route_count: number;
  delta: number;
}> {
  const previousVersion = version.supersedesArtifactVersionId
    ? routeDemandArtifactVersions.get(version.supersedesArtifactVersionId) ?? null
    : null;
  const previousByDate = new Map(
    visibleRouteDemandDayCards(previousVersion?.dayCards ?? []).map((card) => [
      asString(card.service_date),
      asNumber(card.planned_route_count)
    ])
  );
  const requestedDates =
    requestedServiceDates && requestedServiceDates.length > 0
      ? new Set(requestedServiceDates)
      : null;
  return visibleRouteDemandDayCards(version.dayCards).reduce<
    Array<{
      service_date: string;
      previous_planned_route_count: number;
      planned_route_count: number;
      delta: number;
    }>
  >((accumulator, card) => {
    const serviceDate = asString(card.service_date);
    if (!serviceDate || (requestedDates && !requestedDates.has(serviceDate))) {
      return accumulator;
    }
    const previousCount = previousByDate.get(serviceDate) ?? asNumber(card.planned_route_count);
    const currentCount = asNumber(card.planned_route_count);
    const delta = Math.max(currentCount - previousCount, 0);
    if (delta <= 0) {
      return accumulator;
    }
    accumulator.push({
      service_date: serviceDate,
      previous_planned_route_count: previousCount,
      planned_route_count: currentCount,
      delta
    });
    return accumulator;
  }, []);
}

function buildRouteDemandCoverageContext(
  routeDemandVersion: RouteDemandArtifactVersionState,
  scheduleArtifactVersionId: string,
  requestedServiceDates?: string[]
): Record<string, unknown> {
  const deltas = routeDemandCoverageDeltas(routeDemandVersion, requestedServiceDates);
  return {
    workflow_run_id: routeDemandVersion.workflowRunId,
    schedule_artifact_version_id: scheduleArtifactVersionId,
    route_demand_artifact_version_id: routeDemandVersion.artifactVersionId,
    coverage_candidates_path: routeDemandCoverageCandidatesPath(
      routeDemandVersion.workflowRunId,
      scheduleArtifactVersionId
    ),
    coverage_apply_path: routeDemandCoverageApplyPath(
      routeDemandVersion.workflowRunId,
      scheduleArtifactVersionId
    ),
    service_dates: deltas.map((item) => item.service_date),
    added_route_count: deltas.reduce((total, item) => total + item.delta, 0),
    deltas
  };
}

function scheduleDriverNameMap(payload: Record<string, unknown>): Map<string, string> {
  const map = new Map<string, string>();
  scheduleHeatmapPeople(payload).forEach((person) => {
    if (person.driver_id) {
      map.set(person.driver_id, person.driver_name);
    }
  });
  asObjectArray(asObject(payload.calculations)?.driver_metrics).forEach((metric) => {
    const driverId = asString(metric.driver_id);
    const driverName = asString(metric.driver_name);
    if (driverId && driverName) {
      map.set(driverId, driverName);
    }
  });
  return map;
}

function clampRouteDemandCoverageMaxCandidates(value: unknown): number {
  const requested = asNumber(value);
  if (requested <= 0) {
    return 8;
  }
  return Math.min(requested, 20);
}

function routeDemandCoverageTargetSuffix(serviceDate: string, slotNumber: number): string {
  return `${serviceDate.replaceAll("-", "")}-cycle1-standard#${String(slotNumber).padStart(2, "0")}`;
}

function patchScheduleRouteDemandDependency(
  payload: Record<string, unknown>,
  routeDemandArtifactVersionId: string
): void {
  const routeDemandDependency = asObjectArray(payload.dependencies).find(
    (row) => asString(row.dependency_key) === "route_slot_requirements"
  );
  if (!routeDemandDependency) {
    return;
  }
  routeDemandDependency.artifact_version_id = routeDemandArtifactVersionId;
  routeDemandDependency.source_ref = `/api/v1/artifacts/${routeDemandArtifactVersionId}`;
  routeDemandDependency.state = "aligned";
}

function buildRouteDemandCoverageRecommendations(input: {
  scheduleVersion: ScheduleArtifactVersionState;
  routeDemandVersion: RouteDemandArtifactVersionState;
  assignmentRows: Array<Record<string, unknown>>;
  reserveRows: Array<Record<string, unknown>>;
  serviceDates?: string[];
  maxCandidates?: number;
}): Record<string, unknown> {
  const maxCandidates = clampRouteDemandCoverageMaxCandidates(input.maxCandidates);
  const deltas = routeDemandCoverageDeltas(input.routeDemandVersion, input.serviceDates);
  const driverNames = scheduleDriverNameMap(input.scheduleVersion.payload);
  const workloadRows = [...input.assignmentRows, ...input.reserveRows];
  const driverMetricsById = new Map(
    asObjectArray(asObject(input.scheduleVersion.payload.calculations)?.driver_metrics).map(
      (metric) => [asString(metric.driver_id), metric]
    )
  );
  const targets: Array<Record<string, unknown>> = [];
  const candidateGroups: Array<Record<string, unknown>> = [];

  for (const delta of deltas) {
    const reserveRowsForDate = input.reserveRows.filter(
      (row) =>
        asString(row.service_date) === delta.service_date &&
        asString(row.assigned_driver_id).trim().length > 0
    );
    const assignedRowsForDate = input.assignmentRows.filter(
      (row) =>
        asString(row.service_date) === delta.service_date &&
        asString(row.assigned_driver_id).trim().length > 0
    );
    for (let offset = 1; offset <= delta.delta; offset += 1) {
      const slotNumber = delta.previous_planned_route_count + offset;
      const routeSlotId = `slot-${routeDemandCoverageTargetSuffix(delta.service_date, slotNumber)}`;
      const routeId =
        `ROUTE-${delta.service_date.replaceAll("-", "")}-` +
        `${String(slotNumber).padStart(2, "0")}`;
      const targetId = `${input.routeDemandVersion.artifactVersionId}:${delta.service_date}:${offset}`;
      const target = {
        target_id: targetId,
        route_slot_id: routeSlotId,
        route_id: routeId,
        service_date: delta.service_date,
        route_slot_class: "standard",
        station_code: "DVC4",
        service_area: "Metro core",
        shift_start: "10:15",
        shift_end: "18:45",
        projected_minutes: 510,
        required_skill: "standard_delivery",
        vehicle_type: "cargo_van"
      };
      targets.push(target);

      const candidates: Array<Record<string, unknown>> = [];
      const selectableSources =
        reserveRowsForDate.length > 0
          ? reserveRowsForDate.slice(0, maxCandidates)
          : input.assignmentRows
              .filter(
                (row) =>
                  asString(row.service_date) !== delta.service_date &&
                  asString(row.assigned_driver_id).trim().length > 0
              )
              .slice(0, maxCandidates);
      selectableSources.forEach((row, sourceIndex) => {
        const driverId = asString(row.assigned_driver_id);
        const metric = driverMetricsById.get(driverId);
        const totalMinutes = workloadRows
          .filter((candidateRow) => asString(candidateRow.assigned_driver_id) === driverId)
          .reduce((total, candidateRow) => total + asNumber(candidateRow.projected_minutes), 0);
        const clearReserve =
          asString(row.assignment_status) === "reserve" ||
          asString(row.assignment_action) === "reserve" ||
          asString(row.route_id) === "ON_CALL";
        candidates.push({
          recommendation_rank: candidates.length + 1,
          target_id: targetId,
          route_slot_id: target.route_slot_id,
          route_id: target.route_id,
          service_date: target.service_date,
          driver_id: driverId,
          driver_name: driverNames.get(driverId) ?? driverId,
          selection_state: "selectable",
          hard_filter_status: "pass",
          hard_filter_reasons: [],
          score_bucket: sourceIndex === 0 ? "best_fit" : "good_fit",
          soft_score_total: Number((98 - sourceIndex * 4.5).toFixed(2)),
          projected_minutes: target.projected_minutes,
          availability_state:
            asString(metric?.availability_state) ||
            asString(row.availability_state) ||
            "AVAILABLE",
          current_week_shift_count: workloadRows.filter(
            (candidateRow) => asString(candidateRow.assigned_driver_id) === driverId
          ).length,
          projected_rolling7_minutes: totalMinutes + target.projected_minutes,
          remaining_rolling7_minutes: Math.max(
            3600 - (totalMinutes + target.projected_minutes),
            0
          ),
          fairness_balance: 0.12 + sourceIndex * 0.03,
          target_shift_gap: Math.max(5 - sourceIndex, 0),
          preference_fit: sourceIndex === 0 ? 1 : 0.82,
          preferred_shift_band_fit: sourceIndex === 0 ? 1 : 0.9,
          preferred_route_slot_class_fit: 1,
          seniority_preference_fit: 0.88,
          reliability_score: 0.95 - sourceIndex * 0.04,
          previous_week_stability: 0.9 - sourceIndex * 0.03,
          baseline_template_state:
            asString(row.baseline_template_state) || "white_template",
          planned_driver_day_state: clearReserve
            ? "on_call"
            : asString(row.planned_driver_day_state) || "assigned",
          new_agreement_required: Boolean(row.new_agreement_required),
          new_agreement_trigger_reason: asString(row.new_agreement_trigger_reason),
          template_state_preservation_fit:
            asNumber(row.template_state_preservation_fit) || 0.92,
          clear_same_day_on_call_reserve: clearReserve,
          reserve_route_slot_id: clearReserve ? asString(row.route_slot_id) : null,
          reserve_route_id: clearReserve ? asString(row.route_id) : null,
          assignment_action: clearReserve ? "promote_reserve" : "assign",
          evaluation_kind: clearReserve ? "reserve_promotion" : "cross_day_assignment"
        });
      });

      const blockedSource = assignedRowsForDate[0];
      if (blockedSource && candidates.length < maxCandidates) {
        const driverId = asString(blockedSource.assigned_driver_id);
        const totalMinutes = workloadRows
          .filter((candidateRow) => asString(candidateRow.assigned_driver_id) === driverId)
          .reduce((total, candidateRow) => total + asNumber(candidateRow.projected_minutes), 0);
        candidates.push({
          recommendation_rank: candidates.length + 1,
          target_id: targetId,
          route_slot_id: target.route_slot_id,
          route_id: target.route_id,
          service_date: target.service_date,
          driver_id: driverId,
          driver_name: driverNames.get(driverId) ?? driverId,
          selection_state: "blocked",
          hard_filter_status: "fail",
          hard_filter_reasons: ["already_assigned_that_day"],
          score_bucket: "blocked",
          soft_score_total: 0,
          projected_minutes: target.projected_minutes,
          availability_state:
            asString(driverMetricsById.get(driverId)?.availability_state) || "scheduled",
          current_week_shift_count: workloadRows.filter(
            (candidateRow) => asString(candidateRow.assigned_driver_id) === driverId
          ).length,
          projected_rolling7_minutes: totalMinutes + target.projected_minutes,
          remaining_rolling7_minutes: Math.max(
            3600 - (totalMinutes + target.projected_minutes),
            0
          ),
          fairness_balance: 0,
          target_shift_gap: 0,
          preference_fit: 0,
          preferred_shift_band_fit: 0,
          preferred_route_slot_class_fit: 0,
          seniority_preference_fit: 0,
          reliability_score: 0.6,
          previous_week_stability: 0.5,
          baseline_template_state:
            asString(blockedSource.baseline_template_state) || "assigned_template",
          planned_driver_day_state: "assigned",
          new_agreement_required: false,
          new_agreement_trigger_reason: "",
          template_state_preservation_fit: 0,
          clear_same_day_on_call_reserve: false,
          reserve_route_slot_id: null,
          reserve_route_id: null,
          assignment_action: "blocked",
          evaluation_kind: "same_day_conflict"
        });
      }

      candidateGroups.push({
        target,
        candidate_count: candidates.length,
        pass_candidate_count: candidates.filter(
          (candidate) =>
            asString(candidate.selection_state) === "selectable" &&
            asString(candidate.hard_filter_status) === "pass"
        ).length,
        candidates
      });
    }
  }
  const selectedDefaults = buildDistinctCoverageSelectedDefaults(candidateGroups);

  const dependencies = cloneJson(
    input.scheduleVersion.payload.dependencies
  ) as Array<Record<string, unknown>>;
  patchScheduleRouteDemandDependency(
    { dependencies },
    input.routeDemandVersion.artifactVersionId
  );
  return {
    workflow_run_id: input.scheduleVersion.workflowRunId,
    artifact_version_id: input.scheduleVersion.artifactVersionId,
    route_demand_artifact_version_id: input.routeDemandVersion.artifactVersionId,
    dependency_state: "aligned",
    dependencies,
    added_route_count: deltas.reduce((total, item) => total + item.delta, 0),
    target_count: targets.length,
    max_candidates: maxCandidates,
    targets,
    candidate_groups: candidateGroups,
    selected_defaults: selectedDefaults,
    diagnostic_reason: targets.length > 0 ? null : "no_positive_route_demand_increase"
  };
}

function isSelectableCoverageCandidate(candidate: Record<string, unknown>): boolean {
  return (
    asString(candidate.selection_state) === "selectable" &&
    asString(candidate.hard_filter_status) === "pass"
  );
}

function buildDistinctCoverageSelectedDefaults(
  candidateGroups: Array<Record<string, unknown>>
): Array<Record<string, unknown>> {
  const groupsByServiceDate = new Map<string, Array<Record<string, unknown>>>();
  candidateGroups.forEach((group) => {
    const target = asObject(group.target);
    const serviceDate = asString(target?.service_date);
    if (!serviceDate) {
      return;
    }
    const dayGroups = groupsByServiceDate.get(serviceDate) ?? [];
    dayGroups.push(group);
    groupsByServiceDate.set(serviceDate, dayGroups);
  });

  return Array.from(groupsByServiceDate.entries())
    .sort(([left], [right]) => left.localeCompare(right))
    .flatMap(([, dayGroups]) => bestDistinctCoverageDefaultsForServiceDate(dayGroups));
}

function bestDistinctCoverageDefaultsForServiceDate(
  candidateGroups: Array<Record<string, unknown>>
): Array<Record<string, unknown>> {
  const selectableOptions = candidateGroups.map((group) =>
    asObjectArray(group.candidates)
      .map((candidate, candidateIndex) => ({ candidate, candidateIndex }))
      .filter(({ candidate }) => isSelectableCoverageCandidate(candidate))
  );
  const driverMaskById = new Map<string, bigint>();
  selectableOptions.forEach((options) => {
    options.forEach(({ candidate }) => {
      const driverId = asString(candidate.driver_id);
      if (!driverId || driverMaskById.has(driverId)) {
        return;
      }
      driverMaskById.set(driverId, 1n << BigInt(driverMaskById.size));
    });
  });
  const skipOrderIndex = 99;
  const cache = new Map<
    string,
    {
      count: number;
      score: number;
      rankSum: number;
      orderKey: number[];
      assignments: Array<{ groupIndex: number; candidateIndex: number }>;
    }
  >();

  const better = (
    candidateSolution: {
      count: number;
      score: number;
      rankSum: number;
      orderKey: number[];
      assignments: Array<{ groupIndex: number; candidateIndex: number }>;
    },
    currentSolution: {
      count: number;
      score: number;
      rankSum: number;
      orderKey: number[];
      assignments: Array<{ groupIndex: number; candidateIndex: number }>;
    }
  ): boolean => {
    if (candidateSolution.count !== currentSolution.count) {
      return candidateSolution.count > currentSolution.count;
    }
    if (candidateSolution.score !== currentSolution.score) {
      return candidateSolution.score > currentSolution.score;
    }
    if (candidateSolution.rankSum !== currentSolution.rankSum) {
      return candidateSolution.rankSum < currentSolution.rankSum;
    }
    return candidateSolution.orderKey.join(",") < currentSolution.orderKey.join(",");
  };

  const solve = (
    groupIndex: number,
    usedDriverMask: bigint
  ): {
    count: number;
    score: number;
    rankSum: number;
    orderKey: number[];
    assignments: Array<{ groupIndex: number; candidateIndex: number }>;
  } => {
    if (groupIndex >= candidateGroups.length) {
      return {
        count: 0,
        score: 0,
        rankSum: 0,
        orderKey: [],
        assignments: []
      };
    }
    const cacheKey = `${groupIndex}:${usedDriverMask.toString()}`;
    const cached = cache.get(cacheKey);
    if (cached) {
      return cached;
    }

    const nextSolution = solve(groupIndex + 1, usedDriverMask);
    let bestSolution = {
      count: nextSolution.count,
      score: nextSolution.score,
      rankSum: nextSolution.rankSum,
      orderKey: [skipOrderIndex, ...nextSolution.orderKey],
      assignments: nextSolution.assignments
    };

    selectableOptions[groupIndex].forEach(({ candidate, candidateIndex }) => {
      const driverId = asString(candidate.driver_id);
      const driverMask = driverMaskById.get(driverId);
      if (!driverId || driverMask == null || (usedDriverMask & driverMask) !== 0n) {
        return;
      }
      const childSolution = solve(groupIndex + 1, usedDriverMask | driverMask);
      const candidateSolution = {
        count: childSolution.count + 1,
        score: childSolution.score + asNumber(candidate.soft_score_total),
        rankSum:
          childSolution.rankSum +
          (asNumber(candidate.recommendation_rank) || candidateIndex + 1),
        orderKey: [candidateIndex, ...childSolution.orderKey],
        assignments: [{ groupIndex, candidateIndex }, ...childSolution.assignments]
      };
      if (better(candidateSolution, bestSolution)) {
        bestSolution = candidateSolution;
      }
    });

    cache.set(cacheKey, bestSolution);
    return bestSolution;
  };

  return solve(0, 0n).assignments.map(({ groupIndex, candidateIndex }) => {
    const group = candidateGroups[groupIndex];
    const target = asObject(group.target) ?? {};
    const candidate = asObjectArray(group.candidates)[candidateIndex];
    return {
      target_id: asString(target.target_id),
      route_slot_id: asString(target.route_slot_id),
      driver_id: asString(candidate.driver_id),
      row_kind: "assignment"
    };
  });
}

function routeDemandArtifactCreateResponse(
  version: RouteDemandArtifactVersionState
): Record<string, unknown> {
  return {
    created: {
      artifact_version_id: version.artifactVersionId,
      route: routeDemandArtifactRoute(version.artifactVersionId, version.workflowRunId),
      workflow_run_id: version.workflowRunId
    }
  };
}

function ensureWeeklyPlanningRunState(workflowRunId: string): void {
  if (
    state.workflowRuns.some(
      (run) =>
        run.workflow_run_id === workflowRunId &&
        run.workflow_id === "weekly_schedule_planning.v1"
    )
  ) {
    return;
  }
  if (workflowRunId === SCHEDULE_WORKFLOW_RUN_ID) {
    state.workflowRuns.push(
      buildStoryRun({
        workflowRunId,
        workflowId: "weekly_schedule_planning.v1",
        partitionKey: CURRENT_WEEKLY_PLANNING_WEEK_ID,
        state: "OPEN",
        activeIssueCount: 1
      })
    );
    return;
  }
  if (workflowRunId === FUTURE_ROUTE_DEMAND_WORKFLOW_RUN_ID) {
    state.workflowRuns.push(
      buildStoryRun({
        workflowRunId,
        workflowId: "weekly_schedule_planning.v1",
        partitionKey: FUTURE_WEEKLY_PLANNING_WEEK_ID,
        state: "OPEN",
        activeIssueCount: 0
      })
    );
  }
}

function latestDriverPreferencesArtifactForRun(
  workflowRunId: string
): DriverPreferencesArtifactVersionState | null {
  return driverPreferencesVersionsForRun(workflowRunId)[0] ?? null;
}

function patchDriverPreferencesArtifactContractState(
  version: DriverPreferencesArtifactVersionState
): void {
  const payload = version.payload;
  const latestScheduleVersion = latestScheduleArtifactForRun(version.workflowRunId);
  const actions = Array.isArray(payload.actions) ? payload.actions : [];
  const patchedActions = actions.map((action) => {
    if (!action || typeof action !== "object" || Array.isArray(action)) {
      return action;
    }
    const record = { ...(action as Record<string, unknown>) };
    if (asString(record.kind) === "save") {
      record.artifact_version_id = version.artifactVersionId;
      record.submit_path =
        `/api/v1/workpages/workflow-runs/${version.workflowRunId}/driver-preferences-v0/artifacts/` +
        `${version.artifactVersionId}/submit`;
      record.state =
        version.latestInChainArtifactVersionId === version.artifactVersionId ? "available" : "blocked";
      record.disabled_reason =
        version.latestInChainArtifactVersionId === version.artifactVersionId
          ? null
          : "historical_artifact_read_only";
      record.action_ref = buildWorkpageActionRef({
        actionId: asString(record.action_id),
        workpageKind: "driver-preferences-v0",
        workflowRunId: version.workflowRunId,
        artifactVersionId: version.artifactVersionId
      });
    }
    return record;
  });
  payload.actions = patchedActions;
  if (
    !patchedActions.some(
      (action) => asString((action as Record<string, unknown>)?.kind) === "add_availability_exception"
    )
  ) {
    patchedActions.push(buildDriverAvailabilityExceptionAction(version.workflowRunId));
  }

  const artifactState = asObject(payload.artifact_state);
  if (artifactState) {
    artifactState.current_artifact_version_id = version.artifactVersionId;
    artifactState.latest_artifact_version_id = version.latestInChainArtifactVersionId;
    artifactState.editable = version.latestInChainArtifactVersionId === version.artifactVersionId;
    artifactState.state_kind = "artifact_projection";
  }

  payload.preference_grid = cloneDriverPreferenceGrid(version.preferenceGrid);
  payload.driver_availability_exceptions = buildDriverAvailabilityExceptionsPayload(
    version.workflowRunId
  );
  payload.schedule_impact = {
    ...version.scheduleImpact,
    latest_schedule_draft_artifact_version_id: latestScheduleVersion?.artifactVersionId ?? null,
    latest_driver_preferences_artifact_version_id: version.latestInChainArtifactVersionId
  };
  payload.artifact_history = buildArtifactHistoryPayload(
    driverPreferencesVersionsForRun(version.workflowRunId).map(driverPreferencesArtifactVersionRow),
    version.artifactVersionId,
    (row) => driverPreferencesArtifactRoute(row.artifact_version_id, row.workflow_run_id)
  );

  const workpage = asObject(payload.workpage);
  if (workpage) {
    const summary = asObject(workpage.summary);
    if (summary) {
      summary.driver_count = version.preferenceGrid.drivers.length;
      summary.explicit_preference_count = version.preferenceGrid.drivers.reduce(
        (total, row) =>
          total +
          Object.values(asObject(row.preferences_by_weekday) ?? {}).filter(
            (value) => typeof value === "string"
          )
            .length,
        0
      );
    }
  }

  const historySection = findSectionByKind(payload, "history_stub");
  if (historySection) {
    historySection.entries = [
      {
        label: "Current artifact version",
        value: version.artifactVersionId
      },
      {
        label: "Supersedes",
        value: version.supersedesArtifactVersionId ?? "Initial preferences snapshot"
      },
      {
        label: "Latest snapshot",
        value: version.latestInChainArtifactVersionId
      }
    ];
  }
}

function buildDriverPreferencesArtifactPayload(input: {
  artifactVersionId: string;
  workflowRunId: string;
  supersedesArtifactVersionId: string | null;
  supersededByArtifactVersionId: string | null;
  latestInChainArtifactVersionId: string;
  preferenceGrid: DriverPreferencesArtifactVersionState["preferenceGrid"];
  scheduleImpact: Record<string, unknown>;
}): Record<string, unknown> {
  const payload = cloneJson(
    driverPreferencesArtifactStateSnapshot.workpage_state
  ) as Record<string, unknown>;
  const workpage = asObject(payload.workpage) ?? {};
  const source = asObject(payload.source) ?? {};
  const freshness = asObject(payload.freshness) ?? {};
  const artifactContext = asObject(payload.artifact_context) ?? {};

  workpage.source_artifact_version_id = input.artifactVersionId;
  source.source_artifact_version_id = input.artifactVersionId;
  freshness.generated_at = nowIso();
  freshness.source_version = input.artifactVersionId;
  artifactContext.artifact_version_id = input.artifactVersionId;
  artifactContext.workflow_run_id = input.workflowRunId;
  artifactContext.supersedes_artifact_version_id = input.supersedesArtifactVersionId;
  artifactContext.superseded_by_artifact_version_id = input.supersededByArtifactVersionId;
  artifactContext.latest_in_chain_artifact_version_id = input.latestInChainArtifactVersionId;
  artifactContext.download_path = `/api/v1/artifacts/${input.artifactVersionId}/download.bin`;

  payload.workpage = workpage;
  payload.source = source;
  payload.freshness = freshness;
  payload.artifact_context = artifactContext;
  payload.driver_availability_exceptions = buildDriverAvailabilityExceptionsPayload(
    input.workflowRunId
  );

  const version: DriverPreferencesArtifactVersionState = {
    artifactVersionId: input.artifactVersionId,
    workflowRunId: input.workflowRunId,
    fileName: driverPreferencesArtifactFileName(input.artifactVersionId),
    createdAt: nowIso(),
    lineageNote: input.supersedesArtifactVersionId
      ? "Submitted driver-preferences snapshot version."
      : "Created initial driver preferences snapshot.",
    payload,
    preferenceGrid: cloneDriverPreferenceGrid(input.preferenceGrid),
    scheduleImpact: { ...input.scheduleImpact },
    supersedesArtifactVersionId: input.supersedesArtifactVersionId,
    supersededByArtifactVersionId: input.supersededByArtifactVersionId,
    latestInChainArtifactVersionId: input.latestInChainArtifactVersionId
  };

  patchArtifactPayloadLineage(version);
  patchDriverPreferencesArtifactContractState(version);
  return payload;
}

function addDriverPreferencesArtifactVersion(input: {
  artifactVersionId: string;
  workflowRunId: string;
  supersedesArtifactVersionId: string | null;
  supersededByArtifactVersionId?: string | null;
  latestInChainArtifactVersionId: string;
  preferenceGrid?: DriverPreferencesArtifactVersionState["preferenceGrid"];
  scheduleImpact?: Record<string, unknown>;
}): DriverPreferencesArtifactVersionState {
  const createdAt = nowIso();
  const preferenceGrid = buildDriverPreferencesGrid(input.preferenceGrid);
  const scheduleImpact = buildDriverPreferencesScheduleImpact(input.scheduleImpact);
  const version: DriverPreferencesArtifactVersionState = {
    artifactVersionId: input.artifactVersionId,
    workflowRunId: input.workflowRunId,
    fileName: driverPreferencesArtifactFileName(input.artifactVersionId),
    createdAt,
    lineageNote: input.supersedesArtifactVersionId
      ? "Submitted driver-preferences snapshot version."
      : "Created initial driver preferences snapshot.",
    payload: buildDriverPreferencesArtifactPayload({
      artifactVersionId: input.artifactVersionId,
      workflowRunId: input.workflowRunId,
      supersedesArtifactVersionId: input.supersedesArtifactVersionId,
      supersededByArtifactVersionId: input.supersededByArtifactVersionId ?? null,
      latestInChainArtifactVersionId: input.latestInChainArtifactVersionId,
      preferenceGrid,
      scheduleImpact
    }),
    preferenceGrid,
    scheduleImpact,
    supersedesArtifactVersionId: input.supersedesArtifactVersionId,
    supersededByArtifactVersionId: input.supersededByArtifactVersionId ?? null,
    latestInChainArtifactVersionId: input.latestInChainArtifactVersionId
  };
  driverPreferencesArtifactVersions.set(version.artifactVersionId, version);
  patchDriverPreferencesArtifactContractState(version);
  return version;
}

function driverPreferencesArtifactVersionRow(
  version: DriverPreferencesArtifactVersionState
): ArtifactVersionRow {
  return {
    artifact_version_id: version.artifactVersionId,
    workflow_run_id: version.workflowRunId,
    task_run_id: null,
    artifact_kind: "planning.driver_shift_preferences.workbook",
    artifact_role: "",
    media_type: "application/json",
    storage_uri: `memory://workpages/${version.fileName}`,
    content_digest: `sha256:${version.artifactVersionId}`,
    byte_size: JSON.stringify(version.preferenceGrid).length,
    metadata_json: {
      file_name: version.fileName,
      planning_week_id: "PW-2026-W13",
      station_code: "DVC4",
      workflow_family: "weekly_schedule_planning.v1"
    },
    parent_artifact_version_id: version.supersedesArtifactVersionId,
    supersedes_artifact_version_id: version.supersedesArtifactVersionId,
    lineage_note: version.lineageNote,
    created_at: version.createdAt,
    links: [
      {
        artifact_version_id: version.artifactVersionId,
        workflow_run_id: version.workflowRunId,
        subject_kind: "workflow_run",
        subject_id: version.workflowRunId,
        relation_kind: "subject",
        created_at: version.createdAt,
        created_by_actor_id: null,
        created_by_actor_type: null
      }
    ]
  };
}

function updateDriverPreferencesArtifactChainLatest(
  artifactVersionId: string,
  latestArtifactVersionId: string
): void {
  let currentArtifactVersionId: string | null = artifactVersionId;
  while (currentArtifactVersionId) {
    const version = driverPreferencesArtifactVersions.get(currentArtifactVersionId);
    if (!version) {
      break;
    }
    version.latestInChainArtifactVersionId = latestArtifactVersionId;
    patchArtifactPayloadLineage(version);
    patchDriverPreferencesArtifactContractState(version);
    currentArtifactVersionId = version.supersedesArtifactVersionId;
  }
}

function buildRunDriverPreferencesWorkpagePayload(workflowRunId: string): Record<string, unknown> {
  const latestScheduleVersion = ensureScheduleArtifactDraft(workflowRunId);
  const latestVersion = latestDriverPreferencesArtifactForRun(workflowRunId);
  const payload = cloneJson(
    driverPreferencesRunWorkpageStateSnapshot.workpage_state
  ) as Record<string, unknown>;
  const runContext = asObject(payload.run_context) ?? {};
  const freshness = asObject(payload.freshness) ?? {};
  const source = asObject(payload.source) ?? {};
  const artifactState = asObject(payload.artifact_state) ?? {};
  const workpage = asObject(payload.workpage) ?? {};
  const summary = asObject(workpage.summary) ?? {};

  runContext.workflow_run_id = workflowRunId;
  runContext.activation_key = `snapshot:${workflowRunId}:weekly-driver-preferences-workpage`;
  freshness.generated_at = nowIso();
  freshness.source_version = latestVersion?.artifactVersionId ?? workflowRunId;
  source.source_refs = latestVersion
    ? [`/api/v1/artifacts/${latestVersion.artifactVersionId}`]
    : [];
  artifactState.current_artifact_version_id = null;
  artifactState.latest_artifact_version_id = latestVersion?.artifactVersionId ?? null;
  artifactState.editable = false;

  if (latestVersion) {
    summary.driver_count = latestVersion.preferenceGrid.drivers.length;
    summary.explicit_preference_count = latestVersion.preferenceGrid.drivers.reduce(
      (total, row) =>
        total +
        Object.values(asObject(row.preferences_by_weekday) ?? {}).filter(
          (value) => typeof value === "string"
        )
          .length,
      0
    );
    payload.preference_grid = cloneDriverPreferenceGrid(latestVersion.preferenceGrid);
  }

  payload.run_context = runContext;
  payload.freshness = freshness;
  payload.source = source;
  payload.artifact_state = artifactState;
  workpage.summary = summary;
  payload.workpage = workpage;
  payload.schedule_impact = latestVersion
    ? {
        ...latestVersion.scheduleImpact,
        latest_schedule_draft_artifact_version_id: latestScheduleVersion.artifactVersionId,
        latest_driver_preferences_artifact_version_id: latestVersion.artifactVersionId
      }
    : {
        ...asObject(payload.schedule_impact),
        latest_schedule_draft_artifact_version_id: latestScheduleVersion.artifactVersionId,
        latest_driver_preferences_artifact_version_id: null,
        dependency_state: "no_snapshot",
        schedule_state: "no_snapshot"
      };
  payload.driver_availability_exceptions = buildDriverAvailabilityExceptionsPayload(
    workflowRunId
  );
  payload.actions = [
    latestVersion
      ? {
          action_id: "workpage.driver-preferences-v0.open_latest",
          artifact_version_id: latestVersion.artifactVersionId,
          kind: "open_latest",
          label: "Open latest snapshot",
          route: driverPreferencesArtifactRoute(latestVersion.artifactVersionId, workflowRunId),
          state: "available",
          workpage_kind: "driver-preferences-v0",
          action_ref: buildWorkpageActionRef({
            actionId: "workpage.driver-preferences-v0.open_latest",
            workpageKind: "driver-preferences-v0",
            workflowRunId,
            artifactVersionId: latestVersion.artifactVersionId
          })
        }
      : {
          action_id: "workpage.driver-preferences-v0.create_snapshot",
          artifact_version_id: null,
          kind: "create_snapshot",
          label: "Create preferences snapshot",
          create_path: driverPreferencesSnapshotCreatePath(workflowRunId),
          state: "available",
          workpage_kind: "driver-preferences-v0",
          action_ref: buildWorkpageActionRef({
            actionId: "workpage.driver-preferences-v0.create_snapshot",
            workpageKind: "driver-preferences-v0",
            workflowRunId,
            artifactVersionId: null
          })
        },
    buildDriverAvailabilityExceptionAction(workflowRunId)
  ];
  return payload;
}

function resetDriverPreferencesArtifactVersions(): void {
  driverPreferencesArtifactVersionCounter = 0;
  driverPreferencesArtifactVersions.clear();
  driverAvailabilityExceptionCounter = 0;
  driverAvailabilityExceptions.clear();
}

function driverPreferencesArtifactCreateResponse(
  version: DriverPreferencesArtifactVersionState
): Record<string, unknown> {
  const payload = cloneJson(
    driverPreferencesArtifactCreateResponseSnapshot.create_response
  ) as Record<string, unknown>;
  payload.created = {
    artifact_version_id: version.artifactVersionId,
    route: driverPreferencesArtifactRoute(version.artifactVersionId, version.workflowRunId),
    workflow_run_id: version.workflowRunId
  };
  return payload;
}

function driverPreferencesArtifactSubmitResponse(
  version: DriverPreferencesArtifactVersionState,
  supersedesArtifactVersionId: string
): Record<string, unknown> {
  const payload = cloneJson(
    driverPreferencesArtifactSubmitResponseSnapshot.submit_response
  ) as Record<string, unknown>;
  payload.submitted = {
    artifact_version_id: version.artifactVersionId,
    route: driverPreferencesArtifactRoute(version.artifactVersionId, version.workflowRunId),
    supersedes_artifact_version_id: supersedesArtifactVersionId,
    workflow_run_id: version.workflowRunId
  };
  return payload;
}

function buildRunRouteDemandWorkpagePayload(workflowRunId: string): Record<string, unknown> {
  const latestScheduleVersion = latestOrSeedScheduleArtifactForRun(workflowRunId);
  const latestVersion = ensureRouteDemandArtifactDraft(workflowRunId);
  const visibleDayCards = visibleRouteDemandDayCards(latestVersion.dayCards);
  const payload = cloneJson(routeDemandRunWorkpageStateSnapshot.workpage_state) as Record<string, unknown>;
  const runContext = asObject(payload.run_context) ?? {};
  const freshness = asObject(payload.freshness) ?? {};
  const source = asObject(payload.source) ?? {};
  const artifactState = asObject(payload.artifact_state) ?? {};
  const workpage = asObject(payload.workpage) ?? {};
  const summary = asObject(workpage.summary) ?? {};
  const actions = Array.isArray(payload.actions) ? payload.actions : [];

  runContext.workflow_run_id = workflowRunId;
  runContext.activation_key = `snapshot:${workflowRunId}:weekly-route-demand-workpage`;
  freshness.source_version = latestVersion.artifactVersionId;
  freshness.generated_at = nowIso();
  source.source_refs = [`/api/v1/artifacts/${latestVersion.artifactVersionId}`];
  artifactState.latest_artifact_version_id = latestVersion.artifactVersionId;
  artifactState.current_artifact_version_id = null;
  artifactState.editable = false;
  summary.service_day_count = visibleDayCards.length;
  summary.planned_route_total = visibleDayCards.reduce(
    (total, card) => total + asNumber(card.planned_route_count),
    0
  );

  const dailyRowsSection = findTableSectionById(payload, "route_demand_daily_rows");
  if (dailyRowsSection) {
    dailyRowsSection.rows = visibleDayCards.map((card) => ({
      service_date: asString(card.service_date),
      planned_route_count: asNumber(card.planned_route_count),
      standard_slot_count: asNumber(card.standard_slot_count),
      rescue_slot_count: asNumber(card.rescue_slot_count),
      overflow_slot_count: asNumber(card.overflow_slot_count),
      on_call_target: asNumber(card.on_call_target),
      excess_capacity_target: asNumber(card.excess_capacity_target)
    }));
  }

  payload.run_context = runContext;
  payload.freshness = freshness;
  payload.source = source;
  payload.artifact_state = artifactState;
  workpage.summary = summary;
  payload.workpage = workpage;
  payload.calculations = {
    day_cards: latestVersion.dayCards.map((card) => ({ ...card }))
  };
  payload.schedule_impact = {
    ...latestVersion.scheduleImpact,
    latest_schedule_draft_artifact_version_id: latestScheduleVersion?.artifactVersionId ?? null,
    latest_route_demand_artifact_version_id: latestVersion.artifactVersionId
  };
  payload.future_week_options = buildRouteDemandFutureWeekOptions(workflowRunId);
  payload.future_week_activation = buildRouteDemandFutureWeekActivation({
    workflowRunId,
    targetScheduleArtifactVersionId: latestScheduleVersion?.artifactVersionId ?? null
  });
  void actions;
  payload.actions = [
    {
      action_id: "workpage.route-demand-v0.open_latest",
      kind: "open_latest",
      label: "Open route demand",
      state: "available",
      workpage_kind: "route-demand-v0",
      artifact_version_id: latestVersion.artifactVersionId,
      route: routeDemandArtifactRoute(latestVersion.artifactVersionId, workflowRunId),
      action_ref: buildWorkpageActionRef({
        actionId: "workpage.route-demand-v0.open_latest",
        workpageKind: "route-demand-v0",
        workflowRunId,
        artifactVersionId: latestVersion.artifactVersionId
      })
    },
    {
      action_id: "workpage.route-demand-v0.add_next_week",
      kind: "add_next_week",
      label: "Add a week",
      state: "available",
      workpage_kind: "route-demand-v0",
      artifact_version_id: null,
      create_path: `/api/v1/workpages/workflow-runs/${workflowRunId}/route-demand-v0/next-week`,
      action_ref: buildWorkpageActionRef({
        actionId: "workpage.route-demand-v0.add_next_week",
        workpageKind: "route-demand-v0",
        workflowRunId,
        artifactVersionId: null
      })
    }
  ];
  return payload;
}

function buildRunScheduleWorkpagePayload(workflowRunId: string): Record<string, unknown> {
  const payload = cloneJson(scheduleRunWorkpageStateSnapshot.workpage_state) as Record<string, unknown>;
  const runContext = payload.run_context as Record<string, unknown>;
  runContext.workflow_run_id = workflowRunId;
  runContext.activation_key = `snapshot:${workflowRunId}:weekly-schedule-workpage`;
  patchRunSchedulePayloadContractState(payload, workflowRunId);
  return payload;
}

function buildRunEodWorkpagePayload(workflowRunId: string): Record<string, unknown> {
  const payload = cloneJson(eodRunWorkpageStateSnapshot.workpage_state) as Record<string, unknown>;
  const runContext = payload.run_context as Record<string, unknown>;
  const freshness = payload.freshness as Record<string, unknown>;
  const source = payload.source as Record<string, unknown>;
  const draftResolution = payload.draft_resolution as Record<string, unknown>;

  runContext.workflow_run_id = workflowRunId;
  runContext.activation_key = `snapshot:${workflowRunId}:dispatch-reporting-workpage`;

  const latestVersion = latestEodArtifactForRun(workflowRunId);
  if (!latestVersion) {
    draftResolution.state = "no_draft";
    draftResolution.latest_artifact_version_id = null;
    draftResolution.artifact_route = null;
    draftResolution.open_action_ref = null;
    draftResolution.create_action_ref = buildWorkpageActionRef({
      actionId: "workpage.eod-v0.create_draft",
      workpageKind: "eod-v0",
      workflowRunId,
      artifactVersionId: null
    });
    freshness.source_version = workflowRunId;
    source.source_refs = [
      "/api/v1/artifacts/av-reporting-eos-001",
      "/api/v1/artifacts/av-reporting-actuals-001"
    ];
    return payload;
  }

  draftResolution.state = "latest_draft_available";
  draftResolution.latest_artifact_version_id = latestVersion.artifactVersionId;
  draftResolution.artifact_route = artifactRoute(
    latestVersion.artifactVersionId,
    workflowRunId
  );
  draftResolution.open_action_ref = buildWorkpageActionRef({
    actionId: "workpage.eod-v0.open_latest_draft",
    workpageKind: "eod-v0",
    workflowRunId,
    artifactVersionId: latestVersion.artifactVersionId
  });
  draftResolution.create_action_ref = null;
  freshness.source_version = latestVersion.artifactVersionId;
  source.source_refs = [
    "/api/v1/artifacts/av-reporting-eos-001",
    "/api/v1/artifacts/av-reporting-actuals-001",
    `/api/v1/artifacts/${latestVersion.artifactVersionId}`
  ];
  return payload;
}

function resetEodArtifactVersions(): void {
  eodArtifactVersionCounter = 0;
  eodArtifactVersions.clear();
}

function resetScheduleArtifactVersions(): void {
  scheduleArtifactVersionCounter = 0;
  scheduleArtifactVersions.clear();
}

function resetRouteDemandArtifactVersions(): void {
  routeDemandArtifactVersionCounter = 0;
  routeDemandArtifactVersions.clear();
}

const TEMPLATE_FIXTURES = [
  {
    template_id: "schedule.stage05.draft_schedule.workbook.empty.v1",
    workflow_id: "schedule_planning.v1",
    stage_id: "Stage05",
    dataset_key: "schedule.draft_schedule.workbook",
    artifact_kind: "schedule.draft_schedule.workbook",
    variant: "empty",
    media_type: "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    file_path:
      "fixtures/workflows/schedule_planning/template_pack/Stage05_Draft_Schedule_Triage/Stage05_Draft_Schedule_Triage_Spreadsheet_Template_EMPTY.xlsx",
    file_name: "Stage05_Draft_Schedule_Triage_Spreadsheet_Template_EMPTY.xlsx",
    description: "Empty Stage05 draft-schedule workbook template."
  },
  {
    template_id: "schedule.stage06.supervisor_review.doc.empty.v1",
    workflow_id: "schedule_planning.v1",
    stage_id: "Stage06",
    dataset_key: "schedule.supervisor_review.doc",
    artifact_kind: "schedule.supervisor_review.doc",
    variant: "empty",
    media_type: "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    file_path:
      "fixtures/workflows/schedule_planning/template_pack/Stage06_Supervisor_Review_Publish/Stage06_Supervisor_Review_Publish_Document_Template_EMPTY.docx",
    file_name: "Stage06_Supervisor_Review_Publish_Document_Template_EMPTY.docx",
    description: "Empty Stage06 supervisor-review document template."
  },
  {
    template_id: "schedule.stage07.exception_board.doc.empty.v1",
    workflow_id: "schedule_planning.v1",
    stage_id: "Stage07",
    dataset_key: "schedule.exception_board.doc",
    artifact_kind: "schedule.exception_board.doc",
    variant: "empty",
    media_type: "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    file_path:
      "fixtures/workflows/schedule_planning/template_pack/Stage07_Intraday_Exception_Control/Stage07_Intraday_Exception_Control_Document_Template_EMPTY.docx",
    file_name: "Stage07_Intraday_Exception_Control_Document_Template_EMPTY.docx",
    description: "Empty Stage07 exception-board document template."
  }
];

function defaultViewerActorRoles(request: Request): string[] {
  const actorRoles = Array.from(actorRolesFromRequest(request));
  if (actorRoles.length > 0) {
    return actorRoles;
  }
  return [
    "dispatch_supervisor",
    "schedule_planner",
    "fleet_coordinator",
    "operations_manager"
  ];
}

function viewerSessionFromRequest(request: Request): Record<string, unknown> {
  return {
    tenant_id: request.headers.get("x-onetruth-tenant-id") ?? state.tenantId,
    domain_id: request.headers.get("x-onetruth-domain-id") ?? state.domainId,
    actor_id: request.headers.get("x-onetruth-actor-id") ?? "human:frontend-operator",
    actor_type: request.headers.get("x-onetruth-actor-type") ?? "human",
    actor_roles: defaultViewerActorRoles(request),
    boundary_profile: "local_dev",
    request_context_mode: "trusted_headers",
    actor_switching_allowed: true
  };
}

function inScope(request: Request): boolean {
  const tenant = request.headers.get("x-onetruth-tenant-id");
  const domain = request.headers.get("x-onetruth-domain-id");
  if (state.forceForbidden) {
    return false;
  }
  return tenant === state.tenantId && domain === state.domainId;
}

function forbiddenWorkflowRun() {
  return HttpResponse.json(
    {
      status: "error",
      error: {
        code: "workflow_run_not_found",
        message: "workflow run not found",
        details: {}
      }
    },
    { status: 404 }
  );
}

function parseLimitOffset(url: URL): { limit: number; offset: number } {
  const limit = Number.parseInt(url.searchParams.get("limit") ?? "100", 10);
  const offset = Number.parseInt(url.searchParams.get("offset") ?? "0", 10);
  return {
    limit: Number.isNaN(limit) ? 100 : limit,
    offset: Number.isNaN(offset) ? 0 : offset
  };
}

function actorRolesFromRequest(request: Request): Set<string> {
  const rawRoles = request.headers.get("x-onetruth-actor-roles") ?? "";
  return new Set(
    rawRoles
      .split(",")
      .map((role) => role.trim())
      .filter(Boolean)
  );
}

function taskActionability(task: HumanTaskRow, request: Request) {
  const actorId = request.headers.get("x-onetruth-actor-id") ?? "human:frontend-operator";
  const actorType = request.headers.get("x-onetruth-actor-type") ?? "human";
  const actorRoles = actorRolesFromRequest(request);
  const roleMatch =
    task.candidate_roles.length === 0 ||
    task.candidate_roles.some((role) => actorRoles.has(role));
  const isAssignee =
    task.assignee_actor_id === actorId && task.assignee_actor_type === actorType;
  const availableActions: string[] = [];
  const blockingReasonCodes = [...(task.blocking_reason_codes ?? [])];

  if (task.state === "OPEN" && !task.assignee_actor_id && roleMatch) {
    availableActions.push("claim");
  } else if (task.state === "OPEN" && !roleMatch) {
    blockingReasonCodes.push("candidate_role_mismatch");
  }

  if (task.state === "CLAIMED" && isAssignee) {
    availableActions.push("complete");
  } else if (task.state === "CLAIMED" && !isAssignee) {
    blockingReasonCodes.push("claimed_by_other_actor");
  }

  if (task.state !== "COMPLETED") {
    availableActions.push("upload_attachment");
  }

  return {
    available_actions: [...new Set(availableActions)],
    missing_required_inputs: task.missing_required_inputs ?? [],
    blocking_reason_codes: [...new Set(blockingReasonCodes)]
  };
}

const COMPOSITE_TASK_SUBGRAPH_KINDS = new Set([
  "actual_hours_review",
  "planning_feedback_review",
  "dispatcher_review",
  "dispatch_seed_intake",
  "final_packet_review",
  "finalize_reporting_packet"
]);

function taskSubgraphMetadata(task: HumanTaskRow): {
  is_composite: boolean;
  expansion_kind: "none" | "task_subgraph";
  subgraph_ref: { human_task_id: string; endpoint: string } | null;
} {
  if (!COMPOSITE_TASK_SUBGRAPH_KINDS.has(task.task_kind)) {
    return {
      is_composite: false,
      expansion_kind: "none",
      subgraph_ref: null
    };
  }
  return {
    is_composite: true,
    expansion_kind: "task_subgraph",
    subgraph_ref: {
      human_task_id: task.human_task_id,
      endpoint: `/api/v1/human-tasks/${task.human_task_id}/subgraph`
    }
  };
}

function enrichHumanTaskForResponse(task: HumanTaskRow, request: Request): HumanTaskRow {
  return {
    ...task,
    ...taskActionability(task, request),
    ...taskSubgraphMetadata(task)
  };
}

function taskSubgraphTemplate(taskKind: string): {
  template_id: string;
  title: string;
  nodes: Array<{ node_id: string; label: string }>;
} | null {
  if (taskKind === "actual_hours_review" || taskKind === "planning_feedback_review") {
    return {
      template_id: "schedule_planning.feedback_review.v1",
      title: "Planning feedback review",
      nodes: [
        { node_id: "ingest_actual_hours", label: "Ingest actual-hours snapshot" },
        { node_id: "reconcile_plan_variance", label: "Reconcile plan variance" },
        { node_id: "draft_feedback_packet", label: "Draft planning feedback packet" },
        { node_id: "publish_feedback_handoff", label: "Publish feedback handoff" }
      ]
    };
  }
  if (taskKind === "dispatcher_review" || taskKind === "dispatch_seed_intake") {
    return {
      template_id: "live_dispatch.seed_intake.v1",
      title: "Live dispatch seed intake",
      nodes: [
        { node_id: "ingest_weekly_seed", label: "Ingest weekly seed package" },
        { node_id: "verify_route_delta", label: "Verify route delta inputs" },
        { node_id: "resolve_capacity_conflicts", label: "Resolve capacity conflicts" },
        { node_id: "dispatch_ready_confirmation", label: "Confirm dispatch readiness" }
      ]
    };
  }
  if (taskKind === "final_packet_review" || taskKind === "finalize_reporting_packet") {
    return {
      template_id: "dispatch_reporting.final_packet.v1",
      title: "Reporting packet closeout",
      nodes: [
        { node_id: "collect_route_metrics", label: "Collect route metrics" },
        { node_id: "reconcile_variance_notes", label: "Reconcile variance notes" },
        { node_id: "finalize_reporting_packet", label: "Finalize reporting packet" },
        { node_id: "notify_planning_feedback", label: "Notify planning feedback" }
      ]
    };
  }
  return null;
}

function taskSubgraphNodeStatuses(taskState: HumanTaskRow["state"], nodeCount: number): string[] {
  if (nodeCount <= 0) {
    return [];
  }
  if (taskState === "COMPLETED") {
    return Array.from({ length: nodeCount }, () => "completed");
  }
  if (taskState === "CLAIMED") {
    return Array.from({ length: nodeCount }, (_, index) => {
      if (index === 0) {
        return "completed";
      }
      if (index === 1) {
        return "in_progress";
      }
      if (index === 2) {
        return "ready";
      }
      return "not_started";
    });
  }
  return Array.from({ length: nodeCount }, (_, index) =>
    index === 0 ? "in_progress" : "not_started"
  );
}

function taskSubgraphArtifactRefs(task: HumanTaskRow) {
  const refsByArtifactId = new Map<
    string,
    { artifact_version_id: string; label: string; source_label: string }
  >();
  for (const artifact of state.artifactVersions) {
    const links = artifact.links ?? [];
    const hasTaskAttachment = links.some(
      (link) => link.subject_kind === "human_task" && link.subject_id === task.human_task_id
    );
    const hasTaskOutput = links.some(
      (link) => link.subject_kind === "task_run" && link.subject_id === task.task_run_id
    );
    if (!hasTaskAttachment && !hasTaskOutput) {
      continue;
    }
    const metadataName = artifact.metadata_json?.file_name;
    refsByArtifactId.set(artifact.artifact_version_id, {
      artifact_version_id: artifact.artifact_version_id,
      label:
        typeof metadataName === "string" && metadataName.length > 0
          ? metadataName
          : artifact.artifact_kind,
      source_label: hasTaskOutput ? "Task step output" : "Task attachment"
    });
  }
  return Array.from(refsByArtifactId.values());
}

function buildTaskSubgraph(task: HumanTaskRow): HumanTaskSubgraph | null {
  const template = taskSubgraphTemplate(task.task_kind);
  if (!template) {
    return null;
  }
  const statuses = taskSubgraphNodeStatuses(task.state, template.nodes.length);
  return {
    graph_id: `task_subgraph:${task.human_task_id}`,
    template_id: template.template_id,
    title: template.title,
    nodes: template.nodes.map((node, index) => ({
      node_id: node.node_id,
      label: node.label,
      node_kind: "step",
      status: statuses[index] as HumanTaskSubgraph["nodes"][number]["status"],
      row: 0,
      column: index,
      is_blocking: false
    })),
    edges: template.nodes.slice(0, -1).map((node, index) => ({
      edge_id: `${node.node_id}->${template.nodes[index + 1].node_id}`,
      from_node_id: node.node_id,
      to_node_id: template.nodes[index + 1].node_id,
      edge_kind: "linear",
      label: null
    })),
    freshness: {
      status: "fresh",
      as_of: task.updated_at,
      note: "Mock task subgraph freshness"
    },
    artifact_refs: taskSubgraphArtifactRefs(task)
  };
}

function listTemplatesFromQuery(url: URL) {
  const workflowId = url.searchParams.get("workflow_id");
  const stageId = url.searchParams.get("stage_id");
  const datasetKey = url.searchParams.get("dataset_key");
  const variant = url.searchParams.get("variant");
  return TEMPLATE_FIXTURES.filter((template) => {
    if (workflowId && template.workflow_id !== workflowId) {
      return false;
    }
    if (stageId && template.stage_id !== stageId) {
      return false;
    }
    if (datasetKey && template.dataset_key !== datasetKey) {
      return false;
    }
    if (variant && template.variant !== variant) {
      return false;
    }
    return true;
  });
}

function templateDownloadBody(templateId: string): string {
  return `template:${templateId}`;
}

function mutateTaskToClaimed(humanTaskId: string, actorId: string): boolean {
  const row = state.humanTasks.find((task) => task.human_task_id === humanTaskId);
  if (!row || row.state !== "OPEN") {
    return false;
  }

  row.state = "CLAIMED";
  row.assignee_actor_id = actorId;
  row.assignee_actor_type = "human";
  row.lease_version += 1;
  row.claimed_at = new Date().toISOString();
  row.updated_at = row.claimed_at;
  row.task_run_state = "IN_PROGRESS";
  state.audit.mutations.push(`claim:${humanTaskId}`);
  return true;
}

function mutateTaskToCompleted(humanTaskId: string): boolean {
  const row = state.humanTasks.find((task) => task.human_task_id === humanTaskId);
  if (!row || row.state !== "CLAIMED") {
    return false;
  }

  row.state = "COMPLETED";
  row.task_run_state = "COMPLETED";
  row.updated_at = new Date().toISOString();
  state.audit.mutations.push(`complete:${humanTaskId}`);
  return true;
}

function confirmTaskReview(
  humanTaskId: string,
  reviewedArtifactVersionIds: string[]
): { artifactVersion: ArtifactVersionRow; idempotentReplay: boolean } | null {
  const row = state.humanTasks.find((task) => task.human_task_id === humanTaskId);
  if (!row || row.state !== "CLAIMED") {
    return null;
  }

  const existing = state.artifactVersions.find(
    (artifact) =>
      artifact.artifact_kind === "human_task.review_confirmation.json" &&
      artifact.metadata_json?.human_task_id === humanTaskId
  );
  if (existing) {
    state.confirmedReviewTaskIds.add(humanTaskId);
    state.audit.mutations.push(`confirm-review:${humanTaskId}`);
    return { artifactVersion: existing, idempotentReplay: true };
  }

  const artifactVersionId = `av-confirm-${state.artifactVersions.length + 1}`;
  const createdAt = new Date().toISOString();
  const artifactVersion: ArtifactVersionRow = {
    artifact_version_id: artifactVersionId,
    workflow_run_id: row.workflow_run_id,
    task_run_id: row.task_run_id,
    artifact_kind: "human_task.review_confirmation.json",
    artifact_role: "review_evidence",
    media_type: "application/json",
    storage_uri: `memory://confirm-review/${artifactVersionId}.json`,
    content_digest: `sha256:${artifactVersionId}`,
    byte_size: 256,
    metadata_json: {
      human_task_id: humanTaskId,
      reviewed_artifact_version_ids: reviewedArtifactVersionIds
    },
    parent_artifact_version_id: null,
    supersedes_artifact_version_id: null,
    lineage_note: null,
    created_at: createdAt,
    links: [
      {
        artifact_version_id: artifactVersionId,
        workflow_run_id: row.workflow_run_id,
        subject_kind: "human_task",
        subject_id: humanTaskId,
        relation_kind: "review_confirmation",
        created_at: createdAt,
        created_by_actor_id: "human:frontend-operator",
        created_by_actor_type: "human"
      }
    ]
  };

  state.artifactVersions.unshift(artifactVersion);
  state.confirmedReviewTaskIds.add(humanTaskId);
  state.audit.mutations.push(`confirm-review:${humanTaskId}`);
  return { artifactVersion, idempotentReplay: false };
}

function mutateApprovalResponse(approvalId: string, responseKind: string): boolean {
  const row = state.approvals.find((approval) => approval.approval_id === approvalId);
  if (!row || row.state !== "PENDING") {
    return false;
  }

  row.state = "RESPONDED";
  row.response_kind = responseKind;
  row.responded_at = new Date().toISOString();
  row.updated_at = row.responded_at;
  row.generation += 1;
  state.audit.mutations.push(`respond:${approvalId}:${responseKind}`);
  return true;
}

function workflowRunIdForSubject(
  subjectKind: "human_task" | "approval" | "flag" | "workflow_run",
  subjectId: string
): string | null {
  if (subjectKind === "workflow_run") {
    return subjectId;
  }
  if (subjectKind === "human_task") {
    return state.humanTasks.find((task) => task.human_task_id === subjectId)?.workflow_run_id ?? null;
  }
  if (subjectKind === "approval") {
    return state.approvals.find((approval) => approval.approval_id === subjectId)?.workflow_run_id ?? null;
  }
  return state.flags.find((flag) => flag.flag_id === subjectId)?.workflow_run_id ?? null;
}

function taskRunIdForSubject(
  subjectKind: "human_task" | "approval" | "flag" | "workflow_run",
  subjectId: string
): string | null {
  if (subjectKind === "human_task") {
    return state.humanTasks.find((task) => task.human_task_id === subjectId)?.task_run_id ?? null;
  }
  if (subjectKind === "approval") {
    return state.approvals.find((approval) => approval.approval_id === subjectId)?.task_run_id ?? null;
  }
  return null;
}

function addAttachmentArtifact(
  subjectKind: "human_task" | "approval" | "flag" | "workflow_run",
  subjectId: string,
  payload: Record<string, unknown>
) {
  const workflowRunId = workflowRunIdForSubject(subjectKind, subjectId);
  if (!workflowRunId) {
    return null;
  }
  const artifactVersionId = `av-upload-${state.artifactVersions.length + 1}`;
  const createdAt = new Date().toISOString();
  const fileName =
    typeof payload.file_name === "string" && payload.file_name.length > 0
      ? payload.file_name
      : `${artifactVersionId}.txt`;

  const artifactVersion = {
    artifact_version_id: artifactVersionId,
    workflow_run_id: workflowRunId,
    task_run_id: taskRunIdForSubject(subjectKind, subjectId),
    artifact_kind:
      typeof payload.artifact_kind === "string" ? payload.artifact_kind : `attachment.${subjectKind}`,
    artifact_role:
      typeof payload.artifact_role === "string" ? payload.artifact_role : "evidence",
    media_type:
      typeof payload.media_type === "string" ? payload.media_type : "application/octet-stream",
    storage_uri: `memory://attachments/${artifactVersionId}`,
    content_digest: `sha256:${artifactVersionId}`,
    byte_size:
      typeof payload.content_base64 === "string" ? payload.content_base64.length : fileName.length,
    metadata_json: {
      file_name: fileName,
      source: "msw"
    },
    parent_artifact_version_id: null,
    supersedes_artifact_version_id: null,
    lineage_note: null,
    created_at: createdAt,
    links: [
      {
        artifact_version_id: artifactVersionId,
        workflow_run_id: workflowRunId,
        subject_kind: subjectKind,
        subject_id: subjectId,
        relation_kind: "attachment",
        created_at: createdAt,
        created_by_actor_id: "human:frontend-operator",
        created_by_actor_type: "human"
      }
    ]
  };

  state.artifactVersions.unshift(artifactVersion);

  if (subjectKind === "human_task") {
    state.uploadedTaskAttachmentIds.add(subjectId);
  } else if (subjectKind === "approval") {
    state.uploadedApprovalAttachmentIds.add(subjectId);
  } else if (subjectKind === "flag") {
    state.uploadedFlagAttachmentIds.add(subjectId);
  }

  state.audit.mutations.push(`upload:${subjectKind}:${subjectId}`);
  return artifactVersion;
}

function listArtifactsForSubject(
  subjectKind: "human_task" | "approval" | "flag" | "workflow_run",
  subjectId: string
) {
  return state.artifactVersions.filter((artifact) =>
    artifact.links?.some(
      (link) => link.subject_kind === subjectKind && link.subject_id === subjectId
    )
  );
}

function artifactDownloadBody(artifactVersionId: string): string {
  return `artifact:${artifactVersionId}`;
}

function binaryDownloadResponse(
  body: string,
  options: {
    fileName: string;
    mediaType: string;
    requestId: string;
  }
) {
  return new HttpResponse(body, {
    status: 200,
    headers: {
      "content-type": options.mediaType,
      "content-length": String(body.length),
      "content-disposition": `attachment; filename="${options.fileName}"`,
      "x-request-id": options.requestId
    }
  });
}

function buildStoryRun(
  input: {
    workflowRunId: string;
    workflowId: string;
    partitionKey: string;
    state: string;
    activeIssueCount: number;
  }
) {
  const now = new Date().toISOString();
  return {
    workflow_run_id: input.workflowRunId,
    workflow_id: input.workflowId,
    workflow_version: "v1",
    tenant_id: "tenant-a",
    domain_id: "domain-x",
    partition_key: input.partitionKey,
    logical_date: input.partitionKey,
    activation_key: `${input.workflowId}:${input.partitionKey}`,
    state: input.state,
    active_issue_count: input.activeIssueCount,
    created_at: now,
    updated_at: now
  };
}

function buildLogisticsStoryPayload(planningWeekId: string, request: Request, serviceDateId?: string) {
  const now = new Date().toISOString();
  const currentServiceDateId = serviceDateId ?? "SD-2026-03-06";
  ensureWeeklyPlanningRunState(SCHEDULE_WORKFLOW_RUN_ID);
  const weeklyRuns = state.workflowRuns
    .filter((run) => run.workflow_id === "weekly_schedule_planning.v1")
    .sort((left, right) => left.partition_key.localeCompare(right.partition_key));
  const weeklyRun =
    weeklyRuns.find((run) => run.partition_key === planningWeekId) ??
    weeklyRuns[0] ??
    buildStoryRun({
      workflowRunId: "wr-weekly-001",
      workflowId: "weekly_schedule_planning.v1",
      partitionKey: planningWeekId,
      state: "OPEN",
      activeIssueCount: 1
    });
  const reportingRun =
    state.workflowRuns.find(
      (run) =>
        run.workflow_id === "dispatch_reporting.v1" && run.partition_key === currentServiceDateId
    ) ??
    buildStoryRun({
      workflowRunId: "wr-report-001",
      workflowId: "dispatch_reporting.v1",
      partitionKey: currentServiceDateId,
      state: "OPEN",
      activeIssueCount: 0
    });
  const liveRun =
    state.workflowRuns.find(
      (run) => run.workflow_id === "live_dispatch.v1" && run.partition_key === currentServiceDateId
    ) ?? null;

  const weeklyTask = state.humanTasks.find((task) => task.human_task_id === "ht-weekly-001");
  const reportingTask = state.humanTasks.find((task) => task.human_task_id === "ht-reporting-001");
  const liveTask =
    liveRun != null
      ? (state.humanTasks.find(
          (task) =>
            task.workflow_run_id === liveRun.workflow_run_id && task.task_kind === "dispatch_seed_intake"
        ) ?? null)
      : null;

  const weeklyTaskResponse = weeklyTask ? enrichHumanTaskForResponse(weeklyTask, request) : null;
  const reportingTaskResponse = reportingTask
    ? enrichHumanTaskForResponse(reportingTask, request)
    : null;
  const liveTaskResponse = liveTask ? enrichHumanTaskForResponse(liveTask, request) : null;

  const priorFeedbackRun = buildStoryRun({
    workflowRunId: "wr-report-feedback-001",
    workflowId: "dispatch_reporting.v1",
    partitionKey: "SD-2026-03-05",
    state: "COMPLETED",
    activeIssueCount: 0
  });
  const reportingFeedbackArtifact = {
    artifact_version_id: "av-reporting-feedback-001",
    workflow_run_id: priorFeedbackRun.workflow_run_id,
    task_run_id: "tr-report-feedback-stage04-001",
    artifact_kind: "reporting.final_packet.workbook",
    artifact_role: "official_output",
    media_type: "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    storage_uri: "memory://story/av-reporting-feedback-001.xlsx",
    content_digest: "sha256:reporting-feedback-001",
    byte_size: 960,
    metadata_json: {
      file_name: "dispatch_reporting_feedback_packet.xlsx"
    },
    parent_artifact_version_id: null,
    supersedes_artifact_version_id: null,
    lineage_note: null,
    created_at: now
  };
  const reportingFeedbackPointer = {
    workflow_run_id: priorFeedbackRun.workflow_run_id,
    pointer_key: "official:reporting.final_packet.workbook",
    scope_kind: "stage",
    scope_ref: "Stage04",
    artifact_kind: "reporting.final_packet.workbook",
    artifact_version_id: reportingFeedbackArtifact.artifact_version_id,
    promotion_reason: "official_finalize",
    promoted_by_task_run_id: "tr-report-feedback-stage04-001",
    approved_by_approval_id: "ap-report-feedback-stage04-001",
    generation: 1,
    updated_at: now
  };
  const weeklyPublishedArtifact = state.artifactVersions.find(
    (artifact) =>
      artifact.workflow_run_id === weeklyRun.workflow_run_id &&
      artifact.artifact_kind === "planning.published_weekly_schedule.workbook" &&
      artifact.artifact_role === "official_output"
  );
  const liveSeedArtifact =
    liveRun != null
      ? (state.artifactVersions.find(
          (artifact) =>
            artifact.workflow_run_id === liveRun.workflow_run_id &&
            artifact.artifact_kind === "dispatch.base_schedule_seed.workbook"
        ) ?? null)
      : null;

  const workItems = [
    weeklyTaskResponse
      ? {
          item_id: `human_task:${weeklyTaskResponse.human_task_id}`,
          item_type: "human_task" as const,
          lane:
            weeklyTaskResponse.state === "CLAIMED"
              ? "human_tasks.claimed"
              : weeklyTaskResponse.state === "COMPLETED"
                ? "human_tasks.completed"
                : "human_tasks.open",
          title: "Stage04 weekly_input_intake",
          workflow_run_id: weeklyRun.workflow_run_id,
          workflow_id: weeklyRun.workflow_id,
          subject_id: weeklyTaskResponse.human_task_id,
          stage_id: weeklyTaskResponse.stage_id,
          task_kind: weeklyTaskResponse.task_kind,
          state: weeklyTaskResponse.state,
          owner_role: weeklyTaskResponse.owner_role,
          available_actions: weeklyTaskResponse.available_actions ?? [],
          blocking_reason_codes: weeklyTaskResponse.blocking_reason_codes ?? [],
          missing_required_inputs: weeklyTaskResponse.missing_required_inputs ?? [],
          linked_artifact_count: 0
        }
      : null,
    liveTaskResponse && liveRun
      ? {
          item_id: `human_task:${liveTaskResponse.human_task_id}`,
          item_type: "human_task" as const,
          lane:
            liveTaskResponse.state === "CLAIMED"
              ? "human_tasks.claimed"
              : liveTaskResponse.state === "COMPLETED"
                ? "human_tasks.completed"
                : "human_tasks.open",
          title: "Stage01 dispatch_seed_intake",
          workflow_run_id: liveRun.workflow_run_id,
          workflow_id: liveRun.workflow_id,
          subject_id: liveTaskResponse.human_task_id,
          stage_id: liveTaskResponse.stage_id,
          task_kind: liveTaskResponse.task_kind,
          state: liveTaskResponse.state,
          owner_role: liveTaskResponse.owner_role,
          available_actions: liveTaskResponse.available_actions ?? [],
          blocking_reason_codes: liveTaskResponse.blocking_reason_codes ?? [],
          missing_required_inputs: liveTaskResponse.missing_required_inputs ?? [],
          linked_artifact_count: liveSeedArtifact ? 1 : 0
        }
      : null,
    reportingTaskResponse
      ? {
          item_id: `human_task:${reportingTaskResponse.human_task_id}`,
          item_type: "human_task" as const,
          lane:
            reportingTaskResponse.state === "CLAIMED"
              ? "human_tasks.claimed"
              : reportingTaskResponse.state === "COMPLETED"
                ? "human_tasks.completed"
                : "human_tasks.open",
          title: "Stage01 eos_input_intake",
          workflow_run_id: reportingRun.workflow_run_id,
          workflow_id: reportingRun.workflow_id,
          subject_id: reportingTaskResponse.human_task_id,
          stage_id: reportingTaskResponse.stage_id,
          task_kind: reportingTaskResponse.task_kind,
          state: reportingTaskResponse.state,
          owner_role: reportingTaskResponse.owner_role,
          available_actions: reportingTaskResponse.available_actions ?? [],
          blocking_reason_codes: reportingTaskResponse.blocking_reason_codes ?? [],
          missing_required_inputs: reportingTaskResponse.missing_required_inputs ?? [],
          linked_artifact_count: 0
        }
      : null
  ].filter(Boolean);

  const laneDefinitions = [
    { lane: "flags.open", label: "Open Exceptions", position: 5 },
    { lane: "human_tasks.open", label: "Open Tasks", position: 10 },
    { lane: "human_tasks.claimed", label: "Claimed Tasks", position: 20 },
    { lane: "approvals.pending", label: "Pending Approvals", position: 30 },
    { lane: "approvals.responded", label: "Responded Approvals", position: 40 },
    { lane: "human_tasks.completed", label: "Completed Tasks", position: 50 },
    { lane: "flags.resolved", label: "Resolved Exceptions", position: 60 },
    { lane: "flags.closed", label: "Closed Exceptions", position: 70 }
  ];

  return {
    story_id: "logistics_three_workflow_demo.v1",
    family: {
      family_id: "logistics_ops_family.v1",
      family_version: 1,
      contract_version: 1
    },
    partitions: {
      planning_week_id: planningWeekId,
      service_date_ids: [currentServiceDateId]
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
              workflow_run_id: reportingRun.workflow_run_id,
              workflow_id: reportingRun.workflow_id,
              partition_key: reportingRun.partition_key
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
          drilldown_kind: weeklyRuns.length > 1 ? "run_group" : "workflow_run",
          drilldown_refs: weeklyRuns.map((run) => ({
            workflow_run_id: run.workflow_run_id,
            workflow_id: run.workflow_id,
            partition_key: run.partition_key
          })),
          artifact_refs: weeklyPublishedArtifact
            ? [
                {
                  artifact_version_id: weeklyPublishedArtifact.artifact_version_id,
                  label:
                    String(
                      (weeklyPublishedArtifact.metadata_json as Record<string, unknown> | null)?.file_name ??
                        weeklyPublishedArtifact.artifact_version_id
                    ) || weeklyPublishedArtifact.artifact_version_id,
                  source_label: "Official output"
                }
              ]
            : [],
          selection_summary: weeklyPublishedArtifact
            ? `${weeklyRuns.length} linked run${weeklyRuns.length === 1 ? "" : "s"}, 1 downloadable artifact`
            : `${weeklyRuns.length} linked run${weeklyRuns.length === 1 ? "" : "s"}, 0 downloadable artifacts`
        },
        {
          module_id: "live_dispatch",
          workflow_id: "live_dispatch.v1",
          partition_kind: "ServiceDateID",
          activation_policy: "event_driven",
          status: liveRun ? "active" : "ready",
          node_kind: "module",
          drilldown_kind: liveRun ? "workflow_run" : "none",
          drilldown_refs: liveRun
            ? [
                {
                  workflow_run_id: liveRun.workflow_run_id,
                  workflow_id: liveRun.workflow_id,
                  partition_key: liveRun.partition_key
                }
              ]
            : [],
          artifact_refs: [],
          selection_summary: liveRun
            ? "1 linked run, 0 downloadable artifacts"
            : "0 linked runs, prepare service day after weekly publish"
        }
      ],
      edges: [
        {
          edge_id: "reporting_actuals_to_future_planning",
          source_module_id: "dispatch_reporting",
          target_module_id: "weekly_schedule_planning",
          source_stage_id: "Stage05",
          source_dataset_key: "reporting.final_packet.workbook",
          target_stage_id: "Stage03",
          target_dataset_key: "planning.actual_hours_snapshot.workbook",
          partition_transform_id: "service_day_to_future_planning_week",
          handoff_mode: "notify_only",
          writer_mode: "source_only",
          status: "active"
        },
        {
          edge_id: "weekly_seed_to_live_dispatch",
          source_module_id: "weekly_schedule_planning",
          target_module_id: "live_dispatch",
          source_stage_id: "Stage07",
          source_dataset_key: "planning.daily_dispatch_seed.workbook",
          target_stage_id: "Stage01",
          target_dataset_key: "dispatch.base_schedule_seed.workbook",
          partition_transform_id: "planning_week_to_service_date",
          handoff_mode: "materialize_seed",
          writer_mode: "target_materialize",
          status: "active"
        }
      ]
    },
    linked_workflow_runs: {
      weekly_schedule_planning: weeklyRuns,
      live_dispatch: liveRun ? [liveRun] : [],
      dispatch_reporting: [reportingRun],
      summary: {
        weekly_schedule_planning_count: weeklyRuns.length,
        live_dispatch_count: liveRun ? 1 : 0,
        dispatch_reporting_count: 1
      }
    },
    handoff_activity: {
      edges: [
        {
          edge_id: "weekly_seed_to_live_dispatch",
          execution_count: liveRun ? 1 : 0,
          status_counts: liveRun ? { activated: 1 } : {},
          coherence_failed_count: 0,
          executions: liveRun
            ? [
                {
                  edge_execution_id: "edge-weekly-live-001",
                  edge_id: "weekly_seed_to_live_dispatch",
                  source_workflow_run_id: weeklyRun.workflow_run_id,
                  source_stage_id: "Stage07",
                  source_artifact_version_id:
                    weeklyPublishedArtifact?.artifact_version_id ?? "av-weekly-seed-001",
                  target_workflow_id: liveRun.workflow_id,
                  target_workflow_run_id: liveRun.workflow_run_id,
                  target_stage_id: "Stage01",
                  target_partition_key: liveRun.partition_key,
                  status: "activated",
                  created_at: now,
                  updated_at: now,
                  activated_at: now,
                  source_workflow_run: weeklyRun,
                  target_workflow_run: liveRun,
                  coherence: {
                    coherence_status: "passed"
                  }
                }
              ]
            : []
        },
        {
          edge_id: "reporting_actuals_to_future_planning",
          execution_count: 1,
          status_counts: { prepared: 1 },
          coherence_failed_count: 0,
          executions: [
            {
              edge_execution_id: "edge-reporting-weekly-001",
              edge_id: "reporting_actuals_to_future_planning",
              source_workflow_run_id: priorFeedbackRun.workflow_run_id,
              source_stage_id: "Stage04",
              source_artifact_version_id: reportingFeedbackArtifact.artifact_version_id,
              target_workflow_id: weeklyRun.workflow_id,
              target_workflow_run_id: weeklyRun.workflow_run_id,
              target_stage_id: "Stage03",
              target_partition_key: planningWeekId,
              status: "prepared",
              created_at: now,
              updated_at: now,
              activated_at: null,
              source_workflow_run: priorFeedbackRun,
              target_workflow_run: weeklyRun,
              coherence: {
                coherence_status: "passed"
              }
            }
          ]
        }
      ],
      summary: {
        edge_execution_count: liveRun ? 2 : 1,
        coherence_failed_count: 0
      }
    },
    board: {
      lanes: laneDefinitions.map((lane) => ({
        ...lane,
        item_count: workItems.filter((item) => item?.lane === lane.lane).length
      })),
      work_items: workItems,
      page: { limit: 100, offset: 0 },
      summary: {
        work_item_count: workItems.length,
        human_task_count: workItems.filter((item) => item?.item_type === "human_task").length,
        approval_count: 0,
        flag_count: 0,
        primary_actionable_count: workItems.filter(
          (item) => item?.item_type === "human_task" && (item.available_actions?.length ?? 0) > 0
        ).length,
        workflow_item_counts: workItems.reduce<Record<string, number>>((acc, item) => {
          if (!item) {
            return acc;
          }
          acc[item.workflow_id] = (acc[item.workflow_id] ?? 0) + 1;
          return acc;
        }, {})
      }
    },
    official_outputs: {
      pointers: [reportingFeedbackPointer],
      pointer_outputs: [
        {
          pointer: reportingFeedbackPointer,
          artifact_version: reportingFeedbackArtifact
        }
      ],
      official_output_artifacts: [reportingFeedbackArtifact],
      coherence: {
        "official:reporting.final_packet.workbook": {
          coherence_status: "passed"
        }
      },
      summary: {
        pointer_count: 1,
        pointer_output_count: 1,
        official_output_artifact_count: 1,
        artifact_kind_counts: {
          "reporting.final_packet.workbook": 1
        }
      }
    },
    freshness: {
      latest_event_sequence: 44,
      latest_event_recorded_at: now,
      max_workflow_run_updated_at: now,
      generated_at: now
    },
    coherence: {
      official_outputs: {
        "official:reporting.final_packet.workbook": {
          coherence_status: "passed"
        }
      },
      handoff_edges: [
        { edge_id: "weekly_seed_to_live_dispatch", coherence_failed_count: 0 },
        { edge_id: "reporting_actuals_to_future_planning", coherence_failed_count: 0 }
      ]
    }
  };
}

function ensurePreparedLiveDispatchState(serviceDateId: string) {
  const liveRun =
    state.workflowRuns.find(
      (run) => run.workflow_id === "live_dispatch.v1" && run.partition_key === serviceDateId
    ) ??
    (() => {
      const created = buildStoryRun({
        workflowRunId: "wr-live-001",
        workflowId: "live_dispatch.v1",
        partitionKey: serviceDateId,
        state: "OPEN",
        activeIssueCount: 0
      });
      state.workflowRuns.push(created);
      return created;
    })();

  const liveTask =
    state.humanTasks.find(
      (task) => task.workflow_run_id === liveRun.workflow_run_id && task.task_kind === "dispatch_seed_intake"
    ) ??
    (() => {
      const now = new Date().toISOString();
      const created: HumanTaskRow = {
        human_task_id: "ht-live-001",
        workflow_run_id: liveRun.workflow_run_id,
        task_run_id: "tr-live-stage01-001",
        task_kind: "dispatch_seed_intake",
        state: "OPEN",
        candidate_roles: ["dispatch_supervisor"],
        owner_role: "dispatch_supervisor",
        assignee_actor_id: null,
        assignee_actor_type: null,
        due_at: null,
        escalation_at: null,
        lease_version: 0,
        claimed_at: null,
        claimed_until: null,
        linked_approval_id: null,
        reopen_count: 0,
        generation: 0,
        created_at: now,
        updated_at: now,
        task_run_state: "READY",
        stage_id: "Stage01",
        blocked_on_kind: null,
        blocked_on_ref: null,
        spawned_from_flag_id: null
      };
      state.humanTasks.push(created);
      return created;
    })();

  return { liveRun, liveTask };
}

export function resetApiState(): void {
  state = createContractState();
  resetEodArtifactVersions();
  resetScheduleArtifactVersions();
  resetRouteDemandArtifactVersions();
  resetDriverPreferencesArtifactVersions();
}

export function forceForbiddenResponses(value: boolean): void {
  state.forceForbidden = value;
}

export function mutationLog(): string[] {
  return [...state.audit.mutations];
}

function scheduleArtifactNotFoundResponse(artifactVersionId: string) {
  return HttpResponse.json(
    {
      status: "error",
      error: {
        code: "workpage_artifact_not_found",
        message: "artifact-backed workpage not found",
        details: {
          artifact_version_id: artifactVersionId
        }
      }
    },
    { status: 404 }
  );
}

async function handleScheduleArtifactPreviewRequest(
  artifactVersionId: string,
  request: Request
): Promise<Response> {
  if (!inScope(request)) {
    return scheduleArtifactNotFoundResponse(artifactVersionId);
  }

  const baseVersion = scheduleArtifactVersions.get(artifactVersionId);
  if (!baseVersion) {
    return scheduleArtifactNotFoundResponse(artifactVersionId);
  }

  const body = (await request.json()) as {
    rows?: Array<Record<string, unknown>>;
    reserve_rows?: Array<Record<string, unknown>>;
  };
  const workbookPayload = buildScheduleWorkbookPayload(
    Array.isArray(body.rows) ? body.rows : undefined,
    Array.isArray(body.reserve_rows) ? body.reserve_rows : undefined
  );
  state.audit.mutations.push(`workpage-schedule-artifact-preview:${artifactVersionId}`);
  return ok({
    command: "api.workpages.artifact.preview",
    preview: (schedulePreviewResponse(baseVersion, workbookPayload).preview as Record<string, unknown>) ?? {}
  });
}

async function handleScheduleArtifactSubmitRequest(
  artifactVersionId: string,
  request: Request
): Promise<Response> {
  if (!inScope(request)) {
    return scheduleArtifactNotFoundResponse(artifactVersionId);
  }

  const scheduleBaseVersion = scheduleArtifactVersions.get(artifactVersionId);
  if (!scheduleBaseVersion) {
    return scheduleArtifactNotFoundResponse(artifactVersionId);
  }

  if (scheduleBaseVersion.supersededByArtifactVersionId) {
    return HttpResponse.json(
      {
        status: "error",
        error: {
          code: "workpage_artifact_conflict",
          message: "artifact-backed workpage already has a newer draft",
          details: {
            artifact_version_id: artifactVersionId,
            latest_artifact_version_id: scheduleBaseVersion.latestInChainArtifactVersionId,
            workflow_run_id: scheduleBaseVersion.workflowRunId,
            route: scheduleArtifactRoute(
              scheduleBaseVersion.latestInChainArtifactVersionId,
              scheduleBaseVersion.workflowRunId
            )
          }
        }
      },
      { status: 409 }
    );
  }

  const body = (await request.json()) as {
    rows?: Array<Record<string, unknown>>;
    reserve_rows?: Array<Record<string, unknown>>;
  };
  const submittedArtifactVersionId = nextScheduleArtifactVersionId();
  const submittedVersion = addScheduleArtifactVersion({
    artifactVersionId: submittedArtifactVersionId,
    workflowRunId: scheduleBaseVersion.workflowRunId,
    supersedesArtifactVersionId: artifactVersionId,
    latestInChainArtifactVersionId: submittedArtifactVersionId,
    assignmentRows: Array.isArray(body.rows) ? body.rows : undefined,
    reserveRows: Array.isArray(body.reserve_rows) ? body.reserve_rows : undefined
  });
  scheduleBaseVersion.supersededByArtifactVersionId = submittedArtifactVersionId;
  patchArtifactPayloadLineage(scheduleBaseVersion);
  updateScheduleArtifactChainLatest(submittedArtifactVersionId, submittedArtifactVersionId);

  state.audit.mutations.push(
    `workpage-schedule-artifact-submit:${artifactVersionId}:${submittedArtifactVersionId}`
  );
  return ok({
    command: "api.workpages.artifact.submit",
    submitted: (scheduleArtifactSubmitResponse(submittedVersion, artifactVersionId)
      .submitted as Record<string, unknown>) ?? {}
  });
}

async function handleScheduleSickNoShowRequest(
  artifactVersionId: string,
  request: Request
): Promise<Response> {
  if (!inScope(request)) {
    return scheduleArtifactNotFoundResponse(artifactVersionId);
  }

  const scheduleBaseVersion = scheduleArtifactVersions.get(artifactVersionId);
  if (!scheduleBaseVersion) {
    return scheduleArtifactNotFoundResponse(artifactVersionId);
  }

  if (scheduleBaseVersion.supersededByArtifactVersionId) {
    return HttpResponse.json(
      {
        status: "error",
        error: {
          code: "workpage_artifact_conflict",
          message: "artifact-backed workpage already has a newer draft",
          details: {
            artifact_version_id: artifactVersionId,
            latest_artifact_version_id: scheduleBaseVersion.latestInChainArtifactVersionId,
            workflow_run_id: scheduleBaseVersion.workflowRunId,
            route: scheduleArtifactRoute(
              scheduleBaseVersion.latestInChainArtifactVersionId,
              scheduleBaseVersion.workflowRunId
            )
          }
        }
      },
      { status: 409 }
    );
  }

  const body = (await request.json()) as {
    driver_id?: string;
    service_date?: string;
    reason_note?: string;
    rows?: Array<Record<string, unknown>>;
    reserve_rows?: Array<Record<string, unknown>>;
  };
  const driverId = asString(body.driver_id);
  const serviceDate = asString(body.service_date);
  const assignmentRows = (Array.isArray(body.rows) ? body.rows : scheduleAssignmentRows(scheduleBaseVersion.workbookPayload))
    .map((row) =>
      asString(row.assigned_driver_id) === driverId && asString(row.service_date) === serviceDate
        ? { ...row, assigned_driver_id: "", assignment_status: "manual_override" }
        : { ...row }
    );
  const reserveRows = (Array.isArray(body.reserve_rows) ? body.reserve_rows : scheduleBaseVersion.workbookPayload.reserve_rows)
    .map((row) =>
      asString(row.assigned_driver_id) === driverId && asString(row.service_date) === serviceDate
        ? { ...row, assigned_driver_id: "", assignment_status: "manual_override" }
        : { ...row }
    );
  const submittedArtifactVersionId = nextScheduleArtifactVersionId();
  const submittedVersion = addScheduleArtifactVersion({
    artifactVersionId: submittedArtifactVersionId,
    workflowRunId: scheduleBaseVersion.workflowRunId,
    supersedesArtifactVersionId: artifactVersionId,
    latestInChainArtifactVersionId: submittedArtifactVersionId,
    assignmentRows,
    reserveRows
  });
  markSchedulePayloadSickNoShow(submittedVersion.payload, {
    driverId,
    serviceDate
  });
  scheduleBaseVersion.supersededByArtifactVersionId = submittedArtifactVersionId;
  patchArtifactPayloadLineage(scheduleBaseVersion);
  updateScheduleArtifactChainLatest(submittedArtifactVersionId, submittedArtifactVersionId);

  state.audit.mutations.push(
    `workpage-schedule-sick-no-show:${artifactVersionId}:${submittedArtifactVersionId}:${driverId}:${serviceDate}`
  );
  return ok({
    command: "api.workpages.schedule.sick_no_show",
    submitted: (scheduleArtifactSubmitResponse(submittedVersion, artifactVersionId)
      .submitted as Record<string, unknown>) ?? {}
  });
}

async function handleRouteDemandArtifactSubmitRequest(
  artifactVersionId: string,
  request: Request
): Promise<Response> {
  if (!inScope(request)) {
    return scheduleArtifactNotFoundResponse(artifactVersionId);
  }

  const baseVersion = routeDemandArtifactVersions.get(artifactVersionId);
  if (!baseVersion) {
    return scheduleArtifactNotFoundResponse(artifactVersionId);
  }

  const body = (await request.json()) as {
    daily_demand_rows?: Array<{
      service_date?: string;
      planned_route_count?: number;
    }>;
  };
  const nextDayCards = buildRouteDemandDayCardsFromRequestedCounts(
    baseVersion.dayCards,
    body.daily_demand_rows
  );
  const submittedArtifactVersionId = nextRouteDemandArtifactVersionId();
  const submittedVersion = addRouteDemandArtifactVersion({
    artifactVersionId: submittedArtifactVersionId,
    workflowRunId: baseVersion.workflowRunId,
    supersedesArtifactVersionId: artifactVersionId,
    latestInChainArtifactVersionId: submittedArtifactVersionId,
    dayCards: nextDayCards,
    scheduleImpact: {
      ...baseVersion.scheduleImpact,
      dependency_state: "drifted",
      schedule_state: "drifted",
      refresh_task: null
    },
    futureWeekSeed: baseVersion.futureWeekSeed
  });
  baseVersion.supersededByArtifactVersionId = submittedArtifactVersionId;
  patchArtifactPayloadLineage(baseVersion);
  patchRouteDemandArtifactContractState(baseVersion);
  updateRouteDemandArtifactChainLatest(submittedArtifactVersionId, submittedArtifactVersionId);

  state.audit.mutations.push(
    `workpage-route-demand-artifact-submit:${artifactVersionId}:${submittedArtifactVersionId}`
  );
  return ok({
    command: "api.workpages.artifact.submit",
    submitted: (routeDemandArtifactSubmitResponse(submittedVersion, artifactVersionId)
      .submitted as Record<string, unknown>) ?? {}
  });
}

function createRouteDemandNextWeekResponse(
  workflowRunId: string,
  request: Request
): Response {
  if (!inScope(request)) {
    return forbiddenWorkflowRun();
  }
  const createdVersion = ensureFutureRouteDemandArtifactDraft(workflowRunId);
  state.audit.mutations.push(
    `workpage-route-demand-next-week-create:${workflowRunId}:${createdVersion.workflowRunId}:${createdVersion.artifactVersionId}`
  );
  return ok({
    command: "api.workpages.route_demand.next_week.create",
    created:
      (routeDemandArtifactCreateResponse(createdVersion).created as Record<string, unknown>) ?? {}
  });
}

async function handleRouteDemandSaveAndRunRequest(
  artifactVersionId: string,
  request: Request
): Promise<Response> {
  if (!inScope(request)) {
    return scheduleArtifactNotFoundResponse(artifactVersionId);
  }

  const baseVersion = routeDemandArtifactVersions.get(artifactVersionId);
  if (!baseVersion) {
    return scheduleArtifactNotFoundResponse(artifactVersionId);
  }

  const body = (await request.json()) as {
    daily_demand_rows?: Array<{
      service_date?: string;
      planned_route_count?: number;
    }>;
  };
  const nextDayCards = buildRouteDemandDayCardsFromRequestedCounts(
    baseVersion.dayCards,
    body.daily_demand_rows
  );
  const submittedArtifactVersionId = nextRouteDemandArtifactVersionId();
  const submittedVersion = addRouteDemandArtifactVersion({
    artifactVersionId: submittedArtifactVersionId,
    workflowRunId: baseVersion.workflowRunId,
    supersedesArtifactVersionId: artifactVersionId,
    latestInChainArtifactVersionId: submittedArtifactVersionId,
    dayCards: nextDayCards,
    scheduleImpact: {
      ...baseVersion.scheduleImpact,
      dependency_state: baseVersion.futureWeekSeed ? "aligned" : "drifted",
      schedule_state: baseVersion.futureWeekSeed ? "aligned" : "drifted",
      refresh_task: null
    },
    futureWeekSeed: baseVersion.futureWeekSeed
  });
  baseVersion.supersededByArtifactVersionId = submittedArtifactVersionId;
  patchArtifactPayloadLineage(baseVersion);
  patchRouteDemandArtifactContractState(baseVersion);
  updateRouteDemandArtifactChainLatest(submittedArtifactVersionId, submittedArtifactVersionId);

  const latestScheduleVersion = ensureScheduleArtifactDraft(baseVersion.workflowRunId);
  const coverageContext = buildRouteDemandCoverageContext(
    submittedVersion,
    latestScheduleVersion.artifactVersionId
  );
  state.audit.mutations.push(
    `workpage-route-demand-save-and-run:${artifactVersionId}:${submittedArtifactVersionId}:${baseVersion.workflowRunId}`
  );
  return ok({
    command: "api.workpages.route_demand.save_and_run",
    submitted: {
      ...((routeDemandArtifactSubmitResponse(submittedVersion, artifactVersionId)
        .submitted as Record<string, unknown>) ?? {}),
      target_workflow_run_id: baseVersion.workflowRunId,
      target_schedule_route: `/runs/${baseVersion.workflowRunId}/workpages/schedule-v0`,
      target_schedule_artifact_version_id: latestScheduleVersion.artifactVersionId,
      route_demand_coverage_context: baseVersion.futureWeekSeed ? null : coverageContext
    },
    route_demand_coverage_context: baseVersion.futureWeekSeed ? null : coverageContext
  });
}

async function handleScheduleRouteDemandCoverageCandidatesRequest(
  artifactVersionId: string,
  request: Request
): Promise<Response> {
  if (!inScope(request)) {
    return scheduleArtifactNotFoundResponse(artifactVersionId);
  }

  const scheduleVersion = scheduleArtifactVersions.get(artifactVersionId);
  if (!scheduleVersion) {
    return scheduleArtifactNotFoundResponse(artifactVersionId);
  }

  const body = (await request.json()) as {
    route_demand_artifact_version_id?: string;
    service_dates?: string[];
    rows?: Array<Record<string, unknown>>;
    reserve_rows?: Array<Record<string, unknown>>;
    max_candidates?: number;
  };
  const routeDemandArtifactVersionId = asString(body.route_demand_artifact_version_id);
  const routeDemandVersion = routeDemandArtifactVersions.get(routeDemandArtifactVersionId);
  if (!routeDemandVersion || routeDemandVersion.workflowRunId !== scheduleVersion.workflowRunId) {
    return HttpResponse.json(
      {
        status: "error",
        error: {
          code: "workpage_artifact_not_found",
          message: "route-demand coverage artifact not found",
          details: {
            artifact_version_id: routeDemandArtifactVersionId
          }
        }
      },
      { status: 404 }
    );
  }

  const recommendations = buildRouteDemandCoverageRecommendations({
    scheduleVersion,
    routeDemandVersion,
    assignmentRows: Array.isArray(body.rows)
      ? body.rows.map((row) => ({ ...row }))
      : scheduleAssignmentRows(scheduleVersion.workbookPayload),
    reserveRows: Array.isArray(body.reserve_rows)
      ? body.reserve_rows.map((row) => ({ ...row }))
      : scheduleVersion.workbookPayload.reserve_rows.map((row) => ({ ...row })),
    serviceDates: Array.isArray(body.service_dates)
      ? body.service_dates.map((value) => asString(value)).filter(Boolean)
      : undefined,
    maxCandidates: body.max_candidates
  });

  return ok({
    command: "api.workpages.schedule.route_demand_coverage.candidates",
    route_demand_coverage_recommendations: recommendations
  });
}

async function handleScheduleRouteDemandCoverageApplyRequest(
  artifactVersionId: string,
  request: Request
): Promise<Response> {
  if (!inScope(request)) {
    return scheduleArtifactNotFoundResponse(artifactVersionId);
  }

  const scheduleBaseVersion = scheduleArtifactVersions.get(artifactVersionId);
  if (!scheduleBaseVersion) {
    return scheduleArtifactNotFoundResponse(artifactVersionId);
  }
  if (scheduleBaseVersion.supersededByArtifactVersionId) {
    return HttpResponse.json(
      {
        status: "error",
        error: {
          code: "workpage_artifact_conflict",
          message: "artifact-backed workpage already has a newer draft",
          details: {
            artifact_version_id: artifactVersionId,
            latest_artifact_version_id: scheduleBaseVersion.latestInChainArtifactVersionId,
            workflow_run_id: scheduleBaseVersion.workflowRunId,
            route: scheduleArtifactRoute(
              scheduleBaseVersion.latestInChainArtifactVersionId,
              scheduleBaseVersion.workflowRunId
            )
          }
        }
      },
      { status: 409 }
    );
  }

  const body = (await request.json()) as {
    route_demand_artifact_version_id?: string;
    service_dates?: string[];
    rows?: Array<Record<string, unknown>>;
    reserve_rows?: Array<Record<string, unknown>>;
    selections?: Array<Record<string, unknown>>;
    max_candidates?: number;
  };
  const routeDemandArtifactVersionId = asString(body.route_demand_artifact_version_id);
  const routeDemandVersion = routeDemandArtifactVersions.get(routeDemandArtifactVersionId);
  if (!routeDemandVersion || routeDemandVersion.workflowRunId !== scheduleBaseVersion.workflowRunId) {
    return HttpResponse.json(
      {
        status: "error",
        error: {
          code: "workpage_artifact_not_found",
          message: "route-demand coverage artifact not found",
          details: {
            artifact_version_id: routeDemandArtifactVersionId
          }
        }
      },
      { status: 404 }
    );
  }

  const assignmentRows = Array.isArray(body.rows)
    ? body.rows.map((row) => ({ ...row }))
    : scheduleAssignmentRows(scheduleBaseVersion.workbookPayload);
  const reserveRows = Array.isArray(body.reserve_rows)
    ? body.reserve_rows.map((row) => ({ ...row }))
    : scheduleBaseVersion.workbookPayload.reserve_rows.map((row) => ({ ...row }));
  const recommendations = buildRouteDemandCoverageRecommendations({
    scheduleVersion: scheduleBaseVersion,
    routeDemandVersion,
    assignmentRows,
    reserveRows,
    serviceDates: Array.isArray(body.service_dates)
      ? body.service_dates.map((value) => asString(value)).filter(Boolean)
      : undefined,
    maxCandidates: body.max_candidates
  });
  const selectableCandidateByKey = new Map<string, Record<string, unknown>>();
  asObjectArray(recommendations.candidate_groups).forEach((group) => {
    asObjectArray(group.candidates).forEach((candidate) => {
      if (
        asString(candidate.selection_state) !== "selectable" ||
        asString(candidate.hard_filter_status) !== "pass"
      ) {
        return;
      }
      selectableCandidateByKey.set(
        [
          asString(candidate.target_id),
          asString(candidate.route_slot_id),
          asString(candidate.driver_id)
        ].join("|"),
        candidate
      );
    });
  });
  const targetById = new Map(
    asObjectArray(recommendations.targets).map((target) => [asString(target.target_id), target])
  );
  const requestedSelections = Array.isArray(body.selections)
    ? body.selections.map((selection) => ({
        target_id: asString(selection.target_id),
        route_slot_id: asString(selection.route_slot_id),
        driver_id: asString(selection.driver_id)
      }))
    : [];
  const hasDuplicateSameDayDriverSelection = requestedSelections.some((selection, index) => {
    const target = targetById.get(selection.target_id);
    const serviceDate = asString(target?.service_date);
    if (!serviceDate || !selection.driver_id) {
      return false;
    }
    return requestedSelections.slice(0, index).some((otherSelection) => {
      if (otherSelection.driver_id !== selection.driver_id) {
        return false;
      }
      const otherTarget = targetById.get(otherSelection.target_id);
      return asString(otherTarget?.service_date) === serviceDate;
    });
  });
  if (hasDuplicateSameDayDriverSelection) {
    return HttpResponse.json(
      {
        status: "error",
        error: {
          code: "route_demand_coverage_candidate_blocked",
          message: "selected route-demand coverage candidate is blocked",
          details: {
            artifact_version_id: artifactVersionId,
            route_demand_artifact_version_id: routeDemandArtifactVersionId
          }
        }
      },
      { status: 400 }
    );
  }
  const selectedCandidates = requestedSelections.map((selection) =>
    selectableCandidateByKey.get(
      [selection.target_id, selection.route_slot_id, selection.driver_id].join("|")
    )
  );
  if (
    requestedSelections.length === 0 ||
    selectedCandidates.some((candidate) => candidate == null)
  ) {
    return HttpResponse.json(
      {
        status: "error",
        error: {
          code: "route_demand_coverage_candidate_unavailable",
          message: "selected route-demand coverage candidate is unavailable",
          details: {
            artifact_version_id: artifactVersionId,
            route_demand_artifact_version_id: routeDemandArtifactVersionId
          }
        }
      },
      { status: 400 }
    );
  }

  const selected = selectedCandidates.filter(
    (candidate): candidate is Record<string, unknown> => candidate != null
  );
  const reserveKeysToClear = new Set(
    selected
      .filter((candidate) => Boolean(candidate.clear_same_day_on_call_reserve))
      .map((candidate) =>
        [
          asString(candidate.service_date),
          asString(candidate.reserve_route_slot_id),
          asString(candidate.driver_id)
        ].join("|")
      )
  );
  const nextReserveRows = reserveRows.filter(
    (row) =>
      !reserveKeysToClear.has(
        [
          asString(row.service_date),
          asString(row.route_slot_id),
          asString(row.assigned_driver_id)
        ].join("|")
      )
  );
  const appendedRows = selected.map((candidate) => {
    const target = targetById.get(asString(candidate.target_id));
    return {
      service_date: asString(candidate.service_date),
      route_slot_id: asString(candidate.route_slot_id),
      route_id: asString(candidate.route_id),
      assigned_driver_id: asString(candidate.driver_id),
      assignment_status: "assigned",
      phase: "route_demand_coverage",
      projected_minutes: asNumber(candidate.projected_minutes),
      availability_state: asString(candidate.availability_state) || "AVAILABLE",
      baseline_template_state:
        asString(candidate.baseline_template_state) || "white_template",
      planned_driver_day_state: "assigned",
      new_agreement_required: Boolean(candidate.new_agreement_required),
      new_agreement_trigger_reason: asString(candidate.new_agreement_trigger_reason),
      template_state_preservation_fit: asNumber(candidate.template_state_preservation_fit),
      iteration_index: 24,
      rationale_code: Boolean(candidate.clear_same_day_on_call_reserve)
        ? "route_demand_promote_reserve"
        : "route_demand_assign",
      assignment_action: asString(candidate.assignment_action) || "assign",
      route_slot_class: asString(target?.route_slot_class)
    };
  });
  const submittedArtifactVersionId = nextScheduleArtifactVersionId();
  const submittedVersion = addScheduleArtifactVersion({
    artifactVersionId: submittedArtifactVersionId,
    workflowRunId: scheduleBaseVersion.workflowRunId,
    supersedesArtifactVersionId: artifactVersionId,
    latestInChainArtifactVersionId: submittedArtifactVersionId,
    assignmentRows: [...assignmentRows, ...appendedRows],
    reserveRows: nextReserveRows
  });
  patchScheduleRouteDemandDependency(
    submittedVersion.payload,
    routeDemandArtifactVersionId
  );
  scheduleBaseVersion.supersededByArtifactVersionId = submittedArtifactVersionId;
  patchArtifactPayloadLineage(scheduleBaseVersion);
  updateScheduleArtifactChainLatest(submittedArtifactVersionId, submittedArtifactVersionId);

  state.audit.mutations.push(
    `workpage-schedule-route-demand-coverage:${artifactVersionId}:${submittedArtifactVersionId}`
  );
  return ok({
    command: "api.workpages.schedule.route_demand_coverage.apply",
    submitted: (scheduleArtifactSubmitResponse(submittedVersion, artifactVersionId)
      .submitted as Record<string, unknown>) ?? {},
    route_demand_coverage: {
      route_demand_artifact_version_id: routeDemandArtifactVersionId,
      assigned_count: selected.length,
      appended_assignment_count: appendedRows.length,
      cleared_same_day_reserve_count: reserveRows.length - nextReserveRows.length,
      selected
    }
  });
}

function createDriverPreferencesSnapshotResponse(workflowRunId: string, request: Request): Response {
  if (!inScope(request)) {
    return forbiddenWorkflowRun();
  }

  const existing = latestDriverPreferencesArtifactForRun(workflowRunId);
  if (existing) {
    return HttpResponse.json(
      {
        status: "error",
        error: {
          code: "driver_preferences_snapshot_exists",
          message: "driver preferences snapshot already exists for this workflow run",
          details: {
            workflow_run_id: workflowRunId,
            artifact_version_id: existing.artifactVersionId,
            route: driverPreferencesArtifactRoute(existing.artifactVersionId, workflowRunId)
          }
        }
      },
      { status: 409 }
    );
  }

  const createdArtifactVersionId = nextDriverPreferencesArtifactVersionId();
  const createdVersion = addDriverPreferencesArtifactVersion({
    artifactVersionId: createdArtifactVersionId,
    workflowRunId,
    supersedesArtifactVersionId: null,
    latestInChainArtifactVersionId: createdArtifactVersionId
  });
  state.audit.mutations.push(
    `workpage-driver-preferences-create:${workflowRunId}:${createdArtifactVersionId}`
  );
  return ok({
    command: "api.workpages.driver_preferences.snapshots.create",
    created:
      (driverPreferencesArtifactCreateResponse(createdVersion).created as Record<string, unknown>) ??
      {}
  });
}

async function createDriverAvailabilityExceptionResponse(
  workflowRunId: string,
  request: Request
): Promise<Response> {
  if (!inScope(request)) {
    return forbiddenWorkflowRun();
  }
  const body = (await request.json()) as {
    driver_id?: string;
    start_date?: string;
    end_date?: string;
    reason_code?: string;
    reason_note?: string;
  };
  const latestVersion = latestDriverPreferencesArtifactForRun(workflowRunId);
  const grid = latestVersion?.preferenceGrid ?? buildDriverPreferencesGrid();
  const driver = grid.drivers.find((row) => asString(row.driver_id) === asString(body.driver_id));
  if (!driver) {
    return HttpResponse.json(
      {
        status: "error",
        error: {
          code: "invalid_driver_id",
          message: "driver_id is not available in this weekly planning run",
          details: { driver_id: body.driver_id ?? null }
        }
      },
      { status: 400 }
    );
  }
  const exceptionId = nextDriverAvailabilityExceptionId();
  const item: DriverAvailabilityExceptionState = {
    exception_id: exceptionId,
    driver_id: asString(driver.driver_id),
    driver_name: asString(driver.driver_name),
    start_date: asString(body.start_date),
    end_date: asString(body.end_date),
    reason_code: asString(body.reason_code) || "other",
    reason_note: asString(body.reason_note),
    status: "approved",
    source_workflow_run_id: `wr-availability-request-${exceptionId}`,
    source_artifact_version_id: `av-availability-approved-plan-${exceptionId}`,
    affected_planning_week_ids:
      asString(body.start_date) > "2026-03-28" ? [] : ["PW-2026-W13"],
    source_weekly_workflow_run_id: workflowRunId
  };
  driverAvailabilityExceptions.set(exceptionId, item);
  for (const version of driverPreferencesVersionsForRun(workflowRunId)) {
    version.payload.driver_availability_exceptions = buildDriverAvailabilityExceptionsPayload(
      workflowRunId
    );
  }
  state.audit.mutations.push(
    `workpage-driver-availability-exception-create:${workflowRunId}:${exceptionId}`
  );
  return ok({
    command: "api.workpages.driver_preferences.availability_exceptions.add",
    created: {
      exception: serializeDriverAvailabilityException(item),
      availability_request_workflow_run_id: item.source_workflow_run_id,
      source_artifact_version_id: item.source_artifact_version_id,
      weekly_approved_availability_artifact_version_ids: [
        `av-planning-approved-availability-${exceptionId}`
      ],
      affected_planning_week_ids: item.affected_planning_week_ids,
      affected_service_dates: [item.start_date, item.end_date]
    }
  });
}

async function handleDriverPreferencesArtifactSubmitRequest(
  artifactVersionId: string,
  request: Request
): Promise<Response> {
  if (!inScope(request)) {
    return scheduleArtifactNotFoundResponse(artifactVersionId);
  }

  const baseVersion = driverPreferencesArtifactVersions.get(artifactVersionId);
  if (!baseVersion) {
    return scheduleArtifactNotFoundResponse(artifactVersionId);
  }

  if (baseVersion.supersededByArtifactVersionId) {
    return HttpResponse.json(
      {
        status: "error",
        error: {
          code: "workpage_artifact_conflict",
          message: "artifact-backed workpage already has a newer draft",
          details: {
            artifact_version_id: artifactVersionId,
            latest_artifact_version_id: baseVersion.latestInChainArtifactVersionId,
            workflow_run_id: baseVersion.workflowRunId,
            route: driverPreferencesArtifactRoute(
              baseVersion.latestInChainArtifactVersionId,
              baseVersion.workflowRunId
            )
          }
        }
      },
      { status: 409 }
    );
  }

  const body = (await request.json()) as {
    driver_rows?: Array<{
      driver_id?: string;
      driver_quality?: string;
      preferences_by_weekday?: Record<string, unknown>;
    }>;
  };
  const requestedRows = Array.isArray(body.driver_rows) ? body.driver_rows : [];
  const requestedByDriverId = new Map(requestedRows.map((row) => [asString(row.driver_id), row]));
  const nextPreferenceGrid = cloneDriverPreferenceGrid(baseVersion.preferenceGrid);
  nextPreferenceGrid.drivers = nextPreferenceGrid.drivers.map((row) => {
    const requestedRow = requestedByDriverId.get(asString(row.driver_id));
    if (!requestedRow) {
      return row;
    }
    const requestedPreferences = asObject(requestedRow.preferences_by_weekday) ?? {};
    const requestedDriverQuality = asString(requestedRow.driver_quality).trim().toLowerCase();
    return {
      ...row,
      driver_quality:
        requestedDriverQuality === "high" ||
        requestedDriverQuality === "medium" ||
        requestedDriverQuality === "low"
          ? requestedDriverQuality
          : asString(row.driver_quality).trim().toLowerCase() || "medium",
      preferences_by_weekday: {
        ...asObject(row.preferences_by_weekday),
        sun: asStringOrNull(requestedPreferences.sun),
        mon: asStringOrNull(requestedPreferences.mon),
        tue: asStringOrNull(requestedPreferences.tue),
        wed: asStringOrNull(requestedPreferences.wed),
        thu: asStringOrNull(requestedPreferences.thu),
        fri: asStringOrNull(requestedPreferences.fri),
        sat: asStringOrNull(requestedPreferences.sat)
      }
    };
  });
  const submittedArtifactVersionId = nextDriverPreferencesArtifactVersionId();
  const submittedVersion = addDriverPreferencesArtifactVersion({
    artifactVersionId: submittedArtifactVersionId,
    workflowRunId: baseVersion.workflowRunId,
    supersedesArtifactVersionId: artifactVersionId,
    latestInChainArtifactVersionId: submittedArtifactVersionId,
    preferenceGrid: nextPreferenceGrid,
    scheduleImpact: {
      ...baseVersion.scheduleImpact,
      latest_driver_preferences_artifact_version_id: submittedArtifactVersionId
    }
  });
  baseVersion.supersededByArtifactVersionId = submittedArtifactVersionId;
  patchArtifactPayloadLineage(baseVersion);
  patchDriverPreferencesArtifactContractState(baseVersion);
  updateDriverPreferencesArtifactChainLatest(submittedArtifactVersionId, submittedArtifactVersionId);

  state.audit.mutations.push(
    `workpage-driver-preferences-artifact-submit:${artifactVersionId}:${submittedArtifactVersionId}`
  );
  return ok({
    command: "api.workpages.artifact.submit",
    submitted: (driverPreferencesArtifactSubmitResponse(submittedVersion, artifactVersionId)
      .submitted as Record<string, unknown>) ?? {}
  });
}

export const handlers = [
  http.get("*/api/v1/workpages/workflow-runs/:workflowRunId/schedule-v0", ({ params, request }) => {
    if (!inScope(request)) {
      return forbiddenWorkflowRun();
    }
    return HttpResponse.json(buildRunScheduleWorkpagePayload(String(params.workflowRunId)));
  }),
  http.get(
    "*/api/v1/workpages/workflow-runs/:workflowRunId/driver-preferences-v0",
    ({ params, request }) => {
      if (!inScope(request)) {
        return forbiddenWorkflowRun();
      }
      ensureScheduleArtifactDraft(String(params.workflowRunId));
      return HttpResponse.json(buildRunDriverPreferencesWorkpagePayload(String(params.workflowRunId)));
    }
  ),
  http.post(
    "*/api/v1/workpages/workflow-runs/:workflowRunId/driver-preferences-v0/snapshots",
    ({ params, request }) => createDriverPreferencesSnapshotResponse(String(params.workflowRunId), request)
  ),
  http.post(
    "*/api/v1/workpages/workflow-runs/:workflowRunId/driver-preferences-v0/availability-exceptions",
    ({ params, request }) =>
      createDriverAvailabilityExceptionResponse(String(params.workflowRunId), request)
  ),
  http.get("*/api/v1/workpages/workflow-runs/:workflowRunId/route-demand-v0", ({ params, request }) => {
    if (!inScope(request)) {
      return forbiddenWorkflowRun();
    }
    ensureScheduleArtifactDraft(String(params.workflowRunId));
    return HttpResponse.json(buildRunRouteDemandWorkpagePayload(String(params.workflowRunId)));
  }),
  http.post(
    "*/api/v1/workpages/workflow-runs/:workflowRunId/route-demand-v0/next-week",
    ({ params, request }) =>
      createRouteDemandNextWeekResponse(String(params.workflowRunId), request)
  ),
  http.get("*/api/v1/workpages/workflow-runs/:workflowRunId/eod-v0", ({ params, request }) => {
    if (!inScope(request)) {
      return forbiddenWorkflowRun();
    }
    return HttpResponse.json(buildRunEodWorkpagePayload(String(params.workflowRunId)));
  }),
  http.post("*/api/v1/workpages/workflow-runs/:workflowRunId/eod-v0/drafts", ({ params, request }) => {
    if (!inScope(request)) {
      return forbiddenWorkflowRun();
    }

    const workflowRunId = String(params.workflowRunId);
    const version = ensureEodArtifactDraft(workflowRunId);
    state.audit.mutations.push(
      `workpage-eod-draft-create:${workflowRunId}:${version.artifactVersionId}`
    );
    return ok({
      command: "api.workpages.eod_drafts.create",
      draft:
        (eodArtifactCreateResponse(version, workflowRunId).draft as Record<string, unknown>) ?? {}
    });
  }),
  http.post(
    "*/api/v1/workpages/workflow-runs/:workflowRunId/schedule-v0/artifacts/:artifactVersionId/preview",
    async ({ params, request }) =>
      handleScheduleArtifactPreviewRequest(String(params.artifactVersionId), request)
  ),
  http.get(
    "*/api/v1/workpages/workflow-runs/:workflowRunId/schedule-v0/artifacts/:artifactVersionId",
    ({ params, request }) => {
      if (!inScope(request)) {
        return scheduleArtifactNotFoundResponse(String(params.artifactVersionId));
      }
      ensureScheduleArtifactDraft(String(params.workflowRunId));
      const artifactVersionId = String(params.artifactVersionId);
      const version = scheduleArtifactVersions.get(artifactVersionId);
      if (!version) {
        return scheduleArtifactNotFoundResponse(artifactVersionId);
      }
      patchArtifactPayloadLineage(version);
      return HttpResponse.json(version.payload);
    }
  ),
  http.get(
    "*/api/v1/workpages/workflow-runs/:workflowRunId/driver-preferences-v0/artifacts/:artifactVersionId",
    ({ params, request }) => {
      if (!inScope(request)) {
        return scheduleArtifactNotFoundResponse(String(params.artifactVersionId));
      }
      ensureScheduleArtifactDraft(String(params.workflowRunId));
      const artifactVersionId = String(params.artifactVersionId);
      const version = driverPreferencesArtifactVersions.get(artifactVersionId);
      if (!version) {
        return scheduleArtifactNotFoundResponse(artifactVersionId);
      }
      patchArtifactPayloadLineage(version);
      patchDriverPreferencesArtifactContractState(version);
      return HttpResponse.json(version.payload);
    }
  ),
  http.get(
    "*/api/v1/workpages/workflow-runs/:workflowRunId/route-demand-v0/artifacts/:artifactVersionId",
    ({ params, request }) => {
      if (!inScope(request)) {
        return scheduleArtifactNotFoundResponse(String(params.artifactVersionId));
      }
      ensureScheduleArtifactDraft(String(params.workflowRunId));
      ensureRouteDemandArtifactDraft(String(params.workflowRunId));
      const artifactVersionId = String(params.artifactVersionId);
      const version = routeDemandArtifactVersions.get(artifactVersionId);
      if (!version) {
        return scheduleArtifactNotFoundResponse(artifactVersionId);
      }
      patchArtifactPayloadLineage(version);
      patchRouteDemandArtifactContractState(version);
      return HttpResponse.json(version.payload);
    }
  ),
  http.get(
    "*/api/v1/workpages/workflow-runs/:workflowRunId/eod-v0/artifacts/:artifactVersionId",
    ({ params, request }) => {
      if (!inScope(request)) {
        return scheduleArtifactNotFoundResponse(String(params.artifactVersionId));
      }
      const artifactVersionId = String(params.artifactVersionId);
      const version = eodArtifactVersions.get(artifactVersionId);
      if (!version) {
        return scheduleArtifactNotFoundResponse(artifactVersionId);
      }
      patchArtifactPayloadLineage(version);
      return HttpResponse.json(version.payload);
    }
  ),
  http.post(
    "*/api/v1/workpages/workflow-runs/:workflowRunId/schedule-v0/artifacts/:artifactVersionId/submit",
    async ({ params, request }) =>
      handleScheduleArtifactSubmitRequest(String(params.artifactVersionId), request)
  ),
  http.post(
    "*/api/v1/workpages/workflow-runs/:workflowRunId/schedule-v0/artifacts/:artifactVersionId/sick-no-show",
    async ({ params, request }) =>
      handleScheduleSickNoShowRequest(String(params.artifactVersionId), request)
  ),
  http.post(
    "*/api/v1/workpages/workflow-runs/:workflowRunId/schedule-v0/artifacts/:artifactVersionId/route-demand-coverage-candidates",
    async ({ params, request }) =>
      handleScheduleRouteDemandCoverageCandidatesRequest(
        String(params.artifactVersionId),
        request
      )
  ),
  http.post(
    "*/api/v1/workpages/workflow-runs/:workflowRunId/schedule-v0/artifacts/:artifactVersionId/route-demand-coverage",
    async ({ params, request }) =>
      handleScheduleRouteDemandCoverageApplyRequest(
        String(params.artifactVersionId),
        request
      )
  ),
  http.post(
    "*/api/v1/workpages/workflow-runs/:workflowRunId/route-demand-v0/artifacts/:artifactVersionId/submit",
    async ({ params, request }) =>
      handleRouteDemandArtifactSubmitRequest(String(params.artifactVersionId), request)
  ),
  http.post(
    "*/api/v1/workpages/workflow-runs/:workflowRunId/route-demand-v0/artifacts/:artifactVersionId/save-and-run",
    async ({ params, request }) =>
      handleRouteDemandSaveAndRunRequest(String(params.artifactVersionId), request)
  ),
  http.post(
    "*/api/v1/workpages/workflow-runs/:workflowRunId/driver-preferences-v0/artifacts/:artifactVersionId/submit",
    async ({ params, request }) =>
      handleDriverPreferencesArtifactSubmitRequest(String(params.artifactVersionId), request)
  ),
  http.post("*/api/v1/workpages/workflow-runs/:workflowRunId/eod-v0/artifacts/:artifactVersionId/submit", async ({ params, request }) => {
    if (!inScope(request)) {
      return HttpResponse.json(
        {
          status: "error",
          error: {
            code: "workpage_artifact_not_found",
            message: "artifact-backed workpage not found",
            details: {
              artifact_version_id: String(params.artifactVersionId)
            }
          }
        },
        { status: 404 }
      );
    }

    const artifactVersionId = String(params.artifactVersionId);
    const baseVersion = eodArtifactVersions.get(artifactVersionId);
    if (!baseVersion) {
      return HttpResponse.json(
        {
          status: "error",
          error: {
            code: "workpage_artifact_not_found",
            message: "artifact-backed workpage not found",
            details: {
              artifact_version_id: artifactVersionId
            }
          }
        },
        { status: 404 }
      );
    }

    if (baseVersion.supersededByArtifactVersionId) {
      return HttpResponse.json(
        {
          status: "error",
          error: {
            code: "workpage_artifact_conflict",
            message: "artifact-backed workpage already has a newer draft",
            details: {
              artifact_version_id: artifactVersionId,
              latest_artifact_version_id: baseVersion.latestInChainArtifactVersionId,
              workflow_run_id: baseVersion.workflowRunId,
              route: artifactRoute(
                baseVersion.latestInChainArtifactVersionId,
                baseVersion.workflowRunId
              )
            }
          }
        },
        { status: 409 }
      );
    }

    const body = (await request.json()) as {
      form_values?: Record<string, unknown>;
      checklist_values?: Array<{
        item_id: string;
        selected: boolean;
        note: string;
      }>;
    };
    const submittedArtifactVersionId = nextEodArtifactVersionId();
    const submittedVersion = addEodArtifactVersion({
      artifactVersionId: submittedArtifactVersionId,
      workflowRunId: baseVersion.workflowRunId,
      supersedesArtifactVersionId: artifactVersionId,
      latestInChainArtifactVersionId: submittedArtifactVersionId,
      formValues:
        body.form_values && typeof body.form_values === "object" && !Array.isArray(body.form_values)
          ? body.form_values
          : {},
      checklistValues: Array.isArray(body.checklist_values) ? body.checklist_values : []
    });
    baseVersion.supersededByArtifactVersionId = submittedArtifactVersionId;
    patchArtifactPayloadLineage(baseVersion);
    updateEodArtifactChainLatest(submittedArtifactVersionId, submittedArtifactVersionId);

    state.audit.mutations.push(
      `workpage-eod-artifact-submit:${artifactVersionId}:${submittedArtifactVersionId}`
    );
    return ok({
      command: "api.workpages.artifact.submit",
      submitted: (eodArtifactSubmitResponse(submittedVersion, artifactVersionId)
        .submitted as Record<string, unknown>) ?? {}
    });
  }),
  http.get("*/api/v1/viewer", ({ request }) =>
    ok({
      command: "api.viewer.bootstrap",
      viewer_session: viewerSessionFromRequest(request)
    })
  ),

  http.get("*/api/v1/board/schedule-planning", ({ request }) => {
    if (!inScope(request)) {
      return forbiddenWorkflowRun();
    }

    const url = new URL(request.url);
    const workflowRunId = url.searchParams.get("workflow_run_id");
    const taskState = url.searchParams.get("task_state");
    const assigneeActorId = url.searchParams.get("assignee_actor_id");

    const board = buildBoardContract(state);
    let cards = board.cards.slice();
    if (workflowRunId) {
      cards = cards.filter((card) => card.workflow_run_id === workflowRunId);
    }
    if (taskState) {
      cards = cards.filter((card) => card.card_type !== "human_task" || card.state === taskState);
    }
    if (assigneeActorId) {
      cards = cards.filter(
        (card) => card.card_type !== "human_task" || card.assignee_actor_id === assigneeActorId
      );
    }

    const scopedBoard = {
      ...board,
      cards,
      summary: {
        ...board.summary,
        card_count: cards.length,
        human_task_count: cards.filter((card) => card.card_type === "human_task").length,
        approval_count: cards.filter((card) => card.card_type === "approval").length
      }
    };

    return ok({
      command: "api.board.schedule_planning",
      board: scopedBoard
    });
  }),

  http.get("*/api/v1/stories/logistics-three-workflow", ({ request }) => {
    if (!inScope(request)) {
      return forbiddenWorkflowRun();
    }
    const url = new URL(request.url);
    const planningWeekId = url.searchParams.get("planning_week_id");
    if (!planningWeekId) {
      return HttpResponse.json(
        {
          status: "error",
          error: {
            code: "invalid_query_parameter",
            message: "planning_week_id is required",
            details: { parameter: "planning_week_id" }
          }
        },
        { status: 400 }
      );
    }
    const serviceDateId = url.searchParams.get("service_date_id") ?? undefined;
    return ok({
      command: "api.stories.logistics_three_workflow",
      story: buildLogisticsStoryPayload(planningWeekId, request, serviceDateId)
    });
  }),

  http.get("*/api/v1/human-tasks", ({ request }) => {
    if (!inScope(request)) {
      return forbiddenWorkflowRun();
    }

    const url = new URL(request.url);
    const { limit, offset } = parseLimitOffset(url);
    const workflowRunId = url.searchParams.get("workflow_run_id");
    const stateFilter = url.searchParams.get("state");
    const assigneeActorId = url.searchParams.get("assignee_actor_id");

    let rows = state.humanTasks.slice();
    if (workflowRunId) {
      rows = rows.filter((row) => row.workflow_run_id === workflowRunId);
    }
    if (stateFilter) {
      rows = rows.filter((row) => row.state === stateFilter);
    }
    if (assigneeActorId) {
      rows = rows.filter((row) => row.assignee_actor_id === assigneeActorId);
    }

    return ok({
      command: "api.human_tasks.list",
      human_tasks: rows.slice(offset, offset + limit).map((row) => enrichHumanTaskForResponse(row, request)),
      page: { limit, offset }
    });
  }),

  http.get("*/api/v1/human-tasks/:humanTaskId", ({ params, request }) => {
    if (!inScope(request)) {
      return forbiddenWorkflowRun();
    }
    const humanTaskId = String(params.humanTaskId);
    const row = state.humanTasks.find((task) => task.human_task_id === humanTaskId);
    if (!row) {
      return HttpResponse.json(
        {
          status: "error",
          error: {
            code: "human_task_not_found",
            message: "human task not found",
            details: { human_task_id: humanTaskId }
          }
        },
        { status: 404 }
      );
    }
    return ok({
      command: "api.human_tasks.detail",
      human_task: enrichHumanTaskForResponse(row, request)
    });
  }),

  http.get("*/api/v1/human-tasks/:humanTaskId/subgraph", ({ params, request }) => {
    if (!inScope(request)) {
      return forbiddenWorkflowRun();
    }
    const humanTaskId = String(params.humanTaskId);
    const row = state.humanTasks.find((task) => task.human_task_id === humanTaskId);
    if (!row) {
      return HttpResponse.json(
        {
          status: "error",
          error: {
            code: "human_task_not_found",
            message: "human task not found",
            details: { human_task_id: humanTaskId }
          }
        },
        { status: 404 }
      );
    }
    const metadata = taskSubgraphMetadata(row);
    if (!metadata.is_composite) {
      return HttpResponse.json(
        {
          status: "error",
          error: {
            code: "task_subgraph_not_available",
            message: "task does not expose a composite subgraph",
            details: { human_task_id: humanTaskId, task_kind: row.task_kind }
          }
        },
        { status: 409 }
      );
    }
    const subgraph = buildTaskSubgraph(row);
    if (!subgraph) {
      return HttpResponse.json(
        {
          status: "error",
          error: {
            code: "task_subgraph_not_available",
            message: "task does not expose a composite subgraph",
            details: { human_task_id: humanTaskId, task_kind: row.task_kind }
          }
        },
        { status: 409 }
      );
    }
    return ok({
      command: "api.human_tasks.subgraph",
      human_task_id: humanTaskId,
      is_composite: true,
      expansion_kind: "task_subgraph",
      subgraph
    });
  }),

  http.post("*/api/v1/human-tasks/:humanTaskId/claim", async ({ params, request }) => {
    if (!inScope(request)) {
      return forbiddenWorkflowRun();
    }

    const actorId = request.headers.get("x-onetruth-actor-id") ?? "human:frontend-operator";
    const humanTaskId = String(params.humanTaskId);
    const okMutation = mutateTaskToClaimed(humanTaskId, actorId);
    if (!okMutation) {
      return HttpResponse.json(
        {
          status: "error",
          error: {
            code: "task_not_claimable",
            message: "human task cannot be claimed",
            details: { human_task_id: humanTaskId }
          }
        },
        { status: 409 }
      );
    }

    return ok({
      command: "api.human_tasks.claim",
      human_task_id: humanTaskId,
      result: { ok: true }
    });
  }),

  http.post("*/api/v1/human-tasks/:humanTaskId/complete", async ({ params, request }) => {
    if (!inScope(request)) {
      return forbiddenWorkflowRun();
    }

    const humanTaskId = String(params.humanTaskId);
    const okMutation = mutateTaskToCompleted(humanTaskId);
    if (!okMutation) {
      return HttpResponse.json(
        {
          status: "error",
          error: {
            code: "task_not_completable",
            message: "human task cannot be completed",
            details: { human_task_id: humanTaskId }
          }
        },
        { status: 409 }
      );
    }

    return ok({
      command: "api.human_tasks.complete",
      human_task_id: humanTaskId,
      result: { ok: true }
    });
  }),

  http.post("*/api/v1/human-tasks/:humanTaskId/confirm-review", async ({ params, request }) => {
    if (!inScope(request)) {
      return forbiddenWorkflowRun();
    }

    const humanTaskId = String(params.humanTaskId);
    const body = (await request.json()) as { reviewed_artifact_version_ids?: string[] };
    const reviewedArtifactVersionIds = Array.isArray(body.reviewed_artifact_version_ids)
      ? body.reviewed_artifact_version_ids.filter((value): value is string => typeof value === "string")
      : [];
    const confirmed = confirmTaskReview(humanTaskId, reviewedArtifactVersionIds);
    if (!confirmed) {
      return HttpResponse.json(
        {
          status: "error",
          error: {
            code: "task_not_completable",
            message: "review confirmation requires a claimed task",
            details: { human_task_id: humanTaskId }
          }
        },
        { status: 409 }
      );
    }
    return ok({
      command: "api.human_tasks.confirm_review",
      human_task_id: humanTaskId,
      result: {
        artifact_version: confirmed.artifactVersion,
        idempotent_replay: confirmed.idempotentReplay
      }
    });
  }),

  http.post("*/api/v1/human-tasks/:humanTaskId/stage06-agent-review", ({ params, request }) => {
    if (!inScope(request)) {
      return forbiddenWorkflowRun();
    }

    const humanTaskId = String(params.humanTaskId);
    const task = state.humanTasks.find((row) => row.human_task_id === humanTaskId);
    if (!task) {
      return forbiddenWorkflowRun();
    }

    state.stage06ReviewedTaskIds.add(humanTaskId);
    state.audit.mutations.push(`stage06:${humanTaskId}`);
    return ok({
      command: "api.human_tasks.stage06_agent_review",
      human_task_id: humanTaskId,
      result: {
        classification: {
          outcome: "draft_is_publish_ready",
          rationale_summary: "Mock AI review result for workspace test flow",
          evidence_refs: []
        },
        completion_result: {
          ok: true
        }
      }
    });
  }),

  http.get("*/api/v1/human-tasks/:humanTaskId/artifacts", ({ params, request }) => {
    if (!inScope(request)) {
      return forbiddenWorkflowRun();
    }

    const humanTaskId = String(params.humanTaskId);
    return ok({
      command: "api.human_tasks.artifacts.list",
      artifact_versions: listArtifactsForSubject("human_task", humanTaskId)
    });
  }),

  http.post("*/api/v1/human-tasks/:humanTaskId/artifacts/upload", async ({ params, request }) => {
    if (!inScope(request)) {
      return forbiddenWorkflowRun();
    }
    const humanTaskId = String(params.humanTaskId);
    const body = (await request.json()) as Record<string, unknown>;
    const artifactVersion = addAttachmentArtifact("human_task", humanTaskId, body);
    if (!artifactVersion) {
      return forbiddenWorkflowRun();
    }
    return ok({
      command: "api.human_tasks.artifacts.upload",
      artifact_version: artifactVersion
    });
  }),

  http.get("*/api/v1/approvals", ({ request }) => {
    if (!inScope(request)) {
      return forbiddenWorkflowRun();
    }

    const url = new URL(request.url);
    const { limit, offset } = parseLimitOffset(url);
    const workflowRunId = url.searchParams.get("workflow_run_id");
    const stateFilter = url.searchParams.get("state");

    let rows = state.approvals.slice();
    if (workflowRunId) {
      rows = rows.filter((row) => row.workflow_run_id === workflowRunId);
    }
    if (stateFilter) {
      rows = rows.filter((row) => row.state === stateFilter);
    }

    return ok({
      command: "api.approvals.list",
      approvals: rows.slice(offset, offset + limit),
      page: { limit, offset }
    });
  }),

  http.post("*/api/v1/approvals/:approvalId/respond", async ({ params, request }) => {
    if (!inScope(request)) {
      return forbiddenWorkflowRun();
    }

    const approvalId = String(params.approvalId);
    const body = (await request.json()) as { response_kind?: string };
    const responseKind = body.response_kind ?? "approve";
    const okMutation = mutateApprovalResponse(approvalId, responseKind);
    if (!okMutation) {
      return HttpResponse.json(
        {
          status: "error",
          error: {
            code: "approval_not_respondable",
            message: "approval cannot be responded",
            details: { approval_id: approvalId }
          }
        },
        { status: 409 }
      );
    }

    const updated = state.approvals.find((row) => row.approval_id === approvalId);
    return ok({
      command: "api.approvals.respond",
      approval_id: approvalId,
      approval: updated
    });
  }),

  http.get("*/api/v1/approvals/:approvalId/artifacts", ({ params, request }) => {
    if (!inScope(request)) {
      return forbiddenWorkflowRun();
    }

    const approvalId = String(params.approvalId);
    return ok({
      command: "api.approvals.artifacts.list",
      artifact_versions: listArtifactsForSubject("approval", approvalId)
    });
  }),

  http.post("*/api/v1/approvals/:approvalId/artifacts/upload", async ({ params, request }) => {
    if (!inScope(request)) {
      return forbiddenWorkflowRun();
    }
    const approvalId = String(params.approvalId);
    const body = (await request.json()) as Record<string, unknown>;
    const artifactVersion = addAttachmentArtifact("approval", approvalId, body);
    if (!artifactVersion) {
      return forbiddenWorkflowRun();
    }
    return ok({
      command: "api.approvals.artifacts.upload",
      artifact_version: artifactVersion
    });
  }),

  http.get("*/api/v1/flags", ({ request }) => {
    if (!inScope(request)) {
      return forbiddenWorkflowRun();
    }

    const url = new URL(request.url);
    const { limit, offset } = parseLimitOffset(url);
    const workflowRunId = url.searchParams.get("workflow_run_id");
    const stateFilter = url.searchParams.get("state");
    const severity = url.searchParams.get("severity");

    let rows = state.flags.slice();
    if (workflowRunId) {
      rows = rows.filter((row) => row.workflow_run_id === workflowRunId);
    }
    if (stateFilter) {
      rows = rows.filter((row) => row.state === stateFilter);
    }
    if (severity) {
      rows = rows.filter((row) => row.severity === severity);
    }

    return ok({
      command: "api.flags.list",
      flags: rows.slice(offset, offset + limit),
      page: { limit, offset }
    });
  }),

  http.get("*/api/v1/flags/:flagId/artifacts", ({ params, request }) => {
    if (!inScope(request)) {
      return forbiddenWorkflowRun();
    }

    const flagId = String(params.flagId);
    return ok({
      command: "api.flags.artifacts.list",
      artifact_versions: listArtifactsForSubject("flag", flagId)
    });
  }),

  http.post("*/api/v1/flags/:flagId/artifacts/upload", async ({ params, request }) => {
    if (!inScope(request)) {
      return forbiddenWorkflowRun();
    }
    const flagId = String(params.flagId);
    const body = (await request.json()) as Record<string, unknown>;
    const artifactVersion = addAttachmentArtifact("flag", flagId, body);
    if (!artifactVersion) {
      return forbiddenWorkflowRun();
    }
    return ok({
      command: "api.flags.artifacts.upload",
      artifact_version: artifactVersion
    });
  }),

  http.get("*/api/v1/workflow-runs", ({ request }) => {
    if (!inScope(request)) {
      return forbiddenWorkflowRun();
    }

    const url = new URL(request.url);
    const { limit, offset } = parseLimitOffset(url);
    const stateFilter = url.searchParams.get("state");

    let rows = state.workflowRuns.slice();
    if (stateFilter) {
      rows = rows.filter((row) => row.state === stateFilter);
    }

    return ok({
      command: "api.workflow_runs.list",
      workflow_runs: rows.slice(offset, offset + limit),
      page: { limit, offset }
    });
  }),

  http.get("*/api/v1/workflow-runs/:workflowRunId", ({ params, request }) => {
    if (!inScope(request)) {
      return forbiddenWorkflowRun();
    }

    const workflowRunId = String(params.workflowRunId);
    let detail;
    try {
      detail = buildWorkflowRunDetail(state, workflowRunId);
    } catch {
      return forbiddenWorkflowRun();
    }
    return ok({
      command: "api.workflow_runs.detail",
      ...detail
    });
  }),

  http.get("*/api/v1/workflow-runs/:workflowRunId/workspace", ({ params, request }) => {
    if (!inScope(request)) {
      return forbiddenWorkflowRun();
    }
    const workflowRunId = String(params.workflowRunId);
    let workspace;
    try {
      workspace = buildWorkflowRunWorkspace(state, workflowRunId);
    } catch {
      return forbiddenWorkflowRun();
    }
    return ok({
      command: "api.workflow_runs.workspace",
      workspace
    });
  }),

  http.post("*/api/v1/workflow-runs/:workflowRunId/prepare-live-dispatch-day", async ({ params, request }) => {
    if (!inScope(request)) {
      return forbiddenWorkflowRun();
    }
    const workflowRunId = String(params.workflowRunId);
    const body = (await request.json()) as Record<string, unknown>;
    const serviceDateId =
      typeof body.service_date_id === "string" && body.service_date_id.trim().length > 0
        ? body.service_date_id.trim()
        : "SD-2026-03-06";
    const publishedArtifactVersionId =
      typeof body.published_artifact_version_id === "string"
        ? body.published_artifact_version_id
        : "av-weekly-001";

    const { liveRun, liveTask } = ensurePreparedLiveDispatchState(serviceDateId);
    state.audit.mutations.push(`prepare-live-dispatch:${workflowRunId}:${serviceDateId}`);

    return ok({
      command: "api.workflow_runs.prepare_live_dispatch_day",
      workflow_run_id: workflowRunId,
      result: {
        edge_execution: {
          edge_execution_id: "edge-weekly-live-001",
          edge_id: "weekly_seed_to_live_dispatch",
          source_workflow_run_id: workflowRunId,
          target_workflow_run_id: liveRun.workflow_run_id,
          target_partition_key: serviceDateId,
          status: "activated"
        },
        target_workflow_run: liveRun,
        live_seed_artifact: {
          artifact_version_id: "av-live-001",
          workflow_run_id: liveRun.workflow_run_id,
          task_run_id: liveTask.task_run_id,
          artifact_kind: "dispatch.base_schedule_seed.workbook",
          artifact_role: "official_input",
          media_type: "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
          storage_uri: "memory://story/av-live-001.xlsx",
          content_digest: "sha256:live001",
          byte_size: 860,
          metadata_json: {
            source_artifact_version_id: publishedArtifactVersionId,
            service_date_id: serviceDateId,
            file_name: "dispatch_seed_intake.xlsx"
          },
          parent_artifact_version_id: publishedArtifactVersionId,
          supersedes_artifact_version_id: null,
          lineage_note: null,
          created_at: new Date().toISOString()
        },
        seed_intake_task: enrichHumanTaskForResponse(liveTask, request)
      }
    });
  }),

  http.get("*/api/v1/workflow-runs/:workflowRunId/artifacts", ({ params, request }) => {
    if (!inScope(request)) {
      return forbiddenWorkflowRun();
    }
    const workflowRunId = String(params.workflowRunId);
    return ok({
      command: "api.workflow_runs.artifacts.list",
      artifact_versions: listWorkflowRunArtifacts(workflowRunId)
    });
  }),

  http.post("*/api/v1/workflow-runs/:workflowRunId/artifacts/upload", async ({ params, request }) => {
    if (!inScope(request)) {
      return forbiddenWorkflowRun();
    }
    const workflowRunId = String(params.workflowRunId);
    const body = (await request.json()) as Record<string, unknown>;
    const artifactVersion = addAttachmentArtifact("workflow_run", workflowRunId, body);
    if (!artifactVersion) {
      return forbiddenWorkflowRun();
    }
    return ok({
      command: "api.workflow_runs.artifacts.upload",
      artifact_version: artifactVersion
    });
  }),

  http.get("*/api/v1/templates", ({ request }) => {
    if (!inScope(request)) {
      return forbiddenWorkflowRun();
    }
    const url = new URL(request.url);
    const { limit, offset } = parseLimitOffset(url);
    const templates = listTemplatesFromQuery(url);
    return ok({
      command: "api.templates.list",
      registry: {
        id: "schedule_planning.template_registry",
        workflow_id: "schedule_planning.v1",
        version: 1
      },
      templates: templates.slice(offset, offset + limit),
      page: { limit, offset }
    });
  }),

  http.get("*/api/v1/templates/:templateId/download.bin", ({ params, request }) => {
    if (!inScope(request)) {
      return forbiddenWorkflowRun();
    }
    const templateId = String(params.templateId);
    const template = TEMPLATE_FIXTURES.find((item) => item.template_id === templateId);
    if (!template) {
      return HttpResponse.json(
        {
          status: "error",
          error: {
            code: "template_not_found",
            message: "template not found",
            details: { template_id: templateId }
          }
        },
        { status: 404 }
      );
    }
    state.audit.mutations.push(`template-download-bin:${templateId}`);
    return binaryDownloadResponse(templateDownloadBody(templateId), {
      fileName: template.file_name,
      mediaType: template.media_type,
      requestId: `httpreq_template_${templateId}`
    });
  }),

  http.get("*/api/v1/pointers", ({ request }) => {
    if (!inScope(request)) {
      return forbiddenWorkflowRun();
    }

    const url = new URL(request.url);
    const { limit, offset } = parseLimitOffset(url);
    const workflowRunId = url.searchParams.get("workflow_run_id");

    let rows = state.pointers.slice();
    if (workflowRunId) {
      rows = rows.filter((row) => row.workflow_run_id === workflowRunId);
    }

    return ok({
      command: "api.pointers.list",
      pointers: rows.slice(offset, offset + limit),
      page: { limit, offset }
    });
  }),

  http.get("*/api/v1/timeline-events", ({ request }) => {
    if (!inScope(request)) {
      return forbiddenWorkflowRun();
    }

    const url = new URL(request.url);
    const { limit, offset } = parseLimitOffset(url);
    const workflowRunId = url.searchParams.get("workflow_run_id");
    const eventType = url.searchParams.get("event_type");

    let rows = state.timelineEvents.slice();
    if (workflowRunId) {
      rows = rows.filter((row) => row.links.some((link) => link.id === workflowRunId));
    }
    if (eventType) {
      rows = rows.filter((row) => row.event_type === eventType);
    }

    rows.sort((a, b) => b.sequence_no - a.sequence_no);

    return ok({
      command: "api.timeline_events.list",
      events: rows.slice(offset, offset + limit),
      page: { limit, offset }
    });
  }),

  http.get("*/api/v1/artifacts", ({ request }) => {
    if (!inScope(request)) {
      return forbiddenWorkflowRun();
    }
    const url = new URL(request.url);
    const { limit, offset } = parseLimitOffset(url);
    const workflowRunId = url.searchParams.get("workflow_run_id");
    const subjectKind = url.searchParams.get("subject_kind");
    const subjectId = url.searchParams.get("subject_id");

    let rows = state.artifactVersions.slice();
    if (workflowRunId) {
      rows = rows.filter((artifact) => artifact.workflow_run_id === workflowRunId);
    }
    if (subjectKind && subjectId) {
      rows = rows.filter((artifact) =>
        artifact.links?.some(
          (link) => link.subject_kind === subjectKind && link.subject_id === subjectId
        )
      );
    }

    return ok({
      command: "api.artifacts.list",
      artifact_versions: rows.slice(offset, offset + limit),
      page: { limit, offset }
    });
  }),

  http.get("*/api/v1/artifacts/:artifactVersionId/download.bin", ({ params, request }) => {
    if (!inScope(request)) {
      return forbiddenWorkflowRun();
    }
    const artifactVersionId = String(params.artifactVersionId);
    const scheduleArtifactVersion = scheduleArtifactVersions.get(artifactVersionId);
    if (scheduleArtifactVersion) {
      state.audit.mutations.push(`artifact-download-bin:${artifactVersionId}`);
      return binaryDownloadResponse(
        JSON.stringify(scheduleArtifactVersion.workbookPayload, null, 2),
        {
          fileName: scheduleArtifactVersion.fileName,
          mediaType: "application/json",
          requestId: `httpreq_artifact_${artifactVersionId}`
        }
      );
    }
    const eodArtifactVersion = eodArtifactVersions.get(artifactVersionId);
    if (eodArtifactVersion) {
      state.audit.mutations.push(`artifact-download-bin:${artifactVersionId}`);
      return binaryDownloadResponse(artifactDownloadBody(artifactVersionId), {
        fileName: eodArtifactVersion.fileName,
        mediaType: "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        requestId: `httpreq_artifact_${artifactVersionId}`
      });
    }
    const artifactVersion = state.artifactVersions.find(
      (artifact) => artifact.artifact_version_id === artifactVersionId
    );
    if (!artifactVersion) {
      return forbiddenWorkflowRun();
    }
    state.audit.mutations.push(`artifact-download-bin:${artifactVersionId}`);
    return binaryDownloadResponse(artifactDownloadBody(artifactVersionId), {
      fileName:
        (typeof artifactVersion.metadata_json?.file_name === "string" &&
        artifactVersion.metadata_json.file_name.length > 0
          ? artifactVersion.metadata_json.file_name
          : `${artifactVersionId}`),
      mediaType: artifactVersion.media_type || "application/octet-stream",
      requestId: `httpreq_artifact_${artifactVersionId}`
    });
  })
];
