# Restored analysis-job paths are not bound to the requested run

## Executive Summary

ResearchPath persists each analysis job's JSON path in SQLite. On retrieval,
`get_analysis_job()` selects the row by the requested run ID but then reads the
stored `state_path` without proving that it names that run's own
`projects/default/runs/<run_id>/state.json`. A database supplied through a
restored workspace can therefore substitute a different parseable JSON file,
including one outside the workspace, for the requested job.

This is a medium-severity, local workspace vulnerability. A malicious backup
author or someone able to corrupt persisted metadata must arrange for a
compatible JSON file to exist at a predictable path and induce the local user
to operate on the restored workspace. The resulting primitive can disclose
substituted job fields through job consumers or cause lifecycle decisions to be
made from the wrong job state. It does not establish arbitrary non-JSON file
disclosure, code execution, OS privilege escalation, or a cross-tenant breach;
ResearchPath's supported deployment is loopback, single-user, and runs with the
current OS user's rights.

I statically reviewed the unversioned source snapshot dated 2026-07-15. I did
not execute a trigger, build the application, or review a fixing revision, and
the first affected release is therefore unknown. The checked snapshot is
affected; no fixed version was present.

## Background

Normal job creation gives us the intended ownership model. The manager derives
one canonical-looking location from the generated run ID:

```python
# apps/api/app/services/analysis_jobs.py:74-86
def _path(self, run_id: str) -> Path:
    return (
        self.settings.state_root
        / "projects" / "default" / "runs" / run_id / "state.json"
    )

def _save(self, state: dict[str, Any]) -> None:
    state["updatedAt"] = _utc_now()
    self.repository.save_analysis_job(state, self._path(state["id"]))
```

`save_analysis_job()` writes that file and stores a path relative to
`state_root` (`apps/api/app/services/analysis_repository.py:59-90`). Thus the
normal invariant is stronger than mere workspace containment: row ID `R`, run
directory `R`, and JSON field `id == R` should describe the same object.

Backups preserve `metadata.sqlite3`. Restore checks ZIP member paths, CRCs,
manifest hashes, and database structural integrity
(`apps/api/app/services/workspace_archive.py:117-149,161-200`). Those controls
prove that an archive is internally consistent; they do not authorize path
strings stored inside SQLite. The maintenance code already recognizes this
distinction by rejecting absolute and parent-traversing database references in
`_safe_relative_path()` (`apps/api/app/services/workspace_maintenance.py:44-48`),
but the runtime job reader does not use that check.

## Vulnerability Details

The localhost job endpoint passes the URL's `run_id` to the manager
(`apps/api/app/api/routes/analyses.py:75-82`), and the manager delegates directly
to the repository (`apps/api/app/services/analysis_jobs.py:379-380`). We then
reach the complete vulnerable transition:

```python
# apps/api/app/services/analysis_repository.py:138-145
def get_analysis_job(self, run_id: str) -> dict[str, Any]:
    with self._connect() as connection:
        row = connection.execute(
            "SELECT state_path FROM analysis_jobs WHERE id = ?", (run_id,)
        ).fetchone()
    if row is None:
        raise LookupError(f"AnalysisRun 不存在: {run_id}")
    return _read_json_safe(self.settings.state_root / row["state_path"])
```

The parameterized query correctly selects a row; it is not SQL injection. The
missing-row branch only proves that metadata for `run_id` exists. If we carry
the row's `state_path` forward, an absolute path replaces the left-hand root in
`pathlib` joining, while `..` components can escape it. Even an in-workspace
path can name another run. No canonical comparison binds the candidate to the
requested run directory, and after parsing there is no check that the JSON's
`id` equals `run_id`.

`_read_json_safe()` simply calls `path.read_text()` and `json.loads()`
(`apps/api/app/services/repository_io.py:33-40`). Accordingly, the concrete bad
state is object substitution: SQL row `R` can cause the service to return job
state `S`, where `S.id != R` and `S` need not reside in `R`'s directory. Startup
recovery repeats the unbound read for unfinished rows
(`apps/api/app/services/analysis_repository.py:147-157`) and then saves the
loaded object's ID (`apps/api/app/services/analysis_jobs.py:65-72`), so the same
invariant must protect both single retrieval and recovery enumeration.

## Exploitability Analysis

