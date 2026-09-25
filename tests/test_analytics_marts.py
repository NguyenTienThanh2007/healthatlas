from pipeline.load.analytics_marts import MART_VIEWS


def test_expected_analytics_marts():
    assert MART_VIEWS == (
        "country_health_summary",
        "vaccination_trends",
        "infection_burden",
    )


def test_analytics_mart_names_are_unique():
    assert len(MART_VIEWS) == len(set(MART_VIEWS))
