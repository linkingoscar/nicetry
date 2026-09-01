## Executive Summary

ResearchPath restores `analysis_runs.result_path` from SQLite and later treats
that persisted string as authority for the file returned for a requested run.
The lookup is correctly parameterized by `run_id`, but the selected path is
neither required to be relative nor bound to that run's owned directory before
it reaches a JSON file read. A maliciously authored backup, corrupted workspace,
or other persisted-metadata modification can therefore substitute another
run's result. It can also attempt to read a JSON document outside the workspace
with the ResearchPath process's filesystem permissions.

The affected version is the unversioned source snapshot reviewed on
2026-07-15. No repository revision or fixing revision was available, so the
introduction date and affected release range are unknown. I performed a static
review of that snapshot's relevant source files; I did not modify a workspace
database, execute a path-redirection trigger, or test a patched build.

This is a Medium (P2) local-workspace issue. The most reliable impact is local
research-result integrity: a requested run can be made to return another run's
structurally valid result. Confidentiality
impact is narrower than arbitrary-file read because the target must be readable
text, valid JSON, and compatible with the result response model to be returned
successfully. The supported service is loopback-only and runs with the current
user's rights, so this finding does not establish remote code execution,
privilege escalation, cross-tenant access, or a public-network attack.

## Background

Normal model-result persistence gives each generated run a predictable owned
file: `projects/default/runs/<run_id>/result.json`. The repository derives that
location from the result's run identifier, writes JSON atomically, and stores a
workspace-relative representation in SQLite
(`apps/api/app/services/analysis_repository.py:11-28`,
`apps/api/app/services/analysis_repository.py:32-45`). We can state the intended
object-binding invariant directly: the row whose primary key is `run_id` may
refer only to the canonical `result.json` inside that same run's directory.

SQLite stores `result_path` as unconstrained `TEXT`; the schema does not encode
that invariant (`apps/api/app/services/database_migrations.py:86-95`). Backups
include a snapshot of `metadata.sqlite3`, and restore reconstructs registered
archive members in a new workspace (`apps/api/app/services/workspace_archive.py:39-43`,
`apps/api/app/services/workspace_archive.py:161-183`). Archive member checks
prevent ZIP traversal and hashes detect accidental or uncoordinated tampering,
but a self-consistent externally authored archive can still carry internally
untrusted SQLite values. Integrity of the container is not authorization for
every filesystem reference stored inside it.

The read is reachable through `GET /api/v1/analyses/{run_id}/result`, which
passes the requested identifier through the job manager to the repository
(`apps/api/app/api/routes/analyses.py:125-137`,
`apps/api/app/services/analysis_jobs.py:379-388`). The documented deployment is
local-first and listens on `127.0.0.1` (`docs/01-产品需求文档.md:117-123`,
`scripts/dev.ps1:14-17`). That limits exposure, but it does not make restored
metadata trustworthy: the process reads files with the local operator's
authority.

## Vulnerability Details

We first reach `get_analysis_result(run_id)`. Its SQL statement selects exactly
one row by identifier, which prevents SQL injection and row confusion at the
query layer. After the fetch, however, the code joins `state_root` with the
stored `result_path` and immediately reads the resulting path
(`apps/api/app/services/analysis_repository.py:49-57`):

```python
row = connection.execute(
    "SELECT result_path FROM analysis_runs WHERE id = ?", (run_id,)
).fetchone()
...
path = self.settings.state_root / row["result_path"]
return _read_json_safe(path)
```

The missing decision is whether `row["result_path"]` names the requested run's
owned result object. We carry the persisted value directly into `Path` joining.
An absolute path can supersede the left operand on the applicable platform;
`..` components can leave the workspace; and a normal relative path can select
another run. Even a lexical prefix check would be insufficient because a
symlink or Windows reparse point can change the resolved target.

The sink does not supply a compensating control. `_read_json_safe` retries
permission failures and performs `json.loads(path.read_text(...))`; it does not
authorize or schema-bind the path (`apps/api/app/services/repository_io.py:33-41`).
The route's response union requires result fields, but its base response model
allows extra fields (`apps/api/app/api/responses.py:8-10`,
`apps/api/app/api/responses.py:86-92`,
`apps/api/app/api/responses.py:129-144`). Thus response validation constrains
which outside JSON is useful, but it does not repair the filesystem boundary.

A concrete bad state is a row `id = run_A` whose `result_path` names
`projects/default/runs/run_B/result.json`. The request and SQL row still say
`run_A`, while the bytes come from `run_B`. The same primitive can point beyond
`state_root`; success then depends on filesystem access and response-compatible
JSON. Normal writes cannot create this mismatch because they derive and
relativize the path, but restored state must be validated again at every read.

## Exploitability Analysis

