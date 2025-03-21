"""Main weather data ETL pipeline DAG."""

from datetime import datetime, timedelta
import logging

from airflow import DAG
from airflow.providers.standard.operators.python import (
    PythonOperator,
    BranchPythonOperator,
)

from tasks.locations import get_locations_from_db
from tasks.extract import fetch_weather_for_location, get_api_metrics
from tasks.transform import transform_weather_data
from tasks.load import load_weather_data
from tasks.validate import check_data_quality
from sensors.api_health_sensor import OpenWeatherMapHealthSensor

logger = logging.getLogger(__name__)


def alert_failure(context):
    """Alert on task failure."""
    task_instance = context["task_instance"]
    dag_id = context["dag"].dag_id
    task_id = task_instance.task_id
    execution_date = context["execution_date"]
    exception = context.get("exception")

    logger.error(f"Task failed: {dag_id}.{task_id}")
    logger.error(f"Execution date: {execution_date}")
    logger.error(f"Exception: {exception}")
    logger.error(f"Try number: {task_instance.try_number}")


default_args = {
    "owner": "airflow",
    "retries": 3,
    "retry_delay": timedelta(minutes=5),
    "retry_exponential_backoff": True,
    "max_retry_delay": timedelta(minutes=30),
    "execution_timeout": timedelta(minutes=10),
    "email_on_failure": True,
    "email_on_retry": False,
    "email": ["andresbrocco@gmail.com"],
    "on_failure_callback": alert_failure,
}


def get_locations(**context):
    """Retrieve all active locations from database."""
    locations = get_locations_from_db()

    if not locations:
        raise ValueError("No locations found in database")

    context["ti"].xcom_push(key="locations", value=locations)
    return locations


def extract_weather_data(location, **context):
    """Extract weather data from API for a specific location."""
    raw_data = fetch_weather_for_location(location, include_forecast=True)
    return raw_data


def transform_data(raw_data, **context):
    """Transform raw API data into database format."""
    transformed = transform_weather_data(raw_data)
    return transformed


def load_data(transformed_data, **context):
    """Load transformed data into PostgreSQL."""
    result = load_weather_data(transformed_data)
    return result


def extract_all_locations(**context):
    """Extract weather data for all locations."""
    ti = context["ti"]
    locations = ti.xcom_pull(key="locations", task_ids="get_locations")

    extracted_data = []
    for location in locations:
        raw_data = extract_weather_data(location, **context)
        extracted_data.append(
            {
                "location_id": location["id"],
                "city": location["city"],
                "raw_data": raw_data,
            }
        )

    # Log API metrics summary
    metrics = get_api_metrics()
    logger.info("=== API Metrics Summary ===")
    logger.info(f"Total API calls: {metrics['total_calls']}")
    logger.info(f"Successful: {metrics['successful_calls']}, Failed: {metrics['failed_calls']}")
    logger.info(f"Success rate: {metrics['success_rate']:.1f}%")
    logger.info(f"Average response time: {metrics['avg_response_time']:.0f}ms")
    logger.info(f"Slow calls (>2s): {metrics['slow_calls']}")

    if metrics['rate_limits']:
        latest_rate = metrics['rate_limits'][-1]
        logger.info(f"Rate limit status: {latest_rate['remaining']}/{latest_rate['limit']} remaining")

    # Store metrics in XCom for potential monitoring
    ti.xcom_push(key="api_metrics", value=metrics)

    return extracted_data


def transform_all_locations(**context):
    """Transform weather data for all locations."""
    ti = context["ti"]
    extracted_data = ti.xcom_pull(task_ids="extract_weather")

    if not extracted_data:
        raise ValueError("No data received from extract task")

    transformed_data = []
    for item in extracted_data:
        transformed = transform_data(item["raw_data"], **context)
        transformed_data.append(
            {
                "location_id": item["location_id"],
                "city": item["city"],
                "transformed": transformed,
            }
        )

    return transformed_data


def check_quality(**context):
    """Check data quality and decide next task."""
    ti = context["ti"]
    transformed_data = ti.xcom_pull(task_ids="transform_weather")

    if not transformed_data:
        logger.warning("No data to check quality")
        return "quality_alert"

    quality_ok = check_data_quality(transformed_data)

    if quality_ok:
        logger.info("Quality check passed, proceeding to load")
        return "load_weather"
    else:
        logger.warning("Quality check failed, skipping load")
        return "quality_alert"


def quality_alert(**context):
    """Alert on poor data quality."""
    ti = context["ti"]
    transformed_data = ti.xcom_pull(task_ids="transform_weather")

    logger.warning("Data quality alert: Issues detected in weather data")
    logger.warning("Load task skipped due to quality concerns")

    if transformed_data:
        logger.warning(f"Affected locations: {len(transformed_data)}")

    return "quality_alert_sent"


def load_all_locations(**context):
    """Load weather data for all locations."""
    ti = context["ti"]
    transformed_data = ti.xcom_pull(task_ids="transform_weather")

    if not transformed_data:
        raise ValueError("No data received from transform task")

    results = []
    for item in transformed_data:
        loaded = load_data(item["transformed"], **context)
        results.append({"location": item["city"], "loaded": loaded})

    return results


with DAG(
    dag_id="weather_data_pipeline",
    default_args=default_args,
    description="ETL pipeline for weather data from OpenWeatherMap API",
    schedule="@hourly",
    start_date=datetime(2025, 3, 10),
    catchup=False,
    tags=["weather", "etl"],
) as dag:
    api_health_check = OpenWeatherMapHealthSensor(
        task_id="check_api_health",
        poke_interval=60,
        timeout=300,
        mode="poke",
    )

    get_locations_task = PythonOperator(
        task_id="get_locations",
        python_callable=get_locations,
    )

    extract_task = PythonOperator(
        task_id="extract_weather",
        python_callable=extract_all_locations,
        retries=5,
        retry_delay=timedelta(minutes=5),
    )

    transform_task = PythonOperator(
        task_id="transform_weather",
        python_callable=transform_all_locations,
        retries=2,
        retry_delay=timedelta(minutes=2),
        retry_exponential_backoff=False,
    )

    quality_check = BranchPythonOperator(
        task_id="check_quality",
        python_callable=check_quality,
    )

    load_task = PythonOperator(
        task_id="load_weather",
        python_callable=load_all_locations,
    )

    alert_task = PythonOperator(
        task_id="quality_alert",
        python_callable=quality_alert,
    )

    (
        api_health_check
        >> get_locations_task
        >> extract_task
        >> transform_task
        >> quality_check
    )
    quality_check >> [load_task, alert_task]
