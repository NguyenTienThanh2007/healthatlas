from __future__ import annotations

import sqlite3
from pathlib import Path

import pandas as pd


def connect_sqlite(path: Path) -> sqlite3.Connection:
    if not path.exists():
        raise FileNotFoundError(
            f"SQLite database not found: {path}. "
            "Check SQLITE_PATH in .env."
        )

    connection = sqlite3.connect(path)
    connection.row_factory = sqlite3.Row
    return connection


def list_tables(connection: sqlite3.Connection) -> list[str]:
    rows = connection.execute(
        """
        SELECT name
        FROM sqlite_master
        WHERE type = 'table'
          AND name NOT LIKE 'sqlite_%'
        ORDER BY name
        """
    ).fetchall()

    return [row["name"] for row in rows]


def extract_table(
    connection: sqlite3.Connection,
    table_name: str,
) -> pd.DataFrame:
    escaped = table_name.replace('"', '""')
    return pd.read_sql_query(
        f'SELECT * FROM "{escaped}"',
        connection,
    )


def source_row_count(
    connection: sqlite3.Connection,
    table_name: str,
) -> int:
    escaped = table_name.replace('"', '""')
    result = connection.execute(
        f'SELECT COUNT(*) AS total FROM "{escaped}"'
    ).fetchone()
    return int(result["total"])
