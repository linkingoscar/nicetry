# Security Hardening Review: ResearchPath

## Evidence Basis

This portfolio is derived from the repository-wide 2026-07-15 scan and its 11 reportable source findings. It covers archive restore, backup verification, persisted SQLite paths, export, recovery, and cleanup. The snapshot is unversioned, so implementation must refresh the source and record drift.

## Constraints

We assume a local single-user loopback product, but treat imported archives and restored SQLite values as untrusted persistence. Existing relative-path formats and normal analysis latency should be preserved. No memory or latency budget was supplied; benchmarks are acceptance evidence, not claimed results.

## Opportunity Portfolio

| Opportunity | Evidence | Options | Recommendation | Proposal |
| --- | --- | --- | --- | --- |
| Owned filesystem capability and resource boundary | SEC-B02-01/02/04, SEC-B03-01/02/04/05, SEC-B04-02/03/04/05: archive, backup, persisted-path, export, recovery and cleanup findings | 1. Shared safe-path/budget APIs; 2. Isolated restore/export worker | Option 1 first; Option 2 only if measured fault isolation or deployment needs justify it | [Owned path and resource boundary](proposals/owned-path-resource-boundary.md) |

## Recommendation Summary

I recommend Option 1 under the current local-first constraints. We can make safe paths, object identity, archive budgets, and destructive-directory ownership explicit without changing the statistical fast path. Option 2 becomes preferable for unattended or multi-user archive processing, or if fault-injection shows the API process cannot meet availability goals with bounded in-process work.

## Next Decisions

1. Confirm the refreshed state-root and per-run layout.
2. Measure legitimate archive expansion and choose budgets.
3. Implement the shared boundary, migrate persisted reads, then rerun all 11 original paths.
4. Reassess process isolation from measured evidence.
