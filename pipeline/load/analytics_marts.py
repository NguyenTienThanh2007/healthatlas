from __future__ import annotations

from sqlalchemy import text
from sqlalchemy.engine import Engine


MART_VIEWS = (
    "country_health_summary",
    "vaccination_trends",
    "infection_burden",
)


def _quoted(name: str) -> str:
    return '"' + name.replace('"', '""') + '"'


def build_analytics_marts(
    engine: Engine,
    analytics_schema: str = "analytics",
    warehouse_schema: str = "warehouse",
) -> dict:
    analytics = _quoted(analytics_schema)
    warehouse = _quoted(warehouse_schema)

    statements = [
        f"CREATE SCHEMA IF NOT EXISTS {analytics}",
        f"""
        CREATE OR REPLACE VIEW {analytics}.vaccination_trends AS
        SELECT
            c.country_id,
            c.country_name,
            r.region_id,
            r.region_name,
            a.antigen_id,
            a.antigen_name,
            d.year,
            COUNT(*) AS record_count,
            ROUND(AVG(f.coverage)::numeric, 2) AS avg_coverage,
            SUM(f.doses) AS total_doses,
            SUM(f.target_num_numeric) AS total_target_population
        FROM {warehouse}.fact_vaccination f
        LEFT JOIN {warehouse}.dim_country c
            ON f.country_key = c.country_key
        LEFT JOIN {warehouse}.dim_region r
            ON c.region_key = r.region_key
        LEFT JOIN {warehouse}.dim_antigen a
            ON f.antigen_key = a.antigen_key
        LEFT JOIN {warehouse}.dim_date d
            ON f.date_key = d.date_key
        GROUP BY
            c.country_id,
            c.country_name,
            r.region_id,
            r.region_name,
            a.antigen_id,
            a.antigen_name,
            d.year
        """,
        f"""
        CREATE OR REPLACE VIEW {analytics}.infection_burden AS
        SELECT
            c.country_id,
            c.country_name,
            r.region_id,
            r.region_name,
            i.infection_id,
            i.infection_name,
            d.year,
            SUM(f.cases) AS total_cases,
            MAX(p.population) AS population,
            CASE
                WHEN MAX(p.population) > 0
                THEN ROUND(
                    (
                        SUM(f.cases)::numeric
                        / MAX(p.population)::numeric
                    ) * 100000,
                    4
                )
                ELSE NULL
            END AS cases_per_100k
        FROM {warehouse}.fact_infection f
        LEFT JOIN {warehouse}.dim_country c
            ON f.country_key = c.country_key
        LEFT JOIN {warehouse}.dim_region r
            ON c.region_key = r.region_key
        LEFT JOIN {warehouse}.dim_infection i
            ON f.infection_key = i.infection_key
        LEFT JOIN {warehouse}.dim_date d
            ON f.date_key = d.date_key
        LEFT JOIN {warehouse}.fact_population p
            ON f.country_key = p.country_key
           AND f.date_key = p.date_key
        GROUP BY
            c.country_id,
            c.country_name,
            r.region_id,
            r.region_name,
            i.infection_id,
            i.infection_name,
            d.year
        """,
        f"""
        CREATE OR REPLACE VIEW {analytics}.country_health_summary AS
        WITH vaccination AS (
            SELECT
                country_key,
                MAX(date_key) AS latest_vaccination_year,
                ROUND(AVG(coverage)::numeric, 2) AS avg_coverage,
                SUM(doses) AS total_doses
            FROM {warehouse}.fact_vaccination
            GROUP BY country_key
        ),
        infection AS (
            SELECT
                country_key,
                MAX(date_key) AS latest_infection_year,
                SUM(cases) AS total_cases
            FROM {warehouse}.fact_infection
            GROUP BY country_key
        ),
        population AS (
            SELECT DISTINCT ON (country_key)
                country_key,
                date_key AS latest_population_year,
                population
            FROM {warehouse}.fact_population
            WHERE country_key IS NOT NULL
            ORDER BY country_key, date_key DESC
        )
        SELECT
            c.country_id,
            c.country_name,
            r.region_id,
            r.region_name,
            c.economy_id,
            c.economic_phase,
            v.latest_vaccination_year,
            v.avg_coverage,
            v.total_doses,
            i.latest_infection_year,
            i.total_cases,
            p.latest_population_year,
            p.population
        FROM {warehouse}.dim_country c
        LEFT JOIN {warehouse}.dim_region r
            ON c.region_key = r.region_key
        LEFT JOIN vaccination v
            ON c.country_key = v.country_key
        LEFT JOIN infection i
            ON c.country_key = i.country_key
        LEFT JOIN population p
            ON c.country_key = p.country_key
        """,
    ]

    with engine.begin() as connection:
        for statement in statements:
            connection.execute(text(statement))

        counts = {}
        for view_name in MART_VIEWS:
            counts[view_name] = int(
                connection.execute(
                    text(
                        f"SELECT COUNT(*) "
                        f"FROM {analytics}.{_quoted(view_name)}"
                    )
                ).scalar_one()
            )

    return {
        "schema": analytics_schema,
        "views_built": len(MART_VIEWS),
        "view_counts": counts,
    }
