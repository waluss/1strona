import logging
from fastapi import FastAPI, Response
from fastapi.middleware.cors import CORSMiddleware
from prometheus_client import Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST
from alembic.config import Config
from alembic import command

from app.core.config import settings
from app.db.session import engine, SessionLocal
from app.core.bootstrap import bootstrap_initial_data
from app.api import auth, tenants, profiles, imports, tenders

logger = logging.getLogger(__name__)

IMPORT_REQUESTS = Counter("tenderplatform_import_requests_total", "Total import requests executed")
SCORING_REQUESTS = Counter("tenderplatform_scoring_requests_total", "Total tender scoring executions")

app = FastAPI(
    title=settings.PROJECT_NAME,
    openapi_url=f"{settings.API_V1_STR}/openapi.json"
)

# CORS setup for both reverse-proxied and direct cross-origin dev ports
app.add_middleware(
    CORSMiddleware,
    allow_origin_regex=r"http://(localhost|127\.0\.0\.1)(:[0-9]+)?",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
def startup_event():
    try:
        logger.info("Running database migrations via Alembic...")
        alembic_cfg = Config("alembic.ini")
        command.upgrade(alembic_cfg, "head")
        logger.info("Database migrations completed.")
    except Exception as e:
        logger.error(f"Error running database migrations: {e}")

    with SessionLocal() as db:
        try:
            bootstrap_initial_data(db)
        except Exception as e:
            logger.error(f"Error during bootstrap: {e}")

@app.get("/metrics")
def metrics():
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)

app.include_router(auth.router, prefix=f"{settings.API_V1_STR}/auth", tags=["auth"])
app.include_router(tenants.router, prefix=f"{settings.API_V1_STR}/tenants", tags=["tenants"])
app.include_router(profiles.router, prefix=f"{settings.API_V1_STR}/profiles", tags=["profiles"])
app.include_router(imports.router, prefix=f"{settings.API_V1_STR}/imports", tags=["imports"])
app.include_router(tenders.router, prefix=f"{settings.API_V1_STR}/tenders", tags=["tenders"])
