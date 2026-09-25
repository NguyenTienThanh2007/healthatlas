import pandas as pd

from pipeline.quality.scoring import (
    completeness_score,
    consistency_score,
    freshness_score,
    score_run,
    score_table,
    uniqueness_score,
)


def test_completeness_score():
    df = pd.DataFrame({"a": [1, 2], "b": [1, None]})
    assert completeness_score(df) == 75.0


def test_uniqueness_score():
    df = pd.DataFrame({"a": [1, 1, 2]})
    assert uniqueness_score(df) == 66.67


def test_consistency_score():
    assert consistency_score(100, 100) == 100.0
    assert consistency_score(100, 90) == 90.0


def test_freshness_score():
    df = pd.DataFrame({"year": [2023, 2024]})
    assert freshness_score(df, reference_year=2026) == 90.0


def test_table_and_run_scores():
    df = pd.DataFrame({"year": [2025, 2025], "value": [1, 2]})
    table = score_table(
        "example",
        df,
        source_rows=2,
        target_rows=2,
        warning_count=0,
        reference_year=2026,
    )
    assert table.overall_score == 100.0
    run = score_run([table])
    assert run["overall_score"] == 100.0
