export type CapxDesignAPageId = `P${string}`;

export interface CapxDesignAPage {
  id: CapxDesignAPageId;
  title: string;
  question: string;
  role: string;
  band: string;
  surfaceGroup: string;
  route: string;
  commands: string[];
  blockedShortcuts: string[];
  contractFile: string;
  wireframeFile: string;
}

export interface CapxDesignAWorkItem {
  id: string;
  pageId: CapxDesignAPageId;
  label: string;
  type: string;
  owner: string;
  due: string;
  priority: "P0" | "P1" | "P2";
  state: "Fresh" | "Stale" | "Blocked" | "Policy check" | "Needs evidence";
  basis: string;
  evidence: string;
  policy: string;
}

export interface CapxDesignALifecycleStage {
  name: string;
  state: "official" | "active" | "review" | "blocked" | "planned";
}

const publicBase = "/capx-ui-versions/design-a-final";

export const capxDesignASourceBase = publicBase;

export const capxDesignAPages: CapxDesignAPage[] = [
  {
    id: "P01",
    title: "Role Home / Dashboard",
    question: "What needs my attention today?",
    role: "All role clusters",
    band: "MVP",
    surfaceGroup: "Global / role surfaces",
    route: "/home",
    commands: ["open_project", "open_task", "filter", "save_view", "dismiss_low_priority_notification"],
    blockedShortcuts: [
      "mark_project_green_from_home",
      "resolve_blocker_without_bound_task",
      "publish_dashboard_status_as_truth"
    ],
    contractFile: "P01_role_home_dashboard.md",
    wireframeFile: "P01_role_home_dashboard.svg"
  },
  {
    id: "P02",
    title: "Portfolio Cockpit",
    question: "Which projects have exposure, stale state, or decision needs?",
    role: "Finance manager, executive, PM lead",
    band: "Near-MVP",
    surfaceGroup: "Global / role surfaces",
    route: "/portfolio",
    commands: ["drill_to_project", "open_escalation_task", "filter_portfolio", "generate_portfolio_report"],
    blockedShortcuts: ["edit_project_truth_from_portfolio", "hide_unknown_state", "rank_projects_without_basis"],
    contractFile: "P02_portfolio_cockpit.md",
    wireframeFile: "P02_portfolio_cockpit.svg"
  },
  {
    id: "P03",
    title: "Work Queue / Inbox",
    question: "Which bounded decisions or evidence tasks are assigned to me?",
    role: "All role clusters",
    band: "MVP",
    surfaceGroup: "Global / role surfaces",
    route: "/work-queue",
    commands: ["approve", "reject_or_request_changes", "request_evidence", "comment", "promote_pointer_when_task_bound"],
    blockedShortcuts: ["bulk_approve_without_evidence", "approve_stale_generation", "approve_and_promote_hidden"],
    contractFile: "P03_work_queue_inbox.md",
    wireframeFile: "P03_work_queue_inbox.svg"
  },
  {
    id: "P04",
    title: "Global Search",
    question: "Where is this project, supplier, artifact, task, or claim?",
    role: "PM, procurement, finance",
    band: "Near-MVP",
    surfaceGroup: "Global / role surfaces",
    route: "/search",
    commands: ["search", "filter", "open_entity", "save_search"],
    blockedShortcuts: ["treat_search_result_as_evidence", "open_unpermitted_entity", "promote_from_search"],
    contractFile: "P04_global_search.md",
    wireframeFile: "P04_global_search.svg"
  },
  {
    id: "P05",
    title: "Reports",
    question: "What governed report can be produced from current snapshots?",
    role: "Finance, executive, PM lead",
    band: "Near-MVP",
    surfaceGroup: "Global / role surfaces",
    route: "/reports",
    commands: ["generate_report", "export_snapshot_report", "schedule_report", "open_basis"],
    blockedShortcuts: ["export_raw_ai_summary", "omit_basis_from_report", "remove_unresolved_source_warning"],
    contractFile: "P05_reports.md",
    wireframeFile: "P05_reports.svg"
  },
  {
    id: "P06",
    title: "Admin / Settings",
    question: "How are roles, routes, policies, integrations, and terminology configured?",
    role: "Admin, system owner",
    band: "Post-MVP foundation",
    surfaceGroup: "Global / role surfaces",
    route: "/admin",
    commands: ["manage_roles", "configure_routes", "set_terms", "submit_policy_change"],
    blockedShortcuts: ["self_approve_permission", "disable_audit", "bypass_separation_of_duties"],
    contractFile: "P06_admin_settings.md",
    wireframeFile: "P06_admin_settings.svg"
  },
  {
    id: "P07",
    title: "Project Overview / State Snapshot",
    question: "What is the current governed state and what requires action?",
    role: "Project manager",
    band: "MVP",
    surfaceGroup: "Project core",
    route: "/projects/LYN-42/overview",
    commands: ["open_workpage", "open_task", "request_update", "create_summary_draft", "open_evidence"],
    blockedShortcuts: ["mark_green_directly", "mark_project_closed_directly", "hide_not_forecastable"],
    contractFile: "P07_project_overview_state_snapshot.md",
    wireframeFile: "P07_project_overview_state_snapshot.svg"
  },
  {
    id: "P08",
    title: "Project Intake",
    question: "What is being requested and is it ready for feasibility?",
    role: "PM, requester",
    band: "MVP",
    surfaceGroup: "Project core",
    route: "/projects/LYN-42/intake",
    commands: ["save_draft", "submit_for_feasibility", "request_clarification", "attach_evidence"],
    blockedShortcuts: ["submit_without_required_basis", "confuse_request_with_solution", "skip_upload_scan"],
    contractFile: "P08_project_intake.md",
    wireframeFile: "P08_project_intake.svg"
  },
  {
    id: "P09",
    title: "Corpus Baseline",
    question: "What evidence exists, what role does it play, and what is unresolved?",
    role: "PM, evidence reviewer",
    band: "MVP",
    surfaceGroup: "Project core",
    route: "/projects/LYN-42/corpus",
    commands: ["confirm_role", "merge_packet", "split_packet", "quarantine", "request_extraction", "mark_irrelevant"],
    blockedShortcuts: ["treat_file_as_truth", "ignore_duplicate_context", "extract_from_quarantined_file"],
    contractFile: "P09_corpus_baseline.md",
    wireframeFile: "P09_corpus_baseline.svg"
  },
  {
    id: "P10",
    title: "Lifecycle Stage Map",
    question: "Where are we in the CAPEX lifecycle without forcing waterfall semantics?",
    role: "PM, executive",
    band: "MVP",
    surfaceGroup: "Project core",
    route: "/projects/LYN-42/lifecycle",
    commands: ["open_stage_workpage", "explain_blocker", "request_re_review", "create_stage_task"],
    blockedShortcuts: ["manual_done_toggle", "force_waterfall_lock", "close_stage_without_evidence"],
    contractFile: "P10_lifecycle_stage_map.md",
    wireframeFile: "P10_lifecycle_stage_map.svg"
  },
  {
    id: "P11",
    title: "Feasibility & Business Case",
    question: "Is there a technically plausible and justified reason to continue?",
    role: "PM, finance, technical reviewer",
    band: "MVP/Near-MVP",
    surfaceGroup: "Early project shaping",
    route: "/projects/LYN-42/feasibility",
    commands: [
      "save_feasibility_draft",
      "request_review",
      "submit_decision_proposal",
      "request_external_quote",
      "mark_not_forecastable"
    ],
    blockedShortcuts: [
      "treat_feasibility_as_final_scope",
      "approve_business_case_without_basis",
      "hide_strategic_justification_gap"
    ],
    contractFile: "P11_feasibility_and_business_case.md",
    wireframeFile: "P11_feasibility_and_business_case.svg"
  },
  {
    id: "P12",
    title: "Concept Engineering / Options",
    question: "What solution paths exist and what does each imply?",
    role: "PM, engineering",
    band: "Near-MVP",
    surfaceGroup: "Early project shaping",
    route: "/projects/LYN-42/concepts",
    commands: ["create_option", "attach_quote", "compare_options", "send_to_decision_matrix", "request_option_review"],
    blockedShortcuts: ["select_option_without_review", "hide_option_risk", "treat_budgetary_quote_as_order"],
    contractFile: "P12_concept_engineering_options.md",
    wireframeFile: "P12_concept_engineering_options.svg"
  },
  {
    id: "P13",
    title: "Decision Matrix",
    question: "Which option should become the selected planning baseline and why?",
    role: "PM, steering group",
    band: "Near-MVP",
    surfaceGroup: "Early project shaping",
    route: "/projects/LYN-42/decision-matrix",
    commands: ["score_option", "request_review", "approve_selection", "promote_selected_concept", "freeze_matrix_version"],
    blockedShortcuts: ["recommendation_equals_official", "hide_weights", "promote_selected_concept_without_approval"],
    contractFile: "P13_decision_matrix.md",
    wireframeFile: "P13_decision_matrix.svg"
  },
  {
    id: "P14",
    title: "Basic Engineering / Requirements",
    question: "What exactly must the selected concept satisfy before procurement/execution?",
    role: "PM, engineering",
    band: "Near-MVP",
    surfaceGroup: "Early project shaping",
    route: "/projects/LYN-42/basic-engineering",
    commands: ["create_requirement", "mark_reviewed", "request_evidence", "link_interface", "promote_requirement_baseline"],
    blockedShortcuts: ["procurement_ready_with_open_critical_requirement", "convert_concept_assumption_to_requirement_without_review"],
    contractFile: "P14_basic_engineering_requirements.md",
    wireframeFile: "P14_basic_engineering_requirements.svg"
  },
  {
    id: "P15",
    title: "Budget / Forecast Workpage",
    question: "What is approved, committed, actual, remaining, and forecasted?",
    role: "Finance, PM",
    band: "Near-MVP",
    surfaceGroup: "Control workpages",
    route: "/projects/LYN-42/budget",
    commands: ["edit_budget_draft", "submit_budget_review", "approve_budget_change", "request_variance_explanation", "retry_sync"],
    blockedShortcuts: ["post_unapproved_budget", "hide_variance_basis", "sync_before_official_capex_state"],
    contractFile: "P15_budget_forecast_workpage.md",
    wireframeFile: "P15_budget_forecast_workpage.svg"
  },
  {
    id: "P16",
    title: "Governance / Commitment Chain",
    question: "What was decided, quoted, ordered, revised, caveated, or settled?",
    role: "Procurement, PM",
    band: "MVP",
    surfaceGroup: "Control workpages",
    route: "/projects/LYN-42/commitments",
    commands: ["mark_reviewed", "promote_commitment_chain", "request_supplier_clarification", "create_revision_re_review_task"],
    blockedShortcuts: ["latest_order_equals_official", "ignore_order_revision_delta", "settlement_equals_technical_proof"],
    contractFile: "P16_governance_commitment_chain.md",
    wireframeFile: "P16_governance_commitment_chain.svg"
  },
  {
    id: "P17",
    title: "Assumption Closure",
    question: "Which assumptions are open, closed, contradicted, waived, or stale?",
    role: "PM, engineering, procurement",
    band: "MVP",
    surfaceGroup: "Control workpages",
    route: "/projects/LYN-42/assumptions",
    commands: ["close_assumption_with_evidence", "request_evidence", "waive_assumption", "accept_residual_risk", "create_re_review_task"],
    blockedShortcuts: ["close_because_no_contradiction_found", "close_without_evidence", "close_stale_assumption"],
    contractFile: "P17_assumption_closure.md",
    wireframeFile: "P17_assumption_closure.svg"
  },
  {
    id: "P18",
    title: "Interface Resolution",
    question: "Do required and actual conditions match across owner/supplier/site/process boundaries?",
    role: "PM, engineering, site owner",
    band: "MVP",
    surfaceGroup: "Control workpages",
    route: "/projects/LYN-42/interfaces",
    commands: ["assign_owner", "request_site_measurement", "close_interface", "escalate_mismatch", "request_supplier_clarification"],
    blockedShortcuts: [
      "supplier_requirement_as_owner_capability",
      "close_interface_with_unresolved_mismatch",
      "procurement_ready_with_critical_interface_open"
    ],
    contractFile: "P18_interface_resolution.md",
    wireframeFile: "P18_interface_resolution.svg"
  },
  {
    id: "P19",
    title: "Risk / Stale Cockpit",
    question: "What changed, what became stale, and what must be re-reviewed?",
    role: "PM, PMO, executive",
    band: "MVP",
    surfaceGroup: "Control workpages",
    route: "/projects/LYN-42/risk-stale",
    commands: ["assign_mitigation", "request_re_review", "escalate", "mark_not_forecastable_reason_reviewed", "accept_residual_risk"],
    blockedShortcuts: ["invent_precision", "suppress_not_forecastable", "close_risk_without_re_review_after_trigger"],
    contractFile: "P19_risk_stale_cockpit.md",
    wireframeFile: "P19_risk_stale_cockpit.svg"
  },
  {
    id: "P20",
    title: "Tasks and Approvals",
    question: "What decisions are pending for this project and what evidence supports them?",
    role: "All role clusters",
    band: "MVP",
    surfaceGroup: "Decision / reporting surfaces",
    route: "/projects/LYN-42/tasks-approvals",
    commands: ["approve", "reject_or_request_changes", "request_changes", "promote_pointer", "comment", "delegate_if_policy_allows"],
    blockedShortcuts: ["approve_and_promote_in_one_hidden_step", "approve_stale_artifact", "skip_policy_explanation"],
    contractFile: "P20_tasks_and_approvals.md",
    wireframeFile: "P20_tasks_and_approvals.svg"
  },
  {
    id: "P21",
    title: "CEO / Management Transparency",
    question: "What needs management attention and what can be safely reported?",
    role: "Executive, PM lead",
    band: "Near-MVP",
    surfaceGroup: "Decision / reporting surfaces",
    route: "/projects/LYN-42/management",
    commands: ["publish_governed_summary", "request_decision", "drilldown", "create_escalation_task"],
    blockedShortcuts: ["publish_raw_ai_summary", "hide_stale_state", "turn_unknown_into_green"],
    contractFile: "P21_ceo_management_transparency.md",
    wireframeFile: "P21_ceo_management_transparency.svg"
  },
  {
    id: "P22",
    title: "Handover & Closure Readiness",
    question: "Which kind of closure is achieved, blocked, or only partial?",
    role: "PM, operations, quality",
    band: "Near-MVP/Post-MVP partial",
    surfaceGroup: "Decision / reporting surfaces",
    route: "/projects/LYN-42/handover-closure",
    commands: [
      "accept_handover_with_open_points",
      "close_defect",
      "request_effectiveness_evidence",
      "accept_residual_risk",
      "promote_closure_snapshot"
    ],
    blockedShortcuts: ["handover_equals_closure", "settlement_equals_technical_proof", "local_defect_equals_system_effectiveness"],
    contractFile: "P22_handover_and_closure_readiness.md",
    wireframeFile: "P22_handover_and_closure_readiness.svg"
  },
  {
    id: "P23",
    title: "Design / Drawing / Connection Review",
    question: "Do drawings/connections match requirements and interfaces?",
    role: "Engineering, PM",
    band: "Post-MVP",
    surfaceGroup: "Expansion / support",
    route: "/projects/LYN-42/drawing-review",
    commands: ["review_drawing", "flag_connection_mismatch", "link_requirement", "request_supplier_revision"],
    blockedShortcuts: ["claim_drawing_sufficiency_without_review", "use_unapproved_drawing_as_baseline"],
    contractFile: "P23_design_drawing_connection_review.md",
    wireframeFile: "P23_design_drawing_connection_review.svg"
  },
  {
    id: "P24",
    title: "Asset & Configuration Mapping",
    question: "What asset/configuration state is planned, installed, and accepted?",
    role: "Engineering, maintenance",
    band: "Post-MVP",
    surfaceGroup: "Expansion / support",
    route: "/projects/LYN-42/asset-configuration",
    commands: ["link_asset", "compare_as_built", "promote_config_baseline", "request_asset_evidence"],
    blockedShortcuts: ["installed_equals_documented", "promote_config_without_as_built_evidence"],
    contractFile: "P24_asset_and_configuration_mapping.md",
    wireframeFile: "P24_asset_and_configuration_mapping.svg"
  },
  {
    id: "P25",
    title: "Issue / Hypothesis Evidence Review",
    question: "What issue occurred, what hypotheses explain it, and what evidence closes it?",
    role: "PM, engineering, quality",
    band: "Post-MVP",
    surfaceGroup: "Expansion / support",
    route: "/projects/LYN-42/issues",
    commands: ["create_hypothesis", "link_evidence", "close_local_defect", "verify_effectiveness", "reopen_issue"],
    blockedShortcuts: ["local_fix_equals_effectiveness", "close_issue_without_root_cause_or_waiver"],
    contractFile: "P25_issue_hypothesis_evidence_review.md",
    wireframeFile: "P25_issue_hypothesis_evidence_review.svg"
  },
  {
    id: "P26",
    title: "Lessons / Pattern Library",
    question: "What should future projects learn from this project?",
    role: "PMO, engineering",
    band: "Post-MVP",
    surfaceGroup: "Expansion / support",
    route: "/projects/LYN-42/lessons",
    commands: ["promote_lesson", "reject_lesson", "link_fixture", "create_future_checklist_item"],
    blockedShortcuts: ["auto_promote_ai_lesson", "generalize_without_evidence"],
    contractFile: "P26_lessons_pattern_library.md",
    wireframeFile: "P26_lessons_pattern_library.svg"
  },
  {
    id: "P27",
    title: "Supplier / Counterparty Profile",
    question: "What has this supplier/counterparty committed to or failed to evidence across projects?",
    role: "Procurement, PM",
    band: "Post-MVP",
    surfaceGroup: "Expansion / support",
    route: "/suppliers/VALTOR/profile",
    commands: ["open_supplier_record", "compare_project_patterns", "request_counterparty_clarification"],
    blockedShortcuts: ["blackbox_score_without_evidence", "hide_negative_evidence"],
    contractFile: "P27_supplier_counterparty_profile.md",
    wireframeFile: "P27_supplier_counterparty_profile.svg"
  },
  {
    id: "P28",
    title: "Integration / ERP Sync Status",
    question: "What is official in CAPEX versus posted in downstream systems?",
    role: "Finance, admin, PM",
    band: "Near-MVP/Post-MVP",
    surfaceGroup: "Expansion / support",
    route: "/integrations/erp-sync",
    commands: ["retry_sync", "open_exception", "reconcile", "export_handoff_manifest"],
    blockedShortcuts: ["official_equals_synced", "retry_without_current_manifest", "hide_failed_sync"],
    contractFile: "P28_integration_erp_sync_status.md",
    wireframeFile: "P28_integration_erp_sync_status.svg"
  },
  {
    id: "P29",
    title: "Audit / History",
    question: "Who did what, when, on which version, with what outcome?",
    role: "Auditor, PM, approver",
    band: "MVP foundation",
    surfaceGroup: "Expansion / support",
    route: "/audit",
    commands: ["filter", "export_audit", "open_related_entity", "save_audit_view"],
    blockedShortcuts: ["edit_audit_event", "delete_audit_event", "export_without_scope"],
    contractFile: "P29_audit_history.md",
    wireframeFile: "P29_audit_history.svg"
  },
  {
    id: "P30",
    title: "Evidence Library",
    question: "Where are the source artifacts, occurrences, extracted claims, and packets?",
    role: "PM, evidence reviewer",
    band: "MVP foundation",
    surfaceGroup: "Expansion / support",
    route: "/evidence",
    commands: ["preview", "compare_versions", "open_occurrence", "open_packet", "request_extraction"],
    blockedShortcuts: ["treat_artifact_library_as_truth", "use_unresolved_source_as_basis"],
    contractFile: "P30_evidence_library.md",
    wireframeFile: "P30_evidence_library.svg"
  },
  {
    id: "P31",
    title: "Notifications / Activity Center",
    question: "What changed that I should notice but may not need to decide?",
    role: "All role clusters",
    band: "Near-MVP",
    surfaceGroup: "Expansion / support",
    route: "/notifications",
    commands: ["open_notification", "mute_low_priority", "convert_to_task", "open_bound_object"],
    blockedShortcuts: ["notification_only_approval", "dismiss_critical_task_without_action", "hide_stale_alert"],
    contractFile: "P31_notifications_activity_center.md",
    wireframeFile: "P31_notifications_activity_center.svg"
  }
];

