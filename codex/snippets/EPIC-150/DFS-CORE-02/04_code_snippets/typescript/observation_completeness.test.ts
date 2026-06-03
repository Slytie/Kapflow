/**
 * DFS-CORE-02 illustrative observation-completeness tests.
 */

describe('DFS-CORE-02 observation completeness', () => {
  it('does not infer deletion under an inaccessible parent scope', async () => {
    const sourceRoot = await fixtures.sourceRoot();
    const occurrence = await fixtures.reviewedSourceOccurrence(undefined, sourceRoot, {
      pathHash: 'hash:/restricted/file.pdf',
      parentPathHash: 'hash:/restricted',
      contentDigest: 'sha256:D1',
    });

    await fixtures.snapshot(sourceRoot, {
      status: 'complete',
      entries: [{
        pathHash: 'hash:/restricted/file.pdf',
        parentPathHash: 'hash:/restricted',
        contentDigest: 'sha256:D1',
        sourceOccurrenceId: occurrence.id,
      }],
    });

    await reconcileWithSyntheticSnapshot(sourceRoot, {
      status: 'partial',
      scopeStatuses: [
        { scopePathHash: 'hash:/', status: 'partial' },
        { scopePathHash: 'hash:/restricted', status: 'unreachable', errorCode: 'permission_denied' },
      ],
      entries: [],
    });

    expect(await db.sourceOccurrenceDelta.findOne({
      priorSourceOccurrenceId: occurrence.id,
      deltaType: 'deleted_from_source',
    })).toBeNull();

    const incomplete = await db.sourceOccurrenceDelta.findOne({
      priorSourceOccurrenceId: occurrence.id,
      deltaType: 'observation_incomplete',
    });
    expect(incomplete).toBeTruthy();

    const healthTask = await db.reviewTask.findOne({
      sourceRootId: sourceRoot.id,
      taskType: 'source_root_observation_incomplete',
    });
    expect(healthTask).toBeTruthy();
  });

  it('allows deleted_from_source only when parent scope is complete', async () => {
    const sourceRoot = await fixtures.sourceRoot();
    const occurrence = await fixtures.reviewedSourceOccurrence(undefined, sourceRoot, {
      pathHash: 'hash:/A/file.pdf',
      parentPathHash: 'hash:/A',
      contentDigest: 'sha256:D1',
    });

    await fixtures.snapshot(sourceRoot, {
      status: 'complete',
      entries: [{
        pathHash: 'hash:/A/file.pdf',
        parentPathHash: 'hash:/A',
        contentDigest: 'sha256:D1',
        sourceOccurrenceId: occurrence.id,
      }],
    });

    await reconcileWithSyntheticSnapshot(sourceRoot, {
      status: 'complete',
      scopeStatuses: [{ scopePathHash: 'hash:/A', status: 'complete' }],
      entries: [],
    });

    expect(await db.sourceOccurrenceDelta.findOne({
      priorSourceOccurrenceId: occurrence.id,
      deltaType: 'deleted_from_source',
    })).toBeTruthy();
  });
});
