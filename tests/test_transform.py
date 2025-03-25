"""Unit tests for data transformation functions."""

from datetime import datetime, timezone

from tasks.transform import (
    kelvin_to_celsius,
    transform_current_weather,
    transform_forecast,
    transform_weather_data,
)


class TestKelvinToCelsius:
    """Tests for kelvin_to_celsius function."""

    def test_standard_conversion(self):
        """Test standard temperature conversion."""
        # 273.15 K = 0°C
        assert kelvin_to_celsius(273.15) == 0.0

    def test_room_temperature(self):
        """Test room temperature conversion."""
        # 297.15 K = 24°C
        assert kelvin_to_celsius(297.15) == 24.0

    def test_freezing_point(self):
        """Test freezing point of water."""
        # 273.15 K = 0°C
        result = kelvin_to_celsius(273.15)
        assert result == 0.0

    def test_boiling_point(self):
        """Test boiling point of water."""
        # 373.15 K = 100°C
        result = kelvin_to_celsius(373.15)
        assert result == 100.0

    def test_decimal_precision(self):
        """Test that result is rounded to 2 decimal places."""
        result = kelvin_to_celsius(297.13)
        assert result == 23.98

    def test_none_input(self):
        """Test that None input returns None."""
        assert kelvin_to_celsius(None) is None

    def test_negative_celsius(self):
        """Test conversion resulting in negative Celsius."""
        # 263.15 K = -10°C
        result = kelvin_to_celsius(263.15)
        assert result == -10.0


class TestTransformCurrentWeather:
    """Tests for transform_current_weather function."""

    def test_basic_transformation(self, sample_current_weather_response):
        """Test basic transformation of current weather data."""
        result = transform_current_weather(sample_current_weather_response)

        assert result["temperature"] == 23.98
        assert result["feels_like"] == 24.48
        assert result["humidity"] == 78
        assert result["pressure"] == 1013
        assert result["wind_speed"] == 3.5
        assert result["wind_direction"] == 180
        assert result["weather_condition"] == "Clear"
        assert result["weather_description"] == "clear sky"
        assert result["cloudiness"] == 10
        assert result["visibility"] == 10000

    def test_observation_time_is_utc(self, sample_current_weather_response):
        """Test that observation time is converted to UTC datetime."""
        result = transform_current_weather(sample_current_weather_response)

        assert isinstance(result["observation_time"], datetime)
        assert result["observation_time"].tzinfo == timezone.utc

    def test_missing_optional_fields(self):
        """Test handling of missing optional fields."""
        minimal_response = {"dt": 1709900400, "main": {}, "weather": [{}]}

        result = transform_current_weather(minimal_response)

        assert result["temperature"] is None
        assert result["humidity"] is None
        assert result["wind_speed"] is None
        assert result["weather_condition"] is None

    def test_empty_weather_list(self):
        """Test handling of empty weather list."""
        response = {"dt": 1709900400, "main": {"temp": 300}, "weather": []}

        result = transform_current_weather(response)

        assert result["temperature"] == 26.85
        assert result["weather_condition"] is None


class TestTransformForecast:
    """Tests for transform_forecast function."""

    def test_multiple_forecasts(self, sample_forecast_response):
        """Test transformation of multiple forecast entries."""
        result = transform_forecast(sample_forecast_response)

        assert len(result) == 2

    def test_forecast_temperatures(self, sample_forecast_response):
        """Test temperature conversions in forecasts."""
        result = transform_forecast(sample_forecast_response)

        assert result[0]["temperature"] == 22.35
        assert result[1]["temperature"] == 20.0

    def test_precipitation_probability_conversion(self, sample_forecast_response):
        """Test conversion of precipitation probability from 0-1 to 0-100."""
        result = transform_forecast(sample_forecast_response)

        # 0.2 -> 20%
        assert result[0]["precipitation_probability"] == 20
        # 0.65 -> 65%
        assert result[1]["precipitation_probability"] == 65

    def test_forecast_time_is_utc(self, sample_forecast_response):
        """Test that forecast times are UTC datetimes."""
        result = transform_forecast(sample_forecast_response)

        for forecast in result:
            assert isinstance(forecast["forecast_time"], datetime)
            assert forecast["forecast_time"].tzinfo == timezone.utc
            assert isinstance(forecast["predicted_for"], datetime)
            assert forecast["predicted_for"].tzinfo == timezone.utc

    def test_empty_forecast_list(self):
        """Test handling of empty forecast list."""
        response = {"list": []}

        result = transform_forecast(response)

        assert result == []

    def test_missing_pop_field(self):
        """Test handling of missing precipitation probability."""
        response = {
            "list": [
                {
                    "dt": 1709910000,
                    "main": {"temp": 295.5},
                    "weather": [{"main": "Clear"}],
                }
            ]
        }

        result = transform_forecast(response)

        assert result[0]["precipitation_probability"] is None


class TestTransformWeatherData:
    """Tests for transform_weather_data function."""

    def test_complete_transformation(
        self, sample_current_weather_response, sample_forecast_response, sample_location
    ):
        """Test complete weather data transformation."""
        raw_data = {
            "location": sample_location,
            "current": sample_current_weather_response,
            "forecast": sample_forecast_response,
        }

        result = transform_weather_data(raw_data)

        assert result["location"] == sample_location
        assert result["current"] is not None
        assert result["current"]["temperature"] == 23.98
        assert len(result["forecasts"]) == 2

    def test_current_only(self, sample_current_weather_response, sample_location):
        """Test transformation with only current weather."""
        raw_data = {
            "location": sample_location,
            "current": sample_current_weather_response,
            "forecast": None,
        }

        result = transform_weather_data(raw_data)

        assert result["current"] is not None
        assert result["forecasts"] == []

    def test_forecast_only(self, sample_forecast_response, sample_location):
        """Test transformation with only forecast data."""
        raw_data = {
            "location": sample_location,
            "current": None,
            "forecast": sample_forecast_response,
        }

        result = transform_weather_data(raw_data)

        assert result["current"] is None
        assert len(result["forecasts"]) == 2

    def test_no_weather_data(self, sample_location):
        """Test transformation with no weather data."""
        raw_data = {"location": sample_location, "current": None, "forecast": None}

        result = transform_weather_data(raw_data)

        assert result["location"] == sample_location
        assert result["current"] is None
        assert result["forecasts"] == []
