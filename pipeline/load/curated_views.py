from __future__ import annotations

from sqlalchemy import text
from sqlalchemy.engine import Engine


VIEW_SQL = [
    """
    CREATE OR REPLACE VIEW {curated}.vaccination_enriched AS
    SELECT
        v.country,
        c.name AS country_name,
        c.region AS region_id,
        r.region AS region_name,
        c.economy AS economy_id,
        v.antigen,
        a.name AS antigen_name,
        v.year,
        v.coverage,
        v.doses,
        p.population,
        CASE
            WHEN p.population > 0
             AND v.doses IS NOT NULL
            THEN ROUND(
                (v.doses::numeric / p.population::numeric) * 100,
                4
            )
            ELSE NULL
        END AS population_vaccination_rate,
        v._ingested_at
    FROM {staging}.vaccination v
    LEFT JOIN {staging}.country c
        ON v.country = c.country_id
    LEFT JOIN {staging}.region r
        ON c.region = r.region_id
    LEFT JOIN {staging}.antigen a
        ON v.antigen = a.antigen_id
    LEFT JOIN {staging}.country_population p
        ON v.country = p.country
       AND v.year = p.year
    """,
    """
    CREATE OR REPLACE VIEW {curated}.infection_enriched AS
    SELECT
        i.country,
        c.name AS country_name,
        c.region AS region_id,
        r.region AS region_name,
        c.economy AS economy_id,
        e.phase AS economic_phase,
        i.inf_type,
        it.description AS infection_name,
        i.year,
        i.cases,
        p.population,
        CASE
            WHEN p.population > 0
             AND i.cases IS NOT NULL
            THEN ROUND(
                (i.cases::numeric / p.population::numeric) * 100000,
                4
            )
            ELSE NULL
        END AS cases_per_100k,
        i._ingested_at
    FROM {staging}.infection_data i
    LEFT JOIN {staging}.country c
        ON i.country = c.country_id
    LEFT JOIN {staging}.region r
        ON c.region = r.region_id
    LEFT JOIN {staging}.economy e
        ON CAST(c.economy AS TEXT)
         = CAST(e.economy_id AS TEXT)
    LEFT JOIN {staging}.infection_type it
        ON CAST(i.inf_type AS TEXT)
         = CAST(it.id AS TEXT)
    LEFT JOIN {staging}.country_population p
        ON i.country = p.country
       AND i.year = p.year
    """,
]


def _quoted(name: str) -> str:
    return '"' + name.replace('"', '""') + '"'


def drop_curated_views(
    engine: Engine,
    curated_schema: str,
) -> None:
    """
    Drop HealthAtlas curated views before replacing staging tables.

    pandas.to_sql(..., if_exists="replace") drops and recreates staging
    tables. PostgreSQL will refuse to drop a table while a view depends on
    it, so a full refresh must remove the dependent views first and rebuild
    them after the load.
    """
    curated = _quoted(curated_schema)

    with engine.begin() as connection:
        # Drop dependent/derived views first when more are added later.
        connection.execute(
            text(
                f"DROP VIEW IF EXISTS "
                f"{curated}.infection_enriched"
            )
        )
        connection.execute(
            text(
                f"DROP VIEW IF EXISTS "
                f"{curated}.vaccination_enriched"
            )
        )


def build_curated_views(
    engine: Engine,
    staging_schema: str,
    curated_schema: str,
) -> None:
    staging = _quoted(staging_schema)
    curated = _quoted(curated_schema)

    with engine.begin() as connection:
        connection.execute(
            text(
                f"CREATE SCHEMA IF NOT EXISTS "
                f"{curated}"
            )
        )

        for template in VIEW_SQL:
            connection.execute(
                text(
                    template.format(
                        staging=staging,
                        curated=curated,
                    )
                )
            )
