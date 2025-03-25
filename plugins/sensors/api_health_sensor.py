"""Custom sensor for checking OpenWeatherMap API health."""

import json
import logging
import requests

from airflow.sdk.bases.sensor import BaseSensorOperator
from airflow.sdk.bases.hook import BaseHook

logger = logging.getLogger(__name__)

BASE_URL = "https://api.openweathermap.org/data/2.5"
CONN_ID = "openweathermap_api"


class OpenWeatherMapHealthSensor(BaseSensorOperator):
    """Sensor to check if OpenWeatherMap API is accessible."""

    template_fields = ("connection_id",)

    def __init__(
        self, connection_id=CONN_ID, test_lat=51.5074, test_lon=-0.1278, **kwargs
    ):
        super().__init__(**kwargs)
        self.connection_id = connection_id
        self.test_lat = test_lat
        self.test_lon = test_lon

    def poke(self, context):
        """Check API health by making a lightweight API call."""
        try:
            conn = BaseHook.get_connection(self.connection_id)
            extra = json.loads(conn.extra) if conn.extra else {}
            api_key = extra.get("api_key")

            if not api_key:
                logger.error("API key not found in connection")
                return False

            url = f"{BASE_URL}/weather"
            params = {"lat": self.test_lat, "lon": self.test_lon, "appid": api_key}

            logger.info(f"Checking API health at {url}")
            response = requests.get(url, params=params, timeout=10)

            if response.status_code == 200:
                logger.info("API health check passed")
                return True

            logger.warning(
                f"API health check failed with status {response.status_code}"
            )
            return False

        except requests.exceptions.Timeout:
            logger.warning("API health check timed out")
            return False

        except requests.exceptions.ConnectionError:
            logger.warning("API health check connection error")
            return False

        except Exception as e:
            logger.warning(f"API health check failed: {str(e)}")
            return False
