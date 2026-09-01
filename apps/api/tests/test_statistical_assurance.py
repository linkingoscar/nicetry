from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]


def test_metamorphic_suite_covers_declared_invariance_contracts() -> None:
    metamorphic = (
        ROOT / "engine" / "R" / "tests" / "testthat" / "test-metamorphic-statistical-properties.R"
    ).read_text(encoding="utf-8")
    confidence = (
        ROOT / "engine" / "R" / "tests" / "testthat" / "test-confidence-level-conformance.R"
    ).read_text(encoding="utf-8")
    seed = (
        ROOT / "engine" / "R" / "tests" / "testthat" / "test-seed-utils.R"
    ).read_text(encoding="utf-8")
    required_properties = (
        "row permutation preserves OLS estimates",
        "variable renaming preserves OLS estimates",
        "OLS scale and translation equivariance",
        "factor reference preserves fitted values",
        "sample flow conserves rows and clusters",
        "cluster label permutation preserves CR0 inference",
    )
    assert all(token in metamorphic for token in required_properties)
    assert "same seed reproduces the same RNG stream" in seed
    assert "declared confidence matrix" in confidence
    assert "researchpath-counterexample-" in metamorphic


def test_mutation_suite_names_and_kills_every_required_statistical_fault() -> None:
    suite = (
        ROOT / "engine" / "R" / "tests" / "testthat" / "test-metamorphic-statistical-properties.R"
    ).read_text(encoding="utf-8")
    required_mutants = (
        "fixed_1_96",
        "wrong_residual_df",
        "ignore_cluster",
        "mislabel_bc_as_bca",
        "drop_structured_warning",
        "swap_raw_and_adjusted_p",
    )
    assert all(mutant in suite for mutant in required_mutants)
    assert "all(mutant_kills)" in suite
    assert "survivors = names(mutant_kills)[!mutant_kills]" in suite
