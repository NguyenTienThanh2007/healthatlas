from __future__ import annotations

import json
from datetime import datetime
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.engine import Engine

from pipeline.quality.scoring import TableQuality


def ensure_meta_schema(engine: Engine) -> None:
    statements = [
        "CREATE SCHEMA IF NOT EXISTS meta",
        """
        CREATE TABLE IF NOT EXISTS meta.pipeline_run (
            run_id UUID PRIMARY KEY,
            started_at TIMESTAMPTZ NOT NULL,
            finished_at TIMESTAMPTZ NOT NULL,
            status TEXT NOT NULL,
            source_table_count INTEGER NOT NULL,
            tables_loaded INTEGER NOT NULL,
            row_count_mismatches INTEGER NOT NULL,
            validation_issue_count INTEGER NOT NULL,
            completeness NUMERIC(5,2) NOT NULL,
            validity NUMERIC(5,2) NOT NULL,
            consistency NUMERIC(5,2) NOT NULL,
            freshness NUMERIC(5,2) NOT NULL,
            uniqueness NUMERIC(5,2) NOT NULL,
            overall_score NUMERIC(5,2) NOT NULL,
            metadata_json JSONB NOT NULL DEFAULT '{}'::jsonb
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS meta.table_quality (
            run_id UUID NOT NULL
                REFERENCES meta.pipeline_run(run_id)
                ON DELETE CASCADE,
            table_name TEXT NOT NULL,
            row_count BIGINT NOT NULL,
            completeness NUMERIC(5,2) NOT NULL,
            validity NUMERIC(5,2) NOT NULL,
            consistency NUMERIC(5,2) NOT NULL,
            freshness NUMERIC(5,2) NOT NULL,
            uniqueness NUMERIC(5,2) NOT NULL,
            overall_score NUMERIC(5,2) NOT NULL,
            PRIMARY KEY (run_id, table_name)
        )
        """,
    ]

    with engine.begin() as connection:
        for statement in statements:
            connection.execute(text(statement))


def save_quality_run(
    engine: Engine,
    run_id: UUID,
    started_at: datetime,
    finished_at: datetime,
    source_table_count: int,
    tables_loaded: int,
    row_count_mismatches: int,
    validation_issue_count: int,
    run_score: dict[str, float],
    table_scores: list[TableQuality],
    metadata: dict | None = None,
) -> None:
    ensure_meta_schema(engine)

    with engine.begin() as connection:
        connection.execute(
            text(
                """
                INSERT INTO meta.pipeline_run (
                    run_id,
                    started_at,
                    finished_at,
                    status,
                    source_table_count,
                    tables_loaded,
                    row_count_mismatches,
                    validation_issue_count,
                    completeness,
                    validity,
                    consistency,
                    freshness,
                    uniqueness,
                    overall_score,
                    metadata_json
                )
                VALUES (
                    :run_id,
                    :started_at,
                    :finished_at,
                    'success',
                    :source_table_count,
                    :tables_loaded,
                    :row_count_mismatches,
                    :validation_issue_count,
                    :completeness,
                    :validity,
                    :consistency,
                    :freshness,
                    :uniqueness,
                    :overall_score,
                    CAST(:metadata_json AS JSONB)
                )
                """
            ),
            {
                "run_id": run_id,
                "started_at": started_at,
                "finished_at": finished_at,
                "source_table_count": source_table_count,
                "tables_loaded": tables_loaded,
                "row_count_mismatches": row_count_mismatches,
                "validation_issue_count": validation_issue_count,
                "completeness": run_score["completeness"],
                "validity": run_score["validity"],
                "consistency": run_score["consistency"],
                "freshness": run_score["freshness"],
                "uniqueness": run_score["uniqueness"],
                "overall_score": run_score["overall_score"],
                "metadata_json": json.dumps(metadata or {}),
            },
        )

        for score in table_scores:
            connection.execute(
                text(
                    """
                    INSERT INTO meta.table_quality (
                        run_id,
                        table_name,
                        row_count,
                        completeness,
                        validity,
                        consistency,
                        freshness,
                        uniqueness,
                        overall_score
                    )
                    VALUES (
                        :run_id,
                        :table_name,
                        :row_count,
                        :completeness,
                        :validity,
                        :consistency,
                        :freshness,
                        :uniqueness,
                        :overall_score
                    )
                    """
                ),
                {
                    "run_id": run_id,
                    "table_name": score.table_name,
                    "row_count": score.row_count,
                    "completeness": score.completeness,
                    "validity": score.validity,
                    "consistency": score.consistency,
                    "freshness": score.freshness,
                    "uniqueness": score.uniqueness,
                    "overall_score": score.overall_score,
                },
            )
