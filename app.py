from flask import Flask, render_template, request, jsonify, abort
from pathlib import Path
from collections import defaultdict
import sqlite3

from sqlalchemy import create_engine, text

from pipeline.config import get_settings

app = Flask(__name__)

BASE_DIR = Path(__file__).resolve().parent

@app.get("/health")
def health_check():
    return jsonify(
        {
            "status": "ok",
            "service": "healthatlas",
        }
    )

DATABASE = BASE_DIR / "immunisation-2.db"
POSTGRES_ENGINE = create_engine(
    get_settings().postgres_url,
    pool_pre_ping=True,
)


def get_db_connection():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn


def table_exists(conn, table_name):
    return conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name = ?",
        [table_name],
    ).fetchone() is not None


def rows_to_dicts(rows):
    return [dict(row) for row in rows]


def clean_country_ids(values):
    result = []
    for raw in values:
        if not raw:
            continue
        for item in str(raw).split(","):
            value = item.strip().upper()
            if value and value not in result:
                result.append(value)
    return result[:4]


def query_list(conn, sql, params=()):
    return conn.execute(sql, params).fetchall()


# =========================
# OVERVIEW
# =========================

@app.route("/")
def landing():
    conn = get_db_connection()

    country_count = conn.execute("SELECT COUNT(*) AS total FROM Country").fetchone()["total"]
    antigen_count = conn.execute("SELECT COUNT(*) AS total FROM Antigen").fetchone()["total"]
    vaccination_count = conn.execute("SELECT COUNT(*) AS total FROM Vaccination").fetchone()["total"]
    infection_type_count = conn.execute("SELECT COUNT(*) AS total FROM Infection_Type").fetchone()["total"]
    region_count = conn.execute("SELECT COUNT(*) AS total FROM Region").fetchone()["total"]

    years = conn.execute("""
        SELECT MIN(year) AS first_year, MAX(year) AS last_year
        FROM Vaccination
    """).fetchone()

    latest_year = years["last_year"]

    latest_coverage = conn.execute("""
        SELECT
            ROUND(AVG(CAST(coverage AS REAL)), 1) AS average_coverage,
            COUNT(DISTINCT CASE WHEN CAST(coverage AS REAL) >= 90 THEN country END) AS countries_90,
            SUM(CASE WHEN TRIM(CAST(coverage AS TEXT)) = '' THEN 1 ELSE 0 END) AS missing_coverage,
            COUNT(*) AS total_rows
        FROM Vaccination
        WHERE year = ?
    """, [latest_year]).fetchone()

    total_rows = latest_coverage["total_rows"] or 0
    missing_rows = latest_coverage["missing_coverage"] or 0
    quality_score = round((total_rows - missing_rows) / total_rows * 100, 1) if total_rows else 0

    regional_snapshot = conn.execute("""
        SELECT
            Region.region AS region_name,
            ROUND(AVG(CAST(Vaccination.coverage AS REAL)), 1) AS average_coverage
        FROM Vaccination
        JOIN Country ON Vaccination.country = Country.CountryID
        JOIN Region ON Country.region = Region.RegionID
        WHERE Vaccination.year = ?
          AND TRIM(CAST(Vaccination.coverage AS TEXT)) != ''
        GROUP BY Region.RegionID, Region.region
        ORDER BY average_coverage DESC
    """, [latest_year]).fetchall()

    coverage_trend = conn.execute("""
        SELECT year, ROUND(AVG(CAST(coverage AS REAL)), 1) AS value
        FROM Vaccination
        WHERE TRIM(CAST(coverage AS TEXT)) != ''
        GROUP BY year
        ORDER BY year
    """).fetchall()

    conn.close()

    return render_template(
        "landing.html",
        country_count=country_count,
        antigen_count=antigen_count,
        vaccination_count=vaccination_count,
        infection_type_count=infection_type_count,
        region_count=region_count,
        first_year=years["first_year"],
        last_year=years["last_year"],
        latest_year=latest_year,
        average_coverage=latest_coverage["average_coverage"],
        countries_90=latest_coverage["countries_90"],
        quality_score=quality_score,
        regional_snapshot=regional_snapshot,
        coverage_trend=rows_to_dicts(coverage_trend),
    )



# =========================
# TRAVEL HEALTH PLANNER — PRODUCT PIVOT V1
# =========================

@app.route("/travel")
def travel():
    conn = get_db_connection()

    origin = (request.args.get("origin") or "").strip().upper()
    destination = (request.args.get("destination") or "").strip().upper()
    departure = (request.args.get("departure") or "").strip()
    duration = (request.args.get("duration") or "").strip()

    countries = conn.execute("""
        SELECT CountryID, name
        FROM Country
        ORDER BY name
    """).fetchall()

    destination_profile = None

    if destination:
        destination_profile = conn.execute("""
            SELECT
                Country.CountryID AS country_id,
                Country.name AS country_name,
                Region.region AS region_name,
                Economy.phase AS economic_phase
            FROM Country
            LEFT JOIN Region
                ON Country.region = Region.RegionID
            LEFT JOIN Economy
                ON Country.economy = Economy.economyID
            WHERE UPPER(Country.CountryID) = ?
        """, [destination]).fetchone()

        if destination_profile:
            profile = dict(destination_profile)

            latest_population = conn.execute("""
                SELECT year, population
                FROM CountryPopulation
                WHERE UPPER(country) = ?
                  AND population IS NOT NULL
                  AND population > 0
                ORDER BY year DESC
                LIMIT 1
            """, [destination]).fetchone()

            vaccination_snapshot = conn.execute("""
                SELECT
                    year,
                    ROUND(AVG(CAST(coverage AS REAL)), 1) AS average_coverage,
                    COUNT(DISTINCT antigen) AS antigen_count
                FROM Vaccination
                WHERE UPPER(country) = ?
                  AND TRIM(CAST(coverage AS TEXT)) != ''
                GROUP BY year
                ORDER BY year DESC
                LIMIT 1
            """, [destination]).fetchone()

            infection_snapshot = conn.execute("""
                SELECT
                    year,
                    COUNT(DISTINCT inf_type) AS infection_types_reported,
                    SUM(
                        CASE
                            WHEN cases IS NOT NULL
                             AND TRIM(CAST(cases AS TEXT)) != ''
                            THEN 1 ELSE 0
                        END
                    ) AS usable_records
                FROM InfectionData
                WHERE UPPER(country) = ?
                GROUP BY year
                ORDER BY year DESC
                LIMIT 1
            """, [destination]).fetchone()

            profile["population_year"] = latest_population["year"] if latest_population else None
            profile["population"] = latest_population["population"] if latest_population else None
            profile["vaccination_year"] = vaccination_snapshot["year"] if vaccination_snapshot else None
            profile["average_coverage"] = vaccination_snapshot["average_coverage"] if vaccination_snapshot else None
            profile["antigen_count"] = vaccination_snapshot["antigen_count"] if vaccination_snapshot else 0
            profile["infection_year"] = infection_snapshot["year"] if infection_snapshot else None
            profile["infection_types_reported"] = (
                infection_snapshot["infection_types_reported"] if infection_snapshot else 0
            )
            profile["usable_infection_records"] = (
                infection_snapshot["usable_records"] if infection_snapshot else 0
            )
            destination_profile = profile

    conn.close()

    return render_template(
        "travel.html",
        countries=countries,
        origin=origin,
        destination=destination,
        departure=departure,
        duration=duration,
        destination_profile=destination_profile,
    )



