# Security Review: nicetry

> Historical snapshot from 2026-07-15. Findings and coverage are preserved as audit evidence; current closure status is maintained in `../../debt-register.json` and current regression gates. Do not infer that an archived finding is still open or that later code was covered by this scan.

## Scope

Repository-wide source review with ranked runtime-surface coverage and candidate-local validation/attack-path analysis.

- Scan mode: repository
- Target kind: directory_snapshot
- Target ID: target_sha256_7c56d49d6ac59946cd6eaadcd9ee135b9fd4c7e47808b9ff4ee8e0aa3d56b6bf
- Snapshot digest: codex-security-snapshot/v1:sha256:84f0708884bd3f486d678820dcc356748dc2e402f5838748c6e2ea469fc88143
- Inventory strategy: repository
- Included paths: .
- Excluded paths: none
- Runtime or test status: Static source review; safe local validation artifacts only.
- Artifacts reviewed: artifacts/01_context/threat_model.md, artifacts/02_discovery/raw_candidates.jsonl, artifacts/05_findings/validation_summary.md, artifacts/05_findings/attack_path_analysis_report.md
- Scan context: Local-first statistical research application; imported archives and restored persisted values are untrusted.

Limitations and exclusions:
- Unversioned target snapshot; no live or external target testing.
- Severity is calibrated for loopback single-user deployment.

### Scan Summary

| Field | Value |
| --- | --- |
| Reportable findings | 11 |
| Severity mix | medium: 9, low: 2 |
| Confidence mix | high: 11 |
| Coverage | complete |
| Validation mode | repository-wide candidate ledger |

Canonical artifacts: `scan-manifest.json`, `findings.json`, and `coverage.json`. This report is a deterministic projection of those files.

## Threat Model

A local operator uses imported archives, restored SQLite state, export, recovery, and cleanup workflows. Untrusted archive authors and persisted values can cross the filesystem capability boundary.

### Assets

- Research datasets and metadata
- Analysis results and job state
- Workspace files and backup recoverability
- Process availability

### Trust Boundaries

- Untrusted archive or restored SQLite data to local operator filesystem
- Loopback API to local workspace state

### Attacker Capabilities

- Supply a malicious archive or restored metadata
- Trigger normal local restore, export, recovery, or cleanup workflows

### Security Objectives

- Contain all filesystem capabilities
- Bound resource work before allocation
- Preserve backup recoverability and cleanup safety

### Assumptions

- Single-user loopback deployment
- Operator invokes or accepts the imported artifact

## Findings

