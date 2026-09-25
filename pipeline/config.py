from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv


ROOT_DIR = Path(__file__).resolve().parents[1]
load_dotenv(ROOT_DIR / ".env")


@dataclass(frozen=True)
class Settings:
    sqlite_path: Path
    postgres_url: str
    staging_schema: str
    curated_schema: str
    log_level: str


def get_settings() -> Settings:
    sqlite_value = os.getenv("SQLITE_PATH", "immunisation-2.db")
    sqlite_path = (ROOT_DIR / sqlite_value).resolve()

    return Settings(
        sqlite_path=sqlite_path,
        postgres_url=os.getenv(
            "POSTGRES_URL",
            "postgresql+psycopg://postgres:postgres@localhost:5432/healthatlas",
        ),
        staging_schema=os.getenv("STAGING_SCHEMA", "staging"),
        curated_schema=os.getenv("CURATED_SCHEMA", "curated"),
        log_level=os.getenv("LOG_LEVEL", "INFO").upper(),
    )