# =========================
# COUNTRY DIRECTORY — STEP 9A
# PostgreSQL analytics discovery surface
# =========================

@app.route("/countries")
def countries_directory():
    search = (request.args.get("q") or "").strip()
    selected_region = (request.args.get("region") or "").strip()
    sort_option = (request.args.get("sort") or "country").strip()

    allowed_sorts = {
        "country": "country_name ASC",
        "coverage": "avg_coverage DESC NULLS LAST, country_name ASC",
        "population": "population DESC NULLS LAST, country_name ASC",
        "cases": "total_cases DESC NULLS LAST, country_name ASC",
    }
    if sort_option not in allowed_sorts:
        sort_option = "country"

    where_parts = []
    params = {}

    if search:
        where_parts.append(
            "(country_name ILIKE :search OR country_id ILIKE :search OR region_name ILIKE :search)"
        )
        params["search"] = f"%{search}%"

    if selected_region:
        where_parts.append("region_id = :region_id")
        params["region_id"] = selected_region

    where_clause = "WHERE " + " AND ".join(where_parts) if where_parts else ""

    with POSTGRES_ENGINE.connect() as pg_conn:
        region_rows = pg_conn.execute(
            text("""
                SELECT DISTINCT region_id, region_name
                FROM analytics.country_health_summary
                WHERE region_id IS NOT NULL AND region_name IS NOT NULL
                ORDER BY region_name
            """)
        ).mappings().all()

        country_rows = pg_conn.execute(
            text(
                f"""
                SELECT
                    country_id, country_name, region_id, region_name,
                    economy_id, economic_phase,
                    latest_vaccination_year, avg_coverage, total_doses,
                    latest_infection_year, total_cases,
                    latest_population_year, population
                FROM analytics.country_health_summary
                {where_clause}
                ORDER BY {allowed_sorts[sort_option]}
                """
            ),
            params,
        ).mappings().all()

    countries = [dict(row) for row in country_rows]
    regions = [dict(row) for row in region_rows]

    vaccination_profile_count = sum(1 for country in countries if country["avg_coverage"] is not None)
    infection_profile_count = sum(1 for country in countries if country["total_cases"] is not None)
    region_count = len({country["region_id"] for country in countries if country["region_id"]})

    return render_template(
        "countries.html",
        countries=countries,
        regions=regions,
        search=search,
        selected_region=selected_region,
        sort_option=sort_option,
        vaccination_profile_count=vaccination_profile_count,
        infection_profile_count=infection_profile_count,
        region_count=region_count,
    )


# =========================
# VACCINATION EXPLORER
# =========================

@app.route("/vaccination")
def vaccination():
    conn = get_db_connection()

    selected_antigen = request.args.get("antigen")
    selected_year = request.args.get("year")
    selected_region = request.args.get("region")
    selected_country = request.args.get("country")

    try:
        minimum_coverage = float(request.args.get("minimum_coverage", "90"))
    except ValueError:
        minimum_coverage = 90.0
    minimum_coverage = max(0, min(minimum_coverage, 200))

    sort_option = request.args.get("sort", "coverage_desc")
    allowed_sorts = {
        "coverage_desc": "CAST(Vaccination.coverage AS REAL) DESC",
        "coverage_asc": "CAST(Vaccination.coverage AS REAL) ASC",
        "country": "Country.name ASC",
        "region": "Region.region ASC, Country.name ASC",
    }
    if sort_option not in allowed_sorts:
        sort_option = "coverage_desc"

    antigens = conn.execute("SELECT AntigenID, name FROM Antigen ORDER BY AntigenID").fetchall()
    years = conn.execute("SELECT DISTINCT year FROM Vaccination ORDER BY year DESC").fetchall()
    regions = conn.execute("SELECT RegionID, region FROM Region ORDER BY region").fetchall()
    countries = conn.execute("SELECT CountryID, name FROM Country ORDER BY name").fetchall()

    results = []
    regional_summary = []
    missing_coverage_count = 0
    coverage_trend = []
    average_result_coverage = None

    if selected_antigen and selected_year:
        missing_query = """
            SELECT COUNT(*) AS total
            FROM Vaccination
            JOIN Country ON Vaccination.country = Country.CountryID
            JOIN Region ON Country.region = Region.RegionID
            WHERE Vaccination.antigen = ?
              AND Vaccination.year = ?
              AND TRIM(CAST(Vaccination.coverage AS TEXT)) = ''
        """
        missing_params = [selected_antigen, selected_year]
        if selected_region:
            missing_query += " AND Region.RegionID = ?"
            missing_params.append(selected_region)
        if selected_country:
            missing_query += " AND Country.CountryID = ?"
            missing_params.append(selected_country)
        missing_coverage_count = conn.execute(missing_query, missing_params).fetchone()["total"]

        query = """
            SELECT
                Country.CountryID AS country_id,
                Vaccination.antigen,
                Vaccination.year,
                Country.name AS country_name,
                Region.region AS region_name,
                ROUND(CAST(Vaccination.coverage AS REAL), 2) AS coverage,
                Vaccination.doses,
                Vaccination.target_num
            FROM Vaccination
            JOIN Country ON Vaccination.country = Country.CountryID
            JOIN Region ON Country.region = Region.RegionID
            WHERE Vaccination.antigen = ?
              AND Vaccination.year = ?
              AND TRIM(CAST(Vaccination.coverage AS TEXT)) != ''
              AND CAST(Vaccination.coverage AS REAL) >= ?
        """
        params = [selected_antigen, selected_year, minimum_coverage]
        if selected_region:
            query += " AND Region.RegionID = ?"
            params.append(selected_region)
        if selected_country:
            query += " AND Country.CountryID = ?"
            params.append(selected_country)
        query += f" ORDER BY {allowed_sorts[sort_option]}"
        results = conn.execute(query, params).fetchall()

        summary_query = """
            SELECT
                Region.region AS region_name,
                ROUND(AVG(CAST(Vaccination.coverage AS REAL)), 2) AS average_coverage,
                COUNT(DISTINCT CASE WHEN CAST(Vaccination.coverage AS REAL) >= ? THEN Country.CountryID END) AS countries_above_threshold
            FROM Vaccination
            JOIN Country ON Vaccination.country = Country.CountryID
            JOIN Region ON Country.region = Region.RegionID
            WHERE Vaccination.antigen = ?
              AND Vaccination.year = ?
              AND TRIM(CAST(Vaccination.coverage AS TEXT)) != ''
        """
        summary_params = [minimum_coverage, selected_antigen, selected_year]
        if selected_region:
            summary_query += " AND Region.RegionID = ?"
            summary_params.append(selected_region)
        if selected_country:
            summary_query += " AND Country.CountryID = ?"
            summary_params.append(selected_country)
        summary_query += " GROUP BY Region.RegionID, Region.region ORDER BY average_coverage DESC"
        regional_summary = conn.execute(summary_query, summary_params).fetchall()

        if results:
            average_result_coverage = round(sum(float(row["coverage"]) for row in results) / len(results), 1)

        trend_query = """
            SELECT Vaccination.year, ROUND(AVG(CAST(Vaccination.coverage AS REAL)), 1) AS value
            FROM Vaccination
            JOIN Country ON Vaccination.country = Country.CountryID
            JOIN Region ON Country.region = Region.RegionID
            WHERE Vaccination.antigen = ?
              AND TRIM(CAST(Vaccination.coverage AS TEXT)) != ''
        """
        trend_params = [selected_antigen]
        if selected_region:
            trend_query += " AND Region.RegionID = ?"
            trend_params.append(selected_region)
        if selected_country:
            trend_query += " AND Country.CountryID = ?"
            trend_params.append(selected_country)
        trend_query += " GROUP BY Vaccination.year ORDER BY Vaccination.year"
        coverage_trend = conn.execute(trend_query, trend_params).fetchall()

    conn.close()

    return render_template(
        "vaccination.html",
        antigens=antigens,
        years=years,
        regions=regions,
        countries=countries,
        results=results,
        regional_summary=regional_summary,
        missing_coverage_count=missing_coverage_count,
        selected_antigen=selected_antigen,
        selected_year=selected_year,
        selected_region=selected_region,
        selected_country=selected_country,
        minimum_coverage=minimum_coverage,
        sort_option=sort_option,
        average_result_coverage=average_result_coverage,
        coverage_trend=rows_to_dicts(coverage_trend),
    )


