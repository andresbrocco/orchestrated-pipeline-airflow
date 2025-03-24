# Architecture Design Rationales

This document explains the design decisions and trade-offs made in implementing this weather data pipeline. For architecture diagrams, features, and setup instructions, see the main README.

## Executor Choice: CeleryExecutor vs LocalExecutor

**Decision:** CeleryExecutor with Redis message broker

**Rationale:**
- Demonstrates distributed task execution for portfolio purposes
- LocalExecutor would be simpler but doesn't showcase scalability concepts
- In production, CeleryExecutor allows horizontal scaling by adding worker nodes
- Trade-off: Higher resource usage (requires Redis) vs learning value and scalability demonstration

## XCom for Inter-Task Communication

**Decision:** Use XCom to pass location lists and API metrics between tasks

**Alternatives considered:**
- External storage (S3, database) - Too complex for small data volumes in this use case
- Task return values only - Less explicit, harder to access metrics for monitoring

**Rationale:**
- XCom is built into Airflow, no additional infrastructure needed
- Appropriate for small-to-medium data payloads (location lists, metrics)
- Makes data flow between tasks explicit and trackable in Airflow UI
- Limitation: Not suitable for large datasets (e.g., raw API responses) - those would need external storage

## Task Retry Strategy

**Decision:** Differentiated retry policies per task type
- Extract: 5 retries with exponential backoff (5-30 min delays)
- Transform: 2 retries without exponential backoff (2 min fixed)
- Load: 3 retries with exponential backoff (default, 5-30 min)

**Rationale:**
- API calls (extract) are most likely to have transient failures (rate limits, network issues), so more retries with longer delays
- Transform operations typically fail due to data quality issues (not transient), so fewer retries make sense
- Database operations (load) can have connection issues, moderate retry strategy balances persistence vs quick failure detection

## Branching Logic for Data Quality

**Decision:** BranchPythonOperator to conditionally skip load based on quality checks

**Why not fail the entire DAG:**
- Partial failures shouldn't block the entire pipeline
- Quality issues might affect only some cities, not all data
- Alerting on quality issues while continuing anomaly detection provides better observability
- In production, this allows manual intervention without re-running entire ETL

## Custom Sensor for API Health

**Decision:** Implement OpenWeatherMapHealthSensor to check API availability before extraction

**Alternatives:**
- Skip health check and rely on task retries - Results in wasted API calls during outages
- Use generic HttpSensor - Less portable, requires configuring connection details per DAG

**Rationale:**
- Pre-flight check prevents wasting API quota during outages
- Demonstrates custom sensor implementation for portfolio
- Reusable across multiple DAGs (backfill, future enhancements)
- Trade-off: Additional API call per DAG run vs early failure detection

## Database Architecture: Two Separate Databases

**Decision:**
- `airflow` database for Airflow metadata
- `weather_data` database for application data

**Why not use a single database:**
- Separation of concerns: Airflow internals vs application data
- Different backup/retention policies (Airflow logs vs weather data)
- Demonstrates proper database design patterns for data engineering
- Easier to export just application data for analytics without Airflow metadata

## Hourly Schedule vs Real-Time

**Decision:** `@hourly` schedule with catchup=False

**Alternatives:**
- Real-time with streaming (Kafka, Airflow sensors) - Over-engineered for weather data that doesn't change every minute
- Daily schedule - Less data granularity, misses weather patterns

**Rationale:**
- Weather data has low velocity (changes meaningfully every hour, not second-by-second)
- OpenWeatherMap free tier rate limits (60 calls/min) support hourly without issues
- Catchup disabled prevents backlog on pipeline failures or maintenance windows
- For sub-hourly needs, backfill DAG exists for historical data

## Task Grouping Strategy

**Decision:** Flat task structure without TaskGroups in main DAG

**Why not use TaskGroups:**
- Task groups add visual organization but increase cognitive complexity for simple pipelines
- This DAG has clear linear flow: sensor → get locations → extract → transform → branch → load/alert → anomaly
- For portfolio purposes, demonstrates dependencies without over-engineering
- Future enhancement: Could group extract/transform/load per city for parallel processing

## Anomaly Detection Placement

**Decision:** Run anomaly detection after load, even on quality alert branch

**Rationale:**
- Uses historical data in database, not just current run
- trigger_rule="none_failed" ensures it runs if load succeeds OR quality alert fires
- Detecting anomalies on existing data is valuable even if current load fails
- Separates concerns: quality checks validate input, anomaly detection finds patterns

## Performance Metrics Logging

**Decision:** In-memory metrics collection, logged but not persisted

**Alternatives:**
- Store metrics in database - Adds table complexity, not critical for this use case
- No metrics - Misses opportunity to demonstrate observability concepts

**Rationale:**
- Logging provides sufficient visibility for troubleshooting
- XCom storage makes metrics available to downstream tasks if needed
- For production, would integrate with proper observability stack (Prometheus, Datadog)
- Trade-off: Metrics lost after DAG run vs simplicity

## API Key Management

**Decision:** Store API key in Airflow connection's `extra` field (JSON)

**Alternatives:**
- Environment variables - Less secure, visible in docker-compose.yaml
- External secrets manager (AWS Secrets Manager, HashiCorp Vault) - Over-engineered for local development

**Rationale:**
- Airflow connections provide encryption via Fernet key
- Centralizes credential management in Airflow metadata
- Demonstrates proper Airflow connection usage
- For production, would use external secrets backend with IAM roles