export const capxDesignAWorkflowGroups = [
  "Global / role surfaces",
  "Project core",
  "Early project shaping",
  "Control workpages",
  "Decision / reporting surfaces",
  "Expansion / support"
];

export const capxDesignALifecycleStages: CapxDesignALifecycleStage[] = [
  { name: "Intake", state: "official" },
  { name: "Corpus", state: "official" },
  { name: "Feasibility", state: "review" },
  { name: "Concept", state: "active" },
  { name: "Requirements", state: "blocked" },
  { name: "Commitments", state: "planned" },
  { name: "Closure", state: "planned" }
];

export const capxDesignAWorkItems: CapxDesignAWorkItem[] = [
  {
    id: "CAPX-A-103",
    pageId: "P17",
    label: "Closure evidence gap on supplier utility assumption",
    type: "Evidence request",
    owner: "PM + Engineering",
    due: "Today 14:00",
    priority: "P0",
    state: "Needs evidence",
    basis: "basis:asm-closure-v18",
    evidence: "Two accepted sources, one missing counterparty occurrence",
    policy: "Closure command gated until sufficiency check passes"
  },
  {
    id: "CAPX-A-207",
    pageId: "P20",
    label: "Budget delta approval awaiting separate promotion command",
    type: "Approval",
    owner: "Finance approver",
    due: "Today 16:30",
    priority: "P0",
    state: "Policy check",
    basis: "basis:budget-forecast-v09",
    evidence: "Target version visible with variance source links",
    policy: "Approval does not promote pointer"
  },
  {
    id: "CAPX-A-312",
    pageId: "P18",
    label: "Owner/site interface mismatch blocks procurement readiness",
    type: "Interface blocker",
    owner: "Site owner",
    due: "Tomorrow",
    priority: "P1",
    state: "Blocked",
    basis: "basis:interface-map-v12",
    evidence: "Supplier condition conflicts with owner capability measurement",
    policy: "Cannot close interface with unresolved mismatch"
  },
  {
    id: "CAPX-A-421",
    pageId: "P28",
    label: "ERP sync failed against current handoff manifest",
    type: "Integration exception",
    owner: "Finance ops",
    due: "2 days",
    priority: "P1",
    state: "Stale",
    basis: "basis:erp-manifest-v04",
    evidence: "Official CAPEX state differs from downstream posting",
    policy: "Retry requires current manifest and visible failed-sync reason"
  },
  {
    id: "CAPX-A-512",
    pageId: "P01",
    label: "Dashboard status shortcut rejected by command policy",
    type: "Blocked shortcut",
    owner: "PM lead",
    due: "Read-only",
    priority: "P2",
    state: "Fresh",
    basis: "basis:project-snapshot-v31",
    evidence: "Dashboard drills to governed snapshot and audit path",
    policy: "Dashboard display cannot publish truth"
  }
];

