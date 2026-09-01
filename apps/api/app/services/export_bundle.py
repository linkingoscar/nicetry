from __future__ import annotations

import hashlib
import html
import json
import os
import shutil
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.services.dataset_repository import DatasetRepository
from app.services.export_bundle_figures import (
    _model_svg,
    _simple_png,
    _simple_slope_png,
    _simple_slope_svg,
)
from app.services.replay_package import exported_result, write_replay_metadata
from app.services.repository_io import (
    UnsafePathError,
    _read_json_safe,
    resolve_owned_path,
    safe_identifier,
)
from app.settings import Settings


def _confidence_label(value: float | int | str | None, default: float = 0.95) -> str:
    if value is None:
        percent = default * 100
    else:
        try:
            percent = float(value) * 100
        except ValueError:
            percent = default * 100
    return f"{percent:.2f}".rstrip("0").rstrip(".") + "% CI"


def _json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _report_markdown(state: dict[str, Any], frozen: dict[str, Any]) -> str:
    result = state["result"]
    confidence = (result.get("provenance") or {}).get(
        "confidenceLevel",
        frozen.get("modelSpec", {}).get("estimation", {}).get("confidenceLevel", 0.95),
    )
    interval_label = _confidence_label(confidence)
    lines = [
        f"# {frozen['modelSpec']['name']} 分析报告",
        "",
        f"- AnalysisRun: `{state['id']}`",
        f"- ModelVersion: `{frozen['id']}`",
        f"- 模板: `{result['run'].get('template', 'unknown')}`",
        f"- 有效样本: {result['sampleFlow']['included']} / {result['sampleFlow']['original']}",
        "",
        "## 效应估计",
        "",
        "| 效应 | 类型 | 估计 | 区间 |",
        "|---|---:|---:|---:|",
    ]
    for effect in result.get("effects", []):
        interval = effect.get("confidenceInterval")
        rendered = "—" if not interval else f"[{interval['lower']:.4f}, {interval['upper']:.4f}]"
        lines.append(
            f"| {effect['label']} | {effect['type']} | {effect['estimate']:.4f} | {rendered} |"
        )
    probes = result.get("probes", [])
    if probes:
        lines.extend(
            [
                "",
                "## 条件效应与简单斜率",
                "",
                f"| 路径 | 条件 | W | Z | 效应 | SE | t/z | p | {interval_label} | 方法 |",
                "|---|---|---:|---:|---:|---:|---:|---:|---|---|",
            ]
        )
        for probe in probes:
            interval = probe["confidenceInterval"]
            secondary = probe.get("secondaryModeratorValue")
            lines.append(
                f"| {probe.get('predictorLabel', probe.get('targetEdgeId', '—'))} "
                f"| {probe['label']} | {probe['moderatorValue']:.4f} "
                f"| {'—' if secondary is None else f'{secondary:.4f}'} "
                f"| {probe['effect']:.4f} | {probe['standardError']:.4f} "
                f"| {probe['statistic']:.4f} | {probe['pValue']:.4f} "
                f"| [{interval['lower']:.4f}, {interval['upper']:.4f}] "
                f"| {interval['method']} |"
            )
    jn_results = result.get("johnsonNeymanResults", [])
    if jn_results:
        lines.extend(["", "## Johnson–Neyman 区域", ""])
        for item in jn_results:
            jn = item["result"]
            observed = "、".join(
                f"{value:.4f}" for value in jn.get("observedBoundaries", [])
            ) or "观测范围内无临界点"
            regions = "；".join(
                f"[{region['lower']:.4f}, {region['upper']:.4f}] {region['status']}"
                for region in jn.get("regions", [])
            )
            lines.append(
                f"- {item['predictorLabel']} × {item['moderatorLabel']}："
                f"临界点 {observed}；{regions}；方法 `{jn.get('method', '—')}`。"
            )
    if result.get("apaTables"):
        lines.extend(["", "## 论文汇报表", "", result["apaTables"]])
    lines.extend(
        [
            "",
            "## 可追溯性",
            "",
            "完整模型、测量定义、数据版本、结果、引擎脚本、会话信息和文件校验值见同一导出包。",
        ]
    )
    return "\n".join(lines) + "\n"


