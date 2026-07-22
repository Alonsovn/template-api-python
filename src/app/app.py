import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from starlette.middleware.base import BaseHTTPMiddleware

from src.app.config.app_config import AppConfig
from src.app.shared.infrastructure.middleware.request_logging_middleware import (
    request_logging_middleware,
)
from src.app.shared.infrastructure.rate_limit.rate_limiter import limiter
from src.app.shared.logging.logging import initialize_logging
from src.app.shared.presentation.exception_handlers import register_exception_handlers
from src.app.shared.presentation.health_checks import register_health_endpoints
from src.app.shared.presentation.router_registry import register_routers

# ── Config ────────────────────────────────────────────────────────
config = AppConfig.instance()
app_name = config.get_config("app.name", "API")
app_version = config.get_config("app.version", "1.0.0")
ENV = os.getenv("APP_ENV", "local")

# Setup logging
initialize_logging(
    level=config.get_config("logging.level", "INFO"),
    format_type=config.get_config("logging.format", "json"),
)

# ── App ───────────────────────────────────────────────────────────
fastapi_app = FastAPI(title=app_name, version=app_version)

# Disable docs in non-local/non-test envs
if ENV not in ("local", "test"):
    fastapi_app.docs_url = None
    fastapi_app.redoc_url = None
    fastapi_app.openapi_url = None

# ── CORS ──────────────────────────────────────────────────────────
cors_origins = config.get_config(
    "security.cors_origins", ["http://localhost:5173", "http://localhost:*"]
)
fastapi_app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Shared middleware & handlers ──────────────────────────────────
# Rate limiting via slowapi
fastapi_app.state.limiter = limiter
fastapi_app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
fastapi_app.add_middleware(SlowAPIMiddleware)

# Request logging
fastapi_app.add_middleware(
    BaseHTTPMiddleware,
    dispatch=request_logging_middleware,
)

# Register exception handlers (404, 409, 422, 429, 500, etc.)
register_exception_handlers(fastapi_app)

# ── Routes ────────────────────────────────────────────────────────
register_routers(fastapi_app)

# ── Health ────────────────────────────────────────────────────────
register_health_endpoints(fastapi_app)


@fastapi_app.get("/")
async def read_root():
    return {"message": "Welcome to the API"}
