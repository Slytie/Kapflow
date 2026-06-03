/**
 * DFS-CORE-02 illustrative move/duplicate/conflict tests.
 */

describe('DFS-CORE-02 move, duplicate, and conflict semantics', () => {
  it('same digest at a new path while old path remains creates duplicate_seen', async () => {
    const sourceRoot = await fixtures.sourceRoot();
    const occurrence = await fixtures.reviewedSourceOccurrence(undefined, sourceRoot, {
      pathHash: 'hash:/A/form.pdf',
      contentDigest: 'sha256:D',
    });

    await fixtures.snapshot(sourceRoot, {
      status: 'complete',
      entries: [{ pathHash: 'hash:/A/form.pdf', contentDigest: 'sha256:D', sourceOccurrenceId: occurrence.id }],
    });

    await reconcileWithSyntheticSnapshot(sourceRoot, {
      status: 'complete',
      entries: [
        { pathHash: 'hash:/A/form.pdf', contentDigest: 'sha256:D', sourceOccurrenceId: occurrence.id },
        { pathHash: 'hash:/B/form-copy.pdf', contentDigest: 'sha256:D' },
      ],
    });

    const group = await db.sourceOccurrenceDeltaGroup.findOne({ groupType: 'duplicate_seen' });
    expect(group).toBeTruthy();
    expect(group.reviewState).toBe('requires_review');

    // Same digest is not an identity merge.
    const newEntry = await db.folderTreeSnapshotEntry.findByPathHash('hash:/B/form-copy.pdf');
    expect(newEntry.sourceOccurrenceId).not.toBe(occurrence.id);
  });

  it('one disappeared same-digest prior and one new same-digest path creates move candidate', async () => {
    const sourceRoot = await fixtures.sourceRoot();
    const occurrence = await fixtures.reviewedSourceOccurrence(undefined, sourceRoot, {
      pathHash: 'hash:/A/file.pdf',
      parentPathHash: 'hash:/A',
      contentDigest: 'sha256:D',
    });

    await fixtures.snapshot(sourceRoot, {
      status: 'complete',
      entries: [{
        pathHash: 'hash:/A/file.pdf',
        parentPathHash: 'hash:/A',
        contentDigest: 'sha256:D',
        sourceOccurrenceId: occurrence.id,
      }],
    });

    await reconcileWithSyntheticSnapshot(sourceRoot, {
      status: 'complete',
      scopeStatuses: [{ scopePathHash: 'hash:/A', status: 'complete' }, { scopePathHash: 'hash:/B', status: 'complete' }],
      entries: [{ pathHash: 'hash:/B/file.pdf', parentPathHash: 'hash:/B', contentDigest: 'sha256:D' }],
    });

    const group = await db.sourceOccurrenceDeltaGroup.findOne({ groupType: 'renamed_candidate' });
    expect(group).toBeTruthy();
    expect(group.reviewState).toBe('requires_review');
    expect(await db.reviewedCorpusBaseline.wasMutatedBy(group.id)).toBe(false);
  });

  it('multiple same-digest priors creates ambiguity', async () => {
    const sourceRoot = await fixtures.sourceRoot();
    await fixtures.snapshot(sourceRoot, {
      status: 'complete',
      entries: [
        { pathHash: 'hash:/A/file.pdf', contentDigest: 'sha256:D' },
        { pathHash: 'hash:/B/file.pdf', contentDigest: 'sha256:D' },
      ],
    });

    await reconcileWithSyntheticSnapshot(sourceRoot, {
      status: 'complete',
      entries: [{ pathHash: 'hash:/C/file.pdf', contentDigest: 'sha256:D' }],
    });

    expect(await db.sourceOccurrenceDeltaGroup.findOne({
      groupType: 'ambiguous_duplicate_or_move',
    })).toBeTruthy();
  });

  it('same size and mtime but different digest is modified or conflict, not equivalent', async () => {
    const sourceRoot = await fixtures.sourceRoot();
    await fixtures.snapshot(sourceRoot, {
      status: 'complete',
      entries: [{ pathHash: 'hash:/A.pdf', sizeBytes: 100, modifiedAt: '2026-01-01T00:00:00Z', contentDigest: 'sha256:D1' }],
    });

    await reconcileWithSyntheticSnapshot(sourceRoot, {
      status: 'complete',
      entries: [{ pathHash: 'hash:/A.pdf', sizeBytes: 100, modifiedAt: '2026-01-01T00:00:00Z', contentDigest: 'sha256:D2' }],
    });

    expect(await db.sourceOccurrenceDeltaGroup.findOne({ groupType: 'modified' })).toBeTruthy();
  });
});