# =========================
# IMPROVEMENT ANALYSIS
# =========================

@app.route("/improvement")
def improvement():
    conn = get_db_connection()

    selected_antigen = request.args.get("antigen")
    start_year = request.args.get("start_year")
    end_year = request.args.get("end_year")
    limit = request.args.get("limit", "10")
    mode = request.args.get("mode", "improvement")
    if mode not in {"improvement", "decline", "all"}:
        mode = "improvement"

    antigens = conn.execute("SELECT AntigenID, name FROM Antigen ORDER BY AntigenID").fetchall()
    years = conn.execute("SELECT DISTINCT year FROM Vaccination ORDER BY year DESC").fetchall()

    improvement_results = []
    error_message = None
    summary = {"average": None, "largest": None, "count": 0}

    if selected_antigen and start_year and end_year:
        try:
            start_year_int = int(start_year)
            end_year_int = int(end_year)
            limit_int = int(limit)
        except ValueError:
            error_message = "Invalid year or result limit."
        else:
            if start_year_int >= end_year_int:
                error_message = "Start year must be earlier than end year."
            elif limit_int not in [5, 10, 20]:
                error_message = "Invalid number of countries selected."
            else:
                if mode == "decline":
                    where_mode = "WHERE improvement < 0"
                    order_mode = "improvement ASC"
                elif mode == "all":
                    where_mode = ""
                    order_mode = "ABS(improvement) DESC"
                else:
                    where_mode = "WHERE improvement > 0"
                    order_mode = "improvement DESC"

                query = f"""
                    WITH valid_pairs AS (
                        SELECT
                            Country.CountryID AS country_id,
                            Country.name AS country_name,
                            ROUND(CAST(start_v.doses AS REAL) / start_p.population * 100, 2) AS start_rate,
                            ROUND(CAST(end_v.doses AS REAL) / end_p.population * 100, 2) AS end_rate,
                            ROUND(
                                (CAST(end_v.doses AS REAL) / end_p.population * 100)
                                - (CAST(start_v.doses AS REAL) / start_p.population * 100),
                                2
                            ) AS improvement
                        FROM Vaccination AS start_v
                        JOIN Vaccination AS end_v
                          ON start_v.country = end_v.country
                         AND start_v.antigen = end_v.antigen
                        JOIN Country ON start_v.country = Country.CountryID
                        JOIN CountryPopulation AS start_p
                          ON start_v.country = start_p.country AND start_v.year = start_p.year
                        JOIN CountryPopulation AS end_p
                          ON end_v.country = end_p.country AND end_v.year = end_p.year
                        WHERE start_v.antigen = ?
                          AND end_v.antigen = ?
                          AND start_v.year = ?
                          AND end_v.year = ?
                          AND start_p.population > 0
                          AND end_p.population > 0
                          AND TRIM(CAST(start_v.doses AS TEXT)) != ''
                          AND TRIM(CAST(end_v.doses AS TEXT)) != ''
                    )
                    SELECT
                        ROW_NUMBER() OVER (ORDER BY {order_mode}) AS rank,
                        country_id,
                        country_name,
                        start_rate,
                        end_rate,
                        improvement
                    FROM valid_pairs
                    {where_mode}
                    ORDER BY {order_mode}
                    LIMIT ?
                """
                improvement_results = conn.execute(
                    query,
                    [selected_antigen, selected_antigen, start_year_int, end_year_int, limit_int],
                ).fetchall()

                if improvement_results:
                    values = [float(row["improvement"]) for row in improvement_results]
                    summary = {
                        "average": round(sum(values) / len(values), 1),
                        "largest": values[0],
                        "count": len(values),
                    }

    conn.close()

    return render_template(
        "improvement.html",
        antigens=antigens,
        years=years,
        improvement_results=improvement_results,
        selected_antigen=selected_antigen,
        start_year=start_year,
        end_year=end_year,
        limit=limit,
        mode=mode,
        summary=summary,
        error_message=error_message,
    )


# =========================
# MISSION
# =========================

