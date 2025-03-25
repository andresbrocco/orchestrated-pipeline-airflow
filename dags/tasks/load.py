"""Database loading module for weather data."""

import logging

from airflow.providers.postgres.hooks.postgres import PostgresHook

logger = logging.getLogger(__name__)

POSTGRES_CONN_ID = "weather_postgres"


def load_observation(location_id, observation_data):
    """Insert or update a weather observation."""
    hook = PostgresHook(postgres_conn_id=POSTGRES_CONN_ID)

    sql = """
        INSERT INTO weather_observations (
            location_id, observation_time, temperature, feels_like,
            humidity, pressure, wind_speed, wind_direction,
            weather_condition, weather_description, cloudiness, visibility
        ) VALUES (
            %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
        )
        ON CONFLICT (location_id, observation_time)
        DO UPDATE SET
            temperature = EXCLUDED.temperature,
            feels_like = EXCLUDED.feels_like,
            humidity = EXCLUDED.humidity,
            pressure = EXCLUDED.pressure,
            wind_speed = EXCLUDED.wind_speed,
            wind_direction = EXCLUDED.wind_direction,
            weather_condition = EXCLUDED.weather_condition,
            weather_description = EXCLUDED.weather_description,
            cloudiness = EXCLUDED.cloudiness,
            visibility = EXCLUDED.visibility
    """

    params = (
        location_id,
        observation_data["observation_time"],
        observation_data.get("temperature"),
        observation_data.get("feels_like"),
        observation_data.get("humidity"),
        observation_data.get("pressure"),
        observation_data.get("wind_speed"),
        observation_data.get("wind_direction"),
        observation_data.get("weather_condition"),
        observation_data.get("weather_description"),
        observation_data.get("cloudiness"),
        observation_data.get("visibility"),
    )

    hook.run(sql, parameters=params)
    logger.info(f"Loaded observation for location {location_id}")


def load_forecasts(location_id, forecasts):
    """Insert or update multiple forecast records."""
    if not forecasts:
        return 0

    hook = PostgresHook(postgres_conn_id=POSTGRES_CONN_ID)

    sql = """
        INSERT INTO weather_forecasts (
            location_id, forecast_time, predicted_for, temperature, feels_like,
            humidity, pressure, wind_speed, wind_direction,
            weather_condition, weather_description, cloudiness, visibility,
            precipitation_probability
        ) VALUES (
            %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
        )
        ON CONFLICT (location_id, forecast_time, predicted_for)
        DO UPDATE SET
            temperature = EXCLUDED.temperature,
            feels_like = EXCLUDED.feels_like,
            humidity = EXCLUDED.humidity,
            pressure = EXCLUDED.pressure,
            wind_speed = EXCLUDED.wind_speed,
            wind_direction = EXCLUDED.wind_direction,
            weather_condition = EXCLUDED.weather_condition,
            weather_description = EXCLUDED.weather_description,
            cloudiness = EXCLUDED.cloudiness,
            visibility = EXCLUDED.visibility,
            precipitation_probability = EXCLUDED.precipitation_probability
    """

    rows = []
    for forecast in forecasts:
        row = (
            location_id,
            forecast["forecast_time"],
            forecast["predicted_for"],
            forecast.get("temperature"),
            forecast.get("feels_like"),
            forecast.get("humidity"),
            forecast.get("pressure"),
            forecast.get("wind_speed"),
            forecast.get("wind_direction"),
            forecast.get("weather_condition"),
            forecast.get("weather_description"),
            forecast.get("cloudiness"),
            forecast.get("visibility"),
            forecast.get("precipitation_probability"),
        )
        rows.append(row)

    conn = hook.get_conn()
    cursor = conn.cursor()

    try:
        for row in rows:
            cursor.execute(sql, row)
        conn.commit()
        logger.info(f"Loaded {len(rows)} forecasts for location {location_id}")
        return len(rows)
    except Exception as e:
        conn.rollback()
        logger.error(f"Failed to load forecasts: {e}")
        raise
    finally:
        cursor.close()


def load_weather_data(transformed_data):
    """Load complete transformed weather data for a location."""
    location = transformed_data["location"]
    location_id = location["id"]

    loaded = {"observations": 0, "forecasts": 0}

    if transformed_data.get("current"):
        load_observation(location_id, transformed_data["current"])
        loaded["observations"] = 1

    if transformed_data.get("forecasts"):
        loaded["forecasts"] = load_forecasts(location_id, transformed_data["forecasts"])

    logger.info(
        f"Loaded data for {location.get('city', 'Unknown')}: "
        f"{loaded['observations']} observations, {loaded['forecasts']} forecasts"
    )

    return loaded
