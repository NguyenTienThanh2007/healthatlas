from pipeline.orchestration.scheduler import (
    DEFAULT_CRON,
    DEFAULT_DEPLOYMENT_NAME,
    DEFAULT_TIMEZONE,
    build_schedule,
    get_schedule_settings,
)


def test_default_schedule_settings(
    monkeypatch,
):
    monkeypatch.delenv(
        "PREFECT_CRON",
        raising=False,
    )
    monkeypatch.delenv(
        "PREFECT_TIMEZONE",
        raising=False,
    )
    monkeypatch.delenv(
        "PREFECT_DEPLOYMENT_NAME",
        raising=False,
    )

    assert get_schedule_settings() == (
        DEFAULT_CRON,
        DEFAULT_TIMEZONE,
        DEFAULT_DEPLOYMENT_NAME,
    )


def test_schedule_uses_vietnam_timezone(
    monkeypatch,
):
    monkeypatch.delenv(
        "PREFECT_CRON",
        raising=False,
    )
    monkeypatch.delenv(
        "PREFECT_TIMEZONE",
        raising=False,
    )

    schedule = build_schedule()

    assert schedule.cron == DEFAULT_CRON
    assert schedule.timezone == DEFAULT_TIMEZONE


def test_schedule_can_be_overridden(
    monkeypatch,
):
    monkeypatch.setenv(
        "PREFECT_CRON",
        "30 7 * * *",
    )
    monkeypatch.setenv(
        "PREFECT_TIMEZONE",
        "Australia/Melbourne",
    )
    monkeypatch.setenv(
        "PREFECT_DEPLOYMENT_NAME",
        "healthatlas-melbourne",
    )

    cron, timezone, name = (
        get_schedule_settings()
    )

    assert cron == "30 7 * * *"
    assert timezone == "Australia/Melbourne"
    assert name == "healthatlas-melbourne"
