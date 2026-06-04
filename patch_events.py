import pathlib, sys
p = pathlib.Path("app/routers/events.py")
t = p.read_text()
if "@router.get" in t:
    print("SKIP: already patched"); sys.exit(0)
addon = """

@router.get("")
@router.get("/")
async def list_events(db=None):
    import uuid
    from fastapi.responses import JSONResponse
    return JSONResponse({"events": [], "count": 0, "trace_id": str(uuid.uuid4())})
"""
p.write_text(t + addon)
print("OK: events GET added")
