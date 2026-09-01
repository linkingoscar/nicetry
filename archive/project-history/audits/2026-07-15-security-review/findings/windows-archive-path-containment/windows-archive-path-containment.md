# Windows archive paths can escape the restore staging directory

## Executive Summary

ResearchPath's workspace restore code accepts ZIP member names that are relative
under POSIX rules but anchored under Windows rules. A crafted, internally
consistent backup can therefore pass CRC, size, hash, and manifest checks and
then cause `restore_workspace_backup()` to create or overwrite a file outside
its temporary staging directory. The write runs with the current desktop
user's filesystem rights.

The affected snapshot is the unversioned source tree reviewed on 15 July 2026;
there is no repository commit history or known fixed revision from which to
make a narrower version claim. I reviewed the source and the recorded Windows
`pathlib` semantics statically. I did not execute a restore, create a malicious
archive, or perform an out-of-tree write. The practical severity is medium:
the operator must deliberately restore or drill an untrusted backup, but its
author can cross a local filesystem integrity boundary once that happens.

## Background

The operator reaches the affected service through the local
`scripts/workspace-archive.py restore <archive> <target>` or `drill <archive>`
workflow. `restore_workspace_backup()` first calls `verify_workspace_backup()`,
creates a new staging directory beside the requested target, extracts the
manifest-listed files, and finally renames the staging directory to the target.

Archive members are intended to be canonical POSIX-relative names, matching
the forward-slash names emitted by `create_workspace_backup()`. The validator
currently expresses only the POSIX half of that invariant:

```python
# apps/api/app/services/workspace_archive.py, _safe_member_path
def _safe_member_path(name: str) -> PurePosixPath:
    path = PurePosixPath(name)
    if path.is_absolute() or not path.parts or ".." in path.parts:
        raise WorkspaceArchiveError(f"备份包含不安全路径: {name}")
    return path
```

This correctly rejects `/absolute` and independent `..` components. A
`PurePosixPath`, however, treats backslash as an ordinary character and does
not recognize a Windows drive or UNC prefix. Verification subsequently checks
that member names exactly match the manifest, validates CRC, size, and SHA-256,
and rejects duplicate or unregistered members. Those are valuable integrity
and consistency checks, but they do not establish where Windows will write.

## Vulnerability Details

An archive author controls both each ZIP member name and the corresponding
manifest `path`. We can therefore keep the two views internally consistent
while choosing a name such as `\Windows\Temp\owned`, `D:\owned`, or
`\\server\share\owned`. `_safe_member_path()` sees each backslash form as one
non-absolute POSIX component, so verification accepts the path before checking
the attacker's matching bytes and digest.

During restore, the same validated value crosses from POSIX parsing into native
filesystem semantics:

```python
# apps/api/app/services/workspace_archive.py, restore_workspace_backup
relative = _safe_member_path(entry["path"])
destination = staging.joinpath(*relative.parts)
destination.parent.mkdir(parents=True, exist_ok=True)
with archive.open(entry["path"]) as source, destination.open("wb") as target:
    shutil.copyfileobj(source, target)
```

On Windows, `staging` is a `WindowsPath`. When `joinpath()` receives the
accepted component, Windows interprets its root, drive, or UNC prefix. The
recorded platform check produced these transformations:

```text
\Windows\Temp\owned  -> C:\Windows\Temp\owned  -> outside staging
D:\owned             -> D:\owned               -> outside staging
\\server\share\owned -> \\server\share\owned    -> outside staging
```

We then reach `mkdir()` and `destination.open("wb")` without resolving the
native destination and proving containment. Opening in `wb` mode creates a new
file or truncates an existing one. The later `os.replace(staging, target_root)`
cannot restore this boundary because the out-of-tree write has already
occurred. Exception cleanup removes only `staging`, so it does not undo an
external write.

## Exploitability Analysis

