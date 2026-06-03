/**
 * DFS-CORE-02 illustrative CAPEX reconciliation orchestrator.
 *
 * Not production code. Adapt to CAPEX services, DB library, tenancy model,
 * auth/custody checks, migration names, and test harness.
 */

type ReconcileTrigger =
  | 'initial_import'
  | 'manual_reconcile'
  | 'scheduled_reconcile'
  | 'watch_reconcile'
  | 'watcher_uncertain_reconcile'
  | 'repair_reconcile';

type WatcherStatus =
  | 'disabled'
  | 'reliable'
  | 'lost_changes'
  | 'overflow'
  | 'restarted'
  | 'unreliable';

type SnapshotStatus = 'complete' | 'partial' | 'failed';

type ReconcileRequest = {
  projectId: string;
  sourceRootId: string;
  trigger: ReconcileTrigger;
  requestedScopeHash?: string;
  requestedPathHashes?: string[];
  actorUserId: string;
};

type SyncHealth = {
  sourceRootId: string;
  watcherStatus: WatcherStatus;
  lastFullSnapshotId?: string;
  lastCompleteSnapshotAt?: Date;
  fullReconciliationRequired: boolean;
};

type ScanResult = {
  status: SnapshotStatus;
  entries: SnapshotEntry[];
  scopeStatuses: ScopeStatus[];
  scanErrors: ScanError[];
  digestSummary?: string;
};

type SnapshotEntry = {
  redactedPath: string;
  pathHash: string;
  parentPathHash?: string;
  entryType: 'file' | 'directory' | 'symlink' | 'unsupported';
  contentDigest?: string;
  contentDigestAlgorithm?: string;
  sizeBytes?: number;
  modifiedAt?: Date;
  stableFileId?: string;
  inode?: string;
  observationStatus: 'observed' | 'scan_error' | 'ignored' | 'unsupported' | 'transient';
};

type ScopeStatus = {
  scopePathHash: string;
  parentScopePathHash?: string;
  status: 'complete' | 'partial' | 'failed' | 'unreachable' | 'ignored' | 'unsupported';
  errorCode?: string;
  errorMessageRedacted?: string;
};

type ScanError = {
  scopePathHash: string;
  errorCode: string;
  errorMessageRedacted: string;
};

type CandidateDeltaGroup = {
  groupType:
    | 'added'
    | 'modified'
    | 'moved_candidate'
    | 'renamed_candidate'
    | 'deleted_from_source'
    | 'duplicate_seen'
    | 'ambiguous_duplicate_or_move'
    | 'conflict_candidate'
    | 'observation_incomplete'
    | 'ignored_transient'
    | 'resurfaced';
  reviewRequiredReason: string;
  classificationConfidence?: number;
  signals: Record<string, unknown>;
  deltas: CandidateDelta[];
};

type CandidateDelta = {
  deltaType: CandidateDeltaGroup['groupType'] | 'ambiguous';
  priorSourceOccurrenceId?: string;
  priorSnapshotEntryId?: string;
  newSnapshotEntryId?: string;
  staleEffect?: 'none' | 'stale_source_warning' | 'downstream_blocked_until_review';
};

/**
 * One entry point for all reconciliation triggers.
 * Watchers may influence scope; they never bypass scanning/diffing/review.
 */
