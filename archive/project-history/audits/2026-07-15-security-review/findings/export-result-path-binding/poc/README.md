# Harmless regression-test design for SEC-B03-04

This directory intentionally contains no exploit or runnable trigger. The proposed test is a defensive unit test using `pytest`, `tmp_path`, synthetic repository fixtures, and sentinel JSON only.

Test arrangement:

1. Create a temporary `state_root` with two generated run directories, `run_owned` and `run_other`.
2. Place the minimum schema-compatible synthetic result in each run. Give the objects unmistakable non-sensitive sentinel values.
3. Build a succeeded state for `run_owned` with no inline `result`.
4. Invoke `create_export_bundle` through existing repository fixtures; never use a real workspace or user file.

Negative cases, each expected to raise `ValueError` before `_read_json_safe` is called and to leave no ZIP:

- an absolute `resultPath` to a temporary sentinel outside `state_root`;
- a relative path containing `..` that resolves outside `run_owned`;
- a path to `run_other/result.json`, which remains inside the workspace but violates run ownership;
- where permissions permit, a symlink or Windows junction located under `run_owned` whose resolved target is the outside sentinel.

Positive control:

- `projects/default/runs/run_owned/result.json` resolves to the owned canonical file, exports successfully, and the archive's `result-bundle.json` contains only the owned sentinel.

Route-level follow-up:

- inject the restored state through the normal test repository, request `GET /api/v1/analyses/run_owned/export`, and assert HTTP 409 for every negative case;
- assert the response is not a ZIP and the outside sentinel never occurs in response bytes;
- retain the positive case at HTTP 200.

The test should patch or spy on `app.services.repository_io._read_json_safe` to prove unauthorized candidates are rejected before any read. All paths and artifacts remain beneath `tmp_path`, and fixture teardown supplies all cleanup.
