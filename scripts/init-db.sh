#!/bin/bash
set -e

# Create weather database and user using environment variables
# Note: POSTGRES_USER is 'airflow' (from docker-compose.yaml)
psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" <<-EOSQL
    CREATE DATABASE ${WEATHER_DB_NAME:-weather_data};
    CREATE USER ${WEATHER_DB_USER:-weather_user} WITH PASSWORD '${WEATHER_DB_PASSWORD:-weather_pass}';
    GRANT ALL PRIVILEGES ON DATABASE ${WEATHER_DB_NAME:-weather_data} TO ${WEATHER_DB_USER:-weather_user};
EOSQL

# Connect to weather database and grant schema permissions
psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "${WEATHER_DB_NAME:-weather_data}" <<-EOSQL
    GRANT ALL ON SCHEMA public TO ${WEATHER_DB_USER:-weather_user};
EOSQL

echo "Weather database initialized successfully!"
