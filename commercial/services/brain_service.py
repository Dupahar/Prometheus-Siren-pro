import sys
import os
import uvicorn
from fastapi import FastAPI
from pydantic import BaseModel

# Add src to path
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

from src.core.qdrant_client import QdrantManager
from src.prometheus.patch_generator import PatchGenerator

app = FastAPI(title="Prometheus Brain (Control Plane)")

qdrant = QdrantManager()
patcher = PatchGenerator()

class Telemetry(BaseModel):
    payload: str
    source_ip: str
    score: float

@app.on_event("startup")
async def startup():
    qdrant.ensure_collections()
    
@app.post("/telemetry")
async def receive_telemetry(data: Telemetry):
    # 1. Deep Analysis
    # 2. Update Vector DB
    qdrant.upsert_vectors("attack_memory", [data.payload], [{"type": "telemetry"}])
    return {"status": "recorded"}

@app.post("/evolution/patch")
async def trigger_patch(vulnerability: str):
    # Trigger Gemini Patching
    # This would be async in production
    return {"status": "patch_scheduled"}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8001)
