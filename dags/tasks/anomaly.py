"""Anomaly detection module for weather data."""

import logging
from datetime import datetime, timedelta

from airflow.providers.postgres.hooks.postgres import PostgresHook

logger = logging.getLogger(__name__)

POSTGRES_CONN_ID = 'weather_postgres'
TEMP_CHANGE_THRESHOLD = 10.0
STALE_DATA_HOURS = 2


def detect_temperature_anomalies():
    """Detect unusual temperature changes between observations."""
    hook = PostgresHook(postgres_conn_id=POSTGRES_CONN_ID)

    sql = """
        WITH ranked_observations AS (
            SELECT
                location_id,
                observation_time,
                temperature,
                LAG(temperature) OVER (PARTITION BY location_id ORDER BY observation_time) as prev_temperature,
                LAG(observation_time) OVER (PARTITION BY location_id ORDER BY observation_time) as prev_time
            FROM weather_observations
            WHERE observation_time >= NOW() - INTERVAL '24 hours'
        )
        SELECT
            l.city_name,
            l.country_code,
            ro.observation_time,
            ro.temperature,
            ro.prev_temperature,
            ABS(ro.temperature - ro.prev_temperature) as temp_change
        FROM ranked_observations ro
        JOIN locations l ON ro.location_id = l.id
        WHERE ro.prev_temperature IS NOT NULL
            AND ABS(ro.temperature - ro.prev_temperature) > %s
        ORDER BY temp_change DESC
    """

    results = hook.get_records(sql, parameters=(TEMP_CHANGE_THRESHOLD,))

    anomalies = []
    for row in results:
        city, country, obs_time, temp, prev_temp, change = row
        anomaly = {
            'type': 'temperature_spike',
            'location': f'{city}, {country}',
            'observation_time': obs_time,
            'current_temp': float(temp),
            'previous_temp': float(prev_temp),
            'change': float(change)
        }
        anomalies.append(anomaly)
        logger.warning(
            f"Temperature anomaly detected in {city}, {country}: "
            f"{prev_temp}°C → {temp}°C (change: {change:.1f}°C)"
        )

    return anomalies


def detect_missing_locations():
    """Identify locations that haven't reported data recently."""
    hook = PostgresHook(postgres_conn_id=POSTGRES_CONN_ID)

    cutoff_time = datetime.now() - timedelta(hours=STALE_DATA_HOURS)

    sql = """
        SELECT
            l.id,
            l.city_name,
            l.country_code,
            MAX(wo.observation_time) as last_observation
        FROM locations l
        LEFT JOIN weather_observations wo ON l.id = wo.location_id
        GROUP BY l.id, l.city_name, l.country_code
        HAVING MAX(wo.observation_time) IS NULL
            OR MAX(wo.observation_time) < %s
        ORDER BY last_observation NULLS FIRST
    """

    results = hook.get_records(sql, parameters=(cutoff_time,))

    anomalies = []
    for row in results:
        location_id, city, country, last_obs = row
        anomaly = {
            'type': 'missing_data',
            'location': f'{city}, {country}',
            'location_id': location_id,
            'last_observation': last_obs
        }
        anomalies.append(anomaly)

        if last_obs is None:
            logger.warning(f"No observations found for {city}, {country}")
        else:
            hours_old = (datetime.now() - last_obs).total_seconds() / 3600
            logger.warning(
                f"Stale data for {city}, {country}: "
                f"last observation {hours_old:.1f} hours ago"
            )

    return anomalies


