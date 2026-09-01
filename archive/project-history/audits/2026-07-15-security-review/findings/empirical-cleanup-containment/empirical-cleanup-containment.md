**Finding:** SEC-B04-05
**Severity:** Medium (P2)
**Affected component:** empirical-analysis job retention cleanup
**Source basis:** unversioned repository snapshot reviewed on 2026-07-15

## Executive Summary

Empirical-report cleanup derives recursive-deletion authority from a persisted
job-state document. The guard accepts `report_root == state_root` because
`Path.is_relative_to()` includes equality, while `report_root.name == reportId`
only checks consistency between two values supplied by the same state file.
Consequently, a restored or corrupted empirical job can make normal retention
cleanup pass the workspace root, or another chosen in-workspace directory, to
`shutil.rmtree()` (`apps/api/app/services/analysis_repository.py:93-136`).

The validated impact is loss of local research data within one ResearchPath
workspace under the current OS user's filesystem authority. We did not find a
remote-code-execution primitive, a cross-user boundary, or deletion outside
`state_root` in this path. The product is local-first and the cleanup endpoint
must still be invoked, so we rate this P2/medium rather than high.

I statically reviewed the unversioned source snapshot and the supplied
path-equality evidence. I did not invoke cleanup, execute `rmtree`, or run a
destructive demonstration. The introduction date and affected released
versions cannot be established from this snapshot because it has no Git
revision history.

## Background

ResearchPath persists each analysis job in JSON and stores its `state_path` in
SQLite. Deletion starts by loading that file, removes the database rows, and
then cleans filesystem artifacts (`apps/api/app/services/analysis_repository.py:93-109`).
The HTTP retention route calls `cleanup_runs()`, which selects terminal jobs
and delegates each ID to this repository method
(`apps/api/app/api/routes/analyses.py:177-186`; `apps/api/app/services/analysis_jobs.py:412-442`).

For an ordinary empirical run, ResearchPath generates a report ID and writes
the report at this canonical shape:

```text
projects/default/datasets/<dataset-id>/measurement/v<version>/empirical/
  <report-id>/report.json
```

That ownership layout is constructed both when the job records `resultPath`
(`apps/api/app/services/analysis_jobs.py:322-343`) and when the empirical
engine writes the report (`apps/api/app/services/empirical_analysis.py:237-248`).
The security invariant is therefore stronger than generic descendant
containment: cleanup may delete only the exact canonical report directory
owned by the selected empirical job, never `state_root`, an ancestor, a
sibling report, or an arbitrary descendant.

## Vulnerability Details

We first reach `delete_analysis_job_and_run()`, where `state_path` comes from
the `analysis_jobs` row and the JSON document is loaded before its database
records are deleted. For model-run artifacts, the adjacent helper already
recognizes the important boundary:

```python
def remove_known_directory(path: Path, expected_parent: str) -> None:
    resolved = path.resolve()
    if (
        resolved != state_root
        and resolved.is_relative_to(state_root)
        and resolved.parent.name == expected_parent
    ):
        shutil.rmtree(resolved, ignore_errors=True)
```

This helper rejects root equality and requires the expected `runs` parent
(`apps/api/app/services/analysis_repository.py:109-125`). The empirical branch
does not preserve those properties:

```python
report_path = self.settings.state_root / state["resultPath"]
report_id = state.get("reportId")
report_root = report_path.parent.resolve()
if (
    report_id
    and report_root.name == report_id
    and report_root.is_relative_to(state_root)
):
    shutil.rmtree(report_root, ignore_errors=True)
```

(`apps/api/app/services/analysis_repository.py:127-136`)

If we carry `resultPath = "report.json"` into this branch, `report_path.parent`
resolves to `state_root`. Setting `reportId` to the workspace directory's
basename makes the name comparison true, and `state_root.is_relative_to(state_root)`
is also true. The recursive-deletion sink is therefore authorized for the
workspace root. The same self-consistency check permits an unrelated directory
under the root when its basename is copied into `reportId`; neither comparison
proves the canonical dataset, measurement, `empirical`, report-object, or
`report.json` ownership chain.

