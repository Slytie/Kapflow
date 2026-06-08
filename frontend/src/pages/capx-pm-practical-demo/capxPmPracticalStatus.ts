import type { CapxPmPracticalStatus } from "./capxPmPracticalTypes";

interface StatusUi {
  className: string;
  label: string;
  rank: number;
}

const STATUS_UI: Record<CapxPmPracticalStatus, StatusUi> = {
  blocked: {
    className: "capx-pm-practical-status--blocked",
    label: "blocked",
    rank: 0
  },
  "needs-work": {
    className: "capx-pm-practical-status--needs-work",
    label: "needs work",
    rank: 1
  },
  "ready-review": {
    className: "capx-pm-practical-status--ready-review",
    label: "ready for review",
    rank: 2
  },
  "not-started": {
    className: "capx-pm-practical-status--not-started",
    label: "not started",
    rank: 3
  },
  done: {
    className: "capx-pm-practical-status--done",
    label: "done",
    rank: 4
  }
};

export function getCapxPmPracticalStatusClass(status: CapxPmPracticalStatus): string {
  return STATUS_UI[status].className;
}

export function getCapxPmPracticalStatusLabel(status: CapxPmPracticalStatus): string {
  return STATUS_UI[status].label;
}

export function capxPmPracticalStatusRank(status: CapxPmPracticalStatus): number {
  return STATUS_UI[status].rank;
}