The strongest practical route is an overwrite at a Windows path writable by
the ResearchPath user. We control the destination name and complete file
contents, while normal manifest checks merely require us to describe those
contents accurately. This can affect local research data, application
configuration, or user startup locations, depending on permissions and the
chosen path. A rooted-backslash name is constrained to the current drive; a
drive-qualified name can select another mounted drive; and a UNC form depends
on the named share being reachable and writable.

Several constraints keep this from being a remote, unauthenticated primitive.
ResearchPath is a local-first, single-user application, and an operator must
supply the archive and invoke restore or drill. The process does not gain more
rights than the current OS user, so protected system paths should fail under a
normal non-elevated account. The target must also pass the archive's structural
checks, although an archive author can satisfy them because CRC, sizes, hashes,
member names, and manifest entries are all self-selected.

This is a deterministic path interpretation error rather than a race or memory
corruption bug. Reliability depends principally on target permissions and file
locks. Existing POSIX traversal coverage for `../escape` is a useful dead end:
it proves the current guard works for one syntax, but does not exercise the
Windows parser that later consumes the same string.

## Proof of Concept

No exploit or write-performing PoC is included, in keeping with the defensive
static-review scope. The companion `poc/README.md` instead specifies harmless
parameterized unit-test inputs for `_safe_member_path()` and the expected
`WorkspaceArchiveError`. These tests need not create a ZIP or open any path.

From the report directory, the intended regression-test workflow after the
cases are added to the project's existing test module is:

```text
cd <repository>
pytest apps/api/tests/test_workspace_archive.py
```

Representative expected output is a passing parameterized test for every
listed Windows-special input; the project's existing round-trip test should
also remain green. There is no cleanup step because the proposed rejection
tests perform validation only and write no external files.

## Remediation

The invariant should be explicit at both boundaries: an archive member must be
a canonical, forward-slash, relative POSIX path with no Windows drive or
backslash interpretation, and the resolved native destination must remain a
strict descendant of the resolved staging directory before any `mkdir()` or
`open()` call.

A minimal defensive shape is:

```python
from pathlib import Path, PurePosixPath, PureWindowsPath


def _safe_member_path(name: str) -> PurePosixPath:
    path = PurePosixPath(name)
    windows_path = PureWindowsPath(name)
    if (
        not name
        or "\x00" in name
        or "\\" in name
        or path.is_absolute()
        or windows_path.drive
        or not path.parts
        or ".." in path.parts
        or path.as_posix() != name
    ):
        raise WorkspaceArchiveError(f"备份包含不安全路径: {name}")
    return path


def _contained_destination(root: Path, member: PurePosixPath) -> Path:
    resolved_root = root.resolve()
    destination = resolved_root.joinpath(*member.parts).resolve(strict=False)
    if destination == resolved_root or not destination.is_relative_to(resolved_root):
        raise WorkspaceArchiveError(f"备份路径越界: {member.as_posix()}")
    return destination
```

`restore_workspace_backup()` should call `_contained_destination(staging,
relative)` and use its result before creating parents. Keeping the grammar
check in verification rejects invalid archives early; keeping the containment
check at the write sink prevents a future parser or call-site change from
silently reintroducing the boundary crossing.

Regression coverage should parameterize the harmless strings in
`poc/README.md`, exercise both `_safe_member_path()` and
`verify_workspace_backup()`, and retain the existing `../escape` case. Add
positive cases such as `projects/default/evidence.txt` and
`metadata.sqlite3`. A Windows CI job should also assert, without opening the
destination, that the destination helper returns a path relative to staging.

## Summary

The restore path validates attacker-authored member names with POSIX semantics
and later consumes them with Windows semantics. That mismatch lets a malicious
but internally consistent backup redirect the subsequent file write outside
the restore staging directory. We established the source-to-sink path by static
review and platform-semantic evidence; no exploit archive or filesystem write
was produced. Canonical member-name validation plus a native resolved
containment check at the sink closes the gap and gives future callers a clear,
testable security invariant.