## Exploitability Analysis

The strongest realistic route is a malicious or corrupted restored workspace
whose terminal empirical job state contains the crafted fields, followed by a
local operator's ordinary retention cleanup. We control no command string or
code pointer; instead, we influence the directory passed to a recursive
filesystem operation. Root equality maximizes the effect by targeting the
whole workspace. Choosing another in-root directory can make the effect more
selective, but does not extend it beyond the current user's permissions.

Several constraints bound the finding. Cleanup is exposed through the local
workflow rather than a supported public multi-user service; a state document
must be introduced or corrupted; and a cleanup request must select that job.
`resolve()` plus `is_relative_to(state_root)` blocks a straightforward `..`
escape after canonicalization, so we do not claim arbitrary host-filesystem
deletion. Backups can help recovery but do not prevent integrity and
availability loss when the restored content itself supplies the bad state.

## Proof of Concept

The accompanying `poc/README.md` specifies a harmless `pytest` regression
design. It uses `tmp_path` for every fixture and monkeypatches
`shutil.rmtree` with a recorder, so no directory is recursively deleted. We
then carry three states through the real repository method: root equality,
an unrelated in-root subtree, and one valid canonical report directory. On
the vulnerable implementation, the recorder observes forbidden calls for the
first two cases; after remediation, it observes no forbidden call and exactly
one call for the canonical positive control.

I did not implement or execute this test because the assigned review boundary
forbids source edits and deletion execution. The README labels its command and
expected output as a post-fix design rather than observed results.

## Remediation

Restore this invariant before any recursive deletion: the resolved target must
be unequal to `state_root`, remain contained by it, equal the complete
canonical report directory derived from authoritative job ownership fields,
and correspond exactly to that directory's `report.json`. A report ID format
check should also reject separators and non-generated identifiers. Persisting
`report_id` as an immutable `analysis_jobs` column, alongside the existing
database-owned `dataset_id` and `model_version`, avoids deriving every side of
the authorization decision from mutable JSON.

A minimal defensive shape is:

```python
expected_root = (
    state_root / "projects" / "default" / "datasets" / row_job["dataset_id"]
    / "measurement" / f"v{row_job['model_version']}" / "empirical"
    / row_job["report_id"]
).resolve()
report_path = (state_root / state["resultPath"]).resolve()
report_root = report_path.parent

if (
    report_root != state_root
    and report_root.is_relative_to(state_root)
    and expected_root.is_relative_to(state_root)
    and report_root == expected_root
    and report_path == expected_root / "report.json"
):
    shutil.rmtree(report_root, ignore_errors=True)
```

The database query must select those ownership columns, and schema migration
must backfill them safely or decline deletion when ownership is unavailable.
Do not fall back to the current name-only check. Centralizing guarded recursive
deletion would also keep the empirical and normal-run branches on the same
deny-by-default policy.

Regression tests should cover root equality, a nested unrelated directory
whose basename equals `reportId`, a sibling report, `..` normalization, a
resolved link that leaves the canonical object, malformed report IDs, missing
ownership metadata, and the valid canonical path. Every negative case should
assert that the deletion primitive was not called; the positive case should
assert one call for the exact expected directory.

## Summary

SEC-B04-05 is a cleanup authorization failure: descendant containment is
treated as sufficient even though it admits equality, and matching two
state-controlled names is mistaken for ownership. We proved statically that
the bad predicate reaches `shutil.rmtree()` and that the same file already
contains a safer root-inequality pattern. The fix should make recursive
deletion conditional on exact, authoritative object ownership plus canonical
containment. Future variant review should focus narrowly on other maintenance
paths that consume persisted relative paths before recursive deletion.
