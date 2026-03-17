from __future__ import annotations

from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
BACKUP_RUNBOOK_PATH = REPO_ROOT / "docs/ops/runbooks/backup_and_restore.md"
ROLLBACK_RUNBOOK_PATH = REPO_ROOT / "docs/ops/runbooks/rollback_and_deploy.md"
OPS_README_PATH = REPO_ROOT / "docs/ops/README.md"
RUNBOOKS_README_PATH = REPO_ROOT / "docs/ops/runbooks/README.md"
SRE_SIGNOFF_PATH = REPO_ROOT / "docs/planning/checklists/SRE_SIGNOFF.md"
PLAN_PATH = REPO_ROOT / "docs/planning/PRODUCTION_AND_WORKFLOW_LAB_PLAN.md"


def test_backup_restore_runbook_freezes_recoverable_unit_contract() -> None:
    backup_runbook = BACKUP_RUNBOOK_PATH.read_text(encoding="utf-8")

    assert "ONETRUTH_DB_URL" in backup_runbook
    assert "ONETRUTH_ARTIFACT_ROOT" in backup_runbook
    assert "`release_source_bundle`" in backup_runbook
    assert "`bundle_manifest.json`" in backup_runbook
    assert "`release_provenance.json`" in backup_runbook
    assert "Prod and lab backup sets are not interchangeable." in backup_runbook
    assert "This runbook provides the rehearsal basis, not the rehearsal evidence itself." in backup_runbook


def test_recovery_docs_distinguish_rollback_from_restore_and_surface_rehearsal() -> None:
    backup_runbook = BACKUP_RUNBOOK_PATH.read_text(encoding="utf-8")
    rollback_runbook = ROLLBACK_RUNBOOK_PATH.read_text(encoding="utf-8")
    ops_readme = OPS_README_PATH.read_text(encoding="utf-8")
    runbooks_readme = RUNBOOKS_README_PATH.read_text(encoding="utf-8")
    sre_signoff = SRE_SIGNOFF_PATH.read_text(encoding="utf-8")
    plan = PLAN_PATH.read_text(encoding="utf-8")

    assert "Use rollback when" in rollback_runbook
    assert (
        "Use restore when the DB file, artifact root, or both are missing, corrupt, or no longer trustworthy."
        in rollback_runbook
    )
    assert "backup_and_restore.md" in rollback_runbook

    assert "docs/ops/runbooks/backup_and_restore.md" in ops_readme
    assert "`backup_and_restore.md`" in runbooks_readme

    assert "- [ ] backup / restore runbook exists" in sre_signoff
    assert "- [ ] backup / restore rehearsal evidence exists" in sre_signoff

    assert "backup/restore/rollback have been rehearsed" in plan
    assert "runbooks and rehearsal basis alone do not satisfy this gate" in plan
    assert "actual restore rehearsal evidence must exist" in plan

    assert "Record rehearsal evidence." in backup_runbook
