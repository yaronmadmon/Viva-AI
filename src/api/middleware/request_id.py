"""
Request ID middleware for request correlation.

- Generates or accepts X-Request-ID header
- Stores in request.state and response headers
- Sets context var so request_id is available in logs throughout the request
"""

import time
import uuid
from typing import Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from src.logging_config import get_logger, request_id_var

logger = get_logger(__name__)

REQUEST_ID_HEADER = "X-Request-ID"


class RequestIdMiddleware(BaseHTTPMiddleware):
    """
    Assign a unique request ID to each request for correlation across logs.

    - Accepts X-Request-ID from client if present (for distributed tracing)
    - Otherwise generates a new UUID
    - Adds X-Request-ID to response headers
    - Sets context var for use in logging
    """

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Use incoming header or generate new ID
        incoming = request.headers.get(REQUEST_ID_HEADER)
        request_id = incoming if incoming else str(uuid.uuid4())

        # Store for handlers
        request.state.request_id = request_id

        # Set context var so logs include it automatically
        token = request_id_var.set(request_id)

        try:
            start = time.perf_counter()
            response = await call_next(request)
            duration_ms = (time.perf_counter() - start) * 1000

            # Add to response
            response.headers[REQUEST_ID_HEADER] = request_id

            # Log slow requests
            if duration_ms > 1000:
                logger.warning(
                    "Slow request",
                    extra={
                        "path": request.url.path,
                        "method": request.method,
                        "duration_ms": round(duration_ms, 1),
                    },
                )

            return response
        finally:
            request_id_var.reset(token)