def create_export_bundle(
    requested_run_id: str,
    state: dict[str, Any],
    repository: DatasetRepository,
    settings: Settings,
    include_data: bool,
) -> Path:
    try:
        requested_run_id = safe_identifier(requested_run_id, label="analysis run id")
    except UnsafePathError as error:
        raise ValueError("分析运行标识不安全") from error
    state = dict(state)
    if state.get("id") != requested_run_id:
        raise ValueError("分析运行身份与请求不匹配")
    if not state.get("result") and state.get("resultPath"):
        try:
            result_path = resolve_owned_path(
                settings.state_root,
                state["resultPath"],
                label="analysis export result path",
                expected_parent=settings.state_root
                / "projects"
                / "default"
                / "runs"
                / requested_run_id,
                expected_name="result.json",
            )
        except UnsafePathError as error:
            raise ValueError("分析结果文件引用不安全") from error
        if result_path.exists():
            state["result"] = _read_json_safe(result_path)

    if state["status"] != "succeeded" or not state.get("result"):
        raise ValueError("只有成功完成的 AnalysisRun 可以导出")
    if state["result"].get("run", {}).get("id") != requested_run_id:
        raise ValueError("分析结果身份与请求不匹配")
    frozen = repository.get_model_version(state["modelId"], state["modelVersion"])
    dataset = repository.get_dataset(state["datasetId"])
    measurement = repository.get_measurement_for_derived(
        state["datasetId"], frozen["modelSpec"]["datasetVersionId"]
    )
    export_dir = (
        settings.state_root / "projects" / "default" / "runs" / requested_run_id / "exports"
    )
    export_dir.mkdir(parents=True, exist_ok=True)
    suffix = "with-data" if include_data else "no-data"
    target = export_dir / f"{requested_run_id}-{suffix}.zip"
    with tempfile.TemporaryDirectory(prefix="researchpath-export-", dir=export_dir) as temporary:
        root = Path(temporary) / f"{state['id']}-export"
        root.mkdir()
        report = _report_markdown(state, frozen)
        (root / "README.md").write_text(
            "# ResearchPath 可复现分析包\n\n"
            f"本包对应 `{state['id']}`。从 `report/report.md` 开始阅读。"
            + (
                " 数据已包含。\n"
                if include_data
                else " 数据因隐私选项未包含；复现前请放置 `data/analysis-data.csv`。\n"
            ),
            encoding="utf-8",
        )
        (root / "report").mkdir()
        (root / "report" / "report.md").write_text(report, encoding="utf-8")
        (root / "report" / "apa-tables.md").write_text(
            state["result"].get("apaTables", "当前分析未生成 APA 表格。\n"),
            encoding="utf-8",
        )
        (root / "report" / "report.html").write_text(
            "<!doctype html><meta charset='utf-8'><title>ResearchPath report</title>"
            "<style>body{font:16px system-ui;max-width:900px;margin:40px auto;white-space:pre-wrap}</style>"
            f"<body>{html.escape(report)}</body>",
            encoding="utf-8",
        )
        figures = root / "report" / "figures"
        figures.mkdir()
        (figures / "model-path.svg").write_text(
            _model_svg(frozen["modelSpec"], state["result"]), encoding="utf-8"
        )
        _simple_png(figures / "model-path.png", frozen["modelSpec"])
        for index, plot in enumerate(state["result"].get("moderationPlots", []), start=1):
            (figures / f"simple-slope-{index}.svg").write_text(
                _simple_slope_svg(plot), encoding="utf-8"
            )
            _simple_slope_png(figures / f"simple-slope-{index}.png", plot)
        _json(root / "specifications" / "dataset-version.json", dataset)
        _json(root / "specifications" / "measurement-version.json", measurement)
        _json(root / "specifications" / "model-version.json", frozen)
        result_for_export = exported_result(state["result"], include_data=include_data)
        _json(root / "result-bundle.json", result_for_export)
        repro = root / "reproducibility"
        repro.mkdir()
        shutil.copy2(settings.r_engine_path, repro / "run-analysis.R")
        _json(repro / "model-spec.json", frozen["modelSpec"])
        logs = root / "logs"
        logs.mkdir()
        (logs / "analysis-run.log").write_text(
            f"createdAt={state['createdAt']}\nupdatedAt={state['updatedAt']}\nstatus={state['status']}\nstage={state['stage']}\n",
            encoding="utf-8",
        )
        included_data_sha256: str | None = None
        if include_data:
            source = (
                settings.state_root
                / "projects"
                / "default"
                / "runs"
                / requested_run_id
                / "analysis-data.csv"
            )
            if not source.exists():
                source = (
                    settings.state_root
                    / "projects"
                    / "default"
                    / "runs"
                    / requested_run_id
                    / "work"
                    / "analysis-data.csv"
                )
            if not source.exists():
                raise ValueError("该运行缺少可复现分析数据")
            (root / "data").mkdir()
            shutil.copy2(source, root / "data" / "analysis-data.csv")
            included_data_sha256 = _sha256(root / "data" / "analysis-data.csv")
        _json(
            repro / "input.json",
            {
                "runId": f"{state['id']}_reproduced",
                "modelHash": frozen["modelHash"],
                "modelVersionId": frozen["id"],
                "dataSha256": included_data_sha256
                if included_data_sha256 is not None
                else measurement["derivedDataset"]["sha256"],
                "dataPath": "data/analysis-data.csv",
                "modelSpec": frozen["modelSpec"],
            },
        )
        (repro / "reproduce.ps1").write_text(
            "$ErrorActionPreference = 'Stop'\nSet-Location (Join-Path $PSScriptRoot '..')\n"
            "& Rscript --vanilla reproducibility/run-analysis.R reproducibility/input.json reproduced-result.json\n",
            encoding="utf-8",
        )
        provenance = state["result"].get("provenance", {})
        (repro / "session-info.txt").write_text(
            "\n".join(f"{key}: {value}" for key, value in provenance.items()) + "\n",
            encoding="utf-8",
        )
        _json(repro / "package-versions.json", provenance)
        write_replay_metadata(
            root,
            run_id=state["id"],
            command="pwsh -NoProfile -File reproducibility/reproduce.ps1",
            include_data=include_data,
            manifest_path="manifest.json",
        )
        generated_at = datetime.now(timezone.utc).isoformat()
        files = []
        for path in sorted(item for item in root.rglob("*") if item.is_file()):
            files.append(
                {
                    "path": path.relative_to(root).as_posix(),
                    "sizeBytes": path.stat().st_size,
                    "sha256": _sha256(path),
                }
            )
        _json(
            root / "manifest.json",
            {
                "schemaVersion": "1.0.0",
                "generatedAt": generated_at,
                "analysisRunId": state["id"],
                "datasetVersionId": dataset["id"],
                "measurementVersionId": measurement["id"],
                "modelVersionId": frozen["id"],
                "includeData": include_data,
                "files": files,
            },
        )
        archive_base = Path(temporary) / "archive"
        archive = Path(
            shutil.make_archive(str(archive_base), "zip", root_dir=root.parent, base_dir=root.name)
        )
        os.replace(archive, target)
    return target
