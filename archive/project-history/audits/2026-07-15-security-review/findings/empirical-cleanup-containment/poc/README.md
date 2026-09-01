**Harmless `tmp_path` regression-test design for SEC-B04-05**

Purpose: verify the empirical cleanup authorization predicate without deleting
anything. This is a test design, not an executed proof of data loss.

Safety rules:

- Build all repository state beneath pytest's `tmp_path` fixture.
- Monkeypatch `apps.api.app.services.analysis_repository.shutil.rmtree` (using
  the import path appropriate to the test environment) with a recorder before
  invoking `delete_analysis_job_and_run()`.
- The recorder only appends `(resolved_path, ignore_errors)` to a list. It must
  never call the original function.
- Create sentinel files under the temporary state root and assert they remain
  present after every case.

Proposed cases:

1. **Reject root equality.** Set the temporary `state_root` to `tmp_path /
   "workspace"`. Seed a terminal empirical job whose state has `resultPath` set
   to `"report.json"` and `reportId` set to `state_root.name`. Invoke cleanup
   and assert the recorder has no calls.
2. **Reject unrelated containment.** Create
   `state_root / "unrelated" / "chosen" / "report.json"`; set `resultPath` to
   that relative path and `reportId` to `"chosen"`. Assert no call, proving that
   basename agreement plus generic containment does not establish ownership.
3. **Reject a sibling report.** Give the selected job authoritative ownership
   of report A while its JSON points at canonical-looking report B. Assert no
   call.
4. **Accept only the owned canonical report.** Seed authoritative job fields
   for a dataset, measurement version, and report ID; point `resultPath` to the
   exact canonical `<owned-report>/report.json`. Assert the recorder contains
   exactly that resolved report directory, that it is not `state_root`, and
   that no other path was recorded.
5. **Preserve all fixtures.** In each case, assert the workspace sentinel and
   every report sentinel still exist. This confirms the test double made the
   design non-destructive.

Suggested test location:
`apps/api/tests/test_analysis_repository_cleanup.py`.

Once the production fix and tests are implemented, run from the repository
root:

```text
pytest apps/api/tests/test_analysis_repository_cleanup.py -q
```

Illustrative post-fix result (not observed during this static review):

```text
.....                                                                    [100%]
5 passed
```
