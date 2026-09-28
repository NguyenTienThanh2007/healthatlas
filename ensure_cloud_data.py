from __future__ import annotations

import sys

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine

from pipeline.config import get_settings
from pipeline.jobs.full_refresh import run_full_refresh


REQUIRED_ANALYTICS_RELATION = "analytics.country_health_summary"


def analytics_ready(engine: Engine) -> bool:
    with engine.connect() as connection:
        relation = connection.execute(
            text(
                """
                SELECT to_regclass(:relation_name)
                """
            ),
            {
                "relation_name": REQUIRED_ANALYTICS_RELATION,
            },
        ).scalar_one()

    return relation is not None


def main() -> int:
    settings = get_settings()
    engine = create_engine(
        settings.postgres_url,
        pool_pre_ping=True,
    )

    try:
        if analytics_ready(engine):
            print(
                "HealthAtlas cloud data is ready: "
                f"{REQUIRED_ANALYTICS_RELATION}"
            )
            return 0

        print(
            "HealthAtlas analytics layer is missing. "
            "Running one-time ETL bootstrap..."
        )

        run_full_refresh(settings)

        if not analytics_ready(engine):
            print(
                "ERROR: ETL completed but required analytics "
                "relation is still missing."
            )
            return 2

        print(
            "HealthAtlas cloud data bootstrap completed successfully."
        )
        return 0

    except Exception as exc:
        print(
            "ERROR: Cloud data bootstrap failed: "
            f"{exc}"
        )
        return 1
    finally:
        engine.dispose()


if __name__ == "__main__":
    sys.exit(main())
