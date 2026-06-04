"""
NEUROTWIN logging infrastructure with structured logging, trace context, and W3C Traceparent.
"""

import contextvars
import json
import logging
import uuid
from datetime import datetime
from typing import Any, Dict, Optional

# Context variables for trace and span
_trace_id_var: contextvars.ContextVar[Optional[str]] = contextvars.ContextVar("trace_id", default=None)
_span_id_var: contextvars.ContextVar[Optional[str]] = contextvars.ContextVar("span_id", default=None)

def get_trace_id() -> Optional[str]:
    return _trace_id_var.get()

def set_trace_id(trace_id: str):
    _trace_id_var.set(trace_id)

def get_span_id() -> Optional[str]:
    return _span_id_var.get()

def set_span_id(span_id: str):
    _span_id_var.set(span_id)

def generate_trace_id() -> str:
    """Generate a 32-character hex trace ID (W3C compliant)."""
    return uuid.uuid4().hex

def generate_span_id() -> str:
    """Generate a 16-character hex span ID."""
    return uuid.uuid4().hex[:16]

def get_traceparent() -> str:
    """Get current traceparent header value."""
    trace_id = get_trace_id()
    span_id = get_span_id()
    if trace_id and span_id:
        return f"00-{trace_id}-{span_id}-01"
    return ""

def set_traceparent(traceparent: str):
    """Parse W3C traceparent header and set trace_id and span_id."""
    parts = traceparent.split("-")
    if len(parts) == 4 and parts[0] == "00":
        version, trace_id, parent_span_id, flags = parts
        if len(trace_id) == 32 and len(parent_span_id) == 16:
            set_trace_id(trace_id)
            set_span_id(parent_span_id)

class TraceIDFilter(logging.Filter):
    """Filter that adds trace_id and span_id to log records."""
    def filter(self, record: logging.LogRecord) -> bool:
        record.trace_id = get_trace_id() or ""
        record.span_id = get_span_id() or ""
        return True

class JSONFormatter(logging.Formatter):
    """Custom JSON formatter that includes standard fields and any extra attributes."""
    def format(self, record):
        # Build base log record
        log_record = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "level": record.levelname,
            "service": record.name,
            "message": record.getMessage(),
            "trace_id": getattr(record, "trace_id", ""),
            "span_id": getattr(record, "span_id", ""),
        }

        # Include any extra fields passed via extra={...}
        standard_attrs = {
            "name", "msg", "args", "levelname", "levelno", "pathname", "filename",
            "module", "exc_info", "exc_text", "stack_info", "created", "msecs",
            "relativeCreated", "thread", "threadName", "processName", "process",
            "asctime", "message", "trace_id", "span_id"
        }
        for key, value in record.__dict__.items():
            if key not in standard_attrs and not key.startswith("_"):
                log_record[key] = value

        if record.exc_info:
            log_record["exception"] = self.formatException(record.exc_info)

        return json.dumps(log_record)

def setup_logging():
    """Configure root logger with JSON formatter and trace filter."""
    root_logger = logging.getLogger()
    # Clear existing handlers if any
    if root_logger.hasHandlers():
        root_logger.handlers.clear()

    handler = logging.StreamHandler()
    handler.setLevel(logging.INFO)
    formatter = JSONFormatter()
    handler.setFormatter(formatter)
    root_logger.addHandler(handler)
    root_logger.setLevel(logging.INFO)

    # Add trace/span filter
    root_logger.addFilter(TraceIDFilter())