export const capxDesignAComponentRules = [
  "ProjectStateBanner shows lifecycle, official snapshot, forecastability, stale/blocked state, and tasks.",
  "BasisVersionPanel appears on governed pages and blocks truth-changing commands when unresolved or stale.",
  "CommandPanel always produces a user-visible receipt and never mutates truth silently.",
  "EvidenceDrawer distinguishes source occurrence, artifact role, extraction, review, and official baseline input.",
  "AuditTimeline is immutable and remains available for critical objects."
];

export const capxDesignAMobileRules = [
  "Desktop keeps dense workpage behavior with filters, rows, drawer, evidence, audit, and command panels.",
  "Tablet supports walkthrough, status review, task triage, and light evidence preview.",
  "Mobile presents assigned tasks, approvals, missing-evidence requests, stale alerts, comments, and read-only snapshots.",
  "Authoritative mobile commands require online revalidation."
];

export function getCapxDesignAPageById(pageId: string | undefined): CapxDesignAPage {
  const normalizedId = pageId?.toUpperCase();
  return capxDesignAPages.find((page) => page.id === normalizedId) ?? capxDesignAPages[0];
}

export function getCapxDesignAContractSrc(page: CapxDesignAPage): string {
  return `${publicBase}/workflow_pages/${page.contractFile}`;
}

export function getCapxDesignAWireframeSrc(page: CapxDesignAPage): string {
  return `${publicBase}/wireframes/${page.wireframeFile}`;
}
