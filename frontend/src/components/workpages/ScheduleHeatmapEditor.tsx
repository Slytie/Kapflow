import { useMemo, useState } from "react";

import type {
  WorkpageScheduleHeatmapDate,
  WorkpageScheduleHeatmapPerson,
  WorkpageScheduleHeatmapSection,
  WorkpageTableRow
} from "@/lib/types/workpages";

type EditableRowKind = "assignment" | "reserve";

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

interface ScheduleHeatmapDriverState {
  availabilityState?: string;
  complianceState?: string;
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

export function ScheduleHeatmapEditor({
  section,
  assignmentRows,
  reserveRows,
  onRowsChange,
  readOnly = false,
  selectedServiceDate = null,
  availableDriverIds = [],
  driverStateById = {}
}: {
  section: WorkpageScheduleHeatmapSection;
  assignmentRows: WorkpageTableRow[];
  reserveRows: WorkpageTableRow[];
  onRowsChange?: (next: { assignmentRows: WorkpageTableRow[]; reserveRows: WorkpageTableRow[] }) => void;
  readOnly?: boolean;
  selectedServiceDate?: string | null;
  availableDriverIds?: string[];
  driverStateById?: Record<string, ScheduleHeatmapDriverState>;
}): JSX.Element {
  const [armedCell, setArmedCell] = useState<ArmedCell | null>(null);
  const [statusMessage, setStatusMessage] = useState<string | null>(null);

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

  return (
    <section className="workpage-panel schedule-heatmap">
      <header className="workpage-panel__header schedule-heatmap__header">
        <div>
          <h2>{section.title}</h2>
          <p>
            {armedCell
              ? `Moving ${armedCell.driverName}. Pick another cell on ${armedCell.serviceDate} to move or swap it.`
              : section.subtitle ??
                (readOnly
                  ? "Server-authoritative schedule heatmap. Edit controls stay on draft artifact pages."
                  : "Click a filled cell to start moving planned work.")}
          </p>
        </div>
        <div className="schedule-heatmap__legend" aria-label="Heatmap legend">
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
      </header>

      {statusMessage ? <p className="schedule-heatmap__status">{statusMessage}</p> : null}

      <div className="schedule-heatmap__wrap">
        <table className="schedule-heatmap__table">
          <thead>
            <tr>
              <th scope="col">People</th>
              {serviceDates.map((serviceDate) => (
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
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {people.map((person) => {
              const driverState = driverStateById[person.driver_id] ?? {};
              const isAvailableOnSelectedDay = availableDriverIds.includes(person.driver_id);
              return (
              <tr key={person.driver_id}>
                <th
                  scope="row"
                  className={`${
                    isAvailableOnSelectedDay ? "schedule-heatmap__person-cell--available " : ""
                  }${
                    driverState.complianceState === "fail"
                      ? "schedule-heatmap__person-cell--blocked"
                      : ""
                  }`.trim()}
                >
                  <div className="schedule-heatmap__person">
                    <strong>{person.driver_name}</strong>
                    <span>
                      {[person.employment_type, person.on_call_eligible ? "on-call eligible" : ""]
                        .filter((value) => value.length > 0)
                        .join(" · ") || "planner roster"}
                    </span>
                    {selectedServiceDate ? (
                      <span className="schedule-heatmap__person-cues">
                        {isAvailableOnSelectedDay ? "Available on selected day" : "Scheduled on selected day"}
                        {driverState.complianceState === "fail" ? " · Compliance watch" : ""}
                      </span>
                    ) : null}
                  </div>
                </th>
                {serviceDates.map((serviceDate) => {
                  const cell = cellMap.get(`${serviceDate.service_date}:${person.driver_id}`) ?? null;
                  const isArmed =
                    armedCell?.serviceDate === serviceDate.service_date &&
                    armedCell.driverId === person.driver_id;
                  const isSelectedDay = selectedServiceDate === serviceDate.service_date;
                  const isAvailableCell = isSelectedDay && availableDriverIds.includes(person.driver_id);
                  return (
                    <td key={`${person.driver_id}:${serviceDate.service_date}`}>
                      <button
                        type="button"
                        className={`schedule-heatmap__cell schedule-heatmap__cell--${cell?.state ?? "empty"}${cell?.manualOverride ? " schedule-heatmap__cell--manual" : ""}${isArmed ? " is-armed" : ""}${isSelectedDay ? " schedule-heatmap__cell--selected-day" : ""}${isAvailableCell ? " schedule-heatmap__cell--available" : ""}${driverState.complianceState === "fail" ? " schedule-heatmap__cell--blocked" : ""}${readOnly ? " schedule-heatmap__cell--readonly" : ""}`}
                        data-testid={`schedule-heatmap-cell-${serviceDate.service_date}-${person.driver_id}`}
                        aria-label={buildCellLabel(person, serviceDate, cell)}
                        aria-pressed={isArmed}
                        aria-disabled={readOnly}
                        onClick={() => {
                          if (readOnly || !onRowsChange) {
                            setStatusMessage("This view is read-only. Open a draft artifact to move schedule cells.");
                            return;
                          }
                          if (!armedCell) {
                            if (!cell) {
                              setStatusMessage("Pick a planned cell first, then move it to another person on the same day.");
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
                      </button>
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
