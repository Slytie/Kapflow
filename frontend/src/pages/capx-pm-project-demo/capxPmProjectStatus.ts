import type { CapxPmEvidenceFreshness, CapxPmSnapshotReadiness, CapxPmStatus } from "./capxPmProjectTypes";

interface StatusUi {
  className: string;
  label: string;
}

const STATUS_UI: Record<CapxPmStatus, StatusUi> = {
  critical: {
    className: "capx-pm-status--critical",
    label: "critical attention required"
  },
  watch: {
    className: "capx-pm-status--watch",
    label: "watch closely"
  },
  verified: {
    className: "capx-pm-status--verified",
    label: "verified basis"
  },
  neutral: {
    className: "capx-pm-status--neutral",
    label: "neutral projection"
  }
};

export function getCapxPmStatusClass(status: CapxPmStatus): string {
  return STATUS_UI[status].className;
}

export function getCapxPmStatusLabel(status: CapxPmStatus): string {
  return STATUS_UI[status].label;
}

export function getCapxPmEvidenceStatus(freshness: CapxPmEvidenceFreshness): CapxPmStatus {
  switch (freshness) {
    case "conflicting":
    case "stale":
      return "critical";
    case "aging":
      return "watch";
    case "fresh":
      return "verified";
  }
}

export function getCapxPmReadinessStatus(readiness: CapxPmSnapshotReadiness): CapxPmStatus {
  switch (readiness) {
    case "blocked":
      return "critical";
    case "draftable":
      return "watch";
    case "review-ready":
    case "promoted":
      return "verified";
  }
}

export function capxPmStatusRank(status: CapxPmStatus): number {
  switch (status) {
    case "critical":
      return 0;
    case "watch":
      return 1;
    case "neutral":
      return 2;
    case "verified":
      return 3;
  }
}
