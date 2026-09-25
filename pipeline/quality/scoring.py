from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone

import pandas as pd


@dataclass(frozen=True)
class TableQuality:
    table_name: str
    row_count: int
    completeness: float
    validity: float
    consistency: float
    freshness: float
    uniqueness: float
    overall_score: float

    def to_dict(self) -> dict:
        return asdict(self)


def _clamp(value: float) -> float:
    return max(0.0, min(100.0, value))


def completeness_score(df: pd.DataFrame) -> float:
    if df.empty:
        return 100.0
    visible = df.drop(columns=["_ingested_at"], errors="ignore")
    total_cells = visible.shape[0] * visible.shape[1]
    if total_cells == 0:
        return 100.0
    null_cells = int(visible.isna().sum().sum())
    return round(_clamp(100.0 * (1 - null_cells / total_cells)), 2)


def uniqueness_score(df: pd.DataFrame) -> float:
    if df.empty:
        return 100.0
    visible = df.drop(columns=["_ingested_at"], errors="ignore")
    duplicates = int(visible.duplicated().sum())
    return round(_clamp(100.0 * (1 - duplicates / max(len(visible), 1))), 2)


def validity_score(df: pd.DataFrame, warning_count: int) -> float:
    if df.empty:
        return 100.0
    penalty = warning_count / max(len(df), 1) * 100.0
    return round(_clamp(100.0 - penalty), 2)


def consistency_score(source_rows: int, target_rows: int) -> float:
    if source_rows == 0 and target_rows == 0:
        return 100.0
    denominator = max(source_rows, target_rows, 1)
    mismatch = abs(source_rows - target_rows)
    return round(_clamp(100.0 * (1 - mismatch / denominator)), 2)


def freshness_score(df: pd.DataFrame, reference_year: int | None = None) -> float:
    if reference_year is None:
        reference_year = datetime.now(timezone.utc).year
    if "year" not in df.columns:
        return 100.0
    years = pd.to_numeric(df["year"], errors="coerce").dropna()
    if years.empty:
        return 100.0
    lag = max(0, reference_year - int(years.max()))
    if lag <= 1:
        return 100.0
    return round(_clamp(100.0 - (lag - 1) * 10.0), 2)


def overall_score(completeness: float, validity: float, consistency: float, freshness: float, uniqueness: float) -> float:
    score = (
        completeness * 0.25
        + validity * 0.25
        + consistency * 0.20
        + freshness * 0.15
        + uniqueness * 0.15
    )
    return round(_clamp(score), 2)


def score_table(table_name: str, df: pd.DataFrame, source_rows: int, target_rows: int, warning_count: int = 0, reference_year: int | None = None) -> TableQuality:
    completeness = completeness_score(df)
    validity = validity_score(df, warning_count)
    consistency = consistency_score(source_rows, target_rows)
    freshness = freshness_score(df, reference_year)
    uniqueness = uniqueness_score(df)

    return TableQuality(
        table_name=table_name,
        row_count=len(df),
        completeness=completeness,
        validity=validity,
        consistency=consistency,
        freshness=freshness,
        uniqueness=uniqueness,
        overall_score=overall_score(completeness, validity, consistency, freshness, uniqueness),
    )


def score_run(table_scores: list[TableQuality]) -> dict[str, float]:
    if not table_scores:
        return {
            "completeness": 100.0,
            "validity": 100.0,
            "consistency": 100.0,
            "freshness": 100.0,
            "uniqueness": 100.0,
            "overall_score": 100.0,
        }

    total_rows = sum(max(score.row_count, 1) for score in table_scores)

    def weighted(attribute: str) -> float:
        value = sum(
            getattr(score, attribute) * max(score.row_count, 1)
            for score in table_scores
        ) / total_rows
        return round(value, 2)

    result = {
        "completeness": weighted("completeness"),
        "validity": weighted("validity"),
        "consistency": weighted("consistency"),
        "freshness": weighted("freshness"),
        "uniqueness": weighted("uniqueness"),
    }
    result["overall_score"] = overall_score(
        result["completeness"],
        result["validity"],
        result["consistency"],
        result["freshness"],
        result["uniqueness"],
    )
    return result
