import logging
import json
import sys
from datetime import datetime
from typing import Any, Dict
import traceback

_logging_initialized = False


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


def setup_logging(level: str = "INFO", json_format: bool = False) -> logging.Logger:
    global _logging_initialized
    
    app_logger = logging.getLogger("sports_betting")
    
    if _logging_initialized:
        return app_logger
    
    _logging_initialized = True
    
    app_logger.setLevel(getattr(logging, level.upper()))
    
    if not app_logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        handler.setLevel(getattr(logging, level.upper()))
        
        if json_format:
            handler.setFormatter(StructuredFormatter())
        else:
            handler.setFormatter(logging.Formatter(
                "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
            ))
        
        app_logger.addHandler(handler)
    
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    
    return app_logger


logger = setup_logging()
request_logger = RequestLogger()
