**Export bundles do not bind restored run identity to their filesystem authority**

## Executive Summary

ResearchPath's analysis export endpoint looks up a job by the requested `run_id`,
but it passes only the restored state object into the bundle service. The service
then treats `state["id"]` as a trusted path component for its result read,
export directory, staging tree, data source, and final ZIP destination. A
restored workspace can therefore make the selected database row name one run
while its state names another or supplies a path-shaped identifier.

I statically reviewed the unversioned source snapshot supplied for this finding;
there is no Git `HEAD` in the checkout, no fixed revision was available, and I
did not execute a trigger or modify product source. The affected version range
and introduction date are therefore unknown. The validated impact is bounded to
the supported local, single-user deployment: an author of untrusted restored
workspace content can cause the local ResearchPath process to read or write with
the operator's filesystem rights. This can select another run's analysis CSV,
create export artifacts outside the selected run, or replace a predictable ZIP
outside that run. We do not claim remote code execution, a cross-tenant escape,
or unconstrained arbitrary-file contents. The finding is P2/medium (CWE-22).

## Background

Normal model jobs use identifiers of the form `run_` followed by a generated
32-hex-character UUID, and save state below that run's directory
(`apps/api/app/services/analysis_jobs.py:123-148`). A completed model result is
also written to `projects/default/runs/<run_id>/result.json`, and the relative
path is persisted with the job (`apps/api/app/services/analysis_jobs.py:257-289`;
`apps/api/app/services/analysis_repository.py:18-45`). The intended ownership
boundary is consequently straightforward: one selected job owns one directory
below `projects/default/runs`.

Workspace backups preserve the SQLite database and workspace files, then restore
them as an internally consistent snapshot. Member-name validation prevents ZIP
extraction traversal, but it does not establish semantic agreement between a
database row, its referenced state JSON, and identifiers inside that JSON
(`apps/api/app/services/workspace_archive.py:117-179`). Those restored values
must be treated as untrusted when they are converted back into filesystem paths.

The export route selects a row with the URL `run_id`, receives the restored
state, and calls `create_export_bundle` without carrying the selected identity
forward (`apps/api/app/api/routes/analyses.py:95-108`). The repository query is
parameterized, but it returns the JSON named by the row's `state_path` without
rebinding the JSON's `id` (`apps/api/app/services/analysis_repository.py:138-145`).
Thus SQL parameterization protects query syntax, not run ownership.

## Vulnerability Details

We first select the job through `analysis_job_manager.get(run_id)`. At this
point the route knows the authoritative requested identity, while the returned
`state["id"]` is restored data. Because the service signature accepts only
`state`, the distinction is lost (`apps/api/app/services/export_bundle.py:208-213`).

If the state does not embed its result, the service joins its persisted
`resultPath` directly to `state_root` and reads it when present
(`apps/api/app/services/export_bundle.py:214-219`). It then repeats the restored
`id` across independent authorities:

```python
export_dir = settings.state_root / "projects" / "default" / "runs" / state["id"] / "exports"
export_dir.mkdir(parents=True, exist_ok=True)
target = export_dir / f"{state['id']}-{suffix}.zip"
with tempfile.TemporaryDirectory(..., dir=export_dir) as temporary:
    root = Path(temporary) / f"{state['id']}-export"
```

This is the decisive transition (`apps/api/app/services/export_bundle.py:228-234`).
On Windows, absolute, rooted, separator-bearing, and parent-bearing path
components can change the meaning of a `Path` join. Appending `-export` or
`.zip` does not make an identifier safe because separators remain meaningful.
We therefore carry restored data into directory creation, staging placement,
and the final target without equality, identifier-shape, resolved-containment,
or reparse-point checks.

With `include_data=true`, the same value selects either the run-root CSV or its
`work` fallback before `copy2` packages it (`apps/api/app/services/export_bundle.py:289-296`).
Finally, `os.replace` moves the generated archive to the derived target
(`apps/api/app/services/export_bundle.py:315-317`). The archive member walk is
root-relative, and `TemporaryDirectory` randomizes a name, but both controls
operate only after their parent and child roots have been selected from the
untrusted identifier. They do not restore ownership.

The violated invariant is: **the route-selected, canonical run ID is the sole
authority for export filesystem selection; every state-derived result, data,
staging, and destination path must resolve within that run's owned directory.**

## Exploitability Analysis

The strongest practical route begins with a workspace snapshot whose valid job
row is reachable through a requested run ID but whose restored state carries a
different or path-shaped `id`. The state must still describe a succeeded job and
reference model, dataset, and measurement objects that pass the service's normal
lookups (`apps/api/app/services/export_bundle.py:221-227`). These requirements
make this a restore-boundary issue rather than an unauthenticated Internet path.