The strongest realistic route begins with an externally authored workspace
backup. The author places a valid `analysis_jobs` row in its SQLite database and
sets `state_path` to a predictable sibling or absolute JSON location. After the
operator restores and uses that workspace, requesting the matching database
row reaches the unbound read. If the target JSON has the expected job shape,
the GET and progress consumers can surface its fields; cancel or recovery can
make decisions from the substituted status and then persist a derived copy.

Several constraints materially limit this route. Archive extraction itself
cannot create a file outside the restored root because member paths are checked.
The referenced external file must already exist and be readable by the current
OS user. It must parse as JSON, and HTTP response validation requires a
job-compatible shape, so this is not a general text-file read. The supported
loopback, single-user model also means the process does not cross an OS account
boundary. A second local job state or a known JSON artifact is therefore more
credible than an arbitrary secret file.

Pointing at another run inside the same workspace avoids path prediction and is
the reliable substitution case, but it still does not create a multi-tenant
confidentiality boundary that the product does not claim. The meaningful impact
is integrity and confidentiality within one local research workspace: the UI,
progress stream, export preparation, cancellation, or restart recovery may act
on state that does not belong to the requested row. Malformed JSON is only a
denial-of-service error path and does not strengthen the primitive.

## Proof of Concept

No exploit or destructive trigger is included. The companion `poc/README.md`
specifies harmless pytest regression cases that keep the workspace, substitute
JSON, and SQLite database under pytest's temporary directory. The safe-first
demonstration is to create two valid jobs, change job A's stored path to job B's
state, and assert that retrieval rejects the mismatch before returning B. A
second test points to a valid JSON sentinel outside the temporary workspace but
still inside the same pytest temporary root and asserts rejection without
modification.

I did not run these proposed tests, so no observed execution output is claimed.
On a fixed implementation, the expected result is an explicit repository
integrity/path-binding exception for sibling, traversal, absolute, reparse-point,
and JSON-ID mismatch cases, while the canonical job continues to load.

## Remediation

Restore this invariant at the repository boundary: for requested row `R`, the
only authorized state resource is the canonical
`<state_root>/projects/default/runs/R/state.json`, the run directory is a direct
child of the canonical runs root, and the parsed document's `id` is `R`. Fail
closed before reading when the path is not exact, then fail closed after parsing
when identity differs. Apply the same helper to unfinished-job recovery and any
delete-time state read.

A minimal defensive shape is:

```python
def _read_bound_job_state(self, run_id: str, stored: str) -> dict[str, Any]:
    runs_root = (
        self.settings.state_root / "projects" / "default" / "runs"
    ).resolve()
    run_root = (runs_root / run_id).resolve()
    if run_root.parent != runs_root:
        raise ValueError("invalid analysis run identity")

    expected = (run_root / "state.json").resolve()
    candidate = (self.settings.state_root / Path(stored)).resolve()
    if candidate != expected:
        raise ValueError("analysis state path is not owned by the requested run")

    state = _read_json_safe(candidate)
    if state.get("id") != run_id:
        raise ValueError("analysis state identity does not match its database row")
    return state

def get_analysis_job(self, run_id: str) -> dict[str, Any]:
    # Existing parameterized lookup and missing-row handling remain.
    return self._read_bound_job_state(run_id, str(row["state_path"]))
```

For `list_unfinished_analysis_jobs()`, select both `id` and `state_path`, then
call the same helper for every row. Persist canonical relative paths on write,
but do not treat write-time normalization as sufficient for restored databases.
On Windows, add a reparse-point regression; if state directories can be changed
concurrently by a less-trusted actor, open-and-verify semantics or explicit
reparse-point rejection should close the residual check/read race.

Regression coverage should include canonical success; parent traversal;
absolute paths; another run's `state.json`; matching path with mismatched JSON
`id`; symlink/junction escape where supported; unfinished-job startup recovery;
and confirmation that rejected external sentinels remain unchanged. All tests
should use `tmp_path`, never the default ResearchPath workspace.

## Summary

ResearchPath correctly associates the SQL row with a requested run ID, but it
trusts the row's restored filesystem reference as though that association also
proved resource ownership. We traced that gap to a parseable-JSON substitution
primitive reachable from job retrieval and restart recovery. Its impact is
bounded to one local user's workspace and filesystem authority, with no proven
code execution or privilege escalation.

The durable fix is a containment-and-identity invariant, not a generic string
sanitizer: canonical path equals the requested run's sole state path, canonical
run directory is directly owned by the runs root, and document ID equals the
database row ID. The harmless regression matrix in `poc/README.md` exercises
that invariant and its Windows filesystem edge cases.
