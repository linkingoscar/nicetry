**Finding:** SEC-B03-01
**Severity:** Medium (P2)
**Affected snapshot:** the reviewed unversioned ResearchPath working tree; no commit or fixed revision was available.

## Executive Summary

ResearchPath stores each dataset manifest location in
`dataset_versions.manifest_path`. On a dataset read, the service takes this persisted
SQLite value, joins it to the workspace root, and immediately reads and parses the
result. It does not prove that the resolved file remains inside the workspace, that
it is the canonical manifest for the requested dataset, or that the loaded
manifest's identity matches the request.

This matters at the restore boundary. Archive verification constrains ZIP member
names and checks their recorded sizes and hashes, while the recovery drill runs
SQLite structural and foreign-key checks. None of those controls validates the
meaning of path-valued database columns. An externally authored but internally
consistent backup can therefore preserve a traversal path or a path to another
dataset. After an operator restores and uses that workspace, a normal dataset GET
causes ResearchPath to read the selected JSON with the operator's filesystem
authority.

The practical impact is constrained: the target must be JSON, must have the fields
the repository dereferences, and must satisfy the dataset response contract before
it is returned. This is not an arbitrary byte-file disclosure primitive. The
strongest realistic targets are schema-compatible ResearchPath manifests in a
neighboring workspace, which can expose preview values and metadata or silently
substitute one dataset's manifest for another.

I performed a static review of the unversioned snapshot, including the route,
repository, import, archive, maintenance, schema, and existing tests. I did not
modify a workspace database, restore a crafted archive, start the API, or execute a
trigger. No fixed revision or introduction history was available, so exact affected
release claims remain unknown.

## Background

Normal imports generate a fresh identifier and place the manifest at a predictable
location:

```python
#Source: apps/api/app/services/dataset_import.py:340-346,386-390
dataset_id = f"dataset_{uuid.uuid4().hex[:16]}"
dataset_root = (
    settings.state_root / "projects" / "default" / "datasets" / dataset_id
)
manifest_path = dataset_root / "manifest.json"
# ...
manifest_path.write_text(..., encoding="utf-8")
repository.record_dataset(manifest, manifest_path)
return repository.get_dataset(dataset_id)
```

`record_dataset` converts that application-generated location to a workspace-relative
string before inserting it into SQLite (`apps/api/app/services/dataset_repository.py:83-100`).
That protects the ordinary write flow, but a restored database does not pass through
`record_dataset`.

The supported deployment is personal and local: `scripts/dev.ps1:15-17` binds
Uvicorn to `127.0.0.1`, and `README.md:163-169` documents that boundary. The session
token middleware covers mutating methods only (`apps/api/app/main.py:52-63`), so the
GET route itself does not require that token. Exploitation nevertheless requires an
operator to adopt a malicious or corrupted restored workspace, and the resulting
read is limited to that workstation and the OS user's permissions.

## Vulnerability Details

We first reach the public read route, which forwards the path parameter directly to
the repository and validates only the returned document afterward:

```python
#Source: apps/api/app/api/routes/datasets.py:61-68
@router.get("/{dataset_id}", response_model=DatasetVersionResponse)
def get_dataset(dataset_id: str, services: ApiServices = Depends(get_services)):
    dataset = services.dataset_repository.get_dataset(dataset_id)
    validate_contract(dataset, services.settings.dataset_schema_path)
    return dataset
```

The SQL lookup is parameterized and correctly selects the row by the requested ID.
The trust failure occurs after that lookup:

```python
#Source: apps/api/app/services/dataset_repository.py:107-122
row = connection.execute(
    "SELECT * FROM dataset_versions WHERE id = ?", (dataset_id,)
).fetchone()
# ...
manifest_path = self.settings.state_root / row["manifest_path"]
manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
```

If we carry a persisted value such as `../neighbor/manifest.json` into this join,
`Path` preserves the parent component and `read_text` follows it. An absolute value
can also replace the left operand under normal `pathlib` joining semantics. There is
no `resolve`, containment check, or expected-path comparison before the read.

The restore controls do not repair that gap. `verify_workspace_backup` applies
`_safe_member_path` to archive member names and validates the archive manifest's
size/hash records (`apps/api/app/services/workspace_archive.py:117-149`). Restore
then writes those safe archive members into staging (`workspace_archive.py:161-179`).
The recovery drill runs only `PRAGMA quick_check` and `PRAGMA foreign_key_check`
(`workspace_archive.py:186-202`). A valid SQLite text value such as
`../neighbor/manifest.json` violates neither database check.

Finally, the JSON Schema requires an `id` with the dataset-ID shape, but neither the
schema nor `DatasetVersionResponse` says that it must equal the URL parameter
(`specs/dataset-version.schema.json:22-26`; `apps/api/app/api/responses.py:35-47`).
Thus an in-workspace row for dataset A can point at dataset B's valid manifest and
pass response validation as dataset B. The broken invariant is therefore both
spatial and relational: the persisted path must remain inside the workspace and
must name the canonical manifest belonging to the requested row.