For confidentiality, we request an export with data enabled and arrange for the
derived source to identify an existing CSV. We gain only the file that the
service expects at its fixed `analysis-data.csv` location; this is not a general
read-any-file primitive. For integrity, export creation and the final atomic
replace can reach derived locations using predictable suffixes. The generated
ZIP contents are application-produced, so this is not a general attacker-chosen
byte write. Availability follows where an existing predictable ZIP can be
replaced or filesystem clutter created.

Several constraints temper severity. The API is intended for loopback use, the
attacker first needs the operator to restore externally authored content, and
the process has only that operator's OS permissions. `include_data` is explicit
for the cross-run CSV route. Valid linked metadata and a succeeded state are
also required. Conversely, the no-data path still reaches directory creation
and archive replacement, so disabling data inclusion is not a complete
mitigation. ZIP CRC/hash checks and safe member extraction verify archive
integrity and extraction names; they do not validate semantic identities inside
the restored database and JSON.

## Proof of Concept

No exploit program is distributed. The companion `poc/README.md` defines a
harmless unit-test design that uses only pytest temporary directories, sentinel
files, and pre-I/O spies. It demonstrates the security invariant without
writing outside the test-owned temporary root or packaging unrelated user data.

From the repository root, the intended command after the remediation and tests
are implemented is:

```sh
python -m pytest apps/api/tests/test_export_bundle_security.py -q
```

The expected result is a passing identity-mismatch test, path-shaped-ID test,
owned-data selection test, canonical-result test, and destination-containment
test. This is expected output, not output I observed:

```text
5 passed
```

The README also requires assertions that rejection happens before repository or
filesystem side effects and that all canaries outside the owned run remain
unchanged. No cleanup beyond pytest's temporary-directory disposal is needed.

## Remediation

Bind identity at the route/service boundary, validate the canonical generated ID
shape, and derive every export path from one resolved owned run root. Do not use
`state["id"]` or `state["resultPath"]` as independent path authorities. A minimal
defensive shape is:

```python
RUN_ID = re.compile(r"run_[0-9a-f]{32}\Z")

def _owned_run_root(settings: Settings, requested_id: str, state: dict[str, Any]) -> Path:
    if state.get("id") != requested_id or RUN_ID.fullmatch(requested_id) is None:
        raise ValueError("AnalysisRun identity mismatch")
    runs = (settings.state_root / "projects" / "default" / "runs").resolve()
    owned = (runs / requested_id).resolve()
    if owned.parent != runs:
        raise ValueError("AnalysisRun path escapes runs root")
    return owned

def create_export_bundle(requested_id, state, repository, settings, include_data):
    run_root = _owned_run_root(settings, requested_id, state)
    result_path = run_root / "result.json"
    export_dir = run_root / "exports"
    data_candidates = (run_root / "analysis-data.csv", run_root / "work" / "analysis-data.csv")
    # Stage and replace only below export_dir; use requested_id only after validation.
```

The route must call `create_export_bundle(run_id, state, ...)`. Each candidate
should be resolved immediately before use, rejected unless it is relative to
`run_root`, and rejected if an existing path component is a symlink or Windows
reparse point. The staging directory, archive source, and final destination must
likewise be checked as descendants of `export_dir`. Prefer constant filenames
inside the owned root; if the run ID appears in a name, use only the validated
requested ID. Perform these checks before model/dataset lookups so invalid state
cannot trigger secondary work.

Regression tests should cover mismatched IDs, matching but path-shaped IDs,
absolute/drive/rooted forms on Windows, both CSV candidates, a foreign-run-only
CSV, a forged `resultPath`, reparse/symlink components where supported, and the
final `os.replace` target. A normal generated ID must still export with and
without data. Route coverage must prove that the requested ID reaches the
service as a separate argument. The detailed harmless design is in
`poc/README.md`.

## Summary

The export path confuses restored state identity with the database row selected
by the request. We traced that confusion from the route through result loading,
directory and temporary-root creation, optional CSV copying, and final archive
replacement. In the supported deployment, this gives an untrusted backup author
local research-data and filesystem impact under the operator's rights, with
important preconditions and fixed-content constraints that keep the rating at
medium.

The durable fix is one ownership invariant, not a collection of filename
filters: bind `state.id` to the requested canonical run ID, construct one owned
run root, and prove every derived read and write remains beneath it. Future
review should apply the same identity-to-root rule wherever restored row paths
or JSON identifiers are converted into filesystem authority, without treating
those separate call sites as part of this finding.
