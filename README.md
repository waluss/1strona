# TenderPlatform

TenderPlatform is a multi-tenant SaaS platform for aggregating, storing, analyzing, and scoring Polish public procurement notices from the official BZP / e-Zamówienia API.

## Features

- **Official BZP Integration**: Live and cursor-based BZP/e-Zamówienia notice ingestion with automatic rate limiting and backoff.
- **Deduplication & Revision History**: Automatic notice payload canonical SHA256 hashing, tender proceeding view mapping, and historical revision tracking.
- **Read-Only Dry-Run Studio**: Safe simulation mode to evaluate notice ingestion actions without database mutation.
- **Company-Neutral Scoring Engine**: Dynamic tender scoring matching contractor profiles against CPV codes, keywords, regions, and exclusions with clear decision explanations.
- **Multi-Tenant & Role-Based Access Control**: Strict tenant data isolation, JWT authentication, and forced default password change.
- **Vanilla JS Frontend**: Clean, responsive frontend application with strict XSS sanitization (`escapeHtml`).
- **Observability**: Prometheus `/metrics` endpoint and Grafana service integrations.

## Tech Stack

- **Backend**: Python 3.12, FastAPI, Pydantic v2, SQLAlchemy 2.0, Alembic, PostgreSQL, httpx, pytest
- **Frontend**: Vanilla JavaScript (ES Modules), Pure CSS, HTML5
- **Operations**: Docker Compose, Prometheus, Grafana

## Quick Start (Development)

1. **Environment Configuration**:
   Ensure Docker Compose is installed on your system.

2. **Start Services**:
   ```bash
   docker-compose up --build
   ```

3. **Access Services**:
   - **Frontend UI**: `http://localhost:8085`
   - **FastAPI API Docs**: `http://localhost:8005/docs`
   - **Prometheus**: `http://localhost:9095`
   - **Grafana**: `http://localhost:3005`

4. **Default Admin Login**:
   - **Username**: `admin`
   - **Initial Password**: `admin` (You will be prompted to change password on first login)

## Running Automated Tests

To run the offline pytest suite:

```bash
cd backend
PYTHONPATH=. pytest
```
