"""
Research Accountability & Mastery Platform (RAMP)

FastAPI application entry point.
"""

from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI, HTTPException, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError

from src.config import get_settings
from src.database import init_db, close_db
from src.api.v1 import router as api_v1_router
from src.api.middleware.rate_limit import RateLimitMiddleware
from src.api.middleware.request_id import RequestIdMiddleware
from src.schemas.common import HealthResponse
from src.logging_config import configure_logging, get_logger

settings = get_settings()
logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator:
    """
    Application lifespan handler.
    
    Runs startup and shutdown tasks.
    """
    # Configure logging first
    configure_logging(
        log_level=settings.log_level,
        environment=settings.environment,
        debug=settings.debug,
    )

    # Startup
    logger.info("Starting %s v%s", settings.project_name, settings.version)
    await init_db()
    logger.info("Database initialized")

    yield

    # Shutdown
    logger.info("Shutting down...")
    await close_db()
    logger.info("Database connections closed")


# Create FastAPI application
app = FastAPI(
    title=settings.project_name,
    description="""
    Research Accountability & Mastery Platform (RAMP)
    
    A platform for research integrity with AI accountability.
    
    ## Features
    
    - **Research Projects**: Create and manage research projects with artifact graphs
    - **Artifacts**: Claims, evidence, sources with version history and linking
    - **Collaboration**: Share projects, comment threads, advisor reviews
    - **AI Assistance**: Progressive AI disclosure with integrity tracking
    - **Mastery Checkpoints**: Tiered comprehension and defense readiness
    - **Export**: DOCX generation with integrity certificates
    
    ## Architectural Invariants
    
    1. AI Isolation: AI outputs never enter trusted zone without validation
    2. Append-Only Audit: All mutations logged before commit
    3. Human-in-the-Loop: AI suggestions require explicit acceptance
    4. Modification Threshold: Verbatim AI blocks export
    5. Progressive Disclosure: AI unlocked after demonstrated mastery
    """,
    version=settings.version,
    lifespan=lifespan,
    docs_url="/docs" if settings.debug else None,
    redoc_url="/redoc" if settings.debug else None,
)


# Middleware order: add_middleware stacks innermost-first, so LAST added = OUTERMOST.
# CORS must be outermost so it adds headers to ALL responses (including 429, errors from
# rate limit, etc.). Otherwise responses from inner middleware bypass CORS.
_cors_origins = [
    "http://localhost:3000",
    "http://localhost:3001",
    "http://localhost:5173",  # Vite default
    "http://127.0.0.1:3000",
    "http://127.0.0.1:3001",
]
if not (settings.debug or settings.environment == "development"):
    _cors_origins = ["https://ramp.example.com"] + _cors_origins

# Add these first (they become inner middleware)
app.add_middleware(RateLimitMiddleware)
app.add_middleware(RequestIdMiddleware)

# CORS last = outermost = wraps everything; every response gets CORS headers
app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def _cors_headers(request: Request) -> dict:
    """Return CORS headers for error responses so browser receives them (500s often bypass CORS middleware)."""
    origin = request.headers.get("origin") or ""
    allow_origin = origin if origin in _cors_origins else _cors_origins[0]
    return {
        "Access-Control-Allow-Origin": allow_origin,
        "Access-Control-Allow-Credentials": "true",
        "Access-Control-Allow-Methods": "*",
        "Access-Control-Allow-Headers": "*",
    }


# Exception handlers (include CORS headers so 4xx/5xx responses are not blocked by browser)
@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """Ensure 401/403/404 etc. responses have CORS headers."""
    headers = _cors_headers(request)
    req_id = getattr(request.state, "request_id", None)
    if req_id:
        headers["X-Request-ID"] = req_id
    content = {"detail": exc.detail} if isinstance(exc.detail, str) else {"detail": exc.detail}
    if req_id and exc.status_code >= 500:
        content["request_id"] = req_id
    return JSONResponse(status_code=exc.status_code, content=content, headers=headers)


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(
    request: Request,
    exc: RequestValidationError,
):
    """Handle request validation errors."""
    errors = []
    for error in exc.errors():
        field = ".".join(str(loc) for loc in error["loc"])
        errors.append({
            "field": field,
            "message": error["msg"],
            "type": error["type"],
        })
    headers = _cors_headers(request)
    req_id = getattr(request.state, "request_id", None)
    if req_id:
        headers["X-Request-ID"] = req_id
    content = {"detail": "Validation error", "errors": errors}
    if req_id:
        content["request_id"] = req_id
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content=content,
        headers=headers,
    )


@app.exception_handler(Exception)
async def general_exception_handler(
    request: Request,
    exc: Exception,
):
    """Handle unexpected exceptions. CORS headers added so browser does not hide 500 behind CORS error."""
    logger.exception("Unhandled exception: %s", exc)
    headers = _cors_headers(request)
    req_id = getattr(request.state, "request_id", None)
    if req_id:
        headers["X-Request-ID"] = req_id
    if settings.debug:
        content = {
            "detail": str(exc),
            "type": type(exc).__name__,
            "request_id": req_id,
        }
    else:
        content = {"detail": "Internal server error", "request_id": req_id}
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=content,
        headers=headers,
    )


# Health check endpoint
@app.get("/health", response_model=HealthResponse, tags=["Health"])
async def health_check():
    """Check application health."""
    key = (settings.openai_api_key or "").strip()
    ai_configured = bool(
        key
        and not key.startswith("sk-your-")
        and key != "sk-your-openai-api-key"
    )
    return HealthResponse(
        status="ok",
        version=settings.version,
        database="connected",
        ai_configured=ai_configured,
    )


# Root endpoint
@app.get("/", tags=["Root"])
async def root():
    """Root endpoint with API information."""
    return {
        "name": settings.project_name,
        "version": settings.version,
        "docs": "/docs" if settings.debug else "disabled",
        "api": {
            "v1": "/api/v1",
        },
    }


# Mount API v1 routes
app.include_router(
    api_v1_router,
    prefix=settings.api_v1_prefix,
)


# Main entry point for development
if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "src.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.debug,
    )
