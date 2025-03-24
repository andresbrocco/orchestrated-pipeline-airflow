# Deployment Guide

Quick deployment reference for experienced users. See [README.md](../README.md) for detailed setup instructions.

## Prerequisites

- Docker 20.10+ and Docker Compose 2.0+
- OpenWeatherMap API key (free tier sufficient)
- Ports 8080, 5432, 6379 available
- 4GB+ RAM for Docker

## Deployment Steps

- Remove the lines `ports: - "5432:5432"` from the docker-compose.yaml file for safety.

```bash
# 1. Clone and configure
git clone <repo-url>
cd orchestrated-pipeline-airflow
cp .env.example .env
# Edit .env with your OPENWEATHER_API_KEY and passwords

# 2. Generate Fernet key for Airflow
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
# Add to .env as AIRFLOW__CORE__FERNET_KEY

# 3. Start services
docker compose up -d

# 4. Verify deployment
docker compose ps  # All services should be healthy
docker compose logs airflow-init  # Check initialization logs

# 5. Access Airflow UI
# http://localhost:8080 (credentials from .env: airflow/airflow)

# 6. Run database initialization DAG
docker compose exec airflow-scheduler airflow dags unpause db_init
docker compose exec airflow-scheduler airflow dags trigger db_init

# 7. Activate main pipeline
docker compose exec airflow-scheduler airflow dags unpause weather_data_pipeline
```

## Post-Deployment Verification

```bash
# Verify database setup
docker compose exec postgres psql -U weather_user -d weather_data -c "\dt"

# Check connections configured
docker compose exec airflow-scheduler airflow connections list | grep -E "openweathermap|weather_postgres"

# Test API connectivity
docker compose exec airflow-scheduler curl -s "https://api.openweathermap.org/data/2.5/weather?q=London&appid=${OPENWEATHER_API_KEY}" | jq .

# Trigger manual run
docker compose exec airflow-scheduler airflow dags trigger weather_data_pipeline
```

## Service Management

```bash
# Stop all services
docker compose down

# Stop and remove volumes (data loss!)
docker compose down -v

# Restart specific service
docker compose restart airflow-scheduler

# View logs
docker compose logs -f airflow-worker

# Rebuild after code changes
docker compose up -d --build
```

## Data Backup

```bash
# Backup PostgreSQL weather data
docker compose exec postgres pg_dump -U weather_user weather_data > backup.sql

# Restore from backup
cat backup.sql | docker compose exec -T postgres psql -U weather_user -d weather_data
```

## Production Considerations

**Security:**
- Change default passwords in `.env`
- Use external secrets manager (AWS Secrets Manager, Vault)
- Enable SSL for PostgreSQL connections
- Configure firewall rules

**Scaling:**
- Add more Celery workers: `docker compose up -d --scale airflow-worker=3`
- Use external PostgreSQL/Redis for multi-host deployment
- Configure LocalExecutor for single-node deployments (lower overhead)

**Monitoring:**
- Integrate Prometheus metrics: `AIRFLOW__METRICS__STATSD_ON=True`
- Configure email alerts in DAG default_args
- Set up log aggregation (ELK, CloudWatch)

**Resource Allocation:**
- Minimum: 4GB RAM, 2 CPUs
- Recommended: 8GB RAM, 4 CPUs
- Adjust `AIRFLOW__CELERY__WORKER_CONCURRENCY` based on available resources
