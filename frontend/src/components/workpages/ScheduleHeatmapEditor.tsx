import { useMemo, useState, type ReactNode } from "react";

import { InfoDialog } from "@/components/InfoDialog";
import type {
  WorkpageScheduleCalculationTopBarDay,
  WorkpageScheduleDriverMetric,
  WorkpageScheduleHeatmapDate,
  WorkpageScheduleHeatmapPerson,
  WorkpageScheduleHeatmapSection,
  WorkpageTableRow
} from "@/lib/types/workpages";

type EditableRowKind = "assignment" | "reserve";
type DriverPreferenceState =
  | "open_to_work"
  | "prefer_not_to_work"
  | "definitely_can_not_work"
  | "unset";

interface DerivedHeatmapCell {
  driverId: string;
  serviceDate: string;
  state: "assigned" | "on_call";
  rowKind: EditableRowKind;
  rowIndex: number;
  routeSlotId: string | null;
  projectedMinutes: number | null;
  assignmentStatus: string | null;
  plannedDriverDayState: string | null;
  manualOverride: boolean;
}

interface ArmedCell {
  driverId: string;
  driverName: string;
  serviceDate: string;
  rowKind: EditableRowKind;
  rowIndex: number;
}

interface AvailabilityCellState {
  state: string | null;
  reasonCode: string | null;
  sourceRef: string | null;
}

export interface ScheduleSickNoShowTarget {
  driverId: string;
  driverName: string;
  serviceDate: string;
  serviceDateLabel: string;
  currentState: "assigned" | "on_call" | "empty";
}

function asText(value: unknown): string {
  return typeof value === "string" ? value.trim() : String(value ?? "").trim();
}

function asNumberOrNull(value: unknown): number | null {
  if (typeof value === "number" && Number.isFinite(value)) {
    return value;
  }
  const text = asText(value);
  if (!text) {
    return null;
  }
  const parsed = Number(text);
  return Number.isFinite(parsed) ? parsed : null;
}

function buildServiceDates(
  section: WorkpageScheduleHeatmapSection,
  assignmentRows: WorkpageTableRow[],
  reserveRows: WorkpageTableRow[]
): WorkpageScheduleHeatmapDate[] {
  if (section.service_dates.length > 0) {
    return section.service_dates;
  }
  const dates = Array.from(
    new Set(
      [...assignmentRows, ...reserveRows]
        .map((row) => asText(row.service_date))
        .filter((serviceDate) => serviceDate.length > 0)
    )
  ).sort();
  return dates.map((serviceDate) => ({
    service_date: serviceDate,
    label: serviceDate,
    weekday_label: serviceDate
  }));
}

function buildPeople(
  section: WorkpageScheduleHeatmapSection,
  assignmentRows: WorkpageTableRow[],
  reserveRows: WorkpageTableRow[]
): WorkpageScheduleHeatmapPerson[] {
  const people = new Map(section.people.map((person) => [person.driver_id, person]));
  for (const row of [...assignmentRows, ...reserveRows]) {
    const driverId = asText(row.assigned_driver_id);
    if (!driverId || people.has(driverId)) {
      continue;
    }
    people.set(driverId, {
      driver_id: driverId,
      driver_name: driverId,
      employment_type: "",
      on_call_eligible: false,
      previous_week_minutes: 0,
      availability_summary: "driver only present in the current draft rows",
      cells: []
    });
  }
  return Array.from(people.values());
}

