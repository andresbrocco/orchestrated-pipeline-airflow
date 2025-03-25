# Weather Data Pipeline with Apache Airflow

A production-ready ETL pipeline demonstrating workflow orchestration with Apache Airflow. This project fetches real-time weather data from the OpenWeatherMap API, transforms it, and stores it in PostgreSQL for analysis.

![Airflow](https://img.shields.io/badge/Apache%20Airflow-3.1.3-017CEE?style=flat&logo=Apache%20Airflow)
![Python](https://img.shields.io/badge/Python-3.13-3776AB?style=flat&logo=python)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-16-316192?style=flat&logo=postgresql)
![Docker](https://img.shields.io/badge/Docker-Compose-2496ED?style=flat&logo=docker)
![Metabase](https://img.shields.io/badge/Metabase-Analytics-2c3e50?style=flat)

## Overview

This portfolio project demonstrates practical data engineering skills by implementing a complete ETL pipeline with industry-standard tools and practices. The pipeline automatically collects weather data for multiple Brazilian cities, processes it, and stores it in a relational database with built-in data quality checks and anomaly detection.

**Key Highlights:**
- Fully containerized Airflow deployment with CeleryExecutor
- Custom sensors for API health monitoring
- Intelligent branching logic based on data quality
- XCom-based task communication
- Comprehensive error handling and alerting
- Anomaly detection for weather patterns
- Performance metrics logging

## Architecture

```
┌─────────────────┐
│ OpenWeatherMap  │
│      API        │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  API Health     │
│    Sensor       │
└────────┬────────┘
         │
         ▼
┌─────────────────┐     ┌──────────────┐
│  Extract        │────▶│  Transform   │
│  (5 cities)     │     │  (Kelvin→C)  │
└─────────────────┘     └──────┬───────┘
                               │
                               ▼
                        ┌──────────────┐
                        │Data Quality  │
                        │    Check     │
                        └──────┬───────┘
                               │
                    ┌──────────┴──────────┐
                    ▼                     ▼
            ┌──────────────┐      ┌─────────────┐
            │    Load      │      │   Alert     │
            │ (PostgreSQL) │      │  (Quality)  │
            └──────┬───────┘      └─────────────┘
                   │
                   ▼
            ┌──────────────┐
            │   Anomaly    │
            │  Detection   │
            └──────────────┘
```

## Features

### Core ETL Pipeline
- **Extract**: Fetches current weather and 5-day forecasts for 5 Brazilian cities
- **Transform**: Converts temperature units, enriches data with metadata
- **Load**: Stores processed data in normalized PostgreSQL schema
- **Scheduling**: Runs hourly with configurable schedule

### Advanced Airflow Features
- **Custom Sensors**: API health check before pipeline execution
- **Branching Logic**: Conditional task execution based on data quality
- **XCom Communication**: Efficient data passing between tasks
- **Task Groups**: Organized workflow structure
- **Retry Policies**: Exponential backoff with configurable limits
- **Email Alerts**: Notifications for failures and anomalies

### Monitoring & Quality
- **API Performance Metrics**: Response time, success rate tracking
- **Data Quality Checks**: Validates completeness and sanity
- **Anomaly Detection**: Identifies unusual weather patterns
- **Comprehensive Logging**: Detailed execution logs for debugging

### Analytics & Visualization
- **Metabase Integration**: Business intelligence dashboards
- **SQL Query Support**: Direct database queries for analysis
- **Data Exploration**: Interactive visualizations and filters
- **Custom Dashboards**: Create your own weather analytics

## Technology Stack

| Component        | Technology           | Purpose                             |
| ---------------- | -------------------- | ----------------------------------- |
| Orchestration    | Apache Airflow 3.1.3 | Workflow scheduling and monitoring  |
| Executor         | CeleryExecutor       | Distributed task execution          |
| Database         | PostgreSQL 16        | Data warehouse and Airflow metadata |
| Message Broker   | Redis 7.2            | Celery task queue                   |
| Analytics        | Metabase             | Business intelligence & dashboards  |
| Containerization | Docker Compose       | Service orchestration               |
| Language         | Python 3.13          | Pipeline implementation             |
| Package Manager  | uv                   | Fast dependency management          |

## Project Structure

```
orchestrated-pipeline-airflow/
├── dags/                       # Airflow DAG definitions
│   ├── weather_pipeline.py     # Main ETL DAG
│   ├── db_init.py              # Database initialization DAG
│   ├── weather_backfill.py     # Historical data backfill DAG
│   └── tasks/                  # Task implementation modules
│       ├── extract.py          # API data extraction with metrics
│       ├── transform.py        # Data transformation logic
│       ├── load.py             # Database loading functions
│       ├── validate.py         # Data quality checks
│       ├── anomaly.py          # Anomaly detection algorithms
│       └── locations.py        # Location management
├── plugins/                    # Custom Airflow plugins
│   └── sensors/
│       └── api_health_sensor.py # OpenWeatherMap health check
├── config/
│   └── locations.json          # Cities configuration (5 Brazilian cities)
├── sql/
│   └── schema.sql              # Database schema definition
├── scripts/
│   ├── init-db.sh              # PostgreSQL initialization script
│   └── setup_connections.py    # Airflow connections setup
├── tests/                      # Unit and integration tests
├── docs/                       # Additional documentation
│   ├── metabase.md             # Metabase analytics guide
│   ├── setup.md                # Setup instructions
│   ├── architecture.md         # System design
│   └── troubleshooting.md      # Common issues
├── docker-compose.yaml         # Docker services configuration
├── .env.example                # Environment variables template
├── requirements.txt            # Python dependencies
└── README.md                   # This file
```

## Prerequisites

Before running this project, ensure you have:

- **Docker** (20.10+) and **Docker Compose** (2.0+)
- **Python 3.13** (for local development)
- **OpenWeatherMap API Key** (free tier available at [openweathermap.org](https://openweathermap.org/api))
- **Git** for version control
- **4GB RAM minimum** for Docker containers

## Quick Start

### 1. Clone the Repository

```bash
git clone <repository-url>
cd orchestrated-pipeline-airflow
```

### 2. Get OpenWeatherMap API Key

1. Visit [OpenWeatherMap API](https://openweathermap.org/api)
2. Sign up for a free account
3. Generate an API key (free tier: 1,000 calls/day, 60 calls/minute)

### 3. Configure Environment Variables

```bash
# Copy the example environment file
cp .env.example .env

# Edit .env with your credentials
nano .env  # or use your preferred editor
```

**Required variables in `.env`:**
```bash
# OpenWeather API Key (REQUIRED)
OPENWEATHER_API_KEY=your_actual_api_key_here

# Weather Database Credentials (change defaults!)
WEATHER_DB_PASSWORD=your_secure_password_here

# Airflow Admin Credentials
_AIRFLOW_WWW_USER_USERNAME=airflow
_AIRFLOW_WWW_USER_PASSWORD=airflow

# Airflow UID (Linux: run `echo $(id -u)`, macOS/Windows: use 50000)
AIRFLOW_UID=50000
```

### 4. Generate Fernet Key (for encryption)

```bash
# Install Python dependencies locally (optional for development)
pip install cryptography

# Generate Fernet key
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"

# Add the output to .env file as AIRFLOW__CORE__FERNET_KEY
```

### 5. Start the Pipeline

```bash
# Start all services (Airflow, PostgreSQL, Redis)
docker compose up -d

# Wait for initialization (usually 1-2 minutes)
docker compose logs -f airflow-init

# Verify all services are running
docker compose ps
```

### 6. Access Airflow UI

1. Open your browser to [http://localhost:8080](http://localhost:8080)
2. Login with credentials from `.env` (default: `airflow` / `airflow`)
3. Navigate to DAGs page
4. Unpause the `weather_data_pipeline` DAG
5. Trigger a manual run or wait for the hourly schedule

### 7. Access Metabase Analytics

1. Open your browser to [http://localhost:3000](http://localhost:3000)
2. On first access, complete the setup wizard:
   - Create admin account (credentials from `.env`)
   - Connect to `weather_data` database (host: `postgres`)
3. Explore pre-built dashboards or create your own
4. See [docs/metabase.md](docs/metabase.md) for detailed documentation

## Usage

### Triggering the Weather Pipeline

**Via Airflow UI:**
1. Navigate to [http://localhost:8080](http://localhost:8080)
2. Find `weather_data_pipeline` in the DAGs list
3. Click the play button (▶) to trigger manually
4. Monitor progress in the Graph or Grid view

**Via CLI:**
```bash
# Trigger a DAG run
docker compose exec airflow-scheduler airflow dags trigger weather_data_pipeline

# List recent DAG runs
docker compose exec airflow-scheduler airflow dags list-runs -d weather_data_pipeline

# View task instance status
docker compose exec airflow-scheduler airflow tasks states-for-dag-run weather_data_pipeline <run-id>
```

### Querying Weather Data

```bash
# Connect to PostgreSQL
docker compose exec postgres psql -U weather_user -d weather_data

# View recent observations
SELECT
    l.city_name,
    wo.observation_time,
    wo.temperature,
    wo.weather_description
FROM weather_observations wo
JOIN locations l ON wo.location_id = l.id
ORDER BY wo.observation_time DESC
LIMIT 10;

# Check for anomalies
SELECT
    l.city_name,
    wa.anomaly_type,
    wa.detected_at,
    wa.severity,
    wa.description
FROM weather_anomalies wa
JOIN locations l ON wa.location_id = l.id
ORDER BY wa.detected_at DESC;

# View API metrics (from logs)
docker compose logs airflow-worker | grep "API Metrics Summary"
```

### Managing Docker Services

```bash
# View logs for all services
docker compose logs -f

# View logs for specific service
docker compose logs -f airflow-scheduler
docker compose logs -f postgres

# Restart a service
docker compose restart airflow-scheduler

# Stop all services
docker compose down

# Stop and remove all data (including database)
docker compose down -v

# Rebuild services after code changes
docker compose up -d --build
```

## Database Schema

The pipeline uses two PostgreSQL databases:

### 1. Airflow Metadata Database (`airflow`)
- Managed by Airflow
- Stores DAG runs, task instances, connections, variables
- User: `airflow`

### 2. Weather Data Database (`weather_data`)
- Stores weather observations and forecasts
- User: `weather_user`

**Tables:**

```sql
locations               -- Cities being tracked
  ├── id (PK)
  ├── city_name
  ├── country_code
  ├── latitude
  └── longitude

weather_observations    -- Current weather data
  ├── id (PK)
  ├── location_id (FK)
  ├── observation_time
  ├── temperature (°C)
  ├── feels_like
  ├── humidity
  ├── pressure
  ├── wind_speed
  └── weather_description

weather_forecasts       -- 5-day forecast data
  ├── id (PK)
  ├── location_id (FK)
  ├── forecast_time
  ├── predicted_for
  ├── temperature (°C)
  └── precipitation_probability

weather_anomalies       -- Detected anomalies
  ├── id (PK)
  ├── location_id (FK)
  ├── anomaly_type
  ├── detected_at
  ├── severity (low/medium/high)
  └── description
```

## Configuration

### Cities Tracked

The pipeline tracks 5 Brazilian cities (defined in `config/locations.json`):
- Campinas, SP
- São Paulo, SP
- São Luís, MA
- Guarapari, ES
- Ubatuba, SP

**To add/modify cities:**
1. Edit `config/locations.json`
2. Restart the Airflow services: `docker compose restart`
3. Re-run the `db_init` DAG to update the database

### DAG Schedule

Default schedule: `@hourly` (runs every hour)

**To change the schedule:**
1. Edit `dags/weather_pipeline.py`
2. Modify the `schedule` parameter in the DAG definition
3. Common options:
   - `@hourly` - Every hour
   - `@daily` - Once per day at midnight
   - `"0 */6 * * *"` - Every 6 hours
   - `None` - Manual trigger only

### Email Alerts

To enable email notifications for failures:

1. Configure SMTP settings in `.env`:
```bash
AIRFLOW__SMTP__SMTP_HOST=smtp.gmail.com
AIRFLOW__SMTP__SMTP_USER=your-email@gmail.com
AIRFLOW__SMTP__SMTP_PASSWORD=your_app_password
AIRFLOW__SMTP__SMTP_PORT=587
```

2. For Gmail, use an [App Password](https://support.google.com/accounts/answer/185833)

3. Update the email in `dags/weather_pipeline.py`:
```python
default_args = {
    "email": ["your-email@example.com"],
    "email_on_failure": True,
}
```

## Troubleshooting

### Common Issues

**1. Containers fail to start**
```bash
# Check Docker logs
docker compose logs airflow-init

# Verify .env file exists and has required variables
cat .env | grep OPENWEATHER_API_KEY

# Ensure ports are available (8080, 5432, 6379)
lsof -i :8080
```

**2. API key errors**
```bash
# Verify API key is valid
curl "http://api.openweathermap.org/data/2.5/weather?q=London&appid=YOUR_API_KEY"

# Check if key is loaded in Airflow
docker compose exec airflow-scheduler env | grep OPENWEATHER
```

**3. Database connection issues**
```bash
# Test PostgreSQL connection
docker compose exec postgres psql -U weather_user -d weather_data -c "SELECT 1;"

# Check if weather_data database was created
docker compose exec postgres psql -U airflow -c "\l"
```

**4. DAG not appearing in UI**
```bash
# Check for Python syntax errors
docker compose exec airflow-scheduler airflow dags list

# View DAG import errors
docker compose logs airflow-scheduler | grep -i error
```

**5. Tasks stuck in queued state**
```bash
# Check Celery worker status
docker compose logs airflow-worker

# Verify Redis is running
docker compose exec redis redis-cli ping
```

### Performance Tips

- **Reduce API calls**: Modify `config/locations.json` to track fewer cities
- **Adjust schedule**: Change from `@hourly` to `@daily` if needed
- **Increase resources**: Allocate more RAM to Docker (4GB minimum, 8GB recommended)
- **Monitor logs**: Use `docker compose logs -f` to watch for bottlenecks

## Development

### Running Tests

```bash
# Install dependencies locally
uv venv
uv pip install -r requirements.txt

# Run all tests
./venv/bin/python3 -m pytest tests/

# Run specific test file
./venv/bin/python3 -m pytest tests/test_transform.py -v
```

### Adding Custom Tasks

1. Create a new task module in `dags/tasks/`
2. Import and use in `dags/weather_pipeline.py`
3. Test locally before deploying

### Extending the Schema

1. Modify `sql/schema.sql`
2. Create migration script if needed
3. Run `db_init` DAG to apply changes

## Key Concepts Demonstrated

This project showcases several important data engineering patterns:

1. **ETL Pipeline Design**: Separation of extract, transform, load concerns
2. **Workflow Orchestration**: Airflow DAGs with task dependencies
3. **Error Handling**: Retry policies, exponential backoff, failure callbacks
4. **Data Quality**: Validation checks and branching logic
5. **Monitoring**: API metrics, anomaly detection, comprehensive logging
6. **Containerization**: Multi-service Docker Compose setup
7. **Database Design**: Normalized schema with proper indexing
8. **API Integration**: Rate limiting, health checks, error handling
9. **Testing**: Unit tests for transformation and validation logic
10. **Documentation**: Clear README, inline comments, docstrings

## API Information

**OpenWeatherMap API:**
- Endpoint: `api.openweathermap.org/data/2.5/weather`
- Rate Limits (Free Tier):
  - 1,000 calls/day
  - 60 calls/minute
- Temperature Unit: Kelvin (converted to Celsius in pipeline)
- Documentation: [OpenWeatherMap API Docs](https://openweathermap.org/api)

**Sample API response examples** can be found in `docs/api-samples/`

## Future Enhancements

Potential improvements for production deployment:

- [ ] Add data visualization dashboard (Superset/Metabase)
- [ ] Implement data retention policies
- [ ] Add support for additional weather APIs
- [ ] Create data quality metrics dashboard
- [ ] Implement historical trend analysis
- [ ] Add Slack/Discord notifications
- [ ] Set up CI/CD pipeline for testing
- [ ] Add more comprehensive unit tests
- [ ] Implement data versioning
- [ ] Create Kubernetes deployment manifests

## License

This is a portfolio project created for educational and demonstration purposes.

## Contact

Created by Andre Brocco as part of a data engineering portfolio.

**Project Repository**: [GitHub](https://github.com/andresbrocco/orchestrated-pipeline-airflow)