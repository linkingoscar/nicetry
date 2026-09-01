from __future__ import annotations


def _panel_request(model_type: str = "ri_clpm") -> dict[str, object]:
    return {
        "factor_count": 2,
        "longitudinal_panel": {
            "model_type": model_type,
            "subject_variable_id": "subject_id",
            "waves": [
                {
                    "label": "T1",
                    "time_value": 0,
                    "x_variable_id": "x1",
                    "y_variable_id": "y1",
                },
                {
                    "label": "T2",
                    "time_value": 1,
                    "x_variable_id": "x2",
                    "y_variable_id": "y2",
                },
                {
                    "label": "T3",
                    "time_value": 2,
                    "x_variable_id": "x3",
                    "y_variable_id": "y3",
                },
            ],
        },
    }


def _latent_panel_request(model_type: str = "clpm") -> dict[str, object]:
    request = _panel_request(model_type)
    panel = request["longitudinal_panel"]
    assert isinstance(panel, dict)
    panel.update(
        {
            "measurement_mode": "latent_items",
            "invariance_level": "strict",
            "compare_competing_models": True,
        }
    )
    waves = panel["waves"]
    assert isinstance(waves, list)
    for index, wave in enumerate(waves, start=1):
        wave.pop("x_variable_id")
        wave.pop("y_variable_id")
        wave["x_item_ids"] = [f"x_t{index}_i{item}" for item in range(1, 4)]
        wave["y_item_ids"] = [f"y_t{index}_i{item}" for item in range(1, 4)]
    return request


def _panel_contract_payload() -> dict[str, object]:
    request = _panel_request()
    panel = request["longitudinal_panel"]
    assert isinstance(panel, dict)
    return panel
