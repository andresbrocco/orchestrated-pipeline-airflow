"""Database initialization DAG - creates schema and populates initial locations."""

import logging
import sys
from datetime import datetime
from pathlib import Path

# Add dags directory to path for local imports
sys.path.insert(0, str(Path(__file__).parent))

from airflow import DAG
from airflow.providers.standard.operators.python import PythonOperator
from airflow.providers.postgres.hooks.postgres import PostgresHook

from tasks.locations import load_locations_from_config

logger = logging.getLogger(__name__)

SQL_FILE_PATH = "/opt/airflow/sql/schema.sql"
POSTGRES_CONN_ID = "weather_postgres"


def create_schema():
    """Execute schema.sql to create database tables."""
    with open(SQL_FILE_PATH, "r") as f:
        sql = f.read()

    hook = PostgresHook(postgres_conn_id=POSTGRES_CONN_ID)
    hook.run(sql)
    logger.info("Schema created successfully")


def populate_locations():
    """Insert initial locations from config file."""
    locations = load_locations_from_config()
    if not locations:
        logger.warning("No locations found in config")
        return

    hook = PostgresHook(postgres_conn_id=POSTGRES_CONN_ID)

    insert_sql = """
        INSERT INTO locations (city_name, country_code, latitude, longitude)
        VALUES (%s, %s, %s, %s)
        ON CONFLICT (city_name, country_code) DO NOTHING
    """

    for loc in locations:
        hook.run(
            insert_sql, parameters=(loc["city"], loc["country"], loc["lat"], loc["lon"])
        )
        logger.info(f"Processed location: {loc['city']}, {loc['country']}")

    logger.info(f"Populated {len(locations)} locations")


with DAG(
    dag_id="db_init",
    description="Initialize database schema and populate locations",
    schedule=None,
    start_date=datetime(2025, 3, 3),
    catchup=False,
    tags=["setup", "database"],
) as dag:
    create_schema_task = PythonOperator(
        task_id="create_schema",
        python_callable=create_schema,
    )

    populate_locations_task = PythonOperator(
        task_id="populate_locations",
        python_callable=populate_locations,
    )

    create_schema_task >> populate_locations_task
