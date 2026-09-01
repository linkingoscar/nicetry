# Defensive recovery-path regression plan

This directory intentionally contains no exploit or malicious workspace artifact.
The proposed tests are harmless, use pytest's `tmp_path` fixture exclusively, and
verify that recovery rejects an unbound persisted path before any JSON read.

## Intended command

After adding the remediation and repository regression module:

```sh
python -m pytest -q ../../../apps/api/tests/test_analysis_recovery_security.py
```

Run from this `poc` directory. The source-review report does not add that test module
or change application source.

## Temporary test arrangement

Each test should create `tmp_path / "workspace"` as `state_root`, initialize a fresh
`DatasetRepository`, insert the minimum valid dataset and unfinished analysis-job
row, and create any candidate JSON only below `tmp_path`. Monkeypatch
`app.services.analysis_repository._read_json_safe` with a spy so rejected references
can assert a call count of zero.

Cover these cases independently:

1. Store an absolute path under `tmp_path` that is outside `state_root`; assert the
   row is rejected and the read spy is not called.
2. Store `../outside/state.json`; assert pre-read rejection.
3. For row `run_a`, store the canonical state path for `run_b`; assert pre-read
   rejection even though the resolved file remains inside the workspace.
4. Where the platform permits a temporary symlink, point a canonical-looking link
   outside `state_root`; assert resolved containment rejects it before reading.
5. Use the canonical `run_a` path but put `"id": "run_b"` in the JSON; assert no
   file or row for `run_b` is created or modified.
6. Put one malformed/missing row before a canonical valid row; assert recovery
   isolates the first failure and marks the valid row failed by its SQLite ID.

All paths and files must remain descendants of pytest's `tmp_path`. Tests should not
read user files, follow real external paths, start the HTTP server, invoke R, or
delete anything outside the fixture directory.

## Expected fixed result

```text
......                                                                   [100%]
6 passed
```

The key negative assertion is not merely that an unsafe document fails to parse.
It is that path shape, resolved containment, and row/run binding are established
before `_read_json_safe` receives a path.
