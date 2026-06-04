"""NEUROTWIN Digital Twin — Logging (W3C trace, JSON structured)."""
import contextvars, json, logging, uuid
from datetime import datetime, timezone
from typing import Optional

_trace_id_var: contextvars.ContextVar[Optional[str]] = contextvars.ContextVar("trace_id", default=None)

def get_trace_id() -> Optional[str]:  return _trace_id_var.get()
def set_trace_id(v: str):             _trace_id_var.set(v)
def generate_trace_id() -> str:       return uuid.uuid4().hex

class _TraceFilter(logging.Filter):
    def filter(self, r):
        r.trace_id = get_trace_id() or ""; return True

class _JSONFmt(logging.Formatter):
    _SKIP = {"name","msg","args","levelname","levelno","pathname","filename","module",
             "exc_info","exc_text","stack_info","created","msecs","relativeCreated",
             "thread","threadName","processName","process","asctime","message","trace_id"}
    def format(self, r):
        d = {"ts": datetime.now(timezone.utc).isoformat(), "level": r.levelname,
             "svc": r.name, "msg": r.getMessage(), "trace_id": getattr(r,"trace_id","")}
        for k, v in r.__dict__.items():
            if k not in self._SKIP and not k.startswith("_"):
                d[k] = v
        if r.exc_info: d["exc"] = self.formatException(r.exc_info)
        return json.dumps(d)

def setup_logging(service: str = "digital_twin"):
    root = logging.getLogger()
    root.handlers.clear()
    h = logging.StreamHandler()
    h.setFormatter(_JSONFmt())
    root.addHandler(h)
    root.setLevel(logging.INFO)
    root.addFilter(_TraceFilter())
