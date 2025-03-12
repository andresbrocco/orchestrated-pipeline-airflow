"""Location management module for weather pipeline."""

import json
from pathlib import Path

from airflow.providers.postgres.hooks.postgres import PostgresHook

CONFIG_PATH = Path('/opt/airflow/config/locations.json')
POSTGRES_CONN_ID = 'weather_postgres'


def load_locations_from_config():
    """Load locations from the JSON config file."""
    if not CONFIG_PATH.exists():
        return []

    with open(CONFIG_PATH) as f:
        return json.load(f)


def get_locations_from_db():
    """Get all active locations from the database."""
    hook = PostgresHook(postgres_conn_id=POSTGRES_CONN_ID)

    sql = """
        SELECT id, city_name, country_code, latitude, longitude
        FROM locations
        ORDER BY city_name
    """

    records = hook.get_records(sql)

    return [
        {
            'id': row[0],
            'city': row[1],
            'country': row[2],
            'lat': float(row[3]),
            'lon': float(row[4])
        }
        for row in records
    ]


def get_location_by_id(location_id):
    """Get a specific location by its database ID."""
    hook = PostgresHook(postgres_conn_id=POSTGRES_CONN_ID)

    sql = """
        SELECT id, city_name, country_code, latitude, longitude
        FROM locations
        WHERE id = %s
    """

    record = hook.get_first(sql, parameters=(location_id,))

    if not record:
        return None

    return {
        'id': record[0],
        'city': record[1],
        'country': record[2],
        'lat': float(record[3]),
        'lon': float(record[4])
    }


def get_location_by_city(city_name, country_code=None):
    """Get a location by city name and optionally country code."""
    hook = PostgresHook(postgres_conn_id=POSTGRES_CONN_ID)

    if country_code:
        sql = """
            SELECT id, city_name, country_code, latitude, longitude
            FROM locations
            WHERE city_name = %s AND country_code = %s
        """
        record = hook.get_first(sql, parameters=(city_name, country_code))
    else:
        sql = """
            SELECT id, city_name, country_code, latitude, longitude
            FROM locations
            WHERE city_name = %s
        """
        record = hook.get_first(sql, parameters=(city_name,))

    if not record:
        return None

    return {
        'id': record[0],
        'city': record[1],
        'country': record[2],
        'lat': float(record[3]),
        'lon': float(record[4])
    }


def get_api_params(location):
    """Format location data for OpenWeatherMap API call."""
    return {
        'lat': location['lat'],
        'lon': location['lon']
    }
