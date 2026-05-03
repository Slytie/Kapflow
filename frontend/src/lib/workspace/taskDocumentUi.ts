import type {
  WorkflowWorkspaceRequiredReview,
  WorkflowWorkspaceRequiredUpload
} from "@/lib/types/contracts";

const FRIENDLY_DOCUMENT_LABELS: Record<string, string> = {
  "planning.route_slot_requirements.workbook": "Route Slot Requirements",
  "planning.approved_availability.workbook": "Approved Availability",
  "planning.driver_capabilities.workbook": "Driver Capabilities",
  "planning.actual_hours_snapshot.workbook": "Actual Hours Snapshot",
  "planning.route_horizon.doc": "Route Horizon Context",
  "planning.manager_review.doc": "Manager Review Packet",
  "planning.published_weekly_schedule.workbook": "Published Weekly Schedule",
  "schedule.supervisor_review.doc": "Supervisor Review Packet",
  "dispatch.base_schedule_seed.workbook": "Base Schedule Seed",
  "reporting.eos_raw.workbook": "EOS Raw Workbook",
  "reporting.actuals_normalized.workbook": "Normalized Actuals",
  "reporting.upd_draft.workbook": "UPD Draft Workbook",
  "reporting.manager_review.doc": "Manager Review Packet",
  "reporting.final_packet.workbook": "Final Packet Workbook"
};

export type TaskDocumentTone = "danger" | "warning" | "success" | "neutral";

export interface TaskDocumentPreviewCue {
  key: string;
  label: string;
  tone: TaskDocumentTone;
}

export interface TaskDocumentDisplayLabel {
  label: string;
  canonicalKey: string | null;
}

export type TaskRequiredDocumentRow =
  | {
      key: string;
      kind: "upload";
      tone: TaskDocumentTone;
      statusLabel: string;
      display: TaskDocumentDisplayLabel;
      meta: string;
      actionLabel: "Add File" | "Replace";
      requirement: WorkflowWorkspaceRequiredUpload;
      templateLabel: string | null;
    }
  | {
      key: string;
      kind: "review";
      tone: TaskDocumentTone;
      statusLabel: string;
      display: TaskDocumentDisplayLabel;
      meta: string;
      actionLabel: "View" | null;
      review: WorkflowWorkspaceRequiredReview;
    };

interface TaskDocumentPreviewSource {
  missing_required_inputs?: string[];
  required_uploads?: WorkflowWorkspaceRequiredUpload[];
  required_reviews?: WorkflowWorkspaceRequiredReview[];
  available_actions?: string[];
  linked_artifact_count?: number;
  artifact_count?: number;
}

interface TaskRequiredDocumentSource {
  required_uploads?: WorkflowWorkspaceRequiredUpload[];
  required_reviews?: WorkflowWorkspaceRequiredReview[];
}

function pluralize(count: number, singular: string, plural = `${singular}s`): string {
  return `${count} ${count === 1 ? singular : plural}`;
}

function requirementTypeLabel(requirement: WorkflowWorkspaceRequiredUpload): string {
  if (requirement.required === false) {
    return "Optional context";
  }
  if (requirement.artifact_role === "official_input") {
    return "Required input";
  }
  return "Required upload";
}

function uploadTone(
  requirement: WorkflowWorkspaceRequiredUpload
): { tone: TaskDocumentTone; statusLabel: string } {
  if (requirement.status === "satisfied" || requirement.current_count >= requirement.required_count) {
    return {
      tone: "success",
      statusLabel: "Satisfied"
    };
  }
  if (requirement.required === false) {
    return {
      tone: "neutral",
      statusLabel: "Optional"
    };
  }
  return {
    tone: "danger",
    statusLabel: "Missing"
  };
}

function reviewTone(review: WorkflowWorkspaceRequiredReview): {
  tone: TaskDocumentTone;
  statusLabel: string;
} {
  if (review.status === "confirmed") {
    return {
      tone: "success",
      statusLabel: "Reviewed"
    };
  }
  return {
    tone: "warning",
    statusLabel: "Review Required"
  };
}

export function taskDocumentDisplayLabel(
  key: string | null | undefined
): TaskDocumentDisplayLabel {
  const normalizedKey = key?.trim() ?? "";
  if (normalizedKey.length === 0) {
    return {
      label: "Untitled document",
      canonicalKey: null
    };
  }
  const friendlyLabel = FRIENDLY_DOCUMENT_LABELS[normalizedKey];
  if (friendlyLabel) {
    return {
      label: friendlyLabel,
      canonicalKey: normalizedKey
    };
  }
  return {
    label: normalizedKey,
    canonicalKey: null
  };
}

