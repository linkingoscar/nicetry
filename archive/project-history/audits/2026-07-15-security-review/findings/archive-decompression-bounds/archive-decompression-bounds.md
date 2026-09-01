# Executive Summary

ResearchPath accepts ZIP workspace backups through the local `verify`, `restore`,
and `drill` commands. In the reviewed snapshot,
`verify_workspace_backup()` decompresses every ZIP member with `testzip()` and
then materializes each manifest-listed file with `archive.read()` before any
entry-count, per-member expanded-size, total expanded-size, or compression-ratio
ceiling is enforced. A small, highly compressed backup can therefore consume
large amounts of CPU and memory during an operator-initiated workflow. Restore
and recovery-drill operations inherit the same exposure because they verify the
archive first; restore then decompresses the contents a second time.

The validated impact is availability loss for the local ResearchPath process
and the selected recovery workflow, potentially requiring the operator to kill
or restart the process and remove temporary restore state. The application is a
single-user, loopback-oriented system, and an operator must select or receive
the hostile archive, so this review retains the scan's **P3 / low** calibration.
The root cause maps to CWE-409 (improper handling of highly compressed data) and
CWE-770 (resources allocated without limits), as one archive-decompression
resource-safety issue.

I statically reviewed the unversioned snapshot captured on 2026-07-15,
including `apps/api/app/services/workspace_archive.py`, the CLI entry point, and
the focused archive tests. No fixed revision exists in the supplied material,
and I did not generate or execute a decompression bomb; the accompanying PoC
notes are intentionally limited to tiny, bounded regression tests.

# Background

The `scripts/workspace-archive.py` command exposes four local operations:
`create`, `verify`, `restore`, and `drill`. The first creates a ZIP with
`backup-manifest.json`; the other three consume a caller-selected archive.
Manifest entries record a relative path, an expected uncompressed byte count,
and a SHA-256 digest. The normal trust invariant is that only the named files,
with the recorded sizes and hashes, are accepted.

The implementation already enforces useful integrity properties. It rejects
duplicate names, absolute or parent-traversing paths, missing manifests,
unsupported schema versions, manifest/name mismatches, CRC failures, size
mismatches, and digest mismatches. These checks answer whether decompressed
content is structurally and cryptographically consistent. They do not answer
how much work the process may perform before reaching that conclusion.

That distinction matters because ZIP metadata exposes `file_size` and
`compress_size` before payload decompression. We can use those fields for a
cheap preflight policy, then retain independent counters while streaming because
metadata is attacker-controlled. The intended invariant should be: no payload
is decompressed until the archive's member count, each member's expanded size,
the aggregate expanded size, and each member's expansion ratio all fit within a
centrally defined recovery budget.

# Vulnerability Details

We first reach `verify_workspace_backup()` with an operator-controlled archive
path. After `ZipFile` parses the central directory, the function gathers names
and performs path and duplicate checks. The first payload operation is then:

The decisive verifier path is at
`apps/api/app/services/workspace_archive.py:122-142`:

```python
with ZipFile(archive_path) as archive:
    names = archive.namelist()
    # duplicate, path, and manifest-presence checks
    if archive.testzip() is not None:
        raise WorkspaceArchiveError("备份 ZIP CRC 校验失败")
    manifest = json.loads(archive.read(MANIFEST_NAME))
    # schema and manifest-count checks
    for entry in entries:
        member = _safe_member_path(str(entry.get("path", ""))).as_posix()
        payload = archive.read(member)
        if len(payload) != entry.get("sizeBytes"):
            raise WorkspaceArchiveError(...)
        digest = hashlib.sha256(payload).hexdigest()
```

`ZipFile.testzip()` reads every member to verify its CRC. At that point there is
no ceiling on `len(archive.infolist())`, `ZipInfo.file_size`, the sum of those
sizes, or `file_size / compress_size`. Consequently, the integrity check itself
performs the unbounded decompression. If it completes, `archive.read(member)`
allocates a `bytes` object for the full expanded member before comparing its
length with the manifest. A false manifest size does not protect the process:
we pay the decompression and allocation cost before rejecting it. A correct
manifest is also not a resource policy; an attacker can truthfully describe a
very large expanded file.

The call chain extends the same primitive into recovery:

The recovery path is at
`apps/api/app/services/workspace_archive.py:161-178`:

```python
def restore_workspace_backup(archive_path: Path, target_root: Path) -> dict[str, Any]:
    verification = verify_workspace_backup(archive_path)
    # ...
    with ZipFile(archive_path) as archive:
        manifest = json.loads(archive.read(MANIFEST_NAME))
        for entry in manifest["files"]:
            with archive.open(entry["path"]) as source, destination.open("wb") as target:
                shutil.copyfileobj(source, target)
```

Thus `restore` first performs the verifier's full decompression and in-memory
reads, then streams the members to disk without a restoration byte budget.
`drill_workspace_backup()` calls restore, so it follows the same path. We can
also reach verification from backup creation and workspace maintenance, but the
security-relevant precondition remains a backup whose compressed payload and
expanded representation are disproportionate or simply too large for the local
workstation.

# Exploitability Analysis

The strongest practical route is a valid, externally authored backup whose
central-directory metadata and manifest agree with highly compressible content.
We do not need malformed paths or invalid CRCs. If we preserve those integrity
properties, verification willingly expands the data in `testzip()`; it then
expands manifest-listed members again into memory for SHA-256 validation. On a
restore or drill, the extraction pass adds another decompression and consumes
disk space as well.

