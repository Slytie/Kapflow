/**
 * DFS-CORE-02 illustrative watcher queue.
 *
 * Pattern adapted from the repo findings:
 * - watcher events are hints
 * - lost/overflow/restart escalates to full reconciliation
 * - queue rows are durable and acknowledged only after reconciliation commits
 */

type WatchEventFamily = 'non_remove' | 'remove' | 'mixed' | 'root_unknown';
type ReliabilityReason = 'normal' | 'overflow' | 'lost_changes' | 'watcher_restart' | 'watcher_unreliable';

type WatcherEvent = {
  sourceRootId: string;
  projectId: string;
  redactedPath: string;
  pathHash: string;
  eventFamily: WatchEventFamily;
  reliabilityReason: ReliabilityReason;
  observedAt: Date;
};

export async function onWatcherEvent(event: WatcherEvent, deps: Deps): Promise<void> {
  // Watcher uncertainty is a correctness condition, not just telemetry.
  if (event.reliabilityReason !== 'normal') {
    await deps.db.transaction(async (tx: Tx) => {
      await deps.syncHealth.requireFullReconciliationTx(
        tx,
        event.sourceRootId,
        event.reliabilityReason,
      );

      await deps.touchedPathQueue.upsertTx(tx, {
        projectId: event.projectId,
        sourceRootId: event.sourceRootId,
        redactedPath: '[source-root]',
        pathHash: 'SOURCE_ROOT',
        eventFamily: 'root_unknown',
        reliabilityReason: event.reliabilityReason,
        firstSeenAt: event.observedAt,
        lastSeenAt: event.observedAt,
        coalescedScopeHash: 'SOURCE_ROOT',
      });
    });
    return;
  }

  await deps.touchedPathQueue.upsert({
    projectId: event.projectId,
    sourceRootId: event.sourceRootId,
    redactedPath: event.redactedPath,
    pathHash: event.pathHash,
    eventFamily: event.eventFamily,
    reliabilityReason: 'normal',
    firstSeenAt: event.observedAt,
    lastSeenAt: event.observedAt,
    coalescedScopeHash: coalesceScope(event.pathHash, event.eventFamily),
  });
}

/**
 * Conservative coalescing. It is safe to scan too much; unsafe to scan too little.
 * Remove/delete hints can be delayed or widened so add/modify/move candidates are
 * observed first.
 */
function coalesceScope(pathHash: string, eventFamily: WatchEventFamily): string {
  if (eventFamily === 'root_unknown') return 'SOURCE_ROOT';
  if (eventFamily === 'remove') return parentScopeHash(pathHash);
  if (eventFamily === 'mixed') return parentScopeHash(pathHash);
  return pathHash;
}

/**
 * Called by the scheduler. It chooses full reconciliation unless partial is safe.
 */
export async function planWatcherReconcile(sourceRootId: string, deps: Deps): Promise<ReconcilePlan> {
  const health = await deps.syncHealth.get(sourceRootId);

  if (!canPartialReconcile(health)) {
    return { kind: 'full', reason: 'partial_reconcile_not_safe', scopeHash: 'SOURCE_ROOT' };
  }

  const rows = await deps.touchedPathQueue.peekPending(sourceRootId);
  if (rows.some((r: QueueRow) => r.reliabilityReason !== 'normal')) {
    return { kind: 'full', reason: 'watcher_uncertainty', scopeHash: 'SOURCE_ROOT' };
  }

  return {
    kind: 'partial',
    reason: 'watcher_touched_paths',
    scopeHash: widenToSafeScope(rows.map((r: QueueRow) => r.coalescedScopeHash)),
  };
}

function canPartialReconcile(health: SyncHealth): boolean {
  return Boolean(
    health.watcherStatus === 'reliable' &&
    health.lastFullSnapshotId &&
    health.lastCompleteSnapshotAt &&
    !health.fullReconciliationRequired,
  );
}

function widenToSafeScope(scopeHashes: string[]): string {
  if (scopeHashes.includes('SOURCE_ROOT')) return 'SOURCE_ROOT';
  // In production this should reduce overlapping scopes and return a durable
  // scope-group ID. The important rule is: never narrow unsafely.
  return scopeHashes.sort().join('|');
}

function parentScopeHash(pathHash: string): string {
  // Placeholder. CAPEX should compute this from normalized/redacted path segments
  // or stored parent_path_hash relationships, not raw absolute paths.
  return `parent:${pathHash}`;
}

type SyncHealth = {
  watcherStatus: 'disabled' | 'reliable' | 'lost_changes' | 'overflow' | 'restarted' | 'unreliable';
  lastFullSnapshotId?: string;
  lastCompleteSnapshotAt?: Date;
  fullReconciliationRequired: boolean;
};

type QueueRow = {
  coalescedScopeHash: string;
  reliabilityReason: ReliabilityReason;
};

type ReconcilePlan =
  | { kind: 'full'; reason: string; scopeHash: 'SOURCE_ROOT' }
  | { kind: 'partial'; reason: string; scopeHash: string };

type Tx = unknown;
type Deps = any;
