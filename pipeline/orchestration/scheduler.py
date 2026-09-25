from __future__ import annotations

import os

from prefect.schedules import Cron

from pipeline.orchestration.prefect_flow import (
    healthatlas_etl_flow,
)


DEFAULT_CRON = "0 6 * * *"
DEFAULT_TIMEZONE = "Asia/Ho_Chi_Minh"
DEFAULT_DEPLOYMENT_NAME = "healthatlas-daily"


def get_schedule_settings() -> tuple[str, str, str]:
    cron = os.getenv(
        "PREFECT_CRON",
        DEFAULT_CRON,
    )
    timezone = os.getenv(
        "PREFECT_TIMEZONE",
        DEFAULT_TIMEZONE,
    )
    deployment_name = os.getenv(
        "PREFECT_DEPLOYMENT_NAME",
        DEFAULT_DEPLOYMENT_NAME,
    )

    return cron, timezone, deployment_name


def build_schedule() -> Cron:
    cron, timezone, _ = get_schedule_settings()

    return Cron(
        cron,
        timezone=timezone,
    )


def serve_healthatlas() -> None:
    cron, timezone, deployment_name = (
        get_schedule_settings()
    )

    print("Starting HealthAtlas Prefect scheduler")
    print(f"Deployment: {deployment_name}")
    print(f"Cron: {cron}")
    print(f"Timezone: {timezone}")
    print(
        "Keep this process running for local "
        "scheduled execution."
    )

    healthatlas_etl_flow.serve(
        name=deployment_name,
        schedule=build_schedule(),
        pause_on_shutdown=False,
        tags=[
            "healthatlas",
            "etl",
            "scheduled",
        ],
        description=(
            "Scheduled HealthAtlas ETL pipeline "
            "for staging, warehouse, analytics "
            "marts, and data quality."
        ),
    )


if __name__ == "__main__":
    serve_healthatlas()
