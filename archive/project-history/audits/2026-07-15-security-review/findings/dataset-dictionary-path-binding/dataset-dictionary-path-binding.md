**SEC-B03-02: Restored dataset dictionary paths are not containment- or identity-bound**

## Executive Summary

ResearchPath trusts `dictionary_versions.path` from its SQLite workspace when it
reconstructs a dataset. A backup author who supplies a self-consistent restored
workspace can therefore point a dataset's current dictionary at an absolute path,
a `..`-relative path outside the workspace, or another dataset's dictionary. The
loaded JSON is not checked to confirm that its `datasetVersionId` and `version`
match the selected SQL row. This is a stored path traversal and object-substitution
issue (SEC-B03-02, P2/medium).

I reviewed the supplied unversioned source snapshot statically. The application
identifies its local API as version `0.1.0`, but no Git revision, fixed revision, or
release history is available, so the exact affected release range is unknown
(`apps/api/app/main.py:43-48`). I did not execute a crafted restore or access any
file through the vulnerable path. The accompanying artifact deliberately contains
only harmless, temporary-directory regression-test guidance.

The practical impact is bounded. ResearchPath runs as the local OS user and its
development launcher binds the API to loopback (`scripts/dev.ps1:15-17`). A
malicious or corrupted backup must first be restored and activated. The sink parses
the target as JSON and consumes only `confirmedTypes`; it is not a general-purpose
raw-file download. A compatible document can nevertheless substitute variable type
metadata, disclose matching type values in the dataset response, or make dataset
loading fail. Those types also influence measurement eligibility, model typing, and
empirical data preparation (`apps/api/app/services/measurement.py:213-220`,
`apps/api/app/services/model_service.py:49-57`, and
`apps/api/app/services/empirical_analysis.py:51-60`).

## Background

Each imported dataset has a row in `dataset_versions`, including a
`current_dictionary_version`. Each dictionary version has a composite
`(dataset_id, version)` key and a persisted file path
(`apps/api/app/services/database_migrations.py:30-52`). Normal dictionary updates
create a JSON document containing `datasetVersionId`, `version`, and
`confirmedTypes`, write it below
`projects/default/datasets/<dataset-id>/dictionary/`, then store the relative path
in SQLite (`apps/api/app/services/dataset_repository.py:173-203`).

That normal write path establishes the intended invariant:

> Dictionary version `V` for dataset `D` must be read only from the canonical
> workspace resource `projects/default/datasets/D/dictionary/vV.json`; its resolved
> target must remain inside the workspace, and the parsed document must identify
> itself as dataset `D`, version `V`.

Workspace restore is a local maintenance workflow exposed by
`scripts/workspace-archive.py:34-48`. Archive verification rejects unsafe ZIP member
names and checks sizes, CRCs, and SHA-256 values, but those hashes are declared by
the same archive manifest; they establish internal consistency, not publisher
authenticity (`apps/api/app/services/workspace_archive.py:117-158`). Restore then
copies the verified members, including `metadata.sqlite3`, into a new workspace
(`apps/api/app/services/workspace_archive.py:161-183`). SQLite quick checks and
foreign-key checks used by the recovery drill cannot establish that a path stored in
a valid row is safe or that the referenced JSON belongs to that row
(`apps/api/app/services/workspace_archive.py:186-203`).

## Vulnerability Details

A dataset read begins at `GET /api/v1/datasets/{dataset_id}` and delegates to
`DatasetRepository.get_dataset` (`apps/api/app/api/routes/datasets.py:52-64`). We
first obtain the dataset row and its `current_dictionary_version`. The repository
then scopes the SQL lookup by dataset and version, which proves only which database
row was selected:

```python
dictionary_version = int(row["current_dictionary_version"])
if dictionary_version > 0:
    with self._connect() as connection:
        dictionary_row = connection.execute(
            "SELECT path FROM dictionary_versions WHERE dataset_id = ? AND version = ?",
            (dataset_id, dictionary_version),
        ).fetchone()
    if dictionary_row is not None:
        dictionary_path = self.settings.state_root / dictionary_row["path"]
        dictionary = json.loads(dictionary_path.read_text(encoding="utf-8"))
        confirmed = dictionary["confirmedTypes"]
```

If the persisted operand is absolute, `Path` joining discards `state_root`. If it
contains `..`, the filesystem resolves the traversal when `read_text` opens it. A
relative path may also name another dataset's resource. We then carry the parsed
`confirmedTypes` into the requested dataset without comparing
`dictionary["datasetVersionId"]` with `dataset_id` or
`dictionary["version"]` with `dictionary_version`.

The merge is selective: only keys matching variables in the requested manifest are
returned (`apps/api/app/services/dataset_repository.py:137-151`). This constraint
prevents arbitrary JSON fields from being reflected, but it does not restore object
identity. A schema-compatible foreign dictionary with overlapping variable IDs can
change the effective `confirmedType` values. An incompatible file instead causes
JSON, key, or response-contract errors, providing a dataset-specific availability
failure. Mutation-session middleware does not mitigate this read path: the
persisted state is introduced by the offline restore workflow, while dataset
retrieval is a GET (`apps/api/app/main.py:52-63`).

## Exploitability Analysis

