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


def extract_all_locations(**context):
    """Extract weather data for all locations."""
    ti = context['ti']
    locations = ti.xcom_pull(key='locations', task_ids='get_locations')

    extracted_data = []
    for location in locations:
        raw_data = extract_weather_data(location, **context)
        extracted_data.append({
            'location_id': location['id'],
            'city': location['city'],
            'raw_data': raw_data
        })

    return extracted_data


def transform_all_locations(**context):
    """Transform weather data for all locations."""
    ti = context['ti']
    extracted_data = ti.xcom_pull(task_ids='extract_weather')

    if not extracted_data:
        raise ValueError('No data received from extract task')

    transformed_data = []
    for item in extracted_data:
        transformed = transform_data(item['raw_data'], **context)
        transformed_data.append({
            'location_id': item['location_id'],
            'city': item['city'],
            'transformed': transformed
        })

    return transformed_data


def load_all_locations(**context):
    """Load weather data for all locations."""
    ti = context['ti']
    transformed_data = ti.xcom_pull(task_ids='transform_weather')

    if not transformed_data:
        raise ValueError('No data received from transform task')

    results = []
    for item in transformed_data:
        loaded = load_data(item['transformed'], **context)
        results.append({
            'location': item['city'],
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

    extract_task = PythonOperator(
        task_id='extract_weather',
        python_callable=extract_all_locations,
    )

    transform_task = PythonOperator(
        task_id='transform_weather',
        python_callable=transform_all_locations,
    )

    load_task = PythonOperator(
        task_id='load_weather',
        python_callable=load_all_locations,
    )

    api_health_check >> get_locations_task >> extract_task >> transform_task >> load_task
