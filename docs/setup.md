# Airflow Setup and UI Access

## Accessing the Airflow Web UI

**URL:** http://localhost:8080

### Default Credentials

The admin user is created automatically during the first startup. Credentials are configured in your `.env` file:

- **Username:** `_AIRFLOW_WWW_USER_USERNAME` (default: `airflow`)
- **Password:** `_AIRFLOW_WWW_USER_PASSWORD` (default: `airflow`)

### First Login

When you first access the UI, you'll see:

1. **Empty DAGs page** - No DAGs appear because example DAGs are disabled (`AIRFLOW__CORE__LOAD_EXAMPLES=False`)
2. **Airflow 3.1.3** version displayed in the footer
3. **UTC timezone** - All times are displayed in UTC by default

## Basic Navigation

- **DAGs** - Main page showing all your DAGs with status and controls
- **Browse** - Access to task instances, jobs, and logs
- **Admin** - Connections, variables, and other configurations
- **Docs** - Links to Airflow documentation

### Useful Actions

- Toggle DAG on/off with the slider
- Click DAG name to see task dependencies graph
- Trigger manual runs with the play button
- View logs by clicking on individual task instances

## Troubleshooting

### UI Not Loading

**Check services are running:**
```bash
docker compose ps
```

All services should show status `running` or `healthy`.

**Check webserver logs:**
```bash
docker compose logs airflow-webserver
```

### Port Already in Use

If port 8080 is occupied:

1. Find the process using the port:
```bash
lsof -i :8080
```

2. Either stop that process or modify `docker-compose.yml` to use a different port:
```yaml
airflow-webserver:
  ports:
    - "8081:8080"  # Use port 8081 instead
```

### Slow Startup

First startup takes longer because:
- Database migrations run
- Admin user is created
- Initial health checks complete

Wait 1-2 minutes after `docker compose up -d` before accessing the UI. Check progress with:
```bash
docker compose logs airflow-init
```

Look for: `Airflow initialized!`

### Login Fails

1. Verify credentials in `.env` file
2. Ensure `.env` was present before first `docker compose up`
3. If credentials were changed after first run, recreate volumes:
```bash
docker compose down -v
docker compose up -d
```

### Database Connection Errors

Check PostgreSQL is healthy:
```bash
docker compose exec postgres pg_isready
```

## Security Notes

**For production deployments:**

1. Change default admin password in `.env`
2. Generate a new Fernet key:
```bash
./venv/bin/python3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```
3. Consider enabling HTTPS via reverse proxy
4. Restrict network access to the webserver port

For this portfolio project, default credentials are acceptable for local development.

## Configuring API Connections

The weather pipeline needs access to the OpenWeatherMap API. You can configure this via script or manually through the UI.

### Option 1: Using the Setup Script (Recommended)

1. Ensure your `.env` file has a valid `OPENWEATHER_API_KEY`

2. Run the setup script inside the Airflow scheduler container:
```bash
docker compose exec airflow-scheduler python /opt/airflow/scripts/setup_connections.py
```

This creates:
- **Connection:** `openweathermap_api` - HTTP connection to api.openweathermap.org
- **Connection:** `weather_postgres` - PostgreSQL connection for weather data
- **Variable:** `weather_api_base_url` - Base URL for API endpoints
- **Variable:** `weather_api_rate_limit` - Maximum calls per minute

### Option 2: Manual Setup via UI

#### Create the OpenWeatherMap Connection

1. Go to **Admin > Connections**
2. Click **+** to add a new connection
3. Fill in the fields:
   - **Connection Id:** `openweathermap_api`
   - **Connection Type:** HTTP
   - **Host:** `api.openweathermap.org`
   - **Schema:** `https`
   - **Extra:** `{"api_key": "YOUR_API_KEY_HERE"}`
4. Click **Save**

#### Create the PostgreSQL Connection

1. Go to **Admin > Connections**
2. Click **+** to add a new connection
3. Fill in the fields:
   - **Connection Id:** `weather_postgres`
   - **Connection Type:** Postgres
   - **Host:** `postgres`
   - **Schema:** `weather_data`
   - **Login:** `weather_user`
   - **Password:** Your `WEATHER_DB_PASSWORD` from `.env`
   - **Port:** `5432`
4. Click **Save**

**Note:** This connection is for the weather data database, not the Airflow metadata database. The host is `postgres` because that's the Docker service name within the container network.

