**SEC-B03-04 — Export result path is not bound to its analysis run**

## Executive Summary

ResearchPath restores persisted analysis-job state and later lets a local user export a completed run. For a model run, normal execution writes `result.json` below `projects/default/runs/<run-id>/` and persists a workspace-relative `resultPath` (`apps/api/app/services/analysis_repository.py:11-43`, `apps/api/app/services/analysis_jobs.py:274-289`). The exporter does not re-establish that ownership relationship. If the inline result is absent, it joins the restored string to `state_root` and reads the resulting path without resolving it or checking that it remains inside the requested run directory (`apps/api/app/services/export_bundle.py:208-219`).

An author of a malicious or corrupted workspace backup can therefore make a later export include a schema-compatible JSON document from elsewhere readable by the ResearchPath process. The resulting ZIP exposes that document as `result-bundle.json` and derives report content from it (`apps/api/app/services/export_bundle.py:235-259`). This is a local, restore-mediated confidentiality issue, rated medium: supported deployments listen only on loopback, the process has the current user's filesystem rights, and exploitation requires the operator to restore untrusted workspace content and request export (`README.md:163-169`, `scripts/dev.ps1:15-17`). It is not a general arbitrary-file disclosure because the target must be valid JSON and must contain the fields consumed during bundle construction.

I statically reviewed the supplied unversioned source snapshot and the finding evidence. The checkout has no resolvable Git `HEAD`; no fixed revision was supplied. I did not execute a trigger, create an exploit, or run the proposed tests.

## Background

Each model analysis receives a generated `run_<uuid>` identifier. Its state is saved at `projects/default/runs/<run-id>/state.json` (`apps/api/app/services/analysis_jobs.py:74-86`, `apps/api/app/services/analysis_jobs.py:123-146`). After successful execution, `record_analysis_result` writes the result to the same run directory and returns that path; the job manager serializes it relative to `state_root` (`apps/api/app/services/analysis_repository.py:11-43`, `apps/api/app/services/analysis_jobs.py:274-289`). The normal ownership invariant is therefore:

```text
resolved result path == resolved(state_root/projects/default/runs/<state.id>/result.json)
```

The backup verifier protects ZIP extraction paths and verifies manifest hashes, CRCs, and membership, but it does not validate the meaning of paths stored inside restored JSON or SQLite records (`apps/api/app/services/workspace_archive.py:117-180`). This distinction matters: safe archive extraction prevents a ZIP member from escaping during restore, but a restored `resultPath` can still direct a later filesystem read elsewhere.

The GET export route loads the persisted job state and passes it directly to `create_export_bundle`, then returns the resulting ZIP (`apps/api/app/api/routes/analyses.py:95-113`). Mutation-token middleware applies only to POST, PUT, PATCH, and DELETE, so the export GET itself does not require that token (`apps/api/app/main.py:52-63`).

## Vulnerability Details

We first reach `AnalysisRepositoryMixin.get_analysis_job`, which reads the job state referenced by the database and returns its JSON without semantic validation of `resultPath` (`apps/api/app/services/analysis_repository.py:138-145`). The route carries this dictionary into the exporter.

Inside `create_export_bundle`, we then reach the decisive transition:

```python
state = dict(state)
if not state.get("result") and state.get("resultPath"):
    result_path = settings.state_root / state["resultPath"]
    if result_path.exists():
        from app.services.repository_io import _read_json_safe
        state["result"] = _read_json_safe(result_path)
```

`apps/api/app/services/export_bundle.py:214-219`

There is no rejection of an absolute path, `..` component, symlink/junction escape, or path belonging to another run. On Windows, an absolute right-hand operand can replace the earlier base; relative traversal can also leave it. `_read_json_safe` merely reads UTF-8 text and parses JSON, retrying permission failures; it performs no authorization or containment check (`apps/api/app/services/repository_io.py:33-41`).

Only after that read does the exporter require `status == "succeeded"` and a truthy result (`apps/api/app/services/export_bundle.py:221-222`). Those are state and format conditions, not path authorization. If the external JSON supplies the result fields used by `_report_markdown`—notably `run` and `sampleFlow`—bundle creation continues (`apps/api/app/services/export_bundle.py:181-205`). We finally carry the entire loaded object into `_json(root / "result-bundle.json", state["result"])`, making its contents downloadable (`apps/api/app/services/export_bundle.py:235-259`).

