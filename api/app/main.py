"""
Orbital API - Main application entry point.
"""

import logging
import os
import sys
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routers import artifacts, chat, config, datasets, models, session_datasets, session_events, sessions

# Configure logging
log_level = os.getenv("LOG_LEVEL", "INFO").upper()
logging.basicConfig(
    level=getattr(logging, log_level, logging.INFO),
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    datefmt="%H:%M:%S",
    stream=sys.stdout,
)

# Reduce noise from httpx/httpcore
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown logic."""
    # Startup
    logger.info("Initializing Orbital API...")

    # Ensure prebuilt datasets exist with table discovery
    try:
        from app.config import get_settings
        from app.storage.dataset_storage import DatasetStorage

        settings = get_settings()
        dataset_storage = DatasetStorage(database_url=settings.database_url)
        dataset_storage.initialize()

        # Bootstrap prebuilt datasets (discovers tables from PostgreSQL)
        dataset_storage.ensure_prebuilt_datasets()
        logger.info("Prebuilt datasets initialized")
    except Exception as e:
        # Don't crash the app if bootstrap fails
        logger.warning(f"Failed to initialize prebuilt datasets: {e}")

    yield

    # Shutdown
    logger.info("Shutting down Orbital API...")


app = FastAPI(
    title="Orbital API",
    description="AI-powered exploratory data analysis agent",
    version="0.1.0",
    lifespan=lifespan,
)

# CORS configuration
_default_allowed_origins = [
    "http://localhost:3737",  # matches pm2 dev script
    "http://localhost:3000",  # matches `npm run dev` default
]
env_origins = os.getenv("ALLOWED_ORIGINS")
if env_origins:
    allowed_origins = [origin.strip() for origin in env_origins.split(",") if origin.strip()]
else:
    allowed_origins = _default_allowed_origins

# Support wildcard patterns for Vercel preview deploys (e.g. ".*\.vercel\.app")
origin_pattern = os.getenv("ALLOWED_ORIGIN_PATTERN")
allow_origin_regex = f"https://{origin_pattern}" if origin_pattern else None

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_origin_regex=allow_origin_regex,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(chat.router)
app.include_router(sessions.router)
app.include_router(models.router)
app.include_router(datasets.router)
app.include_router(session_datasets.router)
app.include_router(session_events.router)
app.include_router(artifacts.router)
app.include_router(config.router)


# --- Exception Handlers ---
from fastapi import Request
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException


@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    """Normalize HTTPException to {"error": "..."} format."""
    detail = exc.detail
    if isinstance(detail, dict) and "error" in detail:
        detail = detail["error"]
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": detail},
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Normalize Pydantic 422 errors to {"error": "..."} format."""
    errors = exc.errors()
    first = errors[0]
    field = ".".join(str(loc) for loc in first["loc"] if loc != "body")
    return JSONResponse(
        status_code=422,
        content={"error": f"{field}: {first['msg']}"},
    )


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "ok"}
