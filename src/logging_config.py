"""
Central logging configuration for the RAMP platform.

Provides:
- Structured logging (JSON in production, human-readable in development)
- Request correlation via contextvars (request_id set by middleware)
- Environment-aware log levels

Usage:
    from src.logging_config import get_logger
    logger = get_logger(__name__)
    logger.info("Processing artifact", extra={"artifact_id": str(aid)})
"""

import json
import logging
import sys
from contextvars import ContextVar
from datetime import datetime, timezone
from typing import Any, Optional

# Context var for request ID - set by middleware, available throughout request scope
request_id_var: ContextVar[Optional[str]] = ContextVar("request_id", default=None)


def get_request_id() -> Optional[str]:
    """Get the current request ID from context, if set."""
    return request_id_var.get()


class RequestIdFilter(logging.Filter):
    """Filter that adds request_id to log records from context."""

    def filter(self, record: logging.LogRecord) -> bool:
        record.request_id = get_request_id() or "-"  # type: ignore[attr-defined]
        return True


class JsonFormatter(logging.Formatter):
    """Format log records as JSON for production log aggregators."""

    def format(self, record: logging.LogRecord) -> str:
        log_obj: dict[str, Any] = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        # Add request_id when present
        req_id = getattr(record, "request_id", None)
        if req_id and req_id != "-":
            log_obj["request_id"] = req_id

        # Include exception info if present
        if record.exc_info:
            log_obj["exception"] = self.formatException(record.exc_info)

        # Add extra fields (anything passed via extra= in the log call)
        for key, value in record.__dict__.items():
            if key not in (
                "name", "msg", "args", "created", "filename", "funcName",
                "levelname", "levelno", "lineno", "module", "msecs",
                "pathname", "process", "processName", "relativeCreated",
                "stack_info", "exc_info", "exc_text", "thread", "threadName",
                "message", "taskName", "request_id",
            ) and value is not None:
                # Ensure JSON-serializable
                try:
                    json.dumps(value)
                    log_obj[key] = value
                except (TypeError, ValueError):
                    log_obj[key] = str(value)

        return json.dumps(log_obj)


def _create_dev_formatter() -> logging.Formatter:
    return logging.Formatter(
        "%(asctime)s %(levelname)-5s [%(name)s] req=%(request_id)s %(message)s",
        datefmt="%H:%M:%S",
    )


def configure_logging(
    *,
    log_level: str = "INFO",
    environment: str = "development",
    debug: bool = False,
) -> None:
    """
    Configure application-wide logging.

    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR)
        environment: 'development' or 'production'
        debug: If True, use DEBUG level regardless of log_level
    """
    level = logging.DEBUG if debug else getattr(logging, log_level.upper(), logging.INFO)

    # Ensure request_id exists on all records (default before filter runs)
    logging.Logger.manager.loggerDict  # Ensure default manager exists
    old_factory = logging.getLogRecordFactory()

    def record_factory(*args: Any, **kwargs: Any) -> logging.LogRecord:
        record = old_factory(*args, **kwargs)
        if not hasattr(record, "request_id"):
            setattr(record, "request_id", "-")
        return record

    logging.setLogRecordFactory(record_factory)

    # Root logger
    root = logging.getLogger()
    root.setLevel(level)

    # Remove existing handlers to avoid duplicates on reload
    for h in root.handlers[:]:
        root.removeHandler(h)

    handler = logging.StreamHandler(sys.stderr)
    handler.setLevel(level)

    # Add filter to inject request_id
    handler.addFilter(RequestIdFilter())

    if environment == "production":
        handler.setFormatter(JsonFormatter())
    else:
        handler.setFormatter(_create_dev_formatter())

    root.addHandler(handler)

    # Reduce noise from third-party loggers
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger for the given module name.

    Logs will automatically include request_id when available (set by middleware).
    Use extra={} for additional structured fields:
        logger.info("Processing", extra={"artifact_id": str(aid), "user_id": str(uid)})
    """
    return logging.getLogger(name)
