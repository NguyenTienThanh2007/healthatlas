from pipeline.orchestration.prefect_flow import (
    healthatlas_etl_flow,
)


if __name__ == "__main__":
    result = healthatlas_etl_flow()

    print()
    print(
        "=== HEALTHATLAS PREFECT SUMMARY ==="
    )
    print(result)