## Exploitability Analysis

The strongest route is a malicious backup author who controls `metadata.sqlite3`
and the backup's internally consistent hashes. We can place a valid dataset row in
that database, set its current dictionary version to zero so no additional state is
needed, and make `manifest_path` select a schema-compatible manifest outside the
restored root. When the operator requests that row's ID, the service reads the
selected manifest and returns fields including original-file metadata, variable
labels, sample values, and preview rows.

A second, more reliable integrity route needs no workspace escape: point dataset A's
row at dataset B's manifest under the same restored root. This avoids dependence on
neighboring filesystem layout and demonstrates why containment alone is insufficient.
The repository caches the substituted response under the requested key, extending
the incorrect association for that process lifetime.

Several constraints prevent a broader claim. Non-JSON files fail parsing; JSON that
lacks fields used by `get_dataset` fails before a response; and documents that do
not satisfy the dataset schema are rejected at the route. The code does not return
raw file bytes, write to the selected manifest, or create a remote service exposure.
An invalid target may cause an individual request to fail, but static review does
not establish a durable denial of service. These constraints support medium rather
than high severity in the documented single-user, loopback deployment.

## Proof of Concept

The accompanying `poc/README.md` deliberately contains only harmless unit-test
cases that use pytest's temporary directory. The tests cover the two security
properties separately: rejection of an out-of-workspace persisted path and
rejection of a contained path that belongs to a different dataset. A positive case
ensures the canonical manifest still loads.

From the report directory, the proposed post-fix checks are:

```sh
cd poc
# Copy the documented cases into apps/api/tests/test_dataset_repository_paths.py
# in a disposable checkout, then run:
python -m pytest apps/api/tests/test_dataset_repository_paths.py -q
```

Expected fixed behavior is three passing tests. This output is illustrative, not an
observation from this review:

```text
...                                                                      [100%]
3 passed
```

The cases never touch the real ResearchPath workspace, do not start a listener, and
do not read user files. Temporary files are removed by pytest. I did not execute
these proposed tests because this assignment was limited to defensive static-review
documentation and did not authorize source changes.

## Remediation

Restore this invariant before every manifest read: a database path is untrusted
persistent input; it must use the canonical POSIX-relative grammar, resolve inside
the resolved workspace root, equal the canonical location derived from the requested
dataset ID, and load a manifest whose identity matches both the request and row.

A minimal service-side pattern is:

```python
from pathlib import Path, PurePosixPath

def _bound_manifest_path(self, row: sqlite3.Row, dataset_id: str) -> Path:
    root = self.settings.state_root.resolve()
    if row["project_id"] != "default":
        raise DatasetMetadataIntegrityError("invalid dataset project binding")

    value = str(row["manifest_path"])
    relative = PurePosixPath(value)
    if "\\" in value or relative.is_absolute() or not relative.parts or ".." in relative.parts:
        raise DatasetMetadataIntegrityError("invalid dataset manifest path")

    candidate = root.joinpath(*relative.parts).resolve(strict=True)
    expected = (
        root / "projects" / "default" / "datasets" / dataset_id / "manifest.json"
    ).resolve(strict=True)
    if not candidate.is_relative_to(root) or candidate != expected:
        raise DatasetMetadataIntegrityError("dataset manifest is not bound to its row")
    return candidate

# In get_dataset, before using manifest content:
manifest = json.loads(self._bound_manifest_path(row, dataset_id).read_text(encoding="utf-8"))
if manifest.get("id") != dataset_id or manifest.get("projectId") != row["project_id"]:
    raise DatasetMetadataIntegrityError("dataset manifest identity mismatch")
```

Define the integrity error in `apps/api/app/services/repository_errors.py` and
translate it in the route without returning absolute paths, consistent with the
repository's service/HTTP boundary. Keep the read-time check even if restore is also
hardened: it protects upgraded workspaces and later database corruption. As
defense-in-depth, restore/drill can enumerate `dataset_versions` and reject any row
whose manifest path or identity violates the same centralized helper.

Regression coverage should include traversal (`../`), absolute paths, backslash
variants on Windows, symlink escape where the platform permits it, a contained
cross-dataset substitution, manifest-ID mismatch, missing canonical file, and a
valid canonical round trip. The exact-path comparison is essential; a containment-only
patch does not stop dataset A from selecting dataset B.

## Summary

ResearchPath correctly parameterizes the dataset lookup and safely handles archive
member paths, but then trusts a semantic path stored inside restored SQLite metadata.
We followed that value from the GET route to `Path.read_text` and found no containment
or object-binding check. Under the documented local threat model, the issue permits
conditional disclosure of schema-compatible manifest content and reliable
cross-dataset substitution, not arbitrary file disclosure.

The durable fix is to derive the expected manifest location from the requested
dataset, resolve and compare the persisted location against it inside the workspace,
and verify the loaded manifest identity before caching or returning it. The harmless
regression cases supplied with this report directly encode those spatial and
relational invariants.
