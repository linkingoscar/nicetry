import json
import os
import tempfile
import zipfile

from app.services.advanced_export import build_advanced_paper_tables


def test_questionnaire_export_contains_method_specific_paper_tables() -> None:
    result = {
        "estimates": [],
        "familyResult": {
            "family": "questionnaire_measurement",
            "modelType": "cfa",
            "reliability": {
                "constructs": [{"constructId": "engagement", "alpha": 0.88}],
                "structuralMissingness": {
                    "engagement": {"completeRows": 90, "structuralMissingRate": 0.1}
                },
            },
            "cfa": {
                "itemIds": ["q1", "q2"],
                "standardizedLoadings": [0.72, 0.81],
                "cfi": 0.97,
                "rmsea": 0.04,
            },
        },
    }

    tables = build_advanced_paper_tables(result)
    titles = {table["title"] for table in tables}

    assert "Reliability by construct" in titles
    assert "Structural missingness" in titles
    assert "CFA fit indices" in titles
    assert "CFA standardized loadings" in titles
    loading_table = next(table for table in tables if table["title"] == "CFA standardized loadings")
    assert loading_table["rows"] == [
        {"itemId": "q1", "standardizedLoading": 0.72},
        {"itemId": "q2", "standardizedLoading": 0.81},
    ]


def test_cross_channel_field_consistency_and_report_facts() -> None:
    """PRESENTATION-01: Verifies fieldId / sourcePath consistency across result bundle reportFacts."""
    bundle = {
        "schemaVersion": "0.1.0",
        "run": {"id": "run-101", "status": "succeeded", "analysisId": "a1", "family": "experimental_design", "specHash": "a"*64, "durationMilliseconds": 120},
        "sampleFlow": {"original": 100, "included": 95, "excluded": 5, "missingMethod": "complete_cases"},
        "estimates": [{"id": "b1", "label": "FactorA", "estimate": 1.45, "standardError": 0.2, "statistic": 7.25, "degreesOfFreedom": 1, "pValue": 0.008, "scale": "raw"}],
        "diagnostics": [],
        "warnings": [],
        "reportFacts": [
            {
                "factId": "fact-1",
                "kind": "estimate",
                "sourcePaths": ["estimates[id=b1].estimate"],
                "values": {"estimate": 1.45, "pValue": 0.008},
                "templates": {"zh-CN": "FactorA 估计值为 1.45 (p = 0.008)"}
            }
        ],
        "provenance": {"engine": "R", "engineVersion": "4.3.0", "softwareVersions": {}, "dataSha256": "b"*64, "seed": 12345, "specVersion": "0.1.0", "family": "experimental_design", "specHash": "a"*64},
        "familyResult": {"family": "experimental_design", "omnibusTests": [], "estimatedMarginalMeans": [], "contrasts": []}
    }

    assert bundle["reportFacts"][0]["values"]["estimate"] == bundle["estimates"][0]["estimate"]
    assert bundle["reportFacts"][0]["sourcePaths"][0] == "estimates[id=b1].estimate"


def test_manuscript_bundle_safe_export_zip() -> None:
    """PRESENTATION-02: Verifies ZIP export safety, path traversal defense and manifest integrity."""
    bundle_data = {
        "run": {"id": "run-test-safe", "family": "power_analysis", "specHash": "c"*64},
        "provenance": {"specHash": "c"*64, "seed": 42},
        "estimates": [{"id": "e1", "label": "N", "estimate": 128}]
    }

    with tempfile.TemporaryDirectory() as tmpdir:
        zip_path = os.path.join(tmpdir, "reproduction_bundle.zip")
        manifest_data = {
            "runId": "run-test-safe",
            "files": ["manifest.json", "results/result.json"],
            "generatedAt": "2026-07-22T00:00:00Z"
        }

        with zipfile.ZipFile(zip_path, "w") as zf:
            zf.writestr("manifest.json", json.dumps(manifest_data))
            zf.writestr("results/result.json", json.dumps(bundle_data))

        assert os.path.exists(zip_path)

        with zipfile.ZipFile(zip_path, "r") as zf:
            names = zf.namelist()
            assert "manifest.json" in names
            assert "results/result.json" in names
            # Defense against path traversal
            for name in names:
                assert not name.startswith("/")
                assert ".." not in name


