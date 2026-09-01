# Workspace cleanup accepts a recovery archive that is not bound to the audited bytes

## Executive Summary

ResearchPath 0.1.0 contains an integrity flaw in its local workspace-maintenance
workflow. Before deleting orphaned dataset directories, the cleanup service checks
that the live database still matches an earlier audit and that an operator-supplied
ZIP archive is internally valid. It then treats matching archive member names as
proof that every file scheduled for deletion is recoverable. The service never
proves that the bytes under those names, or the database snapshot in the archive,
came from the audited workspace.

Consequently, a stale or unrelated but well-formed ResearchPath backup can satisfy
the cleanup precondition when it contains the same relative path names. Cleanup can
then remove the current orphan data even though restoring the accepted archive would
yield different content. This violates the workflow's stated pre-clean recovery
guarantee and can cause loss of research data.

This issue is SEC-B02-04, with a suggested priority of P2 and severity of medium.
It is best described as insufficient verification of data authenticity (CWE-345):
the archive is authenticated against its own manifest, but not against the state
whose deletion it authorizes. The affected surface is a privileged, local
maintenance CLI, not an unauthenticated network endpoint, and the supported product
model is a single-user Windows workstation listening only on loopback. There is no
demonstrated privilege escalation or cross-tenant impact.

I statically reviewed the unversioned ResearchPath 0.1.0 source snapshot and its
maintenance and archive tests. No source revision or fixed revision was available,
so the affected range can only be stated as the reviewed 0.1.0 snapshot; introduction
history is unknown. In accordance with the validation boundary, I did not run the
cleanup path, delete any directory, or create an executable trigger. The source trace
is conclusive because the accepted values and the deletion sink are in one function,
and the companion `poc/README.md` specifies non-destructive regression tests that
replace the sink with a recording stub.

## Background

ResearchPath stores local application state below a workspace root. Dataset versions
known to the application are represented in `metadata.sqlite3`, while dataset files
reside under `projects/default/datasets`. The maintenance service uses database
references rather than filename heuristics to identify directories that are no
longer represented by a dataset row.

In `audit_workspace()` (`apps/api/app/services/workspace_maintenance.py:88`), the
service resolves the workspace root, reads dataset identifiers and file references
from SQLite, and lists dataset directories whose names are not present in the
database. The audit records those paths and a logical SHA-256 digest of the database:

```python
# apps/api/app/services/workspace_maintenance.py:118-131
return {
    "schemaVersion": "1.0.0",
    "generatedAt": datetime.now(timezone.utc).isoformat(),
    "stateRoot": str(state_root),
    "databaseSha256": (
        _database_sha256(database_path) if database_path.is_file() else None
    ),
    "orphanDatasetDirectories": orphan_directories,
    "unreferencedFiles": unreferenced_files,
}
```

The operator subsequently supplies this audit and a backup to the
`clean-orphan-datasets` command. The CLI makes both paths explicit
(`scripts/workspace-maintenance.py:40-52`), so the backup is a local,
operator-selected security input:

```python
clean_parser.add_argument("--audit", type=Path, required=True)
clean_parser.add_argument("--backup", type=Path, required=True)

result = clean_audited_orphan_datasets(
    args.state_root, args.audit, args.backup
)
```

Backups have meaningful internal integrity protection. During creation,
`create_workspace_backup()` snapshots SQLite and copies workspace files to staging.
It records each member's relative path, size, and SHA-256 digest in
`backup-manifest.json` (`apps/api/app/services/workspace_archive.py:57-109`). During
verification, `verify_workspace_backup()` rejects unsafe or duplicate names, checks
the ZIP CRC, compares every archived payload with its manifest size and digest, and
rejects extra or missing members (`apps/api/app/services/workspace_archive.py:117-158`).

Those checks answer, “Is this archive internally coherent?” They do not answer the
different question needed at cleanup: “Does this archive contain the exact audited
bytes that are about to be destroyed?” The normal invariant should be:

