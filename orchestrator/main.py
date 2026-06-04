import requests
from fastapi import FastAPI

app = FastAPI()

def call_autonomy_service(trace_id: str) -> dict:
    try:
        response = requests.post(
            "http://autonomy:8018/api/v1/autonomy/decide",
            headers={"trace_id": trace_id}
        )
        response.raise_for_status()
        return response.json()
    except requests.RequestException as e:
        return {"error": f"Autonomy service call failed: {str(e)}"}

@app.post("/api/v1/orchestrate")
async def orchestrate(trace_id: str = Header(...)):
    decision = call_autonomy_service(trace_id)
    return {"decision": decision}
