from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
API_ROOT = ROOT / "apps" / "api"
sys.path.insert(0, str(API_ROOT))

from app.services.advanced_analysis import advanced_analysis_registry  # noqa: E402, I001


def load_json(relative_path: str) -> dict:
    return json.loads((ROOT / relative_path).read_text(encoding="utf-8"))


def main() -> int:
    errors: list[str] = []
    spec_schema = load_json("specs/advanced-analysis-spec.schema.json")
    result_schema = load_json("specs/advanced-result-bundle.schema.json")
    debt_register = load_json("docs/debt-register.json")
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    handbook = (ROOT / "docs/25-后续开发可执行手册.md").read_text(encoding="utf-8")
    blueprint = (ROOT / "docs/27-OB-CB实验与问卷实证研究全流程能力审计及开发蓝图.md").read_text(
        encoding="utf-8"
    )
    advanced_runner = (ROOT / "engine/R/run_advanced_analysis.R").read_text(encoding="utf-8")

    expected_families = set(spec_schema["$defs"]["common"]["properties"]["family"]["enum"])
    capabilities = advanced_analysis_registry.capabilities()
    actual_families = {item["family"] for item in capabilities}
    if actual_families != expected_families:
        errors.append(
            f"capability family drift: schema={sorted(expected_families)} registry={sorted(actual_families)}"
        )

    for capability in capabilities:
        slices = capability.get("slices")
        if not isinstance(slices, list) or not slices:
            errors.append(f"{capability['family']} has no slice capability")
            continue
        if not any(item.get("executionAvailable") is True for item in slices):
            errors.append(f"{capability['family']} has no executable slice")
        ids = [item.get("id") for item in slices]
        if len(ids) != len(set(ids)):
            errors.append(f"{capability['family']} has duplicate slice ids")
        for item in slices:
            if item.get("status") == "supported" and item.get("executionAvailable") is not True:
                errors.append(f"supported slice is not executable: {item.get('id')}")

    result_families = set(result_schema["properties"]["run"]["properties"]["family"]["enum"])
    if actual_families != result_families:
        errors.append(
            f"result family drift: registry={sorted(actual_families)} result={sorted(result_families)}"
        )
    dispatch_block = re.search(
        r"result\s*<-\s*switch\(\s*family,(?P<body>.*?)\n\s*stop\(\"Unknown advanced analysis family\"",
        advanced_runner,
        flags=re.DOTALL,
    )
    dispatch_body = dispatch_block.group("body") if dispatch_block else ""
    for capability in capabilities:
        if capability.get("executionAvailable") is True:
            family = capability["family"]
            if not re.search(rf"\b{re.escape(family)}\s*=", dispatch_body):
                errors.append(f"executable family has no R dispatch branch: {family}")

    mi_spec = spec_schema["$defs"]["multipleImputation"]["allOf"][1]["properties"]["pooling"]
    if "rubin" not in mi_spec.get("enum", []):
        errors.append("multipleImputation.pooling must expose the implemented rubin slice")
    mi_result = result_schema["$defs"]["imputationResult"]
    if "poolingStatus" not in mi_result.get("required", []):
        errors.append("imputationResult must require poolingStatus")
    if "rubin" not in mi_result.get("properties", {}).get("poolingStatus", {}).get("enum", []):
        errors.append("imputationResult.poolingStatus must expose rubin")

    if "Rubin 合并" not in readme or "MICE 插补" not in readme:
        errors.append("README is missing the honest MI capability label")
    if "pooling=none" not in handbook and "pooling` 只" not in handbook:
        errors.append("docs/25 does not document the current non-pooling boundary")
    if "WP-R0-01" not in blueprint or "WP-R0-08" not in blueprint:
        errors.append("OB/CB blueprint is missing the R0 work-package anchors")
    longitudinal_missing = spec_schema["$defs"]["longitudinalModel"]["allOf"][1]["properties"][
        "missing"
    ]["enum"]
    if "available_rows_ml" not in longitudinal_missing:
        errors.append("longitudinal observed growth must expose available_rows_ml honestly")
    if "available_rows_ml" not in handbook:
        errors.append("docs/25 does not distinguish observed-growth available-row ML from FIML")
    r0_section = blueprint.split("### 阶段 R0：", 1)[1].split("### 阶段 R1：", 1)[0]
    r0_rows = [line for line in r0_section.splitlines() if line.startswith("| WP-R0-")]
    if len(r0_rows) != 8:
        errors.append("R0 work-package table must contain exactly WP-R0-01 through WP-R0-08")
    if any("部分完成" in row or "未开始" in row for row in r0_rows):
        errors.append("R0 work-package table contains an unfinished status")

    debt_items = {item["id"]: item for item in debt_register["items"]}
    if debt_items.get("METHOD-001", {}).get("status") == "closed":
        errors.append("METHOD-001 cannot be closed while advanced slices remain experimental")
    if debt_items.get("METHOD-002", {}).get("status") == "closed":
        errors.append("METHOD-002 cannot be closed by documentation-only evidence")

    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        return 1

    print(
        f"Capability/document consistency passed: {len(capabilities)} families, {sum(len(item['slices']) for item in capabilities)} slices."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
