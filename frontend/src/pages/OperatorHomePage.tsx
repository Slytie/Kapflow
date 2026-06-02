import { useQuery } from "@tanstack/react-query";
import { NavLink } from "react-router-dom";

import { StatePanel } from "@/components/StatePanel";
import { apiConfig } from "@/lib/api/config";
import { errorText } from "@/lib/api/errorText";
import { operatorHomeRepository } from "@/lib/repositories";
import type { OperatorHomeFinding } from "@/lib/types/contracts";

const FINDING_LABELS: Record<string, string> = {
  weekly_daily_seed_missing: "Missing seed",
  weekly_seed_edge_missing: "Missing seed edge",
  artifact_blob_missing: "Missing blob",
  stale_edge_execution: "Stale edge",
  late_reporting_input_conflict: "Late report",
  notify_only_target_input_binding_missing: "Missing input binding",
  notify_only_target_input_binding_drift: "Input drift",
  live_target_input_binding_missing: "Missing live input",
  live_target_input_binding_drift: "Live input drift",
  edge_target_run_drift: "Run drift"
};

function findingLabel(code: string): string {
  return FINDING_LABELS[code] ?? code.replace(/_/g, " ");
}

function subjectLabel(finding: OperatorHomeFinding): string {
  const subject = finding.subject;
  const artifact = typeof subject.artifact_version_id === "string" ? subject.artifact_version_id : "";
  const edge = typeof subject.edge_execution_id === "string" ? subject.edge_execution_id : "";
  const run = typeof subject.workflow_run_id === "string" ? subject.workflow_run_id : "";
  const partition = typeof subject.partition_key === "string" ? subject.partition_key : "";
  return [artifact || edge || run, partition].filter(Boolean).join(" · ") || "Runtime row";
}

export function OperatorHomePage(): JSX.Element {
  const query = useQuery({
    queryKey: ["operator-home"],
    queryFn: () => operatorHomeRepository.get(),
    refetchInterval: apiConfig.pollIntervalMs
  });

  if (query.isLoading) {
    return (
      <StatePanel
        kind="loading"
        title="Loading operator home"
        detail="Resolving current runtime posture and failure-state report."
      />
    );
  }

  if (query.isError) {
    return (
      <StatePanel
        kind="error"
        title="Operator home failed to load"
        detail={errorText(query.error, "Unable to resolve operator home")}
        onRetry={() => void query.refetch()}
      />
    );
  }

  if (!query.data) {
    return (
      <StatePanel
        kind="error"
        title="Operator home missing"
        detail="Operator home response did not resolve."
        onRetry={() => void query.refetch()}
      />
    );
  }

  const home = query.data;
  const summary = home.failure_state.summary;
  const findings = home.failure_state.findings;
  const topFindings = findings.slice(0, 8);
  const codeCounts = Object.entries(summary.code_counts).sort((left, right) =>
    left[0].localeCompare(right[0])
  );

  return (
    <main className="operator-home-page" data-testid="operator-home-page">
      <header className="operator-home-page__header">
        <div>
          <p className="timeline-page__eyebrow">Operator home</p>
          <h1>Current runtime posture</h1>
          <p>
            Server-derived session for {home.viewer.tenant_id} / {home.viewer.domain_id}
          </p>
        </div>
        <strong
          className={`operator-home-page__status operator-home-page__status--${home.status}`}
        >
          {home.status === "attention" ? "Attention" : "Clear"}
        </strong>
      </header>

      <section className="operator-home-page__grid" aria-label="Failure-state summary">
        <article>
          <span>Findings</span>
          <strong>{summary.finding_count}</strong>
        </article>
        <article>
          <span>Errors</span>
          <strong>{summary.error_count}</strong>
        </article>
        <article>
          <span>Warnings</span>
          <strong>{summary.warning_count}</strong>
        </article>
        <article>
          <span>Dry-run mutations</span>
          <strong>{summary.mutations_performed}</strong>
        </article>
      </section>

      <section className="operator-home-page__actions" aria-label="Operator routes">
        <NavLink to="/my-work">My Work</NavLink>
        <NavLink to="/approvals">Approvals</NavLink>
        <NavLink to="/exceptions">Exceptions</NavLink>
        <NavLink to="/demo/logistics">Logistics Demo</NavLink>
      </section>

      {findings.length === 0 ? (
        <StatePanel
          kind="empty"
          title="No failure-state findings"
          detail="The dry-run reconciler found no missing seeds, stale edges, late reports, drift, or missing blobs in this scope."
        />
      ) : (
        <section className="operator-home-page__findings" aria-label="Failure-state findings">
          <div className="operator-home-page__finding-groups">
            {codeCounts.map(([code, count]) => (
              <span key={code}>
                {findingLabel(code)}: {count}
              </span>
            ))}
          </div>
          <div className="operator-home-page__finding-list">
            {topFindings.map((finding) => (
              <article key={finding.finding_id}>
                <div>
                  <span>{findingLabel(finding.code)}</span>
                  <strong>{finding.message}</strong>
                  <p>{subjectLabel(finding)}</p>
                </div>
                <small>{finding.severity}</small>
              </article>
            ))}
          </div>
        </section>
      )}
    </main>
  );
}
