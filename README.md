# Orchestrated Pipeline with Apache Airflow

A data engineering portfolio project demonstrating ETL pipeline orchestration using Apache Airflow. This pipeline fetches weather data from OpenWeatherMap API, transforms it, and stores it in PostgreSQL.

## Architecture Overview

This project implements a scheduled ETL pipeline that:
- Extracts weather data from OpenWeatherMap API for multiple cities
- Transforms raw JSON data with unit conversions and enrichment
- Loads processed data into PostgreSQL database
- Monitors data quality and API health
- Provides alerting for anomalies

**Tech Stack:**
- Apache Airflow 3.1.3 (workflow orchestration)
- PostgreSQL (data warehouse)
- Docker Compose (containerization)
- Python 3.13

## Setup Instructions

### Prerequisites
- Python 3.13 installed
- Docker and Docker Compose
- OpenWeatherMap API key (free tier)

### Installation

1. **Clone the repository**
```bash
git clone <repository-url>
cd orchestrated-pipeline-airflow
```

2. **Set up Python environment**
```bash
# Install uv package manager if not already installed
curl -LsSf https://astral.sh/uv/install.sh | sh

# Create virtual environment
uv venv

# Install dependencies
uv pip install -r requirements.txt
```

3. **Configure environment variables**
```bash
# Copy environment template
cp .env.example .env

# Edit .env with your credentials
# - OpenWeatherMap API key
# - Database credentials
# - Airflow admin credentials
```

4. **Start Airflow services**
```bash
docker compose up -d
```

5. **Verify services are running**
```bash
# Check all container status
docker compose ps

# View logs for a specific service
docker compose logs airflow-scheduler

# Check Airflow init completed successfully
docker compose logs airflow-init | tail -20
```

6. **Access Airflow UI**
- Open http://localhost:8080
- Login with credentials from `.env` (default: airflow/airflow)
- See [docs/setup.md](docs/setup.md) for detailed setup and troubleshooting

## Useful Docker Commands

### Service Management
```bash
# Start all services
docker compose up -d

# Stop all services
docker compose down

# Restart a specific service
docker compose restart airflow-scheduler

# View real-time logs
docker compose logs -f
```

### Database Verification
```bash
# Check Airflow metadata tables
docker compose exec postgres psql -U airflow -d airflow -c "SELECT tablename FROM pg_tables WHERE schemaname = 'public' LIMIT 10;"

# Test weather_data database connection
docker compose exec postgres psql -U weather_user -d weather_data -c "SELECT 1 as connection_test;"

# Interactive PostgreSQL shell
docker compose exec postgres psql -U airflow -d airflow
```

### Troubleshooting
```bash
# Check container health
docker compose ps

# View detailed logs for init process
docker compose logs airflow-init

# Check for errors in scheduler
docker compose logs airflow-scheduler | grep -i error

# Restart everything from scratch
docker compose down -v && docker compose up -d
```

## Project Structure

```
orchestrated-pipeline-airflow/
├── dags/                  # Airflow DAG definitions
│   └── tasks/             # Task implementation modules
├── plugins/               # Custom Airflow plugins
│   ├── operators/         # Custom operators
│   └── sensors/           # Custom sensors
├── config/                # Configuration files
│   └── locations.json     # Cities to track (5 cities currently)
├── sql/                   # Database schema scripts
├── tests/                 # Unit and integration tests
├── docs/                  # Project documentation
├── logs/                  # Airflow logs (local development)
├── requirements.txt       # Python dependencies
├── .env.example           # Environment variables template
└── README.md              # This file
```

## Usage

Detailed usage instructions will be added as the pipeline is implemented.

## Features

Planned features (to be implemented):
- [ ] Automated weather data collection for multiple cities
- [ ] Data transformation with temperature unit conversions
- [ ] PostgreSQL data warehouse with optimized schema
- [ ] API health monitoring with sensors
- [ ] XCom-based task communication
- [ ] Branching logic for data quality checks
- [ ] Email alerts for failures and anomalies
- [ ] Historical data backfilling
- [ ] Comprehensive logging and monitoring

## Development

### Running Tests
```bash
./venv/bin/python3 -m pytest tests/
```

## License

This is a portfolio project for educational and demonstration purposes.

## Contact

Created as part of a data engineering portfolio.