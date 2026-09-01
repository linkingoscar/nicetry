from __future__ import annotations

import json

from app.services.report_facts import report_fact_rows
from app.services.repository_io import JsonObject


def append_auditable_fact_tables(tables: list[str], result: JsonObject) -> None:
    rows = report_fact_rows(result)
    if rows:
        tables.append("\n### 表：报告事实来源索引\n\n")
        tables.append("| Fact | 语义角色 | JSON Pointer | 当前值 |\n|---|---|---|---|\n")
        for row in rows:
            value = row.get("value")
            rendered = (
                json.dumps(value, ensure_ascii=False)
                if isinstance(value, (dict, list))
                else str(value)
            )
            tables.append(
                f"| {row.get('factId')} | {row.get('semanticRole')} | "
                f"`{row.get('sourcePath')}` | {rendered} |\n"
            )
    assessments = result.get("reportingProfileAssessments")
    if not isinstance(assessments, list):
        return
    tables.append("\n### 表：报告规范披露完整性\n\n")
    tables.append(
        "| Profile | 适用 | 已披露/总项 | 完整度 | 解释边界 |\n"
        "|---|:---:|---:|---:|---|\n"
    )
    for assessment in assessments:
        if not isinstance(assessment, dict):
            continue
        completeness = assessment.get("completeness")
        rendered = "—" if completeness is None else f"{float(completeness) * 100:.1f}%"
        tables.append(
            f"| {assessment.get('label')} | "
            f"{'是' if assessment.get('applicable') else '否'} | "
            f"{assessment.get('satisfiedCount')}/{assessment.get('totalCount')} | "
            f"{rendered} | 仅检查披露完整性；不认证研究质量、因果性或论文资格 |\n"
        )
    gate = result.get("publicationGate")
    if not isinstance(gate, dict):
        return
    tables.append("\n### 表：三层发表门禁\n\n")
    tables.append("| 层级 | 状态 | 原因 |\n|---|---|---|\n")
    for key, label in (
        ("capabilityLayer", "能力验证"),
        ("runEvidenceLayer", "单次运行证据"),
        ("reportingLayer", "稿件披露"),
    ):
        layer = gate.get(key)
        if not isinstance(layer, dict):
            continue
        reasons = layer.get("reasons")
        reason = "；".join(str(item) for item in reasons) if isinstance(reasons, list) else "—"
        tables.append(f"| {label} | {layer.get('status')} | {reason or '—'} |\n")
    confirmation = gate.get("humanConfirmation")
    confirmed = isinstance(confirmation, dict) and confirmation.get("confirmed") is True
    tables.append(
        f"| 具名人工确认 | {'passed' if confirmed else 'failed'} | "
        f"{'已确认' if confirmed else '未确认；机器门禁不能替代研究者与审稿责任'} |\n"
    )
    tables.append(
        f"\n最终状态：`{gate.get('finalStatus')}`；"
        f"finalEligible=`{str(gate.get('finalEligible')).lower()}`。\n"
    )
