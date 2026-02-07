"""Structured logging for the accountability pipeline.

Uses structlog for structured, contextual logging with pipeline-specific fields.
"""

from __future__ import annotations

import logging
import sys

import structlog


def setup_logging(level: str = "INFO", json_output: bool = False) -> None:
    """Configure structured logging for the pipeline.

    Args:
        level: Log level string (DEBUG, INFO, WARNING, ERROR).
        json_output: If True, output JSON-formatted logs (for production).
    """
    log_level = getattr(logging, level.upper(), logging.INFO)

    shared_processors: list = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_log_level,
        structlog.stdlib.add_logger_name,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.UnicodeDecoder(),
    ]

    if json_output:
        renderer = structlog.processors.JSONRenderer()
    else:
        renderer = structlog.dev.ConsoleRenderer()

    structlog.configure(
        processors=[
            *shared_processors,
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ],
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )

    formatter = structlog.stdlib.ProcessorFormatter(
        processors=[
            structlog.stdlib.ProcessorFormatter.remove_processors_meta,
            renderer,
        ],
    )

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(formatter)

    root_logger = logging.getLogger()
    root_logger.handlers.clear()
    root_logger.addHandler(handler)
    root_logger.setLevel(log_level)


def get_logger(name: str, **initial_context: str) -> structlog.stdlib.BoundLogger:
    """Get a structured logger with pipeline context.

    Args:
        name: Logger name (typically module name).
        **initial_context: Additional context fields bound to every log entry.

    Returns:
        Configured bound logger.
    """
    logger = structlog.get_logger(name)
    if initial_context:
        logger = logger.bind(**initial_context)
    return logger
