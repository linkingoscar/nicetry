# Harmless regression-test design

This directory intentionally contains no exploit or executable PoC. The proposed
tests validate the remediation entirely beneath pytest's `tmp_path` and stop
unsafe cases before filesystem operations.

## Test boundary

- Build `Settings` with `state_root=tmp_path / "workspace"` and create one
  canonical owned run, `run_<32 lowercase hex characters>`.
- Use sentinel CSV/result files containing non-sensitive test strings only.
- Monkeypatch repository calls, `TemporaryDirectory`, `shutil.copy2`,
  `shutil.make_archive`, and `os.replace` as needed to record paths.
- For rejection cases, assert those spies receive no calls and assert a canary
  beside the owned run is unchanged.
- Never use a real ResearchPath workspace, user file, network endpoint, or path
  outside `tmp_path`.

## Required cases

1. `test_export_rejects_state_id_mismatch_before_io`: pass a valid requested ID
   and a different valid state ID; expect `ValueError` before repository or I/O.
2. `test_export_rejects_path_shaped_requested_id_before_io`: parameterize parent,
   rooted, drive-qualified, forward-slash, and backslash forms; state and request
   may match, but identifier validation must reject them before I/O.
3. `test_export_uses_only_owned_data`: place distinct sentinel CSVs in the owned
   and a foreign run; inspect the ZIP or `copy2` source and require the owned
   sentinel. If only the foreign CSV exists, expect the normal missing-data
   error rather than fallback across runs.
4. `test_export_ignores_or_rejects_forged_result_path`: give state a `resultPath`
   naming a foreign sentinel while the canonical owned result exists. Require
   the owned result, or reject the state before any read.
5. `test_export_destinations_remain_in_owned_exports`: record the temporary
   parent, staging root, archive source, and `os.replace` target. Resolve each
   and assert it is relative to `<state_root>/projects/default/runs/<requested>/exports`.
6. Add a platform-conditional symlink/reparse test. If the test account cannot
   create one, skip explicitly; otherwise require rejection without following
   it.
7. Preserve the normal-path test for both `include_data=False` and `True`, and
   verify the manifest's `analysisRunId` equals the requested ID.
8. At route level, replace the service with a spy and prove the URL `run_id` is
   passed separately from the restored state.

## Intended command and expected result

After adding the tests to `apps/api/tests/test_export_bundle_security.py`, run
from the repository root:

```sh
python -m pytest apps/api/tests/test_export_bundle_security.py -q
```

Expected output depends on the final parameterization. A minimal implementation
of the five core cases should report:

```text
5 passed
```

That output is illustrative and was not observed during this static review.
