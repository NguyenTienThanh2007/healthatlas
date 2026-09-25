from __future__ import annotations

from sqlalchemy import text
from sqlalchemy.engine import Engine


DIMENSION_TABLES = (
    "dim_region",
    "dim_country",
    "dim_antigen",
    "dim_infection",
    "dim_date",
)

FACT_TABLES = (
    "fact_vaccination",
    "fact_population",
    "fact_infection",
)

WAREHOUSE_TABLES = DIMENSION_TABLES + FACT_TABLES


def _quoted(name: str) -> str:
    return '"' + name.replace('"', '""') + '"'


def build_warehouse(
    engine: Engine,
    staging_schema: str,
    warehouse_schema: str = "warehouse",
) -> dict:
    staging = _quoted(staging_schema)
    warehouse = _quoted(warehouse_schema)

    ddl = [
        f"CREATE SCHEMA IF NOT EXISTS {warehouse}",
        f'''
        CREATE TABLE IF NOT EXISTS {warehouse}.dim_region (
            region_key BIGSERIAL PRIMARY KEY,
            region_id TEXT UNIQUE NOT NULL,
            region_name TEXT,
            source_ingested_at TIMESTAMPTZ
        )
        ''',
        f'''
        CREATE TABLE IF NOT EXISTS {warehouse}.dim_antigen (
            antigen_key BIGSERIAL PRIMARY KEY,
            antigen_id TEXT UNIQUE NOT NULL,
            antigen_name TEXT,
            source_ingested_at TIMESTAMPTZ
        )
        ''',
        f'''
        CREATE TABLE IF NOT EXISTS {warehouse}.dim_infection (
            infection_key BIGSERIAL PRIMARY KEY,
            infection_id TEXT UNIQUE NOT NULL,
            infection_name TEXT,
            source_ingested_at TIMESTAMPTZ
        )
        ''',
        f'''
        CREATE TABLE IF NOT EXISTS {warehouse}.dim_date (
            date_key INTEGER PRIMARY KEY,
            year INTEGER UNIQUE NOT NULL,
            decade INTEGER NOT NULL
        )
        ''',
        f'''
        CREATE TABLE IF NOT EXISTS {warehouse}.dim_country (
            country_key BIGSERIAL PRIMARY KEY,
            country_id TEXT UNIQUE NOT NULL,
            country_name TEXT,
            region_key BIGINT REFERENCES {warehouse}.dim_region(region_key),
            economy_id TEXT,
            economic_phase TEXT,
            source_ingested_at TIMESTAMPTZ
        )
        ''',
        f'''
        CREATE TABLE IF NOT EXISTS {warehouse}.fact_vaccination (
            vaccination_fact_key BIGSERIAL PRIMARY KEY,
            country_key BIGINT REFERENCES {warehouse}.dim_country(country_key),
            antigen_key BIGINT REFERENCES {warehouse}.dim_antigen(antigen_key),
            infection_key BIGINT REFERENCES {warehouse}.dim_infection(infection_key),
            date_key INTEGER REFERENCES {warehouse}.dim_date(date_key),
            country_id_raw TEXT,
            antigen_id_raw TEXT,
            infection_id_raw TEXT,
            target_num_raw TEXT,
            target_num_numeric NUMERIC,
            doses BIGINT,
            coverage DOUBLE PRECISION,
            source_ingested_at TIMESTAMPTZ
        )
        ''',
        f'''
        CREATE TABLE IF NOT EXISTS {warehouse}.fact_population (
            population_fact_key BIGSERIAL PRIMARY KEY,
            country_key BIGINT REFERENCES {warehouse}.dim_country(country_key),
            date_key INTEGER REFERENCES {warehouse}.dim_date(date_key),
            country_id_raw TEXT,
            population BIGINT,
            source_ingested_at TIMESTAMPTZ
        )
        ''',
        f'''
        CREATE TABLE IF NOT EXISTS {warehouse}.fact_infection (
            infection_fact_key BIGSERIAL PRIMARY KEY,
            country_key BIGINT REFERENCES {warehouse}.dim_country(country_key),
            infection_key BIGINT REFERENCES {warehouse}.dim_infection(infection_key),
            date_key INTEGER REFERENCES {warehouse}.dim_date(date_key),
            country_id_raw TEXT,
            infection_id_raw TEXT,
            cases BIGINT,
            source_ingested_at TIMESTAMPTZ
        )
        ''',
        f"CREATE INDEX IF NOT EXISTS idx_fact_vaccination_country ON {warehouse}.fact_vaccination(country_key)",
        f"CREATE INDEX IF NOT EXISTS idx_fact_vaccination_antigen ON {warehouse}.fact_vaccination(antigen_key)",
        f"CREATE INDEX IF NOT EXISTS idx_fact_vaccination_date ON {warehouse}.fact_vaccination(date_key)",
        f"CREATE INDEX IF NOT EXISTS idx_fact_population_country ON {warehouse}.fact_population(country_key)",
        f"CREATE INDEX IF NOT EXISTS idx_fact_population_date ON {warehouse}.fact_population(date_key)",
        f"CREATE INDEX IF NOT EXISTS idx_fact_infection_country ON {warehouse}.fact_infection(country_key)",
        f"CREATE INDEX IF NOT EXISTS idx_fact_infection_type ON {warehouse}.fact_infection(infection_key)",
        f"CREATE INDEX IF NOT EXISTS idx_fact_infection_date ON {warehouse}.fact_infection(date_key)",
    ]

    with engine.begin() as connection:
        for statement in ddl:
            connection.execute(text(statement))

        connection.execute(
            text(
                f'''
                TRUNCATE TABLE
                    {warehouse}.fact_vaccination,
                    {warehouse}.fact_population,
                    {warehouse}.fact_infection,
                    {warehouse}.dim_country,
                    {warehouse}.dim_region,
                    {warehouse}.dim_antigen,
                    {warehouse}.dim_infection,
                    {warehouse}.dim_date
                RESTART IDENTITY CASCADE
                '''
            )
        )

        connection.execute(
            text(
                f'''
                INSERT INTO {warehouse}.dim_region (
                    region_id, region_name, source_ingested_at
                )
                SELECT region_id, region, _ingested_at
                FROM {staging}.region
                WHERE region_id IS NOT NULL
                ORDER BY region_id
                '''
            )
        )

        connection.execute(
            text(
                f'''
                INSERT INTO {warehouse}.dim_antigen (
                    antigen_id, antigen_name, source_ingested_at
                )
                SELECT antigen_id, name, _ingested_at
                FROM {staging}.antigen
                WHERE antigen_id IS NOT NULL
                ORDER BY antigen_id
                '''
            )
        )

        connection.execute(
            text(
                f'''
                INSERT INTO {warehouse}.dim_infection (
                    infection_id, infection_name, source_ingested_at
                )
                SELECT id, description, _ingested_at
                FROM {staging}.infection_type
                WHERE id IS NOT NULL
                ORDER BY id
                '''
            )
        )

        connection.execute(
            text(
                f'''
                INSERT INTO {warehouse}.dim_date (
                    date_key, year, decade
                )
                SELECT year_value, year_value, (year_value / 10) * 10
                FROM (
                    SELECT DISTINCT year::INTEGER AS year_value
                    FROM {staging}.vaccination
                    WHERE year IS NOT NULL
                    UNION
                    SELECT DISTINCT year::INTEGER AS year_value
                    FROM {staging}.infection_data
                    WHERE year IS NOT NULL
                    UNION
                    SELECT DISTINCT year::INTEGER AS year_value
                    FROM {staging}.country_population
                    WHERE year IS NOT NULL
                    UNION
                    SELECT DISTINCT year_i_d::INTEGER AS year_value
                    FROM {staging}.year_date
                    WHERE year_i_d IS NOT NULL
                ) years
                WHERE year_value BETWEEN 1900 AND 2100
                ORDER BY year_value
                '''
            )
        )

        connection.execute(
            text(
                f'''
                INSERT INTO {warehouse}.dim_country (
                    country_id,
                    country_name,
                    region_key,
                    economy_id,
                    economic_phase,
                    source_ingested_at
                )
                SELECT
                    c.country_id,
                    c.name,
                    r.region_key,
                    c.economy,
                    e.phase,
                    c._ingested_at
                FROM {staging}.country c
                LEFT JOIN {warehouse}.dim_region r
                    ON c.region = r.region_id
                LEFT JOIN {staging}.economy e
                    ON CAST(c.economy AS TEXT) = CAST(e.economy_id AS TEXT)
                WHERE c.country_id IS NOT NULL
                ORDER BY c.country_id
                '''
            )
        )

        connection.execute(
            text(
                f'''
                INSERT INTO {warehouse}.fact_vaccination (
                    country_key,
                    antigen_key,
                    infection_key,
                    date_key,
                    country_id_raw,
                    antigen_id_raw,
                    infection_id_raw,
                    target_num_raw,
                    target_num_numeric,
                    doses,
                    coverage,
                    source_ingested_at
                )
                SELECT
                    dc.country_key,
                    da.antigen_key,
                    di.infection_key,
                    dd.date_key,
                    v.country,
                    v.antigen,
                    v.inf_type,
                    v.target_num,
                    CASE
                        WHEN TRIM(COALESCE(v.target_num, ''))
                             ~ '^[0-9]+([.][0-9]+)?$'
                        THEN TRIM(v.target_num)::NUMERIC
                        ELSE NULL
                    END,
                    v.doses,
                    v.coverage,
                    v._ingested_at
                FROM {staging}.vaccination v
                LEFT JOIN {warehouse}.dim_country dc
                    ON v.country = dc.country_id
                LEFT JOIN {warehouse}.dim_antigen da
                    ON v.antigen = da.antigen_id
                LEFT JOIN {warehouse}.dim_infection di
                    ON v.inf_type = di.infection_id
                LEFT JOIN {warehouse}.dim_date dd
                    ON v.year = dd.year
                '''
            )
        )

        connection.execute(
            text(
                f'''
                INSERT INTO {warehouse}.fact_population (
                    country_key,
                    date_key,
                    country_id_raw,
                    population,
                    source_ingested_at
                )
                SELECT
                    dc.country_key,
                    dd.date_key,
                    p.country,
                    p.population,
                    p._ingested_at
                FROM {staging}.country_population p
                LEFT JOIN {warehouse}.dim_country dc
                    ON p.country = dc.country_id
                LEFT JOIN {warehouse}.dim_date dd
                    ON p.year = dd.year
                '''
            )
        )

        connection.execute(
            text(
                f'''
                INSERT INTO {warehouse}.fact_infection (
                    country_key,
                    infection_key,
                    date_key,
                    country_id_raw,
                    infection_id_raw,
                    cases,
                    source_ingested_at
                )
                SELECT
                    dc.country_key,
                    di.infection_key,
                    dd.date_key,
                    i.country,
                    i.inf_type,
                    i.cases,
                    i._ingested_at
                FROM {staging}.infection_data i
                LEFT JOIN {warehouse}.dim_country dc
                    ON i.country = dc.country_id
                LEFT JOIN {warehouse}.dim_infection di
                    ON i.inf_type = di.infection_id
                LEFT JOIN {warehouse}.dim_date dd
                    ON i.year = dd.year
                '''
            )
        )

        counts = {}
        for table_name in WAREHOUSE_TABLES:
            counts[table_name] = int(
                connection.execute(
                    text(
                        f"SELECT COUNT(*) FROM {warehouse}.{_quoted(table_name)}"
                    )
                ).scalar_one()
            )

        source_counts = {
            "fact_vaccination": int(
                connection.execute(
                    text(f"SELECT COUNT(*) FROM {staging}.vaccination")
                ).scalar_one()
            ),
            "fact_population": int(
                connection.execute(
                    text(f"SELECT COUNT(*) FROM {staging}.country_population")
                ).scalar_one()
            ),
            "fact_infection": int(
                connection.execute(
                    text(f"SELECT COUNT(*) FROM {staging}.infection_data")
                ).scalar_one()
            ),
        }

    fact_row_mismatches = sum(
        counts[name] != source_counts[name]
        for name in FACT_TABLES
    )

    return {
        "schema": warehouse_schema,
        "tables_loaded": len(WAREHOUSE_TABLES),
        "dimension_tables": len(DIMENSION_TABLES),
        "fact_tables": len(FACT_TABLES),
        "fact_row_mismatches": fact_row_mismatches,
        "table_counts": counts,
        "source_fact_counts": source_counts,
    }