## Exploitability Analysis

The strongest realistic route is a malicious backup authored by someone who knows that the recipient uses ResearchPath. We can place a succeeded job state in the restored workspace, omit its inline `result`, and store a `resultPath` that resolves outside that run's directory. When the operator opens that run and requests export, the localhost service reads with the operator's OS permissions and packages compatible content.

Several constraints materially limit impact. The attacker does not gain a remote listener or additional filesystem permissions; the service is documented as personal and loopback-only (`README.md:163-169`). The operator must restore or otherwise accept corrupted persistence, and a normal export must be requested. The target must be readable UTF-8 JSON and structurally compatible enough to survive report and figure generation. Plaintext documents, binary files, malformed JSON, or incomplete objects normally cause export failure rather than disclosure (`apps/api/app/services/repository_io.py:33-41`, `apps/api/app/services/export_bundle.py:181-259`).

An absolute path and a `..`-based relative path are equivalent authorization failures, while a symlink or Windows junction inside the run tree shows why lexical prefix checks alone are insufficient. Cross-run references are also invalid even though both paths remain under `state_root`: the security property is ownership by the requested run, not merely workspace containment. The validated primitive is read-and-package of compatible JSON; this review does not establish code execution, arbitrary binary disclosure, privilege escalation, overwrite, or public-network exposure.

## Proof of Concept

No exploit is included. The accompanying `poc/README.md` specifies a harmless unit-level regression test that uses only temporary directories and synthetic sentinel JSON. We would construct a normal-looking succeeded state, point `resultPath` to a compatible sentinel outside the owned run directory, call `create_export_bundle`, and assert fail-closed behavior before any archive is returned.

The design covers absolute-path, dot-dot, cross-run, and resolved-link/junction cases, plus one legitimate in-run control. Expected vulnerable behavior is that the negative case can produce a ZIP whose `result-bundle.json` contains the external sentinel. Expected fixed behavior is a deterministic `ValueError` (translated by the route to HTTP 409) and no export artifact (`apps/api/app/api/routes/analyses.py:101-115`). I did not run these cases; the README intentionally contains test design rather than executable trigger code.

## Remediation

Restore this invariant before any existence check or read: a model run's resolved result path must be the canonical result file owned by that same resolved run directory. Reject absolute, traversing, cross-run, and reparse-point escapes. A narrowly scoped defensive shape is:

```python
run_root = (
    settings.state_root / "projects" / "default" / "runs" / state["id"]
).resolve()
result_path = (settings.state_root / state["resultPath"]).resolve()
expected = (run_root / "result.json").resolve()
if result_path != expected or not result_path.is_relative_to(run_root):
    raise ValueError("Analysis result path is outside its owned run directory")
state["result"] = _read_json_safe(result_path)
```

The equality check matches the file layout created by `record_analysis_result` (`apps/api/app/services/analysis_repository.py:11-43`); the containment check makes the ownership rule explicit. Perform this validation before `exists()` so error behavior does not become an external-path existence oracle. Centralizing persisted-path parsing would also prevent loaders from silently diverging; the repository already demonstrates resolved containment before destructive cleanup (`apps/api/app/services/analysis_repository.py:109-136`).

Regression tests should verify: the canonical in-run result still exports; absolute and `..` paths fail; another run's valid result fails; a symlink or Windows junction resolving outside fails where the platform permits creating it; missing and malformed in-run results retain their intended errors; and rejection leaves no ZIP. A route-level test should confirm HTTP 409 and no leaked sentinel, while a service-level test should assert the read is never attempted for an unauthorized path.

## Summary

SEC-B03-04 is a missing ownership check at a persisted-path trust boundary. We begin with externally restorable state, carry its unvalidated `resultPath` into a filesystem read, and then copy the parsed object into a downloadable export. The realistic impact is bounded disclosure of schema-compatible JSON readable by the local user's process after an untrusted restore and explicit export action.

Binding the resolved path to `projects/default/runs/<state.id>/result.json` closes absolute, traversal, cross-run, and resolved-link variants while preserving the normal write/read contract. The proposed temporary-directory regression matrix demonstrates that invariant without touching real user data or providing an operational exploit.
