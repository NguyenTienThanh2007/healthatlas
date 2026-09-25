from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import dotenv_values
from sqlalchemy import URL


ROOT_DIR = Path(__file__).resolve().parents[1]
ENV_FILE = ROOT_DIR / ".env"

env_values = dotenv_values(ENV_FILE)


def get_value(
    name: str,
    default: str | None = None,
) -> str | None:
    value = env_values.get(name)

    if value not in (None, ""):
        return value

    value = os.getenv(name)

    if value not in (None, ""):
        return value

    return default


@dataclass(frozen=True)
class Settings:
    sqlite_path: Path
    postgres_url: URL
    staging_schema: str
    curated_schema: str
    log_level: str


def get_settings() -> Settings:
    sqlite_value = get_value(
        "SQLITE_PATH",
        "immunisation-2.db",
    )

    sqlite_path = (
        ROOT_DIR / sqlite_value
    ).resolve()

    postgres_url = URL.create(
        drivername="postgresql+psycopg",
        username=get_value(
            "DB_USER",
            "nguyentienthanh",
        ),
        password=get_value(
            "DB_PASSWORD",
        ),
        host=get_value(
            "DB_HOST",
            "localhost",
        ),
        port=int(
            get_value(
                "DB_PORT",
                "5432",
            )
        ),
        database=get_value(
            "DB_NAME",
            "healthatlas",
        ),
    )

    return Settings(
        sqlite_path=sqlite_path,
        postgres_url=postgres_url,
        staging_schema=get_value(
            "STAGING_SCHEMA",
            "staging",
        ),
        curated_schema=get_value(
            "CURATED_SCHEMA",
            "curated",
        ),
        log_level=get_value(
            "LOG_LEVEL",
            "INFO",
        ).upper(),
    )
