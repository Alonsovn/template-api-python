"""Centralized structured logging with request-correlation context.

Emits single-line JSON by default (dev/prod). Call ``initialize_logging()``
at application startup to configure level and format from YAML config.
Correlation IDs (request_id, user_id) are injected into every log record via
context variables so all lines for a request are correlated.

Usage::

    from src.app.shared.logging.logging import get_logger
    log = get_logger(__name__)
    log.info("something happened")
"""

import json
import logging
import sys
from contextvars import ContextVar
from datetime import datetime, timezone

_request_id_ctx: ContextVar[str] = ContextVar("request_id", default="-")
_user_id_ctx: ContextVar[str] = ContextVar("user_id", default="-")

_configured = False


def set_request_id(request_id: str | None) -> None:
    """Tag subsequent log lines with the current request's ID."""
    _request_id_ctx.set(request_id or "-")


def set_user_id(user_id: str | None) -> None:
    """Tag subsequent log lines with the authenticated user's ID."""
    _user_id_ctx.set(user_id or "-")


def clear_context() -> None:
    """Reset correlation IDs so lines outside a request are not mislabelled."""
    _request_id_ctx.set("-")
    _user_id_ctx.set("-")


class _ContextFilter(logging.Filter):
    """Inject the current correlation IDs into every log record."""

    def filter(self, record: logging.LogRecord) -> bool:
        record.request_id = _request_id_ctx.get()
        record.user_id = _user_id_ctx.get()
        return True


class _JsonFormatter(logging.Formatter):
    """Render a log record as a single-line JSON object."""

    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "request_id": getattr(record, "request_id", "-"),
            "user_id": getattr(record, "user_id", "-"),
            "message": record.getMessage(),
        }
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(payload, default=str)


class _PlainFormatter(logging.Formatter):
    """Render a log record as a human-readable single line for local/stage runs."""

    def format(self, record: logging.LogRecord) -> str:
        timestamp = datetime.fromtimestamp(
            record.created, tz=timezone.utc
        ).strftime("%H:%M:%S")
        ids = [
            f"{label}={value}"
            for label, value in (
                ("request_id", getattr(record, "request_id", "-")),
                ("user_id", getattr(record, "user_id", "-")),
            )
            if value != "-"
        ]
        context = f"[{' '.join(ids)}] " if ids else ""
        line = (
            f"{timestamp} [{record.levelname:<5}] "
            f"{context}{record.name} — {record.getMessage()}"
        )
        if record.exc_info:
            line += "\n" + self.formatException(record.exc_info)
        return line


def _configure_root() -> None:
    """One-time root logger bootstrap; ``initialize_logging()`` handles format changes."""
    global _configured
    if _configured:
        return

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(_JsonFormatter())
    # Filter must live on the handler: logger-level filters are not applied to
    # records propagated up from child loggers.
    handler.addFilter(_ContextFilter())

    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(logging.INFO)
    _configured = True


def initialize_logging(
    level: str | int = logging.INFO,
    format_type: str = "json",
) -> None:
    """Configure the root logger. Call once at startup after config is loaded.

    Args:
        level: Log level (e.g. ``"INFO"``, ``"DEBUG"``, or ``logging.INFO``).
        format_type: ``"json"`` for structured output or ``"text"`` for
            human-readable lines.
    """
    _configure_root()
    root = logging.getLogger()
    root.setLevel(level)
    root.handlers[0].setFormatter(
        _PlainFormatter() if format_type == "text" else _JsonFormatter()
    )


def get_logger(name: str) -> logging.Logger:
    """Return a logger that emits structured JSON with correlation-ID context."""
    _configure_root()
    return logging.getLogger(name)