The strongest realistic route is a malicious backup delivered to a local operator.
The backup author can create a structurally valid SQLite database in which dataset
`D` selects version `V`, while the corresponding row names a different JSON object.
Because archive hashes are not signatures, the author can recompute all manifest
metadata. Once the restored directory is used as `state_root`, the next uncached GET
for `D` reaches the read.

We can distinguish three outcomes. An outside-workspace but valid dictionary can
expose matching `confirmedTypes` values and substitute them into `D`. A valid
dictionary belonging to another dataset can silently alter which variables are
treated as continuous, ordinal, binary, or otherwise eligible downstream. A
non-JSON or structurally incompatible target generally stops at parsing, lookup, or
contract validation, so this route offers denial of access to the dataset rather
than raw file disclosure.

Several constraints keep the severity at medium. The supported deployment is
single-user and loopback-only; no remote tenant boundary was identified. The
attacker needs the operator to restore and activate externally authored state, or
already needs write access to the workspace database. The process reads with the
operator's filesystem rights, and the response exposes only compatible type values
for variable IDs present in the requested manifest. There is no source evidence of
arbitrary code execution, arbitrary file write, database credential theft, or full
file-content exfiltration. A path to a file that does not contain the expected JSON
shape is therefore a noisy dead end.

## Proof of Concept

No exploit program is included. `poc/README.md` defines harmless pytest regression
cases that operate entirely below `tmp_path`: an outside sentinel dictionary, a
second dataset dictionary, and mismatched document identities. On the vulnerable
shape, those cases would show that a stored path can select the sentinel or sibling
metadata. After remediation, each case must fail closed with a dedicated workspace
integrity error before any foreign metadata is merged.

The README also gives a safe-first test order and expected post-fix output. I did
not run those proposed tests because this assignment did not authorize source
changes and the regression module does not yet exist. No test should reference a
real user file, existing workspace, network service, or production backup.

## Remediation

Restore and runtime reads should enforce the invariant stated above rather than
treat SQLite path text as authority. For this resource, the safest minimal design is
to derive the canonical relative path from the already-selected `dataset_id` and
`dictionary_version`, require the stored value to equal it, resolve the result, and
then validate the JSON identity before consuming `confirmedTypes`. A representative
pattern is:

```python
from pathlib import Path, PurePosixPath

expected = PurePosixPath(
    "projects", "default", "datasets", dataset_id,
    "dictionary", f"v{dictionary_version}.json",
)
stored = PurePosixPath(str(dictionary_row["path"]))
if stored != expected:
    raise WorkspaceIntegrityError("dictionary path does not match its database identity")

root = self.settings.state_root.resolve()
dictionary_path = (root / Path(*stored.parts)).resolve(strict=True)
if not dictionary_path.is_relative_to(root):
    raise WorkspaceIntegrityError("dictionary path escapes the workspace")

dictionary = _read_json_safe(dictionary_path)
if (
    dictionary.get("schemaVersion") != "1.0.0"
    or dictionary.get("datasetVersionId") != dataset_id
    or dictionary.get("version") != dictionary_version
):
    raise WorkspaceIntegrityError("dictionary document identity mismatch")
```

The implementation should additionally validate that `confirmedTypes` is an object,
its keys are a subset of the manifest variable IDs, its values belong to the
supported type enum, and its length agrees with `confirmed_count`. Fail closed with
a dedicated integrity exception translated to a controlled API response; do not
silently downgrade to an empty dictionary, because that would hide corrupt research
state. Resolve-based containment must account for symlinks and Windows junctions;
where hostile concurrent local mutation is in scope, use a no-follow/open-handle
strategy to avoid a check/use race.

The same validator should run during backup verification, restore drill, and before
a restored workspace is activated. `workspace_maintenance._safe_relative_path`
already rejects absolute and parent-relative database references
(`apps/api/app/services/workspace_maintenance.py:39-47`), but it is not called by
the runtime read and does not establish dataset/version identity. Centralize a
resource-reference validator rather than duplicating this partial check.

Regression coverage should include normal round trips; absolute, drive-qualified,
root-relative, `..`, sibling-dataset, and separator-variant paths; a resolved
symlink/junction escape when the platform permits it; missing files; mismatched
`datasetVersionId`; mismatched `version`; invalid or unknown `confirmedTypes`; and a
restore archive whose CRC, hashes, SQLite quick check, and foreign keys are all
valid but whose dictionary binding is not. Assert both rejection and the absence of
foreign values in the dataset response.

## Summary

SEC-B03-02 exists because a database association is mistaken for filesystem and
document identity. We select the correct SQL row, but then trust its path and the
JSON reached by that path. Under the bounded local restore threat model, this permits
cross-object type-metadata substitution, limited compatible-value disclosure, or a
dataset-loading failure; it does not establish general raw-file disclosure or code
execution.

The durable fix is one invariant enforced at every restored-resource boundary:
derive or verify the canonical resource path, prove resolved containment, and bind
the parsed object's identity back to the database key before use. The same review
should later be applied to other persisted resource columns listed in
`REFERENCE_COLUMNS`, but this report makes no claim that those paths are separately
vulnerable (`apps/api/app/services/workspace_maintenance.py:21-30`).
