from __future__ import annotations

from prefect import flow, get_run_logger, task

from pipeline.config import get_settings
from pipeline.jobs.full_refresh import run_full_refresh


@task(
    name="healthatlas-full-refresh",
    retries=2,
    retry_delay_seconds=30,
)
def run_full_refresh_task() -> dict:
    logger = get_run_logger()

    logger.info(
        "Starting HealthAtlas full refresh task"
    )

    settings = get_settings()
    summary = run_full_refresh(settings)

    logger.info(
        "HealthAtlas refresh completed with "
        "%s source tables, %s row-count mismatches",
        summary.get("source_tables"),
        summary.get("row_count_mismatches"),
    )

    return summary


@flow(
    name="healthatlas-etl",
    log_prints=True,
)
def healthatlas_etl_flow() -> dict:
    logger = get_run_logger()

    logger.info(
        "Launching HealthAtlas ETL orchestration"
    )

    summary = run_full_refresh_task()

    logger.info(
        "HealthAtlas ETL orchestration finished"
    )

    return summary


if __name__ == "__main__":
    healthatlas_etl_flow()
