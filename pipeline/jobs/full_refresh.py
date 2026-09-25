from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

from pipeline.config import Settings
from pipeline.extract.sqlite_source import (
    connect_sqlite,
    extract_table,
    list_tables,
    source_row_count,
)
from pipeline.load.curated_views import build_curated_views
from pipeline.load.postgres_loader import (
    create_postgres_engine,
    ensure_schema,
    load_dataframe,
    target_row_count,
)
from pipeline.logging_config import configure_logging
from pipeline.naming import to_snake_case
from pipeline.transform.cleaners import normalize_dataframe
from pipeline.validation.checks import (
    validate_dataframe,
    validate_required_tables,
)


def run_full_refresh(
    settings: Settings,
) -> dict:
    logger = configure_logging(settings.log_level)
    root = Path(__file__).resolve().parents[2]
    output_dir = root / "data" / "curated"
    output_dir.mkdir(parents=True, exist_ok=True)

    logger.info("Starting HealthAtlas full refresh")
    logger.info("SQLite source: %s", settings.sqlite_path)

    sqlite_connection = connect_sqlite(
        settings.sqlite_path
    )

    source_tables = list_tables(sqlite_connection)
    validation_issues = validate_required_tables(
        source_tables
    )

    fatal = [
        issue
        for issue in validation_issues
        if issue.severity == "ERROR"
    ]

    if fatal:
        sqlite_connection.close()
        raise RuntimeError(
            "Required SQLite source tables are missing."
        )

    engine = create_postgres_engine(
        settings.postgres_url
    )
    ensure_schema(
        engine,
        settings.staging_schema,
    )
    ensure_schema(
        engine,
        settings.curated_schema,
    )

    audit_rows = []

    for source_table in source_tables:
        target_table = to_snake_case(
            source_table
        )

        logger.info(
            "Processing %s -> %s.%s",
            source_table,
            settings.staging_schema,
            target_table,
        )

        source_count = source_row_count(
            sqlite_connection,
            source_table,
        )

        raw = extract_table(
            sqlite_connection,
            source_table,
        )

        cleaned = normalize_dataframe(raw)

        validation_issues.extend(
            validate_dataframe(
                source_table,
                cleaned,
            )
        )

        load_dataframe(
            engine,
            settings.staging_schema,
            target_table,
            cleaned,
        )

        loaded_count = target_row_count(
            engine,
            settings.staging_schema,
            target_table,
        )

        audit_rows.append(
            {
                "source_table": source_table,
                "target_table": target_table,
                "sqlite_rows": source_count,
                "postgres_rows": loaded_count,
                "rows_match": (
                    source_count == loaded_count
                ),
            }
        )

    sqlite_connection.close()

    logger.info(
        "Building curated analytical views"
    )

    build_curated_views(
        engine,
        settings.staging_schema,
        settings.curated_schema,
    )

    audit = pd.DataFrame(audit_rows)

    audit_file = (
        output_dir
        / "source_vs_postgres_counts.csv"
    )
    audit.to_csv(
        audit_file,
        index=False,
    )

    validation_file = (
        output_dir
        / "validation_report.json"
    )
    validation_file.write_text(
        json.dumps(
            [
                issue.to_dict()
                for issue in validation_issues
            ],
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    summary = {
        "finished_at": datetime.now(
            timezone.utc
        ).isoformat(),
        "source_tables": len(source_tables),
        "tables_loaded": len(audit_rows),
        "row_count_mismatches": (
            int((~audit["rows_match"]).sum())
            if not audit.empty
            else 0
        ),
        "validation_issues": len(
            validation_issues
        ),
        "audit_file": str(audit_file),
        "validation_file": str(
            validation_file
        ),
    }

    logger.info(
        "Pipeline finished: %s",
        summary,
    )

    return summary