export async function reconcileSourceRoot(req: ReconcileRequest, deps: Deps): Promise<void> {
  await deps.authz.assertCanReconcileSourceRoot(req.actorUserId, req.projectId, req.sourceRootId);

  const health = await deps.syncHealth.get(req.sourceRootId);
  const mode = chooseReconciliationMode(req, health, deps.clock.now());

  const syncRun = await deps.syncRuns.create({
    projectId: req.projectId,
    sourceRootId: req.sourceRootId,
    triggerKind: mode.trigger,
    requestedScopeHash: req.requestedScopeHash,
    effectiveScopeHash: mode.scopeHash,
    state: 'preparing',
    startedAt: deps.clock.now(),
  });

  let lockedQueueRows: LockedQueueRow[] = [];

  try {
    if (mode.usesWatcherQueue) {
      lockedQueueRows = await deps.touchedPathQueue.lockPendingRows({
        sourceRootId: req.sourceRootId,
        scopeHash: mode.scopeHash,
        syncRunId: syncRun.syncRunId,
      });
    }

    await deps.syncRuns.markState(syncRun.syncRunId, 'scanning');

    // Scanning may be expensive and should not hold the final DB transaction open.
    // It must still obey auth/custody and redaction policy.
    const scan = await deps.snapshotScanner.scan({
      projectId: req.projectId,
      sourceRootId: req.sourceRootId,
      scope: mode.scanScope,
      digestPolicy: 'hash_governed_files_locally',
      redactionPolicy: 'store_redacted_path_and_path_hash',
    });

    await deps.db.transaction(async (tx) => {
      await deps.syncRuns.markStateTx(tx, syncRun.syncRunId, 'staging_snapshot');

      const snapshot = await deps.snapshots.insertTx(tx, {
        projectId: req.projectId,
        sourceRootId: req.sourceRootId,
        syncRunId: syncRun.syncRunId,
        snapshotKind: mode.snapshotKind,
        basisSnapshotId: await deps.snapshots.latestSnapshotIdTx(tx, req.sourceRootId),
        rootScopeHash: mode.scopeHash,
        status: scan.status,
        entryCount: scan.entries.length,
        digestSummary: scan.digestSummary,
      });

      await deps.snapshots.insertEntriesTx(tx, snapshot.snapshotId, scan.entries);
      await deps.snapshots.insertScopeStatusesTx(tx, snapshot.snapshotId, scan.scopeStatuses);
      await deps.snapshots.insertScanErrorsTx(tx, syncRun.syncRunId, snapshot.snapshotId, scan.scanErrors);

      await deps.syncRuns.markStateTx(tx, syncRun.syncRunId, 'diffing');
      const previous = await deps.snapshots.loadBasisSnapshotTx(tx, snapshot.basisSnapshotId);
      const facts = diffSnapshots(previous, snapshot, scan.scopeStatuses);

      await deps.syncRuns.markStateTx(tx, syncRun.syncRunId, 'classifying');
      const groups = await classifySnapshotDeltas({
        previous,
        current: snapshot,
        facts,
        completeness: buildCompletenessIndex(snapshot, scan.scopeStatuses),
        sourceOccurrenceIndex: await deps.sourceOccurrences.indexForRootTx(tx, req.sourceRootId),
      });

      // Hard governance boundary: candidate deltas and review tasks only.
      // No reviewed baseline mutation, no evidence deletion, no official pointer change.
      await deps.deltaGroups.insertManyTx(tx, syncRun.syncRunId, groups);

      await deps.syncRuns.markStateTx(tx, syncRun.syncRunId, 'creating_review_tasks');
      await deps.reviewTasks.createForDeltaGroupsTx(tx, {
        projectId: req.projectId,
        sourceRootId: req.sourceRootId,
        syncRunId: syncRun.syncRunId,
        groups,
      });

      if (mode.usesWatcherQueue) {
        await deps.touchedPathQueue.acknowledgeRowsTx(tx, lockedQueueRows, syncRun.syncRunId);
      }

      await updateSyncHealthAfterScanTx(tx, deps, req.sourceRootId, scan, mode, snapshot.snapshotId);
      await deps.syncRuns.markCommittedTx(tx, syncRun.syncRunId, deps.clock.now());
    });
  } catch (err) {
    await deps.syncRuns.markFailed(syncRun.syncRunId, redactedErrorCode(err), redactedErrorMessage(err));

    // Do not acknowledge watcher queue rows here. Failed partial reconciliation must retry
    // or escalate to full reconciliation.
    if (lockedQueueRows.length > 0) {
      await deps.syncHealth.requireFullReconciliation(req.sourceRootId, 'partial_reconcile_failed');
    }

    throw err;
  }
}

function chooseReconciliationMode(req: ReconcileRequest, health: SyncHealth, now: Date) {
  const watcherUncertain = ['lost_changes', 'overflow', 'restarted', 'unreliable'].includes(health.watcherStatus);
  const hasCompleteBaseline = Boolean(health.lastFullSnapshotId && health.lastCompleteSnapshotAt);
  const fullIntervalExpired = health.lastCompleteSnapshotAt
    ? now.getTime() - health.lastCompleteSnapshotAt.getTime() > 24 * 60 * 60 * 1000
    : true;

  if (
    req.trigger !== 'watch_reconcile' ||
    watcherUncertain ||
    health.fullReconciliationRequired ||
    !hasCompleteBaseline ||
    fullIntervalExpired
  ) {
    return {
      trigger: watcherUncertain ? 'watcher_uncertain_reconcile' as const : req.trigger,
      snapshotKind: watcherUncertain ? 'watcher_uncertain_reconcile' as const : req.trigger,
      scanScope: { kind: 'root' as const },
      scopeHash: 'SOURCE_ROOT',
      usesWatcherQueue: false,
    };
  }

  return {
    trigger: req.trigger,
    snapshotKind: 'watch_reconcile' as const,
    scanScope: { kind: 'path_hashes' as const, pathHashes: req.requestedPathHashes ?? [] },
    scopeHash: req.requestedScopeHash ?? 'SOURCE_ROOT',
    usesWatcherQueue: true,
  };
}

async function updateSyncHealthAfterScanTx(
  tx: unknown,
  deps: Deps,
  sourceRootId: string,
  scan: ScanResult,
  mode: ReturnType<typeof chooseReconciliationMode>,
  snapshotId: string,
) {
  if (scan.status === 'complete' && mode.scanScope.kind === 'root') {
    await deps.syncHealth.markFullCompleteTx(tx, sourceRootId, snapshotId);
    return;
  }

  if (scan.status === 'partial' || scan.status === 'failed') {
    await deps.syncHealth.requireFullReconciliationTx(tx, sourceRootId, 'scan_incomplete_or_failed');
  }
}

// Placeholder interfaces to show boundaries.
type LockedQueueRow = { queueId: string };
type Deps = any;
declare function diffSnapshots(previous: any, current: any, scopes: ScopeStatus[]): any[];
declare function classifySnapshotDeltas(args: any): Promise<CandidateDeltaGroup[]>;
declare function buildCompletenessIndex(snapshot: any, scopes: ScopeStatus[]): any;
declare function redactedErrorCode(err: unknown): string;
declare function redactedErrorMessage(err: unknown): string;
