import pandas as pd

from pipeline.validation.checks import (
    validate_dataframe,
    validate_required_tables,
)


def test_missing_required_table_is_error():
    issues = validate_required_tables(
        ["Country", "Region"]
    )

    assert any(
        issue.severity == "ERROR"
        for issue in issues
    )


def test_non_positive_population_warning():
    source = pd.DataFrame(
        {"population": [100, 0, -1]}
    )

    issues = validate_dataframe(
        "CountryPopulation",
        source,
    )

    issue = next(
        issue
        for issue in issues
        if (
            issue.check
            == "population_positive"
        )
    )

    assert issue.count == 2


def test_coverage_above_100_is_info():
    source = pd.DataFrame(
        {"coverage": [95, 105]}
    )

    issues = validate_dataframe(
        "Vaccination",
        source,
    )

    issue = next(
        item
        for item in issues
        if (
            item.check
            == "coverage_above_100"
        )
    )

    assert issue.severity == "INFO"
    assert issue.count == 1
