from fastapi import FastAPI
import uvicorn

app = FastAPI()

@app.get("/")
async def root():
    return {"message": "Backend service is running"}

@app.get("/health")
async def health():
    return {"status": "ok", "service": "backend"}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
