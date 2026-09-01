# ResearchPath repository guide

Use PowerShell 7 and the scripts in `scripts/` for setup, development and tests.

## Find the right entrypoint

- Machine-readable map: `project.manifest.json`
- API composition only: `apps/api/app/main.py`
- HTTP routes: `apps/api/app/api/routes/`
- Request DTOs and dependencies: `apps/api/app/api/`
- Domain/statistical orchestration: `apps/api/app/services/`
- Cross-language contracts: `specs/`
- R estimators: `engine/R/`
- Frontend API by domain: `apps/web/src/api/`
- Frontend types by domain: `apps/web/src/types/`
- Statistical methods and validation rules: `docs/02-统计方法与报告规范.md`, `docs/04-工程开发与验证.md`

## Architecture rules

- Services and engines must not import `app.api` or `app.main`.
- Route modules translate HTTP errors; statistical decisions stay in services/engines.
- `api.ts` and `types.ts` are compatibility barrels only. Add new code to focused modules.
- JSON Schema, Python contracts and TypeScript types must change together.
- A capability is visible only when its registry reports `executionAvailable=true`.
- Never write generated test data to the repository root. Runtime state belongs in ignored directories.

Run `scripts/check-architecture.ps1` before the full `scripts/test.ps1` gate.

## Mandatory harness loop

- Read `docs/04-工程开发与验证.md` before repository-wide cleanup, performance work, security hardening or release preparation.
- Run `scripts/harness.ps1 -Mode Quick` during a scoped edit, `-Mode Targeted` after a bounded work package, and `-Mode Statistical` for statistical/R/cross-language contract work. Targeted and Statistical never replace `-Mode Full` before merge or `-Mode Release` for a release candidate; unknown/shared-infrastructure impact must fail safe to Full.
- Never raise coverage, type, bundle, performance or statistical tolerances merely to make a failing gate pass.
- A debt item is closed only when every acceptance condition has reproducible closure evidence.
- Validate persisted paths, object identity and resource budgets before filesystem or database side effects.
- Stop only the object the user named: scans, processes, Codex pages and task archives are distinct lifecycle objects.

## Mandatory changelog trail

- Every developer must append a changelog entry to `docs/09-修改日志.md` in the same batch as any completed development task or actual code/contract/config/script/docs change. Entries are additive only.
- Never modify, overwrite, delete or reorder existing changelog content. If an old entry is wrong, record a correction in a new entry naming the corrected entry.
- Cross-language contract changes (JSON Schema / Python / TypeScript / R input) must be recorded across all touched layers in the same entry.

## Mandatory debt registration

- Register newly discovered problems in `docs/debt-register.json` promptly: any confirmed defect, risk or tech debt found during development, review, audit or verification (statistical correctness, security, contract drift, performance, architecture, test gaps) must be recorded as a debt item with evidence, acceptance criteria and priority.
- Register in the same batch as the discovery when practical, or before the task/session ends. Do not let a discovered problem live only in conversation, code comments or review reports.
- Record fixes in the same debt item: update status to `closed` with reproducible `closureEvidence` (tests, harness runs, verification scripts). Do not close a debt merely by deleting its description.
- Keep the register schema-valid: validate `docs/debt-register.json` against `docs/debt-register.schema.json` after every edit.
