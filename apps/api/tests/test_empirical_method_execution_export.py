from __future__ import annotations

from openpyxl import Workbook

from app.services.empirical_export_sections import append_measurement_method_section


def test_measurement_export_preserves_requested_and_executed_method_metadata() -> None:
    execution = {
        "requestedMethod": "maximum_likelihood_factanal_varimax",
        "executedMethod": "principal_components_varimax",
        "fallbackApplied": True,
        "fallbackCode": "EFA_FACTANAL_FALLBACK_PCA",
        "fallbackReason": "maximum-likelihood fit did not converge",
        "affectedOutputs": ["loadings", "factorCorrelations"],
        "interpretationBoundary": "PCA diagnostic only; not a common-factor estimate.",
    }
    report = {
        "efa": {"method": execution["executedMethod"], "methodExecution": execution},
        "cfa": {"methodExecution": execution},
        "validity": {"methodExecution": {}, "htmtMethodExecution": execution},
    }
    workbook = Workbook()
    active_sheet = workbook.active
    assert active_sheet is not None
    workbook.remove(active_sheet)

    def append_sheet(book: Workbook, name: str, rows: list[list[object]]) -> None:
        sheet = book.create_sheet(name)
        for row in rows:
            sheet.append(row)

    append_measurement_method_section(
        workbook,
        report,
        append_sheet,
    )

    rows = list(workbook["测量方法执行"].values)
    exported = dict(zip(rows[0], rows[1], strict=True))
    assert exported["请求方法"] == execution["requestedMethod"]
    assert exported["实际方法"] == execution["executedMethod"]
    assert exported["发生回退"] is True
    assert exported["回退代码"] == execution["fallbackCode"]
    assert exported["回退原因"] == execution["fallbackReason"]
    assert exported["受影响输出"] == "loadings, factorCorrelations"
    assert exported["解释边界"] == execution["interpretationBoundary"]
    cfa_exported = dict(zip(rows[0], rows[2], strict=True))
    assert cfa_exported["分析区块"] == "CFA"
    assert cfa_exported["请求方法"] == execution["requestedMethod"]
    assert cfa_exported["实际方法"] == execution["executedMethod"]
    htmt_exported = dict(zip(rows[0], rows[4], strict=True))
    assert htmt_exported["分析区块"] == "HTMT"
    assert htmt_exported["请求方法"] == execution["requestedMethod"]
    assert htmt_exported["实际方法"] == execution["executedMethod"]
