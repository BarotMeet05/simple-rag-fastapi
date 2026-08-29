# app/core/logging.py
"""
Structured Logging Setup
========================
WHY structured logging?
-----------------------
In a terminal during development, human-readable logs are fine:
    INFO:     document abc123 uploaded

But in production (CloudWatch, Datadog, ELK), you need logs you can query:
    {"timestamp": "2024-01-15T10:23:45Z", "level": "INFO",
     "event": "document_uploaded", "document_id": "abc123", "latency_ms": 42}

Structured logging means emitting logs as key-value pairs (usually JSON) so
that log aggregation systems can index and query them efficiently.

In later phases we'll add request_id, document_id, and latency fields to every
log line automatically using middleware.

For Phase 1, we set up Python's standard logging with a clean formatter.
We keep it simple — no third-party library yet.
"""

import logging
import sys


def setup_logging(log_level: str = "INFO") -> None:
    """
    Configure the root logger for the application.

    This is called once at application startup in main.py.
    All modules then use logging.getLogger(__name__) to get a child logger
    that inherits this configuration.

    Args:
        log_level: One of DEBUG, INFO, WARNING, ERROR, CRITICAL
    """
    numeric_level = getattr(logging, log_level.upper(), logging.INFO)

    # -------------------------------------------------------------------------
    # Handler — where do log records go?
    # StreamHandler sends them to stdout (which Docker/Kubernetes captures)
    # -------------------------------------------------------------------------
    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(numeric_level)

    # -------------------------------------------------------------------------
    # Formatter — what does each log line look like?
    # %(name)s is the logger name (typically the module's __name__)
    # -------------------------------------------------------------------------
    formatter = logging.Formatter(
        fmt="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%dT%H:%M:%S",
    )
    handler.setFormatter(formatter)

    # -------------------------------------------------------------------------
    # Root logger — all loggers in the app are children of this
    # -------------------------------------------------------------------------
    root_logger = logging.getLogger()
    root_logger.setLevel(numeric_level)

    # Remove any existing handlers (e.g., from uvicorn's default setup)
    root_logger.handlers.clear()
    root_logger.addHandler(handler)

    # Silence overly verbose third-party loggers
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("uvicorn.error").setLevel(logging.INFO)


def get_logger(name: str) -> logging.Logger:
    """
    Convenience function to get a named logger.

    Usage in any module:
        from app.core.logging import get_logger
        logger = get_logger(__name__)
        logger.info("document uploaded", extra={"document_id": doc_id})

    Using __name__ as the logger name means the log output shows which
    module produced the message — essential for debugging large codebases.
    """
    return logging.getLogger(name)