def detect_outliers():
    """Detect values outside normal ranges."""
    hook = PostgresHook(postgres_conn_id=POSTGRES_CONN_ID)

    sql = """
        SELECT
            l.city_name,
            l.country_code,
            wo.observation_time,
            wo.temperature,
            wo.humidity,
            wo.wind_speed
        FROM weather_observations wo
        JOIN locations l ON wo.location_id = l.id
        WHERE wo.observation_time >= NOW() - INTERVAL '6 hours'
            AND (
                wo.temperature < -50 OR wo.temperature > 60
                OR wo.humidity < 0 OR wo.humidity > 100
                OR wo.wind_speed < 0 OR wo.wind_speed > 150
            )
    """

    results = hook.get_records(sql)

    anomalies = []
    for row in results:
        city, country, obs_time, temp, humidity, wind_speed = row
        issues = []

        if temp is not None and (temp < -50 or temp > 60):
            issues.append(f'temperature {temp}°C out of range')
        if humidity is not None and (humidity < 0 or humidity > 100):
            issues.append(f'humidity {humidity}% out of range')
        if wind_speed is not None and (wind_speed < 0 or wind_speed > 150):
            issues.append(f'wind speed {wind_speed} m/s out of range')

        if issues:
            anomaly = {
                'type': 'outlier',
                'location': f'{city}, {country}',
                'observation_time': obs_time,
                'issues': issues
            }
            anomalies.append(anomaly)
            logger.warning(
                f"Outlier detected in {city}, {country}: {', '.join(issues)}"
            )

    return anomalies


def store_anomaly(anomaly_data):
    """Store a detected anomaly in the database."""
    hook = PostgresHook(postgres_conn_id=POSTGRES_CONN_ID)

    location_query = """
        SELECT id FROM locations
        WHERE city_name = %s AND country_code = %s
    """

    location_parts = anomaly_data['location'].split(', ')
    if len(location_parts) == 2:
        city, country = location_parts
        result = hook.get_first(location_query, parameters=(city, country))
        location_id = result[0] if result else None
    else:
        location_id = anomaly_data.get('location_id')

    severity_map = {
        'temperature_spike': 'high',
        'missing_data': 'medium',
        'outlier': 'high'
    }

    sql = """
        INSERT INTO weather_anomalies (
            location_id, anomaly_type, observation_time, severity, description, metadata
        ) VALUES (%s, %s, %s, %s, %s, %s)
    """

    import json
    metadata = json.dumps(anomaly_data)

    params = (
        location_id,
        anomaly_data['type'],
        anomaly_data.get('observation_time'),
        severity_map.get(anomaly_data['type'], 'medium'),
        str(anomaly_data),
        metadata
    )

    hook.run(sql, parameters=params)


def check_anomalies(**context):
    """Run all anomaly detection checks and aggregate results."""
    all_anomalies = {
        'temperature_spikes': [],
        'missing_data': [],
        'outliers': []
    }

    logger.info("Running anomaly detection checks...")

    try:
        temp_anomalies = detect_temperature_anomalies()
        all_anomalies['temperature_spikes'] = temp_anomalies
        logger.info(f"Found {len(temp_anomalies)} temperature anomalies")
    except Exception as e:
        logger.error(f"Error detecting temperature anomalies: {e}")

    try:
        missing = detect_missing_locations()
        all_anomalies['missing_data'] = missing
        logger.info(f"Found {len(missing)} locations with missing/stale data")
    except Exception as e:
        logger.error(f"Error detecting missing data: {e}")

    try:
        outliers = detect_outliers()
        all_anomalies['outliers'] = outliers
        logger.info(f"Found {len(outliers)} outlier values")
    except Exception as e:
        logger.error(f"Error detecting outliers: {e}")

    total_anomalies = sum(len(v) for v in all_anomalies.values())

    if total_anomalies == 0:
        logger.info("No anomalies detected")
    else:
        logger.warning(f"Total anomalies detected: {total_anomalies}")

        try:
            for anomalies in all_anomalies.values():
                for anomaly in anomalies:
                    store_anomaly(anomaly)
            logger.info(f"Stored {total_anomalies} anomalies in database")
        except Exception as e:
            logger.error(f"Error storing anomalies: {e}")

    ti = context['ti']
    ti.xcom_push(key='anomalies', value=all_anomalies)

    return all_anomalies
