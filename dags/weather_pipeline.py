"""Main weather data ETL pipeline DAG."""

from datetime import datetime, timedelta

from airflow import DAG
from airflow.providers.standard.operators.python import PythonOperator

from tasks.locations import get_locations_from_db
from tasks.extract import fetch_weather_for_location
from tasks.transform import transform_weather_data
from tasks.load import load_weather_data
from sensors.api_health_sensor import OpenWeatherMapHealthSensor


default_args = {
    'owner': 'airflow',
    'retries': 3,
    'retry_delay': timedelta(minutes=5),
    'execution_timeout': timedelta(minutes=10),
}


def get_locations(**context):
    """Retrieve all active locations from database."""
    locations = get_locations_from_db()

    if not locations:
        raise ValueError('No locations found in database')

    context['ti'].xcom_push(key='locations', value=locations)
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


def process_all_locations(**context):
    """Process weather data for all locations sequentially."""
    ti = context['ti']
    locations = ti.xcom_pull(key='locations', task_ids='get_locations')

    results = []
    for location in locations:
        raw_data = extract_weather_data(location)
        transformed_data = transform_data(raw_data)
        loaded = load_data(transformed_data)

        results.append({
            'location': location['city'],
            'loaded': loaded
        })

    return results


with DAG(
    dag_id='weather_data_pipeline',
    default_args=default_args,
    description='ETL pipeline for weather data from OpenWeatherMap API',
    schedule='@hourly',
    start_date=datetime(2025, 3, 10),
    catchup=False,
    tags=['weather', 'etl'],
) as dag:

    api_health_check = OpenWeatherMapHealthSensor(
        task_id='check_api_health',
        poke_interval=60,
        timeout=300,
        mode='poke',
    )

    get_locations_task = PythonOperator(
        task_id='get_locations',
        python_callable=get_locations,
    )

    process_locations_task = PythonOperator(
        task_id='process_all_locations',
        python_callable=process_all_locations,
    )

    api_health_check >> get_locations_task >> process_locations_task
