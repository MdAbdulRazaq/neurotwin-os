from fastapi import FastAPI
from services.common.logging_utils import setup_logging
from services.common.fastapi_middleware import TraceMiddleware

# Setup structured logging with trace context
setup_logging(service_name="neurotwin.memory")

app = FastAPI(title="neurotwin-memory")
app.add_middleware(TraceMiddleware)

@app.get("/health")
async def health():
    return {"status": "ok", "service": "memory"}
