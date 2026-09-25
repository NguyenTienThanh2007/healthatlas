from __future__ import annotations

import pandas as pd
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine


def create_postgres_engine(postgres_url: str) -> Engine:
    return create_engine(
        postgres_url,
        future=True,
        pool_pre_ping=True,
    )


def ensure_schema(
    engine: Engine,
    schema_name: str,
) -> None:
    safe_schema = schema_name.replace('"', '""')
    with engine.begin() as connection:
        connection.execute(
            text(
                f'CREATE SCHEMA IF NOT EXISTS "{safe_schema}"'
            )
        )


def load_dataframe(
    engine: Engine,
    schema_name: str,
    table_name: str,
    dataframe: pd.DataFrame,
) -> None:
    dataframe.to_sql(
        table_name,
        engine,
        schema=schema_name,
        if_exists="replace",
        index=False,
        method="multi",
        chunksize=1000,
    )


def target_row_count(
    engine: Engine,
    schema_name: str,
    table_name: str,
) -> int:
    safe_schema = schema_name.replace('"', '""')
    safe_table = table_name.replace('"', '""')

    with engine.connect() as connection:
        count = connection.execute(
            text(
                f'SELECT COUNT(*) '
                f'FROM "{safe_schema}"."{safe_table}"'
            )
        ).scalar_one()

    return int(count)