#### Create Variables

1. Go to **Admin > Variables**
2. Click **+** to add each variable:

| Key                      | Value                                     |
| ------------------------ | ----------------------------------------- |
| `weather_api_base_url`   | `https://api.openweathermap.org/data/2.5` |
| `weather_api_rate_limit` | `60`                                      |

### Verifying the Setup

After configuration, verify in Airflow UI:
- **Admin > Connections** - Should show `openweathermap_api` and `weather_postgres`
- **Admin > Variables** - Should show `weather_api_base_url` and `weather_api_rate_limit`

You can also test from the CLI:
```bash
docker compose exec airflow-scheduler airflow connections get openweathermap_api
docker compose exec airflow-scheduler airflow connections get weather_postgres
docker compose exec airflow-scheduler airflow variables get weather_api_base_url
```

To test the PostgreSQL connection works:
```bash
docker compose exec airflow-scheduler airflow connections test weather_postgres
```

## Testing the Database Initialization DAG

The `db_init` DAG creates the database schema and populates initial locations.

### Trigger the DAG

```bash
docker compose exec airflow-scheduler airflow dags trigger db_init
```

### Check Run Status

```bash
docker compose exec airflow-scheduler airflow dags list-runs db_init
```

Expected output shows `state = success`.

### Verify Database Tables

```bash
docker compose exec postgres psql -U weather_user -d weather_data -c "SELECT table_name FROM information_schema.tables WHERE table_schema='public';"
```

Expected tables: `locations`, `weather_observations`, `weather_forecasts`

### Verify Locations

```bash
docker compose exec postgres psql -U weather_user -d weather_data -c "SELECT id, city_name, country_code FROM locations;"
```

Expected: 5 Brazilian cities (Campinas, São Paulo, São Luís, Guarapari, Ubatuba)

## Configuring Email Alerts (Optional)

The DAG is configured to send email notifications on task failures. To enable email alerts, you need to configure SMTP settings.

### Setting Up Email Alerts

1. **Add SMTP configuration to your `.env` file:**

The `.env.example` file includes SMTP configuration templates. Copy these settings to your `.env` file and update with your credentials:

```bash
AIRFLOW__SMTP__SMTP_HOST=smtp.gmail.com
AIRFLOW__SMTP__SMTP_STARTTLS=True
AIRFLOW__SMTP__SMTP_SSL=False
AIRFLOW__SMTP__SMTP_PORT=587
AIRFLOW__SMTP__SMTP_MAIL_FROM=your-email@example.com
AIRFLOW__SMTP__SMTP_USER=your-email@example.com
AIRFLOW__SMTP__SMTP_PASSWORD=your_app_password_here
AIRFLOW_CONN_SMTP_DEFAULT=smtp://USERNAME:PASSWORD@HOST:PORT?secure=starttls # for gmail, use app_password
```

2. **For Gmail users:**
   - Enable 2-factor authentication on your Google account
   - Generate an App Password: https://myaccount.google.com/apppasswords
   - Use the App Password (not your regular password) in `SMTP_PASSWORD`

3. **Restart Airflow services:**

```bash
docker compose down
docker compose up -d
```

### Email Configuration Details

The weather pipeline DAG includes:
- **email_on_failure:** True - Sends email when tasks fail
- **email_on_retry:** False - Does not send email on retries (reduces noise)
- **email recipients:** Configured in DAG default_args

### Without Email Configuration

If you don't configure SMTP, the pipeline will still work normally. Failed tasks will:
- Log errors via the `on_failure_callback` function
- Show failure status in the Airflow UI
- Not send email notifications

The failure logging callback provides visibility without requiring email setup.

### Testing Email Alerts

To test email notifications:

1. Temporarily modify a task to fail (e.g., raise an exception)
2. Trigger the DAG
3. Check your email inbox for failure notification
4. Check Airflow logs for the custom failure callback output

### Retry Policies

The DAG includes different retry strategies for different task types:

- **Extract tasks:** 5 retries with 3-minute initial delay (API calls may have transient failures)
- **Transform tasks:** 2 retries with 2-minute delay, no exponential backoff
- **Default (other tasks):** 3 retries with 5-minute initial delay, exponential backoff up to 30 minutes

Exponential backoff doubles the wait time after each retry, helping handle temporary service disruptions.