export function buildTaskDocumentPreviewCues(
  source: TaskDocumentPreviewSource
): TaskDocumentPreviewCue[] {
  const requiredUploads = source.required_uploads ?? [];
  const requiredReviews = source.required_reviews ?? [];
  const missingRequiredInputs = source.missing_required_inputs ?? [];
  const availableActions = source.available_actions ?? [];
  const artifactCount = source.artifact_count ?? source.linked_artifact_count ?? 0;

  const missingUploads = requiredUploads.filter(
    (requirement) =>
      requirement.required !== false &&
      requirement.status !== "satisfied" &&
      requirement.current_count < requirement.required_count
  ).length;
  const pendingReviewCount = requiredReviews.filter((review) => review.status !== "confirmed").length;
  const hasReviewAction = availableActions.some((action) => action.toLowerCase() === "confirm_review");

  const cues: TaskDocumentPreviewCue[] = [];

  const missingCount = Math.max(missingRequiredInputs.length, missingUploads);
  if (missingCount > 0) {
    cues.push({
      key: "missing",
      label: pluralize(missingCount, "missing input"),
      tone: "danger"
    });
  }

  if (pendingReviewCount > 0 || hasReviewAction) {
    cues.push({
      key: "review",
      label:
        pendingReviewCount > 0
          ? pluralize(pendingReviewCount, "review", "reviews") + " required"
          : "Review required",
      tone: "warning"
    });
  }

  if (artifactCount > 0) {
    cues.push({
      key: "artifacts",
      label: pluralize(artifactCount, "artifact"),
      tone: "neutral"
    });
  }

  if (cues.length === 0 && (requiredUploads.length > 0 || requiredReviews.length > 0)) {
    cues.push({
      key: "ready",
      label: "Docs ready",
      tone: "success"
    });
  }

  return cues.slice(0, 3);
}

export function buildTaskRequiredDocumentRows(
  source: TaskRequiredDocumentSource
): TaskRequiredDocumentRow[] {
  const requiredUploads = source.required_uploads ?? [];
  const requiredReviews = source.required_reviews ?? [];

  const uploadRows: TaskRequiredDocumentRow[] = requiredUploads.map((requirement) => {
    const display = taskDocumentDisplayLabel(requirement.dataset_key);
    const uploadState = uploadTone(requirement);
    const statusDetail =
      requirement.status === "satisfied" || requirement.current_count >= requirement.required_count
        ? `${Math.min(requirement.current_count, requirement.required_count)} of ${requirement.required_count} submitted`
        : requirement.required === false
          ? "Optional context not yet attached"
          : "Missing required submission";
    const metaParts = [
      display.canonicalKey,
      requirementTypeLabel(requirement),
      statusDetail
    ].filter((part): part is string => Boolean(part));

    return {
      key: `upload:${requirement.dataset_key}:${requirement.artifact_kind}`,
      kind: "upload",
      tone: uploadState.tone,
      statusLabel: uploadState.statusLabel,
      display,
      meta: metaParts.join(" · "),
      actionLabel:
        requirement.status === "satisfied" || requirement.current_count > 0 ? "Replace" : "Add File",
      requirement,
      templateLabel: requirement.template_id ? "Download template" : null
    };
  });

  const reviewRows: TaskRequiredDocumentRow[] = requiredReviews.map((review) => {
    const display = taskDocumentDisplayLabel(review.dataset_key || review.artifact_kind);
    const reviewState = reviewTone(review);
    const statusDetail =
      review.status === "confirmed"
        ? "Review confirmed"
        : review.reviewed_artifact_version_id
          ? "Draft ready for review"
          : "Waiting for draft artifact";
    const metaParts = [display.canonicalKey, "Required review", statusDetail].filter(
      (part): part is string => Boolean(part)
    );

    return {
      key: `review:${review.dataset_key}:${review.artifact_kind}`,
      kind: "review",
      tone: reviewState.tone,
      statusLabel: reviewState.statusLabel,
      display,
      meta: metaParts.join(" · "),
      actionLabel: review.reviewed_artifact_version_id ? "View" : null,
      review
    };
  });

  return [...uploadRows, ...reviewRows];
}
