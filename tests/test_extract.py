"""Unit tests for API extraction functions."""

import json
from unittest.mock import patch, MagicMock

import pytest
import requests

from tasks.extract import (
    get_api_key,
    fetch_current_weather,
    fetch_forecast,
    fetch_weather_for_location,
    _make_request,
)


class TestGetApiKey:
    """Tests for get_api_key function."""

    @patch("tasks.extract.BaseHook.get_connection")
    def test_get_api_key_from_connection(self, mock_get_connection):
        """Test retrieving API key from Airflow connection."""
        mock_conn = MagicMock()
        mock_conn.extra = json.dumps({"api_key": "test_api_key_123"})
        mock_get_connection.return_value = mock_conn

        result = get_api_key()

        assert result == "test_api_key_123"
        mock_get_connection.assert_called_once_with("openweathermap_api")

    @patch("tasks.extract.BaseHook.get_connection")
    def test_get_api_key_empty_extra(self, mock_get_connection):
        """Test handling of empty extra field."""
        mock_conn = MagicMock()
        mock_conn.extra = ""
        mock_get_connection.return_value = mock_conn

        result = get_api_key()

        assert result is None

    @patch("tasks.extract.BaseHook.get_connection")
    def test_get_api_key_no_api_key_field(self, mock_get_connection):
        """Test handling of missing api_key in extra."""
        mock_conn = MagicMock()
        mock_conn.extra = json.dumps({"other_field": "value"})
        mock_get_connection.return_value = mock_conn

        result = get_api_key()

        assert result is None


