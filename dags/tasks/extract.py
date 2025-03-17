"""API extraction module for OpenWeatherMap data."""

import json
import time
import logging
import requests

from airflow.sdk.bases.hook import BaseHook

logger = logging.getLogger(__name__)

BASE_URL = 'https://api.openweathermap.org/data/2.5'
CONN_ID = 'openweathermap_api'


def get_api_key():
    """Get API key from Airflow connection."""
    conn = BaseHook.get_connection(CONN_ID)
    extra = json.loads(conn.extra) if conn.extra else {}
    return extra.get('api_key')


def fetch_current_weather(lat, lon, retries=3):
    """Fetch current weather data for a location."""
    api_key = get_api_key()
    if not api_key:
        raise ValueError('OpenWeatherMap API key not configured')

    url = f'{BASE_URL}/weather'
    params = {
        'lat': lat,
        'lon': lon,
        'appid': api_key
    }

    return _make_request(url, params, retries)


def fetch_forecast(lat, lon, retries=3):
    """Fetch 5-day forecast data for a location."""
    api_key = get_api_key()
    if not api_key:
        raise ValueError('OpenWeatherMap API key not configured')

    url = f'{BASE_URL}/forecast'
    params = {
        'lat': lat,
        'lon': lon,
        'appid': api_key
    }

    return _make_request(url, params, retries)


def fetch_weather_for_location(location, include_forecast=True):
    """Fetch both current weather and forecast for a location."""
    lat = location['lat']
    lon = location['lon']
    city = location.get('city', 'Unknown')

    logger.info(f'Fetching weather data for {city} ({lat}, {lon})')

    result = {
        'location': location,
        'current': fetch_current_weather(lat, lon),
        'forecast': None
    }

    if include_forecast:
        result['forecast'] = fetch_forecast(lat, lon)

    return result


def _make_request(url, params, retries=3):
    """Make HTTP request with retry logic and error handling."""
    last_error = None

    for attempt in range(retries):
        start_time = time.time()

        try:
            response = requests.get(url, params=params, timeout=30)
            elapsed = time.time() - start_time

            logger.info(f'API call to {url} - Status: {response.status_code}, Time: {elapsed:.2f}s')

            if response.status_code == 200:
                return response.json()

            if response.status_code == 401:
                raise ValueError('Invalid API key')

            if response.status_code == 404:
                raise ValueError('Location not found')

            if response.status_code == 429:
                # Rate limit - wait and retry
                wait_time = 2 ** attempt
                logger.warning(f'Rate limited, waiting {wait_time}s before retry')
                time.sleep(wait_time)
                last_error = Exception('Rate limit exceeded')
                continue

            if response.status_code >= 500:
                # Server error - retry
                wait_time = 2 ** attempt
                logger.warning(f'Server error {response.status_code}, waiting {wait_time}s before retry')
                time.sleep(wait_time)
                last_error = Exception(f'Server error: {response.status_code}')
                continue

            # Other errors
            response.raise_for_status()

        except requests.exceptions.Timeout:
            wait_time = 2 ** attempt
            logger.warning(f'Request timeout, waiting {wait_time}s before retry')
            time.sleep(wait_time)
            last_error = Exception('Request timeout')
            continue

        except requests.exceptions.ConnectionError as e:
            wait_time = 2 ** attempt
            logger.warning(f'Connection error, waiting {wait_time}s before retry')
            time.sleep(wait_time)
            last_error = e
            continue

    raise last_error or Exception('Max retries exceeded')
