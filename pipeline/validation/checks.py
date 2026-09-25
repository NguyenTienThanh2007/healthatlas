from __future__ import annotations

from dataclasses import asdict, dataclass

import pandas as pd


REQUIRED_TABLES = {
    "Antigen",
    "Country",
    "CountryPopulation",
    "Economy",
    "InfectionData",
    "Infection_Type",
    "Region",
    "Vaccination",
}


@dataclass
class ValidationIssue:
    severity: str
    table: str
    check: str
    count: int
    message: str

    def to_dict(self) -> dict:
        return asdict(self)


def validate_required_tables(
    source_tables: list[str],
) -> list[ValidationIssue]:
    missing = sorted(REQUIRED_TABLES.difference(source_tables))

    return [
        ValidationIssue(
            severity="ERROR",
            table=table,
            check="required_table_exists",
            count=1,
            message=f"Required source table '{table}' is missing.",
        )
        for table in missing
    ]


def validate_dataframe(
    table_name: str,
    dataframe: pd.DataFrame,
) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []

    if dataframe.empty:
        issues.append(
            ValidationIssue(
                severity="WARNING",
                table=table_name,
                check="table_not_empty",
                count=0,
                message="Table contains no rows.",
            )
        )
        return issues

    for column, count in dataframe.isna().sum().items():
        if int(count) > 0:
            issues.append(
                ValidationIssue(
                    severity="INFO",
                    table=table_name,
                    check=f"null_values:{column}",
                    count=int(count),
                    message=f"{count} NULL value(s) found in '{column}'.",
                )
            )

    if "year" in dataframe.columns:
        invalid = int(
            (
                dataframe["year"].notna()
                & (
                    (dataframe["year"] < 1900)
                    | (dataframe["year"] > 2100)
                )
            ).sum()
        )
        if invalid:
            issues.append(
                ValidationIssue(
                    severity="WARNING",
                    table=table_name,
                    check="year_range",
                    count=invalid,
                    message="Year values outside 1900–2100 were found.",
                )
            )

    if "population" in dataframe.columns:
        invalid = int(
            (
                dataframe["population"].notna()
                & (dataframe["population"] <= 0)
            ).sum()
        )
        if invalid:
            issues.append(
                ValidationIssue(
                    severity="WARNING",
                    table=table_name,
                    check="population_positive",
                    count=invalid,
                    message="Population values <= 0 were found.",
                )
            )

    if "coverage" in dataframe.columns:
        negative = int(
            (
                dataframe["coverage"].notna()
                & (dataframe["coverage"] < 0)
            ).sum()
        )
        above_100 = int(
            (
                dataframe["coverage"].notna()
                & (dataframe["coverage"] > 100)
            ).sum()
        )

        if negative:
            issues.append(
                ValidationIssue(
                    severity="WARNING",
                    table=table_name,
                    check="coverage_negative",
                    count=negative,
                    message="Negative vaccination coverage values were found.",
                )
            )

        if above_100:
            issues.append(
                ValidationIssue(
                    severity="INFO",
                    table=table_name,
                    check="coverage_above_100",
                    count=above_100,
                    message=(
                        "Coverage values above 100 were found and preserved "
                        "for data-quality analysis."
                    ),
                )
            )

    return issues