@app.route("/mission")
def mission():
    conn = get_db_connection()

    personas = []
    team_members = []

    if table_exists(conn, "Persona"):
        personas = conn.execute("""
            SELECT PersonaID, persona_name, age_gender, role, location,
                   background, needs, goals, skills, pain_points
            FROM Persona
            ORDER BY PersonaID
        """).fetchall()

    if table_exists(conn, "TeamMember"):
        team_members = conn.execute("""
            SELECT TeamMemberID, full_name, student_number
            FROM TeamMember
            ORDER BY TeamMemberID
        """).fetchall()

    conn.close()

    return render_template("mission.html", personas=personas, team_members=team_members)


# =========================
# INFECTION EXPLORER
# =========================

INFECTION_SORT_COLUMNS = {
    "country": "country_name",
    "rate": "cases_per_100k",
}


@app.route("/infections")
def infections():
    conn = get_db_connection()

    selected_economy = request.args.get("economy")
    selected_infection = request.args.get("infection")
    selected_year = request.args.get("year")
    sort_by = request.args.get("sort_by", "rate")
    sort_dir = request.args.get("sort_dir", "desc")

    if sort_by not in INFECTION_SORT_COLUMNS:
        sort_by = "rate"
    if sort_dir not in ("asc", "desc"):
        sort_dir = "desc"

    country_sort_next = "desc" if (sort_by == "country" and sort_dir == "asc") else "asc"
    rate_sort_next = "asc" if (sort_by == "rate" and sort_dir == "desc") else "desc"

    economies = conn.execute("SELECT economyID, phase FROM Economy ORDER BY economyID").fetchall()
    infection_types = conn.execute("SELECT id, description FROM Infection_Type ORDER BY description").fetchall()
    years = conn.execute("SELECT DISTINCT year FROM InfectionData ORDER BY year DESC").fetchall()

    country_results = []
    phase_summary = []
    missing_data_count = 0
    global_trend = []

    if selected_economy and selected_infection and selected_year:
        missing_data_count = conn.execute("""
            SELECT COUNT(*) AS total
            FROM InfectionData
            JOIN Country ON InfectionData.country = Country.CountryID
            LEFT JOIN CountryPopulation
              ON InfectionData.country = CountryPopulation.country
             AND InfectionData.year = CountryPopulation.year
            WHERE InfectionData.inf_type = ?
              AND InfectionData.year = ?
              AND Country.economy = ?
              AND (
                    InfectionData.cases IS NULL
                    OR TRIM(CAST(InfectionData.cases AS TEXT)) = ''
                    OR CountryPopulation.population IS NULL
                    OR CountryPopulation.population <= 0
                  )
        """, [selected_infection, selected_year, selected_economy]).fetchone()["total"]

        order_column = INFECTION_SORT_COLUMNS[sort_by]
        country_query = f"""
            SELECT
                Country.CountryID AS country_id,
                Infection_Type.description AS infection_name,
                Country.name AS country_name,
                Economy.phase AS economic_phase,
                InfectionData.year,
                ROUND(CAST(InfectionData.cases AS REAL) / CountryPopulation.population * 100000, 2) AS cases_per_100k
            FROM InfectionData
            JOIN Country ON InfectionData.country = Country.CountryID
            JOIN Economy ON Country.economy = Economy.economyID
            JOIN Infection_Type ON InfectionData.inf_type = Infection_Type.id
            JOIN CountryPopulation
              ON InfectionData.country = CountryPopulation.country
             AND InfectionData.year = CountryPopulation.year
            WHERE InfectionData.inf_type = ?
              AND InfectionData.year = ?
              AND Country.economy = ?
              AND TRIM(CAST(InfectionData.cases AS TEXT)) != ''
              AND CountryPopulation.population > 0
            ORDER BY {order_column} {sort_dir.upper()}
        """
        country_results = conn.execute(
            country_query,
            [selected_infection, selected_year, selected_economy],
        ).fetchall()

        phase_summary = conn.execute("""
            SELECT
                Infection_Type.description AS infection_name,
                Economy.phase AS economic_phase,
                InfectionData.year,
                SUM(InfectionData.cases) AS total_cases
            FROM InfectionData
            JOIN Country ON InfectionData.country = Country.CountryID
            JOIN Economy ON Country.economy = Economy.economyID
            JOIN Infection_Type ON InfectionData.inf_type = Infection_Type.id
            WHERE InfectionData.inf_type = ?
              AND InfectionData.year = ?
              AND TRIM(CAST(InfectionData.cases AS TEXT)) != ''
            GROUP BY Economy.economyID, Economy.phase, InfectionData.year, Infection_Type.description
            ORDER BY Economy.economyID ASC
        """, [selected_infection, selected_year]).fetchall()

        global_trend = conn.execute("""
            SELECT
                InfectionData.year,
                ROUND(SUM(InfectionData.cases) * 1.0 / SUM(CountryPopulation.population) * 100000, 2) AS value
            FROM InfectionData
            JOIN CountryPopulation
              ON InfectionData.country = CountryPopulation.country
             AND InfectionData.year = CountryPopulation.year
            WHERE InfectionData.inf_type = ?
              AND TRIM(CAST(InfectionData.cases AS TEXT)) != ''
              AND CountryPopulation.population > 0
            GROUP BY InfectionData.year
            ORDER BY InfectionData.year
        """, [selected_infection]).fetchall()

    conn.close()

    return render_template(
        "infections.html",
        economies=economies,
        infection_types=infection_types,
        years=years,
        country_results=country_results,
        phase_summary=phase_summary,
        missing_data_count=missing_data_count,
        selected_economy=selected_economy,
        selected_infection=selected_infection,
        selected_year=selected_year,
        sort_by=sort_by,
        sort_dir=sort_dir,
        country_sort_next=country_sort_next,
        rate_sort_next=rate_sort_next,
        global_trend=rows_to_dicts(global_trend),
    )


# =========================
# INFECTION RATE BENCHMARK
# =========================

INFECTION_RATE_SORT = {
    "rate_desc": "rate_per_100k DESC",
    "rate_asc": "rate_per_100k ASC",
    "country": "country_name ASC",
}


