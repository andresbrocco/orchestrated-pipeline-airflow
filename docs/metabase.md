# Metabase Analytics Documentation

## Quick Start

### Access Metabase

1. Ensure Docker services are running:
   ```bash
   docker compose ps
   ```

2. Navigate to Metabase UI:
   - **URL**: http://localhost:3000
   - **Health Check**: http://localhost:3000/api/health

### Initial Setup (First Time Only)

1. **Welcome Screen**: Click "Let's get started"

2. **Create Admin Account**:
   - Email: `admin@weatherpipeline.com` (from .env)
   - Password: `MetabaseSecure2024!` (from .env)
   - Or use your own credentials

3. **Add Database Connection**:
   - **Database type**: PostgreSQL
   - **Display name**: Weather Data
   - **Host**: `postgres` (Docker internal DNS)
   - **Port**: 5432
   - **Database name**: `weather_data`
   - **Username**: `weather_user`
   - **Password**: `weather_pass_123` (from .env WEATHER_DB_PASSWORD)
   - Click "Save"

4. **Database Sync**: Metabase will automatically discover tables (1-2 minutes)

## Available Tables

Once connected, you can query these tables directly:

- **`locations`** - Cities being tracked (5 Brazilian cities)
- **`weather_observations`** - Hourly current weather data
- **`weather_forecasts`** - 5-day forecast data
- **`weather_anomalies`** - Detected weather anomalies

## Sample Queries

### Current Weather for All Cities
```sql
SELECT
    l.city_name,
    wo.temperature,
    wo.humidity,
    wo.weather_condition,
    wo.observation_time
FROM weather_observations wo
JOIN locations l ON wo.location_id = l.id
WHERE wo.observation_time = (
    SELECT MAX(observation_time)
    FROM weather_observations
    WHERE location_id = wo.location_id
)
ORDER BY l.city_name;
```

### Daily Temperature Averages (Last 7 Days)
```sql
SELECT
    l.city_name,
    DATE(wo.observation_time) as date,
    ROUND(AVG(wo.temperature), 2) as avg_temp,
    ROUND(MIN(wo.temperature), 2) as min_temp,
    ROUND(MAX(wo.temperature), 2) as max_temp
FROM weather_observations wo
JOIN locations l ON wo.location_id = l.id
WHERE wo.observation_time >= CURRENT_DATE - INTERVAL '7 days'
GROUP BY l.city_name, DATE(wo.observation_time)
ORDER BY date DESC, l.city_name;
```

### Upcoming Forecasts
```sql
SELECT
    l.city_name,
    wf.predicted_for,
    wf.temperature,
    wf.weather_condition,
    wf.precipitation_probability
FROM weather_forecasts wf
JOIN locations l ON wf.location_id = l.id
WHERE wf.predicted_for > CURRENT_TIMESTAMP
  AND wf.predicted_for < CURRENT_TIMESTAMP + INTERVAL '24 hours'
ORDER BY l.city_name, wf.predicted_for;
```

### Recent Anomalies
```sql
SELECT
    l.city_name,
    wa.anomaly_type,
    wa.severity,
    wa.description,
    wa.detected_at
FROM weather_anomalies wa
LEFT JOIN locations l ON wa.location_id = l.id
WHERE wa.detected_at >= CURRENT_DATE - INTERVAL '7 days'
ORDER BY wa.detected_at DESC;
```

## Creating Dashboards

1. **Create a Question**:
   - Click "New" → "Question"
   - Choose data source (table)
   - Build query visually or use SQL
   - Select visualization type

2. **Save to Dashboard**:
   - After creating visualization, click "Save"
   - Create new dashboard or add to existing
   - Arrange cards on dashboard grid

3. **Add Filters** (optional):
   - Click "Add a Filter"
   - Choose field (e.g., city_name, date)
   - Connect to relevant cards

## Troubleshooting

### Cannot Connect to Database

- Verify PostgreSQL is running:
  ```bash
  docker compose ps postgres
  ```
- Check that host is `postgres` (not localhost)
- Verify password matches .env file

### No Data Showing

- Check if data exists:
  ```bash
  docker compose exec postgres psql -U weather_user -d weather_data \
    -c "SELECT COUNT(*) FROM weather_observations;"
  ```
- If no data, trigger the Airflow DAG at http://localhost:8080

### Metabase Container Issues

- Check logs:
  ```bash
  docker compose logs metabase
  ```
- Restart if needed:
  ```bash
  docker compose restart metabase
  ```

## Additional Resources

- [Metabase Documentation](https://www.metabase.com/docs/latest/)
- [SQL Tutorial](https://www.metabase.com/learn/sql-questions/sql-tutorial)