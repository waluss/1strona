# TenderPlatform

TenderPlatform is a multi-tenant SaaS platform for aggregating, storing, analyzing, and scoring Polish public procurement notices from the official BZP / e-Zamówienia API.

## Tech Stack

- **Backend**: Python 3.12, FastAPI, Pydantic v2, SQLAlchemy 2.0, Alembic, PostgreSQL, httpx, pytest
- **Frontend**: Vanilla JavaScript (ES Modules), Pure CSS, HTML5
- **Operations**: Docker Compose, Prometheus, Grafana

---

## Complete Step-by-Step Setup Guide

Follow these exact steps to set up and run TenderPlatform on your machine without port or container name conflicts.

### Step 1: Clean Up Old Containers and Networks

Run the following commands in your terminal to stop any conflicting containers or old versions:

```bash
# Stop and remove any existing TenderPlatform/TenderFlow containers
docker-compose down --remove-orphans
```

If you have old isolated containers running:
```bash
docker rm -f tenderflow-prometheus tenderplatform-prometheus tenderflow-backend tenderplatform-backend 2>/dev/null || true
```

### Step 2: Environment Configuration (`.env`)

Copy `.env.example` to `.env` if `.env` does not already exist:

```bash
cp .env.example .env
```

The default `.env` file uses non-conflicting host ports:
```ini
COMPOSE_PROJECT_NAME=tenderplatform_v2

DB_PORT=5433
BACKEND_PORT=8005
FRONTEND_PORT=8085
PROMETHEUS_PORT=9095
GRAFANA_PORT=3005

SECRET_KEY=dev_secret_key_change_in_production
INITIAL_ADMIN_PASSWORD=admin
ENVIRONMENT=local
IMPORT_DRY_RUN_ENABLED=true
```

*(You can edit `.env` to change any port numbers if `8085` or `8005` are already in use on your PC).*

### Step 3: Build and Launch Docker Compose Stack

Run the following command from the root directory:

```bash
docker-compose up --build -d
```

Check that all containers are healthy:
```bash
docker-compose ps
```

### Step 4: Access the Application

Open your browser and navigate to:

- **Frontend Application UI**: [http://localhost:8085](http://localhost:8085)
- **FastAPI Backend API Docs**: [http://localhost:8005/docs](http://localhost:8005/docs)
- **Prometheus Metrics**: [http://localhost:9095](http://localhost:9095)
- **Grafana Dashboard**: [http://localhost:3005](http://localhost:3005)

### Step 5: Initial Admin Login & Password Change

1. On the Frontend UI ([http://localhost:8085](http://localhost:8085)), log in with:
   - **Username**: `admin`
   - **Password**: `admin`
2. You will be prompted to perform a mandatory first-login password change. Enter your current password (`admin`) and set your new secure password.
3. Upon changing your password, you will be directed to the TenderPlatform dashboard.

---

## Running Automated Tests Locally

To run the backend test suite:

```bash
cd backend
PYTHONPATH=. python3 -m pytest tests/
```
