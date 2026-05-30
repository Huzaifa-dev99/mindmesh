from __future__ import annotations

import json
import logging
import os
import time
import traceback
from contextlib import contextmanager
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Any, Iterator

PROJECT_ROOT = Path(__file__).resolve().parents[2]
LOG_DIR = Path(os.getenv("MM_POC_LOG_DIR", PROJECT_ROOT / "logs"))
LOG_LEVEL = os.getenv("MM_POC_LOG_LEVEL", os.getenv("LOG_LEVEL", "INFO")).upper()
MAX_LOG_BYTES = int(os.getenv("MM_POC_LOG_MAX_BYTES", "10485760"))
BACKUP_COUNT = int(os.getenv("MM_POC_LOG_BACKUP_COUNT", "5"))

SENSITIVE_KEYS = {
    "api_key",
    "authorization",
    "password",
    "secret",
    "secret_key",
    "token",
}


class StructuredLogFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "timestamp": self.formatTime(record, "%Y-%m-%dT%H:%M:%S%z"),
            "level": record.levelname,
            "logger": record.name,
            "module": record.module,
            "file": record.filename,
            "function": record.funcName,
            "line": record.lineno,
            "message": record.getMessage(),
        }
        extra = getattr(record, "event", None)
        if isinstance(extra, dict):
            payload["event"] = sanitize(extra)
        if record.exc_info:
            payload["exception"] = "".join(traceback.format_exception(*record.exc_info)).strip()
        return json.dumps(payload, ensure_ascii=False, default=str)


def sanitize(value: Any) -> Any:
    if isinstance(value, dict):
        cleaned = {}
        for key, item in value.items():
            key_text = str(key).lower()
            if any(sensitive in key_text for sensitive in SENSITIVE_KEYS):
                cleaned[key] = "***"
            else:
                cleaned[key] = sanitize(item)
        return cleaned
    if isinstance(value, list):
        return [sanitize(item) for item in value]
    if isinstance(value, tuple):
        return tuple(sanitize(item) for item in value)
    return value


def configure_logging() -> None:
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    root = logging.getLogger()
    if getattr(root, "_mm_poc_logging_configured", False):
        return

    root.setLevel(getattr(logging, LOG_LEVEL, logging.INFO))
    formatter = StructuredLogFormatter()

    app_handler = RotatingFileHandler(
        LOG_DIR / "app.log",
        maxBytes=MAX_LOG_BYTES,
        backupCount=BACKUP_COUNT,
        encoding="utf-8",
    )
    app_handler.setLevel(getattr(logging, LOG_LEVEL, logging.INFO))
    app_handler.setFormatter(formatter)

    error_handler = RotatingFileHandler(
        LOG_DIR / "errors.log",
        maxBytes=MAX_LOG_BYTES,
        backupCount=BACKUP_COUNT,
        encoding="utf-8",
    )
    error_handler.setLevel(logging.ERROR)
    error_handler.setFormatter(formatter)

    root.addHandler(app_handler)
    root.addHandler(error_handler)
    root._mm_poc_logging_configured = True

    logging.getLogger(__name__).info(
        "logging configured",
        extra={"event": {"log_dir": str(LOG_DIR), "log_level": LOG_LEVEL}},
    )


def get_logger(name: str) -> logging.Logger:
    configure_logging()
    return logging.getLogger(name)


def trace(message: str, logger: logging.Logger | None = None, level: int = logging.INFO) -> None:
    text = str(message)
    for line in text.splitlines() or [""]:
        print(f"====> {line}")
    if logger:
        logger.log(level, text, stacklevel=2)


@contextmanager
def log_timing(
    logger: logging.Logger,
    operation: str,
    **event: Any,
) -> Iterator[None]:
    start = time.perf_counter()
    logger.debug("%s started", operation, extra={"event": event})
    try:
        yield
    except Exception:
        elapsed_ms = round((time.perf_counter() - start) * 1000, 2)
        logger.exception(
            "%s failed",
            operation,
            extra={"event": {**event, "elapsed_ms": elapsed_ms}},
        )
        raise
    else:
        elapsed_ms = round((time.perf_counter() - start) * 1000, 2)
        logger.info(
            "%s completed",
            operation,
            extra={"event": {**event, "elapsed_ms": elapsed_ms}},
        )