| Finding | Severity | Confidence | Detailed write-up |
| --- | --- | --- | --- |
| [Persisted analysis job state path is read without workspace containment](#finding-1) | medium | high | inline below |
| [Export bundle reads persisted resultPath without workspace containment](#finding-2) | medium | high | inline below |
| [Orphan cleanup does not bind the backup to the audited workspace snapshot](#finding-3) | medium | high | inline below |
| [Empirical cleanup containment permits deletion of the workspace root](#finding-4) | medium | high | inline below |
| [Windows archive member names escape the restore staging directory](#finding-5) | medium | high | inline below |
| [Restored dictionary path can escape the workspace and substitute type metadata](#finding-6) | medium | high | inline below |
| [Restored dataset manifest path can escape the workspace on read](#finding-7) | medium | high | inline below |
| [Persisted analysis result path is read without workspace containment](#finding-8) | medium | high | inline below |
| [Persisted run id controls export write roots and included-data source](#finding-9) | medium | high | inline below |
| [Backup verification decompresses unbounded archive members into memory](#finding-10) | low | high | inline below |
| [Unfinished-job recovery reads every persisted state path without containment](#finding-11) | low | high | inline below |

### Confidence Scale

| Label | Meaning |
| --- | --- |
| high | Direct evidence supports the finding with no material unresolved blocker. |
| medium | Evidence supports a plausible issue, but material runtime or reachability proof remains. |
| low | Evidence is incomplete and the item is retained only for explicit follow-up. |

<a id="finding-1"></a>

### [1] Persisted analysis job state path is read without workspace containment

| Field | Value |
| --- | --- |
| Severity | medium |
| Confidence | high |
| Confidence rationale | Candidate-local discovery, validation, and attack-path receipts agree on the input, missing control, and sink. |
| Category | Path traversal or resource boundary failure |
| CWE | CWE-22, CWE-73, CWE-639 |
| Affected lines | apps/api/app/services/analysis_repository.py:138, apps/api/app/services/analysis_repository.py:141, apps/api/app/services/analysis_repository.py:145, apps/api/app/services/analysis_repository.py:138 |

#### Summary

Out-of-workspace JSON ingestion or substituted job state can expose compatible state through consumers and corrupt job lifecycle decisions.

#### Root Cause

The selected job row is associated with run_id in SQL, but the path and loaded JSON are not constrained to the workspace or rebound to the requested job.

**Untrusted imported value** — `apps/api/app/services/analysis_repository.py:138`

The imported value is not a trusted generated capability.

```python
# imported archive or persisted value
```

**Uncontained operation** — `apps/api/app/services/analysis_repository.py:138`

The value reaches the security-relevant sink without containment or identity validation.

```python
# operation consumes the value without the required shared proof
```

#### Validation

No expected runs/\<run_id\>/state.json equality, safe-relative validator, or resolved containment check is present before line 145.

Validation method: static source trace and focused validation

**Untrusted imported value** — `apps/api/app/services/analysis_repository.py:138`

The imported value is not a trusted generated capability.

```python
# imported archive or persisted value
```

**Uncontained operation** — `apps/api/app/services/analysis_repository.py:138`

The value reaches the security-relevant sink without containment or identity validation.

```python
# operation consumes the value without the required shared proof
```

#### Dataflow

The canonical finding records the affected path at apps/api/app/services/analysis_repository.py:138, apps/api/app/services/analysis_repository.py:141, apps/api/app/services/analysis_repository.py:145, apps/api/app/services/analysis_repository.py:138, but no expanded source-to-sink narrative was recorded.

**Untrusted imported value** — `apps/api/app/services/analysis_repository.py:138`

The imported value is not a trusted generated capability.

```python
# imported archive or persisted value
```

**Uncontained operation** — `apps/api/app/services/analysis_repository.py:138`

The value reaches the security-relevant sink without containment or identity validation.

```python
# operation consumes the value without the required shared proof
```

#### Reachability

Reachability was not recorded beyond the canonical finding summary and affected locations.

#### Severity

**Medium** — Direct source, validation, and attack-path evidence support the calibrated local impact.

Broader exposed reach would raise severity; a proven unreachable persisted boundary would lower it.

#### Remediation

The missing-row check at lines 143-144 proves existence of a database row, not safety or identity of its referenced file.

Tests:
- Reject escape, wrong identity, root-equal, and over-budget inputs before side effects.
- Run the original candidate regression under a temporary workspace.

Preventive controls:
- Centralize safe path, identity, and archive-budget validation.

<a id="finding-2"></a>

### [2] Export bundle reads persisted resultPath without workspace containment

| Field | Value |
| --- | --- |
| Severity | medium |
| Confidence | high |
| Confidence rationale | Candidate-local discovery, validation, and attack-path receipts agree on the input, missing control, and sink. |
| Category | Path traversal or resource boundary failure |
| CWE | CWE-22, CWE-73 |
| Affected lines | apps/api/app/api/routes/analyses.py:95, apps/api/app/services/export_bundle.py:216, apps/api/app/services/export_bundle.py:219, apps/api/app/services/export_bundle.py:208 |

#### Summary

A malicious restored run can make export read a schema-compatible result JSON outside the workspace and package its contents into report files and result-bundle.json for download.

#### Root Cause

The exporter assumes the persisted path is safe and does not use the workspace safe-relative/containment helper before reading.

**Untrusted imported value** — `apps/api/app/api/routes/analyses.py:95`

The imported value is not a trusted generated capability.

```python
# imported archive or persisted value
```

**Uncontained operation** — `apps/api/app/services/export_bundle.py:208`

The value reaches the security-relevant sink without containment or identity validation.

```python
# operation consumes the value without the required shared proof
```

#### Validation

No call to resolve/is_relative_to or an expected run-directory helper appears between state\[resultPath\] and _read_json_safe. The later succeeded/result checks only occur after the external JSON has been read.

Validation method: static source trace and focused validation

**Untrusted imported value** — `apps/api/app/api/routes/analyses.py:95`

The imported value is not a trusted generated capability.

```python
# imported archive or persisted value
```

**Uncontained operation** — `apps/api/app/services/export_bundle.py:208`

The value reaches the security-relevant sink without containment or identity validation.

```python
# operation consumes the value without the required shared proof
```

#### Dataflow

The canonical finding records the affected path at apps/api/app/api/routes/analyses.py:95, apps/api/app/services/export_bundle.py:216, apps/api/app/services/export_bundle.py:219, apps/api/app/services/export_bundle.py:208, but no expanded source-to-sink narrative was recorded.

**Untrusted imported value** — `apps/api/app/api/routes/analyses.py:95`

The imported value is not a trusted generated capability.

```python
# imported archive or persisted value
```

**Uncontained operation** — `apps/api/app/services/export_bundle.py:208`

The value reaches the security-relevant sink without containment or identity validation.

```python
# operation consumes the value without the required shared proof
```

#### Reachability

Reachability was not recorded beyond the canonical finding summary and affected locations.

#### Severity

**Medium** — Direct source, validation, and attack-path evidence support the calibrated local impact.

Broader exposed reach would raise severity; a proven unreachable persisted boundary would lower it.

#### Remediation

The state must describe a succeeded run and the result must satisfy the fields later accessed, but those are format constraints rather than path authorization. _read_json_safe limits file size/JSON shape but does not establish path containment at this call site.

Tests:
- Reject escape, wrong identity, root-equal, and over-budget inputs before side effects.
- Run the original candidate regression under a temporary workspace.

Preventive controls:
- Centralize safe path, identity, and archive-budget validation.

<a id="finding-3"></a>

### [3] Orphan cleanup does not bind the backup to the audited workspace snapshot

| Field | Value |
| --- | --- |
| Severity | medium |
| Confidence | high |
| Confidence rationale | Candidate-local discovery, validation, and attack-path receipts agree on the input, missing control, and sink. |
| Category | Path traversal or resource boundary failure |
| CWE | CWE-345, CWE-354 |
| Affected lines | scripts/workspace-maintenance.py:50, apps/api/app/services/workspace_maintenance.py:152, apps/api/app/services/workspace_maintenance.py:155, apps/api/app/services/workspace_maintenance.py:198 |

#### Summary

Cleanup can irreversibly delete orphaned research data while reporting backup coverage even though the supplied archive cannot restore the deleted current contents.

#### Root Cause

Cleanup verifies archive-internal hashes and then reduces the manifest to a filename set; it does not compare backup provenance, state root, database snapshot, or content hashes with the audit/current workspace.

**Untrusted imported value** — `scripts/workspace-maintenance.py:50`

The imported value is not a trusted generated capability.

```python
# imported archive or persisted value
```

**Uncontained operation** — `apps/api/app/services/workspace_maintenance.py:198`

The value reaches the security-relevant sink without containment or identity validation.

```python
# operation consumes the value without the required shared proof
```

#### Validation

Any valid archive containing the scheduled filenames passes missing_from_backup regardless of file bytes or which state_root produced it. verify_workspace_backup returns an archive hash but cleanup neither records nor compares it to the audit.

Validation method: static source trace and focused validation

**Untrusted imported value** — `scripts/workspace-maintenance.py:50`

The imported value is not a trusted generated capability.

```python
# imported archive or persisted value
```

**Uncontained operation** — `apps/api/app/services/workspace_maintenance.py:198`

The value reaches the security-relevant sink without containment or identity validation.

```python
# operation consumes the value without the required shared proof
```

#### Dataflow

The canonical finding records the affected path at scripts/workspace-maintenance.py:50, apps/api/app/services/workspace_maintenance.py:152, apps/api/app/services/workspace_maintenance.py:155, apps/api/app/services/workspace_maintenance.py:198, but no expanded source-to-sink narrative was recorded.

**Untrusted imported value** — `scripts/workspace-maintenance.py:50`

The imported value is not a trusted generated capability.

```python
# imported archive or persisted value
```

**Uncontained operation** — `apps/api/app/services/workspace_maintenance.py:198`

The value reaches the security-relevant sink without containment or identity validation.

```python
# operation consumes the value without the required shared proof
```

#### Reachability

Reachability was not recorded beyond the canonical finding summary and affected locations.

#### Severity

**Medium** — Direct source, validation, and attack-path evidence support the calibrated local impact.

Broader exposed reach would raise severity; a proven unreachable persisted boundary would lower it.

#### Remediation

The current logical DB hash is correctly compared to audit.databaseSha256, but no corresponding value is proved for the backup. Filename membership is not recovery proof.

Tests:
- Reject escape, wrong identity, root-equal, and over-budget inputs before side effects.
- Run the original candidate regression under a temporary workspace.

Preventive controls:
- Centralize safe path, identity, and archive-budget validation.

<a id="finding-4"></a>

### [4] Empirical cleanup containment permits deletion of the workspace root

| Field | Value |
| --- | --- |
| Severity | medium |
| Confidence | high |
| Confidence rationale | Candidate-local discovery, validation, and attack-path receipts agree on the input, missing control, and sink. |
| Category | Path traversal or resource boundary failure |
| CWE | CWE-22, CWE-73 |
| Affected lines | apps/api/app/services/analysis_repository.py:93, apps/api/app/services/analysis_repository.py:103, apps/api/app/services/analysis_repository.py:127, apps/api/app/services/analysis_repository.py:131, apps/api/app/services/analysis_repository.py:136 |

#### Summary

Cleanup can recursively delete the entire workspace root or an unrelated in-workspace subtree, causing broad loss of datasets, models, jobs, results, and metadata files.

#### Root Cause

report_root.is_relative_to(state_root) is true for the root itself, and report_root.name == report_id is merely consistency between two persisted attacker-controlled values; neither proves the expected reports subtree.

**Untrusted imported value** — `apps/api/app/services/analysis_repository.py:93`

The imported value is not a trusted generated capability.

```python
# imported archive or persisted value
```

**Uncontained operation** — `apps/api/app/services/analysis_repository.py:136`

The value reaches the security-relevant sink without containment or identity validation.

```python
# operation consumes the value without the required shared proof
```

#### Validation

The equality case is admitted because Path.is_relative_to returns true when both paths are equal. The normal-run branch explicitly excludes equality; the empirical branch does not and also lacks an expected-parent check.

Validation method: static source trace and focused validation

**Untrusted imported value** — `apps/api/app/services/analysis_repository.py:93`

The imported value is not a trusted generated capability.

```python
# imported archive or persisted value
```

**Uncontained operation** — `apps/api/app/services/analysis_repository.py:136`

The value reaches the security-relevant sink without containment or identity validation.

```python
# operation consumes the value without the required shared proof
```

#### Dataflow

The canonical finding records the affected path at apps/api/app/services/analysis_repository.py:93, apps/api/app/services/analysis_repository.py:103, apps/api/app/services/analysis_repository.py:127, apps/api/app/services/analysis_repository.py:131, apps/api/app/services/analysis_repository.py:136, but no expanded source-to-sink narrative was recorded.

**Untrusted imported value** — `apps/api/app/services/analysis_repository.py:93`

The imported value is not a trusted generated capability.

```python
# imported archive or persisted value
```

**Uncontained operation** — `apps/api/app/services/analysis_repository.py:136`

The value reaches the security-relevant sink without containment or identity validation.

```python
# operation consumes the value without the required shared proof
```

#### Reachability

Reachability was not recorded beyond the canonical finding summary and affected locations.

#### Severity

**Medium** — Direct source, validation, and attack-path evidence support the calibrated local impact.

Broader exposed reach would raise severity; a proven unreachable persisted boundary would lower it.

#### Remediation

The adjacent remove_known_directory helper at lines 111-118 is a safe negative control: it rejects state_root and requires the exact expected parent name runs. The empirical branch needs the same root inequality plus an exact approved reports parent/object binding.

Tests:
- Reject escape, wrong identity, root-equal, and over-budget inputs before side effects.
- Run the original candidate regression under a temporary workspace.

Preventive controls:
- Centralize safe path, identity, and archive-budget validation.

<a id="finding-5"></a>

### [5] Windows archive member names escape the restore staging directory

| Field | Value |
| --- | --- |
| Severity | medium |
| Confidence | high |
| Confidence rationale | Candidate-local discovery, validation, and attack-path receipts agree on the input, missing control, and sink. |
| Category | Path traversal or resource boundary failure |
| CWE | CWE-22, CWE-73 |
| Affected lines | scripts/workspace-archive.py:47, apps/api/app/services/workspace_archive.py:32, apps/api/app/services/workspace_archive.py:177 |

#### Summary

Overwrite or create arbitrary files writable by the user outside the chosen restore target, potentially including configuration or startup paths.

#### Root Cause

_safe_member_path uses PurePosixPath and rejects only POSIX absolute paths and an independent '..' part; restore joins those accepted parts into a Windows Path and opens it for writing without resolving and proving containment under staging.

**Untrusted imported value** — `scripts/workspace-archive.py:47`

The imported value is not a trusted generated capability.

```python
# imported archive or persisted value
```

**Uncontained operation** — `apps/api/app/services/workspace_archive.py:177`

The value reaches the security-relevant sink without containment or identity validation.

```python
# operation consumes the value without the required shared proof
```

#### Validation

Path('C:/stage').joinpath(\*PurePosixPath(r'\\Windows\\Temp\\owned').parts) resolves as a rooted Windows path; UNC and D: forms similarly discard the staging root. No resolved containment check precedes destination.open('wb').

Validation method: static source trace and focused validation

**Untrusted imported value** — `scripts/workspace-archive.py:47`

The imported value is not a trusted generated capability.

```python
# imported archive or persisted value
```

**Uncontained operation** — `apps/api/app/services/workspace_archive.py:177`

The value reaches the security-relevant sink without containment or identity validation.

```python
# operation consumes the value without the required shared proof
```

#### Dataflow

The canonical finding records the affected path at scripts/workspace-archive.py:47, apps/api/app/services/workspace_archive.py:32, apps/api/app/services/workspace_archive.py:177, but no expanded source-to-sink narrative was recorded.

**Untrusted imported value** — `scripts/workspace-archive.py:47`

The imported value is not a trusted generated capability.

```python
# imported archive or persisted value
```

**Uncontained operation** — `apps/api/app/services/workspace_archive.py:177`

The value reaches the security-relevant sink without containment or identity validation.

```python
# operation consumes the value without the required shared proof
```

#### Reachability

Reachability was not recorded beyond the canonical finding summary and affected locations.

#### Severity

**Medium** — Direct source, validation, and attack-path evidence support the calibrated local impact.

Broader exposed reach would raise severity; a proven unreachable persisted boundary would lower it.

#### Remediation

Manifest exact-name, CRC, size and SHA-256 checks prove archive consistency but not Windows destination containment. target_root nonexistence and final os.replace occur after the out-of-tree write.

Tests:
- Reject escape, wrong identity, root-equal, and over-budget inputs before side effects.
- Run the original candidate regression under a temporary workspace.

Preventive controls:
- Centralize safe path, identity, and archive-budget validation.

<a id="finding-6"></a>

### [6] Restored dictionary path can escape the workspace and substitute type metadata

| Field | Value |
| --- | --- |
| Severity | medium |
| Confidence | high |
| Confidence rationale | Candidate-local discovery, validation, and attack-path receipts agree on the input, missing control, and sink. |
| Category | Path traversal or resource boundary failure |
| CWE | CWE-22, CWE-639 |
| Affected lines | apps/api/app/api/routes/datasets.py:61, apps/api/app/services/dataset_repository.py:133, apps/api/app/services/dataset_repository.py:134, apps/api/app/services/dataset_repository.py:116 |

#### Summary

A restored workspace can make one dataset consume dictionary JSON outside the workspace or belonging to another dataset, corrupting confirmed variable types and potentially disclosing schema-compatible confirmedTypes values through the dataset response.

#### Root Cause

The dictionary row is associated by dataset_id/version in SQL, but the file path stored in that associated row is not constrained to the workspace or expected dataset subtree before opening.

**Untrusted imported value** — `apps/api/app/api/routes/datasets.py:61`

The imported value is not a trusted generated capability.

```python
# imported archive or persisted value
```

**Uncontained operation** — `apps/api/app/services/dataset_repository.py:116`

The value reaches the security-relevant sink without containment or identity validation.

```python
# operation consumes the value without the required shared proof
```

#### Validation

The parameterized SQL association is present, but no resolve/is_relative_to check precedes line 134 and no check compares dictionary.datasetVersionId or dictionary.version with the selected row before confirmedTypes is merged at lines 135-151.

Validation method: static source trace and focused validation

**Untrusted imported value** — `apps/api/app/api/routes/datasets.py:61`

The imported value is not a trusted generated capability.

```python
# imported archive or persisted value
```

**Uncontained operation** — `apps/api/app/services/dataset_repository.py:116`

The value reaches the security-relevant sink without containment or identity validation.

```python
# operation consumes the value without the required shared proof
```

#### Dataflow

The canonical finding records the affected path at apps/api/app/api/routes/datasets.py:61, apps/api/app/services/dataset_repository.py:133, apps/api/app/services/dataset_repository.py:134, apps/api/app/services/dataset_repository.py:116, but no expanded source-to-sink narrative was recorded.

**Untrusted imported value** — `apps/api/app/api/routes/datasets.py:61`

The imported value is not a trusted generated capability.

```python
# imported archive or persisted value
```

**Uncontained operation** — `apps/api/app/services/dataset_repository.py:116`

The value reaches the security-relevant sink without containment or identity validation.

```python
# operation consumes the value without the required shared proof
```

#### Reachability

Reachability was not recorded beyond the canonical finding summary and affected locations.

#### Severity

**Medium** — Direct source, validation, and attack-path evidence support the calibrated local impact.

Broader exposed reach would raise severity; a proven unreachable persisted boundary would lower it.

#### Remediation

The SQL query scopes dataset_id and version, and confirm_dictionary generates an internal relative path at lines 181-197. Those controls protect normal writes but do not validate the persisted path on read or bind the loaded JSON's datasetVersionId/version back to the selected row.

Tests:
- Reject escape, wrong identity, root-equal, and over-budget inputs before side effects.
- Run the original candidate regression under a temporary workspace.

Preventive controls:
- Centralize safe path, identity, and archive-budget validation.

<a id="finding-7"></a>

### [7] Restored dataset manifest path can escape the workspace on read

| Field | Value |
| --- | --- |
| Severity | medium |
| Confidence | high |
| Confidence rationale | Candidate-local discovery, validation, and attack-path receipts agree on the input, missing control, and sink. |
| Category | Path traversal or resource boundary failure |
| CWE | CWE-22, CWE-73 |
| Affected lines | apps/api/app/api/routes/datasets.py:61, apps/api/app/services/dataset_repository.py:121, apps/api/app/services/dataset_repository.py:122, apps/api/app/services/dataset_repository.py:116 |

#### Summary

After a crafted backup is restored and used as a workspace, a dataset GET can read a schema-compatible JSON file outside that workspace and expose its content as dataset metadata; it can also substitute another dataset manifest and silently corrupt object association.

#### Root Cause

The repository treats a database path as trusted and performs state_root / row\[manifest_path\] followed by read_text without resolving and proving containment.

**Untrusted imported value** — `apps/api/app/api/routes/datasets.py:61`

The imported value is not a trusted generated capability.

```python
# imported archive or persisted value
```

**Uncontained operation** — `apps/api/app/services/dataset_repository.py:116`

The value reaches the security-relevant sink without containment or identity validation.

```python
# operation consumes the value without the required shared proof
```

#### Validation

FastAPI supplies dataset_id to get_dataset (datasets.py:61-68); the database row supplies manifest_path (dataset_repository.py:107-122); pathlib joins are not followed by resolve/is_relative_to; read_text is the first filesystem enforcement point. Normal imports are safe by construction but do not constrain restored rows.

Validation method: static source trace and focused validation

**Untrusted imported value** — `apps/api/app/api/routes/datasets.py:61`

The imported value is not a trusted generated capability.

```python
# imported archive or persisted value
```

**Uncontained operation** — `apps/api/app/services/dataset_repository.py:116`

The value reaches the security-relevant sink without containment or identity validation.

```python
# operation consumes the value without the required shared proof
```

#### Dataflow

The canonical finding records the affected path at apps/api/app/api/routes/datasets.py:61, apps/api/app/services/dataset_repository.py:121, apps/api/app/services/dataset_repository.py:122, apps/api/app/services/dataset_repository.py:116, but no expanded source-to-sink narrative was recorded.

**Untrusted imported value** — `apps/api/app/api/routes/datasets.py:61`

The imported value is not a trusted generated capability.

```python
# imported archive or persisted value
```

**Uncontained operation** — `apps/api/app/services/dataset_repository.py:116`

The value reaches the security-relevant sink without containment or identity validation.

```python
# operation consumes the value without the required shared proof
```

#### Reachability

Reachability was not recorded beyond the canonical finding summary and affected locations.

#### Severity

**Medium** — Direct source, validation, and attack-path evidence support the calibrated local impact.

Broader exposed reach would raise severity; a proven unreachable persisted boundary would lower it.

#### Remediation

record_dataset uses Path.relative_to on normal application-generated writes at line 84, and maintenance audit has a separate _safe_relative_path helper, but no equivalent check is applied on this persisted read. Backup verification checks archive member names and hashes, not SQLite path-column semantics.

Tests:
- Reject escape, wrong identity, root-equal, and over-budget inputs before side effects.
- Run the original candidate regression under a temporary workspace.

Preventive controls:
- Centralize safe path, identity, and archive-budget validation.

<a id="finding-8"></a>

### [8] Persisted analysis result path is read without workspace containment

| Field | Value |
| --- | --- |
| Severity | medium |
| Confidence | high |
| Confidence rationale | Candidate-local discovery, validation, and attack-path receipts agree on the input, missing control, and sink. |
| Category | Path traversal or resource boundary failure |
| CWE | CWE-22, CWE-73 |
| Affected lines | apps/api/app/services/analysis_repository.py:49, apps/api/app/services/analysis_repository.py:52, apps/api/app/services/analysis_repository.py:56, apps/api/app/services/analysis_repository.py:57 |

#### Summary

A persisted run can ingest a JSON document outside the workspace or substitute another run's result, creating disclosure and analysis-object integrity risk in downstream consumers.

#### Root Cause

The SQL lookup scopes the row by run id but does not authorize the referenced filesystem object; no safe-relative, expected-subtree, resolve, or is_relative_to check precedes the read.

**Untrusted imported value** — `apps/api/app/services/analysis_repository.py:49`

The imported value is not a trusted generated capability.

```python
# imported archive or persisted value
```

**Uncontained operation** — `apps/api/app/services/analysis_repository.py:57`

The value reaches the security-relevant sink without containment or identity validation.

```python
# operation consumes the value without the required shared proof
```

#### Validation

No path normalization, resolved containment, registered-path equality, or expected runs/\<id\>/result.json binding occurs between the SQLite source and the read sink.

Validation method: static source trace and focused validation

**Untrusted imported value** — `apps/api/app/services/analysis_repository.py:49`

The imported value is not a trusted generated capability.

```python
# imported archive or persisted value
```

**Uncontained operation** — `apps/api/app/services/analysis_repository.py:57`

The value reaches the security-relevant sink without containment or identity validation.

```python
# operation consumes the value without the required shared proof
```

#### Dataflow

The canonical finding records the affected path at apps/api/app/services/analysis_repository.py:49, apps/api/app/services/analysis_repository.py:52, apps/api/app/services/analysis_repository.py:56, apps/api/app/services/analysis_repository.py:57, but no expanded source-to-sink narrative was recorded.

**Untrusted imported value** — `apps/api/app/services/analysis_repository.py:49`

The imported value is not a trusted generated capability.

```python
# imported archive or persisted value
```

**Uncontained operation** — `apps/api/app/services/analysis_repository.py:57`

The value reaches the security-relevant sink without containment or identity validation.

```python
# operation consumes the value without the required shared proof
```

#### Reachability

Reachability was not recorded beyond the canonical finding summary and affected locations.

#### Severity

**Medium** — Direct source, validation, and attack-path evidence support the calibrated local impact.

Broader exposed reach would raise severity; a proven unreachable persisted boundary would lower it.

#### Remediation

Parameterized SQL prevents SQL injection and normal writes record relative paths, but persisted values are explicitly untrusted under the threat model and must be revalidated on every read.

Tests:
- Reject escape, wrong identity, root-equal, and over-budget inputs before side effects.
- Run the original candidate regression under a temporary workspace.

Preventive controls:
- Centralize safe path, identity, and archive-budget validation.

<a id="finding-9"></a>

### [9] Persisted run id controls export write roots and included-data source

| Field | Value |
| --- | --- |
| Severity | medium |
| Confidence | high |
| Confidence rationale | Candidate-local discovery, validation, and attack-path receipts agree on the input, missing control, and sink. |
| Category | Path traversal or resource boundary failure |
| CWE | CWE-22, CWE-73, CWE-639 |
| Affected lines | apps/api/app/api/routes/analyses.py:95, apps/api/app/services/export_bundle.py:228, apps/api/app/services/export_bundle.py:233, apps/api/app/services/export_bundle.py:290, apps/api/app/services/export_bundle.py:317 |

#### Summary

A crafted restored run can escape the intended runs directory, leave generated files outside the temporary tree, overwrite a fixed-name ZIP outside the workspace, or package an analysis-data.csv from another run/location when include_data=true.

#### Root Cause

create_export_bundle repeatedly treats persisted state.id as a trusted filesystem identifier for directory creation, temporary-root placement, data selection and final archive replacement.

**Untrusted imported value** — `apps/api/app/api/routes/analyses.py:95`

The imported value is not a trusted generated capability.

```python
# imported archive or persisted value
```

**Uncontained operation** — `apps/api/app/services/export_bundle.py:317`

The value reaches the security-relevant sink without containment or identity validation.

```python
# operation consumes the value without the required shared proof
```

#### Validation

No internal ID regex, equality check with run_id, resolve/is_relative_to check, or generated-directory helper protects any state.id use. On Windows, backslash/drive-qualified state.id values carry path semantics at each join.

Validation method: static source trace and focused validation

**Untrusted imported value** — `apps/api/app/api/routes/analyses.py:95`

The imported value is not a trusted generated capability.

```python
# imported archive or persisted value
```

**Uncontained operation** — `apps/api/app/services/export_bundle.py:317`

The value reaches the security-relevant sink without containment or identity validation.

```python
# operation consumes the value without the required shared proof
```

#### Dataflow

The canonical finding records the affected path at apps/api/app/api/routes/analyses.py:95, apps/api/app/services/export_bundle.py:228, apps/api/app/services/export_bundle.py:233, apps/api/app/services/export_bundle.py:290, apps/api/app/services/export_bundle.py:317, but no expanded source-to-sink narrative was recorded.

**Untrusted imported value** — `apps/api/app/api/routes/analyses.py:95`

The imported value is not a trusted generated capability.

```python
# imported archive or persisted value
```

**Uncontained operation** — `apps/api/app/services/export_bundle.py:317`

The value reaches the security-relevant sink without containment or identity validation.

```python
# operation consumes the value without the required shared proof
```

#### Reachability

Reachability was not recorded beyond the canonical finding summary and affected locations.

#### Severity

**Medium** — Direct source, validation, and attack-path evidence support the calibrated local impact.

Broader exposed reach would raise severity; a proven unreachable persisted boundary would lower it.

#### Remediation

The database lookup for run_id is parameterized, TemporaryDirectory provides safe randomness only after its parent has already been selected, and archive members are generated from a fresh root. None of those controls check state.id == route run_id or constrain its filesystem interpretation.

Tests:
- Reject escape, wrong identity, root-equal, and over-budget inputs before side effects.
- Run the original candidate regression under a temporary workspace.

Preventive controls:
- Centralize safe path, identity, and archive-budget validation.

<a id="finding-10"></a>

### [10] Backup verification decompresses unbounded archive members into memory

| Field | Value |
| --- | --- |
| Severity | low |
| Confidence | high |
| Confidence rationale | Candidate-local discovery, validation, and attack-path receipts agree on the input, missing control, and sink. |
| Category | Path traversal or resource boundary failure |
| CWE | CWE-409, CWE-770 |
| Affected lines | apps/api/app/services/workspace_archive.py:162, apps/api/app/services/workspace_archive.py:130, apps/api/app/services/workspace_archive.py:142 |

#### Summary

Memory and CPU exhaustion during verify, restore, drill, or maintenance backup verification, aborting the local process and requiring manual recovery.

#### Root Cause

verify_workspace_backup has no compressed-size, uncompressed-size, member-count, or compression-ratio ceilings; testzip decompresses the archive and archive.read(member) materializes each full member before semantic size/hash rejection.

**Untrusted imported value** — `apps/api/app/services/workspace_archive.py:162`

The imported value is not a trusted generated capability.

```python
# imported archive or persisted value
```

**Uncontained operation** — `apps/api/app/services/workspace_archive.py:142`

The value reaches the security-relevant sink without containment or identity validation.

```python
# operation consumes the value without the required shared proof
```

#### Validation

restore_workspace_backup always invokes verification. ZipFile.read returns the full uncompressed member, so manifest values cannot prevent allocation; testzip also imposes attacker-selected decompression CPU.

Validation method: static source trace and focused validation

**Untrusted imported value** — `apps/api/app/services/workspace_archive.py:162`

The imported value is not a trusted generated capability.

```python
# imported archive or persisted value
```

**Uncontained operation** — `apps/api/app/services/workspace_archive.py:142`

The value reaches the security-relevant sink without containment or identity validation.

```python
# operation consumes the value without the required shared proof
```

#### Dataflow

The canonical finding records the affected path at apps/api/app/services/workspace_archive.py:162, apps/api/app/services/workspace_archive.py:130, apps/api/app/services/workspace_archive.py:142, but no expanded source-to-sink narrative was recorded.

**Untrusted imported value** — `apps/api/app/services/workspace_archive.py:162`

The imported value is not a trusted generated capability.

```python
# imported archive or persisted value
```

**Uncontained operation** — `apps/api/app/services/workspace_archive.py:142`

The value reaches the security-relevant sink without containment or identity validation.

```python
# operation consumes the value without the required shared proof
```

#### Reachability

Reachability was not recorded beyond the canonical finding summary and affected locations.

#### Severity

**Low** — Direct source, validation, and attack-path evidence support the calibrated local impact.

Broader exposed reach would raise severity; a proven unreachable persisted boundary would lower it.

#### Remediation

CRC, manifest size and SHA-256 validate integrity only after decompression. They do not cap work or allocation.

Tests:
- Reject escape, wrong identity, root-equal, and over-budget inputs before side effects.
- Run the original candidate regression under a temporary workspace.

Preventive controls:
- Centralize safe path, identity, and archive-budget validation.

<a id="finding-11"></a>

### [11] Unfinished-job recovery reads every persisted state path without containment

| Field | Value |
| --- | --- |
| Severity | low |
| Confidence | high |
| Confidence rationale | Candidate-local discovery, validation, and attack-path receipts agree on the input, missing control, and sink. |
| Category | Path traversal or resource boundary failure |
| CWE | CWE-22, CWE-73, CWE-754 |
| Affected lines | apps/api/app/services/analysis_repository.py:147, apps/api/app/services/analysis_repository.py:151, apps/api/app/services/analysis_repository.py:156, apps/api/app/services/analysis_repository.py:147 |

#### Summary

Recovery can ingest an out-of-workspace JSON object, substitute active job state, or fail the entire unfinished-job load on one hostile path/document.

#### Root Cause

Status filtering limits which rows are read but does not constrain their filesystem paths, bind state.id back to the row, or isolate failures per job.

**Untrusted imported value** — `apps/api/app/services/analysis_repository.py:147`

The imported value is not a trusted generated capability.

```python
# imported archive or persisted value
```

**Uncontained operation** — `apps/api/app/services/analysis_repository.py:147`

The value reaches the security-relevant sink without containment or identity validation.

```python
# operation consumes the value without the required shared proof
```

#### Validation

Every selected value reaches the read sink with no resolved-root or expected-run-directory check; the list comprehension also lacks per-row error handling.

Validation method: static source trace and focused validation

**Untrusted imported value** — `apps/api/app/services/analysis_repository.py:147`

The imported value is not a trusted generated capability.

```python
# imported archive or persisted value
```

**Uncontained operation** — `apps/api/app/services/analysis_repository.py:147`

The value reaches the security-relevant sink without containment or identity validation.

```python
# operation consumes the value without the required shared proof
```

#### Dataflow

The canonical finding records the affected path at apps/api/app/services/analysis_repository.py:147, apps/api/app/services/analysis_repository.py:151, apps/api/app/services/analysis_repository.py:156, apps/api/app/services/analysis_repository.py:147, but no expanded source-to-sink narrative was recorded.

**Untrusted imported value** — `apps/api/app/services/analysis_repository.py:147`

The imported value is not a trusted generated capability.

```python
# imported archive or persisted value
```

**Uncontained operation** — `apps/api/app/services/analysis_repository.py:147`

The value reaches the security-relevant sink without containment or identity validation.

```python
# operation consumes the value without the required shared proof
```

#### Reachability

Reachability was not recorded beyond the canonical finding summary and affected locations.

#### Severity

**Low** — Direct source, validation, and attack-path evidence support the calibrated local impact.

Broader exposed reach would raise severity; a proven unreachable persisted boundary would lower it.

#### Remediation

The WHERE status allowlist is a lifecycle control, not a path authorization control; the comprehension lacks safe-relative validation and per-entry exception containment.

Tests:
- Reject escape, wrong identity, root-equal, and over-budget inputs before side effects.
- Run the original candidate regression under a temporary workspace.

Preventive controls:
- Centralize safe path, identity, and archive-budget validation.

## Structural Hardening

The scan also produced derived, unsealed design guidance based on the complete finding collection. These proposals describe options and tradeoffs; they do not indicate that any finding has been remediated.

[Open the structural hardening portfolio](hardening/hardening.md)

## Reviewed Surfaces

| Surface | Risk Area | Outcome | Notes |
| --- | --- | --- | --- |
| Windows archive member names escape the restore staging directory | Path traversal or resource boundary failure | Reported | Validated and reported with candidate-local discovery, validation, and attack-path receipts. Evidence: artifacts/05_findings/SEC-B02-01/candidate_ledger.jsonl |
| Backup verification decompresses unbounded archive members into memory | Path traversal or resource boundary failure | Reported | Validated and reported with candidate-local discovery, validation, and attack-path receipts. Evidence: artifacts/05_findings/SEC-B02-02/candidate_ledger.jsonl |
| Orphan cleanup does not bind the backup to the audited workspace snapshot | Path traversal or resource boundary failure | Reported | Validated and reported with candidate-local discovery, validation, and attack-path receipts. Evidence: artifacts/05_findings/SEC-B02-04/candidate_ledger.jsonl |
| Restored dataset manifest path can escape the workspace on read | Path traversal or resource boundary failure | Reported | Validated and reported with candidate-local discovery, validation, and attack-path receipts. Evidence: artifacts/05_findings/SEC-B03-01/candidate_ledger.jsonl |
| Restored dictionary path can escape the workspace and substitute type metadata | Path traversal or resource boundary failure | Reported | Validated and reported with candidate-local discovery, validation, and attack-path receipts. Evidence: artifacts/05_findings/SEC-B03-02/candidate_ledger.jsonl |
| Export bundle reads persisted resultPath without workspace containment | Path traversal or resource boundary failure | Reported | Validated and reported with candidate-local discovery, validation, and attack-path receipts. Evidence: artifacts/05_findings/SEC-B03-04/candidate_ledger.jsonl |
| Persisted run id controls export write roots and included-data source | Path traversal or resource boundary failure | Reported | Validated and reported with candidate-local discovery, validation, and attack-path receipts. Evidence: artifacts/05_findings/SEC-B03-05/candidate_ledger.jsonl |
| Persisted analysis result path is read without workspace containment | Path traversal or resource boundary failure | Reported | Validated and reported with candidate-local discovery, validation, and attack-path receipts. Evidence: artifacts/05_findings/SEC-B04-02/candidate_ledger.jsonl |
| Persisted analysis job state path is read without workspace containment | Path traversal or resource boundary failure | Reported | Validated and reported with candidate-local discovery, validation, and attack-path receipts. Evidence: artifacts/05_findings/SEC-B04-03/candidate_ledger.jsonl |
| Unfinished-job recovery reads every persisted state path without containment | Path traversal or resource boundary failure | Reported | Validated and reported with candidate-local discovery, validation, and attack-path receipts. Evidence: artifacts/05_findings/SEC-B04-04/candidate_ledger.jsonl |
| Empirical cleanup containment permits deletion of the workspace root | Path traversal or resource boundary failure | Reported | Validated and reported with candidate-local discovery, validation, and attack-path receipts. Evidence: artifacts/05_findings/SEC-B04-05/candidate_ledger.jsonl |
| Suppressed or ignored candidates | coverage | Rejected | Seven candidates were retained as ignore/suppressed with explicit counterevidence in attack-path analysis. Evidence: artifacts/05_findings/attack_path_analysis_report.md |

## Open Questions And Follow Up

- Refresh source revision before implementation and compare drift.
  - Follow-up prompt: Re-run the security review after the first safe-path implementation.
- Re-run the original 11 proof paths after fixes.
  - Follow-up prompt: Verify containment, identity binding, resource budgets, backup binding, and cleanup.
