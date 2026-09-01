from __future__ import annotations

import json
import os
import subprocess
import tempfile
from pathlib import Path

from app.settings import get_settings


def test_complete_separation_fails_instead_of_falling_back_to_ols() -> None:
    settings = get_settings()
    with tempfile.TemporaryDirectory() as temporary_directory:
        root = Path(temporary_directory)
        data_path = root / "separated.csv"
        input_path = root / "input.json"
        output_path = root / "output.json"

        rows = ["x,y,w"]
        for index in range(40):
            x_value = index - 20
            rows.append(f"{x_value},{1 if x_value > 0 else 0},{index % 2}")
        data_path.write_text("\n".join(rows) + "\n", encoding="utf-8")

        model_spec = {
            "schemaVersion": "1.0.0",
            "modelId": "separation_boundary",
            "name": "Separation boundary",
            "datasetVersionId": "derived_test",
            "design": {
                "timeStructure": "cross_sectional",
                "clustering": "none",
                "claimMode": "associational",
            },
            "nodes": [
                {
                    "id": "node_x",
                    "variableId": "x",
                    "label": "X",
                    "kind": "observed",
                    "role": "x",
                    "dataType": "continuous",
                },
                {
                    "id": "node_y",
                    "variableId": "y",
                    "label": "Y",
                    "kind": "observed",
                    "role": "y",
                    "dataType": "binary",
                },
                {
                    "id": "node_w",
                    "variableId": "w",
                    "label": "W",
                    "kind": "observed",
                    "role": "w",
                    "dataType": "continuous",
                },
            ],
            "edges": [{"id": "edge_x_y", "from": "node_x", "to": "node_y", "kind": "regression"}],
            "moderations": [
                {
                    "id": "moderation_w",
                    "moderatorNodeId": "node_w",
                    "targetEdgeId": "edge_x_y",
                    "productTermId": "term_interaction",
                }
            ],
            "covariates": [],
            "estimation": {
                "family": "ols",
                "standardErrors": "classical",
                "confidenceLevel": 0.95,
                "bootstrap": {
                    "enabled": False,
                    "replicates": 100,
                    "method": "percentile",
                    "seed": 12345,
                },
                "missing": "complete_cases_per_model",
                "centering": {"method": "none", "nodeIds": []},
                "reportScale": "unstandardized_primary",
            },
        }
        payload = {
            "runId": "run_separation_boundary",
            "modelHash": "0" * 64,
            "modelVersionId": "test",
            "dataSha256": "0" * 64,
            "dataPath": str(data_path),
            "modelSpec": model_spec,
            "progressPath": None,
            "cancelPath": None,
        }
        input_path.write_text(json.dumps(payload), encoding="utf-8")

        environment = os.environ.copy()
        environment["R_LIBS_USER"] = str(settings.r_library_path)
        environment["LC_ALL"] = "English_United States.utf8"
        completed = subprocess.run(
            [
                str(settings.rscript_path),
                "--vanilla",
                str(settings.r_engine_path),
                str(input_path),
                str(output_path),
            ],
            cwd=str(settings.project_root),
            env=environment,
            check=False,
            capture_output=True,
        )

        diagnostic = (completed.stdout + completed.stderr).decode("utf-8", errors="replace")
        assert completed.returncode != 0
        assert "separation" in diagnostic.lower()
        assert not output_path.exists()
