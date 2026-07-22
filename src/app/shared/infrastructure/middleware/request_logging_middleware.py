"""
Request logging middleware with correlation ID and user identification support.

Logs every HTTP request with method, path, status, latency, correlation ID, and authenticated user.
"""

import time
import uuid
from collections.abc import Callable

from fastapi import Request, Response

from src.app.shared.logging.logging import (
    get_logger,
    set_request_id,
    set_user_id,
    clear_context,
)


log = get_logger(__name__)


async def request_logging_middleware(request: Request, call_next: Callable) -> Response:
    """Log every HTTP request with a correlation ID and authenticated user info.

    Generates a per-request correlation ID and sets it on the logging context
    so all log lines emitted during this request are correlated.  User context
    is set from ``request.state.user_id`` if available (set by auth middleware).
    """
    request_id = str(uuid.uuid4())
    set_request_id(request_id)

    start_time = time.time()

    try:
        response = await call_next(request)
    finally:
        # Clear the context to avoid leaking correlation IDs across requests.
        clear_context()

    # Calculate latency
    latency_ms = (time.time() - start_time) * 1000

    # Extract user_id from request state if authentication middleware set it
    user_id = getattr(request.state, "user_id", None) or "anonymous"
    set_user_id(user_id if user_id != "anonymous" else None)

    # Log request details with structured fields
    log.info(
        "HTTP request processed",
        extra={
            "request_id": request_id,
            "method": request.method,
            "path": request.url.path,
            "status_code": response.status_code,
            "latency_ms": round(latency_ms, 2),
            "client_host": request.client.host if request.client else None,
            "user_id": user_id,
        },
    )

    return response
