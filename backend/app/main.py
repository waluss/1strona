import logging
from fastapi import FastAPI, Response
from fastapi.middleware.cors import CORSMiddleware
from prometheus_client import Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST

from app.core.config import settings
from app.db.session import engine, SessionLocal
from app.core.bootstrap import bootstrap_initial_data
from app.api import auth, tenants, profiles, imports, tenders

logger = logging.getLogger(__name__)

# Prometheus metrics
IMPORT_REQUESTS = Counter("tenderflow_import_requests_total", "Total import requests executed")
SCORING_REQUESTS = Counter("tenderflow_scoring_requests_total", "Total tender scoring executions")

app = FastAPI(
    title=settings.PROJECT_NAME,
    openapi_url=f"{settings.API_V1_STR}/openapi.json"
)

# CORS setup
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
def startup_event():
    with SessionLocal() as db:
        try:
            bootstrap_initial_data(db)
        except Exception as e:
            logger.error(f"Error during bootstrap: {e}")

@app.get("/metrics")
def metrics():
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)

# Router includes
app.include_router(auth.router, prefix=f"{settings.API_V1_STR}/auth", tags=["auth"])
app.include_router(tenants.router, prefix=f"{settings.API_V1_STR}/tenants", tags=["tenants"])
app.include_router(profiles.router, prefix=f"{settings.API_V1_STR}/profiles", tags=["profiles"])
app.include_router(imports.router, prefix=f"{settings.API_V1_STR}/imports", tags=["imports"])
app.include_router(tenders.router, prefix=f"{settings.API_V1_STR}/tenders", tags=["tenders"])
