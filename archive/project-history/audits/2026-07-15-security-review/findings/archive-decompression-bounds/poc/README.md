# Tiny bounded regression-test plan

This directory intentionally contains no archive bomb, payload generator, or
runnable abuse code. Validate the fix with small pytest cases added to
`apps/api/tests/test_workspace_archive.py`; every generated ZIP should remain
below 16 KiB and live only under pytest's `tmp_path`.

Use `monkeypatch` to lower the production policy constants for each test. This
lets a few bytes cross a boundary that would normally be measured in GiB:

- Set the entry limit to 3 and construct a ZIP containing the manifest plus
  three one-byte files. Assert rejection before `ZipFile.open()` is called.
- Set the per-member limit to 1 KiB and include one 1,025-byte member. Assert
  preflight rejection; add a 1,024-byte boundary case that succeeds.
- Set the total expanded limit to 2 KiB and include three 700-byte members.
  Assert aggregate rejection even though each member is individually valid.
- Set the ratio limit low and use at most 2 KiB of repetitive data. Assert ratio
  rejection and separately cover zero-byte/zero-compressed-size behavior.
- Replace the member stream with a tiny deterministic stub that yields one byte
  more than its declared length. Assert the runtime counter rejects both verify
  and restore paths and that restore publishes no target directory.
- Retain a tiny normal archive to prove verification, restoration, CRC, size,
  and SHA-256 behavior still succeeds within all four limits.

Run the focused suite from the repository root:

```text
python -m pytest apps/api/tests/test_workspace_archive.py -q
```

Expected result after implementation: all existing tests and the new bounded
cases pass. No special cleanup is needed beyond `tmp_path` teardown.
