from __future__ import annotations

import hashlib
import json
import os
import shutil
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

from app.advanced_contracts import AdvancedAnalysisSpec
from app.services.advanced_export_paper import (
    JsonObject,
    JsonValue,
    build_advanced_paper_report,
    build_advanced_paper_tables,
)
from app.services.advanced_runner import _canonical_advanced_hash
from app.services.dataset_repository import DatasetRepository
from app.services.owned_resources import resolve_normalized_dataset_path
from app.services.replay_package import exported_result, write_replay_metadata
from app.services.report_facts import resolve_report_facts
from app.services.repository_io import UnsafePathError, safe_identifier
from app.services.result_normalizer import normalize_and_validate
from app.settings import Settings


def _write_json(path: Path, value: JsonValue) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _write_manifest(root: Path, *, run_id: str, spec_hash: str, include_data: bool) -> None:
    files: list[JsonObject] = []
    for path in sorted(item for item in root.rglob("*") if item.is_file()):
        files.append(
            {
                "path": path.relative_to(root).as_posix(),
                "sha256": _sha256(path),
                "bytes": path.stat().st_size,
            }
        )
    _write_json(
        root / "provenance" / "manifest.json",
        {
            "schemaVersion": "1.0.0",
            "runId": run_id,
            "specHash": spec_hash,
            "includeData": include_data,
            "generatedAt": datetime.now(timezone.utc).isoformat(),
            "files": files,
        },
    )


def create_advanced_export_bundle(
    requested_run_id: str,
    state: JsonObject,
    spec: AdvancedAnalysisSpec,
    result: JsonObject,
    repository: DatasetRepository,
    settings: Settings,
    include_data: bool,
) -> Path:
    try:
        run_id = safe_identifier(requested_run_id, label="advanced analysis run id")
    except UnsafePathError as error:
        raise ValueError("高级分析运行标识不安全") from error
    if state.get("id") != run_id or result.get("run", {}).get("id") != run_id:
        raise ValueError("高级分析结果身份与请求不匹配")
    if state.get("status") != "succeeded" or not state.get("resultPath"):
        raise ValueError("只有成功完成的高级分析可以导出")
    spec_hash = _canonical_advanced_hash(spec)
    if state.get("specHash") != spec_hash or result.get("run", {}).get("specHash") != spec_hash:
        raise ValueError("高级分析规格哈希与结果不匹配")
    normalize_and_validate(result, settings.advanced_result_schema_path)
    resolve_report_facts(result)

    dataset: JsonObject | None = None
    data_path: Path | None = None
    if spec.dataset_version_id is not None:
        dataset = repository.get_dataset(spec.dataset_version_id)
        data_path = resolve_normalized_dataset_path(settings.state_root, dataset)
    if include_data and data_path is None:
        raise ValueError("解析功效没有数据版本，不能请求包含数据的导出包")

    export_dir = settings.state_root / "projects" / "default" / "runs" / run_id / "exports"
    export_dir.mkdir(parents=True, exist_ok=True)
    target = export_dir / f"{run_id}-advanced-{'with-data' if include_data else 'no-data'}.zip"
    temporary_target = target.with_suffix(".zip.tmp")
    if temporary_target.exists():
        temporary_target.unlink()

    tables = build_advanced_paper_tables(result)
    report = build_advanced_paper_report(spec, result, tables, include_data=include_data)
    with tempfile.TemporaryDirectory(
        prefix="researchpath-advanced-export-", dir=export_dir
    ) as temporary:
        root = Path(temporary) / f"{run_id}-export"
        root.mkdir()
        _write_json(
            root / "specification" / "advanced-spec.json",
            spec.model_dump(mode="json", by_alias=True),
        )
        result_for_export = exported_result(result, include_data=include_data)
        _write_json(root / "result" / "advanced-result.json", result_for_export)
        _write_json(root / "paper" / "tables.json", tables)
        _write_json(root / "paper" / "apa.json", {"reports": result.get("apaReports", [])})
        (root / "paper" / "report.md").parent.mkdir(parents=True, exist_ok=True)
        (root / "paper" / "report.md").write_text(report, encoding="utf-8")
        _write_json(root / "provenance" / "result-provenance.json", result.get("provenance", {}))
        _write_json(
            root / "provenance" / "data-manifest.json",
            {
                "datasetVersionId": spec.dataset_version_id,
                "sourceSha256": dataset.get("originalFile", {}).get("sha256") if dataset else None,
                "included": include_data,
                "normalizedSha256": _sha256(data_path) if data_path is not None else None,
            },
        )
        (root / "README.md").write_text(
            "# ResearchPath 高级分析复现包\n\n"
            f"对应运行：`{run_id}`\n\n"
            "先阅读 `paper/report.md`，再核对 `specification/advanced-spec.json`、"
            "`result/advanced-result.json` 和 `provenance/manifest.json`。\n"
            "本包不把 experimental 方法声明为 supported。\n",
            encoding="utf-8",
        )
        reproduction = root / "reproduction"
        reproduction.mkdir()
        runner = settings.project_root / "engine" / "R" / "run_advanced_analysis.R"
        if not runner.is_file():
            raise ValueError("高级分析 R runner 不存在")
        shutil.copy2(runner, reproduction / "run_advanced_analysis.R")
        reproduction_input = {
            "spec": spec.model_dump(mode="json", by_alias=True),
            "dataPath": "../data/analysis-data.parquet" if include_data else None,
            "artifactDirectory": "../artifacts",
        }
        _write_json(reproduction / "input.json", reproduction_input)
        (reproduction / "reproduce.ps1").write_text(
            "$ErrorActionPreference = 'Stop'\n"
            "New-Item -ItemType Directory -Force -Path (Join-Path $PSScriptRoot '..\\artifacts') | Out-Null\n"
            "& Rscript --vanilla (Join-Path $PSScriptRoot 'run_advanced_analysis.R') "
            "(Join-Path $PSScriptRoot 'input.json') (Join-Path $PSScriptRoot '..\\reproduced-result.json')\n",
            encoding="utf-8",
        )
        if include_data and data_path is not None:
            (root / "data").mkdir()
            shutil.copy2(data_path, root / "data" / "analysis-data.parquet")
        write_replay_metadata(
            root,
            run_id=run_id,
            command="pwsh -NoProfile -File reproduction/reproduce.ps1",
            include_data=include_data,
            manifest_path="provenance/manifest.json",
        )
        _write_manifest(root, run_id=run_id, spec_hash=spec_hash, include_data=include_data)
        with ZipFile(temporary_target, "w", compression=ZIP_DEFLATED) as archive:
            for path in sorted(item for item in root.rglob("*") if item.is_file()):
                archive.write(path, path.relative_to(root).as_posix())
    os.replace(temporary_target, target)
    return target
