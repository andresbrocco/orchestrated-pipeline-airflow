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
