"""API extraction module for OpenWeatherMap data."""

import json
import time
import logging
import requests

from airflow.sdk.bases.hook import BaseHook

logger = logging.getLogger(__name__)

# API metrics tracking
api_metrics = {
    "total_calls": 0,
    "successful_calls": 0,
    "failed_calls": 0,
    "total_response_time": 0,
    "slow_calls": 0,
}

BASE_URL = "https://api.openweathermap.org/data/2.5"
CONN_ID = "openweathermap_api"


def get_api_key():
    """Get API key from Airflow connection."""
    conn = BaseHook.get_connection(CONN_ID)
    extra = json.loads(conn.extra) if conn.extra else {}
    return extra.get("api_key")


def fetch_current_weather(lat, lon, retries=3):
    """Fetch current weather data for a location."""
    api_key = get_api_key()
    if not api_key:
        raise ValueError("OpenWeatherMap API key not configured")

    url = f"{BASE_URL}/weather"
    params = {"lat": lat, "lon": lon, "appid": api_key}

    return _make_request(url, params, retries)


def fetch_forecast(lat, lon, retries=3):
    """Fetch 5-day forecast data for a location."""
    api_key = get_api_key()
    if not api_key:
        raise ValueError("OpenWeatherMap API key not configured")

    url = f"{BASE_URL}/forecast"
    params = {"lat": lat, "lon": lon, "appid": api_key}

    return _make_request(url, params, retries)


def fetch_weather_for_location(location, include_forecast=True):
    """Fetch both current weather and forecast for a location."""
    lat = location["lat"]
    lon = location["lon"]
    city = location.get("city", "Unknown")

    logger.info(f"Fetching weather data for {city} ({lat}, {lon})")

    start_time = time.perf_counter()

    result = {
        "location": location,
        "current": fetch_current_weather(lat, lon),
        "forecast": None,
    }

    if include_forecast:
        result["forecast"] = fetch_forecast(lat, lon)

    total_time = (time.perf_counter() - start_time) * 1000
    logger.info(f"Completed fetch for {city} in {total_time:.0f}ms")

    return result


def get_api_metrics():
    """Return current API metrics for this task run."""
    metrics = api_metrics.copy()

    if metrics["total_calls"] > 0:
        metrics["avg_response_time"] = (
            metrics["total_response_time"] / metrics["total_calls"]
        )
        metrics["success_rate"] = (
            metrics["successful_calls"] / metrics["total_calls"]
        ) * 100
    else:
        metrics["avg_response_time"] = 0
        metrics["success_rate"] = 0

    return metrics


def _make_request(url, params, retries=3):
    """Make HTTP request with retry logic and error handling."""
    last_error = None
    endpoint = url.split("/")[-1]

    for attempt in range(retries):
        start_time = time.perf_counter()

        try:
            response = requests.get(url, params=params, timeout=30)
            elapsed_ms = (time.perf_counter() - start_time) * 1000

            # Track metrics
            api_metrics["total_calls"] += 1
            api_metrics["total_response_time"] += elapsed_ms

            # Log response details
            logger.info(
                f"API call to {endpoint} took {elapsed_ms:.0f}ms, status: {response.status_code}"
            )

            # Warn on slow responses
            if elapsed_ms > 2000:
                api_metrics["slow_calls"] += 1
                logger.warning(
                    f"Slow API response: {endpoint} took {elapsed_ms:.0f}ms (>2000ms threshold)"
                )

            if response.status_code == 200:
                api_metrics["successful_calls"] += 1
                return response.json()

            # Track failed calls
            api_metrics["failed_calls"] += 1

            if response.status_code == 401:
                raise ValueError("Invalid API key")

            if response.status_code == 404:
                raise ValueError("Location not found")

            if response.status_code == 429:
                wait_time = 2**attempt
                logger.warning(
                    f"Rate limited on {endpoint}, waiting {wait_time}s before retry"
                )
                time.sleep(wait_time)
                last_error = Exception("Rate limit exceeded")
                continue

            if response.status_code >= 500:
                wait_time = 2**attempt
                logger.warning(
                    f"Server error {response.status_code} on {endpoint}, waiting {wait_time}s before retry"
                )
                time.sleep(wait_time)
                last_error = Exception(f"Server error: {response.status_code}")
                continue

            response.raise_for_status()

        except requests.exceptions.Timeout:
            elapsed_ms = (time.perf_counter() - start_time) * 1000
            api_metrics["total_calls"] += 1
            api_metrics["failed_calls"] += 1
            api_metrics["total_response_time"] += elapsed_ms

            wait_time = 2**attempt
            logger.warning(
                f"Request timeout on {endpoint} after {elapsed_ms:.0f}ms, waiting {wait_time}s before retry"
            )
            time.sleep(wait_time)
            last_error = Exception("Request timeout")
            continue

        except requests.exceptions.ConnectionError as e:
            elapsed_ms = (time.perf_counter() - start_time) * 1000
            api_metrics["total_calls"] += 1
            api_metrics["failed_calls"] += 1

            wait_time = 2**attempt
            logger.warning(
                f"Connection error on {endpoint} after {elapsed_ms:.0f}ms, waiting {wait_time}s before retry"
            )
            time.sleep(wait_time)
            last_error = e
            continue

    raise last_error or Exception("Max retries exceeded")
