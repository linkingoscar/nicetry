from __future__ import annotations

import csv
import math
import random
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "samples" / "data"


def bounded(value: float, lower: float = 1.0, upper: float = 5.0) -> float:
    return round(min(upper, max(lower, value)), 3)


def item_triplet(rng: random.Random, score: float) -> list[float]:
    return [bounded(score + rng.gauss(0, 0.28)) for _ in range(3)]


def likert_item(rng: random.Random, latent_score: float, offset: float = 0.0) -> int:
    observed = 3 + 0.72 * latent_score + offset + rng.gauss(0, 0.48)
    return int(round(min(5, max(1, observed))))


def generate_questionnaire() -> None:
    """Generate a research-scale questionnaire demo with reliable, non-trivial structure."""
    rng = random.Random(20260730)
    fields = [
        "respondent_id",
        "group",
        "age",
        "autonomy_1",
        "autonomy_2",
        "autonomy_3",
        "engagement_1",
        "engagement_2",
        "engagement_3",
        "purchase_1",
        "purchase_2",
        "purchase_3",
    ]
    rows: list[dict[str, object]] = []
    for respondent in range(1, 261):
        group = "B" if respondent % 2 == 0 else "A"
        group_effect = 1 if group == "B" else 0
        age = min(60, max(20, int(round(rng.gauss(36, 8.5)))))
        autonomy = rng.gauss(0, 1) + 0.16 * group_effect
        engagement = 0.58 * autonomy + 0.16 * group_effect + rng.gauss(0, 0.72)
        purchase = (
            0.20 * autonomy
            + 0.52 * engagement
            + 0.08 * ((age - 36) / 8.5)
            + rng.gauss(0, 0.74)
        )
        row: dict[str, object] = {
            "respondent_id": respondent,
            "group": group,
            "age": age,
        }
        for prefix, latent in (
            ("autonomy", autonomy),
            ("engagement", engagement),
            ("purchase", purchase),
        ):
            for item, offset in enumerate((-0.08, 0.0, 0.08), start=1):
                value: object = likert_item(rng, latent, offset)
                # A small amount of item-level missingness makes the quality
                # report realistic without compromising the teaching model.
                if rng.random() < 0.008:
                    value = ""
                row[f"{prefix}_{item}"] = value
        rows.append(row)
    _write(OUTPUT / "questionnaire-demo.csv", fields, rows)


def generate_mediation() -> None:
    rng = random.Random(20260731)
    fields = ["var_autonomy", "var_engagement", "var_performance"]
    rows: list[dict[str, object]] = []
    for _ in range(260):
        autonomy = rng.gauss(0, 1)
        engagement = 0.62 * autonomy + rng.gauss(0, 0.72)
        performance = 0.20 * autonomy + 0.58 * engagement + rng.gauss(0, 0.72)
        rows.append(
            {
                "var_autonomy": round(3 + 0.62 * autonomy, 3),
                "var_engagement": round(3 + 0.62 * engagement, 3),
                "var_performance": round(3 + 0.62 * performance, 3),
            }
        )
    _write(OUTPUT / "mediation-demo.csv", fields, rows)


def generate_longitudinal() -> None:
    rng = random.Random(20260728)
    fields = ["subject_id", "age", "group"]
    for wave in range(1, 6):
        fields.extend(
            [f"x{wave}", f"y{wave}"]
            + [f"x_t{wave}_i{item}" for item in range(1, 4)]
            + [f"y_t{wave}_i{item}" for item in range(1, 4)]
        )
    rows: list[dict[str, object]] = []
    for person in range(1, 241):
        trait_x = rng.gauss(0, 0.65)
        trait_y = 0.35 * trait_x + rng.gauss(0, 0.6)
        slope_x = rng.gauss(0.06, 0.09)
        slope_y = 0.35 * slope_x + rng.gauss(0.05, 0.08)
        x_previous = rng.gauss(0, 0.75)
        y_previous = rng.gauss(0, 0.75)
        row: dict[str, object] = {
            "subject_id": f"P{person:03d}",
            "age": rng.randint(20, 55),
            "group": "intervention" if person % 2 == 0 else "control",
        }
        for wave in range(1, 6):
            if wave > 1:
                x_current = 0.48 * x_previous + 0.16 * y_previous + rng.gauss(0, 0.55)
                y_current = 0.45 * y_previous + 0.24 * x_previous + rng.gauss(0, 0.55)
                x_previous, y_previous = x_current, y_current
            x_score = 3 + 0.55 * trait_x + slope_x * (wave - 1) + x_previous
            y_score = 3 + 0.55 * trait_y + slope_y * (wave - 1) + y_previous
            x_items = item_triplet(rng, x_score)
            y_items = item_triplet(rng, y_score)
            row[f"x{wave}"] = round(sum(x_items) / len(x_items), 3)
            row[f"y{wave}"] = round(sum(y_items) / len(y_items), 3)
            for item, value in enumerate(x_items, start=1):
                row[f"x_t{wave}_i{item}"] = value
            for item, value in enumerate(y_items, start=1):
                row[f"y_t{wave}_i{item}"] = value
        rows.append(row)
    _write(OUTPUT / "longitudinal-panel-demo.csv", fields, rows)


