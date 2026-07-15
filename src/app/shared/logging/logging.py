"""Structured logging with batch_id/publication_run_id always present in context.

Emits single-line JSON by default (dev/prod). Call
``reconfigure_logging(plain_text=True)`` at the entry point to switch to
human-readable output for local/stage runs. Correlation ids are injected into
every record via context variables so all lines for a request are correlated.
"""

import json
import logging
import sys
from contextvars import ContextVar
from datetime import datetime, timezone

_batch_id_ctx: ContextVar[str] = ContextVar("batch_id", default="-")
_publication_run_id_ctx: ContextVar[str] = ContextVar("publication_run_id", default="-")

_configured = False


def set_batch_id(batch_id: str | None) -> None:
    """Tag subsequent log lines with the request's batch_id."""
    _batch_id_ctx.set(batch_id or "-")


def set_publication_run_id(run_id: str | None) -> None:
    """Tag subsequent log lines with the request's publication_run_id."""
    _publication_run_id_ctx.set(run_id or "-")


def clear_context() -> None:
    """Reset correlation ids so lines outside a request are not mislabelled."""
    _batch_id_ctx.set("-")
    _publication_run_id_ctx.set("-")


class _ContextFilter(logging.Filter):
    """Inject the current correlation ids into every record."""

    def filter(self, record: logging.LogRecord) -> bool:
        record.batch_id = _batch_id_ctx.get()
        record.publication_run_id = _publication_run_id_ctx.get()
        return True


class _JsonFormatter(logging.Formatter):
    """Render a log record as a single-line JSON object."""

    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "batch_id": getattr(record, "batch_id", "-"),
            "publication_run_id": getattr(record, "publication_run_id", "-"),
            "message": record.getMessage(),
        }
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(payload, default=str)


class _PlainFormatter(logging.Formatter):
    """Render a log record as a human-readable single line for local/stage runs."""

    def format(self, record: logging.LogRecord) -> str:
        timestamp = datetime.fromtimestamp(record.created, tz=timezone.utc).strftime("%H:%M:%S")
        ids = [
            f"{label}={value}"
            for label, value in (
                ("batch_id", getattr(record, "batch_id", "-")),
                ("publication_run_id", getattr(record, "publication_run_id", "-")),
            )
            if value != "-"
        ]
        context = f"[{' '.join(ids)}] " if ids else ""
        line = f"{timestamp} [{record.levelname:<5}] {context}{record.name} — {record.getMessage()}"
        if record.exc_info:
            line += "\n" + self.formatException(record.exc_info)
        return line


def _configure_root() -> None:
    """One-time root logger bootstrap; reconfigure_logging() handles format changes."""
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


def reconfigure_logging(plain_text: bool = False, level: str | int = logging.INFO) -> None:
    """Switch the root handler formatter and level. Call once at entry after config is loaded."""
    _configure_root()
    root = logging.getLogger()
    root.setLevel(level)
    root.handlers[0].setFormatter(_PlainFormatter() if plain_text else _JsonFormatter())


def get_logger(name: str) -> logging.Logger:
    """Return a logger that emits structured JSON with correlation-id context."""
    _configure_root()
    return logging.getLogger(name)