@app.route("/infection-rate")
def infection_rate():
    conn = get_db_connection()

    selected_infection = request.args.get("infection")
    selected_year = request.args.get("year")
    sort_option = request.args.get("sort", "rate_desc")
    try:
        top_n = int(request.args.get("top", "25"))
    except ValueError:
        top_n = 25
    top_n = 100 if top_n > 100 else 5 if top_n < 5 else top_n

    if sort_option not in INFECTION_RATE_SORT:
        sort_option = "rate_desc"

    infection_types = conn.execute("SELECT id, description FROM Infection_Type ORDER BY description").fetchall()
    years = conn.execute("SELECT DISTINCT year FROM InfectionData ORDER BY year DESC").fetchall()

    infection_name = None
    global_rate = None
    above_average_countries = []

    if selected_infection and selected_year:
        infection_row = conn.execute("SELECT description FROM Infection_Type WHERE id = ?", [selected_infection]).fetchone()
        infection_name = infection_row["description"] if infection_row else selected_infection

        global_row = conn.execute("""
            SELECT ROUND(SUM(InfectionData.cases) * 1.0 / SUM(CountryPopulation.population) * 100000, 2) AS global_rate
            FROM InfectionData
            JOIN CountryPopulation
              ON InfectionData.country = CountryPopulation.country
             AND InfectionData.year = CountryPopulation.year
            WHERE InfectionData.inf_type = ?
              AND InfectionData.year = ?
              AND TRIM(CAST(InfectionData.cases AS TEXT)) != ''
              AND CountryPopulation.population > 0
        """, [selected_infection, selected_year]).fetchone()
        global_rate = global_row["global_rate"] if global_row else None

        if global_rate is not None:
            order_clause = INFECTION_RATE_SORT[sort_option]
            rate_query = f"""
                WITH global_stats AS (
                    SELECT
                        SUM(InfectionData.cases) * 1.0 / SUM(CountryPopulation.population) * 100000 AS global_rate
                    FROM InfectionData
                    JOIN CountryPopulation
                      ON InfectionData.country = CountryPopulation.country
                     AND InfectionData.year = CountryPopulation.year
                    WHERE InfectionData.inf_type = ?
                      AND InfectionData.year = ?
                      AND TRIM(CAST(InfectionData.cases AS TEXT)) != ''
                      AND CountryPopulation.population > 0
                )
                SELECT
                    Country.CountryID AS country_id,
                    Country.name AS country_name,
                    ROUND(CAST(InfectionData.cases AS REAL) / CountryPopulation.population * 100000, 2) AS rate_per_100k,
                    ROUND((CAST(InfectionData.cases AS REAL) / CountryPopulation.population * 100000) - global_stats.global_rate, 2) AS rate_above_global
                FROM InfectionData
                JOIN Country ON InfectionData.country = Country.CountryID
                JOIN CountryPopulation
                  ON InfectionData.country = CountryPopulation.country
                 AND InfectionData.year = CountryPopulation.year
                JOIN global_stats
                WHERE InfectionData.inf_type = ?
                  AND InfectionData.year = ?
                  AND TRIM(CAST(InfectionData.cases AS TEXT)) != ''
                  AND CountryPopulation.population > 0
                  AND (CAST(InfectionData.cases AS REAL) / CountryPopulation.population * 100000) > global_stats.global_rate
                  AND EXISTS (
                        SELECT 1 FROM Vaccination
                        WHERE Vaccination.country = InfectionData.country
                  )
                ORDER BY {order_clause}
                LIMIT ?
            """
            above_average_countries = conn.execute(
                rate_query,
                [selected_infection, selected_year, selected_infection, selected_year, top_n],
            ).fetchall()

    conn.close()

    return render_template(
        "infection_rate.html",
        infection_types=infection_types,
        years=years,
        infection_name=infection_name,
        global_rate=global_rate,
        above_average_countries=above_average_countries,
        selected_infection=selected_infection,
        selected_year=selected_year,
        sort_option=sort_option,
        top_n=top_n,
    )


# =========================
# COUNTRY COMPARE
# =========================

@app.route("/compare")
def compare_countries():
    conn = get_db_connection()

    countries = conn.execute("""
        SELECT Country.CountryID, Country.name, Region.region AS region_name
        FROM Country
        LEFT JOIN Region ON Country.region = Region.RegionID
        ORDER BY Country.name
    """).fetchall()
    antigens = conn.execute("SELECT AntigenID, name FROM Antigen ORDER BY AntigenID").fetchall()

    antigen_ids = [row["AntigenID"] for row in antigens]
    selected_antigen = request.args.get("antigen") or ("DTPCV3" if "DTPCV3" in antigen_ids else (antigen_ids[0] if antigen_ids else None))

    years_row = conn.execute("SELECT MIN(year) AS min_year, MAX(year) AS max_year FROM Vaccination").fetchone()
    try:
        start_year = int(request.args.get("start_year", years_row["min_year"]))
        end_year = int(request.args.get("end_year", years_row["max_year"]))
    except (TypeError, ValueError):
        start_year, end_year = years_row["min_year"], years_row["max_year"]

    if start_year > end_year:
        start_year, end_year = end_year, start_year

    selected_ids = clean_country_ids(request.args.getlist("countries"))
    valid_ids = {row["CountryID"] for row in countries}
    selected_ids = [value for value in selected_ids if value in valid_ids]

    summaries = []
    chart_series = []

    if selected_ids and selected_antigen:
        placeholders = ",".join("?" for _ in selected_ids)
        meta_rows = conn.execute(f"""
            SELECT
                Country.CountryID AS country_id,
                Country.name AS country_name,
                Region.region AS region_name,
                Economy.phase AS economy_phase
            FROM Country
            LEFT JOIN Region ON Country.region = Region.RegionID
            LEFT JOIN Economy ON Country.economy = Economy.economyID
            WHERE Country.CountryID IN ({placeholders})
        """, selected_ids).fetchall()
        meta = {row["country_id"]: dict(row) for row in meta_rows}

        trend_rows = conn.execute(f"""
            SELECT
                Vaccination.country AS country_id,
                Country.name AS country_name,
                Vaccination.year,
                ROUND(CAST(Vaccination.coverage AS REAL), 2) AS coverage
            FROM Vaccination
            JOIN Country ON Vaccination.country = Country.CountryID
            WHERE Vaccination.country IN ({placeholders})
              AND Vaccination.antigen = ?
              AND Vaccination.year BETWEEN ? AND ?
              AND TRIM(CAST(Vaccination.coverage AS TEXT)) != ''
            ORDER BY Vaccination.country, Vaccination.year
        """, [*selected_ids, selected_antigen, start_year, end_year]).fetchall()

        grouped = defaultdict(list)
        for row in trend_rows:
            grouped[row["country_id"]].append(dict(row))

        pop_rows = conn.execute(f"""
            SELECT cp.country AS country_id, cp.population, cp.year
            FROM CountryPopulation cp
            JOIN (
                SELECT country, MAX(year) AS max_year
                FROM CountryPopulation
                WHERE country IN ({placeholders}) AND year <= ? AND population > 0
                GROUP BY country
            ) latest ON latest.country = cp.country AND latest.max_year = cp.year
        """, [*selected_ids, end_year]).fetchall()
        latest_population = {row["country_id"]: dict(row) for row in pop_rows}

        infection_rows = conn.execute(f"""
            SELECT
                InfectionData.country AS country_id,
                ROUND(SUM(InfectionData.cases) * 1.0 / MAX(CountryPopulation.population) * 100000, 2) AS infection_rate
            FROM InfectionData
            JOIN CountryPopulation
              ON InfectionData.country = CountryPopulation.country
             AND InfectionData.year = CountryPopulation.year
            WHERE InfectionData.country IN ({placeholders})
              AND InfectionData.year = ?
              AND TRIM(CAST(InfectionData.cases AS TEXT)) != ''
              AND CountryPopulation.population > 0
            GROUP BY InfectionData.country
        """, [*selected_ids, end_year]).fetchall()
        infection_map = {row["country_id"]: row["infection_rate"] for row in infection_rows}

        for country_id in selected_ids:
            series = grouped.get(country_id, [])
            if series:
                start_value = series[0]["coverage"]
                end_value = series[-1]["coverage"]
                change = round(float(end_value) - float(start_value), 1)
            else:
                start_value = end_value = change = None

            row_meta = meta.get(country_id, {"country_id": country_id, "country_name": country_id, "region_name": None, "economy_phase": None})
            pop = latest_population.get(country_id, {})
            summaries.append({
                **row_meta,
                "start_coverage": start_value,
                "end_coverage": end_value,
                "change": change,
                "population": pop.get("population"),
                "population_year": pop.get("year"),
                "infection_rate": infection_map.get(country_id),
            })
            chart_series.append({
                "id": country_id,
                "name": row_meta.get("country_name", country_id),
                "values": [{"year": row["year"], "value": row["coverage"]} for row in series],
            })

    conn.close()

    return render_template(
        "compare.html",
        countries=countries,
        antigens=antigens,
        selected_ids=selected_ids,
        selected_antigen=selected_antigen,
        start_year=start_year,
        end_year=end_year,
        min_year=years_row["min_year"],
        max_year=years_row["max_year"],
        summaries=summaries,
        chart_series=chart_series,
    )


