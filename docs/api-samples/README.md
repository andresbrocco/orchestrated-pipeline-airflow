# OpenWeatherMap API Sample Responses

Sample responses from the OpenWeatherMap API for reference during development.

## Files

- `current_weather_saopaulo.json` - Current weather for São Paulo, BR
- `forecast_saopaulo.json` - 5-day/3-hour forecast for São Paulo (first 8 entries)

## Current Weather Response Structure

Key fields used in our pipeline:

| Field | Path | Description | DB Column |
|-------|------|-------------|-----------|
| City name | `name` | City name | locations.city_name |
| Country | `sys.country` | Country code | locations.country_code |
| Latitude | `coord.lat` | Latitude | locations.latitude |
| Longitude | `coord.lon` | Longitude | locations.longitude |
| Observation time | `dt` | Unix timestamp | weather_observations.observation_time |
| Temperature | `main.temp` | Kelvin (convert to C) | weather_observations.temperature |
| Feels like | `main.feels_like` | Kelvin | weather_observations.feels_like |
| Humidity | `main.humidity` | Percentage | weather_observations.humidity |
| Pressure | `main.pressure` | hPa | weather_observations.pressure |
| Wind speed | `wind.speed` | m/s | weather_observations.wind_speed |
| Wind direction | `wind.deg` | Degrees | weather_observations.wind_direction |
| Weather condition | `weather[0].main` | e.g., "Clouds" | weather_observations.weather_condition |
| Weather description | `weather[0].description` | e.g., "broken clouds" | weather_observations.weather_description |
| Cloudiness | `clouds.all` | Percentage | weather_observations.cloudiness |
| Visibility | `visibility` | Meters | weather_observations.visibility |

## Forecast Response Structure

The forecast endpoint returns data in a `list[]` array. Key fields used:

| Field | Path | Description | DB Column |
|-------|------|-------------|-----------|
| Predicted time | `list[].dt` | Unix timestamp | weather_forecasts.predicted_for |
| Temperature | `list[].main.temp` | Kelvin | weather_forecasts.temperature |
| Feels like | `list[].main.feels_like` | Kelvin | weather_forecasts.feels_like |
| Humidity | `list[].main.humidity` | Percentage | weather_forecasts.humidity |
| Pressure | `list[].main.pressure` | hPa | weather_forecasts.pressure |
| Wind speed | `list[].wind.speed` | m/s | weather_forecasts.wind_speed |
| Wind direction | `list[].wind.deg` | Degrees | weather_forecasts.wind_direction |
| Weather condition | `list[].weather[0].main` | e.g., "Clear" | weather_forecasts.weather_condition |
| Weather description | `list[].weather[0].description` | e.g., "clear sky" | weather_forecasts.weather_description |
| Cloudiness | `list[].clouds.all` | Percentage | weather_forecasts.cloudiness |
| Visibility | `list[].visibility` | Meters | weather_forecasts.visibility |
| Precipitation prob | `list[].pop` | 0-1 (convert to %) | weather_forecasts.precipitation_probability |

Note: `forecast_time` should be set to the current timestamp when fetching the forecast.

## Temperature Conversion

API returns Kelvin. Convert to Celsius:
```python
celsius = kelvin - 273.15
```

## API Endpoints Used

- **Current Weather**: `https://api.openweathermap.org/data/2.5/weather?q={city},{country}&appid={key}`
- **5-Day Forecast**: `https://api.openweathermap.org/data/2.5/forecast?q={city},{country}&appid={key}`
