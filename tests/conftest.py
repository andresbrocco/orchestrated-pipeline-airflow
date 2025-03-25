"""Pytest configuration and shared fixtures."""

import sys
from pathlib import Path

import pytest

# Add dags directory to path for imports
dags_path = Path(__file__).parent.parent / "dags"
sys.path.insert(0, str(dags_path))


@pytest.fixture
def sample_current_weather_response():
    """Sample OpenWeatherMap current weather API response."""
    return {
        "dt": 1709900400,
        "main": {
            "temp": 297.13,
            "feels_like": 297.63,
            "humidity": 78,
            "pressure": 1013,
        },
        "wind": {"speed": 3.5, "deg": 180},
        "weather": [{"main": "Clear", "description": "clear sky"}],
        "clouds": {"all": 10},
        "visibility": 10000,
    }


@pytest.fixture
def sample_forecast_response():
    """Sample OpenWeatherMap forecast API response."""
    return {
        "list": [
            {
                "dt": 1709910000,
                "main": {
                    "temp": 295.5,
                    "feels_like": 296.0,
                    "humidity": 80,
                    "pressure": 1015,
                },
                "wind": {"speed": 2.5, "deg": 90},
                "weather": [{"main": "Clouds", "description": "scattered clouds"}],
                "clouds": {"all": 40},
                "visibility": 8000,
                "pop": 0.2,
            },
            {
                "dt": 1709920800,
                "main": {
                    "temp": 293.15,
                    "feels_like": 293.5,
                    "humidity": 85,
                    "pressure": 1014,
                },
                "wind": {"speed": 1.8, "deg": 120},
                "weather": [{"main": "Rain", "description": "light rain"}],
                "clouds": {"all": 75},
                "visibility": 5000,
                "pop": 0.65,
            },
        ]
    }


@pytest.fixture
def sample_location():
    """Sample location data."""
    return {
        "id": 1,
        "city": "São Paulo",
        "country": "BR",
        "lat": -23.5505,
        "lon": -46.6333,
    }


@pytest.fixture
def sample_locations_config():
    """Sample locations configuration."""
    return [
        {"city": "São Paulo", "country": "BR", "lat": -23.5505, "lon": -46.6333},
        {"city": "Rio de Janeiro", "country": "BR", "lat": -22.9068, "lon": -43.1729},
    ]
