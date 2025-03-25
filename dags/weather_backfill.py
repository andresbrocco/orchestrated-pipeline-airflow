"""Backfill DAG for historical weather data using One Call API 3.0.

Uses the timemachine endpoint to fetch actual historical weather data:
https://api.openweathermap.org/data/3.0/onecall/timemachine

NOTE: This endpoint requires a paid subscription to OpenWeatherMap's One Call API 3.0.
Data is available from January 1st, 1979 till 4 days ahead.

This DAG shows:
- Manual trigger with configurable date ranges
- Historical data extraction from timemachine endpoint
- Duplicate prevention by checking existing observations
- Backfill progress tracking and logging
- Respecting API rate limits during bulk operations
"""

from datetime import datetime, timedelta, timezone
import logging
import sys
import time
from pathlib import Path

from tasks.locations import get_locations_from_db
from tasks.extract import get_api_key
from tasks.transform import kelvin_to_celsius
from tasks.load import load_observation
from airflow.providers.postgres.hooks.postgres import PostgresHook
import requests

from airflow import DAG
from airflow.providers.standard.operators.python import PythonOperator
from airflow.sdk import Param

dags_folder = Path(__file__).parent
if str(dags_folder) not in sys.path:
    sys.path.insert(0, str(dags_folder))


logger = logging.getLogger(__name__)

POSTGRES_CONN_ID = "weather_postgres"


def generate_backfill_dates(**context):
    """Generate list of dates to backfill based on DAG params."""
    params = context["params"]
    start_date_str = params.get("start_date")
    end_date_str = params.get("end_date")

    if not start_date_str or not end_date_str:
        raise ValueError("start_date and end_date parameters are required")

    start_date = datetime.fromisoformat(start_date_str)
    end_date = datetime.fromisoformat(end_date_str)

    if start_date > end_date:
        raise ValueError("start_date must be before end_date")

    if (end_date - start_date).days > 30:
        logger.warning("Backfill range exceeds 30 days - this may take a long time")

    dates = []
    current = start_date
    while current <= end_date:
        dates.append(current.isoformat())
        current += timedelta(days=1)

    logger.info(
        f"Generated {len(dates)} dates for backfill: {start_date_str} to {end_date_str}"
    )
    context["ti"].xcom_push(key="backfill_dates", value=dates)

    return dates


def get_backfill_locations(**context):
    """Get locations for backfill."""
    locations = get_locations_from_db()

    if not locations:
        raise ValueError("No locations found in database")

    logger.info(f"Found {len(locations)} locations to backfill")
    context["ti"].xcom_push(key="locations", value=locations)

    return locations


def check_existing_observations(location_id, target_date):
    """Check if observation already exists for location and date."""
    hook = PostgresHook(postgres_conn_id=POSTGRES_CONN_ID)

    sql = """
        SELECT COUNT(*)
        FROM weather_observations
        WHERE location_id = %s
        AND DATE(observation_time) = DATE(%s)
    """

    result = hook.get_first(sql, parameters=(location_id, target_date))
    count = result[0] if result else 0

    return count > 0


def fetch_historical_weather(lat, lon, timestamp):
    """Fetch historical weather data from One Call API 3.0 timemachine endpoint."""
    api_key = get_api_key()
    if not api_key:
        raise ValueError("API key not configured")

    url = "https://api.openweathermap.org/data/3.0/onecall/timemachine"
    params = {"lat": lat, "lon": lon, "dt": int(timestamp), "appid": api_key}

    response = requests.get(url, params=params, timeout=10)

    if response.status_code == 401:
        raise ValueError(
            "Invalid API key or subscription required for One Call API 3.0"
        )
    elif response.status_code == 404:
        raise ValueError("Historical data not found for this location/time")
    elif response.status_code != 200:
        raise Exception(f"API error: {response.status_code}")

    return response.json()


