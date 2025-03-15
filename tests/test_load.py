"""Unit tests for database loading functions."""

from datetime import datetime, timezone
from unittest.mock import patch, MagicMock

import pytest

from tasks.load import load_observation, load_forecasts, load_weather_data


class TestLoadObservation:
    """Tests for load_observation function."""

    @patch("tasks.load.PostgresHook")
    def test_load_observation_insert(self, mock_hook_class):
        """Test inserting a weather observation."""
        mock_hook = MagicMock()
        mock_hook_class.return_value = mock_hook

        observation_data = {
            "observation_time": datetime(2025, 3, 8, 12, 0, tzinfo=timezone.utc),
            "temperature": 23.5,
            "feels_like": 24.0,
            "humidity": 75,
            "pressure": 1013,
            "wind_speed": 3.5,
            "wind_direction": 180,
            "weather_condition": "Clear",
            "weather_description": "clear sky",
            "cloudiness": 10,
            "visibility": 10000,
        }

        load_observation(1, observation_data)

        mock_hook_class.assert_called_once_with(postgres_conn_id="weather_postgres")
        mock_hook.run.assert_called_once()

        # Verify SQL contains INSERT and ON CONFLICT
        sql_call = mock_hook.run.call_args[0][0]
        assert "INSERT INTO weather_observations" in sql_call
        assert "ON CONFLICT" in sql_call
        assert "DO UPDATE SET" in sql_call

        # Verify parameters
        params = mock_hook.run.call_args[1]["parameters"]
        assert params[0] == 1  # location_id
        assert params[1] == observation_data["observation_time"]
        assert params[2] == 23.5  # temperature

    @patch("tasks.load.PostgresHook")
    def test_load_observation_with_nulls(self, mock_hook_class):
        """Test loading observation with missing fields."""
        mock_hook = MagicMock()
        mock_hook_class.return_value = mock_hook

        observation_data = {
            "observation_time": datetime(2025, 3, 8, 12, 0, tzinfo=timezone.utc),
            "temperature": 20.0,
        }

        load_observation(1, observation_data)

        params = mock_hook.run.call_args[1]["parameters"]
        assert params[0] == 1
        assert params[2] == 20.0
        assert params[3] is None  # feels_like
        assert params[4] is None  # humidity


class TestLoadForecasts:
    """Tests for load_forecasts function."""

    @patch("tasks.load.PostgresHook")
    def test_load_multiple_forecasts(self, mock_hook_class):
        """Test batch loading multiple forecasts."""
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor

        mock_hook = MagicMock()
        mock_hook.get_conn.return_value = mock_conn
        mock_hook_class.return_value = mock_hook

        forecasts = [
            {
                "forecast_time": datetime(2025, 3, 8, 12, 0, tzinfo=timezone.utc),
                "predicted_for": datetime(2025, 3, 8, 15, 0, tzinfo=timezone.utc),
                "temperature": 22.0,
                "humidity": 70,
                "precipitation_probability": 20,
            },
            {
                "forecast_time": datetime(2025, 3, 8, 12, 0, tzinfo=timezone.utc),
                "predicted_for": datetime(2025, 3, 8, 18, 0, tzinfo=timezone.utc),
                "temperature": 20.0,
                "humidity": 75,
                "precipitation_probability": 30,
            },
        ]

        result = load_forecasts(1, forecasts)

        assert result == 2
        assert mock_cursor.execute.call_count == 2
        mock_conn.commit.assert_called_once()
        mock_cursor.close.assert_called_once()

    @patch("tasks.load.PostgresHook")
    def test_load_forecasts_sql_structure(self, mock_hook_class):
        """Test that forecast SQL has correct structure."""
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor

        mock_hook = MagicMock()
        mock_hook.get_conn.return_value = mock_conn
        mock_hook_class.return_value = mock_hook

        forecasts = [
            {
                "forecast_time": datetime(2025, 3, 8, 12, 0, tzinfo=timezone.utc),
                "predicted_for": datetime(2025, 3, 8, 15, 0, tzinfo=timezone.utc),
                "temperature": 22.0,
            }
        ]

        load_forecasts(1, forecasts)

        sql = mock_cursor.execute.call_args[0][0]
        assert "INSERT INTO weather_forecasts" in sql
        assert "ON CONFLICT" in sql
        assert "precipitation_probability" in sql

    @patch("tasks.load.PostgresHook")
    def test_load_empty_forecasts(self, mock_hook_class):
        """Test loading empty forecast list."""
        mock_hook = MagicMock()
        mock_hook_class.return_value = mock_hook

        result = load_forecasts(1, [])

        assert result == 0
        mock_hook.get_conn.assert_not_called()

    @patch("tasks.load.PostgresHook")
    def test_load_forecasts_rollback_on_error(self, mock_hook_class):
        """Test transaction rollback on error."""
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_cursor.execute.side_effect = Exception("Database error")
        mock_conn.cursor.return_value = mock_cursor

        mock_hook = MagicMock()
        mock_hook.get_conn.return_value = mock_conn
        mock_hook_class.return_value = mock_hook

        forecasts = [
            {
                "forecast_time": datetime(2025, 3, 8, 12, 0, tzinfo=timezone.utc),
                "predicted_for": datetime(2025, 3, 8, 15, 0, tzinfo=timezone.utc),
                "temperature": 22.0,
            }
        ]

        with pytest.raises(Exception, match="Database error"):
            load_forecasts(1, forecasts)

        mock_conn.rollback.assert_called_once()
        mock_cursor.close.assert_called_once()


