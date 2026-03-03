from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class Scenario:
    scenario_id: str
    trace_name: str
    title: str
    required_event_types: tuple[str, ...]
    expected_workflow_states: dict[str, str] = field(default_factory=dict)
    expected_task_states: dict[str, str] = field(default_factory=dict)
    expected_pointer_targets: dict[str, str] = field(default_factory=dict)
    expected_approval_outcomes: dict[str, str] = field(default_factory=dict)
    expected_execution_states: dict[str, str] = field(default_factory=dict)
    expected_tool_states: dict[str, str] = field(default_factory=dict)
    expected_degraded_components: dict[str, str] = field(default_factory=dict)
    required_stage_ids: tuple[str, ...] = ()
    require_agent_only_claims: bool = False
    require_no_pointer_promotions: bool = False


SCENARIO_CATALOG: dict[str, Scenario] = {
    "AT-SCH-001": Scenario(
        scenario_id="AT-SCH-001",
        trace_name="schedule_happy_path_publish_and_replan.jsonl",
        title="Happy path publish plus additive replan",
        required_event_types=(
            "workflow.run.created",
            "workflow.run.state_changed",
            "approval.requested",
            "approval.responded",
            "artifact.version.created",
            "artifact.pointer.promoted",
            "flag.created",
            "task.run.created",
            "task.run.state_changed",
        ),
        expected_workflow_states={"run-sd-2026-03-04": "SUCCEEDED"},
        expected_task_states={
            "tr-stage03-001": "SUCCEEDED",
            "tr-stage04-001": "SUCCEEDED",
            "tr-stage05-001": "SUCCEEDED",
            "tr-stage06-001": "SUCCEEDED",
            "tr-stage07-001": "SUCCEEDED",
        },
        expected_pointer_targets={
            "schedule.published_schedule.workbook": "av-published-001",
            "schedule.replan_delta.workbook": "av-replan-001",
        },
        expected_approval_outcomes={
            "apr-publish-001": "approved",
            "apr-replan-001": "approved",
        },
        required_stage_ids=("Stage03", "Stage04", "Stage05", "Stage06", "Stage07"),
    ),
    "AT-SCH-002": Scenario(
        scenario_id="AT-SCH-002",
        trace_name="schedule_drift_after_review.jsonl",
        title="Drift after review is visible",
        required_event_types=(
            "approval.requested",
            "approval.responded",
            "artifact.pointer.drift_detected",
            "artifact.pointer.promoted",
            "task.run.state_changed",
        ),
        expected_workflow_states={"run-sd-2026-03-04": "ACTIVE"},
        expected_task_states={"tr-stage06-drift-001": "STALE"},
        expected_pointer_targets={"schedule.published_schedule.workbook": "av-published-candidate-002"},
        expected_approval_outcomes={"apr-drift-001": "approved"},
        required_stage_ids=("Stage06",),
    ),
    "AT-SCH-003": Scenario(
        scenario_id="AT-SCH-003",
        trace_name="schedule_fully_agentive_whole_flow.jsonl",
        title="Fully agentive whole-flow debug slice",
        required_event_types=(
            "workflow.run.created",
            "workflow.run.state_changed",
            "task.created",
            "task.claimed",
            "task.completed",
            "execution.session.created",
            "execution.session.state_changed",
            "tool.execution.requested",
            "tool.execution.approved",
            "tool.execution.completed",
            "approval.requested",
            "approval.responded",
            "artifact.pointer.promoted",
        ),
        expected_workflow_states={"run-sd-2026-03-04": "SUCCEEDED"},
        expected_pointer_targets={
            "schedule.published_schedule.workbook": "av-agent-published-001",
            "schedule.replan_delta.workbook": "av-agent-replan-001",
        },
        expected_approval_outcomes={
            "apr-agent-publish-001": "approved",
            "apr-agent-replan-001": "approved",
        },
        expected_execution_states={
            "xs-stage03-agent-001": "SUCCEEDED",
            "xs-stage04-agent-001": "SUCCEEDED",
            "xs-stage05-agent-001": "SUCCEEDED",
            "xs-stage06-agent-001": "SUCCEEDED",
            "xs-stage07-agent-001": "SUCCEEDED",
        },
        required_stage_ids=("Stage03", "Stage04", "Stage05", "Stage06", "Stage07"),
        require_agent_only_claims=True,
    ),
    "AT-SCH-004": Scenario(
        scenario_id="AT-SCH-004",
        trace_name="schedule_lease_expiry_recovery.jsonl",
        title="Issue-specific lease expiry and recovery",
        required_event_types=(
            "flag.created",
            "task.created",
            "task.claimed",
            "task.lease_expired",
            "task.completed",
            "task.run.state_changed",
        ),
        expected_workflow_states={"run-sd-2026-03-04": "ACTIVE"},
        expected_task_states={"tr-stage07-lease-001": "SUCCEEDED"},
        required_stage_ids=("Stage07",),
    ),
    "AT-SCH-005": Scenario(
        scenario_id="AT-SCH-005",
        trace_name="schedule_degraded_mode_survivability.jsonl",
        title="Degraded mode while truth writes continue",
        required_event_types=(
            "workflow.run.created",
            "audit.degraded_mode.changed",
            "artifact.version.created",
            "artifact.pointer.promoted",
        ),
        expected_workflow_states={"run-sd-2026-03-04": "ACTIVE"},
        expected_pointer_targets={"schedule.replan_delta.workbook": "av-degraded-001"},
        expected_degraded_components={"projection_exporter": "normal"},
    ),
    "AT-SCH-006": Scenario(
        scenario_id="AT-SCH-006",
        trace_name="schedule_cross_scope_denial.jsonl",
        title="Cross-scope negative",
        required_event_types=(
            "workflow.run.created",
            "task.run.created",
            "task.created",
            "task.claimed",
            "execution.session.created",
            "tool.execution.requested",
            "tool.execution.denied",
            "execution.session.state_changed",
            "task.run.state_changed",
        ),
        expected_workflow_states={"run-sd-2026-03-04": "ACTIVE"},
        expected_task_states={"tr-stage05-scope-001": "FAILED"},
        expected_execution_states={"xs-stage05-scope-001": "FAILED"},
        expected_tool_states={"tx-stage05-scope-001": "DENIED"},
        required_stage_ids=("Stage05",),
        require_no_pointer_promotions=True,
    ),
    "AT-SCH-007": Scenario(
        scenario_id="AT-SCH-007",
        trace_name="schedule_policy_gate_enforced.jsonl",
        title="Sandbox and policy gate enforced before publish-version tool execution",
        required_event_types=(
            "flag.created",
            "task.run.created",
            "task.created",
            "task.claimed",
            "execution.session.created",
            "tool.execution.requested",
            "tool.execution.denied",
            "approval.requested",
            "approval.responded",
            "tool.execution.approved",
            "tool.execution.completed",
            "artifact.version.created",
            "artifact.pointer.promoted",
            "execution.session.state_changed",
            "task.run.state_changed",
        ),
        expected_workflow_states={"run-sd-2026-03-04": "ACTIVE"},
        expected_task_states={"tr-stage07-policy-001": "SUCCEEDED"},
        expected_pointer_targets={"schedule.replan_delta.workbook": "av-policy-001"},
        expected_approval_outcomes={"apr-policy-001": "approved"},
        expected_execution_states={"xs-stage07-policy-001": "SUCCEEDED"},
        expected_tool_states={
            "tx-stage07-policy-denied-001": "DENIED",
            "tx-stage07-policy-approved-001": "COMPLETED",
        },
        required_stage_ids=("Stage07",),
    ),
}


def scenario_ids() -> list[str]:
    return sorted(SCENARIO_CATALOG)
