from pipeline.orchestration.prefect_flow import (
    healthatlas_etl_flow,
    run_full_refresh_task,
)


def test_prefect_flow_name():
    assert (
        healthatlas_etl_flow.name
        == "healthatlas-etl"
    )


def test_prefect_task_name():
    assert (
        run_full_refresh_task.name
        == "healthatlas-full-refresh"
    )


def test_prefect_task_has_retries():
    assert run_full_refresh_task.retries == 2