# =========================
# COUNTRY PROFILE
# =========================

@app.route("/country/<country_id>")
def country_profile(country_id):
    conn = get_db_connection()
    country_id = country_id.upper()

    country = conn.execute("""
        SELECT
            Country.CountryID AS country_id,
            Country.name AS country_name,
            Region.region AS region_name,
            Economy.phase AS economy_phase
        FROM Country
        LEFT JOIN Region ON Country.region = Region.RegionID
        LEFT JOIN Economy ON Country.economy = Economy.economyID
        WHERE Country.CountryID = ?
    """, [country_id]).fetchone()

    if not country:
        conn.close()
        abort(404)

    latest_population = conn.execute("""
        SELECT year, population
        FROM CountryPopulation
        WHERE country = ? AND population > 0
        ORDER BY year DESC
        LIMIT 1
    """, [country_id]).fetchone()

    vaccination_rows = conn.execute("""
        SELECT
            Vaccination.antigen,
            Antigen.name AS antigen_name,
            Vaccination.year,
            ROUND(CAST(Vaccination.coverage AS REAL), 2) AS coverage,
            Vaccination.doses,
            Vaccination.target_num
        FROM Vaccination
        JOIN Antigen ON Vaccination.antigen = Antigen.AntigenID
        WHERE Vaccination.country = ?
          AND TRIM(CAST(Vaccination.coverage AS TEXT)) != ''
        ORDER BY Vaccination.antigen, Vaccination.year
    """, [country_id]).fetchall()

    infection_rows = conn.execute("""
        SELECT
            InfectionData.inf_type,
            Infection_Type.description AS infection_name,
            InfectionData.year,
            InfectionData.cases,
            ROUND(CAST(InfectionData.cases AS REAL) / CountryPopulation.population * 100000, 2) AS rate_per_100k
        FROM InfectionData
        JOIN Infection_Type ON InfectionData.inf_type = Infection_Type.id
        JOIN CountryPopulation
          ON InfectionData.country = CountryPopulation.country
         AND InfectionData.year = CountryPopulation.year
        WHERE InfectionData.country = ?
          AND TRIM(CAST(InfectionData.cases AS TEXT)) != ''
          AND CountryPopulation.population > 0
        ORDER BY InfectionData.inf_type, InfectionData.year
    """, [country_id]).fetchall()

    vaccination_grouped = defaultdict(list)
    latest_vaccination = {}
    for row in vaccination_rows:
        item = dict(row)
        vaccination_grouped[row["antigen"]].append(item)
        latest_vaccination[row["antigen"]] = item

    infection_grouped = defaultdict(list)
    latest_infection = {}
    for row in infection_rows:
        item = dict(row)
        infection_grouped[row["inf_type"]].append(item)
        latest_infection[row["inf_type"]] = item

    vaccination_series = [
        {
            "id": antigen,
            "name": rows[0]["antigen_name"] if rows else antigen,
            "values": [{"year": row["year"], "value": row["coverage"]} for row in rows],
        }
        for antigen, rows in vaccination_grouped.items()
    ]
    infection_series = [
        {
            "id": inf_type,
            "name": rows[0]["infection_name"] if rows else inf_type,
            "values": [{"year": row["year"], "value": row["rate_per_100k"]} for row in rows],
        }
        for inf_type, rows in infection_grouped.items()
    ]

    total_vaccination = conn.execute("SELECT COUNT(*) AS total FROM Vaccination WHERE country = ?", [country_id]).fetchone()["total"]
    missing_vaccination = conn.execute("""
        SELECT COUNT(*) AS total
        FROM Vaccination
        WHERE country = ?
          AND (
            coverage IS NULL OR TRIM(CAST(coverage AS TEXT)) = ''
            OR doses IS NULL OR TRIM(CAST(doses AS TEXT)) = ''
          )
    """, [country_id]).fetchone()["total"]
    profile_quality = round((total_vaccination - missing_vaccination) / total_vaccination * 100, 1) if total_vaccination else 0

    conn.close()

    return render_template(
        "country.html",
        country=country,
        latest_population=latest_population,
        latest_vaccination=list(latest_vaccination.values()),
        latest_infection=list(latest_infection.values()),
        vaccination_series=vaccination_series,
        infection_series=infection_series,
        profile_quality=profile_quality,
    )


# =========================
# GLOBAL INSIGHTS
# =========================

