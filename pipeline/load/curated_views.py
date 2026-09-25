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
        ON c.economy = e.economy_id
    LEFT JOIN {staging}.infection_type it
        ON i.inf_type = it.id
    LEFT JOIN {staging}.country_population p
        ON i.country = p.country
       AND i.year = p.year
    """,
]


def build_curated_views(
    engine: Engine,
    staging_schema: str,
    curated_schema: str,
) -> None:
    staging = '"' + staging_schema.replace('"', '""') + '"'
    curated = '"' + curated_schema.replace('"', '""') + '"'

    with engine.begin() as connection:
        connection.execute(
            text(
                f"CREATE SCHEMA IF NOT EXISTS {curated}"
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
