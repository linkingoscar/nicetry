from __future__ import annotations

import json
import os
import subprocess
import tempfile
from pathlib import Path

import pytest

from app.api.schemas import DiaryMultilevelInput
from app.settings import get_settings


def _base_contract() -> dict[str, object]:
    return {
        "subject_variable_id": "person",
        "time_variable_id": "day",
        "outcome_variable_id": "y",
        "predictor_variable_id": "x",
    }


def test_quadratic_time_requires_linear_hierarchy() -> None:
    with pytest.raises(ValueError, match="必须与线性时间趋势"):
        DiaryMultilevelInput.model_validate(
            {
                **_base_contract(),
                "include_linear_time": False,
                "include_quadratic_time": True,
            }
        )


def test_custom_time_origin_contract_is_explicit() -> None:
    with pytest.raises(ValueError, match="必须提供"):
        DiaryMultilevelInput.model_validate(
            {**_base_contract(), "time_origin_strategy": "custom"}
        )
    with pytest.raises(ValueError, match="仅当"):
        DiaryMultilevelInput.model_validate(
            {**_base_contract(), "custom_time_origin": 3}
        )


def test_unbalanced_centering_uses_equal_person_weights_and_explicit_protocol() -> None:
    settings = get_settings()
    root = settings.project_root
    r_script = """
    suppressPackageStartupMessages(library(jsonlite))
    source(commandArgs(trailingOnly = TRUE)[1])
    source(commandArgs(trailingOnly = TRUE)[2])
    data <- data.frame(
      person = c("a", "a", "a", "b", "b"),
      day = c(1, 2, 3, 1, 2),
      x = c(1, 2, 3, 10, 10),
      z = c(10, 10, 10, 20, 20)
    )
    spec <- list(
      subjectVariableId = "person",
      timeVariableId = "day",
      predictorVariableId = "x",
      centering = "person_mean",
      temporalEffect = "contemporaneous",
      lagOrder = 1,
      includeLinearTime = TRUE,
      includeQuadraticTime = TRUE,
      timeOriginStrategy = "custom",
      customTimeOrigin = 1,
      level2ModeratorVariableId = "z"
    )
    centered <- center_predictor(data, spec)
    temporal <- diary_temporal_design(centered$data, spec, centered)
    result <- list(
      between = centered$data$x__between,
      predictorProtocol = centered$protocol,
      moderator = temporal$data$z__grand_centered,
      moderatorProtocol = temporal$moderatorProtocol,
      timeProtocol = temporal$timeProtocol
    )
    write_json(result, commandArgs(trailingOnly = TRUE)[3], auto_unbox = TRUE, null = "null")
    """
    with tempfile.TemporaryDirectory(prefix="rp-centering-test-") as temporary:
        work = Path(temporary)
        script = work / "run.R"
        output = work / "output.json"
        script.write_text(r_script, encoding="utf-8")
        environment = os.environ.copy()
        environment["R_LIBS_USER"] = str(settings.r_library_path)
        completed = subprocess.run(
            [
                str(settings.rscript_path),
                "--vanilla",
                str(script),
                str(root / "engine/R/lib/diary_multilevel.R"),
                str(root / "engine/R/lib/diary_esm_evidence.R"),
                str(output),
            ],
            cwd=root,
            env=environment,
            capture_output=True,
            text=True,
            timeout=30,
        )
        result = json.loads(output.read_text(encoding="utf-8")) if output.exists() else None

    assert completed.returncode == 0, completed.stdout + completed.stderr
    assert result is not None
    assert result["between"] == pytest.approx([-4, -4, -4, 4, 4])
    assert result["moderator"] == pytest.approx([-5, -5, -5, 5, 5])
    assert result["predictorProtocol"]["personMeanReintroduced"] is True
    assert result["predictorProtocol"]["grandMeanWeighting"] == "equal weight per person"
    assert result["moderatorProtocol"]["grandMeanWeighting"] == "equal weight per person"
    assert result["timeProtocol"]["originValue"] == 1