@app.route("/insights")
def insights():
    conn = get_db_connection()
    antigens = conn.execute("SELECT AntigenID, name FROM Antigen ORDER BY AntigenID").fetchall()
    antigen_ids = [row["AntigenID"] for row in antigens]
    selected_antigen = request.args.get("antigen") or ("DTPCV3" if "DTPCV3" in antigen_ids else (antigen_ids[0] if antigen_ids else None))

    latest_year = conn.execute("SELECT MAX(year) AS year FROM Vaccination").fetchone()["year"]
    first_year = conn.execute("SELECT MIN(year) AS year FROM Vaccination").fetchone()["year"]
    comparison_start = max(first_year, latest_year - 10)

    headline = conn.execute("""
        SELECT
            ROUND(AVG(CAST(coverage AS REAL)), 1) AS average_coverage,
            COUNT(DISTINCT CASE WHEN CAST(coverage AS REAL) >= 90 THEN country END) AS countries_90,
            COUNT(DISTINCT country) AS countries_reporting
        FROM Vaccination
        WHERE antigen = ? AND year = ? AND TRIM(CAST(coverage AS TEXT)) != ''
    """, [selected_antigen, latest_year]).fetchone()

    leaders = conn.execute("""
        SELECT Country.CountryID AS country_id, Country.name AS country_name,
               Region.region AS region_name, ROUND(CAST(Vaccination.coverage AS REAL), 1) AS coverage
        FROM Vaccination
        JOIN Country ON Vaccination.country = Country.CountryID
        LEFT JOIN Region ON Country.region = Region.RegionID
        WHERE Vaccination.antigen = ? AND Vaccination.year = ?
          AND TRIM(CAST(Vaccination.coverage AS TEXT)) != ''
        ORDER BY CAST(Vaccination.coverage AS REAL) DESC
        LIMIT 10
    """, [selected_antigen, latest_year]).fetchall()

    regional = conn.execute("""
        SELECT Region.region AS region_name,
               ROUND(AVG(CAST(Vaccination.coverage AS REAL)), 1) AS average_coverage,
               COUNT(DISTINCT Country.CountryID) AS countries
        FROM Vaccination
        JOIN Country ON Vaccination.country = Country.CountryID
        JOIN Region ON Country.region = Region.RegionID
        WHERE Vaccination.antigen = ? AND Vaccination.year = ?
          AND TRIM(CAST(Vaccination.coverage AS TEXT)) != ''
        GROUP BY Region.RegionID, Region.region
        ORDER BY average_coverage DESC
    """, [selected_antigen, latest_year]).fetchall()

    improvements = conn.execute("""
        WITH pairs AS (
            SELECT
                Country.CountryID AS country_id,
                Country.name AS country_name,
                ROUND(CAST(start_v.doses AS REAL) / start_p.population * 100, 2) AS start_rate,
                ROUND(CAST(end_v.doses AS REAL) / end_p.population * 100, 2) AS end_rate,
                ROUND((CAST(end_v.doses AS REAL) / end_p.population * 100) - (CAST(start_v.doses AS REAL) / start_p.population * 100), 2) AS improvement
            FROM Vaccination start_v
            JOIN Vaccination end_v
              ON start_v.country = end_v.country AND start_v.antigen = end_v.antigen
            JOIN Country ON start_v.country = Country.CountryID
            JOIN CountryPopulation start_p
              ON start_v.country = start_p.country AND start_v.year = start_p.year
            JOIN CountryPopulation end_p
              ON end_v.country = end_p.country AND end_v.year = end_p.year
            WHERE start_v.antigen = ? AND end_v.antigen = ?
              AND start_v.year = ? AND end_v.year = ?
              AND start_p.population > 0 AND end_p.population > 0
              AND TRIM(CAST(start_v.doses AS TEXT)) != ''
              AND TRIM(CAST(end_v.doses AS TEXT)) != ''
        )
        SELECT * FROM pairs
        WHERE improvement > 0
        ORDER BY improvement DESC
        LIMIT 8
    """, [selected_antigen, selected_antigen, comparison_start, latest_year]).fetchall()

    infection_year = conn.execute("SELECT MAX(year) AS year FROM InfectionData").fetchone()["year"]
    infection_summary = conn.execute("""
        SELECT
            Infection_Type.description AS infection_name,
            ROUND(SUM(InfectionData.cases) * 1.0 / SUM(CountryPopulation.population) * 100000, 2) AS global_rate,
            SUM(InfectionData.cases) AS total_cases
        FROM InfectionData
        JOIN Infection_Type ON InfectionData.inf_type = Infection_Type.id
        JOIN CountryPopulation
          ON InfectionData.country = CountryPopulation.country
         AND InfectionData.year = CountryPopulation.year
        WHERE InfectionData.year = ?
          AND TRIM(CAST(InfectionData.cases AS TEXT)) != ''
          AND CountryPopulation.population > 0
        GROUP BY InfectionData.inf_type, Infection_Type.description
        ORDER BY global_rate DESC
    """, [infection_year]).fetchall()

    trend = conn.execute("""
        SELECT year, ROUND(AVG(CAST(coverage AS REAL)), 1) AS value
        FROM Vaccination
        WHERE antigen = ? AND TRIM(CAST(coverage AS TEXT)) != ''
        GROUP BY year
        ORDER BY year
    """, [selected_antigen]).fetchall()

    conn.close()

    return render_template(
        "insights.html",
        antigens=antigens,
        selected_antigen=selected_antigen,
        latest_year=latest_year,
        comparison_start=comparison_start,
        headline=headline,
        leaders=leaders,
        regional=regional,
        improvements=improvements,
        infection_year=infection_year,
        infection_summary=infection_summary,
        trend=rows_to_dicts(trend),
    )


# =========================
# DATA QUALITY CENTER
# =========================