The strongest practical route is cross-run substitution. If an external backup
author can prepare a self-consistent workspace whose database maps `run_A` to
`run_B`'s result, both files are already valid ResearchPath bundles. We avoid
the uncertainty of guessing local filesystem layout, JSON encoding, or response
shape, and the result endpoint can present a valid but misattributed analysis.
This can affect conclusions, reports, or decisions made from the requested run,
although the reviewed path does not itself persist a new result or execute data.

An out-of-workspace read is possible at the file-access layer, but its useful
disclosure conditions are tighter. We need a predictable path readable by the
current OS user, UTF-8 text, valid JSON, and the required fields for one member
of the response union. A generic credential file, database, binary document, or
arbitrary text file normally fails before a successful API response. A crafted
result-shaped JSON already present outside the workspace, or another local
application's compatible JSON, is more plausible. Because extra response fields
are allowed, compatible documents may expose more than the minimum model fields,
but this review does not establish a particular sensitive target.

Parent traversal, absolute paths, sibling-run paths, and symlink/reparse escapes
are variants of the same broken binding, not separate findings. Invalid or
unreadable targets can produce an error and local availability degradation, but
an actor able to author the restored database can already corrupt that workspace;
availability is therefore secondary. Loopback binding, mutation tokens for
write methods, CORS, and archive CRC/hash verification reduce other attack
surfaces but do not authenticate this GET's referenced filesystem object.

## Proof of Concept

The accompanying `poc/README.md` contains only harmless regression-test designs.
They use pytest temporary directories and synthetic, non-sensitive JSON. No test
touches a real user workspace, follows a live secret path, or packages a modified
backup. The safe-first suite should establish one positive case and reject four
negative classes: an absolute temporary path, `..` traversal, a sibling run's
result, and a symlink/reparse escape where the platform supports it.

From the report directory, the intended post-fix invocation is:

```text
cd poc
python -m pytest -q <implemented-test-module>
```

Representative fixed behavior is five passing unit tests, with every negative
case raising the repository's chosen invalid-persisted-path exception before
`_read_json_safe` is called. There is no build step or cleanup beyond pytest's
automatic temporary-directory removal. I did not execute these proposed tests,
because this assignment was limited to defensive source-review documentation
and did not authorize source changes.

## Remediation

Restore one invariant: for row `id = run_id`, the only authorized result object
is the resolved regular file
`<state_root>/projects/default/runs/<run_id>/result.json`, and it must remain
inside the resolved run directory. Reject malformed persisted state; do not
silently normalize it or fall back to whatever file it names.

A minimal defensive shape in `get_analysis_result` is:

```python
stored = Path(str(row["result_path"]))
expected_relative = (
    Path("projects") / "default" / "runs" / run_id / "result.json"
)
if stored.is_absolute() or stored != expected_relative:
    raise ValueError("analysis result path is not bound to the requested run")

state_root = self.settings.state_root.resolve()
runs_root = (state_root / "projects" / "default" / "runs").resolve()
run_root = (runs_root / run_id).resolve()
candidate = (state_root / stored).resolve(strict=True)
if run_root.parent != runs_root or candidate.parent != run_root:
    raise ValueError("analysis result path escapes the requested run")
return _read_json_safe(candidate)
```

The exact-path comparison binds logical identity; the resolved-parent checks
defend against traversal and link/reparse redirection. Production code should
also require a regular file and map validation failures to a controlled
repository/API error without echoing sensitive absolute paths. Centralizing this
logic in a small path-binding helper would let other restored path fields adopt
the same fail-closed rule. If a lower-privileged process can mutate workspace
links concurrently, stronger handle-relative opening is needed to close the
check/use race; the supported same-user model makes that additional hardening,
not a reason to omit the binding check.

Regression tests should verify canonical success; absolute and parent-relative
rejection; sibling-run rejection; symlink/reparse rejection; missing-file and
directory rejection; mixed separator/case behavior on Windows; and that the
read helper is never called after validation fails. A restore-level integration
test should load a self-consistent synthetic archive with a mismatched path and
confirm that requesting the run fails closed.

## Summary

ResearchPath scopes the database lookup to a requested run but delegates file
selection to restored `result_path` text. We traced that value from SQLite,
through unchecked path construction, to a UTF-8 JSON read and a loopback result
response. The most dependable consequence is substitution of another run's
valid result; compatible out-of-workspace JSON can also be read with the local
process's authority under narrower conditions.

Binding every row to its canonical resolved run-owned `result.json` restores
the intended separation and rejects absolute, traversal, sibling, and link-based
variants. The defensive unit-test matrix documents that invariant without
accessing sensitive data. Future variant review should examine other persisted
workspace paths at their read boundaries, while keeping those results separate
from this single analysis-result-path finding.