function buildCellMap(
  assignmentRows: WorkpageTableRow[],
  reserveRows: WorkpageTableRow[]
): Map<string, DerivedHeatmapCell> {
  const cellMap = new Map<string, DerivedHeatmapCell>();
  assignmentRows.forEach((row, rowIndex) => {
    const driverId = asText(row.assigned_driver_id);
    const serviceDate = asText(row.service_date);
    if (!driverId || !serviceDate) {
      return;
    }
    cellMap.set(`${serviceDate}:${driverId}`, {
      driverId,
      serviceDate,
      state: "assigned",
      rowKind: "assignment",
      rowIndex,
      routeSlotId: asText(row.route_slot_id) || null,
      projectedMinutes: asNumberOrNull(row.projected_minutes),
      assignmentStatus: asText(row.assignment_status) || null,
      plannedDriverDayState: asText(row.planned_driver_day_state) || null,
      manualOverride: asText(row.assignment_status) === "manual_override"
    });
  });
  reserveRows.forEach((row, rowIndex) => {
    const driverId = asText(row.assigned_driver_id);
    const serviceDate = asText(row.service_date);
    if (!driverId || !serviceDate) {
      return;
    }
    const key = `${serviceDate}:${driverId}`;
    if (cellMap.has(key)) {
      return;
    }
    cellMap.set(key, {
      driverId,
      serviceDate,
      state: "on_call",
      rowKind: "reserve",
      rowIndex,
      routeSlotId: asText(row.route_slot_id) || null,
      projectedMinutes: asNumberOrNull(row.projected_minutes),
      assignmentStatus: asText(row.assignment_status) || null,
      plannedDriverDayState: asText(row.planned_driver_day_state) || null,
      manualOverride: asText(row.assignment_status) === "manual_override"
    });
  });
  return cellMap;
}

function buildPreferenceStateMap(
  people: WorkpageScheduleHeatmapPerson[]
): Map<string, DriverPreferenceState> {
  const stateMap = new Map<string, DriverPreferenceState>();
  for (const person of people) {
    for (const cell of person.cells) {
      stateMap.set(
        `${cell.service_date}:${person.driver_id}`,
        normalizePreferenceState(cell.preference_state)
      );
    }
  }
  return stateMap;
}

function buildAvailabilityStateMap(
  people: WorkpageScheduleHeatmapPerson[]
): Map<string, AvailabilityCellState> {
  const stateMap = new Map<string, AvailabilityCellState>();
  for (const person of people) {
    for (const cell of person.cells) {
      stateMap.set(`${cell.service_date}:${person.driver_id}`, {
        state: cell.availability_state ?? null,
        reasonCode: cell.availability_reason_code ?? null,
        sourceRef: cell.availability_source_ref ?? null
      });
    }
  }
  return stateMap;
}

function cloneRows(rows: WorkpageTableRow[]): WorkpageTableRow[] {
  return rows.map((row) => ({ ...row }));
}

function setManualOverride(
  rows: WorkpageTableRow[],
  rowIndex: number,
  driverId: string
): WorkpageTableRow[] {
  return rows.map((row, index) =>
    index === rowIndex
      ? {
          ...row,
          assigned_driver_id: driverId,
          assignment_status: "manual_override"
        }
      : row
  );
}

function buildCellLabel(
  person: WorkpageScheduleHeatmapPerson,
  serviceDate: WorkpageScheduleHeatmapDate,
  cell: DerivedHeatmapCell | null
): string {
  const base = `${person.driver_name} on ${serviceDate.label}`;
  if (!cell) {
    return `${base}: no planned work`;
  }
  const stateLabel = cell.state === "on_call" ? "on call" : "assigned route";
  const overrideLabel = cell.manualOverride ? ", manually overridden" : "";
  return `${base}: ${stateLabel}${overrideLabel}`;
}

function formatDriverHours(hours: number | null | undefined): string {
  return typeof hours === "number" && Number.isFinite(hours) ? `${hours.toFixed(1)} h` : "—";
}

function formatStateLabel(state: string | null | undefined): string {
  const value = asText(state);
  if (!value) {
    return "—";
  }
  return value
    .split("_")
    .map((segment) => segment.charAt(0).toUpperCase() + segment.slice(1))
    .join(" ");
}

function normalizePreferenceState(state: string | null | undefined): DriverPreferenceState {
  const value = asText(state);
  if (
    value === "open_to_work" ||
    value === "prefer_not_to_work" ||
    value === "definitely_can_not_work"
  ) {
    return value;
  }
  return "unset";
}