class TestMakeRequest:
    """Tests for _make_request function."""

    @patch("tasks.extract.requests.get")
    def test_successful_request(self, mock_get):
        """Test successful API request."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"data": "test"}
        mock_get.return_value = mock_response

        result = _make_request("http://test.com", {"param": "value"})

        assert result == {"data": "test"}
        mock_get.assert_called_once()

    @patch("tasks.extract.requests.get")
    def test_invalid_api_key_error(self, mock_get):
        """Test handling of 401 unauthorized error."""
        mock_response = MagicMock()
        mock_response.status_code = 401
        mock_get.return_value = mock_response

        with pytest.raises(ValueError, match="Invalid API key"):
            _make_request("http://test.com", {}, retries=1)

    @patch("tasks.extract.requests.get")
    def test_location_not_found_error(self, mock_get):
        """Test handling of 404 not found error."""
        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_get.return_value = mock_response

        with pytest.raises(ValueError, match="Location not found"):
            _make_request("http://test.com", {}, retries=1)

    @patch("tasks.extract.time.sleep")
    @patch("tasks.extract.requests.get")
    def test_rate_limit_retry(self, mock_get, mock_sleep):
        """Test retry on rate limit (429) error."""
        mock_response_429 = MagicMock()
        mock_response_429.status_code = 429

        mock_response_200 = MagicMock()
        mock_response_200.status_code = 200
        mock_response_200.json.return_value = {"data": "success"}

        mock_get.side_effect = [mock_response_429, mock_response_200]

        result = _make_request("http://test.com", {}, retries=2)

        assert result == {"data": "success"}
        assert mock_get.call_count == 2
        mock_sleep.assert_called_once()

    @patch("tasks.extract.time.sleep")
    @patch("tasks.extract.requests.get")
    def test_server_error_retry(self, mock_get, mock_sleep):
        """Test retry on server error (5xx)."""
        mock_response_500 = MagicMock()
        mock_response_500.status_code = 500

        mock_response_200 = MagicMock()
        mock_response_200.status_code = 200
        mock_response_200.json.return_value = {"data": "success"}

        mock_get.side_effect = [mock_response_500, mock_response_200]

        result = _make_request("http://test.com", {}, retries=2)

        assert result == {"data": "success"}

    @patch("tasks.extract.time.sleep")
    @patch("tasks.extract.requests.get")
    def test_timeout_retry(self, mock_get, mock_sleep):
        """Test retry on timeout."""
        mock_response_200 = MagicMock()
        mock_response_200.status_code = 200
        mock_response_200.json.return_value = {"data": "success"}

        mock_get.side_effect = [requests.exceptions.Timeout(), mock_response_200]

        result = _make_request("http://test.com", {}, retries=2)

        assert result == {"data": "success"}

    @patch("tasks.extract.time.sleep")
    @patch("tasks.extract.requests.get")
    def test_connection_error_retry(self, mock_get, mock_sleep):
        """Test retry on connection error."""
        mock_response_200 = MagicMock()
        mock_response_200.status_code = 200
        mock_response_200.json.return_value = {"data": "success"}

        mock_get.side_effect = [
            requests.exceptions.ConnectionError(),
            mock_response_200,
        ]

        result = _make_request("http://test.com", {}, retries=2)

        assert result == {"data": "success"}

    @patch("tasks.extract.time.sleep")
    @patch("tasks.extract.requests.get")
    def test_max_retries_exceeded(self, mock_get, mock_sleep):
        """Test exception raised when max retries exceeded."""
        mock_response = MagicMock()
        mock_response.status_code = 500

        mock_get.return_value = mock_response

        with pytest.raises(Exception, match="Server error: 500"):
            _make_request("http://test.com", {}, retries=2)

        assert mock_get.call_count == 2


class TestFetchCurrentWeather:
    """Tests for fetch_current_weather function."""

    @patch("tasks.extract._make_request")
    @patch("tasks.extract.get_api_key")
    def test_fetch_current_weather(self, mock_get_api_key, mock_make_request):
        """Test fetching current weather data."""
        mock_get_api_key.return_value = "test_key"
        mock_make_request.return_value = {"weather": "data"}

        result = fetch_current_weather(-23.5505, -46.6333)

        assert result == {"weather": "data"}
        mock_make_request.assert_called_once()
        call_args = mock_make_request.call_args
        assert call_args[0][0] == "https://api.openweathermap.org/data/2.5/weather"
        assert call_args[0][1]["lat"] == -23.5505
        assert call_args[0][1]["lon"] == -46.6333
        assert call_args[0][1]["appid"] == "test_key"

    @patch("tasks.extract.get_api_key")
    def test_fetch_current_weather_no_api_key(self, mock_get_api_key):
        """Test error when API key not configured."""
        mock_get_api_key.return_value = None

        with pytest.raises(ValueError, match="API key not configured"):
            fetch_current_weather(-23.5505, -46.6333)


class TestFetchForecast:
    """Tests for fetch_forecast function."""

    @patch("tasks.extract._make_request")
    @patch("tasks.extract.get_api_key")
    def test_fetch_forecast(self, mock_get_api_key, mock_make_request):
        """Test fetching forecast data."""
        mock_get_api_key.return_value = "test_key"
        mock_make_request.return_value = {"list": []}

        result = fetch_forecast(-23.5505, -46.6333)

        assert result == {"list": []}
        call_args = mock_make_request.call_args
        assert call_args[0][0] == "https://api.openweathermap.org/data/2.5/forecast"

    @patch("tasks.extract.get_api_key")
    def test_fetch_forecast_no_api_key(self, mock_get_api_key):
        """Test error when API key not configured."""
        mock_get_api_key.return_value = None

        with pytest.raises(ValueError, match="API key not configured"):
            fetch_forecast(-23.5505, -46.6333)


class TestFetchWeatherForLocation:
    """Tests for fetch_weather_for_location function."""

    @patch("tasks.extract.fetch_forecast")
    @patch("tasks.extract.fetch_current_weather")
    def test_fetch_with_forecast(self, mock_current, mock_forecast):
        """Test fetching both current and forecast data."""
        mock_current.return_value = {"current": "data"}
        mock_forecast.return_value = {"forecast": "data"}

        location = {"city": "São Paulo", "lat": -23.5505, "lon": -46.6333}
        result = fetch_weather_for_location(location)

        assert result["location"] == location
        assert result["current"] == {"current": "data"}
        assert result["forecast"] == {"forecast": "data"}

    @patch("tasks.extract.fetch_current_weather")
    def test_fetch_without_forecast(self, mock_current):
        """Test fetching only current weather data."""
        mock_current.return_value = {"current": "data"}

        location = {"city": "São Paulo", "lat": -23.5505, "lon": -46.6333}
        result = fetch_weather_for_location(location, include_forecast=False)

        assert result["current"] == {"current": "data"}
        assert result["forecast"] is None

    @patch("tasks.extract.fetch_forecast")
    @patch("tasks.extract.fetch_current_weather")
    def test_fetch_with_unknown_city(self, mock_current, mock_forecast):
        """Test fetching with location without city name."""
        mock_current.return_value = {"current": "data"}
        mock_forecast.return_value = {"forecast": "data"}

        location = {"lat": -23.5505, "lon": -46.6333}
        result = fetch_weather_for_location(location)

        assert result["location"] == location
