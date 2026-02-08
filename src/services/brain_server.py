
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from src.services.gemini_general import GeminiGeneral
import uvicorn
import logging

# Initialize App & General
app = FastAPI(title="Jirachi Brain Service")
commander = None

try:
    commander = GeminiGeneral()
except Exception as e:
    logging.error(f"Failed to initialize Gemini General: {e}")

class ThreatRequest(BaseModel):
    trace: str
    slm_score: float

@app.post("/analyze_threat")
async def analyze_threat(req: ThreatRequest):
    if not commander:
        raise HTTPException(status_code=503, detail="Gemini General not initialized")
    
    # Delegate to the General
    decision_artifact = commander.analyze_threat(req.trace, req.slm_score)
    return decision_artifact

if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000)