def generate_diary() -> None:
    rng = random.Random(20260729)
    fields = [
        "person_id",
        "day",
        "age",
        "intervention",
        "daily_stress",
        "daily_recovery",
        "daily_engagement",
        "stress_i1",
        "stress_i2",
        "recovery_i1",
        "recovery_i2",
        "engagement_i1",
        "engagement_i2",
        "scenario",
        "purchase",
        "aigc_clicks",
        "exposure_minutes",
    ]
    rows: list[dict[str, object]] = []
    for person in range(1, 81):
        trait_stress = rng.gauss(0, 0.55)
        trait_recovery = -0.35 * trait_stress + rng.gauss(0, 0.5)
        age = rng.randint(20, 58)
        intervention = 1 if person % 2 == 0 else 0
        previous_stress = rng.gauss(0, 0.4)
        for day in range(1, 11):
            stress = 3 + trait_stress + 0.35 * previous_stress + rng.gauss(0, 0.55)
            recovery = (
                3
                + trait_recovery
                - 0.42 * (stress - (3 + trait_stress))
                + 0.18 * intervention
                + rng.gauss(0, 0.45)
            )
            engagement = (
                3
                - 0.22 * (stress - (3 + trait_stress))
                + 0.46 * (recovery - (3 + trait_recovery))
                + 0.12 * intervention
                + rng.gauss(0, 0.45)
            )
            stress, recovery, engagement = map(bounded, (stress, recovery, engagement))
            stress_items = item_triplet(rng, stress)[:2]
            recovery_items = item_triplet(rng, recovery)[:2]
            engagement_items = item_triplet(rng, engagement)[:2]
            scenario = f"S{(person + day) % 4 + 1}"
            purchase_probability = 1 / (
                1 + math.exp(-(-0.5 - 0.25 * stress + 0.35 * recovery))
            )
            exposure_minutes = rng.randint(20, 60)
            click_probability = min(
                0.85,
                max(0.02, 1 / (1 + math.exp(-(0.2 + 0.2 * engagement)))),
            )
            rows.append(
                {
                    "person_id": f"D{person:03d}",
                    "day": day,
                    "age": age,
                    "intervention": intervention,
                    "daily_stress": stress,
                    "daily_recovery": recovery,
                    "daily_engagement": engagement,
                    "stress_i1": stress_items[0],
                    "stress_i2": stress_items[1],
                    "recovery_i1": recovery_items[0],
                    "recovery_i2": recovery_items[1],
                    "engagement_i1": engagement_items[0],
                    "engagement_i2": engagement_items[1],
                    "scenario": scenario,
                    "purchase": int(rng.random() < purchase_probability),
                    "aigc_clicks": sum(
                        int(rng.random() < click_probability) for _ in range(8)
                    ),
                    "exposure_minutes": exposure_minutes,
                }
            )
            previous_stress = stress - (3 + trait_stress)
    _write(OUTPUT / "daily-diary-demo.csv", fields, rows)


def generate_intensive_esm() -> None:
    rng = random.Random(20260801)
    fields = [
        "person_id",
        "occasion",
        "emotion",
        "ai_trust",
        "scenario",
        "purchase",
        "aigc_clicks",
        "exposure_minutes",
    ]
    rows: list[dict[str, object]] = []
    for person in range(1, 31):
        emotion_mean = rng.gauss(0, 0.55)
        trust_mean = 0.3 * emotion_mean + rng.gauss(0, 0.5)
        emotion = rng.gauss(0, 0.6)
        trust = rng.gauss(0, 0.6)
        for occasion in range(1, 26):
            if occasion > 1:
                previous_emotion, previous_trust = emotion, trust
                emotion = (
                    0.42 * previous_emotion
                    + 0.15 * previous_trust
                    + rng.gauss(0, 0.55)
                )
                trust = (
                    0.38 * previous_trust
                    + 0.22 * previous_emotion
                    + rng.gauss(0, 0.55)
                )
            observed_emotion = emotion_mean + emotion
            observed_trust = trust_mean + trust
            scenario = f"S{(person + occasion) % 5 + 1}"
            exposure = rng.randint(15, 60)
            purchase_probability = 1 / (
                1 + math.exp(-(-0.7 + 0.35 * observed_trust))
            )
            click_probability = min(
                0.9,
                max(0.02, 1 / (1 + math.exp(-(0.1 + 0.25 * observed_trust)))),
            )
            rows.append(
                {
                    "person_id": f"I{person:03d}",
                    "occasion": occasion,
                    "emotion": round(observed_emotion, 3),
                    "ai_trust": round(observed_trust, 3),
                    "scenario": scenario,
                    "purchase": int(rng.random() < purchase_probability),
                    "aigc_clicks": sum(
                        int(rng.random() < click_probability) for _ in range(10)
                    ),
                    "exposure_minutes": exposure,
                }
            )
    _write(OUTPUT / "intensive-esm-demo.csv", fields, rows)


def _write(path: Path, fields: list[str], rows: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as target:
        writer = csv.DictWriter(target, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


if __name__ == "__main__":
    generate_questionnaire()
    generate_mediation()
    generate_longitudinal()
    generate_diary()
    generate_intensive_esm()
