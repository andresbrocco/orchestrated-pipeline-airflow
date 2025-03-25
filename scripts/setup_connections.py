#!/usr/bin/env python3
"""Set up Airflow connections and variables for the weather pipeline."""

import os
import subprocess
import sys


def run_airflow_cmd(cmd):
    """Run an Airflow CLI command and return success status."""
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"Error: {result.stderr}")
        return False
    return True


def setup_openweathermap_connection():
    """Create the OpenWeatherMap API connection."""
    api_key = os.environ.get("OPENWEATHER_API_KEY", "")

    if not api_key or api_key == "your_api_key_here":
        print("Warning: OPENWEATHER_API_KEY not set or using placeholder value")
        print("Set it in your .env file before running this script")
        return False

    # Delete existing connection if it exists
    subprocess.run(
        "airflow connections delete openweathermap_api 2>/dev/null",
        shell=True,
        capture_output=True,
    )

    # Create HTTP connection with API key in extra field
    cmd = f'''airflow connections add openweathermap_api \
        --conn-type http \
        --conn-host api.openweathermap.org \
        --conn-schema https \
        --conn-extra '{{"api_key": "{api_key}"}}'
    '''

    if run_airflow_cmd(cmd):
        print("Created connection: openweathermap_api")
        return True
    return False


def setup_postgres_connection():
    """Create the PostgreSQL connection for weather data."""
    db_name = os.environ.get("WEATHER_DB_NAME", "weather_data")
    db_user = os.environ.get("WEATHER_DB_USER", "weather_user")
    db_password = os.environ.get("WEATHER_DB_PASSWORD", "")

    if not db_password:
        print("Warning: WEATHER_DB_PASSWORD not set")
        print("Set it in your .env file before running this script")
        return False

    # Delete existing connection if it exists
    subprocess.run(
        "airflow connections delete weather_postgres 2>/dev/null",
        shell=True,
        capture_output=True,
    )

    # Create Postgres connection for weather data
    cmd = f"""airflow connections add weather_postgres \
        --conn-type postgres \
        --conn-host postgres \
        --conn-port 5432 \
        --conn-schema {db_name} \
        --conn-login {db_user} \
        --conn-password {db_password}
    """

    if run_airflow_cmd(cmd):
        print("Created connection: weather_postgres")
        return True
    return False


def setup_variables():
    """Create Airflow variables for weather API configuration."""
    variables = {
        "weather_api_base_url": "https://api.openweathermap.org/data/2.5",
        "weather_api_rate_limit": "60",
    }

    success = True
    for key, value in variables.items():
        cmd = f'airflow variables set {key} "{value}"'
        if run_airflow_cmd(cmd):
            print(f"Set variable: {key} = {value}")
        else:
            success = False

    return success


def main():
    print("Setting up Airflow connections and variables...")
    print("-" * 50)

    api_conn_ok = setup_openweathermap_connection()
    pg_conn_ok = setup_postgres_connection()
    var_ok = setup_variables()

    print("-" * 50)
    if api_conn_ok and pg_conn_ok and var_ok:
        print("Setup completed successfully!")
        print("\nVerify in Airflow UI:")
        print("  - Connections: Admin > Connections")
        print("  - Variables: Admin > Variables")
    else:
        print("Setup completed with some warnings")
        sys.exit(1)


if __name__ == "__main__":
    main()
