# Harmless regression unit tests

Implement these as repository unit tests after the path-binding fix. Every test
must use pytest's `tmp_path`, a temporary `state_root`, a temporary SQLite
database, and synthetic result JSON containing no user data. The tests must call
the repository method directly; they must not create a backup, contact an HTTP
service, inspect host files, or demonstrate disclosure.

1. `test_result_path_accepts_only_canonical_owned_file`
   - Create `projects/default/runs/run_a/result.json` under `tmp_path`.
   - Insert an `analysis_runs` row for `run_a` with exactly that relative path.
   - Assert `get_analysis_result("run_a")` returns the synthetic object.

2. `test_result_path_rejects_sibling_run`
   - Create canonical synthetic files for `run_a` and `run_b` under `tmp_path`.
   - Store `run_b`'s relative result path in the row for `run_a`.
   - Assert the repository raises the chosen invalid-persisted-path exception
     before the JSON reader is called.

3. `test_result_path_rejects_parent_traversal`
   - Create a synthetic JSON file in another temporary directory owned by the
     same test.
   - Store a relative path containing `..` in the `run_a` row.
   - Assert fail-closed rejection and leave the synthetic file unchanged.

4. `test_result_path_rejects_absolute_temporary_path`
   - Create a synthetic result-shaped JSON file elsewhere under `tmp_path`.
   - Store its absolute path in the `run_a` row.
   - Assert fail-closed rejection before any read.

5. `test_result_path_rejects_link_or_reparse_escape`
   - When the test platform and account permit links, create a run-directory
     link pointing to another synthetic directory under `tmp_path`.
   - Store the apparent in-workspace path in the row.
   - Assert resolved containment rejects it. Skip with an explicit reason when
     link creation is unavailable.

For each negative test, monkeypatch `app.services.analysis_repository._read_json_safe`
with a spy that fails immediately if invoked. This verifies the security control
precedes the sink. Run only after implementation with:

```text
python -m pytest -q apps/api/tests/<implemented-test-module>.py
```

Expected result: all five tests pass; all temporary artifacts are removed by
pytest. No special cleanup, network access, elevated privileges, or real
workspace is required.