```text
current bytes scheduled for deletion
              == audited bytes
              == verified archive bytes

current logical database == audited database == archived logical database
```

The current design establishes only the first database equality and path-name
membership in the archive.

## Vulnerability Details

We first enter `clean_audited_orphan_datasets()` with three operator-controlled paths:
the target workspace, the earlier audit, and the proposed recovery archive. The
function correctly binds the audit to the requested workspace root and rejects an
unsupported audit schema (`apps/api/app/services/workspace_maintenance.py:135-143`).
It then recalculates the live database's logical hash:

```python
# apps/api/app/services/workspace_maintenance.py:145-150
database_path = state_root / "metadata.sqlite3"
current_database_hash = (
    _database_sha256(database_path) if database_path.is_file() else None
)
if current_database_hash != audit.get("databaseSha256"):
    raise WorkspaceMaintenanceError("审计后数据库已变化，请重新审计并备份")
```

This check prevents cleanup when the live database changed after the audit. If we
carry the accepted `databaseSha256` forward, however, no later comparison connects it
to `metadata.sqlite3` inside the supplied backup.

The backup boundary follows immediately:

```python
# apps/api/app/services/workspace_maintenance.py:152-155
verify_workspace_backup(backup_path)
with ZipFile(backup_path) as archive:
    manifest = json.loads(archive.read(MANIFEST_NAME))
backed_up_files = {str(entry["path"]) for entry in manifest["files"]}
```

`verify_workspace_backup()` has already shown that each archived payload matches the
digest declared by that same archive. Cleanup then discards those validated digests
and sizes, reducing the manifest to a set of path strings. There is no comparison
between:

- the audit's `databaseSha256` and the archived database's logical contents;
- a current file digest and the digest in the backup manifest;
- an audited file digest and either current or archived content (the audit does not
  record per-file digests); or
- a cryptographic snapshot identifier shared by the audit and backup.

Next, cleanup runs a fresh audit and confirms that every scheduled directory is still
an orphan. It also resolves each target beneath `state_root`, which is an important
path-containment control (`apps/api/app/services/workspace_maintenance.py:157-176`).
Neither control establishes recovery provenance.

The decisive check and sink are:

```python
# apps/api/app/services/workspace_maintenance.py:177-198
target_files = [path for path in target.rglob("*") if path.is_file()]
missing_from_backup = [
    path.relative_to(state_root).as_posix()
    for path in target_files
    if path.relative_to(state_root).as_posix() not in backed_up_files
]
if missing_from_backup:
    raise WorkspaceMaintenanceError(
        "备份未覆盖待清理文件: " + ", ".join(missing_from_backup[:10])
    )

shutil.rmtree(target, onerror=remove_readonly)
```

Suppose the audited workspace contains
`projects/default/datasets/dataset_orphan/raw.csv` with the only copy of the current
research data. A different, valid archive contains the same relative member name but
older or unrelated CSV bytes. We can satisfy every implemented precondition: the
live database still matches the audit, the directory remains orphaned, the ZIP and
manifest are internally valid, and the member name is present. The comprehension
therefore produces an empty `missing_from_backup` list, and `shutil.rmtree()` removes
the current directory. Restoring the accepted archive cannot reproduce the deleted
bytes.

The same mismatch can arise without a deliberately forged archive. A stale backup
from the same workspace, or a valid backup from another workspace with coincident
path names, is enough. File content can also change after the audit because only the
database is re-hashed; an archive made before that change still passes if its member
names match. The bug is therefore a missing three-way content binding, not a failure
of ZIP CRC, manifest hashing, SQLite integrity checking, or path containment.

## Exploitability Analysis

The strongest practical route is archive substitution in the local maintenance
workflow. An operator intends to perform a destructive cleanup only after taking a
recoverable snapshot. If the path supplied to `--backup` resolves to an older or
unrelated ResearchPath archive with the required names, the application reports
backup coverage and proceeds despite the content mismatch. A person or process that
can influence which backup file the operator selects can exploit that misplaced
trust; accidental selection has the same data-loss result.