def transform_historical_weather(raw_data):
    """Transform historical weather data from timemachine endpoint."""
    if "data" not in raw_data or not raw_data["data"]:
        return None

    data = raw_data["data"][0]

    return {
        "observation_time": datetime.fromtimestamp(data["dt"], tz=timezone.utc),
        "temperature": kelvin_to_celsius(data.get("temp")),
        "feels_like": kelvin_to_celsius(data.get("feels_like")),
        "humidity": data.get("humidity"),
        "pressure": data.get("pressure"),
        "wind_speed": data.get("wind_speed"),
        "wind_direction": data.get("wind_deg"),
        "weather_condition": data["weather"][0]["main"]
        if data.get("weather")
        else None,
        "weather_description": data["weather"][0]["description"]
        if data.get("weather")
        else None,
        "cloudiness": data.get("clouds"),
        "visibility": data.get("visibility"),
    }


def backfill_location_date(location, target_date_str):
    """Backfill historical weather data for a specific location and date."""
    target_date = datetime.fromisoformat(target_date_str)
    location_id = location["id"]
    city = location.get("city", "Unknown")

    if check_existing_observations(location_id, target_date):
        logger.info(f"Skipping {city} for {target_date_str} - data already exists")
        return {"status": "skipped", "reason": "already_exists"}

    logger.info(f"Backfilling {city} for {target_date_str}")

    try:
        timestamp = int(target_date.replace(hour=12, minute=0, second=0).timestamp())
        raw_data = fetch_historical_weather(location["lat"], location["lon"], timestamp)

        transformed = transform_historical_weather(raw_data)

        if not transformed:
            raise ValueError("No historical data returned from API")

        load_observation(location_id, transformed)

        logger.info(f"Successfully backfilled {city} for {target_date_str}")
        return {"status": "success", "city": city, "date": target_date_str}

    except Exception as e:
        logger.error(f"Failed to backfill {city} for {target_date_str}: {e}")
        return {
            "status": "failed",
            "city": city,
            "date": target_date_str,
            "error": str(e),
        }


def execute_backfill(**context):
    """Execute backfill for all locations and dates."""
    ti = context["ti"]

    locations = ti.xcom_pull(key="locations", task_ids="get_backfill_locations")
    dates = ti.xcom_pull(key="backfill_dates", task_ids="generate_dates")

    if not locations or not dates:
        raise ValueError("No locations or dates to backfill")

    total_operations = len(locations) * len(dates)
    logger.info(
        f"Starting backfill: {len(locations)} locations × {len(dates)} dates = {total_operations} operations"
    )

    results = {"success": 0, "skipped": 0, "failed": 0, "total": total_operations}

    for date_str in dates:
        for location in locations:
            result = backfill_location_date(location, date_str)

            if result["status"] == "success":
                results["success"] += 1
            elif result["status"] == "skipped":
                results["skipped"] += 1
            else:
                results["failed"] += 1

            time.sleep(1)

        completed = results["success"] + results["skipped"] + results["failed"]
        progress = (completed / total_operations) * 100
        logger.info(f"Progress: {completed}/{total_operations} ({progress:.1f}%)")

    logger.info("=== Backfill Summary ===")
    logger.info(f"Total operations: {results['total']}")
    logger.info(f"Successful: {results['success']}")
    logger.info(f"Skipped (already exist): {results['skipped']}")
    logger.info(f"Failed: {results['failed']}")

    ti.xcom_push(key="backfill_results", value=results)

    return results


default_args = {
    "owner": "airflow",
    "retries": 2,
    "retry_delay": timedelta(minutes=5),
}


with DAG(
    dag_id="weather_backfill",
    default_args=default_args,
    description="Backfill historical weather data using One Call API 3.0 timemachine endpoint",
    schedule=None,
    start_date=datetime(2025, 3, 1),
    catchup=False,
    tags=["weather", "backfill"],
    params={
        "start_date": Param(
            default="2025-03-01",
            type="string",
            description="Start date for backfill (YYYY-MM-DD format)",
        ),
        "end_date": Param(
            default="2025-03-07",
            type="string",
            description="End date for backfill (YYYY-MM-DD format)",
        ),
    },
) as dag:
    generate_dates_task = PythonOperator(
        task_id="generate_dates",
        python_callable=generate_backfill_dates,
    )

    get_locations_task = PythonOperator(
        task_id="get_backfill_locations",
        python_callable=get_backfill_locations,
    )

    backfill_task = PythonOperator(
        task_id="execute_backfill",
        python_callable=execute_backfill,
        execution_timeout=timedelta(hours=2),
    )

    [generate_dates_task, get_locations_task] >> backfill_task
