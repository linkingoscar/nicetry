import json
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.goldens.audit_sources import (  # type: ignore[reportMissingImports] # noqa: E402
    audit_all_sources,
    audit_single_source,
)


def test_audit_all_sources_runs_cleanly() -> None:
    """INFRA-02: Auditing existing golden sources in repo returns zero invalid sources after fix."""
    report = audit_all_sources()
    assert report["totalSourcesFound"] >= 20
    assert report["invalidSources"] == 0
    assert report["totalIssues"] == 0


def test_audit_single_source_detects_missing_fields() -> None:
    """INFRA-02: Auditor flags missing required fields in source.json."""
    with tempfile.TemporaryDirectory() as tmpdir:
        src_path = Path(tmpdir) / "data" / "source.json"
        src_path.parent.mkdir(parents=True)
        incomplete_data = {
            "sourceId": "test_src_1",
            "title": "Incomplete Source"
        }
        src_path.write_text(json.dumps(incomplete_data), encoding="utf-8")

        res = audit_single_source(src_path)
        assert res["valid"] is False
        assert any("Missing required field" in issue for issue in res["issues"])
