# HealthAtlas

**Travel smarter. Understand global health.**

HealthAtlas is a travel-first global health intelligence platform. The consumer experience starts with a destination and trip context, while the underlying product retains deeper vaccination, infectious-disease, country-comparison, insight, and data-quality analytics.

Vaccination is now one module inside a broader global-health product rather than the entire product.

## Current milestone

This repository starts from the HealthAtlas product pivot and includes:

- Travel-first HealthAtlas branding
- `/travel` Travel Health Planner
- origin, destination, departure date, and trip duration inputs
- destination health snapshot backed by the existing public-health dataset
- country profiles
- vaccination analytics
- infectious-disease analytics
- country comparison
- global insights
- data-quality centre
- light/dark UI and interactive dashboard features

HealthAtlas does **not** currently provide medical diagnosis or personalised medical advice. Future travel-health guidance should be connected to authoritative sources and display source/freshness metadata.

## Architecture today

```text
SQLite public-health dataset
        ↓
      Flask
        ↓
HealthAtlas Web Product
   ├── Travel Planner
   ├── Country Profiles
   ├── Vaccination Analytics
   ├── Infection Analytics
   ├── Compare
   ├── Insights
   └── Data Quality
```

## Long-term architecture

```text
Authoritative public health sources
              ↓
          Ingestion
              ↓
        Raw / Staging
              ↓
       Data Validation
              ↓
          PostgreSQL
              ↓
      Analytics Warehouse
              ↓
           FastAPI
       ┌──────┼──────┐
       ↓      ↓      ↓
    Travel  Analytics API
       ↓
 Alerts / AI / Forecasting
```

## Local setup

Create a virtual environment:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

The current milestone uses `immunisation-2.db`. The database is intentionally not committed to this new repository. If you are developing from the original course project locally, copy it into this repo:

```bash
cp ~/Documents/cosc3106-immunisation-project/immunisation-2.db ./immunisation-2.db
```

Run:

```bash
python3 app.py
```

Open:

```text
http://127.0.0.1:5001/
http://127.0.0.1:5001/travel
```

## Roadmap

1. Travel-first product pivot
2. Authoritative travel-health source connectors
3. PostgreSQL ETL + data quality
4. Dimensional warehouse
5. Orchestration + dbt
6. FastAPI analytics layer
7. Saved trips + accounts
8. Health alerts and trip monitoring
9. AI analytics copilot
10. B2B API and organisation workspaces
11. SaaS subscriptions

## Product principle

HealthAtlas should make global-health information easier to explore without hiding where the data came from. Source provenance, freshness, data quality, and explicit limitations are core product features.
