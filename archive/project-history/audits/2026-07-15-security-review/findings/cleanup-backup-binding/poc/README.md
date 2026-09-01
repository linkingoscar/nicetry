# Safe regression design for backup-to-audit binding

This directory intentionally contains no executable proof of concept. The vulnerable
path calls `shutil.rmtree`, so the validation design below replaces that sink with a
recording stub and uses only test-framework temporary directories. A correct test
must never delete a fixture directory.

## Safety rules

- Use `pytest`'s `tmp_path` fixture for every workspace, audit, and archive path.
- Monkeypatch `app.services.workspace_maintenance.shutil.rmtree` before invoking
  `clean_audited_orphan_datasets()`.
- The replacement records the requested path and callback but performs no filesystem
  mutation.
- Assert that every sentinel file still exists and retains its original bytes after
  each test, whether the service accepts or rejects the request.
- Do not point the test at `.researchpath/workspace`, a developer checkout, or any
  user-controlled directory.

## Primary regression: same path, different bytes

1. Under `tmp_path`, create independent `victim` and `decoy` workspace roots. Give
   each a valid minimal SQLite database with the same schema state.
2. In both workspaces, create the orphan path
   `projects/default/datasets/dataset_orphan/raw.csv`.
3. Write distinguishable contents: `victim-current-bytes` in the victim and
   `decoy-stale-bytes` in the decoy. Record both byte strings for final assertions.
4. Generate the maintenance audit from the victim.
5. Generate a valid workspace backup from the decoy. Confirm normal archive
   verification accepts it; this establishes that the test is about provenance, not
   archive corruption.
6. Install the non-mutating `rmtree` recording stub.
7. Call `clean_audited_orphan_datasets(victim, victim_audit, decoy_backup)`.
8. On the fixed implementation, assert a `WorkspaceMaintenanceError` describing a
   database or file-content mismatch and assert that the stub recorded zero calls.
9. As a characterization assertion for the vulnerable snapshot only, the current
   code would reach the stub once because the relative member name is present. Do not
   make acceptance the permanent regression expectation.
10. Assert that both CSV files still exist with their original, different bytes.

## Database snapshot mismatch

Create victim and decoy databases with different logical contents while preserving
the same orphan file path and bytes. Audit the victim and back up the decoy. The fixed
service must reject the archive because its staged database logical hash differs from
the audit's `databaseSha256`. The sink stub must record zero calls, and all fixture
files must remain unchanged.

## File changed after audit

Audit a temporary victim workspace, create its exact backup, and then change only the
bytes of a scheduled orphan file without changing its path or the database. The fixed
service must detect that current content no longer matches the audited identity and
must reject before calling the stub. This test covers the current design's database-
only post-audit change check.

## Missing identity metadata

Supply an audit or backup manifest using the legacy schema without per-file content
identity or archived logical-database identity. Destructive cleanup must fail closed;
it must not silently downgrade to filename coverage. Assert zero sink calls and
unchanged sentinels.

## Exact-backup happy path

Audit a temporary workspace and create a backup from the exact same bytes. With the
recording stub installed, fixed cleanup may reach the stub once for the scheduled
directory. Assert that the recorded target resolves beneath the temporary victim
root, then assert that the stub preserved every file. This confirms that the new
binding does not reject a legitimate workflow while keeping the test harmless.

## Acceptance criteria

The regression suite passes only when mismatched database or file bytes are rejected
before the deletion sink, legacy documents fail closed, an exact backup is accepted,
and every test proves that all temporary fixture bytes survived unchanged.