@app.route("/data-quality")
def data_quality():
    # Legacy/source-level checks still come from the local SQLite source.
    conn = get_db_connection()

    vaccination = conn.execute("""
        SELECT
            COUNT(*) AS total,
            SUM(CASE WHEN coverage IS NULL OR TRIM(CAST(coverage AS TEXT)) = '' THEN 1 ELSE 0 END) AS missing_coverage,
            SUM(CASE WHEN doses IS NULL OR TRIM(CAST(doses AS TEXT)) = '' THEN 1 ELSE 0 END) AS missing_doses,
            SUM(CASE WHEN target_num IS NULL OR TRIM(CAST(target_num AS TEXT)) = '' THEN 1 ELSE 0 END) AS missing_target,
            SUM(CASE WHEN TRIM(CAST(coverage AS TEXT)) != '' AND CAST(coverage AS REAL) > 100 THEN 1 ELSE 0 END) AS coverage_over_100
        FROM Vaccination
    """).fetchone()

    population = conn.execute("""
        SELECT
            COUNT(*) AS total,
            SUM(CASE WHEN population IS NULL OR population <= 0 THEN 1 ELSE 0 END) AS invalid_population
        FROM CountryPopulation
    """).fetchone()

    infection = conn.execute("""
        SELECT
            COUNT(*) AS total,
            SUM(CASE WHEN cases IS NULL OR TRIM(CAST(cases AS TEXT)) = '' THEN 1 ELSE 0 END) AS missing_cases
        FROM InfectionData
    """).fetchone()

    antigen_quality = conn.execute("""
        SELECT
            Antigen.AntigenID AS antigen,
            Antigen.name AS antigen_name,
            COUNT(Vaccination.antigen) AS total,
            SUM(CASE WHEN Vaccination.coverage IS NULL OR TRIM(CAST(Vaccination.coverage AS TEXT)) = '' THEN 1 ELSE 0 END) AS missing,
            ROUND(
                100.0 * SUM(CASE WHEN Vaccination.coverage IS NOT NULL AND TRIM(CAST(Vaccination.coverage AS TEXT)) != '' THEN 1 ELSE 0 END)
                / NULLIF(COUNT(Vaccination.antigen), 0),
                1
            ) AS completeness
        FROM Antigen
        LEFT JOIN Vaccination ON Antigen.AntigenID = Vaccination.antigen
        GROUP BY Antigen.AntigenID, Antigen.name
        ORDER BY completeness DESC
    """).fetchall()

    year_quality = conn.execute("""
        SELECT
            year,
            COUNT(*) AS total,
            ROUND(
                100.0 * SUM(
                    CASE
                        WHEN coverage IS NOT NULL
                         AND TRIM(CAST(coverage AS TEXT)) != ''
                        THEN 1
                        ELSE 0
                    END
                ) / COUNT(*),
                1
            ) AS value
        FROM Vaccination
        GROUP BY year
        ORDER BY year
    """).fetchall()

    def completeness(total, missing):
        return (
            round((total - missing) / total * 100, 1)
            if total
            else 0
        )

    legacy_metrics = {
        "vaccination_coverage": completeness(
            vaccination["total"],
            vaccination["missing_coverage"] or 0,
        ),
        "vaccination_doses": completeness(
            vaccination["total"],
            vaccination["missing_doses"] or 0,
        ),
        "population": completeness(
            population["total"],
            population["invalid_population"] or 0,
        ),
        "infection_cases": completeness(
            infection["total"],
            infection["missing_cases"] or 0,
        ),
    }

    legacy_overall_score = round(
        sum(legacy_metrics.values()) / len(legacy_metrics),
        1,
    )

    conn.close()

    # PostgreSQL is the source of truth for pipeline-level quality.
    pipeline_latest = None
    pipeline_tables = []
    pipeline_history = []
    postgres_quality_available = False

    try:
        with POSTGRES_ENGINE.connect() as pg_conn:
            latest_row = pg_conn.execute(
                text("""
                    SELECT
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
                        overall_score
                    FROM meta.pipeline_run
                    ORDER BY finished_at DESC
                    LIMIT 1
                """)
            ).mappings().first()

            if latest_row:
                pipeline_latest = dict(latest_row)
                postgres_quality_available = True

                table_rows = pg_conn.execute(
                    text("""
                        SELECT
                            table_name,
                            row_count,
                            completeness,
                            validity,
                            consistency,
                            freshness,
                            uniqueness,
                            overall_score
                        FROM meta.table_quality
                        WHERE run_id = :run_id
                        ORDER BY overall_score ASC, table_name ASC
                    """),
                    {
                        "run_id": pipeline_latest["run_id"],
                    },
                ).mappings().all()

                pipeline_tables = [
                    dict(row)
                    for row in table_rows
                ]

            history_rows = pg_conn.execute(
                text("""
                    SELECT
                        run_id,
                        finished_at,
                        overall_score,
                        completeness,
                        validity,
                        consistency,
                        freshness,
                        uniqueness
                    FROM meta.pipeline_run
                    ORDER BY finished_at DESC
                    LIMIT 10
                """)
            ).mappings().all()

            pipeline_history = [
                dict(row)
                for row in history_rows
            ]

    except Exception as exc:
        app.logger.warning(
            "Could not load PostgreSQL quality metrics: %s",
            exc,
        )

    if pipeline_latest:
        overall_score = float(
            pipeline_latest["overall_score"]
        )
        metrics = {
            "completeness": float(
                pipeline_latest["completeness"]
            ),
            "validity": float(
                pipeline_latest["validity"]
            ),
            "consistency": float(
                pipeline_latest["consistency"]
            ),
            "freshness": float(
                pipeline_latest["freshness"]
            ),
            "uniqueness": float(
                pipeline_latest["uniqueness"]
            ),
        }
    else:
        overall_score = legacy_overall_score
        metrics = {
            "completeness": legacy_overall_score,
            "validity": legacy_overall_score,
            "consistency": legacy_overall_score,
            "freshness": legacy_overall_score,
            "uniqueness": legacy_overall_score,
        }

    return render_template(
        "data_quality.html",
        vaccination=vaccination,
        population=population,
        infection=infection,
        antigen_quality=antigen_quality,
        year_quality=rows_to_dicts(year_quality),
        metrics=metrics,
        overall_score=overall_score,
        legacy_metrics=legacy_metrics,
        legacy_overall_score=legacy_overall_score,
        pipeline_latest=pipeline_latest,
        pipeline_tables=pipeline_tables,
        pipeline_history=pipeline_history,
        postgres_quality_available=postgres_quality_available,
    )


# =========================
# GLOBAL SEARCH API
# =========================

@app.route("/api/search")
def api_search():
    query = request.args.get("q", "").strip()
    if len(query) < 2:
        return jsonify([])

    conn = get_db_connection()
    like = f"%{query}%"

    countries = conn.execute("""
        SELECT CountryID AS id, name
        FROM Country
        WHERE name LIKE ? OR CountryID LIKE ?
        ORDER BY name
        LIMIT 8
    """, [like, like]).fetchall()

    antigens = conn.execute("""
        SELECT AntigenID AS id, name
        FROM Antigen
        WHERE AntigenID LIKE ? OR name LIKE ?
        ORDER BY AntigenID
        LIMIT 5
    """, [like, like]).fetchall()

    infections = conn.execute("""
        SELECT id, description AS name
        FROM Infection_Type
        WHERE id LIKE ? OR description LIKE ?
        ORDER BY description
        LIMIT 5
    """, [like, like]).fetchall()

    conn.close()

    results = []
    for row in countries:
        results.append({"type": "country", "id": row["id"], "name": row["name"], "url": f"/country/{row['id']}"})
    for row in antigens:
        results.append({"type": "antigen", "id": row["id"], "name": row["name"], "url": f"/vaccination?antigen={row['id']}"})
    for row in infections:
        results.append({"type": "infection", "id": row["id"], "name": row["name"], "url": f"/infections?infection={row['id']}"})
    return jsonify(results)


if __name__ == "__main__":
    app.run(debug=True, port=5001)
