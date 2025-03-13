"""Data transformation module for weather API responses."""

from datetime import datetime, timezone


def kelvin_to_celsius(kelvin):
    """Convert Kelvin to Celsius."""
    if kelvin is None:
        return None
    return round(kelvin - 273.15, 2)


def transform_current_weather(api_response):
    """Transform current weather API response into database format."""
    main = api_response.get('main', {})
    wind = api_response.get('wind', {})
    weather = api_response.get('weather', [{}])[0]
    clouds = api_response.get('clouds', {})

    return {
        'observation_time': datetime.fromtimestamp(
            api_response['dt'], tz=timezone.utc
        ),
        'temperature': kelvin_to_celsius(main.get('temp')),
        'feels_like': kelvin_to_celsius(main.get('feels_like')),
        'humidity': main.get('humidity'),
        'pressure': main.get('pressure'),
        'wind_speed': wind.get('speed'),
        'wind_direction': wind.get('deg'),
        'weather_condition': weather.get('main'),
        'weather_description': weather.get('description'),
        'cloudiness': clouds.get('all'),
        'visibility': api_response.get('visibility')
    }


def transform_forecast(api_response):
    """Transform forecast API response into list of database records."""
    forecast_time = datetime.now(timezone.utc)
    forecasts = []

    for item in api_response.get('list', []):
        main = item.get('main', {})
        wind = item.get('wind', {})
        weather = item.get('weather', [{}])[0]
        clouds = item.get('clouds', {})

        # Convert precipitation probability from 0-1 to 0-100
        pop = item.get('pop')
        precip_prob = round(pop * 100) if pop is not None else None

        forecast = {
            'forecast_time': forecast_time,
            'predicted_for': datetime.fromtimestamp(
                item['dt'], tz=timezone.utc
            ),
            'temperature': kelvin_to_celsius(main.get('temp')),
            'feels_like': kelvin_to_celsius(main.get('feels_like')),
            'humidity': main.get('humidity'),
            'pressure': main.get('pressure'),
            'wind_speed': wind.get('speed'),
            'wind_direction': wind.get('deg'),
            'weather_condition': weather.get('main'),
            'weather_description': weather.get('description'),
            'cloudiness': clouds.get('all'),
            'visibility': item.get('visibility'),
            'precipitation_probability': precip_prob
        }
        forecasts.append(forecast)

    return forecasts


def transform_weather_data(raw_data):
    """Transform complete weather data for a location."""
    result = {
        'location': raw_data['location'],
        'current': None,
        'forecasts': []
    }

    if raw_data.get('current'):
        result['current'] = transform_current_weather(raw_data['current'])

    if raw_data.get('forecast'):
        result['forecasts'] = transform_forecast(raw_data['forecast'])

    return result
