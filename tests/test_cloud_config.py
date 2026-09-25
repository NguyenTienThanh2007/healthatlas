from pathlib import Path

import yaml

from pipeline.config import build_postgres_url


def test_database_url_override(monkeypatch):
    monkeypatch.setenv(
        "DATABASE_URL",
        "postgresql://cloud_user:cloud_password@cloud-db:5432/healthatlas",
    )

    url = build_postgres_url()

    assert url.drivername == "postgresql+psycopg"
    assert url.username == "cloud_user"
    assert url.host == "cloud-db"
    assert url.port == 5432
    assert url.database == "healthatlas"


def test_database_url_postgres_alias(monkeypatch):
    monkeypatch.setenv(
        "DATABASE_URL",
        "postgres://cloud_user:cloud_password@cloud-db:5432/healthatlas",
    )

    url = build_postgres_url()

    assert url.drivername == "postgresql+psycopg"


def test_render_blueprint_structure():
    blueprint = yaml.safe_load(
        Path("render.yaml").read_text(encoding="utf-8")
    )

    service = blueprint["services"][0]
    database = blueprint["databases"][0]

    assert service["type"] == "web"
    assert service["runtime"] == "docker"
    assert service["plan"] == "free"
    assert service["region"] == "singapore"
    assert service["healthCheckPath"] == "/health"
    assert (
        service["initialDeployHook"]
        == "python run_pipeline.py"
    )
    assert "preDeployCommand" not in service

    assert database["name"] == "healthatlas-db"
    assert database["plan"] == "free"
    assert database["region"] == "singapore"
    assert database["postgresMajorVersion"] == "18"
