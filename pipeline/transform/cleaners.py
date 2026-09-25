from __future__ import annotations

from datetime import datetime, timezone

import pandas as pd

from pipeline.naming import to_snake_case


NUMERIC_COLUMNS = {
    "year",
    "coverage",
    "doses",
    "population",
    "cases",
}

INTEGER_COLUMNS = {
    "year",
    "doses",
    "population",
    "cases",
}


def normalize_dataframe(
    dataframe: pd.DataFrame,
) -> pd.DataFrame:
    df = dataframe.copy()
    df.columns = [to_snake_case(column) for column in df.columns]

    for column in df.columns:
        if pd.api.types.is_object_dtype(df[column]):
            df[column] = (
                df[column]
                .astype("string")
                .str.strip()
                .replace("", pd.NA)
            )

    for column in NUMERIC_COLUMNS.intersection(df.columns):
        df[column] = pd.to_numeric(
            df[column],
            errors="coerce",
        )

        if column in INTEGER_COLUMNS:
            df[column] = df[column].astype("Int64")

    df["_ingested_at"] = datetime.now(timezone.utc)
    return df
