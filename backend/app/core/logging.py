"""Structured logging configuration."""

import contextvars
import json
import logging
import sys
from datetime import datetime, timezone
from typing import Any, Dict

request_id_ctx: contextvars.ContextVar[str] = contextvars.ContextVar("request_id", default="")


class JSONFormatter(logging.Formatter):
    """Formats logs as single-line JSON with timestamps and request_id."""

    def format(self, record: logging.LogRecord) -> str:
        log_obj: Dict[str, Any] = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        req_id = request_id_ctx.get()
        if req_id:
            log_obj["request_id"] = req_id

        if record.exc_info:
            log_obj["exception"] = self.formatException(record.exc_info)

        # Include custom extra fields if provided
        if hasattr(record, "extra") and isinstance(record.extra, dict):
            log_obj.update(record.extra)

        return json.dumps(log_obj)


def setup_logging(log_level: str = "INFO", app_env: str = "development") -> None:
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, log_level.upper(), logging.INFO))

    # Clear existing handlers
    root_logger.handlers = []

    handler = logging.StreamHandler(sys.stdout)
    if app_env.lower() in ("production", "staging"):
        handler.setFormatter(JSONFormatter())
    else:
        # Development readable format with timestamp and level
        formatter = logging.Formatter(
            fmt="%(asctime)s [%(levelname)s] [%(name)s] %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
        handler.setFormatter(formatter)

    root_logger.addHandler(handler)
