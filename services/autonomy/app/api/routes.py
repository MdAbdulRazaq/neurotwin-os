from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import JSONResponse
from .core.autonomy_engine import AutonomyEngine
from .utils.logging_utils import get_logger

logger = get_logger(__name__)

router = APIRouter()

@router.post("/api/v1/autonomy/decide")
async def autonomy_decide(trace_id: str = Header(...)):
    try:
        engine = AutonomyEngine()
        decision = engine.run_pipeline()
        logger.info(f"Decision made for trace {trace_id}: {decision}")
        return JSONResponse(content=decision, media_type="application/json")
    except Exception as e:
        logger.error(f"Error processing decision for trace {trace_id}: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.get("/health")
async def health_check() -> JSONResponse:
    return JSONResponse(content={"status": "ok"}, media_type="application/json")
