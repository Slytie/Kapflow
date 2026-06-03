-- Illustrative only. Adapt to CAPEX migration/style conventions.
CREATE TABLE corpus_structure_review_decision (
  decision_id TEXT PRIMARY KEY,
  project_id TEXT NOT NULL,
  proposal_id TEXT NOT NULL,
  proposal_snapshot_json TEXT NOT NULL,
  source_occurrence_id TEXT,
  occurrence_group_id TEXT,
  reviewer_user_id TEXT NOT NULL,
  reviewer_role TEXT NOT NULL,
  decision_kind TEXT NOT NULL CHECK (decision_kind IN ('accept','correct','reject','defer','task_required')),
  prior_value_json TEXT,
  new_value_json TEXT,
  projection_snapshot_id TEXT NOT NULL,
  expected_target_version TEXT NOT NULL,
  bulk_action_id TEXT,
  idempotency_key TEXT NOT NULL,
  risk_class_at_review TEXT NOT NULL,
  warning_count_at_review INTEGER NOT NULL DEFAULT 0,
  conflict_count_at_review INTEGER NOT NULL DEFAULT 0,
  reason TEXT,
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  UNIQUE(project_id, proposal_id, idempotency_key)
);

CREATE INDEX idx_corpus_review_decision_project_created
  ON corpus_structure_review_decision(project_id, created_at);

CREATE INDEX idx_corpus_review_decision_proposal
  ON corpus_structure_review_decision(proposal_id);
