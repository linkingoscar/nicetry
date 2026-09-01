# Harmless regression tests for SEC-B03-02

This directory intentionally contains no exploit code. The recommended proof is a
pytest regression module added by the maintainer after the containment and identity
checks are implemented. Every case must use pytest's `tmp_path`; do not read a real
user file, bind a network port, or restore over an existing workspace.

## Test arrangement

Create a temporary workspace and two ordinary datasets, `dataset_a` and
`dataset_b`, each with dictionary version 1. Put an additional JSON sentinel at
`tmp_path / "outside" / "v1.json"`. The sentinel should contain only synthetic
variable IDs and allowed type strings. Update only the temporary SQLite database
inside the fixture.

Add the following tests to a focused module such as
`apps/api/tests/test_dataset_dictionary_binding.py`:

1. A normal dictionary round trip succeeds.
2. Absolute and `..`-relative stored paths are rejected before the sentinel is read.
3. A stored path naming `dataset_b` from `dataset_a` is rejected.
4. The canonical path with a foreign `datasetVersionId` is rejected.
5. The canonical path with a mismatched `version` is rejected.
6. Unknown variable IDs, invalid type values, and a `confirmed_count` mismatch are
   rejected.
7. A symlink or Windows junction escape is rejected when the platform can create
   the link; otherwise the test is explicitly skipped.
8. Restore validation rejects an otherwise self-consistent archive containing the
   invalid reference.

For every rejection, assert the dedicated integrity exception and assert that no
sentinel type appears in a dataset response. Fixtures should be deleted
automatically with `tmp_path`; no separate cleanup is required.

## Safe run order

From the repository root, run the focused test first, then the project's required
gates:

```powershell
pwsh -NoLogo -NoProfile -Command `
  "apps/api/.venv/Scripts/python.exe -m pytest apps/api/tests/test_dataset_dictionary_binding.py -q"
pwsh -NoLogo -NoProfile -File scripts/check-architecture.ps1
pwsh -NoLogo -NoProfile -File scripts/test.ps1
```

Expected post-fix focused output (illustrative, not an observed run):

```text
8 passed
```

The focused module does not exist in the reviewed snapshot, so these commands must
not be represented as executed until the maintainer adds the regression tests.
