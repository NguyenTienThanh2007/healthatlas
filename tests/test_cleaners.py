import pandas as pd

from pipeline.transform.cleaners import normalize_dataframe


def test_empty_strings_become_null():
    source = pd.DataFrame(
        {
            "CountryID": ["AUS", "VNM"],
            "name": [" Australia ", ""],
        }
    )

    result = normalize_dataframe(source)

    assert list(result["country_id"]) == [
        "AUS",
        "VNM",
    ]
    assert result.loc[0, "name"] == "Australia"
    assert pd.isna(
        result.loc[1, "name"]
    )


def test_numeric_columns_are_converted():
    source = pd.DataFrame(
        {
            "year": ["2020", "2021"],
            "coverage": ["95.2", ""],
            "population": ["1000", "2000"],
        }
    )

    result = normalize_dataframe(source)

    assert result.loc[0, "year"] == 2020
    assert result.loc[0, "coverage"] == 95.2
    assert pd.isna(
        result.loc[1, "coverage"]
    )
    assert (
        result.loc[1, "population"]
        == 2000
    )


def test_coverage_above_100_is_preserved():
    source = pd.DataFrame(
        {"coverage": ["108.5"]}
    )

    result = normalize_dataframe(source)

    assert result.loc[0, "coverage"] == 108.5
