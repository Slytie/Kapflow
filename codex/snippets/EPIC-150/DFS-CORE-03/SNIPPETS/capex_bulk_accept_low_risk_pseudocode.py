"""Illustrative pseudocode only. Not a repo patch."""

def bulk_accept_low_risk_proposals(command, user):
    require_project_role(user, command.project_id, role="PM")
    assert_not_ai_or_service_account(user)

    if command.selected_items is None:
        raise ValidationError("missing_selection")
    if not command.selected_items.all and not command.selected_items.included:
        raise ValidationError("empty_selection")

    with transaction.atomic():
        snapshot = lock_projection_snapshot(
            project_id=command.project_id,
            snapshot_id=command.projection_snapshot_id,
        )
        rows = snapshot.resolve_selected_items(command.selected_items)
        assert_selection_matches(command.selection_assertions, rows)

        proposal_ids = [row.proposal_id for row in rows]
        proposals = lock_proposals(proposal_ids)
        decisions = []

        for row in rows:
            proposal = proposals[row.proposal_id]
            if proposal.status != "ready_for_pm_review":
                raise StaleCommand("proposal_not_reviewable")
            if proposal.version != row.proposal_version:
                raise StaleCommand("proposal_version_changed")
            if proposal.target_version != row.target_version:
                raise StaleCommand("target_version_changed")
            if proposal.risk_class != "low" or proposal.warning_count > 0 or proposal.conflict_count > 0:
                raise IndividualReviewRequired(proposal.id)

            decisions.append(CorpusStructureReviewDecision(
                project_id=command.project_id,
                proposal_id=proposal.id,
                proposal_snapshot_json=proposal.to_review_snapshot(),
                reviewer_user_id=user.id,
                reviewer_role="PM",
                decision_kind="accept",
                projection_snapshot_id=snapshot.id,
                expected_target_version=row.target_version,
                bulk_action_id=command.command_id,
                idempotency_key=f"{command.idempotency_key}:{proposal.id}",
                risk_class_at_review=proposal.risk_class,
                warning_count_at_review=proposal.warning_count,
                conflict_count_at_review=proposal.conflict_count,
                reason=command.reason,
            ))

        insert_review_decisions_idempotently(decisions)
        outbox.emit("ReviewDecisionsCommitted", project_id=command.project_id)

    return {"accepted": len(decisions)}
