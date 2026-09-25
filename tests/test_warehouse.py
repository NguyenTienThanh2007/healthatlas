from pipeline.load.warehouse_builder import (
    DIMENSION_TABLES,
    FACT_TABLES,
    WAREHOUSE_TABLES,
)


def test_warehouse_has_expected_dimensions():
    assert DIMENSION_TABLES == (
        "dim_region",
        "dim_country",
        "dim_antigen",
        "dim_infection",
        "dim_date",
    )


def test_warehouse_has_expected_facts():
    assert FACT_TABLES == (
        "fact_vaccination",
        "fact_population",
        "fact_infection",
    )


def test_warehouse_manifest_contains_eight_tables():
    assert len(WAREHOUSE_TABLES) == 8
    assert len(set(WAREHOUSE_TABLES)) == 8
