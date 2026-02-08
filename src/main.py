"""
Research Accountability & Mastery Platform (RAMP)

FastAPI application entry point.
"""

from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError

from src.config import get_settings
from src.database import init_db, close_db
from src.api.v1 import router as api_v1_router
from src.api.middleware.rate_limit import RateLimitMiddleware
from src.schemas.common import HealthResponse

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator:
    """
    Application lifespan handler.
    
    Runs startup and shutdown tasks.
    """
    # Startup
    print(f"Starting {settings.project_name} v{settings.version}")
    await init_db()
    print("Database initialized")
    
    yield
    
    # Shutdown
    print("Shutting down...")
    await close_db()
    print("Database connections closed")


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


# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"] if settings.debug else ["https://ramp.example.com"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# API Gateway rate limiting (per user / per IP)
app.add_middleware(RateLimitMiddleware)


# Exception handlers
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
    
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "detail": "Validation error",
            "errors": errors,
        },
    )


@app.exception_handler(Exception)
async def general_exception_handler(
    request: Request,
    exc: Exception,
):
    """Handle unexpected exceptions."""
    if settings.debug:
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "detail": str(exc),
                "type": type(exc).__name__,
            },
        )
    else:
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"detail": "Internal server error"},
        )


# Health check endpoint
@app.get("/health", response_model=HealthResponse, tags=["Health"])
async def health_check():
    """Check application health."""
    return HealthResponse(
        status="ok",
        version=settings.version,
        database="connected",
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