class TestLoadWeatherData:
    """Tests for load_weather_data function."""

    @patch("tasks.load.load_forecasts")
    @patch("tasks.load.load_observation")
    def test_load_complete_data(self, mock_load_obs, mock_load_forecasts):
        """Test loading both observation and forecasts."""
        mock_load_forecasts.return_value = 3

        transformed_data = {
            "location": {
                "id": 1,
                "city": "São Paulo",
                "lat": -23.5505,
                "lon": -46.6333,
            },
            "current": {
                "observation_time": datetime(2025, 3, 8, 12, 0, tzinfo=timezone.utc),
                "temperature": 23.5,
            },
            "forecasts": [
                {"forecast_time": datetime(2025, 3, 8, 12, 0, tzinfo=timezone.utc)},
                {"forecast_time": datetime(2025, 3, 8, 12, 0, tzinfo=timezone.utc)},
                {"forecast_time": datetime(2025, 3, 8, 12, 0, tzinfo=timezone.utc)},
            ],
        }

        result = load_weather_data(transformed_data)

        mock_load_obs.assert_called_once_with(1, transformed_data["current"])
        mock_load_forecasts.assert_called_once_with(1, transformed_data["forecasts"])
        assert result == {"observations": 1, "forecasts": 3}

    @patch("tasks.load.load_forecasts")
    @patch("tasks.load.load_observation")
    def test_load_observation_only(self, mock_load_obs, mock_load_forecasts):
        """Test loading only observation without forecasts."""
        transformed_data = {
            "location": {"id": 1, "city": "São Paulo"},
            "current": {
                "observation_time": datetime(2025, 3, 8, 12, 0, tzinfo=timezone.utc),
                "temperature": 23.5,
            },
            "forecasts": None,
        }

        result = load_weather_data(transformed_data)

        mock_load_obs.assert_called_once()
        mock_load_forecasts.assert_not_called()
        assert result == {"observations": 1, "forecasts": 0}

    @patch("tasks.load.load_forecasts")
    @patch("tasks.load.load_observation")
    def test_load_forecasts_only(self, mock_load_obs, mock_load_forecasts):
        """Test loading only forecasts without observation."""
        mock_load_forecasts.return_value = 2

        transformed_data = {
            "location": {"id": 1, "city": "São Paulo"},
            "current": None,
            "forecasts": [
                {"forecast_time": datetime(2025, 3, 8, 12, 0, tzinfo=timezone.utc)},
                {"forecast_time": datetime(2025, 3, 8, 12, 0, tzinfo=timezone.utc)},
            ],
        }

        result = load_weather_data(transformed_data)

        mock_load_obs.assert_not_called()
        mock_load_forecasts.assert_called_once()
        assert result == {"observations": 0, "forecasts": 2}

    @patch("tasks.load.load_forecasts")
    @patch("tasks.load.load_observation")
    def test_load_no_data(self, mock_load_obs, mock_load_forecasts):
        """Test loading with no weather data."""
        transformed_data = {
            "location": {"id": 1, "city": "São Paulo"},
            "current": None,
            "forecasts": None,
        }

        result = load_weather_data(transformed_data)

        mock_load_obs.assert_not_called()
        mock_load_forecasts.assert_not_called()
        assert result == {"observations": 0, "forecasts": 0}