Four attacker-controlled dimensions shape the cost. Many members increase ZIP
bookkeeping and repeated decompressor setup. One oversized member drives the
peak `bytes` allocation at `archive.read()`. Several moderately large members
can keep the peak lower while driving aggregate CPU work. A high ratio lets the
archive remain easy to transfer or store while expanding far beyond its input
size. Because the process uses the current OS user's resources and the workflow
is local, the reliable outcome is process or workstation resource pressure, not
code execution or a privilege-boundary bypass.

Invalid CRCs, incorrect hashes, and understated manifest sizes are weak attack
variants: all are eventually rejected, but only after the relevant payload has
been expanded. Conversely, path traversal is not useful for this finding
because `_safe_member_path()` rejects it before extraction. These constraints
make the issue a bounded local denial of service, while also showing why the
existing integrity controls cannot substitute for resource ceilings.

# Proof of Concept

No large archive or runnable abuse generator is included. The `poc/README.md`
file instead specifies tiny unit tests that lower the proposed limits with
`monkeypatch` and use only kilobytes of repetitive data. This safely demonstrates
the decision points without creating sustained CPU, memory, or disk pressure.

From the report directory, the intended post-fix validation command is:

```text
python -m pytest apps/api/tests/test_workspace_archive.py -q
```

Representative expected output is:

```text
.......                                                                  [100%]
7 passed
```

On the reviewed implementation, the new tests fail because the policy
constants and pre-decompression rejection path do not yet exist. After the fix,
the entry-count, per-member, total-expanded-byte, and ratio tests should raise
`WorkspaceArchiveError` before any payload stream is opened; the exact-boundary
test should still verify and restore successfully. Test archives must remain
small and temporary, and cleanup should be handled by pytest's `tmp_path`.

# Remediation

Define one archive resource policy and apply it before every payload read in
both verification and restoration. The exact production values should be
derived from supported workspace sizes and made configurable where deployments
need different envelopes. A reasonable starting policy for review is 10,000 ZIP
entries, 1 GiB per expanded member, 10 GiB aggregate expanded bytes, and a 200:1
maximum expansion ratio. Backup creation should use the same policy so the
application never emits an archive it later refuses.

The first layer is a central-directory preflight. It must run before
`testzip()`, `archive.read()`, or `archive.open()`:

```python
MAX_ARCHIVE_ENTRIES = 10_000
MAX_MEMBER_BYTES = 1 * 1024**3
MAX_EXPANDED_BYTES = 10 * 1024**3
MAX_COMPRESSION_RATIO = 200

def _bounded_members(archive: ZipFile) -> dict[str, ZipInfo]:
    infos = archive.infolist()
    if len(infos) > MAX_ARCHIVE_ENTRIES:
        raise WorkspaceArchiveError("备份成员数量超过限制")

    expanded = 0
    members: dict[str, ZipInfo] = {}
    for info in infos:
        name = _safe_member_path(info.filename).as_posix()
        if info.file_size > MAX_MEMBER_BYTES:
            raise WorkspaceArchiveError(f"备份成员过大: {name}")
        if info.file_size > MAX_COMPRESSION_RATIO * max(info.compress_size, 1):
            raise WorkspaceArchiveError(f"备份成员压缩比超过限制: {name}")
        if expanded > MAX_EXPANDED_BYTES - info.file_size:
            raise WorkspaceArchiveError("备份展开后总大小超过限制")
        expanded += info.file_size
        members[name] = info
    return members
```

Import `ZipInfo` from `zipfile`, preserve the existing duplicate-name check,
and reject encrypted or unsupported compression methods if they are not part of
the backup format. Zero-byte members pass the ratio check because their
`file_size` is zero; `max(compress_size, 1)` prevents division by zero for other
cases.

The second layer must stream and count actual output. Remove `testzip()` and
full-member `archive.read()` calls. Read fixed-size chunks, update SHA-256
incrementally, and stop as soon as a member exceeds both its declared size and
`MAX_MEMBER_BYTES`, or the operation exceeds `MAX_EXPANDED_BYTES`. Reading to
EOF preserves ZIP CRC verification in `ZipExtFile`. Use the same bounded reader
to load the manifest (with a much smaller manifest-specific cap if desired), to
hash each member during verification, and to copy each member during restore.
This makes attacker-controlled metadata an early rejection signal rather than
the sole enforcement mechanism.

Regression coverage should prove the invariant at both layers:

1. Reject one entry above the count limit before opening a payload stream.
2. Reject a member one byte above the per-member limit.
3. Reject individually valid members whose expanded-size sum is one byte over
   the aggregate limit.
4. Reject a member one step above the ratio limit, including a zero compressed
   size edge case, without dividing by zero.
5. Accept values exactly at every boundary.
6. Simulate a stream that yields more than its metadata declares and prove the
   runtime counter aborts verification and restoration.
7. Preserve the existing round-trip, path-safety, CRC, manifest-size, and hash
   tests, and confirm a rejected restore does not publish the staging directory.

# Summary

The archive service validates content integrity but currently performs
unbounded decompression to do so. We can restore the missing invariant by
checking member count, per-member expanded size, total expanded bytes, and
compression ratio from ZIP metadata before decompression, then enforcing the
same ceilings again while streaming. This removes full-member allocations,
avoids a separate unbounded `testzip()` pass, and ensures verify, restore, drill,
creation verification, and maintenance verification all share one predictable
resource envelope. The remaining work is to select production limits from real
workspace-size telemetry, implement the bounded reader, and add the tiny
boundary tests described here.
