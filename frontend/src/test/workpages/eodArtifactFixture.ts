interface EodArtifactWorkpageOptions {
  artifactVersionId: string;
  workflowRunId?: string;
  latestArtifactVersionId?: string;
  supersedesArtifactVersionId?: string | null;
  supersededByArtifactVersionId?: string | null;
  generatedAt?: string;
}

interface EodArtifactSubmitResponseOptions {
  artifactVersionId: string;
  workflowRunId?: string;
  supersedesArtifactVersionId?: string;
}

const DEFAULT_WORKFLOW_RUN_ID = "wr-eod-artifact-001";
const DEFAULT_GENERATED_AT = "2026-03-25T09:00:00Z";
const DEFAULT_SOURCE_REF =
  "fixtures/workflows/dispatch_reporting/template_pack/Stage03_Threshold_Detection_and_Draft_Packet/Stage03_Threshold_Detection_and_Draft_Packet_upd_draft_Spreadsheet_Template_EMPTY.xlsx";
const WARNING_NOTE =
  "This EOD projection is built from canonical dispatch-reporting artifacts sourced from an intentionally partial 2026-03-16 QDCI / DVC4 example family. Row-level actuals remain the primary truth because the source workbook summary tabs contained broken formulas.";

export function buildEodArtifactWorkpageState(
  options: EodArtifactWorkpageOptions
): Record<string, unknown> {
  const workflowRunId = options.workflowRunId ?? DEFAULT_WORKFLOW_RUN_ID;
  const latestArtifactVersionId = options.latestArtifactVersionId ?? options.artifactVersionId;
  const supersedesArtifactVersionId = options.supersedesArtifactVersionId ?? null;
  const supersededByArtifactVersionId = options.supersededByArtifactVersionId ?? null;
  const generatedAt = options.generatedAt ?? DEFAULT_GENERATED_AT;

  return {
    command: "api.workpages.artifact",
    status: "ok",
    freshness: {
      generated_at: generatedAt,
      source_kind: "artifact_version",
      source_version: options.artifactVersionId
    },
    source: {
      mode: "artifact_projection",
      primary_dataset_key: "reporting.upd_draft.workbook",
      source_artifact_version_id: options.artifactVersionId,
      source_dataset_keys: ["reporting.upd_draft.workbook"],
      source_refs: [DEFAULT_SOURCE_REF]
    },
    artifact_context: {
      artifact_kind: "reporting.upd_draft.workbook",
      artifact_version_id: options.artifactVersionId,
      download_path: `/api/v1/artifacts/${options.artifactVersionId}/download.bin`,
      latest_in_chain_artifact_version_id: latestArtifactVersionId,
      superseded_by_artifact_version_id: supersededByArtifactVersionId,
      supersedes_artifact_version_id: supersedesArtifactVersionId,
      workflow_run_id: workflowRunId
    },
    artifact_history: {
      current_artifact_version_id: options.artifactVersionId,
      latest_artifact_version_id: latestArtifactVersionId,
      previous_artifact_version_id: supersedesArtifactVersionId,
      next_artifact_version_id: null,
      entries: [
        {
          artifact_version_id: options.artifactVersionId,
          workflow_run_id: workflowRunId,
          artifact_kind: "reporting.upd_draft.workbook",
          created_at: generatedAt,
          lineage_note: supersedesArtifactVersionId
            ? "Submitted artifact-backed EOD draft version."
            : "Initial artifact-backed EOD draft seeded from Stage03 template.",
          supersedes_artifact_version_id: supersedesArtifactVersionId,
          route: `/runs/${workflowRunId}/workpages/eod-v0/artifacts/${options.artifactVersionId}`
        }
      ]
    },
    workpage: {
      dataset_key: "reporting.upd_draft.workbook",
      mode: "example",
      sections: [
        {
          kind: "summary_cards",
          title: "Daily summary",
          cards: [
            { key: "total_routes", label: "Total routes actual", value: 0 },
            { key: "packages_dispatched", label: "Packages dispatched", value: 0 },
            { key: "packages_delivered", label: "Packages delivered", value: 0 },
            { key: "packages_returned", label: "Packages returned", value: 0 },
            { key: "delivered_pct", label: "Delivered %", value: "0.00%" },
            { key: "average_route_time", label: "Average route time", value: "0:00:00" }
          ]
        },
        {
          kind: "note_panel",
          title: "Artifact-backed projection note",
          body:
            "This page is projected from an immutable Stage03 reporting workbook artifact. Quality warnings are surfaced from the workbook when present, and formulas are not recomputed."
        },
        {
          kind: "table",
          title: "Route actuals",
          table_id: "route_actuals",
          columns: [
            { key: "route_id", label: "Route" },
            { key: "driver_name", label: "Driver" },
            { key: "packages_dispatched", label: "Dispatched" },
            { key: "packages_delivered", label: "Delivered" },
            { key: "planned_window", label: "Planned" },
            { key: "actual_window", label: "Actual" },
            { key: "actual_minutes", label: "Minutes" },
            { key: "returns", label: "Returns" },
            { key: "return_reasons", label: "Return reasons" },
            { key: "upd_candidate", label: "UPD?" }
          ],
          rows: []
        },
        {
          kind: "form",
          title: "Manual closeout",
          form_id: "closeout_details",
          fields: [
            {
              input: "multi_select",
              key: "sick_calls",
              label: "Sick calls",
              options: [],
              value: []
            },
            {
              input: "multi_select",
              key: "unavailable_drivers",
              label: "Not available",
              options: [],
              value: []
            },
            {
              input: "text",
              key: "working_devices",
              label: "Working devices / rabbits",
              value: ""
            },
            {
              input: "repeater",
              key: "rescues",
              label: "Rescues",
              value: []
            },
            {
              input: "repeater",
              key: "incidents",
              label: "Incidents",
              value: []
            },
            {
              input: "time",
              key: "last_driver_clockout",
              label: "Last driver clock-out",
              value: ""
            },
            {
              input: "textarea",
              key: "dispatcher_comment",
              label: "Dispatcher comment",
              value: ""
            },
            {
              input: "textarea",
              key: "manager_note",
              label: "Manager note",
              value: ""
            }
          ]
        },
        {
          kind: "checklist",
          title: "UPD candidate review",
          checklist_id: "upd_candidates",
          items: []
        },
        {
          kind: "history_stub",
          title: "History",
          entries: [
            { label: "Current artifact version", value: options.artifactVersionId },
            { label: "Supersedes", value: supersedesArtifactVersionId ?? "Initial draft" },
            { label: "Latest draft in chain", value: latestArtifactVersionId }
          ]
        }
      ],
      source_artifact_version_id: options.artifactVersionId,
      source_examples: {},
      summary: {
        actual_dispatched: 0,
        average_route_time: "0:00:00",
        delivered_pct: 0,
        dsp_name: "QDCI",
        formula_integrity_warning: false,
        packages_delivered: 0,
        packages_dispatched: 0,
        packages_returned: 0,
        return_pct: 0,
        service_date: "2026-03-16",
        station_code: "DVC4",
        total_routes_actual: 0,
        warning_note: WARNING_NOTE
      },
      title: "End-of-day report",
      validation: {
        status: "informational",
        warnings: [
          "This workpage is derived from an immutable reporting workbook artifact; the workbook remains authoritative truth.",
          "Submit creates a new superseding workbook artifact version; no in-place workbook mutation occurs."
        ]
      },
      version: 2,
      workflow_id: "dispatch_reporting.v1",
      workpage_id: "eod-v0"
    }
  };
}

export function buildEodArtifactSubmitResponse(
  options: EodArtifactSubmitResponseOptions
): Record<string, unknown> {
  const workflowRunId = options.workflowRunId ?? DEFAULT_WORKFLOW_RUN_ID;

  return {
    command: "api.workpages.artifact.submit",
    status: "ok",
    submitted: {
      artifact_version_id: options.artifactVersionId,
      route: `/runs/${workflowRunId}/workpages/eod-v0/artifacts/${options.artifactVersionId}`,
      supersedes_artifact_version_id: options.supersedesArtifactVersionId ?? null,
      workflow_run_id: workflowRunId
    }
  };
}
