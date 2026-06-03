/**
 * DFS-CORE-02 illustrative negative tests.
 * Not production test code. Adapt to CAPEX test framework and factories.
 */

describe('DFS-CORE-02 local delete semantics', () => {
  it('creates deleted_from_source without erasing governed evidence', async () => {
    const project = await fixtures.project();
    const sourceRoot = await fixtures.sourceRoot(project);

    const occurrence = await fixtures.reviewedSourceOccurrence(project, sourceRoot, {
      pathHash: 'hash:/A/evidence.pdf',
      contentDigest: 'sha256:D1',
    });

    const artifactVersion = await fixtures.artifactVersion({ sourceOccurrenceId: occurrence.id });
    const evidenceBinding = await fixtures.evidenceBinding({ artifactVersionId: artifactVersion.id });
    const officialPointer = await fixtures.officialPointer({ artifactVersionId: artifactVersion.id });

    await fixtures.snapshot(sourceRoot, {
      status: 'complete',
      entries: [{ pathHash: 'hash:/A/evidence.pdf', contentDigest: 'sha256:D1', sourceOccurrenceId: occurrence.id }],
    });

    await reconcileWithSyntheticSnapshot(sourceRoot, {
      status: 'complete',
      scopeStatuses: [{ scopePathHash: 'hash:/A', status: 'complete' }],
      entries: [],
    });

    const delta = await db.sourceOccurrenceDelta.findOne({
      priorSourceOccurrenceId: occurrence.id,
      deltaType: 'deleted_from_source',
    });
    expect(delta).toBeTruthy();
    expect(delta.reviewState).toBe('requires_review');

    expect(await db.sourceOccurrence.exists(occurrence.id)).toBe(true);
    expect(await db.artifactVersion.exists(artifactVersion.id)).toBe(true);
    expect(await db.evidenceBinding.exists(evidenceBinding.id)).toBe(true);
    expect(await db.officialPointer.get(officialPointer.id)).toMatchObject({
      artifactVersionId: artifactVersion.id,
    });

    const baseline = await db.reviewedCorpusBaseline.current(project.id);
    expect(baseline).not.toContainDelta(delta.id);
  });

  it('does not allow a delete delta service to cascade into evidence deletion', async () => {
    const ctx = await fixtures.reviewedEvidenceContext();

    await expect(
      dangerousInternalDeleteSourceOccurrence(ctx.sourceOccurrence.id),
    ).rejects.toThrow(/governed evidence/i);

    expect(await db.artifactVersion.exists(ctx.artifactVersion.id)).toBe(true);
    expect(await db.evidenceBinding.exists(ctx.evidenceBinding.id)).toBe(true);
  });
});
