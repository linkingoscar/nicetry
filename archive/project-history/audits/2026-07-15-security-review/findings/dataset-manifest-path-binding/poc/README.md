# Harmless regression cases for SEC-B03-01

This directory intentionally contains documentation only. The proposed pytest cases
use `tmp_path`; they do not open the real workspace, start the API, or access user
files. Add them to a disposable checkout after implementing
`DatasetMetadataIntegrityError` and the path-binding fix described in the report.

```python
import json
import sqlite3
from dataclasses import replace

import pytest

from app.services.dataset_repository import DatasetRepository
from app.services.repository_errors import DatasetMetadataIntegrityError
from app.settings import get_settings


def manifest(dataset_id: str) -> dict:
    return {
        "schemaVersion": "1.0.0",
        "id": dataset_id,
        "projectId": "default",
        "createdAt": "2026-07-15T00:00:00+00:00",
        "originalFile": {
            "name": "fixture.csv", "format": "csv", "sizeBytes": 1,
            "sha256": "0" * 64,
        },
        "storage": {"raw": "fixture/raw.csv", "normalized": "fixture/data.parquet"},
        "rowCount": 1, "columnCount": 1,
        "variables": [{
            "id": "var_1_00000000", "originalName": "x", "label": "x",
            "storageType": "int64", "inferredType": "continuous",
            "confirmedType": None, "confidence": 1.0, "rationale": "fixture",
            "missingCount": 0, "missingRate": 0.0, "uniqueCount": 1,
            "sampleValues": [1], "valueLabels": {}, "issues": [],
        }],
        "preview": [{"x": 1}], "warnings": [],
    }


def seed(repository: DatasetRepository, dataset_id: str, stored_path: str) -> None:
    with repository._connect() as connection:
        connection.execute(
            """INSERT INTO dataset_versions
               (id, project_id, created_at, original_name, file_format, sha256,
                manifest_path, row_count, column_count)
               VALUES (?, 'default', '2026-07-15T00:00:00+00:00', 'fixture.csv',
                       'csv', ?, ?, 1, 1)""",
            (dataset_id, "0" * 64, stored_path),
        )


def write_manifest(path, dataset_id: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(manifest(dataset_id)), encoding="utf-8")


def test_rejects_manifest_path_outside_workspace(tmp_path) -> None:
    root = tmp_path / "workspace"
    repository = DatasetRepository(replace(get_settings(), state_root=root))
    dataset_id = "dataset_aaaaaaaaaaaaaaaa"
    outside = tmp_path / "outside.json"
    write_manifest(outside, dataset_id)
    seed(repository, dataset_id, "../outside.json")

    with pytest.raises(DatasetMetadataIntegrityError):
        repository.get_dataset(dataset_id)


def test_rejects_contained_manifest_for_another_dataset(tmp_path) -> None:
    root = tmp_path / "workspace"
    repository = DatasetRepository(replace(get_settings(), state_root=root))
    requested = "dataset_aaaaaaaaaaaaaaaa"
    other = "dataset_bbbbbbbbbbbbbbbb"
    other_path = root / "projects/default/datasets" / other / "manifest.json"
    write_manifest(other_path, other)
    seed(repository, requested, f"projects/default/datasets/{other}/manifest.json")

    with pytest.raises(DatasetMetadataIntegrityError):
        repository.get_dataset(requested)


def test_accepts_canonical_manifest_bound_to_requested_dataset(tmp_path) -> None:
    root = tmp_path / "workspace"
    repository = DatasetRepository(replace(get_settings(), state_root=root))
    dataset_id = "dataset_aaaaaaaaaaaaaaaa"
    relative = f"projects/default/datasets/{dataset_id}/manifest.json"
    write_manifest(root / relative, dataset_id)
    seed(repository, dataset_id, relative)

    assert repository.get_dataset(dataset_id)["id"] == dataset_id
```

Run only after the defensive exception and resolver exist:

```sh
python -m pytest apps/api/tests/test_dataset_repository_paths.py -q
```

Expected post-fix result (not executed during this static review):

```text
...                                                                      [100%]
3 passed
```
