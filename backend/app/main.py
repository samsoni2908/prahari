import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from app.api.health import router as health_router
from app.api.auth import router as auth_router
from app.api.commander import router as commander_router
from app.api.personnel import router as personnel_router
from app.api.welfare import router as welfare_router
from app.api.admin import router as admin_router
from app.api.units import router as units_router
from app.api.operational_detection import router as operational_detection_router
from app.api.notifications import router as notifications_router
from app.api.alerts import router as alerts_router
from app.api.errors import install_errors, envelope
from app.api.ingestion import router as ingestion_router
from app.api.master_data import router as master_data_router
from app.config import settings

# Configure logging
logging.basicConfig(
    level=logging.INFO if not settings.DEBUG else logging.DEBUG,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("prahari")
# HTTP transport debug records can include authentication response cookies.
# Suppress third-party HTTP traces even when local application DEBUG is enabled.
logging.getLogger("httpcore").setLevel(logging.WARNING)
logging.getLogger("httpx").setLevel(logging.WARNING)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("PRAHARI API starting up in %s environment...", settings.ENVIRONMENT)
    from sqlalchemy import create_engine
    from app.analytics.operational_scheduler import OperationalScheduler
    detection_engine = create_engine(settings.DATABASE_URL_SYNC, hide_parameters=True, pool_pre_ping=True)
    scheduler = OperationalScheduler(detection_engine)
    scheduler.start()
    app.state.operational_scheduler = scheduler
    try:
        yield
    finally:
        scheduler.stop()
        detection_engine.dispose()
        logger.info("PRAHARI API shutting down...")


app = FastAPI(
    title=settings.PROJECT_NAME,
    description="AI-Powered Personnel Stress and Welfare Monitoring System (SIH 26186)",
    version="1.0.0-PROTOTYPE",
    debug=False,
    lifespan=lifespan,
)
install_errors(app)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PATCH", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "X-CSRF-Token", "Idempotency-Key"],
)

# Mount health endpoints at root as required by Phase 0 specification
app.include_router(health_router)

# Mount v1 feature routers (Strictly 4 locked roles)
app.include_router(auth_router)
app.include_router(commander_router)
app.include_router(personnel_router)
app.include_router(welfare_router)
app.include_router(admin_router)
app.include_router(units_router)
app.include_router(operational_detection_router)
app.include_router(notifications_router)
app.include_router(alerts_router)
app.include_router(ingestion_router)
app.include_router(master_data_router)


@app.exception_handler(Exception)
async def unexpected_error(request, exception):
    logger.error("Request failed: %s", type(exception).__name__)
    return JSONResponse(status_code=500, content=envelope(request, 500))


@app.get("/")
async def root():
    return {
        "project": settings.PROJECT_NAME,
        "purpose": "Personnel Stress and Welfare Monitoring System",
        "challenge": "SIH 26186",
        "status": "Phase 0 Engineering Foundation",
        "docs_url": "/docs",
        "health_url": "/health",
        "ready_url": "/ready",
    }
