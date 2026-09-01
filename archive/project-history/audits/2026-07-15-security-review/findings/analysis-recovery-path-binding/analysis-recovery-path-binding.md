# Analysis recovery does not bind restored paths to job identity

## Executive Summary

ResearchPath automatically converts unfinished analysis jobs to `failed` when the
local service starts. In the reviewed snapshot, recovery selects `state_path` from
each queued, running, or cancelling SQLite row and reads that path without first
proving that it is the canonical state file for that row's job ID. It then trusts
the JSON document's `id` when choosing the destination path and database upsert
identity. A restored or corrupted workspace can therefore redirect recovery to an
unexpected JSON document, substitute one job's state for another, abort recovery,
or—when a structurally valid document supplies a path-like ID—direct the subsequent
`state.json` write outside the intended run directory.

I performed a static review of the unversioned source snapshot available on
2026-07-15. I traced workspace restore, repository loading, manager construction,
and recovery saving, but I did not start the API or execute an adversarial trigger.
No fixed revision or advisory version was available, so the affected release range
is unknown; the checked snapshot is affected. We rate the issue **low severity
(P3)** for ResearchPath's supported loopback, single-user deployment: exploitation
requires a maliciously authored or corrupted restored workspace and affects the
local process and files reachable with that user's permissions.

## Background

Analysis state is represented twice: an `analysis_jobs` row carries lifecycle
metadata and a `state_path`, while a JSON file contains the fuller job document.
Normal saves derive a predictable location from a generated run ID and store its
workspace-relative path in SQLite (`apps/api/app/services/analysis_jobs.py:74-86`,
`apps/api/app/services/analysis_repository.py:59-89`). Under normal operation these
two representations agree:

```text
SQLite row id = run_abc
SQLite state_path = projects/default/runs/run_abc/state.json
JSON id = run_abc
```

The API constructs the repository and then the job manager as part of application
creation (`apps/api/app/main.py:18-29`). The manager invokes interrupted-job
recovery in its constructor, before requests are handled
(`apps/api/app/services/analysis_jobs.py:31-49`). This makes recovery an automatic
consumer of restored persistent state, not an operation protected by the mutation
session token.

Workspace backup verification does useful archive-level work: it rejects unsafe
ZIP member names, duplicate or unlisted members, CRC failures, size mismatches, and
hash mismatches (`apps/api/app/services/workspace_archive.py:117-149`). Restore then
extracts only validated relative members into a new staging directory
(`apps/api/app/services/workspace_archive.py:161-183`). Those checks establish that
the archive was extracted as described by its own manifest. They do not establish
that path strings inside the restored SQLite database are safe or semantically
bound to their rows. The recovery drill checks SQLite `quick_check` and foreign-key
integrity, but neither check validates `analysis_jobs.state_path` or JSON identity
(`apps/api/app/services/workspace_archive.py:186-207`).

The codebase already demonstrates the right kind of lexical control in maintenance
code: `_safe_relative_path` rejects absolute paths and parent components before
using database references (`apps/api/app/services/workspace_maintenance.py:44-48`,
`apps/api/app/services/workspace_maintenance.py:71-85`). Recovery does not apply an
equivalent, job-specific rule.

## Vulnerability Details

We first reach `list_unfinished_analysis_jobs()`. The lifecycle filter is sound as
far as status is concerned, but the query discards the row ID and returns only the
path:

```python
# apps/api/app/services/analysis_repository.py:147-157
def list_unfinished_analysis_jobs(self) -> list[dict[str, Any]]:
    with self._connect() as connection:
        rows = connection.execute(
            """
            SELECT state_path FROM analysis_jobs
            WHERE status IN ('queued', 'running', 'cancelling')
            """
        ).fetchall()
    return [
        _read_json_safe(self.settings.state_root / row["state_path"])
        for row in rows
    ]
```

Because a path join does not itself enforce containment, an absolute stored path can
replace the left operand and a relative path containing `..` can escape it when the
filesystem resolves the name. The function also accepts a sibling run's state file
or any other in-workspace JSON file. Crucially, we have already lost the expected
row ID before the first file read, so recovery cannot prove that the chosen path is
`projects/default/runs/<row-id>/state.json`.

We then carry the loaded document into the manager. Recovery mutates every document
and passes it to `_save()` (`apps/api/app/services/analysis_jobs.py:65-72`). `_save()`
uses the document's `state["id"]` both to construct a destination path and to select
the listener/upsert identity (`apps/api/app/services/analysis_jobs.py:74-90`). The
repository finally inserts or updates the row keyed by that same document field
(`apps/api/app/services/analysis_repository.py:59-89`). There is no comparison
between the original SQLite row ID, the run-directory segment, and the JSON ID.

The bad transition is therefore:

```text
untrusted restored row.state_path
  -> file read before containment or canonical-shape validation
  -> untrusted document.id replaces the missing row identity
  -> failed-state write and SQLite upsert under document.id
```

A malformed, missing, or unreadable file raises during the list comprehension, so
one bad row can prevent all later unfinished jobs from being recovered and can
prevent manager construction. A valid but mismatched document can cause the wrong
job to be marked failed or overwrite an existing internal state record. A path-like
document ID can also influence the destination passed to the atomic JSON writer.
The write is constrained to a file named `state.json`, and its success depends on
the current user's filesystem access and the existence or creatability of the
selected parent path; we do not claim general arbitrary-file overwrite or code
execution.

## Exploitability Analysis