function formatPreferenceStateLabel(state: DriverPreferenceState): string {
  if (state === "open_to_work") {
    return "Open to work";
  }
  if (state === "prefer_not_to_work") {
    return "Prefer not to work";
  }
  if (state === "definitely_can_not_work") {
    return "Cannot work";
  }
  return "Unset";
}

function isSickNoShowAvailability(availability: AvailabilityCellState | null | undefined): boolean {
  return availability?.reasonCode === "sick_no_show";
}

function pillToneForState(state: string | null | undefined): string {
  if (state === "pass" || state === "available") {
    return "success";
  }
  if (state === "fail" || state === "approved_unavailable") {
    return "danger";
  }
  if (state === "warn" || state === "scheduled") {
    return "warn";
  }
  return "neutral";
}

export function ScheduleHeatmapEditor({
  section,
  assignmentRows,
  reserveRows,
  onRowsChange,
  readOnly = false,
  selectedServiceDate = null,
  availableDriverIds = [],
  driverMetrics = [],
  topBarDays = [],
  density = "default",
  headerExtras = null,
  onMarkSickNoShow,
  sickNoShowDisabled = false,
  sickNoShowPendingKey = null
}: {
  section: WorkpageScheduleHeatmapSection;
  assignmentRows: WorkpageTableRow[];
  reserveRows: WorkpageTableRow[];
  onRowsChange?: (next: { assignmentRows: WorkpageTableRow[]; reserveRows: WorkpageTableRow[] }) => void;
  readOnly?: boolean;
  selectedServiceDate?: string | null;
  availableDriverIds?: string[];
  driverMetrics?: WorkpageScheduleDriverMetric[];
  topBarDays?: WorkpageScheduleCalculationTopBarDay[];
  density?: "default" | "compact";
  headerExtras?: ReactNode;
  onMarkSickNoShow?: (target: ScheduleSickNoShowTarget) => void;
  sickNoShowDisabled?: boolean;
  sickNoShowPendingKey?: string | null;
}): JSX.Element {
  const [armedCell, setArmedCell] = useState<ArmedCell | null>(null);
  const [statusMessage, setStatusMessage] = useState<string | null>(null);
  const isCompact = density === "compact";

  const serviceDates = useMemo(
    () => buildServiceDates(section, assignmentRows, reserveRows),
    [assignmentRows, reserveRows, section]
  );
  const people = useMemo(
    () => buildPeople(section, assignmentRows, reserveRows),
    [assignmentRows, reserveRows, section]
  );
  const cellMap = useMemo(
    () => buildCellMap(assignmentRows, reserveRows),
    [assignmentRows, reserveRows]
  );
  const preferenceStateByCell = useMemo(() => buildPreferenceStateMap(people), [people]);
  const availabilityStateByCell = useMemo(() => buildAvailabilityStateMap(people), [people]);
  const driverMetricById = useMemo(
    () => new Map(driverMetrics.map((metric) => [metric.driver_id, metric])),
    [driverMetrics]
  );
  const topBarDayByServiceDate = useMemo(
    () => new Map(topBarDays.map((day) => [day.service_date, day])),
    [topBarDays]
  );

  return (
    <section className={`workpage-panel schedule-heatmap${isCompact ? " schedule-heatmap--compact" : ""}`}>
      <header className="workpage-panel__header schedule-heatmap__header">
        <div className="schedule-heatmap__header-copy">
          <span className="schedule-heatmap__eyebrow">Weekly planning grid</span>
          <h2>{section.title}</h2>
          {!isCompact || armedCell ? (
            <p>
              {armedCell
                ? `Moving ${armedCell.driverName}. Pick another cell on ${armedCell.serviceDate} to move or swap it.`
                : section.subtitle ??
                  (readOnly
                    ? "Server-authoritative schedule heatmap. Edit controls stay on draft artifact pages."
                    : "Click a filled cell to start moving planned work.")}
            </p>
          ) : null}
        </div>
        <div className="schedule-heatmap__header-meta">
          <div className="schedule-heatmap__header-toolbar">
            <section
              className="schedule-heatmap__header-group schedule-heatmap__header-group--legend"
              aria-label="Heatmap legend"
            >
              <span className="schedule-heatmap__legend-label">Legend</span>
              <div className="schedule-heatmap__legend">
                <span className="schedule-heatmap__legend-item">
                  <span className="schedule-heatmap__legend-swatch schedule-heatmap__legend-swatch--assigned" />
                  Assigned route
                </span>
                <span className="schedule-heatmap__legend-item">
                  <span className="schedule-heatmap__legend-swatch schedule-heatmap__legend-swatch--reserve" />
                  On call
                </span>
                <span className="schedule-heatmap__legend-item">
                  <span className="schedule-heatmap__legend-swatch schedule-heatmap__legend-swatch--empty" />
                  No planned work
                </span>
                <span className="schedule-heatmap__legend-item">
                  <span className="schedule-heatmap__legend-swatch schedule-heatmap__legend-swatch--manual" />
                  Manual override
                </span>
              </div>
            </section>
            {headerExtras}
          </div>
        </div>
      </header>

      {statusMessage ? (
        <p className="schedule-heatmap__status" role="status">
          {statusMessage}
        </p>
      ) : null}

      <div className="schedule-heatmap__wrap">
        <table className="schedule-heatmap__table">
          <thead>
            <tr>
              <th scope="col" className="schedule-heatmap__person-header">
                <span aria-hidden="true">Roster</span>
                <strong>People</strong>
              </th>
              <th scope="col" className="schedule-heatmap__metric-header schedule-heatmap__metric-header--hours">
                <span aria-hidden="true">Metrics</span>
                <strong>{isCompact ? "Hrs" : "Hours"}</strong>
              </th>
              <th scope="col" className="schedule-heatmap__metric-header schedule-heatmap__metric-header--routes">
                <span aria-hidden="true">Metrics</span>
                <strong>{isCompact ? "Rt" : "Routes"}</strong>
              </th>
              <th scope="col" className="schedule-heatmap__metric-header schedule-heatmap__metric-header--on-call">
                <span aria-hidden="true">Metrics</span>
                <strong>{isCompact ? "OC" : "On call"}</strong>
              </th>
              <th
                scope="col"
                className="schedule-heatmap__metric-header schedule-heatmap__metric-header--compliance"
              >
                <span aria-hidden="true">Risk</span>
                <strong>{isCompact ? "Risk" : "Compliance"}</strong>
              </th>
              {serviceDates.map((serviceDate) => {
                const dayStats = topBarDayByServiceDate.get(serviceDate.service_date) ?? null;
                return (
                  <th
                    key={serviceDate.service_date}
                    scope="col"
                    className={
                      selectedServiceDate === serviceDate.service_date
                        ? "schedule-heatmap__date-header schedule-heatmap__date-header--selected"
                        : "schedule-heatmap__date-header"
                    }
                  >
                    <span>{serviceDate.weekday_label}</span>
                    <strong>{serviceDate.label}</strong>
                    {dayStats ? (
                      <dl
                        className="schedule-heatmap__date-stats"
                        aria-label={`Daily stats for ${serviceDate.label}`}
                      >
                        <div>
                          <dt>Req</dt>
                          <dd>{dayStats.routes_required}</dd>
                        </div>
                        <div>
                          <dt>Sched</dt>
                          <dd>{dayStats.routes_scheduled ?? "—"}</dd>
                        </div>
                        <div>
                          <dt>OC</dt>
                          <dd>
                            {dayStats.on_call_drivers ?? "—"} / {dayStats.on_call_target}
                          </dd>
                        </div>
                        <div>
                          <dt>Avail</dt>
                          <dd>{dayStats.available_driver_count ?? "—"}</dd>
                        </div>
                      </dl>
                    ) : null}
                  </th>
                );
              })}
            </tr>
          </thead>
          <tbody>
            {people.map((person) => {
              const metric = driverMetricById.get(person.driver_id) ?? null;
              const isAvailableOnSelectedDay = availableDriverIds.includes(person.driver_id);
              const personCellClassName = [
                "schedule-heatmap__person-cell",
                isAvailableOnSelectedDay ? "schedule-heatmap__person-cell--available" : "",
                metric?.compliance_state === "fail" ? "schedule-heatmap__person-cell--blocked" : ""
              ]
                .filter(Boolean)
                .join(" ");
              return (
                <tr key={person.driver_id}>
                  <th scope="row" className={personCellClassName}>
                    <div className="schedule-heatmap__person">
                      <strong>{person.driver_name}</strong>
                      {!isCompact ? (
                        <span className="schedule-heatmap__person-meta">
                          {[person.employment_type, person.on_call_eligible ? "on-call eligible" : ""]
                            .filter((value) => value.length > 0)
                            .join(" · ") || "planner roster"}
                        </span>
                      ) : null}
                      {!isCompact && selectedServiceDate ? (
                        <span className="schedule-heatmap__person-cues">
                          {isAvailableOnSelectedDay ? "Available on selected day" : "Scheduled on selected day"}
                          {metric?.compliance_state === "fail" ? " · Compliance watch" : ""}
                        </span>
                      ) : null}
                    </div>
                  </th>
                  <td className="schedule-heatmap__metric-cell schedule-heatmap__metric-cell--hours">
                    <span className="schedule-heatmap__metric-value">
                      {formatDriverHours(metric?.scheduled_hours)}
                    </span>
                  </td>
                  <td className="schedule-heatmap__metric-cell schedule-heatmap__metric-cell--routes">
                    <span className="schedule-heatmap__metric-value">
                      {metric ? String(metric.scheduled_routes) : "—"}
                    </span>
                  </td>
                  <td className="schedule-heatmap__metric-cell schedule-heatmap__metric-cell--on-call">
                    <span className="schedule-heatmap__metric-value">
                      {metric ? String(metric.on_call_shifts) : "—"}
                    </span>
                  </td>
                  <td className="schedule-heatmap__metric-cell schedule-heatmap__metric-cell--compliance">
                    {metric ? (
                      <div className="schedule-heatmap__compliance-cell">
                        {metric.issues.length > 0 ? (
                          <InfoDialog
                            className={`schedule-pill schedule-pill--${pillToneForState(
                              metric.compliance_state
                            )} schedule-heatmap__risk-trigger`}
                            triggerLabel={`Open compliance details for ${person.driver_name}`}
                            dialogTitle={`Compliance details for ${person.driver_name}`}
                            dialogDescription={`${formatStateLabel(
                              metric.compliance_state
                            )} status from backend schedule calculations.`}
                            triggerContent={
                              <>
                                <span>{formatStateLabel(metric.compliance_state)}</span>
                                <span className="schedule-heatmap__risk-trigger-icon" aria-hidden="true">
                                  i
                                </span>
                              </>
                            }
                          >
                            <div className="schedule-heatmap__issue-panel">
                              <p className="schedule-heatmap__issue-description">
                                These compliance issues come directly from backend schedule
                                calculations for this driver.
                              </p>
                              <div className="schedule-heatmap__issue-summary">
                                <span
                                  className={`schedule-pill schedule-pill--${pillToneForState(
                                    metric.compliance_state
                                  )}`}
                                >
                                  {formatStateLabel(metric.compliance_state)}
                                </span>
                                <span>{`${metric.issues.length} issue${
                                  metric.issues.length === 1 ? "" : "s"
                                }`}</span>
                              </div>
                              <ul className="schedule-heatmap__issue-list">
                                {metric.issues.map((issue) => (
                                  <li key={issue}>{issue}</li>
                                ))}
                              </ul>
                            </div>
                          </InfoDialog>
                        ) : (
                          <span
                            className={`schedule-pill schedule-pill--${pillToneForState(
                              metric.compliance_state
                            )}`}
                          >
                            {formatStateLabel(metric.compliance_state)}
                          </span>
                        )}
                      </div>
                    ) : (
                      <span className="schedule-heatmap__metric-value">—</span>
                    )}
                  </td>
                  {serviceDates.map((serviceDate) => {
                    const cellKey = `${serviceDate.service_date}:${person.driver_id}`;
                    const cell = cellMap.get(cellKey) ?? null;
                    const preferenceState =
                      preferenceStateByCell.get(cellKey) ?? "unset";
                    const availabilityState = availabilityStateByCell.get(cellKey) ?? null;
                    const isSickNoShow = isSickNoShowAvailability(availabilityState);
                    const preferenceLabel = formatPreferenceStateLabel(preferenceState);
                    const isArmed =
                      armedCell?.serviceDate === serviceDate.service_date &&
                      armedCell.driverId === person.driver_id;
                    const isSelectedDay = selectedServiceDate === serviceDate.service_date;
                    const isAvailableCell = isSelectedDay && availableDriverIds.includes(person.driver_id);
                    const sickNoShowPending = sickNoShowPendingKey === cellKey;
                    const sickNoShowActionDisabled =
                      sickNoShowDisabled || sickNoShowPending || isSickNoShow;
                    return (
                      <td key={`${person.driver_id}:${serviceDate.service_date}`}>
                        <div className="schedule-heatmap__cell-wrap">
                          <button
                            type="button"
                            className={`schedule-heatmap__cell schedule-heatmap__cell--${
                              cell?.state ?? "empty"
                            }${cell?.manualOverride ? " schedule-heatmap__cell--manual" : ""}${
                              isArmed ? " is-armed" : ""
                            }${isSelectedDay ? " schedule-heatmap__cell--selected-day" : ""}${
                              isAvailableCell ? " schedule-heatmap__cell--available" : ""
                            }${metric?.compliance_state === "fail" ? " schedule-heatmap__cell--blocked" : ""}${
                              isSickNoShow ? " schedule-heatmap__cell--sick-no-show" : ""
                            }${readOnly ? " schedule-heatmap__cell--readonly" : ""}`}
                            data-testid={`schedule-heatmap-cell-${serviceDate.service_date}-${person.driver_id}`}
                            aria-label={
                              isSickNoShow
                                ? `Sick / No Show: ${person.driver_name} on ${serviceDate.label}`
                                : buildCellLabel(person, serviceDate, cell)
                            }
                            aria-pressed={isArmed}
                            aria-disabled={readOnly}
                            onClick={() => {
                            if (readOnly || !onRowsChange) {
                              setStatusMessage(
                                "This view is read-only. Open a draft artifact to move schedule cells."
                              );
                              return;
                            }
                            if (!armedCell) {
                              if (!cell) {
                                setStatusMessage(
                                  "Pick a planned cell first, then move it to another person on the same day."
                                );
                                return;
                              }
                              setArmedCell({
                                driverId: person.driver_id,
                                driverName: person.driver_name,
                                serviceDate: serviceDate.service_date,
                                rowKind: cell.rowKind,
                                rowIndex: cell.rowIndex
                              });
                              setStatusMessage(null);
                              return;
                            }

                            if (
                              armedCell.driverId === person.driver_id &&
                              armedCell.serviceDate === serviceDate.service_date
                            ) {
                              setArmedCell(null);
                              setStatusMessage("Move cleared.");
                              return;
                            }

                            if (armedCell.serviceDate !== serviceDate.service_date) {
                              setStatusMessage("Moves stay within the same service day.");
                              return;
                            }

                            let nextAssignmentRows = cloneRows(assignmentRows);
                            let nextReserveRows = cloneRows(reserveRows);

                            const sourceDriverId = armedCell.driverId;

                            if (!cell) {
                              if (armedCell.rowKind === "assignment") {
                                nextAssignmentRows = setManualOverride(
                                  nextAssignmentRows,
                                  armedCell.rowIndex,
                                  person.driver_id
                                );
                              } else {
                                nextReserveRows = setManualOverride(
                                  nextReserveRows,
                                  armedCell.rowIndex,
                                  person.driver_id
                                );
                              }
                              onRowsChange({
                                assignmentRows: nextAssignmentRows,
                                reserveRows: nextReserveRows
                              });
                              setArmedCell(null);
                              setStatusMessage(
                                `${armedCell.driverName} moved to ${person.driver_name} on ${serviceDate.service_date}.`
                              );
                              return;
                            }

                            if (armedCell.rowKind === "assignment") {
                              nextAssignmentRows = setManualOverride(
                                nextAssignmentRows,
                                armedCell.rowIndex,
                                person.driver_id
                              );
                            } else {
                              nextReserveRows = setManualOverride(
                                nextReserveRows,
                                armedCell.rowIndex,
                                person.driver_id
                              );
                            }

                            if (cell.rowKind === "assignment") {
                              nextAssignmentRows = setManualOverride(
                                nextAssignmentRows,
                                cell.rowIndex,
                                sourceDriverId
                              );
                            } else {
                              nextReserveRows = setManualOverride(
                                nextReserveRows,
                                cell.rowIndex,
                                sourceDriverId
                              );
                            }

                            onRowsChange({
                              assignmentRows: nextAssignmentRows,
                              reserveRows: nextReserveRows
                            });
                            setArmedCell(null);
                            setStatusMessage(
                              `${armedCell.driverName} and ${person.driver_name} swapped on ${serviceDate.service_date}.`
                            );
                          }}
                        >
                          <span className="schedule-heatmap__cell-top">
                            <span className="schedule-heatmap__cell-state">
                              {cell?.state === "assigned"
                                ? "Route"
                                : cell?.state === "on_call"
                                  ? "On call"
                                  : "Open"}
                            </span>
                            {cell?.manualOverride ? (
                              <span className="schedule-heatmap__cell-chip">Edited</span>
                            ) : null}
                          </span>
                          <span className="schedule-heatmap__cell-meta">
                            {cell?.projectedMinutes ? `${cell.projectedMinutes} min` : "—"}
                          </span>
                          <span
                            className={`schedule-heatmap__preference-bar schedule-heatmap__preference-bar--${preferenceState}`}
                            data-testid={`schedule-heatmap-preference-${serviceDate.service_date}-${person.driver_id}`}
                            aria-label={`Preference: ${preferenceLabel}`}
                            title={`Preference: ${preferenceLabel}`}
                          />
                          </button>
                          {onMarkSickNoShow ? (
                            <button
                              type="button"
                              className="schedule-heatmap__sick-button"
                              disabled={sickNoShowActionDisabled}
                              aria-label={`Mark Sick / No Show: ${person.driver_name} on ${serviceDate.label}`}
                              title={
                                isSickNoShow
                                  ? `${person.driver_name} is already Sick / No Show on ${serviceDate.label}`
                                  : `Mark ${person.driver_name} Sick / No Show on ${serviceDate.label}`
                              }
                              onClick={() => {
                                if (sickNoShowActionDisabled) {
                                  return;
                                }
                                onMarkSickNoShow({
                                  driverId: person.driver_id,
                                  driverName: person.driver_name,
                                  serviceDate: serviceDate.service_date,
                                  serviceDateLabel: serviceDate.label,
                                  currentState: cell?.state ?? "empty"
                                });
                              }}
                            >
                              {sickNoShowPending ? "..." : isSickNoShow ? "Sick / No Show" : "Sick"}
                            </button>
                          ) : null}
                        </div>
                      </td>
                    );
                  })}
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </section>
  );
}
