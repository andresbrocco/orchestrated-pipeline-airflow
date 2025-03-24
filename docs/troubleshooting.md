# Troubleshooting Guide

Quick reference for resolving issues. See [README.md](../README.md#troubleshooting) for common problems.

## Quick Diagnostics

```bash
# Service health
docker compose ps
docker compose logs --tail=50 | grep -i error

# Airflow status
docker compose exec airflow-scheduler airflow dags list
docker compose exec airflow-scheduler airflow dags list-import-errors

# Database connectivity
docker compose exec postgres pg_isready -U airflow
docker compose exec postgres psql -U weather_user -d weather_data -c "SELECT 1;"

# API key validation
docker compose exec airflow-scheduler env | grep OPENWEATHER_API_KEY
```

## Airflow-Specific Issues

### DAG Not Appearing

```bash
# Check for import errors
docker compose exec airflow-scheduler airflow dags list-import-errors

# Verify DAG file syntax
docker compose exec airflow-scheduler python /opt/airflow/dags/weather_pipeline.py

# Force DAG refresh (not typically needed with Airflow 3.x)
docker compose restart airflow-dag-processor
```

### Tasks Stuck in Queued State

```bash
# Check Celery worker status
docker compose logs airflow-worker
docker compose exec airflow-worker celery -A airflow.providers.celery.executors.celery_executor.app inspect active

# Verify Redis connection
docker compose exec redis redis-cli ping

# Restart worker if needed
docker compose restart airflow-worker
```

### XCom Data Not Passing

```bash
# Check XCom size (max 1MB by default)
docker compose exec postgres psql -U airflow -d airflow -c "SELECT key, length(value::text) FROM xcom ORDER BY length(value::text) DESC LIMIT 10;"

# For large data, consider external storage or adjust config:
# AIRFLOW__CORE__XCOM_BACKEND=airflow.models.xcom.BaseXCom
```

## API Issues

### Rate Limit Exceeded

```bash
# Check current API usage
docker compose logs airflow-worker | grep "API Metrics Summary"

# Free tier: 1,000 calls/day, 60/min
# Solution: Reduce schedule frequency or upgrade API plan
```

### Timemachine API 401 Error (Backfill DAG)

Historical weather data requires One Call API 3.0 subscription. Backfill DAG will fail with free tier.

Solution: Either subscribe to One Call API 3.0 or skip backfill DAG.

## Database Issues

### Connection Pool Exhausted

```bash
# Check active connections
docker compose exec postgres psql -U airflow -c "SELECT count(*) FROM pg_stat_activity WHERE datname='airflow';"

# Increase pool size in docker-compose.yaml:
# AIRFLOW__DATABASE__SQL_ALCHEMY_POOL_SIZE=10
# AIRFLOW__DATABASE__SQL_ALCHEMY_MAX_OVERFLOW=20
```

### Schema Migration Required

```bash
# After upgrading Airflow version
docker compose run --rm airflow-init airflow db migrate
docker compose up -d
```

## Performance Issues

### High Memory Usage

```bash
# Check container stats
docker stats

# Reduce worker concurrency
# Edit docker-compose.yaml: AIRFLOW__CELERY__WORKER_CONCURRENCY=2

# Use LocalExecutor instead of CeleryExecutor for lower overhead
# Edit docker-compose.yaml: AIRFLOW__CORE__EXECUTOR=LocalExecutor
# Remove redis, airflow-worker services
```

### Slow Task Execution

```bash
# Check if tasks are waiting for resources
docker compose logs airflow-scheduler | grep -i "resource"

# Profile task execution (add to task code):
# import time
# start = time.time()
# # ... task logic
# logger.info(f"Task completed in {time.time() - start:.2f}s")
```

## Data Quality Issues

### Anomaly Detection False Positives

Adjust thresholds in `dags/tasks/anomaly.py`:
- `TEMP_THRESHOLD = 10` (degrees Celsius)
- `HUMIDITY_THRESHOLD = 30` (percentage)

### Missing Forecast Data

OpenWeatherMap free tier occasionally returns incomplete forecast data. Task will log warning but continue.

## Recovery Procedures

### Reset DAG State

```bash
# Clear all task instances for a DAG run
docker compose exec airflow-scheduler airflow tasks clear weather_data_pipeline -s 2025-03-15 -e 2025-03-15

# Mark failed task as success
docker compose exec airflow-scheduler airflow tasks set-state weather_data_pipeline extract_weather 2025-03-15 success
```

### Rebuild from Scratch

```bash
# Nuclear option: destroy everything and start fresh
docker compose down -v
rm -rf logs/*
docker compose up -d
# Re-run db_init DAG
```

### Restore Database

```bash
# From backup
cat backup.sql | docker compose exec -T postgres psql -U weather_user -d weather_data

# From scratch (re-run db_init DAG)
docker compose exec airflow-scheduler airflow dags trigger db_init
```