The strongest realistic route begins with a workspace backup authored or modified
by someone the local operator does not trust. The attacker places an unfinished
`analysis_jobs` row in its internally consistent SQLite database and supplies a
matching archive manifest and hashes. Archive verification succeeds because hashes
authenticate the archive against its attacker-supplied manifest, not against a
trusted signer or a schema of database references. When the operator launches the
restored workspace, recovery is automatic.

For reliable availability impact, the stored reference can identify a missing,
malformed, or wrong-shaped JSON document. Because the comprehension and recovery
loop do not isolate entries, the exception can stop recovery for the entire manager.
This route requires little knowledge of local filesystem layout and is the most
predictable effect.

For state substitution, we can instead point the row at a structurally sufficient
JSON document whose `id` names another run. Recovery marks that loaded state failed
and saves it under the document-provided identity. This can corrupt the local job
ledger or replace a selected run's state, subject to the foreign-key and required
field constraints applied by the upsert. Extra fields in the JSON may also be
copied into the recovered state document, but we did not validate a separate
confidentiality primitive or remote disclosure path.

The path-directed write is more constrained. A document ID containing parent
components can affect `_path(state["id"])`, but the destination basename remains
`state.json`; permissions, platform path rules, and a usable target directory all
affect reliability. ResearchPath runs with the local operator's rights and exposes
no supported multi-tenant or public-network boundary, so this does not justify a
higher severity on its own. The session token and loopback/CORS controls are also
not relevant mitigations at startup: the triggering input is restored persistence,
not an HTTP mutation.

We deliberately stop at these bounded primitives. The source supports local
availability, job-state integrity, and constrained filesystem-integrity impact. It
does not establish privilege escalation, arbitrary code execution, access beyond
the current OS user's authority, or impact to other ResearchPath installations.

## Proof of Concept

We provide a defensive regression design in `poc/README.md`. It uses only pytest's
temporary directory, a temporary SQLite workspace, and a read spy. It creates no
system-wide files, follows no external paths, and performs no destructive action.
The safe-first assertion is that absolute, parent-traversing, sibling-run, and
mismatched-identity references are rejected **before** the JSON reader is called.

From the report directory, the intended post-fix command is:

```sh
cd poc
python -m pytest -q ../../../apps/api/tests/test_analysis_recovery_security.py
```

The named test module is a proposed repository test location; it is not included in
this source-review-only report bundle. Expected fixed behavior is:

```text
......                                                                   [100%]
6 passed
```

I did not run this command because the remediation and regression module do not yet
exist in the reviewed snapshot. The README records the assertions needed to
distinguish a fixed implementation without packaging a weaponized workspace or an
exploit.

## Remediation

The invariant should be explicit: **before reading any restored job state, recovery
must bind the SQLite row ID, canonical workspace-relative path, resolved path, and
JSON identity to one run; it must never derive recovery authority from the loaded
document.** Invalid entries should be quarantined or marked failed by row ID, and
one invalid entry should not block recovery of other rows.

A minimal defensive shape is:

```python
from pathlib import Path, PurePosixPath

def _bound_state_path(state_root: Path, run_id: str, stored: str) -> Path:
    relative = PurePosixPath(stored)
    expected = PurePosixPath(
        "projects", "default", "runs", run_id, "state.json"
    )
    if relative.is_absolute() or ".." in relative.parts or relative != expected:
        raise ValueError("analysis job state path is not bound to its row")
    root = state_root.resolve()
    candidate = (root / Path(*relative.parts)).resolve()
    if candidate == root or not candidate.is_relative_to(root):
        raise ValueError("analysis job state path escapes the workspace")
    return candidate

# Query both values so row identity exists before the read.
rows = connection.execute(
    "SELECT id, state_path FROM analysis_jobs "
    "WHERE status IN ('queued', 'running', 'cancelling')"
).fetchall()
for row in rows:
    path = _bound_state_path(self.settings.state_root, row["id"], row["state_path"])
    state = _read_json_safe(path)
    if state.get("id") != row["id"]:
        raise ValueError("analysis job document identity mismatch")
    yield row["id"], state
```

The manager should carry `row["id"]` separately and use that value for the recovery
write and database update. Prefer a repository operation such as
`mark_interrupted_failed(run_id, expected_state_path)` that performs a conditional
update by row ID; do not route an untrusted document back through the general
upsert. Catch validation/read failures per row, record a bounded diagnostic, and
continue with other jobs. If symlinks are permitted inside the workspace, use a
safe-open strategy appropriate to the supported platforms so validation and open
cannot be separated by a path-swap race.

Regression coverage should prove all of the following with `tmp_path`:

1. absolute and `..` references are rejected before `_read_json_safe`;
2. an in-root sibling run path is rejected for the current row;
3. a symlink whose resolved target escapes the workspace is rejected;
4. a JSON `id` mismatch cannot create, overwrite, or upsert another run;
5. malformed or missing state for one row does not block a valid later row; and
6. a canonical path plus matching row/document ID is recovered as failed.

The existing workspace recovery drill should also invoke this semantic reference
validation. SQLite integrity and archive hashes are useful, but they are not a
substitute for application-level path and identity invariants.

## Summary

Unfinished-job recovery crosses the restored-workspace trust boundary before it has
bound a persisted path to a job. By selecting only `state_path`, reading it without
containment, and later trusting the loaded `id`, the implementation allows one
restored row to disrupt startup, substitute job state, or direct a constrained
`state.json` write. The impact remains low in the supported single-user local model,
but the recovery invariant is security-relevant and should be enforced before the
first read. Centralizing canonical path binding, carrying row identity separately,
isolating invalid entries, and adding temporary-directory regression tests closes
this issue without expanding the recovery component's authority.