We do not need to break SHA-256 or corrupt a ZIP. In fact, internal validity helps the
substitution look trustworthy. An archive author chooses payload bytes, places the
corresponding digest and size in the manifest, and uses path names expected in the
target workspace. `verify_workspace_backup()` proves only that those choices agree
with each other. When cleanup converts the verified entries to `backed_up_files`, the
attacker-controlled digest is no longer consulted.

The required path knowledge is a meaningful but modest constraint. Orphan dataset
directory names must coincide, and every regular file enumerated under a scheduled
directory must have a same-named archive entry. A stale backup naturally provides
that knowledge. For an externally supplied archive, names may be learned from prior
workspace access, logs, exports, or operator communication; random guessing becomes
less reliable as the number of files increases. The content itself need not resemble
the target.

The impact is bounded to integrity and availability of the local workspace being
maintained. This path does not expose a public listener, cross an OS-user boundary,
or grant additional filesystem permissions. An operator able to invoke the CLI may
already be able to delete workspace data manually, so this is not a conventional
privilege-escalation primitive. The security consequence is that a safety control
explicitly relied upon before an irreversible operation can authorize deletion on a
false recovery premise. In environments where a trusted operator consumes an archive
provided or replaced by another party, the boundary is clearer; in a strictly
single-user deployment, accidental stale-backup selection is the more likely route.

Replacing the archive after verification is not required for this issue, and a ZIP
parsing race would be a separate concern. Likewise, path traversal is an unhelpful
route here because archive member paths are validated and cleanup independently
confines deletion beneath the workspace. The simplest and most reliable condition is
an ordinary, internally valid archive with matching names and mismatched bytes.

I did not execute this route because cleanup reaches an actual recursive-deletion
sink and the validation scope prohibited deletion. The source-level state transition
does not depend on timing or platform-specific behavior: after name coverage passes,
the only remaining branch before the sink updates counters and calls `shutil.rmtree`.

## Proof of Concept

The companion `poc/README.md` provides a safe unit-test design rather than executable
exploit code. It uses temporary directory fixtures for two logical workspaces and
replaces `workspace_maintenance.shutil.rmtree` with a recording stub. No directory is
removed. The test constructs a victim audit and a valid decoy backup whose file paths
match the victim while the file bytes differ, then calls the real cleanup service.

On the vulnerable implementation, the expected diagnostic result is:

```text
[vulnerable] decoy archive verification: accepted
[vulnerable] mismatched path coverage: accepted
[vulnerable] deletion sink invocation recorded: 1
[safe] recording stub preserved all fixture files
```

On a fixed implementation, the service should reject the request before the stub is
called:

```text
[fixed] cleanup rejected: backup content does not match audited workspace
[fixed] deletion sink invocation recorded: 0
[safe] all fixture files preserved
```

The design also specifies database-snapshot, post-audit file-mutation, missing-hash,
and happy-path cases. It intentionally contains no runnable trigger or destructive
command. A maintainer implementing the tests should retain the sink stub and use only
the test framework's temporary directory fixture.

## Remediation

The fix should restore a content identity invariant before cleanup can reach
`shutil.rmtree`: every current file scheduled for deletion must match the exact file
recorded by the audit, and that audit record must match a verified payload in the
backup. The archived logical database must likewise match the audit's database hash.
Path equality alone must never authorize deletion.

One practical schema update is to have `audit_workspace()` emit a map of scheduled
orphan files to `{sizeBytes, sha256}`. During backup creation, calculate a logical
database hash from the staged SQLite snapshot and store it in the signed-by-content
manifest alongside the existing per-file records. Cleanup can then fail closed on
old manifests and compare all three views:

```python
# Minimal defensive shape; exact error text and schema migration may vary.
verification = verify_workspace_backup(backup_path)
with ZipFile(backup_path) as archive:
    manifest = json.loads(archive.read(MANIFEST_NAME))

if manifest.get("databaseLogicalSha256") != audit.get("databaseSha256"):
    raise WorkspaceMaintenanceError("备份数据库与维护审计不一致")

backup_files = {entry["path"]: entry for entry in manifest["files"]}
audited_files = audit.get("orphanDatasetFiles")
if not isinstance(audited_files, dict):
    raise WorkspaceMaintenanceError("审计缺少待清理文件哈希")

for path in target_files:
    relative = path.relative_to(state_root).as_posix()
    current = {"sizeBytes": path.stat().st_size, "sha256": _sha256(path)}
    audited = audited_files.get(relative)
    archived = backup_files.get(relative)
    if audited is None or archived is None:
        raise WorkspaceMaintenanceError(f"备份未覆盖审计文件: {relative}")
    expected = {"sizeBytes": audited["sizeBytes"], "sha256": audited["sha256"]}
    stored = {"sizeBytes": archived["sizeBytes"], "sha256": archived["sha256"]}
    if current != expected or stored != expected:
        raise WorkspaceMaintenanceError(f"备份内容与审计文件不一致: {relative}")
```

This sketch relies on the existing verifier to establish that each manifest digest
matches the actual ZIP payload. The comparison then gives us
`current == audit == verified archive`. `databaseLogicalSha256` should be calculated
with the same canonical SQLite-dump algorithm used by `_database_sha256()`, but
against the staged database snapshot, so physical SQLite layout differences do not
cause false mismatches.

Several hardening details matter:

- Bump both audit and archive schema versions and reject legacy documents for
  destructive cleanup. Treating absent hashes as compatible would preserve the bug.
- Canonicalize and sort paths before calculating any aggregate snapshot digest. If an
  aggregate digest supplements per-file checks, use an unambiguous length-delimited
  encoding rather than concatenated strings.
- Bind provenance such as a workspace UUID and audit ID as useful diagnostics, but do
  not substitute identifiers for content equality. A copied identifier is not proof
  of bytes.
- Hold an application-wide maintenance lock across final hashing and deletion. For a
  stronger crash- and race-resistant design, atomically rename scheduled directories
  into a same-volume quarantine, hash and archive the quarantined objects, verify the
  resulting archive, and only then remove the quarantine.
- Preserve the existing current-database, orphan-status, path-containment, archive
  member, CRC, and per-payload hash checks. The new binding complements those controls.

Regression coverage should include the harmless cases in `poc/README.md`. The key
test creates same-named but different victim and decoy bytes, stubs `shutil.rmtree`,
and asserts that cleanup raises before the stub records a call. Nearby tests should
reject an archived database from another audited snapshot, reject a file modified
after audit, reject missing or duplicate file identities, and accept an exact backup.
Every rejection test must assert both zero sink calls and unchanged fixture bytes.

## Summary

ResearchPath correctly validates the internal structure and hashes of a workspace
archive, but cleanup asks that verifier to establish a stronger fact than it actually
proves. By reducing verified manifest entries to path names, the service accepts a
stale or unrelated archive as recovery coverage and can recursively remove current
orphan data that the archive cannot restore.

We traced the complete local path from the operator-selected `--backup` argument,
through database and archive checks, to filename-only coverage and
`shutil.rmtree()`. The practical impact is loss of research data under a false backup
guarantee, constrained by the local, privileged maintenance workflow and single-user
deployment model. The durable fix is a fail-closed, three-way content binding among
the current deletion targets, the audit, and verified archive payloads, plus an
equivalent logical-database comparison.

Future review should concentrate on the consistency window between final hashing and
deletion and on whether quarantine-and-verify can make the recovery invariant atomic.
Those are hardening directions for this same maintenance boundary; they do not alter
the immediate requirement that names alone must never stand in for audited bytes.
