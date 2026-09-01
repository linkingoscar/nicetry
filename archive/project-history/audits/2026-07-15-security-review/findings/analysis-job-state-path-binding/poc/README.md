# Harmless regression tests for analysis-job path binding

This directory intentionally contains no exploit. The recommended proof is a
set of repository-level negative tests using only pytest's `tmp_path`. Nothing
should touch the default ResearchPath workspace, the network, or a file outside
the test's temporary root.

From the repository root, add the cases to the analysis repository test module
chosen by the maintainers, then run that file with the project's isolated test
environment. For example:

```powershell
Set-Location apps/api
python -m pytest tests/test_analysis_repository.py -q
```

The tests should create a `Settings` copy whose `state_root` is
`tmp_path / "workspace"`, initialize `DatasetRepository`, and create valid job
rows through normal repository APIs before modifying only the temporary SQLite
database. Use valid, non-sensitive JSON sentinels.

Required cases:

1. **Canonical success:** the row path is
   `projects/default/runs/<id>/state.json`, the document `id` matches, and the
   job loads.
2. **Sibling-run substitution:** job A's row points to job B's `state.json`.
   Retrieval of A must raise the path-binding error and must not return B.
3. **Parent traversal:** job A's row uses a `..` path to a valid JSON sentinel
   under `tmp_path` but outside `state_root`. Retrieval must reject it before
   reading it.
4. **Absolute path:** the row contains the sentinel's absolute path. Retrieval
   must reject it on both Windows and POSIX.
5. **Document identity mismatch:** the canonical A path contains a valid job
   document whose `id` is B. Retrieval must raise an identity error.
6. **Recovery parity:** mark A unfinished, apply the sibling or traversal path,
   and call unfinished-job loading. It must fail closed and must not write or
   alter either sentinel.
7. **Reparse-point escape:** where the test account can create one, point A's
   run directory or state file through a symlink/junction to the temporary
   sentinel. The canonical-path check must reject it. Skip with an explicit
   platform reason when the operation is unavailable.

For every rejection case, record the sentinel bytes before the call and assert
they are identical afterward. Also assert that no files were created outside
`tmp_path`. The fixed test run should report all applicable cases as passed;
this README does not claim observed output because these tests were not executed
during static review.
