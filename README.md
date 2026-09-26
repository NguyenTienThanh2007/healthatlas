# HealthAtlas

**Travel smarter. Understand global health.**

HealthAtlas is a travel-first global health intelligence platform that combines a
consumer-facing travel experience with a growing data-engineering platform for
vaccination, infectious-disease, country, data-quality, and global-health analytics.

Public deployment: **https://healthatlas-web.onrender.com/**

> HealthAtlas is an informational analytics project. It does not provide medical
> diagnosis or personalised medical advice.

## Current product

The web product currently includes:

- Travel Health Planner
- country health profiles
- vaccination analytics
- infectious-disease analytics
- country comparison
- global insights
- PostgreSQL-backed data-quality monitoring
- light/dark UI and interactive charts

The existing country-profile route is:

```text
/country/<country_id>
```

Examples:

```text
/country/AUS
/country/VNM
```

## Data platform

HealthAtlas now has a repeatable data-engineering pipeline rather than only a
Flask + SQLite application.

```text
SQLite public-health seed
          ↓
Extraction + normalisation
          ↓
Validation + quality scoring
          ↓
PostgreSQL staging
          ↓
Curated views
          ↓
Dimensional warehouse
          ↓
Analytics marts
          ↓
Flask product + data-quality dashboard
          ↓
Docker + Render
```

### PostgreSQL layers

```text
staging
  ↓
curated
  ↓
warehouse
  ↓
analytics
```

The warehouse includes country, region, antigen, infection, and date dimensions,
plus vaccination, infection, and population facts.

Analytics marts include country health summaries, vaccination trends, and
infection burden.

## Orchestration and deployment

The project includes:

- Prefect orchestration and local scheduling
- Docker and Docker Compose
- PostgreSQL for local/container development
- Render Blueprint deployment
- managed PostgreSQL on Render
- `/health` service health check
- an initial cloud ETL refresh through `run_pipeline.py`

The production web service is deployed from the `main` branch.

## Current data-source transition

`immunisation-2.db` is intentionally tracked **temporarily** as the reproducible
seed used by the current Render deployment.

The codebase is in a hybrid transition:

- SQLite remains the seed/source dataset and is still queried by some existing
  product routes.
- The ETL pipeline loads PostgreSQL and builds curated, warehouse, and analytics
  layers.
- The data-quality experience is backed by PostgreSQL.
- Upcoming product work will move more user-facing routes onto the PostgreSQL
  analytics marts.

The long-term goal is to replace the repository seed database with ingestion from
authoritative public-health and travel-health sources.

## Local setup

Create and activate a virtual environment:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Copy the environment template:

```bash
cp .env.example .env
```

Update the local PostgreSQL credentials in `.env`.

Run the ETL pipeline:

```bash
python run_pipeline.py
```

Run the Flask app:

```bash
python app.py
```

Open:

```text
http://127.0.0.1:5001/
http://127.0.0.1:5001/travel
http://127.0.0.1:5001/data-quality
```

## Tests

```bash
python -m pytest -q
```

## Repository rules

Do not commit:

- `.env`
- passwords, tokens, or API keys
- virtual environments
- logs and generated reports
- temporary ZIP packages or backup files

`immunisation-2.db` is the current exception because it is used as the cloud seed.
It should be removed from Git once source ingestion replaces it.

## Completed engineering milestones

- travel-first HealthAtlas product pivot
- PostgreSQL ETL foundation
- data validation and transparent quality scoring
- persistent pipeline-run history
- dimensional warehouse
- analytics marts
- Prefect orchestration
- scheduled local Prefect deployment
- Docker containerisation
- Render cloud deployment

## Next milestones

1. Country directory and search experience
2. Move country product analytics from direct SQLite queries to PostgreSQL marts
3. Travel Planner v2
4. Authoritative public-health/travel-health source connectors
5. API layer
6. Saved trips and user accounts
7. Health alerts and trip monitoring
8. AI analytics copilot
9. B2B API and organisation workspaces

## Product principle

HealthAtlas should make global-health information easier to explore without hiding
where the data came from. Source provenance, freshness, data quality, and explicit
limitations are core product features.
