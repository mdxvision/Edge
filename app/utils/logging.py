import logging
import json
import sys
import os
from datetime import datetime
from typing import Any, Dict
from pathlib import Path
import traceback
from logging.handlers import RotatingFileHandler

_logging_initialized = False

# Log file location - in project root
LOG_DIR = Path(__file__).parent.parent.parent
LOG_FILE = LOG_DIR / "app.log"


class StructuredFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        log_data = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno
        }
        
        if hasattr(record, 'request_id'):
            log_data["request_id"] = record.request_id
        if hasattr(record, 'client_ip'):
            log_data["client_ip"] = record.client_ip
        if hasattr(record, 'user_id'):
            log_data["user_id"] = record.user_id
        if hasattr(record, 'duration_ms'):
            log_data["duration_ms"] = record.duration_ms
        if hasattr(record, 'status_code'):
            log_data["status_code"] = record.status_code
        if hasattr(record, 'path'):
            log_data["path"] = record.path
        if hasattr(record, 'method'):
            log_data["method"] = record.method
        
        if record.exc_info:
            log_data["exception"] = {
                "type": record.exc_info[0].__name__ if record.exc_info[0] else None,
                "message": str(record.exc_info[1]) if record.exc_info[1] else None,
                "traceback": "".join(traceback.format_exception(*record.exc_info))
            }
        
        if hasattr(record, 'extra_data'):
            log_data["data"] = record.extra_data
        
        return json.dumps(log_data)


class RequestLogger:
    def __init__(self, logger_name: str = "edgebet.request"):
        self.logger = logging.getLogger(logger_name)
    
    def log_request(
        self,
        method: str,
        path: str,
        status_code: int,
        duration_ms: float,
        client_ip: str = None,
        user_id: int = None,
        request_id: str = None,
        extra: Dict[str, Any] = None
    ):
        level = logging.INFO if status_code < 400 else logging.WARNING if status_code < 500 else logging.ERROR
        
        extra_dict = {
            "method": method,
            "path": path,
            "status_code": status_code,
            "duration_ms": duration_ms
        }
        if client_ip:
            extra_dict["client_ip"] = client_ip
        if user_id:
            extra_dict["user_id"] = user_id
        if request_id:
            extra_dict["request_id"] = request_id
        if extra:
            extra_dict.update(extra)
        
        self.logger.log(level, f"{method} {path} - {status_code} ({duration_ms:.2f}ms)", extra=extra_dict)
    
    def log_error(
        self,
        message: str,
        exception: Exception = None,
        path: str = None,
        client_ip: str = None,
        extra: Dict[str, Any] = None
    ):
        extra_dict = {}
        if path:
            extra_dict["path"] = path
        if client_ip:
            extra_dict["client_ip"] = client_ip
        if extra:
            extra_dict.update(extra)
        
        self.logger.error(message, exc_info=exception, extra=extra_dict)


def setup_logging(level: str = "INFO", json_format: bool = False, log_to_file: bool = True) -> logging.Logger:
    global _logging_initialized

    app_logger = logging.getLogger("sports_betting")

    if _logging_initialized:
        return app_logger

    _logging_initialized = True

    app_logger.setLevel(getattr(logging, level.upper()))

    # Human-readable format for console
    console_format = logging.Formatter(
        "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%H:%M:%S"
    )

    # Detailed format for file logging
    file_format = logging.Formatter(
        "%(asctime)s | %(levelname)-8s | %(name)s:%(funcName)s:%(lineno)d | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )

    if not app_logger.handlers:
        # Console handler - always add
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(getattr(logging, level.upper()))
        if json_format:
            console_handler.setFormatter(StructuredFormatter())
        else:
            console_handler.setFormatter(console_format)
        app_logger.addHandler(console_handler)

        # File handler - rotating log file (10MB max, keep 5 backups)
        if log_to_file:
            try:
                file_handler = RotatingFileHandler(
                    LOG_FILE,
                    maxBytes=10*1024*1024,  # 10MB
                    backupCount=5,
                    encoding='utf-8'
                )
                file_handler.setLevel(logging.DEBUG)  # Capture everything in file
                file_handler.setFormatter(file_format)
                app_logger.addHandler(file_handler)
                app_logger.info(f"File logging enabled: {LOG_FILE}")
            except Exception as e:
                app_logger.warning(f"Could not set up file logging: {e}")

    # Reduce noise from third-party libraries
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)

    return app_logger


def get_logger(name: str = None) -> logging.Logger:
    """Get a logger for a specific module. Call this in any file like:

    from app.utils.logging import get_logger
    logger = get_logger(__name__)

    Then use:
    logger.debug("Detailed info for debugging")
    logger.info("Normal operation info")
    logger.warning("Something unexpected")
    logger.error("Something failed", exc_info=True)  # includes stack trace
    """
    if name:
        return logging.getLogger(f"sports_betting.{name}")
    return logging.getLogger("sports_betting")


logger = setup_logging()
request_logger = RequestLogger()
